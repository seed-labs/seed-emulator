## 2026-11-12 15:56 - Restore upstream SeedEMU and validate migrated k8sTools

- User intent: restore the target repository's `seedemu/` to latest
  `upstream/k8s-0917`, replace `seedemu/k8sTools/` with the current working
  implementation, and make B61 run with working ping. Confirmed by the user.
- Scope: `seedemu/`, existing `examples/internet/B61_k8s_compile`, and isolated
  KVM/K3s validation resources. Existing workflow edits and other VMs are preserved.
- Baseline: `git fetch upstream k8s-0917` resolved to
  `776f2e7f4bc25a089c0684ce5a835b1113b494e8`. Restored only `seedemu/` with
  `git restore --source=<commit> --worktree -- seedemu`; no branch reset or commit.
- Backup: original `seedemu/` and B61 files are archived under
  `/data/lxl/k8sTools/b61-migration-backup-20261112-155603/before.tar.gz`.
  The archive is private and excludes Python caches/generated output.
- Copy: `rsync -a --delete` copied the source working tree's `seedemu/k8sTools/`,
  including uncommitted/new files, excluding Python caches. Initial byte comparison
  passed. All 207 non-k8sTools upstream files matched their Git blob hashes.
  A first `git diff` assertion was unsuitable for worktree-only case renames;
  the direct file/blob check replaced it and passed.
- Compatibility changes: B61 adds runtime sysctls/redirect settings through
  `appendStartCommand`, keeping the upstream compiler untouched. Existing static
  checks now reference the copied lower-camel-case helper filenames. Fixed
  deployment parent/MTU selection in the copied runtime renderers; explicit
  trunk mappings preserve separate NICs. These targeted fixes are local to
  the target repository; the source repository is unchanged.
- Added `configKvmValidation.yaml` and read-only `validateRuntime.py`; updated
  README with default placement, archive/queue deployment and lifecycle commands.
- Commands/checks so far: CLI `up --help` confirms default `nodeByAs`;
  Python syntax checks passed for copied package/example files; `bash -n
  prepare.sh` passed. Standardized B61 compile passed. Initial static checks
  exposed missing redirect startup and stale physical CNI parent; both were fixed.
- Live command: `K8sTools.py build --input <generated-local-validation.yaml>
  --config-k3s <artifacts>/configK3s.yaml --kubeconfig <artifacts>/kubeconfig.yaml
  --inventory <artifacts>/inventory.yaml --keep-temp`. Creates only
  `seedemu-b61-verify-*` VMs/network. Generated lab-specific YAML reuses existing
  cloud-image/bootstrap caches and stores test disks under `/data/lxl/k8sTools`.
- Evidence: repository-relative `ci-artifacts/b61-migration-20261112-155603/`
  contains commands, build logs, baseline inventory and integrity results.
  Static-runner evidence is in `ci-artifacts/b61-compile/`.
- Validation: live build/up/ping/clean/redeploy/destroy results will be appended
  as each stage completes. Physical-node and multi-host modes are checked
  statically; this task's live test uses an isolated local-KVM cluster.

### 16:10 - Static checks and cluster build passed

- Standardized commands: `python3 seedemu/testing/cli.py compile
  examples/internet/B61_k8s_compile/example.yaml --artifact-dir ci-artifacts/b61-compile`
  and the corresponding `test` command passed after fixes.
- Static validation checks 58 Deployments, 29 NADs, deterministic compiler
  output, image contexts, and local/physical/multi-host renderings. The fast
  runtime manifests match compatibility-rendered NADs in all three modes.
- Direct dual-trunk check confirms trunk0 -> ens3, trunk1 -> ens4, and rejection
  of an unmapped trunk; evidence: `trunk-mapping-check.json`.
- Live `build` exited 0. Ansible reported no failed/unreachable hosts, K3s
  v1.29.15+k3s1 and Multus became ready on the three isolated VMs.
- Started first `K8sTools.py up` with no `--partition` argument. The receipt
  selected `nodeByAs` and assigned 58 workloads evenly (29/29) to the two workers.
  Image archive build/import is in progress; exact argv is in `up-first-command.json`.

### 16:11 - First deployment and ping results

- First `up` passed in 101.4 seconds. All 58 Pods were Ready, split 29/29 across
  the workers; node-specific image imports and 35 required VLAN parents passed.
- First live check completed 73 directed ping pairs covering 25 hosts; all passed
  with zero loss, including 48 cross-worker pairs. Original report is retained
  under `runtime-first/`.
- The initial checker reported false negatives for CIDR-vs-address comparison,
  route-server inclusion in forwarding FIB checks, and expecting a protocol label
  that `ip route show proto bird` omits. Corrected the checker using raw API/CLI
  evidence; no routing/container settings were changed to address these checks.
- BIRD/FIB checks follow the deterministic-AS and VM-load gate from
  `seedemu-bird-fib-verify`: BIRD protocol sample over the first 10 router ASes,
  and network-count versus main-FIB count over every router AS, excluding IX
  route servers. A fresh full read-only verification is running.

### 16:20 - Final verification and cleanup passed

- First complete read-only runtime report: `runtime-first-final/runtime-summary.json`
  is PASS. All 58 Pods were Ready without restarts; all requested secondary
  addresses matched; whole-AS nodeName placement covered two workers (29/29).
  All 73 directed ping pairs passed with 0% loss (25 hosts, 48 cross-worker pairs).
  The first 10 router-AS protocol samples and all 17 router-AS FIB checks passed.
- Lifecycle commands passed: `K8sTools.py clean`, explicit `kubectl wait
  --for=delete namespace/seedemu --timeout=180s`, and a second `K8sTools.py up`
  without partition overrides. Clean retained all three Ready cluster nodes.
  First up took 101.4 seconds and redeploy took 48.4 seconds.
- Immediate post-redeploy checking correctly exposed transient iBGP Connect
  states and 2 ping pairs with initial loss. Read-only `birdc show protocols`
  subsequently confirmed all affected sessions Established. Without changing
  routing or adding automatic waiting to up, reran validation after convergence:
  `runtime-redeploy-converged/runtime-summary.json` is PASS, with all 73 pairs
  again at 0% loss and all 17 router-AS checks passing. README documents both
  the convergence requirement and asynchronous namespace deletion.
- `redeploy-source-integrity.json` confirms the original unpartitioned compiler
  source was restored before the second up; placement was recomputed normally.
- A fresh compile into an artifact-only output directory and `test_compile.py`
  passed. Besides local/physical/multi-host renderings, an explicit cni.mtu=1360
  case verifies that deployment MTU overrides the compiler's 1400; normal and
  fast renderers agree. Final syntax checks passed for 50 Python files;
  `bash -n prepare.sh` and `git diff --check` passed.
- Final cleanup passed: `K8sTools.py clean`, namespace deletion wait, then
  `K8sTools.py destroy -d <artifacts>/configK3s.yaml` (exit 0). No test VMs,
  test network, test disks or cloud-init files remain. Removed the task's retained
  temporary build directory and empty test storage directories after saving logs.
  Original VM/network inventory and the preexisting workflow edit are preserved.
- Final code integrity: all 207 files outside `seedemu/k8sTools/` still match
  upstream `776f2e7f4bc25a089c0684ce5a835b1113b494e8`. Relative to the copied
  source k8sTools tree, target-only integration fixes touch README.md and
  resources/running/{manageK8sManifest,manageRunningStage,manageWorkload}.py.
- B61 changed/added files: mini_internet_k8s.py, test_compile.py, README.md,
  configKvmValidation.yaml, validateRuntime.py and this worklog. K8sTools.py
  remains the existing thin wrapper. No Git commit or branch reset was made.
- Final summary: `ci-artifacts/b61-migration-20261112-155603/validation-summary.json`.
  Exact executed argv/exit codes and logs are saved beside it. The initial failed
  checker and convergence reports remain available; successful reports are named
  explicitly above. The independent backup remains at the recorded backup path.
- Scope limit: physical-node and multi-host KVM configurations were statically
  checked, including the fast deployment renderer. Live commands used only the
  isolated local-KVM test cluster; no existing physical or remote lab was rebuilt.

## 2026-11-12 17:32 - Recommit migration with the existing renamed filenames

- User intent: undo the latest commit, repair the filename changes introduced
  by the migration, then run Git add and commit again.
- Scope: `seedemu/compiler/Kubernetes.py`, `seedemu/k8sTools/`, B61 integration
  files, and the existing `.github/workflows/on-pull-request.yaml` path fixes.
- History: inspected `git status`, `git log`, `git show`, `git diff-tree`,
  `git branch -vv`, and `git reflog`. Commit `72c17f6e` established the uppercase
  filenames; `5b3d321e` unintentionally changed 31 of those paths back to lowercase.
- Backup: `git branch backup/before-rename-fix-20261112-172940 5b3d321e`
  preserves the original commit. Saved the initial worktree patch and rename
  mapping under `.git/codex-rename-fix-20261112-172940/`.
- Commands: `git reset --soft 72c17f6e` removed the latest commit from the
  active branch while preserving its changes and the preexisting CI edit.
  A local Python repair restored all 31 prior filenames and updated imports,
  embedded shell paths, runtime subprocess paths, tests, CLI text, and README
  references in 36 files. New scripts retain their existing names.
- Changes: preserved the original migration functionality and included the
  already edited CI workflow. Removed extra EOF blank lines in `partition.py`
  and `resources/running/partitionWorkload.py` after the first staged
  `git diff --cached --check` reported them.
- Validation: Python `py_compile.compile(..., doraise=True)` passed for 54 relevant Python
  files. `python3 -m seedemu.k8sTools --help`, B61 `K8sTools.py --help`, and
  eight internal resource CLI help/import checks passed. Filename/reference
  assertions passed for all 31 restored paths and 139 CI file references.
- Validation: extracted all 18 `SHELL_BODY` strings with Python AST and ran
  `bash -n` on each; also ran `bash -n` on B61 `prepare.sh`. All passed.
- Validation: compared 75 relevant files against `5b3d321e`, mapping each
  renamed path to its restored path. Content differs only in letter case and
  trailing blank lines, before this worklog entry was appended.
- Commands: `python3 examples/internet/B61_k8s_compile/mini_internet_k8s.py
  --output-dir ci-artifacts/b61-rename-fix-20261112-172940/output` passed.
  `python3 examples/internet/B61_k8s_compile/test_compile.py --output-dir
  ci-artifacts/b61-rename-fix-20261112-172940/output --artifact-dir
  ci-artifacts/b61-rename-fix-20261112-172940` passed. The report validates
  58 images, 29 networks, local KVM/physical/multi-host rendering, and an
  explicit MTU override; both runtime renderers agree in all four modes.
- Git commands: staged the compiler, k8sTools, B61, and workflow changes with
  `git add -A -- .github/workflows/on-pull-request.yaml seedemu/compiler
  seedemu/k8sTools examples/internet/B61_k8s_compile`; ran the final staged
  whitespace check before `git commit -m "Preserve renamed K8s modules in workflow migration"`.
- Notes: build/deploy/destroy commands and live VM/cluster tests were not run
  because this task changes filenames and references. Compile/test artifacts
  and logs are ignored under `ci-artifacts/b61-rename-fix-20261112-172940/`.
  No push was requested.
