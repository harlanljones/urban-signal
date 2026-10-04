"""Fail-closed source contracts and projected Socrata permit acquisition."""
from __future__ import annotations

import re
import time
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Self

import httpx

_SOQL_FIELD = re.compile(r"^:?[A-Za-z_][A-Za-z0-9_]*$")
_UTC_MILLISECOND = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
_REQUIRED_GUARANTEES = (
    "identity_unique_nonnull", "row_id_persistent", "update_timestamp_semantics",
    "deterministic_keyset_pagination", "bounded_snapshot_consistency",
    "complete_reconciliation", "replacement_detection", "request_limits_known",
)


class SourceNotReady(RuntimeError):
    """The contract lacks verified mandatory source guarantees."""


class SourceProtocolError(RuntimeError):
    """A response violates the declared projection or pagination protocol."""


@dataclass(frozen=True)
class SourceContract:
    source_id: str
    endpoint: str
    dataset_id: str
    version: str
    fields: tuple[str, ...]
    identity_fields: tuple[str, ...]
    source_row_id_field: str
    event_time_field: str
    update_time_field: str
    page_size_max: int
    query_contract: dict[str, Any]
    guarantees: dict[str, dict[str, str]]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SourceContract:
        if not isinstance(data, Mapping):
            raise TypeError("source contract must be a mapping")
        try:
            fields_value = data["fields"]
            identities_value = data["identity_fields"]
            if not isinstance(fields_value, list) or any(not isinstance(f, str) for f in fields_value):
                raise ValueError("fields must be a list of strings")
            if not isinstance(identities_value, list) or any(not isinstance(f, str) for f in identities_value):
                raise ValueError("identity_fields must be a list of strings")
            fields = tuple(fields_value)
            identities = tuple(identities_value)
            string_names = (
                "source_id", "endpoint", "dataset_id", "version", "source_row_id_field",
                "event_time_field", "update_time_field",
            )
            for name in string_names:
                value = data[name]
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"{name} must be a non-empty string")
            page_size = data["page_size_max"]
            if isinstance(page_size, bool) or not isinstance(page_size, int) or page_size <= 0:
                raise ValueError("page_size_max must be a positive integer")
            if not isinstance(data["query_contract"], Mapping):
                raise TypeError("query_contract must be a mapping")
            if not isinstance(data["guarantees"], Mapping):
                raise TypeError("guarantees must be a mapping")
            query = dict(data["query_contract"])
            guarantees = {}
            for name, value in data["guarantees"].items():
                if not isinstance(name, str) or not isinstance(value, Mapping):
                    raise TypeError("guarantees must map string names to evidence mappings")
                guarantees[name] = dict(value)
            result = cls(
                source_id=data["source_id"], endpoint=data["endpoint"],
                dataset_id=data["dataset_id"], version=data["version"],
                fields=fields, identity_fields=identities,
                source_row_id_field=data["source_row_id_field"],
                event_time_field=data["event_time_field"], update_time_field=data["update_time_field"],
                page_size_max=page_size, query_contract=query, guarantees=guarantees,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid source contract: {exc}") from exc
        if not result.endpoint.startswith("https://"):
            raise ValueError("source endpoint must use HTTPS")
        if not fields or len(set(fields)) != len(fields) or "*" in fields:
            raise ValueError("projection fields must be explicit, unique, and cannot project *")
        if any(not _SOQL_FIELD.fullmatch(field) for field in fields):
            raise ValueError("projection contains an unsafe SoQL field identifier")
        if not identities or any(f not in fields for f in identities):
            raise ValueError("identity fields must be included in the explicit projection")
        if "job__" in identities:
            raise ValueError("job__ alone is not a valid permit identity")
        for field in (result.source_row_id_field, result.event_time_field, result.update_time_field):
            if field not in fields:
                raise ValueError(f"required field {field!r} is missing from projection")
        if not 1 <= result.page_size_max <= 50000:
            raise ValueError("page_size_max must be between 1 and 50000")
        if query.get("pagination") != "keyset":
            raise ValueError("only explicitly declared keyset pagination is supported")
        if query.get("timestamp_precision") != "millisecond":
            raise ValueError("only millisecond update timestamp precision is supported")
        if tuple(query.get("ordering_fields", ())) != (result.update_time_field, result.source_row_id_field):
            raise ValueError("ordering fields must be update timestamp then source row id")
        if query.get("status") not in {"verified", "unsupported", "unverified"}:
            raise ValueError("query_contract must record a valid status")
        for name, guarantee in guarantees.items():
            if guarantee.get("status") not in {"verified", "unsupported", "unverified"}:
                raise ValueError(f"guarantee {name!r} has invalid status")
            if not isinstance(guarantee.get("evidence"), str) or not guarantee["evidence"].strip():
                raise ValueError(f"guarantee {name!r} must record evidence")
        return result

    def assert_ready(self) -> None:
        missing = [name for name in _REQUIRED_GUARANTEES if self.guarantees.get(name, {}).get("status") != "verified"]
        if self.query_contract.get("status") != "verified":
            missing.append("query_contract")
        if missing:
            raise SourceNotReady("source contract is not ready; unverified required guarantees: " + ", ".join(missing))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id, "endpoint": self.endpoint, "dataset_id": self.dataset_id,
            "version": self.version, "fields": list(self.fields), "identity_fields": list(self.identity_fields),
            "source_row_id_field": self.source_row_id_field, "event_time_field": self.event_time_field,
            "update_time_field": self.update_time_field, "page_size_max": self.page_size_max,
            "query_contract": dict(self.query_contract),
            "guarantees": {k: dict(v) for k, v in self.guarantees.items()},
        }


@dataclass(frozen=True)
class SourcePage:
    records: list[dict[str, Any]]
    next_cursor: dict[str, str] | None
    exhausted: bool
    complete: bool
    row_count: int
    query_bounds: dict[str, Any]
    reconciliation_complete: bool = False


class SocrataPermitSource:
    def __init__(self, contract: SourceContract, client: httpx.Client | None = None, *,
                 page_size: int = 1000, max_attempts: int = 3, timeout: float = 30.0,
                 retry_delay: float = 0.05) -> None:
        if not 1 <= page_size <= contract.page_size_max:
            raise ValueError("page_size exceeds contract limit")
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self.contract, self.page_size, self.max_attempts = contract, page_size, max_attempts
        self.retry_delay = max(0.0, retry_delay)
        self._owns_client = client is None
        self.client = client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def _get(self, params: dict[str, str]) -> list[dict[str, Any]]:
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self.client.get(self.contract.endpoint, params=params)
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < self.max_attempts:
                        time.sleep(self.retry_delay * 2 ** (attempt - 1))
                        continue
                    raise SourceProtocolError(f"source request failed after {attempt} attempts: HTTP {response.status_code}")
                response.raise_for_status()
                body = response.json()
                if not isinstance(body, list) or any(not isinstance(row, dict) for row in body):
                    raise SourceProtocolError("Socrata response must be a JSON array of objects")
                return body
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt == self.max_attempts:
                    raise SourceProtocolError(f"source request failed after {attempt} attempts: {exc}") from exc
                time.sleep(self.retry_delay * 2 ** (attempt - 1))
            except httpx.HTTPStatusError as exc:
                raise SourceProtocolError(f"source returned HTTP {exc.response.status_code}") from exc
        raise SourceProtocolError(f"source request failed after {self.max_attempts} attempts")

    @staticmethod
    def _validate_update_timestamp(value: Any) -> str:
        if not isinstance(value, str) or not _UTC_MILLISECOND.fullmatch(value):
            raise ValueError("update timestamp must be a UTC millisecond timestamp ending in Z")
        try:
            parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC)
        except ValueError as exc:
            raise ValueError("update timestamp must be a UTC millisecond timestamp ending in Z") from exc
        canonical = parsed.strftime("%Y-%m-%dT%H:%M:%S.%f")[:23] + "Z"
        if value != canonical:
            raise ValueError("update timestamp must be a UTC millisecond timestamp ending in Z")
        return value

    @staticmethod
    def _literal(value: str) -> str:
        if not value or "\n" in value or "\r" in value:
            raise ValueError("cursor values must be non-empty single-line strings")
        return "'" + value.replace("'", "''") + "'"

    def iter_pages(self, cursor: Mapping[str, str] | None = None,
                   upper_bound: str | None = None) -> Iterator[SourcePage]:
        self.contract.assert_ready()
        contract = self.contract
        updated, row_id = contract.update_time_field, contract.source_row_id_field
        if cursor is not None and set(cursor) != {updated, row_id}:
            raise ValueError(f"cursor must contain {updated} and {row_id}")
        if cursor is not None:
            self._validate_update_timestamp(cursor[updated])
            if not isinstance(cursor[row_id], str) or not cursor[row_id]:
                raise ValueError("cursor source row id must be a non-empty string")
        if upper_bound is not None:
            self._validate_update_timestamp(upper_bound)
        lower = None if cursor is None else dict(cursor)
        seen: set[tuple[str, ...]] = set()
        bounds = {"source_id": contract.source_id, "dataset_id": contract.dataset_id,
                  "contract_version": contract.version, "upper_bound_inclusive": True,
                  "upper_bound": upper_bound, "page_size": self.page_size, "pagination": "keyset",
                  "bounded_scope_exhaustion_is_full_reconciliation": False}
        while True:
            predicates = []
            if lower is not None:
                ts, rid = self._literal(lower[updated]), self._literal(lower[row_id])
                predicates.append(f"{updated} > {ts} OR ({updated} = {ts} AND {row_id} > {rid})")
            if upper_bound is not None:
                predicates.append(f"{updated} <= {self._literal(upper_bound)}")
            params = {"$select": ",".join(contract.fields), "$order": f"{updated} ASC, {row_id} ASC",
                      "$limit": str(self.page_size)}
            if predicates:
                params["$where"] = " AND ".join(f"({p})" for p in predicates)
            # Enforce the same allowlist on returned rows in case a proxy or
            # publisher ignores `$select`; unrelated columns must not leak to storage.
            raw_records = self._get(params)
            if len(raw_records) > self.page_size:
                raise SourceProtocolError("publisher exceeded requested page size")
            records = [
                {field: row[field] for field in contract.fields if field in row}
                for row in raw_records
            ]
            previous = None if lower is None else (lower[updated], lower[row_id])
            for record in records:
                missing = [f for f in contract.identity_fields if record.get(f) in (None, "")]
                if missing:
                    raise SourceProtocolError("row missing identity fields: " + ", ".join(missing))
                if record.get(row_id) in (None, "") or record.get(updated) in (None, ""):
                    raise SourceProtocolError("row missing update timestamp or source row id")
                try:
                    update_timestamp = self._validate_update_timestamp(record[updated])
                except ValueError as exc:
                    raise SourceProtocolError(str(exc)) from exc
                if upper_bound is not None and update_timestamp > upper_bound:
                    raise SourceProtocolError("publisher returned a row that exceeds declared upper bound")
                key = (update_timestamp, str(record[row_id]))
                if previous is not None and key <= previous:
                    raise SourceProtocolError("source page is not strictly ordered after cursor")
                previous = key
                identity = tuple(str(record[f]) for f in contract.identity_fields)
                if identity in seen:
                    raise SourceProtocolError(f"identity collision for {identity!r}")
                seen.add(identity)
            exhausted = len(records) < self.page_size
            next_cursor = None if lower is None else dict(lower)
            if records:
                last = records[-1]
                next_cursor = {updated: str(last[updated]), row_id: str(last[row_id])}
            full_recon = exhausted and upper_bound is None and cursor is None and contract.guarantees.get("complete_reconciliation", {}).get("status") == "verified"
            yield SourcePage(records, next_cursor, exhausted, exhausted, len(records), dict(bounds), full_recon)
            if exhausted:
                return
            lower = next_cursor

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
