# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Audit logging middleware for automatic tracking of state-changing operations.
"""

import logging
from functools import wraps
from typing import Dict, Any, Optional, Callable
from flask import request, g
from opentelemetry import trace

from ..services.audit import AuditService, get_audit_service
from ..models.entities import UserContext

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class AuditMiddleware:
    """Middleware for automatic audit logging of state-changing operations."""
    
    def __init__(self, audit_service: Optional[AuditService] = None):
        """Initialize audit middleware with audit service dependency."""
        self.audit_service = audit_service or get_audit_service()
        logger.info("Audit middleware initialized")
    
    def log_action(
        self,
        entity: str,
        action: str,
        entity_id: Optional[str] = None,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Log an audit action using the current user context.
        
        Args:
            entity: Type of entity being acted upon
            action: Action being performed
            entity_id: ID of the specific entity (optional)
            before: State before the action (optional)
            after: State after the action (optional)
        
        Returns:
            Audit log ID if successful, None otherwise
        """
        try:
            # Get user context from Flask g
            user_context = getattr(g, 'user_context', None)
            if not user_context:
                logger.warning("No user context available for audit logging")
                return None
            
            # Use entity_id or generate from context
            audit_entity_id = entity_id or f"{entity}_{user_context.user_id}"
            
            return self.audit_service.log_action(
                user_id=user_context.user_id,
                org_id=user_context.org_id,
                entity=entity,
                entity_id=audit_entity_id,
                action=action,
                before=before,
                after=after,
                user_context=user_context
            )
            
        except Exception as e:
            logger.error(
                "Failed to log audit action",
                extra={
                    "entity": entity,
                    "action": action,
                    "entity_id": entity_id,
                    "error": str(e)
                },
                exc_info=True
            )
            return None


def audit_action(
    entity: str,
    action: str,
    entity_id_param: Optional[str] = None,
    capture_before: bool = False,
    capture_after: bool = True
):
    """
    Decorator for automatic audit logging of route handlers.
    
    Args:
        entity: Type of entity being acted upon
        action: Action being performed
        entity_id_param: Name of the parameter containing entity ID
        capture_before: Whether to capture state before the action
        capture_after: Whether to capture state after the action
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            with tracer.start_as_current_span("audit.decorator") as span:
                span.set_attributes({
                    "audit.entity": entity,
                    "audit.action": action,
                    "audit.capture_before": capture_before,
                    "audit.capture_after": capture_after
                })
                
                # Get entity ID from parameters
                entity_id = None
                if entity_id_param and entity_id_param in kwargs:
                    entity_id = kwargs[entity_id_param]
                
                # Capture before state if requested
                before_state = None
                if capture_before and entity_id:
                    before_state = _capture_entity_state(entity, entity_id)
                
                # Execute the original function
                result = f(*args, **kwargs)
                
                # Capture after state if requested
                after_state = None
                if capture_after and entity_id:
                    after_state = _capture_entity_state(entity, entity_id)
                
                # Log audit action
                try:
                    audit_middleware = getattr(g, 'audit_middleware', None)
                    if audit_middleware:
                        audit_id = audit_middleware.log_action(
                            entity=entity,
                            action=action,
                            entity_id=entity_id,
                            before=before_state,
                            after=after_state
                        )
                        
                        if audit_id:
                            span.set_attribute("audit.log_id", audit_id)
                            logger.debug(f"Audit logged for {action} on {entity}: {audit_id}")
                    else:
                        logger.warning("No audit middleware available in request context")
                        
                except Exception as e:
                    logger.error(
                        "Audit logging failed in decorator",
                        extra={
                            "entity": entity,
                            "action": action,
                            "entity_id": entity_id,
                            "error": str(e)
                        },
                        exc_info=True
                    )
                
                return result
        
        return decorated_function
    return decorator


def _capture_entity_state(entity: str, entity_id: str) -> Optional[Dict[str, Any]]:
    """
    Capture the current state of an entity for audit logging.
    
    Args:
        entity: Type of entity
        entity_id: ID of the entity
    
    Returns:
        Entity state dictionary or None if not found
    """
    try:
        from flask import current_app
        
        # Get user context for organization scoping
        user_context = getattr(g, 'user_context', None)
        if not user_context:
            return None
        
        # Map entity types to collections
        collection_map = {
            'notification': 'notifications',
            'user': 'users',
            'organization': 'organizations',
            'role': 'roles',
            'notification_target': 'notification_targets',
            'notification_category': 'notification_categories',
            'endpoint': 'endpoints'
        }
        
        collection = collection_map.get(entity)
        if not collection:
            logger.warning(f"Unknown entity type for state capture: {entity}")
            return None
        
        # Get entity from database
        mongodb_service = getattr(current_app, 'mongodb_service', None)
        if not mongodb_service:
            logger.warning("MongoDB service not available for state capture")
            return None
        
        entity_doc = mongodb_service.find_one_by_org(
            collection=collection,
            org_id=user_context.org_id,
            doc_id=entity_id,
            include_deleted=True  # Include deleted for audit purposes
        )
        
        if entity_doc:
            # Remove sensitive fields
            sensitive_fields = ['password_hash', 'original_payload']
            for field in sensitive_fields:
                entity_doc.pop(field, None)
        
        return entity_doc
        
    except Exception as e:
        logger.error(
            "Failed to capture entity state",
            extra={
                "entity": entity,
                "entity_id": entity_id,
                "error": str(e)
            },
            exc_info=True
        )
        return None


def setup_audit_middleware(app):
    """
    Set up audit middleware for the Flask application.
    
    Args:
        app: Flask application instance
    """
    audit_middleware = AuditMiddleware()
    
    @app.before_request
    def before_request():
        """Add audit middleware to request context."""
        g.audit_middleware = audit_middleware
    
    logger.info("Audit middleware configured for Flask application")


# Convenience functions for common audit actions

def log_authentication_event(action: str, user_id: Optional[str] = None, success: bool = True, details: Optional[Dict] = None):
    """
    Log authentication-related events.
    
    Args:
        action: Authentication action (login, logout, token_refresh, etc.)
        user_id: User ID (if available)
        success: Whether the action was successful
        details: Additional details about the event
    """
    try:
        audit_middleware = getattr(g, 'audit_middleware', None)
        if not audit_middleware:
            logger.warning("No audit middleware available for authentication event")
            return
        
        # Get user context or create minimal context for auth events
        user_context = getattr(g, 'user_context', None)
        
        if not user_context and user_id:
            # Create minimal context for auth events where user_context might not be available
            from ..models.entities import UserContext
            user_context = UserContext(
                user_id=user_id,
                org_id="unknown",  # Will be updated when we have the full context
                permissions=[],
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                session_id=request.headers.get('X-Session-ID')
            )
        
        if user_context:
            audit_id = audit_middleware.audit_service.log_action(
                user_id=user_context.user_id,
                org_id=user_context.org_id,
                entity="authentication",
                entity_id=f"auth_{action}_{user_context.user_id}",
                action=action,
                before=None,
                after={
                    "success": success,
                    "action": action,
                    "timestamp": str(datetime.utcnow()),
                    "details": details or {}
                },
                user_context=user_context
            )
            
            logger.info(
                f"Authentication event logged: {action}",
                extra={
                    "audit_id": audit_id,
                    "user_id": user_context.user_id,
                    "action": action,
                    "success": success
                }
            )
        
    except Exception as e:
        logger.error(
            "Failed to log authentication event",
            extra={
                "action": action,
                "user_id": user_id,
                "success": success,
                "error": str(e)
            },
            exc_info=True
        )


def log_notification_workflow_event(notification_id: str, action: str, before_state: Optional[Dict] = None, after_state: Optional[Dict] = None):
    """
    Log notification workflow events (approve, deny, dispatch).
    
    Args:
        notification_id: ID of the notification
        action: Workflow action performed
        before_state: State before the action
        after_state: State after the action
    """
    try:
        audit_middleware = getattr(g, 'audit_middleware', None)
        if not audit_middleware:
            logger.warning("No audit middleware available for notification workflow event")
            return
        
        audit_id = audit_middleware.log_action(
            entity="notification",
            action=action,
            entity_id=notification_id,
            before=before_state,
            after=after_state
        )
        
        logger.info(
            f"Notification workflow event logged: {action}",
            extra={
                "audit_id": audit_id,
                "notification_id": notification_id,
                "action": action
            }
        )
        
        return audit_id
        
    except Exception as e:
        logger.error(
            "Failed to log notification workflow event",
            extra={
                "notification_id": notification_id,
                "action": action,
                "error": str(e)
            },
            exc_info=True
        )
        return None