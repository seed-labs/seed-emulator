import React from "react";
import type {TimelineSegment} from "../types";

type Props = {
  timeSec: number;
  segments: TimelineSegment[];
};

export const CaptionBlock: React.FC<Props> = ({timeSec, segments}) => {
  const active =
    segments.find((item) => timeSec >= item.start_sec && timeSec < item.end_sec) ??
    segments[segments.length - 1];
  if (!active) {
    return null;
  }
  return (
    <div
      style={{
        position: "absolute",
        left: 48,
        right: 48,
        bottom: 26,
        padding: "14px 20px",
        borderRadius: 14,
        background: "rgba(7, 12, 22, 0.78)",
        border: "1px solid rgba(137, 180, 250, 0.35)",
        backdropFilter: "blur(6px)",
      }}
    >
      <div
        style={{
          color: "#f8fafc",
          fontSize: 30,
          fontWeight: 600,
          lineHeight: 1.3,
          marginBottom: 4,
        }}
      >
        {active.zh}
      </div>
      <div
        style={{
          color: "#cbd5e1",
          fontSize: 20,
          lineHeight: 1.35,
        }}
      >
        {active.en}
      </div>
    </div>
  );
};
