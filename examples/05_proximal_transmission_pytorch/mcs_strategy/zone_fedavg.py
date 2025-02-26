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
"""Federated Averaging (FedAvg) [McMahan et al., 2016] strategy.

Paper: https://arxiv.org/abs/1602.05629
"""


from typing import Callable, Dict, List, Optional, Tuple, Union

from daisyfl.common import (
    EvaluateIns,
    EvaluateRes,
    FitIns,
    FitRes,
    MetricsAggregationFn,
    NDArrays,
    Parameters,
    Scalar,
    SubtaskStatus,
    METRICS,
    ACCURACY,
    LOSS,
    DATA_SAMPLES,
    CURRENT_ROUND,
)
from daisyfl.utils.parameter import ndarrays_to_parameters, parameters_to_ndarrays
from daisyfl.utils.logger import log
from daisyfl.common.client_proxy import ClientProxy
from daisyfl.common.client_manager import ClientManager
from daisyfl.common.criterion import Criterion

from daisyfl.utils.aggregate import aggregate_fedavg, weighted_loss_avg, weighted_acc_avg
from daisyfl.strategy import Strategy
import time
from daisyfl.utils.logger import log, INFO
import random
from const import TRANSITION
import copy


class ZoneFedAvg(Strategy):
    """Configurable FedAvg strategy implementation."""
    def __init__(
        self,
        client_manager: ClientManager,
        num_clients_fit: int = 2,
        num_clients_evaluate: int = 2,
        min_results_fit: int = 2,
        min_results_evaluate: int = 2,
    ) -> None:
        """Federated Averaging strategy.

        Implementation based on https://arxiv.org/abs/1602.05629
        """
        self.client_manager = client_manager
        self.num_clients_fit = num_clients_fit
        self.num_clients_evaluate = num_clients_evaluate
        self.min_results_fit = min_results_fit
        self.min_results_evaluate = min_results_evaluate

    def configure_fit(
        self,
        parameters: Parameters,
        config: Dict,
        **kwargs,
    ) -> List[Tuple[ClientProxy, FitIns]]:
        """Configure the next round of fitting."""
        fit_ins = FitIns(parameters, config)
        clients = self.client_manager.sample_clients(self.num_clients_fit, 5,)
        
        log(INFO, "Randomly select one client to roam.")
        client_instructions = []
        roamer_idx = random.sample(list(range(len(clients))), 1)
        for idx in range(len(clients)):
            ins = copy.deepcopy(fit_ins)
            if idx in roamer_idx:
                ins.config[TRANSITION] = True
            client_instructions.append((clients[idx], ins))
        
        return client_instructions

    def configure_evaluate(
        self,
        parameters: Parameters,
        config: Dict,
        **kwargs,
    ) -> List[Tuple[ClientProxy, EvaluateIns]]:
        """Configure the next round of evaluation."""
        evaluate_ins = EvaluateIns(parameters, config)
        clients = self.client_manager.sample_clients(self.num_clients_evaluate, 5,)
        return [(client, evaluate_ins) for client in clients]

    def wait_fit(
        self, subtask_status: SubtaskStatus, **kwargs
    ) -> bool:
        """Wait for the termination condition of fitting."""
        time.sleep(kwargs.get("min_waiting_time"))
        with subtask_status.cnd:
            subtask_status.cnd.wait_for(lambda: (subtask_status.success_num + subtask_status.roaming_num >= self.min_results_fit) or \
                (subtask_status.participant_num - subtask_status.failure_num < self.min_results_fit)
            )
        if (subtask_status.success_num + subtask_status.roaming_num >= self.min_results_fit):
            return True
        return False
    
    def wait_evaluate(
        self, subtask_status: SubtaskStatus, **kwargs
    ) -> bool:
        """Wait for the termination condition of evaluating."""
        time.sleep(kwargs.get("min_waiting_time"))
        with subtask_status.cnd:
            subtask_status.cnd.wait_for(lambda: (subtask_status.success_num + subtask_status.roaming_num >= self.min_results_evaluate) or \
                (subtask_status.participant_num - subtask_status.failure_num < self.min_results_evaluate)
            )
        if (subtask_status.success_num + subtask_status.roaming_num >= self.min_results_evaluate):
            return True
        return False

    def aggregate_fit(
        self,
        results: List[Tuple[ClientProxy, FitRes]],
        **kwargs,
    ) -> Tuple[Optional[Parameters], Dict]:
        """Aggregate fit results using weighted average."""
        # parameters
        weighted_results = [
            (parameters_to_ndarrays(fit_res.parameters), fit_res.config[METRICS][DATA_SAMPLES])
            for _, fit_res in results
        ]
        parameters_aggregated = ndarrays_to_parameters(aggregate_fedavg(weighted_results))

        # metrics
        metrics_aggregated = {DATA_SAMPLES: sum([fit_res.config[METRICS][DATA_SAMPLES] for _, fit_res in results])}

        return parameters_aggregated, metrics_aggregated

    def aggregate_evaluate(
        self,
        results: List[Tuple[ClientProxy, EvaluateRes]],
        **kwargs,
    ) -> Dict:
        """Aggregate evaluation losses using weighted average."""
        # Aggregate acc
        acc_aggregated = weighted_acc_avg(
            [
                (evaluate_res.config[METRICS][ACCURACY], evaluate_res.config[METRICS][DATA_SAMPLES])
                for _, evaluate_res in results
            ]
        )
        # Aggregate loss
        loss_aggregated = weighted_loss_avg(
            [
                (evaluate_res.config[METRICS][LOSS], evaluate_res.config[METRICS][DATA_SAMPLES])
                for _, evaluate_res in results
            ]
        )
        # update metrics
        metrics_aggregated = {
            ACCURACY: acc_aggregated,
            LOSS: loss_aggregated,
            DATA_SAMPLES: sum([evaluate_res.config[METRICS][DATA_SAMPLES] for _, evaluate_res in results])
        }
        return metrics_aggregated

