#!/usr/bin/env python
"""
Atlas Integration Demo Script

This script demonstrates creating and managing metadata entities in Apache Atlas
using the REST API directly. It shows how to create and link entities similar to
what would be captured during an ETL process with proper Hive integration.
"""

import requests
import json
import time
import sys
from datetime import datetime
import uuid

# Atlas connection settings
ATLAS_URL = "http://localhost:21000/api/atlas"
ATLAS_AUTH = ("admin", "admin")
HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}

def print_separator(title=""):
    """Print a separator line with optional title."""
    print("\n" + "=" * 80)
    if title:
        print(title)
        print("=" * 80)

def check_atlas_status():
    """Check if Atlas is running and return version info."""
    try:
        response = requests.get(f"{ATLAS_URL}/admin/version", auth=ATLAS_AUTH)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Atlas returned status code {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error connecting to Atlas: {e}")
        return None

def get_all_entity_types():
    """Get all entity types defined in Atlas."""
    try:
        response = requests.get(f"{ATLAS_URL}/v2/types/typedefs", auth=ATLAS_AUTH)
        if response.status_code == 200:
            data = response.json()
            entity_defs = data.get('entityDefs', [])
            return [entity_def.get('name') for entity_def in entity_defs]
        else:
            print(f"❌ Failed to get entity types: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def create_hive_db_entity(db_name="etl_demo"):
    """Create a Hive database entity in Atlas."""
    entity = {
        "entity": {
            "typeName": "hive_db",
            "attributes": {
                "name": db_name,
                "description": "Database for ETL demo",
                "owner": "admin",
                "clusterName": "primary",
                "qualifiedName": f"{db_name}@primary"
            }
        }
    }
    
    try:
        response = requests.post(
            f"{ATLAS_URL}/v2/entity", 
            data=json.dumps(entity),
            headers=HEADERS,
            auth=ATLAS_AUTH
        )
        
        if response.status_code == 200:
            guid = response.json().get('guidAssignments', {}).values()
            print(f"✅ Created Hive database '{db_name}' with GUID: {list(guid)[0] if guid else 'Unknown'}")
            return list(guid)[0] if guid else None
        else:
            print(f"❌ Failed to create Hive database: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def create_hive_table_entity(db_guid, table_name="transformed_data"):
    """Create a Hive table entity in Atlas with a reference to the database."""
    qualified_name = f"etl_demo.{table_name}@primary"
    
    entity = {
        "entity": {
            "typeName": "hive_table",
            "attributes": {
                "name": table_name,
                "description": "Table containing transformed data from ETL process",
                "owner": "admin",
                "qualifiedName": qualified_name,
                "db": {"guid": db_guid, "typeName": "hive_db"},
                "createTime": int(time.time() * 1000),
                "lastAccessTime": int(time.time() * 1000),
                "columns": []
            }
        }
    }
    
    try:
        response = requests.post(
            f"{ATLAS_URL}/v2/entity", 
            data=json.dumps(entity),
            headers=HEADERS,
            auth=ATLAS_AUTH
        )
        
        if response.status_code == 200:
            guid = response.json().get('guidAssignments', {}).values()
            print(f"✅ Created Hive table '{table_name}' with GUID: {list(guid)[0] if guid else 'Unknown'}")
            return list(guid)[0] if guid else None
        else:
            print(f"❌ Failed to create Hive table: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def create_table_columns(table_guid, table_name="transformed_data"):
    """Create columns for the Hive table."""
    columns = [
        {"name": "id", "type": "int", "comment": "Primary identifier"},
        {"name": "name", "type": "string", "comment": "Name field"},
        {"name": "department", "type": "string", "comment": "Department designation"},
        {"name": "salary", "type": "double", "comment": "Annual salary amount"}
    ]
    
    column_entities = []
    
    for col in columns:
        qualified_name = f"etl_demo.{table_name}.{col['name']}@primary"
        column_entity = {
            "typeName": "hive_column",
            "attributes": {
                "name": col["name"],
                "type": col["type"],
                "comment": col["comment"],
                "qualifiedName": qualified_name,
                "table": {"guid": table_guid, "typeName": "hive_table"}
            }
        }
        column_entities.append(column_entity)
    
    try:
        response = requests.post(
            f"{ATLAS_URL}/v2/entity/bulk", 
            data=json.dumps({"entities": column_entities}),
            headers=HEADERS,
            auth=ATLAS_AUTH
        )
        
        if response.status_code == 200:
            print(f"✅ Created {len(columns)} columns for table")
            return True
        else:
            print(f"❌ Failed to create columns: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def create_etl_process(input_guid, output_guid):
    """Create an ETL process entity showing data lineage."""
    process_name = f"etl_process_{int(time.time())}"
    qualified_name = f"{process_name}@primary"
    
    process_entity = {
        "entity": {
            "typeName": "Process",
            "attributes": {
                "name": process_name,
                "description": "ETL process transforming source data to target table",
                "qualifiedName": qualified_name,
                "inputs": [{"guid": input_guid, "typeName": "hive_table"}],
                "outputs": [{"guid": output_guid, "typeName": "hive_table"}],
                "userName": "admin"
            }
        }
    }
    
    try:
        response = requests.post(
            f"{ATLAS_URL}/v2/entity", 
            data=json.dumps(process_entity),
            headers=HEADERS,
            auth=ATLAS_AUTH
        )
        
        if response.status_code == 200:
            guid = response.json().get('guidAssignments', {}).values()
            print(f"✅ Created ETL process with GUID: {list(guid)[0] if guid else 'Unknown'}")
            return list(guid)[0] if guid else None
        else:
            print(f"❌ Failed to create ETL process: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def search_entities(entity_type, query_text=None):
    """Search for entities of a specific type."""
    query = {
        "typeName": entity_type
    }
    
    if query_text:
        query["entityFilters"] = {
            "condition": "AND",
            "criterion": [
                {
                    "attributeName": "name",
                    "operator": "contains",
                    "attributeValue": query_text
                }
            ]
        }
    
    try:
        response = requests.post(
            f"{ATLAS_URL}/v2/search/basic", 
            data=json.dumps(query),
            headers=HEADERS,
            auth=ATLAS_AUTH
        )
        
        if response.status_code == 200:
            entities = response.json().get('entities', [])
            return entities
        else:
            print(f"❌ Failed to search entities: {response.status_code}")
            print(f"   Response: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def main():
    """Main function demonstrating Atlas integration."""
    print_separator("ATLAS INTEGRATION DEMO")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Atlas URL: {ATLAS_URL}")
    print_separator()
    
    # Check Atlas status
    version_info = check_atlas_status()
    if version_info:
        print(f"✅ Atlas is running")
        print(f"   Version: {version_info.get('Version', 'Unknown')}")
    else:
        print("❌ Atlas is not available. Exiting.")
        sys.exit(1)
    
    # Get entity types
    print_separator("GETTING ENTITY TYPES")
    entity_types = get_all_entity_types()
    if entity_types:
        print(f"✅ Found {len(entity_types)} entity types in Atlas")
        print("   Examples:")
        for i, et in enumerate(entity_types[:5]):
            print(f"   - {et}")
    else:
        print("❌ No entity types found")
        sys.exit(1)
    
    # Create source and target tables
    print_separator("CREATING SAMPLE ENTITIES")
    
    # Create database
    db_guid = create_hive_db_entity()
    if not db_guid:
        print("❌ Failed to create database. Exiting.")
        sys.exit(1)
    
    # Create source table
    source_table_guid = create_hive_table_entity(db_guid, "source_data")
    if not source_table_guid:
        print("❌ Failed to create source table. Exiting.")
        sys.exit(1)
    
    # Add columns to source table
    create_table_columns(source_table_guid, "source_data")
    
    # Create target table
    target_table_guid = create_hive_table_entity(db_guid, "transformed_data")
    if not target_table_guid:
        print("❌ Failed to create target table. Exiting.")
        sys.exit(1)
    
    # Add columns to target table
    create_table_columns(target_table_guid, "transformed_data")
    
    # Create ETL process linking source and target
    etl_process_guid = create_etl_process(source_table_guid, target_table_guid)
    if not etl_process_guid:
        print("❌ Failed to create ETL process. Exiting.")
        sys.exit(1)
    
    # Search for created entities
    print_separator("VERIFYING CREATED ENTITIES")
    tables = search_entities("hive_table")
    print(f"✅ Found {len(tables)} Hive tables")
    for table in tables:
        print(f"   - {table.get('displayText')}")
    
    processes = search_entities("Process")
    print(f"✅ Found {len(processes)} processes")
    for process in processes:
        print(f"   - {process.get('displayText')}")
    
    print_separator("DEMO COMPLETE")
    print("Visit Atlas UI at http://localhost:21000 to view the metadata and lineage")
    print("Login with admin/admin")
    
if __name__ == "__main__":
    main()
