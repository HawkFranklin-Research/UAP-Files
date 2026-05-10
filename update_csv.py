import pandas as pd
import sys
import json
from pathlib import Path

def update_csv(file_id, data_json):
    csv_path = Path(__file__).resolve().parent / 'analysis2b' / 'manual_review' / 'manual_review_template.csv'
    df = pd.read_csv(csv_path)
    data = json.loads(data_json)
    
    for key, value in data.items():
        if key in df.columns:
            df.loc[df['file_id'] == file_id, key] = value
            
    df.to_csv(csv_path, index=False)
    print(f"Updated {file_id} successfully.")

if __name__ == '__main__':
    file_id = sys.argv[1]
    data_json = sys.argv[2]
    update_csv(file_id, data_json)
