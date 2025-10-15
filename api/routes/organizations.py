# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Organization management endpoints for CRUD operations.
"""

from flask import Blueprint, request, jsonify, current_app, g
from flask_openapi3 import APIBlueprint, Tag
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
import logging
from datetime import datetime
from typing import Dict, Any, List
from functools import wraps
from bson import ObjectId

from models.requests import (
    CreateOrganizationRequest, 
    UpdateOrganizationRequest,
    PaginationParams
)
from models.responses import (
    OrganizationResponse, 
    OrganizationCollection,
    ErrorResponse
)
from models.entities import Organization, UserContext
from services.mongodb import MongoDBService
from services.audit import AuditService
from middleware.auth import require_auth, require_permission
from utils.request import get_request_context

# Set up logging and tracing
logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


def require_jwt(f):
    """Simple JWT requirement decorator."""
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


def require_org_permission(permission: str):
    """Simple permission requirement decorator."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get auth middleware from current app
            auth_middleware = current_app.auth_middleware
            return require_permission(permission, auth_middleware)(f)(*args, **kwargs)
        return decorated_function
    return decorator

# Create API blueprint
org_tag = Tag(name="Organizations", description="Organization management operations")
org_bp = APIBlueprint(
    'organizations', 
    __name__, 
    url_prefix='/api/organizations',
    abp_tags=[org_tag]
)


@org_bp.get('/')
@require_jwt
@require_org_permission('organization:read')
def list_organizations(user_context: UserContext):
    """
    List organizations with pagination and filtering.
    
    This endpoint returns a paginated list of organizations. Super admins can see all
    organizations, while regular users can only see their own organization.
    """
    with tracer.start_as_current_span(
        "organizations.list",
        attributes={
            "operation": "list_organizations",
            "user.id": user_context.user_id,
            "organization.id": user_context.org_id
        }
    ) as span:
        try:
            # Parse pagination parameters
            page = int(request.args.get('page', 1))
            page_size = min(int(request.args.get('page_size', 20)), 100)
            search = request.args.get('search', '').strip()
            
            span.set_attributes({
                "pagination.page": page,
                "pagination.page_size": page_size,
                "search.query": search if search else None
            })
            
            # Build query filters
            filters = {}
            if search:
                filters["$or"] = [
                    {"name": {"$regex": search, "$options": "i"}},
                    {"slug": {"$regex": search, "$options": "i"}},
                    {"description": {"$regex": search, "$options": "i"}}
                ]
            
            # Check if user is super admin (can see all organizations)
            is_super_admin = "organization:read_all" in user_context.permissions
            
            if not is_super_admin:
                # Regular users can only see their own organization
                filters["_id"] = ObjectId(user_context.org_id)
            
            # Query organizations with pagination
            with tracer.start_as_current_span("db.organizations.paginate") as db_span:
                mongo_service = current_app.mongodb_service
                
                # Get total count
                total_count = mongo_service.get_collection("organizations").count_documents({
                    **filters,
                    "deletedAt": None
                })
                
                # Get paginated results
                skip = (page - 1) * page_size
                organizations_docs = list(mongo_service.get_collection("organizations").find({
                    **filters,
                    "deletedAt": None
                }).sort("createdAt", -1).skip(skip).limit(page_size))
                
                db_span.set_attributes({
                    "db.collection": "organizations",
                    "db.operation": "paginate",
                    "db.total_count": total_count,
                    "db.returned_count": len(organizations_docs)
                })
            
            # Convert to response models
            organizations = []
            for org_doc in organizations_docs:
                try:
                    org_data = {
                        "id": str(org_doc["_id"]),
                        "name": org_doc["name"],
                        "slug": org_doc["slug"],
                        "description": org_doc.get("description"),
                        "settings": org_doc.get("settings", {}),
                        "created_at": org_doc["createdAt"],
                        "updated_at": org_doc["updatedAt"],
                        "created_by": org_doc["createdBy"],
                        "updated_by": org_doc["updatedBy"]
                    }
                    
                    # Build HAL links for each organization
                    org_links = {
                        "self": {"href": f"{current_app.config['BASE_URL']}/api/organizations/{org_data['id']}"}
                    }
                    
                    # Add conditional links based on permissions
                    if "organization:update" in user_context.permissions:
                        org_links["edit"] = {
                            "href": f"{current_app.config['BASE_URL']}/api/organizations/{org_data['id']}",
                            "method": "PUT"
                        }
                    
                    if "organization:delete" in user_context.permissions:
                        org_links["delete"] = {
                            "href": f"{current_app.config['BASE_URL']}/api/organizations/{org_data['id']}",
                            "method": "DELETE"
                        }
                    
                    org_response = OrganizationResponse(**org_data)
                    org_response.links = org_links
                    organizations.append(org_response)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse organization {org_doc.get('_id')}: {str(e)}")
                    continue
            
            # Calculate pagination info
            total_pages = (total_count + page_size - 1) // page_size
            
            # Build collection response with HAL links
            collection_links = {
                "self": {"href": f"{current_app.config['BASE_URL']}/api/organizations?page={page}&page_size={page_size}"}
            }
            
            if page > 1:
                collection_links["prev"] = {
                    "href": f"{current_app.config['BASE_URL']}/api/organizations?page={page-1}&page_size={page_size}"
                }
            
            if page < total_pages:
                collection_links["next"] = {
                    "href": f"{current_app.config['BASE_URL']}/api/organizations?page={page+1}&page_size={page_size}"
                }
            
            collection_links["first"] = {
                "href": f"{current_app.config['BASE_URL']}/api/organizations?page=1&page_size={page_size}"
            }
            
            if total_pages > 0:
                collection_links["last"] = {
                    "href": f"{current_app.config['BASE_URL']}/api/organizations?page={total_pages}&page_size={page_size}"
                }
            
            # Add create link if user has permission
            if "organization:create" in user_context.permissions:
                collection_links["create"] = {
                    "href": f"{current_app.config['BASE_URL']}/api/organizations",
                    "method": "POST"
                }
            
            response_data = {
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "_embedded": {
                    "organizations": [org.model_dump() for org in organizations]
                },
                "_links": collection_links
            }
            
            logger.info(
                "Organizations listed successfully",
                extra={
                    "user_id": user_context.user_id,
                    "organization_id": user_context.org_id,
                    "total_count": total_count,
                    "page": page,
                    "is_super_admin": is_super_admin
                }
            )
            
            span.set_status(Status(StatusCode.OK))
            return jsonify(response_data), 200
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error(
                "Failed to list organizations",
                extra={
                    "user_id": user_context.user_id,
                    "organization_id": user_context.org_id,
                    "error": str(e)
                },
                exc_info=True
            )
            
            return jsonify(current_app.hal_formatter.builder.build_error_response(
                "Failed to list organizations",
                500,
                "internal_error",
                request.url
            )), 500


@org_bp.get('/<string:org_id>')
@require_jwt
@require_org_permission('organization:read')
def get_organization(user_context: UserContext, org_id: str):
    """
    Get organization by ID.
    
    This endpoint returns detailed information about a specific organization.
    Users can only access their own organization unless they have super admin permissions.
    """
    with tracer.start_as_current_span(
        "organizations.get",
        attributes={
            "operation": "get_organization",
            "user.id": user_context.user_id,
            "organization.id": user_context.org_id,
            "target_organization.id": org_id
        }
    ) as span:
        try:
            # Check if user can access this organization
            is_super_admin = "organization:read_all" in user_context.permissions
            if not is_super_admin and org_id != user_context.org_id:
                span.set_status(Status(StatusCode.ERROR, "Access denied"))
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Access denied to organization",
                    403,
                    "access_denied",
                    request.url
                )), 403
            
            # Find organization
            with tracer.start_as_current_span("db.organizations.find_one") as db_span:
                mongo_service = current_app.mongodb_service
                org_doc = mongo_service.get_collection("organizations").find_one({
                    "_id": ObjectId(org_id),
                    "deletedAt": None
                })
                
                db_span.set_attributes({
                    "db.collection": "organizations",
                    "db.operation": "find_one",
                    "db.found": org_doc is not None
                })
            
            if not org_doc:
                span.set_status(Status(StatusCode.ERROR, "Organization not found"))
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Organization not found",
                    404,
                    "not_found",
                    request.url
                )), 404
            
            # Convert to response model
            org_data = {
                "id": str(org_doc["_id"]),
                "name": org_doc["name"],
                "slug": org_doc["slug"],
                "description": org_doc.get("description"),
                "settings": org_doc.get("settings", {}),
                "created_at": org_doc["createdAt"],
                "updated_at": org_doc["updatedAt"],
                "created_by": org_doc["createdBy"],
                "updated_by": org_doc["updatedBy"]
            }
            
            # Build HAL links
            org_links = {
                "self": {"href": f"{current_app.config['BASE_URL']}/api/organizations/{org_id}"},
                "collection": {"href": f"{current_app.config['BASE_URL']}/api/organizations"}
            }
            
            # Add conditional links based on permissions
            if "organization:update" in user_context.permissions:
                org_links["edit"] = {
                    "href": f"{current_app.config['BASE_URL']}/api/organizations/{org_id}",
                    "method": "PUT"
                }
            
            if "organization:delete" in user_context.permissions:
                org_links["delete"] = {
                    "href": f"{current_app.config['BASE_URL']}/api/organizations/{org_id}",
                    "method": "DELETE"
                }
            
            # Add related resource links
            org_links["users"] = {"href": f"{current_app.config['BASE_URL']}/api/organizations/{org_id}/users"}
            org_links["roles"] = {"href": f"{current_app.config['BASE_URL']}/api/organizations/{org_id}/roles"}
            org_links["notifications"] = {"href": f"{current_app.config['BASE_URL']}/api/organizations/{org_id}/notifications"}
            
            response_data = {
                **org_data,
                "_links": org_links
            }
            
            logger.info(
                "Organization retrieved successfully",
                extra={
                    "user_id": user_context.user_id,
                    "organization_id": user_context.org_id,
                    "target_organization_id": org_id
                }
            )
            
            span.set_status(Status(StatusCode.OK))
            return jsonify(response_data), 200
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error(
                "Failed to get organization",
                extra={
                    "user_id": user_context.user_id,
                    "organization_id": user_context.org_id,
                    "target_organization_id": org_id,
                    "error": str(e)
                },
                exc_info=True
            )
            
            return jsonify(current_app.hal_formatter.builder.build_error_response(
                "Failed to get organization",
                500,
                "internal_error",
                request.url
            )), 500


@org_bp.post('/')
@require_jwt
@require_org_permission('organization:create')
def create_organization(user_context: UserContext):
    """
    Create a new organization.
    
    This endpoint creates a new organization. Only super admins can create organizations.
    """
    with tracer.start_as_current_span(
        "organizations.create",
        attributes={
            "operation": "create_organization",
            "user.id": user_context.user_id,
            "organization.id": user_context.org_id
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
                create_request = CreateOrganizationRequest(**request_data)
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, "Validation failed"))
                return jsonify(current_app.hal_formatter.builder.build_validation_error_response(
                    str(e),
                    request.url
                )), 400
            
            # Check slug uniqueness
            with tracer.start_as_current_span("db.organizations.check_slug") as db_span:
                mongo_service = current_app.mongodb_service
                existing_org = mongo_service.get_collection("organizations").find_one({
                    "slug": create_request.slug,
                    "deletedAt": None
                })
                
                db_span.set_attributes({
                    "db.collection": "organizations",
                    "db.operation": "check_slug_uniqueness",
                    "db.slug_exists": existing_org is not None
                })
            
            if existing_org:
                span.set_status(Status(StatusCode.ERROR, "Slug already exists"))
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    f"Organization slug '{create_request.slug}' already exists",
                    409,
                    "slug_conflict",
                    request.url
                )), 409
            
            # Create organization document
            now = datetime.utcnow()
            org_doc = {
                "_id": ObjectId(),
                "name": create_request.name,
                "slug": create_request.slug,
                "description": create_request.description,
                "settings": create_request.settings,
                "createdAt": now,
                "updatedAt": now,
                "deletedAt": None,
                "createdBy": user_context.user_id,
                "updatedBy": user_context.user_id,
                "schemaVersion": 1
            }
            
            # Insert organization
            with tracer.start_as_current_span("db.organizations.create") as db_span:
                result = mongo_service.get_collection("organizations").insert_one(org_doc)
                org_id = str(result.inserted_id)
                
                db_span.set_attributes({
                    "db.collection": "organizations",
                    "db.operation": "insert_one",
                    "db.inserted_id": org_id
                })
            
            # Log audit trail
            audit_service = current_app.audit_service
            audit_service.log_action(
                user_id=user_context.user_id,
                org_id=org_id,  # New organization ID
                entity="organization",
                entity_id=org_id,
                action="create",
                before=None,
                after=org_doc,
                request_context=get_request_context()
            )
            
            # Build response
            org_data = {
                "id": org_id,
                "name": org_doc["name"],
                "slug": org_doc["slug"],
                "description": org_doc["description"],
                "settings": org_doc["settings"],
                "created_at": org_doc["createdAt"],
                "updated_at": org_doc["updatedAt"],
                "created_by": org_doc["createdBy"],
                "updated_by": org_doc["updatedBy"]
            }
            
            # Build HAL links
            org_links = {
                "self": {"href": f"{current_app.config['BASE_URL']}/api/organizations/{org_id}"},
                "collection": {"href": f"{current_app.config['BASE_URL']}/api/organizations"},
                "edit": {
                    "href": f"{current_app.config['BASE_URL']}/api/organizations/{org_id}",
                    "method": "PUT"
                },
                "delete": {
                    "href": f"{current_app.config['BASE_URL']}/api/organizations/{org_id}",
                    "method": "DELETE"
                }
            }
            
            response_data = {
                **org_data,
                "_links": org_links
            }
            
            logger.info(
                "Organization created successfully",
                extra={
                    "user_id": user_context.user_id,
                    "organization_id": user_context.org_id,
                    "new_organization_id": org_id,
                    "organization_name": org_doc["name"],
                    "organization_slug": org_doc["slug"]
                }
            )
            
            span.set_status(Status(StatusCode.OK))
            return jsonify(response_data), 201
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error(
                "Failed to create organization",
                extra={
                    "user_id": user_context.user_id,
                    "organization_id": user_context.org_id,
                    "error": str(e)
                },
                exc_info=True
            )
            
            return jsonify(current_app.hal_formatter.builder.build_error_response(
                "Failed to create organization",
                500,
                "internal_error",
                request.url
            )), 500


@org_bp.put('/<string:org_id>')
@require_jwt
@require_org_permission('organization:update')
def update_organization(user_context: UserContext, org_id: str):
    """
    Update organization by ID.
    
    This endpoint updates an existing organization. Users can only update their own
    organization unless they have super admin permissions.
    """
    with tracer.start_as_current_span(
        "organizations.update",
        attributes={
            "operation": "update_organization",
            "user.id": user_context.user_id,
            "organization.id": user_context.org_id,
            "target_organization.id": org_id
        }
    ) as span:
        try:
            # Check if user can update this organization
            is_super_admin = "organization:update_all" in user_context.permissions
            if not is_super_admin and org_id != user_context.org_id:
                span.set_status(Status(StatusCode.ERROR, "Access denied"))
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Access denied to update organization",
                    403,
                    "access_denied",
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
                update_request = UpdateOrganizationRequest(**request_data)
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, "Validation failed"))
                return jsonify(current_app.hal_formatter.builder.build_validation_error_response(
                    str(e),
                    request.url
                )), 400
            
            # Find existing organization
            with tracer.start_as_current_span("db.organizations.find_existing") as db_span:
                mongo_service = current_app.mongodb_service
                existing_org = mongo_service.get_collection("organizations").find_one({
                    "_id": ObjectId(org_id),
                    "deletedAt": None
                })
                
                db_span.set_attributes({
                    "db.collection": "organizations",
                    "db.operation": "find_existing",
                    "db.found": existing_org is not None
                })
            
            if not existing_org:
                span.set_status(Status(StatusCode.ERROR, "Organization not found"))
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Organization not found",
                    404,
                    "not_found",
                    request.url
                )), 404
            
            # Build update document
            update_doc = {
                "updatedAt": datetime.utcnow(),
                "updatedBy": user_context.user_id
            }
            
            # Add fields that are being updated
            if update_request.name is not None:
                update_doc["name"] = update_request.name
            if update_request.description is not None:
                update_doc["description"] = update_request.description
            if update_request.settings is not None:
                update_doc["settings"] = update_request.settings
            
            # Update organization
            with tracer.start_as_current_span("db.organizations.update") as db_span:
                result = mongo_service.get_collection("organizations").update_one(
                    {"_id": ObjectId(org_id), "deletedAt": None},
                    {"$set": update_doc}
                )
                
                db_span.set_attributes({
                    "db.collection": "organizations",
                    "db.operation": "update_one",
                    "db.modified_count": result.modified_count
                })
            
            if result.modified_count == 0:
                span.set_status(Status(StatusCode.ERROR, "No changes made"))
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "No changes were made to the organization",
                    400,
                    "no_changes",
                    request.url
                )), 400
            
            # Get updated organization
            updated_org = mongo_service.get_collection("organizations").find_one({
                "_id": ObjectId(org_id)
            })
            
            # Log audit trail
            audit_service = current_app.audit_service
            audit_service.log_action(
                user_id=user_context.user_id,
                org_id=org_id,
                entity="organization",
                entity_id=org_id,
                action="update",
                before=existing_org,
                after=updated_org,
                request_context=get_request_context()
            )
            
            # Build response
            org_data = {
                "id": str(updated_org["_id"]),
                "name": updated_org["name"],
                "slug": updated_org["slug"],
                "description": updated_org.get("description"),
                "settings": updated_org.get("settings", {}),
                "created_at": updated_org["createdAt"],
                "updated_at": updated_org["updatedAt"],
                "created_by": updated_org["createdBy"],
                "updated_by": updated_org["updatedBy"]
            }
            
            # Build HAL links
            org_links = {
                "self": {"href": f"{current_app.config['BASE_URL']}/api/organizations/{org_id}"},
                "collection": {"href": f"{current_app.config['BASE_URL']}/api/organizations"}
            }
            
            response_data = {
                **org_data,
                "_links": org_links
            }
            
            logger.info(
                "Organization updated successfully",
                extra={
                    "user_id": user_context.user_id,
                    "organization_id": user_context.org_id,
                    "target_organization_id": org_id,
                    "updated_fields": list(update_doc.keys())
                }
            )
            
            span.set_status(Status(StatusCode.OK))
            return jsonify(response_data), 200
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error(
                "Failed to update organization",
                extra={
                    "user_id": user_context.user_id,
                    "organization_id": user_context.org_id,
                    "target_organization_id": org_id,
                    "error": str(e)
                },
                exc_info=True
            )
            
            return jsonify(current_app.hal_formatter.builder.build_error_response(
                "Failed to update organization",
                500,
                "internal_error",
                request.url
            )), 500


@org_bp.delete('/<string:org_id>')
@require_jwt
@require_org_permission('organization:delete')
def delete_organization(user_context: UserContext, org_id: str):
    """
    Soft delete organization by ID.
    
    This endpoint performs a soft delete on an organization. Only super admins can delete organizations.
    """
    with tracer.start_as_current_span(
        "organizations.delete",
        attributes={
            "operation": "delete_organization",
            "user.id": user_context.user_id,
            "organization.id": user_context.org_id,
            "target_organization.id": org_id
        }
    ) as span:
        try:
            # Find existing organization
            with tracer.start_as_current_span("db.organizations.find_existing") as db_span:
                mongo_service = current_app.mongodb_service
                existing_org = mongo_service.get_collection("organizations").find_one({
                    "_id": ObjectId(org_id),
                    "deletedAt": None
                })
                
                db_span.set_attributes({
                    "db.collection": "organizations",
                    "db.operation": "find_existing",
                    "db.found": existing_org is not None
                })
            
            if not existing_org:
                span.set_status(Status(StatusCode.ERROR, "Organization not found"))
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Organization not found",
                    404,
                    "not_found",
                    request.url
                )), 404
            
            # Perform soft delete
            now = datetime.utcnow()
            with tracer.start_as_current_span("db.organizations.soft_delete") as db_span:
                result = mongo_service.get_collection("organizations").update_one(
                    {"_id": ObjectId(org_id), "deletedAt": None},
                    {
                        "$set": {
                            "deletedAt": now,
                            "updatedAt": now,
                            "updatedBy": user_context.user_id
                        }
                    }
                )
                
                db_span.set_attributes({
                    "db.collection": "organizations",
                    "db.operation": "soft_delete",
                    "db.modified_count": result.modified_count
                })
            
            if result.modified_count == 0:
                span.set_status(Status(StatusCode.ERROR, "Organization already deleted"))
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Organization is already deleted",
                    410,
                    "already_deleted",
                    request.url
                )), 410
            
            # Get updated organization for audit
            deleted_org = mongo_service.get_collection("organizations").find_one({
                "_id": ObjectId(org_id)
            })
            
            # Log audit trail
            audit_service = current_app.audit_service
            audit_service.log_action(
                user_id=user_context.user_id,
                org_id=org_id,
                entity="organization",
                entity_id=org_id,
                action="delete",
                before=existing_org,
                after=deleted_org,
                request_context=get_request_context()
            )
            
            # Build response
            response_data = {
                "message": "Organization deleted successfully",
                "_links": {
                    "collection": {"href": f"{current_app.config['BASE_URL']}/api/organizations"}
                }
            }
            
            logger.info(
                "Organization deleted successfully",
                extra={
                    "user_id": user_context.user_id,
                    "organization_id": user_context.org_id,
                    "deleted_organization_id": org_id,
                    "organization_name": existing_org["name"]
                }
            )
            
            span.set_status(Status(StatusCode.OK))
            return jsonify(response_data), 200
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error(
                "Failed to delete organization",
                extra={
                    "user_id": user_context.user_id,
                    "organization_id": user_context.org_id,
                    "target_organization_id": org_id,
                    "error": str(e)
                },
                exc_info=True
            )
            
            return jsonify(current_app.hal_formatter.builder.build_error_response(
                "Failed to delete organization",
                500,
                "internal_error",
                request.url
            )), 500