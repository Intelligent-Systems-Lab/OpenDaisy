# Copyright 2020 Adap GmbH. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
#
# Modifications copyright 2024 Intelligence Systems Lab. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Daisy master node app."""
from daisyfl.utils.logger import INFO, ERROR
from typing import Optional, Tuple, Dict, Callable, List

from daisyfl.utils.logger import log
from daisyfl.common import (
    NodeType,
    GRPC_MAX_MESSAGE_LENGTH,
)
from daisyfl.proto.transport_pb2_grpc import add_DaisyServiceServicer_to_server
from daisyfl.common.client_manager import ClientManager
from daisyfl.master.grpc_server.grpc_server import (
    generic_create_grpc_server,
    start_grpc_server,
)
from daisyfl.common.communicator import Communicator
from daisyfl.common.task_launcher import TaskLauncher
from daisyfl.common.task_manager import TaskManager
from daisyfl.master.server_api_handler import ServerListener

import threading
import time

DEFAULT_SERVER_ADDRESS = "[::]:8887"
_cnd_stop: threading.Condition = threading.Condition()
def shutdown():
    """Shutdown the Master node."""
    with _cnd_stop:
        _cnd_stop.notify()

def start_master(
    *,
    # server
    server_address: str = DEFAULT_SERVER_ADDRESS,
    # api_handler
    api_ip: str = None,
    api_port: int = None,
    # grpc
    grpc_max_message_length: int = GRPC_MAX_MESSAGE_LENGTH,
    downlink_certificates: Optional[Tuple[bytes, bytes, bytes]] = None,
) -> None:
    """Start a Master node."""
    # Initialize default modules
    client_manager: ClientManager = _init_defaults(
        server_address=server_address,
        api_ip=api_ip,
        api_port=api_port,
    )
    log(INFO, "Master server started.",)

    # Start gRPC server
    grpc_server = start_grpc_server(
        client_manager=client_manager,
        server_address=server_address,
        max_message_length=grpc_max_message_length,
        downlink_certificates=downlink_certificates,
        shutdown_fn=shutdown,
    )
    log(
        INFO,
        "Master gRPC server running , SSL is %s",
        "enabled" if downlink_certificates is not None else "disabled",
    )

    # Wait until shutdown
    with _cnd_stop:
        _cnd_stop.wait()
    # Stop the gRPC server
    grpc_server.stop(grace=1)
    client_manager.shutdown()
    log(INFO, "Master server shutdown")
    exit(0)


def _init_defaults(
    server_address: str,
    api_ip: str = None,
    api_port: int = None,
) -> ClientManager:
    """Initialize the default modules."""
    # client_manager
    client_manager = ClientManager()       
    # communicator
    communicator = Communicator(client_manager=client_manager, server_address=server_address,)
    client_manager.set_communicator(communicator)
    # task_launcher
    task_launcher = TaskLauncher(communicator=communicator, client_manager=client_manager)
    # task_manager
    task_manager = TaskManager(
        task_launcher=task_launcher,
        node_type=NodeType.MASTER,
    )
    # start ServerListener
    listener = _start_server_listener(api_ip=api_ip, api_port=api_port, task_manager=task_manager,)
    listener.set_get_metrics(task_launcher.get_metrics)
    
    return client_manager

# server_listener
def _start_server_listener(api_ip: str, api_port: int, task_manager: TaskManager,) -> ServerListener:
    """Start a ServerListener."""
    listener = ServerListener(api_ip, api_port, task_manager,)
    listener_thread = threading.Thread(target=listener.run, args=())
    listener_thread.setDaemon(True)
    listener_thread.start()
    time.sleep(1)
    if not listener_thread.is_alive():
        log(ERROR, "ServerListner failed")
        exit(1)
    return listener
