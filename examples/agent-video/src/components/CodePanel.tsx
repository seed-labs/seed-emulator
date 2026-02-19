import React from "react";

type Props = {
  title: string;
  lines: string[];
  x: number;
  y: number;
  width: number;
  height?: number;
  style?: React.CSSProperties;
  lineFontSize?: number;
  accentColor?: string;
};

export const CodePanel: React.FC<Props> = ({
  title,
  lines,
  x,
  y,
  width,
  height = 280,
  style,
  lineFontSize = 17,
  accentColor = "#7dd3fc",
}) => {
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width,
        height,
        borderRadius: 14,
        overflow: "hidden",
        border: "1px solid rgba(148, 163, 184, 0.35)",
        background: "rgba(15, 23, 42, 0.78)",
        ...style,
      }}
    >
      <div
        style={{
          height: 44,
          display: "flex",
          alignItems: "center",
          padding: "0 14px",
          fontSize: 18,
          color: "#e2e8f0",
          borderBottom: "1px solid rgba(148, 163, 184, 0.3)",
          fontWeight: 600,
        }}
      >
        <span style={{marginRight: 10, color: accentColor}}>●</span>
        {title}
      </div>
      <pre
        style={{
          margin: 0,
          padding: "12px 14px",
          color: "#cbd5e1",
          fontSize: lineFontSize,
          lineHeight: 1.42,
          fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
          whiteSpace: "pre-wrap",
        }}
      >
        {lines.join("\n")}
      </pre>
    </div>
  );
};
