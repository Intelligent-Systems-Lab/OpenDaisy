import sys, os, torch, numpy as np
sys.path.insert(0, '/home/king25158986/daisy/examples/07_MTLF_training')
from dataset import parse_notifications_json, create_isolated_sliding_windows

measurements = parse_notifications_json('/home/king25158986/daisy/examples/07_MTLF_training/cat1/training_notifications_run001.json')
ue_data_streams = {}
for m in measurements:
    ue_ip = m['ue_ip']
    feat = np.log1p(np.array(m['features'], dtype=np.float32))
    m['features'] = feat
    if ue_ip not in ue_data_streams: ue_data_streams[ue_ip] = []
    ue_data_streams[ue_ip].append(m)

samples = create_isolated_sliding_windows(ue_data_streams, 30, 1)
print(f"Samples found: {len(samples)}")
if len(samples) > 0:
    x, y = samples[0]
    print(f"X shape: {x.shape}, Y shape: {y.shape}")
