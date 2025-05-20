# Apache Atlas Monitoring and Operations Guide

This guide provides comprehensive information on monitoring, maintaining, and operating an Apache Atlas deployment integrated with an ETL pipeline.

## Table of Contents

1. [Monitoring Setup](#monitoring-setup)
2. [Health Checks](#health-checks)
3. [Performance Metrics](#performance-metrics)
4. [Logging](#logging)
5. [Backup and Recovery](#backup-and-recovery)
6. [Troubleshooting](#troubleshooting)
7. [Scaling Considerations](#scaling-considerations)
8. [Maintenance Tasks](#maintenance-tasks)

## Monitoring Setup

### Prometheus Integration

Atlas exposes metrics through JMX that can be collected with Prometheus. To set this up:

1. Add JMX Exporter to Atlas:

```yaml
# jmx_exporter_config.yaml
---
startDelaySeconds: 0
ssl: false
lowercaseOutputName: false
lowercaseOutputLabelNames: false
rules:
  - pattern: ".*"
```

2. Add the following to Atlas startup parameters:

```
ATLAS_OPTS="$ATLAS_OPTS -javaagent:/path/to/jmx_prometheus_javaagent.jar=7070:/path/to/jmx_exporter_config.yaml"
```

3. Configure Prometheus to scrape these metrics:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'atlas'
    scrape_interval: 15s
    static_configs:
      - targets: ['atlas:7070']
```

### Grafana Dashboard

Set up a Grafana dashboard to visualize Atlas metrics:

1. Import a pre-built JVM dashboard (ID: 4701)
2. Create custom panels for Atlas-specific metrics:
   - Entity creation rate
   - Search performance
   - API response times
   - Error rates

## Health Checks

### Basic Health Check Script

```python
#!/usr/bin/env python
import requests
import sys
import json

def check_atlas_health(url="http://atlas:21000"):
    try:
        # Check if Atlas admin API is accessible
        response = requests.get(
            f"{url}/api/atlas/admin/version",
            auth=("admin", "admin"),
            timeout=10
        )
        if response.status_code == 200:
            print(f"✅ Atlas is running. Version: {response.json().get('Version', 'unknown')}")
            return 0
        else:
            print(f"❌ Atlas returned unexpected status code: {response.status_code}")
            return 1
    except Exception as e:
        print(f"❌ Failed to connect to Atlas: {e}")
        return 1

if __name__ == "__main__":
    atlas_url = sys.argv[1] if len(sys.argv) > 1 else "http://atlas:21000"
    sys.exit(check_atlas_health(atlas_url))
```

### Docker Health Check

Integrate with Docker health checks:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:21000/api/atlas/admin/version"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

## Performance Metrics

Key metrics to monitor:

| Metric | Description | Warning Threshold | Critical Threshold |
|--------|-------------|-------------------|-------------------|
| JVM Heap Usage | Memory usage of the JVM | 80% | 90% |
| Search Latency | Response time for search queries | 2s | 5s |
| Entity Create Rate | Rate of entity creation | Depends on load | Depends on load |
| API Error Rate | Percentage of API calls resulting in errors | 5% | 10% |
| Solr Index Size | Size of the Solr index | 80% of capacity | 90% of capacity |
| Graph Database Size | Size of the JanusGraph database | 80% of capacity | 90% of capacity |
| Active User Sessions | Number of concurrent user sessions | Depends on resources | Depends on resources |

## Logging

### Log Configuration

Configure Atlas to generate appropriate logs:

```properties
# log4j.properties
log4j.rootLogger=INFO, file
log4j.appender.file=org.apache.log4j.RollingFileAppender
log4j.appender.file.File=/var/log/atlas/application.log
log4j.appender.file.MaxFileSize=10MB
log4j.appender.file.MaxBackupIndex=10
log4j.appender.file.layout=org.apache.log4j.PatternLayout
log4j.appender.file.layout.ConversionPattern=%d{yyyy-MM-dd HH:mm:ss} %-5p %c{1}:%L - %m%n

# Enable debug logging for specific components if needed
log4j.logger.org.apache.atlas=INFO
log4j.logger.org.apache.atlas.repository=INFO
log4j.logger.org.apache.atlas.notification=INFO
```

### Log Aggregation

Integrate Atlas logs with a centralized logging system:

1. Use Filebeat to ship logs:

```yaml
# filebeat.yml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/atlas/*.log
  fields:
    application: atlas
    environment: production
  fields_under_root: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
```

2. Create Kibana dashboards for visualization and alerting

## Backup and Recovery

### Database Backup Strategy

1. Atlas data is stored in:
   - JanusGraph (or other graph database)
   - Solr (for search)
   - HBase (if using HBase as backend)

2. Backup procedures:
   - **JanusGraph**: Use the backup utility provided by the backend storage (Cassandra/HBase)
   - **Solr**: Use SolrCloud backup collection command
   - **HBase**: Use snapshot feature

Example HBase snapshot script:

```bash
#!/bin/bash
# Atlas HBase backup script
DATE=$(date +%Y%m%d_%H%M%S)
echo "Creating HBase snapshot for Atlas tables..."
hbase shell <<EOF
snapshot 'atlas_janus', 'atlas_backup_$DATE'
exit
EOF
echo "Exporting snapshot..."
hbase org.apache.hadoop.hbase.snapshot.ExportSnapshot \
  -snapshot atlas_backup_$DATE \
  -copy-to hdfs://backup-cluster/hbase/backups/
echo "Backup completed."
```

### Recovery Procedure

Document detailed recovery steps:

1. Stop Atlas service
2. Restore backend databases from backup
3. Verify data integrity
4. Start Atlas service
5. Validate functionality through health check API

## Troubleshooting

### Common Issues and Solutions

| Issue | Possible Causes | Solutions |
|-------|----------------|-----------|
| Atlas fails to start | JVM memory issues | Increase heap size in atlas-env.sh |
| | Database connectivity | Check connection to backend databases |
| | Port conflicts | Verify port availability |
| Slow search performance | Solr indexing issues | Optimize Solr configuration |
| | Large dataset | Add resources, consider sharding |
| Entity creation failures | Schema validation errors | Check entity payload against expected schema |
| | Backend database issues | Verify database connectivity and performance |
| Missing metadata | Hook configuration issues | Verify hook installation and configuration |
| | Notification failures | Check Kafka queue (if used) |

### Diagnostic Commands

```bash
# Check Atlas process
ps -ef | grep atlas

# Check Atlas logs
tail -f /var/log/atlas/application.log

# Verify backend connectivity
curl -u admin:admin -X GET http://atlas:21000/api/atlas/admin/status

# Check entity count
curl -u admin:admin -X GET http://atlas:21000/api/atlas/v2/search/basic \
  -H "Content-Type: application/json" \
  -d '{"typeName":"hive_table"}'
```

## Scaling Considerations

### Horizontal Scaling

Atlas can be scaled horizontally by:

1. Deploying multiple Atlas server instances behind a load balancer
2. Ensuring all instances share the same backend databases
3. Configuring sticky sessions for the web UI

### Vertical Scaling

Tune Atlas for better performance:

```properties
# atlas-application.properties
atlas.graph.storage.backend=hbase
atlas.graph.storage.hbase.table=atlas
atlas.graph.index.search.backend=solr
atlas.graph.index.search.solr.zookeeper-url=zookeeper:2181/solr
atlas.notification.embedded=false
atlas.kafka.zookeeper.connect=zookeeper:2181
atlas.kafka.bootstrap.servers=kafka:9092
atlas.server.xsrf.filterEnabled=true

# JVM settings in atlas-env.sh
export ATLAS_SERVER_HEAP="-Xms4g -Xmx4g -XX:+UseG1GC"
```

## Maintenance Tasks

### Regular Maintenance Schedule

| Task | Frequency | Description |
|------|-----------|------------|
| Patch Updates | Monthly | Apply security and bug fix patches |
| Database Optimization | Quarterly | Optimize backend databases (Solr, graph DB) |
| Credential Rotation | Quarterly | Update service account credentials |
| Full Backup | Weekly | Complete backup of all Atlas data |
| Log Rotation | Daily | Rotate and archive logs |
| Configuration Audit | Quarterly | Review and update configuration |
| Access Audit | Monthly | Review user access and permissions |

### Upgrade Procedure

1. **Pre-upgrade**:
   - Backup all data
   - Document current configuration
   - Test upgrade in a staging environment

2. **Upgrade Steps**:
   - Stop Atlas service
   - Update software
   - Run migration scripts if needed
   - Verify configuration compatibility
   - Start service

3. **Post-upgrade**:
   - Verify functionality
   - Check for schema migration issues
   - Update monitoring and dashboards if needed

This maintenance guide should be reviewed and updated regularly to reflect changes in the deployment architecture and operational practices.
