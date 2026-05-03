
using FStudio.GTEX.Core;
using UnityEngine;
using System.Linq;

namespace FStudio.MatchEngine.Players.Behaviours {
    public class SendBallToSafe : BallChasingBehaviour {

        private readonly float maxBallProgress = 0.3f;

        private const float ANGLE_MIN = -80;
        private const float ANGLE_MAX = 80;

        private readonly float sendAwayPowerMin = 20;
        private readonly float sendAwayPowerMax = 30;

        private readonly float X_SIZE = 22;

        private Vector3 targetSendAwayPosition;
        
        public override bool Behave(bool isAlreadyActive) {
            if (!OriginalRuntimeRoleAwareness.CanUseOpenPlayBehaviour(matchStatus)) {
                return false;
            }

            if (!Player.IsHoldingBall) {
                return false;
            }

            if (Player.GameTeam.TeamDensity < Player.GameTeam.BallProgress) {
                // we have backup behind. so ignore.
                return false;
            }

            if (Player.GameTeam.BallProgress > maxBallProgress) {
                return false;
            }

            var playerZ = Player.Position.z;

            if (playerZ < (fieldEndY / 2) - X_SIZE || playerZ > (fieldEndY / 2) + X_SIZE) {
                return false;
            }

            if (!isAlreadyActive) {
                var forward = new Vector3 (Player.toGoalXDirection, 0, 0);

                var directionErrY = Random.Range(ANGLE_MIN, ANGLE_MAX);
                forward = Quaternion.Euler(0, directionErrY, 0) * forward;

                targetSendAwayPosition = Player.Position + forward * Random.Range(sendAwayPowerMin, sendAwayPowerMax);
            }

            if (Player.LookTo (in deltaTime, targetSendAwayPosition - Player.Position)) {
                var outlet = ResolveSafeOutlet();
                if (outlet != null) {
                    Player.PassingTarget = outlet;
                    Player.Pass(outlet.Position, 0.95f);
                } else {
                    Player.Pass(targetSendAwayPosition, 1.02f);
                }
            }

            return true;
        }

        private PlayerBase ResolveSafeOutlet() {
            var candidates = teammates.
                Where(x =>
                    x != Player &&
                    !x.IsGK &&
                    x.PlayerController != null &&
                    x.PlayerController.IsPhysicsEnabled &&
                    Vector3.Distance(x.Position, Player.Position) <= 24f);

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
                role == OriginalRuntimePlayerRole.Defender ? 1.25f :
                2.25f;
            var distancePenalty = Mathf.Abs(Vector3.Distance(outlet.Position, Player.Position) - 13f) * 0.35f;
            var progressReward = -outlet.PlayerFieldProgress * 4.5f;
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
