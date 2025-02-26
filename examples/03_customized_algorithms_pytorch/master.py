import daisyfl as fl
import argparse
import numpy as np
from model import Net

parser = argparse.ArgumentParser()
parser.add_argument("--server_address", type=str, help="my grpc server port")
parser.add_argument("--api_ip", type=str, help="for api_handler")
parser.add_argument("--api_port", type=str, help="for api_handler")
parser.add_argument('--init_model', action='store_true', help="Initialize the model while deploy the master?")
args = parser.parse_args()

if args.init_model:
    net = Net().to("cpu")
    model_ndarray_list = np.array([val.cpu().numpy() for _, val in net.state_dict().items()], dtype=object)
    np.save("model.npy", model_ndarray_list, allow_pickle=True, fix_imports=True)

fl.master.start_master(
    server_address=args.server_address,
    api_ip=args.api_ip,
    api_port=int(args.api_port),
)
