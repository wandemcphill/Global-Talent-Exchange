using FStudio.GTEX;
using UnityEngine;

namespace FStudio.GTEX.Core
{
    public sealed class GtexLiveStartupOverlay : MonoBehaviour
    {
        [SerializeField] private Vector2 origin = new Vector2(18f, 18f);
        [SerializeField] private Vector2 size = new Vector2(460f, 230f);

        private GUIStyle panelStyle;
        private GUIStyle titleStyle;
        private GUIStyle lineStyle;
        private Texture2D backgroundTexture;
        private GtexMatchRuntime cachedRuntime;
        private float nextRuntimeLookupAt;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void EnsureInstance()
        {
            if (Application.isBatchMode || !ShouldRenderInCurrentBuild())
            {
                return;
            }

            if (Object.FindFirstObjectByType<GtexLiveStartupOverlay>() != null)
            {
                return;
            }

            var host = new GameObject("GTEX Live Startup Overlay");
            DontDestroyOnLoad(host);
            host.hideFlags = HideFlags.DontSave;
            host.AddComponent<GtexLiveStartupOverlay>();
        }

        private void OnGUI()
        {
            if (Application.isBatchMode || !ShouldRenderInCurrentBuild())
            {
                return;
            }

            var runtime = ResolveRuntime();
            var hasStartupIssue = GtexLiveStartupStatus.HasIssue;
            var hasTransportIssue =
                runtime != null &&
                !string.IsNullOrWhiteSpace(runtime.LastTransportError);

            if (!hasStartupIssue && !hasTransportIssue)
            {
                return;
            }

            EnsureStyles();

            var rect = new Rect(origin.x, origin.y, size.x, size.y);
            GUI.Box(rect, GUIContent.none, panelStyle);

            GUILayout.BeginArea(rect);
            GUILayout.Label("GTEX Live Status", titleStyle);

            if (hasStartupIssue)
            {
                DrawLine("Status", GtexLiveStartupStatus.HasBlockingIssue ? "Blocked" : "Warning");
                DrawLine("Issue", GtexLiveStartupStatus.Title);
                DrawLine("Detail", GtexLiveStartupStatus.Message);

                if (!string.IsNullOrWhiteSpace(GtexLiveStartupStatus.ActionHint))
                {
                    DrawLine("Action", GtexLiveStartupStatus.ActionHint);
                }

                if (!string.IsNullOrWhiteSpace(GtexLiveStartupStatus.SourcePath))
                {
                    DrawLine("Source", GtexLiveStartupStatus.SourcePath);
                }
            }
            else
            {
                DrawLine("Status", "Transport degraded");
                DrawLine("Source", runtime.LastTransportSource);
                DrawLine("Detail", runtime.LastTransportError);
                DrawLine("Failures", runtime.ConsecutiveTransportFailures.ToString());
                DrawLine("Clock", runtime.LastKnownClockMinute.ToString("0.0"));
                DrawLine("Score", runtime.LastKnownHomeScore + " - " + runtime.LastKnownAwayScore);
            }

            GUILayout.EndArea();
        }

        private static bool ShouldRenderInCurrentBuild()
        {
            return Application.isEditor || Debug.isDebugBuild || GtexConfig.IsDev;
        }

        private GtexMatchRuntime ResolveRuntime()
        {
            if (cachedRuntime != null)
            {
                return cachedRuntime;
            }

            if (Time.unscaledTime < nextRuntimeLookupAt)
            {
                return null;
            }

            nextRuntimeLookupAt = Time.unscaledTime + 0.5f;
            cachedRuntime = Object.FindFirstObjectByType<GtexMatchRuntime>();
            return cachedRuntime;
        }

        private void DrawLine(string label, string value)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return;
            }

            GUILayout.Label(label + ": " + value, lineStyle);
        }

        private void EnsureStyles()
        {
            if (panelStyle != null)
            {
                return;
            }

            backgroundTexture = new Texture2D(1, 1, TextureFormat.RGBA32, false);
            backgroundTexture.SetPixel(0, 0, new Color(0.18f, 0.07f, 0.08f, 0.92f));
            backgroundTexture.Apply();

            panelStyle = new GUIStyle(GUI.skin.box)
            {
                padding = new RectOffset(14, 14, 12, 12),
                normal =
                {
                    background = backgroundTexture
                }
            };

            titleStyle = new GUIStyle(GUI.skin.label)
            {
                fontSize = 16,
                fontStyle = FontStyle.Bold,
                normal =
                {
                    textColor = new Color(0.98f, 0.96f, 0.96f)
                }
            };

            lineStyle = new GUIStyle(GUI.skin.label)
            {
                fontSize = 12,
                wordWrap = true,
                normal =
                {
                    textColor = new Color(0.96f, 0.87f, 0.87f)
                }
            };
        }

        private void OnDestroy()
        {
            if (backgroundTexture != null)
            {
                Destroy(backgroundTexture);
            }
        }
    }
}
