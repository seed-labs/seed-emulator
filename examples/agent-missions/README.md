# Seed Agent Missions: Six-Class Interactive Operations Baseline

`examples/agent-missions` is the reusable baseline for attached-runtime SEED operations.
It is not a one-off demo pack. The goal is to validate that the agent can operate on already-running SEED networks with supervised, traceable, and replayable behavior.

The baseline loop is:

`attach -> inspect -> decide -> operate -> verify -> summarize`

Interactive Codex operation is the primary mode. Non-interactive mission execution is the regression and evidence-export path.

Core properties:

- task semantics live in YAML
- execution is driven by `seed_agent_task_*` APIs
- runtime context is attached from real running outputs
- reports are execution-trace-first, not summary-only

Curated agent-facing runtime bundles now live in `examples/agent-specific`.
Legacy showcase remains in `examples/agent-base`.

---

## Directory Layout

```text
examples/agent-missions/
├── tasks/          # mission specs (YAML contract)
├── playbooks/      # low-level fallback templates
├── dialogues/      # example multi-turn interactions
├── _common/        # API invocation helpers
└── run_task_demo.sh
```

---

## Six-Class Matrix

- Diagnosis / Maintenance
  - `TS_B00_BGP_FLAP_ROOTCAUSE`
- Disturbance Recovery
  - `RS_B29_FAULT_IMPACT_ABLATION`
- Routing Security
  - `TS_B00_PREFIX_HIJACK_LIVE`
- Service Reachability
  - `TS_B29_MAIL_REACHABILITY_DEBUG`
- Security Offense-Defense
  - `SEC_B29_SOCIAL_ENGINEERING_TRIAGE`
  - `SEC_B29_DNS_MAIL_ABUSE_RESPONSE`
- Research Experiments
  - `RS_B00_CONVERGENCE_COMPARISON`

Each accepted baseline task now declares:

- `scenario_class`
- `scale_hints`
- `rollback_required`
- `evidence_requirements`
- `skill_patterns`

---

## Entry Points

Prerequisites:

- SeedOps MCP server is running
- Seed-Agent MCP server is running
- `SEED_AGENT_MCP_URL`, `SEED_AGENT_MCP_TOKEN` are set

Interactive mode from repo root:

```bash
scripts/seed-codex up
scripts/seed-codex ui
```

Non-interactive mission mode from repo root:

```bash
scripts/seed-codex mission list
```

Important runtime note:

- multiple generated `output/` directories may reuse the same `container_name` values
- do not assume B00/B29 labs can coexist in one Docker namespace
- `run_review_pack.sh` therefore treats runtime preparation as a sequential isolation problem, not a parallel startup problem

---

## Quick Run

```bash
examples/agent-missions/run_task_demo.sh \
  --task TS_B00_BGP_FLAP_ROOTCAUSE \
  --objective "Locate BGP flap root cause and provide fix hints" \
  --attach-output-dir examples/internet/B00_mini_internet/output

# Prefix hijacking (live drill with rollback)
examples/agent-missions/run_task_demo.sh \
  --task TS_B00_PREFIX_HIJACK_LIVE \
  --objective "Run live prefix hijack drill and rollback" \
  --attach-output-dir examples/internet/B00_mini_internet/output \
  --context-json '{"target_prefix":"10.150.0.0/24","attacker_asn":"151"}' \
  --risk on \
  --confirm-token YES_RUN_DYNAMIC_FAULTS
```

Run risky mission with confirmation:

```bash
examples/agent-missions/run_task_demo.sh \
  --task RS_B29_FAULT_IMPACT_ABLATION \
  --objective "Run packet-loss impact ablation with rollback" \
  --attach-output-dir examples/internet/B29_email_dns/output \
  --risk on \
  --confirm-token YES_RUN_DYNAMIC_FAULTS
```

Outputs are written under `/tmp/seed-agent-mission-demo/<task_id>/<timestamp>/`.

`TS_B00_PREFIX_HIJACK_LIVE` executes real runtime changes:

- announces hijack prefix from selected attacker router(s)
- captures before/during/after evidence
- performs explicit rollback and post-check validation

---

## One-command review pack (for presentation)

Run a six-class review bundle from the repo root. If SeedOps and SeedAgent use different bearer tokens, pass them separately:

```bash
examples/agent-missions/run_review_pack.sh \
  --seedops-token "${SEED_MCP_TOKEN}" \
  --seedagent-token "${SEED_AGENT_MCP_TOKEN}"
```

Default output:

- `examples/agent-missions/reports/<timestamp>/review_summary.json`
- `examples/agent-missions/reports/<timestamp>/review_report.md`

The bundle records per-task status, planner mode, selected scope, risky action count, rollback state, verification state, and unresolved backlog.

---

## Evaluation Dimensions

Automated fields:

- attach success
- runtime scale and scale hint
- planner mode and fallback usage
- selected scope
- action count and risky action count
- rollback status
- verification status
- artifact count
- latency
- unresolved issues

Human-review placeholders:

- objective understanding
- environment awareness
- scope choice quality
- evidence-conclusion consistency
- unnecessary action rate

These placeholders are emitted in mission summaries and review-pack outputs so the baseline can be extended into team review, not only CI checks.

---

## Contribution Contract

New runtime-operation skills or tasks should not be merged without:

- one explicit scenario class
- one automated validation path
- one evidence-producing run
- declared side effects and rollback method
