

using FStudio.MatchEngine.Enums;
using FStudio.GTEX.Core;
using FStudio.GTEX.VisualBridge;
using FStudio.Players.Behaviours;

namespace FStudio.MatchEngine.Players.Behaviours {
    internal class BallChasingWithoutCondition : BallChasingBehaviour {
        private const float FOCUS_TO_BALL_AFTER_HEIGHT = 3f;
        public override bool Behave (bool isAlreadyActive) {
            if (!OriginalRuntimeRoleAwareness.CanUseOpenPlayBehaviour(matchStatus)) {
                return false;
            }

            if (GtexVisualAuthority.ShouldSuppressNonControlledAggression(Player)) {
                return false;
            }

            if (!isAlreadyActive) {
                return false; // cannot work automaticly. It should be manually triggered via ActivateBehaviour.
            }

            if (ball.HolderPlayer != null) {
                return false;
            }

            if (!IsRoughValidated()) {
                return false;
            }

            if (Player.CaughtInOffside) {
                return false;
            }

            chasingAct = AmITheChaser();
            var hasCommittedReceive = Player.TryGetOriginalRuntimeReceivePoint(out var receivePoint);

            if (GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime() &&
                !hasCommittedReceive &&
                chasingAct.result == BallChasingResult.None) {
                return false;
            }

            // Chasing ball directly.
            Player.CurrentAct = Acts.GoingToGetTheBall_BallChasing;

            var actualPoint = hasCommittedReceive ? receivePoint : ball.BallPosition(Player, chasingAct.relaxation);

            var actualBallPos = ball.transform.position;

            bool lookPoint = hasCommittedReceive || actualBallPos.y > FOCUS_TO_BALL_AFTER_HEIGHT;

            Player.MoveTo(in deltaTime, actualPoint, !lookPoint);

            if (lookPoint) {
                Player.LookTo(in deltaTime, actualBallPos - Player.Position);
            }

            ChasingDistance = BallChasingDistance(Player);

            return true;
        }
    }
}
