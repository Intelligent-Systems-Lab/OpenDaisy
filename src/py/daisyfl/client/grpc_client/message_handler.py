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
"""Handle server messages by calling appropriate client methods."""

from daisyfl.client.client_operator_launcher import ClientOperatorLauncher
from daisyfl.utils import daisyfl_serde
from daisyfl.proto.transport_pb2 import ClientMessage, ServerMessage
from daisyfl.common import CURRENT_ROUND, METRICS, CID
from daisyfl.utils.logger import log, WARNING

class UnknownServerMessage(Exception):
    """Signifies that the received message is unknown."""


def handle(
    server_msg: ServerMessage,
    client_operator_launcher: ClientOperatorLauncher
) -> ClientMessage:
    """Handle incoming messages from the server."""
    field = server_msg.WhichOneof("msg")
    if field == "fit_ins":
        return _fit(server_msg.fit_ins, client_operator_launcher)
    if field == "evaluate_ins":
        return _evaluate(server_msg.evaluate_ins, client_operator_launcher)
    raise UnknownServerMessage()


def _fit(fit_msg: ServerMessage.FitIns, client_operator_launcher: ClientOperatorLauncher) -> ClientMessage:
    # Deserialize fit instruction
    fit_ins = daisyfl_serde.fit_ins_from_proto(fit_msg)
    # Perform fit
    fit_res = client_operator_launcher.fit(fit_ins)

    if not fit_res.config.__contains__(CURRENT_ROUND):
        log(
            WARNING,
            "Configuration of FitRes doesn't contain \"CURRENT_ROUND\". \"CURRENT_ROUND\" in FitIns will be used in FitRes."
        )
        fit_res.config[CURRENT_ROUND] = fit_ins.config[CURRENT_ROUND]
    if not fit_res.config.__contains__(METRICS):
        log(
            WARNING,
            "Configuration of FitRes doesn't contain \"METRICS\". An empty dicationary will be used in FitRes."
        )
        fit_res.config[METRICS] = {}
    if not fit_res.config.__contains__(CID):
        log(
            WARNING,
            "Configuration of FitRes doesn't contain \"CID\". \"CID\" in FitIns will be used in FitRes."
        )
        fit_res.config[CID] = fit_ins.config[CID]
    
    # Serialize fit result
    fit_res_proto = daisyfl_serde.fit_res_to_proto(fit_res)
    return ClientMessage(fit_res=fit_res_proto)


def _evaluate(evaluate_msg: ServerMessage.EvaluateIns, client_operator_launcher: ClientOperatorLauncher) -> ClientMessage:
    # Deserialize evaluate instruction
    evaluate_ins = daisyfl_serde.evaluate_ins_from_proto(evaluate_msg)
    # Perform evaluation
    evaluate_res = client_operator_launcher.evaluate(evaluate_ins)
    
    if not evaluate_res.config.__contains__(CURRENT_ROUND):
        log(
            WARNING,
            "Configuration of EvaluateRes doesn't contain \"CURRENT_ROUND\". \"CURRENT_ROUND\" in EvaluateIns will be used in EvaluateRes."
        )
        evaluate_res.config[CURRENT_ROUND] = evaluate_ins.config[CURRENT_ROUND]
    if not evaluate_res.config.__contains__(METRICS):
        log(
            WARNING,
            "Configuration of EvaluateRes doesn't contain \"METRICS\". An empty dicationary will be used in EvaluateRes."
        )
        evaluate_res.config[METRICS] = {}
    if not evaluate_res.config.__contains__(CID):
        log(
            WARNING,
            "Configuration of EvaluateRes doesn't contain \"CID\". \"CID\" in EvaluateIns will be used in EvaluateRes."
        )
        evaluate_res.config[CID] = evaluate_ins.config[CID]
    
    # Serialize evaluate result
    evaluate_res_proto = daisyfl_serde.evaluate_res_to_proto(evaluate_res)
    return ClientMessage(evaluate_res=evaluate_res_proto)

