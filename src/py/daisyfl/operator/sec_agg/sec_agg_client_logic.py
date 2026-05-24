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
from typing import Dict, List, Tuple, Callable
from daisyfl.common import (
    Status,
    ErrorCode,
    FitIns,
    FitRes,
    EvaluateIns,
    EvaluateRes,
    NDArrays,
    DATA_SAMPLES,
    METRICS,
)
from .common import (
    PROTO_KEY,
    SEC_AGG_PARAM_DICT,
    PUBLIC_KEYS,
    PUBLIC_KEYS_LIST,
    SHARE_KEYS_PACKETS,
    FORWARD_PACKETS,
    SHARE_REQUEST,
    SHARE_RESPONSE,
    Proto,
    PublicKeys,
    ShareKeysPacket,
    ShareRequest,
    ShareResponse,
)
from daisyfl.utils.logger import log
from daisyfl.utils.parameter import ndarrays_to_parameters, parameters_to_ndarrays
from daisyfl.utils.logger import DEBUG, ERROR, INFO, WARNING
from ..client_logic import ClientLogic
from . import primitives

class SecAggClientLogic(ClientLogic):
    """Daisy Client operational logic definition of secure aggregation."""
    
    def __init__(self, trainer, get_anchor_fn: Callable, handover_fn: Callable) -> None:
        self.trainer = trainer
        self.get_anchor_fn = get_anchor_fn
        self.handover_fn = handover_fn
    
    def fit(
        self, ins: FitIns,
    ) -> FitRes:
        """Define the operation before and after client fit the local model."""
        stage = Proto(ins.config[PROTO_KEY])
        if stage == Proto.SETUP:
            return setup_param(self, ins)
        elif stage == Proto.ASK_KEYS:
            return ask_keys(self, ins)
        elif stage == Proto.SHARE_KEYS:
            return share_keys(self, ins)
        elif stage == Proto.ASK_VECTORS:
            return ask_vectors(self, ins)
        elif stage == Proto.UNMASK_VECTORS:
            return unmask_vectors(self, ins)
        else:
            raise ValueError("Invalid stage Proto received") 

    def evaluate(
        self, ins: EvaluateIns,
    ) -> EvaluateRes:
        """Define the operation before and after client evaluate the local model."""
        return self.trainer.evaluate(ins)


def setup_param(client_logic: ClientLogic, ins: FitIns) -> FitRes:
    """Step 0: Setup parameters of secure aggregation."""
    # Assigning parameter values to object fields
    sec_agg_param_dict = ins.config[SEC_AGG_PARAM_DICT]
    client_logic.participant_num = sec_agg_param_dict['participant_num']
    client_logic.sec_agg_id = sec_agg_param_dict['sec_agg_id']
    client_logic.share_num = sec_agg_param_dict['share_num']
    client_logic.threshold = sec_agg_param_dict['threshold']
    client_logic.clipping_range = sec_agg_param_dict['clipping_range']
    client_logic.target_range = sec_agg_param_dict['target_range']
    client_logic.mod_range = sec_agg_param_dict['mod_range']
    client_logic.max_weights_factor = sec_agg_param_dict['max_weights_factor']

    # key is another client's id
    # value is the secret share we possess that contributes to the client's secret (bytes)
    client_logic.b_share_dict = {}
    client_logic.sk1_share_dict = {}
    client_logic.shared_key_2_dict = {}
    log(INFO, "SecAgg Stage 0 Completed: Parameters Set Up")
    return FitRes(
        status=Status(error_code=ErrorCode.OK, message="Success"),
        parameters=ins.parameters,
        config={},
    )


def ask_keys(client_logic: ClientLogic, ins: FitIns) -> FitRes:
    """Step 1: Ask the public keys."""
    # Create 2 sets private public key pairs
    # One for creating pairwise masks
    # One for encrypting message to distribute shares
    client_logic.sk1, client_logic.pk1 = primitives.generate_key_pairs()
    client_logic.sk2, client_logic.pk2 = primitives.generate_key_pairs()
    log(INFO, "SecAgg Stage 1 Completed: Created Key Pairs")
    config = {}
    config[PUBLIC_KEYS] = PublicKeys(
        pk1=primitives.public_key_to_bytes(client_logic.pk1),
        pk2=primitives.public_key_to_bytes(client_logic.pk2),
    ).to_dict()

    return FitRes(
        status=Status(error_code=ErrorCode.OK, message="Success"),
        parameters=ins.parameters,
        config=config,
    )


def share_keys(client_logic: ClientLogic, ins: FitIns) -> FitRes:
    """Step 2: Share the public keys."""
    # Distribute shares for private mask seed and first private key
    client_logic.public_keys_dict = ins.config[PUBLIC_KEYS_LIST]
    # check size is larger than threshold
    if len(client_logic.public_keys_dict) < client_logic.threshold:
        raise Exception("Available neighbours number smaller than threshold")
    # check if all public keys received are unique
    pk_list: List[bytes] = []
    for i in client_logic.public_keys_dict.values():
        pk_list.append(i["pk1"])
        pk_list.append(i["pk2"])
    if len(set(pk_list)) != len(pk_list):
        raise Exception("Some public keys are identical")
    # sanity check that own public keys are correct in dict
    if client_logic.public_keys_dict[client_logic.sec_agg_id]["pk1"] != primitives.public_key_to_bytes(client_logic.pk1) \
        or client_logic.public_keys_dict[client_logic.sec_agg_id]["pk2"] != primitives.public_key_to_bytes(client_logic.pk2):
        raise Exception(
            "Own public keys are displayed in dict incorrectly, should not happen!")
    # Generate private mask seed
    client_logic.b = primitives.rand_bytes(32)

    # Create shares
    b_shares = primitives.create_shares(
        client_logic.b, client_logic.threshold, client_logic.share_num
    )
    sk1_shares = primitives.create_shares(
        primitives.private_key_to_bytes(
            client_logic.sk1), client_logic.threshold, client_logic.share_num
    )
    share_keys_res = []

    for idx, p in enumerate(client_logic.public_keys_dict.items()):
        client_sec_agg_id, client_public_keys = p
        if client_sec_agg_id == client_logic.sec_agg_id:
            client_logic.b_share_dict[client_logic.sec_agg_id] = b_shares[idx]
            client_logic.sk1_share_dict[client_logic.sec_agg_id] = sk1_shares[idx]
        else:
            shared_key = primitives.generate_shared_key(
                client_logic.sk2, primitives.bytes_to_public_key(client_public_keys["pk2"])
            )
            client_logic.shared_key_2_dict[client_sec_agg_id] = shared_key
            plaintext = primitives.share_keys_plaintext_concat(
                client_logic.sec_agg_id, client_sec_agg_id, b_shares[idx], sk1_shares[idx]
            )
            ciphertext = primitives.encrypt(shared_key, plaintext)
            share_keys_packet_dict = ShareKeysPacket(
                source=client_logic.sec_agg_id, destination=client_sec_agg_id, ciphertext=ciphertext
            ).to_dict()
            share_keys_res.append(share_keys_packet_dict)
    ins.config[SHARE_KEYS_PACKETS] = share_keys_res

    log(INFO, "SecAgg Stage 2 Completed: Sent Shares via Packets")
    return FitRes(
        status=Status(error_code=ErrorCode.OK, message="Success"),
        parameters=ins.parameters,
        config=ins.config,
    )


def ask_vectors(client_logic: ClientLogic, ins: FitIns) -> FitRes:
    """Step 3: Upload masked local model."""
    # Receive shares and fit model
    packet_list = ins.config[FORWARD_PACKETS]
    available_clients: List[int] = []

    if len(packet_list) + 1 < client_logic.threshold:
        raise Exception("Available neighbours number smaller than threshold")

    # decode all packets and verify all packets are valid. Save shares received
    for packet in packet_list:
        source = packet["source"]
        available_clients.append(source)
        destination = packet["destination"]
        ciphertext = packet["ciphertext"]
        if destination != client_logic.sec_agg_id:
            raise Exception(
                "Received packet meant for another user. Not supposed to happen")
        shared_key = client_logic.shared_key_2_dict[source]
        plaintext = primitives.decrypt(shared_key, ciphertext)
        try:
            plaintext_source, plaintext_destination, plaintext_b_share, plaintext_sk1_share = \
                primitives.share_keys_plaintext_separate(plaintext)
        except:
            raise Exception(
                "Decryption of ciphertext failed. Not supposed to happen")
        if plaintext_source != source:
            raise Exception(
                "Received packet source is different from intended source. Not supposed to happen")
        if plaintext_destination != destination:
            raise Exception(
                "Received packet destination is different from intended destination. Not supposed to happen")
        client_logic.b_share_dict[source] = plaintext_b_share
        client_logic.sk1_share_dict[source] = plaintext_sk1_share

    # fit client
    del ins.config[FORWARD_PACKETS]
    res: FitRes = client_logic.trainer.fit(FitIns(
        parameters=ins.parameters, 
        config=ins.config
    ))
    parameters = parameters_to_ndarrays(res.parameters)
    for key, value in res.config.items():
        ins.config[key] = value
    weights_factor = ins.config[METRICS][DATA_SAMPLES]

    # Quantize weight update vector
    quantized_weights = primitives.quantize(
        parameters, client_logic.clipping_range, client_logic.target_range)

    # weights factor cannoot exceed maximum
    if weights_factor > client_logic.max_weights_factor:
        weights_factor = client_logic.max_weights_factor
        log(WARNING, "weights_factor exceeds allowed range and has been clipped. Either increase max_weights_factor, or train with fewer data. (Or server is performing unweighted aggregation)")

    quantized_weights = primitives.weights_multiply(
        quantized_weights, weights_factor)
    quantized_weights = primitives.factor_weights_combine(
        weights_factor, quantized_weights)

    dimensions_list: List[Tuple] = [a.shape for a in quantized_weights]

    # add private mask
    private_mask = primitives.pseudo_rand_gen(
        client_logic.b, client_logic.mod_range, dimensions_list)
    quantized_weights = primitives.weights_addition(
        quantized_weights, private_mask)

    for client_id in available_clients:
        # add pairwise mask
        shared_key = primitives.generate_shared_key(
            client_logic.sk1, primitives.bytes_to_public_key(client_logic.public_keys_dict[client_id]["pk1"]))
        pairwise_mask = primitives.pseudo_rand_gen(
            shared_key, client_logic.mod_range, dimensions_list)
        if client_logic.sec_agg_id > client_id:
            quantized_weights = primitives.weights_addition(
                quantized_weights, pairwise_mask)
        else:
            quantized_weights = primitives.weights_subtraction(
                quantized_weights, pairwise_mask)

    # Take mod of final weight update vector and return to server
    quantized_weights = primitives.weights_mod(
        quantized_weights, client_logic.mod_range)
    log(INFO, "SecAgg Stage 3 Completed: Sent Vectors")
    parameters = ndarrays_to_parameters(quantized_weights)

    return FitRes(
        status=res.status,
        parameters=parameters,
        config=ins.config,
    )


def unmask_vectors(client_logic: ClientLogic, ins: FitIns) -> FitRes:
    """Step 4: Unmasked the proper masks based on client participation."""
    # Send private mask seed share for every avaliable client (including itclient)
    # Send first private key share for building pairwise mask for every dropped client
    available_clients = ins.config[SHARE_REQUEST]["survivals"]
    if len(available_clients) < client_logic.threshold:
        raise Exception("Available neighbours number smaller than threshold")

    dropout_clients = ins.config[SHARE_REQUEST]["dropouts"]
    share_dict: Dict[int, bytes] = {}
    for idx in available_clients:
        share_dict[idx] = client_logic.b_share_dict[idx]
    for idx in dropout_clients:
        share_dict[idx] = client_logic.sk1_share_dict[idx]
    log(INFO, "SecAgg Stage 4 Completed: Sent Shares for Unmasking")
    ins.config[SHARE_RESPONSE] = ShareResponse(share_dict=share_dict).to_dict()
    return FitRes(
        status=Status(error_code=ErrorCode.OK, message="Success"),
        parameters=ins.parameters,
        config=ins.config,
    )
