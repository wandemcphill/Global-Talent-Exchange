using System;
using UnityEngine;

namespace FStudio.GTEX.Playback
{
    public sealed class GtexPitchSpace
    {
        public const float DefaultLength = 105f;
        public const float DefaultWidth = 68f;

        public GtexPitchSpace(float length, float width, float grassY, Vector3 center)
        {
            Length = Mathf.Max(1f, float.IsFinite(length) ? length : DefaultLength);
            Width = Mathf.Max(1f, float.IsFinite(width) ? width : DefaultWidth);
            GrassY = float.IsFinite(grassY) ? grassY : 0f;

            if (!float.IsFinite(center.x) || !float.IsFinite(center.y) || !float.IsFinite(center.z))
            {
                center = Vector3.zero;
            }

            Center = new Vector3(center.x, GrassY, center.z);
        }

        public float Length { get; }

        public float Width { get; }

        public float GrassY { get; }

        public Vector3 Center { get; }

        public float HalfLength => Length * 0.5f;

        public float HalfWidth => Width * 0.5f;

        public float MinX => Center.x - HalfLength;

        public float MaxX => Center.x + HalfLength;

        public float MinZ => Center.z - HalfWidth;

        public float MaxZ => Center.z + HalfWidth;

        public Vector3 ClampWorld(Vector3 worldPosition)
        {
            if (!float.IsFinite(worldPosition.x))
            {
                worldPosition.x = Center.x;
            }

            if (!float.IsFinite(worldPosition.y))
            {
                worldPosition.y = GrassY;
            }

            if (!float.IsFinite(worldPosition.z))
            {
                worldPosition.z = Center.z;
            }

            worldPosition.x = Mathf.Clamp(worldPosition.x, MinX, MaxX);
            worldPosition.y = Mathf.Max(GrassY, worldPosition.y);
            worldPosition.z = Mathf.Clamp(worldPosition.z, MinZ, MaxZ);
            return worldPosition;
        }

        public bool IsOutsideWorld(Vector3 worldPosition)
        {
            if (!float.IsFinite(worldPosition.x) ||
                !float.IsFinite(worldPosition.y) ||
                !float.IsFinite(worldPosition.z))
            {
                return true;
            }

            return worldPosition.x < MinX ||
                   worldPosition.x > MaxX ||
                   worldPosition.z < MinZ ||
                   worldPosition.z > MaxZ ||
                   worldPosition.y < GrassY - 0.01f;
        }

        public Vector3 NormalizedToWorld(Vector3 normalizedPosition)
        {
            var normalizedX = Mathf.Clamp01(float.IsFinite(normalizedPosition.x) ? normalizedPosition.x : 0.5f);
            var normalizedZ = Mathf.Clamp01(float.IsFinite(normalizedPosition.z) ? normalizedPosition.z : 0.5f);
            var relativeY = float.IsFinite(normalizedPosition.y) ? normalizedPosition.y : 0f;

            return new Vector3(
                Mathf.Lerp(MinX, MaxX, normalizedX),
                GrassY + relativeY,
                Mathf.Lerp(MinZ, MaxZ, normalizedZ));
        }

        public Vector3 WorldToNormalized(Vector3 worldPosition)
        {
            var sanitized = ClampWorld(worldPosition);
            return new Vector3(
                Mathf.InverseLerp(MinX, MaxX, sanitized.x),
                sanitized.y - GrassY,
                Mathf.InverseLerp(MinZ, MaxZ, sanitized.z));
        }

        public Vector3 GetHomeGoalCenter()
        {
            return new Vector3(MinX, GrassY, Center.z);
        }

        public Vector3 GetAwayGoalCenter()
        {
            return new Vector3(MaxX, GrassY, Center.z);
        }

        public override string ToString()
        {
            return
                "length=" + Length.ToString("0.##") +
                " width=" + Width.ToString("0.##") +
                " grassY=" + GrassY.ToString("0.##") +
                " center=(" + Center.x.ToString("0.##") + "," + Center.z.ToString("0.##") + ")";
        }
    }
}
