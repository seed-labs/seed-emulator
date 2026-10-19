#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Iterable, Optional

from seedemu.testing import EthereumRuntimeTest


EXPLORER_URL = os.environ.get("D10_ETH_EXPLORER_URL", "http://127.0.0.1:8098").rstrip("/")
EXPLORER_SERVICE = "seedemu-ethexplorer-web"


def record(test: EthereumRuntimeTest, name: str, command: str, ok: bool, stdout: str = "", stderr: str = "") -> None:
    test.results.append(
        {
            "name": name,
            "service": EXPLORER_SERVICE,
            "command": command,
            "exit": 0 if ok else 1,
            "stdout": stdout[-1000:],
            "stderr": stderr[-1000:],
            "status": "passed" if ok else "failed",
        }
    )


def fetch(path: str, *, method: str = "GET", data: Optional[bytes] = None, timeout: int = 10) -> tuple[int, str]:
    url = EXPLORER_URL + path
    request = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body


def wait_for_http(
    test: EthereumRuntimeTest,
    name: str,
    path: str,
    *,
    predicate: Optional[Callable[[str], bool]] = None,
    method: str = "GET",
    data: Optional[bytes] = None,
    retries: int = 90,
    interval: int = 5,
    timeout: int = 10,
) -> Optional[str]:
    last = ""
    command = f"HTTP {method} {EXPLORER_URL}{path}"
    for attempt in range(1, retries + 1):
        try:
            status, body = fetch(path, method=method, data=data, timeout=timeout)
        except Exception as exc:
            last = str(exc)
        else:
            last = f"status={status} body={body[:500]}"
            if 200 <= status < 300 and (predicate is None or predicate(body)):
                record(test, name, command, True, f"attempts={attempt} {last}")
                return body
        if attempt < retries:
            time.sleep(interval)
    record(test, name, command, False, last)
    return None


def wait_for_any_http(
    test: EthereumRuntimeTest,
    name: str,
    paths: Iterable[str],
    *,
    predicate: Optional[Callable[[str], bool]] = None,
    retries: int = 60,
    interval: int = 5,
    timeout: int = 10,
) -> Optional[tuple[str, str]]:
    candidates = list(paths)
    last = ""
    command = "HTTP GET " + ", ".join(EXPLORER_URL + path for path in candidates)
    for attempt in range(1, retries + 1):
        for path in candidates:
            try:
                status, body = fetch(path, timeout=timeout)
            except Exception as exc:
                last = f"{path}: {exc}"
                continue
            last = f"{path}: status={status} body={body[:500]}"
            if 200 <= status < 300 and (predicate is None or predicate(body)):
                record(test, name, command, True, f"attempts={attempt} path={path} body={body[:500]}")
                return path, body
        if attempt < retries:
            time.sleep(interval)
    record(test, name, command, False, last)
    return None


def parse_json_body(body: Optional[str]) -> Optional[Any]:
    if body is None:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def int_from_value(value: object) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if text.startswith(("0x", "0X")):
            try:
                return int(text, 16)
            except ValueError:
                return None
        if text.isdigit():
            return int(text)
    return None


def find_int_by_key(data: Any, key_names: tuple[str, ...], contains: str) -> Optional[int]:
    if isinstance(data, dict):
        for key, value in data.items():
            key_text = str(key).lower()
            if key_text in key_names:
                parsed = int_from_value(value)
                if parsed is not None:
                    return parsed
        for key, value in data.items():
            key_text = str(key).lower()
            if contains in key_text:
                parsed = int_from_value(value)
                if parsed is not None:
                    return parsed
            found = find_int_by_key(value, key_names, contains)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = find_int_by_key(item, key_names, contains)
            if found is not None:
                return found
    return None


def body_has_any(*needles: str) -> Callable[[str], bool]:
    lowered = [needle.lower() for needle in needles]

    def predicate(body: str) -> bool:
        text = body.lower()
        return any(needle in text for needle in lowered)

    return predicate


def body_has_text(text: str) -> Callable[[str], bool]:
    text_lower = text.lower()

    def predicate(body: str) -> bool:
        return text_lower in body.lower()

    return predicate


def datatable_query() -> str:
    return urllib.parse.urlencode({"draw": 1, "start": 0, "length": 10})


def main() -> int:
    test = EthereumRuntimeTest(__file__)

    geth_nodes = test.require_ethereum_services(
        "D10 has Geth nodes for the transaction and explorer tests",
        expected_count=3,
        class_contains="Ethereum-POS-Geth",
        consensus="POS",
    )
    test.require_ethereum_services(
        "D10 has Lighthouse beacon nodes for EthExplorer",
        expected_count=3,
        class_contains="Ethereum-POS-Beacon",
        consensus="POS",
    )
    test.require_ethereum_services(
        "D10 has genesis validator clients for EthExplorer",
        expected_count=9,
        class_contains="Ethereum-POS-Validator",
        role="validator_at_genesis",
        consensus="POS",
    )

    tx_summary: Dict[str, Any] = {}
    if geth_nodes:
        tx_result = test.send_ether_and_verify(
            "A signed ETH transfer is included and changes balances",
            geth_nodes[0],
            value_wei=10**18,
        )
        if tx_result["status"] == "passed":
            try:
                tx_summary = json.loads(str(tx_result["stdout"]))
                record(
                    test,
                    "D10 signed transaction fixture is available for EthExplorer checks",
                    "send Ethereum transaction and parse transaction summary",
                    True,
                    json.dumps(tx_summary, sort_keys=True),
                )
            except json.JSONDecodeError as exc:
                record(test, "D10 transaction summary is parseable", "parse transaction summary", False, str(exc))

    latest_body = wait_for_http(
        test,
        "EthExplorer latest-state API exposes chain status",
        "/api/v1/latestState",
        predicate=body_has_any("slot", "epoch", "head", "finalized"),
        retries=120,
        interval=5,
    )
    latest_data = parse_json_body(latest_body)
    latest_slot = find_int_by_key(
        latest_data,
        ("slot", "currentslot", "headslot", "latestslot", "finalizedslot"),
        "slot",
    )
    latest_epoch = find_int_by_key(
        latest_data,
        ("epoch", "currentepoch", "latestepoch", "finalizedepoch"),
        "epoch",
    )

    if latest_slot is None:
        latest_slot = 1
        record(test, "EthExplorer latest-state slot is parseable", "parse /api/v1/latestState slot", False, latest_body or "")
    else:
        record(test, "EthExplorer latest-state slot is parseable", "parse /api/v1/latestState slot", True, str(latest_slot))
    if latest_epoch is None:
        latest_epoch = max(latest_slot // 32, 0)
        record(test, "EthExplorer latest-state epoch fallback is available", "derive epoch from slot", True, str(latest_epoch))
    else:
        record(test, "EthExplorer latest-state epoch is parseable", "parse /api/v1/latestState epoch", True, str(latest_epoch))

    slot_candidates = []
    for candidate in (latest_slot, latest_slot - 1, 1, 0):
        if candidate >= 0 and candidate not in slot_candidates:
            slot_candidates.append(candidate)
    slot_result = wait_for_any_http(
        test,
        "EthExplorer consensus slot API returns indexed slot data",
        [f"/api/v1/slot/{slot}" for slot in slot_candidates],
        predicate=body_has_any("slot", "block", "proposer", "epoch"),
        retries=120,
        interval=5,
    )
    indexed_slot = slot_candidates[0]
    if slot_result is not None:
        indexed_slot = int(slot_result[0].rsplit("/", 1)[-1])

    wait_for_http(
        test,
        "EthExplorer consensus slot UI renders indexed slot",
        f"/slot/{indexed_slot}",
        predicate=body_has_any("slot", "block", str(indexed_slot)),
        retries=60,
        interval=5,
    )
    wait_for_http(
        test,
        "EthExplorer epoch API returns epoch data",
        f"/api/v1/epoch/{latest_epoch}",
        predicate=body_has_any("epoch", "validators", "blocks", str(latest_epoch)),
        retries=90,
        interval=5,
    )
    wait_for_http(
        test,
        "EthExplorer epoch UI renders epoch page",
        f"/epoch/{latest_epoch}",
        predicate=body_has_any("epoch", str(latest_epoch)),
        retries=60,
        interval=5,
    )

    wait_for_http(
        test,
        "EthExplorer validators list UI renders",
        "/validators",
        predicate=body_has_any("validator", "validators"),
        retries=60,
        interval=5,
    )
    wait_for_http(
        test,
        "EthExplorer validators data endpoint returns table data",
        "/validators/data?" + datatable_query(),
        predicate=body_has_any("data", "validator", "pubkey"),
        retries=90,
        interval=5,
    )

    wait_for_http(
        test,
        "EthExplorer slots list data endpoint returns table data",
        "/slots/data?" + datatable_query(),
        predicate=body_has_any("data", "slot", "epoch"),
        retries=90,
        interval=5,
    )
    wait_for_http(
        test,
        "EthExplorer index data endpoint returns chain activity",
        "/index/data",
        predicate=body_has_any("slot", "epoch", "block", "validator"),
        retries=90,
        interval=5,
    )

    tx_hash = str(tx_summary.get("tx_hash", ""))
    block_number = tx_summary.get("block_number")
    if block_number is None:
        record(test, "D10 transaction block number is available for explorer lookup", "read transaction summary", False, json.dumps(tx_summary))
    else:
        block_text = str(block_number)
        wait_for_http(
            test,
            "EthExplorer execution block UI renders transaction block",
            f"/block/{block_text}",
            predicate=body_has_any("block", block_text),
            retries=90,
            interval=5,
        )
        if tx_hash:
            wait_for_http(
                test,
                "EthExplorer execution block transactions endpoint indexes the signed transfer",
                f"/block/{block_text}/transactions?" + datatable_query(),
                predicate=body_has_any(tx_hash, tx_hash.removeprefix("0x")),
                retries=120,
                interval=5,
            )
        wait_for_http(
            test,
            "EthExplorer execution blocks list UI renders",
            "/blocks",
            predicate=body_has_any("block", "blocks"),
            retries=60,
            interval=5,
        )
        wait_for_http(
            test,
            "EthExplorer execution blocks data endpoint returns table data",
            "/blocks/data?" + datatable_query(),
            predicate=body_has_any("data", "block"),
            retries=90,
            interval=5,
        )

    if tx_hash:
        wait_for_http(
            test,
            "EthExplorer transaction UI renders the signed transfer",
            f"/tx/{tx_hash}",
            predicate=body_has_text(tx_hash),
            retries=120,
            interval=5,
        )
        search_data = urllib.parse.urlencode({"search": tx_hash}).encode("utf-8")
        wait_for_http(
            test,
            "EthExplorer search form can find the signed transfer",
            "/search",
            method="POST",
            data=search_data,
            predicate=body_has_any(tx_hash, tx_hash.removeprefix("0x"), "transaction"),
            retries=30,
            interval=5,
        )
    else:
        record(test, "D10 transaction hash is available for explorer lookup", "read transaction summary", False, json.dumps(tx_summary))

    wait_for_http(
        test,
        "EthExplorer transactions list UI renders",
        "/transactions",
        predicate=body_has_any("transaction", "transactions"),
        retries=60,
        interval=5,
    )
    wait_for_http(
        test,
        "EthExplorer transactions data endpoint returns table data",
        "/transactions/data?" + datatable_query(),
        predicate=body_has_any("data", "transaction", "hash"),
        retries=90,
        interval=5,
    )

    test.write_summary("d10-eth-explorer-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
