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

from typing import Tuple, Dict
from .logger import log
from daisyfl.utils.logger import WARNING, ERROR
from daisyfl.common import ANCHOR, HANDOVER, CID


reserved = [ANCHOR, HANDOVER]
required = [CID]

def metadata_to_dict(
    metadata: Tuple,
    check_reserved: bool = True,
    check_required: bool = True,
) -> Dict:
    """
    Transform a metadata to dictionary and
    check the reserved words and the required words.
    """
    if not isinstance(metadata[0], Tuple):
        log(WARNING, "A metadata must be ((key, value),).")
        log(WARNING, "Transform metadata to correct format.")
        metadata = (metadata,)

    dict = {}
    redundant = False
    for m in metadata:
        # m is not null
        if len(m) >= 2:
            if m[0] in dict:
                redundant = True
            dict[m[0]] = m[1]
    # check reserved words
    if check_reserved:
        for word in reserved:
            if dict.__contains__(word):
                log(WARNING, "\"{}\" is a reserved word.".format(word))
    # check required words
    if check_required:
        for word in required:
            if not dict.__contains__(word):
                log(ERROR, "\"{}\" is a required word but isn't defined".format(word))
    if redundant:
        log(WARNING, "Some keys was redundantly defined.")
    return dict

def dict_to_metadata(dict: Dict) -> Tuple:
    """Transform a dictionary to metadata."""
    l = []
    for key in dict.keys():
        l.append((key, dict[key]))
    return tuple(l)
