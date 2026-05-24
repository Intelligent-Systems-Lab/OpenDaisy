import torch
import numpy as np
from model import get_model
from dataset import get_dataloaders
from sklearn.metrics import mean_squared_error, mean_absolute_error

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
_, testloader, output_dim = get_dataloaders(batch_size=32, seq_length=30, out_seq_len=1, save_scaler=False)
net = get_model(input_dim=10, num_classes=output_dim, num_channels=[32, 64, 64, 64]).to(device)

model_weights = np.load('model/model.npy', allow_pickle=True)
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

mse = mean_squared_error(y_true, y_pred)
mae = mean_absolute_error(y_true, y_pred)

print(f"--- Final Evaluation on Run13-Run15 (Validation Data) ---")
print(f"Mean Squared Error (MSE)   : {mse:.4f} (Calculated on Log1p Scaled space)")
print(f"Mean Absolute Error (MAE)  : {mae:.4f} (Calculated on Log1p Scaled space)")
