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
"""Daisy trainers using NumPy."""


from abc import ABC
from typing import Dict, Tuple
from typing import Dict, Tuple
from daisyfl.common import (
    NDArrays,
    ErrorCode,
    EvaluateIns,
    EvaluateRes,
    FitIns,
    FitRes,
    NDArrays,
    Status,
)
from daisyfl.utils.parameter import ndarrays_to_parameters, parameters_to_ndarrays
from .trainer import Trainer


class NumPyTrainer(ABC):
    """Abstract base class for Daisy trainers using NumPy."""

    def fit(
        self, parameters: NDArrays, config: Dict
    ) -> Tuple[NDArrays, Dict]:
        """Train the provided parameters using the locally held dataset."""

    def evaluate(
        self, parameters: NDArrays, config: Dict
    ) ->  Dict:
        """Evaluate the provided parameters using the locally held dataset."""


class NumPyTrainerWrapper(Trainer):
    """Wrap NumPyTrainer to simply the development cost of Python users."""

    def __init__(self, numpy_trainer: NumPyTrainer) -> None:
        super().__init__()
        self.numpy_trainer = numpy_trainer

    def fit(self, ins: FitIns) -> FitRes:
        """Refine the provided parameters using the locally held dataset."""
        parameters: NDArrays = parameters_to_ndarrays(ins.parameters)
        # Train
        parameters_prime, config = self.numpy_trainer.fit(parameters, ins.config)  # type: ignore
        parameters_prime_proto = ndarrays_to_parameters(parameters_prime)
        # Return FitRes
        return FitRes(
            status=Status(error_code=ErrorCode.OK, message="Success"),
            parameters=parameters_prime_proto,
            config=config,
        )
    
    def evaluate(self, ins: EvaluateIns) -> EvaluateRes:
        """Evaluate the provided parameters using the locally held dataset."""
        parameters: NDArrays = parameters_to_ndarrays(ins.parameters)
        # Evaluate
        config = self.numpy_trainer.evaluate(parameters, ins.config)  # type: ignore
        # Return EvaluateRes
        return EvaluateRes(
            status=Status(error_code=ErrorCode.OK, message="Success"),
            config=config,
        )
