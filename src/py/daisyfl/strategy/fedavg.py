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
from .strategy import Strategy
import time


class FedAvg(Strategy):
    """Configurable FedAvg strategy implementation."""
    def __init__(
        self,
        client_manager: ClientManager,
        num_clients_fit: int = 2,
        num_clients_evaluate: int = 2,
        min_results_fit: int = 2,
        min_results_evaluate: int = 2,
        **kwargs,
    ) -> None:
        """Federated Averaging strategy.

        Implementation based on https://arxiv.org/abs/1602.05629
        """
        super().__init__(**kwargs)
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
        return [(client, fit_ins) for client in clients]

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
            (parameters_to_ndarrays(fit_res.parameters), fit_res.config.get(METRICS, {}).get(DATA_SAMPLES, 0))
            for _, fit_res in results if fit_res.config.get(METRICS, {}).get(DATA_SAMPLES, 0) > 0
        ]
        
        if len(weighted_results) == 0:
            return kwargs.get("parameters"), {DATA_SAMPLES: 0}
            
        parameters_aggregated = ndarrays_to_parameters(aggregate_fedavg(weighted_results))

        # metrics
        metrics_aggregated = {DATA_SAMPLES: sum([w for _, w in weighted_results])}

        return parameters_aggregated, metrics_aggregated

    def aggregate_evaluate(
        self,
        results: List[Tuple[ClientProxy, EvaluateRes]],
        **kwargs,
    ) -> Dict:
        """Aggregate evaluation losses using weighted average."""
        valid_results = [
            (res.config[METRICS][ACCURACY], res.config[METRICS][LOSS], res.config[METRICS][DATA_SAMPLES])
            for _, res in results if METRICS in res.config and DATA_SAMPLES in res.config[METRICS] and res.config[METRICS][DATA_SAMPLES] > 0
        ]
        
        if len(valid_results) == 0:
            return {}

        # Aggregate acc
        acc_aggregated = weighted_acc_avg(
            [(acc, samples) for acc, loss, samples in valid_results]
        )
        # Aggregate loss
        loss_aggregated = weighted_loss_avg(
            [(loss, samples) for acc, loss, samples in valid_results]
        )
        # update metrics
        metrics_aggregated = {
            ACCURACY: acc_aggregated,
            LOSS: loss_aggregated,
            DATA_SAMPLES: sum([samples for acc, loss, samples in valid_results])
        }
        return metrics_aggregated

