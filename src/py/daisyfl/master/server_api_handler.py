# Copyright 2024 Intelligence Systems Lab. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

from flask import Flask, request, make_response, Response, send_file
from typing import Callable, Optional
from daisyfl.common.task_manager import TaskManager
from daisyfl.utils.logger import log
from daisyfl.utils.logger import WARNING, ERROR, INFO, DEBUG
from daisyfl.common import TID, CALLBACK_URL, MODEL_PATH

import threading
import subprocess
import requests as http_requests
import tarfile
import json
import os
import shutil
from pymongo import MongoClient

# Keys used in the task config for artifact packaging
_SCALER_PATH = "SCALER_PATH"
_MODEL_SCRIPT = "MODEL_SCRIPT"

def _get_mongo_uri():
    """Resolve MongoDB URI from daisyconfig.json > env var > default."""
    uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
    config_path = os.path.join(os.getcwd(), "daisyconfig.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                cfg = json.load(f)
                uri = cfg.get("MONGO_URI", uri)
        except Exception:
            pass
    return uri

class ServerListener:
    """
    HTTP server to be required by users and external applications.
    This HTTP server is used to meet the following requirements:
    1. Users can publish task configurations.
    2. Users or external apps (e.g., Prometheus) can get metrics of the specific task.
    3. Serve model artifact downloads after async training.
    """

    def __init__(
            self,
            ip: str,
            port: int,
            task_manager: TaskManager,
        ):
        self.app = Flask(__name__)
        self._ip: str = ip
        self._port: int = port
        self._task_manager: TaskManager = task_manager
        self.get_metrics = None
        self._artifacts_dir: str = os.path.join(os.getcwd(), "artifacts")
        self._base_url: str = f"http://{ip}:{port}"
        
        @self.app.route("/upload_data", methods=["POST"])
        def upload_data():
            """Receive dataset from MTLF and store it in MongoDB."""
            js = request.get_json(silent=True)
            if not js:
                return {"error": "Invalid JSON payload."}, 400
            
            # Support both list of groups and single group payload
            payloads = js if isinstance(js, list) else [js]
            total_inserted = 0
            
            try:
                m_client = MongoClient(_get_mongo_uri())
                db = m_client["daisy_mtlf"]
                col = db["training_data"]
                col.create_index([("tid", 1), ("group_id", 1)])
                
                docs = []
                for p in payloads:
                    tid = p.get("tid") or p.get("TID")
                    group_id = p.get("group_id") or p.get("groupId") or "default_group"
                    data = p.get("data") or p.get("upfEventNotifs")
                    
                    if not tid or data is None:
                        continue
                        
                    if not isinstance(data, list):
                        continue
                        
                    for item in data:
                        item["tid"] = tid
                        item["group_id"] = group_id
                        docs.append(item)
                        
                if docs:
                    col.insert_many(docs)
                    total_inserted = len(docs)
                    
                return {"status": "success", "inserted": total_inserted}, 200
            except Exception as e:
                log(ERROR, "Failed to save data to MongoDB: %s", e)
                return {"error": str(e)}, 500

        @self.app.route("/publish_task", methods=["POST"])
        def publish_task():
            """Publish a task configuration with JSON format to the Master node."""
            js = request.get_json()
            callback_url = js.get(CALLBACK_URL)

            # Dynamically initialize model from MODEL_META if provided
            model_meta = js.get("MODEL_META")
            task_id = js.get(TID, "unknown")
            use_fixed_scaler = bool(js.get("USE_FIXED_SCALER", False))
            seed_model_path = js.get("SEED_MODEL_PATH")
            seed_scaler_path = js.get("SEED_SCALER_PATH")
            
            # Use TID as model storage directory: model/{tid}/model.npy
            if task_id != "unknown":
                model_path = os.path.join("model", task_id, "model.npy")
                js[MODEL_PATH] = model_path  # Update task config so TaskManager uses TID-scoped path
                js[_SCALER_PATH] = os.path.join("model", task_id, "scaler.pkl")
            else:
                model_path = js.get(MODEL_PATH, "model/model.npy")
            scaler_path = js.get(_SCALER_PATH, os.path.join(os.path.dirname(model_path) or "model", "scaler.pkl"))

            log(
                INFO,
                "publish_task tid=%s fixed_scaler=%s seed_model=%s seed_scaler=%s model_path=%s scaler_path=%s",
                task_id,
                use_fixed_scaler,
                seed_model_path,
                seed_scaler_path,
                model_path,
                scaler_path,
            )

            try:
                if seed_model_path:
                    log(INFO, "Task %s uses warm-start seed model: %s", task_id, seed_model_path)
                    self._copy_seed_file(seed_model_path, model_path, "seed model")
                elif model_meta:
                    log(INFO, "Task %s uses fresh init from MODEL_META", task_id)
                    self._init_model_from_meta(model_meta, model_path)
                else:
                    log(WARNING, "Task %s has neither seed model nor MODEL_META; existing model path will be used as-is", task_id)
            except Exception as e:
                log(ERROR, "Failed to prepare model seed for task %s: %s", task_id, e)
                return {"error": f"Model init failed: {e}"}, 500

            if use_fixed_scaler:
                try:
                    log(INFO, "Task %s uses fixed scaler seed: %s", task_id, seed_scaler_path)
                    self._copy_seed_file(seed_scaler_path, scaler_path, "fixed scaler")
                except Exception as e:
                    log(ERROR, "Failed to prepare fixed scaler for task %s: %s", task_id, e)
                    return {"error": f"Fixed scaler init failed: {e}"}, 500

            spawned_clients = []

            # Auto-spawn clients based on groups found in MongoDB for this TID
            if task_id != "unknown":
                try:
                    m_client = MongoClient(_get_mongo_uri())
                    col = m_client["daisy_mtlf"]["training_data"]
                    distinct_groups = [g for g in col.distinct("group_id", {"tid": task_id}) if g is not None]
                    
                    import sys
                    import time
                    
                    parent_address = "127.0.0.1:8887"
                    if "--server_address" in sys.argv:
                        idx = sys.argv.index("--server_address")
                        parent_address = sys.argv[idx + 1]
                    
                    if distinct_groups:
                        log(INFO, "Spawning %d clients for TID %s (Groups: %s)", len(distinct_groups), task_id, distinct_groups)
                        base_port = 10087
                        model_meta_json = json.dumps(model_meta) if model_meta else ""
                        for i, gid in enumerate(distinct_groups):
                            port = base_port + i
                            cmd = [sys.executable, "client.py", 
                                   "--server_address", f"127.0.0.1:{port}", 
                                   "--parent_address", parent_address, 
                                   "--tid", task_id, 
                                   "--group_id", str(gid)]
                            if model_meta_json:
                                cmd += ["--model_meta", model_meta_json]
                            if use_fixed_scaler:
                                cmd += ["--use_fixed_scaler"]
                            p = subprocess.Popen(cmd)
                            spawned_clients.append(p)
                        # Wait briefly for clients to start up and connect
                        time.sleep(3)
                    else:
                        log(WARNING, "No groups found in MongoDB for TID %s. No clients spawned.", task_id)
                except Exception as e:
                    log(ERROR, "Failed to auto-spawn clients: %s", e)
                    return {"error": f"Task preparation failed: {e}"}, 500

            if callback_url:
                # Async path: return 202 immediately, train in background
                t = threading.Thread(
                    target=self._run_task_and_callback,
                    args=(js, callback_url, spawned_clients),
                )
                t.daemon = True
                t.start()
                log(INFO, "Task %s accepted, training in background. Callback: %s", task_id, callback_url)
                return {"task_id": task_id, "status": "accepted"}, 202
            else:
                # Sync path: backward compatible
                try:
                    _, report = self._task_manager.receive_task(task_config=js)
                finally:
                    # Terminate clients after task
                    for p in spawned_clients:
                        try:
                            p.terminate()
                        except Exception as terminate_err:
                            log(WARNING, "Failed to terminate client process: %s", terminate_err)
                self.get_metrics(report.config[TID])
                return js, 200
        
        @self.app.route("/download/<tid>")
        def download_artifact(tid):
            """Download the packaged model artifact tar.gz for a completed task."""
            tar_path = os.path.join(self._artifacts_dir, f"{tid}.tar.gz")
            if not os.path.isfile(tar_path):
                return {"error": f"Artifact for task {tid} not found"}, 404
            return send_file(
                tar_path,
                mimetype="application/gzip",
                as_attachment=True,
                download_name=f"{tid}.tar.gz",
            )

        @self.app.route("/metrics")
        def metrics():
            """
            Expose Daisy metrics to Prometheus or other tools.
            """
            task_id = request.args.get('task_id', None)
            if task_id is None:
                log(WARNING, "Requested task id doesn't exist.")
                response = make_response("")
                response.headers["content-type"] = "text/plain"
                return response
            if self.get_metrics is None:
                log(WARNING, "get_metrics isn't defined.")
                response = make_response("")
                response.headers["content-type"] = "text/plain"
                return response
            return self.get_metrics(task_id)

    def _init_model_from_meta(self, model_meta: dict, model_path: str) -> None:
        """
        Dynamically initialize a TCN model from MODEL_META and save as .npy.
        
        This eliminates the need for --init_model at master startup time.
        The model architecture is fully determined by the task config.
        """
        import numpy as np
        from model import get_model

        model_params = model_meta.get("model", {})
        input_size = model_params.get("input_size", 10)
        output_size = model_params.get("output_size", 2)
        num_channels = model_params.get("num_channels", [32, 64, 64, 64])
        kernel_size = model_params.get("kernel_size", 2)
        dropout = model_params.get("dropout", 0.2)

        # Also check inference.out_seq_len to compute correct output_size
        inference = model_meta.get("inference", {})
        out_seq_len = inference.get("out_seq_len", 1)
        output_fields = inference.get("output_fields", ["ul_vol", "dl_vol"])
        num_classes = out_seq_len * len(output_fields)

        net = get_model(
            input_dim=input_size,
            num_classes=num_classes,
            num_channels=num_channels,
        ).to("cpu")

        model_ndarray_list = np.array(
            [val.cpu().numpy() for _, val in net.state_dict().items()],
            dtype=object,
        )
        os.makedirs(os.path.dirname(model_path) or ".", exist_ok=True)
        np.save(model_path, model_ndarray_list, allow_pickle=True, fix_imports=True)
        log(INFO, "Initialized model from MODEL_META -> %s (input=%d, output=%d, channels=%s)",
            model_path, input_size, num_classes, num_channels)

    def _copy_seed_file(self, source_path: Optional[str], dest_path: str, label: str) -> None:
        """Copy a seed artifact into the task-scoped model directory."""
        if not source_path:
            raise ValueError(f"{label} path is required")
        if not os.path.isfile(source_path):
            raise FileNotFoundError(f"{label} not found: {source_path}")
        os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
        shutil.copy2(source_path, dest_path)
        log(INFO, "Seeded %s -> %s", label, dest_path)

    def _package_artifacts(self, task_config: dict) -> str:
        """
        Package model artifacts into a tar.gz file.
        
        Includes: model weights (.npy), scaler (.pkl), model script (.py),
        and a generated config.json with metadata.
        
        Returns the absolute path to the created tar.gz.
        """
        task_id = task_config.get(TID, "unknown")
        os.makedirs(self._artifacts_dir, exist_ok=True)
        tar_path = os.path.join(self._artifacts_dir, f"{task_id}.tar.gz")

        # Resolve artifact file paths
        model_path = task_config.get(MODEL_PATH, "model/model.npy")
        model_dir = os.path.dirname(model_path) or "model"
        scaler_path = task_config.get(_SCALER_PATH, os.path.join(model_dir, "scaler.pkl"))
        model_script = task_config.get(_MODEL_SCRIPT, "model.py")

        # Generate config.json with task metadata
        config_data = {
            "TID": task_id,
            "MODEL_PATH": os.path.basename(model_path),
            "SCALER_PATH": os.path.basename(scaler_path),
            "MODEL_SCRIPT": os.path.basename(model_script),
        }
        
        # Merge MODEL_META if provided in the task config, otherwise use defaults
        model_meta = task_config.get("MODEL_META")
        if not model_meta or not isinstance(model_meta, dict):
            model_meta = {
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
                        "total_vol", "ul_vol", "dl_vol",
                        "total_nb_pkts", "ul_nb_pkts", "dl_nb_pkts",
                        "ul_thr", "dl_thr", "ul_pkt_thr", "dl_pkt_thr"
                    ],
                    "output_fields": ["ul_vol", "dl_vol"],
                    "preprocessing": "log1p_standard_scaler"
                }
            }
        config_data.update(model_meta)

        config_json_path = os.path.join(model_dir, "config.json")
        os.makedirs(model_dir, exist_ok=True)
        with open(config_json_path, "w") as f:
            json.dump(config_data, f, indent=2)

        # Create tar.gz
        with tarfile.open(tar_path, "w:gz") as tar:
            if os.path.isfile(model_path):
                tar.add(model_path, arcname=os.path.basename(model_path))
            else:
                log(WARNING, "Model file not found: %s", model_path)

            if os.path.isfile(scaler_path):
                tar.add(scaler_path, arcname=os.path.basename(scaler_path))
            else:
                log(WARNING, "Scaler file not found: %s", scaler_path)

            if os.path.isfile(model_script):
                tar.add(model_script, arcname=os.path.basename(model_script))
            else:
                log(WARNING, "Model script not found: %s", model_script)

            tar.add(config_json_path, arcname="config.json")

        # Cleanup temp config.json
        os.remove(config_json_path)

        log(INFO, "Packaged artifacts for task %s -> %s", task_id, tar_path)
        return tar_path

    def _run_task_and_callback(self, task_config: dict, callback_url: str, spawned_clients: list = None) -> None:
        """Run training in background, package artifacts, and POST result to callback_url."""
        task_id = task_config.get(TID, "unknown")
        if spawned_clients is None:
            spawned_clients = []
            
        try:
            try:
                _, report = self._task_manager.receive_task(task_config=task_config)
            except Exception as e:
                if type(e).__name__ == "EarlyStoppingException" or "EarlyStopping" in str(e):
                    log(INFO, "Training stopped early due to Early Stopping. Proceeding to packaging.")
                else:
                    payload = {
                        "task_id": task_id,
                        "status": "failure",
                        "error": str(e),
                    }
                    log(ERROR, "Task %s failed: %s. Sending failure callback to %s", task_id, e, callback_url)
                    try:
                        http_requests.post(callback_url, json=payload, timeout=30)
                    except Exception as post_err:
                        log(ERROR, "Failed to POST callback to %s: %s", callback_url, post_err)
                    return

            # Training succeeded — get_metrics is optional, don't let it break the callback
            try:
                if self.get_metrics is not None:
                    self.get_metrics(task_id)
            except Exception as e:
                log(WARNING, "get_metrics failed for task %s (non-fatal): %s", task_id, e)

            # Package model artifacts into tar.gz
            try:
                self._package_artifacts(task_config)
            except Exception as e:
                log(ERROR, "Failed to package artifacts for task %s: %s", task_id, e)

            # Build download URL and send success callback
            download_url = f"{self._base_url}/download/{task_id}"
            payload = {
                "task_id": task_id,
                "status": "success",
                "model_url": download_url,
            }
            log(INFO, "Task %s completed. Sending callback to %s", task_id, callback_url)

            try:
                http_requests.post(callback_url, json=payload, timeout=30)
            except Exception as e:
                log(ERROR, "Failed to POST callback to %s: %s", callback_url, e)
                
        finally:
            # Terminate spawned clients to free memory
            for p in spawned_clients:
                try:
                    p.terminate()
                except Exception as e:
                    log(WARNING, "Failed to terminate client process: %s", e)

    def run(self,):
        """Run this HTTP server."""
        self.app.run(host=self._ip, port=self._port)
    
    def set_get_metrics(self, get_metrics_fn: Callable) -> None:
        """Set a callback function to get metrics of a specific task."""
        self.get_metrics = get_metrics_fn
