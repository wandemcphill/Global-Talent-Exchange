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

        public Vector3 PitchCenter => pitchSpace != null ? pitchSpace.Center : Vector3.zero;

        public float HalfLength => pitchSpace != null ? pitchSpace.HalfLength : 52.5f;

        public float HalfWidth => pitchSpace != null ? pitchSpace.HalfWidth : 34f;

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
            var maxInfieldInset = Mathf.Clamp(pitchSpace.Length * 0.055f, 2.2f, 5.8f);
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

        public void SnapGoalVisual(Transform goal, int teamSide, bool rotateToFacePitch = true)
        {
            if (goal == null || pitchSpace == null)
            {
                return;
            }

            goal.position = GetGoalVisualCenter(teamSide, Mathf.Clamp(pitchSpace.Length * 0.021f, 1.85f, 2.6f));
            if (!rotateToFacePitch)
            {
                return;
            }

            var look = Vector3.ProjectOnPlane(PitchCenter - goal.position, Vector3.up);
            if (look.sqrMagnitude <= 0.001f)
            {
                return;
            }

            goal.rotation = Quaternion.LookRotation(look.normalized, Vector3.up);
        }

        public void ValidateGoalVisual(Transform goal, int teamSide, string label)
        {
            if (goal == null)
            {
                Debug.LogWarning("[GTEX Pitch] Missing goal visual: " + label);
                return;
            }

            if (IsLegalGoalVisualPosition(goal, teamSide))
            {
                return;
            }

            var local = ToPitchLocal(goal.position);
            Debug.LogWarning(
                "[GTEX Pitch] Goal visual illegal: " +
                label +
                ". local=(" +
                local.x.ToString("0.##") +
                "," +
                local.y.ToString("0.##") +
                ") side=" +
                (IsHomeTeam(teamSide) ? "home" : "away") +
                " expectedGoalLine=" +
                GetGoalLineCoordinate(teamSide).ToString("0.##"));
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

        public Vector3 GetGoalVisualCenter(int teamSide, float infieldInset, float lateralOffset = 0f)
        {
            if (pitchSpace == null)
            {
                return Vector3.zero;
            }

            var inwardDirection = IsHomeTeam(teamSide) ? homeToAwayAxis : -homeToAwayAxis;
            var target =
                GetGoalCenter(teamSide) +
                inwardDirection * Mathf.Max(0f, infieldInset) +
                lateralAxis * lateralOffset;
            target.y = pitchSpace.GrassY;
            return ClampToPlayableGrass(target, 0.18f);
        }

        public Vector3 GetDefaultGoalkeeperHome(int teamSide, float y)
        {
            if (pitchSpace == null)
            {
                return new Vector3(0f, y, 0f);
            }

            var inwardDirection = IsHomeTeam(teamSide) ? homeToAwayAxis : -homeToAwayAxis;
            var homeTarget =
                GetGoalCenter(teamSide) +
                inwardDirection * Mathf.Clamp(GetSixYardDepth() * 0.36f, 1.25f, 2.1f);
            homeTarget.y = y;
            return ClampGoalkeeperHome(homeTarget, teamSide);
        }

        public Vector3 GetKeeperBallAngleTarget(Vector3 ballPos, Vector3 keeperCurrentPos, int teamSide)
        {
            if (pitchSpace == null)
            {
                return keeperCurrentPos;
            }

            var goalCenter = GetGoalCenter(teamSide);
            var inwardDirection = IsHomeTeam(teamSide) ? homeToAwayAxis : -homeToAwayAxis;
            var ballLocal = ToPitchLocal(ballPos);
            var signedBallX = IsHomeTeam(teamSide) ? ballLocal.x : -ballLocal.x;
            var danger = Mathf.InverseLerp(0f, pitchSpace.HalfLength, signedBallX);
            var depthFromGoalLine = Mathf.Lerp(2f, Mathf.Min(GetGoalkeeperHomeDepth() - 1f, 7.5f), danger);
            var lateral = Mathf.Clamp(ballLocal.y * 0.28f, -GetSixYardHalfWidth(), GetSixYardHalfWidth());
            var target =
                goalCenter +
                inwardDirection * depthFromGoalLine +
                lateralAxis * lateral;
            target.y = keeperCurrentPos.y;
            return ClampGoalkeeperHome(target, teamSide);
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
                    Mathf.Min(pitchSpace.HalfLength * 0.11f, pitchSpace.HalfWidth * 0.18f),
                    4.4f,
                    8.4f);
            return ClampToPlayableGrass(target, cameraMargin);
        }

        public float GetInteriorFreedom01(Vector3 worldPos, float safetyMargin)
        {
            if (pitchSpace == null)
            {
                return 1f;
            }

            var margin = Mathf.Max(0.1f, safetyMargin);
            var clamped = ClampToPlayableGrass(worldPos, 0f);
            var local = ToPitchLocal(clamped);
            var distanceToLengthEdge = Mathf.Max(0f, pitchSpace.HalfLength - Mathf.Abs(local.x));
            var distanceToWidthEdge = Mathf.Max(0f, pitchSpace.HalfWidth - Mathf.Abs(local.y));
            var minDistanceToEdge = Mathf.Min(distanceToLengthEdge, distanceToWidthEdge);
            return Mathf.Clamp01(minDistanceToEdge / margin);
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
