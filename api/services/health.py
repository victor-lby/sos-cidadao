"""
Health Check Service

Provides comprehensive health monitoring for all system dependencies
including MongoDB, Redis, AMQP, and system metrics.
"""

import os
import time
import psutil
from datetime import datetime
from typing import Dict, Any, Optional
from opentelemetry import trace

from services.mongodb import MongoDBService
from services.redis import RedisService
from services.amqp import AMQPService

tracer = trace.get_tracer(__name__)


class HealthCheckService:
    """Service for comprehensive system health monitoring."""
    
    def __init__(self, mongodb_service: MongoDBService, redis_service: RedisService, amqp_service: AMQPService):
        self.mongodb_service = mongodb_service
        self.redis_service = redis_service
        self.amqp_service = amqp_service
        self.service_version = "1.0.0"
    
    def get_comprehensive_health(self) -> Dict[str, Any]:
        """Get comprehensive health status including all dependencies and metrics."""
        with tracer.start_as_current_span("health.comprehensive_check") as span:
            start_time = time.time()
            
            # Check all dependencies
            mongodb_health = self._check_mongodb_health()
            redis_health = self._check_redis_health()
            amqp_health = self._check_amqp_health()
            
            # Get system metrics
            system_metrics = self._get_system_metrics()
            
            # Determine overall status
            overall_status = self._determine_overall_status([
                mongodb_health["status"],
                redis_health["status"],
                amqp_health["status"]
            ])
            
            # Calculate response time
            response_time_ms = round((time.time() - start_time) * 1000, 2)
            
            health_data = {
                "status": overall_status,
                "service": "sos-cidadao-api",
                "version": self.service_version,
                "environment": os.getenv('ENVIRONMENT', 'development'),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "response_time_ms": response_time_ms,
                "dependencies": {
                    "mongodb": mongodb_health,
                    "redis": redis_health,
                    "amqp": amqp_health
                },
                "system_metrics": system_metrics,
                "feature_flags": self._get_feature_flags(),
                "configuration": self._get_configuration_status()
            }
            
            # Add span attributes
            span.set_attributes({
                "health.overall_status": overall_status,
                "health.response_time_ms": response_time_ms,
                "health.mongodb_status": mongodb_health["status"],
                "health.redis_status": redis_health["status"],
                "health.amqp_status": amqp_health["status"]
            })
            
            return health_data
    
    def _check_mongodb_health(self) -> Dict[str, Any]:
        """Check MongoDB connectivity and performance."""
        with tracer.start_as_current_span("health.mongodb_check") as span:
            try:
                start_time = time.time()
                
                # Test basic connectivity
                self.mongodb_service.client.admin.command('ping')
                
                # Test database operations
                test_collection = self.mongodb_service.db.health_check
                test_doc = {"timestamp": datetime.utcnow(), "test": True}
                result = test_collection.insert_one(test_doc)
                test_collection.delete_one({"_id": result.inserted_id})
                
                response_time = round((time.time() - start_time) * 1000, 2)
                
                # Get server info
                server_info = self.mongodb_service.client.server_info()
                
                health_info = {
                    "status": "healthy",
                    "response_time_ms": response_time,
                    "version": server_info.get("version", "unknown"),
                    "connection_count": self._get_mongodb_connection_count(),
                    "last_check": datetime.utcnow().isoformat() + "Z"
                }
                
                span.set_attributes({
                    "mongodb.status": "healthy",
                    "mongodb.response_time_ms": response_time,
                    "mongodb.version": server_info.get("version", "unknown")
                })
                
                return health_info
                
            except Exception as e:
                span.set_attribute("mongodb.status", "unhealthy")
                span.record_exception(e)
                
                return {
                    "status": "unhealthy",
                    "error": str(e),
                    "last_check": datetime.utcnow().isoformat() + "Z"
                }
    
    def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance."""
        with tracer.start_as_current_span("health.redis_check") as span:
            try:
                start_time = time.time()
                
                # Test basic connectivity with ping
                ping_result = self.redis_service.ping()
                if not ping_result:
                    raise Exception("Redis ping failed")
                
                # Test set/get operations
                test_key = "health_check_test"
                test_value = f"test_{int(time.time())}"
                
                self.redis_service.set_with_ttl(test_key, test_value, 10)
                retrieved_value = self.redis_service.get(test_key)
                self.redis_service.delete(test_key)
                
                if retrieved_value != test_value:
                    raise Exception("Redis set/get test failed")
                
                response_time = round((time.time() - start_time) * 1000, 2)
                
                # Get Redis info
                redis_info = self.redis_service.get_info()
                
                health_info = {
                    "status": "healthy",
                    "response_time_ms": response_time,
                    "version": redis_info.get("redis_version", "unknown"),
                    "memory_usage_mb": round(redis_info.get("used_memory", 0) / 1024 / 1024, 2),
                    "connected_clients": redis_info.get("connected_clients", 0),
                    "last_check": datetime.utcnow().isoformat() + "Z"
                }
                
                span.set_attributes({
                    "redis.status": "healthy",
                    "redis.response_time_ms": response_time,
                    "redis.memory_usage_mb": health_info["memory_usage_mb"]
                })
                
                return health_info
                
            except Exception as e:
                span.set_attribute("redis.status", "unhealthy")
                span.record_exception(e)
                
                return {
                    "status": "unhealthy",
                    "error": str(e),
                    "last_check": datetime.utcnow().isoformat() + "Z"
                }
    
    def _check_amqp_health(self) -> Dict[str, Any]:
        """Check AMQP/LavinMQ connectivity and performance."""
        with tracer.start_as_current_span("health.amqp_check") as span:
            try:
                start_time = time.time()
                
                # Use the existing health check method
                is_healthy = self.amqp_service.health_check()
                
                if not is_healthy:
                    raise Exception("AMQP health check failed")
                
                response_time = round((time.time() - start_time) * 1000, 2)
                
                health_info = {
                    "status": "healthy",
                    "response_time_ms": response_time,
                    "broker": "LavinMQ",
                    "last_check": datetime.utcnow().isoformat() + "Z"
                }
                
                span.set_attributes({
                    "amqp.status": "healthy",
                    "amqp.response_time_ms": response_time
                })
                
                return health_info
                
            except Exception as e:
                span.set_attribute("amqp.status", "unhealthy")
                span.record_exception(e)
                
                return {
                    "status": "unhealthy",
                    "error": str(e),
                    "last_check": datetime.utcnow().isoformat() + "Z"
                }
    
    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get basic system performance metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage_mb = round(memory.used / 1024 / 1024, 2)
            memory_total_mb = round(memory.total / 1024 / 1024, 2)
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage_gb = round(disk.used / 1024 / 1024 / 1024, 2)
            disk_total_gb = round(disk.total / 1024 / 1024 / 1024, 2)
            disk_percent = round((disk.used / disk.total) * 100, 2)
            
            return {
                "cpu_percent": cpu_percent,
                "memory": {
                    "used_mb": memory_usage_mb,
                    "total_mb": memory_total_mb,
                    "percent": memory_percent
                },
                "disk": {
                    "used_gb": disk_usage_gb,
                    "total_gb": disk_total_gb,
                    "percent": disk_percent
                },
                "load_average": list(os.getloadavg()) if hasattr(os, 'getloadavg') else None
            }
        except Exception as e:
            return {
                "error": f"Failed to collect system metrics: {str(e)}"
            }
    
    def _get_feature_flags(self) -> Dict[str, bool]:
        """Get current feature flag status."""
        return {
            "docs_enabled": os.getenv('DOCS_ENABLED', 'true').lower() == 'true',
            "otel_enabled": os.getenv('OTEL_ENABLED', 'true').lower() == 'true',
            "hal_strict": os.getenv('HAL_STRICT', 'false').lower() == 'true'
        }
    
    def _get_configuration_status(self) -> Dict[str, Any]:
        """Get configuration validation status."""
        config_status = {
            "mongodb_uri_configured": bool(os.getenv('MONGODB_URI')),
            "redis_configured": bool(os.getenv('REDIS_URL')),
            "amqp_configured": bool(os.getenv('AMQP_URL')),
            "jwt_secret_configured": bool(os.getenv('JWT_SECRET')),
            "environment": os.getenv('ENVIRONMENT', 'development')
        }
        
        # Check if all critical configurations are present
        critical_configs = ['mongodb_uri_configured', 'redis_configured', 'amqp_configured']
        config_status["all_critical_configured"] = all(
            config_status[config] for config in critical_configs
        )
        
        return config_status
    
    def _get_mongodb_connection_count(self) -> int:
        """Get current MongoDB connection count."""
        try:
            server_status = self.mongodb_service.client.admin.command('serverStatus')
            return server_status.get('connections', {}).get('current', 0)
        except Exception:
            return 0
    
    def _determine_overall_status(self, dependency_statuses: list) -> str:
        """Determine overall system status based on dependency health."""
        if all(status == "healthy" for status in dependency_statuses):
            return "healthy"
        elif any(status == "healthy" for status in dependency_statuses):
            return "degraded"
        else:
            return "unhealthy"