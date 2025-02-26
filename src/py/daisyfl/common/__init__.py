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
"""Daisy common variables, types, and modules."""


from .const import ACCURACY as ACCURACY
from .const import CLIENT_FAIL as CLIENT_FAIL
from .const import CLIENT_HANDLING as CLIENT_HANDLING
from .const import CLIENT_IDLING as CLIENT_IDLING
from .const import CLIENT_OPERATOR as CLIENT_OPERATOR
from .const import CLIENT_ROAM as CLIENT_ROAM
from .const import CURRENT_ROUND as CURRENT_ROUND
from .const import CURRENT_ROUND_MASTER as CURRENT_ROUND_MASTER
from .const import CURRENT_ROUND_ZONE as CURRENT_ROUND_ZONE
from .const import EVALUATE as EVALUATE
from .const import EVALUATE_INIT_MODEL_MASTER as EVALUATE_INIT_MODEL_MASTER
from .const import EVALUATE_INTERVAL as EVALUATE_INTERVAL
from .const import DATA_SAMPLES as DATA_SAMPLES
from .const import LOSS as LOSS
from .const import MASTER_METRICS_HANDLER as MASTER_METRICS_HANDLER
from .const import MASTER_SERVER_OPERATOR as MASTER_SERVER_OPERATOR
from .const import MASTER_STRATEGY as MASTER_STRATEGY
from .const import METRICS as METRICS
from .const import METRICS_HANDLERS as METRICS_HANDLERS
from .const import MIN_WAITING_TIME as MIN_WAITING_TIME
from .const import MIN_WAITING_TIME_MASTER as MIN_WAITING_TIME_MASTER
from .const import MIN_WAITING_TIME_ZONE as MIN_WAITING_TIME_ZONE
from .const import MODEL_PATH as MODEL_PATH
from .const import NUM_ROUNDS as NUM_ROUNDS
from .const import OPERATORS as OPERATORS
from .const import SAVE_MODEL as SAVE_MODEL
from .const import SERVER_WAITING as SERVER_WAITING
from .const import SERVER_IDLING as SERVER_IDLING
from .const import STRATEGIES as STRATEGIES
from .const import TID as TID
from .const import ZONE_COMM_FREQUENCY as ZONE_COMM_FREQUENCY
from .const import ZONE_METRICS_HANDLER as ZONE_METRICS_HANDLER
from .const import ZONE_SERVER_OPERATOR as ZONE_SERVER_OPERATOR
from .const import ZONE_STRATEGY as ZONE_STRATEGY
from .const import ANCHOR as ANCHOR
from .const import CID as CID
from .const import HANDOVER as HANDOVER
from .const import UPLINK_CERTIFICATES as UPLINK_CERTIFICATES
from .daisyfl_typing import ErrorCode as ErrorCode
from .daisyfl_typing import EvaluateIns as EvaluateIns
from .daisyfl_typing import EvaluateRes as EvaluateRes
from .daisyfl_typing import FitIns as FitIns
from .daisyfl_typing import FitRes as FitRes
from .daisyfl_typing import ClientStatus as ClientStatus
from .daisyfl_typing import ServerReceivedSignal as ServerReceivedSignal
from .daisyfl_typing import ClientUploadingSignal as ClientUploadingSignal
from .daisyfl_typing import ServerStatus as ServerStatus
from .daisyfl_typing import ClientRoamingSignal as ClientRoamingSignal
from .daisyfl_typing import RoamingTerminationSignal as RoamingTerminationSignal
from .daisyfl_typing import Shutdown as Shutdown
from .daisyfl_typing import Metrics as Metrics
from .daisyfl_typing import MetricsAggregationFn as MetricsAggregationFn
from .daisyfl_typing import NDArray as NDArray
from .daisyfl_typing import NDArrays as NDArrays
from .daisyfl_typing import Parameters as Parameters
from .daisyfl_typing import Scalar as Scalar
from .daisyfl_typing import Element as Element
from .daisyfl_typing import Status as Status
from .daisyfl_typing import Task as Task
from .daisyfl_typing import Report as Report
from .daisyfl_typing import NodeType as NodeType
from .daisyfl_typing import SubtaskStatus as SubtaskStatus


GRPC_MAX_MESSAGE_LENGTH: int = 536_870_912  # == 512 * 1024 * 1024


__all__ = [
    "GRPC_MAX_MESSAGE_LENGTH",
    "ANCHOR",
    "CID",
    "HANDOVER",
    "ErrorCode",
    "EvaluateIns",
    "EvaluateRes",
    "FitIns",
    "FitRes",
    "ClientStatus",
    "ServerReceivedSignal",
    "ClientUploadingSignal",
    "ServerStatus",
    "ClientRoamingSignal",
    "RoamingTerminationSignal",
    "Shutdown",
    "Metrics",
    "MetricsAggregationFn",
    "NDArray",
    "NDArrays",
    "Parameters",
    "Scalar",
    "Element",
    "Status",
    "Task",
    "Report",
    "NodeType",
    "SubtaskStatus",
    "ACCURACY",
    "CLIENT_FAIL",
    "CLIENT_HANDLING",
    "CLIENT_IDLING",
    "CLIENT_OPERATOR",
    "CLIENT_ROAM",
    "CURRENT_ROUND",
    "CURRENT_ROUND_MASTER",
    "CURRENT_ROUND_ZONE",
    "EVALUATE",
    "EVALUATE_INIT_MODEL_MASTER",
    "EVALUATE_INTERVAL",
    "DATA_SAMPLES",
    "LOSS",
    "MASTER_METRICS_HANDLER",
    "MASTER_SERVER_OPERATOR",
    "MASTER_STRATEGY",
    "METRICS",
    "METRICS_HANDLERS",
    "MIN_WAITING_TIME",
    "MIN_WAITING_TIME_MASTER",
    "MIN_WAITING_TIME_ZONE",
    "MODEL_PATH",
    "NUM_ROUNDS",
    "OPERATORS",
    "SAVE_MODEL",
    "SERVER_WAITING",
    "SERVER_IDLING",
    "STRATEGIES",
    "TID",
    "UPLINK_CERTIFICATES",
    "ZONE_COMM_FREQUENCY",
    "ZONE_METRICS_HANDLER",
    "ZONE_SERVER_OPERATOR",
    "ZONE_STRATEGY",
]
