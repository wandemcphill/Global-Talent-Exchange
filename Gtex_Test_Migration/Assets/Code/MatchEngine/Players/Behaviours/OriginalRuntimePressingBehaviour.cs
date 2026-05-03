using System.Linq;
using FStudio.GTEX.Core;
using FStudio.GTEX.VisualBridge;
using FStudio.MatchEngine.Enums;
using FStudio.MatchEngine.Players.PlayerController;
using UnityEngine;

namespace FStudio.MatchEngine.Players.Behaviours {
    public sealed class OriginalRuntimePressingBehaviour : BaseBehaviour {
        private const int MaxPressers = 2;
        private const float MaxPressDistance = 31f;
        private const float PressStopDistance = 1.35f;
        private const float MaxPressBallHeight = 0.85f;

        public override bool Behave(bool isAlreadyActive) {
            if (!GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime() ||
                !OriginalRuntimeRoleAwareness.CanUseOpenPlayBehaviour(matchStatus) ||
                GtexVisualAuthority.ShouldSuppressNonControlledAggression(Player) ||
                Player.IsHoldingBall ||
                Player.IsGK ||
                ball == null ||
                ball.HolderPlayer == null ||
                ball.HolderPlayer.GameTeam == Player.GameTeam ||
                ball.HolderPlayer.IsGKUntouchable ||
                ball.transform.position.y > MaxPressBallHeight ||
                !IsRoughValidated()) {
                return false;
            }

            var holder = ball.HolderPlayer;
            var holderPosition = holder.Position;

            if (Vector3.Distance(Player.Position, holderPosition) > MaxPressDistance) {
                return false;
            }

            var index = OriginalRuntimeRoleAwareness.PressureRank(Player, holder, teammates, MaxPressers);
            if (index < 0) {
                return false;
            }

            var goalSide = goalNet.Position - holderPosition;
            goalSide.y = 0f;
            if (goalSide.sqrMagnitude <= 0.01f) {
                goalSide = -holder.Direction;
                goalSide.y = 0f;
            }

            if (goalSide.sqrMagnitude <= 0.01f) {
                goalSide = -Player.GoalDirection;
            }

            goalSide.Normalize();

            var lateral = Vector3.Cross(Vector3.up, goalSide).normalized;
            var side = index == 0 ? 0f : Mathf.Sign(Vector3.Dot(Player.Position - holderPosition, lateral)) * 2.25f;
            var pressDistance = index == 0 ? PressStopDistance : 3.4f;
            var target = holderPosition + goalSide * pressDistance + lateral * side;
            target.y = Player.Position.y;
            KeepInField(ref target);

            if (!isAlreadyActive) {
                Debug.Log(
                    "[GTEX AI] Press -> defender=" + Player +
                    " carrier=" + holder +
                    " role=" + (index == 0 ? "primary" : "cover"));
            }

            Player.CurrentAct = index == 0 ? Acts.GoingToTackle : Acts.DefensiveTacticalPositioningBehaviour;
            Player.MoveTo(
                in deltaTime,
                target,
                true,
                index == 0 ? MovementType.BestHeCanDo : MovementType.Normal);

            if (index == 0 &&
                Vector3.Distance(Player.Position, holderPosition) <= PlayerBase.TACKLING_DISTANCE * 0.95f) {
                Player.Tackle(ball);
                return false;
            }

            return true;
        }
    }
}
