"""
Tests uploading data to MongoDB and then reading it using dataset.py
"""
import sys
import json
import requests
import os

import datetime

# Create mock data mimicking the EES training notifications
# 50 time steps, 3 UEs per time step -> 150 records total
mock_data = []

base_time = datetime.datetime.strptime("2024-01-01T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
for t in range(50):
    current_time_str = (base_time + datetime.timedelta(seconds=t)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for ue_idx in range(1, 4):
        record = {
            "notificationItems": [
                {
                    "eventType": "USER_DATA_USAGE_MEASURES",
                    "ueIpv4Addr": f"10.0.0.{ue_idx + 1}",
                    "timeStamp": current_time_str,
                    "startTime": current_time_str,
                    "userDataUsageMeasurements": [
                        {
                            "volumeMeasurement": {
                                "totalVolume": 1000,
                                "ulVolume": 400,
                                "dlVolume": 600,
                                "totalNbOfPackets": 20,
                                "ulNbOfPackets": 8,
                                "dlNbOfPackets": 12
                            },
                            "throughputMeasurement": {
                                "ulThroughput": "400 bps",
                                "dlThroughput": "600 bps",
                                "ulPacketThroughput": "8 pps",
                                "dlPacketThroughput": "12 pps"
                            }
                        }
                    ]
                }
            ]
        }
        mock_data.append(record)

payload = [
    {
        "TID": "e2e-test-999",
        "group_id": "ue-comm-group1",
        "upfEventNotifs": mock_data
    },
    {
        "TID": "e2e-test-999",
        "group_id": "ue-comm-group2",
        "upfEventNotifs": mock_data
    }
]

API_URL = "http://127.0.0.1:9887/upload_data"

import time
print(f"Uploading mock data for 2 groups to {API_URL}...")
resp = None
for attempt in range(15):
    try:
        resp = requests.post(API_URL, json=payload, timeout=5)
        print("Response:", resp.status_code, resp.json())
        break
    except requests.exceptions.ConnectionError:
        print(f"Attempt {attempt+1}/15 - API not ready, retrying in 2s...")
        time.sleep(2)
if resp is None:
    print("Failed to upload: Connection timed out.")
    sys.exit(1)

print("\nTesting dataset.py reading from MongoDB...")
sys.path.append("/home/king25158986/daisy/examples/07_MTLF_training")
from dataset import get_dataloaders

try:
    train_loader, val_loader, out_dim = get_dataloaders(tid="db-test-002", batch_size=32, seq_length=30, out_seq_len=5, save_scaler=False)
    print(f"Success! Fetched datasets.")
    print(f"Train batches: {len(train_loader)}")
    print(f"Val batches: {len(val_loader)}")
    print(f"Output dim: {out_dim}")
    
    # Peek at the first batch to verify shapes
    for x, y in train_loader:
        print(f"X batch shape: {x.shape}")
        print(f"Y batch shape: {y.shape}")
        break

except Exception as e:
    print("Failed to fetch from MongoDB:", e)
    sys.exit(1)
