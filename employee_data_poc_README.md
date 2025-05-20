# Employee Data POC with Apache Atlas Metadata Integration

This document provides comprehensive implementation details for the Proof of Concept (POC) that demonstrates metadata ingestion into Apache Atlas, integrated with an ETL pipeline for employee data.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Implementation Details](#implementation-details)
4. [Running the POC](#running-the-poc)
5. [Verifying Results](#verifying-results)
6. [Atlas UI Navigation](#atlas-ui-navigation)
7. [Extending the Solution](#extending-the-solution)
8. [FAQs](#faqs)
9. [Troubleshooting](#troubleshooting)

## Overview

This POC implements a complete ETL workflow that:

1. **Extracts** employee data from a CSV file
2. **Transforms** it using PySpark, adding derived columns for employee categorization
3. **Loads** transformed data into a PostgreSQL database
4. **Ingests metadata** into Apache Atlas, including:
   - Dataset metadata for source and target
   - Data lineage tracking transformations
   - Classifications for sensitive data (PII)
   - Business metadata for governance

The solution showcases how to automatically capture and maintain metadata about your data assets and processes, enabling data governance, lineage tracking, and compliance.

## Prerequisites

To run this POC, you need:

- **Apache Airflow** (≥ 2.0.0)
- **Apache Atlas** (2.3.0)
- **PostgreSQL** database
- **PySpark** (≥ 3.0.0)
- **Python** (≥ 3.8)

### Required Python Packages

- `apache-airflow`
- `apache-airflow-providers-postgres`
- `pyspark`
- `pandas`
- `requests`

### Connection Setup

Set up the following Airflow connections:

1. **Postgres Connection**:
   - Connection ID: postgres_default
   - Connection Type: Postgres
   - Host: localhost (or your PostgreSQL host)
   - Database: employee_db
   - Username: airflow (or your PostgreSQL username)
   - Password: airflow (or your PostgreSQL password)
   - Port: 5432

2. **Atlas Configuration (as Variables)**:
   - `atlas_host`: localhost (or your Atlas host)
   - `atlas_port`: 21000
   - `atlas_user`: admin (or your Atlas username)
   - `atlas_password`: admin (or your Atlas password)

## Implementation Details

### File Structure

```
apache_atlas/
├── dags/
│   └── employee_atlas_pipeline.py    # Airflow DAG implementation
├── data/
│   ├── employees.csv                 # Source CSV (created if not exists)
│   └── employees_transformed.csv     # Transformed data
├── etl_mapping.md                    # ETL mapping documentation
├── employee_data_poc_README.md       # This documentation
└── scripts/                          # Custom Atlas scripts
```

### Detailed Implementation

#### 1. Data Model

**Source Data (CSV):**
- `id` (INTEGER) - Employee identifier
- `name` (VARCHAR) - Employee full name
- `age` (INTEGER) - Employee age
- `salary` (DOUBLE) - Annual salary
- `department` (VARCHAR) - Department name

**Target Data (PostgreSQL):**
- All source columns, plus:
- `employee_category` (VARCHAR) - Derived from age
- `salary_band` (VARCHAR) - Derived from salary
- `processed_date` (DATE) - Processing timestamp

#### 2. Atlas Metadata

**Entity Types:**
- `fs_path` - File system entities (CSV files)
- `rdbms_table` - PostgreSQL table
- `rdbms_column` - Table columns
- `etl_process` - Custom process entity type

**Classifications:**
- `employee_data` - Applied to employee-related entities
- `PII` - Applied to personally identifiable columns

**Custom Attributes:**
- `process_type` - Tracks ETL process type
- `owner` - Tracks entity ownership

#### 3. Lineage Model

The lineage captures the complete flow of data:
- Source CSV → Transformation Process → Transformed CSV → Loading Process → PostgreSQL Table

Each entity and process is registered in Atlas with proper metadata and relationships.

## Running the POC

### 1. Start Required Services

Ensure Atlas, PostgreSQL, and Airflow are running:

```bash
# Start Atlas (if using Docker)
docker-compose -f docker-compose.yml up -d atlas

# Start PostgreSQL (if using Docker)
docker-compose -f docker-compose.yml up -d postgres

# Start Airflow (if using Docker)
docker-compose -f docker-compose.yml up -d airflow-webserver airflow-scheduler
```

### 2. Deploy the DAG

Copy the `employee_atlas_pipeline.py` file to your Airflow DAGs folder:

```bash
cp ./dags/employee_atlas_pipeline.py $AIRFLOW_HOME/dags/
```

### 3. Trigger the DAG

- Navigate to the Airflow UI (typically at http://localhost:8080)
- Find the `employee_atlas_pipeline` DAG in the list
- Enable the DAG if it's not already enabled
- Trigger a DAG run

### 4. Monitor Progress

- Monitor the DAG execution in the Airflow UI
- Check task logs for detailed progress information

## Verifying Results

### 1. Verify Data in PostgreSQL

Connect to PostgreSQL and verify the data was loaded:

```sql
SELECT * FROM employees LIMIT 10;
```

Expected output:
```
 id |    name    | age | salary | department | employee_category | salary_band | processed_date 
----+------------+-----+--------+------------+-------------------+-------------+---------------
  1 | John Doe   |  32 |  75000 | IT         | Mid-Level         | Band 2      | 2025-05-20
  2 | Jane Smith |  28 |  82000 | HR         | Junior            | Band 2      | 2025-05-20
  ...
```

### 2. Verify Metadata in Atlas

#### a. Search for Entities

1. Log in to Atlas UI (typically at http://localhost:21000)
2. Use the search bar at the top to search for:
   - `employees` (table name)
   - `employee_data` (classification)
   - `PII` (classification)

#### b. Explore Entity Details

Click on the `employees` table to view:
- **Attributes**: Table properties
- **Schema**: Column definitions with data types
- **Classifications**: Applied tags
- **Lineage**: Data flow visualization

#### c. Verify Lineage

1. Open the `employees` table
2. Click on the "Lineage" tab
3. Explore the lineage graph showing:
   - Source CSV file
   - Transformation process
   - Transformed CSV file
   - Loading process
   - Target PostgreSQL table

## Atlas UI Navigation

### Searching for Metadata

1. **Basic Search**:
   - Use the search bar at the top of the Atlas UI
   - Search for entity names, types, or classifications

2. **Advanced Search**:
   - Click "Search" in the left navigation menu
   - Use filters to search by:
     - Entity type
     - Classification
     - Property value
     - Creation time

3. **Saved Searches**:
   - Save frequently used searches for quick access

### Exploring Entity Details

When viewing an entity:

1. **Attributes**: View basic properties
2. **Classifications**: See applied tags
3. **Schema**: For tables, view column definitions
4. **Lineage**: Visualize data flow
5. **Relationships**: See connected entities
6. **Audit**: View change history

### Lineage Visualization

In the lineage view:

1. **Depth Control**: Adjust how many hops to display
2. **Filters**: Include/exclude entity types
3. **Layout**: Rearrange the lineage graph
4. **Details**: Click on entities for quick information

## Extending the Solution

### Adding More Data Sources

To add new data sources:

1. Create new extraction tasks in the DAG
2. Register the source in Atlas using the appropriate entity type
3. Create process entities to capture lineage

### Adding Business Metadata

To enhance business context:

1. Create business metadata types in Atlas
2. Add business metadata to entities using Atlas API
3. Update the DAG to include business metadata ingestion

### Implementing Data Quality Checks

To add data quality:

1. Add quality check tasks in the DAG
2. Record quality metrics as business metadata
3. Apply classifications for quality issues

## FAQs

### Q: What version of Apache Atlas is required?
A: This POC was tested with Apache Atlas 2.3.0, but should work with versions 2.0.0 and above.

### Q: Can I use other databases instead of PostgreSQL?
A: Yes, you can adapt the code to use any database supported by Airflow. Just update the entity types in Atlas accordingly.

### Q: How do I handle sensitive credentials?
A: In production, use Airflow's Secret Backend or environment variables rather than hardcoding credentials.

### Q: How can I schedule the metadata ingestion?
A: The DAG is configured to run daily by default. You can adjust the `schedule_interval` parameter for different frequencies.

## Troubleshooting

### Common Issues

#### Atlas Connection Issues
- Verify Atlas is running and accessible
- Check network connectivity from Airflow to Atlas
- Verify credentials are correct

#### Postgres Connection Issues
- Ensure the Postgres connection is properly configured in Airflow
- Verify the database exists and user has appropriate permissions

#### Airflow Task Failures
- Check task logs for detailed error messages
- Verify all required Python packages are installed
- Ensure file paths are accessible by the Airflow worker

### Logging

For advanced debugging:

1. Increase logging level in the DAG:
```python
logging.basicConfig(level=logging.DEBUG)
```

2. Check Atlas application logs:
```bash
docker exec -it atlas cat /opt/atlas/logs/application.log
```

---

This POC demonstrates a comprehensive approach to metadata management with Apache Atlas, showcasing how to capture and maintain metadata about your data assets and processes. By following this implementation, you can establish a foundation for data governance, lineage tracking, and compliance in your organization.
