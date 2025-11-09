"""Server implementations used by the Monero service."""

from __future__ import annotations

import json
import os
from textwrap import dedent, indent
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, TYPE_CHECKING

from seedemu.core.Node import Node
from seedemu.core.Service import Server

from .MoneroEnum import (
    MoneroBinarySource,
    MoneroMiningTrigger,
    MoneroNodeKind,
    MoneroNodeRole,
    MoneroSeedConnectionMode,
    MoneroWalletMode,
)
from .MoneroUtil import (
    MoneroBinaryPaths,
    MoneroNodeOptions,
    MoneroWalletSpec,
    build_endpoint,
    sanitize_extra_args,
)

if TYPE_CHECKING:  # Avoid circular imports
    from .MoneroService import MoneroNetwork


class MoneroBaseServer(Server):
    """Base class shared by all Monero servers."""

    def __init__(self, serial: int, network: "MoneroNetwork", options: MoneroNodeOptions):
        super().__init__()
        self._serial = serial
        self._network = network
        self._options = options

        # Runtime binding information (populated during configure phase)
        self._resolved_ip: Optional[str] = None
        self._resolved_node_name: Optional[str] = None
        self._seed_endpoints: List[str] = []
        self._fullnode_rpc_endpoints: List[str] = []
        self._binding_lookup: Dict[str, Tuple[Node, str]] = {}

    # Attribute helpers
    @property
    def options(self) -> MoneroNodeOptions:
        return self._options

    @property
    def network(self) -> "MoneroNetwork":
        return self._network

    def getBinarySource(self) -> MoneroBinarySource:
        return self._options.binary_source

    def is_seed(self) -> bool:
        return self._options.role == MoneroNodeRole.SEED

    def is_full_node(self) -> bool:
        return self._options.kind in (MoneroNodeKind.FULL, MoneroNodeKind.PRUNED)

    def is_light_node(self) -> bool:
        return self._options.kind == MoneroNodeKind.LIGHT

    def get_rpc_port(self) -> Optional[int]:
        return self._options.rpc_bind_port

    def get_p2p_port(self) -> Optional[int]:
        return self._options.p2p_bind_port

    
    # Runtime information setters
    def set_binding(self, node: Node, ip: str):
        self._resolved_node_name = node.getName()
        self._resolved_ip = ip

    def set_binding_lookup(self, lookup: Dict[str, Tuple[Node, str]]):
        self._binding_lookup = lookup

    def set_seed_endpoints(self, endpoints: Sequence[str]):
        self._seed_endpoints = list(endpoints)

    def set_fullnode_rpc_endpoints(self, endpoints: Sequence[str]):
        self._fullnode_rpc_endpoints = list(endpoints)

    
    # Fluent-style configuration API (aligned with EthereumService style)
    
    def setRole(self, role: MoneroNodeRole) -> "MoneroBaseServer":
        """Set the logical role of the node.

        Args:
            role: Desired :class:`MoneroNodeRole` value.

        Returns:
            ``self`` for fluent chaining.

        Raises:
            AssertionError: If a light node is assigned a non-standalone role or
            a pruned node is assigned the seed role.
        """
        if self._options.kind == MoneroNodeKind.LIGHT and role != MoneroNodeRole.STANDALONE:
            raise AssertionError("Light nodes only support the STANDALONE role")
        if self._options.kind == MoneroNodeKind.PRUNED and role == MoneroNodeRole.SEED:
            raise AssertionError("Pruned nodes cannot act as seed nodes")
        self._options.role = role
        if role == MoneroNodeRole.SEED:
            self._options.wait_for_seed = False
        return self

    def setSeedRole(self) -> "MoneroBaseServer":
        """Convenience helper that marks the node as a seed."""
        return self.setRole(MoneroNodeRole.SEED)

    def setClientRole(self) -> "MoneroBaseServer":
        """Convenience helper that marks the node as a client."""
        return self.setRole(MoneroNodeRole.CLIENT)

    def setSeedConnectionMode(self, mode: MoneroSeedConnectionMode) -> "MoneroBaseServer":
        """Set how the node should connect to seed peers."""
        self._options.connect_mode = mode
        return self

    def setWaitForSeed(
        self,
        enabled: bool,
        retry_interval: Optional[int] = None,
        retry_attempts: Optional[int] = None,
    ) -> "MoneroBaseServer":
        self._options.wait_for_seed = enabled
        if retry_interval is not None:
            self._options.seed_retry_interval = retry_interval
        if retry_attempts is not None:
            self._options.seed_retry_attempts = retry_attempts
        return self

    def setWallet(self, wallet_spec: MoneroWalletSpec) -> "MoneroBaseServer":
        self._options.wallet = wallet_spec.clone()
        self._options.enable_wallet = True
        return self

    def enableWallet(self) -> "MoneroBaseServer":
        self._options.enable_wallet = True
        return self

    def disableWallet(self) -> "MoneroBaseServer":
        self._options.enable_wallet = False
        return self

    def enableWalletRpc(
        self,
        *,
        user: Optional[str] = None,
        password: Optional[str] = None,
        bind_ip: Optional[str] = None,
        bind_port: Optional[int] = None,
        allow_external: Optional[bool] = None,
    ) -> "MoneroBaseServer":
        self._options.enable_wallet = True
        wallet = self._options.wallet
        wallet.enable_rpc = True
        if user is not None:
            wallet.rpc_user = user
        if password is not None:
            wallet.rpc_password = password
        if bind_ip is not None:
            wallet.rpc_bind_ip = bind_ip
        if bind_port is not None:
            wallet.rpc_bind_port = bind_port
        if allow_external is not None:
            wallet.allow_external_rpc = allow_external
        return self

    def disableWalletRpc(self) -> "MoneroBaseServer":
        self._options.wallet.enable_rpc = False
        return self

    def setWalletPassword(self, password: str) -> "MoneroBaseServer":
        self._options.enable_wallet = True
        self._options.wallet.password = password
        return self

    def setWalletPrimaryAddressPath(self, path: str) -> "MoneroBaseServer":
        self._options.wallet.primary_address_path = path
        return self

    def setPersistData(self, enabled: bool) -> "MoneroBaseServer":
        self._options.persist_data = enabled
        return self

    def setDataDir(self, data_dir: str) -> "MoneroBaseServer":
        self._options.data_dir = data_dir
        return self

    def setLogDir(self, log_dir: str) -> "MoneroBaseServer":
        self._options.log_dir = log_dir
        return self

    def setExtraDaemonArgs(self, args: Sequence[str]) -> "MoneroBaseServer":
        self._options.extra_daemon_args = list(args)
        return self

    def addExtraDaemonArg(self, arg: str) -> "MoneroBaseServer":
        if arg not in self._options.extra_daemon_args:
            self._options.extra_daemon_args.append(arg)
        return self

    def setExtraEnv(self, env: Dict[str, str]) -> "MoneroBaseServer":
        self._options.extra_env = dict(env)
        return self

    def addExtraEnv(self, key: str, value: str) -> "MoneroBaseServer":
        self._options.extra_env[key] = value
        return self

    def setUpstreamNodes(self, upstreams: Sequence[str]) -> "MoneroBaseServer":
        self._options.upstream_nodes = list(upstreams)
        return self

    def addUpstreamNode(self, upstream: str) -> "MoneroBaseServer":
        if upstream not in self._options.upstream_nodes:
            self._options.upstream_nodes.append(upstream)
        return self

    def clearUpstreamNodes(self) -> "MoneroBaseServer":
        self._options.upstream_nodes.clear()
        return self

    def setFixedDifficulty(self, difficulty: Optional[int]) -> "MoneroBaseServer":
        self._options.fixed_difficulty = difficulty
        return self

    def exposePorts(
        self,
        *,
        p2p: Optional[bool] = None,
        rpc: Optional[bool] = None,
        zmq: Optional[bool] = None,
    ) -> "MoneroBaseServer":
        if p2p is not None:
            self._options.expose_p2p = p2p
        if rpc is not None:
            self._options.expose_rpc = rpc
        if zmq is not None:
            self._options.expose_zmq = zmq
        return self

    
    # Lifecycle hooks
    
    def install(self, node: Node):  # pragma: no cover - executed by seedemu runtime
        raise NotImplementedError

    
    # Helper methods: shared script snippets
    
    def _render_seed_wait_section(self) -> str:
        """Return a shell function that waits until at least one seed is reachable.

        The generated snippet polls each configured seed endpoint with ``nc`` and
        optionally honours retry interval/attempts taken from ``MoneroNodeOptions``.

        Returns:
            A multiline shell function definition or an empty string if the node
            does not need to wait for seeds.
        """
        if not self.options.wait_for_seed or not self._seed_endpoints:
            return ""

        endpoints = " ".join(json.dumps(item) for item in self._seed_endpoints)
        interval = max(1, self.options.seed_retry_interval)
        attempts = self.options.seed_retry_attempts if self.options.seed_retry_attempts >= 0 else -1

        return dedent(
            f"""
            seed_endpoints=({endpoints})
            wait_attempts={attempts}
            wait_interval={interval}

            wait_for_seed() {{
                local tries=0
                if [ ${{#seed_endpoints[@]}} -eq 0 ]; then
                    return 0
                fi
                echo "[monero] Waiting for seed node to become reachable..." >&2
                while true; do
                    for endpoint in "${{seed_endpoints[@]}}"; do
                        IFS=':' read -r host port <<< "${{endpoint}}"
                        if nc -z "$host" "$port" >/dev/null 2>&1; then
                            echo "[monero] Seed node $host:$port is reachable" >&2
                            return 0
                        fi
                    done
                    tries=$((tries + 1))
                    if [ {attempts} -ge 0 ] && [ $tries -ge {attempts} ]; then
                echo "[monero] Timed out waiting for seed node, continuing startup" >&2
                        return 1
                    fi
                    sleep {interval}
                done
            }}

            wait_for_seed
            """
        ).strip()

    def _render_rpc_wait_section(self, invoke: bool = False) -> str:
        """Render a shell snippet that waits for the ``monerod`` RPC endpoint."""

        rpc_port = self.options.rpc_bind_port
        if rpc_port is None:
            return ""

        interval = max(1, self.options.rpc_poll_interval)
        attempts = max(1, self.options.rpc_poll_max_attempts)

        block = dedent(
            f"""
            wait_for_rpc() {{
                local tries=0
                local payload='{{"jsonrpc":"2.0","id":"0","method":"get_info"}}'
                while true; do
                    if curl --silent --fail --max-time 5 \
                        -H 'Content-Type: application/json' \
                        -d "$payload" \
                        http://127.0.0.1:{rpc_port}/json_rpc >/dev/null 2>&1; then
                        echo "[monero] RPC endpoint is ready" >&2
                        return 0
                    fi
                    tries=$((tries + 1))
                    if [ $tries -ge {attempts} ]; then
                        echo "[monero] RPC endpoint is still unavailable, continuing anyway" >&2
                        return 1
                    fi
                    sleep {interval}
                done
            }}
            """
        ).strip()

        if invoke:
            block += "\n\nwait_for_rpc"

        return block

    def _render_env_exports(self) -> str:
        """Convert ``NodeOptions.extra_env`` into shell ``export`` statements."""

        if not self.options.extra_env:
            return ""

        exports = []
        for key, value in sorted(self.options.extra_env.items()):
            exports.append(f"export {key}={json.dumps(value)}")

        return "\n".join(exports)

    
    # Helper methods: wallet handling
    
    def _infer_wallet_dir(self) -> str:
        wallet_path = self.options.wallet.wallet_path
        if not wallet_path:
            return os.path.join(self.options.data_dir, "wallets")
        return os.path.dirname(wallet_path)

    def _render_wallet_generation_block(self) -> str:
        """Render the shell snippet that prepares wallet files.

        The script handles wallet auto-generation, mnemonic import and existing
        file validation. It also ensures the CLI log path and address files are
        kept in sync.

        Returns:
            Shell script lines concatenated into a single string. Empty if wallet
            automation is disabled.
        """

        opts = self.options
        if not opts.enable_wallet:
            return ""

        wallet: MoneroWalletSpec = opts.wallet
        if wallet.mode == MoneroWalletMode.NONE:
            return ""

        wallet_path = json.dumps(wallet.wallet_path)
        password = json.dumps(wallet.password)
        log_file = json.dumps(os.path.join(opts.log_dir, "wallet-cli.log"))
        network_flag = self.network.get_network_flag() or ""
        network_flag_literal = json.dumps(network_flag)

        snippets: List[str] = []

        if wallet.mode == MoneroWalletMode.AUTO_GENERATED:
            wallet_args_loop = indent(
                dedent(
                    """
                    for arg in "${wallet_args[@]}"; do
                        cmd+=" $(printf '%q' "$arg")"
                    done
                    """
                ).strip(),
                " " * 24,
            )

            template = """
            if [ ! -f __WALLET_PATH__ ]; then
                wallet_args=(
                    "--generate-new-wallet" __WALLET_PATH__
                    "--password" __PASSWORD__
                    "--mnemonic-language" "English"
                    "--restore-height" "0"
                    "--create-address-file"
                    "--log-file" __LOG_FILE__
                    "--offline"
                )
                if [ -n __NETWORK_FLAG_LITERAL__ ]; then
                    wallet_args+=(__NETWORK_FLAG_LITERAL__)
                fi
                wallet_generate_script=$(mktemp "/tmp/monero-wallet-generate.XXXXXX")
                cat <<'__MONERO_WALLET_GENERATE__' > "$wallet_generate_script"
#!/bin/bash
set -euo pipefail
{
    sleep 1
    printf 'exit\n'
} | "$@"
__MONERO_WALLET_GENERATE__
                chmod +x "$wallet_generate_script"
                if command -v script >/dev/null 2>&1; then
                    cmd="bash"
                    cmd+=" $(printf '%q' "$wallet_generate_script")"
                    cmd+=" $(printf '%q' "$WALLET_CLI_BIN")"
__WALLET_ARGS_LOOP__
                    script -q -c "$cmd" /dev/null || true
                else
                    bash "$wallet_generate_script" "$WALLET_CLI_BIN" "${wallet_args[@]}" >/dev/null 2>&1 || true
                fi
                rm -f "$wallet_generate_script"
            fi
            """

            snippet = dedent(template).strip()
            replacements = {
                "__WALLET_PATH__": wallet_path,
                "__PASSWORD__": password,
                "__LOG_FILE__": log_file,
                "__NETWORK_FLAG_LITERAL__": network_flag_literal,
            }
            for key, value in replacements.items():
                snippet = snippet.replace(key, value)
            snippet = snippet.replace("__WALLET_ARGS_LOOP__", wallet_args_loop)
            snippets.append(snippet)
        elif wallet.mode == MoneroWalletMode.IMPORT_MNEMONIC:
            if wallet.mnemonic:
                mnemonic_file = json.dumps(
                    os.path.join(self._infer_wallet_dir(), "mnemonic.txt")
                )
                restore_append = ""
                if wallet.restore_height:
                    restore_append = (
                        f'                    restore_args+=( "--restore-height" "{wallet.restore_height}" )'
                    )
                snippet = dedent(
                    f"""
                    if [ ! -f {wallet_path} ]; then
                        cat <<'__MONERO_MNEMONIC__' > {mnemonic_file}
{wallet.mnemonic}
__MONERO_MNEMONIC__
                        mnemonic_words=$(tr '\\n' ' ' < {mnemonic_file} | tr -s ' ')
                        restore_args=(
                            "--restore-deterministic-wallet"
                            "--wallet-file" {wallet_path}
                            "--password" {password}
                            "--electrum-seed" "$mnemonic_words"
                            "--create-address-file"
                            "--log-file" {log_file}
                            "--offline"
                        )
                        if [ -n {network_flag_literal} ]; then
                            restore_args+=({network_flag_literal})
                        fi
__RESTORE_APPEND__
                        "$WALLET_CLI_BIN" "${{restore_args[@]}}" >/dev/null 2>&1 || true
                        rm -f {mnemonic_file}
                    fi
                    """
                ).strip()
                snippet = snippet.replace("__RESTORE_APPEND__", restore_append)
                snippets.append(snippet)
            else:
                snippets.append(
                    f'echo "[monero] Mnemonic not provided, cannot import wallet {wallet.wallet_path}" >&2'
                )
        elif wallet.mode == MoneroWalletMode.EXISTING_FILE:
            snippets.append(
                dedent(
                    f"""
                    if [ ! -f {wallet_path} ]; then
                        echo "[monero] Wallet file {wallet.wallet_path} is expected to be pre-provisioned by the user" >&2
                    fi
                    """
                ).strip()
            )

        if opts.enable_wallet and wallet.auto_save_primary_address:
            address_file_literal = json.dumps(f"{wallet.wallet_path}.address.txt")
            primary_address_path = json.dumps(wallet.primary_address_path)
            snippets.append(
                dedent(
                    f"""
                    if [ -f {address_file_literal} ]; then
                        addr_line=$(sed -n '1p' {address_file_literal} | tr -d '\r\n')
                        if [ -n "$addr_line" ]; then
                            printf "%s\n" "$addr_line" > {primary_address_path}
                        fi
                    fi
                    """
                ).strip()
            )

        if opts.enable_wallet:
            template = """
            if [ -f __WALLET_PATH__ ]; then
                wallet_file=__WALLET_PATH__
                wallet_password=__PASSWORD__
                wallet_cli_args=(
                    "--wallet-file" "$wallet_file"
                    "--password" "$wallet_password"
                    "--log-file" __LOG_FILE__
                    "--offline"
                )
                if [ -n __NETWORK_FLAG_LITERAL__ ]; then
                    wallet_cli_args+=(__NETWORK_FLAG_LITERAL__)
                fi
                wallet_cmd_script=$(mktemp "/tmp/monero-wallet-init.XXXXXX")
                cat <<'__MONERO_WALLET_INIT__' > "$wallet_cmd_script"
#!/bin/bash
set -euo pipefail
wallet_password="$1"
shift
{
    printf 'set refresh-from-block-height 0\n'
    sleep 1
    printf '%s\n' "$wallet_password"
    sleep 1
    printf 'save\n'
    sleep 1
    printf 'exit\n'
} | "$@"
__MONERO_WALLET_INIT__
                chmod +x "$wallet_cmd_script"
                if command -v script >/dev/null 2>&1; then
                    cmd="bash"
                    cmd+=" $(printf '%q' "$wallet_cmd_script")"
                    cmd+=" $(printf '%q' "$wallet_password")"
                    cmd+=" $(printf '%q' "$WALLET_CLI_BIN")"
                    for arg in "${wallet_cli_args[@]}"; do
                        cmd+=" $(printf '%q' "$arg")"
                    done
                    script -q -c "$cmd" /dev/null || true
                else
                    bash "$wallet_cmd_script" "$wallet_password" "$WALLET_CLI_BIN" "${wallet_cli_args[@]}" >/dev/null 2>&1 || true
                fi
                rm -f "$wallet_cmd_script"
            fi
            """
            wallet_refresh_block = dedent(template)
            replacements = {
                "__WALLET_PATH__": wallet_path,
                "__PASSWORD__": password,
                "__LOG_FILE__": log_file,
                "__NETWORK_FLAG_LITERAL__": network_flag_literal,
            }
            for key, value in replacements.items():
                wallet_refresh_block = wallet_refresh_block.replace(key, value)
            wallet_refresh_block = wallet_refresh_block.strip()
            snippets.append(wallet_refresh_block)

        return "\n\n".join(snippets)

    def _render_wallet_rescan_block(
        self, daemon_expr: Optional[str] = None, *, include_refresh: bool = True
    ) -> str:
        """Render the wallet rescan script that runs after the RPC endpoint is ready."""

        opts = self.options
        if not opts.enable_wallet:
            return ""

        wallet = opts.wallet
        if not wallet.wallet_path:
            return ""

        wallet_path = json.dumps(wallet.wallet_path)
        password = json.dumps(wallet.password)
        log_file = json.dumps(os.path.join(opts.log_dir, "wallet-cli.log"))
        network_flag = self.network.get_network_flag() or ""
        network_flag_literal = json.dumps(network_flag)

        if daemon_expr is None:
            if opts.rpc_bind_port is None:
                return ""
            daemon_expr = json.dumps(f"127.0.0.1:{opts.rpc_bind_port}")

        rescan_prefix: List[str] = []
        if include_refresh:
            rescan_prefix.extend(
                [
                    "printf 'set refresh-from-block-height 0\\n'",
                    "sleep 1",
                    "printf '%s\\n' \"$wallet_password\"",
                    "sleep 1",
                ]
            )

        rescan_suffix = [
            "printf 'save\\n'",
            "sleep 1",
            "printf 'exit\\n'",
        ]

        rescan_body_no_confirm = rescan_prefix + [
            "printf 'rescan_bc\\n'",
            "sleep 1",
        ] + rescan_suffix

        rescan_body_with_confirm = rescan_prefix + [
            "printf 'rescan_bc\\n'",
            "sleep 1",
            "printf 'yes\\n'",
            "sleep 1",
        ] + rescan_suffix

        rescan_body = "\n".join(rescan_body_no_confirm)
        rescan_body_confirm = "\n".join(rescan_body_with_confirm)

        lines: List[str] = []
        lines.append(f"        if [ -f {wallet_path} ]; then")
        lines.append(f"            wallet_file={wallet_path}")
        lines.append(f"            wallet_password={password}")
        lines.append(
            "            if pgrep -f \"monero-wallet-rpc --wallet-file $wallet_file\" >/dev/null 2>&1; then"
        )
        lines.append(
            "                echo \"[monero] Stopping existing wallet-rpc before running CLI commands\" >&2"
        )
        lines.append(
            "                pkill -f \"monero-wallet-rpc --wallet-file $wallet_file\" || true"
        )
        lines.append("                sleep 1")
        lines.append("            fi")
        lines.append("            wallet_cli_args=(")
        lines.append("                \"--wallet-file\" \"$wallet_file\"")
        lines.append("                \"--password\" \"$wallet_password\"")
        lines.append(f"                \"--daemon-address\" {daemon_expr}")
        lines.append(f"                \"--log-file\" {log_file}")
        lines.append("            )")
        if network_flag:
            lines.append(f"            if [ -n {network_flag_literal} ]; then")
            lines.append(f"                wallet_cli_args+=({network_flag_literal})")
            lines.append("            fi")
        lines.append(
            "            wallet_rescan_script=$(mktemp \"/tmp/monero-wallet-rescan.XXXXXX\")"
        )
        lines.append(
            "            cat <<'__MONERO_WALLET_RESCAN__' > \"$wallet_rescan_script\""
        )
        lines.extend(
            [
                "#!/bin/bash",
                "set -euo pipefail",
                "wallet_password=\"$1\"",
                "shift",
                "{",
                *rescan_body.splitlines(),
                "} | \"$@\"",
                "__MONERO_WALLET_RESCAN__",
            ]
        )
        lines.append("            chmod +x \"$wallet_rescan_script\"")
        lines.append(
            "            wallet_rescan_confirm_script=$(mktemp \"/tmp/monero-wallet-rescan-confirm.XXXXXX\")"
        )
        lines.append(
            "            cat <<'__MONERO_WALLET_RESCAN_CONFIRM__' > \"$wallet_rescan_confirm_script\""
        )
        lines.extend(
            [
                "#!/bin/bash",
                "set -euo pipefail",
                "wallet_password=\"$1\"",
                "shift",
                "{",
                *rescan_body_confirm.splitlines(),
                "} | \"$@\"",
                "__MONERO_WALLET_RESCAN_CONFIRM__",
            ]
        )
        lines.append("            chmod +x \"$wallet_rescan_confirm_script\"")
        lines.append("")
        lines.append("            run_wallet_rescan() {")
        lines.append("                local script_path=\"$1\"")
        lines.append("                local exit_code=0")
        lines.append("                local cmd=\"\"")
        lines.append("                if command -v script >/dev/null 2>&1; then")
        lines.append("                    cmd=\"bash\"")
        lines.append("                    cmd+=\" $(printf '%q' \"$script_path\")\"")
        lines.append("                    cmd+=\" $(printf '%q' \"$wallet_password\")\"")
        lines.append("                    cmd+=\" $(printf '%q' \"$WALLET_CLI_BIN\")\"")
        lines.append("                    for arg in \"${wallet_cli_args[@]}\"; do")
        lines.append("                        cmd+=\" $(printf '%q' \"$arg\")\"")
        lines.append("                    done")
        lines.append("                    if command -v timeout >/dev/null 2>&1; then")
        lines.append("                        timeout 120 script -q -c \"$cmd\" /dev/null || exit_code=$?")
        lines.append("                    else")
        lines.append("                        script -q -c \"$cmd\" /dev/null || exit_code=$?")
        lines.append("                    fi")
        lines.append("                else")
        lines.append("                    if command -v timeout >/dev/null 2>&1; then")
        lines.append(
            "                        timeout 120 bash \"$script_path\" \"$wallet_password\" \"$WALLET_CLI_BIN\" \"${wallet_cli_args[@]}\" >/dev/null 2>&1 || exit_code=$?"
        )
        lines.append("                    else")
        lines.append(
            "                        bash \"$script_path\" \"$wallet_password\" \"$WALLET_CLI_BIN\" \"${wallet_cli_args[@]}\" >/dev/null 2>&1 || exit_code=$?"
        )
        lines.append("                    fi")
        lines.append("                fi")
        lines.append("                return \"$exit_code\"")
        lines.append("            }")
        lines.append("")
        lines.append(
            "            if ! run_wallet_rescan \"$wallet_rescan_script\"; then"
        )
        lines.append(
            "                echo \"[monero] Rescan needs confirmation, retrying with yes\" >&2"
        )
        lines.append(
            "                run_wallet_rescan \"$wallet_rescan_confirm_script\" || true"
        )
        lines.append("            fi")
        lines.append("")
        lines.append(
            "            rm -f \"$wallet_rescan_script\" \"$wallet_rescan_confirm_script\""
        )
        lines.append("        fi")

        wallet_rescan_block = "\n".join(lines)

        return wallet_rescan_block

    
    # Overridable: start script generation
    
    def _render_start_script(self) -> str:
        """Render the complete start script for the concrete server implementation."""
        raise NotImplementedError

    # MIRROR mode requires no extra installation steps


class MoneroFullNodeServer(MoneroBaseServer):
    """Node that runs ``monerod`` (full or pruned)."""

    def install(self, node: Node):  # pragma: no cover - invoked at runtime
        self._ensure_prerequisites(node)
        script = self._render_start_script()
        node.setFile("/usr/local/bin/seedemu-monero-node.sh", script)
        node.addBuildCommandAtEnd("chmod +x /usr/local/bin/seedemu-monero-node.sh")
        node.appendStartCommand("/usr/local/bin/seedemu-monero-node.sh")

    
    # Pre-installation preparation
    
    def _ensure_prerequisites(self, node: Node):
        """Prepare filesystem and port forwarding before writing the start script."""
        opts = self.options

        if opts.binary_source != MoneroBinarySource.MIRROR:
            self.network.log(
                f"Node {node.getName()} uses custom binary: monerod={opts.binaries.monerod}"
            )

        node.insertStartCommand(0, "cd /")

        if opts.persist_data:
            node.addPersistentStorage(opts.data_dir)

        wallet_dir = self._infer_wallet_dir()

        if opts.expose_p2p and opts.p2p_bind_port:
            node.addPortForwarding(opts.p2p_bind_port, opts.p2p_bind_port, proto="tcp")
        if opts.expose_rpc and opts.rpc_bind_port:
            node.addPortForwarding(opts.rpc_bind_port, opts.rpc_bind_port, proto="tcp")
        if opts.expose_zmq and opts.zmq_bind_port:
            node.addPortForwarding(opts.zmq_bind_port, opts.zmq_bind_port, proto="tcp")

        # Pre-create directories to avoid repeated checks inside scripts
        node.appendStartCommand(f"mkdir -p {opts.data_dir}")
        node.appendStartCommand(f"mkdir -p {opts.log_dir}")
        if opts.enable_wallet:
            node.appendStartCommand(f"mkdir -p {wallet_dir}")

    
    # Fluent configuration
    
    def enableMining(
        self,
        *,
        threads: Optional[int] = None,
        address: Optional[str] = None,
        trigger: Optional[MoneroMiningTrigger] = None,
    ) -> "MoneroFullNodeServer":
        """Enable built-in mining support for the node."""
        if self.options.kind == MoneroNodeKind.PRUNED:
            raise AssertionError("Pruned nodes do not support mining")

        self.options.enable_mining = True
        if threads is not None:
            self.options.mining_threads = threads
        if address is not None:
            self.options.mining_address = address
        if trigger is not None:
            self.options.mining_trigger = trigger

        if self.options.mining_address is None:
            self.options.enable_wallet = True
            wallet_cfg = self.options.wallet
            wallet_cfg.auto_save_primary_address = True
            wallet_cfg.enable_rpc = True
            if not wallet_cfg.rpc_user:
                wallet_cfg.rpc_user = "miner"
            if not wallet_cfg.rpc_password:
                wallet_cfg.rpc_password = wallet_cfg.password or "miner"

        return self

    def disableMining(self) -> "MoneroFullNodeServer":
        """Disable built-in mining for this node."""
        self.options.enable_mining = False
        return self

    def setMiningAddress(self, address: str) -> "MoneroFullNodeServer":
        self.options.mining_address = address
        return self

    def setMiningThreads(self, threads: int) -> "MoneroFullNodeServer":
        self.options.mining_threads = threads
        return self

    def setMiningTrigger(
        self, trigger: MoneroMiningTrigger
    ) -> "MoneroFullNodeServer":
        self.options.mining_trigger = trigger
        return self

    def setSeedRole(self) -> "MoneroFullNodeServer":
        super().setSeedRole()
        return self

    def setClientRole(self) -> "MoneroFullNodeServer":
        super().setClientRole()
        return self

    def setFixedDifficulty(self, difficulty: Optional[int]) -> "MoneroFullNodeServer":
        super().setFixedDifficulty(difficulty)
        return self

    def exposePorts(
        self,
        *,
        p2p: Optional[bool] = None,
        rpc: Optional[bool] = None,
        zmq: Optional[bool] = None,
    ) -> "MoneroFullNodeServer":
        super().exposePorts(p2p=p2p, rpc=rpc, zmq=zmq)
        return self

    
    # Start script generation
    
    def _render_start_script(self) -> str:
        """Compose the full start script used by a full/pruned node."""
        opts = self.options
        wallet = opts.wallet
        wallet_dir = self._infer_wallet_dir()
        wallet_setup_block = self._render_wallet_generation_block()

        daemon_args: List[str] = [
            f"--data-dir={opts.data_dir}",
            f"--log-file={os.path.join(opts.log_dir, 'monerod.log')}",
            f"--p2p-bind-ip={opts.p2p_bind_ip}",
        ]

        if opts.p2p_bind_port is not None:
            daemon_args.append(f"--p2p-bind-port={opts.p2p_bind_port}")

        daemon_args.append(f"--rpc-bind-ip={opts.rpc_bind_ip}")
        if opts.rpc_bind_port is not None:
            daemon_args.append(f"--rpc-bind-port={opts.rpc_bind_port}")

        daemon_args.extend(
            [
                "--confirm-external-bind",
                "--allow-local-ip",
                "--log-level=1",
                "--non-interactive",
                "--no-igd",
            ]
        )

        if opts.zmq_bind_port:
            daemon_args.append(f"--zmq-rpc-bind-ip={opts.zmq_bind_ip}")
            daemon_args.append(f"--zmq-rpc-bind-port={opts.zmq_bind_port}")

        # Network-specific flag
        flag = self.network.get_network_flag()
        if flag:
            daemon_args.append(flag)

        if opts.kind == MoneroNodeKind.PRUNED:
            daemon_args.append("--prune-blockchain")

        if opts.fixed_difficulty:
            daemon_args.append(f"--fixed-difficulty={opts.fixed_difficulty}")

        # Connection strategy
        if self._seed_endpoints:
            for endpoint in self._seed_endpoints:
                if opts.connect_mode == MoneroSeedConnectionMode.EXCLUSIVE:
                    daemon_args.append(f"--add-exclusive-node={endpoint}")
                elif opts.connect_mode == MoneroSeedConnectionMode.PRIORITY:
                    daemon_args.append(f"--add-priority-node={endpoint}")
                else:
                    daemon_args.append(f"--seed-node={endpoint}")

        for peer in opts.preferred_peers:
            daemon_args.append(f"--add-peer={peer}")

        daemon_args.extend(sanitize_extra_args(opts.extra_daemon_args))

        daemon_args_str = "\n".join(
            f"DAEMON_ARGS+=(\"{arg}\")" for arg in daemon_args if arg
        )

        seed_section = self._render_seed_wait_section()
        env_exports = self._render_env_exports()

        should_wait_for_rpc = (
            opts.rpc_bind_port is not None
            and opts.enable_wallet
            and wallet.enable_rpc
        )

        rpc_wait_section = ""
        if should_wait_for_rpc:
            rpc_wait_section = self._render_rpc_wait_section(invoke=True)

        wallet_rescan_block = ""
        if should_wait_for_rpc:
            wallet_rescan_block = self._render_wallet_rescan_block()

        mining_enabled = opts.enable_mining and (
            opts.mining_trigger != MoneroMiningTrigger.MANUAL
        )

        wallet_gen_block = wallet_setup_block

        mining_setup_block = ""
        if mining_enabled:
            direct_address = opts.mining_address or self.network.get_default_mining_address()
            if direct_address:
                mining_setup_block = dedent(
                    f"""
                    echo "[monero] Using fixed mining address {direct_address}" >&2
                    DAEMON_ARGS+=("--start-mining={direct_address}")
                    DAEMON_ARGS+=("--mining-threads={opts.mining_threads}")
                    """
                ).strip()
            elif opts.enable_wallet and wallet.auto_save_primary_address:
                primary_address_path = json.dumps(wallet.primary_address_path)
                address_file_literal = json.dumps(f"{wallet.wallet_path}.address.txt")
                mining_setup_block = dedent(
                    f"""
                    mining_target=""
                    if [ -f {primary_address_path} ]; then
                        mining_target=$(sed -n '1p' {primary_address_path} | tr -d '[:space:]')
                    fi
                    if [ -z "$mining_target" ] && [ -f {address_file_literal} ]; then
                        mining_target=$(grep -oE '[0-9A-Za-z]{{95}}' {address_file_literal} | head -n 1 | tr -d '\r\n')
                        if [ -n "$mining_target" ]; then
                            printf "%s\n" "$mining_target" > {primary_address_path}
                        fi
                    fi
                    if [ -n "$mining_target" ]; then
                        DAEMON_ARGS+=("--start-mining=$mining_target")
                        DAEMON_ARGS+=("--mining-threads={opts.mining_threads}")
                        echo "[monero] Automatically configured mining address $mining_target" >&2
                    else
                        echo "[monero] Mining address not found, mining parameters were not injected" >&2
                    fi
                    """
                ).strip()
            else:
                mining_setup_block = "echo \"[monero] No mining address configured, mining parameters were not injected\" >&2"

        wallet_rpc_block = ""
        if opts.enable_wallet and wallet.enable_rpc:
            rpc_login = ""
            if wallet.rpc_user and wallet.rpc_password:
                rpc_login = f"--rpc-login={wallet.rpc_user}:{wallet.rpc_password}"
            allow_external = "--disable-rpc-ban"
            if not wallet.allow_external_rpc:
                allow_external = ""
            extra_flags = " ".join(wallet.extra_rpc_flags)
            daemon_address = f"127.0.0.1:{opts.rpc_bind_port}"
            wallet_rpc_log = json.dumps(os.path.join(opts.log_dir, "wallet-rpc.log"))
            network_flag_cli = flag or ""
            wallet_rpc_block = dedent(
                f"""
                echo "[monero] Starting wallet RPC..." >&2
                touch {wallet_rpc_log}
                "$WALLET_RPC_BIN" --daemon-address {daemon_address} \
                    --wallet-file {json.dumps(wallet.wallet_path)} \
                    --password {json.dumps(wallet.password)} \
                    --rpc-bind-ip {json.dumps(wallet.rpc_bind_ip)} \
                    --rpc-bind-port {wallet.rpc_bind_port} \
                    --confirm-external-bind \
                    --trusted-daemon \
                    {rpc_login} {allow_external} {extra_flags} {network_flag_cli} \
                    >> {wallet_rpc_log} 2>&1 &
                """
            ).strip()

        tail_helper_block = dedent(
            """
            declare -a TAIL_PIDS=()
            cleanup_tail_processes() {
                for pid in "${TAIL_PIDS[@]}"; do
                    if [ -n "$pid" ]; then
                        kill "$pid" 2>/dev/null || true
                        wait "$pid" 2>/dev/null || true
                    fi
                done
            }
            trap cleanup_tail_processes EXIT
            """
        ).strip()

        monerod_tail_block = dedent(
            """
            if command -v tail >/dev/null 2>&1; then
                tail_monitor_pattern='BLOCK SUCCESSFULLY ADDED|SYNCHRONIZED OK|There were [0-9]+ blocks'
                (
                    set +e
                    set +o pipefail >/dev/null 2>&1 || true
                    tail -F "$monerod_log" | grep --line-buffered -E "$tail_monitor_pattern" >&2
                ) &
                TAIL_PIDS+=("$!")
            fi
            """
        ).strip()

        wallet_cli_monitor_block = ""
        if wallet_setup_block or wallet_rescan_block:
            wallet_cli_log_literal = json.dumps(
                os.path.join(opts.log_dir, "wallet-cli.log")
            )
            wallet_cli_monitor_block = dedent(
                f"""
                wallet_cli_log={wallet_cli_log_literal}
                touch "$wallet_cli_log"
                if command -v tail >/dev/null 2>&1; then
                    wallet_cli_monitor_pattern='Generated new wallet|Opened wallet|Background refresh thread started|wallet failed to connect|Wallet initialization failed'
                    (
                        set +e
                        set +o pipefail >/dev/null 2>&1 || true
                        tail -F "$wallet_cli_log" | grep --line-buffered -E "$wallet_cli_monitor_pattern" >&2
                    ) &
                    TAIL_PIDS+=("$!")
                fi
                """
            ).strip()

        wallet_rpc_monitor_block = ""
        if wallet_rpc_block:
            wallet_rpc_monitor_block = dedent(
                f"""
                wallet_rpc_log={wallet_rpc_log}
                touch "$wallet_rpc_log"
                if command -v tail >/dev/null 2>&1; then
                    wallet_rpc_monitor_pattern='Starting wallet RPC server|Binding on|Loaded wallet keys file|Failed to lock'
                    (
                        set +e
                        set +o pipefail >/dev/null 2>&1 || true
                        tail -F "$wallet_rpc_log" | grep --line-buffered -E "$wallet_rpc_monitor_pattern" >&2
                    ) &
                    TAIL_PIDS+=("$!")
                fi
                """
            ).strip()

        return dedent(
            f"""
            #!/bin/bash
            set -euo pipefail

            MONEROD_BIN={json.dumps(opts.binaries.monerod)}
            WALLET_CLI_BIN={json.dumps(opts.binaries.wallet_cli)}
            WALLET_RPC_BIN={json.dumps(opts.binaries.wallet_rpc)}
            LOG_DIR={json.dumps(opts.log_dir)}

            mkdir -p "$LOG_DIR"

            declare -a DAEMON_ARGS
{daemon_args_str}

            {env_exports}

            {wallet_gen_block}

            {mining_setup_block}

            {seed_section}

            monerod_log="{os.path.join(opts.log_dir, 'monerod.log')}"
            touch "$monerod_log"

            {tail_helper_block}

            {monerod_tail_block}

            {wallet_cli_monitor_block}

            {wallet_rpc_monitor_block}

            echo "[monero] Starting monerod..." >&2
            "$MONEROD_BIN" "${{DAEMON_ARGS[@]}}" \
                >> "$monerod_log" 2>&1 &
            DAEMON_PID=$!

            {rpc_wait_section}

            {wallet_rescan_block}

            {wallet_rpc_block}

            wait "$DAEMON_PID"
            EXIT_STATUS=$?

            exit "$EXIT_STATUS"
            """
        ).strip() + "\n"


class MoneroLightNodeServer(MoneroBaseServer):
    """Light node that only runs ``monero-wallet-rpc``."""

    def install(self, node: Node):  # pragma: no cover
        """Install artifacts required by a light wallet node on the target."""
        opts = self.options

        if opts.binary_source != MoneroBinarySource.MIRROR:
            self.network.log(
                f"Light node {node.getName()} uses custom wallet binary {opts.binaries.wallet_rpc}"
            )

        wallet_dir = self._infer_wallet_dir()
        node.insertStartCommand(0, "cd /")
        node.appendStartCommand(f"mkdir -p {opts.log_dir}")
        node.appendStartCommand(f"mkdir -p {wallet_dir}")

        wallet = opts.wallet
        node.addSoftware("curl")

        script = self._render_start_script()
        node.setFile("/usr/local/bin/seedemu-monero-light.sh", script)
        node.addBuildCommandAtEnd("chmod +x /usr/local/bin/seedemu-monero-light.sh")
        node.appendStartCommand("/usr/local/bin/seedemu-monero-light.sh")

    def _render_start_script(self) -> str:
        """Render the launcher script executed inside a light wallet container."""
        opts = self.options
        wallet = opts.wallet
        wallet_dir = self._infer_wallet_dir()
        wallet_setup_block = self._render_wallet_generation_block()
        wallet_sync_block = self._render_wallet_rescan_block(
            daemon_expr='"$primary_daemon"', include_refresh=False
        )

        primary_daemon_block = ""
        if wallet_sync_block:
            primary_daemon_body = indent(wallet_sync_block, " " * 12).rstrip()
            primary_daemon_body = primary_daemon_body.replace(
                "\n" + " " * 12 + "__MONERO_WALLET_RESCAN__",
                "\n__MONERO_WALLET_RESCAN__",
            )
            primary_daemon_body = primary_daemon_body.replace(
                "\n" + " " * 12 + "__MONERO_WALLET_RESCAN_CONFIRM__",
                "\n__MONERO_WALLET_RESCAN_CONFIRM__",
            )
            primary_daemon_block = (
                " " * 12
                + "primary_daemon=\"${UPSTREAMS[0]}\"\n"
                + " " * 12
                + "if [ -n \"$primary_daemon\" ]; then\n"
                + primary_daemon_body
                + "\n"
                + " " * 12
                + "fi"
            )

        upstreams = opts.upstream_nodes
        if not upstreams and self._fullnode_rpc_endpoints:
            upstreams = list(self._fullnode_rpc_endpoints)

        daemon_address_list = " ".join(json.dumps(item) for item in upstreams)

        rpc_login = ""
        if wallet.rpc_user and wallet.rpc_password:
            rpc_login = f"--rpc-login={wallet.rpc_user}:{wallet.rpc_password}"

        allow_external = "--disable-rpc-ban"
        if not wallet.allow_external_rpc:
            allow_external = ""

        wallet_path_literal = json.dumps(wallet.wallet_path)
        password_literal = json.dumps(wallet.password)
        rpc_bind_ip_literal = json.dumps(wallet.rpc_bind_ip)
        wallet_rpc_log = json.dumps(os.path.join(opts.log_dir, "wallet-rpc.log"))

        extra_flags = " ".join(wallet.extra_rpc_flags)
        network_flag_cli = self.network.get_network_flag() or ""

        env_exports = self._render_env_exports()

        return dedent(
            f"""
            #!/bin/bash
            set -euo pipefail

            WALLET_CLI_BIN={json.dumps(opts.binaries.wallet_cli)}
            WALLET_RPC_BIN={json.dumps(opts.binaries.wallet_rpc)}
            LOG_DIR={json.dumps(opts.log_dir)}

            UPSTREAMS=({daemon_address_list})
            if [ ${{#UPSTREAMS[@]}} -eq 0 ]; then
                echo "[monero-light] No upstream full node specified, exiting" >&2
                exit 1
            fi

            mkdir -p "$LOG_DIR"

            {env_exports}

            {wallet_setup_block}

{primary_daemon_block if primary_daemon_block else ""}

            for daemon in "${{UPSTREAMS[@]}}"; do
                echo "[monero-light] Using upstream $daemon" >&2
                "$WALLET_RPC_BIN" --daemon-address "$daemon" \
                    --wallet-file {wallet_path_literal} \
                    --password {password_literal} \
                    --rpc-bind-ip {rpc_bind_ip_literal} \
                    --rpc-bind-port {wallet.rpc_bind_port} \
                    --confirm-external-bind \
                    {rpc_login} {allow_external} {extra_flags} {network_flag_cli} \
                    >> {wallet_rpc_log} 2>&1 &
            done

            wait
            """
        ).strip() + "\n"


