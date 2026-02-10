from __future__ import annotations

import hashlib
import os
import selectors
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .store import SeedOpsStore
from .workspaces import WorkspaceManager


_TRUNCATED_SUFFIX = "\n...[truncated]"


def _truncate(text: str, max_chars: int, *, truncated: bool = False) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text + (_TRUNCATED_SUFFIX if truncated else "")
    return text[:max_chars] + _TRUNCATED_SUFFIX


def _max_output_bytes(max_output_chars: int) -> int:
    # Bound memory usage even if the output contains multibyte UTF-8.
    # We intentionally over-approximate (worst case is 4 bytes/char).
    if max_output_chars <= 0:
        return 0
    return int(max_output_chars) * 4


def _read_stream_limited(stream: Any, *, max_bytes: int) -> tuple[bytes, bool]:
    """Read bytes from an iterable stream up to max_bytes, returning (data, truncated)."""
    if max_bytes <= 0:
        return b"", False
    buf = bytearray()
    for chunk in stream:
        if chunk is None:
            continue
        if isinstance(chunk, str):
            chunk_b = chunk.encode("utf-8", errors="replace")
        else:
            chunk_b = bytes(chunk)
        remaining = max_bytes - len(buf)
        if remaining <= 0:
            return bytes(buf), True
        if len(chunk_b) <= remaining:
            buf.extend(chunk_b)
        else:
            buf.extend(chunk_b[:remaining])
            return bytes(buf), True
    return bytes(buf), False


def _exec_run(container: Any, cmd: list[str] | str) -> tuple[int, bytes]:
    res = container.exec_run(cmd, demux=False)
    exit_code = getattr(res, "exit_code", None)
    output = getattr(res, "output", None)
    if exit_code is None and isinstance(res, (tuple, list)) and len(res) >= 2:
        exit_code = res[0]
        output = res[1]
    if exit_code is None:
        exit_code = 0
    if output is None:
        output = b""
    return int(exit_code), bytes(output)


def _docker_exec_cli(
    container_name: str,
    *,
    shell_script: str,
    timeout_seconds: int,
    max_bytes: int,
) -> tuple[int, bytes, bool, bool]:
    """Run `docker exec <container> sh -lc <script>` with host-side timeout and output limit.

    Returns (exit_code, output_bytes_limited, output_truncated, timed_out).
    """
    cmd = ["docker", "exec", container_name, "sh", "-lc", shell_script]
    start = time.monotonic()
    proc = subprocess.Popen(  # noqa: S603
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )
    assert proc.stdout is not None
    assert proc.stderr is not None

    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ)
    sel.register(proc.stderr, selectors.EVENT_READ)

    buf = bytearray()
    truncated = False
    timed_out = False

    def read_chunk(f) -> bytes:
        try:
            return f.read1(4096)  # type: ignore[attr-defined]
        except Exception:
            return f.read(4096)

    try:
        while sel.get_map():
            if timeout_seconds and (time.monotonic() - start) > float(timeout_seconds):
                timed_out = True
                break

            events = sel.select(timeout=0.1)
            if not events:
                if proc.poll() is not None:
                    # Process ended; drain any remaining data quickly.
                    for key in list(sel.get_map().values()):
                        chunk = read_chunk(key.fileobj)
                        if not chunk:
                            try:
                                sel.unregister(key.fileobj)
                            except Exception:
                                pass
                            continue
                        if max_bytes > 0 and len(buf) < max_bytes:
                            remaining = max_bytes - len(buf)
                            buf.extend(chunk[:remaining])
                            if len(chunk) > remaining:
                                truncated = True
                        else:
                            truncated = True
                    continue
                continue

            for key, _mask in events:
                chunk = read_chunk(key.fileobj)
                if not chunk:
                    try:
                        sel.unregister(key.fileobj)
                    except Exception:
                        pass
                    continue
                if max_bytes > 0 and len(buf) < max_bytes:
                    remaining = max_bytes - len(buf)
                    buf.extend(chunk[:remaining])
                    if len(chunk) > remaining:
                        truncated = True
                else:
                    truncated = True
    finally:
        try:
            sel.close()
        except Exception:
            pass

    if timed_out:
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        return -1, bytes(buf), True if max_bytes > 0 else False, True

    exit_code = proc.wait()
    return int(exit_code), bytes(buf), truncated, False


class OpsService:
    def __init__(self, *, store: SeedOpsStore, workspaces: WorkspaceManager):
        self._store = store
        self._workspaces = workspaces

    def _pick_exec_backend(self, docker_client: Any) -> str:
        """Pick an exec backend for ops_exec/routing checks.

        - `SEEDOPS_EXEC_BACKEND=sdk|cli|auto` (default auto)
        - In auto mode, prefer CLI when the docker client appears to be real and `docker` is available.
        """
        mode = (os.environ.get("SEEDOPS_EXEC_BACKEND") or "auto").strip().lower()
        if mode == "sdk":
            return "sdk"
        if mode == "cli":
            return "cli" if shutil.which("docker") else "sdk"

        if shutil.which("docker") and getattr(docker_client, "__class__", type("x", (), {})).__module__.startswith("docker."):
            return "cli"
        return "sdk"

    def _run_shell(
        self,
        *,
        docker_client: Any,
        backend: str,
        container_name: str,
        shell_script: str,
        timeout_seconds: int,
        max_output_chars: int,
    ) -> dict[str, Any]:
        max_bytes = _max_output_bytes(max_output_chars)
        if backend == "cli":
            exit_code, out_b, truncated_b, timed_out = _docker_exec_cli(
                container_name,
                shell_script=shell_script,
                timeout_seconds=int(timeout_seconds),
                max_bytes=max_bytes,
            )
        else:
            timed_out = False
            c = docker_client.containers.get(container_name)
            exit_code, full_b = _exec_run(c, ["sh", "-lc", shell_script])
            truncated_b = max_bytes > 0 and len(full_b) > max_bytes
            out_b = full_b[:max_bytes] if truncated_b else full_b

        out_s = out_b.decode("utf-8", errors="replace")
        out_s = _truncate(out_s, int(max_output_chars), truncated=truncated_b)

        return {
            "exit_code": int(exit_code),
            "output": out_s,
            "output_truncated": bool(truncated_b),
            "timed_out": bool(timed_out),
        }

    def exec(
        self,
        workspace_id: str,
        *,
        selector: dict[str, Any],
        command: str,
        timeout_seconds: int = 30,
        parallelism: int = 20,
        max_output_chars: int = 8000,
    ) -> dict[str, Any]:
        nodes = self._workspaces.list_nodes(workspace_id, selector=selector)
        docker_client = self._workspaces.get_docker_client()
        backend = self._pick_exec_backend(docker_client)

        script = f"command -v timeout >/dev/null 2>&1 && timeout {int(timeout_seconds)}s {command} || {command}"

        def worker(node: dict[str, Any]) -> dict[str, Any]:
            node_id = node.get("node_id")
            cname = node.get("container_name")
            try:
                run = self._run_shell(
                    docker_client=docker_client,
                    backend=backend,
                    container_name=str(cname),
                    shell_script=script,
                    timeout_seconds=int(timeout_seconds),
                    max_output_chars=int(max_output_chars),
                )
                exit_code = int(run["exit_code"])
                out = str(run["output"])
                timed_out = bool(run["timed_out"])
                ok = exit_code == 0 and not timed_out
                item: dict[str, Any] = {
                    "node_id": node_id,
                    "container_name": cname,
                    "ok": ok,
                    "exit_code": exit_code,
                    "output": out,
                }
                if not ok:
                    if timed_out:
                        item["error"] = f"timeout after {int(timeout_seconds)}s"
                    else:
                        head = (out or "").strip().splitlines()[:1]
                        item["error"] = head[0][:200] if head else f"exit_code {exit_code}"
                return item
            except Exception as e:
                return {
                    "node_id": node_id,
                    "container_name": cname,
                    "ok": False,
                    "exit_code": -1,
                    "error": str(e),
                    "output": "",
                }

        results: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=max(1, int(parallelism))) as pool:
            futs = [pool.submit(worker, n) for n in nodes]
            for fut in as_completed(futs):
                results.append(fut.result())

        results.sort(key=lambda r: str(r.get("node_id", "")))
        ok = sum(1 for r in results if r.get("ok"))
        fail = len(results) - ok
        cmd_hash = hashlib.sha256(command.encode("utf-8")).hexdigest()[:12]

        fail_reasons: dict[str, int] = {}
        for r in results:
            if r.get("ok"):
                continue
            reason = str(r.get("error") or f"exit_code {r.get('exit_code')}")
            fail_reasons[reason] = fail_reasons.get(reason, 0) + 1

        payload = {
            "command": command,
            "command_hash": cmd_hash,
            "counts": {"total": len(results), "ok": ok, "fail": fail},
            "results": results,
            "backend": backend,
            "fail_reasons": fail_reasons,
        }

        self._store.insert_event(
            workspace_id,
            level="info",
            event_type="ops.exec",
            message=f"Batch exec: {cmd_hash}",
            data={
                "command": command,
                "command_hash": cmd_hash,
                "counts": payload["counts"],
                "backend": backend,
                "fail_reasons": fail_reasons,
            },
        )
        return payload

    def logs(
        self,
        workspace_id: str,
        *,
        selector: dict[str, Any],
        tail: int = 200,
        since_seconds: int = 0,
        parallelism: int = 20,
        max_output_chars: int = 8000,
    ) -> dict[str, Any]:
        nodes = self._workspaces.list_nodes(workspace_id, selector=selector)
        docker_client = self._workspaces.get_docker_client()

        since = None
        if since_seconds and int(since_seconds) > 0:
            since = int(time.time()) - int(since_seconds)

        def worker(node: dict[str, Any]) -> dict[str, Any]:
            node_id = node.get("node_id")
            cname = node.get("container_name")
            try:
                c = docker_client.containers.get(cname)
                max_bytes = _max_output_bytes(int(max_output_chars))
                try:
                    stream = (
                        c.logs(tail=int(tail), since=since, stream=True)
                        if since is not None
                        else c.logs(tail=int(tail), stream=True)
                    )
                    raw_b, truncated_b = _read_stream_limited(stream, max_bytes=max_bytes)
                except TypeError:
                    raw = c.logs(tail=int(tail), since=since) if since is not None else c.logs(tail=int(tail))
                    raw_b = bytes(raw)
                    truncated_b = max_bytes > 0 and len(raw_b) > max_bytes
                    raw_b = raw_b[:max_bytes] if truncated_b else raw_b

                out = raw_b.decode("utf-8", errors="replace")
                out = _truncate(out, int(max_output_chars), truncated=truncated_b)
                return {"node_id": node_id, "container_name": cname, "ok": True, "log": out}
            except Exception as e:
                return {"node_id": node_id, "container_name": cname, "ok": False, "error": str(e), "log": ""}

        results: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=max(1, int(parallelism))) as pool:
            futs = [pool.submit(worker, n) for n in nodes]
            for fut in as_completed(futs):
                results.append(fut.result())

        results.sort(key=lambda r: str(r.get("node_id", "")))
        ok = sum(1 for r in results if r.get("ok"))
        fail = len(results) - ok

        fail_reasons: dict[str, int] = {}
        for r in results:
            if r.get("ok"):
                continue
            reason = str(r.get("error") or "error")
            fail_reasons[reason] = fail_reasons.get(reason, 0) + 1

        payload = {
            "counts": {"total": len(results), "ok": ok, "fail": fail},
            "logs": results,
            "fail_reasons": fail_reasons,
        }

        self._store.insert_event(
            workspace_id,
            level="info",
            event_type="ops.logs",
            message="Batch logs",
            data={
                "counts": payload["counts"],
                "tail": int(tail),
                "since_seconds": int(since_seconds),
                "fail_reasons": fail_reasons,
            },
        )
        return payload

    def bgp_summary(self, workspace_id: str, *, selector: dict[str, Any]) -> dict[str, Any]:
        nodes = self._workspaces.list_nodes(workspace_id, selector=selector)
        docker_client = self._workspaces.get_docker_client()
        backend = self._pick_exec_backend(docker_client)

        def parse_bird_protocols(output: str) -> dict[str, int]:
            up = 0
            down = 0
            for line in output.splitlines():
                parts = line.split()
                if len(parts) < 4:
                    continue
                if parts[1].upper() != "BGP":
                    continue
                state = parts[3].lower()
                if state == "up":
                    up += 1
                else:
                    down += 1
            return {"up": up, "down": down}

        def worker(node: dict[str, Any]) -> dict[str, Any]:
            node_id = node.get("node_id")
            cname = node.get("container_name")
            try:
                run = self._run_shell(
                    docker_client=docker_client,
                    backend=backend,
                    container_name=str(cname),
                    shell_script="birdc show protocols",
                    timeout_seconds=20,
                    max_output_chars=8000,
                )
                exit_code = int(run["exit_code"])
                out = str(run["output"])
                if exit_code != 0 or run["timed_out"]:
                    err = "timeout" if run["timed_out"] else (out.strip()[:200] or f"exit_code {exit_code}")
                    return {"node_id": node_id, "container_name": cname, "ok": False, "error": err}
                bgp = parse_bird_protocols(out)
                return {
                    "node_id": node_id,
                    "container_name": cname,
                    "ok": True,
                    "bgp": bgp,
                    "raw_head": out[:200],
                }
            except Exception as e:
                return {"node_id": node_id, "container_name": cname, "ok": False, "error": str(e)}

        results: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=max(1, int(min(50, max(1, len(nodes)))))) as pool:
            futs = [pool.submit(worker, n) for n in nodes]
            for fut in as_completed(futs):
                results.append(fut.result())

        results.sort(key=lambda r: str(r.get("node_id", "")))
        nodes_ok = sum(1 for r in results if r.get("ok"))
        nodes_error = len(results) - nodes_ok
        bgp_up = 0
        bgp_down = 0
        for r in results:
            if r.get("ok") and isinstance(r.get("bgp"), dict):
                bgp_up += int(r["bgp"].get("up", 0))
                bgp_down += int(r["bgp"].get("down", 0))

        payload = {
            "counts": {
                "nodes": len(results),
                "nodes_ok": nodes_ok,
                "nodes_error": nodes_error,
                "bgp_up": bgp_up,
                "bgp_down": bgp_down,
            },
            "nodes": results,
            "backend": backend,
        }

        self._store.insert_event(
            workspace_id,
            level="info",
            event_type="routing.bgp_summary",
            message="BGP summary",
            data={**payload["counts"], "backend": backend},
        )
        return payload
