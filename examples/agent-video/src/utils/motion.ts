import {interpolate, spring} from "remotion";

const clamp = {extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const};

export const revealStyle = ({
  frame,
  fps,
  delayFrames = 0,
  distance = 28,
  scaleFrom = 0.97,
}: {
  frame: number;
  fps: number;
  delayFrames?: number;
  distance?: number;
  scaleFrom?: number;
}) => {
  const progress = spring({
    frame: frame - delayFrames,
    fps,
    config: {damping: 18, stiffness: 120, mass: 0.9},
  });
  return {
    opacity: interpolate(progress, [0, 1], [0, 1], clamp),
    transform: `translateY(${interpolate(progress, [0, 1], [distance, 0], clamp)}px) scale(${interpolate(
      progress,
      [0, 1],
      [scaleFrom, 1],
      clamp,
    )})`,
  };
};

export const pulseOpacity = ({
  frame,
  min = 0.3,
  max = 0.95,
  cycle = 90,
}: {
  frame: number;
  min?: number;
  max?: number;
  cycle?: number;
}) => {
  const phase = (frame % cycle) / cycle;
  const distance = Math.abs(phase - 0.5) * 2;
  return interpolate(distance, [0, 1], [max, min], clamp);
};

export const stageProgress = ({
  frame,
  startFrame,
  endFrame,
}: {
  frame: number;
  startFrame: number;
  endFrame: number;
}) => {
  return interpolate(frame, [startFrame, endFrame], [0, 1], clamp);
};
