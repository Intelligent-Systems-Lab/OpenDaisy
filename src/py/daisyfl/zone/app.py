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
"""Daisy zone node app."""
from daisyfl.utils.logger import INFO, WARNING, ERROR
from typing import Optional, Tuple, Dict, Callable, List

from daisyfl.utils.logger import log
from daisyfl.utils.metadata import metadata_to_dict, dict_to_metadata
from daisyfl.common import (
    NodeType,
    GRPC_MAX_MESSAGE_LENGTH,
    CID,
)

from daisyfl.common.client_manager import ClientManager
from daisyfl.zone.grpc_server.grpc_server import (
    generic_create_grpc_server,
    start_grpc_server,
)
from daisyfl.common.communicator import Communicator
from daisyfl.common.task_launcher import TaskLauncher
from daisyfl.common.task_manager import TaskManager
from daisyfl.zone.zone_entry import ZoneEntry
import uuid

DEFAULT_SERVER_ADDRESS = "[::]:8888"


def start_zone(
    *,
    parent_address: str = "",
    server_address: str = DEFAULT_SERVER_ADDRESS,
    grpc_max_message_length: int = GRPC_MAX_MESSAGE_LENGTH,
    uplink_certificates: Optional[bytes] = None,
    downlink_certificates: Optional[Tuple[bytes, bytes, bytes]] = None,
) -> None:
    """Start a Zone node."""
    # Initialize default modules
    client_manager, task_manager = _init_defaults(
        server_address=server_address,
    )
    log(INFO, "Zone server started.",)

    # metadata
    metadata = _init_metadata()

    # entry for messages sent from master
    zone_entry = ZoneEntry(
        task_manager=task_manager,
        parent_address=parent_address,
        max_message_length=grpc_max_message_length,
        uplink_certificates=uplink_certificates,
        metadata=metadata,
    )

    # Start gRPC server
    grpc_server = start_grpc_server(
        client_manager=client_manager,
        server_address=server_address,
        max_message_length=grpc_max_message_length,
        downlink_certificates=downlink_certificates,
        shutdown_fn=zone_entry.shutdown,
    )
    log(
        INFO,
        "Zone gRPC server running , SSL is %s",
        "enabled" if downlink_certificates is not None else "disabled",
    )

    # NOTE: repeat message iteration until zone shutdown
    zone_entry.run()

    # Stop the gRPC server
    grpc_server.stop(grace=1)
    client_manager.shutdown()
    log(INFO, "Zone server shutdown")
    exit(0)


def _init_defaults(
    server_address: str,
) -> Tuple[ClientManager, TaskManager]:
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
        node_type=NodeType.ZONE,
    )  
    
    return client_manager, task_manager

def _init_metadata()->Tuple:
    """Initialize a metadata to build connection with Master node."""
    metadata_dict = metadata_to_dict(metadata=((),), check_required=False, check_reserved=True)
    metadata_dict[CID] = "zone_" + str(uuid.uuid4())
    return dict_to_metadata(metadata_dict)
