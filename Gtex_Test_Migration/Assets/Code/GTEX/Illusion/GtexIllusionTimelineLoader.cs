using System;
using System.IO;
using UnityEngine;

namespace FStudio.GTEX.Illusion
{
    public sealed class GtexIllusionTimelineLoadResult
    {
        public GtexIllusionTimeline Timeline;
        public GtexIllusionScenePackage ScenePackage;
        public string Source = string.Empty;
        public string Message = string.Empty;
        public bool IsExternal;
    }

    public static class GtexIllusionTimelineLoader
    {
        private const string TimelinePathEnvVar = "GTEX_ILLUSION_TIMELINE_PATH";
        private const string TimelineResourceEnvVar = "GTEX_ILLUSION_TIMELINE_RESOURCE";
        private const string TimelineUrlEnvVar = "GTEX_ILLUSION_TIMELINE_URL";

        public static GtexIllusionTimelineLoadResult Load(
            TextAsset explicitAsset,
            string defaultResourcePath)
        {
            if (TryLoadFromPath(ResolveTimelinePathOverride(), out var pathResult))
            {
                return pathResult;
            }

            var resourceOverride = ResolveTimelineResourceOverride();
            if (!string.IsNullOrWhiteSpace(resourceOverride) &&
                TryLoadFromResource(resourceOverride.Trim(), true, out var overrideResourceResult))
            {
                return overrideResourceResult;
            }

            if (explicitAsset != null &&
                TryParseTimeline(explicitAsset.text, "asset:" + explicitAsset.name, false, out var assetResult))
            {
                return assetResult;
            }

            if (!string.IsNullOrWhiteSpace(defaultResourcePath) &&
                TryLoadFromResource(defaultResourcePath.Trim(), false, out var defaultResourceResult))
            {
                return defaultResourceResult;
            }

            return new GtexIllusionTimelineLoadResult
            {
                Source = "generated",
                Message = "No external or resource timeline was available."
            };
        }

        public static string ResolveTimelineUrlOverride()
        {
            var commandLineValue = ResolveCommandLineValue(
                "--gtex-illusion-timeline-url",
                "--illusion-timeline-url",
                "--gtex-illusion-url",
                "--illusion-url",
                "--timeline-url");
            if (!string.IsNullOrWhiteSpace(commandLineValue))
            {
                return commandLineValue.Trim();
            }

            return ResolveEnvironmentValue(TimelineUrlEnvVar);
        }

        public static bool TryParseRawJson(
            string json,
            string source,
            bool isExternal,
            out GtexIllusionTimelineLoadResult result)
        {
            return TryParseTimeline(json, source, isExternal, out result);
        }

        public static bool TryLoadFromPath(string path, out GtexIllusionTimelineLoadResult result)
        {
            result = null;
            if (string.IsNullOrWhiteSpace(path))
            {
                return false;
            }

            var trimmedPath = path.Trim().Trim('"');
            try
            {
                if (!File.Exists(trimmedPath))
                {
                    Debug.LogWarning("[GTEX Illusion] Timeline path does not exist: " + trimmedPath);
                    return false;
                }

                var json = File.ReadAllText(trimmedPath);
                return TryParseTimeline(json, trimmedPath, true, out result);
            }
            catch (Exception exception)
            {
                Debug.LogWarning("[GTEX Illusion] Failed to read timeline path '" + trimmedPath + "'.\n" + exception);
                return false;
            }
        }

        public static bool TryLoadFromResource(
            string resourcePath,
            bool isExternal,
            out GtexIllusionTimelineLoadResult result)
        {
            result = null;
            if (string.IsNullOrWhiteSpace(resourcePath))
            {
                return false;
            }

            var asset = Resources.Load<TextAsset>(resourcePath);
            if (asset == null)
            {
                if (isExternal)
                {
                    Debug.LogWarning("[GTEX Illusion] Timeline resource not found: " + resourcePath);
                }

                return false;
            }

            return TryParseTimeline(asset.text, "resource:" + resourcePath, isExternal, out result);
        }

        private static bool TryParseTimeline(
            string json,
            string source,
            bool isExternal,
            out GtexIllusionTimelineLoadResult result)
        {
            result = null;
            if (string.IsNullOrWhiteSpace(json))
            {
                return false;
            }

            var trimmed = (json ?? string.Empty).Trim();

            if (LooksLikeScenePackage(trimmed) &&
                TryParseScenePackage(trimmed, source, isExternal, out result))
            {
                return true;
            }

            var normalizedJson = NormalizeTimelineJson(trimmed);
            try
            {
                var timeline = JsonUtility.FromJson<GtexIllusionTimeline>(normalizedJson);
                if (timeline != null && timeline.events != null && timeline.events.Length > 0)
                {
                    result = new GtexIllusionTimelineLoadResult
                    {
                        Timeline = timeline,
                        Source = source,
                        IsExternal = isExternal,
                        Message = "Loaded timeline from " + source + "."
                    };
                    return true;
                }
            }
            catch (Exception exception)
            {
                Debug.LogWarning("[GTEX Illusion] Failed to parse timeline '" + source + "'.\n" + exception);
            }

            if (TryParseScenePackage(trimmed, source, isExternal, out result))
            {
                return true;
            }

            Debug.LogWarning("[GTEX Illusion] Timeline was empty: " + source);
            return false;
        }

        private static bool TryParseScenePackage(
            string json,
            string source,
            bool isExternal,
            out GtexIllusionTimelineLoadResult result)
        {
            result = null;
            try
            {
                var package = JsonUtility.FromJson<GtexIllusionScenePackage>(NormalizeSceneJson(json));
                if (package == null || package.scenes == null || package.scenes.Length == 0)
                {
                    return false;
                }

                result = new GtexIllusionTimelineLoadResult
                {
                    ScenePackage = package,
                    Source = source,
                    IsExternal = isExternal,
                    Message = "Loaded scene package from " + source + "."
                };
                return true;
            }
            catch (Exception exception)
            {
                Debug.LogWarning("[GTEX Illusion] Failed to parse scene package '" + source + "'.\n" + exception);
                return false;
            }
        }

        private static string NormalizeTimelineJson(string json)
        {
            var trimmed = (json ?? string.Empty).Trim();
            if (trimmed.StartsWith("[", StringComparison.Ordinal))
            {
                return "{\"events\":" + trimmed + "}";
            }

            return trimmed;
        }

        private static string NormalizeSceneJson(string json)
        {
            var trimmed = (json ?? string.Empty).Trim();
            if (trimmed.StartsWith("[", StringComparison.Ordinal))
            {
                return "{\"scenes\":" + trimmed + "}";
            }

            return trimmed;
        }

        private static bool LooksLikeScenePackage(string json)
        {
            return json.IndexOf("\"scenes\"", StringComparison.OrdinalIgnoreCase) >= 0 ||
                   json.IndexOf("_SCENE", StringComparison.OrdinalIgnoreCase) >= 0;
        }

        public static string ResolveTimelinePathOverride()
        {
            var commandLineValue = ResolveCommandLineValue(
                "--gtex-illusion-timeline-path",
                "--illusion-timeline-path",
                "--gtex-illusion-timeline",
                "--illusion-timeline",
                "--timeline-path",
                "--timeline");
            if (!string.IsNullOrWhiteSpace(commandLineValue))
            {
                return commandLineValue;
            }

            return ResolveEnvironmentValue(TimelinePathEnvVar);
        }

        public static string ResolveTimelineResourceOverride()
        {
            var commandLineValue = ResolveCommandLineValue(
                "--gtex-illusion-resource",
                "--gtex-illusion-timeline-resource",
                "--illusion-resource",
                "--timeline-resource");
            if (!string.IsNullOrWhiteSpace(commandLineValue))
            {
                return commandLineValue;
            }

            return ResolveEnvironmentValue(TimelineResourceEnvVar);
        }

        private static string ResolveEnvironmentValue(string name)
        {
            try
            {
                return Environment.GetEnvironmentVariable(name);
            }
            catch (Exception exception)
            {
                Debug.LogWarning("[GTEX Illusion] Failed to read environment value '" + name + "'.\n" + exception);
                return null;
            }
        }

        private static string ResolveCommandLineValue(params string[] flags)
        {
            try
            {
                var args = Environment.GetCommandLineArgs();
                for (var index = 0; index < args.Length; index += 1)
                {
                    var candidate = args[index];
                    if (string.IsNullOrWhiteSpace(candidate))
                    {
                        continue;
                    }

                    for (var flagIndex = 0; flagIndex < flags.Length; flagIndex += 1)
                    {
                        var flag = flags[flagIndex];
                        if (string.Equals(candidate, flag, StringComparison.OrdinalIgnoreCase))
                        {
                            return index + 1 < args.Length ? args[index + 1] : string.Empty;
                        }

                        if (candidate.StartsWith(flag + "=", StringComparison.OrdinalIgnoreCase))
                        {
                            return candidate.Substring(flag.Length + 1);
                        }
                    }
                }
            }
            catch (Exception exception)
            {
                Debug.LogWarning("[GTEX Illusion] Failed to inspect command line args.\n" + exception);
            }

            return null;
        }
    }
}
