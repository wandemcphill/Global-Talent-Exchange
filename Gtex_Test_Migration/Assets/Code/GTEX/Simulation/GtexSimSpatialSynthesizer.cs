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
        private const float RoutinePassIntervalMinutes = 0.85f;
        private const float RoutinePassDurationMinutes = 0.12f;
        private const float ShotDurationMinutes = 0.18f;
        private const float GoalResetDelayMinutes = 0.2f;

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
                    currentCameraPreset = "box_zoom";
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
                    currentCameraPreset = "box_zoom";
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
                    currentCameraPreset = "box_zoom";
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
                    currentCameraPreset = "box_zoom";
                    currentCameraPresetUntilMinute = currentMinute + 0.18f;
                }
            }

            if (!activeTransit.Active &&
                currentMinute >= nextRoutinePassMinute &&
                !string.Equals(ResolvePhaseToken(engine.State), "fulltime", StringComparison.Ordinal))
            {
                StartRoutinePass(currentMinute);
            }
        }

        private void StartRoutinePass(float currentMinute)
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

            StartTransit(
                sourcePlayerId,
                FindPlayer(targetPlayerId)?.Position ?? Vector3.zero,
                currentMinute,
                RoutinePassDurationMinutes,
                0.5f,
                "pass",
                targetPlayerId,
                possessionSide);
            currentCameraPreset = "attack_push";
            currentCameraPresetUntilMinute = currentMinute + 0.14f;
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
                ArcHeight = Mathf.Max(0.2f, arcHeight),
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
                var possessionShift = attackDirection * (teamHasPossession ? 1f : -0.65f) * lineWeight * 7f;
                var roamX = Mathf.Sin(currentMinute * 0.55f + index * 0.61f) * (player.Role == "GK" ? 0.6f : 1.9f);
                var roamZ = Mathf.Cos(currentMinute * 0.72f + index * 0.47f) * (player.Role == "GK" ? 1.2f : 3.4f);
                var targetPosition = ClampToPitch(anchor + new Vector3(possessionShift + roamX, 0f, roamZ));

                if (string.Equals(player.PlayerId, ballHolderPlayerId, StringComparison.Ordinal))
                {
                    targetPosition += new Vector3(attackDirection * 2.4f, 0f, Mathf.Sin(currentMinute * 1.1f) * 1.15f);
                }
                else if (activeTransit.Active && !string.IsNullOrWhiteSpace(activeTransit.PostTransitHolderPlayerId) &&
                         string.Equals(player.PlayerId, activeTransit.PostTransitHolderPlayerId, StringComparison.Ordinal))
                {
                    targetPosition = Vector3.Lerp(targetPosition, activeTransit.End, 0.35f);
                    targetPosition.y = 0f;
                }

                player.Position = Vector3.Lerp(previousPosition, ClampToPitch(targetPosition), Mathf.Clamp01(deltaSeconds * 3.1f));
                player.Position.y = 0f;
                player.Velocity = (player.Position - previousPosition) / Mathf.Max(deltaSeconds, 0.02f);
                player.HasPossession = !activeTransit.Active && string.Equals(player.PlayerId, ballHolderPlayerId, StringComparison.Ordinal);
                player.SpeedRatio = Mathf.Clamp01(new Vector3(player.Velocity.x, 0f, player.Velocity.z).magnitude / 7.5f);
                player.AnimationState = player.HasPossession
                    ? "dribble"
                    : player.SpeedRatio > 0.72f
                        ? "run"
                        : player.SpeedRatio > 0.12f
                            ? "jog"
                            : "idle";

                var facingTarget = player.HasPossession
                    ? ResolveGoalMouthTarget(teamSide, false) - player.Position
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

        private void RegisterEvent(string type, float minute, string teamSide, string commentary, int homeScore, int awayScore, string primaryPlayerId)
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
            if (teamPlayers == null || teamPlayers.Length == 0)
            {
                return string.Empty;
            }

            var sourceIndex = ResolvePlayerIndex(sourcePlayerId);
            for (var offset = 1; offset < teamPlayers.Length; offset += 1)
            {
                var candidateIndex = (sourceIndex + offset) % teamPlayers.Length;
                var candidate = teamPlayers[candidateIndex];
                if (candidate == null || candidate.Role == "GK")
                {
                    continue;
                }

                if (!string.Equals(candidate.PlayerId, sourcePlayerId, StringComparison.Ordinal))
                {
                    return candidate.PlayerId;
                }
            }

            return teamPlayers[0] != null ? teamPlayers[0].PlayerId : string.Empty;
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
