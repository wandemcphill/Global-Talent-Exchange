
using FStudio.GTEX.Core;
using UnityEngine;

namespace FStudio.MatchEngine.Players.Behaviours {
    public class GKSendAway : GKPassBehaviour {
        private PlayerBase target;

        public override bool Behave(bool isAlreadyActive) {
            if (Player.IsGoalKickHolder || Player.IsGKUntouchable || !Player.IsHoldingBall) {
                return false;
            }

            if (!isAlreadyActive) {
                target = FindAOpponentToPass();

                if (target != null) {
                    isAlreadyActive = true;
                }
            }

            if (isAlreadyActive) {
                if (target == null) {
                    return false;
                }

                if (Player.LookTo(in deltaTime, target.Position - Player.Position)) {
                    ball.Hold(Player);
                    Player.PassingTarget = target;
                    var distance = Vector3.Distance(Player.Position, target.Position);
                    var speedMod = GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime()
                        ? Mathf.Lerp(0.72f, 0.88f, Mathf.InverseLerp(7f, 20f, distance))
                        : 0.95f;
                    if (GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime()) {
                        Debug.Log(
                            "[GTEX AI] Keeper pass -> actor=" + Player +
                            " target=" + target +
                            " distance=" + distance.ToString("0.0"));
                    }
                    Player.Pass(target.Position, speedMod);
                    target = null;
                }

                return true;
            }

            return false;
        }
    }
}
