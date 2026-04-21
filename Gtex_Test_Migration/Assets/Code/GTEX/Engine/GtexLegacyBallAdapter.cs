using FStudio.MatchEngine;
using FStudio.MatchEngine.Balls;
using UnityEngine;

namespace FStudio.GTEX.Engine
{
    public sealed class GtexLegacyBallAdapter
    {
        public bool IsAvailable => MatchManager.Current != null && Ball.Current != null;

        public Transform Transform => Ball.Current != null ? Ball.Current.transform : null;

        public void ApplyExternalState(
            Vector3 targetPosition,
            Vector3 targetVelocity,
            GtexLegacyPlayerHandle holder = null)
        {
            if (!IsAvailable)
            {
                return;
            }

            Ball.Current.ApplyExternalState(
                targetPosition,
                targetVelocity,
                holder != null && holder.IsValid ? holder.RawPlayer : null);
        }
    }
}
