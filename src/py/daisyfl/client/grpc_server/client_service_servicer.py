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
"""Servicer for DaisyService.

Relevant knowledge for reading this modules code:
    - https://github.com/grpc/grpc/blob/master/doc/statuscodes.md
"""
from typing import Callable, Iterator, Optional, Tuple

import grpc
from iterators import TimeoutIterator

from daisyfl.proto import transport_pb2_grpc
from daisyfl.proto.transport_pb2 import ClientMessage, ServerMessage
from daisyfl.utils.logger import DEBUG, ERROR, log


class ClientServiceServicer(transport_pb2_grpc.DaisyServiceServicer):
    """ClientServiceServicer for bi-directional gRPC message stream."""

    def __init__(
        self,
        server_address: str,
    ) -> None:
        """Initialize ClientServiceServicer with the client's server address."""
        self.server_address: str = server_address
        self.shutdown_fn: Optional[Callable] = None

    def set_shutdown_fn(self, shutdown_fn: Callable):
        """Set a callback function to shutdown the Client."""
        self.shutdown_fn = shutdown_fn

    def Join(
        self,
        request_iterator: Iterator[ClientMessage],
        context: grpc.ServicerContext,
    ) -> Iterator[ServerMessage]:
        """Method will be invoked by users."""
        # process Iterator
        client_timeout_iterator = TimeoutIterator(iterator=request_iterator, reset_on_next=True)
        client_message, success = self.get_client_message(
            client_message_iterator=client_timeout_iterator,
            context=context,
        )
        if not success:
            return
        field = client_message.WhichOneof("msg")
        if field == "shutdown":
            self.shutdown()
            return

        log(ERROR, "Receive unexpected message type.")

    def shutdown(
        self,
    ):
        """Shutdown the Client."""
        if self.shutdown_fn is not None:
            self.shutdown_fn()

    # communication
    @staticmethod
    def get_client_message(
        client_message_iterator: TimeoutIterator,
        context: grpc.ServicerContext,
        timeout: Optional[int] = None,
    ) -> Tuple[ClientMessage, bool]:
        """Receive a ClientMessage from users."""
        log(DEBUG, "Try receiving ClientMessage")
        if timeout is not None:
            client_message_iterator.set_timeout(float(timeout))
        # Wait for client message
        client_message = next(client_message_iterator)
        if client_message is client_message_iterator.get_sentinel():
            # Important: calling `context.abort` in gRPC always
            # raises an exception so that all code after the call to
            # `context.abort` will not run. If subsequent code should
            # be executed, the `rpc_termination_callback` can be used
            # (as shown in the `register_client` function).
            details = f"Timeout of {timeout}sec was exceeded."
            context.abort(
                code=grpc.StatusCode.DEADLINE_EXCEEDED,
                details=details,
            )
            # This return statement is only for the linter so it understands
            # that client_message in subsequent lines is not None
            # It does not understand that `context.abort` will terminate
            # this execution context by raising an exception.
            return client_message, False
        return client_message, True
