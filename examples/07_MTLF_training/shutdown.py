from typing import Dict
from daisyfl.common import Status, ErrorCode, Shutdown
from daisyfl.utils import daisyfl_serde
from daisyfl.utils.connection import grpc_connection
from daisyfl.proto.transport_pb2 import ClientMessage, ServerMessage
import yaml
from threading import Event

def get_nodes(js: Dict):
    nodes = []
    for key in list(js.keys()):
        if not js[key].__contains__("children"):
            return [js[key]["address"]]
        else:
            for child in js[key]["children"]:
                nodes += get_nodes(child)
        nodes += [js[key]["address"]]
    return nodes

with open("nodes.yaml", "r") as file:
    nodes = get_nodes(yaml.load(file, Loader=yaml.FullLoader))
    for node in nodes:
        try:
            # build connection
            with grpc_connection(
                parent_address=node,
                metadata=(("node_address", node),),
                uplink_certificates=None
            ) as conn:
                send, receive = conn
                # send message
                shutdown_signal = Shutdown(status=Status(error_code=ErrorCode.OK, message=""))
                cm = ClientMessage(shutdown=daisyfl_serde.shutdown_to_proto(shutdown_signal))
                send(cm)
                Event().wait(timeout=2)
        except:
            pass
