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
using FStudio.UI.MatchThemes.MatchEvents;
using FStudio.MatchEngine.Enums;
using FStudio.Database;

namespace FStudio.MatchEngine {
    public class MatchEngineLoader : SceneObjectSingleton<MatchEngineLoader> {
        [SerializeField] private SingleAddressableLoader loader;

        private bool isLoading;
        private bool isLoaded;

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

            // load stadium scene
            StadiumType stadium = StadiumType.SmallStadium;
            await template.stadiumLoader.LoadStadium(stadium);
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

            GtexStadiumAtmosphere.InstallOrRefresh(matchEvent, gtexConfig ?? GtexMatchConfigLoader.Load());
            
            isLoaded = true;
            isLoading = false;

            Debug.Log("Done...");

            // close loading.
            EventManager.Trigger<BigLoadingEvent>(null);
        }

        private static void ResolveKitSelections(UpcomingMatchEvent matchEvent, ref bool homeKit, ref bool awayKit)
        {
            if (matchEvent == null)
            {
                return;
            }

            var homePrimary = matchEvent.details.homeTeam != null ? matchEvent.details.homeTeam.HomeKit : null;
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

            if (!KitsVisuallyClash(homePrimary, awayPrimary))
            {
                return;
            }

            if (awayAlternate != null && ScoreKitContrast(homePrimary, awayAlternate) > ScoreKitContrast(homePrimary, awayPrimary))
            {
                awayKit = true;
                Debug.Log("[GTEX] Auto-selected away alternate kit to avoid a live 3D kit clash.");
                return;
            }
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
