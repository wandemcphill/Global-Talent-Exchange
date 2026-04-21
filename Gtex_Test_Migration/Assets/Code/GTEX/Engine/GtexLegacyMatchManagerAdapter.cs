using System;
using System.Collections.Generic;
using System.Linq;
using FStudio.GTEX;
using FStudio.MatchEngine;
using FStudio.MatchEngine.Enums;
using UnityEngine;

namespace FStudio.GTEX.Engine
{
    public sealed class GtexLegacyMatchManagerAdapter
    {
        public bool IsAvailable => MatchManager.Current != null;

        public bool HasTeams =>
            MatchManager.Current != null &&
            MatchManager.Current.GameTeam1 != null &&
            MatchManager.Current.GameTeam2 != null;

        public bool ExternalPlaybackEnabled =>
            MatchManager.Current != null && MatchManager.Current.ExternalPlaybackEnabled;

        public Vector2 FieldSize =>
            MatchManager.Current != null ? MatchManager.Current.SizeOfField : Vector2.zero;

        public float CurrentMatchMinute =>
            MatchManager.Current != null ? MatchManager.Current.minutes : 0f;

        public int HomeScore =>
            MatchManager.Current != null ? MatchManager.Current.homeTeamScore : 0;

        public int AwayScore =>
            MatchManager.Current != null ? MatchManager.Current.awayTeamScore : 0;

        public MatchStatus MatchFlags =>
            MatchManager.Current != null ? MatchManager.Current.MatchFlags : default;

        public void SetExternalPlayback(bool value)
        {
            if (MatchManager.Current == null)
            {
                return;
            }

            MatchManager.Current.SetExternalPlayback(value);
        }

        public void ApplyExternalLiveState(float clockMinute, int homeScore, int awayScore, MatchStatus matchStatus)
        {
            if (MatchManager.Current == null)
            {
                return;
            }

            MatchManager.Current.ApplyExternalLiveState(clockMinute, homeScore, awayScore, matchStatus);
        }

        public IReadOnlyList<GtexLegacyPlayerHandle> GetHomePlayers()
        {
            return WrapTeamPlayers(MatchManager.Current != null ? MatchManager.Current.GameTeam1 : null);
        }

        public IReadOnlyList<GtexLegacyPlayerHandle> GetAwayPlayers()
        {
            return WrapTeamPlayers(MatchManager.Current != null ? MatchManager.Current.GameTeam2 : null);
        }

        public Vector3 ResolveFieldPosition(PlayerPosition livePosition, MatchResponse state)
        {
            if (livePosition == null || MatchManager.Current == null)
            {
                return Vector3.zero;
            }

            var fieldSize = MatchManager.Current.SizeOfField;
            var pitchLength = ResolvePitchLength(state);
            var pitchWidth = ResolvePitchWidth(state);
            var normalizedX = Mathf.InverseLerp(-pitchLength * 0.5f, pitchLength * 0.5f, livePosition.x);
            var normalizedZ = Mathf.InverseLerp(-pitchWidth * 0.5f, pitchWidth * 0.5f, livePosition.z);

            return new Vector3(
                normalizedX * fieldSize.x,
                livePosition.isBall ? Mathf.Max(0.1f, livePosition.y) : 0f,
                normalizedZ * fieldSize.y);
        }

        public Vector3 ResolveFieldVelocity(PlayerPosition livePosition, MatchResponse state)
        {
            if (livePosition == null || MatchManager.Current == null)
            {
                return Vector3.zero;
            }

            var fieldSize = MatchManager.Current.SizeOfField;
            var pitchLength = ResolvePitchLength(state);
            var pitchWidth = ResolvePitchWidth(state);

            return new Vector3(
                (livePosition.velocityX / pitchLength) * fieldSize.x,
                livePosition.velocityY,
                (livePosition.velocityZ / pitchWidth) * fieldSize.y);
        }

        private static IReadOnlyList<GtexLegacyPlayerHandle> WrapTeamPlayers(GameTeam team)
        {
            if (team == null || team.GamePlayers == null || team.GamePlayers.Length == 0)
            {
                return Array.Empty<GtexLegacyPlayerHandle>();
            }

            return team.GamePlayers
                .Where(player => player != null)
                .Select(player => new GtexLegacyPlayerHandle(player))
                .ToArray();
        }

        private static float ResolvePitchLength(MatchResponse state)
        {
            return state != null ? Mathf.Max(1f, state.pitchLengthMeters) : 105f;
        }

        private static float ResolvePitchWidth(MatchResponse state)
        {
            return state != null ? Mathf.Max(1f, state.pitchWidthMeters) : 68f;
        }
    }
}
