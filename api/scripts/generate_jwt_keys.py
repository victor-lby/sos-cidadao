#!/usr/bin/env python3
"""
Script to generate RSA key pair for JWT signing.
This ensures consistent keys across container restarts.
"""

import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

def generate_jwt_keys():
    """Generate RSA key pair for JWT signing."""
    
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    
    # Serialize private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    # Get public key
    public_key = private_key.public_key()
    
    # Serialize public key
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    return private_pem, public_pem

if __name__ == "__main__":
    private_key, public_key = generate_jwt_keys()
    
    print("=== JWT PRIVATE KEY ===")
    print(private_key)
    print("\n=== JWT PUBLIC KEY ===")
    print(public_key)
    
    print("\n=== Environment Variables ===")
    newline = "\\n"
    print(f'JWT_PRIVATE_KEY="{private_key.replace(chr(10), newline)}"')
    print(f'JWT_PUBLIC_KEY="{public_key.replace(chr(10), newline)}"')