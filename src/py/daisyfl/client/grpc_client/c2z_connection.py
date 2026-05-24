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
"""Contextmanager managing a gRPC channel to the Daisy server."""


from contextlib import contextmanager
from daisyfl.utils.logger import DEBUG, INFO, WARNING, ERROR
from queue import Queue
from typing import Callable, Iterator, Optional, Tuple, Any, Dict, List
from daisyfl.utils.connection import grpc_connection

import grpc
from threading import Condition, Event

from daisyfl.common import (
    HANDOVER,
    UPLINK_CERTIFICATES,
    ANCHOR,
    GRPC_MAX_MESSAGE_LENGTH,
    CLIENT_IDLING,
    CLIENT_HANDLING,
    ClientStatus,
)
from daisyfl.utils import daisyfl_serde
from daisyfl.utils.logger import log
from daisyfl.utils.metadata import metadata_to_dict, dict_to_metadata
from daisyfl.proto.transport_pb2 import ClientMessage, ServerMessage
from daisyfl.proto.transport_pb2_grpc import DaisyServiceStub
from iterators import TimeoutIterator

# The following flags can be uncommented for debugging. Other possible values:
# https://github.com/grpc/grpc/blob/master/doc/environment_variables.md
# import os
# os.environ["GRPC_VERBOSITY"] = "debug"
# os.environ["GRPC_TRACE"] = "tcp,http"


SLEEP_DURATION = 2


def _process_metadata(
    metadata: Tuple,
    anchor: Optional[str],
    uplink_certificates: Optional[bytes],
    handover: bool,
) -> Tuple:
    metadata_dict = metadata_to_dict(metadata=metadata, check_reserved=False, check_required=True)
    
    if anchor is not None:
        metadata_dict[ANCHOR] = anchor
    elif metadata_dict.__contains__(ANCHOR):
        del metadata_dict[ANCHOR]
    
    if uplink_certificates is not None:
        metadata_dict[UPLINK_CERTIFICATES] = uplink_certificates
    elif metadata_dict.__contains__(UPLINK_CERTIFICATES):
        del metadata_dict[UPLINK_CERTIFICATES]
    
    if handover:
        metadata_dict[HANDOVER] = "handover"
    elif metadata_dict.__contains__(HANDOVER):
        del metadata_dict[HANDOVER]
    
    return dict_to_metadata(metadata_dict)


class C2ZConnection:
    """Connection between Zone node and Client node."""

    def __init__(self,
        # for grpc_connection
        parent_address: str = None,
        max_message_length: int = GRPC_MAX_MESSAGE_LENGTH,
        uplink_certificates: Optional[bytes] = None,
        metadata: Tuple = (),
        # sync up
        client_entry = None,
    ):
        # transmission
        self.send: Callable = None
        self.receive: Callable = None
        # for grpc_connection
        self._parent_address: str = parent_address
        self._max_message_length: int = max_message_length
        self._uplink_certificates: Optional[bytes] = uplink_certificates
        self._metadata: Tuple = metadata
        self._anchor: str = None
        # conditions
        self.event_disconn: Event = Event()
        self.event_disconn.set()
        self.event_reconn: Event = Event()
        self._cnd_api: Condition = Condition()
        self._busy: bool = False
        # sync up
        self._client_entry = client_entry
        
    def run(self,):
        """Enable connection between Zone node and Client node."""
        while True:
            # Wait for ClientEntry ready and for reconnection
            log(DEBUG, "Connector idling")
            self.event_reconn.wait()
            log(DEBUG, "Connector reconnecting")
            try:
                self._metadata = _process_metadata(metadata=self._metadata, anchor=self._anchor, uplink_certificates=self._uplink_certificates, handover=self._check_handover())
                with grpc_connection(self._parent_address, self._metadata, self._uplink_certificates) as conn:
                    self.send, self.receive = conn
                    # send ClientStatus
                    self.send(ClientMessage(client_status=self._client_entry.get_client_status()))
                    # ClientEntry can use
                    self.event_reconn.clear()
                    self.event_disconn.clear()
                    log(DEBUG, "ClientEntry's term")
                    # Wait for ConnectionFail
                    self.event_disconn.wait()
                    log(INFO, "Sleep for " + str(SLEEP_DURATION) + " seconds")
                    Event().wait(timeout=SLEEP_DURATION)
                    log(DEBUG, "Connector's term")
            except:
                log(INFO, "Sleep for " + str(SLEEP_DURATION) + " seconds")
                Event().wait(timeout=SLEEP_DURATION)

    def _check_handover(self, ) -> bool:
        """Check if the current connected Zone node is the anchor."""
        if (self._anchor is not None) and (self._parent_address is not None):
            if self._anchor != self._parent_address:
                return True
        return False

    # external APIs
    def reconnect(self,) -> bool:
        with self._cnd_api:
            while self._busy:
                self._cnd_api.wait()
            self._busy = True
        ###
        result = False
        if not self.event_disconn.is_set():
            log(
                WARNING,
                "Try reconnecting before disconnecting. " + \
                "Do nothing."
            )
        elif self.event_reconn.is_set():
            log(
                WARNING,
                "Another reconnection request has not been handled or the connection has not been built. " + \
                "Do nothing."
            )
        else:
            self.event_reconn.set()
            result = True
        ###
        self._busy = False
        with self._cnd_api:
            self._cnd_api.notify_all()
        return result

    def disconnect(self,) -> bool:
        with self._cnd_api:
            while self._busy:
                self._cnd_api.wait()
            self._busy = True
        ###
        result = False
        if self.event_disconn.is_set():
            log(
                WARNING,
                "Another disconnection request has not been handled or the connection has not been built. " + \
                "Do nothing."
            )
        else:
            self.event_disconn.set()
            result = True
        ###
        self._busy = False
        with self._cnd_api:
            self._cnd_api.notify_all()
        return result

    def get_anchor(self,) -> Optional[str]:
        """Get the current anchor."""
        return self._anchor

    def set_anchor(self, reset: bool = True) -> None:
        """Label the current connected Zone node as the anchor."""
        if reset:
            self._anchor = None
        else:    
            self._anchor = self._parent_address

    def handover(self, new_parent_address: str) -> None:
        """Switch the connection to another Zone node."""
        with self._cnd_api:
            while self._busy:
                self._cnd_api.wait()
            self._busy = True
        ###
        if new_parent_address is not None:
            self._parent_address = new_parent_address
        ###
        self._busy = False
        with self._cnd_api:
            self._cnd_api.notify_all()

    def get_metadata(self,) -> Tuple:
        return self._metadata
