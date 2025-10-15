# SPDX-License-Identifier: Apache-2.0

"""
Notification domain logic for workflow management.

This module contains pure functions for notification workflow processing,
validation, status transitions, and HAL response transformation.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import uuid
from models.entities import (
    Notification, NotificationStatus, NotificationSeverity, 
    UserContext, NotificationTarget, NotificationCategory
)
from models.enums import NotificationStatus as StatusEnum


@dataclass
class NotificationFilters:
    """Filters for notification queries."""
    status: Optional[NotificationStatus] = None
    severity: Optional[NotificationSeverity] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search_term: Optional[str] = None
    target_ids: Optional[List[str]] = None
    category_ids: Optional[List[str]] = None
    origin: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of notification validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class WorkflowResult:
    """Result of notification workflow operation."""
    success: bool
    notification: Optional[Notification] = None
    error_message: Optional[str] = None
    validation_errors: List[str] = None
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []


def receive_notification(
    payload: Dict[str, Any], 
    origin: str, 
    user_context: UserContext
) -> WorkflowResult:
    """
    Process incoming notification webhook payload.
    
    Args:
        payload: Raw webhook payload
        origin: Source system identifier
        user_context: User context for organization scoping
        
    Returns:
        WorkflowResult with created notification or errors
    """
    # Validate required fields
    validation = validate_incoming_payload(payload)
    if not validation.is_valid:
        return WorkflowResult(
            success=False,
            error_message="Invalid payload",
            validation_errors=validation.errors
        )
    
    # Extract notification data from payload
    try:
        notification_data = extract_notification_data(payload, origin, user_context)
        
        # Create notification entity
        notification = Notification(
            **notification_data,
            status=NotificationStatus.RECEIVED,
            original_payload=payload,
            correlation_id=str(uuid.uuid4()),
            organization_id=user_context.org_id,
            created_by=user_context.user_id,
            updated_by=user_context.user_id
        )
        
        return WorkflowResult(success=True, notification=notification)
        
    except Exception as e:
        return WorkflowResult(
            success=False,
            error_message=f"Failed to process notification: {str(e)}"
        )


def validate_incoming_payload(payload: Dict[str, Any]) -> ValidationResult:
    """
    Validate incoming webhook payload structure.
    
    Args:
        payload: Raw webhook payload
        
    Returns:
        ValidationResult with validation status and errors
    """
    errors = []
    warnings = []
    
    # Required fields
    required_fields = ['title', 'body', 'severity']
    for field in required_fields:
        if field not in payload:
            errors.append(f"Missing required field: {field}")
        elif not payload[field]:
            errors.append(f"Field '{field}' cannot be empty")
    
    # Validate severity
    if 'severity' in payload:
        try:
            severity = int(payload['severity'])
            if severity < 0 or severity > 5:
                errors.append("Severity must be between 0 and 5")
        except (ValueError, TypeError):
            errors.append("Severity must be a valid integer")
    
    # Validate title length
    if 'title' in payload and len(str(payload['title'])) > 200:
        errors.append("Title cannot exceed 200 characters")
    
    # Validate body length
    if 'body' in payload and len(str(payload['body'])) > 2000:
        errors.append("Body cannot exceed 2000 characters")
    
    # Check for potentially dangerous content
    if 'title' in payload and any(char in str(payload['title']) for char in ['<', '>', '&']):
        warnings.append("Title contains HTML-like characters")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def extract_notification_data(
    payload: Dict[str, Any], 
    origin: str, 
    user_context: UserContext
) -> Dict[str, Any]:
    """
    Extract and normalize notification data from payload.
    
    Args:
        payload: Raw webhook payload
        origin: Source system identifier
        user_context: User context for defaults
        
    Returns:
        Dictionary of normalized notification data
    """
    return {
        'title': str(payload['title']).strip(),
        'body': str(payload['body']).strip(),
        'severity': NotificationSeverity(int(payload['severity'])),
        'origin': origin,
        'target_ids': payload.get('targets', []),
        'category_ids': payload.get('categories', []),
        'base_target_id': payload.get('base_target')
    }


def validate_approval_request(
    notification: Notification,
    target_ids: List[str],
    category_ids: List[str],
    user_context: UserContext
) -> ValidationResult:
    """
    Validate notification approval request.
    
    Args:
        notification: Notification to approve
        target_ids: Selected target IDs
        category_ids: Selected category IDs
        user_context: User context for permission checks
        
    Returns:
        ValidationResult with validation status and errors
    """
    errors = []
    warnings = []
    
    # Check notification state
    if not notification.can_approve():
        errors.append(f"Notification cannot be approved (current status: {notification.status})")
    
    # Check organization access
    if notification.organization_id != user_context.org_id:
        errors.append("Cannot approve notification from different organization")
    
    # Validate targets
    if not target_ids:
        errors.append("At least one target must be selected")
    
    # Validate categories
    if not category_ids:
        errors.append("At least one category must be selected")
    
    # Check for high-severity notifications with many targets
    if notification.severity >= 4 and len(target_ids) > 1000:
        warnings.append("High-severity notification with large target audience")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def approve_notification(
    notification: Notification,
    target_ids: List[str],
    category_ids: List[str],
    user_context: UserContext
) -> WorkflowResult:
    """
    Approve notification for dispatch.
    
    Args:
        notification: Notification to approve
        target_ids: Selected target IDs
        category_ids: Selected category IDs
        user_context: User context for approval
        
    Returns:
        WorkflowResult with updated notification or errors
    """
    # Validate approval request
    validation = validate_approval_request(notification, target_ids, category_ids, user_context)
    if not validation.is_valid:
        return WorkflowResult(
            success=False,
            error_message="Approval validation failed",
            validation_errors=validation.errors
        )
    
    try:
        # Create updated notification
        updated_notification = notification.model_copy()
        updated_notification.approve(user_context.user_id, target_ids, category_ids)
        
        return WorkflowResult(success=True, notification=updated_notification)
        
    except Exception as e:
        return WorkflowResult(
            success=False,
            error_message=f"Failed to approve notification: {str(e)}"
        )


def validate_denial_request(
    notification: Notification,
    reason: str,
    user_context: UserContext
) -> ValidationResult:
    """
    Validate notification denial request.
    
    Args:
        notification: Notification to deny
        reason: Denial reason
        user_context: User context for permission checks
        
    Returns:
        ValidationResult with validation status and errors
    """
    errors = []
    
    # Check notification state
    if not notification.can_deny():
        errors.append(f"Notification cannot be denied (current status: {notification.status})")
    
    # Check organization access
    if notification.organization_id != user_context.org_id:
        errors.append("Cannot deny notification from different organization")
    
    # Validate reason
    if not reason or not reason.strip():
        errors.append("Denial reason is required")
    elif len(reason.strip()) < 10:
        errors.append("Denial reason must be at least 10 characters")
    elif len(reason.strip()) > 500:
        errors.append("Denial reason cannot exceed 500 characters")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors
    )


def deny_notification(
    notification: Notification,
    reason: str,
    user_context: UserContext
) -> WorkflowResult:
    """
    Deny notification with reason.
    
    Args:
        notification: Notification to deny
        reason: Denial reason
        user_context: User context for denial
        
    Returns:
        WorkflowResult with updated notification or errors
    """
    # Validate denial request
    validation = validate_denial_request(notification, reason, user_context)
    if not validation.is_valid:
        return WorkflowResult(
            success=False,
            error_message="Denial validation failed",
            validation_errors=validation.errors
        )
    
    try:
        # Create updated notification
        updated_notification = notification.model_copy()
        updated_notification.deny(user_context.user_id, reason.strip())
        
        return WorkflowResult(success=True, notification=updated_notification)
        
    except Exception as e:
        return WorkflowResult(
            success=False,
            error_message=f"Failed to deny notification: {str(e)}"
        )


def filter_notifications(
    notifications: List[Notification],
    filters: NotificationFilters
) -> List[Notification]:
    """
    Filter notifications based on criteria.
    
    Args:
        notifications: List of notifications to filter
        filters: Filter criteria
        
    Returns:
        Filtered list of notifications
    """
    filtered = notifications
    
    # Filter by status
    if filters.status is not None:
        filtered = [n for n in filtered if n.status == filters.status]
    
    # Filter by severity
    if filters.severity is not None:
        filtered = [n for n in filtered if n.severity == filters.severity]
    
    # Filter by date range
    if filters.date_from:
        filtered = [n for n in filtered if n.created_at >= filters.date_from]
    
    if filters.date_to:
        filtered = [n for n in filtered if n.created_at <= filters.date_to]
    
    # Filter by search term (title and body)
    if filters.search_term:
        search_lower = filters.search_term.lower()
        filtered = [
            n for n in filtered 
            if search_lower in n.title.lower() or search_lower in n.body.lower()
        ]
    
    # Filter by target IDs
    if filters.target_ids:
        filtered = [
            n for n in filtered 
            if any(target_id in n.target_ids for target_id in filters.target_ids)
        ]
    
    # Filter by category IDs
    if filters.category_ids:
        filtered = [
            n for n in filtered 
            if any(cat_id in n.category_ids for cat_id in filters.category_ids)
        ]
    
    # Filter by origin
    if filters.origin:
        filtered = [n for n in filtered if n.origin == filters.origin]
    
    return filtered


def search_notifications(
    notifications: List[Notification],
    search_term: str
) -> List[Notification]:
    """
    Search notifications by title and body content.
    
    Args:
        notifications: List of notifications to search
        search_term: Search term
        
    Returns:
        List of matching notifications
    """
    if not search_term or not search_term.strip():
        return notifications
    
    search_lower = search_term.strip().lower()
    
    return [
        notification for notification in notifications
        if (search_lower in notification.title.lower() or 
            search_lower in notification.body.lower() or
            search_lower in notification.origin.lower())
    ]


def calculate_notification_priority(
    severity: NotificationSeverity,
    target_count: int,
    category_count: int = 1
) -> int:
    """
    Calculate notification priority for processing order.
    
    Args:
        severity: Notification severity level
        target_count: Number of targets
        category_count: Number of categories
        
    Returns:
        Priority level (1=highest, 5=lowest)
    """
    # High severity with many targets = highest priority
    if severity >= 4 and target_count > 1000:
        return 1
    
    # High severity = high priority
    if severity >= 4:
        return 2
    
    # Medium severity with many targets = medium-high priority
    if severity >= 2 and target_count > 500:
        return 2
    
    # Medium severity = medium priority
    if severity >= 2:
        return 3
    
    # Low severity with many targets = medium-low priority
    if target_count > 100:
        return 4
    
    # Low severity = lowest priority
    return 5


def validate_status_transition(
    current_status: NotificationStatus,
    new_status: NotificationStatus
) -> ValidationResult:
    """
    Validate notification status transition.
    
    Args:
        current_status: Current notification status
        new_status: Desired new status
        
    Returns:
        ValidationResult with validation status and errors
    """
    errors = []
    
    # Define valid transitions
    valid_transitions = {
        NotificationStatus.RECEIVED: [NotificationStatus.APPROVED, NotificationStatus.DENIED],
        NotificationStatus.APPROVED: [NotificationStatus.DISPATCHED],
        NotificationStatus.DENIED: [],  # Terminal state
        NotificationStatus.DISPATCHED: []  # Terminal state
    }
    
    if new_status not in valid_transitions.get(current_status, []):
        errors.append(
            f"Invalid status transition from {current_status} to {new_status}"
        )
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors
    )


def build_notification_hal_response(
    notification: Notification,
    user_context: UserContext,
    base_url: str,
    include_embedded: bool = False
) -> Dict[str, Any]:
    """
    Build HAL response for notification with affordance links.
    
    Args:
        notification: Notification entity
        user_context: User context for permission-based links
        base_url: Base URL for link generation
        include_embedded: Whether to include embedded resources
        
    Returns:
        HAL-formatted response dictionary
    """
    response = {
        "id": notification.id,
        "title": notification.title,
        "body": notification.body,
        "severity": notification.severity,
        "status": notification.status,
        "origin": notification.origin,
        "target_ids": notification.target_ids,
        "category_ids": notification.category_ids,
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
        "updated_at": notification.updated_at.isoformat() if notification.updated_at else None,
        "_links": {
            "self": {"href": f"{base_url}/api/notifications/{notification.id}"}
        }
    }
    
    # Add status-specific fields
    if notification.status == NotificationStatus.APPROVED:
        response.update({
            "approved_at": notification.approved_at.isoformat() if notification.approved_at else None,
            "approved_by": notification.approved_by
        })
    elif notification.status == NotificationStatus.DENIED:
        response.update({
            "denied_at": notification.denied_at.isoformat() if notification.denied_at else None,
            "denied_by": notification.denied_by,
            "denial_reason": notification.denial_reason
        })
    elif notification.status == NotificationStatus.DISPATCHED:
        response.update({
            "dispatched_at": notification.dispatched_at.isoformat() if notification.dispatched_at else None,
            "approved_at": notification.approved_at.isoformat() if notification.approved_at else None,
            "approved_by": notification.approved_by
        })
    
    # Add conditional affordance links based on status and permissions
    links = response["_links"]
    
    # Approve link
    if (notification.status == NotificationStatus.RECEIVED and 
        user_context.has_permission("notification:approve")):
        links["approve"] = {
            "href": f"{base_url}/api/notifications/{notification.id}/approve",
            "method": "POST",
            "type": "application/json"
        }
    
    # Deny link
    if (notification.status == NotificationStatus.RECEIVED and 
        user_context.has_permission("notification:deny")):
        links["deny"] = {
            "href": f"{base_url}/api/notifications/{notification.id}/deny",
            "method": "POST",
            "type": "application/json"
        }
    
    # Edit link (only for received notifications)
    if (notification.status == NotificationStatus.RECEIVED and 
        user_context.has_permission("notification:edit")):
        links["edit"] = {
            "href": f"{base_url}/api/notifications/{notification.id}",
            "method": "PUT",
            "type": "application/json"
        }
    
    # Collection link
    links["collection"] = {
        "href": f"{base_url}/api/notifications"
    }
    
    return response


def build_notification_collection_hal_response(
    notifications: List[Notification],
    user_context: UserContext,
    base_url: str,
    page: int = 1,
    page_size: int = 20,
    total_count: int = None
) -> Dict[str, Any]:
    """
    Build HAL collection response for notifications.
    
    Args:
        notifications: List of notification entities
        user_context: User context for permission-based links
        base_url: Base URL for link generation
        page: Current page number
        page_size: Items per page
        total_count: Total number of items (if known)
        
    Returns:
        HAL-formatted collection response
    """
    # Build embedded notification items
    embedded_items = [
        build_notification_hal_response(notification, user_context, base_url)
        for notification in notifications
    ]
    
    # Calculate pagination
    if total_count is None:
        total_count = len(notifications)
    
    total_pages = (total_count + page_size - 1) // page_size
    
    response = {
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "_embedded": {
            "notifications": embedded_items
        },
        "_links": {
            "self": {"href": f"{base_url}/api/notifications?page={page}&size={page_size}"}
        }
    }
    
    # Add pagination links
    links = response["_links"]
    
    # First page
    if page > 1:
        links["first"] = {"href": f"{base_url}/api/notifications?page=1&size={page_size}"}
    
    # Previous page
    if page > 1:
        links["prev"] = {"href": f"{base_url}/api/notifications?page={page-1}&size={page_size}"}
    
    # Next page
    if page < total_pages:
        links["next"] = {"href": f"{base_url}/api/notifications?page={page+1}&size={page_size}"}
    
    # Last page
    if page < total_pages:
        links["last"] = {"href": f"{base_url}/api/notifications?page={total_pages}&size={page_size}"}
    
    return response


def expand_target_hierarchy(
    base_target_id: str,
    all_targets: List[NotificationTarget]
) -> List[str]:
    """
    Expand target hierarchy to include all child targets.
    
    Args:
        base_target_id: Root target ID
        all_targets: All available targets
        
    Returns:
        List of target IDs including base and all descendants
    """
    target_map = {target.id: target for target in all_targets}
    expanded_ids = set()
    
    def expand_recursive(target_id: str):
        if target_id in expanded_ids or target_id not in target_map:
            return
        
        expanded_ids.add(target_id)
        target = target_map[target_id]
        
        # Expand children
        for child_id in target.children_ids:
            expand_recursive(child_id)
    
    expand_recursive(base_target_id)
    return list(expanded_ids)


def validate_target_category_mapping(
    target_ids: List[str],
    category_ids: List[str],
    all_targets: List[NotificationTarget],
    all_categories: List[NotificationCategory]
) -> ValidationResult:
    """
    Validate that selected targets and categories are compatible.
    
    Args:
        target_ids: Selected target IDs
        category_ids: Selected category IDs
        all_targets: All available targets
        all_categories: All available categories
        
    Returns:
        ValidationResult with validation status and errors
    """
    errors = []
    warnings = []
    
    # Check if targets exist
    target_map = {target.id: target for target in all_targets}
    for target_id in target_ids:
        if target_id not in target_map:
            errors.append(f"Target not found: {target_id}")
    
    # Check if categories exist
    category_map = {category.id: category for category in all_categories}
    for category_id in category_ids:
        if category_id not in category_map:
            errors.append(f"Category not found: {category_id}")
    
    # Check target-category compatibility
    for category_id in category_ids:
        if category_id in category_map:
            category = category_map[category_id]
            # Check if any selected targets are associated with this category
            if category.target_ids and not any(tid in category.target_ids for tid in target_ids):
                warnings.append(
                    f"Category '{category.name}' is not associated with any selected targets"
                )
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )