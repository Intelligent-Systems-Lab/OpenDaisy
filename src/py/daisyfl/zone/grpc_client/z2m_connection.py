# Copyright 2020 Adap GmbH. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in trainerliance with the License.
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
"""Contextmanager managing a gRPC channel to the Daisy server."""


from contextlib import contextmanager
from daisyfl.utils.logger import DEBUG, INFO, WARNING, ERROR
from queue import Queue
from typing import Callable, Iterator, Optional, Tuple, Any, Dict, List
from daisyfl.utils.connection import grpc_connection
from daisyfl.utils.metadata import metadata_to_dict, dict_to_metadata
from daisyfl.utils import daisyfl_serde
import grpc
from threading import Condition, Event, Lock

from daisyfl.common import (
    GRPC_MAX_MESSAGE_LENGTH
)
from daisyfl.utils.logger import log
from daisyfl.proto.transport_pb2 import ClientMessage, ServerMessage
from daisyfl.proto.transport_pb2_grpc import DaisyServiceStub
from iterators import TimeoutIterator

# The following flags can be uncommented for debugging. Other possible values:
# https://github.com/grpc/grpc/blob/master/doc/environment_variables.md
# import os
# os.environ["GRPC_VERBOSITY"] = "debug"
# os.environ["GRPC_TRACE"] = "tcp,http"


SLEEP_DURATION = 2


class Z2MConnection:
    """Connection between Master node and Zone node."""

    def __init__(self,
        # for grpc_connection
        parent_address: str = None,
        max_message_length: int = GRPC_MAX_MESSAGE_LENGTH,
        uplink_certificates: Optional[bytes] = None,
        metadata: Tuple = (),
        # sync up with zone entry
        zone_entry = None,
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
        # sync up with zone entry
        self._zone_entry = zone_entry
        
    def run(self,):
        """Enable connection between Master node and Zone node."""
        while True:
            # Wait for ZoneEntry ready and for reconnection
            log(DEBUG, "Connector idling")
            self.event_reconn.wait()
            log(DEBUG, "Connector reconnecting")
            try:
                with grpc_connection(self._parent_address, self._metadata, self._uplink_certificates) as conn:
                    self.send, self.receive = conn
                    # send ClientStatus
                    self.send(ClientMessage(client_status=self._zone_entry.get_client_status()))
                    # ZoneEntry can use
                    self.event_reconn.clear()
                    self.event_disconn.clear()
                    log(DEBUG, "ZoneEntry's term")
                    # Wait for ConnectionFail
                    self.event_disconn.wait()
                    log(INFO, "Sleep for " + str(SLEEP_DURATION) + " seconds")
                    Event().wait(timeout=SLEEP_DURATION)
                    log(DEBUG, "Connector's term")
            except:
                log(INFO, "Sleep for " + str(SLEEP_DURATION) + " seconds")
                Event().wait(timeout=SLEEP_DURATION)

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

    def get_metadata(self,) -> Tuple:
        return self._metadata
