import struct
from .varint import leb128u_encode, leb128u_decode
from .hash import combine_unordered_soft_hash_60

def serialize_null(obj):
    return b'\x00'

def deserialize_null(data, offset=0):
    return None, offset + 1

def serialize_bool(obj):
    return bytes([ 0x02 | int(obj) ])

def deserialize_bool(data, offset=0):
    return data[offset] > 2, offset + 1

def serialize_float(obj):
    return struct.pack('<Bd', 0x10, obj)

def deserialize_float(data, offset=0):
    offset += 1
    return struct.unpack_from('<d', data, offset)[0], offset + 8

def serialize_int(obj):
    prefix = 0x18 | ((obj < 0) << 2)
    data = leb128u_encode(abs(obj))
    length = len(data)
    return struct.pack(f'<B{length}s', prefix, data)

def deserialize_int(data, offset=0):
    sign = 1 - (((data[offset] >> 2) & 1) << 1)
    offset += 1
    result, offset = leb128u_decode(data, offset)
    return sign * result, offset

def _serialize_sequence_prefix(obj, high_bits, length_bits):
    max_length = (1 << length_bits) - 1
    assert high_bits > max_length
    obj_length = len(obj)
    if obj_length < max_length:
        return 1, bytes([ high_bits | obj_length ]), obj_length
    rest = leb128u_encode(obj_length - max_length)
    rest_length = len(rest)
    return (
        rest_length + 1, 
        struct.pack(f'<B{rest_length}s', high_bits | max_length, rest),
        obj_length)

def _deserialize_sequence_length(data, offset=0, length_bits=5):
    max_length = (1 << length_bits) - 1
    obj_length = data[offset] & max_length
    offset +=1
    if obj_length == max_length:
        result, length = leb128u_decode(data, offset)
        return obj_length + result, offset + length
    return obj_length, offset

_packable_type_high_bits = {
    None: 0x40,
    bool: 0x50,
    float: 0x60,
    int: 0x70,
}

_packable_types = set((bool, float, int))

def _packable_array_type(obj):
    return type(obj[0]) \
        if obj \
            and all(map(lambda x: isinstance(x, type(obj[0])), obj)) \
            and type(obj[0]) in _packable_types \
        else None

#def _sequence_high_bits(obj):
#    base = 0x80
#    if isinstance(obj, str):
#        return base
#    if isinstance(obj, bytes):
#        return base | 0x20
#    if isinstance(obj, list):
#        return base | 0x40 | (int(_is_array_same_type(obj)) << 5)
#    raise RuntimeError

def serialize_string(obj):
    data = obj.encode('utf-8')
    prefix_length, prefix, data_length = _serialize_sequence_prefix(
        data, 0x80, 5)
    return prefix + data
    #return struct.pack(f'<{prefix_length}s{data_length}s', prefix, data)

def deserialize_string(data, offset=0):
    length, offset = _deserialize_sequence_length(data, offset)
    return data[offset:offset + length].decode('utf-8'), offset + length

def serialize_bytes(obj):
    prefix_length, prefix, data_length = _serialize_sequence_prefix(
        obj, 0xa0, 5)
    return prefix + obj
    #return struct.pack(f'<{prefix_length}s{data_length}s', prefix, obj)

def deserialize_bytes(data, offset=0):
    length, offset = _deserialize_sequence_length(data, offset)
    return data[offset:offset + length], offset + length

def _serialize_packed_bools(obj):
    result = 0
    for index, item in enumerate(obj):
        result |= int(item) << index
    return result.to_bytes((len(obj) + 7) >> 3, 'little')

def _deserialize_packed_bools(data, length, offset=0):
    result = []
    if not length:
        return result, offset
    bytes_length = (length + 7) >> 3
    value = int.from_bytes(data[offset:offset + bytes_length], 'little')
    for index in range(length):
        result.append(bool(value & 1))
        value >>= 1
    return result, offset + bytes_length

def _serialize_packed_floats(obj):
    return struct.pack('<' + 'd' * len(obj), *obj)

def _deserialize_packed_floats(data, length, offset=0):
    return (
        list(struct.unpack_from('<' + 'd' * length, data, offset)),
        offset + (length << 3))

def _serialize_packed_ints(obj):
    signs = [ item < 0 for item in obj ]
    signs_length = len(signs)
    packed_signs = _serialize_packed_bools(signs)
    return packed_signs \
        + b''.join( leb128u_encode(abs(item)) for item in obj )

def _deserialize_packed_ints(data, length, offset=0):
    sign_bools, offset = _deserialize_packed_bools(data, length, offset)
    result = []
    for index in range(length):
        value, offset = leb128u_decode(data, offset)
        result.append(value)
    return (
        [ (1 - (int(s) << 1)) * x for s, x in zip(sign_bools, result) ], 
        offset)

def _serialize_mixed_array_items(obj):
    return b''.join(map(serialize, obj))

def _deserialize_mixed_array_items(data, length, offset=0):
    result = []
    for index in range(length):
        item, offset = deserialize(data, offset)
        result.append(item)
    return result, offset

_serialize_array_call_table = {
    None: _serialize_mixed_array_items,
    bool: _serialize_packed_bools,
    float: _serialize_packed_floats,
    int: _serialize_packed_ints,
}

def serialize_array(obj):
    if not obj:
        return b'\x40'
    packable_type = _packable_array_type(obj)
    prefix_length, prefix, obj_length = _serialize_sequence_prefix(
        obj, _packable_type_high_bits[packable_type], 4)
    return prefix + _serialize_array_call_table[packable_type](obj)

_deserialize_array_call_table = {
    0x40: _deserialize_mixed_array_items,
    0x50: _deserialize_packed_bools,
    0x60: _deserialize_packed_floats,
    0x70: _deserialize_packed_ints,
}

def deserialize_array(data, offset=0):
    prefix = data[offset]
    length, offset = _deserialize_sequence_length(
        data, offset, length_bits=4)
    return _deserialize_array_call_table[prefix & 0xf0](data, length, offset)

def serialize_object_item_parts(key, value):
    assert isinstance(key, str)
    return serialize_string(key), serialize(value)

#def serialize_object_item(key, value):
#    key_data, value_data = serialize_object_item_parts()
#    return key_data + value_data

def deserialize_object_item(data, offset=0):
    key, offset = deserialize_string(data, offset)
    value, offset = deserialize(data, offset)
    return (key, value), offset

def serialize_object_parts(obj):
    high_bits = 0xf0
    if not obj:
        return bytes([ high_bits ]), tuple()
    prefix_length, prefix, obj_length = _serialize_sequence_prefix(
        obj, high_bits, 4)
    return (
        prefix, 
        tuple( serialize_object_item_parts(*item) for item in obj.items() ))

def serialize_object(obj):
    prefix, items = serialize_object_parts(obj)
    return prefix + b''.join( key + value for key, value in items )

def deserialize_object(data, offset=0):
    length, offset = _deserialize_sequence_length(
        data, offset, length_bits=4)
    result = dict()
    for index in range(length):
        (key, value), offset = deserialize_object_item(data, offset)
        assert key not in result
        result[key] = value
    return result, offset

def serialize_object_pointer(obj):
    assert not any( isinstance(v, dict) for v in obj.values() )
    prefix, items = serialize_object_parts(obj)
    as_int = combine_unordered_soft_hash_60(
        map(lambda i: i[0] + i[1], items), high_bits=0xc)
    return struct.pack('>Q', as_int)

_MAX_INT_64 = (1<<64)-1

def deserialize_object_pointer(data, offset=0, mask_high_bits=True):
    result = struct.unpack_from('>Q', data, offset)[0]
    offset += 8
    result &= _MAX_INT_64 >> (int(mask_high_bits) << 2)
    return result, offset

_serialize_call_table = {
    type(None): serialize_null,
    bool: serialize_bool,
    float: serialize_float,
    int: serialize_int,
    str: serialize_string,
    bytes: serialize_bytes,
    list: serialize_array,
    dict: serialize_object,
}

def serialize(obj):
    return _serialize_call_table[type(obj)](obj)
    
def _select_deserialization_call(data, offset):
    prefix = data[offset]
    if prefix == 0x00:
        return deserialize_null
    if 0x02 <= prefix <= 0x03:
        return deserialize_bool
    if prefix == 0x10:
        return deserialize_float
    if prefix == 0x18 or prefix == 0x1c:
        return deserialize_int
    if (prefix & 0xe0) == 0x80:
        return deserialize_string
    if (prefix & 0xe0) == 0xa0:
        return deserialize_bytes
    if 0x40 <= (prefix & 0xf0) <= 0x80:
        return deserialize_array
    if (prefix & 0xf0) == 0xf0:
        return deserialize_object
    raise RuntimeError

def deserialize(data, offset=0):
    assert offset >= 0
    assert offset < len(data)
    return _select_deserialization_call(data, offset)(data, offset)


