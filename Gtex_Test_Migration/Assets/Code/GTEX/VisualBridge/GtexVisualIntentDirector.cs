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
        [SerializeField] private float shootDistance = 28f;
        [SerializeField] private float clearShotDistance = 20f;
        [SerializeField] private float minShootFieldProgress = 0.52f;
        [SerializeField] private float minShootAngleDot = 0.25f;
        [SerializeField] private float shootCooldownSeconds = 2.5f;

        [Header("Passing")]
        [SerializeField] private float passCooldownSeconds = 1.35f;
        [SerializeField] private float minPossessionBeforePassSeconds = 0.55f;
        [SerializeField] private float pressurePassDistance = 5.2f;

        [Header("Budgets")]
        [SerializeField] private int maxSupportRunners = 3;
        [SerializeField] private int maxMarkers = 4;
        [SerializeField] private int maxPressers = 1;

        private readonly Dictionary<string, float> markCommitUntil = new Dictionary<string, float>();
        private readonly Dictionary<string, string> currentMarks = new Dictionary<string, string>();
        private float nextIntentTick;
        private float nextAllowedShotTime;
        private float nextAllowedPassTime;
        private string observedBallOwnerId = string.Empty;
        private float observedBallOwnerSince;

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
            if (adapter == null ||
                matchDirector == null ||
                !adapter.IsRuntimeReady ||
                !matchDirector.IsRuntimeReady ||
                !adapter.IsMatchActivelyPlaying)
            {
                return;
            }

            if (matchDirector.ShouldSuppressAmbientIntent)
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

            TrackBallOwner(ballOwnerId);

            var attackingAssigned = new HashSet<string>();
            AssignSupportRuns(possessionTeam, ballOwnerId, attackingGoal, attackingAssigned);

            if (TryShoot(ballOwnerId, ballPos, attackingGoal))
            {
                return;
            }

            if (TryPromptWideCross(possessionTeam, ballOwnerId, ballPos, attackingGoal))
            {
                return;
            }

            TryPromptPass(possessionTeam, ballOwnerId, ballPos, attackingGoal);

            var reservedDefenders = new HashSet<string>();
            AssignPresser(defendingTeam, ballOwnerId, ballPos, reservedDefenders);
            AssignDefensiveMarking(defendingTeam, possessionTeam, ballOwnerId, ballPos, reservedDefenders);
            AssignCoverSpace(defendingTeam, ballPos, attackingGoal, reservedDefenders);
        }

        private void TrackBallOwner(string ballOwnerId)
        {
            if (string.Equals(observedBallOwnerId, ballOwnerId, System.StringComparison.OrdinalIgnoreCase))
            {
                return;
            }

            observedBallOwnerId = ballOwnerId;
            observedBallOwnerSince = Time.time;
        }

        private bool TryShoot(string ballOwnerId, Vector3 ballPos, Vector3 attackingGoal)
        {
            if (Time.time < nextAllowedShotTime)
            {
                return false;
            }

            var toGoal = attackingGoal - ballPos;
            toGoal.y = 0f;

            var distance = toGoal.magnitude;
            if (distance > shootDistance || distance <= 0.01f)
            {
                return false;
            }

            if (distance > clearShotDistance && adapter.GetPlayerFieldProgress(ballOwnerId) < minShootFieldProgress)
            {
                return false;
            }

            var forward = adapter.GetPlayerForward(ballOwnerId);
            if (forward.sqrMagnitude > 0.01f && Vector3.Dot(forward.normalized, toGoal.normalized) < minShootAngleDot)
            {
                return false;
            }

            if (!adapter.HasShootingLane(ballOwnerId, attackingGoal))
            {
                return false;
            }

            var shootBias = distance <= clearShotDistance ? 1f : 0.72f;
            if (Random.value > shootBias)
            {
                return false;
            }

            nextAllowedShotTime = Time.time + shootCooldownSeconds;
            nextAllowedPassTime = Time.time + passCooldownSeconds;

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
            return true;
        }

        private void TryPromptPass(int possessionTeam, string ballOwnerId, Vector3 ballPos, Vector3 attackingGoal)
        {
            if (Time.time < nextAllowedPassTime ||
                Time.time - observedBallOwnerSince < minPossessionBeforePassSeconds ||
                !adapter.IsPlayerHoldingBall(ballOwnerId))
            {
                return;
            }

            var nearestOpponent = adapter.GetNearestOpponentDistance(possessionTeam, ballPos);
            var underPressure = nearestOpponent > 0f && nearestOpponent <= pressurePassDistance;
            var nearBoundary = adapter.IsNearPitchBoundary(ballPos, 4f);
            var fieldProgress = adapter.GetPlayerFieldProgress(ballOwnerId);
            var keeperOwner = adapter.IsGoalkeeper(ballOwnerId);
            var shouldPass =
                keeperOwner ||
                underPressure ||
                nearBoundary ||
                fieldProgress >= 0.34f ||
                Random.value < 0.32f;

            if (!shouldPass)
            {
                return;
            }

            var targetId = adapter.FindBestIntentPassTarget(possessionTeam, ballOwnerId, attackingGoal);
            if (string.IsNullOrWhiteSpace(targetId))
            {
                return;
            }

            nextAllowedPassTime = Time.time + passCooldownSeconds;
            matchDirector.HandleCommand(new GtexVisualCommand
            {
                type = GtexVisualCommandType.Pass,
                actorPlayerId = ballOwnerId,
                targetPlayerId = targetId,
                passStyle = GtexVisualPassStyle.Ground,
                duration = keeperOwner ? 1.25f : 1.1f,
                urgency = underPressure ? 0.95f : (keeperOwner ? 0.78f : 0.72f),
                isSuccessful = true,
                outcome = keeperOwner ? "keeper_distribution" : (underPressure ? "pressure_release" : "linkup")
            });

            Debug.Log("[GTEX VisualIntent] Pass -> actor=" + ballOwnerId + " target=" + targetId + " pressure=" + nearestOpponent.ToString("0.0") + " keeper=" + keeperOwner);
        }

        private bool TryPromptWideCross(int possessionTeam, string ballOwnerId, Vector3 ballPos, Vector3 attackingGoal)
        {
            if (Time.time < nextAllowedPassTime ||
                Time.time - observedBallOwnerSince < minPossessionBeforePassSeconds ||
                !adapter.IsPlayerHoldingBall(ballOwnerId) ||
                !adapter.IsWideAttackingCrossPosition(ballOwnerId, ballPos))
            {
                return false;
            }

            var targetId = adapter.FindBestIntentCrossTarget(possessionTeam, ballOwnerId, attackingGoal);
            if (string.IsNullOrWhiteSpace(targetId))
            {
                return false;
            }

            nextAllowedPassTime = Time.time + passCooldownSeconds;
            matchDirector.HandleCommand(new GtexVisualCommand
            {
                type = GtexVisualCommandType.Cross,
                actorPlayerId = ballOwnerId,
                targetPlayerId = targetId,
                targetWorldPosition = adapter.GetPlayerPosition(targetId),
                passStyle = GtexVisualPassStyle.Cross,
                duration = 1.25f,
                urgency = 0.86f,
                isSuccessful = true,
                outcome = "wide_cross"
            });

            Debug.Log("[GTEX VisualIntent] Cross -> actor=" + ballOwnerId + " target=" + targetId);
            return true;
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
