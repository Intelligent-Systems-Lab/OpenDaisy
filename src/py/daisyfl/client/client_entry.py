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
from queue import Queue
from daisyfl.utils.logger import INFO, DEBUG, ERROR, WARNING
from daisyfl.utils.logger import log
from daisyfl.utils import daisyfl_serde
from typing import Callable, Dict, Optional, Union, Tuple, List
from threading import Lock, Event
from daisyfl.proto.transport_pb2 import ClientMessage, ServerMessage
from .grpc_client.message_handler import handle
from .grpc_client.c2z_connection import C2ZConnection
from .client_operator_launcher import ClientOperatorLauncher
from daisyfl.utils.metadata import metadata_to_dict, dict_to_metadata
from enum import Enum
from daisyfl.common import (
    Status,
    ErrorCode,
    Parameters,
    ClientUploadingSignal,
    SERVER_WAITING,
    SERVER_IDLING,
    FitRes,
    CID,
    CLIENT_IDLING,
    CLIENT_HANDLING,
    ClientStatus,
)
import uuid
import threading

CONNECTION_RETRY_INTERVAL = 1

class ClientEntryStatus(Enum):
    RECEIVING = 1
    HANDLING_AND_SENDING = 2
    CLOSE = 3

class ClientEntry:
    """An entry to receive instructions and then send responses."""

    def __init__(
        self,
        client_operator_launcher: ClientOperatorLauncher,
        parent_address: str,
        grpc_max_message_length: int,
        uplink_certificates: Optional[bytes] = None,
        metadata: Optional[Tuple] = None,
    ) -> None:
        self._status: ClientEntryStatus = ClientEntryStatus.RECEIVING
        self._lock_status: Lock = Lock()
        self._event_stop: Event = Event()
        self._shutdown: bool = False
        self._server_message: Optional[ServerMessage] = None
        self._client_message: Optional[ClientMessage] = None
        self._client_operator_launcher = client_operator_launcher
        # === build connection section ===
        ## check metadata
        metadata = self._check_metadata(metadata)
        self._connector = C2ZConnection(
            parent_address=parent_address,
            max_message_length=grpc_max_message_length,
            uplink_certificates=uplink_certificates,
            metadata=metadata,
            client_entry=self,
        )
        connector_thread = threading.Thread(target=self._connector.run, args=())
        connector_thread.setDaemon(True)
        connector_thread.start()
        threading.Event().wait(timeout=1)
        if not connector_thread.is_alive():
            log(ERROR, "C2ZConnection failed")
            exit(1)
        # === build connection end ===
    
    def run(self,) -> None:
        """Run this ClientEntry."""
        while (not self._shutdown):
            self._receiving()
            self._handling()
            self._sending()
        
    def _receiving(self,) -> None:
        """Build a connection with Zone node and try receiving instructions."""
        while True:
            # check status
            if self.get_client_entry_status_code() != ClientEntryStatus.RECEIVING.value:
                log(INFO, "Skip receiving")
                return None
            # try building connection
            if not self._handle_connection(self.get_client_entry_status_code()):
                return None
            # wait for the next ServerMessage
            try:
                log(DEBUG, "ClientEntry tries receiving message")
                self._server_message, _ = self._connector.receive()
                self._connector.set_anchor(reset=False)
                with self._lock_status:
                    if self.get_client_entry_status_code() != ClientEntryStatus.CLOSE.value:
                        self._status = ClientEntryStatus.HANDLING_AND_SENDING
                    self._event_stop.clear()
                    self._connector.disconnect()
            except:
                log(DEBUG, "Reset Connection")
                self._connector.disconnect()
                self._connector.reconnect()
    
    def _handling(self,) -> None:
        """Handle the instructions from Zone node."""
        if self.get_client_entry_status_code() != ClientEntryStatus.HANDLING_AND_SENDING.value:
            log(INFO, "Skip handling")
            return None
        log(DEBUG, "ClientEntry tries handling ServerMessage")
        server_message: ServerMessage = self._server_message
        self._client_message = handle(server_message, self._client_operator_launcher)
        self._server_message = None

    def _sending(self,) -> None:
        """Build a connection with Zone node and try sending responses."""
        while True:
            # check status
            if self.get_client_entry_status_code() != ClientEntryStatus.HANDLING_AND_SENDING.value:
                log(INFO, "Skip sending")
                return None
            # try building connection
            if not self._handle_connection(self.get_client_entry_status_code()):
                return None
            # try sending a client message
            log(DEBUG, "ClientEntry tries sending message")
            try:
                # send client uploading signal
                cus = ClientUploadingSignal(status=Status(error_code=ErrorCode.OK, message=""))
                cus_msg = ClientMessage(client_uploading_signal=daisyfl_serde.client_uploading_signal_to_proto(cus))
                self._connector.send(cus_msg)
                log(DEBUG, "Send ClientUploadingSignal")
                # receive server status
                server_status_msg, success = self._connector.receive()
                if (not success) or (server_status_msg.WhichOneof("msg") != "server_status"):
                    return None
                server_status = daisyfl_serde.server_status_from_proto(server_status_msg.server_status)
                if server_status.status == SERVER_WAITING:
                    server_waiting = True
                elif server_status.status == SERVER_IDLING:
                    server_waiting = False
                else:
                    log(ERROR, "Receive an unkown type of ServerStatus")
                    return None
                log(DEBUG, "Receive ServerStatus")
                # if server waiting, send the result
                if server_waiting:
                    client_message: ClientMessage = self._client_message
                    self._connector.send(client_message)
                    log(DEBUG, "Result uploaded")
                # if server idling, send a null message
                else:
                    client_message: ClientMessage = ClientMessage(fit_res=daisyfl_serde.fit_res_to_proto(FitRes(
                        status=Status(error_code=ErrorCode.OK, message="Success"),
                        parameters=Parameters(tensors=[], tensor_type=""),
                        config={},
                    )))
                    self._connector.send(client_message)
                # receive server received signal
                self._connector.receive() # SRS
                log(DEBUG, "Receive ServerReceivedSignal")
                self._connector.set_anchor(reset=True)
                # status transition
                with self._lock_status:
                    if self.get_client_entry_status_code() != ClientEntryStatus.CLOSE.value:
                        self._client_message = None
                        self._status = ClientEntryStatus.RECEIVING
                    self._connector.disconnect()
                return None
            except:
                log(DEBUG, "Reset Connection")
                self._connector.disconnect()
                self._connector.reconnect()

    def _handle_connection(self, status_code: int) -> bool:
        """
        Try building a connection with Zone node.
        If the network is not connective, client node will try this again by again.
        """
        while True:
            if self.get_client_entry_status_code() != status_code:
                # transit status while trying connecting
                return False
            event_dis = self._connector.event_disconn.is_set()
            event_rec = self._connector.event_reconn.is_set()
            if (not event_dis) and (not event_rec):
                # Connection Ready
                return True
            elif (event_dis) and (not event_rec):
                log(INFO, "Send reconnection request")
                self._connector.reconnect()
                Event().wait(timeout=CONNECTION_RETRY_INTERVAL)
            elif (event_dis) and (event_rec):
                log(INFO, "Wait for reconnecting")
                Event().wait(timeout=CONNECTION_RETRY_INTERVAL)
            else:
                log(ERROR, "Wait for reconnecting before disconnecting. It shouldn't happen.")

    def _check_metadata(self, metadata: Optional[Tuple] = None) -> Tuple:
        if metadata is None:
            log(WARNING, "Metadata is not defined.")
            log(WARNING, "Use uuid as CID.")
            metadata_dict = {}
            metadata_dict[CID] = "client_" + str(uuid.uuid4())
            return dict_to_metadata(metadata_dict)
        # validate the metadata
        metadata_dict = metadata_to_dict(metadata=metadata)
        return dict_to_metadata(metadata_dict)

    # APIs
    def get_client_entry_status_code(self,) -> int:
        return self._status.value

    def get_client_status(self,):
        """Return the ClientStatus to synchronize with Zone node."""
        status_code = self.get_client_entry_status_code()
        if status_code == ClientEntryStatus.RECEIVING.value:
            return daisyfl_serde.client_status_to_proto(ClientStatus(status=CLIENT_IDLING))
        elif status_code == ClientEntryStatus.HANDLING_AND_SENDING.value:
            return daisyfl_serde.client_status_to_proto(ClientStatus(status=CLIENT_HANDLING))
        else:
            log(ERROR, "ClientEntry should be closed.")
            return None

    def get_handover_fn(self,) -> Callable:
        """Bridge the handover function that will be used by ClientOperator."""
        return self._connector.handover

    def get_anchor_fn(self,) -> Callable:
        return self._connector.get_anchor
    
    def shutdown(self,) -> None:
        """Close the connection and shutdown."""
        self._shutdown = True
        with self._lock_status:
            self._status = ClientEntryStatus.CLOSE
            # break from the current function
            self._connector.disconnect()
            self._event_stop.set()
        return
