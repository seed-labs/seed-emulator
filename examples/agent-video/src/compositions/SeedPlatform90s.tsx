import React from "react";
import {AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame, useVideoConfig} from "remotion";
import {CaptionBlock} from "../components/CaptionBlock";
import {S01Problem} from "../scenes/S01_Problem";
import {S02Architecture} from "../scenes/S02_Architecture";
import {S03RuntimeLoop} from "../scenes/S03_RuntimeLoop";
import {S04HITLPolicy} from "../scenes/S04_HITLPolicy";
import {S05RealEvidence} from "../scenes/S05_RealEvidence";
import {S06MissionMatrix} from "../scenes/S06_Takeaway";
import {S07Governance} from "../scenes/S07_Governance";
import {S08Roadmap} from "../scenes/S08_Roadmap";
import timeline from "../../assets/subtitles/timeline.json";
import snapshot from "../../assets/evidence/runtime_snapshot.json";
import logTail from "../../assets/evidence/log_tail.json";
import archRefs from "../../assets/evidence/arch_refs.json";
import type {ArchRef, RuntimeSnapshot, TimelineSegment} from "../types";

const sceneDurations = [360, 510, 540, 480, 600, 480, 360, 270];
const timelineSegments = (timeline as {segments: TimelineSegment[]}).segments ?? [];
const runtimeSnapshot = snapshot as RuntimeSnapshot;
const runtimeLogLines = ((logTail as {lines: string[]}).lines ?? []).slice(-22);
const architectureRefs = ((archRefs as {layers: ArchRef[]}).layers ?? []).slice(0, 6);

export const SeedPlatform120s: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const second = frame / fps;

  let cursor = 0;
  const offsets = sceneDurations.map((value) => {
    const current = cursor;
    cursor += value;
    return current;
  });

  return (
    <AbsoluteFill style={{backgroundColor: "#020617", fontFamily: "Inter, PingFang SC, Segoe UI, sans-serif"}}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(circle at 12% 18%, rgba(59,130,246,0.24), transparent 38%), radial-gradient(circle at 84% 20%, rgba(168,85,247,0.18), transparent 34%), radial-gradient(circle at 50% 82%, rgba(34,211,238,0.14), transparent 42%)",
        }}
      />
      <Audio src={staticFile("voiceover.wav")} volume={0.95} />

      <Sequence from={offsets[0]} durationInFrames={sceneDurations[0]}>
        <S01Problem />
      </Sequence>
      <Sequence from={offsets[1]} durationInFrames={sceneDurations[1]}>
        <S02Architecture />
      </Sequence>
      <Sequence from={offsets[2]} durationInFrames={sceneDurations[2]}>
        <S03RuntimeLoop />
      </Sequence>
      <Sequence from={offsets[3]} durationInFrames={sceneDurations[3]}>
        <S04HITLPolicy />
      </Sequence>
      <Sequence from={offsets[4]} durationInFrames={sceneDurations[4]}>
        <S05RealEvidence snapshot={runtimeSnapshot} logLines={runtimeLogLines} archRefs={architectureRefs} />
      </Sequence>
      <Sequence from={offsets[5]} durationInFrames={sceneDurations[5]}>
        <S06MissionMatrix />
      </Sequence>
      <Sequence from={offsets[6]} durationInFrames={sceneDurations[6]}>
        <S07Governance />
      </Sequence>
      <Sequence from={offsets[7]} durationInFrames={sceneDurations[7]}>
        <S08Roadmap />
      </Sequence>

      <CaptionBlock timeSec={second} segments={timelineSegments} />
    </AbsoluteFill>
  );
};

export const SeedPlatform90s = SeedPlatform120s;
