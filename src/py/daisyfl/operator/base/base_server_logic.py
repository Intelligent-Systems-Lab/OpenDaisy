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
from typing import Dict, List, Optional, Tuple, Callable
from daisyfl.strategy import Strategy
from daisyfl.metrics_handler import MetricsHandler
from daisyfl.common import (
    Parameters,
    Report,
    Task,
    CURRENT_ROUND,
    TID,
    METRICS,
    MIN_WAITING_TIME,
)
from daisyfl.utils.logger import log
from daisyfl.common.communicator import Communicator
from ..server_logic import ServerLogic


class BaseServerLogic(ServerLogic):
    """Base server (Zone or Master) operational logic defenition."""

    def __init__(self,
        communicator: Communicator,
        strategy: Strategy,
        metrics_handler: MetricsHandler,
    ) -> None:
        self.communicator: Communicator = communicator
        self.strategy: Strategy = strategy
        self.metrics_handler: MetricsHandler = metrics_handler

    def fit_round(
        self,
        parameters: Parameters,
        task: Task,
    ) -> Optional[
        Tuple[Optional[Parameters], Optional[Report]]
    ]:
        """Perform a single round fit."""
        client_instructions = self.strategy.configure_fit(parameters=parameters, config=task.config)
        subtask_id, subtask_status = self.communicator.fit_clients(client_instructions=client_instructions)
        if self.strategy.wait_fit(subtask_status=subtask_status, min_waiting_time=task.config[MIN_WAITING_TIME]):
            # success
            results = self.communicator.get_results(subtask_id) + self.communicator.get_results_roaming(tid=task.config[TID], is_fit=True)
            self.communicator.finish_subtask(subtask_id)
            parameters, metrics = self.strategy.aggregate_fit(results=results)
            task.config.update({METRICS: metrics})
            self.metrics_handler.update_metrics_fit(task.config)
            task.config.update({METRICS: metrics,})
        else:
            # fail
            self.communicator.finish_subtask(subtask_id)
            task.config.update({METRICS: {},})
        return parameters, Report(config=task.config)


    def evaluate_round(
        self,
        parameters: Parameters,
        task: Task,
    ) -> Optional[Report]:
        """Validate current global model on a number of clients."""
        client_instructions = self.strategy.configure_evaluate(parameters=parameters, config=task.config)
        subtask_id, subtask_status = self.communicator.evaluate_clients(client_instructions)
        if self.strategy.wait_evaluate(subtask_status=subtask_status, min_waiting_time=task.config[MIN_WAITING_TIME]):
            # success
            results = self.communicator.get_results(subtask_id) + self.communicator.get_results_roaming(tid=task.config[TID], is_fit=False)
            self.communicator.finish_subtask(subtask_id)
            metrics = self.strategy.aggregate_evaluate(results=results)
            task.config.update({METRICS: metrics})
            self.metrics_handler.update_metrics_evaluate(task.config)
            task.config.update({METRICS: metrics,})
        else:
            # fail
            self.communicator.finish_subtask(subtask_id)
            task.config.update({METRICS: {},})
        return Report(config=task.config)

