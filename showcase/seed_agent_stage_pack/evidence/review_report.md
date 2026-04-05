# Seed Agent Six-Class Review Pack

- Generated at (UTC): 2026-03-18T09:04:30.680820+00:00
- Run dir: `/home/parallels/seed-email-service/examples/agent-missions/reports/20260318T085945Z`
- Overall: `passed`

## Class Summary
- Diagnosis / Maintenance: passed 1/1, failed 0
- Disturbance Recovery: passed 1/1, failed 0
- Research Experiments: passed 1/1, failed 0
- Routing Security: passed 1/1, failed 0
- Security Offense-Defense: passed 1/1, failed 0
- Service Reachability: passed 1/1, failed 0

## Task Summary
- `RS_B00_CONVERGENCE_COMPARISON` (Research Experiments):
  start=ok execute=ok approved=None status=ok
  planner=template_fallback scale=large attach=True actions=2 risky_actions=0 verification=verified rollback=not_required
  unresolved: planner_fallback / improve planner grounding, runtime context, or task-specific fallback templates
  manual_review: objective_understanding=?, environment_awareness=?, scope_choice_quality=?, evidence_conclusion_consistency=?, unnecessary_action_rate=?
- `RS_B29_FAULT_IMPACT_ABLATION` (Disturbance Recovery):
  start=awaiting_confirmation execute=awaiting_confirmation approved=ok status=ok
  planner=template_fallback scale=large attach=True actions=12 risky_actions=2 verification=verified rollback=verified
  unresolved: planner_fallback / improve planner grounding, runtime context, or task-specific fallback templates
  manual_review: objective_understanding=?, environment_awareness=?, scope_choice_quality=?, evidence_conclusion_consistency=?, unnecessary_action_rate=?
- `SEC_B29_DNS_MAIL_ABUSE_RESPONSE` (Security Offense-Defense):
  start=awaiting_confirmation execute=awaiting_confirmation approved=ok status=ok
  planner=template_fallback scale=large attach=True actions=6 risky_actions=1 verification=verified rollback=not_required
  unresolved: planner_fallback / improve planner grounding, runtime context, or task-specific fallback templates
  manual_review: objective_understanding=?, environment_awareness=?, scope_choice_quality=?, evidence_conclusion_consistency=?, unnecessary_action_rate=?
- `TS_B00_BGP_FLAP_ROOTCAUSE` (Diagnosis / Maintenance):
  start=awaiting_confirmation execute=awaiting_confirmation approved=ok status=ok
  planner=template_fallback scale=large attach=True actions=3 risky_actions=0 verification=verified rollback=not_required
  unresolved: planner_fallback / improve planner grounding, runtime context, or task-specific fallback templates
  manual_review: objective_understanding=?, environment_awareness=?, scope_choice_quality=?, evidence_conclusion_consistency=?, unnecessary_action_rate=?
- `TS_B00_PREFIX_HIJACK_LIVE` (Routing Security):
  start=awaiting_confirmation execute=awaiting_confirmation approved=ok status=ok
  planner=template_fallback scale=large attach=True actions=10 risky_actions=2 verification=verified rollback=verified
  unresolved: planner_fallback / improve planner grounding, runtime context, or task-specific fallback templates
  manual_review: objective_understanding=?, environment_awareness=?, scope_choice_quality=?, evidence_conclusion_consistency=?, unnecessary_action_rate=?
- `TS_B29_MAIL_REACHABILITY_DEBUG` (Service Reachability):
  start=awaiting_confirmation execute=awaiting_confirmation approved=ok status=ok
  planner=template_fallback scale=large attach=True actions=6 risky_actions=2 verification=verified rollback=not_required
  unresolved: planner_fallback / improve planner grounding, runtime context, or task-specific fallback templates
  manual_review: objective_understanding=?, environment_awareness=?, scope_choice_quality=?, evidence_conclusion_consistency=?, unnecessary_action_rate=?
