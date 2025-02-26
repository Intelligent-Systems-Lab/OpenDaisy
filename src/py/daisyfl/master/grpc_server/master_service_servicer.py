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
"""Servicer for DaisyService of Master node.

Relevant knowledge for reading this modules code:
    - https://github.com/grpc/grpc/blob/master/doc/statuscodes.md
"""
from contextlib import contextmanager
from typing import Callable, Iterator, Any, Dict, Tuple, Optional
import timeit
import grpc
from iterators import TimeoutIterator

from daisyfl.proto import transport_pb2_grpc
from daisyfl.proto.transport_pb2 import ClientMessage, ServerMessage
from daisyfl.common.client_manager import ClientManager
from daisyfl.common.grpc_bridge import GRPCBridge
from daisyfl.utils.connection import grpc_connection
from daisyfl.common.grpc_client_proxy import GrpcClientProxy
from daisyfl.utils.logger import log
from daisyfl.utils import daisyfl_serde
from daisyfl.utils.metadata import metadata_to_dict, dict_to_metadata
from daisyfl.utils.logger import INFO, WARNING, DEBUG, ERROR
from daisyfl.common import (
    ClientStatus,
    ServerStatus,
    CLIENT_HANDLING,
    CLIENT_IDLING,
    SERVER_IDLING,
    SERVER_WAITING,
    CID,
    ErrorCode,
    ServerReceivedSignal,
    Status,
    FitRes,
    Parameters,
)
from daisyfl.proto.transport_pb2_grpc import DaisyServiceStub
from threading import Condition, Event


WAIT_FOR_SERVER_STATE_TRANSITION = 5


def default_bridge_factory(client_idling: bool) -> GRPCBridge:
    """Return GRPCBridge instance."""
    return GRPCBridge(client_idling)


def default_grpc_client_factory(bridge: GRPCBridge, metadata_dict: Dict) -> GrpcClientProxy:
    """Return GrpcClientProxy instance."""
    return GrpcClientProxy(cid=metadata_dict[CID], bridge=bridge, metadata_dict=metadata_dict)


def register_client(
    client_manager: ClientManager,
    client: GrpcClientProxy,
    context: grpc.ServicerContext,
) -> bool:
    """Try registering GrpcClientProxy with ClientManager."""
    is_success = client_manager.register_client(client)

    if is_success:

        def rpc_termination_callback() -> None:
            client_manager.unregister_client(client)
            client.bridge.close()

        context.add_callback(rpc_termination_callback)

    return is_success

class MasterServiceServicer(transport_pb2_grpc.DaisyServiceServicer):
    """MasterServiceServicer for bi-directional gRPC message stream."""

    def __init__(
        self,
        client_manager: ClientManager,
        server_address: str,
        grpc_bridge_factory: Callable[[bool], GRPCBridge] = default_bridge_factory,
        grpc_client_factory: Callable[
            [GRPCBridge, Dict], GrpcClientProxy
        ] = default_grpc_client_factory,
    ) -> None:
        self.client_manager: ClientManager = client_manager
        self.server_address: str = server_address
        self.grpc_bridge_factory = grpc_bridge_factory
        self.client_factory = grpc_client_factory

    def Join(
        self,
        request_iterator: Iterator[ClientMessage],
        context: grpc.ServicerContext,
    ) -> Iterator[ServerMessage]:
        """Method will be invoked by each zone_entry which participates in the network."""
        # process Iterator
        client_timeout_iterator = TimeoutIterator(iterator=request_iterator, reset_on_next=True)
        client_message, success = self.get_client_message(client_message_iterator=client_timeout_iterator, context=context, timeout=None)
        if not success:
            return
        field = client_message.WhichOneof("msg")
        # FL message streaming
        if field == "client_status":
            client_status: ClientStatus = daisyfl_serde.client_status_from_proto(client_message.client_status)
            yield from self.handle_local_connection(client_timeout_iterator=client_timeout_iterator, context=context, client_status=client_status)
        # shutdown request
        elif field == "shutdown":
            self.shutdown()
            return
        else:
            log(ERROR, "Receive unexpected message type.")
            return
    
    def handle_local_connection(
        self,
        client_timeout_iterator: Iterator[ClientMessage],
        context: grpc.ServicerContext,
        client_status: ClientStatus,
    ) -> Iterator[ServerMessage]:
        """Method to handle a local connection from a ZoneEntry."""
        # receive client status
        if client_status.status == CLIENT_IDLING:
            client_idling = True
        elif client_status.status == CLIENT_HANDLING:
            client_idling = False
        else:
            log(ERROR, "Receive undefined ClientStatus")
            return

        # register client_proxy
        metadata_dict = metadata_to_dict(metadata=context.invocation_metadata(), check_reserved=False, check_required=True)
        bridge = self.grpc_bridge_factory(client_idling)
        client_proxy = self.client_factory(bridge, metadata_dict)
        if not register_client(self.client_manager, client_proxy, context):
            return

        # streaming
        if client_idling:
            try:
                yield from self.get_server_message(client_proxy)
                log(DEBUG, "Send ServerMessage")
                client_idling = False
            except StopIteration:
                return
        else:
            try:
                # receive client uploading signal
                client_message, success = self.get_client_message(client_message_iterator=client_timeout_iterator, context=context, timeout=None)
                if (not success) or (client_message.WhichOneof("msg") != "client_uploading_signal"):
                    return
                log(DEBUG, "Receive ClientUploadingSignal")
                # send server status
                server_waiting = client_proxy.is_pending()
                if not server_waiting:
                    server_status = daisyfl_serde.server_status_to_proto(ServerStatus(status=SERVER_IDLING))
                else:
                    server_status = daisyfl_serde.server_status_to_proto(ServerStatus(status=SERVER_WAITING))
                server_status_msg = ServerMessage(server_status=server_status)
                yield server_status_msg
                log(DEBUG, "Send ServerStatus")
                # get the result
                client_message, success = self.get_client_message(client_message_iterator=client_timeout_iterator, context=context, timeout=None)
                if success:
                    # set client_message to grpc_bridge if server is waiting
                    if server_waiting:
                        client_proxy.bridge.set_client_message(client_message=client_message, roaming=False)
                        log(DEBUG, "Set ClientMessage to grpc_bridge")
                    # ignore the client_message if server is not waiting
                    # send server received signal
                    srs = ServerReceivedSignal(status=Status(error_code=ErrorCode.OK, message=""))
                    server_message = ServerMessage(server_received_signal=daisyfl_serde.server_received_signal_to_proto(srs))
                    yield server_message
                    log(DEBUG, "Send ServerReceivedSignal")
                    # wait
                    Event().wait(timeout=WAIT_FOR_SERVER_STATE_TRANSITION)
            except StopIteration:
                return

    # communication
    def get_server_message(self, client_proxy: GrpcClientProxy,) -> Iterator[ServerMessage]:
        """Get the next ServerMessage from gRPC bridge."""
        log(DEBUG, "Try sending ServerMessage")
        _server_message_iterator = client_proxy.bridge.server_message_iterator()
        # Get server_message from bridge
        server_message: ServerMessage = next(_server_message_iterator)
        yield server_message

    def get_client_message(self, client_message_iterator: TimeoutIterator,  context: grpc.ServicerContext, timeout: Optional[int] = None,) -> Tuple[ClientMessage, bool]:
        """Receive a ClientMessage from a ZoneEntry."""
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

    # shutdown
    def set_shutdown_fn(self, shutdown_fn: Callable):
        """Set a callback function to shutdown the Master service."""
        self.shutdown_fn: Callable = shutdown_fn

    def shutdown(self,):
        """Shutdown the Master service."""
        self.shutdown_fn()
        return
