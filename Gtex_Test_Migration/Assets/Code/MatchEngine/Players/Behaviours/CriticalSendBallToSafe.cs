
using FStudio.GTEX.Core;
using UnityEngine;
using System.Linq;

namespace FStudio.MatchEngine.Players.Behaviours {
    /// <summary>
    /// When we are close to our goal net, if someone is around us.
    /// </summary>
    public class CriticalSendBallToSafe : BallChasingBehaviour {
        private readonly float maxBallProgress = 0.2f;

        private const float RISK_AREA = 3f;

        private readonly float sendAwayPowerMin = 26;
        private readonly float sendAwayPowerMax = 38;

        private Vector3 targetSendAwayPosition;

        public override bool Behave(bool isAlreadyActive) {
            if (!OriginalRuntimeRoleAwareness.CanUseOpenPlayBehaviour(matchStatus)) {
                return false;
            }

            if (!Player.IsHoldingBall) {
                return false;
            }

            if (Player.GameTeam.BallProgress > maxBallProgress) {
                return false;
            }

            if (!isAlreadyActive) {
                // check around.
                var myPos = Player.Position;
                if (
                    opponents.Where(x => x.PlayerController.IsPhysicsEnabled && 
                    Vector3.Distance(x.Position, myPos) < RISK_AREA).Any()) {
                    var forward = new Vector3(Player.toGoalXDirection, 0, 0);

                    var forwardLook = Quaternion.LookRotation(forward);
                    var myLook = Quaternion.LookRotation(Player.Direction);

                    forward = Quaternion.Slerp(myLook, forwardLook, 0.5f) * Vector3.forward;

                    targetSendAwayPosition = Player.Position + forward * Random.Range(sendAwayPowerMin, sendAwayPowerMax);

                    isAlreadyActive = true;
                }
            }

            if (isAlreadyActive) {
                if (Player.LookTo(in deltaTime, targetSendAwayPosition - Player.Position)) {
                    var outlet = ResolveSafeOutlet();
                    if (outlet != null) {
                        Player.PassingTarget = outlet;
                        Player.Pass(outlet.Position, 0.98f);
                    } else {
                        Player.Pass(targetSendAwayPosition, 1.05f);
                    }
                }

                return true;
            }

            return false;
        }

        private PlayerBase ResolveSafeOutlet() {
            var candidates = teammates.
                Where(x =>
                    x != Player &&
                    !x.IsGK &&
                    x.PlayerController != null &&
                    x.PlayerController.IsPhysicsEnabled &&
                    Vector3.Distance(x.Position, Player.Position) <= 26f);

            if (GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime()) {
                return candidates.OrderBy(x => ResolveOutletScore(x)).FirstOrDefault();
            }

            return candidates
                .OrderByDescending(x => x.PlayerFieldProgress)
                .ThenBy(x => Vector3.Distance(x.Position, Player.Position))
                .FirstOrDefault();
        }

        private float ResolveOutletScore(PlayerBase outlet) {
            var role = OriginalRuntimeRoleAwareness.RoleOf(outlet);
            var rolePenalty =
                role == OriginalRuntimePlayerRole.Midfielder ? 0f :
                role == OriginalRuntimePlayerRole.Defender ? 1.5f :
                2.5f;
            var distancePenalty = Mathf.Abs(Vector3.Distance(outlet.Position, Player.Position) - 14f) * 0.35f;
            var progressReward = -outlet.PlayerFieldProgress * 5f;
            var boundaryPenalty =
                outlet.Position.x < 4f ||
                outlet.Position.x > fieldEndX - 4f ||
                outlet.Position.z < 4f ||
                outlet.Position.z > fieldEndY - 4f
                    ? 8f
                    : 0f;

            return rolePenalty + distancePenalty + boundaryPenalty + progressReward;
        }
    }
}
