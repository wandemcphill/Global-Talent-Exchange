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

        public MatchCamera CurrentCamera { get; private set; }

        public string CurrentCameraType { get; private set; }

        public Vector3? TargetPosition;

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
        /// Make the transition instant.
        /// </summary>
        public void FocusToBall (bool instant = true) {
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
        }

        private void Update() {
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
                if (TargetPosition.HasValue) {
                    targetPos = TargetPosition.Value;
                } else {
                    if (target == null) {
                        return;
                    }

                    targetPos = target.position;
                }

                var (position, rotation, zoom) = CurrentCamera.Behave(in dT, targetPos);

                if (instantTransitionInNextFrame) {
                    instantTransitionInNextFrame = false;

                    transform.position = position;
                    transform.rotation = rotation;
                    camera.fieldOfView = zoom / (ZoomMultiplier + 1);
                } else {
                    var rawPositionDifference = Vector3.Distance(transform.position, position) + 1f;
                    var rawRotationDifference = Quaternion.Angle(transform.rotation, rotation) + 1f;
                    var positionDifference = Mathf.Clamp(rawPositionDifference, 1f, 8f) * transitionValue;
                    var rotationDifference = Mathf.Clamp(rawRotationDifference, 1f, 24f) * transitionValue;
                    var positionLerp = Mathf.Clamp01(dT * CameraPositionSpeed * positionDifference * positionDifferencePower);
                    var rotationLerp = Mathf.Clamp01(dT * CameraRotationSpeed * rotationDifference * rotationDifferencePower);
                    transform.position = Vector3.Lerp(transform.position, position, positionLerp);
                    transform.rotation = Quaternion.Lerp(transform.rotation, rotation, rotationLerp);

                    camera.fieldOfView = Mathf.Lerp(camera.fieldOfView, zoom / (ZoomMultiplier + 1), dT * CameraZoomSpeed);
                }
            }
        }
    }
}
