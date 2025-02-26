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
"""Daisy communicator."""


import concurrent.futures
from threading import Condition
from queue import Queue
from typing import Dict, List, Optional, Tuple, Union, Callable, Generator
import gc
from daisyfl.common import (
    ErrorCode,
    EvaluateIns,
    EvaluateRes,
    FitIns,
    FitRes,
    SubtaskStatus,
    TID,
    CLIENT_FAIL,
    CLIENT_ROAM
)
from daisyfl.utils.logger import log
from .client_manager import ClientManager
from .client_proxy import ClientProxy
from .criterion import Criterion
import gc

FitResultsAndFailures = Tuple[
    List[Tuple[ClientProxy, FitRes]],
    List[Union[Tuple[ClientProxy, FitRes], BaseException]],
]
EvaluateResultsAndFailures = Tuple[
    List[Tuple[ClientProxy, EvaluateRes]],
    List[Union[Tuple[ClientProxy, EvaluateRes], BaseException]],
]

class Communicator:
    """Daisy communicator."""
    def __init__(
        self, *, 
        client_manager: ClientManager,
        server_address: str,
    ) -> None:
        self.server_address: str = server_address
        self._client_manager: ClientManager = client_manager
        # subtask
        self._generator = self._subtask_id_generation_fn()
        self._generate_subtask_id: Callable = lambda: next(self._generator)
        self._subtask_status: Dict[str, SubtaskStatus] = {}
        self._queues: Dict[str, Queue] = {}
        self._roaming_queues_fit: Dict[str, Queue[FitRes]] = {}
        self._roaming_queues_evaluate: Dict[str, Queue[EvaluateRes]] = {}
        
    # subtask
    def _subtask_id_generation_fn(self,) -> Generator[str, None, None]:
        """Generate a unique subtask ID."""
        _ticket = 0
        while True:
            yield f"{_ticket:05}"
            _ticket += 1

    def _register_subtask(
        self, 
        subtask_id: str, 
        participant_num: int,
    ) -> SubtaskStatus:
        """Register a new subtask."""
        # SubtaskStatus
        self._subtask_status[subtask_id] = SubtaskStatus(
            participant_num=participant_num,
            success_num=0,
            failure_num=0,
            roaming_num=0,
            cnd=Condition(),
        )
        # queue
        self._queues[subtask_id] = Queue()
        return self._subtask_status[subtask_id]

    def finish_subtask(self, subtask_id: str) -> None:
        """
        Method called by ServerOperators to finish a subtask.

        Finishing a subtask means that this Daisy node would not
        wait for more results from associated clients.
        """
        del self._subtask_status[subtask_id]
        del self._queues[subtask_id]
        gc.collect()
        self._client_manager.release_clients(subtask_id)
        return

    def submit_result(
        self, result: Tuple[ClientProxy, Union[FitRes, EvaluateRes]], roaming: bool, subtask_id: Optional[str],
    ) -> None:
        """Method called by ClientManager to submit a result (FitRes or EvaluateRes)."""
        _, res = result
        # case 1: client roamed cross zones
        if roaming:
            if res.status.error_code == ErrorCode.OK:
                tid = res.config[TID]
                # case 1.1: fit
                if isinstance(res, FitRes):
                    if not self._roaming_queues_fit.__contains__(tid):
                        self._roaming_queues_fit[tid] = Queue()
                    self._roaming_queues_fit[tid].put(result)
                # case 1.2: evaluate
                else:
                    if not self._roaming_queues_evaluate.__contains__(tid):
                        self._roaming_queues_evaluate[tid] = Queue()
                    self._roaming_queues_evaluate[tid].put(result)
        # case 2: client uploads its result to anchor
        else:
            try:
                # Check error code
                if res.status.error_code == ErrorCode.OK:
                    self._subtask_status[subtask_id].success_num += 1
                    self._queues[subtask_id].put(result)
                # Not successful, client returned a result where the error code is not OK
                else:
                    self._subtask_status[subtask_id].failure_num += 1
                with self._subtask_status[subtask_id].cnd:
                    self._subtask_status[subtask_id].cnd.notify_all()
            except:
                raise Exception("Designated subtask was expired.")

    def client_status_transition(self, subtask_id: str, status: str) -> None:
        """
        ClientManager call this function to notify the communicator
        that a client failed or roamed.
        """
        try:
            if status == CLIENT_FAIL:
                self._subtask_status[subtask_id].failure_num += 1
            elif status == CLIENT_ROAM:
                self._subtask_status[subtask_id].roaming_num += 1
            with self._subtask_status[subtask_id].cnd:
                self._subtask_status[subtask_id].cnd.notify_all()
        except:
            raise Exception("Designated subtask was expired.")
    
    def get_results(self, subtask_id: str) -> List[Tuple[ClientProxy, Union[FitRes, EvaluateRes]]]:
        """
        Method called by ServerOperators to get the results (FitRes or EvaluateRes).
        """
        results = []
        q = self._queues[subtask_id]
        while not q.empty():
            results.append(q.get())
        return results
    
    def get_results_roaming(self, tid: str, is_fit: bool) -> List[Tuple[ClientProxy, Union[FitRes, EvaluateRes]]]:
        """
        Method called by ServerOperators to get the roamers' results (FitRes or EvaluateRes).
        """
        results = []
        # case 1: get fit results
        if is_fit:
            if not self._roaming_queues_fit.__contains__(tid):
                return []
            q = self._roaming_queues_fit[tid]
            # get all results
            while not q.empty():
                results.append(q.get())
            del self._roaming_queues_fit[tid]
            return results
        
        # case 2: get evaluate results
        if not self._roaming_queues_evaluate.__contains__(tid):
            return []
        q = self._roaming_queues_evaluate[tid]
        # get all results
        while not q.empty():
            results.append(q.get())
        del self._roaming_queues_evaluate[tid]
        return results

    # communication
    def fit_clients(
        self,
        client_instructions: List[Tuple[ClientProxy, FitIns]],
    ) -> Tuple[str, SubtaskStatus]:
        """
        Method called by ServerOperators to communicate with
        children for fitting a FL model.
        """
        subtask_id = self._generate_subtask_id()
        subtask_status: SubtaskStatus = self._register_subtask(subtask_id, len(client_instructions))
        self._fit_clients(
            client_instructions=client_instructions,
        )
        self._client_manager.hold_clients(
            cids=[client.cid for client, _ in client_instructions],
            subtask_id=subtask_id,
        )
        return subtask_id, subtask_status

    def evaluate_clients(
        self,
        client_instructions: List[Tuple[ClientProxy, EvaluateIns]],
    ) -> Tuple[str, SubtaskStatus]:
        """
        Method called by ServerOperators to communicate with
        children for evaluating a FL model.
        """
        subtask_id = self._generate_subtask_id()
        subtask_status: SubtaskStatus = self._register_subtask(subtask_id, len(client_instructions))
        self._evaluate_clients(
            client_instructions=client_instructions,
        )
        self._client_manager.hold_clients(
            cids=[client.cid for client, _ in client_instructions],
            subtask_id=subtask_id,
        )
        return subtask_id, subtask_status

    def _fit_clients(
        self,
        client_instructions: List[Tuple[ClientProxy, FitIns]],
    ) -> None:
        """Refine parameters concurrently on all sampled clients."""
        with concurrent.futures.ThreadPoolExecutor() as executor:
            {
                executor.submit(client_proxy.fit, ins)
                for client_proxy, ins in client_instructions
            }

    def _evaluate_clients(
        self,
        client_instructions: List[Tuple[ClientProxy, EvaluateIns]],
    ) -> None:
        """Evaluate parameters concurrently on all sampled clients."""
        with concurrent.futures.ThreadPoolExecutor() as executor:
            {
                executor.submit(client_proxy.evaluate, ins)
                for client_proxy, ins in client_instructions
            }

