import React from "react";
import {interpolate, useCurrentFrame} from "remotion";

type Props = {
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  color?: string;
  cycleFrames?: number;
  strokeWidth?: number;
};

export const FlowArrow: React.FC<Props> = ({
  fromX,
  fromY,
  toX,
  toY,
  color = "#7dd3fc",
  cycleFrames = 90,
  strokeWidth = 4,
}) => {
  const frame = useCurrentFrame();
  const progress = interpolate(frame % cycleFrames, [0, cycleFrames - 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const x = fromX + (toX - fromX) * progress;
  const y = fromY + (toY - fromY) * progress;
  return (
    <>
      <svg
        style={{position: "absolute", left: 0, top: 0, width: "100%", height: "100%"}}
        viewBox="0 0 1920 1080"
      >
        <line x1={fromX} y1={fromY} x2={toX} y2={toY} stroke={color} strokeWidth={strokeWidth} opacity={0.45} />
      </svg>
      <div
        style={{
          position: "absolute",
          left: x - 7,
          top: y - 7,
          width: 14,
          height: 14,
          borderRadius: 14,
          background: color,
          boxShadow: `0 0 24px ${color}`,
        }}
      />
    </>
  );
};
