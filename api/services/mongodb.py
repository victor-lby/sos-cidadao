# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
MongoDB service layer with multi-tenant operations and connection pooling.
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import (
    ConnectionFailure, 
    ServerSelectionTimeoutError,
    DuplicateKeyError,
    OperationFailure
)
from bson import ObjectId
from bson.errors import InvalidId

logger = logging.getLogger(__name__)


class PaginationResult:
    """Result container for paginated queries."""
    
    def __init__(self, items: List[Dict], total: int, page: int, page_size: int):
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size
        self.total_pages = (total + page_size - 1) // page_size
        self.has_next = page < self.total_pages
        self.has_prev = page > 1


class MongoDBService:
    """MongoDB service with multi-tenant operations and connection pooling."""
    
    def __init__(self, connection_string: str = None, database_name: str = None):
        """Initialize MongoDB service with connection pooling."""
        self.connection_string = connection_string or os.getenv(
            'MONGODB_URI', 
            'mongodb://localhost:27017/sos_cidadao_dev'
        )
        self.database_name = database_name or os.getenv('MONGODB_DATABASE', 'sos_cidadao_dev')
        self._client: Optional[MongoClient] = None
        self._database: Optional[Database] = None
        
        # Connection pool settings
        self.max_pool_size = int(os.getenv('MONGODB_MAX_POOL_SIZE', '10'))
        self.min_pool_size = int(os.getenv('MONGODB_MIN_POOL_SIZE', '1'))
        self.max_idle_time_ms = int(os.getenv('MONGODB_MAX_IDLE_TIME_MS', '30000'))
        self.server_selection_timeout_ms = int(os.getenv('MONGODB_SERVER_SELECTION_TIMEOUT_MS', '5000'))
        
        logger.info(f"MongoDB service initialized for database: {self.database_name}")
    
    @property
    def client(self) -> MongoClient:
        """Get MongoDB client with connection pooling."""
        if self._client is None:
            try:
                self._client = MongoClient(
                    self.connection_string,
                    maxPoolSize=self.max_pool_size,
                    minPoolSize=self.min_pool_size,
                    maxIdleTimeMS=self.max_idle_time_ms,
                    serverSelectionTimeoutMS=self.server_selection_timeout_ms,
                    retryWrites=True,
                    retryReads=True
                )
                # Test connection
                self._client.admin.command('ping')
                logger.info("MongoDB connection established successfully")
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                raise
        
        return self._client
    
    @property
    def database(self) -> Database:
        """Get MongoDB database."""
        if self._database is None:
            self._database = self.client[self.database_name]
        return self._database
    
    def get_collection(self, collection_name: str) -> Collection:
        """Get MongoDB collection."""
        return self.database[collection_name]
    
    def close_connection(self) -> None:
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._database = None
            logger.info("MongoDB connection closed")
    
    def health_check(self) -> Dict[str, Any]:
        """Check MongoDB connection health."""
        try:
            # Ping the database
            result = self.client.admin.command('ping')
            
            # Get server info
            server_info = self.client.server_info()
            
            return {
                'status': 'healthy',
                'ping': result.get('ok') == 1,
                'version': server_info.get('version'),
                'database': self.database_name,
                'connection_pool_size': self.max_pool_size
            }
        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'database': self.database_name
            }
    
    def _validate_object_id(self, doc_id: str) -> ObjectId:
        """Validate and convert string ID to ObjectId."""
        try:
            return ObjectId(doc_id)
        except InvalidId:
            raise ValueError(f"Invalid ObjectId format: {doc_id}")
    
    def _build_org_query(self, org_id: str, filters: Dict = None, include_deleted: bool = False) -> Dict:
        """Build organization-scoped query with optional filters."""
        query = {"organizationId": org_id}
        
        # Exclude soft-deleted records by default
        if not include_deleted:
            query["deletedAt"] = None
        
        # Add additional filters
        if filters:
            query.update(filters)
        
        return query
    
    def _add_timestamps(self, document: Dict, user_id: str, is_update: bool = False) -> Dict:
        """Add creation and update timestamps to document."""
        now = datetime.utcnow()
        
        if not is_update:
            document["createdAt"] = now
            document["createdBy"] = user_id
        
        document["updatedAt"] = now
        document["updatedBy"] = user_id
        
        return document
    
    # CRUD Operations with Organization Scoping
    
    def create(self, collection: str, document: Dict, user_id: str) -> str:
        """Create a new document with organization scoping."""
        try:
            # Add timestamps and ensure organization scoping
            document = self._add_timestamps(document, user_id)
            
            # Ensure document has an ID
            if "_id" not in document:
                document["_id"] = ObjectId()
            
            # Insert document
            collection_obj = self.get_collection(collection)
            result = collection_obj.insert_one(document)
            
            logger.info(f"Created document in {collection}: {result.inserted_id}")
            return str(result.inserted_id)
            
        except DuplicateKeyError as e:
            logger.error(f"Duplicate key error in {collection}: {e}")
            raise ValueError(f"Document with this identifier already exists")
        except Exception as e:
            logger.error(f"Failed to create document in {collection}: {e}")
            raise
    
    def find_by_org(self, collection: str, org_id: str, filters: Dict = None, 
                    include_deleted: bool = False) -> List[Dict]:
        """Find documents by organization with optional filters."""
        try:
            query = self._build_org_query(org_id, filters, include_deleted)
            collection_obj = self.get_collection(collection)
            
            documents = list(collection_obj.find(query))
            
            # Convert ObjectId to string for JSON serialization
            for doc in documents:
                if "_id" in doc:
                    doc["id"] = str(doc["_id"])
                    del doc["_id"]
            
            logger.debug(f"Found {len(documents)} documents in {collection} for org {org_id}")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to find documents in {collection}: {e}")
            raise
    
    def find_one_by_org(self, collection: str, org_id: str, doc_id: str, 
                       include_deleted: bool = False) -> Optional[Dict]:
        """Find a single document by organization and ID."""
        try:
            object_id = self._validate_object_id(doc_id)
            query = self._build_org_query(org_id, {"_id": object_id}, include_deleted)
            
            collection_obj = self.get_collection(collection)
            document = collection_obj.find_one(query)
            
            if document:
                document["id"] = str(document["_id"])
                del document["_id"]
                logger.debug(f"Found document {doc_id} in {collection}")
            else:
                logger.debug(f"Document {doc_id} not found in {collection} for org {org_id}")
            
            return document
            
        except ValueError as e:
            logger.error(f"Invalid document ID {doc_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to find document {doc_id} in {collection}: {e}")
            raise
    
    def update_by_org(self, collection: str, org_id: str, doc_id: str, 
                     updates: Dict, user_id: str) -> bool:
        """Update a document by organization and ID."""
        try:
            object_id = self._validate_object_id(doc_id)
            query = self._build_org_query(org_id, {"_id": object_id})
            
            # Add update timestamp
            updates = self._add_timestamps(updates, user_id, is_update=True)
            
            collection_obj = self.get_collection(collection)
            result = collection_obj.update_one(query, {"$set": updates})
            
            if result.modified_count > 0:
                logger.info(f"Updated document {doc_id} in {collection}")
                return True
            else:
                logger.warning(f"No document updated for {doc_id} in {collection}")
                return False
                
        except ValueError as e:
            logger.error(f"Invalid document ID {doc_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to update document {doc_id} in {collection}: {e}")
            raise
    
    def soft_delete_by_org(self, collection: str, org_id: str, doc_id: str, user_id: str) -> bool:
        """Soft delete a document by setting deletedAt timestamp."""
        try:
            object_id = self._validate_object_id(doc_id)
            query = self._build_org_query(org_id, {"_id": object_id})
            
            updates = {
                "deletedAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow(),
                "updatedBy": user_id
            }
            
            collection_obj = self.get_collection(collection)
            result = collection_obj.update_one(query, {"$set": updates})
            
            if result.modified_count > 0:
                logger.info(f"Soft deleted document {doc_id} in {collection}")
                return True
            else:
                logger.warning(f"No document soft deleted for {doc_id} in {collection}")
                return False
                
        except ValueError as e:
            logger.error(f"Invalid document ID {doc_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to soft delete document {doc_id} in {collection}: {e}")
            raise
    
    def hard_delete_by_org(self, collection: str, org_id: str, doc_id: str) -> bool:
        """Hard delete a document (use with caution)."""
        try:
            object_id = self._validate_object_id(doc_id)
            query = self._build_org_query(org_id, {"_id": object_id}, include_deleted=True)
            
            collection_obj = self.get_collection(collection)
            result = collection_obj.delete_one(query)
            
            if result.deleted_count > 0:
                logger.warning(f"Hard deleted document {doc_id} in {collection}")
                return True
            else:
                logger.warning(f"No document hard deleted for {doc_id} in {collection}")
                return False
                
        except ValueError as e:
            logger.error(f"Invalid document ID {doc_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to hard delete document {doc_id} in {collection}: {e}")
            raise
    
    def paginate_by_org(self, collection: str, org_id: str, page: int = 1, page_size: int = 20,
                       filters: Dict = None, sort_by: str = "createdAt", sort_order: int = -1,
                       include_deleted: bool = False) -> PaginationResult:
        """Paginate documents by organization with sorting and filtering."""
        try:
            query = self._build_org_query(org_id, filters, include_deleted)
            collection_obj = self.get_collection(collection)
            
            # Calculate skip value
            skip = (page - 1) * page_size
            
            # Get total count
            total = collection_obj.count_documents(query)
            
            # Get paginated documents
            cursor = collection_obj.find(query).sort(sort_by, sort_order).skip(skip).limit(page_size)
            documents = list(cursor)
            
            # Convert ObjectId to string
            for doc in documents:
                if "_id" in doc:
                    doc["id"] = str(doc["_id"])
                    del doc["_id"]
            
            logger.debug(f"Paginated {len(documents)} documents from {collection} (page {page})")
            return PaginationResult(documents, total, page, page_size)
            
        except Exception as e:
            logger.error(f"Failed to paginate documents in {collection}: {e}")
            raise
    
    def count_by_org(self, collection: str, org_id: str, filters: Dict = None,
                    include_deleted: bool = False) -> int:
        """Count documents by organization with optional filters."""
        try:
            query = self._build_org_query(org_id, filters, include_deleted)
            collection_obj = self.get_collection(collection)
            
            count = collection_obj.count_documents(query)
            logger.debug(f"Counted {count} documents in {collection} for org {org_id}")
            return count
            
        except Exception as e:
            logger.error(f"Failed to count documents in {collection}: {e}")
            raise
    
    def aggregate_by_org(self, collection: str, org_id: str, pipeline: List[Dict]) -> List[Dict]:
        """Run aggregation pipeline with organization scoping."""
        try:
            # Add organization match stage at the beginning
            org_match = {"$match": {"organizationId": org_id, "deletedAt": None}}
            pipeline.insert(0, org_match)
            
            collection_obj = self.get_collection(collection)
            results = list(collection_obj.aggregate(pipeline))
            
            logger.debug(f"Aggregation returned {len(results)} results from {collection}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to run aggregation in {collection}: {e}")
            raise
    
    # Index Management
    
    def create_indexes(self) -> None:
        """Create performance indexes for all collections."""
        try:
            logger.info("Creating MongoDB indexes...")
            
            # Organizations indexes
            orgs = self.get_collection("organizations")
            orgs.create_index("slug", unique=True)
            orgs.create_index("deletedAt")
            
            # Users indexes
            users = self.get_collection("users")
            users.create_index([("organizationId", ASCENDING), ("email", ASCENDING)], unique=True)
            users.create_index([("organizationId", ASCENDING), ("deletedAt", ASCENDING)])
            users.create_index([("organizationId", ASCENDING), ("status", ASCENDING)])
            
            # Notifications indexes
            notifications = self.get_collection("notifications")
            notifications.create_index([("organizationId", ASCENDING), ("status", ASCENDING), ("createdAt", DESCENDING)])
            notifications.create_index([("organizationId", ASCENDING), ("deletedAt", ASCENDING)])
            notifications.create_index([("organizationId", ASCENDING), ("severity", ASCENDING)])
            notifications.create_index([("organizationId", ASCENDING), ("origin", ASCENDING)])
            notifications.create_index("correlationId")
            
            # Notification targets indexes
            targets = self.get_collection("notification_targets")
            targets.create_index([("organizationId", ASCENDING), ("parentId", ASCENDING)])
            targets.create_index([("organizationId", ASCENDING), ("deletedAt", ASCENDING)])
            
            # Notification categories indexes
            categories = self.get_collection("notification_categories")
            categories.create_index([("organizationId", ASCENDING), ("name", ASCENDING)])
            categories.create_index([("organizationId", ASCENDING), ("deletedAt", ASCENDING)])
            
            # Endpoints indexes
            endpoints = self.get_collection("endpoints")
            endpoints.create_index([("organizationId", ASCENDING), ("isActive", ASCENDING)])
            endpoints.create_index([("organizationId", ASCENDING), ("deletedAt", ASCENDING)])
            
            # Roles indexes
            roles = self.get_collection("roles")
            roles.create_index([("organizationId", ASCENDING), ("name", ASCENDING)])
            roles.create_index([("organizationId", ASCENDING), ("deletedAt", ASCENDING)])
            
            # Audit logs indexes
            audit_logs = self.get_collection("audit_logs")
            audit_logs.create_index([("organizationId", ASCENDING), ("timestamp", DESCENDING)])
            audit_logs.create_index([("organizationId", ASCENDING), ("userId", ASCENDING), ("timestamp", DESCENDING)])
            audit_logs.create_index([("organizationId", ASCENDING), ("entity", ASCENDING), ("timestamp", DESCENDING)])
            audit_logs.create_index("traceId")
            
            logger.info("MongoDB indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create MongoDB indexes: {e}")
            raise
    
    def drop_indexes(self, collection: str) -> None:
        """Drop all indexes for a collection (except _id)."""
        try:
            collection_obj = self.get_collection(collection)
            collection_obj.drop_indexes()
            logger.info(f"Dropped indexes for collection: {collection}")
        except Exception as e:
            logger.error(f"Failed to drop indexes for {collection}: {e}")
            raise
    
    def get_collection_stats(self, collection: str) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            collection_obj = self.get_collection(collection)
            stats = self.database.command("collStats", collection)
            
            return {
                'collection': collection,
                'count': stats.get('count', 0),
                'size': stats.get('size', 0),
                'avgObjSize': stats.get('avgObjSize', 0),
                'storageSize': stats.get('storageSize', 0),
                'indexes': stats.get('nindexes', 0),
                'totalIndexSize': stats.get('totalIndexSize', 0)
            }
        except Exception as e:
            logger.error(f"Failed to get stats for collection {collection}: {e}")
            return {'collection': collection, 'error': str(e)}


# Singleton instance for application use
_mongodb_service: Optional[MongoDBService] = None


def get_mongodb_service() -> MongoDBService:
    """Get singleton MongoDB service instance."""
    global _mongodb_service
    if _mongodb_service is None:
        _mongodb_service = MongoDBService()
    return _mongodb_service


def close_mongodb_connection() -> None:
    """Close MongoDB connection (for cleanup)."""
    global _mongodb_service
    if _mongodb_service:
        _mongodb_service.close_connection()
        _mongodb_service = None