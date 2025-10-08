# SPDX-License-Identifier: Apache-2.0

"""
Integration tests for AMQP service and message publishing.

This module tests the AMQP service functionality including:
- Message publishing with various payload transformations
- Retry logic and error handling scenarios
- Correlation ID and trace context propagation
- Connection management and recovery
"""

import pytest
import json
import time
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from services.amqp import (
    AMQPService, AMQPConfig, PublishResult, PayloadTransformer,
    PayloadTransformationError, AMQPConnectionError, AMQPPublishError
)
from models.entities import Notification, Endpoint, NotificationStatus, NotificationSeverity


class TestPayloadTransformer:
    """Test payload transformation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.transformer = PayloadTransformer()
        
        self.sample_notification_data = {
            "id": "test-notification-123",
            "title": "Test Emergency Alert",
            "body": "This is a test emergency notification",
            "severity": 4,
            "status": "approved",
            "created_at": datetime(2024, 1, 15, 10, 30, 0),
            "organization_id": "org-123",
            "targets": ["target-1", "target-2"],
            "categories": ["emergency", "weather"],
            "original_payload": {"source": "weather-service"},
            "created_by": "user-123"
        }
    
    def test_basic_field_mapping(self):
        """Test basic field mapping with JSONPath."""
        mapping_config = {
            "mappings": [
                {"source": "title", "target": "alert.title"},
                {"source": "body", "target": "alert.message"},
                {"source": "severity", "target": "alert.level"}
            ]
        }
        
        result = self.transformer.transform(self.sample_notification_data, mapping_config)
        
        assert result["alert"]["title"] == "Test Emergency Alert"
        assert result["alert"]["message"] == "This is a test emergency notification"
        assert result["alert"]["level"] == 4
    
    def test_transformation_functions(self):
        """Test built-in transformation functions."""
        mapping_config = {
            "mappings": [
                {"source": "title", "target": "title_upper", "transform": "uppercase"},
                {"source": "severity", "target": "severity_text", "transform": "severity_text"},
                {"source": "status", "target": "status_text", "transform": "status_text"},
                {"source": "created_at", "target": "created_iso", "transform": "format_date"}
            ]
        }
        
        result = self.transformer.transform(self.sample_notification_data, mapping_config)
        
        assert result["title_upper"] == "TEST EMERGENCY ALERT"
        assert result["severity_text"] == "critical"
        assert result["status_text"] == "Approved"
        assert result["created_iso"] == "2024-01-15T10:30:00"
    
    def test_default_values(self):
        """Test default values for missing fields."""
        mapping_config = {
            "mappings": [
                {"source": "nonexistent_field", "target": "with_default", "default": "default_value"},
                {"source": "another_missing", "target": "no_default"}
            ]
        }
        
        result = self.transformer.transform(self.sample_notification_data, mapping_config)
        
        assert result["with_default"] == "default_value"
        assert result["no_default"] is None
    
    def test_nested_object_creation(self):
        """Test creation of nested objects."""
        mapping_config = {
            "mappings": [
                {"source": "title", "target": "notification.header.title"},
                {"source": "body", "target": "notification.content.message"},
                {"source": "severity", "target": "metadata.priority.level"}
            ]
        }
        
        result = self.transformer.transform(self.sample_notification_data, mapping_config)
        
        assert result["notification"]["header"]["title"] == "Test Emergency Alert"
        assert result["notification"]["content"]["message"] == "This is a test emergency notification"
        assert result["metadata"]["priority"]["level"] == 4
    
    def test_static_fields(self):
        """Test addition of static fields."""
        mapping_config = {
            "mappings": [
                {"source": "title", "target": "title"}
            ],
            "static_fields": {
                "source": "sos-cidadao",
                "version": "1.0",
                "type": "emergency_alert"
            }
        }
        
        result = self.transformer.transform(self.sample_notification_data, mapping_config)
        
        assert result["title"] == "Test Emergency Alert"
        assert result["source"] == "sos-cidadao"
        assert result["version"] == "1.0"
        assert result["type"] == "emergency_alert"
    
    def test_global_transforms(self):
        """Test global transformations."""
        mapping_config = {
            "mappings": [
                {"source": "title", "target": "title"}
            ],
            "global_transforms": {
                "add_timestamp": True,
                "add_message_id": True,
                "envelope": "payload"
            }
        }
        
        result = self.transformer.transform(self.sample_notification_data, mapping_config)
        
        assert "payload" in result
        assert result["payload"]["title"] == "Test Emergency Alert"
        assert "timestamp" in result["payload"]
        assert "message_id" in result["payload"]
        assert isinstance(result["payload"]["timestamp"], float)
    
    def test_jsonpath_expressions(self):
        """Test complex JSONPath expressions."""
        complex_data = {
            "notification": {
                "details": {
                    "title": "Complex Title",
                    "metadata": {
                        "tags": ["urgent", "weather"]
                    }
                }
            },
            "targets": [
                {"id": "target-1", "name": "Region A"},
                {"id": "target-2", "name": "Region B"}
            ]
        }
        
        mapping_config = {
            "mappings": [
                {"source": "notification.details.title", "target": "title"},
                {"source": "notification.details.metadata.tags[0]", "target": "primary_tag"},
                {"source": "targets[0].name", "target": "first_target_name"}
            ]
        }
        
        result = self.transformer.transform(complex_data, mapping_config)
        
        assert result["title"] == "Complex Title"
        assert result["primary_tag"] == "urgent"
        assert result["first_target_name"] == "Region A"
    
    def test_transformation_error_handling(self):
        """Test error handling in transformation."""
        invalid_mapping = {
            "mappings": [
                {"source": "title", "target": "title", "transform": "nonexistent_function"}
            ]
        }
        
        # Should not raise exception, just skip the transform
        result = self.transformer.transform(self.sample_notification_data, invalid_mapping)
        assert result["title"] == "Test Emergency Alert"  # Original value


class TestAMQPService:
    """Test AMQP service functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = AMQPConfig(
            url="amqp://test:test@localhost:5672/",
            connection_timeout=5,
            heartbeat=60,
            retry_delay=0.1,
            max_retries=2
        )
        
        self.notification = Notification(
            id="test-notification-123",
            organization_id="org-123",
            title="Test Alert",
            body="Test message",
            severity=NotificationSeverity.HIGH,
            status=NotificationStatus.APPROVED,
            origin="test-system",
            target_ids=["target-1"],
            category_ids=["emergency"],
            original_payload={"test": "data"},
            correlation_id=str(uuid.uuid4()),
            approved_at=datetime.now(timezone.utc),
            approved_by="user-123",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="user-123",
            updated_by="user-123"
        )
        
        self.endpoint = Endpoint(
            id="endpoint-123",
            organization_id="org-123",
            name="Test Endpoint",
            url="https://api.example.com/webhook",
            data_mapping={
                "mappings": [
                    {"source": "title", "target": "alert_title"},
                    {"source": "body", "target": "alert_message"}
                ]
            },
            category_ids=["emergency"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="user-123",
            updated_by="user-123"
        )
    
    @patch('services.amqp.pika.BlockingConnection')
    def test_successful_message_publishing(self, mock_connection):
        """Test successful message publishing."""
        # Mock AMQP connection and channel
        mock_channel = Mock()
        mock_conn = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn
        
        service = AMQPService(self.config)
        
        test_correlation_id = str(uuid.uuid4())
        result = service.publish_notification(
            self.notification,
            self.endpoint,
            correlation_id=test_correlation_id
        )
        
        assert result.success is True
        assert result.correlation_id == test_correlation_id
        assert mock_channel.basic_publish.called
        
        # Verify message content
        call_args = mock_channel.basic_publish.call_args
        message_body = call_args[1]['body']
        message_data = json.loads(message_body)
        
        assert message_data['notification_id'] == "test-notification-123"
        assert message_data['organization_id'] == "org-123"
        assert message_data['correlation_id'] == test_correlation_id
        assert 'payload' in message_data
        assert 'trace_context' in message_data
    
    @patch('services.amqp.pika.BlockingConnection')
    def test_payload_transformation(self, mock_connection):
        """Test payload transformation during publishing."""
        # Mock AMQP connection
        mock_channel = Mock()
        mock_conn = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn
        
        service = AMQPService(self.config)
        
        result = service.publish_notification(
            self.notification,
            self.endpoint
        )
        
        assert result.success is True
        
        # Verify transformed payload
        call_args = mock_channel.basic_publish.call_args
        message_body = call_args[1]['body']
        message_data = json.loads(message_body)
        
        payload = message_data['payload']
        assert payload['alert_title'] == "Test Alert"
        assert payload['alert_message'] == "Test message"
    
    @patch('services.amqp.pika.BlockingConnection')
    def test_connection_failure_handling(self, mock_connection):
        """Test handling of connection failures."""
        # Mock connection failure
        mock_connection.side_effect = Exception("Connection failed")
        
        service = AMQPService(self.config)
        
        result = service.publish_notification(
            self.notification,
            self.endpoint
        )
        
        assert result.success is False
        assert "Connection failed" in result.error
    
    @patch('services.amqp.pika.BlockingConnection')
    def test_retry_logic_with_exponential_backoff(self, mock_connection):
        """Test retry logic with exponential backoff."""
        # Mock connection that fails first two times, succeeds on third
        mock_channel = Mock()
        mock_conn = Mock()
        mock_conn.channel.return_value = mock_channel
        
        call_count = 0
        def connection_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception(f"Connection failed attempt {call_count}")
            return mock_conn
        
        mock_connection.side_effect = connection_side_effect
        
        service = AMQPService(self.config)
        
        start_time = time.time()
        result = service.publish_notification(
            self.notification,
            self.endpoint
        )
        end_time = time.time()
        
        assert result.success is True
        assert result.retry_count == 2  # Two retries before success
        
        # Verify exponential backoff timing (should take at least 0.1 + 0.2 = 0.3 seconds)
        assert end_time - start_time >= 0.3
    
    @patch('services.amqp.pika.BlockingConnection')
    def test_message_validation(self, mock_connection):
        """Test message validation before publishing."""
        mock_channel = Mock()
        mock_conn = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn
        
        service = AMQPService(self.config)
        
        # Test with invalid correlation ID
        result = service.publish_notification(
            self.notification,
            self.endpoint,
            correlation_id="invalid-correlation-id"  # Not a valid UUID
        )
        
        # Should fail validation
        assert result.success is False
        assert "validation failed" in result.error.lower()
    
    @patch('services.amqp.pika.BlockingConnection')
    def test_trace_context_propagation(self, mock_connection):
        """Test OpenTelemetry trace context propagation."""
        mock_channel = Mock()
        mock_conn = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn
        
        service = AMQPService(self.config)
        
        # Mock trace context
        trace_headers = {
            "traceparent": "00-12345678901234567890123456789012-1234567890123456-01",
            "tracestate": "test=value"
        }
        
        result = service.publish_notification(
            self.notification,
            self.endpoint,
            trace_headers=trace_headers
        )
        
        assert result.success is True
        
        # Verify trace context in message
        call_args = mock_channel.basic_publish.call_args
        message_body = call_args[1]['body']
        message_data = json.loads(message_body)
        
        assert 'trace_context' in message_data
        trace_context = message_data['trace_context']
        assert 'traceparent' in trace_context or 'tracestate' in trace_context
    
    @patch('services.amqp.pika.BlockingConnection')
    def test_correlation_id_generation(self, mock_connection):
        """Test automatic correlation ID generation."""
        mock_channel = Mock()
        mock_conn = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn
        
        service = AMQPService(self.config)
        
        # Publish without correlation ID
        result = service.publish_notification(
            self.notification,
            self.endpoint
        )
        
        assert result.success is True
        assert result.correlation_id is not None
        assert len(result.correlation_id) > 0
        
        # Verify correlation ID is a valid UUID
        try:
            uuid.UUID(result.correlation_id)
        except ValueError:
            pytest.fail("Generated correlation ID is not a valid UUID")
    
    @patch('services.amqp.pika.BlockingConnection')
    def test_exchange_and_routing_key_generation(self, mock_connection):
        """Test exchange and routing key generation."""
        mock_channel = Mock()
        mock_conn = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn
        
        service = AMQPService(self.config)
        
        result = service.publish_notification(
            self.notification,
            self.endpoint
        )
        
        assert result.success is True
        
        # Verify exchange and routing key
        call_args = mock_channel.basic_publish.call_args
        exchange = call_args[1]['exchange']
        routing_key = call_args[1]['routing_key']
        
        assert exchange == f"notifications.{self.notification.organization_id}"
        assert self.notification.organization_id in routing_key
        assert self.notification.status in routing_key
    
    def test_health_check_success(self):
        """Test successful health check."""
        with patch('services.amqp.pika.BlockingConnection') as mock_connection:
            mock_channel = Mock()
            mock_conn = Mock()
            mock_conn.channel.return_value = mock_channel
            mock_connection.return_value = mock_conn
            
            service = AMQPService(self.config)
            
            result = service.health_check()
            
            assert result is True
            assert mock_connection.called
    
    def test_health_check_failure(self):
        """Test health check failure."""
        with patch('services.amqp.pika.BlockingConnection') as mock_connection:
            mock_connection.side_effect = Exception("Connection failed")
            
            service = AMQPService(self.config)
            
            result = service.health_check()
            
            assert result is False
    
    def test_default_payload_format(self):
        """Test default payload format when no mapping is provided."""
        service = AMQPService(self.config)
        
        # Test with empty data mapping
        result = service.transform_payload(self.notification, {})
        
        assert 'notification' in result
        assert 'metadata' in result
        assert result['notification']['id'] == self.notification.id
        assert result['notification']['title'] == self.notification.title
        assert result['notification']['severity_text'] == "high"
        assert result['metadata']['source'] == "sos-cidadao"


class TestAMQPIntegration:
    """Integration tests for AMQP with notification workflow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.notification_data = {
            "id": "test-notification-123",
            "organization_id": "org-123",
            "title": "Integration Test Alert",
            "body": "This is an integration test",
            "severity": 4,
            "status": "approved",
            "origin": "test-system",
            "target_ids": ["target-1", "target-2"],
            "category_ids": ["emergency", "weather"],
            "original_payload": {"source": "integration-test"},
            "correlation_id": str(uuid.uuid4()),
            "approved_at": datetime.now(timezone.utc),
            "approved_by": "test-user",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "created_by": "test-user",
            "updated_by": "test-user"
        }
        
        self.endpoint_data = {
            "id": "endpoint-123",
            "organization_id": "org-123",
            "name": "Integration Test Endpoint",
            "url": "https://webhook.example.com/alerts",
            "data_mapping": {
                "mappings": [
                    {"source": "title", "target": "alert.title"},
                    {"source": "body", "target": "alert.message"},
                    {"source": "severity", "target": "alert.priority", "transform": "severity_text"}
                ],
                "static_fields": {
                    "source": "sos-cidadao",
                    "version": "1.0"
                }
            },
            "category_ids": ["emergency"],
            "headers": {"Authorization": "Bearer test-token"},
            "timeout_seconds": 30,
            "retry_attempts": 3,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "created_by": "test-user",
            "updated_by": "test-user"
        }
    
    @patch('services.amqp.pika.BlockingConnection')
    def test_end_to_end_notification_publishing(self, mock_connection):
        """Test complete end-to-end notification publishing flow."""
        # Mock AMQP connection
        mock_channel = Mock()
        mock_conn = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn
        
        # Create entities
        notification = Notification(**self.notification_data)
        endpoint = Endpoint(**self.endpoint_data)
        
        # Create service and publish
        service = AMQPService(AMQPConfig(url="amqp://test:test@localhost:5672/"))
        
        e2e_correlation_id = str(uuid.uuid4())
        result = service.publish_notification(
            notification=notification,
            endpoint=endpoint,
            correlation_id=e2e_correlation_id
        )
        
        # Verify success
        assert result.success is True
        assert result.correlation_id == e2e_correlation_id
        
        # Verify message was published
        assert mock_channel.basic_publish.called
        
        # Verify message content
        call_args = mock_channel.basic_publish.call_args
        message_body = call_args[1]['body']
        message_data = json.loads(message_body)
        
        # Check message structure
        assert message_data['notification_id'] == notification.id
        assert message_data['organization_id'] == notification.organization_id
        assert message_data['correlation_id'] == e2e_correlation_id
        
        # Check transformed payload
        payload = message_data['payload']
        assert payload['alert']['title'] == "Integration Test Alert"
        assert payload['alert']['message'] == "This is an integration test"
        assert payload['alert']['priority'] == "critical"
        assert payload['source'] == "sos-cidadao"
        assert payload['version'] == "1.0"
        
        # Check trace context
        assert 'trace_context' in message_data
    
    @patch('services.amqp.pika.BlockingConnection')
    def test_multiple_endpoint_publishing(self, mock_connection):
        """Test publishing to multiple endpoints."""
        # Mock AMQP connection
        mock_channel = Mock()
        mock_conn = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn
        
        # Create notification
        notification = Notification(**self.notification_data)
        
        # Create multiple endpoints with different mappings
        endpoint1_data = self.endpoint_data.copy()
        endpoint1_data['id'] = 'endpoint-1'
        endpoint1_data['name'] = 'Endpoint 1'
        
        endpoint2_data = self.endpoint_data.copy()
        endpoint2_data['id'] = 'endpoint-2'
        endpoint2_data['name'] = 'Endpoint 2'
        endpoint2_data['data_mapping'] = {
            "mappings": [
                {"source": "title", "target": "message_title"},
                {"source": "body", "target": "message_body"}
            ]
        }
        
        endpoint1 = Endpoint(**endpoint1_data)
        endpoint2 = Endpoint(**endpoint2_data)
        
        service = AMQPService(AMQPConfig(url="amqp://test:test@localhost:5672/"))
        
        # Publish to both endpoints
        result1 = service.publish_notification(notification, endpoint1)
        result2 = service.publish_notification(notification, endpoint2)
        
        # Verify both succeeded
        assert result1.success is True
        assert result2.success is True
        
        # Verify both messages were published
        assert mock_channel.basic_publish.call_count == 2
    
    def test_amqp_service_factory(self):
        """Test AMQP service factory function."""
        from services.amqp import create_amqp_service
        
        with patch.dict('os.environ', {
            'AMQP_URL': 'amqp://factory-test:test@localhost:5672/',
            'AMQP_CONNECTION_TIMEOUT': '10',
            'AMQP_HEARTBEAT': '300',
            'AMQP_MAX_RETRIES': '5'
        }):
            service = create_amqp_service()
            
            assert isinstance(service, AMQPService)
            assert service.config.url == 'amqp://factory-test:test@localhost:5672/'
            assert service.config.connection_timeout == 10
            assert service.config.heartbeat == 300
            assert service.config.max_retries == 5


if __name__ == '__main__':
    pytest.main([__file__])