from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def replace_method(text: str, signature_pattern: str, replacement: str) -> str:
    match = re.search(signature_pattern, text, re.MULTILINE)
    if not match:
        raise SystemExit(f"method not found: {signature_pattern}")
    start = match.start()
    brace = text.find('{', match.end())
    if brace < 0:
        raise SystemExit(f"opening brace not found: {signature_pattern}")
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == '{':
            depth += 1
        elif text[index] == '}':
            depth -= 1
            if depth == 0:
                return text[:start] + replacement.rstrip() + text[index + 1:]
    raise SystemExit(f"closing brace not found: {signature_pattern}")


runtime_path = ROOT / 'Gtex_Test_Migration/Assets/Code/GTEX/GtexMatchRuntime.cs'
runtime = runtime_path.read_text(encoding='utf-8-sig')
runtime = runtime.replace(
    '            config = cfg;\n',
    '            config = cfg;\n            GtexRuntimeState.MarkStarted(GtexRuntimeMode.LivePlayback, nameof(GtexMatchRuntime));\n',
    1,
)
runtime = runtime.replace(
    'return normalized + "/api/v1/ws/match/" + Uri.EscapeDataString(matchId) + "?format=unity";',
    'return normalized + "/api/v2/ws/match/" + Uri.EscapeDataString(matchId) + "?format=unity";',
    1,
)
runtime = replace_method(
    runtime,
    r'\s*private float ApplyLivePlayerState\(',
    '''        private float ApplyLivePlayerState(
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

            var startPosition = player.Position;
            var directIncoming = ConvertIncomingPlaybackPosition(livePlayer, currentState);
            var liveVelocity = snap ? Vector3.zero : ResolveLiveFieldVelocity(livePlayer);
            liveVelocity.y = 0f;

            // LivePlayback presents the backend's authoritative movement. The
            // renderer may interpolate and orient the actor, but it must not invent
            // tactical destinations, support runs, pressing, spacing or roaming.
            var targetPosition = snap
                ? directIncoming.ClampedWorld
                : ResolvePredictedFieldPosition(livePlayer, predictionSeconds);
            if (suppressBoundaryMotion)
            {
                targetPosition = directIncoming.ClampedWorld;
            }
            targetPosition = ClampToFieldBounds(targetPosition, false);

            var targetDelta = targetPosition - startPosition;
            targetDelta.y = 0f;
            var targetDistance = targetDelta.magnitude;
            var hardSnap = snap;
            var presentationSpeed = liveVelocity.magnitude;

            Vector3 appliedPosition;
            if (hardSnap)
            {
                appliedPosition = targetPosition;
            }
            else
            {
                var catchupSpeed = Mathf.Max(
                    presentationSpeed,
                    Mathf.Min(
                        LivePlayerMaxSpeedUnitsPerSecond,
                        targetDistance / Mathf.Max(LivePlayerCatchUpSeconds, 0.05f)));
                appliedPosition = Vector3.MoveTowards(
                    startPosition,
                    targetPosition,
                    catchupSpeed * Mathf.Max(dt, 0f));
            }

            appliedPosition = ClampToFieldBounds(appliedPosition, false);

            var lookDirection = new Vector3(livePlayer.facingX, 0f, livePlayer.facingZ);
            if (lookDirection.sqrMagnitude <= 0.0001f)
            {
                lookDirection = targetDelta.sqrMagnitude > 0.0001f ? targetDelta : player.Forward;
                lookDirection.y = 0f;
            }

            var rotation = player.Rotation;
            if (lookDirection.sqrMagnitude > 0.0001f)
            {
                var desiredRotation = Quaternion.LookRotation(lookDirection.normalized, Vector3.up);
                rotation = hardSnap
                    ? desiredRotation
                    : Quaternion.Slerp(
                        player.Rotation,
                        desiredRotation,
                        Mathf.Clamp01(Mathf.Max(dt, 0f) * LivePlayerRotationLerpSpeed));
            }

            if (traceSample)
            {
                AppendRuntimeTrace(
                    "authoritative-pose",
                    "player=" + DescribeLivePlayer(livePlayer) +
                    " raw=" + FormatPlaybackVector(directIncoming.RawIncoming) +
                    " target=" + FormatPlaybackVector(targetPosition) +
                    " applied=" + FormatPlaybackVector(appliedPosition) +
                    " velocity=" + FormatPlaybackVector(liveVelocity) +
                    " snap=" + hardSnap);
            }

            player.SetExternalPlaybackPose(appliedPosition, rotation, hardSnap);

            var frameMovement = appliedPosition - startPosition;
            ApplyLiveAnimatorState(
                livePlayer,
                player,
                frameMovement,
                liveVelocity,
                dt,
                hardSnap,
                ((livePlayer.state ?? string.Empty).Trim().ToLowerInvariant()),
                1f,
                false);

            if (hardSnap || dt <= 0f)
            {
                return hardSnap ? 0f : presentationSpeed;
            }

            return frameMovement.magnitude / Mathf.Max(dt, LiveTraceDtFloorSeconds);
        }
''',
)
runtime = replace_method(
    runtime,
    r'\s*private void TryStartSyntheticBallTransit\(',
    '''        private void TryStartSyntheticBallTransit(MatchResponse previousState, MatchResponse nextState, bool forceSnap)
        {
            // The backend is authoritative for the ball trajectory. Keep this
            // compatibility hook but never generate a client-side second path.
            ClearSyntheticBallTransit();
        }
''',
)
runtime = replace_method(
    runtime,
    r'\s*private bool TryDriveSyntheticBallTransit\(',
    '''        private bool TryDriveSyntheticBallTransit()
        {
            // Authoritative ball positions/velocities are applied directly by DriveBall().
            return false;
        }
''',
)
runtime = replace_method(
    runtime,
    r'\s*private void DriveBall\(',
    '''        private void DriveBall()
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
            var targetPosition = ballHolder != null || suppressBoundaryMotion
                ? ballConversion.ClampedWorld
                : ResolvePredictedFieldPosition(currentState.ballPosition, ResolveLivePredictionSeconds());
            var ballVelocity = ResolvePlaybackBallVelocity(currentState.ballPosition, suppressBoundaryMotion);
            runtimeTraceBallSpeed = new Vector3(ballVelocity.x, 0f, ballVelocity.z).magnitude;
            targetPosition = ClampToFieldBounds(targetPosition, true);

            if (Time.unscaledTime - runtimeTraceLastBallSampleAt >= PlaybackTraceSampleIntervalSeconds)
            {
                runtimeTraceLastBallSampleAt = Time.unscaledTime;
                TraceBallPitchSample(ballConversion, targetPosition, ballHolder);
            }

            // One source of truth: authoritative backend position + velocity.
            GtexMatchController.BallAdapter.ApplyExternalState(
                targetPosition,
                ballVelocity,
                ballHolder);
        }
''',
)
runtime_path.write_text(runtime + '\n', encoding='utf-8')

player_path = ROOT / 'Gtex_Test_Migration/Assets/Code/MatchEngine/Players/PlayerBase.cs'
player = player_path.read_text(encoding='utf-8-sig')
marker = '        public void ProcessBehaviours (in float time) {\n'
guard = '''        public void ProcessBehaviours (in float time) {
            // GTEX LivePlayback is authoritative playback, not a second local AI
            // simulation. The original behaviour stack remains available in the
            // standalone asset and simulation modes.
            if (GtexRuntimeState.ActiveMode == GtexRuntimeMode.LivePlayback)
            {
                ActiveBehaviour = null;
                NextBehaviour = 0;
                return;
            }
'''
if marker not in player:
    raise SystemExit('PlayerBase ProcessBehaviours marker not found')
if guard not in player:
    player = player.replace(marker, guard, 1)
player_path.write_text(player + '\n', encoding='utf-8')

physics_path = ROOT / 'Gtex_Test_Migration/Assets/Code/GTEX/Engine/GtexPlaybackPhysicsUtil.cs'
physics = physics_path.read_text(encoding='utf-8-sig')
old_physics = '''        public static void ApplyExternalPlaybackPosition(
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
                if (snap)
                {
                    rb.position = nextPosition;
                    rb.rotation = nextRotation;
                    target.SetPositionAndRotation(nextPosition, nextRotation);
                    return;
                }

                rb.MovePosition(nextPosition);
                rb.MoveRotation(nextRotation);
                return;
            }

            target.SetPositionAndRotation(nextPosition, nextRotation);
        }
'''
new_physics = '''        public static void ApplyExternalPlaybackPosition(
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

            // External GTEX playback is render-state application, not a physics
            // simulation. Immediate writes prevent Update/FixedUpdate from becoming
            // two competing clocks for the same actor.
            if (rb != null)
            {
                rb.position = nextPosition;
                rb.rotation = nextRotation;
                target.SetPositionAndRotation(nextPosition, nextRotation);
                return;
            }

            target.SetPositionAndRotation(nextPosition, nextRotation);
        }
'''
if old_physics not in physics:
    raise SystemExit('GtexPlaybackPhysicsUtil method shape not found')
physics_path.write_text(physics.replace(old_physics, new_physics, 1) + '\n', encoding='utf-8')

ball_path = ROOT / 'Gtex_Test_Migration/Assets/Code/MatchEngine/Ball/Ball.cs'
ball = ball_path.read_text(encoding='utf-8-sig')
ball = replace_method(
    ball,
    r'\s*private void FixedUpdate\(\)',
    '''        private void FixedUpdate()
        {
            // GTEX external playback is driven by the authoritative update loop.
            // Do not run a second FixedUpdate trajectory solver.
            if (ExternalPlaybackEnabled)
            {
                return;
            }
        }
''',
)
ball, applied = re.subn(
    r'''\s*if \(!hasExternalPlaybackTarget\s*\|\|\s*Vector3\.Distance\(rigidbody\.position, targetPosition\)\s*>=\s*ResolveExternalPlaybackTeleportDistance\(\)\)\s*\{\s*GtexPlaybackPhysicsUtil\.ApplyExternalPlaybackPosition\(\s*transform,\s*rigidbody,\s*targetPosition,\s*externalPlaybackTargetRotation\);\s*\}\s*\s*hasExternalPlaybackTarget\s*=\s*true;''',
    '''
            // Apply every authoritative frame. Do not skip near targets based on a
            // teleport threshold.
            GtexPlaybackPhysicsUtil.ApplyExternalPlaybackPosition(
                transform,
                rigidbody,
                targetPosition,
                externalPlaybackTargetRotation);
            hasExternalPlaybackTarget = true;''',
    ball,
    count=1,
)
if applied != 1:
    raise SystemExit(f'Ball no-holder external state branch replacements={applied}')
ball, applied = re.subn(
    r'''\s*if \(holderChanged\s*\|\|\s*Vector3\.Distance\(rigidbody\.position, ResolveExternalPlaybackHolderAnchor\(holder\)\)\s*>=\s*ResolveExternalPlaybackHolderSnapDistance\(\) \* 1\.75f\)\s*\{\s*SnapExternalPlaybackHolderAnchor\(holder\);\s*\}\s*\s*return;''',
    '''
                var holderAnchor = ResolveExternalPlaybackHolderAnchor(holder);
                transform.position = holderAnchor;
                rigidbody.position = holderAnchor;
                return;''',
    ball,
    count=1,
)
if applied != 1:
    raise SystemExit(f'Ball holder external state branch replacements={applied}')
ball_path.write_text(ball + '\n', encoding='utf-8')

# Strict source-level gates.
runtime_check = runtime_path.read_text(encoding='utf-8')
apply_match = re.search(r'private float ApplyLivePlayerState\([\s\S]*?\n        }\n\s*private Vector3 ResolveBehaviorAnchorPosition', runtime_check)
if not apply_match:
    raise SystemExit('could not locate patched ApplyLivePlayerState')
assert 'ResolveBehaviorDrivenFieldPosition' not in apply_match.group(0)
assert 'ResolveBehaviorAnchorPosition' not in apply_match.group(0)
assert 'ApplyStructuredTeamSpacing' not in apply_match.group(0)
assert 'FilterLivePlayerTarget' not in apply_match.group(0)
assert '/api/v2/ws/match/' in runtime_check
assert 'GtexRuntimeState.MarkStarted(GtexRuntimeMode.LivePlayback' in runtime_check
assert 'ClearSyntheticBallTransit();' in re.search(r'private void TryStartSyntheticBallTransit\([\s\S]*?\n        }', runtime_check).group(0)
assert 'return false;' in re.search(r'private bool TryDriveSyntheticBallTransit\([\s\S]*?\n        }', runtime_check).group(0)
assert 'GtexRuntimeState.ActiveMode == GtexRuntimeMode.LivePlayback' in player
assert 'rb.MovePosition(nextPosition)' not in physics_path.read_text(encoding='utf-8')
assert 'ResolveExternalPlaybackTeleportDistance()' not in re.search(r'public void ApplyExternalState\([\s\S]*?\n        }', ball_path.read_text(encoding='utf-8')).group(0)
assert 'ApplyExternalPlaybackPosition(' in ball_path.read_text(encoding='utf-8')

subprocess.run(['git', 'diff', '--check'], check=True)
