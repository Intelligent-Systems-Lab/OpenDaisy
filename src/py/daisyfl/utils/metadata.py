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
"""Utilities for converting between gRPC metadata tuples and dictionaries."""

from typing import Dict, Tuple

from daisyfl.common import ANCHOR, CID, HANDOVER
from daisyfl.utils.logger import ERROR, WARNING

from .logger import log

reserved = [ANCHOR, HANDOVER]
required = [CID]


def metadata_to_dict(
    metadata: Tuple,
    check_reserved: bool = True,
    check_required: bool = True,
) -> Dict:
    """Transform a metadata to dictionary and check the reserved words and the required words."""
    if not isinstance(metadata[0], Tuple):
        log(WARNING, "A metadata must be ((key, value),).")
        log(WARNING, "Transform metadata to correct format.")
        metadata = (metadata,)

    metadata_dict = {}
    redundant = False
    for m in metadata:
        # m is not null
        if len(m) >= 2:
            if m[0] in metadata_dict:
                redundant = True
            metadata_dict[m[0]] = m[1]
    # check reserved words
    if check_reserved:
        for word in reserved:
            if metadata_dict.__contains__(word):
                log(WARNING, '"%s" is a reserved word.', word)
    # check required words
    if check_required:
        for word in required:
            if not metadata_dict.__contains__(word):
                log(ERROR, '"%s" is a required word but isn\'t defined', word)
    if redundant:
        log(WARNING, "Some keys was redundantly defined.")
    return metadata_dict


def dict_to_metadata(data_dict: Dict) -> Tuple:
    """Transform a dictionary to metadata."""
    l = []
    for key in data_dict.keys():
        l.append((key, data_dict[key]))
    return tuple(l)
