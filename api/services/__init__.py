# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Services package - External integrations and side effects.
"""

from .mongodb import MongoDBService, PaginationResult, get_mongodb_service, close_mongodb_connection

__all__ = [
    "MongoDBService",
    "PaginationResult", 
    "get_mongodb_service",
    "close_mongodb_connection"
]