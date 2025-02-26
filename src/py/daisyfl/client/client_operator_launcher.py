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
from daisyfl.utils.logger import log, ERROR
from dataclasses import dataclass
from typing import List, Tuple, Union, Dict, Optional, Callable
from daisyfl.utils.dynamic_loader import dynamic_load
from daisyfl.operator import ClientLogic
from daisyfl.common import (
    Parameters,
    Task,
    Report,
    FitIns,
    FitRes,
    EvaluateIns,
    EvaluateRes,
    TID,
    OPERATORS,
    STRATEGIES,
    CLIENT_OPERATOR,
    Status,
    ErrorCode,
)

from daisyfl.client.trainer import Trainer


class ClientOperatorLauncher:
    """Initialize and manage client operators."""

    def __init__(self, trainer: Trainer, server_address: str,):
        self.trainer: Trainer = trainer
        self.server_address = server_address
        self.operators: Dict[ClientLogic] = {}
        self.operator_key = CLIENT_OPERATOR

    def fit(
        self, ins: FitIns,
    ) -> FitRes:
        """
        Method called by MessageHandler to fit a FL model for a round of communication.
        """
        client_operator: Optional[ClientLogic] = self._get_client_operator(tid=ins.config[TID])
        if client_operator is None:
            if self._register_operator(ins.config):
                client_operator: Optional[ClientLogic] = self._get_client_operator(tid=ins.config[TID])
            else:
                return FitRes(
                    status=Status(error_code=ErrorCode.FIT_NOT_IMPLEMENTED, message="Operator initialization fail"),
                    parameters=Parameters(tensors=[], tensor_type=""),
                    config=ins.config,
                )
        return  client_operator.fit(ins)

    def evaluate(
        self, ins: EvaluateIns,
    ) -> EvaluateRes:
        """
        Method called by MessageHandler to evaluate a FL model for a round of communication.
        """
        client_operator: Optional[ClientLogic] = self._get_client_operator(tid=ins.config[TID])

        if client_operator is None:
            if self._register_operator(ins.config):
                client_operator: Optional[ClientLogic] = self._get_client_operator(tid=ins.config[TID])
            else:
                return EvaluateRes(
                    status=Status(error_code=ErrorCode.EVALUATE_NOT_IMPLEMENTED, message="Operator initialization fail"),
                    config=ins.config,
                )
        return client_operator.evaluate(ins)

    def set_handover_fn(self, handover_fn: Callable=None) -> None:
        """
        Set callback function to bridge the handover function, which
        will be used by ClientOperators.
        """
        self._handover_fn = handover_fn
    
    def set_get_anchor_fn(self, get_anchor_fn: Callable=None) -> None:
        """
        Set callback function to bridge the get_anchor function, which
        will be used by ClientOperators.
        """
        self._get_anchor_fn = get_anchor_fn

    def _get_client_operator(self, tid: str) -> Optional[ClientLogic]:
        if self.operators.__contains__(tid):
            return self.operators[tid]
        return None
    
    def _register_operator(self, config: Dict) -> bool:
        tid = config[TID]
        operator_path = config[OPERATORS][self.operator_key]

        try:
            operator: ClientLogic = dynamic_load(operator_path[0], operator_path[1])
            op_instance = operator(trainer=self.trainer, get_anchor_fn=self._get_anchor_fn, handover_fn=self._handover_fn)
            self.operators[tid] = op_instance
            return True
        except:
            log(ERROR, "Can't load Class \"{}\" from \"{}\".".format(operator_path[1], operator_path[0]))
            return False
    
    def _unregister_operator(self, tid: str) -> None:
        if self.operators.__contains__(tid):
            del self.operators[tid]

