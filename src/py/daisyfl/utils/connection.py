# Copyright 2024 Intelligence Systems Lab. All Rights Reserved.
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

from contextlib import contextmanager
from typing import Callable, Iterator, Any, Dict, Tuple, Optional
import grpc
from iterators import TimeoutIterator
from daisyfl.proto.transport_pb2 import ClientMessage, ServerMessage
from .logger import log
from . import daisyfl_serde
from daisyfl.utils.logger import INFO, WARNING, DEBUG, ERROR
from daisyfl.common import (
    GRPC_MAX_MESSAGE_LENGTH, 
    ErrorCode,
    Status,
    FitRes,
    Parameters,
)
from daisyfl.proto.transport_pb2_grpc import DaisyServiceStub
from queue import Queue
    
@contextmanager
def grpc_connection(
    parent_address: str,
    metadata: Tuple,
    uplink_certificates: Optional[bytes] = None,
) -> Iterator[Tuple[Callable[[], ServerMessage], Callable[[ClientMessage], None]]]:
    """Build a gRPC connection with a parent node."""
    # Possible options:
    # https://github.com/grpc/grpc/blob/v1.43.x/include/grpc/impl/codegen/grpc_types.h
    channel_options = [
        ("grpc.max_send_message_length", GRPC_MAX_MESSAGE_LENGTH),
        ("grpc.max_receive_message_length", GRPC_MAX_MESSAGE_LENGTH),
    ]

    if uplink_certificates is not None:
        ssl_channel_credentials = grpc.ssl_channel_credentials(uplink_certificates)
        channel = grpc.secure_channel(
            parent_address, ssl_channel_credentials, options=channel_options
        )
        log(INFO, "Opened secure gRPC connection using certificates")
    else:
        channel = grpc.insecure_channel(parent_address, options=channel_options)
        log(INFO, "Opened insecure gRPC connection (no certificates were passed)")

    channel.subscribe(lambda channel_connectivity: log(DEBUG, channel_connectivity))
    
    stub = DaisyServiceStub(channel)
    queue: Queue[ClientMessage] = Queue(maxsize=1)
    time_iterator = TimeoutIterator(iterator=iter(queue.get, None), reset_on_next=True)

    server_message_iterator: Iterator[ServerMessage] = stub.Join(time_iterator, metadata=metadata)
    timeout_iterator = TimeoutIterator(iterator=server_message_iterator, reset_on_next=True)

    def receive_fn(timeout: Optional[int] = None) -> Tuple[ServerMessage, bool]:
        if timeout is not None:
            timeout_iterator.set_timeout(float(timeout))
        server_message = next(timeout_iterator)
        if server_message is timeout_iterator.get_sentinel():
            return server_message, False
        return server_message, True
    receive: Callable[[Optional[int]], Tuple[ServerMessage, bool]] = receive_fn
    send: Callable[[ClientMessage], None] = lambda msg: queue.put(msg, block=False)

    try:
        yield send, receive
    finally:
        # Release Iterator to avoid leaking memory
        time_iterator.interrupt()
        # Send an arbitrary ClientMessage to interrupt the iterator
        send(
            ClientMessage(fit_res=daisyfl_serde.fit_res_to_proto(FitRes(
            status=Status(error_code=ErrorCode.OK, message="Success"),
            parameters=Parameters(tensors=[], tensor_type=""),
            config={},
        ))))
        # Make sure to have a final
        channel.close()
        log(DEBUG, "gRPC channel closed")