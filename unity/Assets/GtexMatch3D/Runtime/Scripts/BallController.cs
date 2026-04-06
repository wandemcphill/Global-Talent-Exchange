using UnityEngine;

namespace Gtex.Match3D.Runtime
{
    public sealed class BallController : MonoBehaviour
    {
        [SerializeField] private float positionLerpSpeed = 18f;
        [SerializeField] private float rotationLerpSpeed = 20f;
        [SerializeField] private float maxSnapDistance = 10f;

        private Vector3 _targetPosition;
        private Quaternion _targetRotation = Quaternion.identity;
        private Vector3 _targetVelocity;
        private float _spin;
        private string _state;
        private string _trajectoryType;

        public Vector3 Velocity
        {
            get { return _targetVelocity; }
        }

        public float Spin
        {
            get { return _spin; }
        }

        private void Awake()
        {
            _targetPosition = transform.position;
            _targetRotation = transform.rotation;
        }

        private void Update()
        {
            if (Vector3.Distance(transform.position, _targetPosition) > maxSnapDistance)
            {
                transform.position = _targetPosition;
            }
            else
            {
                float moveFactor = DampingFactor(positionLerpSpeed, Time.deltaTime);
                transform.position = Vector3.Lerp(transform.position, _targetPosition, moveFactor);
            }

            float rotateFactor = DampingFactor(rotationLerpSpeed, Time.deltaTime);
            transform.rotation = Quaternion.Slerp(transform.rotation, _targetRotation, rotateFactor);

            if (Mathf.Abs(_spin) > 0.001f)
            {
                transform.Rotate(Vector3.forward, _spin * 540f * Time.deltaTime, Space.Self);
            }
        }

        public void ApplySceneNode(MatchSceneNodeDto node, bool immediate, bool treatAsShot)
        {
            if (node == null)
            {
                return;
            }

            MatchScenePayloadDto payload = node.payload ?? new MatchScenePayloadDto();
            _targetPosition = node.position != null ? node.position.ToVector3() : transform.position;
            _targetVelocity = node.velocity != null ? node.velocity.ToVector3() : Vector3.zero;
            _spin = payload.spin;
            _state = payload.state;
            _trajectoryType = payload.trajectoryType;

            if (treatAsShot && _targetVelocity.sqrMagnitude > 0.0001f)
            {
                _targetRotation = Quaternion.LookRotation(_targetVelocity.normalized, Vector3.up);
            }
            else if (node.rotation != null)
            {
                _targetRotation = node.rotation.ToQuaternion();
            }

            if (immediate || Vector3.Distance(transform.position, _targetPosition) > maxSnapDistance)
            {
                SnapTo(_targetPosition, _targetRotation);
            }
        }

        public void ApplyReplayFrame(ReplayBallFrameData frame, bool immediate)
        {
            if (frame == null)
            {
                return;
            }

            _targetPosition = frame.position;
            _targetRotation = frame.rotation;
            _targetVelocity = frame.velocity;
            _spin = frame.spin;
            _state = frame.state;
            _trajectoryType = frame.trajectoryType;

            if (immediate)
            {
                SnapTo(_targetPosition, _targetRotation);
            }
        }

        public void MoveTo(Vector3 targetPosition)
        {
            _targetPosition = targetPosition;
        }

        public void MoveTo(Vector3 targetPosition, Vector3 velocity, float spinAmount)
        {
            _targetPosition = targetPosition;
            _targetVelocity = velocity;
            _spin = spinAmount;
            if (velocity.sqrMagnitude > 0.0001f)
            {
                _targetRotation = Quaternion.LookRotation(velocity.normalized, Vector3.up);
            }
        }

        public void ApplyShot(Vector3 velocity, float spinAmount)
        {
            _targetVelocity = velocity;
            _spin = spinAmount;
            if (velocity.sqrMagnitude > 0.0001f)
            {
                _targetRotation = Quaternion.LookRotation(velocity.normalized, Vector3.up);
            }
        }

        public void ApplySimulationPose(
            Vector3 position,
            Vector3 velocity,
            float spinAmount,
            bool immediate)
        {
            _targetPosition = position;
            _targetVelocity = velocity;
            _spin = spinAmount;

            if (velocity.sqrMagnitude > 0.0001f)
            {
                _targetRotation = Quaternion.LookRotation(velocity.normalized, Vector3.up);
            }

            if (immediate)
            {
                SnapTo(_targetPosition, _targetRotation);
            }
        }

        public ReplayBallFrameData BuildReplayFrame()
        {
            ReplayBallFrameData frame = new ReplayBallFrameData();
            frame.position = transform.position;
            frame.rotation = transform.rotation;
            frame.velocity = _targetVelocity;
            frame.spin = _spin;
            frame.state = _state;
            frame.trajectoryType = _trajectoryType;
            return frame;
        }

        public void SnapTo(Vector3 position, Quaternion rotation)
        {
            transform.position = position;
            transform.rotation = rotation;
            _targetPosition = position;
            _targetRotation = rotation;
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
