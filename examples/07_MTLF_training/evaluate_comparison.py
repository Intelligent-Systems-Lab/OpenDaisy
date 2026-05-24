import torch
import numpy as np
from model import get_model
from dataset import get_dataloaders
from sklearn.metrics import mean_squared_error, mean_absolute_error
import sys

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

def evaluate_raw_bytes(data_dir, model_net, scaler):
    print(f"\n--- Evaluating Validation Data on [{data_dir}] ---")
    _, testloader, _ = get_dataloaders(data_dir, batch_size=32, seq_length=30, out_seq_len=1, save_scaler=False)
    
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for sequences, labels in testloader:
            sequences = sequences.to(device)
            outputs = model_net(sequences)
            
            all_preds.append(outputs.cpu().numpy())
            all_labels.append(labels.numpy())

    y_pred = np.vstack(all_preds)
    y_true = np.vstack(all_labels)

    # Reconstruct a fake 10-dim array for the scaler
    dummy_pred = np.zeros((y_pred.shape[0], 10))
    dummy_true = np.zeros((y_true.shape[0], 10))
    
    dummy_pred[:, 1:3] = y_pred
    dummy_true[:, 1:3] = y_true
    
    # Scale back to log space
    pred_log = scaler.inverse_transform(dummy_pred)[:, 1:3]
    true_log = scaler.inverse_transform(dummy_true)[:, 1:3]
    
    # Exponentiate back to linear Byte space
    pred_bytes = np.expm1(pred_log)
    true_bytes = np.expm1(true_log)

    mse = mean_squared_error(true_bytes, pred_bytes)
    mae = mean_absolute_error(true_bytes, pred_bytes)
    
    print(f"RAW Mean Squared Error (MSE)   : {mse:.2f} Bytes^2")
    print(f"RAW Mean Absolute Error (MAE)  : {mae:.2f} Bytes")
    return mse, mae

# Accept args to decide which model to load
model_path = sys.argv[1] if len(sys.argv) > 1 else 'model/model.npy'
data_mode = sys.argv[2] if len(sys.argv) > 2 else 'universal'

if data_mode == 'single':
    dirs_to_load = 'ees_training_data'
else:
    dirs_to_load = ['ees_training_data', 'cat123_training_data']

train_loader, _, output_dim = get_dataloaders(dirs_to_load, batch_size=32, seq_length=30, out_seq_len=1, save_scaler=False)
active_scaler = train_loader.dataset.scaler

net = get_model(input_dim=10, num_classes=output_dim, num_channels=[32, 64, 64, 64]).to(device)
model_weights = np.load(model_path, allow_pickle=True)
state_dict = zip(net.state_dict().keys(), model_weights)
net.load_state_dict({k: torch.tensor(v) for k, v in state_dict})
net.eval()

print(f"\n============================================")
print(f"Evaluating Model: {model_path} | Scaler Space: {data_mode}")
print(f"============================================")

mse_ees, mae_ees = evaluate_raw_bytes('ees_training_data', net, active_scaler)
mse_cat, mae_cat = evaluate_raw_bytes('cat123_training_data', net, active_scaler)

print(f"\n[Comparison Summary]")
print(f"Raw MSE Delta: {abs(mse_ees - mse_cat):.2f} Bytes^2")
print(f"Raw MAE Delta: {abs(mae_ees - mae_cat):.2f} Bytes")
