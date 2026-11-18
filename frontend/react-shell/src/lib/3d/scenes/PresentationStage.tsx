/**
 * Thin registered renderers. Each kind loads a different environment and camera.
 */

import React, { useState } from "react";
import { QUALITY_PROFILES } from "../GtexSceneRegistry";
import type { GtexSceneRendererProps } from "../GtexSceneTypes";
import { isJsdomEnvironment, useGtexWebGLHost } from "../GtexWebGLHost";
import { createPresentationController, type PresentationKind } from "../sceneKit";

function Stage({
  kind,
  testId,
  props,
}: {
  kind: PresentationKind;
  testId: string;
  props: GtexSceneRendererProps;
}) {
  const [failed, setFailed] = useState(false);
  const clubName = props.clubName || props.subjectName || "GTEX";
  const shot = props.shot || props.sceneProps?.shot;
  const quality = props.activeQuality || QUALITY_PROFILES.high;
  const { mountRef } = useGtexWebGLHost({
    quality,
    enabled: !failed,
    revision: `${kind}|${clubName}|${shot || ""}|${props.crestUrl || ""}|${props.sponsorName || props.subjectLabel || ""}`,
    onUnavailable: (reason) => {
      if (reason === "context") return;
      setFailed(true);
      props.onPresentationFailure?.(reason);
    },
    onContextRestored: () => props.onPresentationRestored?.(),
    createController: () =>
      createPresentationController(kind, {
        clubName,
        primaryColor: props.primaryColor,
        secondaryColor: props.secondaryColor,
        crestUrl: props.crestUrl,
        subjectLabel: props.subjectLabel || props.subjectName,
        sponsorName: props.sponsorName || props.subjectName,
        shot,
      }),
  });

  if (isJsdomEnvironment()) {
    return <div data-testid={testId} data-scene-kind={kind} data-club-name={clubName} data-shot={shot || kind} />;
  }
  if (failed) return null;
  return <div ref={mountRef} data-testid={testId} data-scene-kind={kind} className="h-full min-h-[280px] w-full" />;
}

export function ClubTakeoverScene(props: GtexSceneRendererProps) {
  return <Stage kind="takeover" testId="club-takeover-scene" props={props} />;
}

export function StadiumCampusScene(props: GtexSceneRendererProps) {
  return <Stage kind="campus" testId="stadium-campus-scene" props={props} />;
}

export function TunnelWalkoutScene(props: GtexSceneRendererProps) {
  return <Stage kind="walkout" testId="tunnel-walkout-scene" props={props} />;
}

export function AcademyGroundScene(props: GtexSceneRendererProps) {
  const shot = props.sceneId === "wonderkid_emergence" ? "emergence" : props.sceneId === "build_a_son" ? "bloodline" : props.shot;
  return <Stage kind="academy" testId="academy-ground-scene" props={{ ...props, shot }} />;
}

export function CeremonyScene(props: GtexSceneRendererProps) {
  const kind: PresentationKind = props.sceneId === "world_gala" ? "gala" : "ceremony";
  return <Stage kind={kind} testId="ceremony-scene" props={props} />;
}

export function SponsorshipBowlScene(props: GtexSceneRendererProps) {
  return <Stage kind="sponsorship" testId="sponsorship-bowl-scene" props={props} />;
}
