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
from const import TRANSITION


class MCSClientLogic(ClientLogic):
    """Daisy Client operational logic to demonstrate the roaming mechanism."""

    def __init__(self, trainer, get_anchor_fn: Callable, handover_fn: Callable,) -> None:
        self.trainer = trainer
        self.get_anchor_fn = get_anchor_fn
        self.handover_fn = handover_fn
        self.available_zones = ["0.0.0.0:8888", "0.0.0.0:8889"]
    
    def fit(
        self, ins: FitIns,
    ) -> FitRes:
        """Define the operation before and after client fit the local model."""
        if ins.config.__contains__(TRANSITION):
            if ins.config[TRANSITION]:
                idx = self.available_zones.index(self.get_anchor_fn())
                idx = (idx + 1) % len(self.available_zones)
                handover = True
            del ins.config[TRANSITION]
        else:
            handover = False

        res = self.trainer.fit(ins)

        if handover:
            log(INFO, "Client tries handover.")
            self.handover_fn(self.available_zones[idx])
            
        return res

    def evaluate(
        self, ins: EvaluateIns,
    ) -> EvaluateRes:
        """Define the operation before and after client evaluate the local model."""
        return self.trainer.evaluate(ins)
