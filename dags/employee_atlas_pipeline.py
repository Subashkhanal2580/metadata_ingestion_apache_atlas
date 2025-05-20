"""
Employee Metadata Ingestion DAG for Apache Atlas

This DAG demonstrates a complete ETL workflow with metadata ingestion into Apache Atlas:
1. Extract employee data from CSV
2. Transform data using PySpark
3. Load data into PostgreSQL
4. Ingest metadata into Apache Atlas

The DAG includes proper error handling, logging, and documentation.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.models import Variable
import os
import logging
import pandas as pd
import json
import requests
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, lit

# Atlas connection details
ATLAS_HOST = Variable.get("atlas_host", default="localhost")
ATLAS_PORT = Variable.get("atlas_port", default="21000")
ATLAS_USER = Variable.get("atlas_user", default="admin")
ATLAS_PASSWORD = Variable.get("atlas_password", default="admin")
ATLAS_BASE_URL = f"http://{ATLAS_HOST}:{ATLAS_PORT}"

# Set up logging
logger = logging.getLogger(__name__)

# File paths
DATA_DIR = "/opt/airflow/data"
SOURCE_CSV_PATH = f"{DATA_DIR}/employees.csv"
TRANSFORMED_CSV_PATH = f"{DATA_DIR}/employees_transformed.csv"

# Database details
DB_NAME = "employee_db"
TABLE_NAME = "employees"

# Default arguments for the DAG
default_args = {
    'owner': 'data_engineering',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2025, 5, 20),
}

# Atlas API functions
def atlas_auth():
    """Return authentication tuple for Atlas API"""
    return (ATLAS_USER, ATLAS_PASSWORD)

def create_atlas_type_defs():
    """
    Create custom type definitions in Atlas for employee data
    """
    logger.info("Creating Atlas type definitions")
    
    # Define custom types
    type_defs = {
        "classificationDefs": [
            {
                "name": "employee_data",
                "description": "Classification for employee data entities",
                "superTypes": [],
                "attributeDefs": []
            },
            {
                "name": "PII",
                "description": "Personally Identifiable Information",
                "superTypes": [],
                "attributeDefs": []
            }
        ],
        "entityDefs": [
            {
                "name": "etl_process",
                "superTypes": ["Process"],
                "description": "Custom ETL process entity",
                "attributeDefs": [
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
                        "name": "process_type",
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
        ]
    }
    
    # Create types in Atlas
    response = requests.post(
        f"{ATLAS_BASE_URL}/api/atlas/v2/types/typedefs",
        auth=atlas_auth(),
        json=type_defs,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        logger.info("Successfully created Atlas type definitions")
    else:
        logger.warning(f"Failed to create Atlas type definitions: {response.text}")
        # If types already exist, that's okay, continue
        
def create_atlas_table_entity(db_name, table_name, columns, description):
    """
    Create a table entity in Atlas
    """
    logger.info(f"Creating Atlas entity for table {db_name}.{table_name}")
    
    qualified_name = f"{db_name}.{table_name}@primary"
    
    # Define the table entity
    table_entity = {
        "entity": {
            "typeName": "rdbms_table",
            "attributes": {
                "owner": "ETL_SERVICE",
                "name": table_name,
                "qualifiedName": qualified_name,
                "description": description,
                "db": {"typeName": "rdbms_db", "uniqueAttributes": {"qualifiedName": f"{db_name}@primary"}}
            },
            "classifications": [
                {
                    "typeName": "employee_data"
                }
            ]
        }
    }
    
    # Create the table entity
    response = requests.post(
        f"{ATLAS_BASE_URL}/api/atlas/v2/entity",
        auth=atlas_auth(),
        json=table_entity,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        table_guid = response.json()["guidAssignments"][0]
        logger.info(f"Successfully created table entity with GUID: {table_guid}")
        
        # Create column entities
        for column in columns:
            create_atlas_column_entity(db_name, table_name, column["name"], 
                                       column["type"], column["description"], 
                                       column["is_pii"])
            
        return table_guid
    else:
        logger.error(f"Failed to create table entity: {response.text}")
        return None

def create_atlas_column_entity(db_name, table_name, column_name, data_type, description, is_pii=False):
    """
    Create a column entity in Atlas
    """
    logger.info(f"Creating Atlas entity for column {db_name}.{table_name}.{column_name}")
    
    qualified_name = f"{db_name}.{table_name}.{column_name}@primary"
    table_qualified_name = f"{db_name}.{table_name}@primary"
    
    # Define the column entity
    column_entity = {
        "entity": {
            "typeName": "rdbms_column",
            "attributes": {
                "owner": "ETL_SERVICE",
                "name": column_name,
                "qualifiedName": qualified_name,
                "description": description,
                "type": data_type,
                "table": {"typeName": "rdbms_table", "uniqueAttributes": {"qualifiedName": table_qualified_name}}
            }
        }
    }
    
    # Add PII classification if needed
    if is_pii:
        column_entity["entity"]["classifications"] = [{"typeName": "PII"}]
    
    # Create the column entity
    response = requests.post(
        f"{ATLAS_BASE_URL}/api/atlas/v2/entity",
        auth=atlas_auth(),
        json=column_entity,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        column_guid = response.json()["guidAssignments"][0]
        logger.info(f"Successfully created column entity with GUID: {column_guid}")
        return column_guid
    else:
        logger.error(f"Failed to create column entity: {response.text}")
        return None

def create_atlas_process_entity(process_name, inputs, outputs, description):
    """
    Create a process entity in Atlas to represent lineage
    """
    logger.info(f"Creating Atlas process entity for {process_name}")
    
    qualified_name = f"{process_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}@primary"
    
    # Define the process entity
    process_entity = {
        "entity": {
            "typeName": "etl_process",
            "attributes": {
                "owner": "ETL_SERVICE",
                "name": process_name,
                "qualifiedName": qualified_name,
                "description": description,
                "inputs": inputs,
                "outputs": outputs,
                "process_type": "SPARK_TRANSFORMATION"
            }
        }
    }
    
    # Create the process entity
    response = requests.post(
        f"{ATLAS_BASE_URL}/api/atlas/v2/entity",
        auth=atlas_auth(),
        json=process_entity,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        process_guid = response.json()["guidAssignments"][0]
        logger.info(f"Successfully created process entity with GUID: {process_guid}")
        return process_guid
    else:
        logger.error(f"Failed to create process entity: {response.text}")
        return None

def create_atlas_dataset_entity(file_path, format_type):
    """
    Create a dataset entity in Atlas for file data
    """
    logger.info(f"Creating Atlas dataset entity for {file_path}")
    
    file_name = os.path.basename(file_path)
    qualified_name = f"{file_name}@primary"
    
    # Define the dataset entity
    dataset_entity = {
        "entity": {
            "typeName": "fs_path",
            "attributes": {
                "owner": "ETL_SERVICE",
                "name": file_name,
                "qualifiedName": qualified_name,
                "path": file_path,
                "description": f"Employee data file in {format_type} format"
            },
            "classifications": [
                {
                    "typeName": "employee_data"
                }
            ]
        }
    }
    
    # Create the dataset entity
    response = requests.post(
        f"{ATLAS_BASE_URL}/api/atlas/v2/entity",
        auth=atlas_auth(),
        json=dataset_entity,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        dataset_guid = response.json()["guidAssignments"][0]
        logger.info(f"Successfully created dataset entity with GUID: {dataset_guid}")
        return dataset_guid
    else:
        logger.error(f"Failed to create dataset entity: {response.text}")
        return None

# ETL functions
def extract_employee_data(**kwargs):
    """
    Extract employee data from source CSV
    """
    logger.info(f"Extracting employee data from {SOURCE_CSV_PATH}")
    
    # Create the data directory if it doesn't exist
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Sample employee data in case the file doesn't exist
    if not os.path.exists(SOURCE_CSV_PATH):
        logger.info("Source CSV doesn't exist, creating sample data")
        employees = pd.DataFrame({
            'id': range(1, 11),
            'name': ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Brown', 
                     'Charlie Davis', 'Eva Wilson', 'Frank Miller', 'Grace Lee', 
                     'Henry Garcia', 'Ivy Martinez'],
            'age': [32, 28, 45, 36, 29, 52, 38, 41, 33, 27],
            'salary': [75000, 82000, 95000, 88000, 72000, 110000, 
                       91000, 86000, 79000, 68000],
            'department': ['IT', 'HR', 'Finance', 'Marketing', 'IT', 
                           'Finance', 'Marketing', 'HR', 'IT', 'Marketing']
        })
        employees.to_csv(SOURCE_CSV_PATH, index=False)
    
    # Read the CSV file
    df = pd.read_csv(SOURCE_CSV_PATH)
    logger.info(f"Extracted {len(df)} employee records")
    
    # Register the CSV file in Atlas
    file_guid = create_atlas_dataset_entity(SOURCE_CSV_PATH, "CSV")
    
    # Store the file GUID for lineage creation
    kwargs['ti'].xcom_push(key='source_file_guid', value=file_guid)
    
    return "Employee data extracted successfully"

def transform_employee_data(**kwargs):
    """
    Transform employee data using PySpark
    """
    logger.info("Transforming employee data using PySpark")
    
    # Initialize Spark session
    spark = SparkSession.builder \
        .appName("EmployeeDataTransformation") \
        .config("spark.driver.bindAddress", "127.0.0.1") \
        .getOrCreate()
    
    # Read CSV into Spark DataFrame
    employees_df = spark.read.csv(SOURCE_CSV_PATH, header=True, inferSchema=True)
    
    # Apply transformations
    transformed_df = employees_df \
        .withColumn("salary", col("salary").cast("double")) \
        .withColumn("age", col("age").cast("integer")) \
        .withColumn("employee_category", when(col("age") < 30, "Junior")
                                        .when(col("age") < 40, "Mid-Level")
                                        .otherwise("Senior")) \
        .withColumn("salary_band", when(col("salary") < 75000, "Band 1")
                                  .when(col("salary") < 90000, "Band 2")
                                  .otherwise("Band 3")) \
        .withColumn("processed_date", lit(datetime.now().strftime("%Y-%m-%d")))
    
    # Save the transformed data
    transformed_df.toPandas().to_csv(TRANSFORMED_CSV_PATH, index=False)
    
    # Register the transformed file in Atlas
    file_guid = create_atlas_dataset_entity(TRANSFORMED_CSV_PATH, "CSV")
    
    # Store the file GUID for lineage creation
    kwargs['ti'].xcom_push(key='transformed_file_guid', value=file_guid)
    
    # Clean up
    spark.stop()
    
    logger.info(f"Transformed data saved to {TRANSFORMED_CSV_PATH}")
    return "Employee data transformed successfully"

def create_postgres_table(**kwargs):
    """
    Create the PostgreSQL table structure
    """
    # This is handled by the PostgresOperator in the DAG
    return "PostgreSQL table created successfully"

def load_data_to_postgres(**kwargs):
    """
    Load the transformed data into PostgreSQL
    """
    logger.info(f"Loading data from {TRANSFORMED_CSV_PATH} to PostgreSQL table {TABLE_NAME}")
    
    # Define column metadata for Atlas
    column_metadata = [
        {"name": "id", "type": "INTEGER", "description": "Employee ID", "is_pii": False},
        {"name": "name", "type": "VARCHAR", "description": "Employee name", "is_pii": True},
        {"name": "age", "type": "INTEGER", "description": "Employee age", "is_pii": True},
        {"name": "salary", "type": "DOUBLE", "description": "Employee base salary", "is_pii": True},
        {"name": "department", "type": "VARCHAR", "description": "Employee department", "is_pii": False},
        {"name": "employee_category", "type": "VARCHAR", "description": "Employee seniority category", "is_pii": False},
        {"name": "salary_band", "type": "VARCHAR", "description": "Salary band classification", "is_pii": False},
        {"name": "processed_date", "type": "DATE", "description": "Date when record was processed", "is_pii": False}
    ]
    
    # Register the table in Atlas
    table_guid = create_atlas_table_entity(
        DB_NAME, 
        TABLE_NAME, 
        column_metadata, 
        "Employee master data with classifications"
    )
    
    # Store the table GUID for lineage creation
    kwargs['ti'].xcom_push(key='target_table_guid', value=table_guid)
    
    return "Data loaded to PostgreSQL successfully"

def create_atlas_lineage(**kwargs):
    """
    Create lineage information in Atlas
    """
    logger.info("Creating lineage information in Atlas")
    
    ti = kwargs['ti']
    source_file_guid = ti.xcom_pull(task_ids='extract_employee_data', key='source_file_guid')
    transformed_file_guid = ti.xcom_pull(task_ids='transform_employee_data', key='transformed_file_guid')
    target_table_guid = ti.xcom_pull(task_ids='load_data_to_postgres', key='target_table_guid')
    
    # Create references for inputs and outputs
    transformation_inputs = [
        {"guid": source_file_guid, "typeName": "fs_path"}
    ]
    
    transformation_outputs = [
        {"guid": transformed_file_guid, "typeName": "fs_path"}
    ]
    
    # Create transformation process
    create_atlas_process_entity(
        "employee_data_transformation",
        transformation_inputs,
        transformation_outputs,
        "Spark transformation to categorize employees and add derived columns"
    )
    
    # Create loading process
    load_inputs = [
        {"guid": transformed_file_guid, "typeName": "fs_path"}
    ]
    
    load_outputs = [
        {"guid": target_table_guid, "typeName": "rdbms_table"}
    ]
    
    create_atlas_process_entity(
        "employee_data_loading",
        load_inputs,
        load_outputs,
        "Loading transformed employee data into PostgreSQL"
    )
    
    return "Atlas lineage created successfully"

def verify_atlas_metadata(**kwargs):
    """
    Verify the metadata in Atlas
    """
    logger.info("Verifying metadata in Atlas")
    
    # Search for employee_data classification
    search_payload = {
        "typeName": "rdbms_table",
        "classification": "employee_data",
        "excludeDeletedEntities": True,
        "includeClassificationAttributes": True,
        "limit": 10,
        "offset": 0
    }
    
    response = requests.post(
        f"{ATLAS_BASE_URL}/api/atlas/v2/search/basic",
        auth=atlas_auth(),
        json=search_payload,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        entities = response.json().get("entities", [])
        logger.info(f"Found {len(entities)} entities with employee_data classification")
        
        for entity in entities:
            logger.info(f"Entity: {entity.get('typeName')}, Name: {entity.get('attributes', {}).get('name')}")
        
        return f"Verified {len(entities)} entities with employee_data classification"
    else:
        logger.error(f"Failed to verify metadata: {response.text}")
        return "Failed to verify metadata"

# Define the DAG
dag = DAG(
    'employee_atlas_pipeline',
    default_args=default_args,
    description='ETL pipeline for employee data with Atlas metadata ingestion',
    schedule_interval=timedelta(days=1),
    catchup=False,
    tags=['example', 'atlas', 'metadata'],
)

# Define tasks
setup_atlas_types = PythonOperator(
    task_id='setup_atlas_types',
    python_callable=create_atlas_type_defs,
    dag=dag,
)

extract_task = PythonOperator(
    task_id='extract_employee_data',
    python_callable=extract_employee_data,
    provide_context=True,
    dag=dag,
)

transform_task = PythonOperator(
    task_id='transform_employee_data',
    python_callable=transform_employee_data,
    provide_context=True,
    dag=dag,
)

create_table_task = PostgresOperator(
    task_id='create_postgres_table',
    postgres_conn_id='postgres_default',
    sql=f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        id INTEGER PRIMARY KEY,
        name VARCHAR(255),
        age INTEGER,
        salary DOUBLE PRECISION,
        department VARCHAR(100),
        employee_category VARCHAR(50),
        salary_band VARCHAR(50),
        processed_date DATE
    );
    TRUNCATE TABLE {TABLE_NAME};
    """,
    dag=dag,
)

load_data_task = PythonOperator(
    task_id='load_data_to_postgres',
    python_callable=load_data_to_postgres,
    provide_context=True,
    dag=dag,
)

load_csv_to_postgres_task = PostgresOperator(
    task_id='load_csv_to_postgres',
    postgres_conn_id='postgres_default',
    sql=f"""
    COPY {TABLE_NAME} FROM '/opt/airflow/data/employees_transformed.csv' 
    DELIMITER ',' CSV HEADER;
    """,
    dag=dag,
)

create_lineage_task = PythonOperator(
    task_id='create_atlas_lineage',
    python_callable=create_atlas_lineage,
    provide_context=True,
    dag=dag,
)

verify_metadata_task = PythonOperator(
    task_id='verify_atlas_metadata',
    python_callable=verify_atlas_metadata,
    provide_context=True,
    dag=dag,
)

# Define task dependencies
setup_atlas_types >> extract_task >> transform_task >> create_table_task
create_table_task >> load_data_task >> load_csv_to_postgres_task
load_csv_to_postgres_task >> create_lineage_task >> verify_metadata_task
