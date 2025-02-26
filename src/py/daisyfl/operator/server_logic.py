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
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Callable
from queue import Queue
from daisyfl.strategy import Strategy
from daisyfl.metrics_handler import MetricsHandler
from daisyfl.common import (
    Parameters,
    Report,
    Task,
    CURRENT_ROUND,
    TID,
)
from daisyfl.utils.logger import log
from daisyfl.common.communicator import Communicator


class ServerLogic(ABC):
    """Abstract base class for server (Zone or Master) operational logic defenition."""
    
    def __init__(self,
        communicator: Communicator,
        strategy: Strategy,
        metrics_handler: MetricsHandler
    ) -> None:
        self.communicator: Communicator = communicator
        self.strategy: Strategy = strategy
        self.metrics_handler: MetricsHandler = metrics_handler

    @abstractmethod
    def fit_round(
        self,
        parameters: Parameters,
        task: Task,
    ) -> Optional[
        Tuple[Optional[Parameters], Optional[Report]]
    ]:
        """Perform a single round fit."""

    @abstractmethod
    def evaluate_round(
        self,
        parameters: Parameters,
        task: Task,
    ) -> Optional[Report]:
        """Validate current global model."""
        
