using FStudio.MatchEngine;
using FStudio.MatchEngine.Balls;
using FStudio.MatchEngine.Players;
using UnityEngine;

namespace FStudio.GTEX.Engine
{
    public sealed class GtexLegacyBallAdapter
    {
        private GtexExternalPlaybackSmoother playbackSmoother;

        public bool IsAvailable => MatchManager.Current != null && Ball.Current != null;

        public Transform Transform => Ball.Current != null ? Ball.Current.transform : null;

        public Vector3 Position => Ball.Current != null ? Ball.Current.transform.position : Vector3.zero;

        public Vector3 Velocity => Ball.Current != null ? Ball.Current.Velocity : Vector3.zero;

        public PlayerBase HolderPlayer => Ball.Current != null ? Ball.Current.HolderPlayer : null;

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

            var transform = Ball.Current.transform;
            if (transform == null)
            {
                return;
            }

            if (playbackSmoother == null)
            {
                playbackSmoother = transform.GetComponent<GtexExternalPlaybackSmoother>();
                if (playbackSmoother == null)
                {
                    playbackSmoother = transform.gameObject.AddComponent<GtexExternalPlaybackSmoother>();
                }
            }

            var targetRotation = targetVelocity.sqrMagnitude > 0.0001f
                ? Quaternion.LookRotation(new Vector3(targetVelocity.x, 0f, targetVelocity.z), Vector3.up)
                : transform.rotation;
            playbackSmoother.SetTarget(targetPosition, targetRotation, false);
        }

        public Vector3 ResolveExternalReleaseAnchor(
            GtexLegacyPlayerHandle holder,
            Vector3 releaseDirection,
            Vector3 fallbackPosition)
        {
            if (!IsAvailable)
            {
                return fallbackPosition;
            }

            return Ball.Current.ResolveExternalPlaybackReleaseAnchor(
                holder != null && holder.IsValid ? holder.RawPlayer : null,
                releaseDirection,
                fallbackPosition);
        }
    }
}
