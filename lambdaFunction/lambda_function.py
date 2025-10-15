import boto3
import pandas as pd
from io import StringIO

s3 = boto3.client('s3')

def lambda_handler(event, context):
    try:
        # Automatically get bucket name and file key from the event
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        
        print(f"Processing file: {key} from bucket: {bucket}")
        
        # Read CSV from S3
        csv_obj = s3.get_object(Bucket=bucket, Key=key)
        body = csv_obj['Body'].read().decode('utf-8')
        df = pd.read_csv(StringIO(body))
        
        # Log detected columns
        print("Detected columns:", df.columns.tolist())
        
        # Safe handling: Drop rows with all NaN
        df.dropna(how='all', inplace=True)
        
        # Detect sales column
        if 'Sales' in df.columns:
            sales_col = 'Sales'
        elif 'Amount' in df.columns:
            sales_col = 'Amount'
        else:
            sales_col = None
            print("Warning: No sales column found")
        
        # Detect profit column
        if 'Profit' in df.columns:
            profit_col = 'Profit'
        else:
            profit_col = None
            print("Warning: No profit column found")
        
        # Calculate Profit Margin if possible
        if sales_col and profit_col:
            df['Profit_Margin'] = df[profit_col] / df[sales_col] * 100
        
        # Calculate Unit Price if Quantity column exists
        if sales_col and 'Quantity' in df.columns:
            df['Unit_Price'] = df[sales_col] / df['Quantity']
        elif sales_col:
            df['Unit_Price'] = df[sales_col]
        
        # Optional: Fill missing numeric values with 0
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        df[numeric_cols] = df[numeric_cols].fillna(0)
        
        # Save processed CSV to a different bucket or prefix
        processed_bucket = bucket.replace('raw', 'processed')  # automatically choose processed bucket
        processed_key = key.replace('.csv', '-Processed.csv')
        
        out_csv = StringIO()
        df.to_csv(out_csv, index=False)
        s3.put_object(Bucket=processed_bucket, Key=processed_key, Body=out_csv.getvalue())
        
        print(f"Processing complete. Processed file saved as: {processed_bucket}/{processed_key}")
        return {
            'statusCode': 200,
            'body': f'Processing complete. File saved as {processed_bucket}/{processed_key}'
        }
        
    except Exception as e:
        print(f"Error processing file: {e}")
        return {
            'statusCode': 500,
            'body': str(e)
        }
