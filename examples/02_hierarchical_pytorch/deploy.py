from typing import Dict
import yaml
import argparse
import os
from torchvision.datasets import CIFAR10
from torchvision.transforms import Compose, Normalize, ToTensor

SLEEP_3 = "sleep 3"

parser = argparse.ArgumentParser()
parser.add_argument("--yaml", type=str, default="nodes.yaml", help="Path to yaml file(topology description)")
parser.add_argument('--init_model', action='store_true', help="Initialize the model while deploy the master?")
args = parser.parse_args()

def deploy_master(address, api_ip, api_port):
    """deploy master"""
    if args.init_model:
        os.system("python master.py --server_address={} --api_ip={} --api_port={} --init_model &".format(
            address,
            api_ip,
            api_port
        ))
    else:
        os.system("python master.py --server_address={} --api_ip={} --api_port={} &".format(
            address,
            api_ip,
            api_port
        ))
    os.system(SLEEP_3)

def deploy_zone(address, parent):
    """deploy zone"""
    os.system("python zone.py --server_address={} --parent_address={} &".format(
        address,
        parent
    ))
    os.system(SLEEP_3)

def deploy_client(address, parent):
    """deploy client"""
    os.system("python client.py --server_address={} --parent_address={} &".format(
        address,
        parent
    ))
    os.system(SLEEP_3)

def deploy_nodes(js: Dict, parent=None):
    for key in list(js.keys()):
        # deploy self
        if js[key]["type"] == "master":
            deploy_master(js[key]["address"], js[key]["api_ip"], js[key]["api_port"])
        elif js[key]["type"] == "zone":
            deploy_zone(js[key]["address"], parent)
        else:
            deploy_client(js[key]["address"], parent)
        # deploy children
        if js[key].__contains__("children"):
            for child in js[key]["children"]:
                deploy_nodes(child, js[key]["address"])

with open(args.yaml, "r") as file:
    # Download CIFAR-10
    trf = Compose([ToTensor(), Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])
    CIFAR10("./data", train=True, download=True, transform=trf)
    CIFAR10("./data", train=False, download=True, transform=trf)
    # Deploy Daisy nodes
    deploy_nodes(yaml.load(file, Loader=yaml.FullLoader))
    
