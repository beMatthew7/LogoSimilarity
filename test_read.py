import pandas as pd

file_path = 'logos.snappy.parquet'

try:
    df = pd.read_parquet(file_path, engine='pyarrow')

    print("Available columns:")
    print(list(df.columns))

    print("\nThe first 5 rows look like this:")
    print(df.head(100).values)

except FileNotFoundError:
    print(f"Error: File '{file_path}' not found.")
except Exception as e:
    print(f"An error occurred: {e}")
