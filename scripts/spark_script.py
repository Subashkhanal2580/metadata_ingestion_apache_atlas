from pyspark.sql import SparkSession

def transform_data():
    """
    Read CSV data, apply transformations, and save as Parquet.
    """
    # Initialize Spark session with Hive support
    spark = SparkSession.builder \
        .appName("ETLTransform") \
        .config("spark.sql.catalogImplementation", "hive") \
        .config("spark.hadoop.hive.metastore.uris", "thrift://hive:9083") \
        .getOrCreate()
    
    # Define data paths
    data_dir = "/opt/spark/data"
    input_path = f"{data_dir}/data.csv"
    output_path = f"{data_dir}/transformed_data.parquet"
    
    # Read CSV
    print(f"Reading CSV data from {input_path}...")
    df = spark.read.csv(input_path, header=True, inferSchema=True)
    
    # Display schema and sample data for debugging
    print("CSV Schema:")
    df.printSchema()
    print("Sample data:")
    df.show(5)
    
    # Transformation: Filter rows where age > 18
    print("Applying transformations...")
    df_transformed = df.filter(df.age > 18)
    
    # Count records before and after transformation
    count_before = df.count()
    count_after = df_transformed.count()
    print(f"Records before transformation: {count_before}")
    print(f"Records after transformation: {count_after}")
    print(f"Filtered out {count_before - count_after} records with age <= 18")
    
    # Save as Parquet
    print(f"Saving as Parquet to {output_path}...")
    df_transformed.write.mode("overwrite").parquet(output_path)
    
    print(f"Transformation complete. Data saved to {output_path}")
    
    spark.stop()

if __name__ == "__main__":
    transform_data()
