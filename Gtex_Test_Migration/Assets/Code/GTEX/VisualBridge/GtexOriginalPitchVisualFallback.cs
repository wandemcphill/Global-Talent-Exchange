using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace FStudio.GTEX.VisualBridge
{
    public sealed class GtexOriginalPitchVisualFallback : MonoBehaviour
    {
        private static readonly string[] PitchTokens = { "pitch", "grass", "field", "ground", "extrudedfield" };

        [SerializeField] private bool createIfMissing = true;
        [SerializeField] private Vector2 pitchSize = new Vector2(105f, 68f);
        [SerializeField] private Color grassColor = new Color(0.08f, 0.45f, 0.12f, 1f);

        private Transform fallbackPitchRoot;
        private Renderer activePitchRenderer;

        public bool PitchRendererReady => activePitchRenderer != null && activePitchRenderer.enabled;

        public bool EnsurePitchVisible(float length = 105f, float width = 68f)
        {
            pitchSize = new Vector2(Mathf.Max(10f, length), Mathf.Max(10f, width));

            activePitchRenderer = FindPitchRenderer();
            if (activePitchRenderer != null)
            {
                activePitchRenderer.enabled = true;
                if (activePitchRenderer.gameObject != null)
                {
                    activePitchRenderer.gameObject.SetActive(true);
                }

                Debug.Log("[GTEX OriginalVisualRuntime] Pitch renderer found: " + activePitchRenderer.name);
                return true;
            }

            if (!createIfMissing)
            {
                return false;
            }

            Debug.LogWarning("[GTEX OriginalVisualRuntime] No pitch renderer found. Creating fallback green pitch.");
            CreateFallbackPitch();
            return fallbackPitchRoot != null && activePitchRenderer != null;
        }

        private Renderer FindPitchRenderer()
        {
            var renderers = FindObjectsByType<Renderer>(FindObjectsInactive.Include, FindObjectsSortMode.None);
            foreach (var renderer in renderers)
            {
                if (renderer == null || renderer.transform == null)
                {
                    continue;
                }

                var name = renderer.name ?? string.Empty;
                if (!PitchTokens.Any(token => name.IndexOf(token, StringComparison.OrdinalIgnoreCase) >= 0))
                {
                    continue;
                }

                var bounds = renderer.bounds.size;
                if (Mathf.Max(bounds.x, bounds.z) < 20f)
                {
                    continue;
                }

                return renderer;
            }

            return null;
        }

        private void CreateFallbackPitch()
        {
            if (fallbackPitchRoot == null)
            {
                var pitch = GameObject.CreatePrimitive(PrimitiveType.Plane);
                pitch.name = "GTEX_Fallback_GreenPitch";
                pitch.transform.SetParent(transform, false);
                pitch.transform.position = Vector3.zero;
                pitch.transform.localRotation = Quaternion.identity;
                fallbackPitchRoot = pitch.transform;

                var shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
                var grassMaterial = shader != null ? new Material(shader) : null;
                if (grassMaterial != null)
                {
                    if (grassMaterial.HasProperty("_BaseColor"))
                    {
                        grassMaterial.SetColor("_BaseColor", grassColor);
                    }

                    if (grassMaterial.HasProperty("_Color"))
                    {
                        grassMaterial.SetColor("_Color", grassColor);
                    }

                    if (grassMaterial.HasProperty("_Smoothness"))
                    {
                        grassMaterial.SetFloat("_Smoothness", 0f);
                    }
                }

                activePitchRenderer = pitch.GetComponent<Renderer>();
                if (activePitchRenderer != null && grassMaterial != null)
                {
                    activePitchRenderer.sharedMaterial = grassMaterial;
                    activePitchRenderer.enabled = true;
                }

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

                CreateFallbackLines();
            }

            fallbackPitchRoot.position = Vector3.zero;
            fallbackPitchRoot.localScale = new Vector3(pitchSize.x / 10f, 1f, pitchSize.y / 10f);
        }

        private void CreateFallbackLines()
        {
            CreateLine(
                "GTEX_Fallback_PitchBoundary",
                new[]
                {
                    new Vector3(-pitchSize.x * 0.5f, 0.03f, -pitchSize.y * 0.5f),
                    new Vector3(-pitchSize.x * 0.5f, 0.03f, pitchSize.y * 0.5f),
                    new Vector3(pitchSize.x * 0.5f, 0.03f, pitchSize.y * 0.5f),
                    new Vector3(pitchSize.x * 0.5f, 0.03f, -pitchSize.y * 0.5f),
                    new Vector3(-pitchSize.x * 0.5f, 0.03f, -pitchSize.y * 0.5f),
                });

            CreateLine(
                "GTEX_Fallback_HalfwayLine",
                new[]
                {
                    new Vector3(0f, 0.03f, -pitchSize.y * 0.5f),
                    new Vector3(0f, 0.03f, pitchSize.y * 0.5f),
                });
        }

        private void CreateLine(string name, IReadOnlyList<Vector3> points)
        {
            if (fallbackPitchRoot == null || points == null || points.Count == 0)
            {
                return;
            }

            var lineObject = new GameObject(name);
            lineObject.transform.SetParent(fallbackPitchRoot, false);
            var line = lineObject.AddComponent<LineRenderer>();
            line.loop = false;
            line.useWorldSpace = false;
            line.positionCount = points.Count;
            for (var index = 0; index < points.Count; index += 1)
            {
                line.SetPosition(index, points[index]);
            }

            line.startWidth = 0.14f;
            line.endWidth = 0.14f;
            line.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            line.receiveShadows = false;

            var shader = Shader.Find("Sprites/Default") ?? Shader.Find("Unlit/Color") ?? Shader.Find("Universal Render Pipeline/Unlit");
            if (shader != null)
            {
                var material = new Material(shader);
                if (material.HasProperty("_Color"))
                {
                    material.SetColor("_Color", Color.white);
                }

                if (material.HasProperty("_BaseColor"))
                {
                    material.SetColor("_BaseColor", Color.white);
                }

                line.sharedMaterial = material;
            }

            line.startColor = Color.white;
            line.endColor = Color.white;
        }
    }
}
