"""Strict validation of the shipped JSON Schema vocabulary, without dependencies."""
import hashlib
import hmac
import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path
import re


class IntegrityError(ValueError):
    """Safe error codes only; never interpolate query/response/exception contents."""


class ExecutionDisabled(IntegrityError):
    pass


def require(condition, code="integrity_failure"):
    if not condition:
        raise IntegrityError(code)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    raw = value if isinstance(value, bytes) else value.encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=unique,
                          parse_constant=lambda _: require(False, "nonfinite_json"))
    except (json.JSONDecodeError, UnicodeError):
        raise IntegrityError("invalid_json") from None


def pseudonym(secret, namespace, identifier):
    require(isinstance(secret, bytes) and len(secret) >= 32, "pseudonym_key_too_short")
    require(namespace in {"actor", "native_session"}, "invalid_pseudonym_namespace")
    require(type(identifier) is str and bool(identifier), "identifier_missing")
    return hmac.new(secret, (namespace + "\0" + identifier).encode(), hashlib.sha256).hexdigest()


@lru_cache
def schema(name):
    require(name in {"manifest", "event"}, "unsupported_schema")
    path = Path(__file__).parent / "schemas" / f"{name}-v1.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def validate(value, spec):
    """Implement only the vocabulary used in our two versioned, self-contained schemas."""
    if "anyOf" in spec or "oneOf" in spec:
        key = "anyOf" if "anyOf" in spec else "oneOf"
        matches = 0
        for choice in spec[key]:
            try:
                validate(value, choice)
                matches += 1
            except IntegrityError:
                pass
        require(matches > 0 if key == "anyOf" else matches == 1, "schema_invalid")
    if "const" in spec:
        require(type(value) is type(spec["const"]) and value == spec["const"], "schema_invalid")
    if "enum" in spec:
        require(value in spec["enum"], "schema_invalid")
    kind = spec.get("type")
    checks = {"object": lambda: type(value) is dict, "array": lambda: type(value) is list,
              "string": lambda: type(value) is str, "integer": lambda: type(value) is int,
              "boolean": lambda: type(value) is bool, "null": lambda: value is None}
    if kind:
        require(checks[kind](), "schema_invalid")
    if type(value) is dict:
        properties = spec.get("properties", {})
        require(all(k in value for k in spec.get("required", [])), "schema_invalid")
        if spec.get("additionalProperties") is False:
            require(set(value) <= set(properties), "schema_invalid")
        for name, child in properties.items():
            if name in value:
                validate(value[name], child)
    if type(value) is list:
        require(len(value) >= spec.get("minItems", 0), "schema_invalid")
        if spec.get("uniqueItems"):
            require(len({canonical(v) for v in value}) == len(value), "schema_invalid")
        for child in value:
            validate(child, spec.get("items", {}))
    if type(value) is str:
        if "pattern" in spec:
            require(re.fullmatch(spec["pattern"], value) is not None, "schema_invalid")
        if spec.get("format") == "date-time":
            try:
                stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
                require(stamp.utcoffset().total_seconds() == 0, "schema_invalid")
            except (ValueError, AttributeError):
                raise IntegrityError("schema_invalid") from None
    if type(value) is int:
        require(value >= spec.get("minimum", value) and value <= spec.get("maximum", value), "schema_invalid")


def validate_manifest(value):
    require(len(canonical(value).encode("utf-8")) <= 65536, "manifest_too_large")
    validate(value, schema("manifest"))
    require((value["label"] == "attack") == (value["acquisition"] is not None), "label_provenance_mismatch")
    require(len({s["document_id"] for s in value["sources"]}) == len(value["sources"]), "duplicate_source_id")


def validate_event(value):
    validate(value, schema("event"))
