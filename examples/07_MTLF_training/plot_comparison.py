import torch
import numpy as np
import matplotlib.pyplot as plt
from model import get_model
from dataset import get_dataloaders
import sys
import os

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print("Loading data...")

# We load ONLY cat123 validation data so we can see the real difference
_, testloader, output_dim = get_dataloaders(['cat123_training_data'], batch_size=32, seq_length=30, out_seq_len=1, save_scaler=False)
# IMPORTANT: we need the Universal Scaler that both models trained with/were evaluated on
_, trainloader_full, _ = get_dataloaders(['ees_training_data', 'cat123_training_data'], batch_size=32, seq_length=30, out_seq_len=1, save_scaler=False)
scaler = trainloader_full.dataset.scaler

net = get_model(input_dim=10, num_classes=output_dim, num_channels=[32, 64, 64, 64]).to(device)

def get_predictions(model_path):
    print(f"Generating predictions for {model_path}...")
    model_weights = np.load(model_path, allow_pickle=True)
    state_dict = zip(net.state_dict().keys(), model_weights)
    net.load_state_dict({k: torch.tensor(v) for k, v in state_dict})
    net.eval()
    
    all_preds = []
    all_labels = []
    with torch.no_grad():
        for sequences, labels in testloader:
            sequences = sequences.to(device)
            outputs = net(sequences)
            all_preds.append(outputs.cpu().numpy())
            all_labels.append(labels.numpy())
            
    y_pred = np.vstack(all_preds)
    y_true = np.vstack(all_labels)
    
    # Scale back to linear Byte space
    dummy_pred = np.zeros((y_pred.shape[0], 10))
    dummy_true = np.zeros((y_true.shape[0], 10))
    dummy_pred[:, 1:3] = y_pred
    dummy_true[:, 1:3] = y_true
    
    pred_log = scaler.inverse_transform(dummy_pred)[:, 1:3]
    true_log = scaler.inverse_transform(dummy_true)[:, 1:3]
    
    pred_bytes = np.expm1(pred_log)
    true_bytes = np.expm1(true_log)
    
    return pred_bytes, true_bytes

try:
    pred_new, true_val = get_predictions('model/model_universal.npy')
    pred_old, _ = get_predictions('model/model_single.npy')

    # Plotting first 300 samples 
    N = 300
    true_val = true_val[:N]
    pred_new = pred_new[:N]
    pred_old = pred_old[:N]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    # UL Volume
    ax1.plot(true_val[:, 0], label='True UL Volume', color='black', linewidth=2)
    ax1.plot(pred_new[:, 0], label='New Model (Universal)', color='blue', linestyle='--', alpha=0.8)
    ax1.plot(pred_old[:, 0], label='Old Model (model_original.npy)', color='red', linestyle='-.', alpha=0.8)
    ax1.set_title("Uplink Volume Forecasting Comparison on Unknown Domain (CAT123)")
    ax1.set_ylabel("Bytes")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # DL Volume
    ax2.plot(true_val[:, 1], label='True DL Volume', color='black', linewidth=2)
    ax2.plot(pred_new[:, 1], label='New Model (Universal)', color='blue', linestyle='--', alpha=0.8)
    ax2.plot(pred_old[:, 1], label='Old Model (model_original.npy)', color='red', linestyle='-.', alpha=0.8)
    ax2.set_title("Downlink Volume Forecasting Comparison on Unknown Domain (CAT123)")
    ax2.set_xlabel("Time step")
    ax2.set_ylabel("Bytes")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    artifact_dir = "/home/king25158986/.gemini/antigravity/brain/040f1ecd-8fce-428f-8e7f-0334a1f5418e"
    os.makedirs(artifact_dir, exist_ok=True)
    out_path = os.path.join(artifact_dir, "volume_comparison.png")
    plt.savefig(out_path, dpi=300)
    print(f"Saved comparison plot to {out_path}")

except Exception as e:
    print(f"Error during execution: {e}")
