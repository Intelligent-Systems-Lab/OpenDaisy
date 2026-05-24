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
"""Handle metrics update and exposure."""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Callable, Optional
from daisyfl.utils.logger import DEBUG, INFO, ERROR, WARNING
from daisyfl.utils.logger import log

class MetricsHandler(ABC):
    """Abstract base class for coping with metrics update and exposure."""
    
    @abstractmethod
    def update_metrics_fit(self, config: Dict):
        """Update fitting metrics."""

    @abstractmethod
    def update_metrics_evaluate(self, config: Dict):
        """Update evaluation metrics."""
    
    @abstractmethod
    def get_metrics(self,):
        """Expose metrics through API gateway."""

    @abstractmethod
    def __repr__(self) -> str:
        """Print metrics."""