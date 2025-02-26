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
from typing import List, Optional, Callable
from daisyfl.common import (
    FitIns,
    FitRes,
    EvaluateIns,
    EvaluateRes,
)
from daisyfl.operator import ClientLogic
from daisyfl.utils.logger import log, INFO

class MyClientLogic(ClientLogic):
    """Base Daisy Client operational logic definition."""

    def __init__(self, trainer, get_anchor_fn: Callable, handover_fn: Callable,) -> None:
        self.trainer = trainer
        self.get_anchor_fn = get_anchor_fn
        self.handover_fn = handover_fn
    
    def fit(
        self, ins: FitIns,
    ) -> FitRes:
        """Define the operation before and after client fit the local model."""
        log(INFO, "=====================================.")
        log(INFO, "Welcome to developing your own module.")
        log(INFO, "You are using the customized module if you see this message.")
        log(INFO, "Client will fit the model.")
        log(INFO, "=====================================.")
        return self.trainer.fit(ins)

    def evaluate(
        self, ins: EvaluateIns,
    ) -> EvaluateRes:
        """Define the operation before and after client evaluate the local model."""
        log(INFO, "=====================================.")
        log(INFO, "Welcome to developing your own module.")
        log(INFO, "You are using the customized module if you see this message.")
        log(INFO, "Client will evaluate the model.")
        log(INFO, "=====================================.")
        return self.trainer.evaluate(ins)
