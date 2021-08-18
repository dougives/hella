from helladb.schema import Schema, TimestampConfig, TimestampFormat
from jsonschema import Draft7Validator
import json
from pprint import PrettyPrinter
from helladb.serialization import (
    serialize_object, deserialize_object, serialize_object_parts,
    serialize_object_pointer, deserialize_object_pointer)
from helladb.hash import combo_soft_hash_60

pp = PrettyPrinter(width=200).pprint

def main():
    schema = Schema({
            'type': 'object',
            'properties': {
                'timestamp': { 
                    'type': 'integer',
                    'minimum': 0,
                },
                'ticker': {
                    'type': 'string',
                    'pattern': r'^[A-Za-z]{1,5}$',
                },
                'price': {
                    'type': 'number',
                },
                'test': {
                    'type': 'object',
                    'properties': {
                        'a': { 'type': 'integer' },
                        'b': { 'type': 'integer' },
                    },
                    'required': [ 'a' ]
                }
            },
            'required': [ 'timestamp', 'ticker', 'price', 'test' ],
        },
        TimestampConfig(
            '/timestamp',
            TimestampFormat.UNIX_NANOSECONDS))

    #obj = json.loads('{"timestamp": 1577398870360465300, "ticker": "AAPL", "price": 97.61}')
    #print(list( p.path for p in Schema._generate_object_pointers(obj) ))
    p = schema.parse('{"timestamp": 1577398870360465300, "ticker": "MSFT", "price": 97.61, "test": { "a": 1 } }')
    pp(p)
    #pp({ k.path: v for k, v in p[1].items() })
    #pp(combo_soft_hash_60((b'\x01', b'\x02', b'\x03', b'\x04')))
    return 0

if __name__ == '__main__':
    exit(main())
