import React from "react";
import {useCurrentFrame, useVideoConfig} from "remotion";
import {revealStyle} from "../utils/motion";

const rows = [
  {track: "security", mission: "SEC_B29_SOCIAL_ENGINEERING_TRIAGE", outcome: "异常归因 + 处置建议"},
  {track: "security", mission: "SEC_B29_DNS_MAIL_ABUSE_RESPONSE", outcome: "DNS/邮件链路证据化"},
  {track: "troubleshooting", mission: "TS_B00_BGP_FLAP_ROOTCAUSE", outcome: "抖动根因 + 修复验证"},
  {track: "troubleshooting", mission: "TS_B29_MAIL_REACHABILITY_DEBUG", outcome: "多跳定位 + 恢复确认"},
  {track: "research", mission: "RS_B00_CONVERGENCE_COMPARISON", outcome: "策略前后收敛指标"},
  {track: "research", mission: "RS_B29_FAULT_IMPACT_ABLATION", outcome: "注入-回滚-复测评估"},
];

export const S06MissionMatrix: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return (
    <div style={{width: "100%", height: "100%", padding: "82px 100px"}}>
      <div style={{fontSize: 54, fontWeight: 800, color: "#f8fafc", marginBottom: 18, ...revealStyle({frame, fps})}}>
        任务包复用矩阵（跨场景同引擎）
      </div>
      <div style={{fontSize: 24, color: "#cbd5e1", lineHeight: 1.45, marginBottom: 18, ...revealStyle({frame, fps, delayFrames: 8})}}>
        新增任务优先通过 YAML + 模板扩展，不改核心状态机与协议层。
      </div>

      <div style={{borderRadius: 14, border: "1px solid rgba(148,163,184,0.35)", overflow: "hidden", ...revealStyle({frame, fps, delayFrames: 14, distance: 20})}}>
        <div style={{display: "grid", gridTemplateColumns: "220px 1fr 340px", background: "rgba(15,23,42,0.88)", padding: "12px 16px"}}>
          <div style={{color: "#7dd3fc", fontSize: 18}}>track</div>
          <div style={{color: "#7dd3fc", fontSize: 18}}>task_id</div>
          <div style={{color: "#7dd3fc", fontSize: 18}}>expected outcome</div>
        </div>
        {rows.map((row, index) => (
          <div
            key={row.mission}
            style={{
              display: "grid",
              gridTemplateColumns: "220px 1fr 340px",
              padding: "12px 16px",
              borderTop: "1px solid rgba(51,65,85,0.7)",
              background: index % 2 === 0 ? "rgba(2,6,23,0.75)" : "rgba(15,23,42,0.75)",
              ...revealStyle({frame, fps, delayFrames: 22 + index * 6, distance: 18}),
            }}
          >
            <div style={{color: "#c4b5fd", fontSize: 18, textTransform: "uppercase"}}>{row.track}</div>
            <div style={{color: "#e2e8f0", fontSize: 17, fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"}}>
              {row.mission}
            </div>
            <div style={{color: "#cbd5e1", fontSize: 17}}>{row.outcome}</div>
          </div>
        ))}
      </div>

      <div style={{marginTop: 20, fontSize: 23, color: "#7dd3fc", ...revealStyle({frame, fps, delayFrames: 62, distance: 14})}}>
        统一状态机：BEGIN → needs_input* → awaiting_confirmation? → executing → done/error
      </div>
    </div>
  );
};

export const S06Takeaway = S06MissionMatrix;
