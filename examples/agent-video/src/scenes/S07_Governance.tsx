import React from "react";
import {useCurrentFrame, useVideoConfig} from "remotion";
import {CodePanel} from "../components/CodePanel";
import {revealStyle} from "../utils/motion";

const governanceRows = [
  "Policy default = read_only，危险动作必须显式升级",
  "LLM plan 非法时自动 template_fallback",
  "全部结果统一 machine-readable JSON envelope",
  "decision_log + artifacts_index 支持审计回放",
];

export const S07Governance: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return (
    <div style={{width: "100%", height: "100%", padding: "84px 100px"}}>
      <div style={{fontSize: 52, fontWeight: 800, color: "#f8fafc", marginBottom: 18, ...revealStyle({frame, fps})}}>
        工程治理与可靠性机制
      </div>
      <div style={{fontSize: 24, color: "#cbd5e1", lineHeight: 1.45, marginBottom: 20, ...revealStyle({frame, fps, delayFrames: 10})}}>
        平台要长期可用，必须保证失败可分流、风险可控、过程可追责。
      </div>

      <div style={{display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18}}>
        <CodePanel
          title="Failure branches"
          x={100}
          y={250}
          width={850}
          height={300}
          lineFontSize={16}
          style={revealStyle({frame, fps, delayFrames: 20, distance: 24})}
          accentColor="#22d3ee"
          lines={[
            "needs_input -> ask targeted questions",
            "blocked -> reject and preserve safety boundary",
            "upstream_error -> provide actionable recovery hints",
            "timeout -> keep trace and allow idempotent retry",
          ]}
        />
        <CodePanel
          title="Operational guarantees"
          x={970}
          y={250}
          width={850}
          height={300}
          lineFontSize={16}
          style={revealStyle({frame, fps, delayFrames: 30, distance: 24})}
          accentColor="#a78bfa"
          lines={[
            "canonical_tool + deprecated_alias_used metadata",
            "service_surface / agent_core identity fields",
            "task_status supports cross-process session restore",
            "seedops_* low-level path kept for debug fallback",
          ]}
        />
      </div>

      <div style={{marginTop: 230}}>
        {governanceRows.map((row, index) => (
          <div
            key={row}
            style={{
              fontSize: 23,
              color: "#e2e8f0",
              lineHeight: 1.52,
              ...revealStyle({frame, fps, delayFrames: 42 + index * 8, distance: 16}),
            }}
          >
            • {row}
          </div>
        ))}
      </div>
    </div>
  );
};
