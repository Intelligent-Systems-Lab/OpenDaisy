from __future__ import annotations

import json
import torch
import numpy as np
import os
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import StandardScaler
import joblib
from typing import Any, Optional

def parse_notifications_json(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)
    return parse_notifications_list(data)

def parse_notifications_list(data):
    # Dictionary to aggregate features: { rounded_timestamp_str: {"sums": [...], "count": 0} }
    agg_map = {}
    
    for req in data:
        items = req.get('notificationItems', [])
        for item in items:
            # Use startTime as the primary source of truth, fallback to timeStamp if parsing legacy data
            timestamp_str = item.get('startTime', item.get('timeStamp'))
            
            # Parse and round to nearest second
            try:
                if "." in timestamp_str:
                    clean_ts = timestamp_str.split(".")[0] + "Z"
                else:
                    clean_ts = timestamp_str
            except:
                clean_ts = timestamp_str
            
            for m in item.get('userDataUsageMeasurements', []):
                vol = m.get('volumeMeasurement', {})
                thr = m.get('throughputMeasurement', {})
                
                ul_thr = float(thr.get('ulThroughput', '0 bps').replace(' bps', ''))
                dl_thr = float(thr.get('dlThroughput', '0 bps').replace(' bps', ''))
                ul_p_thr = float(thr.get('ulPacketThroughput', '0 pps').replace(' pps', ''))
                dl_p_thr = float(thr.get('dlPacketThroughput', '0 pps').replace(' pps', ''))
                
                # We extract 10 features.
                features = [
                    vol.get('totalVolume', 0),
                    vol.get('ulVolume', 0),
                    vol.get('dlVolume', 0),
                    vol.get('totalNbOfPackets', 0),
                    vol.get('ulNbOfPackets', 0),
                    vol.get('dlNbOfPackets', 0),
                    ul_thr, dl_thr, ul_p_thr, dl_p_thr
                ]
                
                if clean_ts not in agg_map:
                    agg_map[clean_ts] = {"sums": [0]*10, "count": 0}
                
                for i in range(10):
                    agg_map[clean_ts]["sums"][i] += features[i]
                agg_map[clean_ts]["count"] += 1

    measurements = []
    # Sort chronologically
    for ts, agg in sorted(agg_map.items()):
        cnt = agg["count"]
        final_features = []
        for i in range(10):
            if i < 6:
                # Volumes and Packets: SUM
                final_features.append(agg["sums"][i])
            else:
                # Throughputs: MEAN
                final_features.append(agg["sums"][i] / cnt if cnt > 0 else 0)
                
        measurements.append({
            'ue_ip': 'group_aggregate', # Treating all UEs collectively as the group stream
            'timestamp': ts,
            'features': final_features
        })
        
    return measurements

def notifications_to_log_feature_rows(data):
    measurements = parse_notifications_list(data)
    rows = []
    for m in measurements:
        rows.append(np.log1p(np.array(m['features'], dtype=np.float32)))
    if not rows:
        return np.empty((0, 10), dtype=np.float32)
    return np.stack(rows)

def build_shared_scaler_from_notifications(data):
    rows = notifications_to_log_feature_rows(data)
    scaler = StandardScaler()
    if len(rows) > 0:
        scaler.fit(rows)
    return scaler, rows

def resolve_shared_scaler_path(tid):
    if not tid:
        return None
    return os.path.join('model', tid, 'scaler.pkl')

def load_tid_documents(tid: str, group_id: Optional[str], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    from pymongo import MongoClient

    mongo_uri = cfg.get("MONGO_URI", "mongodb://localhost:27017/")
    m_client = MongoClient(mongo_uri)
    col = m_client["daisy_mtlf"]["training_data"]

    query = {"tid": tid}
    if group_id:
        query["group_id"] = group_id

    docs = list(col.find(query))
    if not docs:
        raise ValueError(f"No data found in MongoDB for TID: {tid}, Group: {group_id}")
    return docs

def create_isolated_sliding_windows(ue_data_streams, seq_length, out_seq_len):
    samples = []
    for ue_ip, stream in ue_data_streams.items():
        # Sort by timestamp to preserve sequential integrity
        stream.sort(key=lambda x: x['timestamp'])
        
        if len(stream) < seq_length + out_seq_len:
            continue
            
        for i in range(len(stream) - seq_length - out_seq_len + 1):
            input_window = stream[i : i + seq_length]
            output_window = stream[i + seq_length : i + seq_length + out_seq_len]
            
            # Feature shape: (seq_length, num_features)
            x = np.array([item['features'] for item in input_window], dtype=np.float32)
            
            # Targets: ulVolume (index 1) and dlVolume (index 2) for the next out_seq_len steps
            # Shape: (out_seq_len, 2)
            y = np.array([[item['features'][1], item['features'][2]] for item in output_window], dtype=np.float32)
            
            # Flatten to 1D array of size (out_seq_len * 2) = 10
            y = y.flatten()
            
            # Transpose x for PyTorch Conv1d: (num_features, seq_length)
            x = x.transpose(1, 0)
            
            samples.append((x, y))
    return samples

class EESTCNDataset(Dataset):
    def __init__(self, data_dirs=None, run_indices=None, mongo_data=None, seq_length=30, out_seq_len=5, scaler=None):
        self.seq_length = seq_length
        self.out_seq_len = out_seq_len
        self.samples = []
        
        all_features = []
        isolated_streams_per_run = []
        
        if mongo_data is not None:
            measurements = parse_notifications_list(mongo_data)
            ue_data_streams = {}
            for m in measurements:
                ue_ip = m['ue_ip']
                feat = np.log1p(np.array(m['features'], dtype=np.float32))
                m['features'] = feat
                all_features.append(feat)
                
                if ue_ip not in ue_data_streams:
                    ue_data_streams[ue_ip] = []
                ue_data_streams[ue_ip].append(m)
            isolated_streams_per_run.append(ue_data_streams)
        elif data_dirs and run_indices:
            for d in data_dirs:
                for run_idx in run_indices:
                    json_path = os.path.join(d, f'training_notifications_run{run_idx:03d}.json')
                    if not os.path.exists(json_path):
                        continue
                        
                    measurements = parse_notifications_json(json_path)
                
                    # Group by UE IP for isolation within this specific run boundary
                    ue_data_streams = {}
                    for m in measurements:
                        ue_ip = m['ue_ip']
                        # 1. Applying Log Transform (log1p to handle zeros)
                        feat = np.log1p(np.array(m['features'], dtype=np.float32))
                        m['features'] = feat
                        all_features.append(feat)
                        
                        if ue_ip not in ue_data_streams:
                            ue_data_streams[ue_ip] = []
                        ue_data_streams[ue_ip].append(m)
                        
                    isolated_streams_per_run.append(ue_data_streams)

        all_features = np.array(all_features)
        
        # 2. Fit StandardScaler globally across the collected logs
        if scaler is None:
            self.scaler = StandardScaler()
            if len(all_features) > 0:
                self.scaler.fit(all_features)
        else:
            self.scaler = scaler

        # 3. Apply StandardScaler and generate Isolated Sliding Windows
        for ue_data_streams in isolated_streams_per_run:
            for ue_ip in ue_data_streams:
                for m in ue_data_streams[ue_ip]:
                    if hasattr(self.scaler, 'mean_'):
                        m['features'] = self.scaler.transform(m['features'].reshape(1, -1))[0]
            
            run_samples = create_isolated_sliding_windows(ue_data_streams, seq_length, out_seq_len)
            self.samples.extend(run_samples)

    def __len__(self):
        return len(self.samples)
        
    def __getitem__(self, idx):
        x, y = self.samples[idx]
        return torch.tensor(x, dtype=torch.float32), torch.tensor(y, dtype=torch.float32)

def get_local_stats(
    data_dirs=None,
    tid=None,
    group_id=None,
    seq_length=30,
    out_seq_len=5,
):
    """Calculate local scaler statistics on this client's own rows only."""
    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daisyconfig.json")
    cfg = {}
    if os.path.exists(cfg_path):
        with open(cfg_path, "r") as f:
            cfg = json.load(f)

    if tid is not None:
        docs = load_tid_documents(tid, group_id, cfg)
        dataset = EESTCNDataset(
            mongo_data=docs,
            seq_length=seq_length,
            out_seq_len=out_seq_len,
            scaler=None,
        )
    else:
        if data_dirs is None:
            data_dirs_str = cfg.get("DATA_DIRS", "ees_training_data")
            data_dirs = [d.strip() for d in data_dirs_str.split(',')]
        elif isinstance(data_dirs, str):
            data_dirs = [data_dirs]
        dataset = EESTCNDataset(
            data_dirs=data_dirs,
            run_indices=list(range(1, 13)),
            seq_length=seq_length,
            out_seq_len=out_seq_len,
            scaler=None,
        )

    scaler = dataset.scaler
    if not hasattr(scaler, "mean_"):
        raise RuntimeError("Local scaler statistics are unavailable because no feature rows were produced")
    return {
        "mean": scaler.mean_.tolist(),
        "var": scaler.var_.tolist(),
        "n": int(scaler.n_samples_seen_),
    }

def get_dataloaders(
    data_dirs=None,
    tid=None,
    group_id=None,
    batch_size=32,
    seq_length=30,
    out_seq_len=5,
    save_scaler=True,
    require_shared_scaler=False,
):
    # Read daisyconfig.json once
    import os
    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daisyconfig.json")
    cfg = {}
    if os.path.exists(cfg_path):
        with open(cfg_path, "r") as f:
            cfg = json.load(f)

    if tid is not None:
        from torch.utils.data import Subset

        docs = load_tid_documents(tid, group_id, cfg)

        scaler_path = resolve_shared_scaler_path(tid)
        shared_scaler = None
        if scaler_path and os.path.exists(scaler_path):
            shared_scaler = joblib.load(scaler_path)
            save_scaler = False
            print(
                f"[Dataset] TID={tid} group={group_id} loaded shared scaler from {scaler_path} "
                f"(require_shared_scaler={require_shared_scaler})"
            )
        elif require_shared_scaler:
            raise FileNotFoundError(
                f"Shared scaler is required for TID {tid}, but {scaler_path} does not exist"
            )
        else:
            print(
                f"[Dataset] TID={tid} group={group_id} shared scaler missing; "
                f"building in-memory local bootstrap dataset"
            )

        full_dataset = EESTCNDataset(
            mongo_data=docs,
            seq_length=seq_length,
            out_seq_len=out_seq_len,
            scaler=shared_scaler,
        )
            
        total_len = len(full_dataset)
        train_len = int(0.8 * total_len)
        
        train_dataset = Subset(full_dataset, range(0, train_len))
        val_dataset = Subset(full_dataset, range(train_len, total_len))
        
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
        return train_loader, val_loader, out_seq_len * 2
        
    if data_dirs is None:
        data_dirs_str = cfg.get("DATA_DIRS", "ees_training_data")
        data_dirs = [d.strip() for d in data_dirs_str.split(',')]
    elif isinstance(data_dirs, str):
        data_dirs = [data_dirs]
        
    train_dataset = EESTCNDataset(data_dirs=data_dirs, run_indices=list(range(1, 13)), seq_length=seq_length, out_seq_len=out_seq_len)
    
    if save_scaler:
        os.makedirs('model', exist_ok=True)
        joblib.dump(train_dataset.scaler, os.path.join('model', 'scaler.pkl'))

    val_dataset = EESTCNDataset(data_dirs=data_dirs, run_indices=list(range(13, 16)), seq_length=seq_length, out_seq_len=out_seq_len, scaler=train_dataset.scaler)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    return train_loader, val_loader, out_seq_len * 2

if __name__ == '__main__':
    train_loader, val_loader, output_dim = get_dataloaders()
    print(f"Output Dim: {output_dim}")
    for x, y in train_loader:
        print(f"X shape: {x.shape}, Y shape: {y.shape}")
        break
