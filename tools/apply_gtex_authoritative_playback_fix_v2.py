from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def method_span(text, pattern):
    m = re.search(pattern, text, re.MULTILINE)
    if not m:
        raise SystemExit(f"method not found: {pattern}")
    start = m.start()
    brace = text.find('{', m.end())
    if brace < 0:
        raise SystemExit(f"opening brace not found: {pattern}")
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0: return start, brace, i + 1
    raise SystemExit(f"closing brace not found: {pattern}")


def replace_method(text, pattern, replacement):
    start, _, end = method_span(text, pattern)
    return text[:start] + replacement.rstrip() + text[end:]


def insert_after_open(text, pattern, insertion):
    _, brace, _ = method_span(text, pattern)
    return text[:brace + 1] + insertion + text[brace + 1:]

# ---------------- runtime ----------------
runtime_path = ROOT / 'Gtex_Test_Migration/Assets/Code/GTEX/GtexMatchRuntime.cs'
runtime = runtime_path.read_text(encoding='utf-8-sig')

# Mark LivePlayback started only after scene bootstrap has succeeded, so local AI
# is suppressed for the actual GTEX playback session without falsifying bootstrap state.
runtime = runtime.replace(
    '            matchLoaded = true;\n',
    '            matchLoaded = true;\n            GtexRuntimeState.MarkStarted(GtexRuntimeMode.LivePlayback, nameof(GtexMatchRuntime));\n',
    1,
)
runtime = runtime.replace(
    'return normalized + "/api/v1/ws/match/" + Uri.EscapeDataString(matchId) + "?format=unity";',
    'return normalized + "/api/v2/ws/match/" + Uri.EscapeDataString(matchId) + "?format=unity";',
    1,
)

runtime = replace_method(runtime, r'\s*private float ApplyLivePlayerState\(', '''        private float ApplyLivePlayerState(
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

            // LivePlayback is presentation of authoritative backend movement. Do not
            // invent tactical destinations, support runs, pressing, spacing or roaming.
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

            var lookDirection = liveVelocity.sqrMagnitude > 0.0001f
                ? liveVelocity
                : targetDelta.sqrMagnitude > 0.0001f
                    ? targetDelta
                    : player.Forward;
            lookDirection.y = 0f;

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
''')

runtime = replace_method(runtime, r'\s*private void TryStartSyntheticBallTransit\(', '''        private void TryStartSyntheticBallTransit(MatchResponse previousState, MatchResponse nextState, bool forceSnap)
        {
            // Never manufacture a second pass/shot trajectory in LivePlayback.
            ClearSyntheticBallTransit();
        }
''')
runtime = replace_method(runtime, r'\s*private bool TryDriveSyntheticBallTransit\(', '''        private bool TryDriveSyntheticBallTransit()
        {
            // Kept only for the existing playback-applier callback shape.
            return false;
        }
''')
runtime = replace_method(runtime, r'\s*private void DriveBall\(', '''        private void DriveBall()
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
''')

# Add event/action de-duplication so repeated websocket frames cannot replay the same kick.
runtime = runtime.replace(
    '        private string lastAppliedBallHolderId = string.Empty;\n',
    '        private string lastAppliedBallHolderId = string.Empty;\n        private string lastLiveBallActionKey = string.Empty;\n        private string lastLiveEventActionKey = string.Empty;\n',
    1,
)
runtime = runtime.replace(
    '            if (forceSnap || phaseChanged)\n            {\n',
    '            if (forceSnap || phaseChanged)\n            {\n                lastLiveBallActionKey = string.Empty;\n                lastLiveEventActionKey = string.Empty;\n',
    1,
)

runtime = insert_after_open(runtime, r'\s*private void TryTriggerLiveBallAction\(', '''
            var liveBallEvent = nextState != null ? nextState.ResolveActiveEvent() : null;
            var liveBallEventToken = liveBallEvent != null && !string.IsNullOrWhiteSpace(liveBallEvent.id)
                ? liveBallEvent.id.Trim()
                : liveBallEvent != null
                    ? liveBallEvent.sequence + "|" + (liveBallEvent.type ?? string.Empty).Trim().ToLowerInvariant()
                    : "none";
            var liveBallActionKey = liveBallEventToken + "|" +
                ((previousState.ballPosition.playerId ?? string.Empty).Trim()) + "|" +
                ((nextState.ballPosition.playerId ?? string.Empty).Trim());
            if (string.Equals(lastLiveBallActionKey, liveBallActionKey, StringComparison.Ordinal))
            {
                return;
            }
            lastLiveBallActionKey = liveBallActionKey;
''')
runtime = insert_after_open(runtime, r'\s*private void TryTriggerLiveEventAction\(', '''
            var liveEvent = nextState != null ? nextState.ResolveActiveEvent() : null;
            var liveEventToken = liveEvent != null && !string.IsNullOrWhiteSpace(liveEvent.id)
                ? liveEvent.id.Trim()
                : liveEvent != null
                    ? liveEvent.sequence + "|" + (liveEvent.type ?? string.Empty).Trim().ToLowerInvariant()
                    : "none";
            var liveEventActionKey = liveEventToken + "|" +
                (liveEvent != null ? (liveEvent.primaryPlayerId ?? string.Empty).Trim() : string.Empty) + "|" +
                (liveEvent != null ? (liveEvent.secondaryPlayerId ?? string.Empty).Trim() : string.Empty);
            if (string.Equals(lastLiveEventActionKey, liveEventActionKey, StringComparison.Ordinal))
            {
                return;
            }
            lastLiveEventActionKey = liveEventActionKey;
''')
runtime_path.write_text(runtime + '\n', encoding='utf-8')

# ---------------- PlayerBase: disable local AI only for the authoritative live session ----------------
player_path = ROOT / 'Gtex_Test_Migration/Assets/Code/MatchEngine/Players/PlayerBase.cs'
player = player_path.read_text(encoding='utf-8-sig')
marker = '        public void ProcessBehaviours (in float time) {\n'
guard = '''        public void ProcessBehaviours (in float time) {
            // GTEX LivePlayback is authoritative playback, not a second local AI simulation.
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

# ---------------- Physics visual playback ----------------
physics_path = ROOT / 'Gtex_Test_Migration/Assets/Code/GTEX/Engine/GtexPlaybackPhysicsUtil.cs'
physics = physics_path.read_text(encoding='utf-8-sig')
physics = replace_method(physics, r'\s*public static void ApplyExternalPlaybackPosition\(', '''        public static void ApplyExternalPlaybackPosition(
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

            // External GTEX playback is visual state application, not physics simulation.
            if (rb != null)
            {
                rb.position = nextPosition;
                rb.rotation = nextRotation;
                target.SetPositionAndRotation(nextPosition, nextRotation);
                return;
            }

            target.SetPositionAndRotation(nextPosition, nextRotation);
        }
''')
physics_path.write_text(physics + '\n', encoding='utf-8')

# ---------------- Ball: one external movement authority ----------------
ball_path = ROOT / 'Gtex_Test_Migration/Assets/Code/MatchEngine/Ball/Ball.cs'
ball = ball_path.read_text(encoding='utf-8-sig')
ball = replace_method(ball, r'\s*private void FixedUpdate\(\)', '''        private void FixedUpdate()
        {
            // GTEX external playback is driven by Update(), not by a second physics clock.
            if (ExternalPlaybackEnabled)
            {
                return;
            }
        }
''')
ball = re.sub(
    r'''\s*if \(!hasExternalPlaybackTarget\s*\|\|\s*Vector3\.Distance\(rigidbody\.position, targetPosition\)\s*>=\s*ResolveExternalPlaybackTeleportDistance\(\)\)\s*\{\s*GtexPlaybackPhysicsUtil\.ApplyExternalPlaybackPosition\(\s*transform,\s*rigidbody,\s*targetPosition,\s*externalPlaybackTargetRotation\);\s*\}''',
    '''
            // Apply every authoritative target. No hidden distance-based teleport gate.
            GtexPlaybackPhysicsUtil.ApplyExternalPlaybackPosition(
                transform,
                rigidbody,
                targetPosition,
                externalPlaybackTargetRotation);''',
    ball,
    count=1,
)
ball = re.sub(
    r'''\s*if \(holderChanged\s*\|\|\s*Vector3\.Distance\(rigidbody\.position, ResolveExternalPlaybackHolderAnchor\(holder\)\)\s*>=\s*ResolveExternalPlaybackHolderSnapDistance\(\) \* 1\.75f\)\s*\{\s*SnapExternalPlaybackHolderAnchor\(holder\);\s*\}''',
    '''
                var holderAnchor = ResolveExternalPlaybackHolderAnchor(holder);
                transform.position = holderAnchor;
                rigidbody.position = holderAnchor;''',
    ball,
    count=1,
)
ball_path.write_text(ball + '\n', encoding='utf-8')

# ---------------- validation ----------------
runtime_check = runtime_path.read_text(encoding='utf-8')
assert '/api/v2/ws/match/' in runtime_check
assert 'GtexRuntimeState.MarkStarted(GtexRuntimeMode.LivePlayback' in runtime_check
m = re.search(r'private float ApplyLivePlayerState\([\s\S]*?\n        }\n\s*private Vector3 ResolveBehaviorAnchorPosition', runtime_check)
assert m and 'ResolveBehaviorDrivenFieldPosition' not in m.group(0) and 'ApplyStructuredTeamSpacing' not in m.group(0) and 'FilterLivePlayerTarget' not in m.group(0)
assert 'return false;' in re.search(r'private bool TryDriveSyntheticBallTransit\([\s\S]*?\n        }', runtime_check).group(0)
assert 'lastLiveBallActionKey' in runtime_check and 'lastLiveEventActionKey' in runtime_check
assert 'GtexRuntimeState.ActiveMode == GtexRuntimeMode.LivePlayback' in player
assert 'rb.MovePosition(nextPosition)' not in physics_path.read_text(encoding='utf-8')
ball_check = ball_path.read_text(encoding='utf-8')
assert 'GtexPlaybackPhysicsUtil.ApplyExternalPlaybackPosition(' in ball_check
apply_span = re.search(r'public void ApplyExternalState\([\s\S]*?\n        }', ball_check)
assert apply_span and 'ResolveExternalPlaybackTeleportDistance()' not in apply_span.group(0)

subprocess.run(['git', 'diff', '--check'], check=True)
