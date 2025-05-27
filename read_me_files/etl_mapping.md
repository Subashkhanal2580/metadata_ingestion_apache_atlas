# Employee Data ETL Mapping Documentation

This document provides a detailed mapping of the ETL process for the employee data pipeline, including source data structure, transformations, and target schema.

## Table of Contents
- [Source Data](#source-data)
- [Transformations](#transformations)
- [Target Schema](#target-schema)
- [Lineage Diagram](#lineage-diagram)
- [Data Flow](#data-flow)
- [Atlas Metadata](#atlas-metadata)

## Source Data

### CSV Source File
**File Path**: `/opt/airflow/data/employees.csv`

| Column Name | Data Type | Description | Sample Value |
|-------------|-----------|-------------|--------------|
| id | INTEGER | Unique employee identifier | 1 |
| name | VARCHAR | Employee's full name | John Doe |
| age | INTEGER | Employee's age in years | 32 |
| salary | DOUBLE | Annual salary in USD | 75000 |
| department | VARCHAR | Department name | IT |

## Transformations

The following transformations are applied using PySpark:

| Transformation | Description | Implementation |
|----------------|-------------|----------------|
| Data Type Casting | Ensure proper data types | `.withColumn("salary", col("salary").cast("double"))` <br> `.withColumn("age", col("age").cast("integer"))` |
| Employee Categorization | Add category based on age | `.withColumn("employee_category", when(col("age") < 30, "Junior").when(col("age") < 40, "Mid-Level").otherwise("Senior"))` |
| Salary Band Classification | Classify by salary range | `.withColumn("salary_band", when(col("salary") < 75000, "Band 1").when(col("salary") < 90000, "Band 2").otherwise("Band 3"))` |
| Processing Timestamp | Add processing date | `.withColumn("processed_date", lit(datetime.now().strftime("%Y-%m-%d")))` |

### Derived Columns

| Column Name | Derived From | Logic | 
|-------------|--------------|-------|
| employee_category | age | <ul><li>age < 30: "Junior"</li><li>age < 40: "Mid-Level"</li><li>age >= 40: "Senior"</li></ul> |
| salary_band | salary | <ul><li>salary < 75000: "Band 1"</li><li>salary < 90000: "Band 2"</li><li>salary >= 90000: "Band 3"</li></ul> |
| processed_date | Current timestamp | Current date in YYYY-MM-DD format |

## Target Schema

### PostgreSQL Table
**Database**: `employee_db`
**Table**: `employees`

| Column Name | Data Type | Description | PII | Sample Value |
|-------------|-----------|-------------|-----|--------------|
| id | INTEGER | Employee ID (Primary Key) | No | 1 |
| name | VARCHAR(255) | Employee's full name | Yes | John Doe |
| age | INTEGER | Employee's age in years | Yes | 32 |
| salary | DOUBLE PRECISION | Annual salary in USD | Yes | 75000.00 |
| department | VARCHAR(100) | Department name | No | IT |
| employee_category | VARCHAR(50) | Derived seniority category | No | Mid-Level |
| salary_band | VARCHAR(50) | Derived salary classification | No | Band 2 |
| processed_date | DATE | Date record was processed | No | 2025-05-20 |

## Lineage Diagram

```
+-------------------+     +----------------------+     +-------------------+
|                   |     |                      |     |                   |
| Source CSV        |     | Transformed CSV      |     | PostgreSQL Table  |
| employees.csv     +---->+ employees_           +---->+ employee_db.     |
|                   |     | transformed.csv      |     | employees         |
|                   |     |                      |     |                   |
+-------------------+     +----------------------+     +-------------------+
        |                           |                          |
        v                           v                          v
+-------------------+     +----------------------+     +-------------------+
|                   |     |                      |     |                   |
| Atlas Entity      |     | Atlas Entity         |     | Atlas Entity      |
| fs_path           |     | fs_path              |     | rdbms_table       |
|                   |     |                      |     |                   |
+-------------------+     +----------------------+     +-------------------+
        |                           |                          |
        +---------------------------+--------------------------+
                                    |
                                    v
                           +-------------------+
                           |                   |
                           | Atlas Lineage     |
                           | Process Entities  |
                           |                   |
                           +-------------------+
```

## Data Flow

1. **Extraction Phase**:
   - Source data is read from CSV file
   - A corresponding `fs_path` entity is created in Atlas
   - Source data schema and metadata are captured

2. **Transformation Phase**:
   - PySpark reads the source CSV
   - Applies data type conversions
   - Derives new columns based on business rules
   - Writes transformed data to interim CSV
   - A second `fs_path` entity is created in Atlas
   - A process entity linking source to transformed data is created

3. **Loading Phase**:
   - PostgreSQL table is created if it doesn't exist
   - Transformed CSV data is loaded into the table
   - A `rdbms_table` entity is created in Atlas with column metadata
   - PII classifications are applied to sensitive columns
   - A process entity linking transformed data to the table is created

## Atlas Metadata

### Entity Types
| Entity Type | Description | Attributes |
|-------------|-------------|------------|
| fs_path | File system path entity | name, path, qualifiedName, description |
| rdbms_table | Relational database table | name, qualifiedName, description, owner |
| rdbms_column | Database column | name, qualifiedName, description, type |
| etl_process | Custom ETL process | name, qualifiedName, inputs, outputs, process_type, owner |

### Classifications
| Classification | Description | Applied To |
|----------------|-------------|------------|
| employee_data | Identifies employee-related entities | Source CSV, Target Table |
| PII | Personally Identifiable Information | name, age, salary columns |

### Business Metadata
The following business metadata is captured:

1. **Data Ownership**:
   - Owner: ETL_SERVICE
   - Steward: Data Engineering Team

2. **Data Quality**:
   - Last Processed: Current timestamp
   - Processing Status: Successful/Failed

3. **Governance**:
   - PII Classification: Applied to sensitive fields
   - Retention Policy: 7 years
   - Access Level: Restricted

### Atlas Search Examples

To find employee data in Atlas UI:

1. **Find all employee data**:
   - Search for classification: `employee_data`

2. **Find PII columns**:
   - Search for classification: `PII`

3. **Find PostgreSQL tables**:
   - Search for type: `rdbms_table`

4. **View lineage**:
   - Search for the table: `employees`
   - Click on it and select the "Lineage" tab
