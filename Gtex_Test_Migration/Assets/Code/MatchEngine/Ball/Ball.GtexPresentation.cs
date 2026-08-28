using UnityEngine;

namespace FStudio.MatchEngine.Balls
{
    public partial class Ball
    {
        internal bool TryGetGtexLivePresentationTarget(
            out Vector3 position,
            out Vector3 velocity,
            out Quaternion rotation,
            out bool hasTarget)
        {
            position = externalPlaybackTargetPosition;
            velocity = externalPlaybackVelocity;
            rotation = externalPlaybackTargetRotation;
            hasTarget = ExternalPlaybackEnabled &&
                        GtexRuntimeState.ActiveMode == GtexRuntimeMode.LivePlayback &&
                        hasExternalPlaybackTarget;
            return ExternalPlaybackEnabled &&
                   GtexRuntimeState.ActiveMode == GtexRuntimeMode.LivePlayback;
        }
    }
}
