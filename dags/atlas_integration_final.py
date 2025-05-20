from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime
import sys
import os
import requests
import time
import subprocess

# Add scripts directory to path for importing verify_metadata
sys.path.append('/opt/airflow/scripts')

# Add scripts directory to path for importing the Atlas metadata ingestion module
try:
    from atlas_metadata_ingestion import AtlasMetadataIngestion, create_sample_etl_lineage
except ImportError:
    # For local development without Airflow
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))
    from atlas_metadata_ingestion import AtlasMetadataIngestion, create_sample_etl_lineage

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2025, 5, 19),
    'retries': 2,
    'retry_delay': 60,
}

# Define the DAG
dag = DAG(
    'atlas_integration_final',
    default_args=default_args,
    schedule_interval=None,  # Run manually
    catchup=False,
)

def check_atlas_status():
    """Check if Atlas is up and running."""
    atlas_url = "http://atlas:21000"
    try:
        # Create an Atlas client instance
        atlas_client = AtlasMetadataIngestion(atlas_url)
        
        # Check connection
        if atlas_client.check_connection():
            print("✅ Atlas connection successful")
            return True
        else:
            print("❌ Could not connect to Atlas")
            return False
    except Exception as e:
        print(f"❌ Error checking Atlas status: {str(e)}")
        raise

def create_hive_table():
    """Create a sample Hive table for testing Atlas integration using HiveServer2."""
    try:
        # Define Hive commands to create table and load data
        hive_cmd = """
        CREATE DATABASE IF NOT EXISTS atlas_test;
        
        DROP TABLE IF EXISTS atlas_test.employees;
        
        CREATE TABLE atlas_test.employees (
            id INT,
            name STRING,
            age INT,
            department STRING,
            salary DOUBLE
        ) COMMENT 'Employee data for Atlas integration test';
        
        INSERT INTO atlas_test.employees VALUES 
            (1, 'John Doe', 45, 'Engineering', 85000),
            (2, 'Jane Smith', 22, 'Marketing', 62000),
            (3, 'Robert Johnson', 17, 'Intern', 25000),
            (4, 'Lisa Williams', 29, 'Sales', 71000),
            (5, 'Michael Brown', 19, 'Intern', 27000),
            (6, 'Sarah Miller', 38, 'Finance', 92000),
            (7, 'David Wilson', 16, 'Intern', 24000),
            (8, 'Jennifer Taylor', 31, 'Human Resources', 68000),
            (9, 'William Davis', 55, 'Executive', 120000),
            (10, 'Emily Anderson', 27, 'Engineering', 75000);
        
        SELECT * FROM atlas_test.employees LIMIT 5;
        """
        
        # Write the Hive commands to a file
        with open('/tmp/hive_commands.hql', 'w') as f:
            f.write(hive_cmd)
        
        # Execute the Hive commands using beeline
        beeline_cmd = [
            "beeline", 
            "-u", "jdbc:hive2://hive-server:10000",
            "-n", "hive",
            "-p", "hive",
            "-f", "/tmp/hive_commands.hql"
        ]
        
        print(f"Executing Hive commands with beeline: {' '.join(beeline_cmd)}")
        result = subprocess.run(beeline_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error executing Hive commands: {result.stderr}")
            raise Exception(f"Hive command failed with exit code {result.returncode}")
        
        print(f"Hive command output: {result.stdout}")
        print("Hive table created and populated successfully")
        return True
    except Exception as e:
        print(f"Error creating Hive table: {str(e)}")
        raise

def ingest_metadata_to_atlas():
    """Ingest metadata into Atlas using the direct API approach."""
    atlas_url = "http://atlas:21000"
    pipeline_name = f"etl_pipeline_{int(time.time())}"
    
    try:
        print(f"Ingesting metadata for ETL pipeline: {pipeline_name}")
        
        # Create Atlas client
        atlas_client = AtlasMetadataIngestion(atlas_url)
        
        # Create the ETL lineage in Atlas
        success = create_sample_etl_lineage(atlas_client, pipeline_name)
        
        if success:
            print("✅ Successfully ingested metadata into Atlas")
            return True
        else:
            print("❌ Failed to ingest metadata into Atlas")
            return False
    except Exception as e:
        print(f"❌ Error ingesting metadata: {str(e)}")
        raise

def verify_metadata_in_atlas():
    """Verify that metadata has been properly ingested into Atlas."""
    atlas_url = "http://atlas:21000"
    auth = ("admin", "admin")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    
    # Create Atlas client
    atlas_client = AtlasMetadataIngestion(atlas_url)
    
    # Define the entities we expect to find
    expected_entities = [
        {"type": "hive_db", "name": "atlas_test"},
        {"type": "hive_table", "name": "source_data"},
        {"type": "hive_table", "name": "transformed_data"},
        {"type": "hive_table", "name": "analytics_data"}
    ]
    
    # Check each expected entity
    missing_entities = []
    for entity in expected_entities:
        found_entity = atlas_client.get_entity_by_attribute(entity["type"], "name", entity["name"])
        if not found_entity:
            missing_entities.append(f"{entity['type']}:{entity['name']}")
    
    if missing_entities:
        print(f"❌ The following entities are missing in Atlas: {', '.join(missing_entities)}")
        return False
    
    print("✅ All expected entities are present in Atlas")
    
    # Check for lineage - verify the transformed_data table has lineage
    transformed_entity = atlas_client.get_entity_by_attribute("hive_table", "name", "transformed_data")
    if transformed_entity:
        table_guid = transformed_entity['guid']
        lineage_url = f"{atlas_url}/api/atlas/v2/lineage/{table_guid}"
        lineage_response = requests.get(lineage_url, auth=auth)
        
        if lineage_response.status_code == 200:
            lineage_data = lineage_response.json()
            relations = lineage_data.get('relations', {})
            if relations and len(relations) > 0:
                print("✅ Lineage information is available!") 
                return True
            else:
                print("⚠️ Lineage information is missing or incomplete")
    
    return False

def create_atlas_dashboard():
    """Simulate creating an Atlas dashboard with metadata insights."""
    print("Creating Atlas metadata dashboard...")
    print("1. Analyzing metadata structure")
    print("2. Identifying key data assets")
    print("3. Generating data flow visualizations")
    print("4. Preparing governance reports")
    
    # This would typically generate a report or dashboard
    # For simulation purposes, we'll just return success
    time.sleep(2)  # Simulate some processing time
    return True

# Define DAG tasks
check_atlas_task = PythonOperator(
    task_id='check_atlas_status',
    python_callable=check_atlas_status,
    dag=dag,
)

simulate_etl_task = PythonOperator(
    task_id='simulate_etl_process',
    python_callable=simulate_etl_process,
    dag=dag,
)

ingest_metadata_task = PythonOperator(
    task_id='ingest_metadata_to_atlas',
    python_callable=ingest_metadata_to_atlas,
    dag=dag,
)

verify_metadata_task = PythonOperator(
    task_id='verify_metadata_in_atlas',
    python_callable=verify_metadata_in_atlas,
    dag=dag,
)

create_dashboard_task = PythonOperator(
    task_id='create_atlas_dashboard',
    python_callable=create_atlas_dashboard,
    dag=dag,
)

# Set task dependencies
check_atlas_task >> simulate_etl_task >> ingest_metadata_task >> verify_metadata_task >> create_dashboard_task

# Add documentation
"""### Atlas Integration ETL Pipeline

This DAG demonstrates a complete ETL pipeline with Apache Atlas integration for metadata management and data lineage.

#### Tasks:
1. **check_atlas_status**: Verifies that Atlas is running and accessible
2. **simulate_etl_process**: Simulates an ETL process (extraction, transformation, loading)
3. **ingest_metadata_to_atlas**: Creates metadata entities in Atlas via the API to represent the ETL pipeline
4. **verify_metadata_in_atlas**: Confirms that entities and lineage are properly created in Atlas
5. **create_atlas_dashboard**: Creates a simulated dashboard for metadata insights

#### Benefits:
- Complete metadata capture for data assets
- Automated lineage tracking between source and target tables
- Governance capabilities through Atlas UI

Run this DAG to see how metadata is automatically captured for your ETL processes.
"""
