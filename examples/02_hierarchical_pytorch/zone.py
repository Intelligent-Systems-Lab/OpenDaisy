import daisyfl as fl
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--parent_address", type=str, help="parent grpc server port")
parser.add_argument("--server_address", type=str, help="my grpc server port")
args = parser.parse_args()


fl.zone.start_zone(
    parent_address=args.parent_address,
    server_address=args.server_address,
)
