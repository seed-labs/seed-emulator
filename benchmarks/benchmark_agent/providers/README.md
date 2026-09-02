<!-- README_SYNC_REQUIRED -->

# Candidate providers

Provider-agnostic candidate-agent access (design principle 12 of the root README).

- `base.py`: the `CandidateProvider` / `ActionProvider` contract. Every provider returns one validated candidate
  action plus provider metadata, so the evaluation loop never depends on the vendor. The action vocabulary itself
  comes from the scenario file, not from this package.
- `openai_compat.py`: generic OpenAI-compatible chat-completions client with strict JSON-schema response format. The
  allowed actions are injected at construction (`allowed_actions`, from the scenario); the client contains no vendor
  specifics and no action names.

Vendor settings (including MIMO) live in `benchmarks/config.json` — switching vendors is a config change, not a code
change. API keys stay out of the file: the config only names the environment variable (`api_key_env`) that carries
the secret. The same config feeds the Inspect AI harness (`inspect_model`).
