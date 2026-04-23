using UnityEngine;

namespace FStudio.GTEX.Playback
{
    public sealed class GtexPlaybackSanitizer
    {
        public const float DefaultBallHeight = 0.1f;

        private readonly GtexPitchSpace pitchSpace;

        public GtexPlaybackSanitizer(GtexPitchSpace pitchSpace)
        {
            this.pitchSpace = pitchSpace ?? new GtexPitchSpace(
                GtexPitchSpace.DefaultLength,
                GtexPitchSpace.DefaultWidth,
                0f,
                Vector3.zero);
        }

        public GtexPitchSpace PitchSpace => pitchSpace;

        public bool TrySanitizePlayerPosition(Vector3 worldPosition, out Vector3 sanitizedPosition)
        {
            var isFinite = IsFinite(worldPosition);
            sanitizedPosition = isFinite
                ? pitchSpace.ClampWorld(worldPosition)
                : new Vector3(pitchSpace.Center.x, pitchSpace.GrassY, pitchSpace.Center.z);
            sanitizedPosition.y = pitchSpace.GrassY;
            return isFinite;
        }

        public bool TrySanitizeBallPosition(
            Vector3 worldPosition,
            out Vector3 sanitizedPosition,
            float minimumHeight = DefaultBallHeight)
        {
            var isFinite = IsFinite(worldPosition);
            sanitizedPosition = isFinite
                ? pitchSpace.ClampWorld(worldPosition)
                : new Vector3(pitchSpace.Center.x, pitchSpace.GrassY + minimumHeight, pitchSpace.Center.z);
            sanitizedPosition.y = Mathf.Max(pitchSpace.GrassY + Mathf.Max(0f, minimumHeight), sanitizedPosition.y);
            return isFinite;
        }

        public Vector3 SanitizePlayerPosition(Vector3 worldPosition)
        {
            TrySanitizePlayerPosition(worldPosition, out var sanitizedPosition);
            return sanitizedPosition;
        }

        public Vector3 SanitizeBallPosition(Vector3 worldPosition, float minimumHeight = DefaultBallHeight)
        {
            TrySanitizeBallPosition(worldPosition, out var sanitizedPosition, minimumHeight);
            return sanitizedPosition;
        }

        public static bool IsFinite(Vector3 value)
        {
            return float.IsFinite(value.x) &&
                   float.IsFinite(value.y) &&
                   float.IsFinite(value.z);
        }
    }
}
