#!/usr/bin/env python
"""
Create Business-Specific Atlas Entity Types

This script creates business-specific entity types in Atlas to enhance
the metadata governance capabilities for ETL processes.
"""

import requests
import json
import sys
import logging
import argparse
from datetime import datetime
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AtlasTypeManager:
    def __init__(self, atlas_url, username="admin", password="admin"):
        """Initialize Atlas client with connection details."""
        self.atlas_url = atlas_url.rstrip('/')
        self.auth = (username, password)
        self.headers = {"Content-Type": "application/json", "Accept": "application/json"}
        logger.info(f"Initializing Atlas type manager for {atlas_url}")
    
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
    
    def create_business_metadata_defs(self, business_metadata_defs):
        """Create business metadata definitions in Atlas."""
        payload = {
            "classificationDefs": business_metadata_defs,
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
                created_types = [bmd['name'] for bmd in business_metadata_defs]
                logger.info(f"Successfully created business metadata: {', '.join(created_types)}")
                return True
            else:
                logger.error(f"Failed to create business metadata: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error creating business metadata: {e}")
            return False
    
    def apply_business_metadata(self, entity_guid, business_metadata_name, attributes):
        """Apply business metadata to an entity."""
        bmeta = {
            business_metadata_name: attributes
        }
        
        try:
            response = requests.post(
                f"{self.atlas_url}/api/atlas/v2/entity/guid/{entity_guid}/businessmetadata", 
                json=bmeta,
                headers=self.headers,
                auth=self.auth
            )
            
            if response.status_code == 200:
                logger.info(f"Applied business metadata '{business_metadata_name}' to entity {entity_guid}")
                return True
            else:
                logger.error(f"Failed to apply business metadata: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error applying business metadata: {e}")
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

def define_business_metadata():
    """Define business metadata for ETL processes."""
    
    # 1. ETL Pipeline Metadata
    etl_pipeline_metadata = {
        "category": "CLASSIFICATION",
        "name": "ETLPipelineMetadata",
        "description": "Business metadata for ETL pipelines",
        "typeVersion": "1.0",
        "attributeDefs": [
            {
                "name": "pipelineId",
                "typeName": "string",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False
            },
            {
                "name": "pipelineType",
                "typeName": "string",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False
            },
            {
                "name": "schedule",
                "typeName": "string",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False
            },
            {
                "name": "pipelineOwner",
                "typeName": "string",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False
            },
            {
                "name": "executionPlatform",
                "typeName": "string",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False
            }
        ]
    }
    
    # 2. Data Quality Metadata
    data_quality_metadata = {
        "category": "CLASSIFICATION",
        "name": "DataQualityMetadata",
        "description": "Business metadata for data quality",
        "typeVersion": "1.0",
        "attributeDefs": [
            {
                "name": "completeness",
                "typeName": "float",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False
            },
            {
                "name": "accuracy",
                "typeName": "float",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False
            },
            {
                "name": "validationRules",
                "typeName": "string",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False
            },
            {
                "name": "lastValidated",
                "typeName": "string",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False
            }
        ]
    }
    
    # 3. Business Context Metadata
    business_context_metadata = {
        "category": "CLASSIFICATION",
        "name": "BusinessContextMetadata",
        "description": "Business context for data assets",
        "typeVersion": "1.0",
        "attributeDefs": [
            {
                "name": "businessDomain",
                "typeName": "string",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False
            },
            {
                "name": "businessFunction",
                "typeName": "string",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False
            },
            {
                "name": "businessValue",
                "typeName": "string",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False
            },
            {
                "name": "businessOwner",
                "typeName": "string",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False
            },
            {
                "name": "criticality",
                "typeName": "string",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False
            }
        ]
    }
    
    return [etl_pipeline_metadata, data_quality_metadata, business_context_metadata]

def apply_business_metadata_to_sample_entities(atlas_client):
    """Apply business metadata to existing sample entities."""
    
    # Find existing tables
    source_entity = atlas_client.get_entity_by_attribute("hive_table", "name", "source_data")
    transformed_entity = atlas_client.get_entity_by_attribute("hive_table", "name", "transformed_data")
    analytics_entity = atlas_client.get_entity_by_attribute("hive_table", "name", "analytics_data")
    
    # Apply ETL Pipeline Metadata to process entities
    process_entity = atlas_client.get_entity_by_attribute("Process", "name", "sample_etl_extract_transform")
    if process_entity:
        atlas_client.apply_business_metadata(
            process_entity['guid'],
            "ETLPipelineMetadata",
            {
                "pipelineId": "ETL-001",
                "pipelineType": "Batch",
                "schedule": "0 0 * * *",  # Daily at midnight
                "pipelineOwner": "Data Engineering Team",
                "executionPlatform": "Apache Airflow"
            }
        )
    
    # Apply Data Quality Metadata to transformed data
    if transformed_entity:
        atlas_client.apply_business_metadata(
            transformed_entity['guid'],
            "DataQualityMetadata",
            {
                "completeness": 0.98,
                "accuracy": 0.95,
                "validationRules": "salary > 0 AND department IN ('Engineering', 'Marketing', 'Finance')",
                "lastValidated": datetime.now().strftime("%Y-%m-%d")
            }
        )
    
    # Apply Business Context Metadata to analytics data
    if analytics_entity:
        atlas_client.apply_business_metadata(
            analytics_entity['guid'],
            "BusinessContextMetadata",
            {
                "businessDomain": "HR Analytics",
                "businessFunction": "Compensation Analysis",
                "businessValue": "Enable data-driven decisions for compensation planning",
                "businessOwner": "Jane Smith (Director of HR)",
                "criticality": "High"
            }
        )
    
    logger.info("Successfully applied business metadata to sample entities")
    return True

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description="Create Business-Specific Atlas Entity Types")
    parser.add_argument("--atlas-url", default="http://localhost:21000", 
                        help="Atlas server URL (default: http://localhost:21000)")
    parser.add_argument("--username", default="admin", 
                        help="Atlas username (default: admin)")
    parser.add_argument("--password", default="admin", 
                        help="Atlas password (default: admin)")
    
    args = parser.parse_args()
    
    # Initialize Atlas client
    atlas_client = AtlasTypeManager(args.atlas_url, args.username, args.password)
    
    # Check connection
    if not atlas_client.check_connection():
        logger.error("Could not connect to Atlas. Please check the URL and credentials.")
        sys.exit(1)
    
    # Create business metadata definitions
    business_metadata_defs = define_business_metadata()
    if not atlas_client.create_business_metadata_defs(business_metadata_defs):
        logger.error("Failed to create business metadata definitions")
        sys.exit(1)
    
    # Apply business metadata to sample entities
    if not apply_business_metadata_to_sample_entities(atlas_client):
        logger.error("Failed to apply business metadata to sample entities")
        sys.exit(1)
    
    logger.info("Successfully created and applied business metadata")
    print("\n")
    print("🔍 Business metadata has been created and applied to sample entities.")
    print("👉 The following business metadata types are now available in Atlas:")
    print("   - ETLPipelineMetadata: Provides context about ETL pipelines")
    print("   - DataQualityMetadata: Captures data quality metrics")
    print("   - BusinessContextMetadata: Documents business relevance of data")
    print("👀 This metadata has been applied to the sample entities.")
    print("   You can find them by searching in the Atlas UI (http://localhost:21000).")
    print("\n")
    
if __name__ == "__main__":
    main()
