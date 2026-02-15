import json
import os
from datetime import datetime

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("[WARN] Pandas module not found. Skipping Excel check.")

RECORD_FILE = 'user_records.json'
EXCEL_FILE = 'user_records.xlsx'

def check_json_records():
    print(f"--- Checking JSON file: {RECORD_FILE} ---")
    if not os.path.exists(RECORD_FILE):
        print(f"[ERROR] File not found: {RECORD_FILE}")
        return

    try:
        with open(RECORD_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON format corrupted! Reason: {e}")
        return
    except Exception as e:
        print(f"[ERROR] Cannot read file. Reason: {e}")
        return

    if not isinstance(data, list):
        print("[ERROR] Root structure should be a List")
        return

    print(f"[OK] JSON format correct. Total records: {len(data)}")

    valid_count = 0
    issues = []

    required_fields = ["timestamp", "name", "gender", "birth_date", "birth_hour", "lunar_date"]

    for i, record in enumerate(data):
        record_issues = []
        
        # Check required fields
        for field in required_fields:
            if field not in record:
                record_issues.append(f"Missing field: {field}")
            elif record[field] is None:
                record_issues.append(f"Field {field} is None")

        # Validate Date Format
        if "birth_date" in record and record["birth_date"]:
            try:
                datetime.strptime(record["birth_date"], "%Y-%m-%d")
            except ValueError:
                record_issues.append(f"Invalid date format: {record['birth_date']} (expected YYYY-MM-DD)")

        # Validate Name
        if "name" in record and (not record["name"] or record["name"].strip() == ""):
             record_issues.append("Name is empty")

        if record_issues:
            issues.append(f"Record #{i+1} (Index {i}): {', '.join(record_issues)}")
        else:
            valid_count += 1

    if issues:
        print(f"[WARN] Found {len(issues)} records with potential issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("[OK] All data fields seem normal.")

def check_excel_records():
    if not PANDAS_AVAILABLE:
        return

    print(f"\n--- Checking Excel file: {EXCEL_FILE} ---")
    if not os.path.exists(EXCEL_FILE):
        print(f"[WARN] Excel file not found: {EXCEL_FILE} (It will be recreated on next save)")
        return

    try:
        df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
        print(f"[OK] Excel read successfully. Total records: {len(df)}")
        
        # Note: Column names in Excel might be in Chinese as per backend script
        # "紀錄時間", "姓名", "性別", "國曆生日", "時辰(支)", "農曆日期"
        expected_cols = ["紀錄時間", "姓名", "性別", "國曆生日", "時辰(支)", "農曆日期"]
        missing_cols = [col for col in expected_cols if col not in df.columns]
        
        if missing_cols:
            print(f"[WARN] Excel missing columns: {missing_cols}")
        else:
            print("[OK] Excel column names correct.")
            
    except Exception as e:
        print(f"[ERROR] Excel file corrupted or unreadable. Reason: {e}")

if __name__ == "__main__":
    check_json_records()
    check_excel_records()
