using FStudio.MatchEngine.Enums;
using UnityEngine;
using System.Linq;
using FStudio.Events;
using FStudio.GTEX.Core;
using FStudio.MatchEngine.Events;

namespace FStudio.MatchEngine.Players.Behaviours {
    public class ThrowInBehaviour : BaseBehaviour {
        private PlayerBase target;

        /// <summary>
        /// Player will try to find a target, closer to goal net and not marked.
        /// </summary>
        /// <param name="deltaTime"></param>
        /// <param name="ball"></param>
        /// <param name="targetGoalNet"></param>
        /// <param name="teammates"></param>
        /// <returns></returns>
        public override bool Behave (bool isAlreadyActive) {
            if (!Player.IsThrowHolder) {
                target = null;
                return false;
            }

            if (isAlreadyActive && target == null) {
                isAlreadyActive = false;
            }

            if (!isAlreadyActive) {
                var playerPos = Player.Position;

                var targetTeammate = teammates.
                    Where(x =>
                        x != null &&
                        x != Player &&
                        !x.IsGK &&
                        x.PlayerController != null &&
                        x.PlayerController.IsPhysicsEnabled &&
                        Vector3.Distance(x.Position, playerPos) <= PlayerBase.MAX_THROWIN_DISTANCE - 1f &&
                        (!GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime() || IsSafeOriginalRuntimeRestartTarget(x))).
                    OrderBy(x => ResolveThrowInTargetScore(x, playerPos)).
                    FirstOrDefault();

                targetTeammate ??= teammates.
                    Where(x => x != null && x != Player && !x.IsGK && x.PlayerController != null && x.PlayerController.IsPhysicsEnabled).
                    OrderBy(x => ResolveThrowInTargetScore(x, playerPos)).
                    FirstOrDefault();

                if (targetTeammate != null) {
                    target = targetTeammate;
                    isAlreadyActive = true;
                }
            }

            if (isAlreadyActive) {
                Player.CurrentAct = Acts.ThrowIn;

                if (target == null) {
                    Debug.LogWarning("[GTEX Restart] ThrowIn waiting: no valid target for " + Player);
                    return true;
                }

                var targetPos = GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime()
                    ? ResolveOriginalRuntimeThrowInReceivePoint(target)
                    : target.Position;

                if (Player.LookTo (in deltaTime, targetPos - Player.Position)) {
                    Player.PassingTarget = target;
                    if (GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime()) {
                        Debug.Log(
                            "[GTEX AI] Restart ThrowIn -> actor=" + Player +
                            " target=" + target +
                            " distance=" + Vector3.Distance(Player.Position, targetPos).ToString("0.0"));
                        Player.Pass(targetPos, 0.76f);
                    } else {
                        Player.Cross (targetPos);
                    }

                    EventManager.Trigger(new PlayerThrowInEvent(Player));
                }
            }

            return true;
        }

        private float ResolveThrowInTargetScore(PlayerBase candidate, Vector3 throwerPosition) {
            var distance = Vector3.Distance(candidate.Position, throwerPosition);
            var centralityPenalty = Mathf.Abs(candidate.Position.z - fieldEndY * 0.5f) * 0.12f;
            var progressBonus = -candidate.PlayerFieldProgress * 1.6f;
            var boundaryPenalty = IsSafeOriginalRuntimeRestartTarget(candidate) ? 0f : 10f;
            return distance + centralityPenalty + boundaryPenalty + progressBonus;
        }

        private bool IsSafeOriginalRuntimeRestartTarget(PlayerBase candidate) {
            if (!GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime()) {
                return true;
            }

            const float margin = 3.25f;
            return candidate.Position.x >= margin &&
                candidate.Position.x <= fieldEndX - margin &&
                candidate.Position.z >= margin &&
                candidate.Position.z <= fieldEndY - margin;
        }

        private Vector3 ResolveOriginalRuntimeThrowInReceivePoint(PlayerBase receiver) {
            var point = receiver.Position;
            point.y = Player.Position.y;
            point.x = Mathf.Clamp(point.x, 2.25f, fieldEndX - 2.25f);
            point.z = Mathf.Clamp(point.z, 2.25f, fieldEndY - 2.25f);
            return point;
        }
    }
}
