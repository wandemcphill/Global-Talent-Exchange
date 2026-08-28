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
        private const float ShotDurationMinutes = 0.14f;
        private const float GoalResetDelayMinutes = 0.28f;
        private const float PassivePlayerLerpSpeed = 2.15f;
        private const float ActivePlayerLerpSpeed = 4.55f;
        private const float GroundPassArcHeight = 0.04f;
        private const float LoftedPassArcHeight = 0.24f;
        private const float GoalkeeperDistributionArcHeight = 0.18f;
        private const float DecisionMinGapMinutes = 0.16f;
        private const float DecisionMaxGapMinutes = 0.72f;
        private const float FirstTouchSettleMinutes = 0.11f;
        private const float DribbleMinMinutes = 0.13f;
        private const float DribbleMaxMinutes = 0.32f;
        private const float PossessionContestRadius = 3.2f;

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

        private struct DecisionPlan
        {
            public int Sequence;
            public string Action;
            public string SourcePlayerId;
            public string ReceiverPlayerId;
            public Vector3 TargetPosition;
            public float Quality;
            public float Pressure;
            public float Space;
            public float Risk;
            public float ExecuteAtMinute;
            public float ExpiresAtMinute;
            public bool Active;
        }

        private struct BallTransit
        {
            public bool Active;
            public Vector3 Start;
            public Vector3 End;
            public float StartedAtMinute;
            public float DurationMinutes;
            public float ArcHeight;
            public string PostTransitHolderPlayerId;
            public string PostTransitPossessionSide;
            public string TrajectoryType;
        }

        private readonly GtexSimSpatialPlayerState[] homePlayers = new GtexSimSpatialPlayerState[PlayersPerSide];
        private readonly GtexSimSpatialPlayerState[] awayPlayers = new GtexSimSpatialPlayerState[PlayersPerSide];
        private readonly List<GtexEvent> recentEvents = new();
        private readonly System.Random decisionRandom = new(9731);

        private bool initialized;
        private string possessionSide = "home";
        private string ballHolderPlayerId = "home-8";
        private string activeEventId = string.Empty;
        private string currentCameraPreset = "broadcast";
        private float currentCameraPresetUntilMinute = -1f;
        private float activeEventUntilMinute = -1f;
        private float nextDecisionMinute = 0.42f;
        private float firstTouchSettleUntilMinute = -1f;
        private float dribbleUntilMinute = -1f;
        private string dribblePlayerId = string.Empty;
        private float lastClockMinute = -1f;
        private int processedEventCount;
        private int nextEventSequence;
        private int nextDecisionSequence;
        private GtexSimState lastState = GtexSimState.Kickoff;
        private DecisionPlan currentDecision;
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
            if (!initialized || currentMinute + 0.01f < lastClockMinute ||
                (currentMinute <= 0.01f && lastState == GtexSimState.FullTime))
            {
                Reset();
            }

            var realSecondsPerMatchMinute = ResolveRealSecondsPerMatchMinute(matchConfig);
            var deltaMatchMinutes = lastClockMinute >= 0f ? Mathf.Max(0f, currentMinute - lastClockMinute) : 0.05f;
            var deltaSeconds = Mathf.Max(0.02f, deltaMatchMinutes * realSecondsPerMatchMinute);

            HandleStateTransition(engine.State, currentMinute, engine.HomeScore, engine.AwayScore);
            ConsumeNewEvents(engine, currentMinute);
            AdvanceDecisionCycle(currentMinute, engine.State);
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
            nextDecisionMinute = 0.42f;
            firstTouchSettleUntilMinute = -1f;
            dribbleUntilMinute = -1f;
            dribblePlayerId = string.Empty;
            lastClockMinute = -1f;
            processedEventCount = 0;
            nextEventSequence = 0;
            nextDecisionSequence = 0;
            lastState = GtexSimState.Kickoff;
            currentDecision = default;
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
                    RegisterEvent("halftime", currentMinute, string.Empty, "Half-time whistle.", homeScore, awayScore, string.Empty);
                    currentCameraPreset = "broadcast";
                    currentCameraPresetUntilMinute = currentMinute + 0.2f;
                    currentDecision = default;
                    activeTransit = default;
                    break;
                case GtexSimState.SecondHalf:
                    ballHolderPlayerId = "away-8";
                    possessionSide = "away";
                    firstTouchSettleUntilMinute = currentMinute + FirstTouchSettleMinutes;
                    nextDecisionMinute = currentMinute + 0.35f;
                    currentDecision = default;
                    break;
                case GtexSimState.FullTime:
                    RegisterEvent("fulltime", currentMinute, string.Empty, "Full-time whistle.", homeScore, awayScore, string.Empty);
                    currentCameraPreset = "broadcast";
                    currentCameraPresetUntilMinute = currentMinute + 0.35f;
                    currentDecision = default;
                    activeTransit = default;
                    dribbleUntilMinute = -1f;
                    dribblePlayerId = string.Empty;
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
                    var sourcePlayerId = ResolveGoalSourcePlayerId(attackingSide);
                    var restartSide = OppositeSide(attackingSide);
                    RegisterEvent("goal", currentMinute, attackingSide, goalEvent.Summary, goalEvent.HomeScore, goalEvent.AwayScore, sourcePlayerId);
                    StartTransit(sourcePlayerId, ResolveGoalMouthTarget(attackingSide, false), currentMinute, ShotDurationMinutes, 1.3f, "shot", restartSide + "-8", restartSide);
                    nextDecisionMinute = currentMinute + GoalResetDelayMinutes;
                    currentCameraPreset = "broadcast";
                    currentCameraPresetUntilMinute = currentMinute + 0.28f;
                    currentDecision = default;
                    dribbleUntilMinute = -1f;
                    dribblePlayerId = string.Empty;
                    continue;
                }

                if (matchEvent is GtexMissedChanceEvent missedChanceEvent)
                {
                    var attackingSide = ResolveTeamSide(missedChanceEvent.Team);
                    var recoveringSide = OppositeSide(attackingSide);
                    var sourcePlayerId = ResolveGoalSourcePlayerId(attackingSide);
                    RegisterEvent("missed_chance", currentMinute, attackingSide, missedChanceEvent.Summary, engine.HomeScore, engine.AwayScore, sourcePlayerId);
                    StartTransit(sourcePlayerId, ResolveGoalMouthTarget(attackingSide, true), currentMinute, ShotDurationMinutes, 1.05f, "shot", recoveringSide + "-1", recoveringSide);
                    nextDecisionMinute = currentMinute + 0.42f;
                    currentCameraPreset = "broadcast";
                    currentCameraPresetUntilMinute = currentMinute + 0.22f;
                    currentDecision = default;
                    dribbleUntilMinute = -1f;
                    dribblePlayerId = string.Empty;
                    continue;
                }

                if (matchEvent is GtexFoulEvent foulEvent)
                {
                    var fouledTeamSide = ResolveTeamSide(foulEvent.Team);
                    var restartSide = OppositeSide(fouledTeamSide);
                    ballHolderPlayerId = restartSide + "-6";
                    possessionSide = restartSide;
                    firstTouchSettleUntilMinute = currentMinute + FirstTouchSettleMinutes * 1.4f;
                    nextDecisionMinute = currentMinute + 0.3f;
                    currentDecision = default;
                    activeTransit = default;
                    dribbleUntilMinute = -1f;
                    dribblePlayerId = string.Empty;
                    RegisterEvent("foul", currentMinute, fouledTeamSide, foulEvent.Summary, engine.HomeScore, engine.AwayScore, ballHolderPlayerId);
                    currentCameraPreset = "broadcast";
                    currentCameraPresetUntilMinute = currentMinute + 0.18f;
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
        }

        private void AdvanceDecisionCycle(float currentMinute, GtexSimState currentState)
        {
            if (currentState == GtexSimState.HalfTime || currentState == GtexSimState.FullTime)
            {
                return;
            }

            if (activeTransit.Active || currentMinute < firstTouchSettleUntilMinute)
            {
                return;
            }

            if (!string.IsNullOrWhiteSpace(dribblePlayerId) && dribbleUntilMinute >= currentMinute)
            {
                return;
            }

            if (currentDecision.Active)
            {
                if (currentMinute >= currentDecision.ExecuteAtMinute)
                {
                    ApplyDecisionPlan(currentDecision, currentMinute);
                }
                return;
            }

            if (currentMinute < nextDecisionMinute || string.IsNullOrWhiteSpace(ballHolderPlayerId))
            {
                return;
            }

            var source = FindPlayer(ballHolderPlayerId);
            if (source == null)
            {
                nextDecisionMinute = currentMinute + DecisionMinGapMinutes;
                return;
            }

            currentDecision = BuildDecisionPlan(source, currentMinute);
            if (currentDecision.Active && currentMinute >= currentDecision.ExecuteAtMinute)
            {
                ApplyDecisionPlan(currentDecision, currentMinute);
            }
        }

        private DecisionPlan BuildDecisionPlan(GtexSimSpatialPlayerState sourcePlayer, float currentMinute)
        {
            var teamSide = sourcePlayer.TeamSide;
            var opponentSide = OppositeSide(teamSide);
            var opponents = ResolveTeamPlayers(opponentSide);
            var pressure = ResolvePressure(sourcePlayer, opponents);
            var candidates = CollectReceiverCandidates(sourcePlayer, teamSide);

            var bestReceiver = string.Empty;
            var bestTarget = sourcePlayer.Position;
            var bestQuality = float.NegativeInfinity;
            var bestSpace = 0f;
            var bestRisk = 1f;

            for (var index = 0; index < candidates.Count; index += 1)
            {
                var candidate = candidates[index];
                var quality = ScoreReceiver(sourcePlayer, candidate, opponents, pressure, out var target, out var space, out var risk);
                if (quality > bestQuality)
                {
                    bestQuality = quality;
                    bestReceiver = candidate.PlayerId;
                    bestTarget = target;
                    bestSpace = space;
                    bestRisk = risk;
                }
            }

            var forwardValue = ResolveAttackAxisDelta(bestTarget.x - sourcePlayer.Position.x, sourcePlayer.TeamSide);
            var distanceToGoal = DistanceToOpposingGoal(sourcePlayer.TeamSide, sourcePlayer.Position);
            var closeEnoughToCarry = pressure < 0.48f && forwardValue > 2.2f;
            var underImmediatePressure = pressure > 0.72f;
            var strongPassWindow = !string.IsNullOrWhiteSpace(bestReceiver) && bestQuality > 0.62f;
            var shotCorridor = distanceToGoal < 19f && pressure < 0.64f && SpaceToGoal(sourcePlayer, opponents) > 0.56f;

            string action;
            if (underImmediatePressure && strongPassWindow)
            {
                action = "pass";
            }
            else if (shotCorridor)
            {
                action = "carry";
            }
            else if (closeEnoughToCarry && !strongPassWindow)
            {
                action = "carry";
            }
            else if (strongPassWindow)
            {
                action = "pass";
            }
            else
            {
                action = "hold";
            }

            var persistence = action == "pass" ? 0.42f : action == "carry" ? 0.66f : 0.28f;
            var executeDelay = action == "pass"
                ? Mathf.Lerp(0.045f, 0.16f, Mathf.Clamp01(pressure * 0.7f + bestRisk * 0.25f))
                : action == "carry"
                    ? Mathf.Lerp(0.10f, 0.24f, pressure)
                    : Mathf.Lerp(0.16f, 0.32f, pressure);

            return new DecisionPlan
            {
                Sequence = ++nextDecisionSequence,
                Action = action,
                SourcePlayerId = sourcePlayer.PlayerId,
                ReceiverPlayerId = bestReceiver,
                TargetPosition = bestTarget,
                Quality = Mathf.Clamp01((bestQuality + 1f) * 0.5f),
                Pressure = pressure,
                Space = bestSpace,
                Risk = bestRisk,
                ExecuteAtMinute = currentMinute + executeDelay,
                ExpiresAtMinute = currentMinute + Mathf.Lerp(DecisionMinGapMinutes, DecisionMaxGapMinutes, persistence),
                Active = true
            };
        }

        private void ApplyDecisionPlan(DecisionPlan plan, float currentMinute)
        {
            if (!plan.Active || string.IsNullOrWhiteSpace(plan.SourcePlayerId))
            {
                currentDecision = default;
                nextDecisionMinute = currentMinute + DecisionMinGapMinutes;
                return;
            }

            var source = FindPlayer(plan.SourcePlayerId);
            if (source == null || !string.Equals(source.PlayerId, ballHolderPlayerId, StringComparison.Ordinal))
            {
                currentDecision = default;
                nextDecisionMinute = currentMinute + DecisionMinGapMinutes;
                return;
            }

            if (plan.Action == "pass" && !string.IsNullOrWhiteSpace(plan.ReceiverPlayerId))
            {
                var receiver = FindPlayer(plan.ReceiverPlayerId);
                if (receiver != null)
                {
                    var contestRisk = ResolveReceiverContestRisk(receiver, ResolveTeamPlayers(OppositeSide(source.TeamSide)));
                    var contestOutcome = EvaluatePossessionContest(plan.Sequence, contestRisk);
                    var target = ClampToPitch(plan.TargetPosition);
                    if (!contestOutcome.Success)
                    {
                        target = ResolveInterceptPoint(source, receiver, contestOutcome.Defender);
                        RegisterEvent("interception", currentMinute, OppositeSide(source.TeamSide), "Pass intercepted.", 0, 0, contestOutcome.Defender, source.PlayerId);
                        StartTransit(source.PlayerId, target, currentMinute, ResolvePassDuration(source, target), ResolvePassArcHeight(source, receiver, target), "pass", contestOutcome.Defender, OppositeSide(source.TeamSide));
                        nextDecisionMinute = currentMinute + 0.18f;
                        currentDecision = default;
                        return;
                    }

                    RegisterEvent("pass", currentMinute, source.TeamSide, "Pass into space.", 0, 0, source.PlayerId, receiver.PlayerId);
                    StartTransit(source.PlayerId, target, currentMinute, ResolvePassDuration(source, target), ResolvePassArcHeight(source, receiver, target), "pass", receiver.PlayerId, source.TeamSide);
                    firstTouchSettleUntilMinute = currentMinute + FirstTouchSettleMinutes;
                    currentDecision = default;
                    nextDecisionMinute = currentMinute + DecisionMinGapMinutes;
                    currentCameraPreset = "broadcast";
                    currentCameraPresetUntilMinute = currentMinute + 0.14f;
                    return;
                }
            }

            if (plan.Action == "carry")
            {
                dribblePlayerId = source.PlayerId;
                dribbleUntilMinute = currentMinute + Mathf.Lerp(DribbleMinMinutes, DribbleMaxMinutes, Mathf.Clamp01(plan.Space + (1f - plan.Pressure) * 0.5f));
                nextDecisionMinute = dribbleUntilMinute;
                RegisterEvent("carry", currentMinute, source.TeamSide, "Carries through space.", 0, 0, source.PlayerId);
                currentDecision = default;
                return;
            }

            nextDecisionMinute = Mathf.Max(currentMinute + DecisionMinGapMinutes, plan.ExpiresAtMinute);
            currentDecision = default;
        }

        private List<GtexSimSpatialPlayerState> CollectReceiverCandidates(GtexSimSpatialPlayerState sourcePlayer, string teamSide)
        {
            var candidates = new List<GtexSimSpatialPlayerState>();
            var teamPlayers = ResolveTeamPlayers(teamSide);
            if (teamPlayers == null)
            {
                return candidates;
            }

            for (var index = 0; index < teamPlayers.Length; index += 1)
            {
                var candidate = teamPlayers[index];
                if (candidate == null ||
                    string.Equals(candidate.PlayerId, sourcePlayer.PlayerId, StringComparison.Ordinal) ||
                    string.Equals(candidate.Role, "GK", StringComparison.Ordinal))
                {
                    continue;
                }

                var distance = Vector3.Distance(sourcePlayer.Position, candidate.Position);
                if (distance <= 7f || distance >= 34f)
                {
                    continue;
                }

                candidates.Add(candidate);
            }

            return candidates;
        }

        private float ScoreReceiver(
            GtexSimSpatialPlayerState source,
            GtexSimSpatialPlayerState receiver,
            GtexSimSpatialPlayerState[] opponents,
            float sourcePressure,
            out Vector3 target,
            out float space,
            out float risk)
        {
            var attackDirection = source.TeamSide == "home" ? Vector3.right : Vector3.left;
            var lead = Mathf.Clamp(1.1f + receiver.SpeedRatio * 3.5f + sourcePressure * 1.6f, 1f, 5.2f);
            var forwardBias = string.Equals(receiver.Line, "attack", StringComparison.Ordinal) ? 1.35f :
                string.Equals(receiver.Line, "midfield", StringComparison.Ordinal) ? 0.7f : 0.2f;
            var laneBias = IsWideRole(receiver) ? 0.55f : 0.18f;
            target = receiver.Position + attackDirection * (0.45f + forwardBias + lead * 0.15f);
            target += new Vector3(0f, 0f, Mathf.Sign(receiver.Position.z) * laneBias);
            target = ClampToPitch(target);

            space = ResolveSpaceScore(receiver, opponents, target);
            risk = ResolvePassRisk(source, receiver, opponents, target);
            var distance = Vector3.Distance(source.Position, target);
            var distanceQuality = 1f - Mathf.Clamp01(Mathf.Abs(distance - 15f) / 18f);
            var forwardGain = ResolveAttackAxisDelta(target.x - source.Position.x, source.TeamSide);
            var forwardQuality = Mathf.Clamp01((forwardGain + 6f) / 22f);
            var roleQuality = string.Equals(receiver.Line, "attack", StringComparison.Ordinal) ? 0.88f :
                string.Equals(receiver.Line, "midfield", StringComparison.Ordinal) ? 0.76f : 0.58f;
            var pressurePenalty = Mathf.Clamp01(sourcePressure) * 0.24f;
            return distanceQuality * 0.23f +
                   forwardQuality * 0.22f +
                   space * 0.30f +
                   roleQuality * 0.13f +
                   laneBias * 0.04f -
                   risk * 0.26f -
                   pressurePenalty;
        }

        private float ResolvePressure(GtexSimSpatialPlayerState player, GtexSimSpatialPlayerState[] opponents)
        {
            if (player == null || opponents == null || opponents.Length == 0)
            {
                return 0f;
            }

            var nearest = float.MaxValue;
            var second = float.MaxValue;
            for (var index = 0; index < opponents.Length; index += 1)
            {
                var opponent = opponents[index];
                if (opponent == null || opponent.Role == "GK")
                {
                    continue;
                }

                var distance = Vector3.Distance(player.Position, opponent.Position);
                if (distance < nearest)
                {
                    second = nearest;
                    nearest = distance;
                }
                else if (distance < second)
                {
                    second = distance;
                }
            }

            var nearestPressure = nearest == float.MaxValue ? 0f : 1f - Mathf.Clamp01((nearest - 1.5f) / 8.5f);
            var secondPressure = second == float.MaxValue ? 0f : 1f - Mathf.Clamp01((second - 2.5f) / 10f);
            return Mathf.Clamp01(nearestPressure * 0.72f + secondPressure * 0.28f);
        }

        private float ResolveSpaceScore(GtexSimSpatialPlayerState receiver, GtexSimSpatialPlayerState[] opponents, Vector3 target)
        {
            if (receiver == null || opponents == null)
            {
                return 0.5f;
            }

            var nearest = float.MaxValue;
            var countWithinSix = 0;
            for (var index = 0; index < opponents.Length; index += 1)
            {
                var opponent = opponents[index];
                if (opponent == null)
                {
                    continue;
                }

                var distance = Vector3.Distance(opponent.Position, target);
                nearest = Mathf.Min(nearest, distance);
                if (distance < 6f)
                {
                    countWithinSix += 1;
                }
            }

            var nearestScore = nearest == float.MaxValue ? 1f : Mathf.Clamp01((nearest - 2.5f) / 10.5f);
            var crowdPenalty = Mathf.Clamp01(countWithinSix / 4f);
            var widthBonus = Mathf.Clamp01(Mathf.Abs(receiver.Position.z) / (PitchWidthMeters * 0.5f)) * 0.2f;
            return Mathf.Clamp01(nearestScore * 0.75f + (1f - crowdPenalty) * 0.18f + widthBonus);
        }

        private float ResolvePassRisk(GtexSimSpatialPlayerState source, GtexSimSpatialPlayerState receiver, GtexSimSpatialPlayerState[] opponents, Vector3 target)
        {
            if (source == null || receiver == null)
            {
                return 0.5f;
            }

            var corridorRisk = 0f;
            var direction = target - source.Position;
            var distance = direction.magnitude;
            if (distance <= 0.01f || opponents == null)
            {
                return 0.4f;
            }

            direction.Normalize();
            for (var index = 0; index < opponents.Length; index += 1)
            {
                var opponent = opponents[index];
                if (opponent == null)
                {
                    continue;
                }

                var fromSource = opponent.Position - source.Position;
                var along = Vector3.Dot(fromSource, direction);
                if (along < 1f || along > distance - 1f)
                {
                    continue;
                }

                var lateral = Vector3.Cross(direction, fromSource).magnitude;
                if (lateral < 2.6f)
                {
                    corridorRisk += Mathf.Clamp01((2.8f - lateral) / 2.8f) * Mathf.Clamp01(1.2f - along / distance);
                }
            }

            return Mathf.Clamp01(corridorRisk * 0.58f + ResolveReceiverContestRisk(receiver, opponents) * 0.42f);
        }

        private float ResolveReceiverContestRisk(GtexSimSpatialPlayerState receiver, GtexSimSpatialPlayerState[] opponents)
        {
            if (receiver == null || opponents == null)
            {
                return 0.35f;
            }

            var nearest = float.MaxValue;
            var second = float.MaxValue;
            for (var index = 0; index < opponents.Length; index += 1)
            {
                var opponent = opponents[index];
                if (opponent == null || opponent.Role == "GK")
                {
                    continue;
                }

                var distance = Vector3.Distance(receiver.Position, opponent.Position);
                if (distance < nearest)
                {
                    second = nearest;
                    nearest = distance;
                }
                else if (distance < second)
                {
                    second = distance;
                }
            }

            if (nearest == float.MaxValue)
            {
                return 0.08f;
            }

            var nearestRisk = 1f - Mathf.Clamp01((nearest - 1.5f) / 8f);
            var secondRisk = second == float.MaxValue ? 0f : 1f - Mathf.Clamp01((second - 2.2f) / 9f);
            return Mathf.Clamp01(nearestRisk * 0.74f + secondRisk * 0.26f);
        }

        private sealed class ContestOutcome
        {
            public bool Success;
            public string Defender;
        }

        private ContestOutcome EvaluatePossessionContest(int sequence, float risk)
        {
            var sampled = Mathf.Clamp01((float)decisionRandom.NextDouble() * 0.9f + ((sequence % 5) * 0.02f));
            return new ContestOutcome
            {
                Success = sampled >= risk * 0.72f,
                Defender = ResolveClosestOpponentToDecisionReceiver()
            };
        }

        private string ResolveClosestOpponentToDecisionReceiver()
        {
            var receiver = !string.IsNullOrWhiteSpace(currentDecision.ReceiverPlayerId)
                ? FindPlayer(currentDecision.ReceiverPlayerId)
                : FindPlayer(ballHolderPlayerId);
            var opponents = ResolveTeamPlayers(receiver != null ? OppositeSide(receiver.TeamSide) : OppositeSide(possessionSide));
            if (receiver == null || opponents == null)
            {
                return ResolveNearestOutfieldPlayerId(OppositeSide(possessionSide), ResolveBallAnchor(lastClockMinute));
            }

            return ResolveNearestOutfieldPlayerId(OppositeSide(receiver.TeamSide), receiver.Position);
        }

        private Vector3 ResolveInterceptPoint(GtexSimSpatialPlayerState source, GtexSimSpatialPlayerState receiver, string defenderId)
        {
            var defender = FindPlayer(defenderId);
            var target = defender != null ? defender.Position : Vector3.Lerp(source.Position, receiver.Position, 0.6f);
            target += (source.TeamSide == "home" ? Vector3.right : Vector3.left) * 0.35f;
            return ClampToPitch(target);
        }

        private void UpdatePlayers(float currentMinute, float deltaSeconds)
        {
            UpdateTeamPlayers(homePlayers, currentMinute, deltaSeconds, "home");
            UpdateTeamPlayers(awayPlayers, currentMinute, deltaSeconds, "away");
        }

        private void UpdateTeamPlayers(GtexSimSpatialPlayerState[] teamPlayers, float currentMinute, float deltaSeconds, string teamSide)
        {
            var teamHasPossession = string.Equals(possessionSide, teamSide, StringComparison.Ordinal);
            var attackDirection = teamSide == "home" ? 1f : -1f;
            var ballAnchor = ResolveBallAnchor(currentMinute);
            var receiverId = activeTransit.Active ? activeTransit.PostTransitHolderPlayerId : string.Empty;
            var sourceId = !string.IsNullOrWhiteSpace(ballHolderPlayerId) ? ballHolderPlayerId : receiverId;
            var supportPlayerId = teamHasPossession ? ResolveSupportPlayerId(teamSide, sourceId, receiverId) : string.Empty;
            var runnerPlayerId = teamHasPossession ? ResolveRunnerPlayerId(teamSide, sourceId, receiverId) : string.Empty;
            var presserPlayerId = !teamHasPossession ? ResolveNearestOutfieldPlayerId(teamSide, ballAnchor) : string.Empty;
            var coverPlayerId = !teamHasPossession ? ResolveCoverPlayerId(teamSide, presserPlayerId, ballAnchor) : string.Empty;
            var markerPlayerId = !teamHasPossession ? ResolveMarkerPlayerId(teamSide, receiverId, ballAnchor, presserPlayerId, coverPlayerId) : string.Empty;

            for (var index = 0; index < teamPlayers.Length; index += 1)
            {
                var player = teamPlayers[index];
                if (player == null)
                {
                    continue;
                }

                var previousPosition = player.Position;
                var anchor = teamSide == "home" ? HomeAnchors[index] : MirrorAnchor(HomeAnchors[index]);
                var lineWeight = ResolveLineWeight(player.Line);
                var possessionShift = attackDirection * (teamHasPossession ? 1f : -0.34f) * lineWeight * 4.25f;
                var roamX = 0f;
                var roamZ = 0f;
                var targetPosition = ClampToPitch(anchor + new Vector3(possessionShift + roamX, 0f, roamZ));
                var playerId = player.PlayerId ?? string.Empty;
                var isGoalkeeper = string.Equals(player.Role, "GK", StringComparison.Ordinal);
                var isHolder = !activeTransit.Active && string.Equals(playerId, ballHolderPlayerId, StringComparison.Ordinal);
                var isReceiver = !string.IsNullOrWhiteSpace(receiverId) && string.Equals(playerId, receiverId, StringComparison.Ordinal);
                var isSupport = !string.IsNullOrWhiteSpace(supportPlayerId) && string.Equals(playerId, supportPlayerId, StringComparison.Ordinal);
                var isRunner = !string.IsNullOrWhiteSpace(runnerPlayerId) && string.Equals(playerId, runnerPlayerId, StringComparison.Ordinal);
                var isPresser = !string.IsNullOrWhiteSpace(presserPlayerId) && string.Equals(playerId, presserPlayerId, StringComparison.Ordinal);
                var isCover = !string.IsNullOrWhiteSpace(coverPlayerId) && string.Equals(playerId, coverPlayerId, StringComparison.Ordinal);
                var isMarker = !string.IsNullOrWhiteSpace(markerPlayerId) && string.Equals(playerId, markerPlayerId, StringComparison.Ordinal);
                var lerpSpeed = PassivePlayerLerpSpeed;

                if (isGoalkeeper)
                {
                    targetPosition = ResolveGoalkeeperTargetPosition(teamSide, ballAnchor);
                    lerpSpeed = teamHasPossession ? 2.2f : 2.8f;
                }
                else if (isHolder)
                {
                    var carrying = string.Equals(dribblePlayerId, playerId, StringComparison.Ordinal) && dribbleUntilMinute >= currentMinute;
                    var intentTarget = currentDecision.Active && string.Equals(currentDecision.SourcePlayerId, playerId, StringComparison.Ordinal)
                        ? currentDecision.TargetPosition
                        : ballAnchor + new Vector3(attackDirection * (carrying ? 4.0f : 2.0f), 0f, Mathf.Sin(currentMinute * 1.05f) * (carrying ? 1.35f : 1.05f));
                    targetPosition = Vector3.Lerp(targetPosition, ClampToPitch(intentTarget), carrying ? 0.84f : 0.52f);
                    lerpSpeed = ActivePlayerLerpSpeed;
                }
                else if (isReceiver)
                {
                    var receiveTarget = activeTransit.Active
                        ? activeTransit.End + ResolveForward(player) * 0.42f
                        : ballAnchor + new Vector3(attackDirection * 4.2f, 0f, Mathf.Sign(player.Position.z) * 1.55f);
                    targetPosition = Vector3.Lerp(targetPosition, ClampToPitch(receiveTarget), 0.8f);
                    lerpSpeed = ActivePlayerLerpSpeed;
                }
                else if (teamHasPossession && isSupport)
                {
                    var supportOffset = new Vector3(-attackDirection * 4.0f, 0f, Mathf.Clamp(player.Position.z - ballAnchor.z, -8.5f, 8.5f) * 0.58f);
                    targetPosition = Vector3.Lerp(targetPosition, ClampToPitch(ballAnchor + supportOffset), 0.54f);
                    lerpSpeed = 3.05f;
                }
                else if (teamHasPossession && isRunner)
                {
                    var runSpace = currentDecision.Active && string.Equals(currentDecision.Action, "pass", StringComparison.Ordinal)
                        ? currentDecision.Space
                        : 0.55f;
                    var laneZ = Mathf.Clamp(player.Position.z * (1.1f + runSpace * 0.35f), -PitchWidthMeters * 0.34f, PitchWidthMeters * 0.34f);
                    targetPosition = Vector3.Lerp(targetPosition, ClampToPitch(ballAnchor + new Vector3(attackDirection * (9.5f + runSpace * 4.0f), 0f, laneZ)), 0.67f);
                    lerpSpeed = 3.4f;
                }
                else if (!teamHasPossession && isPresser)
                {
                    targetPosition = Vector3.Lerp(targetPosition, ClampToPitch(ballAnchor - new Vector3(attackDirection * 0.6f, 0f, 0f)), 0.86f);
                    lerpSpeed = ActivePlayerLerpSpeed;
                }
                else if (!teamHasPossession && isCover)
                {
                    targetPosition = Vector3.Lerp(targetPosition, ResolveDefensiveCoverPosition(teamSide, ballAnchor), 0.64f);
                    lerpSpeed = 3f;
                }
                else if (!teamHasPossession && isMarker)
                {
                    targetPosition = Vector3.Lerp(targetPosition, ResolveMarkingPosition(teamSide, receiverId, ballAnchor), 0.6f);
                    lerpSpeed = 2.85f;
                }

                player.Position = Vector3.Lerp(previousPosition, ClampToPitch(targetPosition), Mathf.Clamp01(deltaSeconds * lerpSpeed));
                player.Position.y = 0f;
                player.Velocity = (player.Position - previousPosition) / Mathf.Max(deltaSeconds, 0.02f);
                player.HasPossession = !activeTransit.Active && string.Equals(player.PlayerId, ballHolderPlayerId, StringComparison.Ordinal);
                player.SpeedRatio = Mathf.Clamp01(new Vector3(player.Velocity.x, 0f, player.Velocity.z).magnitude / 7.5f);
                player.AnimationState = player.HasPossession
                    ? (dribbleUntilMinute >= currentMinute && string.Equals(dribblePlayerId, player.PlayerId, StringComparison.Ordinal) ? "dribble" : "idle")
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
                    firstTouchSettleUntilMinute = currentMinute + FirstTouchSettleMinutes;
                    dribbleUntilMinute = -1f;
                    dribblePlayerId = string.Empty;
                    var holder = FindPlayer(ballHolderPlayerId);
                    if (holder != null)
                    {
                        ballState.Position = holder.Position + ResolveForward(holder) * 0.5f;
                        ballState.Position.y = GtexPlaybackSanitizer.DefaultBallHeight;
                        ballState.HolderPlayerId = holder.PlayerId;
                        ballState.TrajectoryType = "ground";
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

            var carrying = dribbleUntilMinute >= currentMinute && string.Equals(dribblePlayerId, holderPlayer.PlayerId, StringComparison.Ordinal);
            var holderOffset = ResolveForward(holderPlayer) * (carrying ? 0.78f : 0.62f);
            var targetPosition = holderPlayer.Position + holderOffset;
            targetPosition.y = GtexPlaybackSanitizer.DefaultBallHeight;
            if (carrying)
            {
                targetPosition.z += Mathf.Sin(currentMinute * 9.5f) * 0.05f;
                targetPosition.y += Mathf.Abs(Mathf.Sin(currentMinute * 9.5f)) * 0.02f;
            }

            ballState.Position = Vector3.Lerp(ballState.Position, targetPosition, Mathf.Clamp01(deltaSeconds * (carrying ? 10f : 8f)));
            ballState.Velocity = (ballState.Position - previousPosition) / Mathf.Max(deltaSeconds, 0.02f);
            ballState.HolderPlayerId = holderPlayer.PlayerId;
            ballState.TrajectoryType = "ground";

            ResolvePossessionContestAfterCarry(currentMinute, holderPlayer);
        }

        private void ResolvePossessionContestAfterCarry(float currentMinute, GtexSimSpatialPlayerState holder)
        {
            if (holder == null || dribbleUntilMinute < currentMinute || !string.Equals(dribblePlayerId, holder.PlayerId, StringComparison.Ordinal))
            {
                return;
            }

            var opponents = ResolveTeamPlayers(OppositeSide(holder.TeamSide));
            var pressure = ResolvePressure(holder, opponents);
            if (pressure < 0.82f)
            {
                return;
            }

            var sampled = (float)decisionRandom.NextDouble();
            if (sampled > pressure * 0.68f)
            {
                return;
            }

            var tacklerId = ResolveNearestOutfieldPlayerId(OppositeSide(holder.TeamSide), holder.Position);
            if (string.IsNullOrWhiteSpace(tacklerId))
            {
                return;
            }

            ballHolderPlayerId = tacklerId;
            possessionSide = OppositeSide(holder.TeamSide);
            firstTouchSettleUntilMinute = currentMinute + 0.08f;
            dribbleUntilMinute = -1f;
            dribblePlayerId = string.Empty;
            currentDecision = default;
            nextDecisionMinute = currentMinute + 0.12f;
            RegisterEvent("turnover", currentMinute, possessionSide, "Possession won under pressure.", 0, 0, tacklerId, holder.PlayerId);
            currentCameraPreset = "broadcast";
            currentCameraPresetUntilMinute = currentMinute + 0.12f;
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
            var start = sourcePlayer != null ? sourcePlayer.Position + ResolveForward(sourcePlayer) * 0.68f : ResolveBallAnchor(currentMinute);
            start.y = GtexPlaybackSanitizer.DefaultBallHeight;
            endPosition.y = GtexPlaybackSanitizer.DefaultBallHeight;

            activeTransit = new BallTransit
            {
                Active = true,
                Start = start,
                End = ClampToPitch(endPosition),
                StartedAtMinute = currentMinute,
                DurationMinutes = Mathf.Max(0.06f, durationMinutes),
                ArcHeight = Mathf.Max(0.02f, arcHeight),
                PostTransitHolderPlayerId = postTransitHolderPlayerId ?? string.Empty,
                PostTransitPossessionSide = postTransitPossessionSide ?? string.Empty,
                TrajectoryType = trajectoryType ?? "pass"
            };

            ballHolderPlayerId = string.Empty;
            dribbleUntilMinute = -1f;
            dribblePlayerId = string.Empty;
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

            if (recentEvents.Count >= 10)
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
                case "turnover":
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
            var opponents = ResolveTeamPlayers(OppositeSide(teamSide));
            for (var index = 0; index < teamPlayers.Length; index += 1)
            {
                var candidate = teamPlayers[index];
                if (candidate == null || candidate.Role == "GK" ||
                    string.Equals(candidate.PlayerId, sourcePlayerId, StringComparison.Ordinal) ||
                    string.Equals(candidate.PlayerId, receiverPlayerId, StringComparison.Ordinal))
                {
                    continue;
                }

                var distance = Vector3.Distance(candidate.Position, sourcePlayer.Position);
                var attackDelta = ResolveAttackAxisDelta(candidate.Position.x - sourcePlayer.Position.x, teamSide);
                var score = 0f;
                score += string.Equals(candidate.Line, "midfield", StringComparison.Ordinal) ? 3.4f : 0f;
                score += string.Equals(candidate.Line, "defense", StringComparison.Ordinal) ? 1.6f : 0f;
                score += attackDelta > -8f && attackDelta < 8f ? 1.6f : 0f;
                score += ResolveSpaceScore(candidate, opponents, candidate.Position) * 1.6f;
                score -= Mathf.Abs(distance - 10f) * 0.12f;
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
            var opponents = ResolveTeamPlayers(OppositeSide(teamSide));
            for (var index = 0; index < teamPlayers.Length; index += 1)
            {
                var candidate = teamPlayers[index];
                if (candidate == null || candidate.Role == "GK" ||
                    string.Equals(candidate.PlayerId, sourcePlayerId, StringComparison.Ordinal) ||
                    string.Equals(candidate.PlayerId, receiverPlayerId, StringComparison.Ordinal))
                {
                    continue;
                }

                var attackDelta = ResolveAttackAxisDelta(candidate.Position.x - sourcePlayer.Position.x, teamSide);
                var space = ResolveSpaceScore(candidate, opponents, candidate.Position);
                var score = (string.Equals(candidate.Line, "attack", StringComparison.Ordinal) ? 3.8f : 0f) +
                            (IsWideRole(candidate) ? 1.1f : 0f) +
                            Mathf.Clamp(attackDelta, 0f, 18f) * 0.2f +
                            space * 1.8f -
                            Mathf.Abs(candidate.Position.z) * 0.018f;
                if (attackDelta < 2f)
                {
                    score -= 2.4f;
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
                if (candidate == null || candidate.Role == "GK")
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
                if (candidate == null || candidate.Role == "GK" ||
                    string.Equals(candidate.PlayerId, presserPlayerId, StringComparison.Ordinal))
                {
                    continue;
                }

                if (!string.Equals(candidate.Line, "defense", StringComparison.Ordinal) && !string.Equals(candidate.Role, "DM", StringComparison.Ordinal))
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

        private string ResolveMarkerPlayerId(string teamSide, string threatPlayerId, Vector3 ballAnchor, string presserPlayerId, string coverPlayerId)
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
                if (candidate == null || candidate.Role == "GK" ||
                    string.Equals(candidate.PlayerId, presserPlayerId, StringComparison.Ordinal) ||
                    string.Equals(candidate.PlayerId, coverPlayerId, StringComparison.Ordinal))
                {
                    continue;
                }

                if (!string.Equals(candidate.Line, "defense", StringComparison.Ordinal) && !string.Equals(candidate.Line, "midfield", StringComparison.Ordinal))
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
            var goalX = teamSide == "home" ? -PitchLengthMeters * 0.5f + 4.9f : PitchLengthMeters * 0.5f - 4.9f;
            var zClamp = Mathf.Clamp(ballAnchor.z * 0.28f, -PitchWidthMeters * 0.18f, PitchWidthMeters * 0.18f);
            var xStep = Mathf.Clamp(Mathf.Abs(ballAnchor.x) * 0.02f, 0.35f, 1.65f);
            goalX += teamSide == "home" ? xStep : -xStep;
            return ClampToPitch(new Vector3(goalX, 0f, zClamp));
        }

        private static Vector3 ResolveDefensiveCoverPosition(string teamSide, Vector3 ballAnchor)
        {
            var goalCenter = teamSide == "home"
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

            var goalCenter = teamSide == "home"
                ? new Vector3(-PitchLengthMeters * 0.5f + 9.5f, 0f, 0f)
                : new Vector3(PitchLengthMeters * 0.5f - 9.5f, 0f, 0f);
            return ClampToPitch(Vector3.Lerp(goalCenter, threatPlayer.Position, 0.62f));
        }

        private static float ResolveAttackAxisDelta(float deltaX, string teamSide)
        {
            return teamSide == "away" ? -deltaX : deltaX;
        }

        private static float ResolveLineWeight(string line)
        {
            switch ((line ?? string.Empty).Trim().ToLowerInvariant())
            {
                case "goalkeeper": return 0.15f;
                case "defense": return 0.38f;
                case "attack": return 1.15f;
                default: return 0.75f;
            }
        }

        private static bool IsWideRole(GtexSimSpatialPlayerState player)
        {
            if (player == null)
            {
                return false;
            }

            return player.Role == "RW" || player.Role == "LW" || player.Role == "RB" || player.Role == "LB";
        }

        private string ResolveGoalSourcePlayerId(string teamSide)
        {
            var holder = FindPlayer(ballHolderPlayerId);
            if (holder != null && string.Equals(holder.TeamSide, teamSide, StringComparison.Ordinal))
            {
                return holder.PlayerId;
            }

            var teamPlayers = ResolveTeamPlayers(teamSide);
            if (teamPlayers == null)
            {
                return string.Empty;
            }

            var bestScore = float.NegativeInfinity;
            var bestId = string.Empty;
            for (var index = 0; index < teamPlayers.Length; index += 1)
            {
                var candidate = teamPlayers[index];
                if (candidate == null || candidate.Role == "GK")
                {
                    continue;
                }

                var distanceToGoal = DistanceToOpposingGoal(teamSide, candidate.Position);
                var score = (string.Equals(candidate.Line, "attack", StringComparison.Ordinal) ? 3f : 1f) - distanceToGoal * 0.04f;
                if (score > bestScore)
                {
                    bestScore = score;
                    bestId = candidate.PlayerId;
                }
            }

            return bestId;
        }

        private float DistanceToOpposingGoal(string teamSide, Vector3 position)
        {
            var goalX = teamSide == "home" ? PitchLengthMeters * 0.5f : -PitchLengthMeters * 0.5f;
            return Mathf.Abs(goalX - position.x);
        }

        private float SpaceToGoal(GtexSimSpatialPlayerState source, GtexSimSpatialPlayerState[] opponents)
        {
            if (source == null)
            {
                return 0f;
            }

            var goalX = source.TeamSide == "home" ? PitchLengthMeters * 0.5f : -PitchLengthMeters * 0.5f;
            var direction = goalX > source.Position.x ? Vector3.right : Vector3.left;
            var best = 1f;
            if (opponents == null)
            {
                return best;
            }

            for (var index = 0; index < opponents.Length; index += 1)
            {
                var opponent = opponents[index];
                if (opponent == null)
                {
                    continue;
                }

                var delta = opponent.Position - source.Position;
                var along = Vector3.Dot(delta, direction);
                if (along < 0f || along > 22f)
                {
                    continue;
                }

                var lateral = Vector3.Cross(direction, delta).magnitude;
                if (lateral < 3.6f)
                {
                    best = Mathf.Min(best, Mathf.Clamp01(lateral / 3.6f));
                }
            }

            return best;
        }

        private float ResolvePassDuration(GtexSimSpatialPlayerState source, Vector3 target)
        {
            var distance = source != null ? Vector3.Distance(source.Position, target) : 14f;
            return Mathf.Clamp(0.075f + distance / 250f, 0.08f, 0.18f);
        }

        private float ResolvePassArcHeight(GtexSimSpatialPlayerState source, GtexSimSpatialPlayerState targetPlayer, Vector3 target)
        {
            var distance = source != null ? Vector3.Distance(source.Position, target) : 14f;
            if (source != null && source.Role == "GK")
            {
                return GoalkeeperDistributionArcHeight;
            }

            if (distance > 26f || (targetPlayer != null && IsWideRole(targetPlayer)))
            {
                return LoftedPassArcHeight;
            }

            return GroundPassArcHeight;
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

            var separatorIndex = playerId.IndexOf('-');
            if (separatorIndex < 0 || separatorIndex >= playerId.Length - 1 ||
                !int.TryParse(playerId.Substring(separatorIndex + 1), out var parsedIndex))
            {
                return null;
            }

            var index = Mathf.Clamp(parsedIndex - 1, -1, PlayersPerSide - 1);
            if (index < 0)
            {
                return null;
            }

            return playerId.StartsWith("away-", StringComparison.Ordinal) ? awayPlayers[index] : homePlayers[index];
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
                facing = player.TeamSide == "home" ? Vector3.right : Vector3.left;
            }

            facing.y = 0f;
            return facing.normalized;
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

        private static string OppositeSide(string teamSide)
        {
            return teamSide == "away" ? "home" : "away";
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

            var holder = FindPlayer(ballHolderPlayerId);
            if (holder != null)
            {
                var anchor = holder.Position + ResolveForward(holder) * 0.55f;
                anchor.y = 0f;
                return ClampToPitch(anchor);
            }

            var fallback = ballState.Position;
            fallback.y = 0f;
            return ClampToPitch(fallback);
        }

        private static Vector3 ResolveGoalMouthTarget(string teamSide, bool missedChance)
        {
            var x = teamSide == "home" ? PitchLengthMeters * 0.5f : -PitchLengthMeters * 0.5f;
            var z = missedChance ? 7.5f : 0f;
            if (teamSide == "away")
            {
                z *= -1f;
            }

            return new Vector3(x, GtexPlaybackSanitizer.DefaultBallHeight, z);
        }

        private static string ResolvePhaseToken(GtexSimState state)
        {
            switch (state)
            {
                case GtexSimState.FirstHalf: return "first_half";
                case GtexSimState.HalfTime: return "halftime";
                case GtexSimState.SecondHalf: return "second_half";
                case GtexSimState.FullTime: return "fulltime";
                default: return "kickoff";
            }
        }

        private static float ResolveRealSecondsPerMatchMinute(GtexMatchConfig matchConfig)
        {
            var targetDurationMinutes = matchConfig != null ? Mathf.Max(1f, matchConfig.simulationTargetDurationMinutes) : 15f;
            return (targetDurationMinutes * 60f) / 90f;
        }
    }
}