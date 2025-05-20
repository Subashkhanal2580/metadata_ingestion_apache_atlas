#!/usr/bin/env python
"""
Atlas Metadata Ingestion Script

This script automates the creation of metadata entities in Atlas to track ETL processes.
It creates database, table, and column entities and establishes lineage between them,
simulating what the Hive hook would normally do.
"""

import requests
import json
import time
import sys
import argparse
from datetime import datetime
import uuid
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AtlasMetadataIngestion:
    def __init__(self, atlas_url, username="admin", password="admin"):
        """Initialize Atlas client with connection details."""
        self.atlas_url = atlas_url.rstrip('/')
        self.auth = (username, password)
        self.headers = {"Content-Type": "application/json", "Accept": "application/json"}
        logger.info(f"Initializing Atlas metadata ingestion client for {atlas_url}")
    
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
    
    def create_hive_db(self, db_name, cluster_name="primary", description=None, owner="admin"):
        """Create a Hive database entity in Atlas."""
        # Check if the database already exists
        existing_entity = self.get_entity_by_attribute("hive_db", "name", db_name)
        if existing_entity:
            logger.info(f"Database {db_name} already exists with GUID {existing_entity['guid']}")
            return existing_entity["guid"]
        
        qualified_name = f"{db_name}@{cluster_name}"
        entity = {
            "entity": {
                "typeName": "hive_db",
                "attributes": {
                    "name": db_name,
                    "description": description or f"Database for ETL processing: {db_name}",
                    "owner": owner,
                    "clusterName": cluster_name,
                    "qualifiedName": qualified_name,
                    "createTime": int(time.time() * 1000)
                }
            }
        }
        
        try:
            response = requests.post(
                f"{self.atlas_url}/api/atlas/v2/entity", 
                data=json.dumps(entity),
                headers=self.headers,
                auth=self.auth
            )
            
            if response.status_code == 200:
                result = response.json()
                guid = result.get('guidAssignments', {}).values()
                guid = list(guid)[0] if guid else None
                logger.info(f"Created Hive database '{db_name}' with GUID: {guid}")
                return guid
            else:
                logger.error(f"Failed to create Hive database: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error creating Hive database: {e}")
            return None
    
    def create_hive_table(self, table_name, db_name, db_guid=None, cluster_name="primary", 
                        description=None, owner="admin", columns=None):
        """Create a Hive table entity in Atlas."""
        # Get database GUID if not provided
        if not db_guid:
            db_entity = self.get_entity_by_attribute("hive_db", "name", db_name)
            if db_entity:
                db_guid = db_entity["guid"]
            else:
                db_guid = self.create_hive_db(db_name, cluster_name, None, owner)
        
        if not db_guid:
            logger.error(f"Cannot create table {table_name} without valid database")
            return None
        
        # Check if the table already exists
        qualified_name = f"{db_name}.{table_name}@{cluster_name}"
        existing_entity = self.get_entity_by_attribute("hive_table", "qualifiedName", qualified_name)
        if existing_entity:
            logger.info(f"Table {qualified_name} already exists with GUID {existing_entity['guid']}")
            return existing_entity["guid"]
        
        entity = {
            "entity": {
                "typeName": "hive_table",
                "attributes": {
                    "name": table_name,
                    "description": description or f"Table created by ETL process: {table_name}",
                    "owner": owner,
                    "qualifiedName": qualified_name,
                    "db": {"guid": db_guid, "typeName": "hive_db"},
                    "createTime": int(time.time() * 1000),
                    "lastAccessTime": int(time.time() * 1000),
                    "retention": 0,
                    "parameters": {"created_via": "Atlas ETL Integration"}
                }
            }
        }
        
        try:
            response = requests.post(
                f"{self.atlas_url}/api/atlas/v2/entity", 
                data=json.dumps(entity),
                headers=self.headers,
                auth=self.auth
            )
            
            if response.status_code == 200:
                result = response.json()
                guid = result.get('guidAssignments', {}).values()
                guid = list(guid)[0] if guid else None
                logger.info(f"Created Hive table '{qualified_name}' with GUID: {guid}")
                
                # Create columns if provided
                if columns and guid:
                    self.create_table_columns(guid, db_name, table_name, cluster_name, columns)
                
                return guid
            else:
                logger.error(f"Failed to create Hive table: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error creating Hive table: {e}")
            return None
    
    def create_table_columns(self, table_guid, db_name, table_name, cluster_name="primary", columns=None):
        """Create columns for a Hive table."""
        if not columns:
            return False
        
        column_entities = []
        
        for col in columns:
            col_name = col.get("name")
            col_type = col.get("type")
            col_comment = col.get("comment", "")
            
            qualified_name = f"{db_name}.{table_name}.{col_name}@{cluster_name}"
            
            column_entity = {
                "typeName": "hive_column",
                "attributes": {
                    "name": col_name,
                    "type": col_type,
                    "comment": col_comment,
                    "qualifiedName": qualified_name,
                    "table": {"guid": table_guid, "typeName": "hive_table"}
                }
            }
            column_entities.append(column_entity)
        
        try:
            response = requests.post(
                f"{self.atlas_url}/api/atlas/v2/entity/bulk", 
                data=json.dumps({"entities": column_entities}),
                headers=self.headers,
                auth=self.auth
            )
            
            if response.status_code == 200:
                logger.info(f"Created {len(columns)} columns for table {db_name}.{table_name}")
                return True
            else:
                logger.error(f"Failed to create columns: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error creating columns: {e}")
            return False
    
    def create_etl_process(self, process_name, input_tables, output_tables, 
                        description=None, owner="admin", cluster_name="primary",
                        process_type="ETL"):
        """Create an ETL process entity showing data lineage between tables."""
        # Process qualified name must be unique
        timestamp = int(time.time())
        qualified_name = f"{process_name}_{timestamp}@{cluster_name}"
        
        # Prepare inputs and outputs
        input_refs = []
        for input_table in input_tables:
            if isinstance(input_table, dict) and "guid" in input_table:
                input_refs.append({"guid": input_table["guid"], "typeName": "hive_table"})
            elif isinstance(input_table, str):
                # If string is provided, assume it's a GUID
                input_refs.append({"guid": input_table, "typeName": "hive_table"})
        
        output_refs = []
        for output_table in output_tables:
            if isinstance(output_table, dict) and "guid" in output_table:
                output_refs.append({"guid": output_table["guid"], "typeName": "hive_table"})
            elif isinstance(output_table, str):
                # If string is provided, assume it's a GUID
                output_refs.append({"guid": output_table, "typeName": "hive_table"})
        
        process_entity = {
            "entity": {
                "typeName": "Process",
                "attributes": {
                    "name": process_name,
                    "description": description or f"ETL process transforming data: {process_name}",
                    "qualifiedName": qualified_name,
                    "inputs": input_refs,
                    "outputs": output_refs,
                    "userName": owner,
                    "operationType": process_type,
                    "startTime": timestamp,
                    "endTime": timestamp + 100  # Add small amount to indicate completion
                }
            }
        }
        
        try:
            response = requests.post(
                f"{self.atlas_url}/api/atlas/v2/entity", 
                data=json.dumps(process_entity),
                headers=self.headers,
                auth=self.auth
            )
            
            if response.status_code == 200:
                result = response.json()
                guid = result.get('guidAssignments', {}).values()
                guid = list(guid)[0] if guid else None
                logger.info(f"Created ETL process '{process_name}' with GUID: {guid}")
                return guid
            else:
                logger.error(f"Failed to create ETL process: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error creating ETL process: {e}")
            return None
    
    def add_classification(self, entity_guid, classification_name, attributes=None):
        """Add a classification/tag to an entity."""
        classification = {
            "typeName": classification_name,
            "attributes": attributes or {}
        }
        
        try:
            response = requests.post(
                f"{self.atlas_url}/api/atlas/v2/entity/guid/{entity_guid}/classifications", 
                data=json.dumps([classification]),
                headers=self.headers,
                auth=self.auth
            )
            
            if response.status_code == 200:
                logger.info(f"Added classification '{classification_name}' to entity {entity_guid}")
                return True
            else:
                logger.error(f"Failed to add classification: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error adding classification: {e}")
            return False

def create_sample_etl_lineage(atlas_client, pipeline_name="sample_etl"):
    """Create a sample ETL pipeline with lineage in Atlas."""
    
    # Step 1: Create a database
    db_guid = atlas_client.create_hive_db("atlas_test")
    if not db_guid:
        logger.error("Failed to create database. Exiting.")
        return False
    
    # Step 2: Create source table with columns
    source_columns = [
        {"name": "id", "type": "int", "comment": "Primary identifier"},
        {"name": "name", "type": "string", "comment": "Person name"},
        {"name": "department", "type": "string", "comment": "Department name"},
        {"name": "salary", "type": "double", "comment": "Raw salary amount"}
    ]
    
    source_table_guid = atlas_client.create_hive_table(
        "source_data", 
        "atlas_test", 
        db_guid, 
        description="Raw source data for ETL processing",
        columns=source_columns
    )
    
    if not source_table_guid:
        logger.error("Failed to create source table. Exiting.")
        return False
    
    # Step 3: Create transformed table with columns
    transformed_columns = [
        {"name": "id", "type": "int", "comment": "Primary identifier"},
        {"name": "name", "type": "string", "comment": "Person name"},
        {"name": "department", "type": "string", "comment": "Department name"},
        {"name": "adjusted_salary", "type": "double", "comment": "Adjusted salary after calculations"}
    ]
    
    transformed_table_guid = atlas_client.create_hive_table(
        "transformed_data", 
        "atlas_test", 
        db_guid, 
        description="Transformed data with adjustments",
        columns=transformed_columns
    )
    
    if not transformed_table_guid:
        logger.error("Failed to create transformed table. Exiting.")
        return False
    
    # Step 4: Create analytics table with columns
    analytics_columns = [
        {"name": "id", "type": "int", "comment": "Primary identifier"},
        {"name": "name", "type": "string", "comment": "Person name"},
        {"name": "department", "type": "string", "comment": "Department name"},
        {"name": "department_category", "type": "string", "comment": "Department category grouping"},
        {"name": "adjusted_salary", "type": "double", "comment": "Adjusted salary"},
        {"name": "estimated_tax", "type": "double", "comment": "Estimated tax amount"}
    ]
    
    analytics_table_guid = atlas_client.create_hive_table(
        "analytics_data", 
        "atlas_test", 
        db_guid, 
        description="Final analytics data for reporting",
        columns=analytics_columns
    )
    
    if not analytics_table_guid:
        logger.error("Failed to create analytics table. Exiting.")
        return False
    
    # Step 5: Create ETL process for source to transformed (Extract + Transform)
    extract_transform_guid = atlas_client.create_etl_process(
        f"{pipeline_name}_extract_transform",
        [source_table_guid],
        [transformed_table_guid],
        description="Extract and transform process"
    )
    
    if not extract_transform_guid:
        logger.error("Failed to create extract-transform process. Exiting.")
        return False
    
    # Step 6: Create ETL process for transformed to analytics (Load + Enrich)
    load_enrich_guid = atlas_client.create_etl_process(
        f"{pipeline_name}_load_enrich",
        [transformed_table_guid],
        [analytics_table_guid],
        description="Load and enrich process"
    )
    
    if not load_enrich_guid:
        logger.error("Failed to create load-enrich process. Exiting.")
        return False
    
    # Step 7: Add classifications/tags to provide business context
    atlas_client.add_classification(source_table_guid, "ETL_Source")
    atlas_client.add_classification(transformed_table_guid, "ETL_Intermediate")
    atlas_client.add_classification(analytics_table_guid, "ETL_Target")
    
    logger.info("Successfully created complete ETL lineage in Atlas!")
    return True

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description="Atlas Metadata Ingestion Script")
    parser.add_argument("--atlas-url", default="http://localhost:21000", 
                        help="Atlas server URL (default: http://localhost:21000)")
    parser.add_argument("--username", default="admin", 
                        help="Atlas username (default: admin)")
    parser.add_argument("--password", default="admin", 
                        help="Atlas password (default: admin)")
    parser.add_argument("--pipeline-name", default="sample_etl", 
                        help="Name for the ETL pipeline (default: sample_etl)")
    
    args = parser.parse_args()
    
    # Initialize Atlas client
    atlas_client = AtlasMetadataIngestion(args.atlas_url, args.username, args.password)
    
    # Check connection
    if not atlas_client.check_connection():
        logger.error("Could not connect to Atlas. Please check the URL and credentials.")
        sys.exit(1)
    
    # Create sample ETL lineage
    success = create_sample_etl_lineage(atlas_client, args.pipeline_name)
    
    if success:
        logger.info("Metadata ingestion completed successfully.")
        sys.exit(0)
    else:
        logger.error("Metadata ingestion failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
