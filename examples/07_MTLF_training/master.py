import argparse
import numpy as np
import os
import sys
from pathlib import Path

DAISY_SRC_PY = Path(__file__).resolve().parents[2] / "src" / "py"
if str(DAISY_SRC_PY) not in sys.path:
    sys.path.insert(0, str(DAISY_SRC_PY))

import daisyfl as fl
from model import get_model
from dataset import get_dataloaders

parser = argparse.ArgumentParser()
parser.add_argument("--server_address", type=str, help="my grpc server port")
parser.add_argument("--api_ip", type=str, help="for api_handler")
parser.add_argument("--api_port", type=str, help="for api_handler")
parser.add_argument('--init_model', action='store_true', help="Initialize the model while deploy the master?")
parser.add_argument('--data_dirs', nargs='+', default=['ees_training_data'], help="List of data directories")
args = parser.parse_args()

if args.init_model:
    # Need to know num_classes based on the dataset vocab to initialize correctly
    # We load just a tiny bit of data to get num_classes
    try:
        _, _, num_classes = get_dataloaders(data_dirs=args.data_dirs, batch_size=1)
    except Exception:
        num_classes = 2
        print("Warning: Data load failed, initialized with 2 classes.")

    net = get_model(input_dim=10, num_classes=num_classes, num_channels=[32, 64, 64, 64]).to("cpu")
    model_ndarray_list = np.array([val.cpu().numpy() for _, val in net.state_dict().items()], dtype=object)
    
    os.makedirs('model', exist_ok=True)
    np.save(os.path.join('model', "model.npy"), model_ndarray_list, allow_pickle=True, fix_imports=True)

fl.master.start_master(
    server_address=args.server_address,
    api_ip=args.api_ip,
    api_port=int(args.api_port),
)
