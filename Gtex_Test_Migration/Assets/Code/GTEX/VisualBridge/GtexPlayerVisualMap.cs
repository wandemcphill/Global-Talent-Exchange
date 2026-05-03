using System;
using System.Collections.Generic;
using System.Linq;
using FStudio.GTEX;
using FStudio.MatchEngine;
using FStudio.MatchEngine.Players;
using UnityEngine;

namespace FStudio.GTEX.VisualBridge
{
    public sealed class GtexPlayerVisualMap : MonoBehaviour
    {
        private readonly Dictionary<string, GtexOriginalPlayerVisualProxy> playersByGtexId =
            new Dictionary<string, GtexOriginalPlayerVisualProxy>(StringComparer.OrdinalIgnoreCase);

        public int Count => playersByGtexId.Count;

        public IEnumerable<GtexOriginalPlayerVisualProxy> Proxies => playersByGtexId.Values.Distinct();

        public void Clear()
        {
            playersByGtexId.Clear();
            GtexVisualAuthority.ClearPlayerBindings();
        }

        public void RegisterPlayer(string gtexPlayerId, GtexOriginalPlayerVisualProxy proxy)
        {
            var key = NormalizePlayerUid(gtexPlayerId);
            if (string.IsNullOrWhiteSpace(key) || proxy == null)
            {
                return;
            }

            if (playersByGtexId.TryGetValue(key, out var existing) && existing != null && existing != proxy)
            {
                return;
            }

            playersByGtexId[key] = proxy;
        }

        public void RebuildFromCurrentMatch(MatchResponse state = null)
        {
            Clear();
            var manager = MatchManager.Current;
            if (manager == null)
            {
                return;
            }

            RegisterTeam(manager.GameTeam1, "home", state);
            RegisterTeam(manager.GameTeam2, "away", state);
        }

        public bool TryGetProxy(string gtexPlayerId, out GtexOriginalPlayerVisualProxy proxy)
        {
            return playersByGtexId.TryGetValue(NormalizePlayerUid(gtexPlayerId), out proxy) && proxy != null;
        }

        public bool TryGetCommandProxy(string playerUid, out GtexOriginalPlayerVisualProxy proxy, out string reason)
        {
            proxy = null;
            var normalized = NormalizePlayerUid(playerUid);
            if (string.IsNullOrWhiteSpace(normalized))
            {
                reason = "PlayerUid missing";
                return false;
            }

            if (IsNumericOnlyPlayerUid(normalized))
            {
                reason = "numeric-only ids are not authoritative command ids";
                return false;
            }

            if (!IsSideQualifiedPlayerUid(normalized))
            {
                reason = "side-qualified PlayerUid required";
                return false;
            }

            if (!playersByGtexId.TryGetValue(normalized, out proxy) || proxy == null || proxy.Player == null)
            {
                reason = "unknown PlayerUid";
                proxy = null;
                return false;
            }

            reason = null;
            return true;
        }

        public GtexOriginalPlayerVisualProxy ResolveProxy(string gtexPlayerId)
        {
            return TryGetProxy(gtexPlayerId, out var proxy) ? proxy : null;
        }

        public bool TryGetProxy(PlayerBase player, out GtexOriginalPlayerVisualProxy proxy)
        {
            proxy = playersByGtexId.Values.FirstOrDefault(candidate => candidate != null && candidate.Player == player);
            return proxy != null;
        }

        public bool TryGetPlayer(string gtexPlayerId, out PlayerBase player)
        {
            player = null;
            if (!TryGetProxy(gtexPlayerId, out var proxy) || proxy.Player == null)
            {
                return false;
            }

            player = proxy.Player;
            return true;
        }

        public GtexOriginalPlayerVisualProxy FindGoalkeeper(string teamId)
        {
            var normalizedTeam = NormalizePlayerUid(teamId);
            var manager = MatchManager.Current;
            foreach (var entry in playersByGtexId.Values)
            {
                if (entry == null || entry.Player == null || !entry.Player.IsGK)
                {
                    continue;
                }

                var team = entry.Player.GameTeam;
                if (team == null)
                {
                    continue;
                }

                if (string.Equals(normalizedTeam, "home", StringComparison.OrdinalIgnoreCase) &&
                    manager != null &&
                    team == manager.GameTeam1)
                {
                    return entry;
                }

                if (string.Equals(normalizedTeam, "away", StringComparison.OrdinalIgnoreCase) &&
                    manager != null &&
                    team == manager.GameTeam2)
                {
                    return entry;
                }

                if (string.IsNullOrWhiteSpace(normalizedTeam) ||
                    NormalizePlayerUid(team.TeamId.ToString()) == normalizedTeam ||
                    (team.TeamId == 0 && normalizedTeam == "home") ||
                    (team.TeamId == 1 && normalizedTeam == "away"))
                {
                    return entry;
                }
            }

            return null;
        }

        public GtexOriginalPlayerVisualProxy FindGoalkeeper(GameTeam targetTeam)
        {
            if (targetTeam == null)
            {
                return FindGoalkeeper(string.Empty);
            }

            foreach (var entry in playersByGtexId.Values)
            {
                if (entry != null &&
                    entry.Player != null &&
                    entry.Player.IsGK &&
                    entry.Player.GameTeam == targetTeam)
                {
                    return entry;
                }
            }

            return null;
        }

        private void RegisterTeam(GameTeam team, string teamSide, MatchResponse state)
        {
            if (team == null || team.GamePlayers == null)
            {
                return;
            }

            for (var index = 0; index < team.GamePlayers.Length; index += 1)
            {
                var player = team.GamePlayers[index];
                if (player == null || player.PlayerController == null || player.PlayerController.UnityObject == null)
                {
                    continue;
                }

                var proxy = player.PlayerController.UnityObject.GetComponent<GtexOriginalPlayerVisualProxy>();
                if (proxy == null)
                {
                    proxy = player.PlayerController.UnityObject.AddComponent<GtexOriginalPlayerVisualProxy>();
                }

                var primaryId = ResolvePrimaryId(player, teamSide, index, state);
                proxy.Initialize(primaryId, player);
                RegisterPlayer(primaryId, proxy);

                foreach (var alias in ResolveAliases(player, team, teamSide, index, state))
                {
                    RegisterPlayer(alias, proxy);
                }
            }
        }

        private static string ResolvePrimaryId(PlayerBase player, string teamSide, int index, MatchResponse state)
        {
            var statePlayer = ResolveStatePlayer(player, teamSide, state);
            if (statePlayer != null)
            {
                if (IsSideQualifiedPlayerUid(statePlayer.playerId))
                {
                    return NormalizePlayerUid(statePlayer.playerId);
                }

                if (statePlayer.shirtNumber > 0)
                {
                    return ComposePlayerUid(teamSide, statePlayer.shirtNumber);
                }
            }

            if (player.MatchPlayer != null && player.MatchPlayer.Number > 0)
            {
                return ComposePlayerUid(teamSide, player.MatchPlayer.Number);
            }

            if (player.MatchPlayer != null && player.MatchPlayer.Player != null && player.MatchPlayer.Player.id != 0)
            {
                return ComposePlayerUid(teamSide, player.MatchPlayer.Player.id);
            }

            return ComposePlayerUid(teamSide, index + 1);
        }

        private static IEnumerable<string> ResolveAliases(PlayerBase player, GameTeam team, string teamSide, int index, MatchResponse state)
        {
            var statePlayer = ResolveStatePlayer(player, teamSide, state);
            if (statePlayer != null)
            {
                yield return statePlayer.playerId;
                yield return statePlayer.entityId;
                yield return statePlayer.teamSide + "-" + statePlayer.shirtNumber;
                yield return statePlayer.teamId + "-" + statePlayer.shirtNumber;
            }

            if (player.MatchPlayer != null)
            {
                yield return player.MatchPlayer.Number.ToString();
                yield return teamSide + "-" + player.MatchPlayer.Number;

                if (player.MatchPlayer.Player != null)
                {
                    yield return player.MatchPlayer.Player.id.ToString();
                    yield return player.MatchPlayer.Player.Name;
                }
            }

            if (team != null)
            {
                yield return team.TeamId.ToString() + "-" + (index + 1);
                yield return teamSide + "-" + (index + 1);
                yield return teamSide + "_" + index;
            }
        }

        private static PlayerPosition ResolveStatePlayer(PlayerBase player, string teamSide, MatchResponse state)
        {
            if (player == null || state == null || state.players == null)
            {
                return null;
            }

            var number = player.MatchPlayer != null ? player.MatchPlayer.Number : -1;
            var playerId = player.MatchPlayer != null && player.MatchPlayer.Player != null
                ? player.MatchPlayer.Player.id.ToString()
                : string.Empty;

            return state.players.FirstOrDefault(candidate =>
                candidate != null &&
                !candidate.isBall &&
                (string.IsNullOrWhiteSpace(teamSide) ||
                 string.Equals(candidate.teamSide, teamSide, StringComparison.OrdinalIgnoreCase)) &&
                ((number > 0 && candidate.shirtNumber == number) ||
                 (!string.IsNullOrWhiteSpace(playerId) &&
                  string.Equals(candidate.playerId, playerId, StringComparison.OrdinalIgnoreCase))));
        }

        public static string NormalizePlayerUid(string value)
        {
            return string.IsNullOrWhiteSpace(value) ? string.Empty : value.Trim().ToLowerInvariant();
        }

        public static bool IsSideQualifiedPlayerUid(string value)
        {
            var normalized = NormalizePlayerUid(value);
            return normalized.StartsWith("home-", StringComparison.OrdinalIgnoreCase) ||
                   normalized.StartsWith("away-", StringComparison.OrdinalIgnoreCase);
        }

        public static bool IsNumericOnlyPlayerUid(string value)
        {
            var normalized = NormalizePlayerUid(value);
            if (normalized.Length == 0)
            {
                return false;
            }

            return normalized.All(char.IsDigit);
        }

        public static string ResolveTeamSide(string playerUid)
        {
            var normalized = NormalizePlayerUid(playerUid);
            if (normalized.StartsWith("home-", StringComparison.OrdinalIgnoreCase))
            {
                return "home";
            }

            if (normalized.StartsWith("away-", StringComparison.OrdinalIgnoreCase))
            {
                return "away";
            }

            return string.Empty;
        }

        private static string ComposePlayerUid(string teamSide, int slotOrShirt)
        {
            var side = NormalizePlayerUid(teamSide);
            if (side != "home" && side != "away")
            {
                side = "home";
            }

            return side + "-" + Mathf.Max(1, slotOrShirt);
        }
    }
}
