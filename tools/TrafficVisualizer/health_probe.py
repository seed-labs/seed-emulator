#!/usr/bin/env python3
"""Probe an HTTP service and expose recent measurements through a small API."""

from __future__ import annotations

import argparse
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from queue import Empty, SimpleQueue
import threading
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import urlopen


class HealthTracker:
    """Store a rolling window of measurements made by this probe."""

    def __init__(self, max_samples: int = 300) -> None:
        if max_samples < 1:
            raise ValueError("max_samples must be at least 1")
        self.lock = threading.Lock()
        self.samples: deque[dict[str, Any]] = deque(maxlen=max_samples)

    def record(self, payload: dict[str, Any]) -> None:
        success = payload.get("success")
        if not isinstance(success, bool):
            raise ValueError("success must be a boolean")

        latency = payload.get("latency_ms")
        if success:
            if (
                not isinstance(latency, (int, float))
                or isinstance(latency, bool)
                or not math.isfinite(latency)
                or latency < 0
            ):
                raise ValueError("a successful probe requires a non-negative latency_ms")
            latency = round(float(latency), 2)
        else:
            latency = None

        bandwidth_success = payload.get("bandwidth_success")
        throughput = payload.get("throughput_mbps")
        downloaded_bytes = payload.get("downloaded_bytes")
        if bandwidth_success is None:
            throughput = None
            downloaded_bytes = None
        elif not isinstance(bandwidth_success, bool):
            raise ValueError("bandwidth_success must be a boolean")
        elif bandwidth_success:
            if (
                not isinstance(throughput, (int, float))
                or isinstance(throughput, bool)
                or not math.isfinite(throughput)
                or throughput < 0
            ):
                raise ValueError("a successful bandwidth probe requires throughput_mbps")
            if (
                not isinstance(downloaded_bytes, int)
                or isinstance(downloaded_bytes, bool)
                or downloaded_bytes < 1
            ):
                raise ValueError("a successful bandwidth probe requires positive downloaded_bytes")
            throughput = round(float(throughput), 3)
        else:
            throughput = None
            downloaded_bytes = int(downloaded_bytes or 0)

        sample = {
            "timestamp_ms": round(time.time() * 1000),
            "success": success,
            "latency_ms": latency,
            "bandwidth_success": bandwidth_success,
            "throughput_mbps": throughput,
            "downloaded_bytes": downloaded_bytes,
        }
        with self.lock:
            self.samples.append(sample)

    def reset(self) -> None:
        with self.lock:
            self.samples.clear()

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            samples = list(self.samples)

        successful = [sample for sample in samples if sample["success"]]
        bandwidth_samples = [
            sample for sample in samples if sample["bandwidth_success"] is not None
        ]
        successful_bandwidth = [
            sample for sample in bandwidth_samples if sample["bandwidth_success"]
        ]
        latest = samples[-1] if samples else None
        latest_bandwidth = bandwidth_samples[-1] if bandwidth_samples else None
        return {
            "sample_count": len(samples),
            "failure_count": len(samples) - len(successful),
            "success_rate": round(len(successful) * 100 / len(samples), 1) if samples else 0,
            "latest_success": latest["success"] if latest else None,
            "latest_latency_ms": latest["latency_ms"] if latest else None,
            "average_latency_ms": (
                round(sum(sample["latency_ms"] for sample in successful) / len(successful), 2)
                if successful
                else None
            ),
            "last_probe_age_seconds": (
                round(max(0, time.time() - latest["timestamp_ms"] / 1000), 2)
                if latest
                else None
            ),
            "bandwidth_sample_count": len(bandwidth_samples),
            "bandwidth_failure_count": len(bandwidth_samples) - len(successful_bandwidth),
            "latest_bandwidth_success": (
                latest_bandwidth["bandwidth_success"] if latest_bandwidth else None
            ),
            "latest_throughput_mbps": (
                latest_bandwidth["throughput_mbps"] if latest_bandwidth else None
            ),
            "average_throughput_mbps": (
                round(
                    sum(sample["throughput_mbps"] for sample in successful_bandwidth)
                    / len(successful_bandwidth),
                    3,
                )
                if successful_bandwidth
                else None
            ),
            "last_bandwidth_age_seconds": (
                round(max(0, time.time() - latest_bandwidth["timestamp_ms"] / 1000), 2)
                if latest_bandwidth
                else None
            ),
            "samples": samples,
        }


def make_api_server(
    tracker: HealthTracker,
    host: str,
    port: int,
    cors_origin: str,
) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path.split("?", 1)[0] == "/api/health":
                self._send_json(200, tracker.snapshot())
            elif self.path.split("?", 1)[0] == "/healthz":
                self._send_json(200, {"status": "ok"})
            else:
                self._send_json(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path.split("?", 1)[0] == "/api/reset":
                tracker.reset()
                self._send_json(200, {"status": "reset"})
            else:
                self._send_json(404, {"error": "not found"})

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self._cors_headers()
            self.end_headers()

        def log_message(self, _format: str, *_args: Any) -> None:
            pass

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self._cors_headers()
            self.end_headers()
            self.wfile.write(body)

        def _cors_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", cors_origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

    return ThreadingHTTPServer((host, port), Handler)


def measure(target: str, timeout: float) -> dict[str, object]:
    started = time.monotonic()
    try:
        with urlopen(target, timeout=timeout) as response:
            response.read()
            success = response.status == 200
    except (HTTPError, URLError, OSError, TimeoutError):
        success = False

    if not success:
        return {"success": False}
    return {
        "success": True,
        "latency_ms": round((time.monotonic() - started) * 1000, 2),
    }


def bandwidth_url(target: str, byte_count: int) -> str:
    parsed = urlsplit(target)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["bytes"] = str(byte_count)
    return urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment)
    )


def measure_bandwidth(target: str, byte_count: int, timeout: float) -> dict[str, object]:
    started = time.monotonic()
    received = 0
    try:
        with urlopen(bandwidth_url(target, byte_count), timeout=timeout) as response:
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                received += len(chunk)
            success = response.status == 200 and received == byte_count
    except (HTTPError, URLError, OSError, TimeoutError):
        success = False

    if not success:
        return {
            "bandwidth_success": False,
            "downloaded_bytes": received,
        }
    elapsed = max(time.monotonic() - started, 0.000001)
    return {
        "bandwidth_success": True,
        "throughput_mbps": round(received * 8 / elapsed / 1_000_000, 3),
        "downloaded_bytes": received,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure access to an HTTP service.")
    parser.add_argument("--target", required=True, help="HTTP URL to probe")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=0.8)
    parser.add_argument("--bandwidth-url", help="optional HTTP bandwidth-test endpoint")
    parser.add_argument("--bandwidth-bytes", type=int, default=256 * 1024)
    parser.add_argument("--bandwidth-interval", type=float, default=5.0)
    parser.add_argument("--bandwidth-timeout", type=float, default=3.0)
    parser.add_argument("--serve-host", default="0.0.0.0")
    parser.add_argument("--serve-port", type=int, default=8080)
    parser.add_argument("--cors-origin", default="*")
    parser.add_argument("--max-samples", type=int, default=300)
    args = parser.parse_args()
    if args.interval <= 0 or args.timeout <= 0:
        parser.error("--interval and --timeout must be greater than zero")
    if args.bandwidth_url and (
        args.bandwidth_bytes < 1
        or args.bandwidth_interval <= 0
        or args.bandwidth_timeout <= 0
    ):
        parser.error("bandwidth byte count, interval, and timeout must be greater than zero")
    if not 1 <= args.serve_port <= 65535:
        parser.error("--serve-port must be between 1 and 65535")
    if args.max_samples < 1:
        parser.error("--max-samples must be at least 1")

    tracker = HealthTracker(args.max_samples)
    server = make_api_server(tracker, args.serve_host, args.serve_port, args.cors_origin)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(
        f"Health probe API listening on http://{args.serve_host}:{args.serve_port}/api/health",
        flush=True,
    )
    bandwidth_results: SimpleQueue[dict[str, object]] = SimpleQueue()
    next_bandwidth_probe = 0.0
    bandwidth_probe_running = False

    def run_bandwidth_probe() -> None:
        bandwidth_results.put(
            measure_bandwidth(
                args.bandwidth_url,
                args.bandwidth_bytes,
                args.bandwidth_timeout,
            )
        )

    try:
        while True:
            cycle_started = time.monotonic()
            sample = measure(args.target, args.timeout)
            if bandwidth_probe_running:
                try:
                    sample.update(bandwidth_results.get_nowait())
                    bandwidth_probe_running = False
                    next_bandwidth_probe = time.monotonic() + args.bandwidth_interval
                except Empty:
                    pass
            if (
                args.bandwidth_url
                and not bandwidth_probe_running
                and cycle_started >= next_bandwidth_probe
            ):
                threading.Thread(target=run_bandwidth_probe, daemon=True).start()
                bandwidth_probe_running = True
            tracker.record(sample)
            remaining = args.interval - (time.monotonic() - cycle_started)
            if remaining > 0:
                time.sleep(remaining)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
