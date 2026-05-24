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
"""Implements utility function to create a gRPC server."""


import concurrent.futures
import sys
from daisyfl.utils.logger import ERROR
from typing import Any, Callable, Optional, Tuple, Union

import grpc

from daisyfl.common import GRPC_MAX_MESSAGE_LENGTH
from daisyfl.utils.logger import log
from daisyfl.proto.transport_pb2_grpc import add_DaisyServiceServicer_to_server
from daisyfl.common.client_manager import ClientManager
from daisyfl.zone.grpc_server.zone_service_servicer import ZoneServiceServicer

INVALID_CERTIFICATES_ERR_MSG = """
    When setting downlink_certificates.
"""

AddServicerToServerFn = Callable[..., Any]


def valid_certificates(downlink_certificates: Tuple[bytes, bytes, bytes]) -> bool:
    """Validate certificates tuple."""
    is_valid = (
        all(isinstance(certificate, bytes) for certificate in downlink_certificates)
        and len(downlink_certificates) == 3
    )

    if not is_valid:
        log(ERROR, INVALID_CERTIFICATES_ERR_MSG)

    return is_valid


def start_grpc_server(
    client_manager: ClientManager,
    server_address: str,
    max_concurrent_workers: int = 1000,
    max_message_length: int = GRPC_MAX_MESSAGE_LENGTH,
    keepalive_time_ms: int = 210000,
    downlink_certificates: Optional[Tuple[bytes, bytes, bytes]] = None,
    shutdown_fn: Callable = None,
) -> grpc.Server:
    """Create and start a gRPC server running DaisyServiceServicer."""

    servicer = ZoneServiceServicer(client_manager, server_address)
    if shutdown_fn is not None:
        servicer.set_shutdown_fn(shutdown_fn)
    add_servicer_to_server_fn = add_DaisyServiceServicer_to_server

    server = generic_create_grpc_server(
        servicer_and_add_fn=(servicer, add_servicer_to_server_fn),
        server_address=server_address,
        max_concurrent_workers=max_concurrent_workers,
        max_message_length=max_message_length,
        keepalive_time_ms=keepalive_time_ms,
        downlink_certificates=downlink_certificates,
    )

    server.start()

    return server


def generic_create_grpc_server(
    servicer_and_add_fn: Tuple[ZoneServiceServicer, AddServicerToServerFn],
    server_address: str,
    max_concurrent_workers: int = 1000,
    max_message_length: int = GRPC_MAX_MESSAGE_LENGTH,
    keepalive_time_ms: int = 210000,
    downlink_certificates: Optional[Tuple[bytes, bytes, bytes]] = None,
) -> grpc.Server:
    """Generic function to create a gRPC server with a single servicer."""

    # Deconstruct tuple into servicer and function
    servicer, add_servicer_to_server_fn = servicer_and_add_fn

    # Possible options:
    # https://github.com/grpc/grpc/blob/v1.43.x/include/grpc/impl/codegen/grpc_types.h
    options = [
        ("grpc.max_concurrent_streams", max(100, max_concurrent_workers)),
        ("grpc.max_send_message_length", max_message_length),
        ("grpc.max_receive_message_length", max_message_length),
        ("grpc.keepalive_time_ms", keepalive_time_ms),
        ("grpc.http2.max_pings_without_data", 0),
    ]

    server = grpc.server(
        concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent_workers),
        # Set the maximum number of concurrent RPCs this server will service before
        # returning RESOURCE_EXHAUSTED status, or None to indicate no limit.
        maximum_concurrent_rpcs=max_concurrent_workers,
        options=options,
    )
    add_servicer_to_server_fn(servicer, server)

    if downlink_certificates is not None:
        if not valid_certificates(downlink_certificates):
            sys.exit(1)

        root_certificate_b, certificate_b, private_key_b = downlink_certificates

        server_credentials = grpc.ssl_server_credentials(
            ((private_key_b, certificate_b),),
            root_certificates=root_certificate_b,
            # A boolean indicating whether or not to require clients to be
            # authenticated. May only be True if downlink_certificates is not None.
            # We are explicitly setting the current gRPC default to document
            # the option. For further reference see:
            # https://grpc.github.io/grpc/python/grpc.html#create-server-credentials
            require_client_auth=False,
        )
        server.add_secure_port(server_address, server_credentials)
    else:
        server.add_insecure_port(server_address)

    return server
