import requests
from dlc_database import DLCDatabase
import concurrent.futures
import json
import os
import sys

def get_size(dlc_id, info):
    total_size = 0
    urls = []
    
    if 'url' in info:
        urls.append(info['url'])
    elif 'urls' in info:
        urls.extend(info['urls'])
        
    for url in urls:
        try:
            response = requests.head(url, allow_redirects=True, timeout=10)
            if response.status_code == 200:
                total_size += int(response.headers.get('content-length', 0))
        except:
            pass
            
    return dlc_id, total_size

db = DLCDatabase()
dlcs = db.all()
results = {}

# Load existing if any
if os.path.exists("dlc_sizes.json"):
    try:
        with open("dlc_sizes.json", "r") as f:
            results = json.load(f)
    except:
        pass

to_fetch = [k for k, v in dlcs.items() if k not in results or results[k] == 0]

print(f"Fetching sizes for {len(to_fetch)} remaining DLCs...", file=sys.stderr)

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    future_to_dlc = {executor.submit(get_size, dlc_id, dlcs[dlc_id]): dlc_id for dlc_id in to_fetch}
    for i, future in enumerate(concurrent.futures.as_completed(future_to_dlc)):
        dlc_id, size = future.result()
        if size > 0:
            results[dlc_id] = size
            # Save incrementally every 5 items
            if i % 5 == 0:
                with open("dlc_sizes.json", "w") as f:
                    json.dump(results, f, indent=4)
            print(f"Fetched {dlc_id}: {size}", file=sys.stderr)

# Final save
with open("dlc_sizes.json", "w") as f:
    json.dump(results, f, indent=4)

print("Done.")
