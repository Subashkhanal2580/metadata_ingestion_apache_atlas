from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime
import sys
import os
import requests
import time

# Add scripts directory to path for importing verify_metadata
sys.path.append('/opt/airflow/scripts')

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2025, 5, 19),
    'retries': 1,
}

# Define the DAG
dag = DAG(
    'atlas_integration_test',
    default_args=default_args,
    schedule_interval=None,  # Run manually
    catchup=False,
)

def check_atlas_status():
    """Check if Atlas is up and running."""
    atlas_url = "http://atlas:21000/api/atlas/admin/version"
    max_retries = 5
    retry_delay = 10  # seconds
    
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt+1}: Checking Atlas status...")
            response = requests.get(atlas_url, auth=("admin", "admin"), timeout=5)
            
            if response.status_code == 200:
                version_info = response.json()
                print(f"Atlas is running. Version: {version_info.get('Version', 'unknown')}")
                return True
            else:
                print(f"Atlas returned status code: {response.status_code}")
        except Exception as e:
            print(f"Error connecting to Atlas: {str(e)}")
        
        # If we're not at the last attempt, retry
        if attempt < max_retries - 1:
            print(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
    
    raise Exception("Could not connect to Atlas after multiple attempts")

def create_hive_table():
    """Create a sample Hive table for testing Atlas integration."""
    try:
        # Use a Hive connection to create a table
        hive_cmd = """
        CREATE DATABASE IF NOT EXISTS atlas_test;
        
        CREATE TABLE IF NOT EXISTS atlas_test.employees (
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
        
        # Execute the Hive commands (this assumes Hive is accessible)
        os.system("beeline -u jdbc:hive2://hive:10000 -n hive -p hive -f /tmp/hive_commands.hql")
        
        print("Hive table created and populated successfully")
        return True
    except Exception as e:
        print(f"Error creating Hive table: {str(e)}")
        raise

def verify_atlas_metadata():
    """Import and run the verify_metadata function from the scripts directory."""
    # Dynamically import the verify_metadata function
    try:
        from verify_metadata import verify_metadata
        # Override the Atlas URL and table name for our test
        result = verify_metadata(
            atlas_url="http://atlas:21000/api/atlas/v2/search/basic",
            table_name="employees",
            database="atlas_test",
            cluster_name="primary"
        )
        return result
    except Exception as e:
        print(f"Error verifying Atlas metadata: {str(e)}")
        raise

# Define the tasks
check_atlas = PythonOperator(
    task_id='check_atlas_status',
    python_callable=check_atlas_status,
    dag=dag,
)

create_table = PythonOperator(
    task_id='create_hive_table',
    python_callable=create_hive_table,
    dag=dag,
)

wait_for_metadata = BashOperator(
    task_id='wait_for_metadata_propagation',
    bash_command='sleep 60',  # Wait for metadata to propagate to Atlas
    dag=dag,
)

verify_metadata = PythonOperator(
    task_id='verify_atlas_metadata',
    python_callable=verify_atlas_metadata,
    dag=dag,
)

# Set the task dependencies
check_atlas >> create_table >> wait_for_metadata >> verify_metadata
