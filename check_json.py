import os
import json

data_dir = 'data'
for filename in os.listdir(data_dir):
    if filename.endswith('.json'):
        filepath = os.path.join(data_dir, filename)
        try:
            with open(filepath, 'r') as f:
                json.load(f)
            print(f"Valid: {filename}")
        except json.JSONDecodeError as e:
            print(f"INVALID: {filename} at line {e.lineno}, col {e.colno}: {e.msg}")
