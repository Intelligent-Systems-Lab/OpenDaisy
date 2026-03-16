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
"""Daisy task launcher."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from daisyfl.common import METRICS_HANDLERS, OPERATORS, STRATEGIES, TID, Parameters, Report, Task
from daisyfl.metrics_handler.metrics_handler import MetricsHandler
from daisyfl.operator import ServerLogic
from daisyfl.strategy.strategy import Strategy
from daisyfl.utils.dynamic_loader import dynamic_load
from daisyfl.utils.logger import ERROR, log

from .client_manager import ClientManager
from .communicator import Communicator


@dataclass
class TaskCoreInstance:
    """Data structure consists of all dynamically loaded modules."""

    operator: ServerLogic
    strategy: Strategy
    metrics_handler: MetricsHandler


class TaskLauncher:
    """Initialize and manage all dynamically loaded modules."""

    def __init__(
        self,
        communicator: Communicator,
        client_manager: ClientManager,
    ):
        """Initialize TaskLauncher."""
        self.communicator: Communicator = communicator
        self.client_manager: ClientManager = client_manager
        self.task_core_instances: Dict[str, TaskCoreInstance] = {}
        self.operator_key = ""
        self.strategy_key = ""
        self.metrics_handler_key = ""

    def fit_round(self, parameters: Parameters, task: Task) -> Tuple[Parameters, Report]:
        """Method called by TaskManager to fit a FL model for a round of communication."""
        task_core_instance: Optional[TaskCoreInstance] = self._get_task_core_instance(tid=task.config[TID])
        if task_core_instance is None:
            self._register_task_core_instance(task.config)
            task_core_instance: Optional[TaskCoreInstance] = self._get_task_core_instance(tid=task.config[TID])
        parameters, report = task_core_instance.operator.fit_round(parameters, task)

        return parameters, report

    def evaluate_round(self, parameters: Parameters, task: Task) -> Report:
        """Method called by TaskManager to evaluate a FL model for a round of communication."""
        task_core_instance: Optional[TaskCoreInstance] = self._get_task_core_instance(tid=task.config[TID])
        if task_core_instance is None:
            self._register_task_core_instance(task.config)
            task_core_instance: Optional[TaskCoreInstance] = self._get_task_core_instance(tid=task.config[TID])
        report = task_core_instance.operator.evaluate_round(parameters, task)

        return report

    def get_metrics(self, tid: str):
        """Expose the metrics from MetricsHandler."""
        try:
            return self.task_core_instances[tid].metrics_handler.get_metrics()
        except Exception as err:
            raise Exception(
                "Can't get metrics from MetricsHandler. "
                "Either incorrect task_id or inappropriate MetricsHandler was used."
            ) from err

    def set_task_launcher_keys(self, keys: List[str]) -> None:
        """Called by TaskManager to set the path for loading modules."""
        self.operator_key = keys[0]
        self.strategy_key = keys[1]
        self.metrics_handler_key = keys[2]

    def _get_task_core_instance(self, tid: str) -> Optional[TaskCoreInstance]:
        """Find the TaskCoreInstance."""
        if self.task_core_instances.__contains__(tid):
            return self.task_core_instances[tid]
        return None

    def _register_task_core_instance(self, config: Dict) -> None:
        """Register a new TaskCoreInstance."""
        tid = config[TID]
        operator_path = config[OPERATORS][self.operator_key]
        strategy_path = config[STRATEGIES][self.strategy_key]
        metrics_handler_path = config[METRICS_HANDLERS][self.metrics_handler_key]

        try:
            operator: ServerLogic = dynamic_load(operator_path[0], operator_path[1])
        except Exception as err:
            log(ERROR, 'Can\'t load Class "%s" from "%s".', operator_path[1], operator_path[0])
            raise Exception(f'Can\'t load Class "{operator_path[1]}" from "{operator_path[0]}".') from err
        try:
            strategy: Strategy = dynamic_load(strategy_path[0], strategy_path[1])
        except Exception as err:
            log(ERROR, 'Can\'t load Class "%s" from "%s".', strategy_path[1], strategy_path[0])
            raise Exception(f'Can\'t load Class "{strategy_path[1]}" from "{strategy_path[0]}".') from err
        try:
            metrics_handler: MetricsHandler = dynamic_load(metrics_handler_path[0], metrics_handler_path[1])
        except Exception as err:
            log(ERROR, 'Can\'t load Class "%s" from "%s".', metrics_handler_path[1], metrics_handler_path[0])
            raise Exception(f'Can\'t load Class "{metrics_handler_path[1]}" from "{metrics_handler_path[0]}".') from err

        strategy_instance = strategy(self.client_manager)
        metrics_handler_instance = metrics_handler()
        operator_instance = operator(
            communicator=self.communicator, strategy=strategy_instance, metrics_handler=metrics_handler_instance
        )

        self.task_core_instances[tid] = TaskCoreInstance(
            operator=operator_instance,
            strategy=strategy_instance,
            metrics_handler=metrics_handler_instance,
        )

    def _unregister_task_core_instance(self, tid: str) -> None:
        """Unregister a TaskCoreInstance."""
        if self.task_core_instances.__contains__(tid):
            del self.task_core_instances[tid]
