using UnityEngine;

namespace Gtex.Match3D.Runtime
{
    public sealed class PitchController : MonoBehaviour
    {
        [SerializeField] private Transform surfaceTransform;

        public float LengthMeters { get; private set; } = 105f;
        public float WidthMeters { get; private set; } = 68f;
        public float HalfLength
        {
            get { return LengthMeters * 0.5f; }
        }

        public float HalfWidth
        {
            get { return WidthMeters * 0.5f; }
        }

        private void Awake()
        {
            if (surfaceTransform == null)
            {
                surfaceTransform = transform;
            }
        }

        public void ApplySceneNode(MatchSceneNodeDto node)
        {
            if (node == null || node.payload == null)
            {
                return;
            }

            float length = node.payload.lengthMeters > 0f ? node.payload.lengthMeters : 105f;
            float width = node.payload.widthMeters > 0f ? node.payload.widthMeters : 68f;
            ApplyDimensions(length, width);
        }

        public void ApplyDimensions(float lengthMeters, float widthMeters)
        {
            LengthMeters = Mathf.Max(1f, lengthMeters);
            WidthMeters = Mathf.Max(1f, widthMeters);

            if (surfaceTransform == null)
            {
                surfaceTransform = transform;
            }

            surfaceTransform.localPosition = Vector3.zero;
            surfaceTransform.localRotation = Quaternion.identity;
            surfaceTransform.localScale = new Vector3(LengthMeters / 10f, 1f, WidthMeters / 10f);
        }

        public void SetSurfaceTransform(Transform target)
        {
            surfaceTransform = target;
            ApplyDimensions(LengthMeters, WidthMeters);
        }

        public Vector3 ToWorldPosition(float normalizedX, float normalizedY, float elevation = 0f)
        {
            float clampedX = Mathf.Clamp(normalizedX, 0f, 100f);
            float clampedY = Mathf.Clamp(normalizedY, 0f, 100f);
            float worldX = ((clampedX / 100f) * LengthMeters) - HalfLength;
            float worldZ = ((clampedY / 100f) * WidthMeters) - HalfWidth;
            return new Vector3(worldX, elevation, worldZ);
        }
    }
}
