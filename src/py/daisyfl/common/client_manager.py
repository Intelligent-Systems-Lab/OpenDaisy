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
"""Daisy ClientManager."""


import random
import threading
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Set, Union, Tuple

from daisyfl.utils.logger import log, INFO, WARNING
from daisyfl.common import FitRes, EvaluateRes

from .client_proxy import ClientProxy
from .criterion import Criterion
import time


class ClientManager:
    """Daisy ClientManager."""

    def __init__(self) -> None:
        self.communicator = None
        self.children: Dict[str, ClientProxy] = {}
        self.busy_children: Set = set()
        self.busy_children_subtask_id: Dict[str, List[str]] = {}    
        self._cv = threading.Condition()
    
    # children
    def register_client(self, client: ClientProxy) -> bool:
        """Register a Daisy ClientProxy instance.

        Returns:
            bool: Indicating if registration was successful. False if ClientProxy is
                already registered or can not be registered for any reason
        """
        # check cid
        if self.children.__contains__(client.cid):
            return False
        
        client.set_submit_result_fn(self.submit_result)
        client.set_is_pending_fn(self.is_client_pending)
        client.set_client_status_transition_fn(self.client_status_transition)
        
        self.children[client.cid] = client

        with self._cv:
            self._cv.notify_all()
        
        return True

    def unregister_client(self, client: ClientProxy) -> None:
        """Unregister a Daisy ClientProxy instance."""
        if self.children.__contains__(client.cid):
            self.children.pop(client.cid)
        else:
            log(WARNING, "Unregister a nonexistent client.")
        
        with self._cv:
            self._cv.notify_all()

    def shutdown(self,) -> None:
        """Unregister all client proxies before shutdown."""
        # NOTE: Iterating over a snapshot of values to avoid race condition
        for client in list(self.children.values()):
            client.bridge.close()
            self.unregister_client(client)
            del client
            
    # communicator
    def set_communicator(self, communicator) -> None:
        """Set the communicator."""
        self.communicator = communicator

    def hold_clients(self, cids: List[str], subtask_id: str) -> None:
        """Let clients become busy."""
        self.busy_children_subtask_id[subtask_id] = cids
        for cid in cids:
            self.busy_children.add(cid)

    def release_clients(self, subtask_id: str) -> None:
        """Remove all client proxies associated with the specific subtask from busy_children."""
        if self.busy_children_subtask_id.__contains__(subtask_id):
            l = self.busy_children_subtask_id[subtask_id]
            for cid in l:
                if self.busy_children.__contains__(cid):
                    self.busy_children.remove(cid)
            del self.busy_children_subtask_id[subtask_id]

    def submit_result(
        self, result: Tuple[ClientProxy, Union[FitRes, EvaluateRes]], roaming: bool,
    ) -> None:
        """Method called by client proxies to submit a result."""
        if roaming:
            # submit to communicator
            self.communicator.submit_result(result, roaming, None)
        else:
            # find subtask_id
            client_proxy, _ = result
            obj_stid = None
            # NOTE: Iterating over a snapshot of items to avoid race condition
            for stid, cids in list(self.busy_children_subtask_id.items()):
                if cids.__contains__(client_proxy.cid):
                    obj_stid = stid
                    self.busy_children_subtask_id[stid].pop(self.busy_children_subtask_id[stid].index(client_proxy.cid))
                    break
            if self.busy_children.__contains__(client_proxy.cid):
                self.busy_children.remove(client_proxy.cid)
            # submit to communicator
            self.communicator.submit_result(result, roaming, obj_stid)

    def is_client_pending(self, cid: str,) -> None:
        """Check the existence of the related subtask."""
        if self.busy_children.__contains__(cid):
            return True
        return False

    def client_status_transition(self, client: ClientProxy, status: str) -> None:
        """
        Method to transit the status of a client proxy.
        The argument "status" can be one of the following global variables:
        1. CLIENT_ROAM
        2. CLIENT_FAIL
        """
        obj_stid = None
        # NOTE: Iterating over a snapshot of items to avoid race condition
        for stid, cids in list(self.busy_children_subtask_id.items()):
            if cids.__contains__(client.cid):
                obj_stid = stid
                self.busy_children_subtask_id[stid].pop(self.busy_children_subtask_id[stid].index(client.cid))
                break
        if obj_stid is None:
            return
        if self.busy_children.__contains__(client.cid):
            self.busy_children.remove(client.cid)
        self.communicator.client_status_transition(obj_stid, status)
        return

    def sample_clients(
        self,
        num_clients: Optional[int] = None,
        waiting_time_before_sample: float = 5.0,
        retries: int = 100,
        cv_timeout: float = 60.0,
        criterion: Optional[Criterion] = None,
    ) -> List[ClientProxy]:
        """Sample Daisy ClientProxy instances."""
        time.sleep(waiting_time_before_sample)
        # case 1: best effort
        if num_clients is None:
            return self.get_available_clients(criterion=criterion)
        # case 2: sample clients with blocking quotas
        elif num_clients > 0:
            for _ in range(retries):
                # Block until at least num_clients are connected.
                with self._cv:
                    success = self._cv.wait_for(
                        lambda: self.num_available() >= num_clients, timeout=cv_timeout,
                    )
                
                if success:
                    client_list = self.get_available_clients(criterion=criterion)
                
                    if len(client_list) >= num_clients:
                        return random.sample(client_list, num_clients)
                    
                    # Block until the next client registration
                    with self._cv:
                        self._cv.wait()
        # case 3: num_clients is invalid
        else:
            log(
                WARNING,
                "Sampling failed: number of requested clients (%s) is non-positive.",
                num_clients,
            )
            return []

    def num_available(self,) -> int:
        """Return the number of available clients."""
        nums = 0
        # NOTE: Iterating over a snapshot of values to avoid race condition
        for client in list(self.children.values()):
            if client.bridge.client_available():
                nums = nums + 1
        return nums

    def get_available_clients(self, criterion: Optional[Criterion] = None):
        """Get all available client proxies."""
        client_list = []
        # NOTE: Iterating over a snapshot of values to avoid race condition
        for client in list(self.children.values()):
            if client.bridge.client_available():
                if criterion is not None:
                    if criterion.is_valid_candidate(client):
                            client_list.append(client)
                else:
                    client_list.append(client)
        return client_list

