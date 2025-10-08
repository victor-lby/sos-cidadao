# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""
Services package - External integrations and side effects.
"""

from .mongodb import MongoDBService, PaginationResult, get_mongodb_service, close_mongodb_connection
from .amqp import AMQPService, AMQPConfig, PublishResult, create_amqp_service

__all__ = [
    "MongoDBService",
    "PaginationResult", 
    "get_mongodb_service",
    "close_mongodb_connection",
    "AMQPService",
    "AMQPConfig",
    "PublishResult",
    "create_amqp_service"
]