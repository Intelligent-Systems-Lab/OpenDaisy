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
"""Cryptographic primitives for the Secure Aggregation protocol."""
import base64
import os
import pickle
import random
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple

import numpy as np
from Crypto.Protocol.SecretSharing import Shamir
from Crypto.Util.Padding import pad, unpad
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from daisyfl.common import NDArrays
from daisyfl.utils.logger import WARNING, log

# Key Generation  ====================================================================

# Generate private and public key pairs with Cryptography


def generate_key_pairs() -> Tuple[ec.EllipticCurvePrivateKey, ec.EllipticCurvePublicKey]:
    """Generate an ECDH private/public key pair using SECP384R1."""
    sk = ec.generate_private_key(ec.SECP384R1())
    pk = sk.public_key()
    return sk, pk


# Serialize private key


def private_key_to_bytes(sk: ec.EllipticCurvePrivateKey) -> bytes:
    """Serialize an elliptic curve private key to PEM-encoded bytes."""
    return sk.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


# Deserialize private key


def bytes_to_private_key(b: bytes) -> ec.EllipticCurvePrivateKey:
    """Deserialize a PEM-encoded bytes string to an elliptic curve private key."""
    return serialization.load_pem_private_key(data=b, password=None)


# Serialize public key


def public_key_to_bytes(pk: ec.EllipticCurvePublicKey) -> bytes:
    """Serialize an elliptic curve public key to PEM-encoded bytes."""
    return pk.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


# Deserialize public key


def bytes_to_public_key(b: bytes) -> ec.EllipticCurvePublicKey:
    """Deserialize a PEM-encoded bytes string to an elliptic curve public key."""
    return serialization.load_pem_public_key(data=b)


# Generate shared key by exchange function and key derivation function
# Key derivation function is needed to obtain final shared key of exactly 32 bytes


def generate_shared_key(sk: ec.EllipticCurvePrivateKey, pk: ec.EllipticCurvePublicKey) -> bytes:
    """Derive a 32-byte URL-safe shared key from a private key and a peer's public key."""
    # Generate a 32 byte urlsafe(for fernet) shared key from own private key and another public key
    sharedk = sk.exchange(ec.ECDH(), pk)
    derivedk = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=None,
    ).derive(sharedk)
    return base64.urlsafe_b64encode(derivedk)


# Authenticated Encryption ================================================================

# Encrypt plaintext with Fernet. Key must be 32 bytes.


def encrypt(key: bytes, plaintext: bytes) -> bytes:
    """Encrypt plaintext using Fernet symmetric encryption with a 32-byte URL-safe key."""
    # key must be url safe
    f = Fernet(key)
    return f.encrypt(plaintext)


# Decrypt ciphertext with Fernet. Key must be 32 bytes.


def decrypt(key: bytes, token: bytes):
    """Decrypt a Fernet token using a 32-byte URL-safe key."""
    # key must be url safe
    f = Fernet(key)
    return f.decrypt(token)


# Shamir's Secret Sharing Scheme ============================================================

# Create shares with PyCryptodome. Each share must be processed to be a byte string with pickle for RPC


def create_shares(secret: bytes, threshold: int, num: int) -> List[bytes]:
    """Split a secret into `num` Shamir shares requiring `threshold` to reconstruct."""
    # return list of list for each user. Each sublist contains a share for a 16 byte chunk of the secret.
    # The int part of the tuple represents the index of the share, not the index of the chunk it is representing.
    secret_padded = pad(secret, 16)
    secret_padded_chunk = [(threshold, num, secret_padded[i : i + 16]) for i in range(0, len(secret_padded), 16)]
    share_list = []
    for _ in range(num):
        share_list.append([])

    with ThreadPoolExecutor(max_workers=10) as executor:
        for chunk_shares in executor.map(lambda arg: shamir_split(*arg), secret_padded_chunk):
            for idx, share in chunk_shares:
                # idx start with 1
                share_list[idx - 1].append((idx, share))

    for idx, shares in enumerate(share_list):
        share_list[idx] = pickle.dumps(shares)

    return share_list


def shamir_split(threshold: int, num: int, chunk: bytes) -> List[Tuple[int, bytes]]:
    """Split a 16-byte chunk into Shamir shares using PyCryptodome."""
    return Shamir.split(threshold, num, chunk)


# Reconstructing secret with PyCryptodome


def combine_shares(share_list: List[bytes]) -> bytes:
    """Reconstruct a secret from a list of Shamir shares."""
    for idx, share in enumerate(share_list):
        share_list[idx] = pickle.loads(share)

    chunk_num = len(share_list[0])
    secret_padded = bytearray(0)
    chunk_shares_list = []
    for i in range(chunk_num):
        chunk_shares = []
        for user_share in share_list:
            chunk_shares.append(user_share[i])
        chunk_shares_list.append(chunk_shares)

    with ThreadPoolExecutor(max_workers=10) as executor:
        for chunk in executor.map(shamir_combine, chunk_shares_list):
            secret_padded += chunk

    secret = unpad(secret_padded, 16)
    return bytes(secret)


def shamir_combine(shares: List[Tuple[int, bytes]]) -> bytes:
    """Combine Shamir share chunks into a single 16-byte secret chunk."""
    return Shamir.combine(shares)


# Random Bytes Generator =============================================================

# Generate random bytes with os. Usually 32 bytes for Fernet
def rand_bytes(num: int = 32) -> bytes:
    """Generate `num` cryptographically random bytes using os.urandom."""
    return os.urandom(num)


# Pseudo Bytes Generator ==============================================================

# Pseudo random generator for creating masks.


def pseudo_rand_gen(seed: bytes, num_range: int, dimensions_list: List[Tuple]) -> NDArrays:
    """Generate a deterministic list of integer arrays from a seed for use as masks."""
    random.seed(seed)
    output = []
    for dimension in dimensions_list:
        flat_arr = np.array([random.randrange(0, num_range) for i in range(np.prod(dimension))])
        modified_arr = np.reshape(flat_arr, dimension)
        output.append(modified_arr)
    return output


# String Concatenation ===================================================================

# Unambiguous string concatenation of source, destination, and two secret shares.
def share_keys_plaintext_concat(source: int, destination: int, b_share: bytes, sk_share: bytes) -> bytes:
    """Serialize source, destination, and two secret shares into a single bytes object."""
    return pickle.dumps([source, destination, b_share, sk_share])


# Unambiguous string splitting to obtain source, destination and two secret shares.


def share_keys_plaintext_separate(plaintext: bytes) -> Tuple[int, int, bytes, bytes]:
    """Deserialize bytes back into source, destination, and two secret shares."""
    return tuple(pickle.loads(plaintext))


# Weight Quantization ======================================================================

# Clip weight vector to [-clipping_range, clipping_range]
# Transform weight vector to range [0, target_range] and take floor
# If final value is target_range, take 1 from it so it is an integer from 0 to target_range-1


def quantize(weight: NDArrays, clipping_range: float, target_range: int) -> NDArrays:
    """Clip and quantize a weight vector to integer values in [0, target_range)."""
    quantized_list = []
    check_clipping_range(weight, clipping_range)
    f = np.vectorize(
        lambda x: min(
            target_range - 1,
            (sorted((-clipping_range, x, clipping_range))[1] + clipping_range) * target_range / (2 * clipping_range),
        )
    )
    for arr in weight:
        quantized_list.append(f(arr).astype(int))
    return quantized_list


# Quick check that all numbers are within the clipping range
# Throw warning if there exists numbers that exceed it


def check_clipping_range(weight: NDArrays, clipping_range: float):
    """Log a warning if any weight value exceeds the specified clipping range."""
    for arr in weight:
        for x in arr.flatten():
            if x < -clipping_range or x > clipping_range:
                log(
                    WARNING,
                    "There are some numbers in the local vector that exceeds clipping range. "
                    "Please increase the clipping range to account for value %s",
                    x,
                )
                return


# Transform weight vector to range [-clipping_range, clipping_range]
# Convert to float


def reverse_quantize(weight: NDArrays, clipping_range: float, target_range: int) -> NDArrays:
    """Reverse quantization, mapping integer values back to floats in [-clipping_range, clipping_range]."""
    reverse_quantized_list = []
    f = np.vectorize(lambda x: (x) / target_range * (2 * clipping_range) - clipping_range)
    for arr in weight:
        reverse_quantized_list.append(f(arr.astype(float)))
    return reverse_quantized_list


# Weight Manipulation =============================================================

# Combine factor with weights


def factor_weights_combine(weights_factor: int, weights: NDArrays) -> NDArrays:
    """Prepend a scalar weights factor array to the weights list."""
    return [np.array([weights_factor])] + weights


# Extract factor from weights


def factor_weights_extract(weights: NDArrays) -> Tuple[int, NDArrays]:
    """Extract the scalar weights factor prepended by factor_weights_combine."""
    return weights[0][0], weights[1:]


# Create dimensions list of each element in weights


def weights_shape(weights: NDArrays) -> List[Tuple]:
    """Return a list of shapes for each array in the weights."""
    return [arr.shape for arr in weights]


# Generate zero weights based on dimensions list


def weights_zero_generate(dimensions_list: List[Tuple]) -> NDArrays:
    """Generate a list of zero-filled arrays with the given shapes."""
    return [np.zeros(dimensions) for dimensions in dimensions_list]


# Add two weights together


def weights_addition(a: NDArrays, b: NDArrays) -> NDArrays:
    """Element-wise add two weight arrays."""
    return [a[idx] + b[idx] for idx in range(len(a))]


# Subtract one weight from the other


def weights_subtraction(a: NDArrays, b: NDArrays) -> NDArrays:
    """Element-wise subtract weight array b from a."""
    return [a[idx] - b[idx] for idx in range(len(a))]


# Take mod of a weights with an integer


def weights_mod(a: NDArrays, b: int) -> NDArrays:
    """Element-wise modulo of each weight array by integer b."""
    return [a[idx] % b for idx in range(len(a))]


# Multiply weight by an integer


def weights_multiply(a: NDArrays, b: int) -> NDArrays:
    """Multiply each weight array by integer b."""
    return [a[idx] * b for idx in range(len(a))]


# Divide weight by an integer


def weights_divide(a: NDArrays, b: int) -> NDArrays:
    """Divide each weight array by integer b."""
    return [a[idx] / b for idx in range(len(a))]
