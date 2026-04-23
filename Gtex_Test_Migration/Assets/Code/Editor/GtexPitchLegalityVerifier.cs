#if UNITY_EDITOR
using System;
using System.Globalization;
using System.IO;
using System.Linq;
using FStudio.GTEX.Core;
using FStudio.GTEX.Playback;
using FStudio.MatchEngine;
using FStudio.MatchEngine.Balls;
using FStudio.MatchEngine.Players;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace FStudio.GTEX.Editor
{
    public static class GtexPitchLegalityVerifier
    {
        [Serializable]
        private sealed class FullSessionSummary
        {
            public string runtime_trace;
        }

        [MenuItem("Tools/GTEX/Simulation/Verify Pitch Legality")]
        public static void VerifyFromEditorMenu()
        {
            Verify();
        }

        public static void VerifyFromCommandLine()
        {
            Verify();
        }

        private static void Verify()
        {
            if (!TryFindPitchArtifacts(out var players, out var goals, out var ball) ||
                !HasCompletePitchArtifacts(players, goals, ball))
            {
                LoadDevelopmentSceneIfAvailable();
                BootstrapSceneArtifactsIfNeeded();
                if (!TryFindPitchArtifacts(out players, out goals, out ball) ||
                    !HasCompletePitchArtifacts(players, goals, ball))
                {
                    if (TryVerifyRuntimeArtifacts(out var runtimeSummary))
                    {
                        Debug.Log("[GTEX Pitch Verify] Success. " + runtimeSummary);
                        return;
                    }

                    throw new InvalidOperationException(
                        "Pitch legality verification could not find complete player/goal/ball artifacts in the active scene, " +
                        "and no runtime trace legality artifacts were available.");
                }
            }

            var pitchSpace = GtexPitchLocator.Resolve(out var sourceDescription);
            if (MatchManager.Current != null)
            {
                MatchManager.Current.ConfigureExternalPlaybackPitchSpace(pitchSpace);
            }

            ValidatePlayers(players, pitchSpace, sourceDescription);

            if (ball != null && pitchSpace.IsOutsideWorld(ball.transform.position))
            {
                throw new InvalidOperationException(
                    "Ball is outside pitch space. Position=" +
                    ball.transform.position +
                    ", source=" +
                    sourceDescription +
                    ".");
            }

            ValidateGoal(goals[0], pitchSpace.GetHomeGoalCenter(), "home");
            ValidateGoal(goals[goals.Length - 1], pitchSpace.GetAwayGoalCenter(), "away");

            Debug.Log(
                "[GTEX Pitch Verify] Success. Source=" +
                sourceDescription +
                ", players=" +
                players.Length +
                ", goals=" +
                goals.Length +
                ", ball=" +
                (ball != null) +
                ".");
        }

        private static bool HasCompletePitchArtifacts(PlayerBase[] players, GoalNet[] goals, Ball ball)
        {
            return players != null &&
                   players.Length > 0 &&
                   goals != null &&
                   goals.Length >= 2 &&
                   ball != null;
        }

        private static void ValidatePlayers(PlayerBase[] players, GtexPitchSpace pitchSpace, string sourceDescription)
        {
            for (var index = 0; index < players.Length; index += 1)
            {
                var player = players[index];
                if (pitchSpace.IsOutsideWorld(player.Position))
                {
                    throw new InvalidOperationException(
                        "Player '" +
                        DescribePlayer(player) +
                        "' is outside pitch space. Position=" +
                        player.Position +
                        ", source=" +
                        sourceDescription +
                        ".");
                }

                if (Mathf.Abs(player.Position.y - pitchSpace.GrassY) > 0.35f)
                {
                    throw new InvalidOperationException(
                        "Player '" +
                        DescribePlayer(player) +
                        "' is not anchored to grass height. Position=" +
                        player.Position +
                        ", grassY=" +
                        pitchSpace.GrassY.ToString("0.##") +
                        ".");
                }
            }
        }

        private static bool TryFindPitchArtifacts(out PlayerBase[] players, out GoalNet[] goals, out Ball ball)
        {
            players = ResolveRuntimePlayers();
            goals = UnityEngine.Object.FindObjectsByType<GoalNet>(FindObjectsSortMode.None)
                .Where(goal => goal != null)
                .OrderBy(goal => goal.GroundAnchorPosition.x)
                .ToArray();
            ball = Ball.Current != null ? Ball.Current : UnityEngine.Object.FindFirstObjectByType<Ball>();
            return players.Length > 0 || goals.Length > 0 || ball != null;
        }

        private static bool TryVerifyRuntimeArtifacts(out string summary)
        {
            summary = string.Empty;
            if (!TryResolveRuntimeTracePath(out var runtimeTracePath))
            {
                return false;
            }

            var lines = File.ReadAllLines(runtimeTracePath);
            if (!TryResolvePitchSpaceFromTrace(lines, out var pitchSpace, out var sourceDescription))
            {
                throw new InvalidOperationException(
                    "Runtime trace did not include a pitch-space resolution record: " + runtimeTracePath);
            }

            var playerSampleCount = 0;
            var playerSampleLines = lines.Where(line => line.Contains("| pitch-sample |")).ToArray();
            if (playerSampleLines.Length == 0)
            {
                throw new InvalidOperationException(
                    "Runtime trace did not include any sampled player pitch coordinates: " + runtimeTracePath);
            }

            foreach (var line in playerSampleLines)
            {
                if (!TryParseTraceVector(line, "clamped=", out var clampedPosition))
                {
                    continue;
                }

                ValidateTracePlayerPosition(clampedPosition, pitchSpace, sourceDescription);
                playerSampleCount += 1;
            }

            if (playerSampleCount == 0)
            {
                throw new InvalidOperationException(
                    "Runtime trace contained player pitch samples, but none could be parsed: " + runtimeTracePath);
            }

            var ballSampleCount = 0;
            var ballSampleLines = lines.Where(line => line.Contains("| ball-pitch-sample |")).ToArray();
            if (ballSampleLines.Length == 0)
            {
                throw new InvalidOperationException(
                    "Runtime trace did not include any sampled ball pitch coordinates: " + runtimeTracePath);
            }

            foreach (var line in ballSampleLines)
            {
                if (!TryParseTraceVector(line, "clamped=", out var clampedPosition))
                {
                    continue;
                }

                if (pitchSpace.IsOutsideWorld(clampedPosition))
                {
                    throw new InvalidOperationException(
                        "Sampled ball runtime trace position is outside pitch space. Position=" +
                        clampedPosition +
                        ", source=" +
                        sourceDescription +
                        ", trace=" +
                        runtimeTracePath +
                        ".");
                }

                ballSampleCount += 1;
            }

            if (ballSampleCount == 0)
            {
                throw new InvalidOperationException(
                    "Runtime trace contained ball pitch samples, but none could be parsed: " + runtimeTracePath);
            }

            var homeGoalValidated = false;
            var awayGoalValidated = false;
            var goalAnchorLines = lines.Where(line => line.Contains("| goal-anchor |")).ToArray();
            foreach (var line in goalAnchorLines)
            {
                if (!TryParseGoalAnchor(line, out var side, out var expectedGroundCenter, out var actualGroundCenter))
                {
                    continue;
                }

                ValidateGoal(actualGroundCenter, expectedGroundCenter, side);
                homeGoalValidated |= string.Equals(side, "home", StringComparison.OrdinalIgnoreCase);
                awayGoalValidated |= string.Equals(side, "away", StringComparison.OrdinalIgnoreCase);
            }

            if (!homeGoalValidated || !awayGoalValidated)
            {
                throw new InvalidOperationException(
                    "Runtime trace did not include both goal anchor diagnostics: " + runtimeTracePath);
            }

            summary =
                "Source=" +
                sourceDescription +
                ", runtimeTrace=" +
                runtimeTracePath +
                ", sampledPlayers=" +
                playerSampleCount +
                ", sampledBallFrames=" +
                ballSampleCount +
                ", goals=2.";
            return true;
        }

        private static bool TryResolveRuntimeTracePath(out string runtimeTracePath)
        {
            runtimeTracePath = string.Empty;

            var summaryPath = ResolveFullSessionSummaryPath();
            if (File.Exists(summaryPath))
            {
                var json = File.ReadAllText(summaryPath);
                var summary = JsonUtility.FromJson<FullSessionSummary>(json);
                if (summary != null &&
                    !string.IsNullOrWhiteSpace(summary.runtime_trace) &&
                    File.Exists(summary.runtime_trace))
                {
                    runtimeTracePath = summary.runtime_trace;
                    return true;
                }
            }

            var candidates = new[]
            {
                Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "tmp", "gtex_full_session_capture", "gtex_full_session_validation.runtime.log")),
                Path.GetFullPath(Path.Combine(Application.dataPath, "..", "Builds", "WindowsProduction", "tmp", "gtex_live_runtime_trace.log"))
            };

            for (var index = 0; index < candidates.Length; index += 1)
            {
                var candidate = candidates[index];
                if (File.Exists(candidate))
                {
                    runtimeTracePath = candidate;
                    return true;
                }
            }

            return false;
        }

        private static string ResolveFullSessionSummaryPath()
        {
            return Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "tmp", "gtex_full_session_summary.json"));
        }

        private static bool TryResolvePitchSpaceFromTrace(
            string[] lines,
            out GtexPitchSpace pitchSpace,
            out string sourceDescription)
        {
            pitchSpace = null;
            sourceDescription = string.Empty;
            if (lines == null)
            {
                return false;
            }

            for (var index = lines.Length - 1; index >= 0; index -= 1)
            {
                if (TryParseTracePitchSpace(lines[index], out pitchSpace, out sourceDescription))
                {
                    return true;
                }
            }

            return false;
        }

        private static bool TryParseTracePitchSpace(
            string line,
            out GtexPitchSpace pitchSpace,
            out string sourceDescription)
        {
            pitchSpace = null;
            sourceDescription = string.Empty;
            if (string.IsNullOrWhiteSpace(line) || !line.Contains("| pitch |"))
            {
                return false;
            }

            var sourceIndex = line.IndexOf("source=", StringComparison.Ordinal);
            var lengthIndex = line.IndexOf(" length=", StringComparison.Ordinal);
            if (sourceIndex < 0 || lengthIndex <= sourceIndex)
            {
                return false;
            }

            sourceDescription = line.Substring(sourceIndex + "source=".Length, lengthIndex - (sourceIndex + "source=".Length)).Trim();
            if (!TryParseTraceFloat(line, "length=", out var length) ||
                !TryParseTraceFloat(line, "width=", out var width) ||
                !TryParseTraceFloat(line, "grassY=", out var grassY) ||
                !TryParseTraceCenter(line, out var center))
            {
                return false;
            }

            pitchSpace = new GtexPitchSpace(length, width, grassY, center);
            return true;
        }

        private static void ValidateTracePlayerPosition(Vector3 position, GtexPitchSpace pitchSpace, string sourceDescription)
        {
            if (pitchSpace.IsOutsideWorld(position))
            {
                throw new InvalidOperationException(
                    "Sampled player runtime trace position is outside pitch space. Position=" +
                    position +
                    ", source=" +
                    sourceDescription +
                    ".");
            }

            if (Mathf.Abs(position.y - pitchSpace.GrassY) > 0.35f)
            {
                throw new InvalidOperationException(
                    "Sampled player runtime trace position is not anchored to grass height. Position=" +
                    position +
                    ", grassY=" +
                    pitchSpace.GrassY.ToString("0.##") +
                    ".");
            }
        }

        private static bool TryParseGoalAnchor(
            string line,
            out string side,
            out Vector3 expectedGroundCenter,
            out Vector3 actualGroundCenter)
        {
            side = string.Empty;
            expectedGroundCenter = Vector3.zero;
            actualGroundCenter = Vector3.zero;
            if (string.IsNullOrWhiteSpace(line) || !line.Contains("| goal-anchor |"))
            {
                return false;
            }

            side = TryReadTokenValue(line, "side=");
            return !string.IsNullOrWhiteSpace(side) &&
                   TryParseTraceVector(line, "expected=", out expectedGroundCenter) &&
                   TryParseTraceVector(line, "actual=", out actualGroundCenter);
        }

        private static bool TryParseTraceCenter(string line, out Vector3 center)
        {
            center = Vector3.zero;
            var token = "center=(";
            var start = line.IndexOf(token, StringComparison.Ordinal);
            if (start < 0)
            {
                return false;
            }

            start += token.Length;
            var end = line.IndexOf(')', start);
            if (end <= start)
            {
                return false;
            }

            var parts = line.Substring(start, end - start).Split(',');
            if (parts.Length < 2 ||
                !float.TryParse(parts[0], NumberStyles.Float, CultureInfo.InvariantCulture, out var x) ||
                !float.TryParse(parts[1], NumberStyles.Float, CultureInfo.InvariantCulture, out var z))
            {
                return false;
            }

            center = new Vector3(x, 0f, z);
            return true;
        }

        private static bool TryParseTraceFloat(string line, string token, out float value)
        {
            value = 0f;
            var rawValue = TryReadTokenValue(line, token);
            return !string.IsNullOrWhiteSpace(rawValue) &&
                   float.TryParse(rawValue, NumberStyles.Float, CultureInfo.InvariantCulture, out value);
        }

        private static bool TryParseTraceVector(string line, string token, out Vector3 value)
        {
            value = Vector3.zero;
            var start = line.IndexOf(token, StringComparison.Ordinal);
            if (start < 0)
            {
                return false;
            }

            start += token.Length;
            if (start >= line.Length || line[start] != '(')
            {
                return false;
            }

            start += 1;
            var end = line.IndexOf(')', start);
            if (end <= start)
            {
                return false;
            }

            var parts = line.Substring(start, end - start).Split(',');
            if (parts.Length < 3 ||
                !float.TryParse(parts[0], NumberStyles.Float, CultureInfo.InvariantCulture, out var x) ||
                !float.TryParse(parts[1], NumberStyles.Float, CultureInfo.InvariantCulture, out var y) ||
                !float.TryParse(parts[2], NumberStyles.Float, CultureInfo.InvariantCulture, out var z))
            {
                return false;
            }

            value = new Vector3(x, y, z);
            return true;
        }

        private static string TryReadTokenValue(string line, string token)
        {
            var start = line.IndexOf(token, StringComparison.Ordinal);
            if (start < 0)
            {
                return string.Empty;
            }

            start += token.Length;
            var end = line.IndexOf(' ', start);
            if (end < 0)
            {
                end = line.Length;
            }

            return line.Substring(start, end - start).Trim();
        }

        private static PlayerBase[] ResolveRuntimePlayers()
        {
            if (MatchManager.AllPlayers != null)
            {
                return MatchManager.AllPlayers
                    .Where(player => player != null && player.PlayerController != null)
                    .ToArray();
            }

            if (MatchManager.Current == null)
            {
                return Array.Empty<PlayerBase>();
            }

            var players = Enumerable.Empty<PlayerBase>();
            if (MatchManager.Current.GameTeam1 != null && MatchManager.Current.GameTeam1.GamePlayers != null)
            {
                players = players.Concat(MatchManager.Current.GameTeam1.GamePlayers);
            }

            if (MatchManager.Current.GameTeam2 != null && MatchManager.Current.GameTeam2.GamePlayers != null)
            {
                players = players.Concat(MatchManager.Current.GameTeam2.GamePlayers);
            }

            return players
                .Where(player => player != null && player.PlayerController != null)
                .ToArray();
        }

        private static string DescribePlayer(PlayerBase player)
        {
            if (player == null)
            {
                return "unknown";
            }

            var playerName =
                player.MatchPlayer != null && player.MatchPlayer.Player != null
                    ? player.MatchPlayer.Player.name
                    : null;
            if (!string.IsNullOrWhiteSpace(playerName))
            {
                return playerName;
            }

            var teamName =
                player.GameTeam != null && player.GameTeam.Team != null && player.GameTeam.Team.Team != null
                    ? player.GameTeam.Team.Team.TeamName
                    : "team";
            var shirtNumber = player.MatchPlayer != null ? player.MatchPlayer.Number.ToString() : "?";
            return teamName + "#" + shirtNumber;
        }

        private static void LoadDevelopmentSceneIfAvailable()
        {
            if (!GtexSceneLoader.SceneExists(GtexSceneLoader.DevelopmentScenePath))
            {
                return;
            }

            var activeScene = EditorSceneManager.GetActiveScene();
            if (string.Equals(activeScene.path, GtexSceneLoader.DevelopmentScenePath, StringComparison.OrdinalIgnoreCase))
            {
                return;
            }

            EditorSceneManager.OpenScene(GtexSceneLoader.DevelopmentScenePath, OpenSceneMode.Single);
        }

        private static void LoadProductionSceneIfAvailable()
        {
            if (!GtexSceneLoader.SceneExists(GtexSceneLoader.ProductionScenePath))
            {
                return;
            }

            var activeScene = EditorSceneManager.GetActiveScene();
            if (string.Equals(activeScene.path, GtexSceneLoader.ProductionScenePath, StringComparison.OrdinalIgnoreCase))
            {
                return;
            }

            EditorSceneManager.OpenScene(GtexSceneLoader.ProductionScenePath, OpenSceneMode.Single);
        }

        private static void BootstrapSceneArtifactsIfNeeded()
        {
            if (TryFindPitchArtifacts(out var players, out var goals, out var ball) &&
                HasCompletePitchArtifacts(players, goals, ball))
            {
                return;
            }

            LoadProductionSceneIfAvailable();
        }

        private static void ValidateGoal(GoalNet goal, Vector3 expectedGroundCenter, string goalLabel)
        {
            if (goal == null)
            {
                return;
            }

            ValidateGoal(goal.GroundAnchorPosition, expectedGroundCenter, goalLabel);
        }

        private static void ValidateGoal(Vector3 actualGround, Vector3 expectedGroundCenter, string goalLabel)
        {
            var planarDistance = Vector2.Distance(
                new Vector2(actualGround.x, actualGround.z),
                new Vector2(expectedGroundCenter.x, expectedGroundCenter.z));

            if (planarDistance > 2f)
            {
                throw new InvalidOperationException(
                    "The " +
                    goalLabel +
                    " goal is outside legal pitch space. Expected=" +
                    expectedGroundCenter +
                    ", actual=" +
                    actualGround +
                    ".");
            }

            if (Mathf.Abs(actualGround.y - expectedGroundCenter.y) > 0.25f)
            {
                throw new InvalidOperationException(
                    "The " +
                    goalLabel +
                    " goal is not resting on the resolved grass height. ExpectedY=" +
                    expectedGroundCenter.y.ToString("0.##") +
                    ", actualY=" +
                    actualGround.y.ToString("0.##") +
                    ".");
            }
        }
    }
}
#endif
