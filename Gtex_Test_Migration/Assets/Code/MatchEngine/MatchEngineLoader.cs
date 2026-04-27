using FStudio.Events;
using FStudio.Graphics;
using FStudio.Loaders;
using FStudio.Graphics.TimeOfDay;
using FStudio.UI;
using FStudio.UI.Events;
using FStudio.UI.GamepadInput;
using FStudio.UI.MatchThemes;
using FStudio.Utilities;
using Shared.Responses;
using FStudio.Data;
using System.Threading.Tasks;
using UnityEngine;
using FStudio.MatchEngine.Graphics.GraphicsModes;
using FStudio.Graphics.Cameras;
using FStudio.GTEX;
using FStudio.GTEX.Core;
using FStudio.UI.MatchThemes.MatchEvents;
using FStudio.MatchEngine.Enums;
using FStudio.Database;

namespace FStudio.MatchEngine {
    public enum OriginalVisualEnvironmentMode {
        EssentialOnly,
        FullOriginalStadium,
        None
    }

    public class MatchEngineLoader : SceneObjectSingleton<MatchEngineLoader> {
        [SerializeField] private SingleAddressableLoader loader;
        [SerializeField] private OriginalVisualEnvironmentMode originalVisualEnvironmentMode = OriginalVisualEnvironmentMode.EssentialOnly;

        private bool isLoading;
        private bool isLoaded;

        private const float Live3DKitContrastMinimumScore = 1.4f;

        public static async Task CreateMatch(MatchCreateRequest matchData) {
            // close all UI.
            EventManager.Trigger(new CloseAllPanelsEvent());

            // clear all snap history.
            SnapManager.Clear();

            // load the match UI
            await UILoader.Current.MatchUILoader.Load();

            // unload the general UI
            UILoader.Current.GeneralUILoader.Unload();

            var upcomingMatchEvent = new UpcomingMatchEvent(matchData);

            EventManager.Trigger(upcomingMatchEvent);
        }

        public async Task StartMatchEngine (
            UpcomingMatchEvent matchEvent,
            bool homeKit,
            bool awayKit,
            GtexMatchConfig gtexConfig = null) {

            if (isLoading) {
                return;
            }

            if (isLoaded) {
                // unload.
                await UnloadMatch();
            }

            ResolveKitSelections(matchEvent, ref homeKit, ref awayKit);
            EnsureLive3DKitContrast(matchEvent, homeKit, awayKit);

            // match kits.
            EventManager.Trigger(
                new MatchKitsEvent(
                homeKit ? matchEvent.details.homeTeam.AwayKit : matchEvent.details.homeTeam.HomeKit,
                awayKit ? matchEvent.details.awayTeam.AwayKit : matchEvent.details.awayTeam.HomeKit));
            //

            isLoading = true;

            // close all UI.
            EventManager.Trigger(new CloseAllPanelsEvent());

            // Big loading.
            EventManager.Trigger(new BigLoadingEvent());

            var template = GraphicLoaders.Current;
            var resolvedGtexConfig = gtexConfig ?? GtexMatchConfigLoader.Load();

            // load stadium scene
            StadiumType stadium = StadiumType.SmallStadium;
            if (GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime())
            {
                await LoadOriginalVisualEnvironment(template, stadium);
            }
            else
            {
                await template.stadiumLoader.LoadStadium(stadium);
            }
            // 

            await loader.Load(); // load match prefab.

            if (TimeOfDaySystem.Current != null) {
                // load time of day.
                await TimeOfDaySystem.Current.LoadTemplate(matchEvent.details.dayTime);
            }

            MainCamera.Current.Camera.cullingMask = template.renderLayer;

            // skybox mode on.
            MainCamera.Current.Camera.clearFlags = CameraClearFlags.Skybox;

            Debug.Log("Creating core match...");

            await MatchManager.CreateMatch(
                new MatchManager.MatchDetails(
                    matchEvent,
                    homeKit,
                    awayKit)
                );

            Debug.Log("Loading ball...");

            // load random ball.
            await template.ballLoader.LoadRandomBall();

            var shouldUseAtmosphereUpgrade =
                resolvedGtexConfig != null &&
                !resolvedGtexConfig.ShouldPreserveOriginalScenePresentation &&
                (resolvedGtexConfig.enableStadiumUpgrade ||
                 resolvedGtexConfig.showCrowd ||
                 resolvedGtexConfig.showBroadcastScaffolding);

            if (shouldUseAtmosphereUpgrade) {
                GtexStadiumAtmosphere.InstallOrRefresh(matchEvent, resolvedGtexConfig);
            } else {
                GtexStadiumAtmosphere.RemoveIfPresent();
            }
            
            isLoaded = true;
            isLoading = false;

            Debug.Log("Done...");

            // close loading.
            EventManager.Trigger<BigLoadingEvent>(null);
        }

        private async Task LoadOriginalVisualEnvironment(GraphicLoaders template, StadiumType stadium)
        {
            switch (originalVisualEnvironmentMode)
            {
                case OriginalVisualEnvironmentMode.None:
                    Debug.Log("[GTEX OriginalVisualRuntime] Original visual environment skipped. Fallback pitch/camera will be used if needed.");
                    break;
                case OriginalVisualEnvironmentMode.EssentialOnly:
                case OriginalVisualEnvironmentMode.FullOriginalStadium:
                    Debug.Log("[GTEX OriginalVisualRuntime] Loading original visual environment: " + originalVisualEnvironmentMode + " via " + stadium + ".");
                    await template.stadiumLoader.LoadStadium(stadium);
                    SanitizeOriginalVisualEnvironment();
                    break;
            }
        }

        private void SanitizeOriginalVisualEnvironment()
        {
            if (!GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime())
            {
                return;
            }

            Debug.Log("[GTEX OriginalVisualRuntime] Sanitizing original visual environment.");

            DisableIfNameContains("DefaultScene");
            DisableIfNameContains("MainMenu");
            DisableIfNameContains("ReturnToMenu");
            DisableIfNameContains("SceneTransition");
            DisableIfNameContains("PauseMenu");

            EnsureRenderersEnabled("Pitch");
            EnsureRenderersEnabled("Grass");
            EnsureRenderersEnabled("Field");
            EnsureRenderersEnabled("Line");
            EnsureRenderersEnabled("Goal");
            EnsureLightsEnabled();
        }

        private static void DisableIfNameContains(string token)
        {
            if (string.IsNullOrWhiteSpace(token))
            {
                return;
            }

            var behaviours = FindObjectsByType<Behaviour>(FindObjectsInactive.Include, FindObjectsSortMode.None);
            foreach (var behaviour in behaviours)
            {
                if (behaviour == null)
                {
                    continue;
                }

                var objectName = behaviour.name ?? string.Empty;
                var typeName = behaviour.GetType().Name ?? string.Empty;
                if (objectName.IndexOf(token, System.StringComparison.OrdinalIgnoreCase) < 0 &&
                    typeName.IndexOf(token, System.StringComparison.OrdinalIgnoreCase) < 0)
                {
                    continue;
                }

                if (behaviour is Camera ||
                    behaviour is Light)
                {
                    continue;
                }

                behaviour.enabled = false;
            }

            var transforms = FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None);
            foreach (var transform in transforms)
            {
                if (transform == null || transform == MatchEngineLoader.Current?.transform)
                {
                    continue;
                }

                var name = transform.name ?? string.Empty;
                if (name.IndexOf(token, System.StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    transform.gameObject.SetActive(false);
                }
            }
        }

        private static void EnsureRenderersEnabled(string token)
        {
            if (string.IsNullOrWhiteSpace(token))
            {
                return;
            }

            var renderers = FindObjectsByType<Renderer>(FindObjectsInactive.Include, FindObjectsSortMode.None);
            foreach (var renderer in renderers)
            {
                if (renderer == null)
                {
                    continue;
                }

                var name = renderer.name ?? string.Empty;
                if (name.IndexOf(token, System.StringComparison.OrdinalIgnoreCase) < 0)
                {
                    continue;
                }

                renderer.gameObject.SetActive(true);
                renderer.enabled = true;
            }
        }

        private static void EnsureLightsEnabled()
        {
            var lights = FindObjectsByType<Light>(FindObjectsInactive.Include, FindObjectsSortMode.None);
            foreach (var light in lights)
            {
                if (light == null)
                {
                    continue;
                }

                light.gameObject.SetActive(true);
                light.enabled = true;
                light.intensity = Mathf.Max(light.intensity, light.type == LightType.Directional ? 1.1f : 0.35f);
            }
        }

        private static void ResolveKitSelections(UpcomingMatchEvent matchEvent, ref bool homeKit, ref bool awayKit)
        {
            if (matchEvent == null)
            {
                return;
            }

            var homePrimary = matchEvent.details.homeTeam != null ? matchEvent.details.homeTeam.HomeKit : null;
            var homeAlternate = matchEvent.details.homeTeam != null ? matchEvent.details.homeTeam.AwayKit : null;
            var awayPrimary = matchEvent.details.awayTeam != null ? matchEvent.details.awayTeam.HomeKit : null;
            var awayAlternate = matchEvent.details.awayTeam != null ? matchEvent.details.awayTeam.AwayKit : null;
            if (homePrimary == null || awayPrimary == null)
            {
                return;
            }

            if (homeKit || awayKit)
            {
                return;
            }

            var baselineScore = ScoreKitPairForLive3D(homePrimary, awayPrimary);
            var baselineClash = KitsVisuallyClash(homePrimary, awayPrimary);
            var bestScore = baselineScore;
            var bestHomeAlternate = false;
            var bestAwayAlternate = false;

            EvaluateKitPairForLive3D(homePrimary, false, awayPrimary, false, ref bestScore, ref bestHomeAlternate, ref bestAwayAlternate);
            EvaluateKitPairForLive3D(homeAlternate, true, awayPrimary, false, ref bestScore, ref bestHomeAlternate, ref bestAwayAlternate);
            EvaluateKitPairForLive3D(homePrimary, false, awayAlternate, true, ref bestScore, ref bestHomeAlternate, ref bestAwayAlternate);
            EvaluateKitPairForLive3D(homeAlternate, true, awayAlternate, true, ref bestScore, ref bestHomeAlternate, ref bestAwayAlternate);

            var improvement = bestScore - baselineScore;
            if ((baselineClash || improvement >= 0.18f) &&
                (bestHomeAlternate != homeKit || bestAwayAlternate != awayKit))
            {
                homeKit = bestHomeAlternate;
                awayKit = bestAwayAlternate;
                Debug.Log(
                    "[GTEX] Auto-selected the highest-contrast live 3D kit pair. " +
                    "homeAlternate=" + bestHomeAlternate +
                    " awayAlternate=" + bestAwayAlternate +
                    " baselineScore=" + baselineScore.ToString("F2") +
                    " bestScore=" + bestScore.ToString("F2"));
            }
        }

        private static void EnsureLive3DKitContrast(UpcomingMatchEvent matchEvent, bool homeKit, bool awayKit)
        {
            if (matchEvent == null ||
                matchEvent.details.homeTeam == null ||
                matchEvent.details.awayTeam == null)
            {
                return;
            }

            var selectedHomeKit = ResolveSelectedKit(matchEvent.details.homeTeam, homeKit);
            var selectedAwayKit = ResolveSelectedKit(matchEvent.details.awayTeam, awayKit);
            if (selectedHomeKit == null || selectedAwayKit == null)
            {
                return;
            }

            var selectedScore = ScoreKitPairForLive3D(selectedHomeKit, selectedAwayKit);
            var selectedTextureClash = !KitsUseDistinctMaterials(selectedHomeKit, selectedAwayKit);
            if (!selectedTextureClash &&
                selectedScore >= Live3DKitContrastMinimumScore &&
                !KitsVisuallyClash(selectedHomeKit, selectedAwayKit))
            {
                return;
            }

            var adaptedAwayKit = CreateLive3DContrastKit(selectedAwayKit, selectedHomeKit);
            ApplySelectedKit(matchEvent.details.awayTeam, awayKit, adaptedAwayKit);

            Debug.Log(
                "[GTEX] Applied live 3D away-kit contrast fallback. " +
                "selectedScore=" + selectedScore.ToString("F2") +
                " textureClash=" + selectedTextureClash +
                " awayAlternate=" + awayKit);
        }

        private static KitEntry ResolveSelectedKit(TeamEntry team, bool useAlternate)
        {
            if (team == null)
            {
                return null;
            }

            return useAlternate ? team.AwayKit : team.HomeKit;
        }

        private static void ApplySelectedKit(TeamEntry team, bool useAlternate, KitEntry kit)
        {
            if (team == null || kit == null)
            {
                return;
            }

            if (useAlternate)
            {
                team.AwayKit = kit;
            }
            else
            {
                team.HomeKit = kit;
            }
        }

        private static KitEntry CreateLive3DContrastKit(KitEntry sourceKit, KitEntry opponentKit)
        {
            var adaptedKit = ScriptableObject.CreateInstance<KitEntry>();
            adaptedKit.name = sourceKit != null ? sourceKit.name + " GTEX Live Contrast" : "GTEX Live Contrast Kit";

            if (sourceKit != null)
            {
                adaptedKit.PreviewTexture = sourceKit.PreviewTexture;
                adaptedKit.KitMaterial = sourceKit.KitMaterial;
                adaptedKit.TextColor = sourceKit.TextColor;
                adaptedKit.GKKitMaterial = sourceKit.GKKitMaterial;
                adaptedKit.GKTextColor = sourceKit.GKTextColor;
            }

            var opponentBrightness = opponentKit != null ? ResolvePerceivedBrightness(opponentKit.Color1) : 0.35f;
            if (opponentBrightness < 0.55f)
            {
                adaptedKit.Color1 = new Color(0.96f, 0.96f, 0.9f, 1f);
                adaptedKit.Color2 = new Color(0.02f, 0.74f, 1f, 1f);
                adaptedKit.TextColor = Color.black;
                adaptedKit.GKColor1 = new Color(1f, 0.58f, 0.04f, 1f);
                adaptedKit.GKColor2 = new Color(0.05f, 0.05f, 0.05f, 1f);
                adaptedKit.GKTextColor = Color.black;
                return adaptedKit;
            }

            adaptedKit.Color1 = new Color(0.02f, 0.04f, 0.1f, 1f);
            adaptedKit.Color2 = new Color(1f, 0.58f, 0.04f, 1f);
            adaptedKit.TextColor = Color.white;
            adaptedKit.GKColor1 = new Color(0.02f, 0.74f, 1f, 1f);
            adaptedKit.GKColor2 = new Color(0.05f, 0.05f, 0.05f, 1f);
            adaptedKit.GKTextColor = Color.white;
            return adaptedKit;
        }

        private static bool KitsVisuallyClash(KitEntry homeKit, KitEntry awayKit)
        {
            if (homeKit == null || awayKit == null)
            {
                return false;
            }

            var textureClash =
                ReferenceEquals(homeKit.KitMaterial, awayKit.KitMaterial) ||
                (homeKit.KitMaterial != null &&
                 awayKit.KitMaterial != null &&
                 string.Equals(homeKit.KitMaterial.name, awayKit.KitMaterial.name, System.StringComparison.Ordinal));

            var primaryDistance = ColorDistance(homeKit.Color1, awayKit.Color1);
            var secondaryDistance = ColorDistance(homeKit.Color2, awayKit.Color2);
            var severeColorClash = primaryDistance < 0.5f && secondaryDistance < 0.46f;
            var moderateTextureClash = textureClash && primaryDistance < 0.72f;
            return severeColorClash || moderateTextureClash;
        }

        private static float ScoreKitContrast(KitEntry homeKit, KitEntry awayKit)
        {
            if (homeKit == null || awayKit == null)
            {
                return 0f;
            }

            return ColorDistance(homeKit.Color1, awayKit.Color1) +
                    ColorDistance(homeKit.Color2, awayKit.Color2) * 0.5f +
                    ColorDistance(homeKit.GKColor1, awayKit.GKColor1) * 0.25f;
        }

        private static void EvaluateKitPairForLive3D(
            KitEntry homeKit,
            bool useHomeAlternate,
            KitEntry awayKit,
            bool useAwayAlternate,
            ref float bestScore,
            ref bool bestHomeAlternate,
            ref bool bestAwayAlternate)
        {
            if (homeKit == null || awayKit == null)
            {
                return;
            }

            var score = ScoreKitPairForLive3D(homeKit, awayKit);
            if (score <= bestScore)
            {
                return;
            }

            bestScore = score;
            bestHomeAlternate = useHomeAlternate;
            bestAwayAlternate = useAwayAlternate;
        }

        private static float ScoreKitPairForLive3D(KitEntry homeKit, KitEntry awayKit)
        {
            if (homeKit == null || awayKit == null)
            {
                return float.MinValue;
            }

            var primaryDistance = ColorDistance(homeKit.Color1, awayKit.Color1);
            var secondaryDistance = ColorDistance(homeKit.Color2, awayKit.Color2);
            var brightnessDistance =
                Mathf.Abs(ResolvePerceivedBrightness(homeKit.Color1) - ResolvePerceivedBrightness(awayKit.Color1)) +
                Mathf.Abs(ResolvePerceivedBrightness(homeKit.Color2) - ResolvePerceivedBrightness(awayKit.Color2));
            var textureBonus = KitsUseDistinctMaterials(homeKit, awayKit) ? 0.35f : -0.55f;
            var clashPenalty = KitsVisuallyClash(homeKit, awayKit) ? 2.5f : 0f;

            return
                primaryDistance * 1.5f +
                secondaryDistance * 0.95f +
                brightnessDistance * 0.8f +
                ColorDistance(homeKit.GKColor1, awayKit.GKColor1) * 0.2f +
                textureBonus -
                clashPenalty;
        }

        private static bool KitsUseDistinctMaterials(KitEntry homeKit, KitEntry awayKit)
        {
            if (homeKit == null || awayKit == null)
            {
                return false;
            }

            if (ReferenceEquals(homeKit.KitMaterial, awayKit.KitMaterial))
            {
                return false;
            }

            if (homeKit.KitMaterial == null || awayKit.KitMaterial == null)
            {
                return true;
            }

            return !string.Equals(
                homeKit.KitMaterial.name,
                awayKit.KitMaterial.name,
                System.StringComparison.Ordinal);
        }

        private static float ResolvePerceivedBrightness(Color color)
        {
            return color.r * 0.299f + color.g * 0.587f + color.b * 0.114f;
        }

        private static float ColorDistance(Color left, Color right)
        {
            var dr = left.r - right.r;
            var dg = left.g - right.g;
            var db = left.b - right.b;
            return Mathf.Sqrt(dr * dr + dg * dg + db * db);
        }

        public async Task UnloadMatch () {
            if (MatchManager.Current == null) {
                Debug.LogWarning($"Match is not loaded to unload.");
                return;
            }

            // skybox mode off.
            MainCamera.Current.Camera.clearFlags = CameraClearFlags.SolidColor;

            // close all UI.
            EventManager.Trigger(new CloseAllPanelsEvent());

            var template = GraphicLoaders.Current;

            // unload ball & stadium.
            template.ballLoader.UnloadBall();
            await template.stadiumLoader.Unload();
            // 

            SnapManager.Clear();

            UILoader.Current.MatchUILoader.Unload();

            MatchManager.Current.ClearMatch(); // clear field.

            loader.Unload(); // clear match manager prefab.

            await UILoader.Current.GeneralUILoader.Load();

            GameInput.SwitchToUI();

            isLoaded = false;
        }
    }
}
