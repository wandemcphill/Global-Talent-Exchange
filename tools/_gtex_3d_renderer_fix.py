from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_method(text: str, signature: str, replacement: str) -> str:
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f"missing method: {signature}")
    brace = text.find("{", start)
    depth = 0
    end = -1
    for i in range(brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        raise SystemExit(f"unclosed method: {signature}")
    return text[:start] + replacement.rstrip() + text[end:]


def extract_method(text: str, signature: str) -> str:
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f"missing method for validation: {signature}")
    brace = text.find("{", start)
    depth = 0
    end = -1
    for i in range(brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        raise SystemExit(f"unclosed method for validation: {signature}")
    return text[start:end]


def write(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


p = ROOT / "Gtex_Test_Migration/Assets/Code/GTEX/GtexMatchRuntime.cs"
t = p.read_text(encoding="utf-8-sig")
if "filteredPlayerVelocities" not in t:
    t = t.replace(
        "private readonly Dictionary<string, Vector3> filteredPlayerTargets = new();",
        "private readonly Dictionary<string, Vector3> filteredPlayerTargets = new();\n"
        "        private readonly Dictionary<string, Vector3> filteredPlayerVelocities = new();",
        1,
    )
t = replace_method(t, "private float ApplyLivePlayerState(", '''        private float ApplyLivePlayerState(
            PlayerPosition livePlayer,
            GtexLegacyPlayerHandle player,
            float dt,
            float predictionSeconds,
            bool snap,
            bool traceSample,
            bool suppressBoundaryMotion)
        {
            if (livePlayer == null || player == null || !player.IsValid) return 0f;
            var safeDt = Mathf.Max(dt, LiveTraceDtFloorSeconds);
            var current = player.Position;
            var conversion = ConvertIncomingPlaybackPosition(livePlayer, currentState);
            var target = ClampToFieldBounds(conversion.ClampedWorld, false);
            var backendVelocity = snap ? Vector3.zero : ResolveLiveFieldVelocity(livePlayer);
            backendVelocity.y = 0f;
            var delta = target - current; delta.y = 0f;
            var key = livePlayer.playerId ?? string.Empty;
            var velocityRef = filteredPlayerVelocities.TryGetValue(key, out var saved) ? saved : Vector3.zero;
            var maxSpeed = Mathf.Clamp(Mathf.Max(backendVelocity.magnitude * 1.25f, delta.magnitude / safeDt, LivePlayerMinSpeedUnitsPerSecond), LivePlayerMinSpeedUnitsPerSecond, 10.5f);
            Vector3 applied;
            if (snap || !filteredPlayerTargets.ContainsKey(key)) { applied = target; velocityRef = Vector3.zero; }
            else { applied = Vector3.SmoothDamp(current, target, ref velocityRef, 0.10f, maxSpeed, safeDt); }
            applied = ClampToFieldBounds(applied, false);
            var presentationVelocity = (applied - current) / safeDt; presentationVelocity.y = 0f;
            filteredPlayerTargets[key] = target;
            filteredPlayerVelocities[key] = velocityRef;
            var look = presentationVelocity.sqrMagnitude > 0.01f ? presentationVelocity.normalized : (backendVelocity.sqrMagnitude > 0.0001f ? backendVelocity.normalized : player.Forward);
            look.y = 0f;
            var rotation = player.Rotation;
            if (look.sqrMagnitude > 0.0001f) rotation = Quaternion.Slerp(player.Rotation, Quaternion.LookRotation(look, Vector3.up), 1f - Mathf.Exp(-LivePlayerRotationLerpSpeed * safeDt));
            player.SetExternalPlaybackPose(applied, rotation, snap);
            ApplyLiveAnimatorState(livePlayer, player, applied-current, presentationVelocity, safeDt, snap, (livePlayer.state ?? string.Empty).Trim().ToLowerInvariant(), 1f, false);
            return presentationVelocity.magnitude;
        }
''')
t = replace_method(t, "private void TryStartSyntheticBallTransit(", '''        private void TryStartSyntheticBallTransit(MatchResponse previousState, MatchResponse nextState, bool forceSnap)
        {
            ClearSyntheticBallTransit();
        }
''')
t = replace_method(t, "private bool TryDriveSyntheticBallTransit(", '''        private bool TryDriveSyntheticBallTransit()
        {
            return false;
        }
''')
t = replace_method(t, "private void DriveBall(", '''        private void DriveBall()
        {
            if (currentState == null || currentState.ballPosition == null || !GtexMatchController.BallAdapter.IsAvailable)
            {
                ClearSyntheticBallTransit();
                hasFilteredBallTarget = false;
                runtimeTraceBallSpeed = 0f;
                return;
            }
            var target = ClampToFieldBounds(ConvertIncomingPlaybackPosition(currentState.ballPosition, currentState).ClampedWorld, true);
            var velocity = ResolvePlaybackBallVelocity(currentState.ballPosition, false);
            velocity.y = 0f;
            runtimeTraceBallSpeed = velocity.magnitude;
            GtexMatchController.BallAdapter.ApplyExternalState(target, velocity, ResolveBallHolder(currentState.ballPosition));
        }
''')
t = t.replace("/api/v1/ws/match/", "/api/v2/ws/match/", 1)
if "GtexRuntimeState.MarkStarted(GtexRuntimeMode.LivePlayback" not in t and "            matchLoaded = true;\n" in t:
    t = t.replace(
        "            matchLoaded = true;\n",
        "            matchLoaded = true;\n            GtexRuntimeState.MarkStarted(GtexRuntimeMode.LivePlayback, nameof(GtexMatchRuntime));\n",
        1,
    )
write(p, t)

p = ROOT / "Gtex_Test_Migration/Assets/Code/MatchEngine/Players/PlayerBase.cs"
t = p.read_text(encoding="utf-8-sig")
marker = "        public void ProcessBehaviours (in float time) {\n"
guard = marker + '''            if (GtexRuntimeState.ActiveMode == GtexRuntimeMode.LivePlayback)
            {
                ActiveBehaviour = null;
                NextBehaviour = 0;
                return;
            }

'''
if marker not in t:
    raise SystemExit("missing ProcessBehaviours")
section = t[t.find(marker) : t.find(marker) + 900]
if "GtexRuntimeState.ActiveMode == GtexRuntimeMode.LivePlayback" not in section:
    t = t.replace(marker, guard, 1)
write(p, t)

p = ROOT / "Gtex_Test_Migration/Assets/Code/MatchEngine/Players/PlayerController/CodeBasedController.cs"
t = p.read_text(encoding="utf-8-sig")
t = replace_method(t, "public void SetExternalPlaybackPose(", '''        public void SetExternalPlaybackPose(Vector3 position, Quaternion rotation, bool snap = false)
        {
            rotation = Quaternion.Euler(0f, rotation.eulerAngles.y, 0f);
            externalPlaybackTargetPosition = position;
            externalPlaybackTargetRotation = rotation;
            hasExternalPlaybackPose = true;
            if (!externalPlaybackEnabled || rigidbody == null)
            {
                SetInstantPosition(position);
                SetInstantRotation(rotation);
                return;
            }
            GtexPlaybackPhysicsUtil.ApplyExternalPlaybackPosition(transform, rigidbody, position, rotation, snap);
            lastKnownPosition = transform.position;
        }
''')
write(p, t)

p = ROOT / "Gtex_Test_Migration/Assets/Code/MatchEngine/Ball/Ball.cs"
t = p.read_text(encoding="utf-8-sig")
if "private Vector3 externalPlaybackPresentationVelocity;" not in t:
    t = t.replace(
        "        private float nextExternalPlaybackValidationAt;\n",
        "        private float nextExternalPlaybackValidationAt;\n        private Vector3 externalPlaybackPresentationVelocity;\n",
        1,
    )
t = replace_method(t, "private void FixedUpdate()", '''        private void FixedUpdate()
        {
            if (ExternalPlaybackEnabled && GtexRuntimeState.ActiveMode == GtexRuntimeMode.LivePlayback)
            {
                return;
            }
            if (!ExternalPlaybackEnabled || rigidbody == null) return;
            if (HolderPlayer != null) { DriveExternalPlaybackHolderAnchor(); return; }
            if (!hasExternalPlaybackTarget) return;
            var nextPosition = Vector3.MoveTowards(rigidbody.position, externalPlaybackTargetPosition, externalPlaybackMoveSpeed * Time.fixedDeltaTime);
            GtexPlaybackPhysicsUtil.ApplyExternalPlaybackPosition(transform, rigidbody, nextPosition, externalPlaybackTargetRotation);
        }
''')
old = '''            if (!hasExternalPlaybackTarget ||
                Vector3.Distance(rigidbody.position, targetPosition) >= ResolveExternalPlaybackTeleportDistance()) {
                GtexPlaybackPhysicsUtil.ApplyExternalPlaybackPosition(
                    transform,
                    rigidbody,
                    targetPosition,
                    externalPlaybackTargetRotation);
            }

            hasExternalPlaybackTarget = true;'''
new = '''            if (GtexRuntimeState.ActiveMode == GtexRuntimeMode.LivePlayback)
            {
                if (!hasExternalPlaybackTarget)
                {
                    GtexPlaybackPhysicsUtil.ApplyExternalPlaybackPosition(transform, rigidbody, targetPosition, externalPlaybackTargetRotation, true);
                    externalPlaybackPresentationVelocity = Vector3.zero;
                }
                else
                {
                    var maxVisualSpeed = Mathf.Clamp(Mathf.Max(externalPlaybackVelocity.magnitude * 1.35f, 18f), 18f, 28f);
                    var smoothed = Vector3.SmoothDamp(transform.position, targetPosition, ref externalPlaybackPresentationVelocity, 0.055f, maxVisualSpeed, Mathf.Max(Time.unscaledDeltaTime, 1f / 60f));
                    smoothed.y = targetPosition.y;
                    GtexPlaybackPhysicsUtil.ApplyExternalPlaybackPosition(transform, rigidbody, smoothed, externalPlaybackTargetRotation, false);
                }
            }
            else if (!hasExternalPlaybackTarget || Vector3.Distance(rigidbody.position, targetPosition) >= ResolveExternalPlaybackTeleportDistance())
            {
                GtexPlaybackPhysicsUtil.ApplyExternalPlaybackPosition(transform, rigidbody, targetPosition, externalPlaybackTargetRotation);
            }

            hasExternalPlaybackTarget = true;'''
if old not in t:
    raise SystemExit("missing Ball state tail")
t = t.replace(old, new, 1)
write(p, t)

p = ROOT / "Gtex_Test_Migration/Assets/Code/MatchEngine/Camera/CameraSystem.cs"
t = p.read_text(encoding="utf-8-sig")
needle = "                var (position, rotation, zoom) = CurrentCamera.Behave(in dT, targetPos);"
if needle not in t:
    raise SystemExit("missing camera behavior call")
t = t.replace(needle, '''                if (IsBroadcastCamera && Ball.Current != null)
                {
                    ApplyGtexBroadcastCamera(targetPos, dT);
                    return;
                }

                var (position, rotation, zoom) = CurrentCamera.Behave(in dT, targetPos);''', 1)
if "private void ApplyGtexBroadcastCamera(" not in t:
    idx = t.rfind("    }\n}")
    if idx < 0:
        raise SystemExit("camera class end missing")
    helper = '''\n        private void ApplyGtexBroadcastCamera(Vector3 targetPos, float dT)\n        {\n            var ball = Ball.Current;\n            if (ball == null) return;\n            var velocity = ball.Velocity;\n            velocity.y = 0f;\n            var direction = velocity.sqrMagnitude > 0.04f ? velocity.normalized : Vector3.right;\n            var target = targetPos;\n            target.y = 0f;\n            var desiredPosition = new Vector3(target.x - Mathf.Clamp(direction.x * 3.5f, -3.5f, 3.5f), 18f, Mathf.Clamp(target.z - 27f, -46f, 46f));\n            var lookAt = target + Vector3.up * 0.8f;\n            var desiredRotation = Quaternion.LookRotation(lookAt - desiredPosition, Vector3.up);\n            var positionT = 1f - Mathf.Exp(-7.5f * Mathf.Max(dT, 0.001f));\n            var rotationT = 1f - Mathf.Exp(-12f * Mathf.Max(dT, 0.001f));\n            transform.position = Vector3.Lerp(transform.position, desiredPosition, positionT);\n            transform.rotation = Quaternion.Slerp(transform.rotation, desiredRotation, rotationT);\n            var desiredFov = Mathf.Lerp(52f, 47f, Mathf.Clamp01(velocity.magnitude / 12f));\n            camera.fieldOfView = Mathf.Lerp(camera.fieldOfView, desiredFov, Mathf.Clamp01(dT * CameraZoomSpeed));\n        }\n'''
    t = t[:idx] + "    }" + helper + "\n}"
write(p, t)

# Focused source assertions after all edits.
r = (ROOT / "Gtex_Test_Migration/Assets/Code/GTEX/GtexMatchRuntime.cs").read_text(encoding="utf-8-sig")
b = (ROOT / "Gtex_Test_Migration/Assets/Code/MatchEngine/Ball/Ball.cs").read_text(encoding="utf-8-sig")
p = (ROOT / "Gtex_Test_Migration/Assets/Code/MatchEngine/Players/PlayerBase.cs").read_text(encoding="utf-8-sig")
c = (ROOT / "Gtex_Test_Migration/Assets/Code/MatchEngine/Camera/CameraSystem.cs").read_text(encoding="utf-8-sig")
assert "/api/v2/ws/match/" in r
assert "GtexRuntimeState.MarkStarted(GtexRuntimeMode.LivePlayback" in r
assert "TryDriveSyntheticBallTransit()" not in extract_method(r, "private void DriveBall()")
assert "GtexRuntimeState.ActiveMode == GtexRuntimeMode.LivePlayback" in p
assert "Vector3.SmoothDamp" in b
assert "ApplyGtexBroadcastCamera" in c
print("GTEX 3D renderer fix applied and source contract validated")
