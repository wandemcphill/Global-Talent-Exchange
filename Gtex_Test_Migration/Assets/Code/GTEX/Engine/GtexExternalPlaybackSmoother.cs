using UnityEngine;

namespace FStudio.GTEX.Engine
{
    [DisallowMultipleComponent]
    public sealed class GtexExternalPlaybackSmoother : MonoBehaviour
    {
        [SerializeField] private float positionSmoothTime = 0.10f;
        [SerializeField] private float rotationDegreesPerSecond = 720f;
        [SerializeField] private float maxPositionSpeed = 14f;
        [SerializeField] private float snapDistance = 12f;

        private Vector3 targetPosition;
        private Quaternion targetRotation = Quaternion.identity;
        private Vector3 positionVelocity;
        private bool initialized;
        private bool active;

        public Vector3 TargetPosition => targetPosition;

        public void SetTarget(Vector3 position, Quaternion rotation, bool snap)
        {
            if (!GtexPlaybackSanitizer.IsFinite(position))
            {
                return;
            }

            rotation = Quaternion.Euler(0f, rotation.eulerAngles.y, 0f);
            targetPosition = position;
            targetRotation = rotation;
            active = true;

            if (!initialized || snap || Vector3.Distance(transform.position, targetPosition) > snapDistance)
            {
                transform.SetPositionAndRotation(targetPosition, targetRotation);
                positionVelocity = Vector3.zero;
                initialized = true;
            }
        }

        public void Clear()
        {
            active = false;
            positionVelocity = Vector3.zero;
        }

        private void Awake()
        {
            targetPosition = transform.position;
            targetRotation = transform.rotation;
            initialized = true;
        }

        private void LateUpdate()
        {
            if (!active)
            {
                return;
            }

            var dt = Mathf.Max(Time.unscaledDeltaTime, 1f / 120f);
            var nextPosition = Vector3.SmoothDamp(
                transform.position,
                targetPosition,
                ref positionVelocity,
                Mathf.Max(0.025f, positionSmoothTime),
                Mathf.Max(0.5f, maxPositionSpeed),
                dt);

            transform.position = nextPosition;
            transform.rotation = Quaternion.RotateTowards(
                transform.rotation,
                targetRotation,
                Mathf.Max(30f, rotationDegreesPerSecond) * dt);

            if (Vector3.Distance(transform.position, targetPosition) < 0.0025f)
            {
                transform.SetPositionAndRotation(targetPosition, targetRotation);
                positionVelocity = Vector3.zero;
            }
        }
    }
}
