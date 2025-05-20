from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime
import requests
import os

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2025, 5, 19),
    'retries': 1,
}

dag = DAG(
    'etl_pipeline',
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False,
)

def download_csv():
    """Download CSV data from GitHub repository or use local sample file."""
    # For demonstration purposes, we'll use the local sample file
    # In a real-world scenario, we would download from GitHub:
    # url = "https://raw.githubusercontent.com/sample/repo/main/data.csv"
    # response = requests.get(url)
    # with open("/opt/airflow/data/data.csv", "wb") as f:
    #     f.write(response.content)
    
    # Instead, we'll copy our sample file to the target location
    data_dir = "/opt/airflow/data"
    os.makedirs(data_dir, exist_ok=True)
    
    # Check if we need to copy the sample file
    if not os.path.exists(f"{data_dir}/data.csv"):
        # In Docker, the sample file would be mounted, but for local testing
        # we provide a backup option to copy from the original sample location
        try:
            import shutil
            shutil.copyfile("/opt/airflow/sample_data.csv", f"{data_dir}/data.csv")
        except Exception as e:
            print(f"Warning: Could not copy sample file: {e}")
            print("Using existing sample file in data directory...")
    
    if os.path.exists(f"{data_dir}/data.csv"):
        print(f"CSV data ready at {data_dir}/data.csv")
        return f"{data_dir}/data.csv"
    else:
        raise FileNotFoundError(f"No CSV data found at {data_dir}/data.csv")

download_task = PythonOperator(
    task_id='download_csv',
    python_callable=download_csv,
    dag=dag,
)

spark_submit = BashOperator(
    task_id='spark_transform',
    bash_command='spark-submit --master local[*] /opt/airflow/scripts/spark_script.py',
    dag=dag,
)

load_to_hive = BashOperator(
    task_id='load_to_hive',
    bash_command='spark-submit --master local[*] /opt/airflow/scripts/spark_load_hive.py',
    dag=dag,
)

verify_metadata = PythonOperator(
    task_id='verify_metadata_in_atlas',
    python_callable=lambda: __import__('verify_metadata').verify_metadata(),
    dag=dag,
)

# Define task dependencies
download_task >> spark_submit >> load_to_hive >> verify_metadata
