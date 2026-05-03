using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using FStudio.MatchEngine;
using FStudio.MatchEngine.Balls;
using FStudio.MatchEngine.Enums;
using UnityEngine;

namespace FStudio.GTEX.VisualBridge
{
    public sealed class GtexSequenceRunner : MonoBehaviour
    {
        private GtexVisualMatchDirector director;
        private GtexOriginalSimAdapter adapter;
        private Coroutine activeRoutine;

        public bool IsRunning => activeRoutine != null;

        public bool LastRunSucceeded { get; private set; }

        public string LastFailureReason { get; private set; } = string.Empty;

        public void Bind(GtexVisualMatchDirector matchDirector, GtexOriginalSimAdapter simAdapter)
        {
            director = matchDirector;
            adapter = simAdapter;
        }

        public Coroutine StartSequence(GtexVisualSequence sequence)
        {
            if (activeRoutine != null)
            {
                StopCoroutine(activeRoutine);
                activeRoutine = null;
                director?.ReleaseAuthority("sequence-restart");
            }

            activeRoutine = StartCoroutine(RunSequence(sequence));
            return activeRoutine;
        }

        public IEnumerator RunSequence(GtexVisualSequence sequence)
        {
            LastRunSucceeded = false;
            LastFailureReason = string.Empty;

            if (!ValidateSequence(sequence, out var reason))
            {
                Debug.LogError("[GTEX Sequence] Abort: " + reason);
                LastFailureReason = reason;
                activeRoutine = null;
                yield break;
            }

            Debug.Log("[GTEX Sequence] Start id=" + sequence.sequenceId + " team=" + sequence.teamId);
            if (sequence.preSequencePositions.Count > 0)
            {
                var positioningComplete = false;
                yield return RunPreSequencePositioning(sequence, value => positioningComplete = value);
                if (!positioningComplete)
                {
                    Debug.LogError("[GTEX Sequence] Abort id=" + sequence.sequenceId + ": " + LastFailureReason);
                    activeRoutine = null;
                    yield break;
                }
            }

            if (!director.RequestAuthorityLease(
                    sequence.teamId,
                    sequence.controlledPlayerUids,
                    sequence.leaseDurationSeconds,
                    allowCrossTeam: true))
            {
                Debug.LogError("[GTEX Sequence] Abort id=" + sequence.sequenceId + ": authority lease rejected.");
                LastFailureReason = "authority lease rejected";
                director.ReleaseAuthority("sequence-lease-rejected");
                activeRoutine = null;
                yield break;
            }

            var completed = false;
            try
            {
                for (var index = 0; index < sequence.steps.Count; index += 1)
                {
                    var step = sequence.steps[index];
                    if (!ValidateStepLease(sequence, step, out reason))
                    {
                        if (step.required)
                        {
                            Debug.LogError("[GTEX Sequence] Abort id=" + sequence.sequenceId + ": " + reason);
                            LastFailureReason = reason;
                            yield break;
                        }

                        Debug.LogWarning("[GTEX Sequence] Skip optional step " + (index + 1).ToString("D2") + ": " + reason);
                        continue;
                    }

                    GtexVisualCommand preparedShotOutcomeCommand = null;
                    var preparedOutcomeLabel = string.Empty;
                    var preparedShotDistance = 0f;
                    var preparedShotAngle = 0f;
                    var preparedShotChance = 0f;
                    if (step.evaluateShotOutcome &&
                        step.command.type == GtexVisualCommandType.Shoot &&
                        !TryBuildShotOutcomeCommand(
                            sequence,
                            step,
                            out preparedShotOutcomeCommand,
                            out preparedOutcomeLabel,
                            out preparedShotDistance,
                            out preparedShotAngle,
                            out preparedShotChance,
                            out reason))
                    {
                        if (step.required)
                        {
                            Debug.LogError("[GTEX SEQ] Shot evaluation failed: " + reason);
                            LastFailureReason = "shot evaluation failed " + reason;
                            yield break;
                        }

                        Debug.LogWarning("[GTEX SEQ] Optional shot evaluation skipped: " + reason);
                        continue;
                    }

                    if (preparedShotOutcomeCommand != null)
                    {
                        step.command.outcome = preparedShotOutcomeCommand.type == GtexVisualCommandType.Goal
                            ? "goal"
                            : "saved";
                        if (preparedShotOutcomeCommand.type == GtexVisualCommandType.KeeperSave)
                        {
                            step.command.secondaryTargetPlayerId = preparedShotOutcomeCommand.actorPlayerId;
                        }
                    }

                    if (!RefreshSequenceLease(sequence, "step " + (index + 1).ToString("D2")))
                    {
                        yield break;
                    }

                    Debug.Log("[GTEX Sequence] Step " + (index + 1).ToString("D2") + " " + ResolveStepName(step));
                    GtexVisualAuthority.AllowCommandBallParticipants(step.command);
                    director.HandleCommand(step.command);

                    var stepComplete = false;
                    yield return WaitForStepCompletion(sequence, step, value => stepComplete = value);
                    if (!stepComplete && step.required)
                    {
                        Debug.LogError("[GTEX Sequence] Abort id=" + sequence.sequenceId + ": step failed " + ResolveStepName(step));
                        LastFailureReason = "step failed " + ResolveStepName(step);
                        yield break;
                    }

                    if (stepComplete && step.evaluateShotOutcome)
                    {
                        var outcomeComplete = false;
                        yield return ExecuteShotOutcomeBranch(
                            sequence,
                            step,
                            preparedShotOutcomeCommand,
                            preparedOutcomeLabel,
                            preparedShotDistance,
                            preparedShotAngle,
                            preparedShotChance,
                            value => outcomeComplete = value);
                        if (!outcomeComplete && step.required)
                        {
                            LastFailureReason = "shot outcome failed " + ResolveStepName(step);
                            yield break;
                        }
                    }

                    if (step.delayAfterSeconds > 0f)
                    {
                        yield return new WaitForSeconds(step.delayAfterSeconds);
                    }
                }

                completed = true;
                LastRunSucceeded = true;
            }
            finally
            {
                director.ReleaseAuthority(completed ? "sequence-complete" : "sequence-abort");
                Debug.Log(
                    completed
                        ? "[GTEX Sequence] Complete id=" + sequence.sequenceId
                        : "[GTEX Sequence] Aborted id=" + sequence.sequenceId);
                activeRoutine = null;
            }
        }

        private IEnumerator RunPreSequencePositioning(GtexVisualSequence sequence, Action<bool> result)
        {
            if (GtexVisualAuthority.IsLeaseActive)
            {
                LastFailureReason = "active authority lease before positioning";
                result(false);
                yield break;
            }

            var matchPlaying = false;
            yield return WaitForMatchPlaying(value => matchPlaying = value);
            if (!matchPlaying)
            {
                LastFailureReason = "match did not enter Playing before positioning";
                result(false);
                yield break;
            }

            var setupPlayers = ResolvePreSequencePlayerUids(sequence).ToArray();
            if (setupPlayers.Length == 0)
            {
                LastFailureReason = "no positioning players";
                result(false);
                yield break;
            }

            Debug.Log("[GTEX SEQ] Positioning phase start");
            if (!director.RequestAuthorityLease(sequence.teamId, setupPlayers, 6f))
            {
                LastFailureReason = "positioning authority lease rejected";
                result(false);
                yield break;
            }

            var completed = false;
            try
            {
                var ownerUid = GtexPlayerVisualMap.NormalizePlayerUid(sequence.preSequenceBallOwnerUid);
                if (!string.IsNullOrWhiteSpace(ownerUid))
                {
                    yield return EnsureBallOwnerForPositioning(ownerUid, sequence);
                    director.RequestAuthorityLease(sequence.teamId, setupPlayers, 6f);
                    if (!IsHolding(ownerUid))
                    {
                        LastFailureReason = "ball not ready with " + ownerUid;
                        result(false);
                        yield break;
                    }
                }

                var readyPlayers = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                var ballReadyLogged = false;
                var nextMoveIssue = 0f;
                var nextLeaseRefresh = Time.time + 4.75f;
                var nextBallWaitLog = 0f;
                var end = Time.time + Mathf.Max(2f, sequence.preSequenceTimeoutSeconds);
                while (Time.time < end)
                {
                    if (Time.time >= nextLeaseRefresh)
                    {
                        director.RequestAuthorityLease(sequence.teamId, setupPlayers, 6f);
                        nextLeaseRefresh = Time.time + 4.75f;
                    }

                    if (Time.time >= nextMoveIssue)
                    {
                        IssuePreSequenceMoves(sequence);
                        nextMoveIssue = Time.time + 1.05f;
                    }

                    for (var index = 0; index < sequence.preSequencePositions.Count; index += 1)
                    {
                        var target = sequence.preSequencePositions[index];
                        var playerUid = GtexPlayerVisualMap.NormalizePlayerUid(target.playerUid);
                        if (readyPlayers.Contains(playerUid))
                        {
                            continue;
                        }

                        if (IsPreSequencePlayerReady(target))
                        {
                            readyPlayers.Add(playerUid);
                            Debug.Log("[GTEX SEQ] " + ResolveReadyLabel(target) + " ready");
                        }
                    }

                    if (!ballReadyLogged && (string.IsNullOrWhiteSpace(ownerUid) || IsHolding(ownerUid)))
                    {
                        ballReadyLogged = true;
                        if (!string.IsNullOrWhiteSpace(ownerUid))
                        {
                            Debug.Log("[GTEX SEQ] Ball ready with " + ownerUid);
                        }
                    }

                    var allPlayersReady = readyPlayers.Count >= sequence.preSequencePositions.Count;
                    if (allPlayersReady &&
                        !string.IsNullOrWhiteSpace(ownerUid) &&
                        !IsHolding(ownerUid))
                    {
                        TryClaimBallAtFeet(ownerUid, 2.6f, 5.5f, "Pre-sequence ball");
                        if (!IsHolding(ownerUid) && Time.time >= nextBallWaitLog)
                        {
                            nextBallWaitLog = Time.time + 1f;
                            Debug.LogWarning("[GTEX SEQ] Waiting for ball ready with " + ownerUid + " before attacking sequence");
                        }
                    }

                    if (allPlayersReady &&
                        (string.IsNullOrWhiteSpace(ownerUid) || IsHolding(ownerUid)))
                    {
                        Debug.Log("[GTEX SEQ] Entering attacking sequence");
                        completed = true;
                        result(true);
                        yield break;
                    }

                    yield return null;
                }

                LastFailureReason = "positioning timeout";
                result(false);
            }
            finally
            {
                director.ReleaseAuthority(completed ? "pre-sequence-positioning-complete" : "pre-sequence-positioning-abort");
            }
        }

        private IEnumerator WaitForMatchPlaying(Action<bool> result)
        {
            const float waitSeconds = 6f;
            var end = Time.time + waitSeconds;
            var logged = false;
            while (Time.time < end)
            {
                if (IsMatchPlaying())
                {
                    result(true);
                    yield break;
                }

                if (!logged)
                {
                    logged = true;
                    Debug.Log("[GTEX SEQ] Waiting for kickoff before positioning");
                }

                yield return null;
            }

            if (!IsMatchPlaying() && adapter != null)
            {
                Debug.LogWarning("[GTEX SEQ] Kickoff wait elapsed; starting controlled replay play state before positioning.");
                adapter.StartMatch();
                yield return null;
            }

            result(IsMatchPlaying());
        }

        private static bool IsMatchPlaying()
        {
            var manager = MatchManager.Current;
            return manager != null && manager.MatchFlags.HasFlag(MatchStatus.Playing);
        }

        private IEnumerable<string> ResolvePreSequencePlayerUids(GtexVisualSequence sequence)
        {
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            for (var index = 0; index < sequence.preSequencePositions.Count; index += 1)
            {
                var playerUid = GtexPlayerVisualMap.NormalizePlayerUid(sequence.preSequencePositions[index].playerUid);
                if (!string.IsNullOrWhiteSpace(playerUid) && seen.Add(playerUid))
                {
                    yield return playerUid;
                }
            }

            var ownerUid = GtexPlayerVisualMap.NormalizePlayerUid(sequence.preSequenceBallOwnerUid);
            if (!string.IsNullOrWhiteSpace(ownerUid) && seen.Add(ownerUid))
            {
                yield return ownerUid;
            }
        }

        private IEnumerator EnsureBallOwnerForPositioning(string ownerUid, GtexVisualSequence sequence)
        {
            if (IsHolding(ownerUid))
            {
                yield break;
            }

            var owner = adapter.PlayerMap.ResolveProxy(ownerUid);
            if (owner == null)
            {
                yield break;
            }

            var ballPosition = adapter.GetBallPosition();
            if (DistanceXZ(owner.Root.position, ballPosition) > 2.2f)
            {
                var collectEnd = Time.time + Mathf.Min(5f, Mathf.Max(2f, sequence.preSequenceTimeoutSeconds * 0.35f));
                while (Time.time < collectEnd && DistanceXZ(owner.Root.position, ballPosition) > 2.2f)
                {
                    owner.MoveToSupportPoint(ballPosition, 1f, 0.9f);
                    yield return new WaitForSeconds(0.55f);
                    ballPosition = adapter.GetBallPosition();
                }
            }

            director.HandleCommand(new GtexVisualCommand
            {
                type = GtexVisualCommandType.AssignPossession,
                actorPlayerId = ownerUid
            });

            var possessionEnd = Time.time + 1.5f;
            while (Time.time < possessionEnd && !IsHolding(ownerUid))
            {
                yield return null;
            }
        }

        private void IssuePreSequenceMoves(GtexVisualSequence sequence)
        {
            var ownerUid = GtexPlayerVisualMap.NormalizePlayerUid(sequence.preSequenceBallOwnerUid);
            for (var index = 0; index < sequence.preSequencePositions.Count; index += 1)
            {
                var target = sequence.preSequencePositions[index];
                var playerUid = GtexPlayerVisualMap.NormalizePlayerUid(target.playerUid);
                var proxy = adapter.PlayerMap.ResolveProxy(playerUid);
                if (proxy == null)
                {
                    continue;
                }

                var targetPoint = adapter.ClampToPitch(target.targetWorldPosition);
                if (!string.IsNullOrWhiteSpace(ownerUid) &&
                    string.Equals(playerUid, ownerUid, StringComparison.OrdinalIgnoreCase) &&
                    IsHolding(ownerUid))
                {
                    proxy.DribbleToward(targetPoint);
                }
                else
                {
                    proxy.MoveToSupportPoint(targetPoint, Mathf.Clamp01(target.urgency), 1.2f);
                }
            }
        }

        private bool IsPreSequencePlayerReady(GtexVisualSequencePositionTarget target)
        {
            if (target == null)
            {
                return false;
            }

            var playerUid = GtexPlayerVisualMap.NormalizePlayerUid(target.playerUid);
            if (string.IsNullOrWhiteSpace(playerUid))
            {
                return false;
            }

            var threshold = target.thresholdDistance > 0.1f ? target.thresholdDistance : 2f;
            return DistanceXZ(adapter.GetPlayerPosition(playerUid), target.targetWorldPosition) <= threshold;
        }

        private static string ResolveReadyLabel(GtexVisualSequencePositionTarget target)
        {
            if (target != null && !string.IsNullOrWhiteSpace(target.readyLabel))
            {
                return target.readyLabel;
            }

            return target != null ? target.playerUid : "player";
        }

        private IEnumerator ExecuteShotOutcomeBranch(
            GtexVisualSequence sequence,
            GtexVisualSequenceStep shotStep,
            GtexVisualCommand outcomeCommand,
            string outcomeLabel,
            float distance,
            float angle,
            float chance,
            Action<bool> result)
        {
            if (outcomeCommand == null)
            {
                Debug.LogError("[GTEX SEQ] Shot outcome failed: missing prepared outcome.");
                result(false);
                yield break;
            }

            if (!ValidateStepLease(
                    sequence,
                    new GtexVisualSequenceStep { command = outcomeCommand, label = outcomeLabel },
                    out var reason))
            {
                Debug.LogError("[GTEX SEQ] Shot outcome rejected: " + reason);
                result(false);
                yield break;
            }

            Debug.Log(
                "[GTEX SEQ] Shot evaluation: distance=" + distance.ToString("0.0") +
                " angle=" + angle.ToString("0.0") +
                " chance=" + chance.ToString("0.00") +
                " -> outcome=" + outcomeLabel);

            director.HandleCommand(outcomeCommand);

            if (outcomeCommand.type == GtexVisualCommandType.KeeperSave)
            {
                var outcomeStep = new GtexVisualSequenceStep
                {
                    command = outcomeCommand,
                    label = outcomeLabel,
                    timeoutSeconds = 2.4f,
                    completionMode = GtexVisualSequenceCompletionMode.KeeperOutcome,
                    completionWorldPosition = shotStep.command.targetWorldPosition,
                    completionDistance = 2.2f
                };

                var keeperComplete = false;
                yield return WaitForStepCompletion(sequence, outcomeStep, value => keeperComplete = value);
                if (!keeperComplete)
                {
                    Debug.LogWarning("[GTEX Sequence] KeeperSave reaction window elapsed; treating outcome as resolved by original runtime.");
                }

                result(true);
                yield break;
            }

            yield return new WaitForSeconds(0.35f);
            result(true);
        }

        private bool TryBuildShotOutcomeCommand(
            GtexVisualSequence sequence,
            GtexVisualSequenceStep shotStep,
            out GtexVisualCommand outcomeCommand,
            out string outcomeLabel,
            out float distance,
            out float angle,
            out float chance,
            out string reason)
        {
            outcomeCommand = null;
            outcomeLabel = string.Empty;
            distance = 0f;
            angle = 0f;
            chance = 0f;
            reason = string.Empty;

            if (shotStep == null || shotStep.command == null)
            {
                reason = "shot step missing";
                return false;
            }

            var shooterId = GtexPlayerVisualMap.NormalizePlayerUid(shotStep.command.actorPlayerId);
            var shooter = adapter.PlayerMap.ResolveProxy(shooterId);
            if (shooter == null)
            {
                reason = "shooter missing: " + shooterId;
                return false;
            }

            var goalTarget = ResolveShotGoalTarget(sequence, shotStep);
            if (goalTarget.sqrMagnitude <= 0.001f)
            {
                reason = "shot target missing";
                return false;
            }

            var shooterPosition = shooter.Root.position;
            var toGoal = goalTarget - shooterPosition;
            toGoal.y = 0f;
            distance = toGoal.magnitude;
            if (distance <= 0.1f)
            {
                reason = "shot distance invalid";
                return false;
            }

            var forward = adapter.GetPlayerForward(shooterId);
            forward.y = 0f;
            if (forward.sqrMagnitude <= 0.001f)
            {
                forward = toGoal;
            }

            angle = Vector3.Angle(forward.normalized, toGoal.normalized);
            var laneClear = adapter.HasShootingLane(shooterId, goalTarget);
            chance = ResolveGoalChance(distance, angle, laneClear);
            var goalSelected = UnityEngine.Random.value < chance;

            if (goalSelected)
            {
                director.ResolveCurrentVisualScore(out var homeScore, out var awayScore, out var minute);
                if (string.Equals(sequence.teamId, "away", StringComparison.OrdinalIgnoreCase))
                {
                    awayScore += 1;
                }
                else
                {
                    homeScore += 1;
                }

                outcomeLabel = "Goal";
                outcomeCommand = new GtexVisualCommand
                {
                    type = GtexVisualCommandType.Goal,
                    actorPlayerId = shooterId,
                    teamId = sequence.teamId,
                    targetWorldPosition = goalTarget,
                    homeScore = homeScore,
                    awayScore = awayScore,
                    matchMinute = minute,
                    outcome = "sequence_goal",
                    isSuccessful = true
                };
                return true;
            }

            var keeperId = ResolveOutcomeKeeperUid(sequence, shotStep);
            if (string.IsNullOrWhiteSpace(keeperId))
            {
                reason = "opposing goalkeeper missing";
                return false;
            }

            outcomeLabel = "KeeperSave";
            outcomeCommand = new GtexVisualCommand
            {
                type = GtexVisualCommandType.KeeperSave,
                actorPlayerId = keeperId,
                targetWorldPosition = goalTarget,
                matchMinute = 0f,
                outcome = "sequence_save",
                isSuccessful = true
            };
            return true;
        }

        private Vector3 ResolveShotGoalTarget(GtexVisualSequence sequence, GtexVisualSequenceStep shotStep)
        {
            if (shotStep.command.targetWorldPosition.sqrMagnitude > 0.001f)
            {
                return shotStep.command.targetWorldPosition;
            }

            var teamIndex = string.Equals(sequence.teamId, "away", StringComparison.OrdinalIgnoreCase) ? 1 : 0;
            return adapter.GetAttackingGoalCenter(teamIndex);
        }

        private string ResolveOutcomeKeeperUid(GtexVisualSequence sequence, GtexVisualSequenceStep shotStep)
        {
            var keeperUid = GtexPlayerVisualMap.NormalizePlayerUid(shotStep.completionPlayerUid);
            if (GtexPlayerVisualMap.IsSideQualifiedPlayerUid(keeperUid) &&
                adapter.PlayerMap.ResolveProxy(keeperUid) != null)
            {
                return keeperUid;
            }

            var opposingTeam = string.Equals(sequence.teamId, "away", StringComparison.OrdinalIgnoreCase) ? "home" : "away";
            var keeper = adapter.PlayerMap.FindGoalkeeper(opposingTeam);
            return keeper != null ? keeper.GtexPlayerId : string.Empty;
        }

        private static float ResolveGoalChance(float distance, float angle, bool laneClear)
        {
            var chance = 0.12f;
            if (distance <= 12f && angle <= 50f)
            {
                chance = 0.74f;
            }
            else if (distance <= 18f && angle <= 42f)
            {
                chance = 0.58f;
            }
            else if (distance <= 25f && angle <= 32f)
            {
                chance = 0.34f;
            }

            if (!laneClear)
            {
                chance *= 0.35f;
            }

            return Mathf.Clamp01(chance);
        }

        private bool ValidateSequence(GtexVisualSequence sequence, out string reason)
        {
            reason = string.Empty;
            if (director == null)
            {
                reason = "director missing";
                return false;
            }

            if (adapter == null || adapter.PlayerMap == null)
            {
                reason = "adapter/player map missing";
                return false;
            }

            if (sequence == null)
            {
                reason = "sequence missing";
                return false;
            }

            if (string.IsNullOrWhiteSpace(sequence.sequenceId))
            {
                reason = "sequenceId missing";
                return false;
            }

            if (!IsTeamId(sequence.teamId))
            {
                reason = "teamId must be home or away";
                return false;
            }

            if (sequence.controlledPlayerUids.Count == 0)
            {
                reason = "no controlled players";
                return false;
            }

            for (var index = 0; index < sequence.controlledPlayerUids.Count; index += 1)
            {
                var uid = sequence.controlledPlayerUids[index];
                if (!adapter.PlayerMap.TryGetCommandProxy(uid, out _, out var playerReason))
                {
                    reason = "invalid controlled player " + uid + ": " + playerReason;
                    return false;
                }
            }

            if (sequence.steps.Count == 0)
            {
                reason = "no steps";
                return false;
            }

            return true;
        }

        private bool ValidateStepLease(GtexVisualSequence sequence, GtexVisualSequenceStep step, out string reason)
        {
            reason = string.Empty;
            if (step == null || step.command == null)
            {
                reason = "step/command missing";
                return false;
            }

            if (!IsLeaseCommandPlayerValid(sequence, step.command.actorPlayerId, out reason))
            {
                return false;
            }

            if (!string.IsNullOrWhiteSpace(step.command.targetPlayerId) &&
                RequiresControlledTarget(step.command.type) &&
                !IsLeaseCommandPlayerValid(sequence, step.command.targetPlayerId, out reason))
            {
                return false;
            }

            return true;
        }

        private bool IsLeaseCommandPlayerValid(GtexVisualSequence sequence, string playerUid, out string reason)
        {
            reason = string.Empty;
            if (string.IsNullOrWhiteSpace(playerUid))
            {
                return true;
            }

            var normalized = GtexPlayerVisualMap.NormalizePlayerUid(playerUid);
            if (!GtexPlayerVisualMap.IsSideQualifiedPlayerUid(normalized))
            {
                reason = "side-qualified PlayerUid required: " + playerUid;
                return false;
            }

            if (!sequence.controlledPlayerUids.Contains(normalized, StringComparer.OrdinalIgnoreCase))
            {
                reason = "command references player outside lease: " + normalized;
                return false;
            }

            return true;
        }

        private IEnumerator WaitForStepCompletion(GtexVisualSequence sequence, GtexVisualSequenceStep step, Action<bool> result)
        {
            var mode = ResolveCompletionMode(step);
            if (mode == GtexVisualSequenceCompletionMode.DelayOnly)
            {
                result(true);
                yield break;
            }

            Debug.Log("[GTEX Sequence] Waiting for " + ResolveStepName(step) + " completion");
            var timeout = Mathf.Max(0.1f, step.timeoutSeconds);
            var end = Time.time + timeout;
            var nextLeaseRefresh = Time.time + 2.5f;
            while (Time.time < end)
            {
                if (Time.time >= nextLeaseRefresh)
                {
                    if (!RefreshSequenceLease(sequence, "waiting for " + ResolveStepName(step)))
                    {
                        result(false);
                        yield break;
                    }

                    nextLeaseRefresh = Time.time + 2.5f;
                }

                if (HasInterception(step))
                {
                    result(false);
                    yield break;
                }

                if (IsStepComplete(step, mode))
                {
                    Debug.Log("[GTEX Sequence] " + ResolveStepName(step) + " complete");
                    Debug.Log("[GTEX Sequence] Executing next step");
                    result(true);
                    yield break;
                }

                yield return null;
            }

            Debug.LogError("[GTEX Sequence] Timeout waiting for " + ResolveStepName(step) + " completion");
            result(false);
        }

        private bool RefreshSequenceLease(GtexVisualSequence sequence, string reason)
        {
            if (sequence == null || director == null)
            {
                LastFailureReason = "authority refresh failed: sequence/director missing";
                return false;
            }

            if (director.RefreshAuthorityLease(
                    sequence.teamId,
                    sequence.controlledPlayerUids,
                    sequence.leaseDurationSeconds,
                    allowCrossTeam: true))
            {
                return true;
            }

            LastFailureReason = "authority refresh failed during " + reason;
            Debug.LogError("[GTEX Sequence] Abort id=" + sequence.sequenceId + ": " + LastFailureReason);
            return false;
        }

        private bool IsStepComplete(GtexVisualSequenceStep step, GtexVisualSequenceCompletionMode mode)
        {
            var command = step.command;
            switch (mode)
            {
                case GtexVisualSequenceCompletionMode.Possession:
                    return IsHolding(command.actorPlayerId);
                case GtexVisualSequenceCompletionMode.PlayerAtPoint:
                    return DistanceXZ(adapter.GetPlayerPosition(command.actorPlayerId), ResolveCompletionPoint(step)) <= ResolveCompletionDistance(step, 1.5f);
                case GtexVisualSequenceCompletionMode.PassReceived:
                    return IsHolding(command.targetPlayerId) ||
                           TryClaimBallAtFeet(
                               command.targetPlayerId,
                               ResolveCompletionDistance(step, 1.45f),
                               3.2f,
                               "Pass reception");
                case GtexVisualSequenceCompletionMode.ThroughPassReachable:
                {
                    var receiverPoint = string.IsNullOrWhiteSpace(command.targetPlayerId)
                        ? ResolveCompletionPoint(step)
                        : adapter.GetPlayerPosition(command.targetPlayerId);
                    if (!string.IsNullOrWhiteSpace(command.targetPlayerId))
                    {
                        return IsHolding(command.targetPlayerId) ||
                               TryClaimBallAtFeet(
                                   command.targetPlayerId,
                                   ResolveCompletionDistance(step, 2.15f),
                                   4.2f,
                                   "ThroughPass reception");
                    }

                    return DistanceXZ(adapter.GetBallPosition(), receiverPoint) <= ResolveCompletionDistance(step, 2.15f);
                }
                case GtexVisualSequenceCompletionMode.ShotReleased:
                    return !IsHolding(command.actorPlayerId) &&
                           (ResolveBallSpeed() >= 1.5f ||
                            DistanceXZ(adapter.GetBallPosition(), adapter.GetPlayerPosition(command.actorPlayerId)) >= 1.2f);
                case GtexVisualSequenceCompletionMode.KeeperOutcome:
                    return IsHolding(command.actorPlayerId) ||
                           DistanceXZ(adapter.GetBallPosition(), ResolveCompletionPoint(step)) <= ResolveCompletionDistance(step, 2.2f);
                default:
                    return true;
            }
        }

        private bool HasInterception(GtexVisualSequenceStep step)
        {
            if (Ball.Current == null || Ball.Current.HolderPlayer == null || adapter == null || adapter.PlayerMap == null)
            {
                return false;
            }

            var holder = Ball.Current.HolderPlayer;
            var actor = adapter.PlayerMap.ResolveProxy(step.command.actorPlayerId);
            var target = adapter.PlayerMap.ResolveProxy(step.command.targetPlayerId);
            if (actor != null && holder == actor.Player)
            {
                return false;
            }

            if (target != null && holder == target.Player)
            {
                return false;
            }

            if (step.command.type != GtexVisualCommandType.Pass &&
                step.command.type != GtexVisualCommandType.ThroughPass)
            {
                return false;
            }

            var holderProxy = adapter.PlayerMap.Proxies.FirstOrDefault(proxy => proxy != null && proxy.Player == holder);
            Debug.LogError("[GTEX Sequence] Action failed: ball holder changed to " + (holderProxy != null ? holderProxy.GtexPlayerId : holder.ToString()));
            return true;
        }

        private bool IsHolding(string playerUid)
        {
            if (Ball.Current == null || string.IsNullOrWhiteSpace(playerUid) || adapter == null || adapter.PlayerMap == null)
            {
                return false;
            }

            var proxy = adapter.PlayerMap.ResolveProxy(playerUid);
            return proxy != null && Ball.Current.HolderPlayer == proxy.Player;
        }

        private bool TryClaimBallAtFeet(string playerUid, float maxDistance, float maxSpeed, string reason)
        {
            if (Ball.Current == null || string.IsNullOrWhiteSpace(playerUid) || adapter == null || adapter.PlayerMap == null)
            {
                return false;
            }

            var proxy = adapter.PlayerMap.ResolveProxy(playerUid);
            if (proxy == null || proxy.Player == null)
            {
                return false;
            }

            var ball = Ball.Current;
            if (ball.HolderPlayer == proxy.Player)
            {
                return true;
            }

            if (ball.HolderPlayer != null)
            {
                return false;
            }

            var distance = DistanceXZ(ball.transform.position, proxy.Root.position);
            if (distance > maxDistance || ResolveBallSpeed() > maxSpeed)
            {
                return false;
            }

            adapter.GiveBallTo(proxy.GtexPlayerId);
            Debug.Log("[GTEX Sequence] " + reason + " trapped by " + proxy.GtexPlayerId + " distance=" + distance.ToString("0.00"));
            return IsHolding(proxy.GtexPlayerId);
        }

        private float ResolveBallSpeed()
        {
            return Ball.Current != null ? Ball.Current.Velocity.magnitude : 0f;
        }

        private static GtexVisualSequenceCompletionMode ResolveCompletionMode(GtexVisualSequenceStep step)
        {
            if (step.completionMode != GtexVisualSequenceCompletionMode.Auto)
            {
                return step.completionMode;
            }

            switch (step.command.type)
            {
                case GtexVisualCommandType.AssignPossession:
                    return GtexVisualSequenceCompletionMode.Possession;
                case GtexVisualCommandType.CarryBall:
                case GtexVisualCommandType.SupportRun:
                    return GtexVisualSequenceCompletionMode.PlayerAtPoint;
                case GtexVisualCommandType.Pass:
                    return GtexVisualSequenceCompletionMode.PassReceived;
                case GtexVisualCommandType.ThroughPass:
                case GtexVisualCommandType.Cross:
                    return GtexVisualSequenceCompletionMode.ThroughPassReachable;
                case GtexVisualCommandType.Shoot:
                    return GtexVisualSequenceCompletionMode.ShotReleased;
                case GtexVisualCommandType.KeeperSave:
                    return GtexVisualSequenceCompletionMode.KeeperOutcome;
                case GtexVisualCommandType.Goal:
                    return GtexVisualSequenceCompletionMode.DelayOnly;
                default:
                    return GtexVisualSequenceCompletionMode.DelayOnly;
            }
        }

        private static string ResolveStepName(GtexVisualSequenceStep step)
        {
            if (step != null && !string.IsNullOrWhiteSpace(step.label))
            {
                return step.label;
            }

            return step != null && step.command != null ? step.command.type.ToString() : "Unknown";
        }

        private static Vector3 ResolveCompletionPoint(GtexVisualSequenceStep step)
        {
            if (step.completionWorldPosition.sqrMagnitude > 0.001f)
            {
                return step.completionWorldPosition;
            }

            return step.command != null ? step.command.targetWorldPosition : Vector3.zero;
        }

        private static float ResolveCompletionDistance(GtexVisualSequenceStep step, float fallback)
        {
            return step.completionDistance > 0.01f ? step.completionDistance : fallback;
        }

        private static bool RequiresControlledTarget(GtexVisualCommandType type)
        {
            return type == GtexVisualCommandType.Pass ||
                   type == GtexVisualCommandType.ThroughPass ||
                   type == GtexVisualCommandType.MarkPlayer ||
                   type == GtexVisualCommandType.PressBallCarrier;
        }

        private static bool IsTeamId(string teamId)
        {
            return string.Equals(teamId, "home", StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(teamId, "away", StringComparison.OrdinalIgnoreCase);
        }

        private static float DistanceXZ(Vector3 a, Vector3 b)
        {
            a.y = 0f;
            b.y = 0f;
            return Vector3.Distance(a, b);
        }
    }
}
