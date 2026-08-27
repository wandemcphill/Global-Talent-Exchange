using System;
using System.Threading.Tasks;
using FStudio.Utilities;
using FStudio.MatchEngine;
using FStudio.MatchEngine.Balls;
using FStudio.Events;
using FStudio.UI.Events;
using UnityEngine;

namespace FStudio.MatchEngine.Cameras
{
    [RequireComponent(typeof(Camera))]
    public class CameraSystem : SceneObjectSingleton<CameraSystem>
    {
#pragma warning disable 0109
        public new Camera camera = default;
#pragma warning restore 0109

        [SerializeField] private SerializableAssetCollection<string, MatchCamera> matchCameras =
            new SerializableAssetCollection<string, MatchCamera>();

        [SerializeField] public Transform target = default;

        [SerializeField] private float positionDifferencePower = 0.25f;
        [SerializeField] private float rotationDifferencePower = 0.25f;

        public float ZoomMultiplier;

        private bool isInTransition;
        private float transitionValue = 1f;
        private bool instantTransitionInNextFrame;

        [SerializeField] private float transitionSpeed = 0.5f;

        [Header("Camera Speed")]
        public float CameraPositionSpeed = 4f;
        public float CameraRotationSpeed = 20f;
        public float CameraZoomSpeed = 4f;

        [Header("GTEX Broadcast Presentation")]
        [SerializeField] private float broadcastMinFieldOfView = 46f;
        [SerializeField] private float broadcastMaxFieldOfView = 54f;
        [SerializeField] private float broadcastLookAheadDistance = 5f;
        [SerializeField] private float broadcastPositionSpeed = 5.5f;
        [SerializeField] private float broadcastRotationSpeed = 9f;
        [SerializeField] private float broadcastHeight = 24f;
        [SerializeField] private float broadcastSidelineOffset = 30f;
        [SerializeField] private float broadcastAlongPlayOffset = 7f;
        [SerializeField] private float broadcastFollowWeight = 0.72f;
        [SerializeField] private float broadcastCenterBias = 0.18f;

        public MatchCamera CurrentCamera { get; private set; }
        public string CurrentCameraType { get; private set; }
        public Vector3? TargetPosition;

        private bool IsBroadcastCamera =>
            string.Equals(CurrentCameraType, "TVBroadcast", StringComparison.OrdinalIgnoreCase) ||
            string.Equals(CurrentCameraType, "Broadcast", StringComparison.OrdinalIgnoreCase);

        private void ActiveCameraChanged()
        {
            if (target == null)
            {
                EventManager.Trigger<MatchCameraActiveEvent>(null);
            }
            else
            {
                EventManager.Trigger(new MatchCameraActiveEvent());
            }
        }

        public void SetTarget(Transform target)
        {
            this.target = target;
            ActiveCameraChanged();
        }

        public async Task SwitchCamera(string cameraType, bool instant = true)
        {
            var resolvedCameraType = ResolveCameraAlias(cameraType);
            var resolvedCamera = await matchCameras.FindAsync(resolvedCameraType);

            if (resolvedCamera == null && !string.Equals(resolvedCameraType, "Stadium", StringComparison.OrdinalIgnoreCase))
            {
                resolvedCameraType = "Stadium";
                resolvedCamera = await matchCameras.FindAsync(resolvedCameraType);
            }

            if (resolvedCamera == null)
            {
                Debug.LogWarning($"[CameraSystem] Camera asset not found for requested type '{cameraType}'.");
                return;
            }

            CurrentCamera = resolvedCamera;
            CurrentCameraType = resolvedCameraType;
            isInTransition = false;
            transitionValue = 1f;
            instantTransitionInNextFrame = instant;
            TargetPosition = null;
            ActiveCameraChanged();
        }

        private static string ResolveCameraAlias(string cameraType)
        {
            var normalized = (cameraType ?? string.Empty).Trim();
            return string.Equals(normalized, "Broadcast", StringComparison.OrdinalIgnoreCase)
                ? "TVBroadcast"
                : normalized;
        }

        private async void Start()
        {
            await SwitchCamera("TVBroadcast", false);
        }

        public void FocusToBall(bool instant = true)
        {
            if (Ball.Current == null)
            {
                return;
            }

            SetTarget(Ball.Current.transform);
            TargetPosition = null;
            instantTransitionInNextFrame = instant;
            isInTransition = false;
            transitionValue = 1f;
        }

        public void FocusToPosition(Vector3 position, bool instant = true)
        {
            if (target == null && Ball.Current != null)
            {
                SetTarget(Ball.Current.transform);
            }

            TargetPosition = position;
            instantTransitionInNextFrame = instant;
            isInTransition = false;
            transitionValue = 1f;
        }

        private void OnValidate()
        {
            camera = GetComponent<Camera>();
            broadcastMinFieldOfView = Mathf.Clamp(broadcastMinFieldOfView, 35f, 65f);
            broadcastMaxFieldOfView = Mathf.Clamp(broadcastMaxFieldOfView, broadcastMinFieldOfView, 65f);
            broadcastLookAheadDistance = Mathf.Clamp(broadcastLookAheadDistance, 0f, 12f);
            broadcastPositionSpeed = Mathf.Clamp(broadcastPositionSpeed, 1f, 12f);
            broadcastRotationSpeed = Mathf.Clamp(broadcastRotationSpeed, 2f, 18f);
            broadcastHeight = Mathf.Clamp(broadcastHeight, 16f, 36f);
            broadcastSidelineOffset = Mathf.Clamp(broadcastSidelineOffset, 20f, 40f);
            broadcastAlongPlayOffset = Mathf.Clamp(broadcastAlongPlayOffset, 0f, 14f);
            broadcastFollowWeight = Mathf.Clamp01(broadcastFollowWeight);
            broadcastCenterBias = Mathf.Clamp01(broadcastCenterBias);
        }

        private void Update()
        {
            if (target == null && Ball.Current != null)
            {
                target = Ball.Current.transform;
            }

            if (target == null || CurrentCamera == null)
            {
                return;
            }

            var dT = Mathf.Max(0.001f, Time.unscaledDeltaTime);

            if (isInTransition)
            {
                transitionValue += dT * transitionSpeed;
                if (transitionValue >= 1f)
                {
                    isInTransition = false;
                    transitionValue = 1f;
                }
            }

            var targetPos = IsBroadcastCamera && Ball.Current != null
                ? BuildBroadcastFocusPoint(dT)
                : TargetPosition.HasValue ? TargetPosition.Value : target.position;

            if (IsBroadcastCamera && Ball.Current != null)
            {
                ApplyGtexBroadcastCamera(targetPos, dT);
                return;
            }

            var (position, rotation, zoom) = CurrentCamera.Behave(in dT, targetPos);

            if (instantTransitionInNextFrame)
            {
                instantTransitionInNextFrame = false;
                transform.position = position;
                transform.rotation = rotation;
                camera.fieldOfView = zoom / (ZoomMultiplier + 1f);
                return;
            }

            var rawPositionDifference = Vector3.Distance(transform.position, position) + 1f;
            var rawRotationDifference = Quaternion.Angle(transform.rotation, rotation) + 1f;
            var positionDifference = Mathf.Clamp(rawPositionDifference, 1f, 8f) * transitionValue;
            var rotationDifference = Mathf.Clamp(rawRotationDifference, 1f, 24f) * transitionValue;
            var positionLerp = Mathf.Clamp01(dT * CameraPositionSpeed * positionDifference * positionDifferencePower);
            var rotationLerp = Mathf.Clamp01(dT * CameraRotationSpeed * rotationDifference * rotationDifferencePower);

            transform.position = Vector3.Lerp(transform.position, position, positionLerp);
            transform.rotation = Quaternion.Slerp(transform.rotation, rotation, rotationLerp);
            camera.fieldOfView = Mathf.Lerp(
                camera.fieldOfView,
                zoom / (ZoomMultiplier + 1f),
                Mathf.Clamp01(dT * CameraZoomSpeed));
        }

        private Vector3 BuildBroadcastFocusPoint(float dT)
        {
            var ball = Ball.Current;
            var field = MatchManager.Current != null
                ? MatchManager.Current.SizeOfField
                : new Vector2(105f, 68f);

            var fieldMinX = 0f;
            var fieldMaxX = Mathf.Max(1f, field.x);
            var fieldMinZ = 0f;
            var fieldMaxZ = Mathf.Max(1f, field.y);
            var fieldCenter = new Vector3(fieldMaxX * 0.5f, 0f, fieldMaxZ * 0.5f);

            var velocity = ball.Velocity;
            velocity.y = 0f;
            var lookAhead = velocity.sqrMagnitude > 0.04f
                ? Vector3.ClampMagnitude(velocity.normalized * broadcastLookAheadDistance, broadcastLookAheadDistance)
                : Vector3.zero;

            var ballPoint = ball.transform.position + lookAhead;
            ballPoint.y = 0f;
            ballPoint.x = Mathf.Clamp(ballPoint.x, fieldMinX + 7f, fieldMaxX - 7f);
            ballPoint.z = Mathf.Clamp(ballPoint.z, fieldMinZ + 7f, fieldMaxZ - 7f);

            var desiredFocus = Vector3.Lerp(fieldCenter, ballPoint, broadcastFollowWeight);
            desiredFocus = Vector3.Lerp(desiredFocus, fieldCenter, broadcastCenterBias * 0.35f);

            if (_broadcastFocus == Vector3.zero)
            {
                _broadcastFocus = desiredFocus;
            }

            var followT = 1f - Mathf.Exp(-broadcastPositionSpeed * Mathf.Max(dT, 0.001f));
            _broadcastFocus = Vector3.Lerp(_broadcastFocus, desiredFocus, followT);
            return _broadcastFocus;
        }

        private Vector3 _broadcastFocus = Vector3.zero;

        private void ApplyGtexBroadcastCamera(Vector3 focus, float dT)
        {
            var ball = Ball.Current;
            if (ball == null)
            {
                return;
            }

            var field = MatchManager.Current != null
                ? MatchManager.Current.SizeOfField
                : new Vector2(105f, 68f);
            var halfLength = Mathf.Max(1f, field.x * 0.5f);
            var halfWidth = Mathf.Max(1f, field.y * 0.5f);

            var velocity = ball.Velocity;
            velocity.y = 0f;
            var playDirection = velocity.sqrMagnitude > 0.04f
                ? velocity.normalized
                : Vector3.right;

            var side = new Vector3(-playDirection.z, 0f, playDirection.x);
            if (side.sqrMagnitude < 0.04f)
            {
                side = Vector3.back;
            }
            side.Normalize();

            var along = new Vector3(playDirection.x, 0f, playDirection.z) * -broadcastAlongPlayOffset;
            var desiredPosition = focus + side * broadcastSidelineOffset + along;
            desiredPosition.y = broadcastHeight;

            var xPadding = 8f;
            var zPadding = 4f;
            desiredPosition.x = Mathf.Clamp(desiredPosition.x, -xPadding, field.x + xPadding);
            desiredPosition.z = Mathf.Clamp(desiredPosition.z, -broadcastSidelineOffset, field.y + broadcastSidelineOffset);

            var lookTarget = focus + Vector3.up * 0.75f;
            var desiredRotation = Quaternion.LookRotation(lookTarget - desiredPosition, Vector3.up);
            var positionT = 1f - Mathf.Exp(-broadcastPositionSpeed * Mathf.Max(dT, 0.001f));
            var rotationT = 1f - Mathf.Exp(-broadcastRotationSpeed * Mathf.Max(dT, 0.001f));

            transform.position = Vector3.Lerp(transform.position, desiredPosition, positionT);
            transform.rotation = Quaternion.Slerp(transform.rotation, desiredRotation, rotationT);

            var ballSpeedRatio = Mathf.Clamp01(velocity.magnitude / 15f);
            var desiredFov = Mathf.Lerp(broadcastMaxFieldOfView, broadcastMinFieldOfView, ballSpeedRatio);
            desiredFov = Mathf.Clamp(desiredFov, broadcastMinFieldOfView, broadcastMaxFieldOfView);
            camera.fieldOfView = Mathf.Lerp(
                camera.fieldOfView,
                desiredFov,
                Mathf.Clamp01(dT * CameraZoomSpeed));
        }
    }
}
