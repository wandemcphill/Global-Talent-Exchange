using System;
using FStudio.MatchEngine;
using UnityEngine;

namespace FStudio.GTEX.Playback
{
    public static class GtexPitchLocator
    {
        private sealed class PitchCandidate
        {
            public Bounds Bounds;
            public float Score;
            public string SourceDescription;
        }

        public static GtexPitchSpace Resolve(out string sourceDescription)
        {
            if (TryResolve(out var pitchSpace, out sourceDescription))
            {
                return pitchSpace;
            }

            if (TryResolveFromMatchManagerField(out pitchSpace, out sourceDescription))
            {
                return pitchSpace;
            }

            var fallbackCenter = Vector3.zero;
            if (MatchManager.Current != null)
            {
                var fieldSize = MatchManager.Current.SizeOfField;
                if (fieldSize != Vector2.zero)
                {
                    fallbackCenter = new Vector3(fieldSize.x * 0.5f, 0f, fieldSize.y * 0.5f);
                }
            }

            sourceDescription = "fallback:default";
            return new GtexPitchSpace(
                GtexPitchSpace.DefaultLength,
                GtexPitchSpace.DefaultWidth,
                0f,
                fallbackCenter);
        }

        public static bool TryResolve(out GtexPitchSpace pitchSpace, out string sourceDescription)
        {
            pitchSpace = null;
            sourceDescription = string.Empty;

            PitchCandidate bestCandidate = null;

            var renderers = UnityEngine.Object.FindObjectsByType<Renderer>(FindObjectsSortMode.None);
            for (var index = 0; index < renderers.Length; index += 1)
            {
                var renderer = renderers[index];
                if (renderer == null || !renderer.enabled)
                {
                    continue;
                }

                if (renderer is ParticleSystemRenderer)
                {
                    continue;
                }

                if (TryCreateCandidate(renderer, renderer.bounds, "renderer", GetMaterialHint(renderer.sharedMaterials), out var candidate) &&
                    IsBetterCandidate(candidate, bestCandidate))
                {
                    bestCandidate = candidate;
                }
            }

            var colliders = UnityEngine.Object.FindObjectsByType<Collider>(FindObjectsSortMode.None);
            for (var index = 0; index < colliders.Length; index += 1)
            {
                var collider = colliders[index];
                if (collider == null || !collider.enabled)
                {
                    continue;
                }

                if (TryCreateCandidate(collider, collider.bounds, "collider", string.Empty, out var candidate) &&
                    IsBetterCandidate(candidate, bestCandidate))
                {
                    bestCandidate = candidate;
                }
            }

            if (bestCandidate == null)
            {
                return false;
            }

            var size = bestCandidate.Bounds.size;
            var length = Mathf.Max(size.x, size.z);
            var width = Mathf.Min(size.x, size.z);
            var grassY = bestCandidate.Bounds.max.y;
            var center = bestCandidate.Bounds.center;

            pitchSpace = new GtexPitchSpace(length, width, grassY, center);
            sourceDescription = bestCandidate.SourceDescription;
            return true;
        }

        private static bool TryResolveFromMatchManagerField(out GtexPitchSpace pitchSpace, out string sourceDescription)
        {
            pitchSpace = null;
            sourceDescription = string.Empty;

            if (MatchManager.Current == null)
            {
                return false;
            }

            var fieldSize = MatchManager.Current.SizeOfField;
            if (fieldSize == Vector2.zero)
            {
                return false;
            }

            if (!TryFindMatchManagerFieldAnchor(out var anchor, out var anchorBounds))
            {
                return false;
            }

            var center = anchorBounds.size.sqrMagnitude > 0.0001f
                ? anchorBounds.center
                : anchor.transform.position;
            var grassY = anchorBounds.size.sqrMagnitude > 0.0001f
                ? anchorBounds.max.y
                : anchor.transform.position.y;
            if (Mathf.Abs(grassY) <= 0.1f)
            {
                grassY = 0f;
            }

            pitchSpace = new GtexPitchSpace(fieldSize.x, fieldSize.y, grassY, center);
            sourceDescription =
                "match-manager:" +
                BuildHierarchyName(anchor.transform) +
                " size=(" +
                fieldSize.x.ToString("0.##") +
                "x" +
                fieldSize.y.ToString("0.##") +
                ")";
            return true;
        }

        private static bool TryCreateCandidate(
            Component component,
            Bounds bounds,
            string sourceType,
            string materialHint,
            out PitchCandidate candidate)
        {
            candidate = null;
            if (component == null)
            {
                return false;
            }

            var size = bounds.size;
            var length = Mathf.Max(size.x, size.z);
            var width = Mathf.Min(size.x, size.z);
            if (!float.IsFinite(length) ||
                !float.IsFinite(width) ||
                length < 60f ||
                width < 35f ||
                length > 160f ||
                width > 100f)
            {
                return false;
            }

            var aspect = length / Mathf.Max(width, 0.001f);
            if (aspect < 1.1f || aspect > 1.9f)
            {
                return false;
            }

            var nameHint = BuildHierarchyName(component.transform);
            var combinedHint = (nameHint + " " + materialHint).ToLowerInvariant();
            var score = 0f;

            if (combinedHint.Contains("grass"))
            {
                score += 120f;
            }

            if (combinedHint.Contains("pitch"))
            {
                score += 100f;
            }

            if (combinedHint.Contains("field"))
            {
                score += 60f;
            }

            if (combinedHint.Contains("ground"))
            {
                score += 20f;
            }

            if (combinedHint.Contains("stadium") ||
                combinedHint.Contains("platform") ||
                combinedHint.Contains("stand") ||
                combinedHint.Contains("tribune") ||
                combinedHint.Contains("crowd") ||
                combinedHint.Contains("goal") ||
                combinedHint.Contains("net"))
            {
                score -= 120f;
            }

            score += Mathf.Max(0f, 30f - Mathf.Abs(length - GtexPitchSpace.DefaultLength));
            score += Mathf.Max(0f, 30f - Mathf.Abs(width - GtexPitchSpace.DefaultWidth));
            score += sourceType == "renderer" ? 20f : 5f;

            if (score <= 0f)
            {
                return false;
            }

            candidate = new PitchCandidate
            {
                Bounds = bounds,
                Score = score,
                SourceDescription =
                    sourceType +
                    ":" +
                    nameHint +
                    " size=(" +
                    length.ToString("0.##") +
                    "x" +
                    width.ToString("0.##") +
                    ")"
            };
            return true;
        }

        private static bool TryFindMatchManagerFieldAnchor(out Component anchor, out Bounds bounds)
        {
            anchor = null;
            bounds = default;

            var bestScore = float.MinValue;

            var colliders = UnityEngine.Object.FindObjectsByType<Collider>(FindObjectsSortMode.None);
            for (var index = 0; index < colliders.Length; index += 1)
            {
                var collider = colliders[index];
                if (collider == null || !collider.enabled)
                {
                    continue;
                }

                ConsiderFieldAnchor(collider, string.Empty, collider.bounds, ref anchor, ref bounds, ref bestScore);
            }

            var renderers = UnityEngine.Object.FindObjectsByType<Renderer>(FindObjectsSortMode.None);
            for (var index = 0; index < renderers.Length; index += 1)
            {
                var renderer = renderers[index];
                if (renderer == null || !renderer.enabled || renderer is ParticleSystemRenderer)
                {
                    continue;
                }

                ConsiderFieldAnchor(
                    renderer,
                    GetMaterialHint(renderer.sharedMaterials),
                    renderer.bounds,
                    ref anchor,
                    ref bounds,
                    ref bestScore);
            }

            return anchor != null;
        }

        private static void ConsiderFieldAnchor(
            Component component,
            string materialHint,
            Bounds bounds,
            ref Component bestAnchor,
            ref Bounds bestBounds,
            ref float bestScore)
        {
            if (component == null)
            {
                return;
            }

            var combinedHint = (BuildHierarchyName(component.transform) + " " + materialHint).ToLowerInvariant();
            if (!combinedHint.Contains("field") &&
                !combinedHint.Contains("ground") &&
                !combinedHint.Contains("grass") &&
                !combinedHint.Contains("pitch"))
            {
                return;
            }

            if (combinedHint.Contains("goal") ||
                combinedHint.Contains("net") ||
                combinedHint.Contains("stadium") ||
                combinedHint.Contains("platform"))
            {
                return;
            }

            var score = 0f;
            if (combinedHint.Contains("fieldground"))
            {
                score += 180f;
            }

            if (combinedHint.Contains("field"))
            {
                score += 120f;
            }

            if (combinedHint.Contains("grass"))
            {
                score += 90f;
            }

            if (combinedHint.Contains("pitch"))
            {
                score += 75f;
            }

            if (combinedHint.Contains("ground"))
            {
                score += 60f;
            }

            if (bounds.size.sqrMagnitude > 0.0001f)
            {
                score += Mathf.Max(0f, 10f - Mathf.Abs(bounds.center.y));
            }

            if (score <= bestScore)
            {
                return;
            }

            bestScore = score;
            bestAnchor = component;
            bestBounds = bounds;
        }

        private static bool IsBetterCandidate(PitchCandidate candidate, PitchCandidate currentBest)
        {
            if (candidate == null)
            {
                return false;
            }

            if (currentBest == null)
            {
                return true;
            }

            return candidate.Score > currentBest.Score;
        }

        private static string GetMaterialHint(Material[] materials)
        {
            if (materials == null || materials.Length == 0)
            {
                return string.Empty;
            }

            var names = string.Empty;
            for (var index = 0; index < materials.Length; index += 1)
            {
                var material = materials[index];
                if (material == null)
                {
                    continue;
                }

                names += " " + material.name;
            }

            return names;
        }

        private static string BuildHierarchyName(Transform transform)
        {
            if (transform == null)
            {
                return string.Empty;
            }

            var result = transform.name ?? string.Empty;
            var parent = transform.parent;
            var depth = 0;
            while (parent != null && depth < 3)
            {
                result = parent.name + "/" + result;
                parent = parent.parent;
                depth += 1;
            }

            return result;
        }
    }
}
