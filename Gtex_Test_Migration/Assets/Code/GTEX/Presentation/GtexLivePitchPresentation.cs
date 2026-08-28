using FStudio.GTEX.Core;
using FStudio.GTEX.Playback;
using FStudio.MatchEngine;
using UnityEngine;

namespace FStudio.GTEX.Presentation
{
    /// <summary>
    /// Deterministic production pitch presenter for GTEX LivePlayback.
    /// Avoids textured pitch underlays whose UV/scale can duplicate or stretch
    /// markings. The field and markings are generated directly in GTEX pitch space.
    /// </summary>
    [DefaultExecutionOrder(9990)]
    public sealed class GtexLivePitchPresentation : MonoBehaviour
    {
        private const string GeneratedRootName = "GTEX Live Pitch Presentation";
        private const string LegacyFieldName = "ExtrudedField";
        private const string ExternalUnderlayName = "GTEX_ExternalPlaybackFieldUnderlay";

        private static GtexLivePitchPresentation instance;
        private GameObject generatedRoot;
        private MeshRenderer pitchRenderer;
        private MeshRenderer linesRenderer;
        private Material pitchMaterial;
        private Material linesMaterial;
        private Vector3 lastCenter;
        private float lastLength = -1f;
        private float lastWidth = -1f;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Install()
        {
            if (instance != null)
            {
                return;
            }

            var host = new GameObject(GeneratedRootName + " Host");
            DontDestroyOnLoad(host);
            instance = host.AddComponent<GtexLivePitchPresentation>();
        }

        private void LateUpdate()
        {
            if (GtexRuntimeState.ActiveMode != GtexRuntimeMode.LivePlayback)
            {
                return;
            }

            var manager = MatchManager.Current;
            var pitch = manager != null ? manager.ExternalPlaybackPitchSpace : null;
            if (pitch == null)
            {
                return;
            }

            EnsurePresentation(pitch);
            HideLegacyPitchRenderers();
        }

        private void EnsurePresentation(GtexPitchSpace pitch)
        {
            if (generatedRoot == null)
            {
                generatedRoot = new GameObject(GeneratedRootName);
                generatedRoot.transform.SetParent(transform, false);
                CreateMeshes();
            }

            if (Mathf.Abs(pitch.Length - lastLength) > 0.01f ||
                Mathf.Abs(pitch.Width - lastWidth) > 0.01f ||
                Vector3.Distance(pitch.Center, lastCenter) > 0.01f)
            {
                BuildPitch(pitch);
                lastLength = pitch.Length;
                lastWidth = pitch.Width;
                lastCenter = pitch.Center;
            }
        }

        private void CreateMeshes()
        {
            var pitchObject = new GameObject("Pitch Surface");
            pitchObject.transform.SetParent(generatedRoot.transform, false);
            pitchRenderer = pitchObject.AddComponent<MeshRenderer>();
            pitchRenderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            pitchRenderer.receiveShadows = false;
            pitchRenderer.material = CreatePitchMaterial();
            pitchMaterial = pitchRenderer.sharedMaterial;

            var linesObject = new GameObject("Pitch Markings");
            linesObject.transform.SetParent(generatedRoot.transform, false);
            linesRenderer = linesObject.AddComponent<MeshRenderer>();
            linesRenderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            linesRenderer.receiveShadows = false;
            linesRenderer.material = CreateLinesMaterial();
            linesMaterial = linesRenderer.sharedMaterial;
        }

        private Material CreatePitchMaterial()
        {
            var shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
            var material = new Material(shader);
            material.name = "GTEX Live Pitch Material";
            if (material.HasProperty("_BaseColor")) material.SetColor("_BaseColor", new Color(0.10f, 0.34f, 0.12f, 1f));
            if (material.HasProperty("_Color")) material.SetColor("_Color", new Color(0.10f, 0.34f, 0.12f, 1f));
            if (material.HasProperty("_Smoothness")) material.SetFloat("_Smoothness", 0f);
            if (material.HasProperty("_Glossiness")) material.SetFloat("_Glossiness", 0f);
            return material;
        }

        private Material CreateLinesMaterial()
        {
            var shader = Shader.Find("Universal Render Pipeline/Unlit") ?? Shader.Find("Unlit/Color");
            var material = new Material(shader);
            material.name = "GTEX Live Pitch Lines Material";
            if (material.HasProperty("_BaseColor")) material.SetColor("_BaseColor", Color.white);
            if (material.HasProperty("_Color")) material.SetColor("_Color", Color.white);
            material.renderQueue = 3000;
            return material;
        }

        private void BuildPitch(GtexPitchSpace pitch)
        {
            var y = pitch.GrassY + 0.0125f;
            var minX = pitch.MinX;
            var maxX = pitch.MaxX;
            var minZ = pitch.MinZ;
            var maxZ = pitch.MaxZ;

            var pitchMesh = new Mesh { name = "GTEX Live Pitch Surface Mesh" };
            pitchMesh.vertices = new[]
            {
                new Vector3(minX, y, minZ),
                new Vector3(maxX, y, minZ),
                new Vector3(maxX, y, maxZ),
                new Vector3(minX, y, maxZ)
            };
            pitchMesh.triangles = new[] { 0, 2, 1, 0, 3, 2 };
            pitchMesh.RecalculateBounds();
            pitchMesh.UploadMeshData(false);
            pitchRenderer.sharedMesh = pitchMesh;

            var lineMesh = BuildLineMesh(pitch, y + 0.008f);
            linesRenderer.sharedMesh = lineMesh;
        }

        private static Mesh BuildLineMesh(GtexPitchSpace pitch, float y)
        {
            var vertices = new System.Collections.Generic.List<Vector3>();
            var triangles = new System.Collections.Generic.List<int>();
            const float width = 0.12f;

            void AddLine(Vector3 a, Vector3 b)
            {
                var dir = (b - a);
                dir.y = 0f;
                if (dir.sqrMagnitude < 0.0001f) return;
                dir.Normalize();
                var normal = new Vector3(-dir.z, 0f, dir.x) * width;
                var start = vertices.Count;
                vertices.Add(a - normal);
                vertices.Add(a + normal);
                vertices.Add(b + normal);
                vertices.Add(b - normal);
                triangles.Add(start);
                triangles.Add(start + 1);
                triangles.Add(start + 2);
                triangles.Add(start);
                triangles.Add(start + 2);
                triangles.Add(start + 3);
            }

            void AddCircle(Vector3 center, float radius, int segments)
            {
                var previous = center + Vector3.forward * radius;
                for (var i = 1; i <= segments; i++)
                {
                    var angle = (Mathf.PI * 2f * i) / segments;
                    var next = center + new Vector3(Mathf.Sin(angle) * radius, 0f, Mathf.Cos(angle) * radius);
                    AddLine(previous, next);
                    previous = next;
                }
            }

            var minX = pitch.MinX;
            var maxX = pitch.MaxX;
            var minZ = pitch.MinZ;
            var maxZ = pitch.MaxZ;
            var midX = pitch.Center.x;
            var midZ = pitch.Center.z;

            AddLine(new Vector3(minX, y, minZ), new Vector3(maxX, y, minZ));
            AddLine(new Vector3(maxX, y, minZ), new Vector3(maxX, y, maxZ));
            AddLine(new Vector3(maxX, y, maxZ), new Vector3(minX, y, maxZ));
            AddLine(new Vector3(minX, y, maxZ), new Vector3(minX, y, minZ));
            AddLine(new Vector3(midX, y, minZ), new Vector3(midX, y, maxZ));
            AddCircle(new Vector3(midX, y, midZ), 9.15f, 64);
            AddCircle(new Vector3(midX, y, midZ), 0.18f, 16);

            var penaltyDepth = Mathf.Min(16.5f, pitch.Length * 0.16f);
            var penaltyHalf = Mathf.Min(20.16f, pitch.Width * 0.30f);
            var sixDepth = Mathf.Min(5.5f, pitch.Length * 0.055f);
            var sixHalf = Mathf.Min(9.16f, pitch.Width * 0.135f);
            var boxY0 = midZ - penaltyHalf;
            var boxY1 = midZ + penaltyHalf;
            var sixY0 = midZ - sixHalf;
            var sixY1 = midZ + sixHalf;

            AddLine(new Vector3(minX, y, boxY0), new Vector3(minX + penaltyDepth, y, boxY0));
            AddLine(new Vector3(minX + penaltyDepth, y, boxY0), new Vector3(minX + penaltyDepth, y, boxY1));
            AddLine(new Vector3(minX + penaltyDepth, y, boxY1), new Vector3(minX, y, boxY1));
            AddLine(new Vector3(maxX, y, boxY0), new Vector3(maxX - penaltyDepth, y, boxY0));
            AddLine(new Vector3(maxX - penaltyDepth, y, boxY0), new Vector3(maxX - penaltyDepth, y, boxY1));
            AddLine(new Vector3(maxX - penaltyDepth, y, boxY1), new Vector3(maxX, y, boxY1));

            AddLine(new Vector3(minX, y, sixY0), new Vector3(minX + sixDepth, y, sixY0));
            AddLine(new Vector3(minX + sixDepth, y, sixY0), new Vector3(minX + sixDepth, y, sixY1));
            AddLine(new Vector3(minX + sixDepth, y, sixY1), new Vector3(minX, y, sixY1));
            AddLine(new Vector3(maxX, y, sixY0), new Vector3(maxX - sixDepth, y, sixY0));
            AddLine(new Vector3(maxX - sixDepth, y, sixY0), new Vector3(maxX - sixDepth, y, sixY1));
            AddLine(new Vector3(maxX - sixDepth, y, sixY1), new Vector3(maxX, y, sixY1));

            var mesh = new Mesh { name = "GTEX Live Pitch Markings Mesh" };
            mesh.SetVertices(vertices);
            mesh.SetTriangles(triangles, 0);
            mesh.RecalculateBounds();
            return mesh;
        }

        private static void HideLegacyPitchRenderers()
        {
            HideNamedRenderers(LegacyFieldName);
            HideNamedRenderers(ExternalUnderlayName);
        }

        private static void HideNamedRenderers(string objectName)
        {
            var transforms = FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None);
            for (var i = 0; i < transforms.Length; i++)
            {
                var transform = transforms[i];
                if (transform == null || transform.name != objectName)
                {
                    continue;
                }

                var renderers = transform.GetComponentsInChildren<Renderer>(true);
                for (var r = 0; r < renderers.Length; r++)
                {
                    if (renderers[r] != null)
                    {
                        renderers[r].enabled = false;
                    }
                }
            }
        }
    }
}
