import React from "react";
import {useCurrentFrame, useVideoConfig} from "remotion";
import {CodePanel} from "../components/CodePanel";
import {FlowArrow} from "../components/FlowArrow";
import {revealStyle, stageProgress} from "../utils/motion";

export const S04HITLPolicy: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const progress = stageProgress({frame, startFrame: 0, endFrame: fps * 15});

  const nodes = [
    {label: "BEGIN", x: 160, y: 280, color: "#38bdf8"},
    {label: "needs_input", x: 420, y: 280, color: "#22d3ee"},
    {label: "awaiting_confirmation", x: 760, y: 280, color: "#fbbf24"},
    {label: "executing", x: 1170, y: 280, color: "#a78bfa"},
    {label: "done/error", x: 1500, y: 280, color: "#f472b6"},
  ];

  return (
    <div style={{width: "100%", height: "100%", padding: "82px 100px"}}>
      <div style={{fontSize: 48, color: "#f8fafc", fontWeight: 800, ...revealStyle({frame, fps})}}>HITL 风险门与可审计策略</div>
      <div style={{marginTop: 18, fontSize: 26, color: "#cbd5e1", lineHeight: 1.4, ...revealStyle({frame, fps, delayFrames: 12})}}>
        缺参、风险动作、目标冲突都会触发受控交互，而不是盲目执行。
      </div>

      {nodes.map((node, index) => (
        <div
          key={node.label}
          style={{
            position: "absolute",
            left: node.x,
            top: node.y,
            minWidth: 170,
            padding: "10px 14px",
            textAlign: "center",
            borderRadius: 12,
            border: `1px solid ${node.color}`,
            background: "rgba(2,6,23,0.76)",
            color: "#e2e8f0",
            fontSize: 18,
            ...revealStyle({frame, fps, delayFrames: 18 + index * 8, distance: 18}),
          }}
        >
          {node.label}
        </div>
      ))}

      <FlowArrow fromX={330} fromY={301} toX={420} toY={301} cycleFrames={110} />
      <FlowArrow fromX={610} fromY={301} toX={760} toY={301} cycleFrames={96} />
      <FlowArrow fromX={980} fromY={301} toX={1170} toY={301} cycleFrames={88} />
      <FlowArrow fromX={1365} fromY={301} toX={1500} toY={301} cycleFrames={78} />

      <CodePanel
        title="Gate statuses"
        x={100}
        y={410}
        width={840}
        lines={[
          "needs_input: required_inputs 未满足，返回问题清单",
          "awaiting_confirmation: 跨 read_only 阶段前必须确认",
          "blocked: 当前 policy_profile 禁止该动作",
          "upstream_error: SeedOps / transport 不可达",
        ]}
        style={revealStyle({frame, fps, delayFrames: 42, distance: 20})}
        lineFontSize={16}
        accentColor="#22d3ee"
      />

      <CodePanel
        title="Risk confirmation + audit trail"
        x={980}
        y={410}
        width={840}
        lines={[
          "task_execute(session_id) -> awaiting_confirmation",
          "approval_token=YES_RUN_DYNAMIC_FAULTS",
          "task_execute(..., approval_token)",
          "-> run experiment + rollback + verify",
          "decision_log.json / artifacts_index.json persisted",
        ]}
        style={revealStyle({frame, fps, delayFrames: 50, distance: 20})}
        lineFontSize={16}
        accentColor="#fbbf24"
      />

      <div
        style={{
          position: "absolute",
          left: 102,
          right: 102,
          bottom: 80,
          height: 8,
          borderRadius: 8,
          background: "rgba(30,41,59,0.8)",
          overflow: "hidden",
          ...revealStyle({frame, fps, delayFrames: 60, distance: 10}),
        }}
      >
        <div
          style={{
            width: `${Math.round(progress * 100)}%`,
            height: "100%",
            background: "linear-gradient(90deg, rgba(56,189,248,0.9), rgba(244,114,182,0.9))",
          }}
        />
      </div>

      <div style={{position: "absolute", left: 106, bottom: 50, color: "#94a3b8", fontSize: 18}}>
        policy-first, human-in-the-loop, and fully auditable execution
      </div>
    </div>
  );
};
