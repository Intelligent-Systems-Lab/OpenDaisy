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
"""Daisy type definitions."""


from dataclasses import dataclass
from dataclasses_json import dataclass_json
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from threading import Condition
import numpy.typing as npt

NDArray = npt.NDArray[Any]
NDArrays = List[NDArray]

# The following union type contains Python types corresponding to ProtoBuf types that
# ProtoBuf considers to be "Scalar Value Types", even though some of them arguably do
# not conform to other definitions of what a scalar is. Source:
# https://developers.google.com/protocol-buffers/docs/overview#scalar
Scalar = Union[bool, bytes, float, int, str]

Metrics = Dict[str, Scalar]

Element = Union[Scalar, Dict, None]

MetricsAggregationFn = Callable[[List[Tuple[int, Metrics]]], Metrics]


class ErrorCode(Enum):
    """Status codes tagged on ClientMessage."""

    OK = 0
    FIT_NOT_IMPLEMENTED = 1
    EVALUATE_NOT_IMPLEMENTED = 2
    ROAMING_FAILED = 3


@dataclass
class Status:
    """Status code with a message tagged on ClientMessage."""

    error_code: ErrorCode
    message: str


@dataclass
class Parameters:
    """Model parameters."""

    tensors: List[bytes]
    tensor_type: str


@dataclass
class FitIns:
    """Fit instructions for a client or zone."""

    parameters: Parameters
    config: Dict


@dataclass
class FitRes:
    """Fit response from a client or zone."""

    status: Status
    parameters: Parameters
    config: Dict


@dataclass
class EvaluateIns:
    """Evaluate instructions for a client or zone."""

    parameters: Parameters
    config: Dict


@dataclass
class EvaluateRes:
    """Evaluate response from a client or zone."""

    status: Status
    config: Dict


@dataclass
class Task:
    """Task configurations are parsed and structured as this class."""
    config: Dict


@dataclass
class Report:
    """Report is used to notify TaskManager that a subtask is finished."""
    config: Dict

class NodeType(Enum):
    """Types of Daisy node."""

    MASTER = 1
    ZONE = 2
    # CLIENT = 3


@dataclass
class SubtaskStatus:
    """
    Data structure to record the status of a subtask.
    Checking SubtaskStatus, we can determine if ServerOperators
    continuously wait for a subtask.
    """
    participant_num: int
    success_num: int
    failure_num: int
    roaming_num: int
    cnd: Condition


@dataclass
class ClientStatus:
    """Data structure used to synchronize the both sides of gRPC agents."""
    status: str


@dataclass
class ServerStatus:
    """Data structure used to synchronize the both sides of gRPC agents."""
    status: str


@dataclass
class ServerReceivedSignal:
    """Data structure used as an Ack to notify the client-side of gRPC agents."""
    status: Status


@dataclass
class ClientUploadingSignal:
    """Data structure used to require result uploading."""
    status: Status


@dataclass
class ClientRoamingSignal:
    """Data structure used to notify the anchor zone that a client roamed."""
    status: Status

@dataclass
class RoamingTerminationSignal:
    """Data structure used to notify the anchor and terminate the temporary connection."""
    status: Status

@dataclass
class Shutdown:
    """Data structure used to shutdown a Daisy node."""
    status: Status

