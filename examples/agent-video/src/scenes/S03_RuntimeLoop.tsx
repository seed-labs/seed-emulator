import React from "react";
import {interpolate, useCurrentFrame, useVideoConfig} from "remotion";
import {CodePanel} from "../components/CodePanel";
import {revealStyle} from "../utils/motion";

export const S03RuntimeLoop: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const stages = [
    "objective",
    "task_begin",
    "task_plan",
    "policy_check",
    "seedops_run",
    "follow_job",
    "artifacts",
  ];
  const stageIndex = Math.min(stages.length - 1, Math.floor(frame / Math.max(fps * 2, 1)));

  return (
    <div style={{width: "100%", height: "100%", padding: "78px 100px"}}>
      <div style={{fontSize: 50, color: "#f8fafc", fontWeight: 800, ...revealStyle({frame, fps, delayFrames: 0})}}>主链路机制（OPS-first）</div>
      <div style={{marginTop: 18, fontSize: 27, color: "#cbd5e1", ...revealStyle({frame, fps, delayFrames: 10})}}>
        请求 → 计划 → 策略校验 → SeedOps 执行 → 工件汇总
      </div>

      <div style={{marginTop: 22, display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 8}}>
        {stages.map((stage, index) => {
          const active = index <= stageIndex;
          return (
            <div
              key={stage}
              style={{
                borderRadius: 10,
                padding: "10px 8px",
                border: `1px solid ${active ? "rgba(125,211,252,0.9)" : "rgba(100,116,139,0.35)"}`,
                background: active ? "rgba(14,116,144,0.32)" : "rgba(15,23,42,0.58)",
                color: active ? "#e0f2fe" : "#94a3b8",
                fontSize: 15,
                textAlign: "center",
                letterSpacing: 0.2,
              }}
            >
              {stage}
            </div>
          );
        })}
      </div>

      <CodePanel
        title="Canonical high-level tools"
        x={100}
        y={290}
        width={860}
        lines={[
          "seed_agent_task_begin(task_id, objective, ...)",
          "seed_agent_task_reply(session_id, answers_json)",
          "seed_agent_task_execute(session_id, approval_token, ...)",
          "seed_agent_task_status(session_id)",
          "",
          "seed_agent_run(...) / seed_agent_plan(...)",
        ]}
        style={revealStyle({frame, fps, delayFrames: 20, distance: 26})}
        lineFontSize={16}
        accentColor="#38bdf8"
      />

      <CodePanel
        title="Response envelope and guarantees"
        x={1000}
        y={290}
        width={820}
        lines={[
          "{",
          '  "api_version": "seed_agent.v2",',
          '  "service_surface": "seed_agent_mcp",',
          '  "status": "ok|needs_input|awaiting_confirmation|blocked|...",',
          '  "session_id": "...", "job_id": "...",',
          '  "canonical_tool": "seed_agent_task_execute"',
          "}",
        ]}
        style={revealStyle({frame, fps, delayFrames: 30, distance: 26})}
        lineFontSize={15}
        accentColor="#a78bfa"
      />

      <div
        style={{
          position: "absolute",
          left: 100,
          right: 100,
          bottom: 90,
          height: 10,
          borderRadius: 10,
          background: "rgba(30,41,59,0.75)",
          overflow: "hidden",
          ...revealStyle({frame, fps, delayFrames: 40, distance: 8}),
        }}
      >
        <div
          style={{
            width: `${Math.round(interpolate(frame, [0, fps * 16], [6, 100], {extrapolateLeft: "clamp", extrapolateRight: "clamp"}))}%`,
            height: "100%",
            background: "linear-gradient(90deg, #22d3ee, #a78bfa)",
          }}
        />
      </div>

      <div style={{position: "absolute", left: 104, bottom: 56, fontSize: 18, color: "#94a3b8"}}>
        deterministic JSON + policy-first orchestration + fallback safety
      </div>
    </div>
  );
};
