# End-to-End ETL Pipeline with Apache Atlas Integration

This project implements an end-to-end ETL (Extract, Transform, Load) pipeline orchestrated by Apache Airflow, with Apache Spark for transformation, Apache Hive for storage, and Apache Atlas for data governance and metadata management.

## Overview

The pipeline follows these steps:
1. Extract a CSV file from a GitHub repository (or use a provided sample file)
2. Transform the data using Apache Spark
3. Load the transformed data into Apache Hive for storage
4. Ingest metadata into Apache Atlas for data governance

## Project Structure

```
apache_atlas/
├── config/
│   └── hive-site.xml              # Hive configuration with Atlas hook
├── dags/
│   ├── etl_pipeline.py            # Main Airflow DAG
│   ├── atlas_integration_test.py  # Initial Atlas integration test
│   ├── atlas_integration_test_fixed.py # Updated integration test
│   └── atlas_integration_final.py # Final Atlas integration DAG
├── scripts/
│   ├── spark_script.py            # Spark transformation script
│   ├── spark_load_hive.py         # Spark to Hive loading script
│   ├── verify_metadata.py         # Atlas metadata verification
│   └── atlas_direct_test.py       # Direct Atlas API testing script
├── data/
│   └── sample_data.csv            # Sample data for testing
├── docker-compose.yml             # Main Docker Compose file
├── docker-compose-atlas.yml       # Atlas container configuration
├── docker-compose-hive.yml        # Initial Hive configuration
├── docker-compose-hive-fixed.yml  # Updated Hive configuration
├── integration_documentation.md   # Detailed integration docs
├── etl_pipeline_instructions.md   # Step-by-step instructions
└── README_FINAL.md                # This file
```

## Key Components

### 1. Apache Atlas
- Central repository for metadata governance
- Captures table schemas, column definitions, and data lineage
- Provides a web UI for exploring metadata relationships

### 2. Apache Airflow
- Orchestrates the ETL workflow
- Schedules and monitors task execution
- Provides visibility into pipeline progress

### 3. Apache Spark
- Performs data transformation
- Filters and processes the extracted data
- Prepares data for loading into Hive

### 4. Apache Hive
- Stores the transformed data
- Integrates with Atlas via the Hive hook
- Enables SQL-based querying of the processed data

## Implementation Highlights

### Atlas Integration
The integration with Atlas is primarily achieved through:
1. The Atlas Hive hook, configured in `hive-site.xml`
2. Direct Atlas API interaction for metadata verification

### Data Lineage
The pipeline captures data lineage automatically:
1. Source CSV file → Spark transformation → Hive table
2. Lineage information is viewable in the Atlas UI under the "Lineage" tab

### Metadata Governance
Atlas provides governance capabilities:
1. Automatic schema capture
2. Metadata search and discovery
3. Relationship visualization
4. Classification and tagging (for future enhancement)

## Getting Started

Follow the detailed instructions in `etl_pipeline_instructions.md` to:
1. Start Apache Atlas
2. Deploy Hive services
3. Run the ETL pipeline
4. Verify metadata in Atlas

## Atlas UI Access
- URL: http://localhost:21000
- Username: admin
- Password: admin

## Troubleshooting

Common issues and their solutions are documented in:
1. `integration_documentation.md` - Section 5
2. `etl_pipeline_instructions.md` - Troubleshooting section

## Future Enhancements

1. **Security**: Implement proper authentication and authorization
2. **Scaling**: Configure for larger datasets and higher throughput
3. **Advanced Governance**: Utilize Atlas's classification and tagging features
4. **Monitoring**: Add alerts and notifications for pipeline failures
5. **Automated Testing**: Implement comprehensive test suite

## References

- [Apache Atlas Documentation](https://atlas.apache.org/)
- [Apache Hive-Atlas Integration](https://atlas.apache.org/#/HookHive)
- [Apache Airflow Documentation](https://airflow.apache.org/)
- [Apache Spark Documentation](https://spark.apache.org/)
