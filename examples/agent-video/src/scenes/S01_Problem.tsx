import React from "react";
import {interpolate, useCurrentFrame, useVideoConfig} from "remotion";
import {pulseOpacity, revealStyle} from "../utils/motion";

export const S01Problem: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const pillars = [
    "教学：可复现的任务闭环与可视化证据",
    "科研：可控实验、可回滚、可对比",
    "工程：跨场景任务包与稳定 API 语义",
  ];

  const metricCards = [
    {label: "Core Positioning", value: "Seed-Agent Core"},
    {label: "Interaction Shell", value: "Codex Optional"},
    {label: "Execution Backbone", value: "SeedOps MCP"},
  ];

  const glow = pulseOpacity({frame, min: 0.2, max: 0.68, cycle: 140});
  const progress = interpolate(frame, [0, fps * 10], [0.15, 0.98], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div style={{width: "100%", height: "100%", padding: "100px 120px"}}>
      <div
        style={{
          position: "absolute",
          left: 90,
          top: 84,
          width: 560,
          height: 560,
          borderRadius: 999,
          background: `radial-gradient(circle, rgba(56,189,248,${glow}) 0%, rgba(2,6,23,0) 70%)`,
          filter: "blur(18px)",
        }}
      />

      <div style={{fontSize: 58, fontWeight: 800, color: "#f8fafc", marginBottom: 26, ...revealStyle({frame, fps, delayFrames: 0})}}>
        平台化目标：从演示走向能力底座
      </div>
      <div style={{fontSize: 31, color: "#cbd5e1", lineHeight: 1.42, ...revealStyle({frame, fps, delayFrames: 10, distance: 34})}}>
        <div>• 不是单点脚本，而是面向整个 SEED Emulator 的统一任务执行层</div>
        <div>• 重点覆盖“已运行网络”的动态维护、实验控制与证据沉淀</div>
        <div>• 支持多轮交互、追问补参、风险确认、自动回滚与复测</div>
      </div>

      <div style={{marginTop: 30, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16}}>
        {metricCards.map((card, index) => (
          <div
            key={card.label}
            style={{
              borderRadius: 16,
              border: "1px solid rgba(125,211,252,0.35)",
              background: "rgba(2,6,23,0.72)",
              padding: "16px 18px",
              ...revealStyle({frame, fps, delayFrames: 18 + index * 8, distance: 24}),
            }}
          >
            <div style={{fontSize: 17, color: "#94a3b8", marginBottom: 8}}>{card.label}</div>
            <div style={{fontSize: 24, color: "#e2e8f0", fontWeight: 700}}>{card.value}</div>
          </div>
        ))}
      </div>

      <div style={{marginTop: 30}}>
        {pillars.map((item, index) => (
          <div
            key={item}
            style={{
              fontSize: 24,
              color: "#e2e8f0",
              lineHeight: 1.5,
              marginBottom: 6,
              ...revealStyle({frame, fps, delayFrames: 38 + index * 8, distance: 20}),
            }}
          >
            {item}
          </div>
        ))}
      </div>

      <div
        style={{
          marginTop: 22,
          fontSize: 24,
          color: "#7dd3fc",
          letterSpacing: 0.3,
          ...revealStyle({frame, fps, delayFrames: 62, distance: 10}),
        }}
      >
        Codex 是壳，Seed-Agent 才是行为核心
      </div>

      <div
        style={{
          position: "absolute",
          left: 120,
          bottom: 110,
          right: 120,
          height: 8,
          borderRadius: 8,
          background: "rgba(30,41,59,0.8)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${Math.round(progress * 100)}%`,
            height: "100%",
            background: "linear-gradient(90deg, rgba(56,189,248,0.85), rgba(167,139,250,0.85))",
          }}
        />
      </div>
    </div>
  );
};
