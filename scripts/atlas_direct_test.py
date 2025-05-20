#!/usr/bin/env python
"""
Direct Atlas API Integration Test Script
This script demonstrates direct interaction with the Atlas API to:
1. Check Atlas status
2. Create sample type definitions
3. Create sample metadata entities
4. Verify lineage creation
"""

import requests
import json
import time
import sys
from datetime import datetime

# Configuration
ATLAS_URL = "http://localhost:21000"
ATLAS_AUTH = ("admin", "admin")
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def check_atlas_status():
    """Check if Atlas is available and return version information."""
    try:
        response = requests.get(
            f"{ATLAS_URL}/api/atlas/admin/version",
            auth=ATLAS_AUTH,
            headers=HEADERS
        )
        
        if response.status_code == 200:
            print("✅ Atlas is running")
            version_info = response.json()
            print(f"   Version: {version_info.get('Version', 'unknown')}")
            return True
        else:
            print(f"❌ Atlas returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error connecting to Atlas: {str(e)}")
        return False

def get_entity_types():
    """Get the list of entity types defined in Atlas."""
    try:
        response = requests.get(
            f"{ATLAS_URL}/api/atlas/v2/types/typedefs",
            auth=ATLAS_AUTH,
            headers=HEADERS
        )
        
        if response.status_code == 200:
            typedefs = response.json()
            entity_types = typedefs.get("entityDefs", [])
            print(f"✅ Found {len(entity_types)} entity types in Atlas")
            
            # Print some examples
            print("   Examples:")
            for i, entity_type in enumerate(entity_types[:5]):
                print(f"   - {entity_type.get('name')}")
            
            return entity_types
        else:
            print(f"❌ Failed to get entity types: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error getting entity types: {str(e)}")
        return []

def create_sample_entities():
    """Create sample entities to demonstrate Atlas metadata capabilities."""
    # Sample ETL process entities
    etl_process = {
        "entities": [
            # Source CSV file
            {
                "typeName": "DataFile",
                "attributes": {
                    "name": "source_data.csv",
                    "qualifiedName": "file://data/source_data.csv",
                    "description": "Source CSV file containing raw data",
                    "format": "csv",
                    "size": 1024000,
                    "createTime": int(time.time() * 1000),
                    "modifiedTime": int(time.time() * 1000)
                }
            },
            # ETL Process
            {
                "typeName": "Process",
                "attributes": {
                    "name": "ETLTransformation",
                    "qualifiedName": "etl_pipeline.transformation",
                    "description": "ETL transformation process",
                    "inputs": [{"typeName": "DataFile", "uniqueAttributes": {"qualifiedName": "file://data/source_data.csv"}}],
                    "outputs": [{"typeName": "hive_table", "uniqueAttributes": {"qualifiedName": "default.transformed_data@primary"}}],
                    "startTime": int(time.time() * 1000),
                    "endTime": int(time.time() * 1000) + 60000,
                    "userName": "airflow"
                }
            },
            # Hive Table (Output)
            {
                "typeName": "hive_table",
                "attributes": {
                    "name": "transformed_data",
                    "qualifiedName": "default.transformed_data@primary",
                    "description": "Transformed data stored in Hive",
                    "owner": "airflow",
                    "temporary": False,
                    "createTime": int(time.time() * 1000),
                    "lastAccessTime": int(time.time() * 1000)
                }
            },
            # Hive Columns
            {
                "typeName": "hive_column",
                "attributes": {
                    "name": "id",
                    "qualifiedName": "default.transformed_data.id@primary",
                    "description": "Unique identifier",
                    "owner": "airflow",
                    "type": "int",
                    "comment": "Primary key",
                    "table": {"typeName": "hive_table", "uniqueAttributes": {"qualifiedName": "default.transformed_data@primary"}}
                }
            },
            {
                "typeName": "hive_column",
                "attributes": {
                    "name": "name",
                    "qualifiedName": "default.transformed_data.name@primary",
                    "description": "Employee name",
                    "owner": "airflow",
                    "type": "string",
                    "comment": "Full name of employee",
                    "table": {"typeName": "hive_table", "uniqueAttributes": {"qualifiedName": "default.transformed_data@primary"}}
                }
            },
            {
                "typeName": "hive_column",
                "attributes": {
                    "name": "age",
                    "qualifiedName": "default.transformed_data.age@primary",
                    "description": "Employee age",
                    "owner": "airflow",
                    "type": "int",
                    "comment": "Age in years",
                    "table": {"typeName": "hive_table", "uniqueAttributes": {"qualifiedName": "default.transformed_data@primary"}}
                }
            }
        ]
    }
    
    try:
        # Create the entities
        response = requests.post(
            f"{ATLAS_URL}/api/atlas/v2/entity/bulk",
            auth=ATLAS_AUTH,
            headers=HEADERS,
            data=json.dumps(etl_process)
        )
        
        if response.status_code == 200:
            result = response.json()
            created = result.get("mutatedEntities", {}).get("CREATE", [])
            print(f"✅ Successfully created {len(created)} entities")
            
            # Return the GUIDs of created entities
            return [entity.get("guid") for entity in created]
        else:
            print(f"❌ Failed to create entities: {response.status_code}")
            print(f"   Response: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Error creating entities: {str(e)}")
        return []

def verify_lineage(guid):
    """Verify lineage information for a specific entity."""
    try:
        response = requests.get(
            f"{ATLAS_URL}/api/atlas/v2/lineage/{guid}",
            auth=ATLAS_AUTH,
            headers=HEADERS
        )
        
        if response.status_code == 200:
            lineage = response.json()
            
            # Extract lineage information
            relations = lineage.get("relations", [])
            input_count = len([r for r in relations if r.get("relationshipType") == "input"])
            output_count = len([r for r in relations if r.get("relationshipType") == "output"])
            
            print(f"✅ Lineage verified for entity {guid}")
            print(f"   - Inputs: {input_count}")
            print(f"   - Outputs: {output_count}")
            return True
        else:
            print(f"❌ Failed to get lineage: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error verifying lineage: {str(e)}")
        return False

def list_hive_tables():
    """List all Hive tables registered in Atlas."""
    try:
        # Search for Hive tables
        query = {
            "typeName": "hive_table",
            "excludeDeletedEntities": True,
            "limit": 10
        }
        
        response = requests.post(
            f"{ATLAS_URL}/api/atlas/v2/search/basic",
            auth=ATLAS_AUTH,
            headers=HEADERS,
            data=json.dumps(query)
        )
        
        if response.status_code == 200:
            result = response.json()
            entities = result.get("entities", [])
            
            print(f"✅ Found {len(entities)} Hive tables")
            for entity in entities:
                name = entity.get("attributes", {}).get("name", "unknown")
                qualified_name = entity.get("attributes", {}).get("qualifiedName", "unknown")
                print(f"   - {name} ({qualified_name})")
                
            return entities
        else:
            print(f"❌ Failed to search for Hive tables: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error listing Hive tables: {str(e)}")
        return []

def main():
    """Main function to run the Atlas integration test."""
    print("=" * 80)
    print("ATLAS DIRECT INTEGRATION TEST")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Atlas URL: {ATLAS_URL}")
    print("=" * 80)
    
    # Check Atlas status
    if not check_atlas_status():
        print("❌ Cannot proceed because Atlas is not available")
        sys.exit(1)
    
    print("\n" + "=" * 80)
    print("GETTING ENTITY TYPES")
    print("=" * 80)
    entity_types = get_entity_types()
    
    print("\n" + "=" * 80)
    print("CREATING SAMPLE ENTITIES")
    print("=" * 80)
    entity_guids = create_sample_entities()
    
    if entity_guids:
        print("\n" + "=" * 80)
        print("VERIFYING LINEAGE")
        print("=" * 80)
        # Verify lineage for the Hive table
        for guid in entity_guids:
            verify_lineage(guid)
    
    print("\n" + "=" * 80)
    print("LISTING HIVE TABLES")
    print("=" * 80)
    list_hive_tables()
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
