CREATE DATABASE IF NOT EXISTS atlas_test;
CREATE TABLE IF NOT EXISTS atlas_test.transformed_data (
  id INT, 
  name STRING, 
  department STRING, 
  adjusted_salary DOUBLE
) 
ROW FORMAT DELIMITED 
FIELDS TERMINATED BY ',' 
STORED AS TEXTFILE;
