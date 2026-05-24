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
"""Common types and class for secure aggregation."""


from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import Dict, List
from enum import Enum

# check stage
PROTO_KEY = "PROTO_KEY"
# stage 0 ins
SEC_AGG_PARAM_DICT = "SEC_AGG_PARAM_DICT"
# stage 1 res
PUBLIC_KEYS = "PUBLIC_KEYS"
# stage 2 ins
PUBLIC_KEYS_LIST = "PUBLIC_KEYS_LIST"
# stage 2 res
SHARE_KEYS_PACKETS = "SHARE_KEYS_PACKETS"
# stage 3 ins
FORWARD_PACKETS = "FORWARD_PACKETS"
# stage 4 ins
SHARE_REQUEST = "SHARE_REQUEST"
# stage 4 res
SHARE_RESPONSE = "SHARE_RESPONSE" 


class Proto(Enum):
    """Type of the SecAgg stages."""
    
    SETUP = 0
    ASK_KEYS = 1
    SHARE_KEYS = 2
    ASK_VECTORS = 3
    UNMASK_VECTORS = 4

@dataclass_json
@dataclass
class PublicKeys:
    pk1: bytes
    pk2: bytes

@dataclass_json
@dataclass
class ShareKeysPacket:
    source: int
    destination: int
    ciphertext: bytes

@dataclass_json
@dataclass
class ShareRequest:
    survivals: List[int]
    dropouts: List[int]
    
@dataclass_json
@dataclass
class ShareResponse:
    share_dict: Dict[int, bytes]