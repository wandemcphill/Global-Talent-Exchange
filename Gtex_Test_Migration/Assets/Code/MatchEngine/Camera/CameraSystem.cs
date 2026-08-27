using UnityEngine;
using FStudio.Utilities;
using FStudio.MatchEngine.Balls;
using FStudio.Events;
using FStudio.UI.Events;
using FStudio.MatchEngine.Events;
using System.Threading.Tasks;

namespace FStudio.MatchEngine.Cameras {
    [RequireComponent (typeof (Camera))]
    public class CameraSystem : SceneObjectSingleton<CameraSystem> {
#pragma warning disable 0109
        public new Camera camera = default;
#pragma warning restore 0109

        [SerializeField] private SerializableAssetCollection<string, MatchCamera> matchCameras =
            new SerializableAssetCollection<string, MatchCamera>();

        [SerializeField] public Transform target = default;

        [SerializeField] private float positionDifferencePower = 0.25f;
        [SerializeField] private float rotationDifferencePower = 0.25f;

        public float ZoomMultiplier;

        private bool isInTransition = false;
        private float transitionValue = 1;

        private bool instantTransitionInNextFrame = false;

        [SerializeField] private float transitionSpeed = 0.5f;

        [Header("Camera Speed")]
        public float CameraPositionSpeed = 4;
        public float CameraRotationSpeed = 20;
        public float CameraZoomSpeed = 4;

        [Header("GTEX Broadcast Presentation")]
        [SerializeField] private float broadcastMinFieldOfView = 42f;
        [SerializeField] private float broadcastMaxFieldOfView = 55f;
        [SerializeField] private float broadcastLookAheadDistance = 3.5f;
        [SerializeField] private float broadcastPositionSpeed = 7f;
        [SerializeField] private float broadcastRotationSpeed = 24f;

        public MatchCamera CurrentCamera { get; private set; }

        public string CurrentCameraType { get; private set; }

        public Vector3? TargetPosition;

        private bool IsBroadcastCamera =>
            string.Equals(CurrentCameraType, "TVBroadcast", System.StringComparison.OrdinalIgnoreCase) ||
            string.Equals(CurrentCameraType, "Broadcast", System.StringComparison.OrdinalIgnoreCase);

        private void ActiveCameraChanged () {
            if (target == null) {
                EventManager.Trigger<MatchCameraActiveEvent>(null);
            } else {
                EventManager.Trigger(new MatchCameraActiveEvent());
            }
        }

        public void SetTarget(Transform target) {
            Debug.Log($"[SetTarget] {target}");
            this.target = target;
            ActiveCameraChanged();
        }

        public async Task SwitchCamera(string cameraType, bool instant = true) {
            var resolvedCameraType = ResolveCameraAlias(cameraType);
            Debug.Log($"[CameraSystem] Switch Camera: {cameraType} -> {resolvedCameraType}");
            var resolvedCamera = await matchCameras.FindAsync(resolvedCameraType);
            if (resolvedCamera == null && !string.Equals(resolvedCameraType, "Stadium", System.StringComparison.OrdinalIgnoreCase)) {
                resolvedCameraType = "Stadium";
                resolvedCamera = await matchCameras.FindAsync(resolvedCameraType);
            }

            if (resolvedCamera == null) {
                Debug.LogWarning($"[CameraSystem] Camera asset not found for requested type '{cameraType}'.");
                return;
            }

            CurrentCamera = resolvedCamera;
            CurrentCameraType = resolvedCameraType;
            isInTransition = false;
            instantTransitionInNextFrame = instant;
            TargetPosition = null;

            ActiveCameraChanged();
        }

        private static string ResolveCameraAlias(string cameraType) {
            var normalized = (cameraType ?? string.Empty).Trim();
            if (string.Equals(normalized, "Broadcast", System.StringComparison.OrdinalIgnoreCase)) {
                return "TVBroadcast";
            }

            return normalized;
        }

        private async void Start() {
            // GTEX's live broadcast director uses the semantic camera name
            // "Broadcast". The original asset collection ships the actual
            // production camera as "TVBroadcast". Resolve that alias here so
            // live play never silently falls back to the generic Stadium camera.
            await SwitchCamera("TVBroadcast");
        }

        /// <summary>
        /// Make the transition instant and bind the camera to the live ball.
        /// </summary>
        public void FocusToBall (bool instant = true) {
            if (Ball.Current == null) {
                return;
            }

            SetTarget(Ball.Current.transform);
            TargetPosition = null;

            instantTransitionInNextFrame = instant;
            isInTransition = false;
        }

        public void FocusToPosition(Vector3 position, bool instant = true) {
            if (target == null && Ball.Current != null) {
                SetTarget(Ball.Current.transform);
            }

            TargetPosition = position;
            instantTransitionInNextFrame = instant;
            isInTransition = false;
        }

        private void OnValidate() {
            camera = GetComponent<Camera>();
            broadcastMinFieldOfView = Mathf.Clamp(broadcastMinFieldOfView, 25f, 75f);
            broadcastMaxFieldOfView = Mathf.Max(broadcastMinFieldOfView, broadcastMaxFieldOfView);
            broadcastLookAheadDistance = Mathf.Clamp(broadcastLookAheadDistance, 0f, 10f);
            broadcastPositionSpeed = Mathf.Max(1f, broadcastPositionSpeed);
            broadcastRotationSpeed = Mathf.Max(1f, broadcastRotationSpeed);
        }

        private void Update() {
            if (target == null && Ball.Current != null) {
                target = Ball.Current.transform;
            }

            if (target == null) {
                return;
            }

            var dT = Mathf.Max(0.001f, Time.unscaledDeltaTime);

            if (isInTransition) {
                transitionValue += dT * transitionSpeed;

                if (transitionValue >= 1 ) {
                    isInTransition = false;
                }
            } else {
                transitionValue = 1;
            }

            if (CurrentCamera != null) {
                Vector3 targetPos;
                if (IsBroadcastCamera && Ball.Current != null) {
                    // The broadcast camera must follow the actual live ball every frame.
                    // Do not allow a stale TargetPosition from an action/replay cue to
                    // pin the camera to a static world coordinate.
                    TargetPosition = null;
                    targetPos = Ball.Current.transform.position;

                    var ballVelocity = Ball.Current.GetComponent<Rigidbody>() != null
                        ? Ball.Current.GetComponent<Rigidbody>().linearVelocity
                        : Vector3.zero;
                    ballVelocity.y = 0f;
                    if (ballVelocity.sqrMagnitude > 0.0001f) {
                        targetPos += Vector3.ClampMagnitude(ballVelocity.normalized * broadcastLookAheadDistance, broadcastLookAheadDistance);
                    }
                } else if (TargetPosition.HasValue) {
                    targetPos = TargetPosition.Value;
                } else {
                    targetPos = target.position;
                }

                if (IsBroadcastCamera && Ball.Current != null)
                {
                    ApplyGtexBroadcastCamera(targetPos, dT);
                    return;
                }

                var (position, rotation, zoom) = CurrentCamera.Behave(in dT, targetPos);

                if (instantTransitionInNextFrame) {
                    instantTransitionInNextFrame = false;

                    transform.position = position;
                    transform.rotation = rotation;
                    var instantFov = zoom / (ZoomMultiplier + 1);
                    camera.fieldOfView = IsBroadcastCamera
                        ? Mathf.Clamp(instantFov, broadcastMinFieldOfView, broadcastMaxFieldOfView)
                        : instantFov;
                } else {
                    var rawPositionDifference = Vector3.Distance(transform.position, position) + 1f;
                    var rawRotationDifference = Quaternion.Angle(transform.rotation, rotation) + 1f;
                    var positionDifference = Mathf.Clamp(rawPositionDifference, 1f, 8f) * transitionValue;
                    var rotationDifference = Mathf.Clamp(rawRotationDifference, 1f, 24f) * transitionValue;
                    var positionSpeed = IsBroadcastCamera ? broadcastPositionSpeed : CameraPositionSpeed;
                    var rotationSpeed = IsBroadcastCamera ? broadcastRotationSpeed : CameraRotationSpeed;
                    var positionLerp = Mathf.Clamp01(dT * positionSpeed * positionDifference * positionDifferencePower);
                    var rotationLerp = Mathf.Clamp01(dT * rotationSpeed * rotationDifference * rotationDifferencePower);
                    transform.position = Vector3.Lerp(transform.position, position, positionLerp);
                    transform.rotation = Quaternion.Lerp(transform.rotation, rotation, rotationLerp);

                    var desiredFov = zoom / (ZoomMultiplier + 1);
                    if (IsBroadcastCamera) {
                        desiredFov = Mathf.Clamp(desiredFov, broadcastMinFieldOfView, broadcastMaxFieldOfView);
                    }

                    camera.fieldOfView = Mathf.Lerp(camera.fieldOfView, desiredFov, Mathf.Clamp01(dT * CameraZoomSpeed));
                }
            }
        }

        private void ApplyGtexBroadcastCamera(Vector3 targetPos, float dT)
        {
            var ball = Ball.Current;
            if (ball == null) return;
            var velocity = ball.Velocity;
            velocity.y = 0f;
            var direction = velocity.sqrMagnitude > 0.04f ? velocity.normalized : Vector3.right;
            var target = targetPos;
            target.y = 0f;
            var desiredPosition = new Vector3(target.x - Mathf.Clamp(direction.x * 3.5f, -3.5f, 3.5f), 18f, Mathf.Clamp(target.z - 27f, -46f, 46f));
            var lookAt = target + Vector3.up * 0.8f;
            var desiredRotation = Quaternion.LookRotation(lookAt - desiredPosition, Vector3.up);
            var positionT = 1f - Mathf.Exp(-7.5f * Mathf.Max(dT, 0.001f));
            var rotationT = 1f - Mathf.Exp(-12f * Mathf.Max(dT, 0.001f));
            transform.position = Vector3.Lerp(transform.position, desiredPosition, positionT);
            transform.rotation = Quaternion.Slerp(transform.rotation, desiredRotation, rotationT);
            var desiredFov = Mathf.Lerp(52f, 47f, Mathf.Clamp01(velocity.magnitude / 12f));
            camera.fieldOfView = Mathf.Lerp(camera.fieldOfView, desiredFov, Mathf.Clamp01(dT * CameraZoomSpeed));
        }
    }
}
