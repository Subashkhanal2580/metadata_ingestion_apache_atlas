# Apache Atlas Data Lineage Visualization Guide

This guide provides comprehensive information on leveraging Apache Atlas for data lineage visualization and data quality monitoring in an ETL pipeline.

## Table of Contents

1. [Data Lineage Overview](#data-lineage-overview)
2. [Lineage Capture Methods](#lineage-capture-methods)
3. [Visualizing Lineage in Atlas UI](#visualizing-lineage-in-atlas-ui)
4. [Extending Lineage with Custom Processes](#extending-lineage-with-custom-processes)
5. [Data Quality Integration](#data-quality-integration)
6. [Advanced Lineage Querying](#advanced-lineage-querying)
7. [Exporting Lineage Data](#exporting-lineage-data)

## Data Lineage Overview

Data lineage in Apache Atlas provides a visual representation of how data flows through your organization, showing:

- Source data origins
- Transformation processes and their impact
- Downstream dependencies
- Temporal aspects of data movement
- Process execution details

Lineage information helps with:

- **Impact analysis**: Identify what downstream processes are affected by changes
- **Root cause analysis**: Trace data issues back to their source
- **Compliance reporting**: Show complete data flow for audit purposes
- **Data governance**: Understand how sensitive data moves through your systems

## Lineage Capture Methods

### 1. Native Hooks

Atlas provides native hooks for many data processing tools:

- **Hive Hook**: Captures metadata from Hive DDL/DML operations
- **Spark Hook**: Records Spark job inputs, outputs, and transformations
- **Kafka Hook**: Tracks topics, producers, and consumers
- **Storm Hook**: Captures Storm topology and component details

Example Hive Hook configuration (in `hive-site.xml`):

```xml
<property>
  <name>hive.exec.post.hooks</name>
  <value>org.apache.atlas.hive.hook.HiveHook</value>
</property>
<property>
  <name>atlas.hook.hive.synchronous</name>
  <value>true</value>
</property>
<property>
  <name>atlas.rest.address</name>
  <value>http://atlas-server:21000</value>
</property>
```

### 2. Direct API Integration

For custom applications or tools without native hooks:

```python
def record_lineage_via_api(process_name, input_datasets, output_datasets, atlas_url, auth):
    """Create a process entity showing lineage between datasets."""
    qualified_name = f"{process_name}_{int(time.time())}"
    
    # Prepare input and output entity references
    input_refs = [{"guid": input_ds, "typeName": "DataSet"} for input_ds in input_datasets]
    output_refs = [{"guid": output_ds, "typeName": "DataSet"} for output_ds in output_datasets]
    
    # Create process entity
    process_entity = {
        "entity": {
            "typeName": "Process",
            "attributes": {
                "name": process_name,
                "qualifiedName": qualified_name,
                "inputs": input_refs,
                "outputs": output_refs
            }
        }
    }
    
    # Send to Atlas API
    response = requests.post(
        f"{atlas_url}/api/atlas/v2/entity",
        json=process_entity,
        auth=auth,
        headers={"Content-Type": "application/json"}
    )
    
    return response.json()
```

### 3. Custom ETL Process Annotations

For ETL pipelines, you can annotate your code to capture lineage:

```python
# Example for an Airflow DAG with Atlas lineage tracking
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

# Import Atlas lineage tracking library
from atlas_lineage_tracker import track_lineage

def transform_data(input_file, output_table, **kwargs):
    # Perform data transformation
    df = read_file(input_file)
    transformed_df = apply_transformations(df)
    write_to_table(transformed_df, output_table)
    
    # Track lineage in Atlas
    track_lineage(
        process_name="data_transformation",
        input_datasets=[input_file],
        output_datasets=[output_table],
        transformation_details={
            "transformations": ["filter", "aggregation"],
            "columns_added": ["total_amount", "category_group"],
            "columns_removed": ["raw_timestamp"]
        }
    )

with DAG('etl_with_lineage', start_date=datetime(2023, 1, 1)) as dag:
    transform_task = PythonOperator(
        task_id='transform_data',
        python_callable=transform_data,
        op_kwargs={
            'input_file': 'hdfs://data/raw/sales.csv',
            'output_table': 'hive://sales.transformed_sales'
        }
    )
```

## Visualizing Lineage in Atlas UI

### Basic Lineage Visualization

1. Log in to the Atlas UI (e.g., http://atlas-server:21000)
2. Search for an entity (e.g., a Hive table or dataset)
3. Click on the entity to view its details
4. Select the "Lineage" tab to view the visualization

### Understanding the Lineage Graph

The lineage graph consists of:

- **Nodes**: Represent entities (tables, files, views, etc.)
- **Edges**: Represent processes that transform data
- **Direction**: Typically flows from left (source) to right (target)

### Lineage Visualization Options

You can customize the lineage view:

- **Depth**: Control how many hops to display (1 to 5+)
- **Direction**: Show inputs, outputs, or both
- **Filters**: Filter by entity type or time period
- **Layout**: Adjust layout for complex lineage graphs

## Extending Lineage with Custom Processes

### Custom Process Type Creation

For richer lineage, create custom process types:

```python
def create_custom_process_type(atlas_client):
    """Create a custom ETL process type in Atlas."""
    process_type = {
        "entityDefs": [{
            "name": "ETLDataTransformation",
            "superTypes": ["Process"],
            "attributeDefs": [
                {
                    "name": "transformationType",
                    "typeName": "string",
                    "cardinality": "SINGLE",
                    "isIndexable": True,
                    "isOptional": False
                },
                {
                    "name": "dataQualityScore",
                    "typeName": "float",
                    "cardinality": "SINGLE",
                    "isIndexable": True,
                    "isOptional": True
                },
                {
                    "name": "columnMappings",
                    "typeName": "map<string,string>",
                    "cardinality": "SINGLE",
                    "isIndexable": False,
                    "isOptional": True
                }
            ]
        }]
    }
    
    # Send to Atlas API
    response = requests.post(
        f"{atlas_client.base_url}/api/atlas/v2/types/typedefs",
        json=process_type,
        auth=atlas_client.auth,
        headers={"Content-Type": "application/json"}
    )
    
    return response.json()
```

### Creating Column-Level Lineage

To track column-level lineage:

```python
def create_column_lineage(atlas_client, source_table, target_table, column_mappings):
    """Create column-level lineage between two tables."""
    # Get source table columns
    source_columns = atlas_client.get_columns_for_table(source_table)
    
    # Get target table columns
    target_columns = atlas_client.get_columns_for_table(target_table)
    
    # Create column lineage process
    column_process = {
        "entity": {
            "typeName": "ColumnLineageProcess",
            "attributes": {
                "name": f"column_mapping_{source_table}_to_{target_table}",
                "qualifiedName": f"column_lineage_{source_table}_to_{target_table}_{int(time.time())}",
                "inputs": [{"guid": source_columns[col], "typeName": "hive_column"} 
                          for col in column_mappings.keys() if col in source_columns],
                "outputs": [{"guid": target_columns[col], "typeName": "hive_column"} 
                           for col in column_mappings.values() if col in target_columns],
                "query": "SELECT source.col1 as target_col1, source.col2 as target_col2...",
                "dependencyType": "EXPRESSION"
            }
        }
    }
    
    # Send to Atlas API
    response = atlas_client.create_entity(column_process)
    return response
```

## Data Quality Integration

### Capturing Data Quality Metrics

Integrate data quality metrics with lineage:

```python
def record_data_quality_results(atlas_client, entity_guid, quality_metrics):
    """Update an entity with data quality metrics."""
    # Apply data quality metrics as business metadata
    business_metadata = {
        "DataQualityMetrics": {
            "completeness": quality_metrics.get('completeness', None),
            "accuracy": quality_metrics.get('accuracy', None),
            "validity": quality_metrics.get('validity', None),
            "lastChecked": datetime.now().isoformat(),
            "overallScore": quality_metrics.get('overall_score', None)
        }
    }
    
    # Send to Atlas API
    response = requests.post(
        f"{atlas_client.base_url}/api/atlas/v2/entity/guid/{entity_guid}/businessmetadata",
        json=business_metadata,
        auth=atlas_client.auth,
        headers={"Content-Type": "application/json"}
    )
    
    return response.json()
```

### Custom Data Quality Classifications

Create data quality-related classifications:

```python
def create_data_quality_classifications(atlas_client):
    """Create data quality classifications in Atlas."""
    classifications = {
        "classificationDefs": [
            {
                "name": "DataQualityIssue",
                "description": "Indicates data quality problems",
                "attributeDefs": [
                    {
                        "name": "issueType",
                        "typeName": "string",
                        "cardinality": "SINGLE",
                        "isIndexable": True,
                        "isOptional": False
                    },
                    {
                        "name": "severity",
                        "typeName": "string",
                        "cardinality": "SINGLE",
                        "isIndexable": True,
                        "isOptional": False
                    },
                    {
                        "name": "affectedRecords",
                        "typeName": "int",
                        "cardinality": "SINGLE",
                        "isIndexable": True,
                        "isOptional": True
                    }
                ]
            }
        ]
    }
    
    # Send to Atlas API
    response = requests.post(
        f"{atlas_client.base_url}/api/atlas/v2/types/typedefs",
        json=classifications,
        auth=atlas_client.auth,
        headers={"Content-Type": "application/json"}
    )
    
    return response.json()
```

## Advanced Lineage Querying

### REST API Queries

Query lineage programmatically:

```python
def get_full_lineage(atlas_client, entity_guid, depth=5, direction="BOTH"):
    """Get complete lineage for an entity."""
    response = requests.get(
        f"{atlas_client.base_url}/api/atlas/v2/lineage/{entity_guid}?depth={depth}&direction={direction}",
        auth=atlas_client.auth
    )
    
    return response.json()
```

### Impact Analysis

Identify downstream impacts:

```python
def analyze_impact(atlas_client, entity_guid):
    """Analyze impact of changes to an entity."""
    # Get downstream lineage only
    lineage = atlas_client.get_lineage(entity_guid, direction="OUTPUT")
    
    # Process results to identify critical dependencies
    critical_entities = []
    for guid, entity in lineage.get('guidEntityMap', {}).items():
        if entity.get('classifications'):
            # Check for critical classifications
            for classification in entity.get('classifications'):
                if classification.get('typeName') in ['PII', 'Confidential', 'BusinessCritical']:
                    critical_entities.append({
                        'guid': guid,
                        'name': entity.get('attributes', {}).get('name'),
                        'type': entity.get('typeName'),
                        'classification': classification.get('typeName')
                    })
    
    return critical_entities
```

## Exporting Lineage Data

### Export for Visualization Tools

Export lineage to external visualization tools:

```python
def export_lineage_to_json(atlas_client, entity_guid, output_file, depth=3):
    """Export lineage data to JSON for external visualization."""
    lineage = atlas_client.get_lineage(entity_guid, depth=depth)
    
    # Transform to visualization-friendly format
    viz_data = {
        "nodes": [],
        "edges": []
    }
    
    # Process nodes (entities)
    for guid, entity in lineage.get('guidEntityMap', {}).items():
        viz_data["nodes"].append({
            "id": guid,
            "label": entity.get('attributes', {}).get('name', 'Unknown'),
            "type": entity.get('typeName'),
            "properties": {
                "qualifiedName": entity.get('attributes', {}).get('qualifiedName'),
                "createdBy": entity.get('createdBy'),
                "createTime": entity.get('createTime')
            }
        })
    
    # Process edges (relationships)
    for relation in lineage.get('relations', []):
        viz_data["edges"].append({
            "source": relation.get('fromEntityId'),
            "target": relation.get('toEntityId'),
            "label": relation.get('relationshipId')
        })
    
    # Write to file
    with open(output_file, 'w') as f:
        json.dump(viz_data, f, indent=2)
    
    return output_file
```

### Integration with External Tools

Sample code for D3.js visualization:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Atlas Lineage Visualization</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        .node {
            fill: #ccc;
            stroke: #fff;
            stroke-width: 2px;
        }
        .link {
            stroke: #999;
            stroke-opacity: 0.6;
        }
        .label {
            font-family: Arial;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div id="lineage-viz"></div>
    <script>
        // Load the lineage data exported from Atlas
        d3.json('lineage_data.json').then(function(data) {
            const width = 960, height = 600;
            
            // Create a force simulation
            const simulation = d3.forceSimulation(data.nodes)
                .force("link", d3.forceLink(data.edges).id(d => d.id).distance(150))
                .force("charge", d3.forceManyBody().strength(-300))
                .force("center", d3.forceCenter(width / 2, height / 2));
            
            // Create SVG
            const svg = d3.select("#lineage-viz")
                .append("svg")
                .attr("width", width)
                .attr("height", height);
            
            // Add links
            const link = svg.append("g")
                .selectAll("line")
                .data(data.edges)
                .enter().append("line")
                .attr("class", "link");
            
            // Add nodes
            const node = svg.append("g")
                .selectAll("circle")
                .data(data.nodes)
                .enter().append("circle")
                .attr("class", "node")
                .attr("r", 10)
                .attr("fill", d => {
                    // Color by entity type
                    if (d.type === 'hive_table') return "#6baed6";
                    if (d.type === 'hive_column') return "#9ecae1";
                    if (d.type.includes('Process')) return "#fd8d3c";
                    return "#ccc";
                });
            
            // Add labels
            const label = svg.append("g")
                .selectAll("text")
                .data(data.nodes)
                .enter().append("text")
                .attr("class", "label")
                .text(d => d.label);
            
            // Update positions on simulation tick
            simulation.on("tick", () => {
                link
                    .attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);
                
                node
                    .attr("cx", d => d.x)
                    .attr("cy", d => d.y);
                
                label
                    .attr("x", d => d.x + 15)
                    .attr("y", d => d.y + 5);
            });
        });
    </script>
</body>
</html>
```

By following this guide, you can effectively visualize, extend, and leverage the lineage capabilities of Apache Atlas in your ETL pipeline. This lineage information is crucial for data governance, impact analysis, and regulatory compliance.
