using UnityEngine;

namespace FStudio.GTEX.Playback
{
    public sealed class GtexPitchZoneHelper
    {
        public const int HomeTeamSide = 0;
        public const int AwayTeamSide = 1;

        private const float PenaltyDepthRatio = 16.5f / 105f;
        private const float PenaltyWidthRatio = 40.32f / 68f;
        private const float SixYardDepthRatio = 5.5f / 105f;
        private const float SixYardWidthRatio = 18.32f / 68f;
        private const float GoalWidthRatio = 7.32f / 68f;

        private readonly GtexPitchSpace pitchSpace;
        private readonly Vector3 homeToAwayAxis;
        private readonly Vector3 lateralAxis;

        public GtexPitchZoneHelper(GtexPitchSpace pitchSpace)
        {
            this.pitchSpace = pitchSpace;

            var rawPrimaryAxis = Vector3.right;
            if (pitchSpace != null)
            {
                rawPrimaryAxis = pitchSpace.GetAwayGoalCenter() - pitchSpace.GetHomeGoalCenter();
                rawPrimaryAxis.y = 0f;
            }

            if (rawPrimaryAxis.sqrMagnitude <= 0.0001f)
            {
                rawPrimaryAxis = Vector3.right;
            }

            homeToAwayAxis = rawPrimaryAxis.normalized;

            var rawLateralAxis = Vector3.Cross(Vector3.up, homeToAwayAxis);
            if (rawLateralAxis.sqrMagnitude <= 0.0001f)
            {
                rawLateralAxis = Vector3.forward;
            }

            lateralAxis = rawLateralAxis.normalized;
        }

        public GtexPitchSpace PitchSpace => pitchSpace;

        public Vector3 HomeToAwayAxis => homeToAwayAxis;

        public Vector3 LateralAxis => lateralAxis;

        public bool IsInsidePlayableGrass(Vector3 worldPos)
        {
            if (pitchSpace == null || !GtexPlaybackSanitizer.IsFinite(worldPos))
            {
                return false;
            }

            var local = ToPitchLocal(worldPos);
            return local.x >= -pitchSpace.HalfLength &&
                   local.x <= pitchSpace.HalfLength &&
                   local.y >= -pitchSpace.HalfWidth &&
                   local.y <= pitchSpace.HalfWidth &&
                   worldPos.y >= pitchSpace.GrassY - 0.05f;
        }

        public Vector3 ClampToPlayableGrass(Vector3 worldPos, float margin)
        {
            if (pitchSpace == null)
            {
                return worldPos;
            }

            if (!GtexPlaybackSanitizer.IsFinite(worldPos))
            {
                worldPos = pitchSpace.Center;
            }

            var local = ToPitchLocal(worldPos);
            var clampedMargin = Mathf.Max(0f, margin);
            var halfLength = Mathf.Max(0.1f, pitchSpace.HalfLength - clampedMargin);
            var halfWidth = Mathf.Max(0.1f, pitchSpace.HalfWidth - clampedMargin);
            local.x = Mathf.Clamp(local.x, -halfLength, halfLength);
            local.y = Mathf.Clamp(local.y, -halfWidth, halfWidth);
            return FromPitchLocal(local, Mathf.Max(pitchSpace.GrassY, worldPos.y));
        }

        public bool IsInsidePenaltyArea(Vector3 worldPos, int teamSide)
        {
            return IsInsideTeamZone(worldPos, teamSide, GetPenaltyDepth(), GetPenaltyHalfWidth());
        }

        public bool IsInsideSixYardArea(Vector3 worldPos, int teamSide)
        {
            return IsInsideTeamZone(worldPos, teamSide, GetSixYardDepth(), GetSixYardHalfWidth());
        }

        public bool IsInsideGoalkeeperHomeZone(Vector3 worldPos, int teamSide)
        {
            return IsInsideTeamZone(worldPos, teamSide, GetGoalkeeperHomeDepth(), GetGoalkeeperHomeHalfWidth());
        }

        public Vector3 ClampGoalkeeperHome(Vector3 worldPos, int teamSide)
        {
            if (pitchSpace == null)
            {
                return worldPos;
            }

            if (!GtexPlaybackSanitizer.IsFinite(worldPos))
            {
                worldPos = GetGoalCenter(teamSide);
            }

            var local = ToPitchLocal(worldPos);
            var depth = GetGoalkeeperHomeDepth();
            var halfWidth = GetGoalkeeperHomeHalfWidth();

            if (IsHomeTeam(teamSide))
            {
                local.x = Mathf.Clamp(local.x, -pitchSpace.HalfLength, -pitchSpace.HalfLength + depth);
            }
            else
            {
                local.x = Mathf.Clamp(local.x, pitchSpace.HalfLength - depth, pitchSpace.HalfLength);
            }

            local.y = Mathf.Clamp(local.y, -halfWidth, halfWidth);
            return FromPitchLocal(local, Mathf.Max(pitchSpace.GrassY, worldPos.y));
        }

        public bool IsLegalGoalVisualPosition(Transform goal, int teamSide)
        {
            if (goal == null || pitchSpace == null)
            {
                return false;
            }

            var local = ToPitchLocal(goal.position);
            var expectedGoalLine = GetGoalLineCoordinate(teamSide);
            var maxInfieldInset = Mathf.Clamp(pitchSpace.Length * 0.025f, 1f, 2.8f);
            var maxOutfieldDrift = 0.9f;
            var maxLateralDrift = Mathf.Clamp(pitchSpace.Width * 0.04f, 1.15f, 2.4f);
            var onGoalLine =
                IsHomeTeam(teamSide)
                    ? local.x >= expectedGoalLine - maxOutfieldDrift &&
                      local.x <= expectedGoalLine + maxInfieldInset
                    : local.x <= expectedGoalLine + maxOutfieldDrift &&
                      local.x >= expectedGoalLine - maxInfieldInset;

            if (!onGoalLine || Mathf.Abs(local.y) > maxLateralDrift)
            {
                return false;
            }

            var expectedForward = IsHomeTeam(teamSide) ? homeToAwayAxis : -homeToAwayAxis;
            var flattenedForward = Vector3.ProjectOnPlane(goal.forward, Vector3.up);
            if (flattenedForward.sqrMagnitude <= 0.0001f)
            {
                return false;
            }

            flattenedForward.Normalize();
            return Vector3.Dot(flattenedForward, expectedForward) >= 0.4f;
        }

        public Vector3 GetGoalCenter(int teamSide)
        {
            if (pitchSpace == null)
            {
                return Vector3.zero;
            }

            return IsHomeTeam(teamSide)
                ? pitchSpace.Center - homeToAwayAxis * pitchSpace.HalfLength
                : pitchSpace.Center + homeToAwayAxis * pitchSpace.HalfLength;
        }

        public float GetGoalLineCoordinate(int teamSide)
        {
            if (pitchSpace == null)
            {
                return 0f;
            }

            return IsHomeTeam(teamSide) ? -pitchSpace.HalfLength : pitchSpace.HalfLength;
        }

        public Bounds GetPenaltyBoxBounds(int teamSide)
        {
            return BuildZoneBounds(teamSide, GetPenaltyDepth(), GetPenaltyHalfWidth());
        }

        public Vector3 GetSafeCameraFocusPoint(Vector3 target)
        {
            if (pitchSpace == null)
            {
                return target;
            }

            var cameraMargin =
                Mathf.Clamp(
                    Mathf.Min(pitchSpace.HalfLength * 0.09f, pitchSpace.HalfWidth * 0.16f),
                    2.8f,
                    6.25f);
            return ClampToPlayableGrass(target, cameraMargin);
        }

        public float DistanceToGoalCenter(Vector3 worldPos, int teamSide)
        {
            var goalCenter = GetGoalCenter(teamSide);
            var planarOffset = worldPos - goalCenter;
            planarOffset.y = 0f;
            return planarOffset.magnitude;
        }

        private bool IsInsideTeamZone(Vector3 worldPos, int teamSide, float depth, float halfWidth)
        {
            if (pitchSpace == null || !GtexPlaybackSanitizer.IsFinite(worldPos))
            {
                return false;
            }

            var local = ToPitchLocal(worldPos);
            if (Mathf.Abs(local.y) > halfWidth)
            {
                return false;
            }

            if (IsHomeTeam(teamSide))
            {
                return local.x >= -pitchSpace.HalfLength &&
                       local.x <= -pitchSpace.HalfLength + depth;
            }

            return local.x <= pitchSpace.HalfLength &&
                   local.x >= pitchSpace.HalfLength - depth;
        }

        private Bounds BuildZoneBounds(int teamSide, float depth, float halfWidth)
        {
            if (pitchSpace == null)
            {
                return default;
            }

            var goalLine = GetGoalLineCoordinate(teamSide);
            var nearAttack = IsHomeTeam(teamSide) ? goalLine + depth : goalLine - depth;
            var cornerA = FromPitchLocal(new Vector2(goalLine, -halfWidth), pitchSpace.GrassY);
            var cornerB = FromPitchLocal(new Vector2(goalLine, halfWidth), pitchSpace.GrassY);
            var cornerC = FromPitchLocal(new Vector2(nearAttack, -halfWidth), pitchSpace.GrassY);
            var cornerD = FromPitchLocal(new Vector2(nearAttack, halfWidth), pitchSpace.GrassY);
            var bounds = new Bounds(cornerA, Vector3.zero);
            bounds.Encapsulate(cornerB);
            bounds.Encapsulate(cornerC);
            bounds.Encapsulate(cornerD);
            return bounds;
        }

        private Vector2 ToPitchLocal(Vector3 worldPos)
        {
            if (pitchSpace == null)
            {
                return Vector2.zero;
            }

            var offset = worldPos - pitchSpace.Center;
            return new Vector2(
                Vector3.Dot(offset, homeToAwayAxis),
                Vector3.Dot(offset, lateralAxis));
        }

        private Vector3 FromPitchLocal(Vector2 local, float y)
        {
            if (pitchSpace == null)
            {
                return new Vector3(local.x, y, local.y);
            }

            return pitchSpace.Center +
                   homeToAwayAxis * local.x +
                   lateralAxis * local.y +
                   Vector3.up * (y - pitchSpace.Center.y);
        }

        private float GetPenaltyDepth()
        {
            return pitchSpace != null ? pitchSpace.Length * PenaltyDepthRatio : 16.5f;
        }

        private float GetPenaltyHalfWidth()
        {
            return pitchSpace != null ? pitchSpace.Width * PenaltyWidthRatio * 0.5f : 20.16f;
        }

        private float GetSixYardDepth()
        {
            return pitchSpace != null ? pitchSpace.Length * SixYardDepthRatio : 5.5f;
        }

        private float GetSixYardHalfWidth()
        {
            return pitchSpace != null ? pitchSpace.Width * SixYardWidthRatio * 0.5f : 9.16f;
        }

        private float GetGoalkeeperHomeDepth()
        {
            return Mathf.Max(GetSixYardDepth() + 2.25f, GetPenaltyDepth() * 0.46f);
        }

        private float GetGoalkeeperHomeHalfWidth()
        {
            return Mathf.Min(GetPenaltyHalfWidth(), Mathf.Max(GetSixYardHalfWidth() + 2.25f, pitchSpace != null ? pitchSpace.Width * GoalWidthRatio * 0.85f : 5.5f));
        }

        private static bool IsHomeTeam(int teamSide)
        {
            return teamSide != AwayTeamSide;
        }
    }
}
