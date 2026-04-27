using System;
using System.Collections.Generic;
using FStudio.GTEX.Playback;
using UnityEngine;
using GtexEvent = FStudio.GTEX.Event;

namespace FStudio.GTEX.Simulation
{
    public sealed class GtexSimSpatialSynthesizer
    {
        private const int PlayersPerSide = 11;
        private const float PitchLengthMeters = GtexPitchSpace.DefaultLength;
        private const float PitchWidthMeters = GtexPitchSpace.DefaultWidth;
        private const float ActiveEventLifetimeMinutes = 0.45f;
        private const float RoutinePassIntervalMinutes = 0.62f;
        private const float ShotDurationMinutes = 0.14f;
        private const float GoalResetDelayMinutes = 0.2f;
        private const float PassivePlayerLerpSpeed = 2.2f;
        private const float ActivePlayerLerpSpeed = 4.6f;
        private const float GroundPassArcHeight = 0.04f;
        private const float LoftedPassArcHeight = 0.24f;
        private const float GoalkeeperDistributionArcHeight = 0.18f;

        private static readonly int[] ShirtNumbers = { 1, 2, 4, 5, 3, 6, 8, 10, 7, 9, 11 };
        private static readonly string[] Roles = { "GK", "RB", "CB", "CB", "LB", "DM", "CM", "AM", "RW", "ST", "LW" };
        private static readonly string[] Lines = { "goalkeeper", "defense", "defense", "defense", "defense", "midfield", "midfield", "midfield", "attack", "attack", "attack" };
        private static readonly Vector3[] HomeAnchors =
        {
            new(-48f, 0f, 0f),
            new(-31f, 0f, 22f),
            new(-35f, 0f, 8f),
            new(-35f, 0f, -8f),
            new(-31f, 0f, -22f),
            new(-16f, 0f, 15f),
            new(-10f, 0f, 5f),
            new(-6f, 0f, -5f),
            new(-12f, 0f, -18f),
            new(12f, 0f, 8f),
            new(14f, 0f, -8f)
        };

        private struct BallTransit
        {
            public bool Active;
            public Vector3 Start;
            public Vector3 End;
            public float StartedAtMinute;
            public float DurationMinutes;
            public float ArcHeight;
            public string TargetPlayerId;
            public string PostTransitHolderPlayerId;
            public string PostTransitPossessionSide;
            public string TrajectoryType;
        }

        private readonly GtexSimSpatialPlayerState[] homePlayers = new GtexSimSpatialPlayerState[PlayersPerSide];
        private readonly GtexSimSpatialPlayerState[] awayPlayers = new GtexSimSpatialPlayerState[PlayersPerSide];
        private readonly List<GtexEvent> recentEvents = new();

        private bool initialized;
        private string possessionSide = "home";
        private string ballHolderPlayerId = "home-8";
        private string activeEventId = string.Empty;
        private string currentCameraPreset = "broadcast";
        private float currentCameraPresetUntilMinute = -1f;
        private float activeEventUntilMinute = -1f;
        private float nextRoutinePassMinute = RoutinePassIntervalMinutes;
        private float lastClockMinute = -1f;
        private int processedEventCount;
        private int nextEventSequence;
        private GtexSimState lastState = GtexSimState.Kickoff;
        private BallTransit activeTransit;
        private GtexSimSpatialBallState ballState = new();

        public MatchResponse SynthesizeMatchResponse(GtexSimEngine engine, GtexMatchConfig matchConfig, string matchId)
        {
            return SynthesizeSpatialState(engine, matchConfig).ToMatchResponse(matchId);
        }

        public GtexSimSpatialState SynthesizeSpatialState(GtexSimEngine engine, GtexMatchConfig matchConfig)
        {
            if (engine == null)
            {
                return new GtexSimSpatialState();
            }

            var currentMinute = Mathf.Max(0f, engine.Clock.CurrentMatchMinute);
            if (!initialized || currentMinute + 0.01f < lastClockMinute || (currentMinute <= 0.01f && lastState == GtexSimState.FullTime))
            {
                Reset();
            }

            var realSecondsPerMatchMinute = ResolveRealSecondsPerMatchMinute(matchConfig);
            var deltaMatchMinutes = lastClockMinute >= 0f ? Mathf.Max(0f, currentMinute - lastClockMinute) : 0.05f;
            var deltaSeconds = Mathf.Max(0.02f, deltaMatchMinutes * realSecondsPerMatchMinute);

            HandleStateTransition(engine.State, currentMinute, engine.HomeScore, engine.AwayScore);
            ConsumeNewEvents(engine, currentMinute);
            UpdatePlayers(currentMinute, deltaSeconds);
            UpdateBall(currentMinute, deltaSeconds, engine.State);
            UpdateCameraPreset(currentMinute);

            var spatialState = new GtexSimSpatialState
            {
                ClockMinute = currentMinute,
                Phase = ResolvePhaseToken(engine.State),
                HomeScore = engine.HomeScore,
                AwayScore = engine.AwayScore,
                PossessionSide = possessionSide,
                CameraPreset = currentCameraPreset,
                ActiveEventId = activeEventUntilMinute >= currentMinute ? activeEventId : string.Empty,
                Players = BuildSnapshotPlayers(),
                Ball = CloneBallState(),
                Events = BuildRecentEvents()
            };

            lastClockMinute = currentMinute;
            lastState = engine.State;
            return spatialState;
        }

        public void Reset()
        {
            InitializePlayers();
            possessionSide = "home";
            ballHolderPlayerId = "home-8";
            activeEventId = string.Empty;
            currentCameraPreset = "broadcast";
            currentCameraPresetUntilMinute = -1f;
            activeEventUntilMinute = -1f;
            nextRoutinePassMinute = RoutinePassIntervalMinutes;
            lastClockMinute = -1f;
            processedEventCount = 0;
            nextEventSequence = 0;
            lastState = GtexSimState.Kickoff;
            activeTransit = default;
            recentEvents.Clear();
            ballState = new GtexSimSpatialBallState
            {
                Position = new Vector3(0f, GtexPlaybackSanitizer.DefaultBallHeight, 0f),
                Velocity = Vector3.zero,
                HolderPlayerId = ballHolderPlayerId,
                TrajectoryType = "ground"
            };
            initialized = true;
        }

        private void InitializePlayers()
        {
            for (var index = 0; index < PlayersPerSide; index += 1)
            {
                homePlayers[index] = CreatePlayerState("home", index, HomeAnchors[index]);
                awayPlayers[index] = CreatePlayerState("away", index, MirrorAnchor(HomeAnchors[index]));
            }
        }

        private static GtexSimSpatialPlayerState CreatePlayerState(string teamSide, int index, Vector3 anchor)
        {
            var facingX = string.Equals(teamSide, "home", StringComparison.Ordinal) ? 1f : -1f;
            return new GtexSimSpatialPlayerState
            {
                EntityId = teamSide + "-" + (index + 1),
                PlayerId = teamSide + "-" + (index + 1),
                TeamSide = teamSide,
                Label = (string.Equals(teamSide, "home", StringComparison.Ordinal) ? "Home " : "Away ") + ShirtNumbers[index],
                Role = Roles[index],
                Line = Lines[index],
                ShirtNumber = ShirtNumbers[index],
                Position = anchor,
                Facing = new Vector3(facingX, 0f, 0f),
                AnimationState = "idle",
                SpeedRatio = 0f
            };
        }

        private void HandleStateTransition(GtexSimState nextState, float currentMinute, int homeScore, int awayScore)
        {
            if (lastState == nextState)
            {
                return;
            }

            switch (nextState)
            {
                case GtexSimState.HalfTime:
                    RegisterEvent("halftime", currentMinute, string.Empty, "Half-time whistle.", homeScore, awayScore, null);
                    currentCameraPreset = "broadcast";
                    currentCameraPresetUntilMinute = currentMinute + 0.2f;
                    activeTransit = default;
                    break;
                case GtexSimState.SecondHalf:
                    ballHolderPlayerId = "away-8";
                    possessionSide = "away";
                    nextRoutinePassMinute = currentMinute + 0.55f;
                    break;
                case GtexSimState.FullTime:
                    RegisterEvent("fulltime", currentMinute, string.Empty, "Full-time whistle.", homeScore, awayScore, null);
                    currentCameraPreset = "broadcast";
                    currentCameraPresetUntilMinute = currentMinute + 0.35f;
                    activeTransit = default;
                    break;
            }
        }

        private void ConsumeNewEvents(GtexSimEngine engine, float currentMinute)
        {
            var history = engine.EventSystem.History;
            for (; processedEventCount < history.Count; processedEventCount += 1)
            {
                var matchEvent = history[processedEventCount];
                if (matchEvent == null)
                {
                    continue;
                }

                if (matchEvent is GtexGoalEvent goalEvent)
                {
                    var attackingSide = ResolveTeamSide(goalEvent.ScoringTeam);
                    var sourcePlayerId = ResolveAttackingPlayerId(attackingSide);
                    var restartSide = string.Equals(attackingSide, "home", StringComparison.Ordinal) ? "away" : "home";
                    RegisterEvent("goal", currentMinute, attackingSide, goalEvent.Summary, goalEvent.HomeScore, goalEvent.AwayScore, sourcePlayerId);
                    StartTransit(
                        sourcePlayerId,
                        ResolveGoalMouthTarget(attackingSide, false),
                        currentMinute,
                        ShotDurationMinutes,
                        1.3f,
                        "shot",
                        restartSide + "-8",
                        restartSide);
                    nextRoutinePassMinute = currentMinute + GoalResetDelayMinutes;
                    currentCameraPreset = "broadcast";
                    currentCameraPresetUntilMinute = currentMinute + 0.28f;
                    continue;
                }

                if (matchEvent is GtexMissedChanceEvent missedChanceEvent)
                {
                    var attackingSide = ResolveTeamSide(missedChanceEvent.Team);
                    var recoveringSide = string.Equals(attackingSide, "home", StringComparison.Ordinal) ? "away" : "home";
                    var sourcePlayerId = ResolveAttackingPlayerId(attackingSide);
                    RegisterEvent("missed_chance", currentMinute, attackingSide, missedChanceEvent.Summary, engine.HomeScore, engine.AwayScore, sourcePlayerId);
                    StartTransit(
                        sourcePlayerId,
                        ResolveGoalMouthTarget(attackingSide, true),
                        currentMinute,
                        ShotDurationMinutes,
                        1.05f,
                        "shot",
                        recoveringSide + "-1",
                        recoveringSide);
                    nextRoutinePassMinute = currentMinute + 0.45f;
                    currentCameraPreset = "broadcast";
                    currentCameraPresetUntilMinute = currentMinute + 0.22f;
                    continue;
                }

                if (matchEvent is GtexFoulEvent foulEvent)
                {
                    var teamSide = ResolveTeamSide(foulEvent.Team);
                    var restartSide = string.Equals(teamSide, "home", StringComparison.Ordinal) ? "away" : "home";
                    ballHolderPlayerId = restartSide + "-6";
                    possessionSide = restartSide;
                    RegisterEvent("foul", currentMinute, teamSide, foulEvent.Summary, engine.HomeScore, engine.AwayScore, ballHolderPlayerId);
                    currentCameraPreset = "broadcast";
                    currentCameraPresetUntilMinute = currentMinute + 0.18f;
                    nextRoutinePassMinute = currentMinute + 0.42f;
                    activeTransit = default;
                    continue;
                }

                if (matchEvent is GtexCardEvent cardEvent)
                {
                    var teamSide = ResolveTeamSide(cardEvent.Team);
                    RegisterEvent(
                        cardEvent.CardType == GtexSimCardType.Red ? "red_card" : "yellow_card",
                        currentMinute,
                        teamSide,
                        cardEvent.Summary,
                        engine.HomeScore,
                        engine.AwayScore,
                        ResolveCentralPlayerId(teamSide));
                    currentCameraPreset = "broadcast";
                    currentCameraPresetUntilMinute = currentMinute + 0.18f;
                }
            }

            if (!activeTransit.Active &&
                currentMinute >= nextRoutinePassMinute &&
                !string.Equals(ResolvePhaseToken(engine.State), "fulltime", StringComparison.Ordinal))
            {
                StartRoutinePass(currentMinute, engine.HomeScore, engine.AwayScore);
            }
        }

        private void StartRoutinePass(float currentMinute, int homeScore, int awayScore)
        {
            var sourcePlayerId = string.IsNullOrWhiteSpace(ballHolderPlayerId)
                ? ResolveCentralPlayerId(possessionSide)
                : ballHolderPlayerId;
            var targetPlayerId = ResolveRoutinePassTarget(sourcePlayerId);
            if (string.IsNullOrWhiteSpace(targetPlayerId) || string.Equals(sourcePlayerId, targetPlayerId, StringComparison.Ordinal))
            {
                nextRoutinePassMinute = currentMinute + RoutinePassIntervalMinutes;
                return;
            }

            var sourcePlayer = FindPlayer(sourcePlayerId);
            var targetPlayer = FindPlayer(targetPlayerId);
            var targetPosition = targetPlayer != null
                ? ClampToPitch(
                    targetPlayer.Position +
                    ResolveForward(targetPlayer) * 0.45f +
                    targetPlayer.Velocity * 0.1f)
                : Vector3.zero;
            var passDurationMinutes = ResolveRoutinePassDuration(sourcePlayer, targetPlayer, targetPosition);
            var passArcHeight = ResolveRoutinePassArcHeight(sourcePlayer, targetPlayer, targetPosition);
            RegisterEvent(
                "pass",
                currentMinute,
                possessionSide,
                "Routine pass sequence.",
                homeScore,
                awayScore,
                sourcePlayerId,
                targetPlayerId);
            StartTransit(
                sourcePlayerId,
                targetPosition,
                currentMinute,
                passDurationMinutes,
                passArcHeight,
                "pass",
                targetPlayerId,
                possessionSide);
            currentCameraPreset = "broadcast";
            currentCameraPresetUntilMinute = currentMinute + 0.18f;
            nextRoutinePassMinute = currentMinute + RoutinePassIntervalMinutes;
        }

        private void StartTransit(
            string sourcePlayerId,
            Vector3 endPosition,
            float currentMinute,
            float durationMinutes,
            float arcHeight,
            string trajectoryType,
            string postTransitHolderPlayerId,
            string postTransitPossessionSide)
        {
            var sourcePlayer = FindPlayer(sourcePlayerId);
            var start = sourcePlayer != null ? sourcePlayer.Position + ResolveForward(sourcePlayer) * 0.7f : Vector3.zero;
            start.y = GtexPlaybackSanitizer.DefaultBallHeight;
            endPosition.y = GtexPlaybackSanitizer.DefaultBallHeight;

            activeTransit = new BallTransit
            {
                Active = true,
                Start = start,
                End = ClampToPitch(endPosition),
                StartedAtMinute = currentMinute,
                DurationMinutes = Mathf.Max(0.05f, durationMinutes),
                ArcHeight = Mathf.Max(0.02f, arcHeight),
                TargetPlayerId = postTransitHolderPlayerId,
                PostTransitHolderPlayerId = postTransitHolderPlayerId,
                PostTransitPossessionSide = postTransitPossessionSide,
                TrajectoryType = trajectoryType ?? "pass"
            };

            ballHolderPlayerId = string.Empty;
        }

        private void UpdatePlayers(float currentMinute, float deltaSeconds)
        {
            UpdateTeamPlayers(homePlayers, currentMinute, deltaSeconds, "home");
            UpdateTeamPlayers(awayPlayers, currentMinute, deltaSeconds, "away");
        }

        private void UpdateTeamPlayers(GtexSimSpatialPlayerState[] teamPlayers, float currentMinute, float deltaSeconds, string teamSide)
        {
            var teamHasPossession = string.Equals(possessionSide, teamSide, StringComparison.Ordinal);
            var attackDirection = string.Equals(teamSide, "home", StringComparison.Ordinal) ? 1f : -1f;
            var ballAnchor = ResolveBallAnchor(currentMinute);
            var activeReceiverPlayerId = activeTransit.Active ? activeTransit.PostTransitHolderPlayerId : string.Empty;
            var supportPlayerId =
                teamHasPossession
                    ? ResolveSupportPlayerId(teamSide, string.IsNullOrWhiteSpace(ballHolderPlayerId) ? activeReceiverPlayerId : ballHolderPlayerId, activeReceiverPlayerId)
                    : string.Empty;
            var runnerPlayerId =
                teamHasPossession
                    ? ResolveRunnerPlayerId(teamSide, string.IsNullOrWhiteSpace(ballHolderPlayerId) ? activeReceiverPlayerId : ballHolderPlayerId, activeReceiverPlayerId)
                    : string.Empty;
            var presserPlayerId = !teamHasPossession ? ResolveNearestOutfieldPlayerId(teamSide, ballAnchor) : string.Empty;
            var coverPlayerId = !teamHasPossession ? ResolveCoverPlayerId(teamSide, presserPlayerId, ballAnchor) : string.Empty;
            var markerPlayerId = !teamHasPossession ? ResolveMarkerPlayerId(teamSide, activeReceiverPlayerId, ballAnchor, presserPlayerId, coverPlayerId) : string.Empty;
            for (var index = 0; index < teamPlayers.Length; index += 1)
            {
                var player = teamPlayers[index];
                if (player == null)
                {
                    continue;
                }

                var previousPosition = player.Position;
                var anchor = string.Equals(teamSide, "home", StringComparison.Ordinal)
                    ? HomeAnchors[index]
                    : MirrorAnchor(HomeAnchors[index]);
                var lineWeight = ResolveLineWeight(player.Line);
                var possessionShift = attackDirection * (teamHasPossession ? 1f : -0.38f) * lineWeight * 4.4f;
                var roamX = Mathf.Sin(currentMinute * 0.45f + index * 0.61f) * (player.Role == "GK" ? 0.15f : 0.45f);
                var roamZ = Mathf.Cos(currentMinute * 0.58f + index * 0.47f) * (player.Role == "GK" ? 0.45f : 1.15f);
                var targetPosition = ClampToPitch(anchor + new Vector3(possessionShift + roamX, 0f, roamZ));
                var playerId = player.PlayerId ?? string.Empty;
                var isGoalkeeper = string.Equals(player.Role, "GK", StringComparison.Ordinal);
                var isHolder = !activeTransit.Active && string.Equals(playerId, ballHolderPlayerId, StringComparison.Ordinal);
                var isReceiver = !string.IsNullOrWhiteSpace(activeReceiverPlayerId) && string.Equals(playerId, activeReceiverPlayerId, StringComparison.Ordinal);
                var isSupport = !string.IsNullOrWhiteSpace(supportPlayerId) && string.Equals(playerId, supportPlayerId, StringComparison.Ordinal);
                var isRunner = !string.IsNullOrWhiteSpace(runnerPlayerId) && string.Equals(playerId, runnerPlayerId, StringComparison.Ordinal);
                var isPresser = !string.IsNullOrWhiteSpace(presserPlayerId) && string.Equals(playerId, presserPlayerId, StringComparison.Ordinal);
                var isCover = !string.IsNullOrWhiteSpace(coverPlayerId) && string.Equals(playerId, coverPlayerId, StringComparison.Ordinal);
                var isMarker = !string.IsNullOrWhiteSpace(markerPlayerId) && string.Equals(playerId, markerPlayerId, StringComparison.Ordinal);
                var lerpSpeed = PassivePlayerLerpSpeed;

                if (isGoalkeeper)
                {
                    targetPosition = ResolveGoalkeeperTargetPosition(teamSide, ballAnchor);
                    lerpSpeed = teamHasPossession ? 2.25f : 2.85f;
                }
                else if (isHolder)
                {
                    targetPosition += new Vector3(attackDirection * 2.4f, 0f, Mathf.Sin(currentMinute * 1.1f) * 1.15f);
                    targetPosition = Vector3.Lerp(targetPosition, ballAnchor + new Vector3(attackDirection * 1.8f, 0f, Mathf.Sin(currentMinute * 1.15f) * 1.1f), 0.42f);
                    lerpSpeed = ActivePlayerLerpSpeed;
                }
                else if (isReceiver)
                {
                    var receiveTarget = activeTransit.Active
                        ? activeTransit.End + ResolveForward(player) * 0.45f
                        : ballAnchor + new Vector3(attackDirection * 4.8f, 0f, Mathf.Sign(player.Position.z) * 1.6f);
                    targetPosition = Vector3.Lerp(targetPosition, ClampToPitch(receiveTarget), 0.78f);
                    targetPosition.y = 0f;
                    lerpSpeed = ActivePlayerLerpSpeed;
                }
                else if (teamHasPossession && isSupport)
                {
                    var supportOffset = new Vector3(-attackDirection * 3.6f, 0f, Mathf.Clamp(player.Position.z - ballAnchor.z, -8f, 8f) * 0.55f);
                    targetPosition = Vector3.Lerp(targetPosition, ClampToPitch(ballAnchor + supportOffset), 0.52f);
                    lerpSpeed = 3.05f;
                }
                else if (teamHasPossession && isRunner)
                {
                    var laneZ = Mathf.Clamp(player.Position.z * 1.2f, -PitchWidthMeters * 0.34f, PitchWidthMeters * 0.34f);
                    targetPosition = Vector3.Lerp(targetPosition, ClampToPitch(ballAnchor + new Vector3(attackDirection * 10.5f, 0f, laneZ)), 0.66f);
                    lerpSpeed = 3.35f;
                }
                else if (!teamHasPossession && isPresser)
                {
                    targetPosition = Vector3.Lerp(targetPosition, ClampToPitch(ballAnchor - new Vector3(attackDirection * 0.6f, 0f, 0f)), 0.84f);
                    lerpSpeed = ActivePlayerLerpSpeed;
                }
                else if (!teamHasPossession && isCover)
                {
                    targetPosition = Vector3.Lerp(targetPosition, ResolveDefensiveCoverPosition(teamSide, ballAnchor), 0.62f);
                    lerpSpeed = 3f;
                }
                else if (!teamHasPossession && isMarker)
                {
                    targetPosition = Vector3.Lerp(targetPosition, ResolveMarkingPosition(teamSide, activeReceiverPlayerId, ballAnchor), 0.58f);
                    lerpSpeed = 2.8f;
                }

                player.Position = Vector3.Lerp(previousPosition, ClampToPitch(targetPosition), Mathf.Clamp01(deltaSeconds * lerpSpeed));
                player.Position.y = 0f;
                player.Velocity = (player.Position - previousPosition) / Mathf.Max(deltaSeconds, 0.02f);
                player.HasPossession = !activeTransit.Active && string.Equals(player.PlayerId, ballHolderPlayerId, StringComparison.Ordinal);
                player.SpeedRatio = Mathf.Clamp01(new Vector3(player.Velocity.x, 0f, player.Velocity.z).magnitude / 7.5f);
                player.AnimationState = player.HasPossession
                    ? "dribble"
                    : player.SpeedRatio > (isPresser || isRunner || isReceiver ? 0.4f : 0.66f)
                        ? "run"
                    : player.SpeedRatio > 0.12f
                            ? "jog"
                            : "idle";

                var facingTarget = player.HasPossession
                    ? ResolveGoalMouthTarget(teamSide, false) - player.Position
                    : isReceiver && activeTransit.Active
                        ? activeTransit.End - player.Position
                    : isPresser || isCover || isMarker
                        ? ballAnchor - player.Position
                    : player.Velocity.sqrMagnitude > 0.01f
                        ? player.Velocity
                        : new Vector3(attackDirection, 0f, 0f);
                facingTarget.y = 0f;
                if (facingTarget.sqrMagnitude > 0.0001f)
                {
                    player.Facing = facingTarget.normalized;
                }
            }
        }

        private void UpdateBall(float currentMinute, float deltaSeconds, GtexSimState state)
        {
            var previousPosition = ballState.Position;
            if (activeTransit.Active)
            {
                var elapsedMinutes = Mathf.Max(0f, currentMinute - activeTransit.StartedAtMinute);
                var t = Mathf.Clamp01(elapsedMinutes / Mathf.Max(0.01f, activeTransit.DurationMinutes));
                var position = Vector3.Lerp(activeTransit.Start, activeTransit.End, t);
                position.y += 4f * activeTransit.ArcHeight * t * (1f - t);

                ballState.Position = position;
                ballState.Velocity = (ballState.Position - previousPosition) / Mathf.Max(deltaSeconds, 0.02f);
                ballState.HolderPlayerId = string.Empty;
                ballState.TrajectoryType = activeTransit.TrajectoryType;

                if (t >= 1f)
                {
                    ballHolderPlayerId = activeTransit.PostTransitHolderPlayerId;
                    if (!string.IsNullOrWhiteSpace(activeTransit.PostTransitPossessionSide))
                    {
                        possessionSide = activeTransit.PostTransitPossessionSide;
                    }

                    activeTransit = default;
                    if (!string.IsNullOrWhiteSpace(ballHolderPlayerId))
                    {
                        var holder = FindPlayer(ballHolderPlayerId);
                        if (holder != null)
                        {
                            ballState.Position = holder.Position + ResolveForward(holder) * 0.55f;
                            ballState.Position.y = GtexPlaybackSanitizer.DefaultBallHeight;
                            ballState.HolderPlayerId = holder.PlayerId;
                            ballState.TrajectoryType = "ground";
                        }
                    }
                }

                return;
            }

            if (state == GtexSimState.FullTime)
            {
                ballState.Velocity = Vector3.zero;
                ballState.HolderPlayerId = ballHolderPlayerId;
                ballState.TrajectoryType = "ground";
                return;
            }

            var holderPlayer = FindPlayer(ballHolderPlayerId);
            if (holderPlayer == null)
            {
                ballState.Position = Vector3.Lerp(ballState.Position, new Vector3(0f, GtexPlaybackSanitizer.DefaultBallHeight, 0f), Mathf.Clamp01(deltaSeconds * 3f));
                ballState.Velocity = (ballState.Position - previousPosition) / Mathf.Max(deltaSeconds, 0.02f);
                ballState.HolderPlayerId = string.Empty;
                ballState.TrajectoryType = "ground";
                return;
            }

            var holderOffset = ResolveForward(holderPlayer) * 0.65f;
            var targetPosition = holderPlayer.Position + holderOffset;
            targetPosition.y = GtexPlaybackSanitizer.DefaultBallHeight;
            ballState.Position = Vector3.Lerp(ballState.Position, targetPosition, Mathf.Clamp01(deltaSeconds * 8f));
            ballState.Velocity = (ballState.Position - previousPosition) / Mathf.Max(deltaSeconds, 0.02f);
            ballState.HolderPlayerId = holderPlayer.PlayerId;
            ballState.TrajectoryType = "ground";
        }

        private void UpdateCameraPreset(float currentMinute)
        {
            if (currentCameraPresetUntilMinute < currentMinute)
            {
                currentCameraPreset = "broadcast";
            }

            if (activeEventUntilMinute < currentMinute)
            {
                activeEventId = string.Empty;
            }
        }

        private void RegisterEvent(
            string type,
            float minute,
            string teamSide,
            string commentary,
            int homeScore,
            int awayScore,
            string primaryPlayerId,
            string secondaryPlayerId = null)
        {
            nextEventSequence += 1;
            var gtexEvent = new GtexEvent
            {
                id = "sim-event-" + nextEventSequence,
                type = type ?? string.Empty,
                sequence = nextEventSequence,
                minute = Mathf.FloorToInt(minute),
                clockLabel = minute.ToString("0.0") + "'",
                teamId = teamSide ?? string.Empty,
                teamName = string.IsNullOrWhiteSpace(teamSide) ? string.Empty : teamSide,
                primaryPlayerId = primaryPlayerId ?? string.Empty,
                primaryPlayerName = primaryPlayerId ?? string.Empty,
                secondaryPlayerId = secondaryPlayerId ?? string.Empty,
                secondaryPlayerName = secondaryPlayerId ?? string.Empty,
                homeScore = homeScore,
                awayScore = awayScore,
                bannerText = commentary ?? string.Empty,
                commentary = commentary ?? string.Empty,
                emphasisLevel = ResolveEmphasis(type)
            };

            if (recentEvents.Count >= 8)
            {
                recentEvents.RemoveAt(0);
            }

            recentEvents.Add(gtexEvent);
            activeEventId = gtexEvent.id;
            activeEventUntilMinute = minute + ActiveEventLifetimeMinutes;
        }

        private static int ResolveEmphasis(string type)
        {
            switch ((type ?? string.Empty).Trim().ToLowerInvariant())
            {
                case "goal":
                case "fulltime":
                    return 3;
                case "missed_chance":
                case "red_card":
                    return 2;
                default:
                    return 1;
            }
        }

        private GtexEvent[] BuildRecentEvents()
        {
            if (recentEvents.Count == 0)
            {
                return Array.Empty<GtexEvent>();
            }

            var events = new GtexEvent[recentEvents.Count];
            for (var index = 0; index < recentEvents.Count; index += 1)
            {
                events[index] = recentEvents[index];
            }

            return events;
        }

        private GtexSimSpatialPlayerState[] BuildSnapshotPlayers()
        {
            var snapshotPlayers = new GtexSimSpatialPlayerState[PlayersPerSide * 2];
            var writeIndex = 0;
            for (var index = 0; index < PlayersPerSide; index += 1)
            {
                snapshotPlayers[writeIndex++] = ClonePlayerState(homePlayers[index]);
            }

            for (var index = 0; index < PlayersPerSide; index += 1)
            {
                snapshotPlayers[writeIndex++] = ClonePlayerState(awayPlayers[index]);
            }

            return snapshotPlayers;
        }

        private static GtexSimSpatialPlayerState ClonePlayerState(GtexSimSpatialPlayerState player)
        {
            if (player == null)
            {
                return null;
            }

            return new GtexSimSpatialPlayerState
            {
                EntityId = player.EntityId,
                PlayerId = player.PlayerId,
                TeamSide = player.TeamSide,
                Label = player.Label,
                Role = player.Role,
                Line = player.Line,
                ShirtNumber = player.ShirtNumber,
                HasPossession = player.HasPossession,
                AnimationState = player.AnimationState,
                SpeedRatio = player.SpeedRatio,
                Position = player.Position,
                Velocity = player.Velocity,
                Facing = player.Facing
            };
        }

        private GtexSimSpatialBallState CloneBallState()
        {
            return new GtexSimSpatialBallState
            {
                Position = ballState.Position,
                Velocity = ballState.Velocity,
                HolderPlayerId = ballState.HolderPlayerId,
                TrajectoryType = ballState.TrajectoryType
            };
        }

        private string ResolveRoutinePassTarget(string sourcePlayerId)
        {
            var sourcePlayer = FindPlayer(sourcePlayerId);
            var teamPlayers = ResolveTeamPlayers(sourcePlayer != null ? sourcePlayer.TeamSide : possessionSide);
            if (sourcePlayer == null || teamPlayers == null || teamPlayers.Length == 0)
            {
                return ResolveCentralPlayerId(possessionSide);
            }

            var bestScore = float.NegativeInfinity;
            var bestPlayerId = string.Empty;
            for (var index = 0; index < teamPlayers.Length; index += 1)
            {
                var candidate = teamPlayers[index];
                if (candidate == null || candidate.Role == "GK")
                {
                    continue;
                }

                if (string.Equals(candidate.PlayerId, sourcePlayerId, StringComparison.Ordinal))
                {
                    continue;
                }

                var attackDelta = ResolveAttackAxisDelta(candidate.Position.x - sourcePlayer.Position.x, sourcePlayer.TeamSide);
                var lateralDistance = Mathf.Abs(candidate.Position.z - sourcePlayer.Position.z);
                var directDistance = Vector3.Distance(candidate.Position, sourcePlayer.Position);
                var score = 0f;
                score += string.Equals(candidate.Line, "midfield", StringComparison.Ordinal) ? 3.2f : 0f;
                score += string.Equals(candidate.Line, "attack", StringComparison.Ordinal) ? 2.6f : 0f;
                score += IsWideRole(candidate) ? 0.8f : 0f;
                score += Mathf.Clamp(attackDelta, -6f, 12f) * 0.18f;
                score -= Mathf.Abs(directDistance - 14f) * 0.11f;
                score -= lateralDistance * 0.045f;
                if (attackDelta < -10f)
                {
                    score -= 3.5f;
                }

                if (sourcePlayer != null && string.Equals(sourcePlayer.Role, "GK", StringComparison.Ordinal))
                {
                    score += string.Equals(candidate.Line, "defense", StringComparison.Ordinal) ? 2.4f : 0f;
                    score += string.Equals(candidate.Role, "DM", StringComparison.Ordinal) ? 2.1f : 0f;
                    score -= Mathf.Max(0f, attackDelta - 6f) * 0.2f;
                }

                if (score > bestScore)
                {
                    bestScore = score;
                    bestPlayerId = candidate.PlayerId;
                }
            }

            if (!string.IsNullOrWhiteSpace(bestPlayerId))
            {
                return bestPlayerId;
            }

            return ResolveCentralPlayerId(sourcePlayer != null ? sourcePlayer.TeamSide : possessionSide);
        }

        private string ResolveAttackingPlayerId(string teamSide)
        {
            var teamPlayers = ResolveTeamPlayers(teamSide);
            return teamPlayers != null && teamPlayers.Length > 9 && teamPlayers[9] != null
                ? teamPlayers[9].PlayerId
                : string.Empty;
        }

        private string ResolveCentralPlayerId(string teamSide)
        {
            var teamPlayers = ResolveTeamPlayers(teamSide);
            return teamPlayers != null && teamPlayers.Length > 6 && teamPlayers[6] != null
                ? teamPlayers[6].PlayerId
                : string.Empty;
        }

        private GtexSimSpatialPlayerState[] ResolveTeamPlayers(string teamSide)
        {
            return string.Equals(teamSide, "away", StringComparison.Ordinal) ? awayPlayers : homePlayers;
        }

        private GtexSimSpatialPlayerState FindPlayer(string playerId)
        {
            if (string.IsNullOrWhiteSpace(playerId))
            {
                return null;
            }

            var index = ResolvePlayerIndex(playerId);
            if (index < 0)
            {
                return null;
            }

            return playerId.StartsWith("away-", StringComparison.Ordinal)
                ? awayPlayers[index]
                : homePlayers[index];
        }

        private static int ResolvePlayerIndex(string playerId)
        {
            if (string.IsNullOrWhiteSpace(playerId))
            {
                return -1;
            }

            var separatorIndex = playerId.IndexOf('-');
            if (separatorIndex < 0 || separatorIndex >= playerId.Length - 1)
            {
                return -1;
            }

            return int.TryParse(playerId.Substring(separatorIndex + 1), out var parsedIndex)
                ? Mathf.Clamp(parsedIndex - 1, -1, PlayersPerSide - 1)
                : -1;
        }

        private static Vector3 ResolveGoalMouthTarget(string teamSide, bool missedChance)
        {
            var x = string.Equals(teamSide, "home", StringComparison.Ordinal) ? PitchLengthMeters * 0.5f : -PitchLengthMeters * 0.5f;
            var z = missedChance ? 7.5f : 0f;
            if (string.Equals(teamSide, "away", StringComparison.Ordinal))
            {
                z *= -1f;
            }

            return new Vector3(x, GtexPlaybackSanitizer.DefaultBallHeight, z);
        }

        private static Vector3 ResolveForward(GtexSimSpatialPlayerState player)
        {
            if (player == null)
            {
                return Vector3.forward;
            }

            var facing = player.Facing;
            if (facing.sqrMagnitude <= 0.0001f)
            {
                facing = string.Equals(player.TeamSide, "home", StringComparison.Ordinal) ? Vector3.right : Vector3.left;
            }

            facing.y = 0f;
            return facing.normalized;
        }

        private static float ResolveLineWeight(string line)
        {
            switch ((line ?? string.Empty).Trim().ToLowerInvariant())
            {
                case "goalkeeper":
                    return 0.15f;
                case "defense":
                    return 0.38f;
                case "attack":
                    return 1.15f;
                case "midfield":
                default:
                    return 0.75f;
            }
        }

        private static Vector3 ClampToPitch(Vector3 position)
        {
            position.x = Mathf.Clamp(position.x, -PitchLengthMeters * 0.5f, PitchLengthMeters * 0.5f);
            position.y = Mathf.Max(0f, position.y);
            position.z = Mathf.Clamp(position.z, -PitchWidthMeters * 0.5f, PitchWidthMeters * 0.5f);
            return position;
        }

        private static Vector3 MirrorAnchor(Vector3 anchor)
        {
            return new Vector3(-anchor.x, anchor.y, -anchor.z);
        }

        private static string ResolveTeamSide(GtexSimTeamSide teamSide)
        {
            return teamSide == GtexSimTeamSide.Away ? "away" : "home";
        }

        private Vector3 ResolveBallAnchor(float currentMinute)
        {
            if (activeTransit.Active)
            {
                var elapsedMinutes = Mathf.Max(0f, currentMinute - activeTransit.StartedAtMinute);
                var t = Mathf.Clamp01(elapsedMinutes / Mathf.Max(0.01f, activeTransit.DurationMinutes));
                var anchor = Vector3.Lerp(activeTransit.Start, activeTransit.End, t);
                anchor.y = 0f;
                return ClampToPitch(anchor);
            }

            if (!string.IsNullOrWhiteSpace(ballHolderPlayerId))
            {
                var holder = FindPlayer(ballHolderPlayerId);
                if (holder != null)
                {
                    var holderAnchor = holder.Position + ResolveForward(holder) * 0.55f;
                    holderAnchor.y = 0f;
                    return ClampToPitch(holderAnchor);
                }
            }

            var fallback = ballState.Position;
            fallback.y = 0f;
            return ClampToPitch(fallback);
        }

        private float ResolveRoutinePassDuration(GtexSimSpatialPlayerState sourcePlayer, GtexSimSpatialPlayerState targetPlayer, Vector3 targetPosition)
        {
            var startPosition = sourcePlayer != null ? sourcePlayer.Position : Vector3.zero;
            var distance = Vector3.Distance(startPosition, targetPosition);
            return Mathf.Clamp(0.08f + distance / 250f, 0.09f, 0.15f);
        }

        private float ResolveRoutinePassArcHeight(GtexSimSpatialPlayerState sourcePlayer, GtexSimSpatialPlayerState targetPlayer, Vector3 targetPosition)
        {
            var startPosition = sourcePlayer != null ? sourcePlayer.Position : Vector3.zero;
            var distance = Vector3.Distance(startPosition, targetPosition);
            if (sourcePlayer != null && string.Equals(sourcePlayer.Role, "GK", StringComparison.Ordinal))
            {
                return GoalkeeperDistributionArcHeight;
            }

            if (distance > 26f || (targetPlayer != null && IsWideRole(targetPlayer)))
            {
                return LoftedPassArcHeight;
            }

            return GroundPassArcHeight;
        }

        private string ResolveSupportPlayerId(string teamSide, string sourcePlayerId, string receiverPlayerId)
        {
            var sourcePlayer = FindPlayer(sourcePlayerId);
            var teamPlayers = ResolveTeamPlayers(teamSide);
            if (sourcePlayer == null || teamPlayers == null)
            {
                return string.Empty;
            }

            var bestScore = float.NegativeInfinity;
            var bestPlayerId = string.Empty;
            for (var index = 0; index < teamPlayers.Length; index += 1)
            {
                var candidate = teamPlayers[index];
                if (candidate == null ||
                    string.Equals(candidate.Role, "GK", StringComparison.Ordinal) ||
                    string.Equals(candidate.PlayerId, sourcePlayerId, StringComparison.Ordinal) ||
                    string.Equals(candidate.PlayerId, receiverPlayerId, StringComparison.Ordinal))
                {
                    continue;
                }

                var attackDelta = ResolveAttackAxisDelta(candidate.Position.x - sourcePlayer.Position.x, teamSide);
                var distance = Vector3.Distance(candidate.Position, sourcePlayer.Position);
                var lateralDistance = Mathf.Abs(candidate.Position.z - sourcePlayer.Position.z);
                var score = 0f;
                score += string.Equals(candidate.Line, "midfield", StringComparison.Ordinal) ? 3.1f : 0f;
                score += string.Equals(candidate.Line, "defense", StringComparison.Ordinal) ? 1.8f : 0f;
                score += attackDelta > -9f && attackDelta < 8f ? 1.9f : 0f;
                score -= Mathf.Abs(distance - 10f) * 0.13f;
                score -= lateralDistance * 0.06f;
                if (score > bestScore)
                {
                    bestScore = score;
                    bestPlayerId = candidate.PlayerId;
                }
            }

            return bestPlayerId;
        }

        private string ResolveRunnerPlayerId(string teamSide, string sourcePlayerId, string receiverPlayerId)
        {
            var sourcePlayer = FindPlayer(sourcePlayerId);
            var teamPlayers = ResolveTeamPlayers(teamSide);
            if (sourcePlayer == null || teamPlayers == null)
            {
                return string.Empty;
            }

            var bestScore = float.NegativeInfinity;
            var bestPlayerId = string.Empty;
            for (var index = 0; index < teamPlayers.Length; index += 1)
            {
                var candidate = teamPlayers[index];
                if (candidate == null ||
                    string.Equals(candidate.Role, "GK", StringComparison.Ordinal) ||
                    string.Equals(candidate.PlayerId, sourcePlayerId, StringComparison.Ordinal) ||
                    string.Equals(candidate.PlayerId, receiverPlayerId, StringComparison.Ordinal))
                {
                    continue;
                }

                var attackDelta = ResolveAttackAxisDelta(candidate.Position.x - sourcePlayer.Position.x, teamSide);
                var score = 0f;
                score += string.Equals(candidate.Line, "attack", StringComparison.Ordinal) ? 3.4f : 0f;
                score += IsWideRole(candidate) ? 1.2f : 0f;
                score += Mathf.Clamp(attackDelta, 0f, 18f) * 0.18f;
                score -= Mathf.Abs(candidate.Position.z) * 0.02f;
                if (attackDelta < 2f)
                {
                    score -= 2.5f;
                }

                if (score > bestScore)
                {
                    bestScore = score;
                    bestPlayerId = candidate.PlayerId;
                }
            }

            return bestPlayerId;
        }

        private string ResolveNearestOutfieldPlayerId(string teamSide, Vector3 targetPosition)
        {
            var teamPlayers = ResolveTeamPlayers(teamSide);
            if (teamPlayers == null)
            {
                return string.Empty;
            }

            var bestDistance = float.MaxValue;
            var bestPlayerId = string.Empty;
            for (var index = 0; index < teamPlayers.Length; index += 1)
            {
                var candidate = teamPlayers[index];
                if (candidate == null || string.Equals(candidate.Role, "GK", StringComparison.Ordinal))
                {
                    continue;
                }

                var distance = Vector3.Distance(candidate.Position, targetPosition);
                if (distance < bestDistance)
                {
                    bestDistance = distance;
                    bestPlayerId = candidate.PlayerId;
                }
            }

            return bestPlayerId;
        }

        private string ResolveCoverPlayerId(string teamSide, string presserPlayerId, Vector3 ballAnchor)
        {
            var teamPlayers = ResolveTeamPlayers(teamSide);
            if (teamPlayers == null)
            {
                return string.Empty;
            }

            var coverPosition = ResolveDefensiveCoverPosition(teamSide, ballAnchor);
            var bestDistance = float.MaxValue;
            var bestPlayerId = string.Empty;
            for (var index = 0; index < teamPlayers.Length; index += 1)
            {
                var candidate = teamPlayers[index];
                if (candidate == null ||
                    string.Equals(candidate.Role, "GK", StringComparison.Ordinal) ||
                    string.Equals(candidate.PlayerId, presserPlayerId, StringComparison.Ordinal))
                {
                    continue;
                }

                if (!string.Equals(candidate.Line, "defense", StringComparison.Ordinal) &&
                    !string.Equals(candidate.Role, "DM", StringComparison.Ordinal))
                {
                    continue;
                }

                var distance = Vector3.Distance(candidate.Position, coverPosition);
                if (distance < bestDistance)
                {
                    bestDistance = distance;
                    bestPlayerId = candidate.PlayerId;
                }
            }

            return bestPlayerId;
        }

        private string ResolveMarkerPlayerId(
            string teamSide,
            string threatPlayerId,
            Vector3 ballAnchor,
            string presserPlayerId,
            string coverPlayerId)
        {
            var threatPlayer = FindPlayer(threatPlayerId);
            var referencePosition = threatPlayer != null ? threatPlayer.Position : ballAnchor;
            var teamPlayers = ResolveTeamPlayers(teamSide);
            if (teamPlayers == null)
            {
                return string.Empty;
            }

            var bestDistance = float.MaxValue;
            var bestPlayerId = string.Empty;
            for (var index = 0; index < teamPlayers.Length; index += 1)
            {
                var candidate = teamPlayers[index];
                if (candidate == null ||
                    string.Equals(candidate.Role, "GK", StringComparison.Ordinal) ||
                    string.Equals(candidate.PlayerId, presserPlayerId, StringComparison.Ordinal) ||
                    string.Equals(candidate.PlayerId, coverPlayerId, StringComparison.Ordinal))
                {
                    continue;
                }

                if (!string.Equals(candidate.Line, "defense", StringComparison.Ordinal) &&
                    !string.Equals(candidate.Line, "midfield", StringComparison.Ordinal))
                {
                    continue;
                }

                var distance = Vector3.Distance(candidate.Position, referencePosition);
                if (distance < bestDistance)
                {
                    bestDistance = distance;
                    bestPlayerId = candidate.PlayerId;
                }
            }

            return bestPlayerId;
        }

        private static Vector3 ResolveGoalkeeperTargetPosition(string teamSide, Vector3 ballAnchor)
        {
            var goalX = string.Equals(teamSide, "home", StringComparison.Ordinal)
                ? -PitchLengthMeters * 0.5f + 4.9f
                : PitchLengthMeters * 0.5f - 4.9f;
            var zClamp = Mathf.Clamp(ballAnchor.z * 0.28f, -PitchWidthMeters * 0.18f, PitchWidthMeters * 0.18f);
            var xStep = Mathf.Clamp(Mathf.Abs(ballAnchor.x) * 0.02f, 0.35f, 1.65f);
            goalX += string.Equals(teamSide, "home", StringComparison.Ordinal) ? xStep : -xStep;
            return ClampToPitch(new Vector3(goalX, 0f, zClamp));
        }

        private static Vector3 ResolveDefensiveCoverPosition(string teamSide, Vector3 ballAnchor)
        {
            var goalCenter = string.Equals(teamSide, "home", StringComparison.Ordinal)
                ? new Vector3(-PitchLengthMeters * 0.5f + 7.2f, 0f, 0f)
                : new Vector3(PitchLengthMeters * 0.5f - 7.2f, 0f, 0f);
            var cover = Vector3.Lerp(goalCenter, ballAnchor, 0.38f);
            cover.z = Mathf.Clamp(cover.z, -PitchWidthMeters * 0.28f, PitchWidthMeters * 0.28f);
            return ClampToPitch(cover);
        }

        private Vector3 ResolveMarkingPosition(string teamSide, string threatPlayerId, Vector3 ballAnchor)
        {
            var threatPlayer = FindPlayer(threatPlayerId);
            if (threatPlayer == null)
            {
                return ResolveDefensiveCoverPosition(teamSide, ballAnchor);
            }

            var goalCenter = string.Equals(teamSide, "home", StringComparison.Ordinal)
                ? new Vector3(-PitchLengthMeters * 0.5f + 9.5f, 0f, 0f)
                : new Vector3(PitchLengthMeters * 0.5f - 9.5f, 0f, 0f);
            return ClampToPitch(Vector3.Lerp(goalCenter, threatPlayer.Position, 0.62f));
        }

        private static float ResolveAttackAxisDelta(float deltaX, string teamSide)
        {
            return string.Equals(teamSide, "away", StringComparison.Ordinal) ? -deltaX : deltaX;
        }

        private static bool IsWideRole(GtexSimSpatialPlayerState player)
        {
            if (player == null || string.IsNullOrWhiteSpace(player.Role))
            {
                return false;
            }

            return
                string.Equals(player.Role, "RW", StringComparison.Ordinal) ||
                string.Equals(player.Role, "LW", StringComparison.Ordinal) ||
                string.Equals(player.Role, "RB", StringComparison.Ordinal) ||
                string.Equals(player.Role, "LB", StringComparison.Ordinal);
        }

        private static string ResolvePhaseToken(GtexSimState state)
        {
            switch (state)
            {
                case GtexSimState.FirstHalf:
                    return "first_half";
                case GtexSimState.HalfTime:
                    return "halftime";
                case GtexSimState.SecondHalf:
                    return "second_half";
                case GtexSimState.FullTime:
                    return "fulltime";
                case GtexSimState.Kickoff:
                default:
                    return "kickoff";
            }
        }

        private static float ResolveRealSecondsPerMatchMinute(GtexMatchConfig matchConfig)
        {
            var targetDurationMinutes = matchConfig != null ? Mathf.Max(1f, matchConfig.simulationTargetDurationMinutes) : 15f;
            return (targetDurationMinutes * 60f) / 90f;
        }
    }
}
