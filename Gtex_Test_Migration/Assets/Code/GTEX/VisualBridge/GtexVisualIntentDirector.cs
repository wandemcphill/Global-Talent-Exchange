using System.Collections.Generic;
using UnityEngine;

namespace FStudio.GTEX.VisualBridge
{
    public sealed class GtexVisualIntentDirector : MonoBehaviour
    {
        [SerializeField] private GtexVisualMatchDirector matchDirector;
        [SerializeField] private GtexOriginalSimAdapter adapter;

        [Header("Intent Timing")]
        [SerializeField] private float intentTickSeconds = 0.45f;
        [SerializeField] private float supportCommitSeconds = 1.0f;
        [SerializeField] private float markingCommitSeconds = 1.2f;

        [Header("Shooting")]
        [SerializeField] private float shootDistance = 25f;
        [SerializeField] private float clearShotDistance = 18f;
        [SerializeField] private float minShootAngleDot = 0.45f;
        [SerializeField] private float shootCooldownSeconds = 2.5f;

        [Header("Budgets")]
        [SerializeField] private int maxSupportRunners = 3;
        [SerializeField] private int maxMarkers = 4;
        [SerializeField] private int maxPressers = 1;

        private readonly Dictionary<string, float> markCommitUntil = new Dictionary<string, float>();
        private readonly Dictionary<string, string> currentMarks = new Dictionary<string, string>();
        private float nextIntentTick;
        private float nextAllowedShotTime;

        public void Bind(GtexVisualMatchDirector director, GtexOriginalSimAdapter simAdapter)
        {
            matchDirector = director;
            adapter = simAdapter;
        }

        private void Awake()
        {
            if (matchDirector == null)
            {
                matchDirector = GetComponent<GtexVisualMatchDirector>();
            }

            if (adapter == null)
            {
                adapter = GetComponent<GtexOriginalSimAdapter>();
            }
        }

        private void Update()
        {
            if (adapter == null || matchDirector == null || !adapter.IsRuntimeReady)
            {
                return;
            }

            if (matchDirector.IsScriptedReplayRunning)
            {
                return;
            }

            if (Time.time < nextIntentTick)
            {
                return;
            }

            nextIntentTick = Time.time + intentTickSeconds;
            TickIntent();
        }

        private void TickIntent()
        {
            var ballOwnerId = adapter.CurrentBallOwnerId;
            if (string.IsNullOrWhiteSpace(ballOwnerId))
            {
                return;
            }

            var possessionTeam = adapter.GetPlayerTeam(ballOwnerId);
            if (possessionTeam < 0)
            {
                return;
            }

            var defendingTeam = possessionTeam == 0 ? 1 : 0;
            var ballPos = adapter.GetBallPosition();
            var attackingGoal = adapter.GetAttackingGoalCenter(possessionTeam);

            TryShoot(ballOwnerId, ballPos, attackingGoal);

            var attackingAssigned = new HashSet<string>();
            AssignSupportRuns(possessionTeam, ballOwnerId, attackingGoal, attackingAssigned);
            var reservedDefenders = new HashSet<string>();
            AssignPresser(defendingTeam, ballOwnerId, ballPos, reservedDefenders);
            AssignDefensiveMarking(defendingTeam, possessionTeam, ballOwnerId, ballPos, reservedDefenders);
            AssignCoverSpace(defendingTeam, ballPos, attackingGoal, reservedDefenders);
            AssignHoldShape(possessionTeam, ballPos, ballOwnerId, attackingAssigned);
            AssignHoldShape(defendingTeam, ballPos, null, reservedDefenders);
        }

        private void TryShoot(string ballOwnerId, Vector3 ballPos, Vector3 attackingGoal)
        {
            if (Time.time < nextAllowedShotTime)
            {
                return;
            }

            var toGoal = attackingGoal - ballPos;
            toGoal.y = 0f;

            var distance = toGoal.magnitude;
            if (distance > shootDistance || distance <= 0.01f)
            {
                return;
            }

            var forward = adapter.GetPlayerForward(ballOwnerId);
            if (forward.sqrMagnitude > 0.01f && Vector3.Dot(forward.normalized, toGoal.normalized) < minShootAngleDot)
            {
                return;
            }

            if (!adapter.HasShootingLane(ballOwnerId, attackingGoal))
            {
                return;
            }

            var shootBias = distance <= clearShotDistance ? 1f : 0.55f;
            if (Random.value > shootBias)
            {
                return;
            }

            nextAllowedShotTime = Time.time + shootCooldownSeconds;

            var command = new GtexVisualCommand
            {
                type = GtexVisualCommandType.Shoot,
                actorPlayerId = ballOwnerId,
                targetWorldPosition = attackingGoal,
                outcome = "on_target",
                duration = 1.2f,
                urgency = 1f
            };

            matchDirector.HandleCommand(command);
            Debug.Log("[GTEX VisualIntent] Shoot -> actor=" + ballOwnerId + ", distance=" + distance.ToString("0.0"));
        }

        private void AssignSupportRuns(int possessionTeam, string ballOwnerId, Vector3 attackingGoal, HashSet<string> attackingAssigned)
        {
            var candidates = adapter.GetNearestTeamPlayers(
                possessionTeam,
                adapter.GetBallPosition(),
                ballOwnerId,
                6);

            var assigned = 0;
            for (var index = 0; index < candidates.Count && assigned < maxSupportRunners; index += 1)
            {
                var playerId = candidates[index];
                var supportPoint = adapter.ResolveSupportPoint(playerId, ballOwnerId, attackingGoal, assigned);
                if (supportPoint == Vector3.zero)
                {
                    continue;
                }

                attackingAssigned.Add(playerId);
                matchDirector.HandleCommand(new GtexVisualCommand
                {
                    type = GtexVisualCommandType.SupportRun,
                    actorPlayerId = playerId,
                    targetWorldPosition = supportPoint,
                    duration = supportCommitSeconds,
                    urgency = assigned == 0 ? 0.9f : 0.55f
                });

                assigned += 1;
            }
        }

        private void AssignDefensiveMarking(
            int defendingTeam,
            int attackingTeam,
            string ballOwnerId,
            Vector3 ballPos,
            HashSet<string> reservedDefenders)
        {
            var defenders = adapter.GetNearestTeamPlayers(defendingTeam, ballPos, null, 7);
            var attackers = adapter.GetNearestTeamPlayers(attackingTeam, ballPos, ballOwnerId, 7);

            var assigned = 0;
            for (var index = 0; index < defenders.Count && assigned < maxMarkers; index += 1)
            {
                var defenderId = defenders[index];
                if (reservedDefenders.Contains(defenderId) || Time.time < GetMarkCommitUntil(defenderId))
                {
                    continue;
                }

                var targetId = adapter.FindBestMarkTarget(defenderId, attackers);
                if (string.IsNullOrWhiteSpace(targetId))
                {
                    continue;
                }

                currentMarks[defenderId] = targetId;
                markCommitUntil[defenderId] = Time.time + markingCommitSeconds;
                reservedDefenders.Add(defenderId);

                matchDirector.HandleCommand(new GtexVisualCommand
                {
                    type = GtexVisualCommandType.MarkPlayer,
                    actorPlayerId = defenderId,
                    targetPlayerId = targetId,
                    duration = markingCommitSeconds,
                    urgency = 0.75f
                });

                assigned += 1;
            }
        }

        private void AssignPresser(int defendingTeam, string ballOwnerId, Vector3 ballPos, HashSet<string> reservedDefenders)
        {
            if (maxPressers <= 0)
            {
                return;
            }

            var presser = adapter.FindNearestDefenderToBall(defendingTeam, ballPos);
            if (string.IsNullOrWhiteSpace(presser))
            {
                return;
            }

            reservedDefenders.Add(presser);
            matchDirector.HandleCommand(new GtexVisualCommand
            {
                type = GtexVisualCommandType.PressBallCarrier,
                actorPlayerId = presser,
                targetPlayerId = ballOwnerId,
                duration = 0.8f,
                urgency = 1f
            });
        }

        private void AssignCoverSpace(int defendingTeam, Vector3 ballPos, Vector3 attackingGoal, HashSet<string> reservedDefenders)
        {
            var defenders = adapter.GetNearestTeamPlayers(defendingTeam, ballPos, null, 8);
            for (var index = 0; index < defenders.Count; index += 1)
            {
                var defenderId = defenders[index];
                if (reservedDefenders.Contains(defenderId))
                {
                    continue;
                }

                var coverPoint = adapter.ClampToPitch(Vector3.Lerp(ballPos, attackingGoal, 0.35f));
                matchDirector.HandleCommand(new GtexVisualCommand
                {
                    type = GtexVisualCommandType.CoverSpace,
                    actorPlayerId = defenderId,
                    targetWorldPosition = coverPoint,
                    duration = 0.9f,
                    urgency = 0.5f
                });
                return;
            }
        }

        private void AssignHoldShape(int teamId, Vector3 ballPos, string excludePlayerId, HashSet<string> reservedPlayers)
        {
            var players = adapter.GetNearestTeamPlayers(teamId, ballPos, excludePlayerId, 10);
            for (var index = 0; index < players.Count; index += 1)
            {
                var playerId = players[index];
                if (reservedPlayers.Contains(playerId))
                {
                    continue;
                }

                matchDirector.HandleCommand(new GtexVisualCommand
                {
                    type = GtexVisualCommandType.HoldShape,
                    actorPlayerId = playerId,
                    targetWorldPosition = adapter.GetPlayerPosition(playerId),
                    duration = 0.9f,
                    urgency = 0.25f
                });
            }
        }

        private float GetMarkCommitUntil(string playerId)
        {
            float value;
            return markCommitUntil.TryGetValue(playerId, out value) ? value : 0f;
        }
    }
}
