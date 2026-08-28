using FStudio.GTEX.Core;
using FStudio.GTEX.Playback;
using FStudio.MatchEngine;
using FStudio.MatchEngine.Balls;
using FStudio.MatchEngine.Cameras;
using UnityEngine;

namespace FStudio.GTEX.Presentation
{
    [DefaultExecutionOrder(10000)]
    public sealed class GtexLiveBroadcastCameraDriver : MonoBehaviour
    {
        private const float DefaultLength = 105f;
        private const float DefaultWidth = 68f;
        private const float CameraHeight = 24f;
        private const float LateralOffset = 31f;
        private const float PlayOffset = 10f;
        private const float FollowSmoothTime = 0.16f;
        private const float RotationSmoothTime = 0.12f;
        private const float MinFov = 46f;
        private const float MaxFov = 54f;
        private const float LookAheadSeconds = 0.28f;
        private const float MaxLookAhead = 8f;
        private const float BallFocusWeight = 0.88f;
        private const float ActionFocusWeight = 0.18f;
        private const float CameraSideSign = -1f;

        private static GtexLiveBroadcastCameraDriver instance;
        private CameraSystem legacyCameraSystem;
        private Camera targetCamera;
        private Ball ball;
        private Vector3 focus;
        private Vector3 focusVelocity;
        private Vector3 lastPlayDirection = Vector3.right;
        private Vector3 lastCameraPosition;
        private bool initialized;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Install()
        {
            if (instance != null)
            {
                return;
            }

            var host = new GameObject("GTEX Live Broadcast Camera");
            DontDestroyOnLoad(host);
            instance = host.AddComponent<GtexLiveBroadcastCameraDriver>();
        }

        private void LateUpdate()
        {
            if (!GtexRuntimeState.IsStarted ||
                GtexRuntimeState.ActiveMode != GtexRuntimeMode.LivePlayback)
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
                targetCamera = Camera.main ?? FindFirstObjectByType<Camera>();
            }

            if (ball == null)
            {
                ball = Ball.Current ?? FindFirstObjectByType<Ball>();
            }

            if (legacyCameraSystem == null)
            {
                legacyCameraSystem = FindFirstObjectByType<CameraSystem>();
            }

            initialized = targetCamera != null && ball != null;
        }

        private void DisableLegacyCameraController()
        {
            if (legacyCameraSystem != null && legacyCameraSystem.enabled)
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

            var center = manager != null ? manager.transform.position : Vector3.zero;
            return new GtexPitchSpace(DefaultLength, DefaultWidth, 0f, center);
        }

        private void ApplyBroadcastFrame(float deltaTime)
        {
            var pitch = ResolvePitchSpace();
            var ballPosition = pitch.ClampWorld(ball.transform.position);
            var velocity = ball.Velocity;
            velocity.y = 0f;

            var playDirection = velocity.sqrMagnitude > 0.16f
                ? velocity.normalized
                : lastPlayDirection;
            playDirection.y = 0f;
            if (playDirection.sqrMagnitude <= 0.0001f)
            {
                playDirection = Vector3.right;
            }
            else
            {
                playDirection.Normalize();
            }

            // Do not let a single noisy velocity sample swing the whole camera.
            // Broadcast direction changes should be deliberate and gradual.
            lastPlayDirection = Vector3.Slerp(
                lastPlayDirection,
                playDirection,
                1f - Mathf.Exp(-5.5f * Mathf.Max(deltaTime, 0.001f)));
            lastPlayDirection.y = 0f;
            lastPlayDirection.Normalize();

            var lookAhead = velocity.sqrMagnitude > 0.04f
                ? Vector3.ClampMagnitude(velocity * LookAheadSeconds, MaxLookAhead)
                : Vector3.zero;
            var ballFocus = pitch.ClampWorld(ballPosition + lookAhead);
            ballFocus.y = pitch.GrassY;

            var desiredFocus = Vector3.Lerp(pitch.Center, ballFocus, BallFocusWeight);
            desiredFocus = Vector3.Lerp(desiredFocus, ballFocus, ActionFocusWeight);
            desiredFocus = pitch.ClampWorld(desiredFocus);
            desiredFocus.y = pitch.GrassY;

            if (!initialized || focus == Vector3.zero)
            {
                focus = desiredFocus;
                focusVelocity = Vector3.zero;
            }
            else
            {
                focus = Vector3.SmoothDamp(
                    focus,
                    desiredFocus,
                    ref focusVelocity,
                    FollowSmoothTime,
                    Mathf.Infinity,
                    Mathf.Max(deltaTime, 1f / 120f));
            }

            // Camera stays outside the touchline but its longitudinal position is
            // driven by the actual ball direction. The previous implementation
            // hard-pinned Z to MinZ - 30, so the camera could not genuinely follow
            // play when the ball moved through the width of the field.
            var lateral = new Vector3(-lastPlayDirection.z, 0f, lastPlayDirection.x);
            if (lateral.sqrMagnitude <= 0.0001f)
            {
                lateral = Vector3.back;
            }
            lateral.Normalize();
            lateral *= CameraSideSign;

            var desiredPosition =
                focus - lastPlayDirection * PlayOffset +
                lateral * LateralOffset +
                Vector3.up * CameraHeight;

            var cameraXMargin = Mathf.Clamp(pitch.Length * 0.08f, 7f, 11f);
            var cameraZMargin = Mathf.Clamp(pitch.Width * 0.08f, 5f, 8f);
            desiredPosition.x = Mathf.Clamp(
                desiredPosition.x,
                pitch.MinX - cameraXMargin,
                pitch.MaxX + cameraXMargin);
            desiredPosition.z = Mathf.Clamp(
                desiredPosition.z,
                pitch.MinZ - LateralOffset - cameraZMargin,
                pitch.MaxZ + LateralOffset + cameraZMargin);

            var positionT = 1f - Mathf.Exp(-7f * Mathf.Max(deltaTime, 0.001f));
            targetCamera.transform.position = Vector3.Lerp(
                targetCamera.transform.position,
                desiredPosition,
                positionT);
            lastCameraPosition = targetCamera.transform.position;

            var lookTarget = Vector3.Lerp(ballFocus, focus, 0.18f);
            lookTarget.y = pitch.GrassY + 0.9f;
            var lookVector = lookTarget - targetCamera.transform.position;
            if (lookVector.sqrMagnitude > 0.01f)
            {
                var desiredRotation = Quaternion.LookRotation(lookVector.normalized, Vector3.up);
                var rotationT = 1f - Mathf.Exp(-9f * Mathf.Max(deltaTime, 0.001f));
                targetCamera.transform.rotation = Quaternion.Slerp(
                    targetCamera.transform.rotation,
                    desiredRotation,
                    rotationT);
            }

            var speedRatio = Mathf.Clamp01(velocity.magnitude / 18f);
            var desiredFov = Mathf.Lerp(MaxFov, MinFov, speedRatio);
            targetCamera.fieldOfView = Mathf.Lerp(
                targetCamera.fieldOfView,
                desiredFov,
                Mathf.Clamp01(deltaTime * 4f));
        }
    }
}
