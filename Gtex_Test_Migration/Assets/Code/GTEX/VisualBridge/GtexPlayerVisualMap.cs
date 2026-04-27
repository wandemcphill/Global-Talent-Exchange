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
        }

        public void RegisterPlayer(string gtexPlayerId, GtexOriginalPlayerVisualProxy proxy)
        {
            var key = NormalizeKey(gtexPlayerId);
            if (string.IsNullOrWhiteSpace(key) || proxy == null)
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
            return playersByGtexId.TryGetValue(NormalizeKey(gtexPlayerId), out proxy) && proxy != null;
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
            var normalizedTeam = NormalizeKey(teamId);
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

                if (string.IsNullOrWhiteSpace(normalizedTeam) ||
                    NormalizeKey(team.TeamId.ToString()) == normalizedTeam ||
                    (team.TeamId == 0 && normalizedTeam == "home") ||
                    (team.TeamId == 1 && normalizedTeam == "away"))
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

                foreach (var alias in ResolveAliases(player, team, teamSide, index, state))
                {
                    RegisterPlayer(alias, proxy);
                }
            }
        }

        private static string ResolvePrimaryId(PlayerBase player, string teamSide, int index, MatchResponse state)
        {
            var statePlayer = ResolveStatePlayer(player, teamSide, state);
            if (statePlayer != null && !string.IsNullOrWhiteSpace(statePlayer.playerId))
            {
                return statePlayer.playerId;
            }

            if (player.MatchPlayer != null && player.MatchPlayer.Player != null && player.MatchPlayer.Player.id != 0)
            {
                return player.MatchPlayer.Player.id.ToString();
            }

            return teamSide + "_" + index.ToString();
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

        private static string NormalizeKey(string value)
        {
            return string.IsNullOrWhiteSpace(value) ? string.Empty : value.Trim().ToLowerInvariant();
        }
    }
}
