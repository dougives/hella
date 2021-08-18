import json
import jsonschema
import jsonpointer
from .serialization import serialize_object_parts

class Ingester:
    def __init__(self, schema, source_path):
        self._schema = schema
        self._source_path = source_path

    def _process_target(self):
        with open(self._source_path) as file:
            for line in file:
                obj = json.loads(line)
                timestamp, columns = self._schema.parse(obj)
                raise NotImplementedError




