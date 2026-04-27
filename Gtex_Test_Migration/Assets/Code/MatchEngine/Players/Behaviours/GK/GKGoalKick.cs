
namespace FStudio.MatchEngine.Players.Behaviours {
    public class GKGoalKick : GKPassBehaviour {
        public override bool Behave(bool isAlreadyActive) {
            if (!Player.IsGoalKickHolder) {
                return false;
            }

            var target = FindAOpponentToPass();
            if (target != null) {
                var receiveDirection = (target.Position - Player.Position).normalized;
                var distance = UnityEngine.Vector3.Distance(Player.Position, target.Position);
                var leadDistance = UnityEngine.Mathf.Clamp(distance * 0.08f, 0.35f, 1.1f);
                var targetPoint = target.Position + receiveDirection * leadDistance;
                var speedMod = UnityEngine.Mathf.Lerp(1.08f, 1.38f, UnityEngine.Mathf.InverseLerp(10f, 28f, distance));

                Player.PassingTarget = target;
                Player.Pass(targetPoint, speedMod);
            }

            return true;
        }
    }
}
