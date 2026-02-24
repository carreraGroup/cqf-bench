#!/usr/bin/env python
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import os
import random
import re
import subprocess
import statistics
import string
import time
from datetime import datetime, timezone
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from config_io import load_config


class EngineAdapter:
    name = "generic-cqf"

    def adapt_query(self, scenario: dict[str, Any], query: dict[str, Any]) -> dict[str, Any]:
        return query

    def adapt_payload(self, scenario: dict[str, Any], payload: dict[str, Any], phase: str = "main") -> dict[str, Any]:
        return payload

    def adapt_path(self, scenario: dict[str, Any], path: str, phase: str = "main", payload: Any | None = None) -> str:
        return path

    def adapt_method(self, scenario: dict[str, Any], method: str, phase: str = "main", payload: Any | None = None) -> str:
        return method

    def payload_from_query(self, scenario: dict[str, Any], patient_id: str, phase: str = "main") -> dict[str, Any] | None:
        return None


class GenericCqfAdapter(EngineAdapter):
    name = "generic-cqf"


class MercuryCqfAdapter(EngineAdapter):
    name = "mercury-cqf"

    def _library_id_from_scenario(self, scenario: dict[str, Any], payload: dict[str, Any] | None = None) -> str | None:
        query_lib = scenario.get("query", {}).get("library") if isinstance(scenario.get("query"), dict) else None
        ref = parse_library_ref(query_lib) if isinstance(query_lib, str) else None
        if ref is not None:
            return ref[0]

        source = payload if isinstance(payload, dict) else scenario.get("payload", {})
        if isinstance(source, dict) and source.get("resourceType") == "Parameters":
            for p in source.get("parameter", []):
                if isinstance(p, dict) and p.get("name") == "library":
                    value = p.get("valueCanonical") or p.get("valueString")
                    ref = parse_library_ref(value) if isinstance(value, str) else None
                    if ref is not None:
                        return ref[0]
        return None

    def _library_canonical_from_measure_ref(self, measure_ref: str | None) -> str | None:
        if not isinstance(measure_ref, str):
            return None
        ref = parse_library_ref(measure_ref)
        if ref is None:
            return None
        library_id, version = ref
        return f"http://example.com/Library/{library_id}|{version}"

    def _normalize_library_canonical(self, raw: str | None) -> str | None:
        if not isinstance(raw, str):
            return None
        ref = parse_library_ref(raw)
        if ref is None:
            return raw
        library_id, version = ref
        return f"http://example.com/Library/{library_id}|{version}"

    def adapt_query(self, scenario: dict[str, Any], query: dict[str, Any]) -> dict[str, Any]:
        if scenario.get("path", "").startswith("/Measure/"):
            query = dict(query)
            if "library" not in query:
                canonical = self._library_canonical_from_measure_ref(query.get("measure"))
                if canonical is not None:
                    query["library"] = canonical
        if scenario.get("path") == "/Library/$evaluate":
            query = dict(query)
            query.pop("library", None)
        return query

    def adapt_path(self, scenario: dict[str, Any], path: str, phase: str = "main", payload: Any | None = None) -> str:
        if phase == "setup" and scenario.get("path_role") == "data":
            return "/data/bundle"
        if phase == "main" and path == "/Library/$evaluate":
            library_id = self._library_id_from_scenario(scenario, payload if isinstance(payload, dict) else None)
            if library_id:
                return f"/Library/{library_id}/$evaluate"
        return path

    def adapt_payload(self, scenario: dict[str, Any], payload: dict[str, Any], phase: str = "main") -> dict[str, Any]:
        if phase == "setup" and payload.get("resourceType") == "Bundle" and payload.get("type") == "transaction":
            entries = payload.get("entry", [])
            return {
                "resourceType": "Bundle",
                "type": "collection",
                "entry": [{"resource": e.get("resource", {})} for e in entries],
            }
        if phase == "main" and scenario.get("path") == "/Library/$evaluate" and payload.get("resourceType") == "Parameters":
            out = dict(payload)
            library_id = self._library_id_from_scenario(scenario, payload)
            params = []
            for p in payload.get("parameter", []):
                if not isinstance(p, dict):
                    continue
                if str(p.get("name", "")) == "library":
                    if library_id is not None:
                        # Path is rewritten to /Library/{id}/$evaluate, so body library is redundant and can trigger
                        # canonical/system mismatches in Mercury's resolver.
                        continue
                    normalized = self._normalize_library_canonical(p.get("valueCanonical") or p.get("valueString"))
                    if normalized is not None:
                        updated = dict(p)
                        updated.pop("valueString", None)
                        updated["valueCanonical"] = normalized
                        params.append(updated)
                        continue
                params.append(p)
            out["parameter"] = params
            return out
        if phase == "main" and scenario.get("path", "").startswith("/Measure/") and payload.get("resourceType") == "Parameters":
            out = dict(payload)
            params = [p for p in payload.get("parameter", []) if isinstance(p, dict)]
            has_library = any(str(p.get("name", "")) == "library" for p in params)
            if not has_library:
                measure_ref = None
                for p in params:
                    if str(p.get("name", "")) == "measure":
                        measure_ref = p.get("valueCanonical") or p.get("valueString")
                        break
                canonical = self._library_canonical_from_measure_ref(measure_ref)
                if canonical is not None:
                    params = [{"name": "library", "valueCanonical": canonical}] + params
                    out["parameter"] = params
            return out
        return payload


class HapiCqfRulerAdapter(EngineAdapter):
    name = "hapi-cqf-ruler"

    _GET_TO_POST_PATHS = {
        "/Library/$evaluate",
        "/Measure/$evaluate-measure",
    }
    _INSTANCE_MEASURE_OPS = {
        "/Measure/$evaluate-measure",
        "/Measure/$collect-data",
        "/Measure/$submit-data",
    }

    def _is_instance_library_evaluate(self, path: str) -> bool:
        return bool(re.fullmatch(r"/Library/[^/]+/\$evaluate", path))

    def _effective_method(self, scenario: dict[str, Any], method: str) -> str:
        if method == "GET" and str(scenario.get("path")) in self._GET_TO_POST_PATHS:
            return "POST"
        return method

    def _library_id_from_scenario(self, scenario: dict[str, Any], payload: dict[str, Any] | None = None) -> str | None:
        query_lib = scenario.get("query", {}).get("library") if isinstance(scenario.get("query"), dict) else None
        ref = parse_library_ref(query_lib) if isinstance(query_lib, str) else None
        if ref is not None:
            return ref[0]

        source = payload if isinstance(payload, dict) else scenario.get("payload", {})
        if isinstance(source, dict) and source.get("resourceType") == "Parameters":
            for p in source.get("parameter", []):
                if isinstance(p, dict) and p.get("name") == "library":
                    value = p.get("valueCanonical") or p.get("valueString")
                    ref = parse_library_ref(value) if isinstance(value, str) else None
                    if ref is not None:
                        return ref[0]
        return None

    def _measure_id_from_scenario(self, scenario: dict[str, Any], payload: dict[str, Any] | None = None) -> str | None:
        query_measure = scenario.get("query", {}).get("measure") if isinstance(scenario.get("query"), dict) else None
        ref = parse_measure_ref(query_measure) if isinstance(query_measure, str) else None
        if ref is not None:
            return ref[0]

        source = payload if isinstance(payload, dict) else scenario.get("payload", {})
        if isinstance(source, dict) and source.get("resourceType") == "Parameters":
            for p in source.get("parameter", []):
                if isinstance(p, dict) and p.get("name") == "measure":
                    value = p.get("valueCanonical") or p.get("valueString")
                    ref = parse_measure_ref(value) if isinstance(value, str) else None
                    if ref is not None:
                        return ref[0]
        return None

    def _parameter_from_query(self, name: str, value: Any) -> dict[str, Any]:
        if name in {"periodStart", "periodEnd"}:
            return {"name": name, "valueDate": str(value)}
        if name in {"library", "measure"}:
            return {"name": name, "valueCanonical": str(value)}
        return {"name": name, "valueString": str(value)}

    def adapt_method(self, scenario: dict[str, Any], method: str, phase: str = "main", payload: Any | None = None) -> str:
        if phase == "main":
            return self._effective_method(scenario, method)
        return method

    def payload_from_query(self, scenario: dict[str, Any], patient_id: str, phase: str = "main") -> dict[str, Any] | None:
        if phase != "main":
            return None
        path = str(scenario.get("path", ""))
        method = self._effective_method(scenario, str(scenario.get("method", "GET")))
        if method != "POST":
            return None
        if path != "/Library/$evaluate" and not self._is_instance_library_evaluate(path) and path not in self._GET_TO_POST_PATHS:
            return None
        q = scenario.get("query")
        if not isinstance(q, dict):
            return None
        rendered = {k: render_obj(v, patient_id) for k, v in q.items()}
        params = []
        for name, value in rendered.items():
            if (path == "/Library/$evaluate" or self._is_instance_library_evaluate(path)) and name == "library":
                continue
            if scenario.get("path") == "/Measure/$evaluate-measure" and name == "measure":
                continue
            params.append(self._parameter_from_query(name, value))
        return {"resourceType": "Parameters", "parameter": params}

    def adapt_query(self, scenario: dict[str, Any], query: dict[str, Any]) -> dict[str, Any]:
        path = scenario.get("path")
        out = dict(query)
        method = self._effective_method(scenario, str(scenario.get("method", "GET")))
        if method == "POST" and (
            path in self._GET_TO_POST_PATHS
            or (isinstance(path, str) and self._is_instance_library_evaluate(path))
        ):
            return {}
        if path == "/Library/$evaluate":
            out.pop("library", None)
        if path in self._INSTANCE_MEASURE_OPS:
            out.pop("measure", None)
        return out

    def adapt_path(self, scenario: dict[str, Any], path: str, phase: str = "main", payload: Any | None = None) -> str:
        if phase == "setup" and scenario.get("path_role") == "data":
            return "/"
        if phase != "main":
            return path

        payload_dict = payload if isinstance(payload, dict) else None
        if path == "/Library/$evaluate":
            library_id = self._library_id_from_scenario(scenario, payload_dict)
            if library_id:
                return f"/Library/{library_id}/$evaluate"
        if path in self._INSTANCE_MEASURE_OPS:
            measure_id = self._measure_id_from_scenario(scenario, payload_dict)
            if measure_id:
                op = path.split("/")[-1]
                return f"/Measure/{measure_id}/{op}"
        return path

    def adapt_payload(self, scenario: dict[str, Any], payload: dict[str, Any], phase: str = "main") -> dict[str, Any]:
        if phase != "main" or payload.get("resourceType") != "Parameters":
            return payload

        path = scenario.get("path")
        out = dict(payload)
        params = [p for p in payload.get("parameter", []) if isinstance(p, dict)]

        if (path == "/Library/$evaluate" or self._is_instance_library_evaluate(str(path))) and self._library_id_from_scenario(scenario, payload) is not None:
            params = [p for p in params if str(p.get("name", "")) != "library"]
            out["parameter"] = params
            return out

        if path in self._INSTANCE_MEASURE_OPS and self._measure_id_from_scenario(scenario, payload) is not None:
            params = [p for p in params if str(p.get("name", "")) != "measure"]
            out["parameter"] = params
            return out

        return payload


class SmileCdrAdapter(EngineAdapter):
    name = "smile-cdr"


class GoogleCqlAdapter(EngineAdapter):
    name = "google-cql"


ADAPTERS: dict[str, EngineAdapter] = {
    GenericCqfAdapter.name: GenericCqfAdapter(),
    MercuryCqfAdapter.name: MercuryCqfAdapter(),
    HapiCqfRulerAdapter.name: HapiCqfRulerAdapter(),
    SmileCdrAdapter.name: SmileCdrAdapter(),
    GoogleCqlAdapter.name: GoogleCqlAdapter(),
}


LIBRARY_REF_RE = re.compile(r"Library/([^|/]+)(?:\|([^\s]+))?")
MEASURE_REF_RE = re.compile(r"Measure/([^|/]+)(?:\|([^\s]+))?")


def parse_library_ref(raw: str) -> tuple[str, str] | None:
    if not isinstance(raw, str):
        return None
    m = LIBRARY_REF_RE.search(raw)
    if not m:
        return None
    library_id = m.group(1)
    version = m.group(2) or "1.0.0"
    if not library_id or library_id.startswith("$"):
        return None
    return library_id, version


def parse_measure_ref(raw: str) -> tuple[str, str] | None:
    if not isinstance(raw, str):
        return None
    m = MEASURE_REF_RE.search(raw)
    if not m:
        return None
    measure_id = m.group(1)
    version = m.group(2) or "1.0.0"
    if not measure_id or measure_id.startswith("$"):
        return None
    return measure_id, version


def _collect_library_refs(value: Any, out: set[tuple[str, str]]) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            if k in {"library", "valueCanonical", "valueString"} and isinstance(v, str):
                ref = parse_library_ref(v)
                if ref is not None:
                    out.add(ref)
            _collect_library_refs(v, out)
    elif isinstance(value, list):
        for item in value:
            _collect_library_refs(item, out)


def _collect_measure_refs(value: Any, out: set[tuple[str, str]]) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            if k in {"measure", "valueCanonical", "valueString"} and isinstance(v, str):
                ref = parse_measure_ref(v)
                if ref is not None:
                    out.add(ref)
            _collect_measure_refs(v, out)
    elif isinstance(value, list):
        for item in value:
            _collect_measure_refs(item, out)


def required_library_refs(scenarios: list[dict[str, Any]]) -> set[tuple[str, str]]:
    refs: set[tuple[str, str]] = set()
    for scenario in scenarios:
        _collect_library_refs(scenario.get("query"), refs)
        _collect_library_refs(scenario.get("payload"), refs)
        _collect_library_refs(scenario.get("setup"), refs)
        path_ref = parse_library_ref(str(scenario.get("path", "")))
        if path_ref is not None:
            refs.add(path_ref)
    return refs


def required_measure_refs(scenarios: list[dict[str, Any]]) -> set[tuple[str, str]]:
    refs: set[tuple[str, str]] = set()
    for scenario in scenarios:
        _collect_measure_refs(scenario.get("query"), refs)
        _collect_measure_refs(scenario.get("payload"), refs)
        _collect_measure_refs(scenario.get("setup"), refs)
        path_ref = parse_measure_ref(str(scenario.get("path", "")))
        if path_ref is not None:
            refs.add(path_ref)
    return refs


def cql_for_benchmark_library(library_id: str, version: str) -> str:
    return f"""library {library_id} version '{version}'
using FHIR version '4.0.1'
codesystem "SNOMED": 'http://snomed.info/sct'
valueset "Bench Condition ValueSet": 'http://example.com/fhir/ValueSet/bench-condition-vs'

context Patient

define "HasSyncope":
  exists([Condition] C)

define "AnyCondition":
  exists([Condition] C)

define "InDenominator":
  exists([Condition] C)

define "RetrieveWithValueSetSyntax":
  exists([Condition: "Bench Condition ValueSet"] C)

define "NakedRetrieveWhereCodeInValueSet":
  exists([Condition] C where C.code in "Bench Condition ValueSet")

define function "ComplexConditionMatch"(C Condition):
  C.recordedDate is not null
    and StartsWith(ToString(C.recordedDate.value), '2024')
    and exists(C.clinicalStatus.coding CS where CS.code.value = 'active')
    and Length(Coalesce(C.id.value, '')) > 10
    and C.code in "Bench Condition ValueSet"

define "WhereWithComplexMatchingFunction":
  exists([Condition] C where "ComplexConditionMatch"(C))

define "WithAndWithoutJoinClauses":
  [Condition] C
    with [Observation] O
      such that O.subject.reference.value = 'Patient/' + Patient.id.value
        and O.status.value = 'final'
        and O.code ~ C.code
    without [Observation] OX
      such that OX.subject.reference.value = 'Patient/' + Patient.id.value
        and OX.status.value = 'cancelled'
        and OX.code ~ C.code

define "ReturnReshaping":
  [Condition] C
    where "ComplexConditionMatch"(C)
    return Coalesce(C.code.coding[0].code.value, 'unknown')

define "ProjectIntoTuples":
  [Condition] C
    where C.code in "Bench Condition ValueSet"
    return {{
      conditionId: Coalesce(C.id.value, ''),
      code: Coalesce(C.code.coding[0].code.value, ''),
      recordedDate: ToString(C.recordedDate.value),
      active: exists(C.clinicalStatus.coding CS where CS.code.value = 'active')
    }}

define "ChallengeSort":
  [Condition] C
    where C.recordedDate is not null
    sort by
      Length(Coalesce(C.code.coding[0].code.value, '')) desc,
      ToString(C.recordedDate.value) desc,
      Coalesce(C.id.value, '') asc
"""


def build_library_resource(library_id: str, version: str, cql_text: str | None = None) -> dict[str, Any]:
    cql = cql_text if isinstance(cql_text, str) else cql_for_benchmark_library(library_id, version)
    return {
        "resourceType": "Library",
        "id": library_id,
        "url": f"http://example.com/Library/{library_id}",
        "name": library_id,
        "version": version,
        "status": "active",
        "type": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/library-type",
                    "code": "logic-library",
                }
            ]
        },
        "content": [
            {
                "contentType": "text/cql",
                "data": base64.b64encode(cql.encode("utf-8")).decode("utf-8"),
            }
        ],
    }


def preload_required_libraries(engine: dict[str, Any], scenarios: list[dict[str, Any]], timeout: int) -> None:
    refs = required_library_refs(scenarios)
    if not refs:
        return
    base_url = engine["base_url"].rstrip("/")
    fhir_base = engine.get("fhir_base_path", engine.get("cqf_base_path", ""))
    headers = expand_headers(engine.get("headers", {}))
    for library_id, version in sorted(refs):
        url = f"{base_url}{fhir_base}/Library/{library_id}"
        # Ensure latest content is applied even when servers treat same-id/version updates as immutable.
        request_once("DELETE", url, headers, None, timeout)
        payload = build_library_resource(library_id, version)
        status, _, raw = request_once("PUT", url, headers, payload, timeout)
        if status // 100 == 2:
            print(f"preload library {library_id}|{version}: status={status}")
        else:
            msg = raw[:240].replace("\n", " ")
            print(f"preload library {library_id}|{version}: status={status} body={msg}")


def preload_scenario_cql_libraries(engine: dict[str, Any], scenarios: list[dict[str, Any]], timeout: int) -> None:
    base_url = engine["base_url"].rstrip("/")
    fhir_base = engine.get("fhir_base_path", engine.get("cqf_base_path", ""))
    headers = expand_headers(engine.get("headers", {}))
    for scenario in scenarios:
        cql_text = scenario.get("_cql_text")
        if not isinstance(cql_text, str):
            continue
        library_id, version = scenario_library_ref(scenario)
        url = f"{base_url}{fhir_base}/Library/{library_id}"
        # Ensure latest content is applied even when servers treat same-id/version updates as immutable.
        request_once("DELETE", url, headers, None, timeout)
        payload = build_library_resource(library_id, version, cql_text=cql_text)
        status, _, raw = request_once("PUT", url, headers, payload, timeout)
        if status // 100 == 2:
            print(f"preload scenario library {scenario['id']} ({library_id}|{version}): status={status}")
        else:
            msg = raw[:240].replace("\n", " ")
            print(f"preload scenario library {scenario['id']} ({library_id}|{version}): status={status} body={msg}")


def build_measure_resource(measure_id: str, version: str) -> dict[str, Any]:
    return {
        "resourceType": "Measure",
        "id": measure_id,
        "url": f"http://example.com/Measure/{measure_id}",
        "name": measure_id,
        "version": version,
        "status": "active",
        "library": [f"http://example.com/Library/{measure_id}|{version}"],
        "scoring": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/measure-scoring",
                    "code": "proportion",
                }
            ]
        },
        "group": [
            {
                "id": "grp-1",
                "population": [
                    {
                        "id": "pop-ip",
                        "code": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/measure-population",
                                    "code": "initial-population",
                                }
                            ]
                        },
                        "criteria": {"language": "text/cql", "expression": "InDenominator"},
                    },
                    {
                        "id": "pop-den",
                        "code": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/measure-population",
                                    "code": "denominator",
                                }
                            ]
                        },
                        "criteria": {"language": "text/cql", "expression": "InDenominator"},
                    },
                    {
                        "id": "pop-num",
                        "code": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/measure-population",
                                    "code": "numerator",
                                }
                            ]
                        },
                        "criteria": {"language": "text/cql", "expression": "InDenominator"},
                    },
                ]
            }
        ],
    }


def preload_standard_valuesets(engine: dict[str, Any], timeout: int) -> None:
    base_url = engine["base_url"].rstrip("/")
    fhir_base = engine.get("fhir_base_path", engine.get("cqf_base_path", ""))
    headers = expand_headers(engine.get("headers", {}))
    value_set = {
        "resourceType": "ValueSet",
        "id": "bench-condition-vs",
        "url": "http://example.com/fhir/ValueSet/bench-condition-vs",
        "version": "1.0.0",
        "status": "active",
        "name": "BenchConditionValueSet",
        "compose": {
            "include": [
                {
                    "system": "http://snomed.info/sct",
                    "concept": [{"code": "38341003", "display": "Hypertension"}],
                }
            ]
        },
        "expansion": {
            "contains": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "38341003",
                    "display": "Hypertension",
                }
            ]
        },
    }
    url = f"{base_url}{fhir_base}/ValueSet/bench-condition-vs"
    status, _, raw = request_once("PUT", url, headers, value_set, timeout)
    if status // 100 == 2:
        print(f"preload valueset bench-condition-vs: status={status}")
    else:
        msg = raw[:240].replace("\n", " ")
        print(f"preload valueset bench-condition-vs: status={status} body={msg}")


def preload_required_measures(engine: dict[str, Any], scenarios: list[dict[str, Any]], timeout: int) -> None:
    refs = required_measure_refs(scenarios)
    if not refs:
        return
    base_url = engine["base_url"].rstrip("/")
    fhir_base = engine.get("fhir_base_path", engine.get("cqf_base_path", ""))
    headers = expand_headers(engine.get("headers", {}))
    for measure_id, version in sorted(refs):
        url = f"{base_url}{fhir_base}/Measure/{measure_id}"
        payload = build_measure_resource(measure_id, version)
        status, _, raw = request_once("PUT", url, headers, payload, timeout)
        if status // 100 == 2:
            print(f"preload measure {measure_id}|{version}: status={status}")
        else:
            msg = raw[:240].replace("\n", " ")
            print(f"preload measure {measure_id}|{version}: status={status} body={msg}")


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def default_http_policy() -> dict[str, list[int]]:
    return {
        "success": [200, 201],
        "unsupported": [400, 404, 405, 409, 410, 415, 422, 501],
        "warning": [],
        "fail": [],
    }


def normalize_http_policy(raw: Any, fallback_success: list[int] | None = None) -> dict[str, set[int]]:
    fallback = default_http_policy()
    if fallback_success is not None:
        fallback["success"] = list(fallback_success)
    if not isinstance(raw, dict):
        raw = {}

    def to_int_set(key: str) -> set[int]:
        vals = raw.get(key, fallback.get(key, []))
        if not isinstance(vals, list):
            return set(fallback.get(key, []))
        out: set[int] = set()
        for v in vals:
            try:
                out.add(int(v))
            except (TypeError, ValueError):
                continue
        return out

    success = to_int_set("success")
    if not success:
        success = set(fallback["success"])
    return {
        "success": success,
        "unsupported": to_int_set("unsupported"),
        "warning": to_int_set("warning"),
        "fail": to_int_set("fail"),
    }


def resolve_http_policy_for_spec(spec: dict[str, Any], strict_mode: bool, suite_defaults: dict[str, Any] | None = None) -> dict[str, set[int]]:
    if strict_mode:
        return {"success": set(range(200, 300)), "unsupported": set(), "warning": set(), "fail": set()}
    if "expected_http" in spec:
        return normalize_http_policy(spec.get("expected_http"))
    if isinstance(suite_defaults, dict) and "expected_http" in suite_defaults:
        return normalize_http_policy(suite_defaults.get("expected_http"))
    return normalize_http_policy(None)


def classify_status(status: int, policy: dict[str, set[int]]) -> str:
    if status == -1:
        return "timeout"
    if status in policy["success"]:
        return "success"
    if status in policy["unsupported"]:
        return "unsupported"
    if status in policy.get("warning", set()):
        return "warning"
    if status in policy["fail"]:
        return "fail"
    return "fail"


def is_conformance_scenario(scenario: dict[str, Any]) -> bool:
    return str(scenario.get("test_type", "")).lower() == "conformance" or str(scenario.get("id", "")).startswith("CONF")


CONF_ENDPOINT_CANDIDATES: dict[str, list[dict[str, str]]] = {
    "library_evaluate": [
        {"conf_id": "CONF012", "method": "POST", "path": "/Library/{id}/$evaluate"},
        {"conf_id": "CONF011", "method": "POST", "path": "/Library/$evaluate"},
        {"conf_id": "CONF010", "method": "GET", "path": "/Library/$evaluate"},
    ],
}


def capability_operation_key(scenario: dict[str, Any]) -> str | None:
    path = str(scenario.get("path", ""))
    if path in {"/Library/$evaluate", "/Library/{id}/$evaluate"}:
        return "library_evaluate"
    return None


def resolve_endpoint_path_template(path_template: str, scenario: dict[str, Any]) -> str:
    if "{id}" not in path_template:
        return path_template
    if path_template.startswith("/Library/"):
        library_id, _ = scenario_library_ref(scenario)
        return path_template.replace("{id}", library_id)
    if path_template.startswith("/Measure/"):
        query = scenario.get("query") if isinstance(scenario.get("query"), dict) else {}
        measure_ref = parse_measure_ref(query.get("measure")) if isinstance(query.get("measure"), str) else None
        if measure_ref is not None:
            return path_template.replace("{id}", measure_ref[0])
    return path_template


def apply_dynamic_cap_endpoint(
    scenario: dict[str, Any],
    conf_results_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    out = dict(scenario)
    out["_endpoint_source"] = "scenario_default"
    out["_endpoint_conf_id"] = None
    out["_endpoint_operation"] = None

    op_key = capability_operation_key(scenario)
    if op_key is None:
        return out
    candidates = CONF_ENDPOINT_CANDIDATES.get(op_key, [])
    if not candidates:
        return out
    for cand in candidates:
        conf_id = cand.get("conf_id")
        if not isinstance(conf_id, str):
            continue
        conf = conf_results_by_id.get(conf_id, {})
        if str(conf.get("conformance_status", "")).upper() != "PASS":
            continue
        method = cand.get("method")
        path_template = cand.get("path")
        if not (isinstance(method, str) and isinstance(path_template, str)):
            continue
        out["method"] = method
        out["path"] = resolve_endpoint_path_template(path_template, scenario)
        out["_endpoint_source"] = "dynamic_conf"
        out["_endpoint_conf_id"] = conf_id
        out["_endpoint_operation"] = op_key
        return out
    return out


def scenario_library_ref(scenario: dict[str, Any]) -> tuple[str, str]:
    if isinstance(scenario.get("cql_library_id"), str):
        return scenario["cql_library_id"], str(scenario.get("cql_library_version", "1.0.0"))
    if isinstance(scenario.get("cql_file"), str):
        scenario_id = str(scenario.get("id", "Bench"))
        library_id = "Bench" + re.sub(r"[^A-Za-z0-9]", "", scenario_id)
        return library_id, "1.0.0"
    query = scenario.get("query") if isinstance(scenario.get("query"), dict) else {}
    ref = parse_library_ref(query.get("library")) if isinstance(query.get("library"), str) else None
    if ref is not None:
        return ref
    scenario_id = str(scenario.get("id", "Bench"))
    library_id = "Bench" + re.sub(r"[^A-Za-z0-9]", "", scenario_id)
    return library_id, "1.0.0"


def load_suite_with_scenarios(suite_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[Path]]:
    if suite_path.is_dir():
        suite_path = suite_path / "suite.yaml"

    suite_doc = load_config(suite_path)
    base_dir = suite_path.parent
    files_hashed: list[Path] = [suite_path]

    if "scenario_ids" not in suite_doc:
        raise ValueError(f"Suite file must use folder-based schema with scenario_ids: {suite_path}")

    scenarios: list[dict[str, Any]] = []
    for scenario_id in suite_doc.get("scenario_ids", []):
        scenario_dir = base_dir / str(scenario_id)
        scenario_path = scenario_dir / "scenario.yaml"
        scenario = load_config(scenario_path)
        scenario["__base_dir"] = str(scenario_dir)
        files_hashed.append(scenario_path)

        cql_file = scenario.get("cql_file")
        if isinstance(cql_file, str):
            cql_path = scenario_dir / cql_file
            scenario["_cql_text"] = cql_path.read_text(encoding="utf-8")
            files_hashed.append(cql_path)
            library_id, version = scenario_library_ref(scenario)
            scenario["_library_id"] = library_id
            scenario["_library_version"] = version
            if scenario.get("path") == "/Library/$evaluate":
                query = dict(scenario.get("query", {}))
                query["library"] = f"Library/{library_id}|{version}"
                query.setdefault("subject", "Patient/{patient_id}")
                if isinstance(scenario.get("cql_entrypoint"), str):
                    query["expression"] = scenario["cql_entrypoint"]
                scenario["query"] = query

        data_file = scenario.get("data_file")
        if isinstance(data_file, str):
            data_path = scenario_dir / data_file
            scenario["_data_config"] = load_config(data_path)
            files_hashed.append(data_path)

        expected_file = scenario.get("expected_file")
        if isinstance(expected_file, str):
            expected_path = scenario_dir / expected_file
            scenario["_expected_config"] = load_config(expected_path)
            files_hashed.append(expected_path)

        scenarios.append(scenario)
    return suite_doc, scenarios, files_hashed


def env_expand(value: str) -> str:
    out = value
    for key, env_val in os.environ.items():
        out = out.replace(f"${{{key}}}", env_val)
    return out


def expand_headers(headers: dict[str, str]) -> dict[str, str]:
    return {k: env_expand(v) for k, v in headers.items()}


def render_obj(obj: Any, patient_id: str) -> Any:
    if isinstance(obj, str):
        return obj.replace("{patient_id}", patient_id)
    if isinstance(obj, list):
        return [render_obj(x, patient_id) for x in obj]
    if isinstance(obj, dict):
        return {k: render_obj(v, patient_id) for k, v in obj.items()}
    return obj


def _stable_rng(seed_text: str) -> random.Random:
    seed_int = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:16], 16)
    return random.Random(seed_int)


def _set_path_value(obj: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    cur: Any = obj
    for i, part in enumerate(parts):
        m = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)(?:\[(\d+)\])?", part)
        if not m:
            return
        key = m.group(1)
        idx = int(m.group(2)) if m.group(2) is not None else None
        is_last = i == len(parts) - 1
        if idx is None:
            if is_last:
                if isinstance(cur, dict):
                    cur[key] = value
                return
            if not isinstance(cur, dict):
                return
            if key not in cur or not isinstance(cur[key], dict):
                cur[key] = {}
            cur = cur[key]
        else:
            if not isinstance(cur, dict):
                return
            if key not in cur or not isinstance(cur[key], list):
                cur[key] = []
            arr = cur[key]
            while len(arr) <= idx:
                arr.append({})
            if is_last:
                arr[idx] = value
                return
            if not isinstance(arr[idx], dict):
                arr[idx] = {}
            cur = arr[idx]


def _get_path_value(obj: dict[str, Any], path: str) -> Any:
    parts = path.split(".")
    cur: Any = obj
    for part in parts:
        m = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)(?:\[(\d+)\])?", part)
        if not m:
            return None
        key = m.group(1)
        idx = int(m.group(2)) if m.group(2) is not None else None
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
        if idx is not None:
            if not isinstance(cur, list) or idx >= len(cur):
                return None
            cur = cur[idx]
    return cur


def _parse_fsh_value(raw: str) -> Any:
    text = raw.strip()
    if text.startswith('"') and text.endswith('"') and len(text) >= 2:
        return text[1:-1]
    if text in {"true", "false"}:
        return text == "true"
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    ref_match = re.fullmatch(r"Reference\(([^)]+)\)", text)
    if ref_match:
        return {"reference": ref_match.group(1)}
    return text


def parse_fsh_instances(path: Path) -> dict[str, dict[str, Any]]:
    instances: dict[str, dict[str, Any]] = {}
    current_name: str | None = None
    current: dict[str, Any] | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("Instance:"):
            current_name = line.split(":", 1)[1].strip()
            current = {"resourceType": "Basic"}
            instances[current_name] = current
            continue
        if current_name is None or current is None:
            continue
        if line.startswith("InstanceOf:"):
            current["resourceType"] = line.split(":", 1)[1].strip()
            continue
        if line.startswith("* "):
            body = line[2:].strip()
            if "=" not in body:
                continue
            lhs, rhs = body.split("=", 1)
            _set_path_value(current, lhs.strip(), _parse_fsh_value(rhs.strip()))
    return instances


def _apply_mutation_op(resource: dict[str, Any], field: dict[str, Any], counter: int, rng: random.Random) -> None:
    path = str(field.get("path", ""))
    op = str(field.get("op", ""))
    if not path or not op:
        return
    if op == "suffix-counter":
        base = _get_path_value(resource, path)
        if base is None:
            base = ""
        _set_path_value(resource, path, f"{base}-{counter}")
        return
    if op == "pick":
        vals = field.get("values", [])
        if isinstance(vals, list) and vals:
            _set_path_value(resource, path, rng.choice(vals))
        return
    if op == "date-jitter":
        cur = _get_path_value(resource, path)
        if not isinstance(cur, str) or "T" not in cur:
            return
        days = field.get("days", [-7, 7])
        if not (isinstance(days, list) and len(days) == 2):
            return
        try:
            d0 = int(days[0])
            d1 = int(days[1])
            from datetime import datetime, timedelta
            base_dt = datetime.fromisoformat(cur.replace("Z", "+00:00"))
            delta_days = rng.randint(d0, d1)
            out = (base_dt + timedelta(days=delta_days)).isoformat().replace("+00:00", "Z")
            _set_path_value(resource, path, out)
        except Exception:  # noqa: BLE001
            return
        return


def _collect_unique_key(resource: dict[str, Any], key_paths: list[str]) -> tuple[Any, ...]:
    return tuple(_get_path_value(resource, p) for p in key_paths)


def generate_bundle_from_fsh_mutator(
    scenario: dict[str, Any],
    phase_cfg: dict[str, Any],
    patient_id: str,
    selectivity: float,
) -> dict[str, Any]:
    base_dir = Path(str(scenario.get("__base_dir", ".")))
    match_fsh = base_dir / str(phase_cfg.get("match_fsh", "match.fsh"))
    variations_fsh = base_dir / str(phase_cfg.get("variations_fsh", "variations.fsh"))
    mutator_path = base_dir / str(phase_cfg.get("mutator_file", "mutator.yaml"))

    templates: dict[str, dict[str, Any]] = {}
    if match_fsh.exists():
        templates.update(parse_fsh_instances(match_fsh))
    if variations_fsh.exists():
        templates.update(parse_fsh_instances(variations_fsh))
    plan = load_config(mutator_path)

    seed_template = str(plan.get("seed", "{patient_id}:{scenario_id}"))
    seed_text = seed_template.replace("{patient_id}", patient_id).replace("{scenario_id}", str(scenario.get("id", "")))
    rng = _stable_rng(seed_text)

    total_count = int(plan.get("total_count", 40))
    mix = plan.get("mix", [])
    counts: dict[str, int] = {}
    remaining = total_count
    for i, item in enumerate(mix):
        if not isinstance(item, dict):
            continue
        template = str(item.get("template", ""))
        if not template:
            continue
        ratio = item.get("ratio")
        if item.get("ratio_from_selectivity") == "match":
            ratio = selectivity
        elif item.get("ratio_from_selectivity") == "nomatch":
            ratio = 1.0 - selectivity
        try:
            r = float(ratio) if ratio is not None else 0.0
        except (TypeError, ValueError):
            r = 0.0
        if i == len(mix) - 1:
            count = max(0, remaining)
        else:
            count = int(round(total_count * max(0.0, min(1.0, r))))
            remaining -= count
        counts[template] = counts.get(template, 0) + count

    mutations_by_template: dict[str, list[dict[str, Any]]] = {}
    for m in plan.get("mutations", []):
        if isinstance(m, dict):
            t = str(m.get("template", ""))
            if t:
                mutations_by_template.setdefault(t, []).append(m)

    uniqueness_rules = [x for x in plan.get("uniqueness", []) if isinstance(x, list) and x]
    unique_seen: set[tuple[Any, ...]] = set()
    entries: list[dict[str, Any]] = []

    include_templates = [x for x in plan.get("include_templates", []) if isinstance(x, str)]
    for t in include_templates:
        if t not in templates:
            continue
        resource = render_obj(copy.deepcopy(templates[t]), patient_id)
        if not isinstance(resource, dict):
            continue
        rid = str(resource.get("id", f"{t.lower()}-{patient_id}"))
        resource["id"] = rid
        entries.append({"request": {"method": "PUT", "url": f"{resource['resourceType']}/{rid}"}, "resource": resource})

    linked_templates = plan.get("linked_templates", {})
    for template_name, count in counts.items():
        if template_name not in templates or count <= 0:
            continue
        for i in range(count):
            resource = render_obj(copy.deepcopy(templates[template_name]), patient_id)
            if not isinstance(resource, dict):
                continue
            mut_seq = mutations_by_template.get(template_name, [])
            for m in mut_seq:
                for f in m.get("fields", []):
                    if isinstance(f, dict):
                        _apply_mutation_op(resource, f, i, rng)

            if not resource.get("id"):
                resource["id"] = f"{template_name.lower()}-{patient_id}-{i}"

            attempts = 0
            while attempts < 6:
                duplicate = False
                for rule in uniqueness_rules:
                    key = _collect_unique_key(resource, [str(p) for p in rule])
                    if key in unique_seen:
                        duplicate = True
                        break
                if not duplicate:
                    break
                resource["id"] = f"{resource.get('id', template_name)}-u{attempts+1}"
                attempts += 1

            for rule in uniqueness_rules:
                unique_seen.add(_collect_unique_key(resource, [str(p) for p in rule]))

            rid = str(resource["id"])
            entries.append({"request": {"method": "PUT", "url": f"{resource['resourceType']}/{rid}"}, "resource": resource})

            linked = linked_templates.get(template_name, [])
            if isinstance(linked, list):
                for linked_name in linked:
                    if not isinstance(linked_name, str) or linked_name not in templates:
                        continue
                    linked_resource = render_obj(copy.deepcopy(templates[linked_name]), patient_id)
                    if not isinstance(linked_resource, dict):
                        continue
                    if not linked_resource.get("id"):
                        linked_resource["id"] = f"{linked_name.lower()}-{patient_id}-{i}"
                    for m in mutations_by_template.get(linked_name, []):
                        for f in m.get("fields", []):
                            if isinstance(f, dict):
                                _apply_mutation_op(linked_resource, f, i, rng)
                    lrid = str(linked_resource["id"])
                    entries.append(
                        {
                            "request": {"method": "PUT", "url": f"{linked_resource['resourceType']}/{lrid}"},
                            "resource": linked_resource,
                        }
                    )

    bundle = {"resourceType": "Bundle", "type": "transaction", "entry": entries}
    output_mode = str(phase_cfg.get("output_mode", "bundle"))
    if output_mode == "parameters_data":
        collection_entries = [{"resource": e.get("resource", {})} for e in entries if isinstance(e, dict)]
        query = scenario.get("query") if isinstance(scenario.get("query"), dict) else {}
        rendered = {k: render_obj(v, patient_id) for k, v in query.items()}
        params: list[dict[str, Any]] = []
        for name, value in rendered.items():
            if name in {"library", "measure"}:
                params.append({"name": name, "valueCanonical": str(value)})
            elif name in {"periodStart", "periodEnd"}:
                params.append({"name": name, "valueDate": str(value)})
            else:
                params.append({"name": name, "valueString": str(value)})
        params.append(
            {
                "name": "data",
                "resource": {
                    "resourceType": "Bundle",
                    "type": "collection",
                    "entry": collection_entries,
                },
            }
        )
        return {"resourceType": "Parameters", "parameter": params}
    return bundle


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = int((len(s) - 1) * p)
    return s[idx]


def request_once(
    method: str,
    url: str,
    headers: dict[str, str],
    payload: Any | None,
    timeout: int,
    content_type: str | None = None,
) -> tuple[int, float, str]:
    body = None
    h = {"Accept": "application/fhir+json, application/json", **headers}
    if payload is not None:
        if isinstance(payload, (dict, list)):
            body = json.dumps(payload).encode("utf-8")
            h["Content-Type"] = content_type or "application/fhir+json"
        elif isinstance(payload, str):
            body = payload.encode("utf-8")
            h["Content-Type"] = content_type or "text/plain; charset=utf-8"
        elif isinstance(payload, bytes):
            body = payload
            h["Content-Type"] = content_type or "application/octet-stream"
        else:
            body = str(payload).encode("utf-8")
            h["Content-Type"] = content_type or "text/plain; charset=utf-8"

    req = urllib.request.Request(url=url, method=method, data=body, headers=h)
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = (time.perf_counter() - start) * 1000.0
            raw = resp.read().decode("utf-8")
            return resp.status, elapsed, raw
    except urllib.error.HTTPError as e:
        elapsed = (time.perf_counter() - start) * 1000.0
        raw = e.read().decode("utf-8")
        return e.code, elapsed, raw
    except Exception as e:  # noqa: BLE001
        elapsed = (time.perf_counter() - start) * 1000.0
        return -1, elapsed, f"REQUEST ERROR: {e}"


def _json_or_none(raw: str) -> Any | None:
    try:
        return json.loads(raw)
    except Exception:  # noqa: BLE001
        return None


def _operation_outcome_has_error(resource: Any) -> bool:
    if not isinstance(resource, dict):
        return False
    if resource.get("resourceType") != "OperationOutcome":
        return False
    for issue in resource.get("issue", []):
        if not isinstance(issue, dict):
            continue
        sev = str(issue.get("severity", "")).lower()
        if sev in {"error", "fatal"}:
            return True
    return False


def response_has_evaluation_error(raw: str) -> bool:
    parsed = _json_or_none(raw)
    if not isinstance(parsed, dict):
        return False

    if _operation_outcome_has_error(parsed):
        return True

    if parsed.get("resourceType") == "Parameters":
        for p in parsed.get("parameter", []):
            if not isinstance(p, dict):
                continue
            if str(p.get("name", "")).strip().lower() == "evaluation error":
                return True
            if _operation_outcome_has_error(p.get("resource")):
                return True

    return False


def _split_json_path(path: str) -> list[str]:
    tokens: list[str] = []
    cur = ""
    bracket_depth = 0
    for ch in path:
        if ch == "." and bracket_depth == 0:
            if cur:
                tokens.append(cur)
                cur = ""
            continue
        cur += ch
        if ch == "[":
            bracket_depth += 1
        elif ch == "]":
            bracket_depth = max(0, bracket_depth - 1)
    if cur:
        tokens.append(cur)
    return tokens


def json_path_select(data: Any, path: str) -> list[Any]:
    if path == "$":
        return [data]
    if not path.startswith("$."):
        return []
    tokens = _split_json_path(path[2:])
    nodes = [data]
    for token in tokens:
        m = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)(\[\*\]|\[\?\(@\.([A-Za-z_][A-Za-z0-9_]*)==['\"]([^'\"]+)['\"]\)\])?", token)
        if not m:
            return []
        field = m.group(1)
        suffix = m.group(2)
        filter_field = m.group(3)
        filter_value = m.group(4)
        next_nodes: list[Any] = []
        for node in nodes:
            if not isinstance(node, dict) or field not in node:
                continue
            value = node[field]
            if suffix is None:
                next_nodes.append(value)
                continue
            if not isinstance(value, list):
                continue
            if suffix == "[*]":
                next_nodes.extend(value)
            else:
                for item in value:
                    if isinstance(item, dict) and str(item.get(filter_field, "")) == filter_value:
                        next_nodes.append(item)
        nodes = next_nodes
    return nodes


def run_response_validators(raw: str, expected_cfg: dict[str, Any] | None, status: int) -> tuple[bool, bool, list[str]]:
    if not isinstance(expected_cfg, dict):
        return True, False, []
    when_status_in = expected_cfg.get("when_status_in")
    if not isinstance(when_status_in, list):
        when_status_in = []
    eligible_codes: set[int] = set()
    for x in when_status_in:
        try:
            eligible_codes.add(int(x))
        except (TypeError, ValueError):
            continue
    eligible = (not eligible_codes) or (status in eligible_codes)
    if not eligible:
        return True, False, []

    validators = expected_cfg.get("validators", [])
    if not isinstance(validators, list):
        return True, True, []

    parsed = _json_or_none(raw)
    failures: list[str] = []

    for v in validators:
        if not isinstance(v, dict):
            continue
        vtype = str(v.get("type", "")).strip()
        if vtype == "not_operation_outcome_error":
            if response_has_evaluation_error(raw):
                failures.append("operation outcome contains error/fatal")
            continue

        if vtype == "parameters_has_name":
            wanted = str(v.get("name", ""))
            found = False
            if isinstance(parsed, dict) and parsed.get("resourceType") == "Parameters":
                for p in parsed.get("parameter", []):
                    if isinstance(p, dict) and str(p.get("name", "")) == wanted:
                        found = True
                        break
            if not found:
                failures.append(f"Parameters.parameter name '{wanted}' not found")
            continue

        if vtype == "function_result_body_equals":
            param_name = str(v.get("name", "return"))
            expected_body = v.get("expected_body")
            compare_field = v.get("compare_field")
            found = None
            if isinstance(parsed, dict) and parsed.get("resourceType") == "Parameters":
                for p in parsed.get("parameter", []):
                    if isinstance(p, dict) and str(p.get("name", "")) == param_name:
                        found = p
                        break
            if not isinstance(found, dict):
                failures.append(f"Parameters.parameter name '{param_name}' not found for function_result_body_equals")
                continue

            actual: Any
            if isinstance(compare_field, str) and compare_field:
                actual = _get_path_value(found, compare_field)
            elif "resource" in found:
                actual = found.get("resource")
            else:
                value_keys = [k for k in found.keys() if k.startswith("value")]
                if value_keys:
                    actual = found[value_keys[0]]
                else:
                    actual = found
            if actual != expected_body:
                failures.append("function_result_body_equals mismatch")
            continue

        path = v.get("path")
        nodes = json_path_select(parsed, path) if isinstance(path, str) and parsed is not None else []

        if vtype == "exists":
            if not nodes:
                failures.append(f"path does not exist: {path}")
        elif vtype == "min_items":
            try:
                min_items = int(v.get("min", 0))
            except (TypeError, ValueError):
                min_items = 0
            if len(nodes) < min_items:
                failures.append(f"path {path} has {len(nodes)} items, expected at least {min_items}")
        elif vtype == "max_items":
            try:
                max_items = int(v.get("max", 0))
            except (TypeError, ValueError):
                max_items = 0
            if len(nodes) > max_items:
                failures.append(f"path {path} has {len(nodes)} items, expected at most {max_items}")
        elif vtype == "equals":
            wanted = v.get("value")
            if not any(node == wanted for node in nodes):
                failures.append(f"path {path} does not equal expected value")
        elif vtype == "contains":
            wanted = str(v.get("value", ""))
            ok = False
            for node in nodes:
                if isinstance(node, str) and wanted in node:
                    ok = True
                    break
                if isinstance(node, list) and wanted in [str(x) for x in node]:
                    ok = True
                    break
            if not ok:
                failures.append(f"path {path} does not contain '{wanted}'")
        elif vtype == "regex":
            pattern = str(v.get("pattern", ""))
            if not pattern:
                continue
            rx = re.compile(pattern)
            if not any(rx.search(str(node)) for node in nodes):
                failures.append(f"path {path} does not match /{pattern}/")

    return len(failures) == 0, True, failures


def clamp_selectivity(value: Any, default: float = 0.2) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, parsed))


def resolve_selectivity(scenario: dict[str, Any], defaults: dict[str, Any], cli_selectivity: float) -> float:
    if "selectivity" in scenario:
        return clamp_selectivity(scenario.get("selectivity"), default=cli_selectivity)
    if "selectivity" in defaults:
        return clamp_selectivity(defaults.get("selectivity"), default=cli_selectivity)
    return clamp_selectivity(cli_selectivity, default=0.2)


def resolve_requests_per_patient(scenario: dict[str, Any], defaults: dict[str, Any]) -> int:
    raw = scenario.get("requests_per_patient", defaults.get("requests_per_patient", 1))
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return 1


def make_payload(template_name: str, patient_id: str, selectivity: float = 0.2) -> dict[str, Any]:
    if template_name == "care_gaps":
        return {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "measure", "valueCanonical": "Measure/Test|1.0.0"},
                {"name": "subject", "valueString": f"Patient/{patient_id}"},
                {"name": "periodStart", "valueDate": "2024-01-01"},
                {"name": "periodEnd", "valueDate": "2024-12-31"},
            ],
        }
    if template_name == "collect_data":
        return {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "measure", "valueCanonical": "Measure/Test|1.0.0"},
                {"name": "subject", "valueString": f"Patient/{patient_id}"},
            ],
        }
    if template_name == "submit_data":
        return {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "measure", "valueCanonical": "Measure/Test|1.0.0"},
                {
                    "name": "measureReport",
                    "resource": {
                        "resourceType": "MeasureReport",
                        "status": "complete",
                        "type": "individual",
                        "measure": "Measure/Test|1.0.0",
                        "subject": {"reference": f"Patient/{patient_id}"},
                        "period": {"start": "2024-01-01", "end": "2024-12-31"},
                        "date": "2024-12-31T00:00:00Z",
                    },
                },
            ],
        }
    if template_name == "inline_bundle_library_evaluate":
        return {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "library", "valueCanonical": "Library/Test|1.0.0"},
                {"name": "subject", "valueString": f"Patient/{patient_id}"},
                {"name": "expression", "valueString": "InDenominator"},
                {
                    "name": "data",
                    "resource": {
                        "resourceType": "Bundle",
                        "type": "collection",
                        "entry": [
                            {
                                "resource": {
                                    "resourceType": "Patient",
                                    "id": patient_id,
                                }
                            },
                            {
                                "resource": {
                                    "resourceType": "Condition",
                                    "id": f"cond-{patient_id}",
                                    "subject": {"reference": f"Patient/{patient_id}"},
                                    "code": {
                                        "coding": [
                                            {
                                                "system": "http://snomed.info/sct",
                                                "code": "38341003",
                                                "display": "Hypertension",
                                            }
                                        ]
                                    },
                                }
                            },
                        ],
                    },
                },
            ],
        }
    if template_name == "resident_bundle_transaction":
        return {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": [
                {
                    "request": {"method": "PUT", "url": f"Patient/{patient_id}"},
                    "resource": {
                        "resourceType": "Patient",
                        "id": patient_id,
                    },
                },
                {
                    "request": {"method": "PUT", "url": f"Condition/cond-{patient_id}"},
                    "resource": {
                        "resourceType": "Condition",
                        "id": f"cond-{patient_id}",
                        "subject": {"reference": f"Patient/{patient_id}"},
                        "code": {
                            "coding": [
                                {
                                    "system": "http://snomed.info/sct",
                                    "code": "38341003",
                                    "display": "Hypertension",
                                }
                            ]
                        },
                    },
                },
            ],
        }
    if template_name == "resident_bundle_transaction_with_dates":
        # Stable total row count with selectivity-controlled match/non-match split.
        total_count = 43
        matching_count = int(round(total_count * clamp_selectivity(selectivity)))
        non_matching_count = total_count - matching_count
        entries: list[dict[str, Any]] = [
            {
                "request": {"method": "PUT", "url": f"Patient/{patient_id}"},
                "resource": {
                    "resourceType": "Patient",
                    "id": patient_id,
                },
            }
        ]

        for i in range(matching_count):
            entries.append(
                {
                    "request": {"method": "PUT", "url": f"Condition/cond-{patient_id}-match-{i}"},
                    "resource": {
                        "resourceType": "Condition",
                        "id": f"cond-{patient_id}-match-{i}",
                        "subject": {"reference": f"Patient/{patient_id}"},
                        "recordedDate": "2024-06-15T00:00:00Z",
                        "onsetDateTime": "2024-06-15T00:00:00Z",
                        "code": {
                            "coding": [
                                {
                                    "system": "http://snomed.info/sct",
                                    "code": "38341003",
                                    "display": "Hypertension",
                                }
                            ]
                        },
                    },
                }
            )

        for i in range(non_matching_count):
            entries.append(
                {
                    "request": {"method": "PUT", "url": f"Condition/cond-{patient_id}-miss-{i}"},
                    "resource": {
                        "resourceType": "Condition",
                        "id": f"cond-{patient_id}-miss-{i}",
                        "subject": {"reference": f"Patient/{patient_id}"},
                        "recordedDate": "2010-01-01T00:00:00Z",
                        "onsetDateTime": "2010-01-01T00:00:00Z",
                        "code": {
                            "coding": [
                                {
                                    "system": "http://snomed.info/sct",
                                    "code": "90000001",
                                    "display": "Historical condition",
                                }
                            ]
                        },
                    },
                }
            )

        return {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": entries,
        }
    if template_name == "resident_bundle_transaction_with_clinical_status":
        # Stable total row count with selectivity-controlled active/inactive split.
        total_count = 40
        active_count = int(round(total_count * clamp_selectivity(selectivity)))
        inactive_count = total_count - active_count
        entries: list[dict[str, Any]] = [
            {
                "request": {"method": "PUT", "url": f"Patient/{patient_id}"},
                "resource": {
                    "resourceType": "Patient",
                    "id": patient_id,
                },
            }
        ]

        for i in range(active_count):
            entries.append(
                {
                    "request": {"method": "PUT", "url": f"Condition/cond-{patient_id}-active-{i}"},
                    "resource": {
                        "resourceType": "Condition",
                        "id": f"cond-{patient_id}-active-{i}",
                        "subject": {"reference": f"Patient/{patient_id}"},
                        "clinicalStatus": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                                    "code": "active",
                                }
                            ]
                        },
                        "code": {
                            "coding": [
                                {
                                    "system": "http://snomed.info/sct",
                                    "code": "38341003",
                                    "display": "Hypertension",
                                }
                            ]
                        },
                    },
                }
            )

        for i in range(inactive_count):
            entries.append(
                {
                    "request": {"method": "PUT", "url": f"Condition/cond-{patient_id}-inactive-{i}"},
                    "resource": {
                        "resourceType": "Condition",
                        "id": f"cond-{patient_id}-inactive-{i}",
                        "subject": {"reference": f"Patient/{patient_id}"},
                        "clinicalStatus": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                                    "code": "inactive",
                                }
                            ]
                        },
                        "code": {
                            "coding": [
                                {
                                    "system": "http://snomed.info/sct",
                                    "code": "38341003",
                                    "display": "Hypertension",
                                }
                            ]
                        },
                    },
                }
            )

        return {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": entries,
        }
    if template_name == "resident_bundle_transaction_query_idioms":
        # Stable total row count with selectivity-controlled in-vs/out-vs split.
        total_count = 40
        matching_count = int(round(total_count * clamp_selectivity(selectivity)))
        non_matching_count = total_count - matching_count
        entries: list[dict[str, Any]] = [
            {
                "request": {"method": "PUT", "url": f"Patient/{patient_id}"},
                "resource": {
                    "resourceType": "Patient",
                    "id": patient_id,
                },
            },
            {
                "request": {"method": "PUT", "url": "ValueSet/bench-condition-vs"},
                "resource": {
                    "resourceType": "ValueSet",
                    "id": "bench-condition-vs",
                    "url": "http://example.com/fhir/ValueSet/bench-condition-vs",
                    "version": "1.0.0",
                    "status": "active",
                    "name": "BenchConditionValueSet",
                    "compose": {
                        "include": [
                            {
                                "system": "http://snomed.info/sct",
                                "concept": [
                                    {
                                        "code": "38341003",
                                        "display": "Hypertension",
                                    }
                                ],
                            }
                        ]
                    },
                },
            },
        ]

        for i in range(matching_count):
            condition_id = f"cond-{patient_id}-vs-{i}"
            entries.append(
                {
                    "request": {"method": "PUT", "url": f"Condition/{condition_id}"},
                    "resource": {
                        "resourceType": "Condition",
                        "id": condition_id,
                        "subject": {"reference": f"Patient/{patient_id}"},
                        "recordedDate": "2024-06-15T00:00:00Z",
                        "clinicalStatus": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                                    "code": "active",
                                }
                            ]
                        },
                        "code": {
                            "coding": [
                                {
                                    "system": "http://snomed.info/sct",
                                    "code": "38341003",
                                    "display": "Hypertension",
                                }
                            ]
                        },
                    },
                }
            )
            entries.append(
                {
                    "request": {"method": "PUT", "url": f"Observation/obs-{patient_id}-final-{i}"},
                    "resource": {
                        "resourceType": "Observation",
                        "id": f"obs-{patient_id}-final-{i}",
                        "status": "final",
                        "subject": {"reference": f"Patient/{patient_id}"},
                        "code": {
                            "coding": [
                                {
                                    "system": "http://snomed.info/sct",
                                    "code": "38341003",
                                }
                            ]
                        },
                        "valueString": "match",
                    },
                }
            )

        for i in range(non_matching_count):
            condition_id = f"cond-{patient_id}-novs-{i}"
            entries.append(
                {
                    "request": {"method": "PUT", "url": f"Condition/{condition_id}"},
                    "resource": {
                        "resourceType": "Condition",
                        "id": condition_id,
                        "subject": {"reference": f"Patient/{patient_id}"},
                        "recordedDate": "2010-01-01T00:00:00Z",
                        "clinicalStatus": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                                    "code": "inactive",
                                }
                            ]
                        },
                        "code": {
                            "coding": [
                                {
                                    "system": "http://snomed.info/sct",
                                    "code": "90000001",
                                    "display": "Historical condition",
                                }
                            ]
                        },
                    },
                }
            )
            entries.append(
                {
                    "request": {"method": "PUT", "url": f"Observation/obs-{patient_id}-cancelled-{i}"},
                    "resource": {
                        "resourceType": "Observation",
                        "id": f"obs-{patient_id}-cancelled-{i}",
                        "status": "cancelled",
                        "subject": {"reference": f"Patient/{patient_id}"},
                        "code": {
                            "coding": [
                                {
                                    "system": "http://snomed.info/sct",
                                    "code": "90000001",
                                }
                            ]
                        },
                        "valueString": "non-match",
                    },
                }
            )

        return {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": entries,
        }
    if template_name == "resident_library_evaluate":
        return {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "library", "valueCanonical": "Library/Test|1.0.0"},
                {"name": "subject", "valueString": f"Patient/{patient_id}"},
                {"name": "expression", "valueString": "InDenominator"},
            ],
        }
    if template_name == "system_cql_inline_data":
        return {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "expression", "valueString": "exists([Condition] C)"},
                {"name": "subject", "valueString": f"Patient/{patient_id}"},
                {
                    "name": "data",
                    "resource": {
                        "resourceType": "Bundle",
                        "type": "collection",
                        "entry": [
                            {
                                "resource": {
                                    "resourceType": "Patient",
                                    "id": patient_id,
                                }
                            },
                            {
                                "resource": {
                                    "resourceType": "Condition",
                                    "id": f"cond-{patient_id}",
                                    "subject": {"reference": f"Patient/{patient_id}"},
                                    "code": {
                                        "coding": [
                                            {
                                                "system": "http://snomed.info/sct",
                                                "code": "15339004",
                                                "display": "Pulmonary emphysema",
                                            }
                                        ]
                                    },
                                }
                            },
                        ],
                    },
                },
            ],
        }
    raise ValueError(f"Unknown payload template: {template_name}")


def base_path_for_role(engine: dict[str, Any], role: str) -> str:
    if role == "data":
        return engine.get("data_base_path", engine.get("cqf_base_path", ""))
    if role == "fhir":
        return engine.get("fhir_base_path", engine.get("cqf_base_path", ""))
    return engine.get("cqf_base_path", "")


def endpoint_url(
    engine: dict[str, Any],
    spec: dict[str, Any],
    patient_id: str,
    adapter: EngineAdapter,
    phase: str = "main",
    payload: Any | None = None,
) -> str:
    role = spec.get("path_role", "cqf")
    base_path = base_path_for_role(engine, role)
    path = adapter.adapt_path(spec, spec["path"], phase, payload)
    endpoint = f"{engine['base_url'].rstrip('/')}{base_path}{path}"
    q = spec.get("query")
    if not q:
        return endpoint
    rendered = {k: render_obj(v, patient_id) for k, v in q.items()}
    rendered = adapter.adapt_query(spec, rendered)
    if not rendered:
        return endpoint
    return endpoint + "?" + urllib.parse.urlencode(rendered)


def _merge_parameters_from_query(payload: dict[str, Any], spec: dict[str, Any], patient_id: str) -> dict[str, Any]:
    query = spec.get("query")
    if not isinstance(query, dict):
        return payload
    if payload.get("resourceType") != "Parameters":
        return payload
    rendered = {k: render_obj(v, patient_id) for k, v in query.items()}
    param_by_name: dict[str, dict[str, Any]] = {}
    params: list[dict[str, Any]] = []
    for p in payload.get("parameter", []):
        if isinstance(p, dict) and isinstance(p.get("name"), str):
            param_by_name[p["name"]] = dict(p)
            params.append(param_by_name[p["name"]])
    for name, value in rendered.items():
        if isinstance(value, bool):
            val_key = "valueBoolean"
        elif name in {"periodStart", "periodEnd"}:
            val_key = "valueDate"
        elif name in {"library", "measure"}:
            val_key = "valueCanonical"
        else:
            val_key = "valueString"
        updated = {"name": name, val_key: str(value)}
        if name in param_by_name:
            idx = params.index(param_by_name[name])
            params[idx] = updated
            param_by_name[name] = updated
        else:
            params.append(updated)
            param_by_name[name] = updated
    return {"resourceType": "Parameters", "parameter": params}


def _payload_from_data_config(
    spec: dict[str, Any],
    data_cfg: dict[str, Any] | None,
    patient_id: str,
    selectivity: float,
    phase: str,
) -> Any | None:
    if not isinstance(data_cfg, dict):
        return None
    phase_cfg = data_cfg.get(phase)
    if not isinstance(phase_cfg, dict):
        return None
    base_dir = Path(str(spec.get("__base_dir", ".")))

    input_bundle_path = phase_cfg.get("input_bundle_path")
    if isinstance(input_bundle_path, str) and input_bundle_path:
        rendered_path = input_bundle_path.replace("{patient_id}", patient_id)
        bundle_path = Path(rendered_path)
        if not bundle_path.is_absolute():
            bundle_path = base_dir / bundle_path
        if bundle_path.exists():
            if bundle_path.suffix.lower() in {".yaml", ".yml"}:
                return load_config(bundle_path)
            if bundle_path.suffix.lower() == ".json":
                return json.loads(bundle_path.read_text(encoding="utf-8"))
            return bundle_path.read_text(encoding="utf-8")

    input_bundle_dir = phase_cfg.get("input_bundle_dir")
    if isinstance(input_bundle_dir, str) and input_bundle_dir:
        bundle_dir = Path(input_bundle_dir)
        if not bundle_dir.is_absolute():
            bundle_dir = base_dir / bundle_dir
        cand = bundle_dir / f"{patient_id}.json"
        if not cand.exists():
            cand = bundle_dir / f"{patient_id}.yaml"
        if not cand.exists():
            cand = bundle_dir / "default.json"
        if not cand.exists():
            cand = bundle_dir / "default.yaml"
        if cand.exists():
            if cand.suffix.lower() in {".yaml", ".yml"}:
                return load_config(cand)
            return json.loads(cand.read_text(encoding="utf-8"))

    generator = phase_cfg.get("generator")
    if isinstance(generator, dict) and str(generator.get("type", "")) == "fsh_mutation":
        return generate_bundle_from_fsh_mutator(spec, generator, patient_id, selectivity)
    if "payload_template" in phase_cfg:
        return make_payload(str(phase_cfg["payload_template"]), patient_id, selectivity=selectivity)
    if "payload" in phase_cfg:
        return render_obj(phase_cfg["payload"], patient_id)
    if "raw_body" in phase_cfg:
        return render_obj(phase_cfg["raw_body"], patient_id)
    return None


def prepare_payload(
    spec: dict[str, Any],
    patient_id: str,
    adapter: EngineAdapter,
    selectivity: float = 0.2,
    phase: str = "main",
    apply_adapter: bool = True,
) -> Any | None:
    payload: Any | None = _payload_from_data_config(spec, spec.get("_data_config"), patient_id, selectivity, phase)
    if payload is None and "payload_template" in spec:
        payload = make_payload(spec["payload_template"], patient_id, selectivity=selectivity)
    elif payload is None and "payload" in spec:
        payload = render_obj(spec["payload"], patient_id)
    elif payload is None and "raw_body" in spec:
        payload = render_obj(spec["raw_body"], patient_id)
    if isinstance(payload, dict) and payload.get("resourceType") == "Parameters":
        payload = _merge_parameters_from_query(payload, spec, patient_id)
    if payload is not None and apply_adapter:
        payload = adapter.adapt_payload(spec, payload, phase)
    return payload


def _override_phase_with_generated_input(
    data_cfg: dict[str, Any],
    scenario_id: str,
    phase: str,
    generated_root: Path,
) -> None:
    phase_cfg = copy.deepcopy(data_cfg.get(phase) or {})
    phase_dir = generated_root / scenario_id / phase
    phase_cfg["input_bundle_dir"] = str(phase_dir)
    phase_cfg.pop("input_bundle_path", None)
    # Force use of pre-generated payloads when a generated-data root is provided.
    phase_cfg.pop("generator", None)
    phase_cfg.pop("payload_template", None)
    phase_cfg.pop("payload", None)
    phase_cfg.pop("raw_body", None)
    data_cfg[phase] = phase_cfg


def apply_generated_data_root_overrides(
    scenarios: list[dict[str, Any]],
    generated_root: Path,
    use_setup_phase: bool,
    use_main_phase: bool,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for scenario in scenarios:
        updated = copy.deepcopy(scenario)
        sid = str(updated.get("id", ""))
        data_cfg = copy.deepcopy(updated.get("_data_config") or {})
        if use_setup_phase:
            _override_phase_with_generated_input(data_cfg, sid, "setup", generated_root)
        if use_main_phase:
            _override_phase_with_generated_input(data_cfg, sid, "main", generated_root)
        updated["_data_config"] = data_cfg
        out.append(updated)
    return out


def setup_for_scenario(
    engine: dict[str, Any],
    scenario: dict[str, Any],
    patient_ids: list[str],
    timeout: int,
    adapter: EngineAdapter,
    selectivity: float = 0.2,
    strict_mode: bool = False,
    suite_defaults: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    setup = scenario.get("setup")
    if not setup:
        return None
    setup_spec = dict(setup)
    setup_spec["_data_config"] = scenario.get("_data_config")
    setup_spec["__base_dir"] = scenario.get("__base_dir")

    method = setup_spec.get("method", "POST")
    method = adapter.adapt_method(setup_spec, method, phase="setup")
    policy = resolve_http_policy_for_spec(setup_spec, strict_mode, suite_defaults=suite_defaults)
    per_patient = bool(setup_spec.get("per_patient", True))
    ids = patient_ids if per_patient else [patient_ids[0]]

    status_counts: dict[str, int] = {}
    latencies: list[float] = []
    success_count = 0
    unsupported_count = 0
    warning_count = 0
    timeout_count = 0
    fail_count = 0

    for patient_id in ids:
        raw_payload = prepare_payload(
            setup_spec,
            patient_id,
            adapter,
            selectivity=selectivity,
            phase="setup",
            apply_adapter=False,
        )
        url = endpoint_url(engine, setup_spec, patient_id, adapter, phase="setup", payload=raw_payload)
        payload = adapter.adapt_payload(setup_spec, raw_payload, phase="setup") if raw_payload is not None else None
        status, ms, _ = request_once(
            method,
            url,
            expand_headers(engine.get("headers", {})),
            payload,
            timeout,
            setup_spec.get("content_type"),
        )
        latencies.append(ms)
        status_counts[str(status)] = status_counts.get(str(status), 0) + 1
        outcome = classify_status(status, policy)
        if outcome == "success":
            success_count += 1
        elif outcome == "unsupported":
            unsupported_count += 1
        elif outcome == "warning":
            warning_count += 1
        elif outcome == "timeout":
            timeout_count += 1
            fail_count += 1
        else:
            fail_count += 1

    total = len(ids)
    return {
        "total_requests": total,
        "pass_requests": success_count,
        "pass_rate": (success_count / total) if total else 0.0,
        "failure_rate": (fail_count / total) if total else 0.0,
        "unsupported_requests": unsupported_count,
        "warning_requests": warning_count,
        "timeout_requests": timeout_count,
        "status_counts": status_counts,
        "latency_ms_avg": statistics.mean(latencies) if latencies else 0.0,
    }


def run_scenario(
    engine: dict[str, Any],
    scenario: dict[str, Any],
    patient_ids: list[str],
    concurrency: int,
    timeout: int,
    adapter: EngineAdapter,
    warmup_requests: int = 0,
    requests_per_patient: int = 1,
    repetitions: int = 1,
    selectivity: float = 0.2,
    strict_mode: bool = False,
    suite_defaults: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base_method = scenario["method"]
    policy = resolve_http_policy_for_spec(scenario, strict_mode, suite_defaults=suite_defaults)
    headers = expand_headers(engine.get("headers", {}))
    conformance_only = is_conformance_scenario(scenario)
    endpoint_used: dict[str, Any] | None = None

    if conformance_only:
        total_requests = max(1, int(repetitions))
        status_counts: dict[str, int] = {}
        latencies: list[float] = []
        success_count = 0
        unsupported_count = 0
        warning_count = 0
        timeout_count = 0
        fail_count = 0

        patient_id = patient_ids[0] if patient_ids else "p1"
        for _ in range(total_requests):
            raw_payload = prepare_payload(
                scenario,
                patient_id,
                adapter,
                selectivity=selectivity,
                phase="main",
                apply_adapter=False,
            )
            if raw_payload is None:
                raw_payload = adapter.payload_from_query(scenario, patient_id, phase="main")
            method = adapter.adapt_method(scenario, base_method, phase="main", payload=raw_payload)
            url = endpoint_url(engine, scenario, patient_id, adapter, phase="main", payload=raw_payload)
            payload = adapter.adapt_payload(scenario, raw_payload, phase="main") if raw_payload is not None else None
            if endpoint_used is None:
                endpoint_used = {
                    "selected_method": base_method,
                    "selected_path": scenario.get("path"),
                    "effective_method": method,
                    "effective_path": urllib.parse.urlsplit(url).path,
                    "source": scenario.get("_endpoint_source", "scenario_default"),
                    "derived_from_conf": scenario.get("_endpoint_conf_id"),
                    "operation": scenario.get("_endpoint_operation"),
                }
            status, ms, _ = request_once(method, url, headers, payload, timeout, scenario.get("content_type"))
            latencies.append(ms)
            status_counts[str(status)] = status_counts.get(str(status), 0) + 1
            outcome = classify_status(status, policy)
            if outcome == "success":
                success_count += 1
            elif outcome == "unsupported":
                unsupported_count += 1
            elif outcome == "warning":
                warning_count += 1
                fail_count += 1
            elif outcome == "timeout":
                timeout_count += 1
                fail_count += 1
            else:
                fail_count += 1

        passed = success_count == total_requests
        conformance_label = "PASS"
        conformance_note = ""
        if fail_count > 0:
            conformance_label = "FAIL"
            if timeout_count > 0:
                conformance_note = "timeout/request crash (included in FAIL)"
            elif warning_count > 0:
                conformance_note = "4xx warning: server/config requires attention"
            else:
                conformance_note = "unexpected failure status"
        elif unsupported_count > 0:
            conformance_label = "UNSUPPORTED"
            conformance_note = "HTTP 422 unsupported"
        elif warning_count > 0:
            conformance_label = "WARNING"
            conformance_note = "4xx warning: server/config requires attention"
        return {
            "scenario_id": scenario["id"],
            "scenario_name": scenario["name"],
            "kind": scenario["kind"],
            "test_type": "conformance",
            "required_capabilities": scenario.get("required_capabilities", []),
            "setup": None,
            "total_requests": total_requests,
            "pass_requests": success_count,
            "pass_rate": (success_count / total_requests) if total_requests else 0.0,
            "failure_rate": (fail_count / total_requests) if total_requests else 0.0,
            "http_pass_requests": success_count,
            "correct_pass_requests": 0,
            "correct_pass_rate": 0.0,
            "validate_eligible_requests": 0,
            "timed_requests": 0,
            "timed_ok_requests": 0,
            "unsupported_requests": unsupported_count,
            "warning_requests": warning_count,
            "timeout_requests": timeout_count,
            "fail_requests": fail_count,
            "status_counts": status_counts,
            "latency_ms": None,
            "requests_per_second": 0.0,
            "all_latency_ms_avg": statistics.mean(latencies) if latencies else 0.0,
            "endpoint_used": endpoint_used,
            "conformance_pass": passed,
            "conformance_status": conformance_label,
            "conformance_note": conformance_note,
        }

    setup_result = setup_for_scenario(
        engine,
        scenario,
        patient_ids,
        timeout,
        adapter,
        selectivity=selectivity,
        strict_mode=strict_mode,
        suite_defaults=suite_defaults,
    )

    warmup_count = max(0, min(int(warmup_requests), len(patient_ids)))
    if warmup_count:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            warmup_tasks = []
            for patient_id in patient_ids[:warmup_count]:
                raw_payload = prepare_payload(
                    scenario,
                    patient_id,
                    adapter,
                    selectivity=selectivity,
                    phase="main",
                    apply_adapter=False,
                )
                if raw_payload is None:
                    raw_payload = adapter.payload_from_query(scenario, patient_id, phase="main")
                method = adapter.adapt_method(scenario, base_method, phase="main", payload=raw_payload)
                url = endpoint_url(engine, scenario, patient_id, adapter, phase="main", payload=raw_payload)
                payload = adapter.adapt_payload(scenario, raw_payload, phase="main") if raw_payload is not None else None
                if endpoint_used is None:
                    endpoint_used = {
                        "selected_method": base_method,
                        "selected_path": scenario.get("path"),
                        "effective_method": method,
                        "effective_path": urllib.parse.urlsplit(url).path,
                        "source": scenario.get("_endpoint_source", "scenario_default"),
                        "derived_from_conf": scenario.get("_endpoint_conf_id"),
                        "operation": scenario.get("_endpoint_operation"),
                    }
                warmup_tasks.append(
                    pool.submit(request_once, method, url, headers, payload, timeout, scenario.get("content_type"))
                )
            for fut in as_completed(warmup_tasks):
                fut.result()

    if bool(scenario.get("restart_after_setup", False)):
        restarted = restart_engine_container(engine)
        if not restarted:
            print(f"{scenario['id']}: requested restart_after_setup but container restart was not performed")

    all_latencies: list[float] = []
    timed_latencies: list[float] = []
    per_run_p95: list[float] = []
    status_counts: dict[str, int] = {}
    http_pass = 0
    correct_pass = 0
    validate_eligible = 0
    timed_ok = 0
    unsupported = 0
    warning = 0
    timeout_count = 0
    fail = 0
    incorrect_result_failures = 0
    incorrect_result_notes: list[str] = []

    main_started = time.perf_counter()
    total_tasks = 0
    for _run_idx in range(max(1, int(repetitions))):
        tasks = []
        timed_latencies_this_run: list[float] = []
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            for patient_id in patient_ids:
                for _ in range(max(1, requests_per_patient)):
                    raw_payload = prepare_payload(
                        scenario,
                        patient_id,
                        adapter,
                        selectivity=selectivity,
                        phase="main",
                        apply_adapter=False,
                    )
                    if raw_payload is None:
                        raw_payload = adapter.payload_from_query(scenario, patient_id, phase="main")
                    method = adapter.adapt_method(scenario, base_method, phase="main", payload=raw_payload)
                    url = endpoint_url(engine, scenario, patient_id, adapter, phase="main", payload=raw_payload)
                    payload = adapter.adapt_payload(scenario, raw_payload, phase="main") if raw_payload is not None else None
                    if endpoint_used is None:
                        endpoint_used = {
                            "selected_method": base_method,
                            "selected_path": scenario.get("path"),
                            "effective_method": method,
                            "effective_path": urllib.parse.urlsplit(url).path,
                            "source": scenario.get("_endpoint_source", "scenario_default"),
                            "derived_from_conf": scenario.get("_endpoint_conf_id"),
                            "operation": scenario.get("_endpoint_operation"),
                        }
                    tasks.append(
                        pool.submit(request_once, method, url, headers, payload, timeout, scenario.get("content_type"))
                    )
            total_tasks += len(tasks)
            for fut in as_completed(tasks):
                status, ms, raw = fut.result()
                all_latencies.append(ms)
                key = str(status)
                status_counts[key] = status_counts.get(key, 0) + 1
                status_class = classify_status(status, policy)

                if status_class == "unsupported":
                    unsupported += 1
                    continue
                if status_class == "warning":
                    warning += 1
                    fail += 1
                    continue
                if status_class == "timeout":
                    timeout_count += 1
                    fail += 1
                    continue
                if status_class != "success":
                    fail += 1
                    continue

                http_pass += 1
                valid, eligible, validation_failures = run_response_validators(raw, scenario.get("_expected_config"), status)
                if eligible:
                    validate_eligible += 1
                    if valid:
                        correct_pass += 1
                        timed_ok += 1
                        timed_latencies.append(ms)
                        timed_latencies_this_run.append(ms)
                    else:
                        fail += 1
                        incorrect_result_failures += 1
                        for vf in validation_failures:
                            sv = str(vf).strip()
                            if sv and sv not in incorrect_result_notes:
                                incorrect_result_notes.append(sv)
                else:
                    # If no explicit validation window is configured, allow success statuses to be timed.
                    if scenario.get("_expected_config") is None:
                        correct_pass += 1
                        timed_ok += 1
                        timed_latencies.append(ms)
                        timed_latencies_this_run.append(ms)
                    else:
                        unsupported += 1
        if timed_latencies_this_run:
            per_run_p95.append(percentile(timed_latencies_this_run, 0.95))
    main_elapsed_seconds = time.perf_counter() - main_started

    total = total_tasks
    requests_per_second = (total / main_elapsed_seconds) if main_elapsed_seconds > 0 else 0.0
    if strict_mode and setup_result is not None and setup_result.get("pass_rate", 0.0) < 1.0:
        fail += timed_ok
        timed_ok = 0
        timed_latencies = []
    timed_requests = len(timed_latencies)
    latency_ms = (
        {
            "min": min(timed_latencies) if timed_latencies else 0.0,
            "avg": statistics.mean(timed_latencies) if timed_latencies else 0.0,
            "p50": percentile(timed_latencies, 0.50),
            "p95": percentile(timed_latencies, 0.95),
            "p99": percentile(timed_latencies, 0.99),
            "max": max(timed_latencies) if timed_latencies else 0.0,
            "avg_p95_over_repetitions": statistics.mean(per_run_p95) if per_run_p95 else percentile(timed_latencies, 0.95),
        }
        if timed_requests > 0
        else None
    )
    return {
        "scenario_id": scenario["id"],
        "scenario_name": scenario["name"],
        "kind": scenario["kind"],
        "test_type": str(scenario.get("test_type", "capability")),
        "required_capabilities": scenario.get("required_capabilities", []),
        "setup": setup_result,
        "total_requests": total,
        "pass_requests": timed_ok,
        "pass_rate": (timed_ok / total) if total else 0.0,
        "failure_rate": (fail / total) if total else 0.0,
        "http_pass_requests": http_pass,
        "correct_pass_requests": correct_pass,
        "correct_pass_rate": (correct_pass / validate_eligible) if validate_eligible else 0.0,
        "validate_eligible_requests": validate_eligible,
        "timed_requests": timed_requests,
        "timed_ok_requests": timed_ok,
        "unsupported_requests": unsupported,
        "warning_requests": warning,
        "timeout_requests": timeout_count,
        "fail_requests": fail,
        "status_counts": status_counts,
        "latency_ms": latency_ms,
        "requests_per_second": requests_per_second,
        "all_latency_ms_avg": statistics.mean(all_latencies) if all_latencies else 0.0,
        "endpoint_used": endpoint_used,
        "incorrect_result_failures": incorrect_result_failures,
        "incorrect_result_notes": incorrect_result_notes[:5],
    }


def build_patient_ids(scale: int) -> list[str]:
    return [f"p{i}" for i in range(1, scale + 1)]


def random_suffix(n: int = 6) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def supports_scenario(engine: dict[str, Any], scenario: dict[str, Any]) -> bool:
    needed = set(scenario.get("required_capabilities", []))
    have = set(engine.get("capabilities", []))
    return needed.issubset(have)


def get_git_commit() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out or None
    except Exception:  # noqa: BLE001
        return None


def wait_for_engine_health(engine: dict[str, Any], timeout_seconds: int = 90) -> bool:
    docker = engine.get("docker")
    if not isinstance(docker, dict):
        return True
    health_path = docker.get("health_path")
    if not isinstance(health_path, str) or not health_path:
        return True
    base_url = str(engine.get("base_url", "")).rstrip("/")
    if not base_url:
        return False
    health_url = base_url + (health_path if health_path.startswith("/") else f"/{health_path}")

    deadline = time.time() + max(1, timeout_seconds)
    while time.time() < deadline:
        try:
            req = urllib.request.Request(health_url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                code = int(getattr(resp, "status", 0) or 0)
                if 200 <= code < 500:
                    return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(2)
    return False


def restart_engine_container(engine: dict[str, Any]) -> bool:
    docker = engine.get("docker")
    if not isinstance(docker, dict):
        return False
    if not docker.get("enabled", False):
        return False
    container_name = docker.get("container_name")
    if not isinstance(container_name, str) or not container_name:
        return False
    try:
        subprocess.run(["docker", "stop", container_name], check=True, text=True, capture_output=True)
        subprocess.run(["docker", "start", container_name], check=True, text=True, capture_output=True)
        return wait_for_engine_health(engine)
    except Exception:  # noqa: BLE001
        return False


def write_markdown_summary(report: dict[str, Any], out_md: Path) -> None:
    lines = []
    lines.append(f"# CQF Benchmark Report: {report['run_id']}")
    lines.append("")
    lines.append(f"- suite: `{report['suite_id']}`")
    lines.append(f"- scale: `{report['scale']}`")
    lines.append(f"- concurrency: `{report['concurrency']}`")
    lines.append(f"- started_utc: `{report.get('started_utc', 'n/a')}`")
    lines.append(f"- started_local: `{report.get('started_local', 'n/a')}`")
    lines.append(f"- ended_utc: `{report.get('ended_utc', 'n/a')}`")
    lines.append(f"- ended_local: `{report.get('ended_local', 'n/a')}`")
    lines.append(f"- duration_seconds: `{report['duration_seconds']:.2f}`")
    lines.append(f"- score_mode: `{report.get('score_mode', 'compat')}`")
    lines.append(f"- repetitions: `{report.get('repetitions', 1)}`")
    lines.append("")

    engines = report.get("engines", [])
    engine_names = [e["name"] for e in engines]

    conformance_rows: dict[str, dict[str, Any]] = {}
    capability_rows: dict[str, dict[str, Any]] = {}
    scenario_names: dict[str, str] = {}

    for engine in engines:
        for r in engine.get("results", []):
            sid = r["scenario_id"]
            scenario_names[sid] = r.get("scenario_name", sid)
            if r.get("test_type") == "conformance" or str(sid).startswith("CONF"):
                conformance_rows.setdefault(sid, {})[engine["name"]] = r
            else:
                capability_rows.setdefault(sid, {})[engine["name"]] = r

    def endpoint_note(r: dict[str, Any]) -> str:
        ep = r.get("endpoint_used")
        if not isinstance(ep, dict):
            return ""
        eff_method = ep.get("effective_method")
        eff_path = ep.get("effective_path")
        sel_method = ep.get("selected_method")
        sel_path = ep.get("selected_path")
        source = str(ep.get("source", ""))
        conf_id = ep.get("derived_from_conf")
        base = ""
        if isinstance(eff_method, str) and isinstance(eff_path, str):
            base = f"{eff_method} {eff_path}"
        elif isinstance(sel_method, str) and isinstance(sel_path, str):
            base = f"{sel_method} {sel_path}"
        if base and source == "dynamic_conf" and isinstance(conf_id, str):
            base += f" via {conf_id}"
        return base

    def http_status_note(r: dict[str, Any]) -> str:
        status_counts = r.get("status_counts")
        if not isinstance(status_counts, dict) or not status_counts:
            return ""
        codes: list[int] = []
        for k, v in status_counts.items():
            try:
                code = int(k)
                cnt = int(v)
            except (TypeError, ValueError):
                continue
            if cnt > 0:
                codes.append(code)
        if not codes:
            return ""
        uniq = sorted(set(codes))
        if len(uniq) == 1:
            return f"HTTP {uniq[0]}"
        return "HTTP " + ", ".join(str(c) for c in uniq)

    if conformance_rows:
        lines.append("## Conformance Matrix")
        lines.append("")
        header_cols = ["Scenario", "Intent"]
        divider_cols = ["---", "---"]
        for en in engine_names:
            header_cols.extend([f"{en} Result", f"{en} Time", f"{en} Note"])
            divider_cols.extend(["---", "---", "---"])
        header = "| " + " | ".join(header_cols) + " |"
        divider = "| " + " | ".join(divider_cols) + " |"
        lines.append(header)
        lines.append(divider)
        for sid in sorted(conformance_rows.keys()):
            row = [sid, scenario_names.get(sid, sid)]
            for en in engine_names:
                r = conformance_rows[sid].get(en)
                if not r:
                    row.extend(["FAIL", "", "not executed"])
                    continue
                status = str(r.get("conformance_status", "FAIL")).upper()
                result = "PASS" if status == "PASS" else "FAIL"
                note_parts: list[str] = []
                if status == "UNSUPPORTED":
                    note_parts.append("unsupported")
                elif status == "WARNING":
                    note_parts.append("warning")
                else:
                    note = str(r.get("conformance_note", ""))
                    if note:
                        note_parts.append(note)
                ep = endpoint_note(r)
                if ep:
                    note_parts.append(f"endpoint: {ep}")
                hs = http_status_note(r)
                if hs:
                    note_parts.append(hs)
                row.extend([result, "", "; ".join(note_parts) if note_parts else ""])
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    if capability_rows:
        lines.append("## Capability + Performance Matrix")
        lines.append("")
        header_cols = ["Scenario", "Intent"]
        divider_cols = ["---", "---"]
        for en in engine_names:
            header_cols.extend([f"{en} Result", f"{en} Time", f"{en} Note"])
            divider_cols.extend(["---", "---", "---"])
        header = "| " + " | ".join(header_cols) + " |"
        divider = "| " + " | ".join(divider_cols) + " |"
        lines.append(header)
        lines.append(divider)
        for sid in sorted(capability_rows.keys()):
            row = [sid, scenario_names.get(sid, sid)]
            for en in engine_names:
                r = capability_rows[sid].get(en)
                if not r:
                    row.extend(["FAIL", "", "not executed"])
                    continue
                status_counts = r.get("status_counts", {})
                has_non_200_status = False
                if isinstance(status_counts, dict):
                    for k, v in status_counts.items():
                        try:
                            code = int(k)
                            count = int(v)
                        except (TypeError, ValueError):
                            continue
                        if count > 0 and code != 200:
                            has_non_200_status = True
                            break

                is_pass = (
                    int(r.get("fail_requests", 0)) == 0
                    and int(r.get("unsupported_requests", 0)) == 0
                    and int(r.get("warning_requests", 0)) == 0
                    and int(r.get("timeout_requests", 0)) == 0
                    and int(r.get("timed_ok_requests", 0)) > 0
                    and not has_non_200_status
                )
                result = "PASS" if is_pass else "FAIL"
                latency = r.get("latency_ms")
                time_metric = None
                if isinstance(latency, dict):
                    time_metric = latency.get("avg_p95_over_repetitions", latency.get("p95"))
                time_cell = f"{float(time_metric):.1f}ms" if (is_pass and time_metric is not None and r.get("timed_requests", 0)) else ""
                note_parts: list[str] = []
                if int(r.get("incorrect_result_failures", 0)) > 0:
                    note_parts.append("incorrect result")
                    details = r.get("incorrect_result_notes", [])
                    if isinstance(details, list) and details:
                        note_parts.append(str(details[0]))
                if int(r.get("unsupported_requests", 0)) > 0:
                    note_parts.append(f"unsupported={r.get('unsupported_requests', 0)}")
                if int(r.get("warning_requests", 0)) > 0:
                    note_parts.append(f"warning={r.get('warning_requests', 0)}")
                if int(r.get("timeout_requests", 0)) > 0:
                    note_parts.append(f"timeout={r.get('timeout_requests', 0)}")
                ep = endpoint_note(r)
                if ep:
                    note_parts.append(f"endpoint: {ep}")
                hs = http_status_note(r)
                if hs:
                    note_parts.append(hs)
                row.extend([result, time_cell, "; ".join(note_parts)])
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    out_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CQF engine comparison benchmark")
    parser.add_argument("--engines", type=Path, default=Path("bench/config/engines.example.yaml"))
    parser.add_argument("--suite", type=Path, default=Path("bench/scenarios/tpcqf/suite.yaml"))
    parser.add_argument("--scale", type=int, required=True, help="Number of patients (e.g., 100, 10000, 1000000)")
    parser.add_argument("--out", type=Path, default=Path("results"))
    parser.add_argument("--concurrency", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument(
        "--selectivity",
        type=float,
        default=0.2,
        help="Target fraction of matching rows in selectivity-sensitive payloads (0.0-1.0). Default 20%%.",
    )
    parser.add_argument("--filter-engine", action="append", default=[], help="Run only selected engine(s)")
    parser.add_argument(
        "--score-mode",
        choices=["compat", "strict-2xx"],
        default="compat",
        help="compat uses scenario expected_http; strict-2xx requires 2xx for setup and main calls",
    )
    parser.add_argument(
        "--run-phase",
        choices=["full", "load", "execute"],
        default="full",
        help="full=setup+execute, load=preload data only, execute=execute tests only (no setup)",
    )
    parser.add_argument(
        "--generated-data-root",
        type=Path,
        default=None,
        help="Root directory of pre-generated payloads from generate_scenario_data.py",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=1,
        help="Number of repeated scenario execution runs to average timing over",
    )
    args = parser.parse_args()

    engines_doc = load_config(args.engines)
    suite, scenarios, suite_files = load_suite_with_scenarios(args.suite)
    if args.generated_data_root is not None:
        root = args.generated_data_root
        if args.run_phase == "load":
            scenarios = apply_generated_data_root_overrides(scenarios, root, use_setup_phase=True, use_main_phase=False)
        elif args.run_phase == "execute":
            scenarios = apply_generated_data_root_overrides(scenarios, root, use_setup_phase=False, use_main_phase=True)
        else:
            scenarios = apply_generated_data_root_overrides(scenarios, root, use_setup_phase=True, use_main_phase=True)

    defaults = suite.get("defaults", {})
    concurrency = args.concurrency or defaults.get("concurrency", 16)
    timeout = args.timeout or defaults.get("timeout_seconds", 30)

    all_engines = engines_doc.get("engines", [])
    if args.filter_engine:
        engines = [e for e in all_engines if e["name"] in set(args.filter_engine)]
    else:
        engines = all_engines

    enabled_engines = []
    for e in engines:
        if e.get("disabled", False):
            reason = e.get("disabled_reason", "engine disabled in config")
            print(f"Skipping disabled engine {e['name']}: {reason}")
            continue
        enabled_engines.append(e)
    engines = enabled_engines

    if not engines:
        print("No enabled engines selected")
        return 1

    if args.run_phase == "load":
        patient_ids = build_patient_ids(args.scale)
        had_failures = False
        for engine in engines:
            engine_base = engine.get("cqf_base_path", "")
            adapter_name = engine.get("adapter", "generic-cqf")
            adapter = ADAPTERS.get(adapter_name, ADAPTERS["generic-cqf"])
            print(f"\n=== Engine (load-only): {engine['name']} ({engine['base_url']}{engine_base}) adapter={adapter_name} ===")
            preload_required_libraries(engine, scenarios, timeout)
            preload_scenario_cql_libraries(engine, scenarios, timeout)
            preload_required_measures(engine, scenarios, timeout)
            preload_standard_valuesets(engine, timeout)

            ordered_scenarios = [s for s in scenarios if is_conformance_scenario(s)] + [
                s for s in scenarios if not is_conformance_scenario(s)
            ]
            for scenario in ordered_scenarios:
                if is_conformance_scenario(scenario):
                    continue
                if not supports_scenario(engine, scenario):
                    needed = set(scenario.get("required_capabilities", []))
                    missing = sorted(list(needed - set(engine.get("capabilities", []))))
                    missing_capability = missing[0] if missing else "unknown"
                    print(f"{scenario['id']} {scenario['name']}: skipped (missing {missing_capability})")
                    continue
                if not isinstance(scenario.get("setup"), dict):
                    print(f"{scenario['id']} {scenario['name']}: skipped (no setup block)")
                    continue
                setup_result = setup_for_scenario(
                    engine,
                    scenario,
                    patient_ids,
                    timeout,
                    adapter,
                    selectivity=resolve_selectivity(scenario, defaults, args.selectivity),
                    strict_mode=(args.score_mode == "strict-2xx"),
                    suite_defaults=suite,
                )
                if setup_result is None:
                    print(f"{scenario['id']} {scenario['name']}: skipped (setup returned no result)")
                    continue
                pass_rate = float(setup_result.get("pass_rate", 0.0))
                status_counts = setup_result.get("status_counts", {})
                print(
                    f"{scenario['id']} {scenario['name']}: setup_pass={pass_rate:.3f} "
                    f"unsupported={setup_result.get('unsupported_requests', 0)} "
                    f"warning={setup_result.get('warning_requests', 0)} "
                    f"timeout={setup_result.get('timeout_requests', 0)} "
                    f"status={status_counts}"
                )
                if pass_rate < 1.0:
                    had_failures = True
        return 1 if had_failures else 0

    patient_ids = build_patient_ids(args.scale)
    suite_hash_input = []
    for fp in sorted({str(p) for p in suite_files}):
        try:
            suite_hash_input.append(f"{fp}:{file_sha256(Path(fp))}")
        except Exception:  # noqa: BLE001
            continue
    suite_hash = sha256_hex("\n".join(suite_hash_input)) if suite_hash_input else None

    run_id = f"{suite.get('suite_id', 'suite')}_{args.scale}_{random_suffix()}"
    started = time.time()
    started_dt_utc = datetime.now(timezone.utc)
    started_dt_local = started_dt_utc.astimezone()

    report = {
        "run_id": run_id,
        "suite_id": suite.get("suite_id"),
        "suite_file": str(args.suite),
        "suite_hash": suite_hash,
        "scenario_files_hashed": sorted({str(p) for p in suite_files}),
        "engines_file": str(args.engines),
        "git_commit": get_git_commit(),
        "scale": args.scale,
        "concurrency": concurrency,
        "timeout_seconds": timeout,
        "score_mode": args.score_mode,
        "repetitions": max(1, int(args.repetitions)),
        "run_phase": args.run_phase,
        "generated_data_root": str(args.generated_data_root) if args.generated_data_root is not None else None,
        "started_epoch": started,
        "started_utc": started_dt_utc.isoformat(),
        "started_local": started_dt_local.isoformat(),
        "engines": [],
    }

    for engine in engines:
        engine_base = engine.get("cqf_base_path", "")
        adapter_name = engine.get("adapter", "generic-cqf")
        adapter = ADAPTERS.get(adapter_name, ADAPTERS["generic-cqf"])

        print(f"\n=== Engine: {engine['name']} ({engine['base_url']}{engine_base}) adapter={adapter_name} ===")
        engine_results = []
        skipped = []
        conf_results_by_id: dict[str, dict[str, Any]] = {}

        preload_required_libraries(engine, scenarios, timeout)
        preload_scenario_cql_libraries(engine, scenarios, timeout)
        preload_required_measures(engine, scenarios, timeout)
        preload_standard_valuesets(engine, timeout)

        ordered_scenarios = [s for s in scenarios if is_conformance_scenario(s)] + [
            s for s in scenarios if not is_conformance_scenario(s)
        ]
        for scenario in ordered_scenarios:
            scenario_for_run = scenario
            if not is_conformance_scenario(scenario):
                scenario_for_run = apply_dynamic_cap_endpoint(scenario, conf_results_by_id)
                if args.run_phase == "execute":
                    scenario_for_run = copy.deepcopy(scenario_for_run)
                    scenario_for_run.pop("setup", None)
                    scenario_for_run.pop("restart_after_setup", None)

            if not supports_scenario(engine, scenario_for_run):
                needed = set(scenario.get("required_capabilities", []))
                missing = sorted(list(needed - set(engine.get("capabilities", []))))
                missing_capability = missing[0] if missing else "unknown"
                skipped.append({"id": scenario["id"], "missing_capability": missing_capability})
                print(f"{scenario['id']} {scenario['name']}: skipped (missing {missing_capability})")
                continue

            result = run_scenario(
                engine,
                scenario_for_run,
                patient_ids,
                concurrency,
                timeout,
                adapter,
                warmup_requests=defaults.get("warmup_requests", 0),
                requests_per_patient=resolve_requests_per_patient(scenario, defaults),
                repetitions=max(1, int(args.repetitions)),
                selectivity=resolve_selectivity(scenario, defaults, args.selectivity),
                strict_mode=(args.score_mode == "strict-2xx"),
                suite_defaults=suite,
            )
            engine_results.append(result)
            if is_conformance_scenario(scenario):
                conf_results_by_id[scenario["id"]] = result
            setup_msg = ""
            if result.get("setup"):
                setup_msg = f" setup_pass={result['setup']['pass_rate']:.3f}"
            p95_display = f"{result['latency_ms']['p95']:.1f}ms" if result.get("latency_ms") is not None else "n/a"
            endpoint_msg = ""
            endpoint_used = result.get("endpoint_used")
            if isinstance(endpoint_used, dict):
                src = str(endpoint_used.get("source", "scenario_default"))
                selected_method = endpoint_used.get("selected_method")
                selected_path = endpoint_used.get("selected_path")
                if isinstance(selected_method, str) and isinstance(selected_path, str):
                    endpoint_msg = f" endpoint={selected_method} {selected_path}"
                    if src == "dynamic_conf":
                        conf_id = endpoint_used.get("derived_from_conf")
                        if isinstance(conf_id, str):
                            endpoint_msg += f" via={conf_id}"
            print(
                f"{scenario['id']} {scenario['name']}: timed_ok={result.get('timed_ok_requests', 0)} "
                f"unsupported={result.get('unsupported_requests', 0)} warning={result.get('warning_requests', 0)} "
                f"timeout={result.get('timeout_requests', 0)} fail={result.get('fail_requests', 0)} "
                f"p95={p95_display} "
                f"status={result['status_counts']}{setup_msg}{endpoint_msg}"
            )

        report["engines"].append({
            "name": engine["name"],
            "adapter": adapter_name,
            "base_url": engine["base_url"],
            "cqf_base_path": engine_base,
            "data_base_path": engine.get("data_base_path", engine_base),
            "capabilities": engine.get("capabilities", []),
            "results": engine_results,
            "skipped": skipped,
        })

    report["ended_epoch"] = time.time()
    ended_dt_utc = datetime.now(timezone.utc)
    ended_dt_local = ended_dt_utc.astimezone()
    report["ended_utc"] = ended_dt_utc.isoformat()
    report["ended_local"] = ended_dt_local.isoformat()
    report["duration_seconds"] = report["ended_epoch"] - report["started_epoch"]

    args.out.mkdir(parents=True, exist_ok=True)
    out_json = args.out / f"{run_id}.json"
    out_md = args.out / f"{run_id}.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown_summary(report, out_md)

    print(f"\nWrote report JSON: {out_json}")
    print(f"Wrote report MD:   {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
