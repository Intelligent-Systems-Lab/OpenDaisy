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
"""Parameter conversion."""


from io import BytesIO
from typing import cast

import numpy as np

from daisyfl.common.daisyfl_typing import NDArray, NDArrays, Parameters


def ndarrays_to_parameters(ndarrays: NDArrays) -> Parameters:
    """Convert NumPy ndarrays to parameters object."""
    tensors = [ndarray_to_bytes(ndarray) for ndarray in ndarrays]
    return Parameters(tensors=tensors, tensor_type="numpy.ndarray")


def parameters_to_ndarrays(parameters: Parameters) -> NDArrays:
    """Convert parameters object to NumPy ndarrays."""
    return [bytes_to_ndarray(tensor) for tensor in parameters.tensors]


def ndarray_to_bytes(ndarray: NDArray) -> bytes:
    """Serialize NumPy ndarray to bytes."""
    bytes_io = BytesIO()
    # WARNING: NEVER set allow_pickle to true.
    # Reason: loading pickled data can execute arbitrary code
    # Source: https://numpy.org/doc/stable/reference/generated/numpy.save.html
    np.save(bytes_io, ndarray, allow_pickle=False)  # type: ignore
    return bytes_io.getvalue()


def bytes_to_ndarray(tensor: bytes) -> NDArray:
    """Deserialize NumPy ndarray from bytes."""
    bytes_io = BytesIO(tensor)
    # WARNING: NEVER set allow_pickle to true.
    # Reason: loading pickled data can execute arbitrary code
    # Source: https://numpy.org/doc/stable/reference/generated/numpy.load.html
    ndarray_deserialized = np.load(bytes_io, allow_pickle=False)  # type: ignore
    return cast(NDArray, ndarray_deserialized)

def encode_ndarrays(weights: NDArrays) -> str:
    """Encode NDArrays to str."""
    en_weights = ""
    num_layers = len(weights)
    en_weights = en_weights + str(num_layers) + '[nlayers]'
    for j in range(num_layers):
        shape = ""
        for k in range(len(weights[j].shape)):
            shape = shape + str(np.float64(weights[j].shape[k]))
            if k != (len(weights[j].shape) - 1):
                shape = shape + ','
        reshaped = weights[j].reshape(-1)
        w_layer = ""
        for m in range(len(reshaped)):
            w_layer = w_layer + str(reshaped[m])
            if m != (len(reshaped)-1):
                 w_layer = w_layer + " "

        layer_info = shape + '[shape]' + w_layer
        if j != num_layers-1:
            en_weights = en_weights + layer_info + '[layer_info]'
        else:
            en_weights = en_weights + layer_info
    return en_weights

def decode_ndarrays(parameter: str) -> NDArrays:
    """Decode str to NDArrays."""
    weight_result_list = list()
    num_layers, l = parameter.split("[nlayers]")
    all_layer_info = l.split("[layer_info]") 
    for j in range(int(num_layers)):
        shape, w_layer = all_layer_info[j].split("[shape]")
        if "," in shape:
            shape_list = shape.split(',')
            for k in range(len(shape_list)):
                shape_list[k] = int(float(shape_list[k]))
            shape = tuple(shape_list)
        else:    
            shape = (int(float(shape)), )
        
        w_layer_list = w_layer.split(" ")
        weight = np.ndarray(shape=(0), dtype=float)
        for m in range(len(w_layer_list)):
            weight = np.append(weight, np.array([np.float64(w_layer_list[m])]))
        weight = np.reshape(weight, shape)
        weight_result_list.append(weight)
    return weight_result_list