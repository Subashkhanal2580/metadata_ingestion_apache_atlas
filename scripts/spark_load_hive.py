from pyspark.sql import SparkSession

def load_to_hive():
    """
    Load transformed Parquet data into a Hive table.
    """
    # Initialize Spark session with Hive support
    spark = SparkSession.builder \
        .appName("ETLHiveLoad") \
        .config("spark.sql.catalogImplementation", "hive") \
        .config("spark.hadoop.hive.metastore.uris", "thrift://hive:9083") \
        .getOrCreate()
    
    try:
        # Define data paths
        data_dir = "/opt/spark/data"
        input_path = f"{data_dir}/transformed_data.parquet"
        
        # Read the transformed Parquet data
        print(f"Reading transformed Parquet data from {input_path}...")
        df = spark.read.parquet(input_path)
        
        # Display schema and sample data for debugging
        print("Parquet Schema:")
        df.printSchema()
        print("Sample data:")
        df.show(5)
        
        # Create Hive database if it doesn't exist
        spark.sql("CREATE DATABASE IF NOT EXISTS default")
        
        # Save to Hive table
        print("Saving data to Hive table 'default.transformed_data'...")
        df.write.mode("overwrite").saveAsTable("default.transformed_data")
        
        # Verify table creation
        print("Verifying table creation:")
        result = spark.sql("SELECT * FROM default.transformed_data LIMIT 5")
        result.show()
        
        print("Data successfully loaded into Hive table 'default.transformed_data'")
    
    except Exception as e:
        print(f"Error loading data into Hive: {str(e)}")
        raise
    finally:
        spark.stop()

if __name__ == "__main__":
    load_to_hive()
