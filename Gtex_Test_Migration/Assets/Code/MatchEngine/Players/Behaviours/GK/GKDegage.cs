
using System.Linq;
using FStudio.GTEX.Core;
using UnityEngine;

namespace FStudio.MatchEngine.Players.Behaviours {
    public class GKDegage : GKPassBehaviour {

        /// <summary>
        /// This cannot be bigger than Ball.IGNORE_COLLISION_TIME_FOR_BALL_HITTER
        /// </summary>
        private const float BALL_HIT_DELAYER = 0.45f;
        private float timer;
        private bool hitter;
        private PlayerBase target;

        public override bool Behave(bool isAlreadyActive) {
            if (Player.IsGoalKickHolder) {
                return false;
            }

            if (!Player.IsHoldingBall && !hitter) {
                return false;
            }

            if (!isAlreadyActive) {
                if (!Player.IsGKUntouchable) {
                    return false;
                } else {
                    isAlreadyActive = true;
                }
            }

            if (!isAlreadyActive) {
                return false;
            }

            if (Player.MoveSpeed > 0.1f) { // stop before degage.
                Player.Stop(in deltaTime);
                return true;
            }

            if (!hitter) {
                timer = time + BALL_HIT_DELAYER;
                if (!GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime()) {
                    ball.Release();
                }

                // we will force this behaviour,
                // this will stop others, and keep this working.
                ForceBehaviour = true; // forcing enabled.

                hitter = true;
            }

            if (hitter) {
                if (timer > time) {
                    return true;
                }

                if (target == null) {
                    target = FindAOpponentToPass();
                }

                if (target == null) {
                    hitter = false;
                    timer = 0;
                    ForceBehaviour = false;
                    return false;
                }

                var dir = (target.Position - Player.Position).normalized;

                if (Player.LookTo (in deltaTime, dir)) {

                    hitter = false;
                    timer = 0;
                    ForceBehaviour = false; // forcing disabled.

                    // hold the ball again (we cannot hit the ball without holding)
                    if (ball.HolderPlayer != Player) {
                        ball.Hold(Player);
                    }
                    Player.PassingTarget = target;
                    var leadDistance = GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime() ? 0.2f : 0.75f;
                    var speedMod = GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime() ? 0.82f : 0.95f;
                    if (GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime()) {
                        Debug.Log(
                            "[GTEX AI] Keeper distribution -> actor=" + Player +
                            " target=" + target +
                            " distance=" + Vector3.Distance(Player.Position, target.Position).ToString("0.0"));
                    }
                    Player.Pass(target.Position + dir * leadDistance, speedMod);
                    //

                    target = null;
                }

                return true;
            }

            return true;
        }
    }
}
