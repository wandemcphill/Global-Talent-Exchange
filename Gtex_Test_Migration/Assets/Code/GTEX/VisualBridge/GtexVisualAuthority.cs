using System;
using System.Collections.Generic;
using System.Linq;
using FStudio.MatchEngine.Players;
using FStudio.MatchEngine.Balls;
using UnityEngine;

namespace FStudio.GTEX.VisualBridge
{
    public enum MatchAuthority
    {
        UnityFreePlay,
        GtexControlledSequence
    }

    public sealed class AuthorityLease
    {
        public bool IsActive;
        public float ExpiryTime;
        public string OwningTeamId = string.Empty;
        public readonly HashSet<string> ControlledPlayerUids = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
    }

    public static class GtexVisualAuthority
    {
        private static readonly AuthorityLease currentLease = new AuthorityLease();
        private static readonly Dictionary<PlayerBase, string> playerUidsByPlayer = new Dictionary<PlayerBase, string>();
        private static readonly HashSet<string> ballInteractionPlayerUids = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        private static bool ballInteractionRestricted;

        public static MatchAuthority CurrentAuthority =>
            currentLease.IsActive ? MatchAuthority.GtexControlledSequence : MatchAuthority.UnityFreePlay;

        public static bool IsLeaseActive
        {
            get
            {
                Tick();
                return currentLease.IsActive;
            }
        }

        public static bool RequestAuthorityLease(
            string teamId,
            IEnumerable<string> playerUids,
            float durationSeconds,
            GtexPlayerVisualMap playerMap,
            bool allowCrossTeam = false)
        {
            Tick();

            var normalizedTeam = NormalizeTeamId(teamId);
            if (string.IsNullOrWhiteSpace(normalizedTeam))
            {
                Debug.LogWarning("[GTEX Authority] Lease rejected: teamId must be home or away.");
                return false;
            }

            if (playerMap == null)
            {
                Debug.LogWarning("[GTEX Authority] Lease rejected: player map missing.");
                return false;
            }

            var validUids = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var uid in playerUids ?? Enumerable.Empty<string>())
            {
                var normalizedUid = GtexPlayerVisualMap.NormalizePlayerUid(uid);
                if (!GtexPlayerVisualMap.IsSideQualifiedPlayerUid(normalizedUid))
                {
                    Debug.LogWarning("[GTEX Authority] Lease rejected player id '" + uid + "': side-qualified PlayerUid required.");
                    return false;
                }

                if (!playerMap.TryGetCommandProxy(normalizedUid, out _, out var reason))
                {
                    Debug.LogWarning("[GTEX Authority] Lease rejected player id '" + uid + "': " + reason);
                    return false;
                }

                var playerTeam = GtexPlayerVisualMap.ResolveTeamSide(normalizedUid);
                if (!allowCrossTeam && !string.Equals(playerTeam, normalizedTeam, StringComparison.OrdinalIgnoreCase))
                {
                    Debug.LogError("[GTEX Authority] Lease rejected cross-team player " + normalizedUid + " for team=" + normalizedTeam + ".");
                    return false;
                }

                validUids.Add(normalizedUid);
            }

            if (validUids.Count == 0)
            {
                Debug.LogWarning("[GTEX Authority] Lease rejected: no valid controlled players.");
                return false;
            }

            currentLease.IsActive = true;
            currentLease.OwningTeamId = normalizedTeam;
            currentLease.ExpiryTime = Time.time + Mathf.Clamp(durationSeconds, 2f, 6f);
            currentLease.ControlledPlayerUids.Clear();
            foreach (var uid in validUids)
            {
                currentLease.ControlledPlayerUids.Add(uid);
            }

            foreach (var uid in currentLease.ControlledPlayerUids)
            {
                Debug.Log("[GTEX LOCK] Player locked: " + uid);
            }

            ballInteractionPlayerUids.Clear();
            AllowCurrentHolderInteraction();
            ballInteractionRestricted = true;
            Debug.Log("[GTEX LOCK] Ball interaction restricted");

            Debug.Log(
                "[GTEX Authority] Lease acquired team=" + normalizedTeam +
                " players=" + string.Join(",", currentLease.ControlledPlayerUids) +
                " duration=" + Mathf.Clamp(durationSeconds, 2f, 6f).ToString("0.0"));
            return true;
        }

        public static bool RefreshAuthorityLease(
            string teamId,
            IEnumerable<string> playerUids,
            float durationSeconds,
            GtexPlayerVisualMap playerMap,
            bool allowCrossTeam = false)
        {
            Tick();
            if (!currentLease.IsActive)
            {
                return RequestAuthorityLease(teamId, playerUids, durationSeconds, playerMap, allowCrossTeam);
            }

            var normalizedTeam = NormalizeTeamId(teamId);
            if (string.IsNullOrWhiteSpace(normalizedTeam))
            {
                Debug.LogWarning("[GTEX Authority] Lease refresh rejected: teamId must be home or away.");
                return false;
            }

            if (!string.Equals(currentLease.OwningTeamId, normalizedTeam, StringComparison.OrdinalIgnoreCase))
            {
                Debug.LogWarning("[GTEX Authority] Lease refresh rejected: active lease team=" + currentLease.OwningTeamId + " requested=" + normalizedTeam + ".");
                return false;
            }

            if (playerMap == null)
            {
                Debug.LogWarning("[GTEX Authority] Lease refresh rejected: player map missing.");
                return false;
            }

            var validUids = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var uid in playerUids ?? Enumerable.Empty<string>())
            {
                var normalizedUid = GtexPlayerVisualMap.NormalizePlayerUid(uid);
                if (!GtexPlayerVisualMap.IsSideQualifiedPlayerUid(normalizedUid))
                {
                    Debug.LogWarning("[GTEX Authority] Lease refresh rejected player id '" + uid + "': side-qualified PlayerUid required.");
                    return false;
                }

                if (!playerMap.TryGetCommandProxy(normalizedUid, out _, out var reason))
                {
                    Debug.LogWarning("[GTEX Authority] Lease refresh rejected player id '" + uid + "': " + reason);
                    return false;
                }

                var playerTeam = GtexPlayerVisualMap.ResolveTeamSide(normalizedUid);
                if (!allowCrossTeam && !string.Equals(playerTeam, normalizedTeam, StringComparison.OrdinalIgnoreCase))
                {
                    Debug.LogError("[GTEX Authority] Lease refresh rejected cross-team player " + normalizedUid + " for team=" + normalizedTeam + ".");
                    return false;
                }

                validUids.Add(normalizedUid);
            }

            if (validUids.Count != currentLease.ControlledPlayerUids.Count ||
                validUids.Any(uid => !currentLease.ControlledPlayerUids.Contains(uid)))
            {
                Debug.LogWarning("[GTEX Authority] Lease refresh rejected: controlled players changed.");
                return false;
            }

            currentLease.ExpiryTime = Time.time + Mathf.Clamp(durationSeconds, 2f, 6f);
            ballInteractionRestricted = true;
            AllowCurrentHolderInteraction();
            return true;
        }

        public static void ReleaseAuthority(string reason)
        {
            if (!currentLease.IsActive)
            {
                return;
            }

            var resolvedReason = string.IsNullOrWhiteSpace(reason) ? "released" : reason.Trim();
            currentLease.IsActive = false;
            currentLease.ExpiryTime = 0f;
            currentLease.OwningTeamId = string.Empty;
            currentLease.ControlledPlayerUids.Clear();
            if (ballInteractionRestricted)
            {
                Debug.Log("[GTEX LOCK] Sequence integrity maintained");
            }

            ballInteractionPlayerUids.Clear();
            ballInteractionRestricted = false;
            Debug.Log("[GTEX Authority] Lease released reason=" + resolvedReason);
        }

        public static void Tick()
        {
            if (currentLease.IsActive && Time.time >= currentLease.ExpiryTime)
            {
                ReleaseAuthority("expired");
            }
        }

        public static bool IsPlayerControlled(string playerUid)
        {
            Tick();
            return currentLease.IsActive &&
                   currentLease.ControlledPlayerUids.Contains(GtexPlayerVisualMap.NormalizePlayerUid(playerUid));
        }

        public static bool ShouldSuppressAutonomousDecision(PlayerBase player)
        {
            Tick();
            if (!currentLease.IsActive || player == null)
            {
                return false;
            }

            return playerUidsByPlayer.TryGetValue(player, out var playerUid) &&
                   currentLease.ControlledPlayerUids.Contains(playerUid);
        }

        public static void AllowCommandBallParticipants(GtexVisualCommand command)
        {
            Tick();
            if (!currentLease.IsActive || command == null)
            {
                return;
            }

            ballInteractionRestricted = true;
            ballInteractionPlayerUids.Clear();
            AllowCurrentHolderInteraction();

            switch (command.type)
            {
                case GtexVisualCommandType.AssignPossession:
                case GtexVisualCommandType.CarryBall:
                case GtexVisualCommandType.Shoot:
                case GtexVisualCommandType.KeeperSave:
                case GtexVisualCommandType.KeeperClaim:
                case GtexVisualCommandType.Goal:
                    AllowBallInteraction(command.actorPlayerId);
                    AllowBallInteraction(command.secondaryTargetPlayerId);
                    break;
                case GtexVisualCommandType.Pass:
                case GtexVisualCommandType.ThroughPass:
                case GtexVisualCommandType.Cross:
                    AllowBallInteraction(command.actorPlayerId);
                    AllowBallInteraction(command.targetPlayerId);
                    AllowBallInteraction(command.secondaryTargetPlayerId);
                    break;
            }
        }

        public static bool ShouldBlockBallInteraction(PlayerBase player)
        {
            Tick();
            if (!currentLease.IsActive || !ballInteractionRestricted || player == null)
            {
                return false;
            }

            return !TryResolvePlayerUid(player, out var playerUid) ||
                   !ballInteractionPlayerUids.Contains(playerUid);
        }

        public static bool ShouldSuppressNonControlledAggression(PlayerBase player)
        {
            Tick();
            if (!currentLease.IsActive || player == null)
            {
                return false;
            }

            if (!TryResolvePlayerUid(player, out var playerUid))
            {
                return true;
            }

            return !currentLease.ControlledPlayerUids.Contains(playerUid) &&
                   (!ballInteractionRestricted || !ballInteractionPlayerUids.Contains(playerUid));
        }

        public static bool ShouldProtectControlledPossession(PlayerBase holder, PlayerBase challenger)
        {
            Tick();
            if (!currentLease.IsActive || holder == null || challenger == null)
            {
                return false;
            }

            return !ShouldBlockBallInteraction(holder) && ShouldBlockBallInteraction(challenger);
        }

        public static bool IsPassiveCommand(GtexVisualCommandType type)
        {
            return type == GtexVisualCommandType.HoldShape ||
                   type == GtexVisualCommandType.CoverSpace;
        }

        public static void RegisterPlayer(PlayerBase player, string playerUid)
        {
            if (player == null || !GtexPlayerVisualMap.IsSideQualifiedPlayerUid(playerUid))
            {
                return;
            }

            playerUidsByPlayer[player] = GtexPlayerVisualMap.NormalizePlayerUid(playerUid);
        }

        public static void ClearPlayerBindings()
        {
            playerUidsByPlayer.Clear();
            ballInteractionPlayerUids.Clear();
            ballInteractionRestricted = false;
        }

        private static bool TryResolvePlayerUid(PlayerBase player, out string playerUid)
        {
            if (playerUidsByPlayer.TryGetValue(player, out playerUid))
            {
                playerUid = GtexPlayerVisualMap.NormalizePlayerUid(playerUid);
                return GtexPlayerVisualMap.IsSideQualifiedPlayerUid(playerUid);
            }

            playerUid = string.Empty;
            return false;
        }

        private static void AllowBallInteraction(string playerUid)
        {
            var normalizedUid = GtexPlayerVisualMap.NormalizePlayerUid(playerUid);
            if (!GtexPlayerVisualMap.IsSideQualifiedPlayerUid(normalizedUid))
            {
                return;
            }

            ballInteractionPlayerUids.Add(normalizedUid);
        }

        private static void AllowCurrentHolderInteraction()
        {
            if (Ball.Current == null || Ball.Current.HolderPlayer == null)
            {
                return;
            }

            if (TryResolvePlayerUid(Ball.Current.HolderPlayer, out var holderUid))
            {
                ballInteractionPlayerUids.Add(holderUid);
            }
        }

        private static string NormalizeTeamId(string teamId)
        {
            var normalized = (teamId ?? string.Empty).Trim().ToLowerInvariant();
            return normalized == "home" || normalized == "away" ? normalized : string.Empty;
        }
    }
}
