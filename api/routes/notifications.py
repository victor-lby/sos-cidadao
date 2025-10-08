# SPDX-License-Identifier: Apache-2.0

"""
Notification workflow endpoints.

This module implements the notification workflow API endpoints including
webhook intake, listing, detail view, approval, and denial operations.
"""

from flask import Blueprint, request, jsonify, current_app
from flask_openapi3 import APIBlueprint, Tag
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from functools import wraps

# Import domain logic and models
from ..domain import notifications as notification_domain
from ..models.requests import (
    NotificationWebhookRequest, ApproveNotificationRequest, 
    DenyNotificationRequest, NotificationFilters, PaginationParams
)
from ..models.responses import (
    NotificationResponse, NotificationCollectionResponse,
    ErrorResponse, ValidationErrorResponse
)
from ..models.entities import UserContext, NotificationStatus
from ..services.mongodb import MongoDBService
from ..services.redis import RedisService
from ..services.auth import AuthService
from ..services.hal import HALFormatter
from ..middleware.auth import require_auth
from ..utils.request import get_request_context

# Set up logging and tracing
logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Create API blueprint
notifications_tag = Tag(name="Notifications", description="Notification workflow management")
notifications_bp = APIBlueprint(
    'notifications', 
    __name__, 
    url_prefix='/api/notifications',
    abp_tags=[notifications_tag]
)


def require_jwt(f):
    """Simple JWT requirement decorator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get auth middleware from current app
        auth_middleware = current_app.auth_middleware
        return require_auth(auth_middleware)(f)(*args, **kwargs)
    return decorated_function


@notifications_bp.post('/incoming')
@require_jwt
def receive_notification_webhook():
    """
    Receive notification via webhook.
    
    This endpoint accepts incoming notifications from external systems,
    validates the payload, and stores them with status='received' for moderation.
    """
    from flask import g
    user_context = g.user_context
    
    with tracer.start_as_current_span(
        "notification.webhook.receive",
        attributes={
            "user.id": user_context.user_id,
            "organization.id": user_context.org_id,
            "operation": "receive_webhook"
        }
    ) as span:
        try:
            # Get request data
            request_data = request.get_json()
            if not request_data:
                span.set_status(Status(StatusCode.ERROR, "Missing request body"))
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Missing request body",
                    400,
                    "validation_error",
                    request.url
                )), 400
            
            # Validate request using Pydantic
            try:
                webhook_request = NotificationWebhookRequest(**request_data)
                span.set_attributes({
                    "notification.title": webhook_request.title[:50],  # Truncated for logs
                    "notification.severity": webhook_request.severity,
                    "notification.targets_count": len(webhook_request.targets or [])
                })
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, "Validation failed"))
                logger.warning(
                    "Webhook payload validation failed",
                    extra={
                        "user_id": user_context.user_id,
                        "org_id": user_context.org_id,
                        "validation_errors": str(e),
                        "payload_keys": list(request_data.keys()) if request_data else []
                    }
                )
                return jsonify(current_app.hal_formatter.builder.build_validation_error_response(
                    str(e),
                    request.url
                )), 400
            
            # Extract origin from request headers or use default
            origin = request.headers.get('X-Origin', 'webhook')
            span.set_attribute("notification.origin", origin)
            
            # Process notification using domain logic
            with tracer.start_as_current_span("domain.notification.receive") as domain_span:
                result = notification_domain.receive_notification(
                    payload=request_data,
                    origin=origin,
                    user_context=user_context
                )
                
                domain_span.set_attributes({
                    "domain.operation": "receive_notification",
                    "domain.result": "success" if result.success else "failed"
                })
            
            if not result.success:
                span.set_status(Status(StatusCode.ERROR, result.error_message))
                logger.error(
                    "Failed to process notification webhook",
                    extra={
                        "user_id": user_context.user_id,
                        "org_id": user_context.org_id,
                        "error": result.error_message,
                        "validation_errors": result.validation_errors
                    }
                )
                
                if result.validation_errors:
                    return jsonify(current_app.hal_formatter.builder.build_validation_error_response(
                        result.error_message,
                        request.url,
                        result.validation_errors
                    )), 400
                else:
                    return jsonify(current_app.hal_formatter.builder.build_error_response(
                        result.error_message,
                        500,
                        "processing_error",
                        request.url
                    )), 500
            
            # Store notification in database
            with tracer.start_as_current_span("db.notification.create") as db_span:
                notification_dict = result.notification.model_dump()
                notification_id = current_app.mongodb_service.create("notifications", notification_dict)
                
                db_span.set_attributes({
                    "db.collection": "notifications",
                    "db.operation": "create",
                    "db.organization_id": user_context.org_id,
                    "notification.id": notification_id
                })
            
            # Update notification with database ID
            result.notification.id = notification_id
            span.set_attribute("notification.id", notification_id)
            
            # Build HAL response
            hal_response = notification_domain.build_notification_hal_response(
                result.notification,
                user_context,
                current_app.config['BASE_URL']
            )
            
            # Log successful creation
            logger.info(
                "Notification received successfully via webhook",
                extra={
                    "notification_id": notification_id,
                    "user_id": user_context.user_id,
                    "org_id": user_context.org_id,
                    "origin": origin,
                    "severity": result.notification.severity,
                    "title": result.notification.title[:50]
                }
            )
            
            span.set_status(Status(StatusCode.OK))
            return jsonify(hal_response), 201
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error(
                "Unexpected error in notification webhook",
                extra={
                    "user_id": user_context.user_id,
                    "org_id": user_context.org_id,
                    "error": str(e)
                },
                exc_info=True
            )
            
            return jsonify(current_app.hal_formatter.builder.build_error_response(
                "Internal server error",
                500,
                "internal_error",
                request.url
            )), 500


@notifications_bp.get('')
@require_jwt
def list_notifications():
    """
    List notifications with filtering and pagination.
    
    Returns a HAL collection of notifications with pagination links
    and filtering capabilities.
    """
    from flask import g
    user_context = g.user_context
    
    with tracer.start_as_current_span(
        "notification.list",
        attributes={
            "user.id": user_context.user_id,
            "organization.id": user_context.org_id,
            "operation": "list"
        }
    ) as span:
        try:
            # Parse query parameters
            page = int(request.args.get('page', 1))
            page_size = min(int(request.args.get('size', 20)), 100)  # Max 100 items per page
            
            # Parse filters
            filters = notification_domain.NotificationFilters(
                status=request.args.get('status'),
                severity=int(request.args.get('severity')) if request.args.get('severity') else None,
                search_term=request.args.get('search'),
                origin=request.args.get('origin'),
                target_ids=request.args.getlist('target_ids'),
                category_ids=request.args.getlist('category_ids')
            )
            
            # Parse date filters
            if request.args.get('date_from'):
                try:
                    filters.date_from = datetime.fromisoformat(request.args.get('date_from'))
                except ValueError:
                    return jsonify(current_app.hal_formatter.builder.build_error_response(
                        "Invalid date_from format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
                        400,
                        "validation_error",
                        request.url
                    )), 400
            
            if request.args.get('date_to'):
                try:
                    filters.date_to = datetime.fromisoformat(request.args.get('date_to'))
                except ValueError:
                    return jsonify(current_app.hal_formatter.builder.build_error_response(
                        "Invalid date_to format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
                        400,
                        "validation_error",
                        request.url
                    )), 400
            
            span.set_attributes({
                "pagination.page": page,
                "pagination.page_size": page_size,
                "filters.status": filters.status,
                "filters.severity": filters.severity,
                "filters.search_term": filters.search_term[:50] if filters.search_term else None
            })
            
            # Query notifications from database
            with tracer.start_as_current_span("db.notification.list") as db_span:
                # Build MongoDB query
                query = {"organizationId": user_context.org_id, "deletedAt": None}
                
                if filters.status:
                    query["status"] = filters.status
                
                if filters.severity is not None:
                    query["severity"] = filters.severity
                
                if filters.origin:
                    query["origin"] = filters.origin
                
                if filters.target_ids:
                    query["targetIds"] = {"$in": filters.target_ids}
                
                if filters.category_ids:
                    query["categoryIds"] = {"$in": filters.category_ids}
                
                if filters.date_from or filters.date_to:
                    date_query = {}
                    if filters.date_from:
                        date_query["$gte"] = filters.date_from
                    if filters.date_to:
                        date_query["$lte"] = filters.date_to
                    query["createdAt"] = date_query
                
                # Add text search if provided
                if filters.search_term:
                    query["$or"] = [
                        {"title": {"$regex": filters.search_term, "$options": "i"}},
                        {"body": {"$regex": filters.search_term, "$options": "i"}}
                    ]
                
                # Get paginated results
                pagination_result = current_app.mongodb_service.paginate_by_org(
                    "notifications",
                    user_context.org_id,
                    page,
                    page_size,
                    query
                )
                
                db_span.set_attributes({
                    "db.collection": "notifications",
                    "db.operation": "paginate",
                    "db.organization_id": user_context.org_id,
                    "db.result_count": len(pagination_result.items),
                    "db.total_count": pagination_result.total
                })
            
            # Convert to notification entities
            notifications = []
            for item in pagination_result.items:
                try:
                    # Convert MongoDB document to Notification entity
                    notification_data = {
                        "id": str(item["_id"]),
                        "organization_id": item["organizationId"],
                        "title": item["title"],
                        "body": item["body"],
                        "severity": item["severity"],
                        "origin": item["origin"],
                        "original_payload": item["originalPayload"],
                        "base_target_id": item.get("baseTargetId"),
                        "target_ids": item.get("targetIds", []),
                        "category_ids": item.get("categoryIds", []),
                        "status": item["status"],
                        "denial_reason": item.get("denialReason"),
                        "approved_at": item.get("approvedAt"),
                        "approved_by": item.get("approvedBy"),
                        "denied_at": item.get("deniedAt"),
                        "denied_by": item.get("deniedBy"),
                        "dispatched_at": item.get("dispatchedAt"),
                        "correlation_id": item.get("correlationId"),
                        "created_at": item["createdAt"],
                        "updated_at": item["updatedAt"],
                        "deleted_at": item.get("deletedAt"),
                        "created_by": item["createdBy"],
                        "updated_by": item["updatedBy"],
                        "schema_version": item.get("schemaVersion", 1)
                    }
                    
                    from ..models.entities import Notification
                    notification = Notification(**notification_data)
                    notifications.append(notification)
                    
                except Exception as e:
                    logger.warning(
                        f"Failed to parse notification {item.get('_id')}: {str(e)}",
                        extra={
                            "notification_id": str(item.get("_id")),
                            "org_id": user_context.org_id,
                            "parse_error": str(e)
                        }
                    )
                    continue
            
            # Build HAL collection response
            hal_response = notification_domain.build_notification_collection_hal_response(
                notifications,
                user_context,
                current_app.config['BASE_URL'],
                page,
                page_size,
                pagination_result.total
            )
            
            # Log successful listing
            logger.info(
                "Notifications listed successfully",
                extra={
                    "user_id": user_context.user_id,
                    "org_id": user_context.org_id,
                    "page": page,
                    "page_size": page_size,
                    "total_count": pagination_result.total,
                    "returned_count": len(notifications)
                }
            )
            
            span.set_status(Status(StatusCode.OK))
            return jsonify(hal_response), 200
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error(
                "Unexpected error listing notifications",
                extra={
                    "user_id": user_context.user_id,
                    "org_id": user_context.org_id,
                    "error": str(e)
                },
                exc_info=True
            )
            
            return jsonify(current_app.hal_formatter.builder.build_error_response(
                "Internal server error",
                500,
                "internal_error",
                request.url
            )), 500


@notifications_bp.get('/<notification_id>')
@require_jwt
def get_notification_detail(notification_id: str):
    """
    Get notification detail with HAL affordance links.
    
    Returns detailed notification information with conditional action links
    based on current status and user permissions.
    """
    from flask import g
    user_context = g.user_context
    
    with tracer.start_as_current_span(
        "notification.detail",
        attributes={
            "user.id": user_context.user_id,
            "organization.id": user_context.org_id,
            "notification.id": notification_id,
            "operation": "detail"
        }
    ) as span:
        try:
            # Get notification from database
            with tracer.start_as_current_span("db.notification.get") as db_span:
                notification_doc = current_app.mongodb_service.find_one_by_org(
                    "notifications",
                    user_context.org_id,
                    notification_id
                )
                
                db_span.set_attributes({
                    "db.collection": "notifications",
                    "db.operation": "find_one",
                    "db.organization_id": user_context.org_id,
                    "db.found": notification_doc is not None
                })
            
            if not notification_doc:
                span.set_status(Status(StatusCode.ERROR, "Notification not found"))
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Notification not found",
                    404,
                    "not_found",
                    request.url
                )), 404
            
            # Convert to notification entity
            try:
                notification_data = {
                    "id": str(notification_doc["_id"]),
                    "organization_id": notification_doc["organizationId"],
                    "title": notification_doc["title"],
                    "body": notification_doc["body"],
                    "severity": notification_doc["severity"],
                    "origin": notification_doc["origin"],
                    "original_payload": notification_doc["originalPayload"],
                    "base_target_id": notification_doc.get("baseTargetId"),
                    "target_ids": notification_doc.get("targetIds", []),
                    "category_ids": notification_doc.get("categoryIds", []),
                    "status": notification_doc["status"],
                    "denial_reason": notification_doc.get("denialReason"),
                    "approved_at": notification_doc.get("approvedAt"),
                    "approved_by": notification_doc.get("approvedBy"),
                    "denied_at": notification_doc.get("deniedAt"),
                    "denied_by": notification_doc.get("deniedBy"),
                    "dispatched_at": notification_doc.get("dispatchedAt"),
                    "correlation_id": notification_doc.get("correlationId"),
                    "created_at": notification_doc["createdAt"],
                    "updated_at": notification_doc["updatedAt"],
                    "deleted_at": notification_doc.get("deletedAt"),
                    "created_by": notification_doc["createdBy"],
                    "updated_by": notification_doc["updatedBy"],
                    "schema_version": notification_doc.get("schemaVersion", 1)
                }
                
                from ..models.entities import Notification
                notification = Notification(**notification_data)
                
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, "Failed to parse notification"))
                logger.error(
                    f"Failed to parse notification {notification_id}: {str(e)}",
                    extra={
                        "notification_id": notification_id,
                        "org_id": user_context.org_id,
                        "parse_error": str(e)
                    }
                )
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Failed to parse notification data",
                    500,
                    "data_error",
                    request.url
                )), 500
            
            # Build HAL response with affordance links
            hal_response = notification_domain.build_notification_hal_response(
                notification,
                user_context,
                current_app.config['BASE_URL'],
                include_embedded=True
            )
            
            # Log successful retrieval
            logger.info(
                "Notification detail retrieved successfully",
                extra={
                    "notification_id": notification_id,
                    "user_id": user_context.user_id,
                    "org_id": user_context.org_id,
                    "status": notification.status,
                    "severity": notification.severity
                }
            )
            
            span.set_status(Status(StatusCode.OK))
            return jsonify(hal_response), 200
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error(
                "Unexpected error retrieving notification detail",
                extra={
                    "notification_id": notification_id,
                    "user_id": user_context.user_id,
                    "org_id": user_context.org_id,
                    "error": str(e)
                },
                exc_info=True
            )
            
            return jsonify(current_app.hal_formatter.builder.build_error_response(
                "Internal server error",
                500,
                "internal_error",
                request.url
            )), 500


@notifications_bp.post('/<notification_id>/approve')
@require_jwt
def approve_notification(notification_id: str):
    """
    Approve notification for dispatch.
    
    This endpoint approves a notification, validates target/category selections,
    and triggers AMQP publishing for dispatch to external systems.
    """
    from flask import g
    user_context = g.user_context
    
    with tracer.start_as_current_span(
        "notification.approve",
        attributes={
            "user.id": user_context.user_id,
            "organization.id": user_context.org_id,
            "notification.id": notification_id,
            "operation": "approve"
        }
    ) as span:
        try:
            # Check permission
            if not user_context.has_permission("notification:approve"):
                span.set_status(Status(StatusCode.ERROR, "Insufficient permissions"))
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Insufficient permissions to approve notifications",
                    403,
                    "insufficient_permissions",
                    request.url
                )), 403
            
            # Get request data
            request_data = request.get_json()
            if not request_data:
                span.set_status(Status(StatusCode.ERROR, "Missing request body"))
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Missing request body",
                    400,
                    "validation_error",
                    request.url
                )), 400
            
            # Validate request using Pydantic
            try:
                approve_request = ApproveNotificationRequest(**request_data)
                span.set_attributes({
                    "approval.targets_count": len(approve_request.target_ids),
                    "approval.categories_count": len(approve_request.category_ids)
                })
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, "Validation failed"))
                logger.warning(
                    "Approval request validation failed",
                    extra={
                        "notification_id": notification_id,
                        "user_id": user_context.user_id,
                        "org_id": user_context.org_id,
                        "validation_errors": str(e)
                    }
                )
                return jsonify(current_app.hal_formatter.builder.build_validation_error_response(
                    str(e),
                    request.url
                )), 400
            
            # Get notification from database
            with tracer.start_as_current_span("db.notification.get") as db_span:
                notification_doc = current_app.mongodb_service.find_one_by_org(
                    "notifications",
                    user_context.org_id,
                    notification_id
                )
                
                db_span.set_attributes({
                    "db.collection": "notifications",
                    "db.operation": "find_one",
                    "db.organization_id": user_context.org_id,
                    "db.found": notification_doc is not None
                })
            
            if not notification_doc:
                span.set_status(Status(StatusCode.ERROR, "Notification not found"))
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Notification not found",
                    404,
                    "not_found",
                    request.url
                )), 404
            
            # Convert to notification entity
            try:
                notification_data = {
                    "id": str(notification_doc["_id"]),
                    "organization_id": notification_doc["organizationId"],
                    "title": notification_doc["title"],
                    "body": notification_doc["body"],
                    "severity": notification_doc["severity"],
                    "origin": notification_doc["origin"],
                    "original_payload": notification_doc["originalPayload"],
                    "base_target_id": notification_doc.get("baseTargetId"),
                    "target_ids": notification_doc.get("targetIds", []),
                    "category_ids": notification_doc.get("categoryIds", []),
                    "status": notification_doc["status"],
                    "denial_reason": notification_doc.get("denialReason"),
                    "approved_at": notification_doc.get("approvedAt"),
                    "approved_by": notification_doc.get("approvedBy"),
                    "denied_at": notification_doc.get("deniedAt"),
                    "denied_by": notification_doc.get("deniedBy"),
                    "dispatched_at": notification_doc.get("dispatchedAt"),
                    "correlation_id": notification_doc.get("correlationId"),
                    "created_at": notification_doc["createdAt"],
                    "updated_at": notification_doc["updatedAt"],
                    "deleted_at": notification_doc.get("deletedAt"),
                    "created_by": notification_doc["createdBy"],
                    "updated_by": notification_doc["updatedBy"],
                    "schema_version": notification_doc.get("schemaVersion", 1)
                }
                
                from ..models.entities import Notification
                notification = Notification(**notification_data)
                
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, "Failed to parse notification"))
                logger.error(
                    f"Failed to parse notification {notification_id}: {str(e)}",
                    extra={
                        "notification_id": notification_id,
                        "org_id": user_context.org_id,
                        "parse_error": str(e)
                    }
                )
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Failed to parse notification data",
                    500,
                    "data_error",
                    request.url
                )), 500
            
            # Process approval using domain logic
            with tracer.start_as_current_span("domain.notification.approve") as domain_span:
                result = notification_domain.approve_notification(
                    notification,
                    approve_request.target_ids,
                    approve_request.category_ids,
                    user_context
                )
                
                domain_span.set_attributes({
                    "domain.operation": "approve_notification",
                    "domain.result": "success" if result.success else "failed"
                })
            
            if not result.success:
                span.set_status(Status(StatusCode.ERROR, result.error_message))
                logger.error(
                    "Failed to approve notification",
                    extra={
                        "notification_id": notification_id,
                        "user_id": user_context.user_id,
                        "org_id": user_context.org_id,
                        "error": result.error_message,
                        "validation_errors": result.validation_errors
                    }
                )
                
                if result.validation_errors:
                    return jsonify(current_app.hal_formatter.builder.build_validation_error_response(
                        result.error_message,
                        request.url,
                        result.validation_errors
                    )), 400
                else:
                    return jsonify(current_app.hal_formatter.builder.build_error_response(
                        result.error_message,
                        500,
                        "processing_error",
                        request.url
                    )), 500
            
            # Update notification in database
            with tracer.start_as_current_span("db.notification.update") as db_span:
                update_data = result.notification.model_dump()
                update_data.pop("id", None)  # Remove ID from update data
                
                success = current_app.mongodb_service.update_by_org(
                    "notifications",
                    user_context.org_id,
                    notification_id,
                    update_data
                )
                
                db_span.set_attributes({
                    "db.collection": "notifications",
                    "db.operation": "update",
                    "db.organization_id": user_context.org_id,
                    "db.success": success
                })
                
                if not success:
                    span.set_status(Status(StatusCode.ERROR, "Failed to update notification"))
                    logger.error(
                        "Failed to update notification in database",
                        extra={
                            "notification_id": notification_id,
                            "user_id": user_context.user_id,
                            "org_id": user_context.org_id
                        }
                    )
                    return jsonify(current_app.hal_formatter.builder.build_error_response(
                        "Failed to update notification",
                        500,
                        "database_error",
                        request.url
                    )), 500
            
            # TODO: Integrate with AMQP publishing (placeholder for now)
            # This will be implemented in task 6 (AMQP message publishing)
            with tracer.start_as_current_span("amqp.notification.publish") as amqp_span:
                amqp_span.set_attributes({
                    "amqp.operation": "publish_notification",
                    "amqp.status": "placeholder",
                    "notification.id": notification_id,
                    "targets.count": len(approve_request.target_ids),
                    "categories.count": len(approve_request.category_ids)
                })
                
                logger.info(
                    "AMQP publishing placeholder - notification approved",
                    extra={
                        "notification_id": notification_id,
                        "user_id": user_context.user_id,
                        "org_id": user_context.org_id,
                        "target_ids": approve_request.target_ids,
                        "category_ids": approve_request.category_ids,
                        "note": "AMQP integration will be implemented in task 6"
                    }
                )
            
            # Create audit log entry
            with tracer.start_as_current_span("audit.log_approval") as audit_span:
                # TODO: Implement audit logging (will be done in task 7)
                audit_span.set_attributes({
                    "audit.operation": "log_approval",
                    "audit.status": "placeholder",
                    "notification.id": notification_id,
                    "user.id": user_context.user_id
                })
                
                logger.info(
                    "Audit logging placeholder - notification approved",
                    extra={
                        "notification_id": notification_id,
                        "user_id": user_context.user_id,
                        "org_id": user_context.org_id,
                        "action": "approve",
                        "before_status": notification.status,
                        "after_status": result.notification.status,
                        "note": "Audit service will be implemented in task 7"
                    }
                )
            
            # Build HAL response
            hal_response = notification_domain.build_notification_hal_response(
                result.notification,
                user_context,
                current_app.config['BASE_URL']
            )
            
            # Log successful approval
            logger.info(
                "Notification approved successfully",
                extra={
                    "notification_id": notification_id,
                    "user_id": user_context.user_id,
                    "org_id": user_context.org_id,
                    "target_ids": approve_request.target_ids,
                    "category_ids": approve_request.category_ids,
                    "severity": result.notification.severity,
                    "title": result.notification.title[:50]
                }
            )
            
            span.set_status(Status(StatusCode.OK))
            return jsonify(hal_response), 200
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error(
                "Unexpected error approving notification",
                extra={
                    "notification_id": notification_id,
                    "user_id": user_context.user_id,
                    "org_id": user_context.org_id,
                    "error": str(e)
                },
                exc_info=True
            )
            
            return jsonify(current_app.hal_formatter.builder.build_error_response(
                "Internal server error",
                500,
                "internal_error",
                request.url
            )), 500

@not
ifications_bp.post('/<notification_id>/deny')
@require_jwt
def deny_notification(notification_id: str):
    """
    Deny notification with reason.
    
    This endpoint denies a notification, stores the denial reason,
    and creates an audit trail for the decision.
    """
    from flask import g
    user_context = g.user_context
    
    with tracer.start_as_current_span(
        "notification.deny",
        attributes={
            "user.id": user_context.user_id,
            "organization.id": user_context.org_id,
            "notification.id": notification_id,
            "operation": "deny"
        }
    ) as span:
        try:
            # Check permission
            if not user_context.has_permission("notification:deny"):
                span.set_status(Status(StatusCode.ERROR, "Insufficient permissions"))
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Insufficient permissions to deny notifications",
                    403,
                    "insufficient_permissions",
                    request.url
                )), 403
            
            # Get request data
            request_data = request.get_json()
            if not request_data:
                span.set_status(Status(StatusCode.ERROR, "Missing request body"))
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Missing request body",
                    400,
                    "validation_error",
                    request.url
                )), 400
            
            # Validate request using Pydantic
            try:
                deny_request = DenyNotificationRequest(**request_data)
                span.set_attribute("denial.reason_length", len(deny_request.reason))
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, "Validation failed"))
                logger.warning(
                    "Denial request validation failed",
                    extra={
                        "notification_id": notification_id,
                        "user_id": user_context.user_id,
                        "org_id": user_context.org_id,
                        "validation_errors": str(e)
                    }
                )
                return jsonify(current_app.hal_formatter.builder.build_validation_error_response(
                    str(e),
                    request.url
                )), 400
            
            # Get notification from database
            with tracer.start_as_current_span("db.notification.get") as db_span:
                notification_doc = current_app.mongodb_service.find_one_by_org(
                    "notifications",
                    user_context.org_id,
                    notification_id
                )
                
                db_span.set_attributes({
                    "db.collection": "notifications",
                    "db.operation": "find_one",
                    "db.organization_id": user_context.org_id,
                    "db.found": notification_doc is not None
                })
            
            if not notification_doc:
                span.set_status(Status(StatusCode.ERROR, "Notification not found"))
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Notification not found",
                    404,
                    "not_found",
                    request.url
                )), 404
            
            # Convert to notification entity
            try:
                notification_data = {
                    "id": str(notification_doc["_id"]),
                    "organization_id": notification_doc["organizationId"],
                    "title": notification_doc["title"],
                    "body": notification_doc["body"],
                    "severity": notification_doc["severity"],
                    "origin": notification_doc["origin"],
                    "original_payload": notification_doc["originalPayload"],
                    "base_target_id": notification_doc.get("baseTargetId"),
                    "target_ids": notification_doc.get("targetIds", []),
                    "category_ids": notification_doc.get("categoryIds", []),
                    "status": notification_doc["status"],
                    "denial_reason": notification_doc.get("denialReason"),
                    "approved_at": notification_doc.get("approvedAt"),
                    "approved_by": notification_doc.get("approvedBy"),
                    "denied_at": notification_doc.get("deniedAt"),
                    "denied_by": notification_doc.get("deniedBy"),
                    "dispatched_at": notification_doc.get("dispatchedAt"),
                    "correlation_id": notification_doc.get("correlationId"),
                    "created_at": notification_doc["createdAt"],
                    "updated_at": notification_doc["updatedAt"],
                    "deleted_at": notification_doc.get("deletedAt"),
                    "created_by": notification_doc["createdBy"],
                    "updated_by": notification_doc["updatedBy"],
                    "schema_version": notification_doc.get("schemaVersion", 1)
                }
                
                from ..models.entities import Notification
                notification = Notification(**notification_data)
                
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, "Failed to parse notification"))
                logger.error(
                    f"Failed to parse notification {notification_id}: {str(e)}",
                    extra={
                        "notification_id": notification_id,
                        "org_id": user_context.org_id,
                        "parse_error": str(e)
                    }
                )
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Failed to parse notification data",
                    500,
                    "data_error",
                    request.url
                )), 500
            
            # Process denial using domain logic
            with tracer.start_as_current_span("domain.notification.deny") as domain_span:
                result = notification_domain.deny_notification(
                    notification,
                    deny_request.reason,
                    user_context
                )
                
                domain_span.set_attributes({
                    "domain.operation": "deny_notification",
                    "domain.result": "success" if result.success else "failed"
                })
            
            if not result.success:
                span.set_status(Status(StatusCode.ERROR, result.error_message))
                logger.error(
                    "Failed to deny notification",
                    extra={
                        "notification_id": notification_id,
                        "user_id": user_context.user_id,
                        "org_id": user_context.org_id,
                        "error": result.error_message,
                        "validation_errors": result.validation_errors
                    }
                )
                
                if result.validation_errors:
                    return jsonify(current_app.hal_formatter.builder.build_validation_error_response(
                        result.error_message,
                        request.url,
                        result.validation_errors
                    )), 400
                else:
                    return jsonify(current_app.hal_formatter.builder.build_error_response(
                        result.error_message,
                        500,
                        "processing_error",
                        request.url
                    )), 500
            
            # Update notification in database
            with tracer.start_as_current_span("db.notification.update") as db_span:
                update_data = result.notification.model_dump()
                update_data.pop("id", None)  # Remove ID from update data
                
                success = current_app.mongodb_service.update_by_org(
                    "notifications",
                    user_context.org_id,
                    notification_id,
                    update_data
                )
                
                db_span.set_attributes({
                    "db.collection": "notifications",
                    "db.operation": "update",
                    "db.organization_id": user_context.org_id,
                    "db.success": success
                })
                
                if not success:
                    span.set_status(Status(StatusCode.ERROR, "Failed to update notification"))
                    logger.error(
                        "Failed to update notification in database",
                        extra={
                            "notification_id": notification_id,
                            "user_id": user_context.user_id,
                            "org_id": user_context.org_id
                        }
                    )
                    return jsonify(current_app.hal_formatter.builder.build_error_response(
                        "Failed to update notification",
                        500,
                        "database_error",
                        request.url
                    )), 500
            
            # Create audit log entry
            with tracer.start_as_current_span("audit.log_denial") as audit_span:
                # TODO: Implement audit logging (will be done in task 7)
                audit_span.set_attributes({
                    "audit.operation": "log_denial",
                    "audit.status": "placeholder",
                    "notification.id": notification_id,
                    "user.id": user_context.user_id
                })
                
                logger.info(
                    "Audit logging placeholder - notification denied",
                    extra={
                        "notification_id": notification_id,
                        "user_id": user_context.user_id,
                        "org_id": user_context.org_id,
                        "action": "deny",
                        "before_status": notification.status,
                        "after_status": result.notification.status,
                        "denial_reason": deny_request.reason[:100],  # Truncated for logs
                        "note": "Audit service will be implemented in task 7"
                    }
                )
            
            # Build HAL response
            hal_response = notification_domain.build_notification_hal_response(
                result.notification,
                user_context,
                current_app.config['BASE_URL']
            )
            
            # Log successful denial
            logger.info(
                "Notification denied successfully",
                extra={
                    "notification_id": notification_id,
                    "user_id": user_context.user_id,
                    "org_id": user_context.org_id,
                    "denial_reason": deny_request.reason[:100],  # Truncated for logs
                    "severity": result.notification.severity,
                    "title": result.notification.title[:50]
                }
            )
            
            span.set_status(Status(StatusCode.OK))
            return jsonify(hal_response), 200
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error(
                "Unexpected error denying notification",
                extra={
                    "notification_id": notification_id,
                    "user_id": user_context.user_id,
                    "org_id": user_context.org_id,
                    "error": str(e)
                },
                exc_info=True
            )
            
            return jsonify(current_app.hal_formatter.builder.build_error_response(
                "Internal server error",
                500,
                "internal_error",
                request.url
            )), 500