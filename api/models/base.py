# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Base entity models with common fields and validation.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId


def generate_object_id() -> str:
    """Generate a new MongoDB ObjectId as string."""
    return str(ObjectId())


class BaseEntity(BaseModel):
    """Base entity with common fields for all domain objects."""
    
    model_config = ConfigDict(
        # Allow population by field name or alias
        populate_by_name=True,
        # Use enum values instead of enum objects
        use_enum_values=True,
        # Validate assignment
        validate_assignment=True,
        # Arbitrary types allowed
        arbitrary_types_allowed=True
    )
    
    id: str = Field(default_factory=generate_object_id, description="Unique identifier")
    organization_id: str = Field(..., description="Organization scope identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    deleted_at: Optional[datetime] = Field(None, description="Soft delete timestamp")
    created_by: str = Field(..., description="User ID who created this entity")
    updated_by: str = Field(..., description="User ID who last updated this entity")
    schema_version: int = Field(default=1, description="Schema version for migrations")
    
    def update_timestamp(self, updated_by: str) -> None:
        """Update the timestamp and updated_by fields."""
        self.updated_at = datetime.utcnow()
        self.updated_by = updated_by
    
    def soft_delete(self, deleted_by: str) -> None:
        """Perform soft delete by setting deleted_at timestamp."""
        self.deleted_at = datetime.utcnow()
        self.updated_by = deleted_by
        self.update_timestamp(deleted_by)
    
    def is_deleted(self) -> bool:
        """Check if entity is soft deleted."""
        return self.deleted_at is not None


class BaseEntityCreate(BaseModel):
    """Base model for entity creation requests."""
    
    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True
    )
    
    organization_id: str = Field(..., description="Organization scope identifier")
    created_by: str = Field(..., description="User ID creating this entity")


class BaseEntityUpdate(BaseModel):
    """Base model for entity update requests."""
    
    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True
    )
    
    updated_by: str = Field(..., description="User ID updating this entity")