import enum
import json
from jsonpointer import JsonPointer
import jsonschema
import dateutil
from operator import itemgetter
from .serialization import serialize_object_pointer

@enum.unique
class TimestampFormat(enum.Enum):
    RFC3339 = enum.auto()
    UNIX_NANOSECONDS = enum.auto()
    UNIX_MICROSECONDS = enum.auto()
    UNIX_SECONDS = enum.auto()

class TimestampConfig:
    def __init__(self,
        pointer : str,
        input_format : TimestampFormat, 
        rounding_function=round): 
        # need leap seconds option
        assert isinstance(pointer, str)
        assert isinstance(input_format, TimestampFormat)
        self.pointer : JsonPointer = JsonPointer(pointer)
        self._input_format = input_format
        self._rounding_function = rounding_function

    # to ns, since python datetime like timeval does not support ns
    def normalize(self, ts_value):
        if self._input_format == TimestampFormat.RFC3339:
            return int(self._rounding_function(
                dateutil.parser.parse(ts_value).timestamp() * 1000))
        if self._input_format == TimestampFormat.UNIX_SECONDS:
            return int(self._rounding_function(ts_value) * 1000000000)
        if self._input_format == TimestampFormat.UNIX_MICROSECONDS:
            return int(self._rounding_function(ts_value) * 1000)
        if self._input_format == TimestampFormat.UNIX_NANOSECONDS:
            return int(self._rounding_function(ts_value))
        raise RuntimeError        

_root_pointer = JsonPointer('')

class Missing:
    pass
_missing = Missing()

class Schema:
    def __init__(self, json_schema, timestamp_config):
        jsonschema.Draft7Validator.check_schema(json_schema)
        self._validator = jsonschema.Draft7Validator(json_schema)
        self._timestamp_config = timestamp_config
        _pointer_items = tuple(Schema._generate_object_pointers(
            self._validator.schema))
        assert self._timestamp_config.pointer.path \
            in ( pointer.path for pointer, _ in _pointer_items )
        self._pointers = dict(filter(
            lambda kvp: kvp[0].path != self._timestamp_config.pointer.path,
            _pointer_items))
        self._timestamp_parent_pointer = next(filter(
            lambda pointer: pointer.parts \
                == self._timestamp_config.pointer.parts[:-1],
            self._pointers))
        self._column_pointers = tuple(map(itemgetter(0), filter(
            lambda kvp: kvp[1] is not dict,
            self._pointers.items())))


    _type_map = {
        'null': type(None),
        'boolean': bool,
        'object': dict,
        'array': list,
        'number': float,
        'string': str,
        'integer': int,
    }

    @staticmethod
    def _generate_object_pointers(schema):
        assert isinstance(schema, dict)
        assert schema['type'] == 'object'
        yield _root_pointer, Schema._type_map[schema['type']]
        def _generate_object_pointers_inner(obj, base=_root_pointer):
            for key, value in obj['properties'].items():
                inner = JsonPointer.from_parts([ *base.parts, key ])
                inner_type = Schema._type_map[value['type']]
                yield inner, inner_type
                if inner_type is not dict:
                    continue
                for pointer, pointer_type in _generate_object_pointers_inner(
                    value, inner):
                    yield pointer, pointer_type
        for item in _generate_object_pointers_inner(schema):
            yield item

    @staticmethod
    def _select_objects_from_pointers_iter(obj, *pointers):
        return map(lambda p: p.resolve(obj), pointers)

    def _extract_timestamp(self, obj : dict) -> int:
        ts_value = self._timestamp_config.pointer.resolve(obj)
        del self._timestamp_parent_pointer.resolve(obj)[
            self._timestamp_config.pointer.parts[-1]]
        return self._timestamp_config.normalize(ts_value)

    def parse(self, s : str):
        obj = json.loads(s)
        self._validator.validate(obj)
        ts_value_ns = self._extract_timestamp(obj)
        parsed = (
            (pointer, pointer.resolve(obj, default=_missing) \
                if pointer_type is not dict \
                else object)
            for pointer, pointer_type in self._pointers.items()
        )
        return (
            ts_value_ns, 
            dict(filter(
                lambda kvp: kvp[1] is not _missing,
                parsed)))

            

