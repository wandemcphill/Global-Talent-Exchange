using System;
using FStudio.GTEX.Core;
using FStudio.GTEX.Playback;
using FStudio.MatchEngine;
using FStudio.MatchEngine.Balls;
using FStudio.MatchEngine.Cameras;
using UnityEngine;

namespace FStudio.GTEX.Presentation
{
    /// <summary>
    /// Sole camera presenter for GTEX authoritative LivePlayback.
    /// Disables the legacy asset camera controller and follows the real
    /// pitch-space ball while maintaining a stable touchline broadcast view.
    /// </summary>
    [DefaultExecutionOrder(10000)]
    public sealed class GtexLiveBroadcastCameraDriver : MonoBehaviour
    {
        private const float DefaultLength = 105f;
        private const float DefaultWidth = 68f;
        private const float Height = 24f;
        private const float TouchlineOffset = 30f;
        private const float AlongPlayOffset = 6f;
        private const float FollowSharpness = 6.5f;
        private const float RotationSharpness = 9f;
        private const float MinFov = 48f;
        private const float MaxFov = 54f;
        private const float LookAheadSeconds = 0.22f;

        private CameraSystem legacyCameraSystem;
        private Camera targetCamera;
        private Ball ball;
        private Vector3 focus;
        private bool initialized;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Install()
        {
            if (GtexRuntimeState.ActiveMode != GtexRuntimeMode.LivePlayback)
            {
                return;
            }

            if (FindFirstObjectByType<GtexLiveBroadcastCameraDriver>() != null)
            {
                return;
            }

            var host = new GameObject("GTEX Live Broadcast Camera");
            DontDestroyOnLoad(host);
            host.AddComponent<GtexLiveBroadcastCameraDriver>();
        }

        private void LateUpdate()
        {
            if (GtexRuntimeState.ActiveMode != GtexRuntimeMode.LivePlayback)
            {
                return;
            }

            ResolveSceneReferences();
            if (!initialized || targetCamera == null || ball == null)
            {
                return;
            }

            DisableLegacyCameraController();
            ApplyBroadcastFrame(Time.unscaledDeltaTime);
        }

        private void ResolveSceneReferences()
        {
            if (targetCamera == null)
            {
                targetCamera = Camera.main;
                if (targetCamera == null)
                {
                    targetCamera = FindFirstObjectByType<Camera>();
                }
            }

            if (ball == null)
            {
                ball = Ball.Current;
                if (ball == null)
                {
                    ball = FindFirstObjectByType<Ball>();
                }
            }

            if (legacyCameraSystem == null)
            {
                legacyCameraSystem = FindFirstObjectByType<CameraSystem>();
            }

            initialized = targetCamera != null && ball != null;
        }

        private void DisableLegacyCameraController()
        {
            if (legacyCameraSystem == null)
            {
                return;
            }

            if (legacyCameraSystem.enabled)
            {
                legacyCameraSystem.enabled = false;
            }
        }

        private GtexPitchSpace ResolvePitchSpace()
        {
            var manager = MatchManager.Current;
            if (manager != null && manager.ExternalPlaybackPitchSpace != null)
            {
                return manager.ExternalPlaybackPitchSpace;
            }

            var center = manager != null && manager.transform != null
                ? manager.transform.position
                : Vector3.zero;
            return new GtexPitchSpace(DefaultLength, DefaultWidth, 0f, center);
        }

        private void ApplyBroadcastFrame(float deltaTime)
        {
            var pitch = ResolvePitchSpace();
            var ballPosition = ball.transform.position;
            var velocity = ball.Velocity;
            velocity.y = 0f;

            var lookAhead = velocity.sqrMagnitude > 0.04f
                ? Vector3.ClampMagnitude(velocity * LookAheadSeconds, 7f)
                : Vector3.zero;

            var ballFocus = pitch.ClampWorld(ballPosition + lookAhead);
            ballFocus.y = pitch.GrassY;

            var desiredFocus = Vector3.Lerp(pitch.Center, ballFocus, 0.82f);
            desiredFocus.y = pitch.GrassY;

            if (focus == Vector3.zero)
            {
                focus = desiredFocus;
            }

            var positionT = 1f - Mathf.Exp(-FollowSharpness * Mathf.Max(deltaTime, 0.001f));
            var rotationT = 1f - Mathf.Exp(-RotationSharpness * Mathf.Max(deltaTime, 0.001f));
            focus = Vector3.Lerp(focus, desiredFocus, positionT);

            var direction = velocity.sqrMagnitude > 0.04f ? velocity.normalized : Vector3.right;
            var cameraSide = Vector3.back;
            var desiredPosition = focus + cameraSide * TouchlineOffset - direction * AlongPlayOffset;
            desiredPosition.y = pitch.GrassY + Height;

            // Keep the lens along the same physical touchline instead of
            // allowing the camera to cut across the pitch or switch sides.
            desiredPosition.z = pitch.MinZ - TouchlineOffset;
            desiredPosition.x = Mathf.Clamp(desiredPosition.x, pitch.MinX - 8f, pitch.MaxX + 8f);

            var lookTarget = focus + Vector3.up * 0.8f;
            var desiredRotation = Quaternion.LookRotation(lookTarget - desiredPosition, Vector3.up);

            targetCamera.transform.position = Vector3.Lerp(
                targetCamera.transform.position,
                desiredPosition,
                positionT);
            targetCamera.transform.rotation = Quaternion.Slerp(
                targetCamera.transform.rotation,
                desiredRotation,
                rotationT);

            var speedRatio = Mathf.Clamp01(velocity.magnitude / 16f);
            var desiredFov = Mathf.Lerp(MaxFov, MinFov, speedRatio);
            targetCamera.fieldOfView = Mathf.Lerp(
                targetCamera.fieldOfView,
                desiredFov,
                Mathf.Clamp01(deltaTime * 4f));
        }
    }
}
