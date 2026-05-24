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
"""gRPC-based Daisy ClientProxy implementation."""

from typing import Optional, Dict, Union, Callable

from daisyfl.common import FitIns, EvaluateIns, CID
from daisyfl.proto.transport_pb2 import ClientMessage, ServerMessage
from .client_proxy import ClientProxy
from .grpc_bridge import GRPCBridge
from daisyfl.utils.logger import log
from daisyfl.utils import daisyfl_serde
from daisyfl.utils.logger import WARNING, INFO, ERROR

class GrpcClientProxy(ClientProxy):
    """Daisy client proxy which delegates over the network using gRPC."""

    def __init__(
        self,
        cid: str,
        bridge: GRPCBridge,
        metadata_dict: Dict,
    ):
        super().__init__(cid)
        self.bridge = bridge
        self.metadata_dict: Dict = metadata_dict
        self.submit_result = None
        self.bridge.set_submit_client_message_fn(self.submit_client_message)


    def fit(
        self,
        ins: FitIns,
    ) -> None:
        """Refine the provided parameters using the locally held dataset."""
        # label CID
        ins.config[CID] = self.cid
        fit_msg = daisyfl_serde.fit_ins_to_proto(ins)
        self.bridge.request(ServerMessage(fit_ins=fit_msg))

    def evaluate(
        self,
        ins: EvaluateIns,
    ) -> None:
        """Evaluate the provided parameters using the locally held dataset."""
        # label CID
        ins.config[CID] = self.cid
        evaluate_msg = daisyfl_serde.evaluate_ins_to_proto(ins)
        self.bridge.request(ServerMessage(evaluate_ins=evaluate_msg))

    def submit_client_message(
        self, client_message: ClientMessage, roaming,
    ) -> None:
        """Receive, deserialize, and submit a ClientMessage."""
        field = client_message.WhichOneof("msg")
        if field == "fit_res":
            fit_res = daisyfl_serde.fit_res_from_proto(client_message.fit_res)
            self.submit_result((self, fit_res), roaming)
        elif field == "evaluate_res":
            evaluate_res = daisyfl_serde.evaluate_res_from_proto(client_message.evaluate_res)
            self.submit_result((self, evaluate_res), roaming)
        else:
            log(INFO, "Will not return {} type of message to Server".format(field))

    def set_is_pending_fn(self, is_pending: Callable) -> None:
        """Set callback function for checking if the client_proxy is pending."""
        def is_pending_with_cid():
            return is_pending(self.cid)
        self.is_pending: Callable = is_pending_with_cid

    def set_submit_result_fn(self, submit_result: Callable) -> None:
        """Set callback function for submitting a result."""
        self.submit_result = submit_result

    def set_client_status_transition_fn(self, client_status_transition: Callable) -> None:
        """Set callback function for client status transition."""
        self.client_status_transition = client_status_transition
    