using System;
using System.Linq;
using UnityEngine;

namespace FStudio.GTEX.VisualBridge
{
    public sealed class GtexOriginalPitchVisualFallback : MonoBehaviour
    {
        private static readonly string[] PreferredPitchNames = { "ExtrudedField", "fieldGround" };
        private static readonly string[] PitchTokens = { "pitch", "grass", "field", "ground" };
        private static readonly string[] IgnoreTokens = { "line", "marking", "boundary", "halfway" };

        [SerializeField] private GameObject originalPitchPrefab;
        [SerializeField] private bool preferOriginalPitchPrefab = true;
        [SerializeField] private bool disableUnderlayWhenOriginalPitchIsActive = true;
        [SerializeField] private bool createIfMissing;
        [SerializeField] private Vector2 pitchSize = new Vector2(105f, 68f);
        [SerializeField] private Color fallbackGrassColor = new Color(0.1f, 0.44f, 0.12f, 1f);

        private Transform fallbackPitchRoot;
        private Transform originalPitchInstanceRoot;
        private Renderer activePitchRenderer;
        private Renderer instancedOriginalPitchRenderer;
        private Material runtimeFallbackMaterial;
        private Vector3 originalPitchBaseScale = Vector3.one;
        private bool hasOriginalPitchBaseScale;

        public bool PitchRendererReady => activePitchRenderer != null &&
                                          activePitchRenderer.enabled &&
                                          HasUsablePitchSurface(activePitchRenderer);

        public bool EnsurePitchVisible(float length = 105f, float width = 68f)
        {
            pitchSize = new Vector2(Mathf.Max(10f, length), Mathf.Max(10f, width));

            activePitchRenderer = FindPreferredOriginalPitchRenderer();
            if (activePitchRenderer == null && preferOriginalPitchPrefab)
            {
                EnsureOriginalPitchInstance();
                activePitchRenderer = FindPreferredOriginalPitchRenderer();
            }

            if (activePitchRenderer == null)
            {
                activePitchRenderer = FindPitchRenderer();
            }

            if (activePitchRenderer != null)
            {
                PreparePitchRenderer(activePitchRenderer);
                if (PitchRendererReady)
                {
                    UpdatePitchPresentation(activePitchRenderer);
                    Debug.Log("[GTEX OriginalVisualRuntime] Pitch renderer found: " + activePitchRenderer.name);
                    return true;
                }

                Debug.LogWarning(
                    "[GTEX OriginalVisualRuntime] Pitch renderer '" +
                    activePitchRenderer.name +
                    "' is present but has no usable original material.");
            }

            if (!createIfMissing)
            {
                return false;
            }

            Debug.LogWarning("[GTEX OriginalVisualRuntime] No original pitch renderer was available. Creating plain fallback pitch.");
            CreateFallbackPitch();
            return PitchRendererReady;
        }

        private Renderer FindPreferredOriginalPitchRenderer()
        {
            var exactExtrudedField = FindScenePitchRendererExact("ExtrudedField");
            if (HasUsablePitchSurface(exactExtrudedField))
            {
                return exactExtrudedField;
            }

            var exactFieldGround = FindScenePitchRendererExact("fieldGround");
            if (HasUsablePitchSurface(exactFieldGround))
            {
                return exactFieldGround;
            }

            return null;
        }

        private Renderer FindPitchRenderer()
        {
            Renderer bestRenderer = null;
            var bestScore = float.MinValue;
            var renderers = FindObjectsByType<Renderer>(FindObjectsInactive.Include, FindObjectsSortMode.None);
            for (var index = 0; index < renderers.Length; index += 1)
            {
                var renderer = renderers[index];
                if (renderer == null || renderer.transform == null || renderer is LineRenderer)
                {
                    continue;
                }

                var name = renderer.name ?? string.Empty;
                if (IgnoreTokens.Any(token => name.IndexOf(token, StringComparison.OrdinalIgnoreCase) >= 0))
                {
                    continue;
                }

                var isPreferredName = PreferredPitchNames.Any(
                    preferred => string.Equals(name, preferred, StringComparison.OrdinalIgnoreCase));
                var matchesPitchToken = PitchTokens.Any(
                    token => name.IndexOf(token, StringComparison.OrdinalIgnoreCase) >= 0);
                if (!isPreferredName && !matchesPitchToken)
                {
                    continue;
                }

                var bounds = renderer.bounds.size;
                var maxDimension = Mathf.Max(bounds.x, bounds.z);
                if (!isPreferredName && maxDimension < 20f)
                {
                    continue;
                }

                var score = maxDimension * Mathf.Max(1f, Mathf.Min(bounds.x, bounds.z));
                if (isPreferredName)
                {
                    score += 1_000_000f;
                }

                if (renderer.enabled)
                {
                    score += 25_000f;
                }

                if (HasUsablePitchSurface(renderer))
                {
                    score += 50_000f;
                }

                if (score <= bestScore)
                {
                    continue;
                }

                bestRenderer = renderer;
                bestScore = score;
            }

            return bestRenderer;
        }

        private Renderer FindScenePitchRendererExact(string exactName)
        {
            if (string.IsNullOrWhiteSpace(exactName))
            {
                return null;
            }

            var renderers = FindObjectsByType<Renderer>(FindObjectsInactive.Include, FindObjectsSortMode.None);
            for (var index = 0; index < renderers.Length; index += 1)
            {
                var renderer = renderers[index];
                if (renderer == null ||
                    renderer.transform == null ||
                    renderer is LineRenderer ||
                    !string.Equals(renderer.name, exactName, StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }

                return renderer;
            }

            return null;
        }

        private void EnsureOriginalPitchInstance()
        {
            if (originalPitchPrefab == null)
            {
                return;
            }

            if (originalPitchInstanceRoot == null)
            {
                var instance = Instantiate(originalPitchPrefab, transform);
                instance.name = "ExtrudedField";
                originalPitchInstanceRoot = instance.transform;
                instancedOriginalPitchRenderer = instance.GetComponentInChildren<Renderer>(true);
                if (originalPitchInstanceRoot != null)
                {
                    originalPitchBaseScale = originalPitchInstanceRoot.localScale;
                    hasOriginalPitchBaseScale = true;
                }
            }

            AlignOriginalPitchInstance();
        }

        private void AlignOriginalPitchInstance()
        {
            if (originalPitchInstanceRoot == null)
            {
                return;
            }

            if (instancedOriginalPitchRenderer == null)
            {
                instancedOriginalPitchRenderer = originalPitchInstanceRoot.GetComponentInChildren<Renderer>(true);
                if (instancedOriginalPitchRenderer == null)
                {
                    return;
                }
            }

            if (!hasOriginalPitchBaseScale)
            {
                originalPitchBaseScale = originalPitchInstanceRoot.localScale;
                hasOriginalPitchBaseScale = true;
            }

            var underlayRenderer = FindScenePitchRendererExact("fieldGround");
            var targetCenter = underlayRenderer != null
                ? underlayRenderer.bounds.center
                : new Vector3(pitchSize.x * 0.5f, 0f, pitchSize.y * 0.5f);
            var targetSize = underlayRenderer != null
                ? underlayRenderer.bounds.size
                : new Vector3(pitchSize.x, 0f, pitchSize.y);

            originalPitchInstanceRoot.gameObject.SetActive(true);
            originalPitchInstanceRoot.localRotation = Quaternion.identity;
            originalPitchInstanceRoot.localScale = originalPitchBaseScale;
            originalPitchInstanceRoot.position = Vector3.zero;

            var sourceBounds = instancedOriginalPitchRenderer.bounds;
            var scaleX = targetSize.x > 0.01f && sourceBounds.size.x > 0.01f
                ? targetSize.x / sourceBounds.size.x
                : 1f;
            var scaleZ = targetSize.z > 0.01f && sourceBounds.size.z > 0.01f
                ? targetSize.z / sourceBounds.size.z
                : 1f;

            originalPitchInstanceRoot.localScale = new Vector3(
                originalPitchBaseScale.x * scaleX,
                originalPitchBaseScale.y,
                originalPitchBaseScale.z * scaleZ);

            sourceBounds = instancedOriginalPitchRenderer.bounds;
            var targetSurfaceY = underlayRenderer != null ? underlayRenderer.bounds.max.y + 0.02f : 0.02f;
            var offset = targetCenter - sourceBounds.center;
            offset.y = targetSurfaceY - sourceBounds.min.y;
            originalPitchInstanceRoot.position += offset;
        }

        private void PreparePitchRenderer(Renderer renderer)
        {
            if (renderer == null)
            {
                return;
            }

            renderer.enabled = true;
            renderer.gameObject.SetActive(true);

            if (originalPitchInstanceRoot != null &&
                renderer.transform != null &&
                renderer.transform.IsChildOf(originalPitchInstanceRoot))
            {
                SetHierarchyRenderersEnabled(originalPitchInstanceRoot, true);
            }
        }

        private void CreateFallbackPitch()
        {
            if (fallbackPitchRoot == null)
            {
                var pitch = GameObject.CreatePrimitive(PrimitiveType.Plane);
                pitch.name = "GTEX_Fallback_PlainPitch";
                pitch.transform.SetParent(transform, false);
                fallbackPitchRoot = pitch.transform;

                var collider = pitch.GetComponent<Collider>();
                if (collider != null)
                {
                    if (Application.isPlaying)
                    {
                        Destroy(collider);
                    }
                    else
                    {
                        DestroyImmediate(collider);
                    }
                }

                activePitchRenderer = pitch.GetComponent<Renderer>();
                if (activePitchRenderer != null)
                {
                    activePitchRenderer.sharedMaterial = GetOrCreateFallbackMaterial();
                }
            }

            fallbackPitchRoot.position = new Vector3(pitchSize.x * 0.5f, 0f, pitchSize.y * 0.5f);
            fallbackPitchRoot.localRotation = Quaternion.identity;
            fallbackPitchRoot.localScale = new Vector3(pitchSize.x / 10f, 1f, pitchSize.y / 10f);
            PreparePitchRenderer(activePitchRenderer);
        }

        private void UpdatePitchPresentation(Renderer preferredRenderer)
        {
            if (preferredRenderer == null)
            {
                return;
            }

            if (disableUnderlayWhenOriginalPitchIsActive &&
                string.Equals(preferredRenderer.name, "ExtrudedField", StringComparison.OrdinalIgnoreCase))
            {
                var underlayRenderer = FindScenePitchRendererExact("fieldGround");
                if (underlayRenderer != null && underlayRenderer != preferredRenderer)
                {
                    underlayRenderer.enabled = false;
                }
            }
            else
            {
                var underlayRenderer = FindScenePitchRendererExact("fieldGround");
                if (underlayRenderer != null)
                {
                    underlayRenderer.enabled = true;
                    underlayRenderer.gameObject.SetActive(true);
                }
            }

            if (fallbackPitchRoot != null && preferredRenderer.transform != fallbackPitchRoot)
            {
                fallbackPitchRoot.gameObject.SetActive(false);
            }
        }

        private static void SetHierarchyRenderersEnabled(Transform root, bool enabled)
        {
            if (root == null)
            {
                return;
            }

            var renderers = root.GetComponentsInChildren<Renderer>(true);
            for (var index = 0; index < renderers.Length; index += 1)
            {
                var renderer = renderers[index];
                if (renderer == null)
                {
                    continue;
                }

                renderer.enabled = enabled;
                renderer.gameObject.SetActive(true);
            }
        }

        private bool HasUsablePitchSurface(Renderer renderer)
        {
            if (renderer == null)
            {
                return false;
            }

            var sharedMaterials = renderer.sharedMaterials;
            if (sharedMaterials == null || sharedMaterials.Length == 0)
            {
                return false;
            }

            for (var index = 0; index < sharedMaterials.Length; index += 1)
            {
                if (!HasUsablePitchMaterial(sharedMaterials[index]))
                {
                    return false;
                }
            }

            return true;
        }

        private static bool HasUsablePitchMaterial(Material material)
        {
            if (material == null)
            {
                return false;
            }

            var shader = material.shader;
            if (shader == null || !shader.isSupported)
            {
                return false;
            }

            var shaderName = shader.name ?? string.Empty;
            return shaderName.IndexOf("error", StringComparison.OrdinalIgnoreCase) < 0;
        }

        private Material GetOrCreateFallbackMaterial()
        {
            if (runtimeFallbackMaterial != null)
            {
                return runtimeFallbackMaterial;
            }

            var shader = Shader.Find("Universal Render Pipeline/Lit") ??
                         Shader.Find("Universal Render Pipeline/Simple Lit") ??
                         Shader.Find("Standard");
            if (shader == null)
            {
                return null;
            }

            runtimeFallbackMaterial = new Material(shader)
            {
                name = "GTEX_Runtime_FallbackPitch"
            };

            if (runtimeFallbackMaterial.HasProperty("_BaseColor"))
            {
                runtimeFallbackMaterial.SetColor("_BaseColor", fallbackGrassColor);
            }

            if (runtimeFallbackMaterial.HasProperty("_Color"))
            {
                runtimeFallbackMaterial.SetColor("_Color", fallbackGrassColor);
            }

            if (runtimeFallbackMaterial.HasProperty("_Smoothness"))
            {
                runtimeFallbackMaterial.SetFloat("_Smoothness", 0f);
            }

            return runtimeFallbackMaterial;
        }
    }
}
