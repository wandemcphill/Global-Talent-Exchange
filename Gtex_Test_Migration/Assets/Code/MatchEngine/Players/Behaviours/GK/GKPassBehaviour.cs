
using System.Linq;
using FStudio.GTEX.Core;
using UnityEngine;

namespace FStudio.MatchEngine.Players.Behaviours {
    public abstract class GKPassBehaviour : BaseBehaviour {
        protected const float DEGAGE_SPEED_MOD = 15f;

        protected PlayerBase FindAOpponentToPass() {
            var forward = new Vector3(Player.toGoalXDirection, 0f, 0f);
            if (forward.sqrMagnitude <= 0.01f) {
                forward = Player.Direction;
                forward.y = 0f;
            }

            if (forward.sqrMagnitude <= 0.01f) {
                forward = Vector3.right;
            }

            forward.Normalize();

            return teammates.
                Where(x =>
                    x != Player &&
                    !x.IsGK &&
                    x.PlayerController != null &&
                    x.PlayerController.IsPhysicsEnabled).
                OrderBy(x => ResolveDistributionScore(x, forward)).
                FirstOrDefault();
        }

        private float ResolveDistributionScore(PlayerBase candidate, Vector3 forward) {
            var offset = candidate.Position - Player.Position;
            offset.y = 0f;

            var distance = offset.magnitude;
            var forwardScore = distance > 0.01f ? Vector3.Dot(forward, offset / distance) : 0f;
            var idealDistance = GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime() ? 13.5f : 17f;
            var maxDistance = GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime() ? 22f : 28f;
            var minDistance = GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime() ? 6f : 7f;
            var distancePenalty = Mathf.Abs(distance - idealDistance) * 0.55f;
            var tooLongPenalty = distance > maxDistance ? (distance - maxDistance) * 3.5f : 0f;
            var tooClosePenalty = distance < minDistance ? (minDistance - distance) * 1.4f : 0f;
            var centralityPenalty = GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime()
                ? Mathf.Abs(candidate.Position.z - fieldEndY * 0.5f) * 0.1f
                : 0f;
            var boundaryPenalty = GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime() &&
                (candidate.Position.x < 4f ||
                 candidate.Position.x > fieldEndX - 4f ||
                 candidate.Position.z < 4f ||
                 candidate.Position.z > fieldEndY - 4f)
                    ? 8f
                    : 0f;

            return distancePenalty + tooLongPenalty + tooClosePenalty + centralityPenalty + boundaryPenalty - forwardScore * 3f;
        }
    }
}
