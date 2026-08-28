using FStudio.GTEX.Core;
using FStudio.MatchEngine.Balls;
using UnityEngine;

namespace FStudio.GTEX.Presentation
{
    [DefaultExecutionOrder(9990)]
    [DisallowMultipleComponent]
    public sealed class GtexLiveBallVisualSmoother : MonoBehaviour
    {
        private const float PositionSmoothTime = 0.055f;
        private const float MaxVisualSpeed = 35f;
        private const float HardSnapDistance = 8f;
        private const float SpinSharpness = 16f;

        private static GtexLiveBallVisualSmoother instance;
        private Vector3 visualVelocity;
        private Vector3 spinVelocity;
        private Quaternion visualRotation = Quaternion.identity;
        private bool initialized;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Install()
        {
            if (instance != null) return;
            var host = new GameObject("GTEX Live Ball Visual Smoother");
            DontDestroyOnLoad(host);
            instance = host.AddComponent<GtexLiveBallVisualSmoother>();
        }

        private void LateUpdate()
        {
            if (!GtexRuntimeState.IsStarted || GtexRuntimeState.ActiveMode != GtexRuntimeMode.LivePlayback)
            {
                initialized = false;
                return;
            }

            var ball = Ball.Current;
            if (ball == null || !ball.TryGetGtexLivePresentationTarget(out var target, out var velocity, out var targetRotation, out var hasTarget) || !hasTarget)
            {
                return;
            }

            var transform = ball.transform;
            var dt = Mathf.Max(Time.unscaledDeltaTime, 1f / 120f);
            if (!initialized)
            {
                transform.SetPositionAndRotation(target, targetRotation);
                visualVelocity = Vector3.zero;
                spinVelocity = Vector3.zero;
                visualRotation = targetRotation;
                initialized = true;
                return;
            }

            var targetDelta = target - transform.position;
            if (targetDelta.sqrMagnitude >= HardSnapDistance * HardSnapDistance)
            {
                transform.SetPositionAndRotation(target, targetRotation);
                visualVelocity = Vector3.zero;
                visualRotation = targetRotation;
                return;
            }

            var speed = Mathf.Clamp(Mathf.Max(velocity.magnitude * 1.15f, 8f), 8f, MaxVisualSpeed);
            var nextPosition = Vector3.SmoothDamp(
                transform.position,
                target,
                ref visualVelocity,
                PositionSmoothTime,
                speed,
                dt);
            transform.position = nextPosition;

            var horizontalVelocity = velocity;
            horizontalVelocity.y = 0f;
            if (horizontalVelocity.sqrMagnitude > 0.0025f)
            {
                var desiredRotation = Quaternion.LookRotation(horizontalVelocity.normalized, Vector3.up);
                var rotationT = 1f - Mathf.Exp(-SpinSharpness * dt);
                visualRotation = Quaternion.Slerp(visualRotation, desiredRotation, rotationT);
                transform.rotation = visualRotation;
            }
        }
    }
}
