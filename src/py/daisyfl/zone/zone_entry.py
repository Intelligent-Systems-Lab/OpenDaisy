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
from daisyfl.utils.logger import INFO, DEBUG, ERROR
from daisyfl.utils.logger import log
from daisyfl.utils import daisyfl_serde
from typing import Callable, Dict, Optional, Union, Tuple, List
from threading import Lock, Event
from daisyfl.proto.transport_pb2 import ClientMessage, ServerMessage
from .grpc_client.message_handler import handle
from enum import Enum
from daisyfl.common.task_manager import TaskManager
from daisyfl.common import (
    Status,
    ErrorCode,
    Parameters,
    ClientUploadingSignal,
    SERVER_WAITING,
    SERVER_IDLING,
    FitRes,
    GRPC_MAX_MESSAGE_LENGTH,
    CLIENT_IDLING,
    CLIENT_HANDLING,
    ClientStatus,
)
from daisyfl.zone.grpc_client.z2m_connection import Z2MConnection
import threading

CONNECTION_RETRY_INTERVAL = 1

class ZoneEntryStatus(Enum):
    RECEIVING = 1
    HANDLING_AND_SENDING = 2
    CLOSE = 3

class ZoneEntry:
    """An entry to receive instructions and then send responses."""
    
    def __init__(
        self,
        task_manager: TaskManager,
        parent_address: str = None,
        max_message_length: int = GRPC_MAX_MESSAGE_LENGTH,
        uplink_certificates: Optional[bytes] = None,
        metadata: Tuple = (),
    ) -> None:
        self._status: ZoneEntryStatus = ZoneEntryStatus.RECEIVING
        self._lock_status: Lock = Lock()
        self._event_stop: Event = Event()
        self._shutdown: bool = False
        self._server_message: Optional[ServerMessage] = None
        self._client_message: Optional[ClientMessage] = None
        self._task_manager: TaskManager = task_manager
        # === build connection section ===
        self._connector = Z2MConnection(
            parent_address=parent_address,
            max_message_length=max_message_length,
            uplink_certificates=uplink_certificates,
            metadata=metadata,
            zone_entry=self,
        )
        # start connector
        connector_thread = threading.Thread(target=self._connector.run, args=())
        connector_thread.setDaemon(True)
        connector_thread.start()
        # check liveness
        threading.Event().wait(timeout=1)
        if not connector_thread.is_alive():
            log(ERROR, "Z2MConnection failed")
            exit(1)
        # === build connection end ===
    
    def run(self,) -> None:
        """Run this ZoneEntry."""
        while not self._shutdown:
            self._receiving()
            self._handling()
            self._sending()
        
    def _receiving(self,) -> None:
        """Build a connection with Master node and try receiving instructions."""
        while True:
            # check status
            if self.get_zone_entry_status_code() != ZoneEntryStatus.RECEIVING.value:
                log(INFO, "Skip receiving")
                return None
            # try building connection
            if not self._handle_connection(self.get_zone_entry_status_code()):
                return None
            # wait for the next ServerMessage
            try:
                log(DEBUG, "ZoneEntry tries receiving message")
                self._server_message, _ = self._connector.receive()
                with self._lock_status:
                    # status transition
                    if self.get_zone_entry_status_code() != ZoneEntryStatus.CLOSE.value:
                        self._status = ZoneEntryStatus.HANDLING_AND_SENDING
                    self._event_stop.clear()
                    self._connector.disconnect()
            except:
                log(DEBUG, "Reset Connection")
                self._connector.disconnect()
                self._connector.reconnect()
    
    def _handling(self,) -> None:
        """Handle the instructions from Master node."""
        # check status
        if self.get_zone_entry_status_code() != ZoneEntryStatus.HANDLING_AND_SENDING.value:
            log(INFO, "Skip handling")
            return None
        log(DEBUG, "ZoneEntry tries handling ServerMessage")
        server_message: ServerMessage = self._server_message
        self._client_message = handle(server_message, self._task_manager)
        self._server_message = None

    def _sending(self,) -> None:
        """Build a connection with Master node and try sending responses."""
        while True:
            # check status
            if self.get_zone_entry_status_code() != ZoneEntryStatus.HANDLING_AND_SENDING.value:
                log(INFO, "Skip sending")
                return None
            # try building connection
            if not self._handle_connection(self.get_zone_entry_status_code()):
                return None
            # try sending a client message
            log(DEBUG, "ZoneEntry tries sending message")
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
                # status transition
                with self._lock_status:
                    if self.get_zone_entry_status_code() != ZoneEntryStatus.CLOSE.value:
                        self._client_message = None
                        self._status = ZoneEntryStatus.RECEIVING
                    """for loose association"""
                    self._connector.disconnect()
                return None
            except:
                log(DEBUG, "Reset Connection")
                self._connector.disconnect()
                self._connector.reconnect()

    def _handle_connection(self, status_code: int) -> bool:
        """
        Try building a connection with Master node.
        If the network is not connective, zone node will try this again by again.
        """
        while True:
            if self.get_zone_entry_status_code() != status_code:
                # transit status while trying connecting
                return False
            event_dis = self._connector.event_disconn.is_set()
            event_rec = self._connector.event_reconn.is_set()
            if (not event_dis) and (not event_rec):
                # connection ready
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

    # APIs
    def get_zone_entry_status_code(self,) -> int:
        return self._status.value

    def get_client_status(self,):
        """Return the ClientStatus to synchronize with Master node."""
        status_code = self.get_zone_entry_status_code()
        if status_code == ZoneEntryStatus.RECEIVING.value:
            return daisyfl_serde.client_status_to_proto(ClientStatus(status=CLIENT_IDLING))
        elif status_code == ZoneEntryStatus.HANDLING_AND_SENDING.value:
            return daisyfl_serde.client_status_to_proto(ClientStatus(status=CLIENT_HANDLING))
        else:
            log(ERROR, "ZoneEntry should be closed.")
            return None

    def shutdown(self,) -> None:
        """Close the connection and shutdown."""
        self._shutdown = True
        with self._lock_status:
            self._status = ZoneEntryStatus.CLOSE
            # break from the current function
            self._connector.disconnect()
            self._event_stop.set()
        return
