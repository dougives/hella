# hella

Binary serializer in pure Python 3. Leb128 int encoding and special handling of arrays with the same type elements produces a compact result.

Capable of serializing:
- Nested dicts
- Nested lists
- Strings
- Variable length ints
- Floats
- Bytes
- Bools
- Nulls
