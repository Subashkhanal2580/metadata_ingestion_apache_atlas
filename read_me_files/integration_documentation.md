# Apache Atlas Integration for ETL Pipeline

This document outlines the integration of Apache Atlas with the ETL pipeline components (Airflow, Spark, and Hive) for metadata governance and lineage tracking.

## 1. Architecture Overview

The ETL pipeline integrates the following components:
- **Apache Airflow**: Orchestrates the workflow
- **Apache Spark**: Performs data transformations
- **Apache Hive**: Stores transformed data
- **Apache Atlas**: Captures metadata and lineage

![Architecture Diagram](https://i.imgur.com/example.png)

## 2. Integration Points

### 2.1 Hive to Atlas Integration

The primary integration point is between Hive and Atlas through the Atlas Hive hook. This hook automatically captures:
- Table schemas
- Column definitions and data types
- Table statistics
- Data lineage

#### Hive Configuration for Atlas (hive-site.xml):
```xml
<configuration>
  <!-- Atlas Hook Configuration -->
  <property>
    <name>atlas.cluster.name</name>
    <value>primary</value>
  </property>
  
  <property>
    <name>atlas.rest.address</name>
    <value>http://atlas:21000</value>
  </property>
  
  <property>
    <name>atlas.hook.hive.synchronous</name>
    <value>true</value>
  </property>
  
  <!-- Hive Atlas Hook -->
  <property>
    <name>hive.exec.post.hooks</name>
    <value>org.apache.atlas.hive.hook.HiveHook</value>
  </property>
</configuration>
```

### 2.2 Airflow to Atlas Integration

Airflow orchestrates the ETL pipeline and can verify metadata ingestion in Atlas using its API.

#### Atlas Verification in Airflow (Python Script):
```python
import requests
import json
import time

def verify_metadata(
    atlas_url="http://atlas:21000/api/atlas/v2/search/basic", 
    table_name="employees", 
    database="atlas_test", 
    cluster_name="primary"
):
    """Verify that Hive table metadata has been ingested into Atlas."""
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    auth = ("admin", "admin")
    
    query = {
        "typeName": "hive_table",
        "query": table_name,
        "limit": 10
    }
    
    # Implement retry logic
    max_retries = 5
    retry_delay = 10  # initial delay in seconds
    
    for attempt in range(max_retries):
        try:
            response = requests.post(atlas_url, json=query, headers=headers, auth=auth)
            
            if response.status_code == 200:
                result = response.json()
                entities = result.get("entities", [])
                
                if entities:
                    return True
            
            # If we need to retry
            if attempt < max_retries - 1:
                retry_seconds = retry_delay * (2 ** attempt)
                time.sleep(retry_seconds)
            
        except Exception as e:
            pass
    
    return False
```

### 2.3 Spark to Hive Integration

Spark loads data into Hive, which then triggers the Atlas Hive hook for metadata capture.

#### Spark-Hive Integration (Python Script):
```python
from pyspark.sql import SparkSession

def load_to_hive(input_path, hive_table, database="default"):
    """Load Spark DataFrame into Hive table, triggering Atlas hook."""
    
    # Initialize Spark session with Hive support
    spark = SparkSession.builder \
        .appName("ETLHiveLoad") \
        .config("spark.sql.catalogImplementation", "hive") \
        .config("spark.hadoop.hive.metastore.uris", "thrift://hive-metastore:9083") \
        .getOrCreate()
    
    # Read data
    df = spark.read.parquet(input_path)
    
    # Create database if it doesn't exist
    spark.sql(f"CREATE DATABASE IF NOT EXISTS {database}")
    
    # Save to Hive table
    df.write.mode("overwrite").saveAsTable(f"{database}.{hive_table}")
    
    spark.stop()
```

## 3. Configuration Requirements

### 3.1 Network Configuration

All services must be on the same Docker network (e.g., `etl_network`) to communicate with each other:

```yaml
networks:
  etl_network:
    driver: bridge
```

### 3.2 Environment Variables

Hive requires these environment variables for Atlas integration:

```yaml
environment:
  - HIVE_SITE_CONF_atlas_cluster_name=primary
  - HIVE_SITE_CONF_atlas_rest_address=http://atlas:21000
  - HIVE_SITE_CONF_atlas_hook_hive_synchronous=true
  - HIVE_SITE_CONF_hive_exec_post_hooks=org.apache.atlas.hive.hook.HiveHook
```

## 4. Verification and Testing

### 4.1 Verifying Atlas Integration

1. Access Atlas UI: http://localhost:21000 (admin/admin)
2. Navigate to "Search" tab
3. Search for table name or database
4. Verify schema and lineage information

### 4.2 Testing Metadata Propagation

```python
# Create Hive table
spark.sql("""
CREATE TABLE IF NOT EXISTS test_db.test_table (
  id INT,
  name STRING,
  value DOUBLE
) COMMENT 'Test table for Atlas integration'
""")

# Insert data
spark.sql("""
INSERT INTO test_db.test_table VALUES
  (1, 'Test1', 100.0),
  (2, 'Test2', 200.0)
""")

# Wait for metadata propagation (typically 30-60 seconds)
time.sleep(60)

# Verify in Atlas
verify_metadata(table_name="test_table", database="test_db")
```

## 5. Troubleshooting

### 5.1 Atlas Hook Configuration

If metadata is not appearing in Atlas, verify:
- Hive has the correct Atlas hook configuration
- Atlas is accessible from the Hive container
- Atlas and Hive are on the same Docker network

### 5.2 Network Connectivity

Test connectivity between containers:
```bash
docker exec hive-server ping -c 2 atlas
docker exec atlas ping -c 2 hive-server
```

### 5.3 Logs

Check logs for errors:
```bash
docker logs atlas | grep ERROR
docker logs hive-server | grep atlas
```

## 6. Production Considerations

For production environments:
- Use external HBase and Solr for Atlas (not embedded)
- Implement security (TLS, authentication) for all components
- Set up monitoring and alerting for the ETL pipeline
- Implement proper error handling and retry logic
- Consider scaling options for Hive and Spark
