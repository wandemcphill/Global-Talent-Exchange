using System.Linq;
using FStudio.GTEX.Core;
using FStudio.MatchEngine.Enums;
using UnityEngine;

namespace FStudio.MatchEngine.Players.Behaviours {
    public class CornerBehaviour : BaseBehaviour {
        private readonly Vector2 cornerBox = new Vector2 (8, 16);

        private const float TO_PENALTY_BOX = 9.15f;

        private const float TO_TARGET = 0.8f;

        private const float DIRECTION_MULTIPLIER = 7;

        private Vector3 target;
        private PlayerBase targetPlayer;

        /// <summary>
        /// Player will try to find a target, closer to goal net and not marked.
        /// </summary>
        /// <param name="deltaTime"></param>
        /// <param name="ball"></param>
        /// <param name="targetGoalNet"></param>
        /// <param name="teammates"></param>
        /// <returns></returns>
        public override bool Behave(bool isAlreadyActive) {
            if (!Player.IsCornerHolder) {
                return false;
            }

            if (!isAlreadyActive) {
                var penaltyPoint = targetGoalNet.Position;
                penaltyPoint -= Player.GoalDirection * TO_PENALTY_BOX;

                target = penaltyPoint + new Vector3(
                    Random.Range(-cornerBox.x, cornerBox.x),
                    0,
                    Random.Range(-cornerBox.y, cornerBox.y)
                    );

                var closest = teammates.OrderBy(x => Vector3.Distance(x.Position, target)).FirstOrDefault ();
                if (closest == null) {
                    return false;
                }

                targetPlayer = closest;

                target = Vector3.Lerp(target, closest.Position, TO_TARGET) + DIRECTION_MULTIPLIER * (closest.Position - Player.Position).normalized;

                Debug.Log($"Corner target is {target}");

                isAlreadyActive = true;
            }

            if (isAlreadyActive) {
                Player.CurrentAct = Acts.ThrowIn;

                if (GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime()) {
                    if (targetPlayer != null) {
                        Player.PassingTarget = targetPlayer;
                        target = targetPlayer.Position;
                    }

                    Player.Pass(target, 0.92f);
                } else {
                    Player.Cross(target);
                }

                // teammates chase the ball directly.
                var chasers = GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime()
                    ? Player.GameTeam.GamePlayers
                        .Where(e => e == targetPlayer || (!e.IsGK && e.PlayerFieldProgress > 0.72f))
                        .OrderBy(e => e == targetPlayer ? 0f : Vector3.Distance(e.Position, target))
                        .Take(3)
                    : Player.GameTeam.GamePlayers.Where(e => e.PlayerFieldProgress > 0.8f);

                foreach (var e in chasers) {
                    e.ActivateBehaviour("BallChasingWithoutCondition");
                }
            }

            return true;
        }
    }
}
