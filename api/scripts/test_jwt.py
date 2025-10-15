#!/usr/bin/env python3
"""
Script to test JWT generation and validation.
"""

import os
import sys
import jwt
from datetime import datetime, timedelta, timezone

# Add the parent directory to the path so we can import from api
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.auth import AuthService

def test_jwt():
    """Test JWT generation and validation."""
    print("Testing JWT generation and validation...")
    
    # Initialize auth service
    auth_service = AuthService()
    
    print(f"Private key length: {len(auth_service.private_key)}")
    print(f"Public key length: {len(auth_service.public_key)}")
    
    # Create test payload
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=15)
    
    test_payload = {
        "sub": "test_user",
        "org_id": "test_org",
        "email": "test@example.com",
        "name": "Test User",
        "permissions": ["test:permission"],
        "iat": now,
        "exp": exp,
        "type": "access"
    }
    
    try:
        # Generate token
        print("Generating token...")
        token = jwt.encode(test_payload, auth_service.private_key, algorithm="RS256")
        print(f"Token generated: {token[:50]}...")
        
        # Validate token
        print("Validating token...")
        decoded = jwt.decode(token, auth_service.public_key, algorithms=["RS256"])
        print(f"Token validated successfully: {decoded['sub']}")
        
        # Test with auth service
        print("Testing with AuthService...")
        validated_payload = auth_service.validate_token(token, "access")
        print(f"AuthService validation successful: {validated_payload['sub']}")
        
        return True
        
    except Exception as e:
        print(f"JWT test failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_jwt()
    sys.exit(0 if success else 1)