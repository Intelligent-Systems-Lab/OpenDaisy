"""
End-to-end test for async 202 + callback + tar download.

Prerequisites:
    cd /home/king25158986/daisy/examples/07_MTLF_training
    python3 deploy.py --init_model

Usage:
    python3 test_async_callback.py
"""

import sys
import json
import time
import tarfile
import tempfile
import os
import threading
import requests
from flask import Flask, request as flask_request

# ── Configuration ──
MASTER_API = "http://127.0.0.1:9887"
CALLBACK_PORT = 5555
CALLBACK_HOST = "127.0.0.1"

# ── Mock callback receiver ──
callback_app = Flask("callback_receiver")
received_callbacks = []

@callback_app.route("/mtlf/training-complete", methods=["POST"])
def receive_callback():
    data = flask_request.get_json()
    received_callbacks.append(data)
    print(f"\n[CALLBACK RECEIVED] {json.dumps(data, indent=2)}")
    return {"received": True}, 200

def start_callback_server():
    callback_app.run(host=CALLBACK_HOST, port=CALLBACK_PORT, use_reloader=False)

# ── Test ──
def main():
    print("=" * 60)
    print("  Async 202 + Callback + Download Test")
    print("=" * 60)

    # Step 0: Start callback receiver
    print("\n[STEP 0] Starting mock callback receiver on port", CALLBACK_PORT)
    t = threading.Thread(target=start_callback_server, daemon=True)
    t.start()
    time.sleep(1)

    # Step 1: Send task with CALLBACK_URL (1 round only)
    task_config = {
        "TID": "test-async-001",
        "NUM_ROUNDS": 1,
        "EVALUATE_INTERVAL": 1,
        "EVALUATE_INIT_MODEL_MASTER": True,
        "MIN_WAITING_TIME_MASTER": 5,
        "MODEL_PATH": "model/model.npy",
        "SAVE_MODEL": True,
        "OPERATORS": {
            "MASTER_SERVER_OPERATOR": [
                "daisyfl.operator.base.base_server_logic",
                "BaseServerLogic"
            ],
            "CLIENT_OPERATOR": [
                "daisyfl.operator.base.base_client_logic",
                "BaseClientLogic"
            ]
        },
        "STRATEGIES": {
            "MASTER_STRATEGY": [
                "custom_strategy",
                "EarlyStoppingFedAvg"
            ]
        },
        "METRICS_HANDLERS": {
            "MASTER_METRICS_HANDLER": [
                "daisyfl.metrics_handler.flat_metrics_handler",
                "FlatMetricsHandler"
            ]
        },
        "CALLBACK_URL": f"http://{CALLBACK_HOST}:{CALLBACK_PORT}/mtlf/training-complete",
        "MODEL_META": {
            "model": {
                "input_size": 10,
                "output_size": 2,
                "num_channels": [32, 64, 64, 64],
                "kernel_size": 2,
                "dropout": 0.2
            },
            "inference": {
                "seq_length": 30,
                "out_seq_len": 1,
                "feature_order": [
                    "total_vol",
                    "ul_vol",
                    "dl_vol",
                    "total_nb_pkts",
                    "ul_nb_pkts",
                    "dl_nb_pkts",
                    "ul_thr",
                    "dl_thr",
                    "ul_pkt_thr",
                    "dl_pkt_thr"
                ],
                "output_fields": [
                    "ul_vol",
                    "dl_vol"
                ],
                "preprocessing": "log1p_standard_scaler"
            }
        }
    }

    print(f"\n[STEP 1] POST to {MASTER_API}/publish_task (NUM_ROUNDS=1)")
    print(f"         Waiting for master API to be ready...")
    resp = None
    for attempt in range(15):
        try:
            resp = requests.post(f"{MASTER_API}/publish_task", json=task_config, timeout=10)
            break
        except requests.exceptions.ConnectionError:
            print(f"         Attempt {attempt+1}/15 - master not ready, retrying in 2s...")
            time.sleep(2)
    if resp is None:
        print(f"\n[ERROR] Cannot connect to {MASTER_API} after 30s.")
        print(f"        Deploy first: python3 deploy.py --init_model")
        sys.exit(1)

    # Step 2: Verify 202
    print(f"\n[STEP 2] Response: {resp.status_code} {resp.json()}")
    if resp.status_code != 202:
        print(f"[FAIL] Expected 202, got {resp.status_code}")
        sys.exit(1)
    print("         ✅ 202 Accepted")

    # Step 3: Wait for callback
    print(f"\n[STEP 3] Waiting for callback...")
    timeout = 600  # 10 minutes max (training can take ~7 min)
    start = time.time()
    while not received_callbacks and (time.time() - start) < timeout:
        time.sleep(2)
        print(f"         waiting... {int(time.time() - start)}s", end="\r")

    if not received_callbacks:
        print(f"\n[FAIL] No callback after {timeout}s")
        sys.exit(1)

    cb = received_callbacks[0]
    print(f"\n         ✅ Callback received!")
    print(f"         task_id:   {cb.get('task_id')}")
    print(f"         status:    {cb.get('status')}")

    if cb.get("status") == "failure":
        print(f"         error:     {cb.get('error')}")
        sys.exit(1)

    model_url = cb.get("model_url")
    print(f"         model_url: {model_url}")

    # Step 4: Download tar.gz
    print(f"\n[STEP 4] Downloading from {model_url}")
    dl = requests.get(model_url, timeout=30)
    if dl.status_code != 200:
        print(f"[FAIL] Download returned {dl.status_code}")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmpdir:
        tar_path = os.path.join(tmpdir, "model.tar.gz")
        with open(tar_path, "wb") as f:
            f.write(dl.content)
        print(f"         Downloaded {len(dl.content)} bytes")

        extract_dir = os.path.join(tmpdir, "extracted")
        os.makedirs(extract_dir)
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(extract_dir)

        contents = sorted(os.listdir(extract_dir))
        print(f"\n[STEP 5] Tar contents:")
        for fname in contents:
            size = os.path.getsize(os.path.join(extract_dir, fname))
            print(f"         - {fname} ({size} bytes)")

        expected = {"model.npy", "scaler.pkl", "model.py", "config.json"}
        missing = expected - set(contents)

        if os.path.isfile(os.path.join(extract_dir, "config.json")):
            with open(os.path.join(extract_dir, "config.json")) as f:
                print(f"\n[STEP 6] config.json: {json.dumps(json.load(f), indent=2)}")

    print("\n" + "=" * 60)
    if not missing:
        print("  ✅ ALL TESTS PASSED")
    else:
        print(f"  ⚠️  Missing files: {missing}")
    print("=" * 60)

if __name__ == "__main__":
    main()
