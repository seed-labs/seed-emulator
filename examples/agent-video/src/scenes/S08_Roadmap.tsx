import React from "react";
import {interpolate, useCurrentFrame, useVideoConfig} from "remotion";
import {revealStyle} from "../utils/motion";

const milestones = [
  "M1：任务引擎骨架 + MCP 任务接口稳定化",
  "M2：跨安全/排障/科研任务包批量接入",
  "M3：真实网络回归 + 报告模板固化",
  "M4：平台叙事发布，服务教学/科研/工程三类用户",
];

export const S08Roadmap: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const barWidth = interpolate(frame, [0, fps * 8], [0.08, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div style={{width: "100%", height: "100%", padding: "110px 120px"}}>
      <div style={{fontSize: 60, color: "#f8fafc", fontWeight: 800, marginBottom: 20, ...revealStyle({frame, fps})}}>
        平台化结论（120s 总结）
      </div>
      <div style={{fontSize: 30, color: "#cbd5e1", lineHeight: 1.45, marginBottom: 24, ...revealStyle({frame, fps, delayFrames: 10})}}>
        Codex 可替换，Seed-Agent 不可替换；MCP 是接口标准，任务引擎是能力核心。
      </div>

      {milestones.map((item, index) => (
        <div
          key={item}
          style={{
            fontSize: 24,
            color: "#e2e8f0",
            lineHeight: 1.5,
            marginBottom: 10,
            ...revealStyle({frame, fps, delayFrames: 20 + index * 8, distance: 14}),
          }}
        >
          {item}
        </div>
      ))}

      <div
        style={{
          marginTop: 34,
          height: 12,
          borderRadius: 12,
          background: "rgba(30,41,59,0.76)",
          overflow: "hidden",
          ...revealStyle({frame, fps, delayFrames: 52, distance: 8}),
        }}
      >
        <div
          style={{
            width: `${Math.round(barWidth * 100)}%`,
            height: "100%",
            background: "linear-gradient(90deg, #22d3ee, #38bdf8, #a78bfa, #f472b6)",
          }}
        />
      </div>

      <div style={{marginTop: 18, fontSize: 26, color: "#7dd3fc", ...revealStyle({frame, fps, delayFrames: 58, distance: 10})}}>
        MCP + Seed-Agent = 面向 SEED 全生态的长期智能体能力总线
      </div>
    </div>
  );
};
