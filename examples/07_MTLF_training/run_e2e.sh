#!/bin/bash
source /home/king25158986/daisy-env/bin/activate
cd /home/king25158986/daisy/examples/07_MTLF_training

echo "[E2E] Kill old processes..."
pkill -f "python3 master.py"
pkill -f "python3 client.py"
sleep 2

echo "[E2E] 1. Starting Master..."
python3 master.py --server_address 127.0.0.1:8887 --api_ip 0.0.0.0 --api_port 9887 > master_e2e.log 2>&1 &
sleep 5

echo "[E2E] 2. Uploading Data to MongoDB (TID: e2e-test-999)..."
python3 test_mongodb_upload.py > upload.log 2>&1
cat upload.log

echo "[E2E] 3. Starting Clients hooked to MongoDB data... (Now Auto-Spawned)"
# Master will automatically spawn these clients when publish_task is invoked
sleep 2

echo "[E2E] 4. Triggering Training Task and Waiting for Callback..."
python3 test_async_callback.py
