import argparse
import subprocess
import os
import sys
import yaml

parser = argparse.ArgumentParser()
parser.add_argument('--init_model', action='store_true', help="Initialize the model while deploy the master?")
parser.add_argument('--data_dirs', nargs='+', default=['ees_training_data'], help="List of directories for training data")
parser.add_argument('--training_name', type=str, default="", help="Name of the training session for isolated saving")
args = parser.parse_args()

data_dirs_str = " ".join(args.data_dirs)

python_bin = sys.executable

env = os.environ.copy()
if args.training_name:
    env["TRAINING_NAME"] = args.training_name

with open("nodes.yaml", "r") as stream:
    try:
        nodes = yaml.safe_load(stream)
        
        master_address = nodes['master']['address']
        api_ip = nodes['master']['api_ip']
        api_port = nodes['master']['api_port']
        
        master_log = open("master.log", "w")
        if args.init_model:
            subprocess.Popen([python_bin, "master.py", "--server_address", master_address, "--api_ip", f"{api_ip}", "--api_port", f"{api_port}", "--init_model", "--data_dirs"] + args.data_dirs, stdout=master_log, stderr=subprocess.STDOUT, env=env)
        else:
            subprocess.Popen([python_bin, "master.py", "--server_address", master_address, "--api_ip", f"{api_ip}", "--api_port", f"{api_port}", "--data_dirs"] + args.data_dirs, stdout=master_log, stderr=subprocess.STDOUT, env=env)

        print("Skipping static client deployment. Clients are expected to be started dynamically.")
    except yaml.YAMLError as exc:
        print(exc)

print("Daisy started!")
