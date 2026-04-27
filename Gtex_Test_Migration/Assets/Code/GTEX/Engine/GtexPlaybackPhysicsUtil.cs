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
