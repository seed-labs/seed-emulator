from __future__ import annotations

import hashlib
import os
import selectors
import shlex
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .store import SeedOpsStore
from .workspaces import WorkspaceManager


_TRUNCATED_SUFFIX = "\n...[truncated]"
_FRR_DAEMONS = {
    "watchfrr",
    "zebra",
    "bgpd",
    "ospfd",
    "ospf6d",
    "ldpd",
    "staticd",
    "ripd",
    "ripngd",
    "isisd",
    "pimd",
    "babeld",
    "bfdd",
}
_FRR_UNUSABLE_MARKERS = (
    "bgpd is not running",
    "% bgpd is not running",
    "failed to connect to any daemons",
)


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

    def _workspace_redacted_fields(self, workspace_id: str) -> list[str]:
        getter = getattr(self._workspaces, "get_visibility", None)
        if not callable(getter):
            return []
        try:
            visibility = getter(workspace_id)
        except Exception:
            return []
        if not isinstance(visibility, dict):
            return []
        fields = visibility.get("redacted_fields")
        if not isinstance(fields, list):
            return []
        return [str(field) for field in fields if str(field or "").strip()]

    def _redact_results(self, workspace_id: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        redacted_fields = self._workspace_redacted_fields(workspace_id)
        if not redacted_fields:
            return rows
        redacted: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            for field in redacted_fields:
                item.pop(field, None)
            redacted.append(item)
        return redacted

    @staticmethod
    def _parse_bird_protocols(output: str) -> dict[str, int]:
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

    @staticmethod
    def _parse_frr_bgp_summary(output: str) -> dict[str, int]:
        up = 0
        down = 0
        for line in output.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith(("BGP router identifier", "Neighbor", "Total number", "Displayed", "IPv4 Unicast")):
                continue
            parts = stripped.split()
            if len(parts) < 2:
                continue
            neighbor = parts[0]
            if not any(ch.isdigit() for ch in neighbor):
                continue
            state = parts[-1]
            if state.isdigit():
                up += 1
                continue
            if "/" in state:
                chunks = [chunk for chunk in state.split("/") if chunk]
                if chunks and all(chunk.isdigit() for chunk in chunks):
                    up += 1
                    continue
            down += 1
        return {"up": up, "down": down}

    @staticmethod
    def _routing_summary_command(backend: str) -> str:
        if backend == "bird":
            return "birdc show protocols"
        if backend == "frr":
            return "vtysh -c 'show bgp summary'"
        raise ValueError(f"unsupported routing backend: {backend}")

    @staticmethod
    def _routing_backend_probe_command() -> str:
        return (
            "# seedops-routing-probe\n"
            "if command -v birdc >/dev/null 2>&1; then echo 'cmd:birdc=1'; else echo 'cmd:birdc=0'; fi\n"
            "if command -v vtysh >/dev/null 2>&1; then echo 'cmd:vtysh=1'; else echo 'cmd:vtysh=0'; fi\n"
            "(ps -eo comm= 2>/dev/null || ps -A -o comm= 2>/dev/null || ps 2>/dev/null || true) | "
            "while read -r proc _rest; do "
            "case \"$proc\" in COMMAND|PID|'') continue ;; esac; "
            "proc=${proc##*/}; "
            "echo \"proc:$proc\"; "
            "done\n"
        )

    @staticmethod
    def _parse_routing_backend_probe(output: str) -> dict[str, Any]:
        has_birdc = False
        has_vtysh = False
        processes: set[str] = set()
        for line in str(output or "").splitlines():
            item = line.strip()
            if not item:
                continue
            if item == "cmd:birdc=1":
                has_birdc = True
                continue
            if item == "cmd:vtysh=1":
                has_vtysh = True
                continue
            if item.startswith("proc:"):
                proc = item.split(":", 1)[1].strip()
                if proc:
                    processes.add(proc)

        frr_processes = sorted(proc for proc in processes if proc in _FRR_DAEMONS)
        return {
            "has_birdc": has_birdc,
            "has_vtysh": has_vtysh,
            "bird_running": "bird" in processes,
            "bgpd_running": "bgpd" in processes,
            "frr_processes": frr_processes,
            "frr_running": bool(frr_processes),
        }

    @staticmethod
    def _routing_backend_chain(probe: dict[str, Any]) -> list[str]:
        has_bird = bool(probe.get("has_birdc") or probe.get("bird_running"))
        has_frr = bool(probe.get("has_vtysh") or probe.get("frr_running"))
        if has_bird and has_frr:
            if probe.get("bgpd_running"):
                return ["frr", "bird"]
            if probe.get("bird_running"):
                return ["bird", "frr"]
            return ["frr", "bird"]
        if has_frr:
            return ["frr"]
        if has_bird:
            return ["bird"]
        return ["bird", "frr"]

    @staticmethod
    def _routing_output_usable(backend: str, output: str) -> bool:
        if backend != "frr":
            return True
        lowered = str(output or "").strip().lower()
        if not lowered:
            return False
        return not any(marker in lowered for marker in _FRR_UNUSABLE_MARKERS)

    @staticmethod
    def _routing_looking_glass_command(backend: str, prefix: str) -> str:
        prefix_s = str(prefix or "").strip()
        if backend == "bird":
            if prefix_s:
                safe = prefix_s.replace('"', "").replace("'", "")
                return f'birdc "show route for {safe} all"'
            return "birdc 'show route all'"
        if backend == "frr":
            if prefix_s:
                safe = shlex.quote(prefix_s)
                return (
                    f"vtysh -c 'show bgp ipv4 unicast {prefix_s}'"
                    f" || vtysh -c 'show bgp {prefix_s}'"
                )
            return "vtysh -c 'show bgp ipv4 unicast' || vtysh -c 'show bgp'"
        raise ValueError(f"unsupported routing backend: {backend}")

    def _run_routing_backend(
        self,
        *,
        docker_client: Any,
        exec_backend: str,
        container_name: str,
        requested_backend: str,
        command_builder: Any,
        output_validator: Any | None = None,
        timeout_seconds: int = 20,
        max_output_chars: int = 8000,
    ) -> dict[str, Any]:
        backend_chain = [requested_backend]
        probe_data: dict[str, Any] | None = None
        if requested_backend == "auto":
            probe = self._run_shell(
                docker_client=docker_client,
                backend=exec_backend,
                container_name=container_name,
                shell_script=self._routing_backend_probe_command(),
                timeout_seconds=min(8, int(timeout_seconds)),
                max_output_chars=4000,
            )
            if int(probe["exit_code"]) == 0 and not bool(probe["timed_out"]):
                probe_data = self._parse_routing_backend_probe(str(probe["output"] or ""))
                backend_chain = self._routing_backend_chain(probe_data)
            else:
                backend_chain = ["bird", "frr"]

        failures: list[dict[str, Any]] = []
        for backend in backend_chain:
            run = self._run_shell(
                docker_client=docker_client,
                backend=exec_backend,
                container_name=container_name,
                shell_script=str(command_builder(backend)),
                timeout_seconds=int(timeout_seconds),
                max_output_chars=int(max_output_chars),
            )
            exit_code = int(run["exit_code"])
            output = str(run["output"] or "")
            timed_out = bool(run["timed_out"])
            usable = exit_code == 0 and not timed_out
            if usable and callable(output_validator):
                usable = bool(output_validator(backend, output))
            if usable:
                return {
                    "ok": True,
                    "backend": backend,
                    "output": output,
                    "raw_head": output[:200],
                    "timed_out": False,
                    **({"probe": probe_data} if probe_data else {}),
                }
            error_text = output.strip()[:200] or f"exit_code {exit_code}"
            if exit_code == 0 and not timed_out and not usable:
                error_text = output.strip()[:200] or f"{backend} returned unusable output"
            failures.append(
                {
                    "backend": backend,
                    "exit_code": exit_code,
                    "timed_out": timed_out,
                    "raw_head": output[:200],
                    "error": "timeout" if timed_out else error_text,
                }
            )

        failure = failures[-1] if failures else {"backend": "unsupported", "error": "unsupported"}
        return {
            "ok": False,
            "backend": failure.get("backend", "unsupported"),
            "output": "",
            "raw_head": str(failure.get("raw_head") or ""),
            "timed_out": bool(failure.get("timed_out")),
            "error": str(failure.get("error") or "unsupported"),
            "attempts": failures,
            **({"probe": probe_data} if probe_data else {}),
        }

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
        results = self._redact_results(workspace_id, results)
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

    def exec_cli(
        self,
        workspace_id: str,
        *,
        selector: dict[str, Any],
        command: str,
        timeout_seconds: int = 30,
        parallelism: int = 20,
        max_output_chars: int = 8000,
    ) -> dict[str, Any]:
        """Execute a shell command across containers using the docker CLI backend.

        This is safer for long-running commands because it enforces a host-side timeout.
        """
        if not shutil.which("docker"):
            raise RuntimeError("docker CLI not found; cannot use exec_cli backend.")

        nodes = self._workspaces.list_nodes(workspace_id, selector=selector)
        backend = "cli"

        script = f"command -v timeout >/dev/null 2>&1 && timeout {int(timeout_seconds)}s {command} || {command}"

        def worker(node: dict[str, Any]) -> dict[str, Any]:
            node_id = node.get("node_id")
            cname = node.get("container_name")
            try:
                run = self._run_shell(
                    docker_client=None,
                    backend="cli",
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
        results = self._redact_results(workspace_id, results)
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
            message=f"Batch exec (cli): {cmd_hash}",
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
                # Avoid Docker SDK streaming here: some long-lived containers keep the
                # stream open, which stalls follow-job workflows on logs steps.
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

    def routing_protocol_summary(
        self,
        workspace_id: str,
        *,
        selector: dict[str, Any],
        backend: str = "auto",
    ) -> dict[str, Any]:
        nodes = self._workspaces.list_nodes(workspace_id, selector=selector)
        docker_client = self._workspaces.get_docker_client()
        exec_backend = self._pick_exec_backend(docker_client)
        requested_backend = str(backend or "auto").strip().lower() or "auto"
        if requested_backend not in {"auto", "bird", "frr"}:
            raise ValueError("backend must be one of: auto, bird, frr")

        def worker(node: dict[str, Any]) -> dict[str, Any]:
            node_id = node.get("node_id")
            cname = node.get("container_name")
            try:
                routing = self._run_routing_backend(
                    docker_client=docker_client,
                    exec_backend=exec_backend,
                    container_name=str(cname),
                    requested_backend=requested_backend,
                    command_builder=self._routing_summary_command,
                    output_validator=self._routing_output_usable,
                )
                if not routing["ok"]:
                    backend_name = (
                        "unsupported" if requested_backend == "auto" and len(routing.get("attempts") or []) >= 2 else routing["backend"]
                    )
                    return {
                        "node_id": node_id,
                        "container_name": cname,
                        "ok": False,
                        "backend": backend_name,
                        "bgp": {"up": 0, "down": 0},
                        "raw_head": routing.get("raw_head", ""),
                        "error": routing.get("error", "unsupported"),
                    }
                out = str(routing["output"])
                active_backend = str(routing["backend"])
                parser = self._parse_bird_protocols if active_backend == "bird" else self._parse_frr_bgp_summary
                bgp = parser(out)
                return {
                    "node_id": node_id,
                    "container_name": cname,
                    "ok": True,
                    "backend": active_backend,
                    "bgp": bgp,
                    "raw_head": out[:200],
                }
            except Exception as e:
                return {
                    "node_id": node_id,
                    "container_name": cname,
                    "ok": False,
                    "backend": "unsupported",
                    "bgp": {"up": 0, "down": 0},
                    "raw_head": "",
                    "error": str(e),
                }

        results: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=max(1, int(min(50, max(1, len(nodes)))))) as pool:
            futs = [pool.submit(worker, n) for n in nodes]
            for fut in as_completed(futs):
                results.append(fut.result())

        results.sort(key=lambda r: str(r.get("node_id", "")))
        results = self._redact_results(workspace_id, results)
        nodes_ok = sum(1 for r in results if r.get("ok"))
        nodes_error = len(results) - nodes_ok
        bgp_up = 0
        bgp_down = 0
        backend_counts: dict[str, int] = {}
        for r in results:
            backend_name = str(r.get("backend") or "unknown")
            backend_counts[backend_name] = backend_counts.get(backend_name, 0) + 1
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
            "backend_counts": backend_counts,
            "nodes": results,
            "backend": requested_backend,
        }

        self._store.insert_event(
            workspace_id,
            level="info",
            event_type="routing.protocol_summary",
            message="Routing protocol summary",
            data={**payload["counts"], "backend": requested_backend, "backend_counts": backend_counts},
        )
        return payload

    def routing_looking_glass(
        self,
        workspace_id: str,
        *,
        selector: dict[str, Any],
        prefix: str = "",
        backend: str = "auto",
    ) -> dict[str, Any]:
        nodes = self._workspaces.list_nodes(workspace_id, selector=selector)
        docker_client = self._workspaces.get_docker_client()
        exec_backend = self._pick_exec_backend(docker_client)
        requested_backend = str(backend or "auto").strip().lower() or "auto"
        if requested_backend not in {"auto", "bird", "frr"}:
            raise ValueError("backend must be one of: auto, bird, frr")

        def worker(node: dict[str, Any]) -> dict[str, Any]:
            node_id = node.get("node_id")
            cname = node.get("container_name")
            try:
                routing = self._run_routing_backend(
                    docker_client=docker_client,
                    exec_backend=exec_backend,
                    container_name=str(cname),
                    requested_backend=requested_backend,
                    command_builder=lambda active_backend: self._routing_looking_glass_command(active_backend, prefix),
                    output_validator=self._routing_output_usable,
                )
                backend_name = (
                    "unsupported" if requested_backend == "auto" and not routing["ok"] and len(routing.get("attempts") or []) >= 2 else routing["backend"]
                )
                return {
                    "node_id": node_id,
                    "container_name": cname,
                    "ok": bool(routing["ok"]),
                    "backend": backend_name,
                    "raw_head": str(routing.get("raw_head") or ""),
                    **({"error": routing.get("error")} if not routing["ok"] else {}),
                }
            except Exception as e:
                return {
                    "node_id": node_id,
                    "container_name": cname,
                    "ok": False,
                    "backend": "unsupported",
                    "raw_head": "",
                    "error": str(e),
                }

        results: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=max(1, int(min(50, max(1, len(nodes)))))) as pool:
            futs = [pool.submit(worker, n) for n in nodes]
            for fut in as_completed(futs):
                results.append(fut.result())

        results.sort(key=lambda r: str(r.get("node_id", "")))
        results = self._redact_results(workspace_id, results)
        nodes_ok = sum(1 for r in results if r.get("ok"))
        nodes_error = len(results) - nodes_ok
        backend_counts: dict[str, int] = {}
        for row in results:
            backend_name = str(row.get("backend") or "unknown")
            backend_counts[backend_name] = backend_counts.get(backend_name, 0) + 1

        payload = {
            "prefix": str(prefix or ""),
            "counts": {
                "nodes": len(results),
                "nodes_ok": nodes_ok,
                "nodes_error": nodes_error,
            },
            "backend_counts": backend_counts,
            "nodes": results,
            "backend": requested_backend,
        }

        self._store.insert_event(
            workspace_id,
            level="info",
            event_type="routing.looking_glass",
            message="Routing looking glass",
            data={**payload["counts"], "backend": requested_backend, "prefix": str(prefix or "")},
        )
        return payload

    def bgp_summary(self, workspace_id: str, *, selector: dict[str, Any]) -> dict[str, Any]:
        payload = self.routing_protocol_summary(workspace_id, selector=selector, backend="bird")
        legacy_payload = {
            "counts": dict(payload.get("counts") or {}),
            "nodes": list(payload.get("nodes") or []),
            "backend": "bird",
        }
        self._store.insert_event(
            workspace_id,
            level="info",
            event_type="routing.bgp_summary",
            message="BGP summary",
            data={**legacy_payload["counts"], "backend": "bird"},
        )
        return legacy_payload
