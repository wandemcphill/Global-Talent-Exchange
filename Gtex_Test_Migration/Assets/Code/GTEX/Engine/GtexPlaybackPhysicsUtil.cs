using FStudio.GTEX;
using UnityEngine;

namespace FStudio.GTEX.Engine
{
    public static class GtexPlaybackPhysicsUtil
    {
        public static void SafeSetRigidbodyVelocity(Rigidbody rb, Vector3 linearVelocity, Vector3 angularVelocity)
        {
            if (rb == null)
            {
                return;
            }

            if (rb.isKinematic)
            {
                GtexRuntimeTelemetry.RegisterKinematicVelocityWriteBlocked();
                return;
            }

#if UNITY_6000_0_OR_NEWER
            rb.linearVelocity = linearVelocity;
#else
            rb.velocity = linearVelocity;
#endif
            rb.angularVelocity = angularVelocity;
        }

        public static void ApplyExternalPlaybackPosition(
            Transform target,
            Rigidbody rb,
            Vector3 nextPosition,
            Quaternion nextRotation,
            bool snap = false)
        {
            if (target == null)
            {
                return;
            }

            // GTEX LivePlayback is a render-time presentation stream. The
            // backend already owns the authoritative trajectory, so routing
            // kinematic objects through the physics clock creates visible
            // one-frame latency, rubber-banding and position fights. Apply the
            // pose directly for live playback and keep the physics-driven path
            // for the legacy/local simulation modes.
            if (GtexRuntimeState.ActiveMode == GtexRuntimeMode.LivePlayback)
            {
                target.SetPositionAndRotation(nextPosition, nextRotation);
                if (rb != null)
                {
                    rb.position = nextPosition;
                    rb.rotation = nextRotation;
#if UNITY_6000_0_OR_NEWER
                    rb.linearVelocity = Vector3.zero;
#else
                    rb.velocity = Vector3.zero;
#endif
                    rb.angularVelocity = Vector3.zero;
                }
                return;
            }

            if (rb != null)
            {
                if (snap)
                {
                    rb.position = nextPosition;
                    rb.rotation = nextRotation;
                    target.SetPositionAndRotation(nextPosition, nextRotation);
                    return;
                }

                rb.MovePosition(nextPosition);
                rb.MoveRotation(nextRotation);
                return;
            }

            target.SetPositionAndRotation(nextPosition, nextRotation);
        }
    }
}
