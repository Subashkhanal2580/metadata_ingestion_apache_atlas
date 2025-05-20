#!/usr/bin/env python
"""
Atlas Custom Classifications Script

This script creates custom classifications (tags) in Atlas for better data governance.
Classifications can be applied to entities to indicate their sensitivity, quality, and regulatory status.
"""

import requests
import json
import sys
import logging
import argparse
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AtlasClassificationManager:
    def __init__(self, atlas_url, username="admin", password="admin"):
        """Initialize Atlas client with connection details."""
        self.atlas_url = atlas_url.rstrip('/')
        self.auth = (username, password)
        self.headers = {"Content-Type": "application/json", "Accept": "application/json"}
        logger.info(f"Initializing Atlas classification manager for {atlas_url}")
    
    def check_connection(self):
        """Check if Atlas is running and return version info."""
        try:
            response = requests.get(f"{self.atlas_url}/api/atlas/admin/version", auth=self.auth)
            if response.status_code == 200:
                version_info = response.json()
                logger.info(f"Successfully connected to Atlas {version_info.get('Version', 'Unknown')}")
                return True
            else:
                logger.error(f"Atlas returned status code {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error connecting to Atlas: {e}")
            return False
    
    def get_all_classifications(self):
        """Get all classification definitions from Atlas."""
        try:
            response = requests.get(
                f"{self.atlas_url}/api/atlas/v2/types/typedefs", 
                auth=self.auth
            )
            
            if response.status_code == 200:
                data = response.json()
                classifications = data.get('classificationDefs', [])
                logger.info(f"Retrieved {len(classifications)} classification definitions")
                return classifications
            else:
                logger.error(f"Failed to get classifications: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting classifications: {e}")
            return []
    
    def create_classification(self, classification_def):
        """Create a new classification definition in Atlas."""
        payload = {
            "classificationDefs": [classification_def],
            "entityDefs": [],
            "enumDefs": [],
            "relationshipDefs": [],
            "structDefs": []
        }
        
        try:
            response = requests.post(
                f"{self.atlas_url}/api/atlas/v2/types/typedefs", 
                json=payload,
                headers=self.headers,
                auth=self.auth
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully created classification: {classification_def['name']}")
                return True
            else:
                logger.error(f"Failed to create classification: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error creating classification: {e}")
            return False
    
    def apply_classification_to_entity(self, entity_guid, classification_name, attributes=None):
        """Apply a classification to an entity."""
        classification = {
            "typeName": classification_name,
            "attributes": attributes or {}
        }
        
        try:
            response = requests.post(
                f"{self.atlas_url}/api/atlas/v2/entity/guid/{entity_guid}/classifications", 
                json=[classification],
                headers=self.headers,
                auth=self.auth
            )
            
            if response.status_code == 200:
                logger.info(f"Applied classification '{classification_name}' to entity {entity_guid}")
                return True
            else:
                logger.error(f"Failed to apply classification: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error applying classification: {e}")
            return False
    
    def get_entity_by_attribute(self, type_name, attribute_name, attribute_value):
        """Search for an entity by a specific attribute value."""
        query = {
            "typeName": type_name,
            "excludeDeletedEntities": True,
            "entityFilters": {
                "condition": "AND",
                "criterion": [
                    {
                        "attributeName": attribute_name,
                        "operator": "=",
                        "attributeValue": attribute_value
                    }
                ]
            }
        }
        
        try:
            response = requests.post(
                f"{self.atlas_url}/api/atlas/v2/search/basic", 
                json=query,
                headers=self.headers,
                auth=self.auth
            )
            
            if response.status_code == 200:
                entities = response.json().get("entities", [])
                if entities:
                    logger.info(f"Found {type_name} with {attribute_name}={attribute_value}")
                    return entities[0]
                else:
                    logger.info(f"No {type_name} found with {attribute_name}={attribute_value}")
                    return None
            else:
                logger.error(f"Search failed with status code {response.status_code}: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error searching for entity: {e}")
            return None

def create_data_governance_classifications(atlas_client):
    """Create custom classifications for data governance."""
    
    # 1. Data Sensitivity Classification
    sensitivity_classification = {
        "category": "CLASSIFICATION",
        "name": "DataSensitivity",
        "description": "Classification for data sensitivity levels",
        "typeVersion": "1.0",
        "attributeDefs": [
            {
                "name": "level",
                "typeName": "string",
                "isOptional": False,
                "cardinality": "SINGLE",
                "valuesMinCount": 1,
                "valuesMaxCount": 1,
                "isUnique": False,
                "isIndexable": True,
                "includedInNotification": True,
                "constraints": [
                    {
                        "type": "ENUM",
                        "params": {
                            "values": ["Public", "Internal", "Confidential", "Restricted"]
                        }
                    }
                ]
            },
            {
                "name": "justification",
                "typeName": "string",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False,
                "isIndexable": True
            }
        ]
    }
    
    # 2. Data Quality Classification
    quality_classification = {
        "category": "CLASSIFICATION",
        "name": "DataQuality",
        "description": "Classification for data quality metrics",
        "typeVersion": "1.0",
        "attributeDefs": [
            {
                "name": "completeness",
                "typeName": "float",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False,
                "isIndexable": True
            },
            {
                "name": "accuracy",
                "typeName": "float",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False,
                "isIndexable": True
            },
            {
                "name": "lastValidated",
                "typeName": "date",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False,
                "isIndexable": True
            }
        ]
    }
    
    # 3. Compliance Classification
    compliance_classification = {
        "category": "CLASSIFICATION",
        "name": "Compliance",
        "description": "Classification for regulatory compliance",
        "typeVersion": "1.0",
        "attributeDefs": [
            {
                "name": "regulations",
                "typeName": "array<string>",
                "isOptional": True,
                "cardinality": "SET",
                "valuesMinCount": 0,
                "valuesMaxCount": 100,
                "isUnique": False,
                "isIndexable": True,
                "constraints": [
                    {
                        "type": "ENUM",
                        "params": {
                            "values": ["GDPR", "CCPA", "HIPAA", "PCI-DSS", "SOX"]
                        }
                    }
                ]
            },
            {
                "name": "dataRetentionPeriod",
                "typeName": "int",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False,
                "isIndexable": True
            }
        ]
    }
    
    # 4. Business Context Classification
    business_classification = {
        "category": "CLASSIFICATION",
        "name": "BusinessContext",
        "description": "Classification for business context",
        "typeVersion": "1.0",
        "attributeDefs": [
            {
                "name": "businessDomain",
                "typeName": "string",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False,
                "isIndexable": True
            },
            {
                "name": "businessOwner",
                "typeName": "string",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False,
                "isIndexable": True
            },
            {
                "name": "criticality",
                "typeName": "string",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False,
                "isIndexable": True,
                "constraints": [
                    {
                        "type": "ENUM",
                        "params": {
                            "values": ["Low", "Medium", "High", "Critical"]
                        }
                    }
                ]
            }
        ]
    }
    
    # Create all classifications
    classifications = [
        sensitivity_classification,
        quality_classification,
        compliance_classification,
        business_classification
    ]
    
    success = True
    for classification in classifications:
        if not atlas_client.create_classification(classification):
            success = False
    
    return success

def apply_classifications_to_sample_data(atlas_client):
    """Apply classifications to our sample data entities."""
    
    # 1. Apply DataSensitivity classification to tables
    source_entity = atlas_client.get_entity_by_attribute("hive_table", "name", "source_data")
    if source_entity:
        atlas_client.apply_classification_to_entity(
            source_entity['guid'], 
            "DataSensitivity", 
            {"level": "Confidential", "justification": "Contains employee salary information"}
        )
    
    transformed_entity = atlas_client.get_entity_by_attribute("hive_table", "name", "transformed_data")
    if transformed_entity:
        atlas_client.apply_classification_to_entity(
            transformed_entity['guid'], 
            "DataSensitivity", 
            {"level": "Confidential", "justification": "Contains processed employee salary information"}
        )
    
    analytics_entity = atlas_client.get_entity_by_attribute("hive_table", "name", "analytics_data")
    if analytics_entity:
        atlas_client.apply_classification_to_entity(
            analytics_entity['guid'], 
            "DataSensitivity", 
            {"level": "Internal", "justification": "Aggregated data with restricted identifiable information"}
        )
    
    # 2. Apply DataQuality classification
    atlas_client.apply_classification_to_entity(
        transformed_entity['guid'],
        "DataQuality",
        {
            "completeness": 0.95,
            "accuracy": 0.98,
            "lastValidated": datetime.now().strftime("%Y-%m-%d")
        }
    )
    
    # 3. Apply Compliance classification
    atlas_client.apply_classification_to_entity(
        source_entity['guid'],
        "Compliance",
        {
            "regulations": ["GDPR", "CCPA"],
            "dataRetentionPeriod": 365
        }
    )
    
    # 4. Apply BusinessContext classification
    atlas_client.apply_classification_to_entity(
        analytics_entity['guid'],
        "BusinessContext",
        {
            "businessDomain": "HR Analytics",
            "businessOwner": "Jane Smith",
            "criticality": "High"
        }
    )
    
    # Apply ETL-specific classifications to distinguish entities based on their role in the pipeline
    db_entity = atlas_client.get_entity_by_attribute("hive_db", "name", "atlas_test")
    if db_entity:
        atlas_client.apply_classification_to_entity(db_entity['guid'], "ETL_Database")
    
    atlas_client.apply_classification_to_entity(source_entity['guid'], "ETL_Source")
    atlas_client.apply_classification_to_entity(transformed_entity['guid'], "ETL_Intermediate")
    atlas_client.apply_classification_to_entity(analytics_entity['guid'], "ETL_Target")
    
    logger.info("Successfully applied classifications to sample entities")
    return True

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description="Atlas Custom Classifications Script")
    parser.add_argument("--atlas-url", default="http://localhost:21000", 
                        help="Atlas server URL (default: http://localhost:21000)")
    parser.add_argument("--username", default="admin", 
                        help="Atlas username (default: admin)")
    parser.add_argument("--password", default="admin", 
                        help="Atlas password (default: admin)")
    
    args = parser.parse_args()
    
    # Initialize Atlas client
    atlas_client = AtlasClassificationManager(args.atlas_url, args.username, args.password)
    
    # Check connection
    if not atlas_client.check_connection():
        logger.error("Could not connect to Atlas. Please check the URL and credentials.")
        sys.exit(1)
    
    # Create custom classifications
    if not create_data_governance_classifications(atlas_client):
        logger.error("Failed to create all custom classifications")
        sys.exit(1)
    
    # Apply classifications to sample data
    if not apply_classifications_to_sample_data(atlas_client):
        logger.error("Failed to apply classifications to sample data")
        sys.exit(1)
    
    logger.info("Successfully created and applied custom classifications")
    print("\n")
    print("🔍 Classifications have been created and applied to sample entities.")
    print("👉 Go to the Atlas UI (http://localhost:21000) and search for the entities:")
    print("   - Database: atlas_test")
    print("   - Tables: source_data, transformed_data, analytics_data")
    print("👀 Click on each entity and check the 'Classifications' tab to see the applied tags.")
    print("\n")
    
if __name__ == "__main__":
    main()
