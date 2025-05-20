import requests
import json
import time
import sys

def verify_metadata(atlas_url="http://atlas:21000/api/atlas/v2/search/basic", table_name="transformed_data", database="default", cluster_name="primary"):
    """
    Verify that the Hive table metadata has been ingested into Atlas.
    
    Parameters:
    - atlas_url: The Atlas API URL to query
    - table_name: The name of the Hive table to search for
    - database: The database containing the table
    - cluster_name: The Atlas cluster name
    
    Returns:
    - True if metadata is found, raises Exception otherwise
    """
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    auth = ("admin", "admin")
    
    # Query to search for the Hive table in Atlas
    query = {
        "typeName": "hive_table",
        "query": table_name,
        "limit": 10
    }
    
    # Retry mechanism with exponential backoff
    max_retries = 5
    retry_delay = 10  # initial delay in seconds
    
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt+1}: Checking Atlas for 'transformed_data' metadata...")
            response = requests.post(atlas_url, json=query, headers=headers, auth=auth)
            
            if response.status_code == 200:
                result = response.json()
                entities = result.get("entities", [])
                
                if entities:
                    print("SUCCESS: Metadata for 'transformed_data' found in Atlas.")
                    print(f"Found {len(entities)} matching entities:")
                    
                    # Print details of found entities
                    for idx, entity in enumerate(entities):
                        print(f"\nEntity {idx+1}:")
                        print(f"  Name: {entity.get('attributes', {}).get('name')}")
                        print(f"  Qualified Name: {entity.get('attributes', {}).get('qualifiedName')}")
                        print(f"  Type: {entity.get('typeName')}")
                        print(f"  GUID: {entity.get('guid')}")
                    
                    return True
                else:
                    print("No matching entities found. Metadata might not have been ingested yet.")
            else:
                print(f"Failed to query Atlas. Status code: {response.status_code}")
                print(f"Response: {response.text}")
            
            # If we reached here, we need to retry
            if attempt < max_retries - 1:
                retry_seconds = retry_delay * (2 ** attempt)
                print(f"Retrying in {retry_seconds} seconds...")
                time.sleep(retry_seconds)
            
        except Exception as e:
            print(f"Error communicating with Atlas: {str(e)}")
            if attempt < max_retries - 1:
                retry_seconds = retry_delay * (2 ** attempt)
                print(f"Retrying in {retry_seconds} seconds...")
                time.sleep(retry_seconds)
    
    # If we've exhausted all retries
    error_msg = "ERROR: Metadata for 'transformed_data' not found in Atlas after multiple attempts."
    print(error_msg)
    raise Exception(error_msg)

if __name__ == "__main__":
    try:
        verify_metadata()
        sys.exit(0)
    except Exception as e:
        print(f"Verification failed: {str(e)}")
        sys.exit(1)
