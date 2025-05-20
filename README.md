# End-to-End ETL Pipeline with Airflow, Spark, Hive, and Atlas

This project implements an end-to-end ETL (Extract, Transform, Load) pipeline orchestrated by Apache Airflow, running in a Dockerized environment.

## Architecture Overview

The pipeline:
1. Extracts CSV data from a GitHub repository (simulated with a local file for testing)
2. Transforms the data using Apache Spark
3. Loads the transformed data into Apache Hive for storage
4. Ingests metadata into Apache Atlas for data governance

## Components

- **Apache Airflow**: Orchestrates the ETL workflow
- **Apache Spark**: Performs data transformation
- **Apache Hive**: Stores transformed data with schema
- **Apache Atlas**: Captures metadata including lineage

## Directory Structure

```
apache_atlas/
├── config/
│   └── hive-site.xml              # Hive configuration with Atlas hook
├── dags/
│   ├── etl_pipeline.py            # Airflow DAG definition
│   └── verify_metadata.py         # Atlas metadata verification module
├── scripts/
│   ├── spark_script.py            # Spark transformation script
│   ├── spark_load_hive.py         # Spark to Hive loading script
│   └── verify_metadata.py         # Atlas metadata verification script
├── docker-compose.yml             # Main Docker Compose file
├── docker-compose-atlas.yml       # Atlas-specific Docker Compose
├── sample_data.csv                # Sample CSV data for testing
└── README.md                      # Project documentation
```

## Prerequisites

- Docker and Docker Compose installed
- At least 8GB of RAM available for Docker
- Port 21000 (Atlas), 8080 (Airflow), 9083 (Hive Metastore), and 8090 (Spark UI) available

## Setup Instructions

1. Clone this repository
2. Start the Atlas service first:
   ```
   docker-compose -f docker-compose-atlas.yml up -d
   ```
3. Wait for Atlas to initialize (check logs with `docker logs atlas`)
4. Start the rest of the services:
   ```
   docker-compose up -d
   ```

## Accessing the Services

- **Apache Atlas UI**: http://localhost:21000 (admin/admin)
- **Apache Airflow UI**: http://localhost:8080 (admin/admin)
- **Apache Spark UI**: http://localhost:8090
- **Hive Web UI**: http://localhost:10002

## Running the ETL Pipeline

1. Verify all containers are running:
   ```
   docker ps
   ```

2. Trigger the ETL pipeline from Airflow UI:
   - Navigate to http://localhost:8080
   - Login with admin/admin
   - Find the `etl_pipeline` DAG and click "Trigger DAG"
   
3. Monitor the pipeline execution in Airflow

4. Verify data and metadata:
   - Check Hive data: Connect to Hive and run `SELECT * FROM default.transformed_data;`
   - Check Atlas metadata: Search for "transformed_data" in Atlas UI

## Monitoring and Debugging

- **Airflow logs**: Available in the Airflow UI or `docker logs airflow-scheduler`
- **Spark logs**: Available in the Spark UI or `docker logs spark`
- **Atlas logs**: `docker logs atlas`
- **Hive logs**: `docker logs hive`

## Understanding Data Lineage

After the pipeline runs successfully, you can view data lineage in Atlas:
1. Navigate to the Atlas UI (http://localhost:21000)
2. Search for "transformed_data"
3. Click on the found entity
4. Select the "Lineage" tab to view data flow from source to target

## Customization

- To use a different CSV source, update the `download_csv` function in `dags/etl_pipeline.py`
- To modify transformations, edit `scripts/spark_script.py`
- To change the Hive table schema, modify the table creation in `scripts/spark_load_hive.py`

## Troubleshooting

- **Atlas not starting**: Check if ports are already in use or increase memory allocation
- **Hive connection failures**: Ensure the Hive metastore is properly initialized
- **Spark transformation errors**: Check Spark logs for schema issues with the CSV data
- **Metadata not appearing in Atlas**: Verify the Atlas-Hive hook configuration in `hive-site.xml`

## Architecture Diagram

```
  +-----------+       +------------+       +----------+       +-----------+
  |           |       |            |       |          |       |           |
  |  CSV File +------>+    Spark   +------>+   Hive   +------>+   Atlas   |
  |           |       |            |       |          |       |           |
  +-----------+       +------------+       +----------+       +-----------+
        ^                   ^                   ^                  ^
        |                   |                   |                  |
        |                   |                   |                  |
        +-------------------+-------------------+------------------+
                                |
                        +---------------+
                        |               |
                        |    Airflow    |
                        |               |
                        +---------------+
```

## Notes

- This implementation uses embedded HBase and Solr for Atlas, which is suitable for development but not for production
- For production environments, consider using external HBase and Solr instances
- Update default credentials before deploying to production
