#!/usr/bin/env python
"""
Create Custom Atlas Types

This script creates custom entity types in Atlas to better represent specialized
data assets in the ETL pipeline ecosystem.
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
    
    def get_all_types(self):
        """Get all entity type definitions from Atlas."""
        try:
            response = requests.get(
                f"{self.atlas_url}/api/atlas/v2/types/typedefs", 
                auth=self.auth
            )
            
            if response.status_code == 200:
                data = response.json()
                entity_defs = data.get('entityDefs', [])
                logger.info(f"Retrieved {len(entity_defs)} entity type definitions")
                return entity_defs
            else:
                logger.error(f"Failed to get entity types: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting entity types: {e}")
            return []
    
    def create_entity_types(self, entity_defs):
        """Create new entity type definitions in Atlas."""
        payload = {
            "entityDefs": entity_defs,
            "classificationDefs": [],
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
                created_types = [entity_def['name'] for entity_def in entity_defs]
                logger.info(f"Successfully created entity types: {', '.join(created_types)}")
                return True
            else:
                logger.error(f"Failed to create entity types: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error creating entity types: {e}")
            return False
    
    def create_relationship_types(self, relationship_defs):
        """Create new relationship type definitions in Atlas."""
        payload = {
            "entityDefs": [],
            "classificationDefs": [],
            "enumDefs": [],
            "relationshipDefs": relationship_defs,
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
                created_types = [rel_def['name'] for rel_def in relationship_defs]
                logger.info(f"Successfully created relationship types: {', '.join(created_types)}")
                return True
            else:
                logger.error(f"Failed to create relationship types: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error creating relationship types: {e}")
            return False
    
    def create_instance(self, entity_def):
        """Create an instance of an entity type."""
        try:
            response = requests.post(
                f"{self.atlas_url}/api/atlas/v2/entity", 
                json={"entity": entity_def},
                headers=self.headers,
                auth=self.auth
            )
            
            if response.status_code == 200:
                result = response.json()
                guid = result.get('guidAssignments', {}).values()
                guid = list(guid)[0] if guid else None
                logger.info(f"Created entity '{entity_def['attributes'].get('name', 'unknown')}' with GUID: {guid}")
                return guid
            else:
                logger.error(f"Failed to create entity: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error creating entity: {e}")
            return None

def define_custom_etl_types():
    """Define custom entity types for ETL pipelines."""
    
    # 1. Data Pipeline Type
    data_pipeline_type = {
        "category": "ENTITY",
        "name": "DataPipeline",
        "description": "A data pipeline that processes data through multiple stages",
        "typeVersion": "1.0",
        "superTypes": ["Process"],
        "attributeDefs": [
            {
                "name": "pipelineId",
                "typeName": "string",
                "isOptional": False,
                "cardinality": "SINGLE",
                "valuesMinCount": 1,
                "valuesMaxCount": 1,
                "isUnique": True,
                "isIndexable": True
            },
            {
                "name": "pipelineType",
                "typeName": "string",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False,
                "isIndexable": True
            },
            {
                "name": "schedule",
                "typeName": "string",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False,
                "isIndexable": True
            },
            {
                "name": "owner",
                "typeName": "string",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False,
                "isIndexable": True
            },
            {
                "name": "executionPlatform",
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
    
    # 2. Data Quality Check Type
    data_quality_check_type = {
        "category": "ENTITY",
        "name": "DataQualityCheck",
        "description": "A quality check performed on data",
        "typeVersion": "1.0",
        "superTypes": ["Process"],
        "attributeDefs": [
            {
                "name": "checkId",
                "typeName": "string",
                "isOptional": False,
                "cardinality": "SINGLE",
                "valuesMinCount": 1,
                "valuesMaxCount": 1,
                "isUnique": True,
                "isIndexable": True
            },
            {
                "name": "checkType",
                "typeName": "string",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False,
                "isIndexable": True
            },
            {
                "name": "checkExpression",
                "typeName": "string",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False,
                "isIndexable": True
            },
            {
                "name": "threshold",
                "typeName": "float",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False,
                "isIndexable": True
            },
            {
                "name": "lastResult",
                "typeName": "boolean",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False,
                "isIndexable": True
            },
            {
                "name": "lastRunTime",
                "typeName": "long",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False,
                "isIndexable": True
            }
        ]
    }
    
    # 3. Business KPI Type
    business_kpi_type = {
        "category": "ENTITY",
        "name": "BusinessKPI",
        "description": "A business key performance indicator derived from data",
        "typeVersion": "1.0",
        "superTypes": ["DataSet"],
        "attributeDefs": [
            {
                "name": "kpiId",
                "typeName": "string",
                "isOptional": False,
                "cardinality": "SINGLE",
                "valuesMinCount": 1,
                "valuesMaxCount": 1,
                "isUnique": True,
                "isIndexable": True
            },
            {
                "name": "kpiName",
                "typeName": "string",
                "isOptional": False,
                "cardinality": "SINGLE",
                "valuesMinCount": 1,
                "valuesMaxCount": 1,
                "isUnique": False,
                "isIndexable": True
            },
            {
                "name": "description",
                "typeName": "string",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False,
                "isIndexable": True
            },
            {
                "name": "formula",
                "typeName": "string",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False,
                "isIndexable": True
            },
            {
                "name": "owner",
                "typeName": "string",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False,
                "isIndexable": True
            },
            {
                "name": "targetValue",
                "typeName": "float",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False,
                "isIndexable": True
            },
            {
                "name": "currentValue",
                "typeName": "float",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False,
                "isIndexable": True
            },
            {
                "name": "lastUpdated",
                "typeName": "long",
                "isOptional": True,
                "cardinality": "SINGLE",
                "valuesMinCount": 0,
                "valuesMaxCount": 1,
                "isUnique": False,
                "isIndexable": True
            }
        ]
    }
    
    return [data_pipeline_type, data_quality_check_type, business_kpi_type]

def define_custom_relationship_types():
    """Define custom relationship types for ETL entities."""
    
    # 1. DataQualityAssessment - Relates a quality check to a dataset
    quality_assessment_rel = {
        "category": "RELATIONSHIP",
        "name": "DataQualityAssessment",
        "description": "Relationship between a data quality check and the dataset it assesses",
        "typeVersion": "1.0",
        "endDef1": {
            "type": "DataQualityCheck",
            "name": "checks",
            "isContainer": False,
            "cardinality": "SINGLE"
        },
        "endDef2": {
            "type": "DataSet",
            "name": "assessedBy",
            "isContainer": False,
            "cardinality": "SET"
        },
        "relationshipCategory": "ASSOCIATION"
    }
    
    # 2. KPIDependency - Relates a KPI to its source datasets
    kpi_dependency_rel = {
        "category": "RELATIONSHIP",
        "name": "KPIDependency",
        "description": "Relationship between a business KPI and the datasets it depends on",
        "typeVersion": "1.0",
        "endDef1": {
            "type": "BusinessKPI",
            "name": "dependsOn",
            "isContainer": False,
            "cardinality": "SET"
        },
        "endDef2": {
            "type": "DataSet",
            "name": "usedInKPIs",
            "isContainer": False,
            "cardinality": "SET"
        },
        "relationshipCategory": "ASSOCIATION"
    }
    
    # 3. PipelineExecution - Relates a pipeline to a process execution
    pipeline_execution_rel = {
        "category": "RELATIONSHIP",
        "name": "PipelineExecution",
        "description": "Relationship between a data pipeline and a process execution",
        "typeVersion": "1.0",
        "endDef1": {
            "type": "DataPipeline",
            "name": "executes",
            "isContainer": False,
            "cardinality": "SET"
        },
        "endDef2": {
            "type": "Process",
            "name": "executedBy",
            "isContainer": False,
            "cardinality": "SINGLE"
        },
        "relationshipCategory": "ASSOCIATION"
    }
    
    return [quality_assessment_rel, kpi_dependency_rel, pipeline_execution_rel]

def create_sample_instances(atlas_client):
    """Create sample instances of our custom entity types."""
    
    # 1. Create DataPipeline instance
    pipeline_entity = {
        "typeName": "DataPipeline",
        "attributes": {
            "name": "Employee Data ETL",
            "description": "Pipeline for processing employee data",
            "qualifiedName": f"pipeline-emp-etl-{int(time.time())}",
            "pipelineId": f"EMP-ETL-{int(time.time())}",
            "pipelineType": "Batch",
            "schedule": "0 0 * * *",  # Daily at midnight
            "pipelineOwner": "Data Engineering Team",
            "executionPlatform": "Apache Airflow"
        }
    }
    
    pipeline_guid = atlas_client.create_instance(pipeline_entity)
    
    # 2. Create DataQualityCheck instance
    quality_check_entity = {
        "typeName": "DataQualityCheck",
        "attributes": {
            "name": "Salary Range Check",
            "description": "Validates salary values are within expected range",
            "qualifiedName": f"quality-check-salary-{int(time.time())}",
            "checkId": f"QC-SALARY-{int(time.time())}",
            "checkType": "Range Validation",
            "checkExpression": "salary >= 0 AND salary <= 500000",
            "threshold": 0.99,
            "lastResult": True,
            "lastRunTime": int(time.time() * 1000)
        }
    }
    
    check_guid = atlas_client.create_instance(quality_check_entity)
    
    # 3. Create BusinessKPI instance
    kpi_entity = {
        "typeName": "BusinessKPI",
        "attributes": {
            "name": "Avg Salary by Department",
            "description": "Average salary across departments for budget planning",
            "qualifiedName": f"kpi-avg-salary-dept-{int(time.time())}",
            "kpiId": f"KPI-SALARY-{int(time.time())}",
            "formula": "AVG(salary) GROUP BY department",
            "kpiOwner": "Finance Department",
            "targetValue": 80000.0,
            "currentValue": 78500.0,
            "lastUpdated": int(time.time() * 1000)
        }
    }
    
    kpi_guid = atlas_client.create_instance(kpi_entity)
    
    return True

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description="Create Custom Atlas Types")
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
    
    # Create custom entity types
    entity_types = define_custom_etl_types()
    if not atlas_client.create_entity_types(entity_types):
        logger.error("Failed to create custom entity types")
        sys.exit(1)
    
    # Create custom relationship types
    relationship_types = define_custom_relationship_types()
    if not atlas_client.create_relationship_types(relationship_types):
        logger.error("Failed to create custom relationship types")
        sys.exit(1)
    
    # Create sample instances
    if not create_sample_instances(atlas_client):
        logger.error("Failed to create sample instances")
        sys.exit(1)
    
    logger.info("Successfully created custom types and instances")
    print("\n")
    print("🔍 Custom entity and relationship types have been created.")
    print("👉 The following entity types are now available in Atlas:")
    print("   - DataPipeline: Represents an ETL pipeline with schedule and ownership")
    print("   - DataQualityCheck: Represents data quality validations")
    print("   - BusinessKPI: Represents business metrics derived from the data")
    print("👉 The following relationship types have been created:")
    print("   - DataQualityAssessment: Links quality checks to datasets")
    print("   - KPIDependency: Links KPIs to their source datasets")
    print("   - PipelineExecution: Links pipelines to processes")
    print("👀 Sample instances have been created for each type.")
    print("   You can find them by searching in the Atlas UI (http://localhost:21000).")
    print("\n")
    
if __name__ == "__main__":
    main()
