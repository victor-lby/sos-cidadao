# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Audit service for comprehensive action logging with OpenTelemetry correlation.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from opentelemetry import trace
from bson import ObjectId

from .mongodb import MongoDBService, PaginationResult
from models.entities import AuditLog, UserContext

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class AuditFilters:
    """Filters for audit log queries."""
    
    def __init__(
        self,
        user_id: Optional[str] = None,
        entity: Optional[str] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        trace_id: Optional[str] = None,
        entity_id: Optional[str] = None
    ):
        self.user_id = user_id
        self.entity = entity
        self.action = action
        self.start_date = start_date
        self.end_date = end_date
        self.trace_id = trace_id
        self.entity_id = entity_id
    
    def to_mongo_query(self) -> Dict[str, Any]:
        """Convert filters to MongoDB query."""
        query = {}
        
        if self.user_id:
            query["userId"] = self.user_id
        
        if self.entity:
            query["entity"] = self.entity
        
        if self.action:
            query["action"] = self.action
        
        if self.trace_id:
            query["traceId"] = self.trace_id
        
        if self.entity_id:
            query["entityId"] = self.entity_id
        
        # Date range filter
        if self.start_date or self.end_date:
            date_filter = {}
            if self.start_date:
                date_filter["$gte"] = self.start_date
            if self.end_date:
                date_filter["$lte"] = self.end_date
            query["timestamp"] = date_filter
        
        return query


class AuditService:
    """Service for audit logging with MongoDB persistence and organization scoping."""
    
    def __init__(self, mongo_service: MongoDBService):
        """Initialize audit service with MongoDB dependency."""
        self.mongo_service = mongo_service
        self.collection_name = "audit_logs"
        logger.info("Audit service initialized")
    
    def log_action(
        self,
        user_id: str,
        org_id: str,
        entity: str,
        entity_id: str,
        action: str,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
        user_context: Optional[UserContext] = None
    ) -> str:
        """
        Log an audit trail entry with trace correlation and structured logging.
        
        Args:
            user_id: ID of user performing the action
            org_id: Organization ID for multi-tenant scoping
            entity: Type of entity being acted upon
            entity_id: ID of the specific entity
            action: Action being performed
            before: State before the action (optional)
            after: State after the action (optional)
            user_context: Full user context with request details (optional)
        
        Returns:
            str: ID of the created audit log entry
        """
        with tracer.start_as_current_span("audit.log_action") as span:
            try:
                # Get current span context for trace correlation
                span_context = span.get_span_context()
                
                # Create audit entry
                audit_entry = {
                    "id": str(ObjectId()),
                    "timestamp": datetime.utcnow(),
                    "userId": user_id,
                    "organizationId": org_id,
                    "entity": entity,
                    "entityId": entity_id,
                    "action": action,
                    "before": before,
                    "after": after,
                    "schemaVersion": 1
                }
                
                # Add trace correlation if available
                if span_context.is_valid:
                    audit_entry.update({
                        "traceId": format(span_context.trace_id, "032x"),
                        "spanId": format(span_context.span_id, "016x")
                    })
                
                # Add request context if available
                if user_context:
                    audit_entry.update({
                        "ipAddress": user_context.ip_address,
                        "userAgent": user_context.user_agent,
                        "sessionId": user_context.session_id
                    })
                
                # Set span attributes
                span.set_attributes({
                    "audit.entity": entity,
                    "audit.action": action,
                    "audit.user_id": user_id,
                    "audit.organization_id": org_id,
                    "audit.entity_id": entity_id
                })
                
                # Store audit entry
                audit_id = self.mongo_service.create(
                    self.collection_name, 
                    audit_entry, 
                    user_id
                )
                
                # Calculate changes for logging
                changes_count = 0
                if before and after:
                    changes_count = len(self._calculate_changes(before, after))
                
                # Structured logging for audit event
                logger.info(
                    "Audit trail entry created",
                    extra={
                        "audit_id": audit_id,
                        "entity": entity,
                        "entity_id": entity_id,
                        "action": action,
                        "user_id": user_id,
                        "organization_id": org_id,
                        "trace_id": audit_entry.get("traceId"),
                        "changes_count": changes_count,
                        "audit_category": "business_action"
                    }
                )
                
                return audit_id
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                logger.error(
                    "Failed to create audit trail entry",
                    extra={
                        "entity": entity,
                        "entity_id": entity_id,
                        "action": action,
                        "user_id": user_id,
                        "organization_id": org_id,
                        "error": str(e)
                    },
                    exc_info=True
                )
                raise
    
    def query_audit_logs(
        self,
        org_id: str,
        filters: AuditFilters,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "timestamp",
        sort_order: int = -1
    ) -> PaginationResult:
        """
        Query audit logs with filtering, pagination, and organization scoping.
        
        Args:
            org_id: Organization ID for scoping
            filters: Audit log filters
            page: Page number (1-based)
            page_size: Number of items per page
            sort_by: Field to sort by
            sort_order: Sort order (1 for ascending, -1 for descending)
        
        Returns:
            PaginationResult: Paginated audit log results
        """
        with tracer.start_as_current_span("audit.query_logs") as span:
            try:
                # Convert filters to MongoDB query
                mongo_filters = filters.to_mongo_query()
                
                # Set span attributes
                span.set_attributes({
                    "audit.query.organization_id": org_id,
                    "audit.query.page": page,
                    "audit.query.page_size": page_size,
                    "audit.query.sort_by": sort_by,
                    "audit.query.filters_count": len(mongo_filters)
                })
                
                # Query with pagination
                result = self.mongo_service.paginate_by_org(
                    collection=self.collection_name,
                    org_id=org_id,
                    page=page,
                    page_size=page_size,
                    filters=mongo_filters,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    include_deleted=False
                )
                
                logger.info(
                    "Audit logs queried successfully",
                    extra={
                        "organization_id": org_id,
                        "page": page,
                        "page_size": page_size,
                        "total_results": result.total,
                        "returned_items": len(result.items)
                    }
                )
                
                return result
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                logger.error(
                    "Failed to query audit logs",
                    extra={
                        "organization_id": org_id,
                        "page": page,
                        "page_size": page_size,
                        "error": str(e)
                    },
                    exc_info=True
                )
                raise
    
    def get_audit_log(self, org_id: str, audit_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific audit log entry by ID.
        
        Args:
            org_id: Organization ID for scoping
            audit_id: Audit log entry ID
        
        Returns:
            Optional[Dict]: Audit log entry or None if not found
        """
        with tracer.start_as_current_span("audit.get_log") as span:
            try:
                span.set_attributes({
                    "audit.organization_id": org_id,
                    "audit.log_id": audit_id
                })
                
                audit_log = self.mongo_service.find_one_by_org(
                    collection=self.collection_name,
                    org_id=org_id,
                    doc_id=audit_id,
                    include_deleted=False
                )
                
                if audit_log:
                    logger.debug(f"Retrieved audit log {audit_id} for org {org_id}")
                else:
                    logger.debug(f"Audit log {audit_id} not found for org {org_id}")
                
                return audit_log
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                logger.error(
                    "Failed to get audit log",
                    extra={
                        "organization_id": org_id,
                        "audit_id": audit_id,
                        "error": str(e)
                    },
                    exc_info=True
                )
                raise
    
    def export_audit_logs(
        self,
        org_id: str,
        filters: AuditFilters,
        format_type: str = "json",
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Export audit logs in specified format with streaming support.
        
        Args:
            org_id: Organization ID for scoping
            filters: Audit log filters
            format_type: Export format ("json" or "csv")
            limit: Maximum number of records to export (optional)
        
        Returns:
            List[Dict]: Audit log entries for export
        """
        with tracer.start_as_current_span("audit.export_logs") as span:
            try:
                # Convert filters to MongoDB query
                mongo_filters = filters.to_mongo_query()
                
                span.set_attributes({
                    "audit.export.organization_id": org_id,
                    "audit.export.format": format_type,
                    "audit.export.limit": limit or 0,
                    "audit.export.filters_count": len(mongo_filters)
                })
                
                # Query all matching records (with optional limit)
                if limit:
                    # Use pagination with large page size for limited export
                    result = self.mongo_service.paginate_by_org(
                        collection=self.collection_name,
                        org_id=org_id,
                        page=1,
                        page_size=limit,
                        filters=mongo_filters,
                        sort_by="timestamp",
                        sort_order=-1,
                        include_deleted=False
                    )
                    audit_logs = result.items
                else:
                    # Get all matching records
                    audit_logs = self.mongo_service.find_by_org(
                        collection=self.collection_name,
                        org_id=org_id,
                        filters=mongo_filters,
                        include_deleted=False
                    )
                    # Sort by timestamp descending
                    audit_logs.sort(key=lambda x: x.get("timestamp", datetime.min), reverse=True)
                
                logger.info(
                    "Audit logs exported successfully",
                    extra={
                        "organization_id": org_id,
                        "format": format_type,
                        "exported_count": len(audit_logs),
                        "limit": limit
                    }
                )
                
                return audit_logs
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                logger.error(
                    "Failed to export audit logs",
                    extra={
                        "organization_id": org_id,
                        "format": format_type,
                        "limit": limit,
                        "error": str(e)
                    },
                    exc_info=True
                )
                raise
    
    def get_audit_statistics(self, org_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get audit statistics for the organization.
        
        Args:
            org_id: Organization ID for scoping
            days: Number of days to include in statistics
        
        Returns:
            Dict: Audit statistics
        """
        with tracer.start_as_current_span("audit.get_statistics") as span:
            try:
                # Calculate date range
                end_date = datetime.utcnow()
                start_date = datetime.utcnow().replace(
                    day=end_date.day - days if end_date.day > days else 1
                )
                
                span.set_attributes({
                    "audit.stats.organization_id": org_id,
                    "audit.stats.days": days,
                    "audit.stats.start_date": start_date.isoformat(),
                    "audit.stats.end_date": end_date.isoformat()
                })
                
                # Aggregation pipeline for statistics
                pipeline = [
                    {
                        "$match": {
                            "timestamp": {"$gte": start_date, "$lte": end_date}
                        }
                    },
                    {
                        "$group": {
                            "_id": {
                                "entity": "$entity",
                                "action": "$action"
                            },
                            "count": {"$sum": 1}
                        }
                    },
                    {
                        "$group": {
                            "_id": "$_id.entity",
                            "actions": {
                                "$push": {
                                    "action": "$_id.action",
                                    "count": "$count"
                                }
                            },
                            "total": {"$sum": "$count"}
                        }
                    }
                ]
                
                # Run aggregation
                stats_result = self.mongo_service.aggregate_by_org(
                    collection=self.collection_name,
                    org_id=org_id,
                    pipeline=pipeline
                )
                
                # Format results
                statistics = {
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "days": days
                    },
                    "total_actions": sum(item["total"] for item in stats_result),
                    "entities": {}
                }
                
                for item in stats_result:
                    entity = item["_id"]
                    statistics["entities"][entity] = {
                        "total": item["total"],
                        "actions": {action["action"]: action["count"] for action in item["actions"]}
                    }
                
                logger.info(
                    "Audit statistics calculated",
                    extra={
                        "organization_id": org_id,
                        "days": days,
                        "total_actions": statistics["total_actions"],
                        "entities_count": len(statistics["entities"])
                    }
                )
                
                return statistics
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                logger.error(
                    "Failed to calculate audit statistics",
                    extra={
                        "organization_id": org_id,
                        "days": days,
                        "error": str(e)
                    },
                    exc_info=True
                )
                raise
    
    def _calculate_changes(self, before: Dict[str, Any], after: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Calculate field-level changes for detailed audit trail.
        
        Args:
            before: State before the change
            after: State after the change
        
        Returns:
            List[Dict]: List of field changes
        """
        changes = []
        
        # Get all keys from both dictionaries
        all_keys = set(before.keys()) | set(after.keys())
        
        for key in all_keys:
            old_value = before.get(key)
            new_value = after.get(key)
            
            # Skip timestamp fields and internal fields
            if key in ["updatedAt", "updatedBy", "_id", "id"]:
                continue
            
            if old_value != new_value:
                changes.append({
                    "field": key,
                    "old_value": old_value,
                    "new_value": new_value
                })
        
        return changes


# Singleton instance for application use
_audit_service: Optional[AuditService] = None


def get_audit_service(mongo_service: Optional[MongoDBService] = None) -> AuditService:
    """Get singleton audit service instance."""
    global _audit_service
    if _audit_service is None:
        from .mongodb import get_mongodb_service
        mongo_svc = mongo_service or get_mongodb_service()
        _audit_service = AuditService(mongo_svc)
    return _audit_service