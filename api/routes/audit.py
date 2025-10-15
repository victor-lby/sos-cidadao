# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Audit log endpoints for querying and exporting audit trails.
"""

from flask import Blueprint, request, jsonify, current_app, g, Response
from flask_openapi3 import APIBlueprint, Tag
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
import logging
import csv
import json
import io
from datetime import datetime
from typing import Dict, Any, List

from models.requests import AuditLogFilters, PaginationParams
from models.responses import AuditLogResponse, AuditLogCollectionResponse, AuditStatisticsResponse
from models.entities import UserContext
from services.audit import AuditService, AuditFilters, get_audit_service
from middleware.auth import require_auth
from utils.request import get_request_context

# Set up logging and tracing
logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Create API blueprint
audit_tag = Tag(name="Audit Logs", description="Audit trail querying and export")
audit_bp = APIBlueprint(
    'audit', 
    __name__, 
    url_prefix='/api/audit-logs',
    abp_tags=[audit_tag]
)


def require_jwt(f):
    """Simple JWT requirement decorator."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import g
        from middleware.auth import require_auth
        
        # Get auth middleware from current app
        auth_middleware = current_app.auth_middleware
        
        # Extract token from request
        token = auth_middleware.extract_token_from_request()
        if not token:
            return jsonify({
                "type": "https://api.sos-cidadao.org/problems/authentication-required",
                "title": "Authentication Required",
                "status": 401,
                "detail": "Missing authorization token",
                "instance": request.path
            }), 401
        
        # Check if token is blocked
        if auth_middleware.is_token_blocked(token):
            return jsonify({
                "type": "https://api.sos-cidadao.org/problems/token-revoked",
                "title": "Token Revoked",
                "status": 401,
                "detail": "Token has been revoked",
                "instance": request.path
            }), 401
        
        # Validate token
        try:
            from services.auth import TokenValidationError
            
            token_payload = auth_middleware.auth_service.validate_token(token, "access")
            
            # Build user context
            request_info = auth_middleware.get_request_info()
            user_context = auth_middleware.build_user_context(token_payload, request_info)
            
            # Store user context in Flask's g object
            g.user_context = user_context
            
            # Call the protected route with user context
            return f(user_context, *args, **kwargs)
            
        except TokenValidationError as e:
            return jsonify({
                "type": "https://api.sos-cidadao.org/problems/invalid-token",
                "title": "Invalid Token",
                "status": 401,
                "detail": str(e),
                "instance": request.path
            }), 401
        
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return jsonify({
                "type": "https://api.sos-cidadao.org/problems/authentication-error",
                "title": "Authentication Error",
                "status": 500,
                "detail": "Internal authentication error",
                "instance": request.path
            }), 500
    
    return decorated_function


@audit_bp.get('')
@require_jwt
def list_audit_logs():
    """
    List audit logs with filtering and pagination.
    
    Returns a HAL collection of audit log entries with pagination links
    and filtering capabilities.
    """
    from flask import g
    user_context = g.user_context
    
    with tracer.start_as_current_span(
        "audit.list",
        attributes={
            "user.id": user_context.user_id,
            "organization.id": user_context.org_id,
            "operation": "list_audit_logs"
        }
    ) as span:
        try:
            # Check permission
            if not user_context.has_permission("audit:read"):
                span.set_status(Status(StatusCode.ERROR, "Insufficient permissions"))
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Insufficient permissions to view audit logs",
                    403,
                    "insufficient_permissions",
                    request.url
                )), 403
            
            # Parse query parameters
            page = int(request.args.get('page', 1))
            page_size = min(int(request.args.get('size', 20)), 100)  # Max 100 items per page
            sort_by = request.args.get('sort_by', 'timestamp')
            sort_order = -1 if request.args.get('sort_order', 'desc') == 'desc' else 1
            
            # Parse filters
            filters = AuditFilters(
                user_id=request.args.get('user_id'),
                entity=request.args.get('entity'),
                action=request.args.get('action'),
                trace_id=request.args.get('trace_id'),
                entity_id=request.args.get('entity_id')
            )
            
            # Parse date filters
            if request.args.get('date_from'):
                try:
                    filters.start_date = datetime.fromisoformat(request.args.get('date_from'))
                except ValueError:
                    return jsonify(current_app.hal_formatter.builder.build_error_response(
                        "Invalid date_from format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
                        400,
                        "validation_error",
                        request.url
                    )), 400
            
            if request.args.get('date_to'):
                try:
                    filters.end_date = datetime.fromisoformat(request.args.get('date_to'))
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
                "filters.user_id": filters.user_id,
                "filters.entity": filters.entity,
                "filters.action": filters.action
            })
            
            # Query audit logs
            with tracer.start_as_current_span("audit.query") as query_span:
                audit_service = get_audit_service()
                result = audit_service.query_audit_logs(
                    org_id=user_context.org_id,
                    filters=filters,
                    page=page,
                    page_size=page_size,
                    sort_by=sort_by,
                    sort_order=sort_order
                )
                
                query_span.set_attributes({
                    "audit.query.total_results": result.total,
                    "audit.query.returned_items": len(result.items),
                    "audit.query.page": result.page,
                    "audit.query.total_pages": result.total_pages
                })
            
            # Convert to response models
            audit_responses = []
            for item in result.items:
                audit_response = AuditLogResponse(
                    id=item["id"],
                    timestamp=item["timestamp"].isoformat() if isinstance(item["timestamp"], datetime) else item["timestamp"],
                    user_id=item["userId"],
                    organization_id=item["organizationId"],
                    entity=item["entity"],
                    entity_id=item["entityId"],
                    action=item["action"],
                    before=item.get("before"),
                    after=item.get("after"),
                    ip_address=item.get("ipAddress"),
                    user_agent=item.get("userAgent"),
                    session_id=item.get("sessionId"),
                    trace_id=item.get("traceId"),
                    span_id=item.get("spanId"),
                    _links={
                        "self": {"href": f"{current_app.config['BASE_URL']}/api/audit-logs/{item['id']}"}
                    }
                )
                audit_responses.append(audit_response)
            
            # Build HAL collection response
            base_url = current_app.config['BASE_URL']
            query_params = f"page={page}&size={page_size}"
            if filters.user_id:
                query_params += f"&user_id={filters.user_id}"
            if filters.entity:
                query_params += f"&entity={filters.entity}"
            if filters.action:
                query_params += f"&action={filters.action}"
            
            links = {
                "self": {"href": f"{base_url}/api/audit-logs?{query_params}"}
            }
            
            # Add pagination links
            if result.has_prev:
                prev_params = query_params.replace(f"page={page}", f"page={page-1}")
                links["prev"] = {"href": f"{base_url}/api/audit-logs?{prev_params}"}
                links["first"] = {"href": f"{base_url}/api/audit-logs?{query_params.replace(f'page={page}', 'page=1')}"}
            
            if result.has_next:
                next_params = query_params.replace(f"page={page}", f"page={page+1}")
                links["next"] = {"href": f"{base_url}/api/audit-logs?{next_params}"}
                links["last"] = {"href": f"{base_url}/api/audit-logs?{query_params.replace(f'page={page}', f'page={result.total_pages}')}"}
            
            # Add export links
            export_params = query_params.replace(f"page={page}&size={page_size}", "")
            if export_params.startswith("&"):
                export_params = export_params[1:]
            
            links["export_json"] = {
                "href": f"{base_url}/api/audit-logs/export?format=json&{export_params}",
                "type": "application/json"
            }
            links["export_csv"] = {
                "href": f"{base_url}/api/audit-logs/export?format=csv&{export_params}",
                "type": "text/csv"
            }
            
            response_data = {
                "total": result.total,
                "page": result.page,
                "page_size": result.page_size,
                "total_pages": result.total_pages,
                "_embedded": {
                    "audit_logs": [audit.model_dump(by_alias=True) for audit in audit_responses]
                },
                "_links": links
            }
            
            # Log successful listing
            logger.info(
                "Audit logs listed successfully",
                extra={
                    "user_id": user_context.user_id,
                    "org_id": user_context.org_id,
                    "page": page,
                    "page_size": page_size,
                    "total_count": result.total,
                    "returned_count": len(audit_responses)
                }
            )
            
            span.set_status(Status(StatusCode.OK))
            return jsonify(response_data), 200
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error(
                "Unexpected error listing audit logs",
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


@audit_bp.get('/<audit_id>')
@require_jwt
def get_audit_log_detail(audit_id: str):
    """
    Get audit log detail with trace correlation links.
    
    Returns detailed audit log information with links to related traces
    and observability data.
    """
    from flask import g
    user_context = g.user_context
    
    with tracer.start_as_current_span(
        "audit.detail",
        attributes={
            "user.id": user_context.user_id,
            "organization.id": user_context.org_id,
            "audit.id": audit_id,
            "operation": "get_audit_detail"
        }
    ) as span:
        try:
            # Check permission
            if not user_context.has_permission("audit:read"):
                span.set_status(Status(StatusCode.ERROR, "Insufficient permissions"))
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Insufficient permissions to view audit logs",
                    403,
                    "insufficient_permissions",
                    request.url
                )), 403
            
            # Get audit log from service
            with tracer.start_as_current_span("audit.get") as get_span:
                audit_service = get_audit_service()
                audit_log = audit_service.get_audit_log(user_context.org_id, audit_id)
                
                get_span.set_attributes({
                    "audit.organization_id": user_context.org_id,
                    "audit.log_id": audit_id,
                    "audit.found": audit_log is not None
                })
            
            if not audit_log:
                span.set_status(Status(StatusCode.ERROR, "Audit log not found"))
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Audit log not found",
                    404,
                    "not_found",
                    request.url
                )), 404
            
            # Build response with trace correlation links
            base_url = current_app.config['BASE_URL']
            links = {
                "self": {"href": f"{base_url}/api/audit-logs/{audit_id}"},
                "collection": {"href": f"{base_url}/api/audit-logs"}
            }
            
            # Add trace correlation links if trace ID is available
            if audit_log.get("traceId"):
                # These would link to your observability platform
                # For now, we'll add placeholder links
                links["trace"] = {
                    "href": f"{base_url}/api/traces/{audit_log['traceId']}",
                    "title": "View distributed trace"
                }
            
            # Add entity link if applicable
            entity_type = audit_log.get("entity")
            entity_id = audit_log.get("entityId")
            if entity_type and entity_id:
                entity_endpoints = {
                    "notification": f"{base_url}/api/notifications/{entity_id}",
                    "user": f"{base_url}/api/users/{entity_id}",
                    "organization": f"{base_url}/api/organizations/{entity_id}"
                }
                
                if entity_type in entity_endpoints:
                    links["entity"] = {
                        "href": entity_endpoints[entity_type],
                        "title": f"View {entity_type}"
                    }
            
            response_data = {
                "id": audit_log["id"],
                "timestamp": audit_log["timestamp"].isoformat() if isinstance(audit_log["timestamp"], datetime) else audit_log["timestamp"],
                "user_id": audit_log["userId"],
                "organization_id": audit_log["organizationId"],
                "entity": audit_log["entity"],
                "entity_id": audit_log["entityId"],
                "action": audit_log["action"],
                "before": audit_log.get("before"),
                "after": audit_log.get("after"),
                "ip_address": audit_log.get("ipAddress"),
                "user_agent": audit_log.get("userAgent"),
                "session_id": audit_log.get("sessionId"),
                "trace_id": audit_log.get("traceId"),
                "span_id": audit_log.get("spanId"),
                "_links": links
            }
            
            # Log successful retrieval
            logger.info(
                "Audit log detail retrieved successfully",
                extra={
                    "audit_id": audit_id,
                    "user_id": user_context.user_id,
                    "org_id": user_context.org_id,
                    "entity": audit_log.get("entity"),
                    "action": audit_log.get("action")
                }
            )
            
            span.set_status(Status(StatusCode.OK))
            return jsonify(response_data), 200
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error(
                "Unexpected error retrieving audit log detail",
                extra={
                    "audit_id": audit_id,
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


@audit_bp.get('/export')
@require_jwt
def export_audit_logs():
    """
    Export audit logs in CSV or JSON format with streaming.
    
    Supports filtering and format selection for bulk audit log export.
    """
    from flask import g
    user_context = g.user_context
    
    with tracer.start_as_current_span(
        "audit.export",
        attributes={
            "user.id": user_context.user_id,
            "organization.id": user_context.org_id,
            "operation": "export_audit_logs"
        }
    ) as span:
        try:
            # Check permission
            if not user_context.has_permission("audit:export"):
                span.set_status(Status(StatusCode.ERROR, "Insufficient permissions"))
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Insufficient permissions to export audit logs",
                    403,
                    "insufficient_permissions",
                    request.url
                )), 403
            
            # Parse parameters
            format_type = request.args.get('format', 'json').lower()
            if format_type not in ['json', 'csv']:
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Invalid format. Supported formats: json, csv",
                    400,
                    "validation_error",
                    request.url
                )), 400
            
            limit = request.args.get('limit')
            if limit:
                try:
                    limit = int(limit)
                    if limit <= 0 or limit > 10000:  # Max 10k records
                        raise ValueError("Limit must be between 1 and 10000")
                except ValueError as e:
                    return jsonify(current_app.hal_formatter.builder.build_error_response(
                        f"Invalid limit parameter: {str(e)}",
                        400,
                        "validation_error",
                        request.url
                    )), 400
            
            # Parse filters (same as list endpoint)
            filters = AuditFilters(
                user_id=request.args.get('user_id'),
                entity=request.args.get('entity'),
                action=request.args.get('action'),
                trace_id=request.args.get('trace_id'),
                entity_id=request.args.get('entity_id')
            )
            
            # Parse date filters
            if request.args.get('date_from'):
                try:
                    filters.start_date = datetime.fromisoformat(request.args.get('date_from'))
                except ValueError:
                    return jsonify(current_app.hal_formatter.builder.build_error_response(
                        "Invalid date_from format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
                        400,
                        "validation_error",
                        request.url
                    )), 400
            
            if request.args.get('date_to'):
                try:
                    filters.end_date = datetime.fromisoformat(request.args.get('date_to'))
                except ValueError:
                    return jsonify(current_app.hal_formatter.builder.build_error_response(
                        "Invalid date_to format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
                        400,
                        "validation_error",
                        request.url
                    )), 400
            
            span.set_attributes({
                "audit.export.format": format_type,
                "audit.export.limit": limit or 0,
                "filters.user_id": filters.user_id,
                "filters.entity": filters.entity,
                "filters.action": filters.action
            })
            
            # Export audit logs
            with tracer.start_as_current_span("audit.export_data") as export_span:
                audit_service = get_audit_service()
                audit_logs = audit_service.export_audit_logs(
                    org_id=user_context.org_id,
                    filters=filters,
                    format_type=format_type,
                    limit=limit
                )
                
                export_span.set_attributes({
                    "audit.export.records_count": len(audit_logs),
                    "audit.export.format": format_type
                })
            
            # Generate filename with timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"audit_logs_{user_context.org_id}_{timestamp}.{format_type}"
            
            if format_type == 'csv':
                # Generate CSV response
                output = io.StringIO()
                if audit_logs:
                    # Get all possible field names
                    fieldnames = set()
                    for log in audit_logs:
                        fieldnames.update(log.keys())
                    
                    # Remove complex fields for CSV
                    fieldnames.discard('before')
                    fieldnames.discard('after')
                    fieldnames = sorted(list(fieldnames))
                    
                    writer = csv.DictWriter(output, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for log in audit_logs:
                        # Flatten the log entry for CSV
                        csv_row = {}
                        for field in fieldnames:
                            value = log.get(field)
                            if isinstance(value, datetime):
                                csv_row[field] = value.isoformat()
                            elif value is not None:
                                csv_row[field] = str(value)
                            else:
                                csv_row[field] = ""
                        writer.writerow(csv_row)
                
                response_data = output.getvalue()
                output.close()
                
                response = Response(
                    response_data,
                    mimetype='text/csv',
                    headers={
                        'Content-Disposition': f'attachment; filename="{filename}"'
                    }
                )
                
            else:  # JSON format
                # Convert datetime objects to ISO strings
                json_logs = []
                for log in audit_logs:
                    json_log = {}
                    for key, value in log.items():
                        if isinstance(value, datetime):
                            json_log[key] = value.isoformat()
                        else:
                            json_log[key] = value
                    json_logs.append(json_log)
                
                response_data = json.dumps({
                    "exported_at": datetime.utcnow().isoformat(),
                    "organization_id": user_context.org_id,
                    "total_records": len(json_logs),
                    "filters": {
                        "user_id": filters.user_id,
                        "entity": filters.entity,
                        "action": filters.action,
                        "start_date": filters.start_date.isoformat() if filters.start_date else None,
                        "end_date": filters.end_date.isoformat() if filters.end_date else None
                    },
                    "audit_logs": json_logs
                }, indent=2)
                
                response = Response(
                    response_data,
                    mimetype='application/json',
                    headers={
                        'Content-Disposition': f'attachment; filename="{filename}"'
                    }
                )
            
            # Log successful export
            logger.info(
                "Audit logs exported successfully",
                extra={
                    "user_id": user_context.user_id,
                    "org_id": user_context.org_id,
                    "format": format_type,
                    "records_count": len(audit_logs),
                    "filename": filename
                }
            )
            
            span.set_status(Status(StatusCode.OK))
            return response
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error(
                "Unexpected error exporting audit logs",
                extra={
                    "user_id": user_context.user_id,
                    "org_id": user_context.org_id,
                    "format": request.args.get('format', 'json'),
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


@audit_bp.get('/statistics')
@require_jwt
def get_audit_statistics():
    """
    Get audit statistics for the organization.
    
    Returns aggregated statistics about audit log entries for analysis
    and reporting purposes.
    """
    from flask import g
    user_context = g.user_context
    
    with tracer.start_as_current_span(
        "audit.statistics",
        attributes={
            "user.id": user_context.user_id,
            "organization.id": user_context.org_id,
            "operation": "get_audit_statistics"
        }
    ) as span:
        try:
            # Check permission
            if not user_context.has_permission("audit:read"):
                span.set_status(Status(StatusCode.ERROR, "Insufficient permissions"))
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Insufficient permissions to view audit statistics",
                    403,
                    "insufficient_permissions",
                    request.url
                )), 403
            
            # Parse parameters
            days = int(request.args.get('days', 30))
            if days <= 0 or days > 365:
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Days parameter must be between 1 and 365",
                    400,
                    "validation_error",
                    request.url
                )), 400
            
            span.set_attribute("audit.statistics.days", days)
            
            # Get statistics
            with tracer.start_as_current_span("audit.get_statistics") as stats_span:
                audit_service = get_audit_service()
                statistics = audit_service.get_audit_statistics(user_context.org_id, days)
                
                stats_span.set_attributes({
                    "audit.statistics.total_actions": statistics["total_actions"],
                    "audit.statistics.entities_count": len(statistics["entities"])
                })
            
            # Build HAL response
            base_url = current_app.config['BASE_URL']
            response_data = {
                **statistics,
                "_links": {
                    "self": {"href": f"{base_url}/api/audit-logs/statistics?days={days}"},
                    "audit_logs": {"href": f"{base_url}/api/audit-logs"},
                    "export": {"href": f"{base_url}/api/audit-logs/export"}
                }
            }
            
            # Log successful statistics retrieval
            logger.info(
                "Audit statistics retrieved successfully",
                extra={
                    "user_id": user_context.user_id,
                    "org_id": user_context.org_id,
                    "days": days,
                    "total_actions": statistics["total_actions"],
                    "entities_count": len(statistics["entities"])
                }
            )
            
            span.set_status(Status(StatusCode.OK))
            return jsonify(response_data), 200
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error(
                "Unexpected error retrieving audit statistics",
                extra={
                    "user_id": user_context.user_id,
                    "org_id": user_context.org_id,
                    "days": request.args.get('days', 30),
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