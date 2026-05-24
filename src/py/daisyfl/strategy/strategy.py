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
"""Daisy strategy."""


from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Union

from daisyfl.common import EvaluateIns, EvaluateRes, FitIns, FitRes, Parameters, Scalar, SubtaskStatus
from daisyfl.common.client_proxy import ClientProxy


class Strategy(ABC):
    """Abstract base class for Daisy strategy implementations."""

    @abstractmethod
    def configure_fit(
        self, parameters: Parameters, config: Dict, **kwargs
    ) -> List[Tuple[ClientProxy, FitIns]]:
        """Configure the next round of fitting."""
    
    @abstractmethod
    def configure_evaluate(
        self, parameters: Parameters, config: Dict, **kwargs
    ) -> List[Tuple[ClientProxy, EvaluateIns]]:
        """Configure the next round of evaluating."""

    @abstractmethod
    def wait_fit(
        self, subtask_status: SubtaskStatus, **kwargs
    ) -> bool:
        """Wait for the termination condition of fitting."""

    @abstractmethod
    def wait_evaluate(
        self, subtask_status: SubtaskStatus, **kwargs
    ) -> bool:
        """Wait for the termination condition of evaluating."""

    @abstractmethod
    def aggregate_fit(
        self,
        results: List[Tuple[ClientProxy, FitRes]],
        **kwargs,
    ) -> Tuple[Optional[Parameters], Dict]:
        """Aggregate fitting results."""

    @abstractmethod
    def aggregate_evaluate(
        self,
        results: List[Tuple[ClientProxy, EvaluateRes]],
        **kwargs,
    ) -> Dict:
        """Aggregate evaluation results."""

