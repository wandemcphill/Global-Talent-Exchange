import React from "react";
import type { GtexSceneRendererProps } from "../GtexSceneTypes";
import { PrestigeShowroomScene } from "./PrestigeShowroomScene";

/** Routes luxury and jet presentations at the existing GLB inspector. */
export function LuxuryTurntableScene(props: GtexSceneRendererProps) {
  const jet = props.sceneId === "private_jet_flex";
  const archetype =
    props.meshArchetype ||
    props.sceneProps?.meshArchetype ||
    (jet ? "private_jet" : undefined);
  return (
    <PrestigeShowroomScene
      {...props}
      meshArchetype={archetype}
      assetName={props.assetName || props.subjectName || (jet ? "Sovereign 900X" : props.title)}
      assetCategory={props.assetCategory || (jet ? "jet" : undefined)}
      clubName={props.clubName}
      primaryColor={props.primaryColor}
      secondaryColor={props.secondaryColor}
    />
  );
}
