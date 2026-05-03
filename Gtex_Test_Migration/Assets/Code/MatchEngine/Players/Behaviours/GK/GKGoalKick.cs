
using System.Linq;
using FStudio.GTEX.Core;
using UnityEngine;

namespace FStudio.MatchEngine.Players.Behaviours {
    public class GKGoalKick : GKPassBehaviour {
        public override bool Behave(bool isAlreadyActive) {
            if (!Player.IsGoalKickHolder) {
                return false;
            }

            if (ball != null && ball.HolderPlayer != Player) {
                ball.Hold(Player);
                Debug.Log("[GTEX Restart] GoalKick holder rebound -> " + Player);
            }

            var target = FindAOpponentToPass() ?? teammates?
                .Where(teammate => teammate != null && teammate != Player && !teammate.IsGK)
                .OrderBy(teammate => Vector3.Distance(Player.Position, teammate.Position))
                .FirstOrDefault();

            if (target != null) {
                var distance = Vector3.Distance(Player.Position, target.Position);
                var receiveDirection = (target.Position - Player.Position).normalized;
                var leadDistance = GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime()
                    ? Mathf.Clamp(distance * 0.015f, 0.05f, 0.25f)
                    : Mathf.Clamp(distance * 0.04f, 0.2f, 0.65f);
                var targetPoint = target.Position + receiveDirection * leadDistance;
                var speedMod = GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime()
                    ? Mathf.Lerp(0.72f, 0.88f, Mathf.InverseLerp(7f, 20f, distance))
                    : Mathf.Lerp(0.78f, 0.98f, Mathf.InverseLerp(8f, 24f, distance));

                Player.PassingTarget = target;
                Debug.Log("[GTEX Restart] GoalKick pass -> target=" + target + " distance=" + distance.ToString("0.0"));
                Player.Pass(targetPoint, speedMod);
            } else {
                Debug.LogWarning("[GTEX Restart] GoalKick waiting: no available short target for " + Player);
            }

            return true;
        }
    }
}
