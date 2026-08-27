from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def replace_method(text: str, pattern: str, replacement: str) -> str:
    m = re.search(pattern, text, re.MULTILINE)
    if not m:
        raise SystemExit(f"method not found: {pattern}")
    start = m.start()
    brace = text.find("{", m.end())
    if brace < 0:
        raise SystemExit(f"opening brace not found: {pattern}")
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[:start] + replacement.rstrip() + text[i + 1:]
    raise SystemExit(f"closing brace not found: {pattern}")

runtime_path = ROOT / "Gtex_Test_Migration/Assets/Code/GTEX/GtexMatchRuntime.cs"
runtime = runtime_path.read_text(encoding="utf-8-sig")
runtime = runtime.replace(
    "            matchLoaded = true;\n",
    "            matchLoaded = true;\n            GtexRuntimeState.MarkStarted(GtexRuntimeMode.LivePlayback, nameof(GtexMatchRuntime));\n",
    1,
)
runtime = runtime.replace(
    'return normalized + "/api/v1/ws/match/" + Uri.EscapeDataString(matchId) + "?format=unity";',
    'return normalized + "/api/v2/ws/match/" + Uri.EscapeDataString(matchId) + "?format=unity";',
    1,
)
runtime = replace_method(runtime, r"\s*private float ApplyLivePlayerState\(", '''        private float ApplyLivePlayerState(
            PlayerPosition livePlayer,
            GtexLegacyPlayerHandle player,
            float dt,
            float predictionSeconds,
            bool snap,
            bool traceSample,
            bool suppressBoundaryMotion)
        {
            if (livePlayer == null || player == null || !player.IsValid)
            {
                return 0f;
            }

            var currentPosition = player.Position;
            var directIncomingPosition = ConvertIncomingPlaybackPosition(livePlayer, currentState);
            var liveVelocity = snap ? Vector3.zero : ResolveLiveFieldVelocity(livePlayer);
            liveVelocity.y = 0f;
            var targetPosition = snap
                ? directIncomingPosition.ClampedWorld
                : ResolvePredictedFieldPosition(livePlayer, predictionSeconds);

            if (suppressBoundaryMotion)
            {
                targetPosition = directIncomingPosition.ClampedWorld;
            }
            targetPosition = ClampToFieldBounds(targetPosition, false);

            var targetDelta = targetPosition - currentPosition;
            targetDelta.y = 0f;
            var targetDistance = targetDelta.magnitude;
            var hardSnap = snap || targetDistance >= ResolveHardSnapDistance(suppressBoundaryMotion);
            var desiredLookDirection = ResolveLookDirection(livePlayer, targetDelta, player);

            var appliedPosition = targetPosition;
            if (!hardSnap)
            {
                var presentationSpeed = Mathf.Max(
                    liveVelocity.magnitude,
                    Mathf.Min(
                        LivePlayerMaxSpeedUnitsPerSecond,
                        targetDistance / Mathf.Max(LivePlayerCatchUpSeconds, 0.05f)));
                appliedPosition = Vector3.MoveTowards(
                    currentPosition,
                    targetPosition,
                    presentationSpeed * Mathf.Max(dt, 0f));
            }
            appliedPosition = ClampToFieldBounds(appliedPosition, false);

            var appliedRotation = player.Rotation;
            if (desiredLookDirection.sqrMagnitude > 0.0001f)
            {
                var desiredRotation = Quaternion.LookRotation(desiredLookDirection.normalized, Vector3.up);
                appliedRotation = hardSnap
                    ? desiredRotation
                    : Quaternion.Slerp(
                        player.Rotation,
                        desiredRotation,
                        Mathf.Clamp01(dt * LivePlayerRotationLerpSpeed));
            }

            if (traceSample)
            {
                AppendRuntimeTrace(
                    "pitch-sample",
                    "player=" + DescribeLivePlayer(livePlayer) +
                    " raw=" + FormatPlaybackVector(directIncomingPosition.RawIncoming) +
                    " converted=" + FormatPlaybackVector(directIncomingPosition.ConvertedWorld) +
                    " clamped=" + FormatPlaybackVector(directIncomingPosition.ClampedWorld));
            }

            player.SetExternalPlaybackPose(appliedPosition, appliedRotation, hardSnap);
            ApplyLiveAnimatorState(
                livePlayer,
                player,
                appliedPosition - currentPosition,
                liveVelocity,
                dt,
                hardSnap,
                (livePlayer.state ?? string.Empty).Trim().ToLowerInvariant(),
                1f,
                false);

            if (hardSnap || dt <= 0f)
            {
                return 0f;
            }

            var frameMovement = appliedPosition - currentPosition;
            frameMovement.y = 0f;
            return frameMovement.magnitude / Mathf.Max(dt, LiveTraceDtFloorSeconds);
        }
''')
runtime = replace_method(runtime, r"\s*private void TryStartSyntheticBallTransit\(", '''        private void TryStartSyntheticBallTransit(MatchResponse previousState, MatchResponse nextState, bool forceSnap)
        {
            ClearSyntheticBallTransit();
        }
''')
runtime = replace_method(runtime, r"\s*private bool TryDriveSyntheticBallTransit\(", '''        private bool TryDriveSyntheticBallTransit()
        {
            return false;
        }
''')
runtime = replace_method(runtime, r"\s*private void DriveBall\(", '''        private void DriveBall()
        {
            if (currentState == null ||
                currentState.ballPosition == null ||
                !GtexMatchController.BallAdapter.IsAvailable)
            {
                ClearSyntheticBallTransit();
                hasFilteredBallTarget = false;
                runtimeTraceBallSpeed = 0f;
                return;
            }

            var ballHolder = ResolveBallHolder(currentState.ballPosition);
            var ballConversion = ConvertIncomingPlaybackPosition(currentState.ballPosition, currentState);
            var suppressBoundaryMotion = ShouldSuppressBoundaryMotion(currentState);
            var authoritativeTarget = ballHolder != null || suppressBoundaryMotion
                ? ballConversion.ClampedWorld
                : ResolvePredictedFieldPosition(currentState.ballPosition, ResolveLivePredictionSeconds());
            var ballVelocity = ResolvePlaybackBallVelocity(currentState.ballPosition, suppressBoundaryMotion);
            authoritativeTarget = ClampToFieldBounds(authoritativeTarget, true);

            if (Time.unscaledTime - runtimeTraceLastBallSampleAt >= PlaybackTraceSampleIntervalSeconds)
            {
                runtimeTraceLastBallSampleAt = Time.unscaledTime;
                TraceBallPitchSample(ballConversion, authoritativeTarget, ballHolder);
            }

            GtexMatchController.BallAdapter.ApplyExternalState(
                authoritativeTarget,
                ballVelocity,
                ballHolder);
        }
''')
runtime_path.write_text(runtime + "\n", encoding="utf-8")

player_path = ROOT / "Gtex_Test_Migration/Assets/Code/MatchEngine/Players/PlayerBase.cs"
player = player_path.read_text(encoding="utf-8-sig")
marker = "        public void ProcessBehaviours (in float time) {\n"
guard = """        public void ProcessBehaviours (in float time) {
            if (GtexRuntimeState.ActiveMode == GtexRuntimeMode.LivePlayback)
            {
                ActiveBehaviour = null;
                NextBehaviour = 0;
                return;
            }
"""
if marker not in player:
    raise SystemExit("PlayerBase ProcessBehaviours marker not found")
if guard not in player:
    player = player.replace(marker, guard, 1)
player_path.write_text(player + "\n", encoding="utf-8")

physics_path = ROOT / "Gtex_Test_Migration/Assets/Code/GTEX/Engine/GtexPlaybackPhysicsUtil.cs"
physics = physics_path.read_text(encoding="utf-8-sig")
physics = replace_method(physics, r"\s*public static void ApplyExternalPlaybackPosition\(", '''        public static void ApplyExternalPlaybackPosition(
            Transform target,
            Rigidbody rb,
            Vector3 nextPosition,
            Quaternion nextRotation,
            bool snap = false)
        {
            if (target == null)
            {
                return;
            }

            if (rb != null)
            {
                rb.position = nextPosition;
                rb.rotation = nextRotation;
            }
            target.SetPositionAndRotation(nextPosition, nextRotation);
        }
''')
physics_path.write_text(physics + "\n", encoding="utf-8")

ball_path = ROOT / "Gtex_Test_Migration/Assets/Code/MatchEngine/Ball/Ball.cs"
ball = ball_path.read_text(encoding="utf-8-sig")
ball = replace_method(ball, r"\s*private void FixedUpdate\(\)", '''        private void FixedUpdate()
        {
            if (ExternalPlaybackEnabled)
            {
                return;
            }
        }
''')
ball, changed = re.subn(
    r"\s*if \(!hasExternalPlaybackTarget\s*\|\|\s*Vector3\.Distance\(rigidbody\.position, targetPosition\)\s*>=\s*ResolveExternalPlaybackTeleportDistance\(\)\)\s*\{\s*GtexPlaybackPhysicsUtil\.ApplyExternalPlaybackPosition\(\s*transform,\s*rigidbody,\s*targetPosition,\s*externalPlaybackTargetRotation\);\s*\}",
    """\n            GtexPlaybackPhysicsUtil.ApplyExternalPlaybackPosition(
                transform,
                rigidbody,
                targetPosition,
                externalPlaybackTargetRotation);""",
    ball,
    count=1,
)
if changed != 1:
    raise SystemExit(f"Ball external target gate replacement count={changed}")
ball = re.sub(
    r"\s*if \(holderChanged\s*\|\|\s*Vector3\.Distance\(rigidbody\.position, ResolveExternalPlaybackHolderAnchor\(holder\)\)\s*>=\s*ResolveExternalPlaybackHolderSnapDistance\(\) \* 1\.75f\)\s*\{\s*SnapExternalPlaybackHolderAnchor\(holder\);\s*\}",
    """\n                var holderAnchor = ResolveExternalPlaybackHolderAnchor(holder);
                transform.position = holderAnchor;
                if (rigidbody != null)
                {
                    rigidbody.position = holderAnchor;
                }""",
    ball,
    count=1,
)
ball_path.write_text(ball + "\n", encoding="utf-8")

# Disable autonomous goalkeeper updates during LivePlayback.
gk_path = ROOT / "Gtex_Test_Migration/Assets/Code/GTEX/Engine/GtexGoalkeeperBehavior.cs"
if gk_path.exists():
    gk = gk_path.read_text(encoding="utf-8-sig")
    if "using FStudio.GTEX.Core;" not in gk and "using FStudio.GTEX;" in gk:
        gk = gk.replace("using FStudio.GTEX;\n", "using FStudio.GTEX;\nusing FStudio.GTEX.Core;\n", 1)
    gk = gk.replace(
        "        private void LateUpdate()\n        {\n            if (GtexRuntimeFlags.IsOriginalVisualRuntime)\n            {",
        "        private void LateUpdate()\n        {\n            if (GtexRuntimeState.ActiveMode == GtexRuntimeMode.LivePlayback ||\n                GtexRuntimeFlags.IsOriginalVisualRuntime)\n            {",
        1,
    )
    gk_path.write_text(gk + "\n", encoding="utf-8")

# The previous guard was an unconnected second playback system. Remove it.
guard_path = ROOT / "Gtex_Test_Migration/Assets/Code/GTEX/Authoritative/GtexAuthoritativePlaybackGuard.cs"
if guard_path.exists():
    guard_path.unlink()

# Source gates.
r = runtime_path.read_text(encoding="utf-8")
m = re.search(r"private float ApplyLivePlayerState\([\s\S]*?\n        }\n\s*private Vector3 ResolveBehaviorAnchorPosition", r)
if not m:
    raise SystemExit("ApplyLivePlayerState boundary missing")
body = m.group(0)
for token in (
    "ResolveBehaviorAnchorPosition",
    "ResolveBehaviorDrivenFieldPosition",
    "ApplyStructuredTeamSpacing",
    "FilterLivePlayerTarget",
    "ResolveLiveMovementUrgency",
    "ResolveLivePlayerMoveSpeed",
    "ResolveLegalPlayerVelocity",
):
    if token in body:
        raise SystemExit("forbidden live-player decision token remains: " + token)
if "/api/v2/ws/match/" not in r:
    raise SystemExit("v2 WebSocket endpoint missing")
if "GtexRuntimeState.MarkStarted(GtexRuntimeMode.LivePlayback" not in r:
    raise SystemExit("LivePlayback state marker missing")
if "return false;" not in re.search(r"private bool TryDriveSyntheticBallTransit\([\s\S]*?\n        }", r).group(0):
    raise SystemExit("synthetic ball transit is still active")
if "rb.MovePosition(nextPosition)" in physics_path.read_text(encoding="utf-8"):
    raise SystemExit("Rigidbody MovePosition remains in playback helper")
b = ball_path.read_text(encoding="utf-8")
if "ResolveExternalPlaybackTeleportDistance()" in b:
    raise SystemExit("ball teleport gate remains")
if "GtexRuntimeState.ActiveMode == GtexRuntimeMode.LivePlayback" not in player_path.read_text(encoding="utf-8"):
    raise SystemExit("PlayerBase LivePlayback guard missing")
print("GTEX authoritative playback finalizer passed")
