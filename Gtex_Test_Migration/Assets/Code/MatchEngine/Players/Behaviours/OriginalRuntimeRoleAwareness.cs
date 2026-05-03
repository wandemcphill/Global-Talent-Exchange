using System.Linq;
using FStudio.Data;
using FStudio.GTEX.Core;
using FStudio.MatchEngine.Balls;
using FStudio.MatchEngine.Enums;
using FStudio.MatchEngine.FieldPositions;
using UnityEngine;
using DataPositions = FStudio.Data.Positions;

namespace FStudio.MatchEngine.Players.Behaviours {
    internal enum OriginalRuntimePlayerRole {
        Goalkeeper,
        Defender,
        Midfielder,
        Forward
    }

    internal static class OriginalRuntimeRoleAwareness {
        private const int MaxLooseBallChasers = 2;
        private const int MaxPressers = 2;
        private const float GoalkeeperMaxAdvance = 16f;
        private const float GoalkeeperBoxHalfWidth = 19.5f;
        private const float GoalkeeperLooseBallHalfWidth = 17f;
        private const float GoalkeeperLooseBallMaxAdvance = 14.5f;

        public static OriginalRuntimePlayerRole RoleOf(PlayerBase player) {
            if (player == null || player.IsGK || HasAny(player, DataPositions.GK)) {
                return OriginalRuntimePlayerRole.Goalkeeper;
            }

            if (HasAny(player,
                DataPositions.RB,
                DataPositions.LB,
                DataPositions.CB,
                DataPositions.CB_R,
                DataPositions.CB_L)) {
                return OriginalRuntimePlayerRole.Defender;
            }

            if (HasAny(player,
                DataPositions.LW,
                DataPositions.RW,
                DataPositions.ST,
                DataPositions.ST_L,
                DataPositions.ST_R)) {
                return OriginalRuntimePlayerRole.Forward;
            }

            return OriginalRuntimePlayerRole.Midfielder;
        }

        public static bool CanUseOpenPlayBehaviour(MatchStatus matchStatus) {
            return !IsActive() || matchStatus.HasFlag(MatchStatus.Playing);
        }

        public static bool CanOfferSupport(PlayerBase player, PlayerBase holder, PlayerBase[] teammates, int supportIndex) {
            if (!IsActive() || player == null || holder == null || teammates == null || player.IsGK || player == holder) {
                return false;
            }

            if (supportIndex > 2) {
                return false;
            }

            var role = RoleOf(player);
            if (role == OriginalRuntimePlayerRole.Defender) {
                var defendersAhead = teammates
                    .Where(x => x != null && x != holder && x != player && RoleOf(x) == OriginalRuntimePlayerRole.Defender)
                    .Count(x => x.PlayerFieldProgress > player.PlayerFieldProgress + 0.04f);

                if (holder.PlayerFieldProgress < 0.55f || defendersAhead > 0) {
                    return false;
                }

                return supportIndex == 2;
            }

            if (role == OriginalRuntimePlayerRole.Midfielder) {
                return supportIndex <= 2;
            }

            return supportIndex <= 1 || holder.PlayerFieldProgress >= 0.48f;
        }

        public static bool CanPress(PlayerBase player, PlayerBase holder, PlayerBase[] teammates, int maxPressers = MaxPressers) {
            if (!IsActive() || player == null || holder == null || player.IsGK) {
                return false;
            }

            return PressureRank(player, holder, teammates, maxPressers) >= 0;
        }

        public static bool CanJoinAttack(PlayerBase player, Ball ball, PlayerBase[] teammates) {
            if (!IsActive() || player == null || ball == null || teammates == null || player.IsGK) {
                return false;
            }

            var holder = ball.HolderPlayer;
            if (holder == null || holder.GameTeam != player.GameTeam || holder == player) {
                return false;
            }

            var progress = player.GameTeam.BallProgress;
            var budget = progress >= 0.72f ? 3 : 2;

            var ranked = teammates
                .Where(x =>
                    x != null &&
                    x != holder &&
                    !x.IsGK &&
                    !x.IsInOffside &&
                    x.PlayerController != null &&
                    x.PlayerController.IsPhysicsEnabled &&
                    (RoleOf(x) != OriginalRuntimePlayerRole.Defender || progress >= 0.72f))
                .OrderBy(x => JoinAttackScore(x, ball.transform.position, progress))
                .Take(budget)
                .ToArray();

            return System.Array.IndexOf(ranked, player) >= 0;
        }

        public static int PressureRank(PlayerBase player, PlayerBase holder, PlayerBase[] teammates, int maxPressers = MaxPressers) {
            if (player == null || holder == null || teammates == null) {
                return -1;
            }

            var ranked = teammates
                .Where(x =>
                    x != null &&
                    !x.IsGK &&
                    !x.CaughtInOffside &&
                    x.PlayerController != null &&
                    x.PlayerController.IsPhysicsEnabled)
                .OrderBy(x => PressureScore(x, holder))
                .Take(Mathf.Max(1, maxPressers))
                .ToArray();

            return System.Array.IndexOf(ranked, player);
        }

        public static bool TryGetLooseBallChaseRole(
            PlayerBase player,
            PlayerBase[] teammates,
            GoalNet goalNet,
            Ball ball,
            int fieldEndX,
            int fieldEndY,
            out BallChasingBehaviour.BallChasingResult result) {
            result = BallChasingBehaviour.BallChasingResult.None;

            if (!IsActive() || player == null || teammates == null || ball == null || ball.HolderPlayer != null) {
                return false;
            }

            var ballPosition = ball.transform.position;
            var ranked = teammates
                .Where(x =>
                    x != null &&
                    x.PlayerController != null &&
                    x.PlayerController.IsPhysicsEnabled &&
                    !x.CaughtInOffside &&
                    (!x.IsGK || CanGoalkeeperLeaveBoxForBall(x, ballPosition, goalNet, fieldEndX, fieldEndY)))
                .OrderBy(x => LooseBallScore(x, ballPosition))
                .Take(MaxLooseBallChasers)
                .ToArray();

            var index = System.Array.IndexOf(ranked, player);
            if (index < 0) {
                return false;
            }

            result = index == 0
                ? BallChasingBehaviour.BallChasingResult.ChaserTrue
                : BallChasingBehaviour.BallChasingResult.SecondaryChaser;
            return true;
        }

        public static bool CanGoalkeeperLeaveBoxForBall(
            PlayerBase goalkeeper,
            Vector3 ballPosition,
            GoalNet goalNet,
            int fieldEndX,
            int fieldEndY) {
            if (!IsActive() || goalkeeper == null || !goalkeeper.IsGK || goalNet == null) {
                return true;
            }

            if (ballPosition.x < 0f || ballPosition.x > fieldEndX || ballPosition.z < 0f || ballPosition.z > fieldEndY) {
                return false;
            }

            var forwardDistance = (ballPosition.x - goalNet.Position.x) * goalNet.Direction.x;
            var lateralDistance = Mathf.Abs(ballPosition.z - fieldEndY * 0.5f);

            return forwardDistance >= -0.25f &&
                forwardDistance <= GoalkeeperLooseBallMaxAdvance &&
                lateralDistance <= GoalkeeperLooseBallHalfWidth;
        }

        public static Vector3 ClampGoalkeeperPoint(
            Vector3 point,
            GoalNet goalNet,
            int fieldEndX,
            int fieldEndY,
            float maxAdvance = GoalkeeperMaxAdvance) {
            if (!IsActive() || goalNet == null) {
                return point;
            }

            var forwardDistance = (point.x - goalNet.Position.x) * goalNet.Direction.x;
            forwardDistance = Mathf.Clamp(forwardDistance, 0.85f, maxAdvance);

            point.x = goalNet.Position.x + forwardDistance * goalNet.Direction.x;
            point.x = Mathf.Clamp(point.x, 0.85f, fieldEndX - 0.85f);
            point.z = Mathf.Clamp(point.z, fieldEndY * 0.5f - GoalkeeperBoxHalfWidth, fieldEndY * 0.5f + GoalkeeperBoxHalfWidth);
            return point;
        }

        public static Vector3 DampShapeMovement(PlayerBase player, Vector3 currentPosition, Vector3 desiredPosition, bool teamHasBall) {
            if (!IsActive() || player == null || player.IsHoldingBall || player.IsGK) {
                return desiredPosition;
            }

            var role = RoleOf(player);
            var distance = Vector3.Distance(currentPosition, desiredPosition);

            if (distance <= 2.25f) {
                return desiredPosition;
            }

            var maxStep = 7.5f;
            if (teamHasBall) {
                maxStep = role == OriginalRuntimePlayerRole.Defender ? 4.5f : 7f;
            } else {
                maxStep = role == OriginalRuntimePlayerRole.Forward ? 5f : 6.5f;
            }

            return currentPosition + Vector3.ClampMagnitude(desiredPosition - currentPosition, maxStep);
        }

        private static bool IsActive() {
            return GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime();
        }

        private static float PressureScore(PlayerBase player, PlayerBase holder) {
            var distance = Vector3.Distance(player.Position, holder.Position);
            var role = RoleOf(player);
            var rolePenalty =
                role == OriginalRuntimePlayerRole.Defender ? 0.35f :
                role == OriginalRuntimePlayerRole.Midfielder ? 0f :
                0.8f;
            var wrongSidePenalty = IsGoalSideOfHolder(player, holder) ? 0f : 2.25f;
            return distance + rolePenalty + wrongSidePenalty;
        }

        private static float LooseBallScore(PlayerBase player, Vector3 ballPosition) {
            var distance = BallChasingBehaviour.BallChasingDistance(player);
            var role = RoleOf(player);
            var rolePenalty =
                role == OriginalRuntimePlayerRole.Goalkeeper ? 5.5f :
                role == OriginalRuntimePlayerRole.Defender ? 0.35f :
                role == OriginalRuntimePlayerRole.Midfielder ? 0f :
                0.75f;
            var heightPenalty = Mathf.Max(0f, ballPosition.y - 0.7f) * 8f;
            return distance + rolePenalty + heightPenalty;
        }

        private static float JoinAttackScore(PlayerBase player, Vector3 ballPosition, float teamProgress) {
            var role = RoleOf(player);
            var distance = Vector3.Distance(player.Position, ballPosition);
            var rolePenalty =
                role == OriginalRuntimePlayerRole.Forward ? 0f :
                role == OriginalRuntimePlayerRole.Midfielder ? 1.25f :
                7f;
            var alreadyAdvancedPenalty = player.PlayerFieldProgress > teamProgress + 0.16f ? 3f : 0f;
            return distance * 0.55f + rolePenalty + alreadyAdvancedPenalty - player.PlayerFieldProgress * 2f;
        }

        private static bool IsGoalSideOfHolder(PlayerBase defender, PlayerBase holder) {
            var holderToGoal = defender.GameTeam == null ? Vector3.zero : defender.GoalDirection * -1f;
            if (holderToGoal.sqrMagnitude <= 0.01f) {
                return true;
            }

            var holderToDefender = defender.Position - holder.Position;
            holderToDefender.y = 0f;
            return Vector3.Dot(holderToGoal.normalized, holderToDefender.normalized) > -0.1f;
        }

        private static bool HasAny(PlayerBase player, params DataPositions[] positions) {
            if (player == null || player.MatchPlayer == null) {
                return false;
            }

            var playerPosition = player.MatchPlayer.Position;
            for (int i = 0; i < positions.Length; i++) {
                if (playerPosition.HasFlag(positions[i])) {
                    return true;
                }
            }

            return false;
        }
    }
}
