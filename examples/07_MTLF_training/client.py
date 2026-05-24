import os
import sys
from pathlib import Path

DAISY_SRC_PY = Path(__file__).resolve().parents[2] / "src" / "py"
if str(DAISY_SRC_PY) not in sys.path:
    sys.path.insert(0, str(DAISY_SRC_PY))

import warnings
from collections import OrderedDict

import daisyfl as fl
from model import get_model
from dataset import get_dataloaders
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm
from daisyfl.common import (
    METRICS,
    LOSS,
    CID,
    ACCURACY,
    DATA_SAMPLES,
    CURRENT_ROUND,
)
import argparse
import uuid
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("--server_address", type=str, help="my grpc server port")
parser.add_argument("--parent_address", type=str, help="for grpc connection")
parser.add_argument('--data_dirs', nargs='+', default=['ees_training_data'], help="List of data directories")
parser.add_argument('--tid', type=str, default=None, help="TID to fetch data from MongoDB")
parser.add_argument('--group_id', type=str, default=None, help="Group ID for the isolated dataset")
parser.add_argument('--model_meta', type=str, default=None, help="JSON string of MODEL_META from task config")
parser.add_argument('--use_fixed_scaler', action='store_true', help="Require a pre-seeded shared scaler and skip scaler aggregation flow")
args = parser.parse_args()

# Parse MODEL_META with defaults
import json as _json
_model_meta = _json.loads(args.model_meta) if args.model_meta else {}
_model_cfg = _model_meta.get("model", {})
_infer_cfg = _model_meta.get("inference", {})

_train_cfg = _model_meta.get("training", {})
_input_dim = _model_cfg.get("input_size", 10)
_num_channels = _model_cfg.get("num_channels", [32, 64, 64, 64])
_seq_length = _infer_cfg.get("seq_length", 30)
_out_seq_len = _infer_cfg.get("out_seq_len", 5)
_local_epochs = int(_train_cfg.get("local_epochs", 3))

warnings.filterwarnings("ignore", category=UserWarning)
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

print(
    f"[Client] startup group={args.group_id} tid={args.tid} "
    f"use_fixed_scaler={args.use_fixed_scaler} seq_length={_seq_length} out_seq_len={_out_seq_len}"
)

def train(net, trainloader, epochs, lr=0.001):
    """Train the model on the training set using Huber Loss."""
    criterion = torch.nn.HuberLoss()
    optimizer = torch.optim.Adam(net.parameters(), lr=lr)
    
    net.train()
    for _ in range(epochs):
        for sequences, labels in tqdm(trainloader, desc="Training"):
            sequences, labels = sequences.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = net(sequences)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()


def test(net, testloader):
    """Validate the model on the test set."""
    criterion = torch.nn.MSELoss()
    l1_loss = torch.nn.L1Loss(reduction='sum')
    total, mse_loss, mae_sum = 0, 0.0, 0.0
    
    net.eval()
    with torch.no_grad():
        for sequences, labels in tqdm(testloader, desc="Evaluating"):
            sequences, labels = sequences.to(device), labels.to(device)
            outputs = net(sequences)
            
            mse_loss += criterion(outputs, labels).item() * labels.size(0)
            mae_sum += l1_loss(outputs, labels).item()
            total += labels.size(0)
            
    return mse_loss / max(total, 1), mae_sum / max(total, 1)


# Use MODEL_META values for dataset and model construction
trainloader, testloader, output_dim = get_dataloaders(
    data_dirs=args.data_dirs, tid=args.tid, group_id=args.group_id,
    batch_size=32, seq_length=_seq_length, out_seq_len=_out_seq_len,
    save_scaler=False, require_shared_scaler=args.use_fixed_scaler)

net = get_model(input_dim=_input_dim, num_classes=output_dim, num_channels=_num_channels).to(device)

def reload_dataloaders() -> None:
    global trainloader, testloader
    trainloader, testloader, _ = get_dataloaders(
        data_dirs=args.data_dirs,
        tid=args.tid,
        group_id=args.group_id,
        batch_size=32,
        seq_length=_seq_length,
        out_seq_len=_out_seq_len,
        save_scaler=False,
        require_shared_scaler=True,
    )

class DaisyTrainer(fl.client.NumPyTrainer):
    def get_parameters(self, config):
        return [val.cpu().numpy() for _, val in net.state_dict().items()]

    def set_parameters(self, parameters):
        params_dict = zip(net.state_dict().keys(), parameters)
        state_dict = OrderedDict({k: torch.tensor(v) for k, v in params_dict})
        net.load_state_dict(state_dict, strict=True)

    def fit(self, parameters, config):
        self.set_parameters(parameters)

        if config.get("is_stats_round"):
            from dataset import get_local_stats

            print(f"\n[Client] Stats round: calculating local scaler statistics for group={args.group_id}")
            stats = get_local_stats(
                data_dirs=args.data_dirs,
                tid=args.tid,
                group_id=args.group_id,
                seq_length=_seq_length,
                out_seq_len=_out_seq_len,
            )
            config[METRICS] = {"scaler_stats": stats}
            return self.get_parameters(config={}), config

        if args.use_fixed_scaler and config.get(CURRENT_ROUND, 0) == 1:
            print(f"[Client] Fixed scaler mode: training starts immediately with pre-seeded shared scaler for group={args.group_id}")

        if args.tid and (not args.use_fixed_scaler) and config.get(CURRENT_ROUND, 0) == 2:
            print(f"[Client] Round 2: reloading dataloaders with aggregated global scaler for group={args.group_id}")
            reload_dataloaders()

        lr = config.get("lr", 0.001)
        train(net, trainloader, epochs=_local_epochs, lr=lr)
        config[METRICS] = { DATA_SAMPLES: len(trainloader.dataset) }
        return self.get_parameters(config={}), config

    def evaluate(self, parameters, config):
        self.set_parameters(parameters)

        if config.get("is_stats_round"):
            config[METRICS] = {
                "MAE": 0.0,
                ACCURACY: 0.0,
                LOSS: 0.0,
                DATA_SAMPLES: len(testloader.dataset),
            }
            return config

        loss, mae = test(net, testloader)
        config[METRICS] = {
            "MAE": mae,
            ACCURACY: 0.0,
            LOSS: loss,
            DATA_SAMPLES: len(testloader.dataset)
        }
        return config

metadata = (
    (CID, str(uuid.uuid4())),
)

if __name__=='__main__':
    # Start Daisy client
    fl.client.start_client_numpy(
        server_address=args.server_address,
        parent_address=args.parent_address,
        numpy_trainer=DaisyTrainer(),
        metadata=metadata,
    )
