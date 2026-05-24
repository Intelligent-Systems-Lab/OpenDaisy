import joblib
import numpy as np
import os

def compare_scalers(name, s1_path, s2_path):
    print(f"\n[{name}] Comparing: ")
    print(f" 1. {s1_path}")
    print(f" 2. {s2_path}")
    
    if not os.path.exists(s1_path):
        print(f" => ERORR: {s1_path} not found.")
        return
    if not os.path.exists(s2_path):
        print(f" => ERORR: {s2_path} not found.")
        return
        
    scaler1 = joblib.load(s1_path)
    scaler2 = joblib.load(s2_path)
    
    mean_diff = np.abs(scaler1.mean_ - scaler2.mean_).max()
    var_diff = np.abs(scaler1.var_ - scaler2.var_).max()
    scale_diff = np.abs(scaler1.scale_ - scaler2.scale_).max()
    
    print(f" Max diff in mean_: {mean_diff}")
    print(f" Max diff in var_: {var_diff}")
    print(f" Max diff in scale_: {scale_diff}")
    
    if mean_diff < 1e-6 and var_diff < 1e-6 and scale_diff < 1e-6:
        print(" => Result: They are IDENTICAL.")
    else:
        print(" => Result: They are DIFFERENT.")

base_dir = '/home/king25158986/daisy/examples/07_MTLF_training'

# Compare EES Scalers
compare_scalers(
    "EES Data", 
    os.path.join(base_dir, 'model/scaler_original.pkl'), 
    os.path.join(base_dir, 'scaler.pkl')
)

# Compare Universal Scalers
compare_scalers(
    "Universal Data", 
    os.path.join(base_dir, 'model/scaler_new.pkl'), 
    os.path.join(base_dir, 'universal_training/scaler.pkl')
)
