using System;
using UnityEngine;

namespace Gtex.Match3D.Runtime
{
    [RequireComponent(typeof(Camera))]
    public sealed class CameraController : MonoBehaviour
    {
        [SerializeField] private float positionLerpSpeed = 8f;
        [SerializeField] private float rotationLerpSpeed = 10f;
        [SerializeField] private float broadcastFov = 50f;
        [SerializeField] private float sidelineFov = 44f;
        [SerializeField] private float goalboxFov = 36f;
        [SerializeField] private float tacticalFov = 58f;
        [SerializeField] private float cinematicFov = 38f;

        private Camera _camera;
        private Vector3 _targetPosition;
        private Vector3 _lookTarget;
        private string _mode = "followBall";
        private string _projectionPreset = "broadcast";
        private Transform _trackedBall;
        private Transform _primaryFocus;
        private Transform _secondaryFocus;

        private void Awake()
        {
            _camera = GetComponent<Camera>();
            _targetPosition = transform.position;
            _lookTarget = transform.position + (transform.forward * 10f);
        }

        private void LateUpdate()
        {
            float moveFactor = DampingFactor(positionLerpSpeed, Time.deltaTime);
            float rotateFactor = DampingFactor(rotationLerpSpeed, Time.deltaTime);
            transform.position = Vector3.Lerp(transform.position, _targetPosition, moveFactor);

            Vector3 desiredTarget = _lookTarget;
            if (string.Equals(_mode, "cinematic", StringComparison.OrdinalIgnoreCase) && _primaryFocus != null)
            {
                desiredTarget = Vector3.Lerp(_lookTarget, _primaryFocus.position, 0.45f);
            }
            else if (string.Equals(_mode, "followBall", StringComparison.OrdinalIgnoreCase) && _trackedBall != null)
            {
                desiredTarget = Vector3.Lerp(_lookTarget, _trackedBall.position, 0.60f);
            }

            if (_secondaryFocus != null && string.Equals(_mode, "tactical", StringComparison.OrdinalIgnoreCase))
            {
                desiredTarget = Vector3.Lerp(desiredTarget, _secondaryFocus.position, 0.20f);
            }

            Vector3 direction = desiredTarget - transform.position;
            if (direction.sqrMagnitude > 0.0001f)
            {
                Quaternion desiredRotation = Quaternion.LookRotation(direction.normalized, Vector3.up);
                transform.rotation = Quaternion.Slerp(transform.rotation, desiredRotation, rotateFactor);
            }

            UpdateFieldOfView();
        }

        public void ApplyRig(
            MatchCameraRigDto rig,
            MatchSceneActionDto action,
            Transform ballTransform,
            Transform primaryFocus,
            Transform secondaryFocus,
            bool immediate)
        {
            if (rig == null)
            {
                return;
            }

            _trackedBall = ballTransform;
            _primaryFocus = primaryFocus;
            _secondaryFocus = secondaryFocus;
            _mode = !string.IsNullOrWhiteSpace(rig.mode)
                ? rig.mode
                : action != null ? action.cameraMode : "followBall";
            _projectionPreset = !string.IsNullOrWhiteSpace(rig.projectionPreset)
                ? rig.projectionPreset
                : "broadcast";
            _targetPosition = rig.position != null ? rig.position.ToVector3() : transform.position;
            _lookTarget = rig.target != null ? rig.target.ToVector3() : transform.position + transform.forward;

            if (immediate)
            {
                transform.position = _targetPosition;
                FocusPoint(_lookTarget, true);
            }
        }

        public void ApplyReplayFrame(ReplayCameraFrameData frame, bool immediate)
        {
            if (frame == null)
            {
                return;
            }

            _mode = frame.mode;
            _projectionPreset = frame.projectionPreset;
            _targetPosition = frame.position;
            _lookTarget = frame.target;

            if (immediate)
            {
                transform.position = _targetPosition;
                FocusPoint(_lookTarget, true);
            }
        }

        public ReplayCameraFrameData BuildReplayFrame()
        {
            ReplayCameraFrameData frame = new ReplayCameraFrameData();
            frame.position = transform.position;
            frame.target = _lookTarget;
            frame.mode = _mode;
            frame.projectionPreset = _projectionPreset;
            return frame;
        }

        public void FocusBall()
        {
            if (_trackedBall != null)
            {
                _lookTarget = _trackedBall.position;
            }
        }

        public void FocusTransform(Transform target)
        {
            if (target != null)
            {
                _lookTarget = target.position;
            }
        }

        private void FocusPoint(Vector3 target, bool snap)
        {
            _lookTarget = target;
            Vector3 direction = target - transform.position;
            if (!snap || direction.sqrMagnitude <= 0.0001f)
            {
                return;
            }

            transform.rotation = Quaternion.LookRotation(direction.normalized, Vector3.up);
        }

        private void UpdateFieldOfView()
        {
            if (_camera == null)
            {
                return;
            }

            float targetFov;
            if (string.Equals(_mode, "tactical", StringComparison.OrdinalIgnoreCase))
            {
                targetFov = tacticalFov;
            }
            else if (string.Equals(_mode, "cinematic", StringComparison.OrdinalIgnoreCase))
            {
                targetFov = cinematicFov;
            }
            else if (string.Equals(_projectionPreset, "sideline", StringComparison.OrdinalIgnoreCase))
            {
                targetFov = sidelineFov;
            }
            else if (string.Equals(_projectionPreset, "goalbox", StringComparison.OrdinalIgnoreCase))
            {
                targetFov = goalboxFov;
            }
            else
            {
                targetFov = broadcastFov;
            }

            _camera.fieldOfView = Mathf.Lerp(_camera.fieldOfView, targetFov, DampingFactor(6f, Time.unscaledDeltaTime));
        }

        private static float DampingFactor(float speed, float deltaTime)
        {
            if (speed <= 0f)
            {
                return 1f;
            }

            return 1f - Mathf.Exp(-speed * deltaTime);
        }
    }
}
