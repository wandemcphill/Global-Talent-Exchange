using System;
using FStudio.GTEX;
using FStudio.GTEX.Playback;
using UnityEngine;

namespace FStudio.GTEX.Simulation
{
    [Serializable]
    public sealed class GtexSimSpatialState
    {
        public float ClockMinute;
        public string Phase = "kickoff";
        public int HomeScore;
        public int AwayScore;
        public string PossessionSide = "home";
        public string CameraPreset = "broadcast";
        public string ActiveEventId = string.Empty;
        public GtexSimSpatialPlayerState[] Players = Array.Empty<GtexSimSpatialPlayerState>();
        public GtexSimSpatialBallState Ball = new();
        public Event[] Events = Array.Empty<Event>();

        public MatchResponse ToMatchResponse(string matchId)
        {
            var matchResponse = new MatchResponse
            {
                matchId = matchId ?? string.Empty,
                source = "simulation",
                status = string.Equals(Phase, "fulltime", StringComparison.OrdinalIgnoreCase) ? "completed" : "live",
                frameId = BuildFrameId(),
                clockMinute = ClockMinute,
                phase = Phase ?? "kickoff",
                homeScore = HomeScore,
                awayScore = AwayScore,
                possessionSide = PossessionSide ?? string.Empty,
                activeEventId = ActiveEventId ?? string.Empty,
                cameraPreset = CameraPreset ?? "broadcast",
                pitchLengthMeters = GtexPitchSpace.DefaultLength,
                pitchWidthMeters = GtexPitchSpace.DefaultWidth,
                players = BuildPlayerPositions(),
                ballPosition = Ball != null ? Ball.ToPlayerPosition() : new PlayerPosition { entityId = "ball", isBall = true },
                events = Events ?? Array.Empty<Event>()
            };

            matchResponse.Normalize();
            return matchResponse;
        }

        private string BuildFrameId()
        {
            // Preserve sub-100ms simulation frames. The previous 0.1-minute
            // rounding collapsed a continuous stream into identical frame IDs.
            return "sim-" + Mathf.RoundToInt(ClockMinute * 60000f);
        }

        private PlayerPosition[] BuildPlayerPositions()
        {
            if (Players == null || Players.Length == 0)
            {
                return Array.Empty<PlayerPosition>();
            }

            var positions = new PlayerPosition[Players.Length];
            for (var index = 0; index < Players.Length; index += 1)
            {
                var player = Players[index];
                positions[index] = player != null ? player.ToPlayerPosition() : null;
            }

            return positions;
        }
    }

    [Serializable]
    public sealed class GtexSimSpatialPlayerState
    {
        public string EntityId = string.Empty;
        public string PlayerId = string.Empty;
        public string TeamSide = string.Empty;
        public string Label = string.Empty;
        public string Role = string.Empty;
        public string Line = string.Empty;
        public int ShirtNumber;
        public bool HasPossession;
        public string AnimationState = "idle";
        public float SpeedRatio;
        public Vector3 Position;
        public Vector3 Velocity;
        public Vector3 Facing = Vector3.forward;

        public PlayerPosition ToPlayerPosition()
        {
            var facing = Facing;
            if (facing.sqrMagnitude <= 0.0001f)
            {
                facing = Vector3.forward;
            }

            return new PlayerPosition
            {
                entityId = EntityId,
                playerId = PlayerId,
                teamSide = TeamSide,
                label = Label,
                role = Role,
                line = Line,
                shirtNumber = ShirtNumber,
                hasPossession = HasPossession,
                animationState = AnimationState,
                speedRatio = SpeedRatio,
                x = Position.x,
                y = Position.y,
                z = Position.z,
                velocityX = Velocity.x,
                velocityY = Velocity.y,
                velocityZ = Velocity.z,
                facingX = facing.x,
                facingZ = facing.z
            };
        }
    }

    [Serializable]
    public sealed class GtexSimSpatialBallState
    {
        public Vector3 Position;
        public Vector3 Velocity;
        public string HolderPlayerId = string.Empty;
        public string TrajectoryType = string.Empty;

        public PlayerPosition ToPlayerPosition()
        {
            return new PlayerPosition
            {
                entityId = "ball",
                playerId = HolderPlayerId,
                label = "Ball",
                isBall = true,
                x = Position.x,
                y = Position.y,
                z = Position.z,
                velocityX = Velocity.x,
                velocityY = Velocity.y,
                velocityZ = Velocity.z,
                trajectoryType = TrajectoryType
            };
        }
    }
}
