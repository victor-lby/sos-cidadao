#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Script to create MongoDB indexes for performance optimization.
"""

import sys
import os
import logging

# Add the parent directory to the path so we can import from api
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.mongodb import get_mongodb_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Create MongoDB indexes."""
    try:
        logger.info("Starting MongoDB index creation...")
        
        # Get MongoDB service
        mongodb_service = get_mongodb_service()
        
        # Test connection
        health = mongodb_service.health_check()
        if health['status'] != 'healthy':
            logger.error(f"MongoDB is not healthy: {health}")
            sys.exit(1)
        
        logger.info(f"Connected to MongoDB {health['version']} - Database: {health['database']}")
        
        # Create indexes
        mongodb_service.create_indexes()
        
        logger.info("MongoDB indexes created successfully!")
        
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")
        sys.exit(1)
    finally:
        # Close connection
        from services.mongodb import close_mongodb_connection
        close_mongodb_connection()


if __name__ == "__main__":
    main()