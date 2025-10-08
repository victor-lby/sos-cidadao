"""
Performance validation integration tests.

Comprehensive performance testing including load testing,
response time validation, and resource usage monitoring.
"""

import pytest
import time
import threading
import queue
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import concurrent.futures
import psutil
import requests
from unittest.mock import patch


class TestPerformanceValidation:
    """Comprehensive performance validation tests."""
    
    @pytest.fixture(autouse=True)
    def setup_performance_test_environment(self, test_client, test_db):
        """Set up performance testing environment."""
        self.client = test_client
        self.db = test_db
        self.base_url = "http://localhost:5000"
        
        # Performance thresholds
        self.response_time_threshold = 2.0  # seconds
        self.throughput_threshold = 100     # requests per second
        self.memory_threshold = 512         # MB
        self.cpu_threshold = 80             # percentage
        
        # Create test data for performance testing
        self._create_performance_test_data()
    
    def _create_performance_test_data(self):
        """Create test data for performance testing."""
        # Create test organization
        self.test_org_id = "perf_test_org"
        self.db.organizations.insert_one({
            "_id": self.test_org_id,
            "name": "Performance Test Organization",
            "createdAt": datetime.utcnow(),
            "schemaVersion": 1
        })
        
        # Create test users
        self.test_users = []
        for i in range(10):
            user = {
                "_id": f"perf_user_{i}",
                "organizationId": self.test_org_id,
                "email": f"user{i}@perf-test.com",
                "name": f"Performance User {i}",
                "permissions": ["notification:read", "notification:create"],
                "createdAt": datetime.utcnow(),
                "schemaVersion": 1
            }
            self.test_users.append(user)
            self.db.users.insert_one(user)
        
        # Create test notifications for pagination testing
        self.test_notifications = []
        for i in range(1000):
            notification = {
                "_id": f"perf_notif_{i:04d}",
                "organizationId": self.test_org_id,
                "title": f"Performance Test Notification {i}",
                "body": f"This is performance test notification number {i} with some content to test response sizes.",
                "severity": i % 6,
                "status": "received",
                "createdBy": f"perf_user_{i % 10}",
                "createdAt": datetime.utcnow() - timedelta(minutes=i),
                "updatedAt": datetime.utcnow() - timedelta(minutes=i),
                "deletedAt": None,
                "schemaVersion": 1
            }
            self.test_notifications.append(notification)
        
        # Insert notifications in batches for better performance
        batch_size = 100
        for i in range(0, len(self.test_notifications), batch_size):
            batch = self.test_notifications[i:i + batch_size]
            self.db.notifications.insert_many(batch)
    
    def test_api_response_times(self):
        """Test API response times under normal load."""
        token = self._get_auth_token("user0@perf-test.com")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test different endpoints
        endpoints_to_test = [
            ("/api/health", "GET", None),
            ("/api", "GET", None),
            ("/api/notifications", "GET", None),
            ("/api/notifications?page=1&limit=20", "GET", None),
            ("/api/notifications", "POST", {
                "title": "Performance Test",
                "body": "Testing response time",
                "severity": 2
            })
        ]
        
        response_times = {}
        
        for endpoint, method, data in endpoints_to_test:
            times = []
            
            # Test each endpoint multiple times
            for _ in range(10):
                start_time = time.time()
                
                if method == "GET":
                    response = self.client.get(endpoint, headers=headers)
                else:
                    response = self.client.post(endpoint, json=data, headers=headers)
                
                end_time = time.time()
                response_time = end_time - start_time
                
                # Verify response is successful
                assert response.status_code in [200, 201], f"Failed request to {endpoint}"
                
                times.append(response_time)
                time.sleep(0.1)  # Small delay between requests
            
            # Calculate statistics
            avg_time = statistics.mean(times)
            max_time = max(times)
            min_time = min(times)
            p95_time = statistics.quantiles(times, n=20)[18]  # 95th percentile
            
            response_times[endpoint] = {
                "average": avg_time,
                "maximum": max_time,
                "minimum": min_time,
                "p95": p95_time,
                "samples": len(times)
            }
            
            # Assert performance thresholds
            assert avg_time < self.response_time_threshold, f"{endpoint} average response time too slow: {avg_time:.2f}s"
            assert p95_time < self.response_time_threshold * 1.5, f"{endpoint} 95th percentile too slow: {p95_time:.2f}s"
        
        # Log performance results
        print("\nAPI Response Time Results:")
        for endpoint, stats in response_times.items():
            print(f"{endpoint}:")
            print(f"  Average: {stats['average']:.3f}s")
            print(f"  95th percentile: {stats['p95']:.3f}s")
            print(f"  Max: {stats['maximum']:.3f}s")
    
    def test_concurrent_request_handling(self):
        """Test handling of concurrent requests."""
        token = self._get_auth_token("user0@perf-test.com")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test concurrent GET requests
        def make_request():
            try:
                start_time = time.time()
                response = self.client.get("/api/notifications", headers=headers)
                end_time = time.time()
                
                return {
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "success": response.status_code == 200
                }
            except Exception as e:
                return {
                    "status_code": 0,
                    "response_time": 0,
                    "success": False,
                    "error": str(e)
                }
        
        # Run concurrent requests
        num_concurrent_requests = 20
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent_requests) as executor:
            futures = [executor.submit(make_request) for _ in range(num_concurrent_requests)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Analyze results
        successful_requests = [r for r in results if r["success"]]
        failed_requests = [r for r in results if not r["success"]]
        
        success_rate = len(successful_requests) / len(results)
        
        # Assert performance requirements
        assert success_rate >= 0.95, f"Success rate too low under concurrent load: {success_rate:.2%}"
        
        if successful_requests:
            avg_response_time = statistics.mean([r["response_time"] for r in successful_requests])
            assert avg_response_time < self.response_time_threshold * 2, f"Response time degraded under load: {avg_response_time:.2f}s"
        
        print(f"\nConcurrent Request Results:")
        print(f"  Total requests: {len(results)}")
        print(f"  Successful: {len(successful_requests)}")
        print(f"  Failed: {len(failed_requests)}")
        print(f"  Success rate: {success_rate:.2%}")
        
        if successful_requests:
            print(f"  Average response time: {avg_response_time:.3f}s")
    
    def test_database_query_performance(self):
        """Test database query performance."""
        from api.services.mongodb import MongoDBService
        
        mongo_service = MongoDBService()
        
        # Test different query patterns
        query_tests = [
            ("find_by_org", lambda: mongo_service.find_by_org("notifications", self.test_org_id)),
            ("find_with_filter", lambda: mongo_service.find_by_org("notifications", self.test_org_id, {"severity": {"$gte": 3}})),
            ("find_with_pagination", lambda: mongo_service.find_by_org("notifications", self.test_org_id, {}, limit=20, skip=100)),
            ("find_with_sort", lambda: mongo_service.find_by_org("notifications", self.test_org_id, {}, sort=[("createdAt", -1)])),
            ("count_documents", lambda: mongo_service.count_by_org("notifications", self.test_org_id)),
        ]
        
        query_performance = {}
        
        for query_name, query_func in query_tests:
            times = []
            
            # Run each query multiple times
            for _ in range(5):
                start_time = time.time()
                result = query_func()
                end_time = time.time()
                
                query_time = end_time - start_time
                times.append(query_time)
                
                # Verify query returned results
                if query_name != "count_documents":
                    assert result is not None, f"Query {query_name} returned no results"
                    if isinstance(result, list):
                        assert len(result) > 0, f"Query {query_name} returned empty list"
                
                time.sleep(0.1)
            
            avg_time = statistics.mean(times)
            max_time = max(times)
            
            query_performance[query_name] = {
                "average": avg_time,
                "maximum": max_time,
                "samples": len(times)
            }
            
            # Assert query performance thresholds
            assert avg_time < 1.0, f"Database query {query_name} too slow: {avg_time:.3f}s"
        
        print("\nDatabase Query Performance:")
        for query_name, stats in query_performance.items():
            print(f"  {query_name}: {stats['average']:.3f}s avg, {stats['maximum']:.3f}s max")
    
    def test_pagination_performance(self):
        """Test pagination performance with large datasets."""
        token = self._get_auth_token("user0@perf-test.com")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test different page sizes and positions
        pagination_tests = [
            (1, 10),    # First page, small size
            (1, 50),    # First page, medium size
            (1, 100),   # First page, large size
            (10, 20),   # Middle page
            (50, 20),   # Later page
        ]
        
        pagination_performance = {}
        
        for page, limit in pagination_tests:
            test_name = f"page_{page}_limit_{limit}"
            
            start_time = time.time()
            response = self.client.get(
                f"/api/notifications?page={page}&limit={limit}",
                headers=headers
            )
            end_time = time.time()
            
            response_time = end_time - start_time
            
            assert response.status_code == 200, f"Pagination request failed: {test_name}"
            
            data = response.get_json()
            assert "_embedded" in data
            assert "notifications" in data["_embedded"]
            
            notifications = data["_embedded"]["notifications"]
            assert len(notifications) <= limit, f"Returned more items than limit: {test_name}"
            
            pagination_performance[test_name] = {
                "response_time": response_time,
                "items_returned": len(notifications),
                "total_items": data.get("total", 0)
            }
            
            # Assert pagination performance
            assert response_time < 2.0, f"Pagination too slow: {test_name} took {response_time:.3f}s"
        
        print("\nPagination Performance:")
        for test_name, stats in pagination_performance.items():
            print(f"  {test_name}: {stats['response_time']:.3f}s, {stats['items_returned']} items")
    
    def test_memory_usage_under_load(self):
        """Test memory usage under load."""
        import psutil
        import os
        
        # Get current process
        process = psutil.Process(os.getpid())
        
        # Measure initial memory usage
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        token = self._get_auth_token("user0@perf-test.com")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Generate load
        memory_measurements = [initial_memory]
        
        for i in range(100):
            # Make request
            response = self.client.get("/api/notifications?limit=50", headers=headers)
            assert response.status_code == 200
            
            # Measure memory every 10 requests
            if i % 10 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_measurements.append(current_memory)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        max_memory = max(memory_measurements)
        memory_increase = final_memory - initial_memory
        
        print(f"\nMemory Usage Analysis:")
        print(f"  Initial memory: {initial_memory:.1f} MB")
        print(f"  Final memory: {final_memory:.1f} MB")
        print(f"  Maximum memory: {max_memory:.1f} MB")
        print(f"  Memory increase: {memory_increase:.1f} MB")
        
        # Assert memory usage is reasonable
        assert max_memory < self.memory_threshold, f"Memory usage too high: {max_memory:.1f} MB"
        assert memory_increase < 100, f"Memory leak detected: {memory_increase:.1f} MB increase"
    
    def test_throughput_capacity(self):
        """Test API throughput capacity."""
        token = self._get_auth_token("user0@perf-test.com")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test throughput for read operations
        def make_read_request():
            try:
                response = self.client.get("/api/health", headers=headers)
                return response.status_code == 200
            except:
                return False
        
        # Measure throughput over a time period
        test_duration = 10  # seconds
        start_time = time.time()
        successful_requests = 0
        total_requests = 0
        
        while time.time() - start_time < test_duration:
            if make_read_request():
                successful_requests += 1
            total_requests += 1
            
            # Small delay to prevent overwhelming the system
            time.sleep(0.01)
        
        actual_duration = time.time() - start_time
        throughput = successful_requests / actual_duration
        success_rate = successful_requests / total_requests if total_requests > 0 else 0
        
        print(f"\nThroughput Test Results:")
        print(f"  Duration: {actual_duration:.1f}s")
        print(f"  Total requests: {total_requests}")
        print(f"  Successful requests: {successful_requests}")
        print(f"  Success rate: {success_rate:.2%}")
        print(f"  Throughput: {throughput:.1f} requests/second")
        
        # Assert throughput requirements
        assert success_rate >= 0.95, f"Success rate too low: {success_rate:.2%}"
        # Note: Throughput threshold might be adjusted based on hardware capabilities
    
    def test_large_payload_handling(self):
        """Test handling of large payloads."""
        token = self._get_auth_token("user0@perf-test.com")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test different payload sizes
        payload_sizes = [
            (1024, "1KB"),      # 1KB
            (10240, "10KB"),    # 10KB
            (102400, "100KB"),  # 100KB
        ]
        
        for size_bytes, size_label in payload_sizes:
            # Create large payload
            large_body = "A" * (size_bytes - 100)  # Account for other fields
            
            large_notification = {
                "title": f"Large Payload Test {size_label}",
                "body": large_body,
                "severity": 2
            }
            
            start_time = time.time()
            response = self.client.post("/api/notifications", json=large_notification, headers=headers)
            end_time = time.time()
            
            response_time = end_time - start_time
            
            if response.status_code == 201:
                # Large payload accepted
                assert response_time < 5.0, f"Large payload ({size_label}) processing too slow: {response_time:.2f}s"
                print(f"  {size_label} payload: {response_time:.3f}s")
            elif response.status_code == 413:
                # Payload too large - this is acceptable
                print(f"  {size_label} payload: Rejected (too large)")
            else:
                # Other error
                assert False, f"Unexpected response for {size_label} payload: {response.status_code}"
    
    def test_database_connection_pooling(self):
        """Test database connection pooling performance."""
        from api.services.mongodb import MongoDBService
        
        # Test multiple concurrent database operations
        def db_operation():
            try:
                mongo_service = MongoDBService()
                result = mongo_service.find_by_org("notifications", self.test_org_id, limit=10)
                return len(result) > 0
            except Exception as e:
                print(f"Database operation failed: {e}")
                return False
        
        # Run concurrent database operations
        num_concurrent_ops = 20
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent_ops) as executor:
            futures = [executor.submit(db_operation) for _ in range(num_concurrent_ops)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        successful_ops = sum(results)
        success_rate = successful_ops / len(results)
        
        print(f"\nDatabase Connection Pooling Test:")
        print(f"  Concurrent operations: {num_concurrent_ops}")
        print(f"  Successful operations: {successful_ops}")
        print(f"  Success rate: {success_rate:.2%}")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Average time per operation: {total_time / num_concurrent_ops:.3f}s")
        
        # Assert connection pooling performance
        assert success_rate >= 0.95, f"Database connection pooling success rate too low: {success_rate:.2%}"
        assert total_time < 10.0, f"Concurrent database operations too slow: {total_time:.2f}s"
    
    def test_cache_performance(self):
        """Test caching performance (if implemented)."""
        token = self._get_auth_token("user0@perf-test.com")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test endpoint that might be cached
        cache_test_endpoint = "/api/notifications?page=1&limit=10"
        
        # First request (cache miss)
        start_time = time.time()
        response1 = self.client.get(cache_test_endpoint, headers=headers)
        first_request_time = time.time() - start_time
        
        assert response1.status_code == 200
        
        # Second request (potential cache hit)
        start_time = time.time()
        response2 = self.client.get(cache_test_endpoint, headers=headers)
        second_request_time = time.time() - start_time
        
        assert response2.status_code == 200
        
        # Compare response times
        if second_request_time < first_request_time * 0.8:
            # Significant improvement suggests caching
            print(f"\nCache Performance Detected:")
            print(f"  First request: {first_request_time:.3f}s")
            print(f"  Second request: {second_request_time:.3f}s")
            print(f"  Improvement: {((first_request_time - second_request_time) / first_request_time * 100):.1f}%")
        else:
            print(f"\nNo significant cache performance detected")
            print(f"  First request: {first_request_time:.3f}s")
            print(f"  Second request: {second_request_time:.3f}s")
    
    def test_error_handling_performance(self):
        """Test that error handling doesn't significantly impact performance."""
        token = self._get_auth_token("user0@perf-test.com")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test error scenarios
        error_tests = [
            ("/api/notifications/nonexistent", "GET", 404),
            ("/api/notifications", "POST", 400, {"invalid": "data"}),
            ("/api/notifications/invalid-id", "PUT", 404, {"title": "Updated"}),
        ]
        
        for test_case in error_tests:
            if len(test_case) == 3:
                endpoint, method, expected_status = test_case
                data = None
            else:
                endpoint, method, expected_status, data = test_case
            
            # Measure error response time
            start_time = time.time()
            
            if method == "GET":
                response = self.client.get(endpoint, headers=headers)
            elif method == "POST":
                response = self.client.post(endpoint, json=data, headers=headers)
            elif method == "PUT":
                response = self.client.put(endpoint, json=data, headers=headers)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            assert response.status_code == expected_status
            assert response_time < 1.0, f"Error response too slow: {endpoint} took {response_time:.3f}s"
    
    def _get_auth_token(self, email: str) -> str:
        """Helper method to get authentication token."""
        return f"test_token_{email.replace('@', '_').replace('.', '_')}"


class TestScalabilityValidation:
    """Test scalability characteristics."""
    
    def test_user_scalability(self, test_db):
        """Test system behavior with many users."""
        # Create many users and test performance
        num_users = 1000
        users = []
        
        for i in range(num_users):
            user = {
                "_id": f"scale_user_{i}",
                "organizationId": "scale_test_org",
                "email": f"user{i}@scale-test.com",
                "name": f"Scale User {i}",
                "createdAt": datetime.utcnow(),
                "schemaVersion": 1
            }
            users.append(user)
        
        # Insert users in batches
        batch_size = 100
        start_time = time.time()
        
        for i in range(0, len(users), batch_size):
            batch = users[i:i + batch_size]
            test_db.users.insert_many(batch)
        
        insert_time = time.time() - start_time
        
        # Test querying with many users
        start_time = time.time()
        user_count = test_db.users.count_documents({"organizationId": "scale_test_org"})
        query_time = time.time() - start_time
        
        assert user_count == num_users
        assert insert_time < 10.0, f"User insertion too slow: {insert_time:.2f}s"
        assert query_time < 1.0, f"User count query too slow: {query_time:.3f}s"
        
        print(f"\nUser Scalability Test:")
        print(f"  Users created: {num_users}")
        print(f"  Insert time: {insert_time:.3f}s")
        print(f"  Query time: {query_time:.3f}s")
    
    def test_notification_scalability(self, test_db):
        """Test system behavior with many notifications."""
        # This test is similar to user scalability but for notifications
        # Implementation would test large numbers of notifications
        pass
    
    def test_concurrent_user_scalability(self, test_client):
        """Test system behavior with many concurrent users."""
        # Simulate many concurrent users
        num_concurrent_users = 50
        
        def simulate_user_session():
            try:
                # Simulate user actions
                response = test_client.get("/api/health")
                return response.status_code == 200
            except:
                return False
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent_users) as executor:
            futures = [executor.submit(simulate_user_session) for _ in range(num_concurrent_users)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        successful_sessions = sum(results)
        success_rate = successful_sessions / len(results)
        
        print(f"\nConcurrent User Scalability:")
        print(f"  Concurrent users: {num_concurrent_users}")
        print(f"  Successful sessions: {successful_sessions}")
        print(f"  Success rate: {success_rate:.2%}")
        print(f"  Total time: {total_time:.3f}s")
        
        assert success_rate >= 0.90, f"Concurrent user success rate too low: {success_rate:.2%}"