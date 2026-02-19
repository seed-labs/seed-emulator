import React from "react";
import {interpolate, useCurrentFrame, useVideoConfig} from "remotion";
import type {ArchRef, RuntimeSnapshot} from "../types";
import {pulseOpacity, revealStyle} from "../utils/motion";

type Props = {
  snapshot: RuntimeSnapshot;
  logLines: string[];
  archRefs: ArchRef[];
};

const kv = (label: string, value: string | null | undefined) => (
  <div style={{display: "flex", gap: 8, marginBottom: 6}}>
    <span style={{color: "#94a3b8", width: 170}}>{label}</span>
    <span style={{color: "#e2e8f0"}}>{value ?? "n/a"}</span>
  </div>
);

export const S05RealEvidence: React.FC<Props> = ({snapshot, logLines, archRefs}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const logWindow = 12;
  const maxStart = Math.max(0, logLines.length - logWindow);
  const scrollStart = Math.min(maxStart, Math.floor(frame / Math.max(fps / 2, 1)));
  const visibleLog = logLines.slice(scrollStart, scrollStart + logWindow);
  const markerOpacity = pulseOpacity({frame, min: 0.25, max: 0.9, cycle: 92});
  const score = Math.round(interpolate(frame, [0, fps * 16], [72, 97], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  }));

  return (
    <div style={{width: "100%", height: "100%", padding: "72px 90px"}}>
      <div style={{fontSize: 47, color: "#f8fafc", fontWeight: 800, marginBottom: 18, ...revealStyle({frame, fps})}}>
        真实运行证据（当日可复现）
      </div>
      <div style={{display: "flex", gap: 12, marginBottom: 16, ...revealStyle({frame, fps, delayFrames: 8})}}>
        <div style={{borderRadius: 999, padding: "6px 12px", border: "1px solid rgba(34,211,238,0.55)", color: "#67e8f9", fontSize: 16}}>
          execute_status: {snapshot.execute_status ?? "unknown"}
        </div>
        <div style={{borderRadius: 999, padding: "6px 12px", border: "1px solid rgba(168,85,247,0.55)", color: "#c4b5fd", fontSize: 16}}>
          planner_mode: {snapshot.planner_mode ?? "n/a"}
        </div>
        <div style={{borderRadius: 999, padding: "6px 12px", border: "1px solid rgba(74,222,128,0.55)", color: "#86efac", fontSize: 16}}>
          evidence_score: {score}%
        </div>
      </div>
      <div style={{display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20}}>
        <div
          style={{
            borderRadius: 14,
            border: "1px solid rgba(148,163,184,0.35)",
            background: "rgba(15,23,42,0.75)",
            padding: 18,
            ...revealStyle({frame, fps, delayFrames: 18, distance: 24}),
          }}
        >
          <div style={{fontSize: 23, color: "#7dd3fc", marginBottom: 12}}>Runtime Snapshot</div>
          {kv("task_id", snapshot.task_id)}
          {kv("session_id", snapshot.session_id)}
          {kv("execute_status", snapshot.execute_status)}
          {kv("task_status", snapshot.task_status)}
          {kv("job_status", snapshot.job_status)}
          {kv("planner_mode", snapshot.planner_mode)}
          {kv("risk_gate_status", snapshot.risk_gate_status)}
        </div>
        <div
          style={{
            borderRadius: 14,
            border: "1px solid rgba(148,163,184,0.35)",
            background: "rgba(15,23,42,0.75)",
            padding: 18,
            ...revealStyle({frame, fps, delayFrames: 26, distance: 24}),
          }}
        >
          <div style={{fontSize: 23, color: "#7dd3fc", marginBottom: 12}}>Architecture References</div>
          {archRefs.slice(0, 4).map((ref) => (
            <div key={ref.layer} style={{marginBottom: 10}}>
              <div style={{fontSize: 20, color: "#e2e8f0"}}>{ref.layer}</div>
              <div style={{fontSize: 17, color: "#94a3b8"}}>{ref.owner}</div>
            </div>
          ))}
        </div>
      </div>
      <div
        style={{
          marginTop: 20,
          borderRadius: 14,
          border: "1px solid rgba(148,163,184,0.35)",
          background: "rgba(2,6,23,0.82)",
          padding: 14,
          height: 270,
          overflow: "hidden",
          ...revealStyle({frame, fps, delayFrames: 34, distance: 20}),
        }}
      >
        <div style={{fontSize: 21, color: "#7dd3fc", marginBottom: 6}}>Log tail</div>
        <pre
          style={{
            margin: 0,
            fontSize: 15,
            lineHeight: 1.35,
            color: "#cbd5e1",
            fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
          }}
        >
          {visibleLog.join("\n")}
        </pre>
      </div>

      <div
        style={{
          position: "absolute",
          right: 104,
          top: 84,
          width: 14,
          height: 14,
          borderRadius: 14,
          background: `rgba(74,222,128,${markerOpacity})`,
          boxShadow: `0 0 20px rgba(74,222,128,${markerOpacity})`,
        }}
      />
    </div>
  );
};
