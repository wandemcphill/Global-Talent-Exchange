using System;
using System.Collections.Generic;
using System.Linq;
using FStudio.GTEX.Engine;
using FStudio.MatchEngine;
using FStudio.MatchEngine.Players;
using FStudio.MatchEngine.Players.PlayerController;
using Shared.Responses;
using UnityEngine;

namespace FStudio.GTEX.Authoritative
{
    /// <summary>
    /// Final presentation guard for GTEX LivePlayback.
    ///
    /// The backend remains the football authority. This component runs late enough
    /// to overwrite any legacy visual solver that may still be present in the asset,
    /// while keeping interpolation here strictly presentational.
    /// </summary>
    [DefaultExecutionOrder(10000)]
    public sealed class GtexAuthoritativePlaybackGuard : MonoBehaviour
    {
        private const float PlayerCatchupSeconds = 0.20f;
        private const float BallCatchupSeconds = 0.12f;
        private const float MaxPlayerPresentationSpeed = 9.5f;
        private const float MaxBallPresentationSpeed = 14f;
        private const float CameraMoveSharpness = 4.8f;
        private const float CameraRotationSharpness = 6.5f;
        private const float CameraFovSharpness = 4.2f;
        private const float BroadcastLookAheadSeconds = 0.12f;
        private const float BroadcastHeight = 34f;
        private const float BroadcastDepth = -43f;
        private const float BroadcastFov = 46f;
        private const float BroadcastFieldInsetX = 7.5f;
        private const float BroadcastFieldInsetZ = 5.5f;
        private const float MinBallHeight = 0.1f;

        private sealed class TrackedPlayer
        {
            public GtexLegacyPlayerHandle Handle;
            public string PlayerId;
            public string TeamSide;
            public Vector3 FilteredPosition;
            public bool Initialized;
        }

        private readonly Dictionary<string, TrackedPlayer> trackedPlayers = new(StringComparer.Ordinal);
        private float nextBindingRefreshAt;
        private Camera controlledCamera;
        private bool cameraInitialized;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Bootstrap()
        {
            if (FindFirstObjectByType<GtexAuthoritativePlaybackGuard>() != null)
            {
                return;
            }

            var host = new GameObject("GTEX Authoritative Playback Guard");
            DontDestroyOnLoad(host);
            host.AddComponent<GtexAuthoritativePlaybackGuard>();
        }

        private void Update()
        {
            if (GtexRuntimeState.ActiveMode != GtexRuntimeMode.LivePlayback)
            {
                return;
            }

            SuppressLegacyDecisions();
        }

        private void LateUpdate()
        {
            if (GtexRuntimeState.ActiveMode != GtexRuntimeMode.LivePlayback)
            {
                return;
            }

            var state = GtexMatchController.CurrentState;
            if (state == null || MatchManager.Current == null)
            {
                return;
            }

            RefreshBindings(state);
            DrivePlayers(state);
            DriveBall(state);
            DriveBroadcastCamera(state);
        }

        private void SuppressLegacyDecisions()
        {
            if (MatchManager.Current == null || !GtexMatchController.MatchManagerAdapter.HasTeams)
            {
                return;
            }

            foreach (var player in EnumeratePlayers())
            {
                if (player == null)
                {
                    continue;
                }

                player.ResetBehaviours();
                player.ActiveBehaviour = null;
                player.NextBehaviour = 0f;
            }
        }

        private IEnumerable<PlayerBase> EnumeratePlayers()
        {
            if (MatchManager.Current == null)
            {
                yield break;
            }

            var home = MatchManager.Current.GameTeam1;
            var away = MatchManager.Current.GameTeam2;

            if (home != null && home.GamePlayers != null)
            {
                foreach (var player in home.GamePlayers)
                {
                    if (player != null)
                    {
                        yield return player;
                    }
                }
            }

            if (away != null && away.GamePlayers != null)
            {
                foreach (var player in away.GamePlayers)
                {
                    if (player != null)
                    {
                        yield return player;
                    }
                }
            }
        }

        private void RefreshBindings(GtexMatchState state)
        {
            if (Time.unscaledTime < nextBindingRefreshAt && trackedPlayers.Count > 0)
            {
                return;
            }

            nextBindingRefreshAt = Time.unscaledTime + 0.5f;
            var liveState = TryGetLiveResponse(state.MatchId);
            if (liveState == null || liveState.players == null)
            {
                return;
            }

            var home = GtexMatchController.MatchManagerAdapter.GetHomePlayers();
            var away = GtexMatchController.MatchManagerAdapter.GetAwayPlayers();
            BindSide(liveState, "home", home);
            BindSide(liveState, "away", away);
        }

        private MatchResponse TryGetLiveResponse(string matchId)
        {
            // GtexMatchRuntime owns the transport. Its current state is private,
            // so use the public live-state signal cache maintained by this guard.
            return liveResponse;
        }

        private MatchResponse liveResponse;

        public void SetObservedLiveState(MatchResponse state)
        {
            liveResponse = state;
        }

        private void BindSide(MatchResponse state, string side, IReadOnlyList<GtexLegacyPlayerHandle> candidates)
        {
            var livePlayers = state.players
                .Where(p => p != null && !p.isBall && string.Equals(NormalizeSide(p.teamSide), side, StringComparison.OrdinalIgnoreCase))
                .ToArray();

            var available = new List<GtexLegacyPlayerHandle>(candidates ?? Array.Empty<GtexLegacyPlayerHandle>());
            foreach (var live in livePlayers)
            {
                var key = BuildKey(live);
                if (string.IsNullOrWhiteSpace(key))
                {
                    continue;
                }

                if (trackedPlayers.TryGetValue(key, out var existing) && existing.Handle != null && existing.Handle.IsValid)
                {
                    continue;
                }

                GtexLegacyPlayerHandle best = null;
                var bestScore = float.MaxValue;
                foreach (var candidate in available)
                {
                    if (candidate == null || !candidate.IsValid)
                    {
                        continue;
                    }

                    var score = Vector3.Distance(candidate.Position, candidate.Position);
                    if (live.shirtNumber > 0 && candidate.ShirtNumber == live.shirtNumber)
                    {
                        score -= 20f;
                    }

                    if (ResolveRoleBucket(live) == ResolveRoleBucket(candidate.PositionRole))
                    {
                        score -= 40f;
                    }
                    else
                    {
                        score += 25f;
                    }

                    if (live.playerId != null && int.TryParse(live.playerId, out var numericId) &&
                        candidate.DatabasePlayerId.HasValue && candidate.DatabasePlayerId.Value == numericId)
                    {
                        score -= 100f;
                    }

                    if (score < bestScore)
                    {
                        bestScore = score;
                        best = candidate;
                    }
                }

                if (best == null)
                {
                    continue;
                }

                if (available.Contains(best))
                {
                    available.Remove(best);
                }

                trackedPlayers[key] = new TrackedPlayer
                {
                    Handle = best,
                    PlayerId = (live.playerId ?? string.Empty).Trim(),
                    TeamSide = side,
                    FilteredPosition = ResolveLivePosition(live, state),
                    Initialized = false,
                };
                GtexVisualAuthority.RegisterPlayer(best.RawPlayer, side + ":" + (live.playerId ?? live.shirtNumber.ToString()));
            }
        }

        private void DrivePlayers(GtexMatchState controllerState)
        {
            var state = liveResponse;
            if (state == null || state.players == null)
            {
                return;
            }

            var dt = Mathf.Max(Time.unscaledDeltaTime, 1f / 60f);
            foreach (var live in state.players)
            {
                if (live == null || live.isBall)
                {
                    continue;
                }

                var key = BuildKey(live);
                if (string.IsNullOrWhiteSpace(key) || !trackedPlayers.TryGetValue(key, out var tracked) || tracked.Handle == null || !tracked.Handle.IsValid)
                {
                    continue;
                }

                var authoritative = ResolveLivePosition(live, state);
                if (!tracked.Initialized)
                {
                    tracked.FilteredPosition = authoritative;
                    tracked.Initialized = true;
                }

                var delta = authoritative - tracked.FilteredPosition;
                delta.y = 0f;
                var distance = delta.magnitude;
                if (distance > 0.01f)
                {
                    var speed = Mathf.Min(MaxPlayerPresentationSpeed, Mathf.Max(1.5f, distance / PlayerCatchupSeconds));
                    tracked.FilteredPosition = Vector3.MoveTowards(
                        tracked.FilteredPosition,
                        authoritative,
                        speed * dt);
                }

                tracked.FilteredPosition = ClampPitch(tracked.FilteredPosition, false);

                var direction = ResolveFacing(live, delta, tracked.Handle.Forward);
                var rotation = tracked.Handle.Rotation;
                if (direction.sqrMagnitude > 0.001f)
                {
                    var desired = Quaternion.LookRotation(direction.normalized, Vector3.up);
                    rotation = Quaternion.Slerp(
                        rotation,
                        desired,
                        1f - Mathf.Exp(-10f * dt));
                }

                tracked.Handle.SetExternalPlaybackPose(tracked.FilteredPosition, rotation, false);
                tracked.Handle.ApplyExternalAnimatorState(
                    live.hasPossession,
                    ResolveAnimatorSpeed(live, delta, dt),
                    0f,
                    delta.magnitude > 0.01f ? 1f : 0f);
            }
        }

        private void DriveBall(GtexMatchState controllerState)
        {
            var state = liveResponse;
            if (state == null || state.ballPosition == null || !GtexMatchController.BallAdapter.IsAvailable)
            {
                return;
            }

            var ball = Ball.Current;
            if (ball == null)
            {
                return;
            }

            var authoritative = ResolveLivePosition(state.ballPosition, state, true);
            var velocity = ResolveLiveVelocity(state.ballPosition, state);
            var dt = Mathf.Max(Time.unscaledDeltaTime, 1f / 60f);
            var holder = ResolveHolder(state, state.ballPosition.playerId);

            var current = ball.transform.position;
            var desired = authoritative;
            if (holder == null)
            {
                var delta = authoritative - current;
                delta.y = 0f;
                var distance = delta.magnitude;
                if (distance > 0.01f)
                {
                    var velocitySpeed = new Vector3(velocity.x, 0f, velocity.z).magnitude;
                    var speed = Mathf.Min(
                        MaxBallPresentationSpeed,
                        Mathf.Max(velocitySpeed, distance / BallCatchupSeconds));
                    desired = Vector3.MoveTowards(current, authoritative, speed * dt);
                }
            }

            desired = ClampPitch(desired, true);
            ball.transform.position = desired;
            if (ball.Rigidbody != null)
            {
                ball.Rigidbody.position = desired;
            }

            var holderId = state.ballPosition.playerId ?? string.Empty;
            if (holder != null && holder.IsValid)
            {
                var direction = velocity.sqrMagnitude > 0.0001f ? velocity.normalized : holder.Forward;
                var anchor = GtexMatchController.BallAdapter.ResolveExternalReleaseAnchor(holder.RawPlayer, direction, desired);
                ball.transform.position = anchor;
                if (ball.Rigidbody != null)
                {
                    ball.Rigidbody.position = anchor;
                }
            }
        }

        private void DriveBroadcastCamera(GtexMatchState controllerState)
        {
            EnsureCamera();
            if (controlledCamera == null)
            {
                return;
            }

            var ball = Ball.Current;
            var focus = ball != null ? ball.transform.position : Vector3.zero;
            var velocity = ball != null ? ball.Velocity : Vector3.zero;
            velocity.y = 0f;
            focus += velocity * BroadcastLookAheadSeconds;

            var pitch = GtexMatchController.MatchManagerAdapter.FieldSize;
            var halfX = pitch.x > 1f ? pitch.x * 0.5f : 52.5f;
            var halfZ = pitch.y > 1f ? pitch.y * 0.5f : 34f;
            focus.x = Mathf.Clamp(focus.x, -halfX + BroadcastFieldInsetX, halfX - BroadcastFieldInsetX);
            focus.z = Mathf.Clamp(focus.z, -halfZ + BroadcastFieldInsetZ, halfZ - BroadcastFieldInsetZ);
            focus.y = 0.75f;

            var desiredPosition = focus + new Vector3(0f, BroadcastHeight, BroadcastDepth);
            var desiredRotation = Quaternion.LookRotation(focus - desiredPosition, Vector3.up);
            var dt = Mathf.Max(Time.unscaledDeltaTime, 1f / 60f);

            if (!cameraInitialized)
            {
                controlledCamera.transform.SetPositionAndRotation(desiredPosition, desiredRotation);
                controlledCamera.fieldOfView = BroadcastFov;
                cameraInitialized = true;
                return;
            }

            var positionBlend = 1f - Mathf.Exp(-CameraMoveSharpness * dt);
            var rotationBlend = 1f - Mathf.Exp(-CameraRotationSharpness * dt);
            var fovBlend = 1f - Mathf.Exp(-CameraFovSharpness * dt);
            controlledCamera.transform.position = Vector3.Lerp(
                controlledCamera.transform.position,
                desiredPosition,
                positionBlend);
            controlledCamera.transform.rotation = Quaternion.Slerp(
                controlledCamera.transform.rotation,
                desiredRotation,
                rotationBlend);
            controlledCamera.fieldOfView = Mathf.Lerp(
                controlledCamera.fieldOfView,
                BroadcastFov,
                fovBlend);
        }

        private void EnsureCamera()
        {
            if (controlledCamera != null)
            {
                return;
            }

            controlledCamera = Camera.main;
        }

        private Vector3 ResolveLivePosition(PlayerPosition live, MatchResponse state, bool ball = false)
        {
            var pitchLength = Mathf.Max(1f, state.pitchLengthMeters);
            var pitchWidth = Mathf.Max(1f, state.pitchWidthMeters);
            var normalizedX = Mathf.InverseLerp(-pitchLength * 0.5f, pitchLength * 0.5f, live.x);
            var normalizedZ = Mathf.InverseLerp(-pitchWidth * 0.5f, pitchWidth * 0.5f, live.z);
            var field = GtexMatchController.MatchManagerAdapter.FieldSize;
            var halfX = field.x * 0.5f;
            var halfZ = field.y * 0.5f;
            return new Vector3(
                Mathf.Lerp(-halfX, halfX, normalizedX),
                ball ? Mathf.Max(MinBallHeight, live.y) : 0f,
                Mathf.Lerp(-halfZ, halfZ, normalizedZ));
        }

        private Vector3 ResolveLiveVelocity(PlayerPosition live, MatchResponse state)
        {
            if (live == null)
            {
                return Vector3.zero;
            }

            var field = GtexMatchController.MatchManagerAdapter.FieldSize;
            var pitchLength = Mathf.Max(1f, state.pitchLengthMeters);
            var pitchWidth = Mathf.Max(1f, state.pitchWidthMeters);
            return new Vector3(
                live.velocityX / pitchLength * field.x,
                live.velocityY,
                live.velocityZ / pitchWidth * field.y);
        }

        private static Vector3 ResolveFacing(PlayerPosition live, Vector3 delta, Vector3 fallback)
        {
            // PlayerPosition versions in this migration do not guarantee explicit
            // facing fields, so use authoritative velocity first, then position delta.
            var direction = new Vector3(live.velocityX, 0f, live.velocityZ);
            if (direction.sqrMagnitude <= 0.0001f)
            {
                direction = delta;
            }

            if (direction.sqrMagnitude <= 0.0001f)
            {
                direction = fallback;
            }

            direction.y = 0f;
            return direction;
        }

        private static float ResolveAnimatorSpeed(PlayerPosition live, Vector3 delta, float dt)
        {
            var speed = dt > 0.0001f ? delta.magnitude / dt : 0f;
            speed = Mathf.Clamp01(speed / 8f);
            if (live.hasPossession)
            {
                speed = Mathf.Max(speed, Mathf.Clamp01(new Vector3(live.velocityX, 0f, live.velocityZ).magnitude / 8f));
            }

            return speed;
        }

        private static GtexLegacyPlayerHandle ResolveHolder(MatchResponse state, string playerId)
        {
            if (string.IsNullOrWhiteSpace(playerId))
            {
                return null;
            }

            var key = string.Empty;
            if (TryFindTrackedKey(state, playerId, out key) &&
                FindObjectOfType<GtexAuthoritativePlaybackGuard>()?.trackedPlayers.TryGetValue(key, out var tracked) == true)
            {
                return tracked.Handle;
            }

            return null;
        }

        private static bool TryFindTrackedKey(MatchResponse state, string playerId, out string key)
        {
            key = string.Empty;
            if (state == null || state.players == null)
            {
                return false;
            }

            var player = state.players.FirstOrDefault(p => p != null && !p.isBall && string.Equals((p.playerId ?? string.Empty).Trim(), (playerId ?? string.Empty).Trim(), StringComparison.Ordinal));
            if (player == null)
            {
                return false;
            }

            key = BuildKey(player);
            return !string.IsNullOrWhiteSpace(key);
        }

        private static string BuildKey(PlayerPosition player)
        {
            if (player == null)
            {
                return string.Empty;
            }

            if (!string.IsNullOrWhiteSpace(player.entityId))
            {
                return player.entityId.Trim();
            }

            if (!string.IsNullOrWhiteSpace(player.playerId))
            {
                return "player:" + player.playerId.Trim();
            }

            return NormalizeSide(player.teamSide) + ":shirt:" + player.shirtNumber;
        }

        private static string NormalizeSide(string value)
        {
            var normalized = (value ?? string.Empty).Trim().ToLowerInvariant();
            return normalized == "away" || normalized == "2" ? "away" : "home";
        }

        private static int ResolveRoleBucket(PlayerPosition player)
        {
            if (player == null)
            {
                return 0;
            }

            var role = (player.role ?? string.Empty).Trim().ToUpperInvariant();
            if (role.Contains("GK") || role.Contains("KEEPER")) return 0;
            if (role.Contains("DEF") || role.Contains("BACK")) return 1;
            if (role.Contains("MID")) return 2;
            return 3;
        }

        private static int ResolveRoleBucket(FStudio.Data.Positions position)
        {
            if ((position & FStudio.Data.Positions.GK) != 0) return 0;
            if ((position & (FStudio.Data.Positions.DF | FStudio.Data.Positions.DCB | FStudio.Data.Positions.DLB | FStudio.Data.Positions.DRB)) != 0) return 1;
            if ((position & FStudio.Data.Positions.MF) != 0) return 2;
            return 3;
        }

        private static Vector3 ClampPitch(Vector3 position, bool ball)
        {
            var pitch = GtexMatchController.CurrentPitchSpace;
            if (pitch == null)
            {
                return position;
            }

            var clamped = pitch.ClampWorld(position);
            clamped.y = ball ? Mathf.Max(MinBallHeight, clamped.y) : pitch.GrassY;
            return clamped;
        }
    }
}
