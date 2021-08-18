from functools import reduce

def leb128u_encode_gen(value : int):
    assert value >= 0
    if not value:
        yield value
    while value:
        result = value & 0x7f
        value >>= 7
        if value:
            result |= 0x80
        yield result

def leb128u_encode(value : int):
    assert value >= 0
    if not value:
        return b'\x00'
    result = reduce(lambda a, b: (a << 8) | b, leb128u_encode_gen(value), 0)
    return result.to_bytes((result.bit_length() + 7) >> 3, 'big')

def leb128u_decode(data : bytes, offset : int=0):
    result = 0
    shift = 0
    while True:
        byte = data[offset]
        result |= (byte & 0x7f) << shift
        if not (byte & 0x80):
            return result, offset + 1
        shift += 7
        offset += 1


