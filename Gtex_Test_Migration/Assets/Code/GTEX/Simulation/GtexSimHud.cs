using UnityEngine;

namespace FStudio.GTEX.Simulation
{
    public sealed class GtexSimHud : MonoBehaviour
    {
        [SerializeField] private bool showHud = true;
        [SerializeField] private bool showOnlyInSimulationMode = true;
        [SerializeField] private Vector2 origin = new Vector2(18f, 18f);
        [SerializeField] private Vector2 size = new Vector2(380f, 320f);

        private GtexSimRuntimeHost host;
        private GtexSimRenderer simRenderer;
        private GtexSimCrowdController crowdController;
        private GtexSimUiBridge uiBridge;
        private GUIStyle panelStyle;
        private GUIStyle titleStyle;
        private GUIStyle lineStyle;
        private Texture2D backgroundTexture;

        public void Bind(
            GtexSimRuntimeHost runtimeHost,
            GtexSimRenderer renderer,
            GtexSimCrowdController crowd,
            GtexSimUiBridge bridge)
        {
            host = runtimeHost;
            simRenderer = renderer;
            crowdController = crowd;
            uiBridge = bridge;
        }

        private void OnGUI()
        {
            if (!showHud || Application.isBatchMode)
            {
                return;
            }

            if (showOnlyInSimulationMode && (host == null || host.Engine == null))
            {
                return;
            }

            EnsureStyles();

            var rect = new Rect(origin.x, origin.y, size.x, size.y);
            GUI.Box(rect, GUIContent.none, panelStyle);

            GUILayout.BeginArea(rect);
            GUILayout.Label("GTEX Local Simulation", titleStyle);
            DrawLine(host != null ? host.HomeDisplayName : "Home", host != null ? host.AwayDisplayName : "Away");
            DrawLine("Score", uiBridge != null ? uiBridge.Scoreline : "0 - 0");
            DrawLine("State", uiBridge != null ? uiBridge.LastState.ToString() : "Idle");
            DrawLine(
                "Minute",
                host != null && host.Engine != null
                    ? host.Engine.Clock.CurrentMatchMinute.ToString("0.0")
                    : "0.0");
            DrawLine("Last Event", uiBridge != null ? uiBridge.LastEventSummary : "Waiting for kickoff");
            DrawLine("Banner", simRenderer != null ? simRenderer.ActiveBannerText : "-");
            DrawLine("Crowd", crowdController != null ? crowdController.MoodLabel : "Muted");
            DrawLine(
                "Crowd Energy",
                crowdController != null ? crowdController.CrowdEnergy.ToString("0.00") : "0.00");
            GUILayout.Space(8f);
            GUILayout.Label("Recent Feed", titleStyle);
            DrawRecentFeed();
            GUILayout.EndArea();
        }

        private void DrawLine(string label, string value)
        {
            GUILayout.Label(label + ": " + value, lineStyle);
        }

        private void DrawRecentFeed()
        {
            if (simRenderer == null || simRenderer.RecentFeedEntries == null || simRenderer.RecentFeedEntries.Count == 0)
            {
                GUILayout.Label("No moments yet.", lineStyle);
                return;
            }

            for (var index = simRenderer.RecentFeedEntries.Count - 1; index >= 0; index -= 1)
            {
                GUILayout.Label("- " + simRenderer.RecentFeedEntries[index], lineStyle);
            }
        }

        private void EnsureStyles()
        {
            if (panelStyle != null)
            {
                return;
            }

            backgroundTexture = new Texture2D(1, 1, TextureFormat.RGBA32, false);
            backgroundTexture.SetPixel(0, 0, new Color(0.07f, 0.11f, 0.14f, 0.9f));
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
                    textColor = new Color(0.95f, 0.98f, 0.99f)
                }
            };

            lineStyle = new GUIStyle(GUI.skin.label)
            {
                fontSize = 12,
                wordWrap = true,
                normal =
                {
                    textColor = new Color(0.83f, 0.89f, 0.92f)
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
