# SPDX-License-Identifier: Apache-2.0

"""
AMQP Service for LavinMQ Integration

This module provides AMQP message publishing capabilities for the S.O.S Cidadão platform.
It handles connection management, exchange/queue setup, and message publishing with
serverless-friendly connection handling for Vercel deployment.
"""

import json
import logging
import os
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Generator
from urllib.parse import urlparse

import pika
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from pydantic import BaseModel

from models.entities import Notification, NotificationTarget, Endpoint


logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class AMQPConfig:
    """AMQP configuration settings."""
    url: str
    connection_timeout: int = 30
    heartbeat: int = 600
    blocked_connection_timeout: int = 300
    retry_delay: float = 1.0
    max_retries: int = 3


@dataclass
class PublishResult:
    """Result of message publishing operation."""
    success: bool
    correlation_id: str
    exchange: str
    routing_key: str
    error: Optional[str] = None
    retry_count: int = 0


class AMQPConnectionError(Exception):
    """Raised when AMQP connection fails."""
    pass


class AMQPPublishError(Exception):
    """Raised when message publishing fails."""
    pass


class AMQPService:
    """
    AMQP service for LavinMQ integration with serverless-friendly connection handling.
    
    This service provides:
    - Connection pooling with automatic reconnection
    - Exchange and queue setup
    - Message publishing with retry logic
    - Payload transformation based on endpoint configuration
    - OpenTelemetry tracing integration
    """
    
    def __init__(self, config: AMQPConfig):
        self.config = config
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[pika.channel.Channel] = None
        self._connection_params = self._parse_connection_url(config.url)
        
    def _parse_connection_url(self, url: str) -> pika.ConnectionParameters:
        """Parse AMQP URL and create connection parameters."""
        parsed = urlparse(url)
        
        return pika.ConnectionParameters(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 5672,
            virtual_host=parsed.path.lstrip('/') or '/',
            credentials=pika.PlainCredentials(
                username=parsed.username or 'guest',
                password=parsed.password or 'guest'
            ),
            connection_attempts=self.config.max_retries,
            retry_delay=self.config.retry_delay,
            socket_timeout=self.config.connection_timeout,
            heartbeat=self.config.heartbeat,
            blocked_connection_timeout=self.config.blocked_connection_timeout
        )
    
    @contextmanager
    def _get_connection(self) -> Generator[pika.channel.Channel, None, None]:
        """
        Context manager for AMQP connections with automatic cleanup.
        
        This is serverless-friendly as it creates fresh connections for each operation
        and ensures proper cleanup to avoid connection leaks.
        """
        connection = None
        channel = None
        
        try:
            with tracer.start_as_current_span("amqp.connection.create") as span:
                connection = pika.BlockingConnection(self._connection_params)
                channel = connection.channel()
                
                span.set_attributes({
                    "amqp.host": self._connection_params.host,
                    "amqp.port": self._connection_params.port,
                    "amqp.virtual_host": self._connection_params.virtual_host
                })
                
                logger.debug(
                    "AMQP connection established",
                    extra={
                        "extra_fields": {
                            "host": self._connection_params.host,
                            "port": self._connection_params.port,
                            "virtual_host": self._connection_params.virtual_host
                        }
                    }
                )
            
            yield channel
            
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(
                "AMQP connection failed",
                extra={
                    "extra_fields": {
                        "error": str(e),
                        "host": self._connection_params.host,
                        "port": self._connection_params.port
                    }
                },
                exc_info=True
            )
            raise AMQPConnectionError(f"Failed to connect to AMQP broker: {e}")
            
        except Exception as e:
            logger.error(
                "Unexpected error in AMQP connection",
                extra={
                    "extra_fields": {
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                },
                exc_info=True
            )
            raise
            
        finally:
            # Ensure proper cleanup
            if channel and not channel.is_closed:
                try:
                    channel.close()
                except Exception as e:
                    logger.warning(f"Error closing AMQP channel: {e}")
                    
            if connection and not connection.is_closed:
                try:
                    connection.close()
                except Exception as e:
                    logger.warning(f"Error closing AMQP connection: {e}")
    
    def setup_exchanges_and_queues(self, exchanges_config: Dict[str, Any]) -> bool:
        """
        Set up exchanges and queues based on configuration.
        
        Args:
            exchanges_config: Dictionary containing exchange and queue configuration
            
        Returns:
            bool: True if setup successful, False otherwise
        """
        with tracer.start_as_current_span("amqp.setup.exchanges_queues") as span:
            try:
                with self._get_connection() as channel:
                    for exchange_name, config in exchanges_config.items():
                        # Declare exchange
                        channel.exchange_declare(
                            exchange=exchange_name,
                            exchange_type=config.get('type', 'topic'),
                            durable=config.get('durable', True),
                            auto_delete=config.get('auto_delete', False)
                        )
                        
                        # Declare queues if specified
                        for queue_config in config.get('queues', []):
                            queue_name = queue_config['name']
                            routing_key = queue_config.get('routing_key', '#')
                            
                            channel.queue_declare(
                                queue=queue_name,
                                durable=queue_config.get('durable', True),
                                auto_delete=queue_config.get('auto_delete', False)
                            )
                            
                            channel.queue_bind(
                                exchange=exchange_name,
                                queue=queue_name,
                                routing_key=routing_key
                            )
                        
                        logger.info(
                            "AMQP exchange and queues set up successfully",
                            extra={
                                "extra_fields": {
                                    "exchange": exchange_name,
                                    "type": config.get('type', 'topic'),
                                    "queues_count": len(config.get('queues', []))
                                }
                            }
                        )
                
                span.set_status(Status(StatusCode.OK))
                return True
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                logger.error(
                    "Failed to set up AMQP exchanges and queues",
                    extra={
                        "extra_fields": {
                            "error": str(e),
                            "exchanges": list(exchanges_config.keys())
                        }
                    },
                    exc_info=True
                )
                return False
    
    def publish_notification(
        self,
        notification: Notification,
        endpoint: Endpoint,
        correlation_id: Optional[str] = None,
        trace_headers: Optional[Dict[str, str]] = None
    ) -> PublishResult:
        """
        Publish notification message to AMQP exchange.
        
        Args:
            notification: Notification to publish
            endpoint: Endpoint configuration for routing and transformation
            correlation_id: Optional correlation ID for message tracking
            trace_headers: Optional trace context headers
            
        Returns:
            PublishResult: Result of the publishing operation
        """
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
            
        with tracer.start_as_current_span("amqp.publish.notification") as span:
            span.set_attributes({
                "notification.id": notification.id,
                "notification.status": notification.status,
                "endpoint.name": endpoint.name,
                "amqp.correlation_id": correlation_id
            })
            
            try:
                # Transform payload based on endpoint configuration
                transformed_payload = self.transform_payload(notification, endpoint.data_mapping)
                
                # Prepare message
                message = {
                    "notification_id": notification.id,
                    "organization_id": notification.organization_id,
                    "correlation_id": correlation_id,
                    "timestamp": notification.created_at.isoformat(),
                    "payload": transformed_payload
                }
                
                # Add trace context if provided
                if trace_headers:
                    message["trace_context"] = trace_headers
                
                # Determine routing
                exchange = self._get_exchange_name(endpoint)
                routing_key = self._get_routing_key(notification, endpoint)
                
                span.set_attributes({
                    "amqp.exchange": exchange,
                    "amqp.routing_key": routing_key
                })
                
                # Publish with retry logic
                return self._publish_with_retry(
                    exchange=exchange,
                    routing_key=routing_key,
                    message=message,
                    correlation_id=correlation_id
                )
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                
                logger.error(
                    "Failed to publish notification",
                    extra={
                        "extra_fields": {
                            "notification_id": notification.id,
                            "endpoint_name": endpoint.name,
                            "correlation_id": correlation_id,
                            "error": str(e)
                        }
                    },
                    exc_info=True
                )
                
                return PublishResult(
                    success=False,
                    correlation_id=correlation_id,
                    exchange=self._get_exchange_name(endpoint),
                    routing_key=self._get_routing_key(notification, endpoint),
                    error=str(e)
                )
    
    def _publish_with_retry(
        self,
        exchange: str,
        routing_key: str,
        message: Dict[str, Any],
        correlation_id: str
    ) -> PublishResult:
        """Publish message with exponential backoff retry logic."""
        last_error = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                with self._get_connection() as channel:
                    # Prepare message properties
                    properties = pika.BasicProperties(
                        correlation_id=correlation_id,
                        timestamp=int(time.time()),
                        delivery_mode=2,  # Persistent message
                        content_type='application/json'
                    )
                    
                    # Publish message
                    channel.basic_publish(
                        exchange=exchange,
                        routing_key=routing_key,
                        body=json.dumps(message, default=str),
                        properties=properties,
                        mandatory=True  # Ensure message is routed
                    )
                    
                    logger.info(
                        "Message published successfully",
                        extra={
                            "extra_fields": {
                                "exchange": exchange,
                                "routing_key": routing_key,
                                "correlation_id": correlation_id,
                                "attempt": attempt + 1
                            }
                        }
                    )
                    
                    return PublishResult(
                        success=True,
                        correlation_id=correlation_id,
                        exchange=exchange,
                        routing_key=routing_key,
                        retry_count=attempt
                    )
                    
            except Exception as e:
                last_error = e
                
                if attempt < self.config.max_retries:
                    # Exponential backoff with jitter
                    delay = self.config.retry_delay * (2 ** attempt) + (time.time() % 1)
                    
                    logger.warning(
                        "Message publish failed, retrying",
                        extra={
                            "extra_fields": {
                                "exchange": exchange,
                                "routing_key": routing_key,
                                "correlation_id": correlation_id,
                                "attempt": attempt + 1,
                                "retry_delay": delay,
                                "error": str(e)
                            }
                        }
                    )
                    
                    time.sleep(delay)
                else:
                    logger.error(
                        "Message publish failed after all retries",
                        extra={
                            "extra_fields": {
                                "exchange": exchange,
                                "routing_key": routing_key,
                                "correlation_id": correlation_id,
                                "total_attempts": attempt + 1,
                                "error": str(e)
                            }
                        },
                        exc_info=True
                    )
        
        return PublishResult(
            success=False,
            correlation_id=correlation_id,
            exchange=exchange,
            routing_key=routing_key,
            error=str(last_error),
            retry_count=self.config.max_retries
        )
    
    def transform_payload(self, notification: Notification, data_mapping: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform notification payload based on endpoint data mapping configuration.
        
        This method will be implemented in the next subtask (6.3).
        For now, return the basic notification data.
        """
        return {
            "id": notification.id,
            "title": notification.title,
            "body": notification.body,
            "severity": notification.severity,
            "status": notification.status,
            "created_at": notification.created_at.isoformat(),
            "targets": notification.targets,
            "categories": notification.categories
        }
    
    def _get_exchange_name(self, endpoint: Endpoint) -> str:
        """Get exchange name for endpoint."""
        # Default exchange naming convention
        return f"notifications.{endpoint.organization_id}"
    
    def _get_routing_key(self, notification: Notification, endpoint: Endpoint) -> str:
        """Get routing key for notification and endpoint."""
        # Default routing key based on notification properties
        severity_level = "high" if notification.severity >= 4 else "medium" if notification.severity >= 2 else "low"
        return f"org.{notification.organization_id}.{notification.status}.{severity_level}"
    
    def health_check(self) -> bool:
        """
        Perform health check by attempting to connect to AMQP broker.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            with self._get_connection() as channel:
                # Simple operation to verify connection
                channel.queue_declare(queue='health_check', passive=True, auto_delete=True)
                return True
        except Exception as e:
            logger.warning(
                "AMQP health check failed",
                extra={
                    "extra_fields": {
                        "error": str(e),
                        "host": self._connection_params.host
                    }
                }
            )
            return False


def create_amqp_service() -> AMQPService:
    """
    Factory function to create AMQP service with configuration from environment.
    
    Returns:
        AMQPService: Configured AMQP service instance
    """
    amqp_url = os.getenv('AMQP_URL', 'amqp://guest:guest@localhost:5672/')
    
    config = AMQPConfig(
        url=amqp_url,
        connection_timeout=int(os.getenv('AMQP_CONNECTION_TIMEOUT', '30')),
        heartbeat=int(os.getenv('AMQP_HEARTBEAT', '600')),
        blocked_connection_timeout=int(os.getenv('AMQP_BLOCKED_TIMEOUT', '300')),
        retry_delay=float(os.getenv('AMQP_RETRY_DELAY', '1.0')),
        max_retries=int(os.getenv('AMQP_MAX_RETRIES', '3'))
    )
    
    return AMQPService(config)