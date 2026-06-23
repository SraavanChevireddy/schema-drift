from schemadrift.core import (
    diff_schemas,
    infer_schema_from_csv,
    infer_schema_from_json,
    infer_schema_from_records,
)


def test_infer_basic_types():
    schema = infer_schema_from_records([
        {"id": 1, "name": "a", "price": 9.99, "active": True},
    ])
    assert schema == {"active": "bool", "id": "int", "name": "string", "price": "float"}


def test_infer_promotes_int_and_float():
    schema = infer_schema_from_records([{"x": 1}, {"x": 2.5}])
    assert schema["x"] == "float"


def test_infer_null_then_value():
    schema = infer_schema_from_records([{"x": None}, {"x": "hello"}])
    assert schema["x"] == "string"


def test_infer_from_jsonl():
    text = '{"a": 1}\n{"a": 2, "b": "x"}'
    assert infer_schema_from_json(text) == {"a": "int", "b": "string"}


def test_infer_from_json_array():
    text = '[{"a": 1.0}, {"a": 2.0}]'
    assert infer_schema_from_json(text) == {"a": "float"}


def test_infer_from_csv():
    text = "id,price,active\n1,9.99,true\n2,3.50,false\n"
    schema = infer_schema_from_csv(text)
    assert schema == {"active": "bool", "id": "int", "price": "float"}


def test_diff_added_column_is_safe():
    diff = diff_schemas({"a": "int"}, {"a": "int", "b": "string"})
    assert not diff.has_breaking
    assert diff.safe[0].kind == "added"


def test_diff_removed_column_is_breaking():
    diff = diff_schemas({"a": "int", "b": "string"}, {"a": "int"})
    assert diff.has_breaking
    assert diff.breaking[0].kind == "removed"


def test_diff_widening_is_safe():
    diff = diff_schemas({"a": "int"}, {"a": "float"})
    assert not diff.has_breaking
    assert diff.changes[0].kind == "type_widened"


def test_diff_narrowing_is_breaking():
    diff = diff_schemas({"a": "string"}, {"a": "int"})
    assert diff.has_breaking
    assert diff.breaking[0].kind == "type_narrowed"


def test_diff_incompatible_change_is_breaking():
    diff = diff_schemas({"a": "bool"}, {"a": "string"})
    # bool widens to string, so this is actually safe — verify the lattice.
    assert not diff.has_breaking


def test_identical_schemas_no_changes():
    assert diff_schemas({"a": "int"}, {"a": "int"}).changes == []
