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
"""Daisy client app."""


from queue import Queue
from daisyfl.utils.logger import INFO, ERROR, WARNING
from typing import Callable, Dict, Optional, Union, Tuple, List
from daisyfl.common import (
    GRPC_MAX_MESSAGE_LENGTH,
)
from daisyfl.utils.logger import log

from .trainer import Trainer
from .client_entry import ClientEntry
from .grpc_server.grpc_server import start_grpc_server
from daisyfl.client.client_operator_launcher import ClientOperatorLauncher
from .numpy_trainer import NumPyTrainer, NumPyTrainerWrapper


def start_client(
    *,
    server_address: str,
    parent_address: str,
    trainer: Trainer,
    grpc_max_message_length: int = GRPC_MAX_MESSAGE_LENGTH,
    uplink_certificates: Optional[bytes] = None,
    # downlink_certificates: Optional[Tuple[bytes, bytes, bytes]] = None,
    metadata: Optional[Tuple] = None,
) -> None:
    # client_operator_launcher
    client_operator_launcher = ClientOperatorLauncher(trainer=trainer, server_address=server_address,)

    # client_entry:
    client_entry = ClientEntry(client_operator_launcher, parent_address, grpc_max_message_length, uplink_certificates, metadata)
    client_operator_launcher.set_handover_fn(client_entry.get_handover_fn())
    client_operator_launcher.set_get_anchor_fn(client_entry.get_anchor_fn())

    # gRPCServer: for shutdown, and TODO: C2C communication
    grpc_server = start_grpc_server(
        server_address=server_address,
        shutdown_fn=client_entry.shutdown,
    )
    log(INFO, "gRPCServer is running.")

    # NOTE: repeat message iteration until client shutdown
    client_entry.run()
    grpc_server.stop(grace=1)
    exit(0)


def start_client_numpy(
    *,
    server_address: str,
    parent_address: str,
    numpy_trainer: NumPyTrainer,
    grpc_max_message_length: int = GRPC_MAX_MESSAGE_LENGTH,
    uplink_certificates: Optional[bytes] = None,
    # downlink_certificates: Optional[Tuple[bytes, bytes, bytes]] = None,
    metadata: Tuple = None,
) -> None:
    # Start
    start_client(
        server_address=server_address,
        parent_address=parent_address,
        trainer=NumPyTrainerWrapper(numpy_trainer=numpy_trainer),
        grpc_max_message_length=grpc_max_message_length,
        uplink_certificates=uplink_certificates,
        # downlink_certificates=downlink_certificates,
        metadata=metadata,
    )

