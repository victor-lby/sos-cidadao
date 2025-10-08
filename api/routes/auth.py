# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Authentication endpoints for login, logout, and token refresh.
"""

from flask import Blueprint, request, jsonify, current_app, g
from flask_openapi3 import APIBlueprint, Tag
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
import logging
from datetime import datetime
from typing import Dict, Any
from bson import ObjectId

from ..models.requests import LoginRequest, RefreshTokenRequest
from ..models.responses import LoginResponse, RefreshTokenResponse, ErrorResponse
from ..models.entities import UserContext
from ..services.mongodb import MongoDBService
from ..services.redis import RedisService
from ..services.auth import AuthService, AuthenticationError, TokenValidationError
from ..middleware.audit import log_authentication_event
from ..utils.request import get_request_context

# Set up logging and tracing
logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Create API blueprint
auth_tag = Tag(name="Authentication", description="User authentication and token management")
auth_bp = APIBlueprint(
    'auth', 
    __name__, 
    url_prefix='/api/auth',
    abp_tags=[auth_tag]
)


@auth_bp.post('/login')
def login():
    """
    Authenticate user and return JWT tokens.
    
    This endpoint validates user credentials and returns access and refresh tokens
    for authenticated sessions.
    """
    with tracer.start_as_current_span(
        "auth.login",
        attributes={
            "operation": "login",
            "ip_address": request.remote_addr
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
                login_request = LoginRequest(**request_data)
                span.set_attribute("auth.email", login_request.email)
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, "Validation failed"))
                logger.warning(
                    "Login request validation failed",
                    extra={
                        "email": request_data.get("email", "unknown"),
                        "ip_address": request.remote_addr,
                        "validation_errors": str(e)
                    }
                )
                
                # Log failed authentication attempt
                log_authentication_event(
                    action="login",
                    user_id=None,
                    success=False,
                    details={
                        "error": "validation_failed",
                        "email": request_data.get("email", "unknown"),
                        "validation_errors": str(e)
                    }
                )
                
                return jsonify(current_app.hal_formatter.builder.build_validation_error_response(
                    str(e),
                    request.url
                )), 400
            
            # Find user by email
            with tracer.start_as_current_span("db.user.find_by_email") as db_span:
                # We need to search across all organizations for the email
                # This is a special case for authentication
                users_collection = current_app.mongodb_service.get_collection("users")
                user_doc = users_collection.find_one({
                    "email": login_request.email,
                    "deletedAt": None
                })
                
                db_span.set_attributes({
                    "db.collection": "users",
                    "db.operation": "find_by_email",
                    "db.found": user_doc is not None,
                    "auth.email": login_request.email
                })
            
            if not user_doc:
                span.set_status(Status(StatusCode.ERROR, "User not found"))
                logger.warning(
                    "Login attempt with non-existent email",
                    extra={
                        "email": login_request.email,
                        "ip_address": request.remote_addr
                    }
                )
                
                # Log failed authentication attempt
                log_authentication_event(
                    action="login",
                    user_id=None,
                    success=False,
                    details={
                        "error": "user_not_found",
                        "email": login_request.email
                    }
                )
                
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Invalid email or password",
                    401,
                    "authentication_failed",
                    request.url
                )), 401
            
            # Convert to user entity
            try:
                from ..models.entities import User
                user_data = {
                    "id": str(user_doc["_id"]),
                    "organization_id": user_doc["organizationId"],
                    "email": user_doc["email"],
                    "name": user_doc["name"],
                    "password_hash": user_doc["passwordHash"],
                    "roles": user_doc.get("roles", []),
                    "status": user_doc["status"],
                    "last_login": user_doc.get("lastLogin"),
                    "failed_login_attempts": user_doc.get("failedLoginAttempts", 0),
                    "locked_until": user_doc.get("lockedUntil"),
                    "created_at": user_doc["createdAt"],
                    "updated_at": user_doc["updatedAt"],
                    "deleted_at": user_doc.get("deletedAt"),
                    "created_by": user_doc["createdBy"],
                    "updated_by": user_doc["updatedBy"],
                    "schema_version": user_doc.get("schemaVersion", 1)
                }
                
                user = User(**user_data)
                
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, "Failed to parse user"))
                logger.error(
                    f"Failed to parse user data for {login_request.email}: {str(e)}",
                    extra={
                        "email": login_request.email,
                        "user_id": str(user_doc.get("_id")),
                        "parse_error": str(e)
                    }
                )
                
                # Log failed authentication attempt
                log_authentication_event(
                    action="login",
                    user_id=str(user_doc.get("_id")),
                    success=False,
                    details={
                        "error": "user_parse_failed",
                        "email": login_request.email
                    }
                )
                
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Authentication failed",
                    500,
                    "internal_error",
                    request.url
                )), 500
            
            # Check if user account is active
            if not user.is_active():
                span.set_status(Status(StatusCode.ERROR, "User account inactive"))
                logger.warning(
                    "Login attempt with inactive account",
                    extra={
                        "email": login_request.email,
                        "user_id": user.id,
                        "status": user.status,
                        "is_locked": user.is_locked()
                    }
                )
                
                # Log failed authentication attempt
                log_authentication_event(
                    action="login",
                    user_id=user.id,
                    success=False,
                    details={
                        "error": "account_inactive",
                        "email": login_request.email,
                        "status": user.status,
                        "is_locked": user.is_locked()
                    }
                )
                
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Account is inactive or locked",
                    401,
                    "account_inactive",
                    request.url
                )), 401
            
            # Verify password
            with tracer.start_as_current_span("auth.verify_password") as auth_span:
                auth_service = current_app.auth_service
                password_valid = auth_service.verify_password(
                    login_request.password,
                    user.password_hash
                )
                
                auth_span.set_attributes({
                    "auth.operation": "verify_password",
                    "auth.result": "success" if password_valid else "failed",
                    "user.id": user.id
                })
            
            if not password_valid:
                span.set_status(Status(StatusCode.ERROR, "Invalid password"))
                logger.warning(
                    "Login attempt with invalid password",
                    extra={
                        "email": login_request.email,
                        "user_id": user.id,
                        "ip_address": request.remote_addr
                    }
                )
                
                # TODO: Implement failed login attempt tracking and account locking
                
                # Log failed authentication attempt
                log_authentication_event(
                    action="login",
                    user_id=user.id,
                    success=False,
                    details={
                        "error": "invalid_password",
                        "email": login_request.email
                    }
                )
                
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Invalid email or password",
                    401,
                    "authentication_failed",
                    request.url
                )), 401
            
            # Get user permissions (aggregate from roles)
            with tracer.start_as_current_span("auth.get_permissions") as perm_span:
                permissions = []
                if user.roles:
                    # Get roles from database
                    roles_collection = current_app.mongodb_service.get_collection("roles")
                    roles_docs = list(roles_collection.find({
                        "_id": {"$in": [ObjectId(role_id) for role_id in user.roles]},
                        "organizationId": user.organization_id,
                        "deletedAt": None
                    }))
                    
                    # Aggregate permissions from all roles
                    for role_doc in roles_docs:
                        permissions.extend(role_doc.get("permissions", []))
                    
                    # Remove duplicates
                    permissions = list(set(permissions))
                
                perm_span.set_attributes({
                    "auth.roles_count": len(user.roles),
                    "auth.permissions_count": len(permissions),
                    "user.id": user.id
                })
            
            # Update user entity with permissions
            user.permissions = permissions
            
            # Generate JWT tokens
            with tracer.start_as_current_span("auth.generate_tokens") as token_span:
                try:
                    tokens = auth_service.generate_tokens(user)
                    token_span.set_attribute("auth.tokens_generated", "success")
                except AuthenticationError as e:
                    token_span.set_attribute("auth.tokens_generated", "failed")
                    logger.error(
                        "Token generation failed",
                        extra={
                            "user_id": user.id,
                            "email": user.email,
                            "error": str(e)
                        }
                    )
                    
                    # Log failed authentication attempt
                    log_authentication_event(
                        action="login",
                        user_id=user.id,
                        success=False,
                        details={
                            "error": "token_generation_failed",
                            "email": login_request.email
                        }
                    )
                    
                    return jsonify(current_app.hal_formatter.builder.build_error_response(
                        "Authentication failed",
                        500,
                        "token_generation_failed",
                        request.url
                    )), 500
            
            # Update last login timestamp
            with tracer.start_as_current_span("db.user.update_last_login") as update_span:
                current_app.mongodb_service.update_by_org(
                    "users",
                    user.organization_id,
                    user.id,
                    {
                        "lastLogin": datetime.utcnow(),
                        "failedLoginAttempts": 0  # Reset failed attempts on successful login
                    }
                )
                
                update_span.set_attributes({
                    "db.collection": "users",
                    "db.operation": "update_last_login",
                    "user.id": user.id
                })
            
            # Log successful authentication
            log_authentication_event(
                action="login",
                user_id=user.id,
                success=True,
                details={
                    "email": user.email,
                    "organization_id": user.organization_id,
                    "permissions_count": len(permissions)
                }
            )
            
            # Build response
            response_data = {
                **tokens,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "organization_id": user.organization_id,
                    "permissions": permissions
                },
                "_links": {
                    "self": {"href": f"{current_app.config['BASE_URL']}/api/auth/login"},
                    "refresh": {"href": f"{current_app.config['BASE_URL']}/api/auth/refresh"},
                    "logout": {"href": f"{current_app.config['BASE_URL']}/api/auth/logout"}
                }
            }
            
            logger.info(
                "User logged in successfully",
                extra={
                    "user_id": user.id,
                    "email": user.email,
                    "organization_id": user.organization_id,
                    "ip_address": request.remote_addr,
                    "permissions_count": len(permissions)
                }
            )
            
            span.set_status(Status(StatusCode.OK))
            return jsonify(response_data), 200
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error(
                "Unexpected error during login",
                extra={
                    "email": request_data.get("email", "unknown") if 'request_data' in locals() else "unknown",
                    "ip_address": request.remote_addr,
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


@auth_bp.post('/refresh')
def refresh_token():
    """
    Refresh access token using refresh token.
    
    This endpoint generates a new access token using a valid refresh token.
    """
    with tracer.start_as_current_span(
        "auth.refresh",
        attributes={
            "operation": "refresh_token",
            "ip_address": request.remote_addr
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
                refresh_request = RefreshTokenRequest(**request_data)
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, "Validation failed"))
                logger.warning(
                    "Token refresh request validation failed",
                    extra={
                        "ip_address": request.remote_addr,
                        "validation_errors": str(e)
                    }
                )
                
                return jsonify(current_app.hal_formatter.builder.build_validation_error_response(
                    str(e),
                    request.url
                )), 400
            
            # Check if refresh token is blocked
            with tracer.start_as_current_span("redis.check_token_blocked") as redis_span:
                auth_service = current_app.auth_service
                redis_service = current_app.redis_service
                
                try:
                    token_id = auth_service.extract_token_id(refresh_request.refresh_token)
                    is_blocked = redis_service.is_token_blocked(token_id)
                    
                    redis_span.set_attributes({
                        "redis.operation": "check_token_blocked",
                        "redis.token_blocked": is_blocked
                    })
                    
                    if is_blocked:
                        span.set_status(Status(StatusCode.ERROR, "Token is blocked"))
                        logger.warning(
                            "Attempt to use blocked refresh token",
                            extra={
                                "token_id": token_id,
                                "ip_address": request.remote_addr
                            }
                        )
                        
                        return jsonify(current_app.hal_formatter.builder.build_error_response(
                            "Token is invalid or has been revoked",
                            401,
                            "token_revoked",
                            request.url
                        )), 401
                        
                except Exception as e:
                    logger.warning(f"Failed to check token blocklist: {str(e)}")
                    # Continue without blocklist check if Redis is unavailable
            
            # Refresh access token
            with tracer.start_as_current_span("auth.refresh_access_token") as refresh_span:
                try:
                    new_tokens = auth_service.refresh_access_token(refresh_request.refresh_token)
                    refresh_span.set_attribute("auth.refresh_result", "success")
                    
                    # Extract user info from refresh token for logging
                    refresh_payload = auth_service.validate_token(refresh_request.refresh_token, "refresh")
                    user_id = refresh_payload.get("sub")
                    org_id = refresh_payload.get("org_id")
                    
                    span.set_attributes({
                        "user.id": user_id,
                        "organization.id": org_id
                    })
                    
                except (TokenValidationError, AuthenticationError) as e:
                    refresh_span.set_attribute("auth.refresh_result", "failed")
                    logger.warning(
                        "Token refresh failed",
                        extra={
                            "ip_address": request.remote_addr,
                            "error": str(e)
                        }
                    )
                    
                    return jsonify(current_app.hal_formatter.builder.build_error_response(
                        "Invalid or expired refresh token",
                        401,
                        "token_invalid",
                        request.url
                    )), 401
            
            # Log successful token refresh
            log_authentication_event(
                action="token_refresh",
                user_id=user_id,
                success=True,
                details={
                    "organization_id": org_id
                }
            )
            
            # Build response
            response_data = {
                **new_tokens,
                "_links": {
                    "self": {"href": f"{current_app.config['BASE_URL']}/api/auth/refresh"},
                    "login": {"href": f"{current_app.config['BASE_URL']}/api/auth/login"},
                    "logout": {"href": f"{current_app.config['BASE_URL']}/api/auth/logout"}
                }
            }
            
            logger.info(
                "Access token refreshed successfully",
                extra={
                    "user_id": user_id,
                    "organization_id": org_id,
                    "ip_address": request.remote_addr
                }
            )
            
            span.set_status(Status(StatusCode.OK))
            return jsonify(response_data), 200
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error(
                "Unexpected error during token refresh",
                extra={
                    "ip_address": request.remote_addr,
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


@auth_bp.post('/logout')
def logout():
    """
    Logout user and revoke tokens.
    
    This endpoint revokes the user's tokens by adding them to the blocklist.
    """
    with tracer.start_as_current_span(
        "auth.logout",
        attributes={
            "operation": "logout",
            "ip_address": request.remote_addr
        }
    ) as span:
        try:
            # Get authorization header
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                span.set_status(Status(StatusCode.ERROR, "Missing or invalid authorization header"))
                return jsonify(current_app.hal_formatter.builder.build_error_response(
                    "Missing or invalid authorization header",
                    401,
                    "missing_token",
                    request.url
                )), 401
            
            access_token = auth_header.replace('Bearer ', '')
            
            # Validate access token to get user info
            with tracer.start_as_current_span("auth.validate_access_token") as validate_span:
                try:
                    auth_service = current_app.auth_service
                    token_payload = auth_service.validate_token(access_token, "access")
                    
                    user_id = token_payload.get("sub")
                    org_id = token_payload.get("org_id")
                    
                    validate_span.set_attributes({
                        "auth.validation_result": "success",
                        "user.id": user_id,
                        "organization.id": org_id
                    })
                    
                    span.set_attributes({
                        "user.id": user_id,
                        "organization.id": org_id
                    })
                    
                except TokenValidationError as e:
                    validate_span.set_attribute("auth.validation_result", "failed")
                    logger.warning(
                        "Logout attempt with invalid token",
                        extra={
                            "ip_address": request.remote_addr,
                            "error": str(e)
                        }
                    )
                    
                    return jsonify(current_app.hal_formatter.builder.build_error_response(
                        "Invalid or expired token",
                        401,
                        "token_invalid",
                        request.url
                    )), 401
            
            # Block the access token
            with tracer.start_as_current_span("redis.block_token") as redis_span:
                try:
                    redis_service = current_app.redis_service
                    token_id = auth_service.extract_token_id(access_token)
                    
                    # Block token with TTL matching token expiration
                    token_exp = token_payload.get("exp")
                    if token_exp:
                        import time
                        ttl_seconds = max(0, token_exp - int(time.time()))
                        redis_service.block_token(token_id, ttl_seconds)
                    
                    redis_span.set_attributes({
                        "redis.operation": "block_token",
                        "redis.token_id": token_id
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to block token in Redis: {str(e)}")
                    # Continue with logout even if Redis is unavailable
            
            # Log successful logout
            log_authentication_event(
                action="logout",
                user_id=user_id,
                success=True,
                details={
                    "organization_id": org_id
                }
            )
            
            # Build response
            response_data = {
                "message": "Logged out successfully",
                "_links": {
                    "login": {"href": f"{current_app.config['BASE_URL']}/api/auth/login"}
                }
            }
            
            logger.info(
                "User logged out successfully",
                extra={
                    "user_id": user_id,
                    "organization_id": org_id,
                    "ip_address": request.remote_addr
                }
            )
            
            span.set_status(Status(StatusCode.OK))
            return jsonify(response_data), 200
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error(
                "Unexpected error during logout",
                extra={
                    "ip_address": request.remote_addr,
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