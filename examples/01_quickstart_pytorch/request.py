import argparse
import json
import requests
import uuid
from daisyfl.common import TID

parser = argparse.ArgumentParser()
parser.add_argument("--json", type=str, help="json path")
parser.add_argument("--api", type=str, help="Restful API url")
parser.add_argument("--method", type=str, help="get or post")
args = parser.parse_args()

js = {}

# Load JSON file
if args.json is not None:
    f = open(args.json, "r")
    js = json.load(f)

# TID
if not js.__contains__(TID):
    js[TID] = str(uuid.uuid4())

# Send request
if hasattr(args, "method"):
    if args.method == "get":
        res = requests.get(args.api)
    else:
        requests.post(args.api, json=js)
else:
    requests.post(args.api, json=js)
