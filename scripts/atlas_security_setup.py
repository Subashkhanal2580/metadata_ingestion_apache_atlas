#!/usr/bin/env python
"""
Atlas Security Setup

This script demonstrates how to enhance security for Apache Atlas in a production environment.
- Creates a configuration file with secure settings
- Provides guidance on securing Atlas deployments
- Implements best practices for API security
"""

import argparse
import logging
import os
import json
import sys
import yaml
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security configuration templates
ATLAS_APPLICATION_PROPERTIES = """
#
# Atlas Server Security Configuration
#

# Server Properties
atlas.server.http.port=21000
atlas.server.https.port=21443
atlas.enableTLS=true

# SSL/TLS Configuration
atlas.server.https.keystore.file=/path/to/keystore.jks
atlas.server.https.keystore.password=<keystore_password>
atlas.server.https.keystore.keypassword=<key_password>
atlas.server.https.truststore.file=/path/to/truststore.jks
atlas.server.https.truststore.password=<truststore_password>

# Authentication Configuration
atlas.authentication.method=file
atlas.authentication.method.file.filename=/path/to/users.properties

# Alternative Authentication Methods
# atlas.authentication.method=ldap
# atlas.authentication.method.ldap.url=ldap://ldap.example.com:389
# atlas.authentication.method.ldap.userDNpattern=uid={0},ou=People,dc=example,dc=com
# atlas.authentication.method.ldap.groupSearchBase=ou=Groups,dc=example,dc=com
# atlas.authentication.method.ldap.groupSearchFilter=(member=uid={0},ou=People,dc=example,dc=com)
# atlas.authentication.method.ldap.groupRoleAttribute=cn

# JAAS Configuration
atlas.jaas.KafkaClient.loginModuleName=com.sun.security.auth.module.Krb5LoginModule
atlas.jaas.KafkaClient.loginModuleControlFlag=required
atlas.jaas.KafkaClient.option.useKeyTab=true
atlas.jaas.KafkaClient.option.storeKey=true
atlas.jaas.KafkaClient.option.serviceName=kafka
atlas.jaas.KafkaClient.option.keyTab=/path/to/atlas.keytab
atlas.jaas.KafkaClient.option.principal=atlas@EXAMPLE.COM

# Authorization Configuration
atlas.authorizer.impl=org.apache.atlas.authorize.SimpleAtlasAuthorizer
atlas.rest.address=https://atlas.example.com:21443

# Kerberos Configuration
atlas.authentication.method.kerberos.principal=atlas/_HOST@EXAMPLE.COM
atlas.authentication.method.kerberos.keytab=/etc/security/keytabs/atlas.service.keytab
atlas.authentication.method.kerberos.name.rules=DEFAULT
"""

ATLAS_USERS_PROPERTIES = """
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# Format: username=password,role1,role2
admin=AtlasSecurePassword123,ROLE_ADMIN
datasteward=DataStewardPass456,ROLE_DATA_STEWARD
analyst=AnalystPass789,ROLE_DATA_SCIENTIST
readonly=ReadOnlyPass321,ROLE_USER
"""

ATLAS_AUTHORIZATION_POLICY = """
{
  "roles": {
    "ROLE_ADMIN": {
      "adminPermissions": [
        {
          "privileges": ["*"]
        }
      ],
      "typePermissions": [
        {
          "privileges": ["*"],
          "typeCategories": ["*"],
          "typeNames": ["*"]
        }
      ],
      "entityPermissions": [
        {
          "privileges": ["*"],
          "entityTypes": ["*"],
          "entityIds": ["*"],
          "classifications": ["*"],
          "labels": ["*"]
        }
      ]
    },
    "ROLE_DATA_STEWARD": {
      "adminPermissions": [
        {
          "privileges": ["type-create", "type-update", "entity-create", "entity-update", "entity-read"]
        }
      ],
      "typePermissions": [
        {
          "privileges": ["create", "update", "read"],
          "typeCategories": ["*"],
          "typeNames": ["*"]
        }
      ],
      "entityPermissions": [
        {
          "privileges": ["read", "update", "create", "delete"],
          "entityTypes": ["*"],
          "entityIds": ["*"],
          "classifications": ["*"],
          "labels": ["*"]
        }
      ]
    },
    "ROLE_DATA_SCIENTIST": {
      "adminPermissions": [
        {
          "privileges": ["entity-read"]
        }
      ],
      "typePermissions": [
        {
          "privileges": ["read"],
          "typeCategories": ["*"],
          "typeNames": ["*"]
        }
      ],
      "entityPermissions": [
        {
          "privileges": ["read", "update"],
          "entityTypes": ["*"],
          "entityIds": ["*"],
          "classifications": ["*"],
          "labels": ["*"]
        }
      ]
    },
    "ROLE_USER": {
      "adminPermissions": [],
      "typePermissions": [
        {
          "privileges": ["read"],
          "typeCategories": ["*"],
          "typeNames": ["*"]
        }
      ],
      "entityPermissions": [
        {
          "privileges": ["read"],
          "entityTypes": ["*"],
          "entityIds": ["*"],
          "classifications": ["*"],
          "labels": ["*"]
        }
      ]
    }
  }
}
"""

API_SECURITY_GUIDELINES = """
# Atlas API Security Best Practices

## Authentication
- Always use HTTPS for all communications
- Implement token-based authentication for API clients
- Rotate API tokens regularly
- Use separate service accounts for different systems integrating with Atlas

## Authorization
- Grant minimal required permissions to each role
- Regularly audit user and role assignments
- Implement resource-based access control for sensitive data

## API Calls
- Validate all inputs before sending to the API
- Implement rate limiting for API requests
- Log all API access for auditing purposes
- Use API versioning to avoid breaking changes

## Secure Integration
- Store credentials securely, never in plain text
- Use environment variables or secure vaults for credentials
- Create dedicated service accounts for ETL processes
- Implement proper error handling to avoid exposing sensitive information

## Network Security
- Use a private network for Atlas communication where possible
- Implement network-level controls (firewalls, security groups)
- Consider using a VPN or private service connect for secure access
"""

DOCKER_COMPOSE_SECURITY = """
version: '3'

services:
  atlas:
    image: sburn/apache-atlas:2.3.0
    container_name: atlas
    ports:
      - "21443:21443"
    environment:
      - ATLAS_ENABLE_TLS=true
      - ATLAS_KEYSTORE_PASSWORD=keystore_password
      - ATLAS_TRUSTSTORE_PASSWORD=truststore_password
    volumes:
      - ./atlas_security:/opt/atlas/conf/security
      - ./ssl:/opt/atlas/conf/ssl
      - ./atlas_data:/opt/apache-atlas/data
      - ./atlas_logs:/opt/apache-atlas/logs
    networks:
      - etl_network
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-k", "--fail", "https://localhost:21443/api/atlas/admin/version"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s

networks:
  etl_network:
    external: true
"""

def create_security_configuration_files(output_dir, env):
    """Create security configuration files for Atlas."""
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Write atlas-application.properties
    with open(os.path.join(output_dir, "atlas-application.properties"), "w") as f:
        f.write(ATLAS_APPLICATION_PROPERTIES)
    
    # Write users.properties
    with open(os.path.join(output_dir, "users.properties"), "w") as f:
        f.write(ATLAS_USERS_PROPERTIES)
    
    # Write authorization policy
    with open(os.path.join(output_dir, "authorization-policy.json"), "w") as f:
        f.write(ATLAS_AUTHORIZATION_POLICY)
    
    # Write API security guidelines
    with open(os.path.join(output_dir, "api-security-guidelines.md"), "w") as f:
        f.write(API_SECURITY_GUIDELINES)
    
    # Write secured docker-compose file
    with open(os.path.join(output_dir, "docker-compose-secure.yml"), "w") as f:
        f.write(DOCKER_COMPOSE_SECURITY)
    
    logger.info(f"Security configuration files created in {output_dir}")

def main():
    parser = argparse.ArgumentParser(description="Atlas Security Setup")
    parser.add_argument("--output-dir", default="./atlas_security", 
                        help="Output directory for security configuration files")
    parser.add_argument("--env", default="prod", 
                        choices=["dev", "test", "prod"],
                        help="Target environment")
    
    args = parser.parse_args()
    
    # Create security configuration files
    create_security_configuration_files(args.output_dir, args.env)
    
    # Print summary
    print("\n")
    print("🔒 Atlas Security Configuration")
    print("==============================")
    print("Security configuration files have been created for production deployment of Apache Atlas.")
    print("\nThese files include:")
    print("1. atlas-application.properties - Secure server configuration")
    print("2. users.properties - User authentication configuration")
    print("3. authorization-policy.json - Role-based access control")
    print("4. api-security-guidelines.md - Best practices for API security")
    print("5. docker-compose-secure.yml - Secure Docker deployment")
    print("\nSecurity Best Practices:")
    print("- Replace default admin/admin credentials before deployment")
    print("- Generate proper SSL certificates and update paths in configuration")
    print("- Use a strong password policy for all users")
    print("- Implement network segmentation for Atlas access")
    print("- Regularly audit access logs and permissions")
    print("- Keep Atlas updated with security patches")
    print("\nNext Steps:")
    print("1. Review and customize these configuration files")
    print("2. Generate SSL certificates for TLS configuration")
    print("3. Set up proper authentication (File, LDAP, or Kerberos)")
    print("4. Implement role-based access control")
    print("5. Secure network communication")
    print("6. Set up monitoring and logging")
    print("\n")

if __name__ == "__main__":
    main()
