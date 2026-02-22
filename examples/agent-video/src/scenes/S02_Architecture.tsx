import React from "react";
import {useCurrentFrame, useVideoConfig} from "remotion";
import {FlowArrow} from "../components/FlowArrow";
import {revealStyle} from "../utils/motion";

const layerStyle = (left: number, top: number, title: string, subtitle: string, color: string, motion: React.CSSProperties) => (
  <div
    style={{
      position: "absolute",
      left,
      top,
      width: 360,
      height: 170,
      borderRadius: 16,
      border: `1px solid ${color}`,
      background: "rgba(15, 23, 42, 0.72)",
      padding: "18px 20px",
      ...motion,
    }}
  >
    <div style={{fontSize: 30, color: "#f8fafc", fontWeight: 700}}>{title}</div>
    <div style={{marginTop: 12, fontSize: 22, color: "#cbd5e1", lineHeight: 1.35}}>{subtitle}</div>
  </div>
);

export const S02Architecture: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return (
    <div style={{width: "100%", height: "100%", padding: "70px 90px"}}>
      <div style={{fontSize: 52, color: "#f8fafc", fontWeight: 800, marginBottom: 20, ...revealStyle({frame, fps, delayFrames: 0})}}>
        四层闭环架构（职责分离 + 语义统一）
      </div>

      {layerStyle(
        80,
        210,
        "MCP Server",
        "SeedOps primitives: workspace / playbook / artifacts",
        "#22d3ee",
        revealStyle({frame, fps, delayFrames: 8, distance: 28}),
      )}
      {layerStyle(
        510,
        210,
        "MCP Client",
        "Deterministic wrappers + transport resilience",
        "#38bdf8",
        revealStyle({frame, fps, delayFrames: 16, distance: 28}),
      )}
      {layerStyle(
        940,
        210,
        "Codex Shell",
        "Optional UX shell + operator productivity",
        "#a78bfa",
        revealStyle({frame, fps, delayFrames: 24, distance: 28}),
      )}
      {layerStyle(
        1370,
        210,
        "Seed-Agent Core",
        "Planning / policy / task state machine",
        "#f472b6",
        revealStyle({frame, fps, delayFrames: 32, distance: 28}),
      )}

      <FlowArrow fromX={440} fromY={295} toX={510} toY={295} cycleFrames={86} />
      <FlowArrow fromX={870} fromY={295} toX={940} toY={295} cycleFrames={80} />
      <FlowArrow fromX={1300} fromY={295} toX={1370} toY={295} cycleFrames={74} />

      <div
        style={{
          position: "absolute",
          left: 92,
          top: 470,
          width: 1730,
          borderRadius: 14,
          border: "1px solid rgba(125,211,252,0.34)",
          background: "rgba(2,6,23,0.72)",
          padding: "16px 20px",
          ...revealStyle({frame, fps, delayFrames: 42, distance: 24}),
        }}
      >
        <div style={{fontSize: 24, color: "#7dd3fc", marginBottom: 10}}>Control Plane vs Execution Plane</div>
        <div style={{display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16}}>
          <div style={{fontSize: 21, color: "#e2e8f0", lineHeight: 1.45}}>
            <div>• Control Plane: objective, planning, policy, HITL gate</div>
            <div>• Canonical tools: `seed_agent_task_*`, `seed_agent_run`</div>
          </div>
          <div style={{fontSize: 21, color: "#e2e8f0", lineHeight: 1.45}}>
            <div>• Execution Plane: workspace ops, playbook run, artifact pipeline</div>
            <div>• Fallback path: low-level `seedops_*` remains available</div>
          </div>
        </div>
      </div>

      <div style={{position: "absolute", left: 100, top: 730, fontSize: 24, color: "#e2e8f0", lineHeight: 1.5, ...revealStyle({frame, fps, delayFrames: 54})}}>
        <div>• 统一入口：自然语言、CLI、API 客户端都能接入</div>
        <div>• 统一语义：`ok / needs_input / awaiting_confirmation / blocked / upstream_error`</div>
      </div>
    </div>
  );
};
