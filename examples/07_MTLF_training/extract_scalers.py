import sys
import os
import joblib

base_dir = '/home/king25158986/daisy/examples/07_MTLF_training'

print("--- Generating Scaler for 07_MTLF_training (EES) ---")
sys.path.insert(0, base_dir)
from dataset import get_dataloaders as get_dl_ees
train_loader1, _, _ = get_dl_ees(os.path.join(base_dir, 'ees_training_data'))
scaler_ees = train_loader1.dataset.scaler
joblib.dump(scaler_ees, os.path.join(base_dir, 'scaler_ees.pkl'))
print(f"Saved: {os.path.join(base_dir, 'scaler_ees.pkl')} (Mean: {scaler_ees.mean_[0]:.4f}...)")

sys.path.pop(0) # remove base dir

print("\n--- Generating Scaler for universal_training ---")
univ_dir = os.path.join(base_dir, 'universal_training')
sys.path.insert(0, univ_dir)

# We must delete the cached dataset module so it reloads from universal_training/dataset.py
if 'dataset' in sys.modules:
    del sys.modules['dataset']

from dataset import get_dataloaders as get_dl_univ
train_loader2, _, _ = get_dl_univ([
    os.path.join(base_dir, 'ees_training_data'), 
    os.path.join(base_dir, 'cat123_training_data')
])
scaler_univ = train_loader2.dataset.scaler
joblib.dump(scaler_univ, os.path.join(univ_dir, 'scaler_universal.pkl'))
print(f"Saved: {os.path.join(univ_dir, 'scaler_universal.pkl')} (Mean: {scaler_univ.mean_[0]:.4f}...)")

print("\nDone! scalers have been created.")
