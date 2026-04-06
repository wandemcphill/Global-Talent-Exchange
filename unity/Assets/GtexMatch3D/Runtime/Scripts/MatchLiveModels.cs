using System;

namespace Gtex.Match3D.Runtime
{
    [Serializable]
    public sealed class MatchResponse
    {
        public string matchId;
        public string source;
        public string status;
        public string frameId;
        public float clockMinute;
        public string phase;
        public int homeScore;
        public int awayScore;
        public string possessionSide;
        public string activeEventId;
        public string cameraPreset;
        public float pitchLengthMeters = 105f;
        public float pitchWidthMeters = 68f;
        public PlayerPosition[] players = Array.Empty<PlayerPosition>();
        public PlayerPosition ballPosition;
        public Event[] events = Array.Empty<Event>();

        public void Normalize()
        {
            if (players == null)
            {
                players = Array.Empty<PlayerPosition>();
            }

            if (events == null)
            {
                events = Array.Empty<Event>();
            }
        }

        public Event ResolveActiveEvent()
        {
            Normalize();

            if (!string.IsNullOrWhiteSpace(activeEventId))
            {
                for (int index = 0; index < events.Length; index += 1)
                {
                    Event candidate = events[index];
                    if (candidate != null &&
                        string.Equals(candidate.id, activeEventId, StringComparison.Ordinal))
                    {
                        return candidate;
                    }
                }
            }

            return events.Length > 0 ? events[events.Length - 1] : null;
        }
    }

    [Serializable]
    public sealed class Event
    {
        public string id;
        public string type;
        public int sequence;
        public int minute;
        public int addedTime;
        public string clockLabel;
        public float timeSeconds;
        public string teamId;
        public string teamName;
        public string primaryPlayerId;
        public string primaryPlayerName;
        public string secondaryPlayerId;
        public string secondaryPlayerName;
        public int homeScore;
        public int awayScore;
        public string bannerText;
        public string commentary;
        public int emphasisLevel;
        public string[] highlightedPlayerIds = Array.Empty<string>();
        public string[] flags = Array.Empty<string>();
        public string playbackProfile;
        public string missVariant;
        public bool reviewable;
        public string reviewReason;
        public string reviewDecision;
        public string scoreCommit;
    }

    [Serializable]
    public sealed class PlayerPosition
    {
        public string entityId;
        public string playerId;
        public string teamId;
        public string teamSide;
        public string label;
        public string role;
        public string line;
        public int shirtNumber;
        public bool active = true;
        public bool highlighted;
        public bool hasPossession;
        public string animationState;
        public float speedRatio;
        public string state;
        public float x;
        public float y;
        public float z;
        public float velocityX;
        public float velocityY;
        public float velocityZ;
        public float facingX;
        public float facingZ = 1f;
        public float spin;
        public string trajectoryType;
        public bool isBall;
    }
}
