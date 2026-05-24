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
"""Aggregation functions for strategy implementations."""


from functools import reduce
from typing import List, Tuple, Callable

import numpy as np

from daisyfl.common import NDArrays


def aggregate_fedavg(results: List[Tuple[NDArrays, int]]) -> NDArrays:
    """Compute weighted average."""
    # Calculate the total number of data volumes used during training
    data_samples_total = sum([data_samples for _, data_samples in results])
    
    if data_samples_total == 0:
        data_samples_total = len(results)

    # Create a list of weights, each multiplied by the related number of data volumes
    weighted_weights = [
        [layer * data_samples for layer in weights] for weights, data_samples in results
    ]

    # Compute average weights of each layer
    weights_prime: NDArrays = [
        reduce(np.add, layer_updates) / data_samples_total
        for layer_updates in zip(*weighted_weights)
    ]
    return weights_prime

def aggregate_fedasync(
    global_model: NDArrays,
    local_model: NDArrays,
    alpha: float,
) -> NDArrays:
    """Aggregate local model using FedAsync"""
    weighted_global_model = [layer * (1 - alpha) for layer in global_model]
    weighted_local_model = [layer * alpha for layer in local_model]
    nd_arrays_list = [weighted_global_model, weighted_local_model]
    new_global_model: NDArrays = [
        reduce(np.add, layer_updates) for layer_updates in zip(*nd_arrays_list)
    ]
    return new_global_model

def weighted_loss_avg(results: List[Tuple[float, int]]) -> float:
    """Aggregate loss obtained from multiple clients."""
    data_samples_total = sum([data_samples for _, data_samples in results])
    weighted_losses = [data_samples * loss for loss, data_samples in results]
    return sum(weighted_losses) / data_samples_total

def weighted_acc_avg(results: List[Tuple[float, int]]) -> float:
    """Aggregate accuracy obtained from multiple clients."""
    data_samples_total = sum([data_samples for _, data_samples in results])
    weighted_accs = [data_samples * acc for acc, data_samples in results]
    return sum(weighted_accs) / data_samples_total
