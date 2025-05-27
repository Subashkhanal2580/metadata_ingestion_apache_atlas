# ETL Pipeline with Apache Atlas - Implementation Instructions

This guide provides detailed steps to implement and run the ETL pipeline with Apache Atlas integration. Follow these instructions in order to set up each component and verify the integration.

## Prerequisites

- Docker and Docker Compose installed
- At least 8GB of RAM available for the containers
- Ports 21000 (Atlas), 8080 (Airflow), 10000 (Hive), and 8090 (Spark) available

## Step 1: Start Apache Atlas

Atlas is the central metadata repository that will track all data assets and their lineage.

```bash
# Start Atlas container
docker-compose -f docker-compose-atlas.yml up -d

# Check Atlas status (may take 3-5 minutes to fully initialize)
docker logs atlas --tail 20
```

**Verification**: Access Atlas UI at http://localhost:21000 with credentials admin/admin.

## Step 2: Start Hive Server

Hive will store the transformed data and integrate with Atlas for metadata tracking.

```bash
# Start Hive and related services
docker-compose -f docker-compose-hive-fixed.yml up -d

# Verify Hive services are running
docker ps | grep hive
```

**Verification**: You should see hive-server, hive-metastore, and hive-metastore-postgresql containers running.

## Step 3: Create Test Data

We'll use a sample dataset for our ETL process.

```bash
# Make sure the data directory exists
mkdir -p data

# Copy the sample data for processing
cp sample_data.csv data/
```

## Step 4: Run the Direct Atlas Test

This will test direct integration with Atlas by creating sample entities and verifying lineage.

```bash
# Install the required Python packages
pip install requests

# Run the Atlas direct test script
python scripts/atlas_direct_test.py
```

**Verification**: The script should output successful creation of entities and verification of lineage.

## Step 5: Run the ETL Pipeline

Since we have an existing Airflow setup, we'll use it to trigger our ETL pipeline.

```bash
# Copy the DAG file to Airflow
docker cp dags/atlas_integration_final.py metadata_ingestion-airflow-scheduler-1:/opt/airflow/dags/

# Restart Airflow scheduler to pick up the new DAG
docker restart metadata_ingestion-airflow-scheduler-1

# Unpause and trigger the DAG
docker exec metadata_ingestion-airflow-scheduler-1 airflow dags unpause atlas_integration_final
docker exec metadata_ingestion-airflow-scheduler-1 airflow dags trigger atlas_integration_final
```

**Verification**: Monitor the Airflow DAG execution in the Airflow UI (http://localhost:8080).

## Step 6: Verify Metadata in Atlas

After the pipeline runs, check Atlas for the captured metadata.

1. Open Atlas UI at http://localhost:21000
2. Navigate to Search tab
3. Search for either:
   - Type: `hive_table`
   - Text: `transformed_data`
4. Click on the search result to view details
5. Check the "Lineage" tab to see data flow visualization

## Step 7: Run Custom Queries in Hive

You can run queries on the transformed data in Hive.

```bash
# Connect to Hive server and run a query
docker exec hive-server beeline -u "jdbc:hive2://localhost:10000" -e "SELECT * FROM transformed_data LIMIT 10;"
```

## Troubleshooting

### Atlas Not Initializing

If Atlas fails to initialize properly:

```bash
# Check Atlas logs
docker logs atlas

# Restart Atlas
docker restart atlas
```

### Hive Connectivity Issues

If you experience connectivity issues with Hive:

```bash
# Check Hive server logs
docker logs hive-server

# Verify network connectivity
docker network inspect etl_network
```

### Metadata Not Appearing in Atlas

If metadata is not appearing in Atlas after running the pipeline:

1. Verify the Atlas hook is properly configured in Hive
2. Check that all containers are on the same network
3. Increase the wait time for metadata propagation (default is 120 seconds)
4. Check Atlas logs for any ingestion errors

## Next Steps

After successfully implementing this ETL pipeline with Atlas integration, consider:

1. **Security Enhancements**: Implement proper authentication and authorization
2. **Monitoring**: Set up monitoring for the pipeline components
3. **Scaling**: Configure for larger datasets and more frequent processing
4. **Advanced Governance**: Utilize Atlas's classification and tagging features for better governance
5. **Automated Testing**: Add automated tests for the complete pipeline
