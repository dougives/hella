from hashlib import sha256
from functools import reduce, partial
from itertools import combinations, chain
from operator import xor
import struct

_GOLDEN_RATIO_64 = 0x9e3779b97f4a7c15
_MAX_INT_64 = (1<<64)-1
_MAX_INT_60 = (1<<60)-1

# taken from sqlite
def soft_hash_64(z : bytes) -> int:
    return reduce(
        lambda h, c: ((h + c) * _GOLDEN_RATIO_64) & _MAX_INT_64,
        z,
        _GOLDEN_RATIO_64)

def soft_hash_60(z : bytes, high_bits=0x0) -> int:
    return (soft_hash_64(z) & _MAX_INT_60) | (high_bits << 60)

def combine_unordered_soft_hash_64(s) -> int:
    return reduce(xor, map(soft_hash_64, s))

def combine_unordered_soft_hash_60(s, high_bits=0x0) -> int:
    return (combine_unordered_soft_hash_64(s) & _MAX_INT_60) \
        | (high_bits << 60)

def combo_soft_hash_60(s, high_bits=0x0):
    return {
        x: combine_unordered_soft_hash_60(x)
        for x in chain(*map(partial(combinations, s), range(1, len(s) + 1)))
    }

def hard_hash_256(z : bytes) -> int:
    return int.from_bytes(sha256(z).digest(), 'little')
