import React from "react";
import {Composition} from "remotion";
import {SeedPlatform120s} from "./compositions/SeedPlatform90s";

export const Root: React.FC = () => {
  return (
    <Composition
      id="SeedPlatform120s"
      component={SeedPlatform120s}
      width={1920}
      height={1080}
      fps={30}
      durationInFrames={3600}
    />
  );
};
