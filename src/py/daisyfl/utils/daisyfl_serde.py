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
"""ProtoBuf serialization and deserialization."""


from typing import Any, List, cast

from daisyfl.proto.transport_pb2 import (
    ClientMessage,
    ErrorCode,
    Element,
    Parameters,
    ServerMessage,
    Status,
    InnerMap,
    InnerMapInt,
    InnerList,
)

from daisyfl.common import daisyfl_typing



# === Parameters ===


def parameters_to_proto(parameters: daisyfl_typing.Parameters) -> Parameters:
    """."""
    return Parameters(tensors=parameters.tensors, tensor_type=parameters.tensor_type)


def parameters_from_proto(msg: Parameters) -> daisyfl_typing.Parameters:
    """."""
    tensors: List[bytes] = list(msg.tensors)
    return daisyfl_typing.Parameters(tensors=tensors, tensor_type=msg.tensor_type)


# === Fit messages ===


def fit_ins_to_proto(ins: daisyfl_typing.FitIns) -> ServerMessage.FitIns:
    """Serialize FitIns to ProtoBuf message."""
    parameters_proto = parameters_to_proto(ins.parameters)
    config_msg = inner_map_to_proto(ins.config)
    return ServerMessage.FitIns(parameters=parameters_proto, config=config_msg)


def fit_ins_from_proto(msg: ServerMessage.FitIns) -> daisyfl_typing.FitIns:
    """Deserialize FitIns from ProtoBuf message."""
    parameters = parameters_from_proto(msg.parameters)
    config = inner_map_from_proto(msg.config)
    return daisyfl_typing.FitIns(parameters=parameters, config=config)


def fit_res_to_proto(res: daisyfl_typing.FitRes) -> ClientMessage.FitRes:
    """Serialize FitIns to ProtoBuf message."""
    status_msg = status_to_proto(res.status)
    if res.status.error_code == daisyfl_typing.ErrorCode.FIT_NOT_IMPLEMENTED:
        return ClientMessage.FitRes(status=status_msg)
    parameters_proto = parameters_to_proto(res.parameters)
    config_msg = None if res.config is None else inner_map_to_proto(res.config)
    return ClientMessage.FitRes(
        status=status_msg,
        parameters=parameters_proto,
        config=config_msg,
    )


def fit_res_from_proto(msg: ClientMessage.FitRes) -> daisyfl_typing.FitRes:
    """Deserialize FitRes from ProtoBuf message."""
    status = status_from_proto(msg=msg.status)
    parameters = parameters_from_proto(msg.parameters)
    config = None if msg.config is None else inner_map_from_proto(msg.config)
    return daisyfl_typing.FitRes(
        status=status,
        parameters=parameters,
        config=config,
    )


# === Status ===


def status_to_proto(status: daisyfl_typing.Status) -> Status:
    """Serialize ErrorCode to ProtoBuf message."""
    error_code = ErrorCode.OK
    if status.error_code == daisyfl_typing.ErrorCode.FIT_NOT_IMPLEMENTED:
        error_code = ErrorCode.FIT_NOT_IMPLEMENTED
    if status.error_code == daisyfl_typing.ErrorCode.EVALUATE_NOT_IMPLEMENTED:
        error_code = ErrorCode.EVALUATE_NOT_IMPLEMENTED
    return Status(error_code=error_code, message=status.message)


def status_from_proto(msg: Status) -> daisyfl_typing.Status:
    """Deserialize ErrorCode from ProtoBuf message."""
    error_code = daisyfl_typing.ErrorCode.OK
    if msg.error_code == ErrorCode.FIT_NOT_IMPLEMENTED:
        error_code = daisyfl_typing.ErrorCode.FIT_NOT_IMPLEMENTED
    if msg.error_code == ErrorCode.EVALUATE_NOT_IMPLEMENTED:
        error_code = daisyfl_typing.ErrorCode.EVALUATE_NOT_IMPLEMENTED
    return daisyfl_typing.Status(error_code=error_code, message=msg.message)


# === Evaluate messages ===


def evaluate_ins_to_proto(ins: daisyfl_typing.EvaluateIns) -> ServerMessage.EvaluateIns:
    """Serialize EvaluateIns to ProtoBuf message."""
    parameters_proto = parameters_to_proto(ins.parameters)
    config_msg = inner_map_to_proto(ins.config)
    return ServerMessage.EvaluateIns(parameters=parameters_proto, config=config_msg)


def evaluate_ins_from_proto(msg: ServerMessage.EvaluateIns) -> daisyfl_typing.EvaluateIns:
    """Deserialize EvaluateIns from ProtoBuf message."""
    parameters = parameters_from_proto(msg.parameters)
    config = inner_map_from_proto(msg.config)
    return daisyfl_typing.EvaluateIns(parameters=parameters, config=config)


def evaluate_res_to_proto(res: daisyfl_typing.EvaluateRes) -> ClientMessage.EvaluateRes:
    """Serialize EvaluateIns to ProtoBuf message."""
    status_msg = status_to_proto(res.status)
    if res.status.error_code == daisyfl_typing.ErrorCode.EVALUATE_NOT_IMPLEMENTED:
        return ClientMessage.EvaluateRes(status=status_msg)
    config_msg = None if res.config is None else inner_map_to_proto(res.config)
    return ClientMessage.EvaluateRes(
        status=status_msg,
        config=config_msg,
    )


def evaluate_res_from_proto(msg: ClientMessage.EvaluateRes) -> daisyfl_typing.EvaluateRes:
    """Deserialize EvaluateRes from ProtoBuf message."""
    status = status_from_proto(msg=msg.status)
    config = None if msg.config is None else inner_map_from_proto(msg.config)
    return daisyfl_typing.EvaluateRes(
        status=status,
        config=config,
    )


#  === ClientStatus ===


def client_status_to_proto(cs: daisyfl_typing.ClientStatus) -> ClientMessage.ClientStatus:
    """Serialize ClientStatus to ProtoBuf message."""
    return ClientMessage.ClientStatus(status=cs.status)


def client_status_from_proto(msg: ClientMessage.ClientStatus) -> daisyfl_typing.ClientStatus:
    """Deserialize ProtoBuf message to ClientStatus."""
    return daisyfl_typing.ClientStatus(status=msg.status)


# === ServerStatus ===


def server_status_to_proto(ss: daisyfl_typing.ServerStatus) -> ServerMessage.ServerStatus:
    """Serialize ServerStatus to ProtoBuf message."""
    return ServerMessage.ServerStatus(status=ss.status)


def server_status_from_proto(msg: ServerMessage.ServerStatus) -> daisyfl_typing.ServerStatus:
    """Deserialize ProtoBuf message to ServerStatus."""
    return daisyfl_typing.ServerStatus(status=msg.status)


# === SRS, CUS, CRS, RTS ===


def server_received_signal_to_proto(ins: daisyfl_typing.ServerReceivedSignal) -> ServerMessage.ServerReceivedSignal:
    """Serialize SRS to ProtoBuf message."""
    status_proto = status_to_proto(ins.status)
    return ServerMessage.ServerReceivedSignal(status=status_proto)


def server_received_signal_from_proto(msg: ServerMessage.ServerReceivedSignal) -> daisyfl_typing.ServerReceivedSignal:
    """Deserialize ProtoBuf message to SRS"""
    status = status_from_proto(msg.status)
    return daisyfl_typing.ServerReceivedSignal(status=status)


def client_uploading_signal_to_proto(res: daisyfl_typing.ClientUploadingSignal) -> ClientMessage.ClientUploadingSignal:
    """Serialize CUS to ProtoBuf message."""
    status_proto = status_to_proto(res.status)
    return ClientMessage.ClientUploadingSignal(status=status_proto)


def client_uploading_signal_from_proto(msg: ClientMessage.ClientUploadingSignal) -> daisyfl_typing.ClientUploadingSignal:
    """Deserialize ProtoBuf message to CUS"""
    status = status_from_proto(msg.status)
    return daisyfl_typing.ClientUploadingSignal(status=status)


def client_roaming_signal_to_proto(res: daisyfl_typing.ClientRoamingSignal) -> ClientMessage.ClientRoamingSignal:
    """Serialize CRS to ProtoBuf message."""
    status_proto = status_to_proto(res.status)
    return ClientMessage.ClientRoamingSignal(status=status_proto)


def client_roaming_signal_from_proto(msg: ClientMessage.ClientRoamingSignal) -> daisyfl_typing.ClientRoamingSignal:
    """Deserialize ProtoBuf message to CRS"""
    status = status_from_proto(msg.status)
    return daisyfl_typing.ClientRoamingSignal(status=status)


def roaming_termination_signal_to_proto(res: daisyfl_typing.RoamingTerminationSignal) -> ClientMessage.RoamingTerminationSignal:
    """Serialize RTS to ProtoBuf message."""
    status_proto = status_to_proto(res.status)
    return ClientMessage.RoamingTerminationSignal(status=status_proto)


def roaming_termination_signal_from_proto(msg: ClientMessage.RoamingTerminationSignal) -> daisyfl_typing.RoamingTerminationSignal:
    """Deserialize ProtoBuf message to RTS"""
    status = status_from_proto(msg.status)
    return daisyfl_typing.RoamingTerminationSignal(status=status)


# === Shutdown ===


def shutdown_to_proto(shutdown_signal: daisyfl_typing.Shutdown) -> ClientMessage.Shutdown:
    """Serialize Shutdown to ProtoBuf message."""
    status_proto = status_to_proto(shutdown_signal.status)
    return ClientMessage.Shutdown(status=status_proto)


# === Element messages ===


def element_to_proto(element: daisyfl_typing.Element) -> Element:

    if isinstance(element, bool):
        return Element(bool=element)

    if isinstance(element, bytes):
        return Element(bytes=element)

    if isinstance(element, float):
        return Element(double=element)

    if isinstance(element, int):
        return Element(sint64=element)

    if isinstance(element, str):
        return Element(string=element)
    
    if (isinstance(element, dict)):
        keys = list(element.keys())
        if len(keys) > 0 and type(keys[0]) == int:
            return Element(inner_map_int=inner_map_int_to_proto(element))
        return Element(inner_map=inner_map_to_proto(element))
    
    if (isinstance(element, List)):
        return Element(inner_list=inner_list_to_proto(element))

    raise Exception(
        f"Accepted types: {bool, bytes, float, int, str, dict, List} (but not {type(element)})"
    )


def element_from_proto(element_msg: Element) -> daisyfl_typing.Element:
    """Deserialize... ."""
    element_field = element_msg.WhichOneof("element")
    element = getattr(element_msg, cast(str, element_field))
    if type(cast(daisyfl_typing.Element, element)) is InnerMap:
        inner_map_msg = cast(daisyfl_typing.Element, element)
        return inner_map_from_proto(inner_map_msg)
    elif type(cast(daisyfl_typing.Element, element)) is InnerMapInt:
        inner_map_int_msg = cast(daisyfl_typing.Element, element)
        return inner_map_int_from_proto(inner_map_int_msg)
    elif type(cast(daisyfl_typing.Element, element)) is InnerList:
        inner_list_msg = cast(daisyfl_typing.Element, element)
        return inner_list_from_proto(inner_list_msg)
    return cast(daisyfl_typing.Element, element)


# === InnerMap messages ===


def inner_map_to_proto(inner_map: Any) -> InnerMap:
    """Serialize... ."""
    proto = {}
    for key in inner_map:
        proto[key] = element_to_proto(inner_map[key])
    return InnerMap(inner_map=proto)


def inner_map_from_proto(inner_map_msg: InnerMap) -> Any:
    """Deserialize... ."""
    inner_map_field = cast(str, InnerMap.DESCRIPTOR.fields[0].name)
    proto = getattr(inner_map_msg, inner_map_field)
    inner_map = {}
    for key in proto:
        inner_map[key] = element_from_proto(proto[key])
    return inner_map


# === InnerMapInt messages ===


def inner_map_int_to_proto(inner_map_int: Any) -> InnerMapInt:
    """Serialize... ."""
    proto = {}
    for key in inner_map_int:
        proto[key] = element_to_proto(inner_map_int[key])
    return InnerMapInt(inner_map_int=proto)


def inner_map_int_from_proto(inner_map_int_msg: InnerMapInt) -> Any:
    """Deserialize... ."""
    inner_map_int_field = cast(str, InnerMapInt.DESCRIPTOR.fields[0].name)
    proto = getattr(inner_map_int_msg, inner_map_int_field)
    inner_map_int = {}
    for key in proto:
        inner_map_int[key] = element_from_proto(proto[key])
    return inner_map_int


# === InnerList messages ===


def inner_list_to_proto(inner_list: Any) -> InnerMap:
    """Serialize... ."""
    proto = []
    for i in range(len(inner_list)):
        proto.append(element_to_proto(inner_list[i]))
    return InnerList(inner_list=proto)


def inner_list_from_proto(inner_list_msg: InnerList) -> Any:
    """Deserialize... ."""
    inner_list_field = cast(str, InnerList.DESCRIPTOR.fields[0].name)
    proto = getattr(inner_list_msg, inner_list_field)
    inner_list = []
    for i in range(len(proto)):
        inner_list.append(element_from_proto(proto[i]))
    return inner_list

