using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace FStudio.GTEX.VisualBridge
{
    public static class GtexVisualSequencePatternLibrary
    {
        public const string CentralBuildupShot = "central-buildup-shot";
        public const string WideCrossChance = "wide-cross-chance";
        public const string CutbackChance = "cutback-chance";

        public static bool TryBuild(
            string sequenceId,
            string teamId,
            GtexOriginalSimAdapter adapter,
            out GtexVisualSequence sequence,
            out string reason)
        {
            sequence = null;
            reason = string.Empty;

            var normalizedSequence = NormalizeSequenceId(sequenceId);
            var normalizedTeam = NormalizeTeamId(teamId);
            if (string.IsNullOrWhiteSpace(normalizedTeam))
            {
                reason = "teamId must be home or away";
                return false;
            }

            if (adapter == null || adapter.PlayerMap == null)
            {
                reason = "adapter/player map missing";
                return false;
            }

            if (!TryResolveParticipants(normalizedTeam, adapter, out var participants, out reason))
            {
                return false;
            }

            switch (normalizedSequence)
            {
                case WideCrossChance:
                    sequence = BuildWideCrossChance(participants, adapter);
                    return true;
                case CutbackChance:
                    sequence = BuildCutbackChance(participants, adapter);
                    return true;
                case CentralBuildupShot:
                default:
                    sequence = BuildCentralBuildupShot(participants, adapter);
                    return true;
            }
        }

        private static GtexVisualSequence BuildCentralBuildupShot(Participants p, GtexOriginalSimAdapter adapter)
        {
            ResolveCentralFinalThirdSetup(
                p,
                adapter,
                out var carrierSetupPoint,
                out var runnerSetupPoint,
                out var supportSetupPoint);

            var supportPoint = ResolveCentralSupportPoint(carrierSetupPoint, supportSetupPoint, adapter);
            var throughPoint = ResolveCentralThroughPoint(p, runnerSetupPoint, adapter);

            var sequence = CreateBaseSequence(CentralBuildupShot, p);
            AddFinalThirdPositioning(sequence, p, carrierSetupPoint, runnerSetupPoint, supportSetupPoint);
            sequence.steps.Add(Step("AssignPossession", GtexVisualCommandType.AssignPossession, p.carrier.GtexPlayerId, null, Vector3.zero, GtexVisualSequenceCompletionMode.Possession, 1.5f));
            sequence.steps.Add(Step("SupportRun", GtexVisualCommandType.SupportRun, p.support.GtexPlayerId, null, supportPoint, GtexVisualSequenceCompletionMode.PlayerAtPoint, 2.8f));
            var pressStep = Step("PressBallCarrier", GtexVisualCommandType.PressBallCarrier, p.presser.GtexPlayerId, p.carrier.GtexPlayerId, Vector3.zero, GtexVisualSequenceCompletionMode.DelayOnly, 0.2f, required: false);
            pressStep.command.duration = 2.3f;
            pressStep.command.urgency = 1f;
            sequence.steps.Add(pressStep);
            var markStep = Step("MarkPlayer", GtexVisualCommandType.MarkPlayer, p.marker.GtexPlayerId, p.runner.GtexPlayerId, Vector3.zero, GtexVisualSequenceCompletionMode.DelayOnly, 0.2f, required: false);
            markStep.command.duration = 2.6f;
            markStep.command.urgency = 0.85f;
            sequence.steps.Add(markStep);
            sequence.steps.Add(Step("Pass", GtexVisualCommandType.Pass, p.carrier.GtexPlayerId, p.support.GtexPlayerId, Vector3.zero, GtexVisualSequenceCompletionMode.PassReceived, 3.5f, GtexVisualPassStyle.Ground));
            sequence.steps.Add(Step("ThroughPass", GtexVisualCommandType.ThroughPass, p.support.GtexPlayerId, p.runner.GtexPlayerId, throughPoint, GtexVisualSequenceCompletionMode.ThroughPassReachable, 3.5f, GtexVisualPassStyle.ThroughGround));
            sequence.steps.Add(Step("Shoot", GtexVisualCommandType.Shoot, p.runner.GtexPlayerId, null, p.goal, GtexVisualSequenceCompletionMode.ShotReleased, 2.2f, outcome: "on_target", evaluateShotOutcome: true, completionPlayerUid: p.keeper.GtexPlayerId));
            return sequence;
        }

        private static GtexVisualSequence BuildWideCrossChance(Participants p, GtexOriginalSimAdapter adapter)
        {
            var wideCarrier = p.attackers
                .OrderByDescending(proxy => Mathf.Abs(proxy.Root.position.z - p.goal.z))
                .ThenBy(proxy => Vector3.SqrMagnitude(proxy.Root.position - adapter.GetBallPosition()))
                .FirstOrDefault() ?? p.carrier;
            var boxRunner = p.attackers.FirstOrDefault(proxy => proxy != wideCarrier && proxy != null) ?? p.runner;
            var widePoint = ResolveReachableIntentPoint(
                wideCarrier,
                ResolveAdvancePoint(wideCarrier, p.goal, adapter, 9f, Mathf.Sign(wideCarrier.Root.position.z - p.goal.z) * 7f),
                adapter,
                4.2f);
            var boxPoint = ResolveReachableIntentPoint(
                boxRunner,
                ResolveAdvancePoint(boxRunner, p.goal, adapter, 12f, -Mathf.Sign(wideCarrier.Root.position.z - p.goal.z) * 2.5f),
                adapter,
                3.8f);

            var sequence = CreateBaseSequence(WideCrossChance, p);
            AddControlled(sequence, wideCarrier.GtexPlayerId, boxRunner.GtexPlayerId);
            sequence.steps.Add(Step("AssignPossession", GtexVisualCommandType.AssignPossession, wideCarrier.GtexPlayerId, null, Vector3.zero, GtexVisualSequenceCompletionMode.Possession, 1.5f));
            sequence.steps.Add(Step("CarryBall", GtexVisualCommandType.CarryBall, wideCarrier.GtexPlayerId, null, widePoint, GtexVisualSequenceCompletionMode.PlayerAtPoint, 3.2f));
            sequence.steps.Add(Step("SupportRun", GtexVisualCommandType.SupportRun, boxRunner.GtexPlayerId, null, boxPoint, GtexVisualSequenceCompletionMode.PlayerAtPoint, 3.2f));
            sequence.steps.Add(Step("MarkPlayer", GtexVisualCommandType.MarkPlayer, p.marker.GtexPlayerId, boxRunner.GtexPlayerId, Vector3.zero, GtexVisualSequenceCompletionMode.DelayOnly, 0.2f, required: false));
            sequence.steps.Add(Step("Cross", GtexVisualCommandType.Cross, wideCarrier.GtexPlayerId, null, boxPoint, GtexVisualSequenceCompletionMode.ThroughPassReachable, 3.2f, GtexVisualPassStyle.Cross));
            sequence.steps.Add(Step("Shoot", GtexVisualCommandType.Shoot, boxRunner.GtexPlayerId, null, p.goal, GtexVisualSequenceCompletionMode.ShotReleased, 2.2f, outcome: "on_target", required: false, evaluateShotOutcome: true, completionPlayerUid: p.keeper.GtexPlayerId));
            return sequence;
        }

        private static GtexVisualSequence BuildCutbackChance(Participants p, GtexOriginalSimAdapter adapter)
        {
            var channelPoint = ResolveReachableIntentPoint(
                p.carrier,
                ResolveAdvancePoint(p.carrier, p.goal, adapter, 9f, 5f),
                adapter,
                4.0f);
            var cutbackPoint = ResolveReachableIntentPoint(
                p.support,
                ResolveAdvancePoint(p.support, p.goal, adapter, 5f, -3.5f),
                adapter,
                3.0f);

            var sequence = CreateBaseSequence(CutbackChance, p);
            sequence.steps.Add(Step("AssignPossession", GtexVisualCommandType.AssignPossession, p.carrier.GtexPlayerId, null, Vector3.zero, GtexVisualSequenceCompletionMode.Possession, 1.5f));
            sequence.steps.Add(Step("CarryBall", GtexVisualCommandType.CarryBall, p.carrier.GtexPlayerId, null, channelPoint, GtexVisualSequenceCompletionMode.PlayerAtPoint, 3.2f));
            sequence.steps.Add(Step("SupportRun", GtexVisualCommandType.SupportRun, p.support.GtexPlayerId, null, cutbackPoint, GtexVisualSequenceCompletionMode.PlayerAtPoint, 3.2f));
            sequence.steps.Add(Step("Pass", GtexVisualCommandType.Pass, p.carrier.GtexPlayerId, p.support.GtexPlayerId, cutbackPoint, GtexVisualSequenceCompletionMode.PassReceived, 3.5f, GtexVisualPassStyle.Ground));
            sequence.steps.Add(Step("Shoot", GtexVisualCommandType.Shoot, p.support.GtexPlayerId, null, p.goal, GtexVisualSequenceCompletionMode.ShotReleased, 2.2f, outcome: "on_target", evaluateShotOutcome: true, completionPlayerUid: p.keeper.GtexPlayerId));
            return sequence;
        }

        private static GtexVisualSequence CreateBaseSequence(string sequenceId, Participants p)
        {
            var sequence = new GtexVisualSequence
            {
                sequenceId = sequenceId,
                teamId = p.teamId,
                leaseDurationSeconds = 6f
            };

            AddControlled(
                sequence,
                p.carrier.GtexPlayerId,
                p.support.GtexPlayerId,
                p.runner.GtexPlayerId,
                p.presser.GtexPlayerId,
                p.marker.GtexPlayerId,
                p.keeper.GtexPlayerId);
            return sequence;
        }

        private static GtexVisualSequenceStep Step(
            string label,
            GtexVisualCommandType type,
            string actor,
            string target,
            Vector3 point,
            GtexVisualSequenceCompletionMode completionMode,
            float timeoutSeconds,
            GtexVisualPassStyle passStyle = GtexVisualPassStyle.Ground,
            string outcome = "",
            bool required = true,
            bool evaluateShotOutcome = false,
            string completionPlayerUid = "")
        {
            return new GtexVisualSequenceStep
            {
                label = label,
                required = required,
                timeoutSeconds = timeoutSeconds,
                completionMode = completionMode,
                completionWorldPosition = point,
                completionDistance = ResolveCompletionDistance(type),
                completionPlayerUid = completionPlayerUid ?? string.Empty,
                evaluateShotOutcome = evaluateShotOutcome,
                command = new GtexVisualCommand
                {
                    type = type,
                    actorPlayerId = actor ?? string.Empty,
                    targetPlayerId = target ?? string.Empty,
                    targetWorldPosition = point,
                    passStyle = passStyle,
                    outcome = outcome,
                    isSuccessful = true,
                    duration = Mathf.Clamp(timeoutSeconds, 0.2f, 3.5f),
                    urgency = 0.85f
                }
            };
        }

        private static bool TryResolveParticipants(
            string teamId,
            GtexOriginalSimAdapter adapter,
            out Participants participants,
            out string reason)
        {
            participants = null;
            reason = string.Empty;

            var opponentTeamId = teamId == "home" ? "away" : "home";
            var attackers = ResolveOutfield(adapter, teamId);
            var defenders = ResolveOutfield(adapter, opponentTeamId);
            if (attackers.Count < 3)
            {
                reason = "not enough attacking outfield players for " + teamId;
                return false;
            }

            if (defenders.Count < 2)
            {
                reason = "not enough defending outfield players for " + opponentTeamId;
                return false;
            }

            var keeper = adapter.PlayerMap.FindGoalkeeper(opponentTeamId);
            if (keeper == null)
            {
                reason = "opposing goalkeeper missing for " + opponentTeamId;
                return false;
            }

            var ballPosition = adapter.GetBallPosition();
            var goal = adapter.GetAttackingGoalCenter(teamId == "home" ? 0 : 1);
            GtexOriginalPlayerVisualProxy carrier;
            GtexOriginalPlayerVisualProxy support;
            GtexOriginalPlayerVisualProxy runner;
            if (!TryResolvePreferredCentralAttackers(teamId, adapter, out carrier, out support, out runner))
            {
                carrier = attackers.OrderBy(proxy => Vector3.SqrMagnitude(proxy.Root.position - ballPosition)).FirstOrDefault();
                support = attackers
                    .Where(proxy => proxy != carrier)
                    .OrderBy(proxy => Vector3.SqrMagnitude(proxy.Root.position - carrier.Root.position))
                    .FirstOrDefault();
                runner = attackers
                    .Where(proxy => proxy != carrier && proxy != support)
                    .OrderBy(proxy => Vector3.SqrMagnitude(proxy.Root.position - goal))
                    .FirstOrDefault();
            }

            var presser = defenders.OrderBy(proxy => Vector3.SqrMagnitude(proxy.Root.position - carrier.Root.position)).FirstOrDefault();
            var marker = defenders
                .Where(proxy => proxy != presser)
                .OrderBy(proxy => Vector3.SqrMagnitude(proxy.Root.position - runner.Root.position))
                .FirstOrDefault();

            if (carrier == null || support == null || runner == null || presser == null || marker == null)
            {
                reason = "failed to resolve carrier/support/runner/presser/marker";
                return false;
            }

            participants = new Participants
            {
                teamId = teamId,
                opponentTeamId = opponentTeamId,
                attackers = attackers,
                defenders = defenders,
                carrier = carrier,
                support = support,
                runner = runner,
                presser = presser,
                marker = marker,
                keeper = keeper,
                goal = goal
            };
            return true;
        }

        private static bool TryResolvePreferredCentralAttackers(
            string teamId,
            GtexOriginalSimAdapter adapter,
            out GtexOriginalPlayerVisualProxy carrier,
            out GtexOriginalPlayerVisualProxy support,
            out GtexOriginalPlayerVisualProxy runner)
        {
            carrier = null;
            support = null;
            runner = null;

            if (!string.Equals(teamId, "home", StringComparison.OrdinalIgnoreCase))
            {
                return false;
            }

            carrier = adapter.PlayerMap.ResolveProxy("home-7");
            runner = adapter.PlayerMap.ResolveProxy("home-9");
            support = adapter.PlayerMap.ResolveProxy("home-10");
            return IsUsableOutfield(carrier) &&
                   IsUsableOutfield(support) &&
                   IsUsableOutfield(runner);
        }

        private static bool IsUsableOutfield(GtexOriginalPlayerVisualProxy proxy)
        {
            return proxy != null && proxy.Player != null && !proxy.IsGoalkeeper;
        }

        private static List<GtexOriginalPlayerVisualProxy> ResolveOutfield(GtexOriginalSimAdapter adapter, string teamId)
        {
            return adapter.PlayerMap.Proxies
                .Where(proxy =>
                    proxy != null &&
                    proxy.Player != null &&
                    !proxy.IsGoalkeeper &&
                    string.Equals(GtexPlayerVisualMap.ResolveTeamSide(proxy.GtexPlayerId), teamId, StringComparison.OrdinalIgnoreCase) &&
                    GtexPlayerVisualMap.IsSideQualifiedPlayerUid(proxy.GtexPlayerId))
                .OrderBy(proxy => proxy.Player.MatchPlayer != null ? proxy.Player.MatchPlayer.Number : int.MaxValue)
                .ToList();
        }

        private static void AddFinalThirdPositioning(
            GtexVisualSequence sequence,
            Participants p,
            Vector3 carrierPoint,
            Vector3 runnerPoint,
            Vector3 supportPoint)
        {
            sequence.preSequenceBallOwnerUid = p.carrier.GtexPlayerId;
            sequence.preSequenceTimeoutSeconds = 18f;
            sequence.preSequencePositions.Add(PositionTarget(p.carrier.GtexPlayerId, carrierPoint));
            sequence.preSequencePositions.Add(PositionTarget(p.runner.GtexPlayerId, runnerPoint));
            sequence.preSequencePositions.Add(PositionTarget(p.support.GtexPlayerId, supportPoint));
        }

        private static GtexVisualSequencePositionTarget PositionTarget(string playerUid, Vector3 point)
        {
            return new GtexVisualSequencePositionTarget
            {
                playerUid = playerUid ?? string.Empty,
                targetWorldPosition = point,
                thresholdDistance = 2f,
                urgency = 1f,
                readyLabel = playerUid ?? string.Empty
            };
        }

        private static void ResolveCentralFinalThirdSetup(
            Participants p,
            GtexOriginalSimAdapter adapter,
            out Vector3 carrierPoint,
            out Vector3 runnerPoint,
            out Vector3 supportPoint)
        {
            var attackSign = string.Equals(p.teamId, "away", StringComparison.OrdinalIgnoreCase) ? -1f : 1f;
            var goal = p.goal;
            goal.y = 0f;

            var supportLateral = Mathf.Sign(p.support.Root.position.z - goal.z);
            if (Mathf.Abs(supportLateral) < 0.01f)
            {
                supportLateral = 1f;
            }

            carrierPoint = ResolveFinalThirdPoint(p.carrier, goal, attackSign, 28f, 0f, adapter);
            runnerPoint = ResolveFinalThirdPoint(p.runner, goal, attackSign, 20f, -supportLateral * 1.5f, adapter);
            supportPoint = ResolveFinalThirdPoint(p.support, goal, attackSign, 24f, supportLateral * 8f, adapter);
        }

        private static Vector3 ResolveFinalThirdPoint(
            GtexOriginalPlayerVisualProxy actor,
            Vector3 goal,
            float attackSign,
            float distanceFromGoal,
            float lateralDistance,
            GtexOriginalSimAdapter adapter)
        {
            var point = new Vector3(
                goal.x - attackSign * distanceFromGoal,
                actor.Root.position.y,
                goal.z + lateralDistance);
            return adapter != null ? adapter.ClampToPitch(point) : point;
        }

        private static Vector3 ResolveCentralSupportPoint(
            Vector3 carrierPoint,
            Vector3 supportPoint,
            GtexOriginalSimAdapter adapter)
        {
            var point = supportPoint;
            point.y = supportPoint.y;
            return adapter != null ? adapter.ClampToPitch(point) : point;
        }

        private static Vector3 ResolveCentralThroughPoint(
            Participants p,
            Vector3 runnerPoint,
            GtexOriginalSimAdapter adapter)
        {
            var attackSign = string.Equals(p.teamId, "away", StringComparison.OrdinalIgnoreCase) ? -1f : 1f;
            var point = runnerPoint + Vector3.right * attackSign * 7f;
            point.y = runnerPoint.y;
            return adapter != null ? adapter.ClampToPitch(point) : point;
        }

        private static Vector3 ResolveAdvancePoint(
            GtexOriginalPlayerVisualProxy actor,
            Vector3 goal,
            GtexOriginalSimAdapter adapter,
            float distanceFromGoal,
            float lateralDistance)
        {
            var fromGoalToActor = actor.Root.position - goal;
            fromGoalToActor.y = 0f;
            if (fromGoalToActor.sqrMagnitude <= 0.001f)
            {
                fromGoalToActor = Vector3.left;
            }

            fromGoalToActor.Normalize();
            var right = Vector3.Cross(Vector3.up, fromGoalToActor).normalized;
            var point = goal + fromGoalToActor * distanceFromGoal + right * lateralDistance;
            point.y = actor.Root.position.y;
            return adapter.ClampToPitch(point);
        }

        private static Vector3 ResolveReachableIntentPoint(
            GtexOriginalPlayerVisualProxy actor,
            Vector3 desiredPoint,
            GtexOriginalSimAdapter adapter,
            float maxDistance)
        {
            if (actor == null)
            {
                return desiredPoint;
            }

            var origin = actor.Root.position;
            var offset = desiredPoint - origin;
            offset.y = 0f;
            if (offset.sqrMagnitude > maxDistance * maxDistance)
            {
                desiredPoint = origin + offset.normalized * maxDistance;
            }

            desiredPoint.y = origin.y;
            return adapter != null ? adapter.ClampToPitch(desiredPoint) : desiredPoint;
        }

        private static void AddControlled(GtexVisualSequence sequence, params string[] playerUids)
        {
            for (var index = 0; index < playerUids.Length; index += 1)
            {
                var uid = GtexPlayerVisualMap.NormalizePlayerUid(playerUids[index]);
                if (string.IsNullOrWhiteSpace(uid) ||
                    sequence.controlledPlayerUids.Contains(uid, StringComparer.OrdinalIgnoreCase))
                {
                    continue;
                }

                sequence.controlledPlayerUids.Add(uid);
            }
        }

        private static float ResolveCompletionDistance(GtexVisualCommandType type)
        {
            switch (type)
            {
                case GtexVisualCommandType.Pass:
                    return 1.45f;
                case GtexVisualCommandType.ThroughPass:
                case GtexVisualCommandType.Cross:
                    return 2.15f;
                case GtexVisualCommandType.KeeperSave:
                    return 2.2f;
                default:
                    return 1.5f;
            }
        }

        private static string NormalizeSequenceId(string value)
        {
            var normalized = string.IsNullOrWhiteSpace(value) ? CentralBuildupShot : value.Trim().ToLowerInvariant();
            normalized = normalized.Replace("_", "-");
            return normalized == WideCrossChance || normalized == CutbackChance ? normalized : CentralBuildupShot;
        }

        private static string NormalizeTeamId(string value)
        {
            var normalized = string.IsNullOrWhiteSpace(value) ? "home" : value.Trim().ToLowerInvariant();
            return normalized == "home" || normalized == "away" ? normalized : string.Empty;
        }

        private sealed class Participants
        {
            public string teamId;
            public string opponentTeamId;
            public List<GtexOriginalPlayerVisualProxy> attackers;
            public List<GtexOriginalPlayerVisualProxy> defenders;
            public GtexOriginalPlayerVisualProxy carrier;
            public GtexOriginalPlayerVisualProxy support;
            public GtexOriginalPlayerVisualProxy runner;
            public GtexOriginalPlayerVisualProxy presser;
            public GtexOriginalPlayerVisualProxy marker;
            public GtexOriginalPlayerVisualProxy keeper;
            public Vector3 goal;
        }
    }
}
