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
"""Daisy client (abstract base class)."""


from abc import ABC, abstractmethod
from typing import Optional, Union, Callable

from daisyfl.common import (
    EvaluateIns,
    EvaluateRes,
    FitIns,
    FitRes,
)
from daisyfl.proto.transport_pb2 import ClientMessage


class ClientProxy(ABC):
    """Abstract base class for Daisy client proxies."""

    def __init__(self, cid: str):
        self.cid = cid

    @abstractmethod
    def fit(
        self,
        ins: FitIns,
    ) -> None:
        """Refine the provided parameters using the locally held dataset."""

    @abstractmethod
    def evaluate(
        self,
        ins: EvaluateIns,
    ) -> None:
        """Evaluate the provided parameters using the locally held dataset."""

    @abstractmethod
    def submit_client_message(
        self,
        client_message: ClientMessage,
    ) -> None:
        """Receive, deserialize, and submit a ClientMessage."""

    @abstractmethod
    def set_is_pending_fn(self, is_pending: Callable) -> None:
        """Set callback function for checking if the client_proxy is pending."""

    @abstractmethod
    def set_submit_result_fn(self, submit_result: Callable) -> None:
        """Set callback function for submitting a result."""

    @abstractmethod
    def set_client_status_transition_fn(self, client_status_transition: Callable) -> None:
        """Set callback function for client status transition."""
    