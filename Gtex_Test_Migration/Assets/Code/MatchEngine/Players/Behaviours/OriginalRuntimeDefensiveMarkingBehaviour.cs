using System.Linq;
using FStudio.GTEX.Core;
using FStudio.MatchEngine.Enums;
using FStudio.MatchEngine.Players.PlayerController;
using UnityEngine;

namespace FStudio.MatchEngine.Players.Behaviours {
    public sealed class OriginalRuntimeDefensiveMarkingBehaviour : BaseBehaviour {
        private const int MaxMarkers = 4;
        private const float MaxMarkDistanceFromBall = 42f;
        private const float GoalSideDistance = 1.75f;

        private PlayerBase markTarget;

        public override bool Behave(bool isAlreadyActive) {
            if (!GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime() ||
                !OriginalRuntimeRoleAwareness.CanUseOpenPlayBehaviour(matchStatus) ||
                Player.IsHoldingBall ||
                Player.IsGK ||
                ball == null ||
                ball.HolderPlayer == null ||
                ball.HolderPlayer.GameTeam == Player.GameTeam ||
                ball.HolderPlayer.IsGKUntouchable ||
                !IsRoughValidated()) {
                markTarget = null;
                return false;
            }

            var holder = ball.HolderPlayer;
            if (OriginalRuntimeRoleAwareness.CanPress(Player, holder, teammates)) {
                markTarget = null;
                return false;
            }

            var ballPosition = ball.transform.position;
            var markers = teammates
                .Where(x =>
                    x != null &&
                    !x.IsGK &&
                    !x.CaughtInOffside &&
                    x.PlayerController != null &&
                    x.PlayerController.IsPhysicsEnabled &&
                    Vector3.Distance(x.Position, ballPosition) <= MaxMarkDistanceFromBall &&
                    !OriginalRuntimeRoleAwareness.CanPress(x, holder, teammates))
                .OrderBy(ResolveMarkerScore)
                .Take(MaxMarkers)
                .ToArray();

            var markerIndex = System.Array.IndexOf(markers, Player);
            if (markerIndex < 0) {
                markTarget = null;
                return false;
            }

            var targets = opponents
                .Where(x =>
                    x != null &&
                    x != holder &&
                    !x.IsGK &&
                    !x.IsInOffside &&
                    x.PlayerController != null &&
                    x.PlayerController.IsPhysicsEnabled)
                .OrderByDescending(ResolveAttackerDanger)
                .ToArray();

            if (targets.Length == 0) {
                markTarget = null;
                return false;
            }

            markTarget = targets[Mathf.Min(markerIndex, targets.Length - 1)];
            var targetPoint = ResolveGoalSideMarkPoint(markTarget.Position);
            Player.AvoidMarkers(teammates, ref targetPoint, 2.5f);
            KeepInField(ref targetPoint);

            if (!isAlreadyActive) {
                Debug.Log(
                    "[GTEX AI] Mark -> defender=" + Player +
                    " target=" + markTarget +
                    " point=" + targetPoint);
            }

            Player.CurrentAct = Acts.DefensiveTacticalPositioningBehaviour;
            Player.MoveTo(in deltaTime, targetPoint, false, MovementType.Normal);
            Player.FocusToBall(in deltaTime, ball);
            return true;
        }

        private float ResolveMarkerScore(PlayerBase candidate) {
            var role = OriginalRuntimeRoleAwareness.RoleOf(candidate);
            var rolePenalty =
                role == OriginalRuntimePlayerRole.Defender ? 0f :
                role == OriginalRuntimePlayerRole.Midfielder ? 0.65f :
                4f;
            var distancePenalty = Vector3.Distance(candidate.Position, ball.transform.position) * 0.35f;
            var depthPenalty = Mathf.Abs(candidate.PlayerFieldProgress - Player.GameTeam.BallProgress) * 4f;
            return rolePenalty + distancePenalty + depthPenalty;
        }

        private float ResolveAttackerDanger(PlayerBase attacker) {
            var role = OriginalRuntimeRoleAwareness.RoleOf(attacker);
            var roleBonus =
                role == OriginalRuntimePlayerRole.Forward ? 5f :
                role == OriginalRuntimePlayerRole.Midfielder ? 2.5f :
                0f;
            var ballDistancePenalty = Vector3.Distance(attacker.Position, ball.transform.position) * 0.18f;
            return attacker.PlayerFieldProgress * 8f + roleBonus - ballDistancePenalty;
        }

        private Vector3 ResolveGoalSideMarkPoint(Vector3 attackerPosition) {
            var fromGoalToAttacker = attackerPosition - goalNet.Position;
            fromGoalToAttacker.y = 0f;

            if (fromGoalToAttacker.sqrMagnitude <= 0.01f) {
                fromGoalToAttacker = -Player.GoalDirection;
            }

            var point = attackerPosition - fromGoalToAttacker.normalized * GoalSideDistance;
            point.y = Player.Position.y;
            return point;
        }
    }
}
