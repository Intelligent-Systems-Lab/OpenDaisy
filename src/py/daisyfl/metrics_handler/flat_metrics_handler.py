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

from functools import reduce
from .metrics_handler import MetricsHandler
from typing import Dict, List, Tuple, Callable, Optional
from daisyfl.utils.logger import DEBUG, INFO, ERROR, WARNING
from daisyfl.utils.logger import log

from daisyfl.common import (
    CURRENT_ROUND,
    CURRENT_ROUND_MASTER,
    CURRENT_ROUND_ZONE,
    ZONE_COMM_FREQUENCY,
    METRICS,
    ACCURACY,
    LOSS,
    DATA_SAMPLES,
)
from flask import Flask, request, make_response, Response

class FlatMetricsHandler(MetricsHandler):
    """MetricsHandler class to cope with metrics update and exposure."""

    def __init__(
        self,
    ) -> None:
        log(DEBUG, "Start MetricsHandler.")
        super().__init__()
        self.acc: List = []
        self.loss: List = []
        self.fit_data_samples: List = []
        self.evaluate_data_samples: List = []
    
    def update_metrics_fit(self, config: Dict):
        """Update fitting metrics."""
        # DEFAULT: data_samples
        self.fit_data_samples.append((config[CURRENT_ROUND], config[METRICS][DATA_SAMPLES]))
        return

    def update_metrics_evaluate(self, config: Dict):
        """Update evaluation metrics."""
        # DEFAULT: data_samples, accuracy and loss.
        self.acc.append((config[CURRENT_ROUND], config[METRICS][ACCURACY]))
        self.loss.append((config[CURRENT_ROUND], config[METRICS][LOSS]))
        self.evaluate_data_samples.append((config[CURRENT_ROUND], config[METRICS][DATA_SAMPLES]))
        return
    
    def get_metrics(self,):
        """Expose metrics through API gateway."""
        # DEFAULT: expose metrics to prometheus.
        log(INFO, self)
        response = make_response("")
        response.headers["content-type"] = "text/plain"
        return response

    def __repr__(self) -> str:
        """Print metrics."""
        rep = ""
        rep += "Accuracy:\n" + reduce(
                lambda a, b: a + b,
                [
                    f"\tround {server_round}: {acc}\n"
                    for server_round, acc in self.acc
                ],
            )
        rep += "Loss:\n" + reduce(
                lambda a, b: a + b,
                [
                    f"\tround {server_round}: {loss}\n"
                    for server_round, loss in self.loss
                ],
            )
        return rep

