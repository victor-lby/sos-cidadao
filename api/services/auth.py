# SPDX-License-Identifier: Apache-2.0

"""
Authentication service for JWT token management and password hashing.

This module provides JWT token generation, validation, refresh, and password
hashing utilities using RS256 signing and bcrypt for secure authentication.
"""

import os
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from opentelemetry import trace
import logging

from ..models.entities import User

tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class TokenValidationError(Exception):
    """Raised when token validation fails."""
    pass


class AuthService:
    """
    JWT authentication service with RS256 signing and bcrypt password hashing.
    
    Provides secure token generation, validation, refresh, and password management
    for the multi-tenant notification platform.
    """
    
    def __init__(self, private_key: Optional[str] = None, public_key: Optional[str] = None):
        """
        Initialize the authentication service.
        
        Args:
            private_key: RS256 private key for token signing (PEM format)
            public_key: RS256 public key for token verification (PEM format)
        """
        self.private_key = private_key or self._get_private_key()
        self.public_key = public_key or self._get_public_key()
        self.algorithm = "RS256"
        self.access_token_expire_minutes = 15
        self.refresh_token_expire_days = 7
        
    def _get_private_key(self) -> str:
        """Get private key from environment or generate for development."""
        private_key_env = os.getenv("JWT_PRIVATE_KEY")
        if private_key_env:
            return private_key_env
            
        # Generate key pair for development
        logger.warning("No JWT_PRIVATE_KEY found, generating development key pair")
        return self._generate_dev_key_pair()[0]
    
    def _get_public_key(self) -> str:
        """Get public key from environment or generate for development."""
        public_key_env = os.getenv("JWT_PUBLIC_KEY")
        if public_key_env:
            return public_key_env
            
        # Generate key pair for development
        logger.warning("No JWT_PUBLIC_KEY found, generating development key pair")
        return self._generate_dev_key_pair()[1]
    
    def _generate_dev_key_pair(self) -> Tuple[str, str]:
        """Generate RSA key pair for development use."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        return private_pem, public_pem
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt with salt.
        
        Args:
            password: Plain text password to hash
            
        Returns:
            Hashed password string
        """
        with tracer.start_as_current_span("auth.hash_password") as span:
            span.set_attribute("auth.operation", "hash_password")
            
            salt = bcrypt.gensalt(rounds=12)
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            
            logger.debug("Password hashed successfully")
            return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: Plain text password to verify
            hashed_password: Stored hashed password
            
        Returns:
            True if password matches, False otherwise
        """
        with tracer.start_as_current_span("auth.verify_password") as span:
            span.set_attribute("auth.operation", "verify_password")
            
            try:
                result = bcrypt.checkpw(
                    password.encode('utf-8'), 
                    hashed_password.encode('utf-8')
                )
                
                span.set_attribute("auth.verification_result", "success" if result else "failed")
                logger.debug(f"Password verification: {'success' if result else 'failed'}")
                
                return result
            except Exception as e:
                span.set_attribute("auth.verification_result", "error")
                logger.error(f"Password verification error: {str(e)}")
                return False
    
    def generate_tokens(self, user: User) -> Dict[str, Any]:
        """
        Generate access and refresh tokens for a user.
        
        Args:
            user: User entity to generate tokens for
            
        Returns:
            Dictionary containing access_token, refresh_token, and metadata
        """
        with tracer.start_as_current_span("auth.generate_tokens") as span:
            span.set_attributes({
                "auth.operation": "generate_tokens",
                "user.id": user.id,
                "organization.id": user.organization_id
            })
            
            now = datetime.now(timezone.utc)
            access_exp = now + timedelta(minutes=self.access_token_expire_minutes)
            refresh_exp = now + timedelta(days=self.refresh_token_expire_days)
            
            # Access token payload
            access_payload = {
                "sub": user.id,
                "org_id": user.organization_id,
                "email": user.email,
                "name": user.name,
                "permissions": user.permissions,
                "iat": now,
                "exp": access_exp,
                "type": "access"
            }
            
            # Refresh token payload
            refresh_payload = {
                "sub": user.id,
                "org_id": user.organization_id,
                "iat": now,
                "exp": refresh_exp,
                "type": "refresh"
            }
            
            try:
                access_token = jwt.encode(
                    access_payload, 
                    self.private_key, 
                    algorithm=self.algorithm
                )
                
                refresh_token = jwt.encode(
                    refresh_payload, 
                    self.private_key, 
                    algorithm=self.algorithm
                )
                
                span.set_attribute("auth.tokens_generated", "success")
                
                logger.info(
                    "JWT tokens generated successfully",
                    extra={
                        "user_id": user.id,
                        "organization_id": user.organization_id,
                        "access_expires_at": access_exp.isoformat(),
                        "refresh_expires_at": refresh_exp.isoformat()
                    }
                )
                
                return {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "Bearer",
                    "expires_in": self.access_token_expire_minutes * 60,
                    "access_expires_at": access_exp.isoformat(),
                    "refresh_expires_at": refresh_exp.isoformat()
                }
                
            except Exception as e:
                span.set_attribute("auth.tokens_generated", "error")
                logger.error(f"Token generation failed: {str(e)}")
                raise AuthenticationError(f"Failed to generate tokens: {str(e)}")
    
    def validate_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Validate and decode a JWT token.
        
        Args:
            token: JWT token string to validate
            token_type: Expected token type ("access" or "refresh")
            
        Returns:
            Decoded token payload
            
        Raises:
            TokenValidationError: If token is invalid or expired
        """
        with tracer.start_as_current_span("auth.validate_token") as span:
            span.set_attributes({
                "auth.operation": "validate_token",
                "auth.token_type": token_type
            })
            
            try:
                payload = jwt.decode(
                    token,
                    self.public_key,
                    algorithms=[self.algorithm],
                    options={"verify_exp": True}
                )
                
                # Verify token type
                if payload.get("type") != token_type:
                    raise TokenValidationError(f"Invalid token type. Expected {token_type}")
                
                span.set_attributes({
                    "auth.validation_result": "success",
                    "user.id": payload.get("sub"),
                    "organization.id": payload.get("org_id")
                })
                
                logger.debug(
                    "Token validated successfully",
                    extra={
                        "user_id": payload.get("sub"),
                        "organization_id": payload.get("org_id"),
                        "token_type": token_type
                    }
                )
                
                return payload
                
            except jwt.ExpiredSignatureError:
                span.set_attribute("auth.validation_result", "expired")
                logger.warning("Token validation failed: token expired")
                raise TokenValidationError("Token has expired")
                
            except jwt.InvalidTokenError as e:
                span.set_attribute("auth.validation_result", "invalid")
                logger.warning(f"Token validation failed: {str(e)}")
                raise TokenValidationError(f"Invalid token: {str(e)}")
            
            except Exception as e:
                span.set_attribute("auth.validation_result", "error")
                logger.error(f"Token validation error: {str(e)}")
                raise TokenValidationError(f"Token validation failed: {str(e)}")
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Generate a new access token using a valid refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New access token and metadata
            
        Raises:
            TokenValidationError: If refresh token is invalid
        """
        with tracer.start_as_current_span("auth.refresh_access_token") as span:
            span.set_attribute("auth.operation", "refresh_access_token")
            
            # Validate refresh token
            refresh_payload = self.validate_token(refresh_token, "refresh")
            
            # Create new access token payload
            now = datetime.now(timezone.utc)
            access_exp = now + timedelta(minutes=self.access_token_expire_minutes)
            
            access_payload = {
                "sub": refresh_payload["sub"],
                "org_id": refresh_payload["org_id"],
                "iat": now,
                "exp": access_exp,
                "type": "access"
            }
            
            try:
                access_token = jwt.encode(
                    access_payload,
                    self.private_key,
                    algorithm=self.algorithm
                )
                
                span.set_attribute("auth.refresh_result", "success")
                
                logger.info(
                    "Access token refreshed successfully",
                    extra={
                        "user_id": refresh_payload["sub"],
                        "organization_id": refresh_payload["org_id"],
                        "new_expires_at": access_exp.isoformat()
                    }
                )
                
                return {
                    "access_token": access_token,
                    "token_type": "Bearer",
                    "expires_in": self.access_token_expire_minutes * 60,
                    "expires_at": access_exp.isoformat()
                }
                
            except Exception as e:
                span.set_attribute("auth.refresh_result", "error")
                logger.error(f"Token refresh failed: {str(e)}")
                raise AuthenticationError(f"Failed to refresh token: {str(e)}")
    
    def extract_token_id(self, token: str) -> str:
        """
        Extract a unique identifier from a token for blocklist purposes.
        
        Args:
            token: JWT token string
            
        Returns:
            Unique token identifier
        """
        try:
            # Decode without verification to get the payload
            payload = jwt.decode(token, options={"verify_signature": False})
            
            # Create unique ID from user, org, issued time, and type
            token_id = f"{payload.get('sub')}:{payload.get('org_id')}:{payload.get('iat')}:{payload.get('type')}"
            return token_id
            
        except Exception as e:
            logger.error(f"Failed to extract token ID: {str(e)}")
            raise TokenValidationError(f"Invalid token format: {str(e)}")