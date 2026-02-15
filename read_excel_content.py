
import pandas as pd
import sys

file_path = '紫微斗數邏輯總表.xlsx'

try:
    xl = pd.ExcelFile(file_path)
    print(f"Sheet names: {xl.sheet_names}")
    
    for sheet in xl.sheet_names:
        print(f"\n--- Sheet: {sheet} ---")
        df = xl.parse(sheet)
        print("Columns:", df.columns.tolist())
        print("First 5 rows:")
        print(df.head().to_string())
        
except Exception as e:
    print(f"Error reading excel file: {e}")
