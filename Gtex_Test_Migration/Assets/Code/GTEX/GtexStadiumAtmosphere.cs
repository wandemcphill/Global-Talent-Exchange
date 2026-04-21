using System.Collections.Generic;
using FStudio.Database;
using FStudio.GTEX.Engine;
using FStudio.UI.MatchThemes.MatchEvents;
using Shared.Responses;
using UnityEngine;
using UnityEngine.Rendering;

namespace FStudio.GTEX {
    public sealed class GtexStadiumAtmosphere : MonoBehaviour {
        private sealed class CrowdMember {
            public Transform Transform;
            public Vector3 BaseLocalPosition;
            public float Phase;
            public float BobSpeed;
            public float BobHeight;
        }

        private readonly List<CrowdMember> crowdMembers = new List<CrowdMember>();
        private readonly List<Material> runtimeMaterials = new List<Material>();
        private readonly Dictionary<Material, Material> importedMaterialMap = new Dictionary<Material, Material>();

        private const string StadiumResourcePath = "GTEX/FreeAssets/Stadium/SoccerField";
        private const string AmbientCrowdResourcePath = "GTEX/FreeAssets/Audio/mixkit_ambient_sports_crowd";
        private const string CrowdStadiumResourcePath = "GTEX/FreeAssets/Audio/mixkit_crowd_at_the_stadium";
        private const string CrowdCheerResourcePath = "GTEX/FreeAssets/Audio/mixkit_huge_crowd_cheering_victory";
        private const string RefereeWhistleResourcePath = "GTEX/FreeAssets/Audio/mixkit_police_short_whistle";

        private static readonly string[] CrowdResourcePaths = {
            "GTEX/FreeAssets/Crowd/Characters/character-a",
            "GTEX/FreeAssets/Crowd/Characters/character-b",
            "GTEX/FreeAssets/Crowd/Characters/character-c",
            "GTEX/FreeAssets/Crowd/Characters/character-d",
            "GTEX/FreeAssets/Crowd/Characters/character-e",
            "GTEX/FreeAssets/Crowd/Characters/character-f",
            "GTEX/FreeAssets/Crowd/Characters/character-g",
            "GTEX/FreeAssets/Crowd/Characters/character-h"
        };

        private GtexMatchConfig config;
        private readonly List<GameObject> crowdPrefabs = new List<GameObject>();
        private GameObject stadiumPrefab;
        private AudioClip ambienceLoopClip;
        private AudioClip ambienceAccentClip;
        private AudioClip cheerClip;
        private AudioClip whistleClip;
        private AudioSource ambienceSource;
        private AudioSource effectsSource;
        private int lastLiveSequence = -1;
        private int lastLiveHomeScore = -1;
        private int lastLiveAwayScore = -1;
        private bool hasLiveSnapshot;
        private bool finalCuePlayed;
        private float lastWhistleCueAt = -10f;
        private float lastCheerCueAt = -10f;

        public static void InstallOrRefresh(UpcomingMatchEvent matchEvent, GtexMatchConfig config = null) {
            if (matchEvent == null) {
                return;
            }

            InstallOrRefresh(matchEvent.details, config);
        }

        public static void InstallOrRefresh(MatchCreateRequest matchData, GtexMatchConfig config = null) {
            var instance = FindFirstObjectByType<GtexStadiumAtmosphere>();
            if (instance == null) {
                var host = new GameObject("GTEX Stadium Atmosphere");
                instance = host.AddComponent<GtexStadiumAtmosphere>();
            }

            instance.Apply(matchData, config);
        }

        private void OnEnable() {
            GtexMatchController.EventStream.EventPublished += HandleControllerEvent;
            GtexMatchController.LiveStateObserved += LiveStateUpdated;
        }

        private void OnDisable() {
            GtexMatchController.EventStream.EventPublished -= HandleControllerEvent;
            GtexMatchController.LiveStateObserved -= LiveStateUpdated;
        }

        private void Apply(MatchCreateRequest matchData, GtexMatchConfig config) {
            this.config = config;
            EnsureAudioSources();
            LoadResources();
            ClearRuntimeChildren();
            ApplyEnvironment(matchData.dayTime);
            BuildImportedStadium();
            BuildPerimeterBoards();
            BuildCornerFloodlights(matchData.dayTime);

            if (config == null || config.enableStadiumUpgrade) {
                BuildBroadcastScaffolding(matchData);
            }

            if (config == null || config.showCrowd) {
                BuildCrowd(matchData);
            }

            StartAmbience();
        }

        private void Update() {
            if (crowdMembers.Count == 0) {
                return;
            }

            var time = Time.unscaledTime;
            for (int index = 0; index < crowdMembers.Count; index += 1) {
                var member = crowdMembers[index];
                if (member.Transform == null) {
                    continue;
                }

                var animatedPosition = member.BaseLocalPosition;
                animatedPosition.y += Mathf.Sin(time * member.BobSpeed + member.Phase) * member.BobHeight;
                member.Transform.localPosition = animatedPosition;
            }
        }

        private void OnDestroy() {
            if (ambienceSource != null) {
                ambienceSource.Stop();
            }

            if (effectsSource != null) {
                effectsSource.Stop();
            }

            for (int index = 0; index < runtimeMaterials.Count; index += 1) {
                if (runtimeMaterials[index] != null) {
                    Destroy(runtimeMaterials[index]);
                }
            }

            runtimeMaterials.Clear();
            importedMaterialMap.Clear();
        }

        private void EnsureAudioSources() {
            if (ambienceSource == null) {
                ambienceSource = gameObject.AddComponent<AudioSource>();
                ambienceSource.playOnAwake = false;
                ambienceSource.loop = true;
                ambienceSource.spatialBlend = 0f;
                ambienceSource.volume = 0.18f;
            }

            if (effectsSource == null) {
                effectsSource = gameObject.AddComponent<AudioSource>();
                effectsSource.playOnAwake = false;
                effectsSource.loop = false;
                effectsSource.spatialBlend = 0f;
                effectsSource.volume = 0.4f;
            }
        }

        private void LoadResources() {
            if (stadiumPrefab == null) {
                stadiumPrefab = Resources.Load<GameObject>(StadiumResourcePath);
            }

            if (ambienceLoopClip == null) {
                ambienceLoopClip = Resources.Load<AudioClip>(AmbientCrowdResourcePath);
            }

            if (ambienceAccentClip == null) {
                ambienceAccentClip = Resources.Load<AudioClip>(CrowdStadiumResourcePath);
            }

            if (cheerClip == null) {
                cheerClip = Resources.Load<AudioClip>(CrowdCheerResourcePath);
            }

            if (whistleClip == null) {
                whistleClip = Resources.Load<AudioClip>(RefereeWhistleResourcePath);
            }

            if (crowdPrefabs.Count > 0) {
                return;
            }

            for (int index = 0; index < CrowdResourcePaths.Length; index += 1) {
                var prefab = Resources.Load<GameObject>(CrowdResourcePaths[index]);
                if (prefab != null) {
                    crowdPrefabs.Add(prefab);
                }
            }

            Debug.Log(
                "[GTEX Atmosphere] Resources -> stadium:" +
                (stadiumPrefab != null) +
                ", crowdPrefabs:" +
                crowdPrefabs.Count +
                ", ambience:" +
                (ambienceLoopClip != null) +
                ", accent:" +
                (ambienceAccentClip != null) +
                ", cheer:" +
                (cheerClip != null) +
                ", whistle:" +
                (whistleClip != null));
        }

        private void StartAmbience() {
            if (ambienceSource == null || ambienceLoopClip == null) {
                return;
            }

            ambienceSource.clip = ambienceLoopClip;
            ambienceSource.volume = 0.16f;

            if (!ambienceSource.isPlaying) {
                ambienceSource.Play();
            }
        }

        private void BuildImportedStadium() {
            if (stadiumPrefab == null) {
                Debug.LogWarning("[GTEX Atmosphere] Imported stadium resource was not found. Using scene stadium only.");
                return;
            }

            var root = CreateRoot("ImportedStadium", Vector3.zero);
            var stadium = Instantiate(stadiumPrefab, root, false).transform;
            stadium.name = stadiumPrefab.name;

            DisableColliders(stadium);
            FitStadiumToField(stadium, ResolveFieldSize(), ResolveFieldCenter());
            SanitizeImportedHierarchy(stadium, new Color(0.32f, 0.35f, 0.38f), true);
            Debug.Log("[GTEX Atmosphere] Imported stadium attached.");
        }

        private void ApplyEnvironment(FStudio.Data.DayTimes dayTime) {
            switch (dayTime) {
                case FStudio.Data.DayTimes.Morning:
                    RenderSettings.fog = true;
                    RenderSettings.fogColor = new Color(0.82f, 0.88f, 0.95f);
                    RenderSettings.fogDensity = 0.0022f;
                    RenderSettings.ambientLight = new Color(0.75f, 0.78f, 0.82f);
                    break;
                case FStudio.Data.DayTimes.Afternoon:
                    RenderSettings.fog = true;
                    RenderSettings.fogColor = new Color(0.79f, 0.86f, 0.93f);
                    RenderSettings.fogDensity = 0.0016f;
                    RenderSettings.ambientLight = new Color(0.82f, 0.82f, 0.79f);
                    break;
                case FStudio.Data.DayTimes.Night:
                default:
                    RenderSettings.fog = true;
                    RenderSettings.fogColor = new Color(0.07f, 0.1f, 0.14f);
                    RenderSettings.fogDensity = 0.0035f;
                    RenderSettings.ambientLight = new Color(0.18f, 0.2f, 0.24f);
                    break;
            }
        }

        private void BuildPerimeterBoards() {
            var field = ResolveFieldSize();
            var boardMaterial = CreateMaterial(new Color(0.12f, 0.15f, 0.19f), new Color(0.2f, 0.8f, 1f), 1.8f);
            const float boardHeight = 0.42f;
            const float sideBoardOffset = 3.4f;
            var boardY = 0.22f;

            ConfigurePerimeterBoardRenderer(
                CreateQuad(
                    "LED North",
                    new Vector3(field.x * 0.5f, boardY, -sideBoardOffset),
                    Quaternion.identity,
                    new Vector3(field.x + 8f, boardHeight, 1f),
                    boardMaterial,
                    transform));

            ConfigurePerimeterBoardRenderer(
                CreateQuad(
                    "LED West",
                    new Vector3(-sideBoardOffset, boardY, field.y * 0.5f),
                    Quaternion.Euler(0f, 90f, 0f),
                    new Vector3(field.y + 8f, boardHeight, 1f),
                    boardMaterial,
                    transform));

            ConfigurePerimeterBoardRenderer(
                CreateQuad(
                    "LED East",
                    new Vector3(field.x + sideBoardOffset, boardY, field.y * 0.5f),
                    Quaternion.Euler(0f, -90f, 0f),
                    new Vector3(field.y + 8f, boardHeight, 1f),
                    boardMaterial,
                    transform));
        }

        private static void ConfigurePerimeterBoardRenderer(Transform board) {
            if (board == null) {
                return;
            }

            var renderer = board.GetComponent<MeshRenderer>();
            if (renderer == null) {
                return;
            }

            renderer.shadowCastingMode = ShadowCastingMode.Off;
            renderer.receiveShadows = false;
            renderer.lightProbeUsage = LightProbeUsage.Off;
            renderer.reflectionProbeUsage = ReflectionProbeUsage.Off;
            renderer.motionVectorGenerationMode = MotionVectorGenerationMode.ForceNoMotion;
        }

        private void BuildBroadcastScaffolding(MatchCreateRequest matchData) {
            var field = ResolveFieldSize();
            var accent = ResolveAccentColor(matchData.homeTeam.HomeKit, matchData.awayTeam.HomeKit);
            var archMaterial = CreateMaterial(new Color(0.12f, 0.14f, 0.17f), accent, 0.9f);

            var northRig = CreateRoot("BroadcastRigNorth", new Vector3(field.x * 0.5f, 0f, -10f));
            CreateCube("North Bar", new Vector3(0f, 8.5f, 0f), new Vector3(field.x * 0.48f, 0.28f, 0.28f), archMaterial, northRig);
            CreateCube("North Leg Left", new Vector3(-field.x * 0.22f, 4.1f, 0f), new Vector3(0.35f, 8.2f, 0.35f), archMaterial, northRig);
            CreateCube("North Leg Right", new Vector3(field.x * 0.22f, 4.1f, 0f), new Vector3(0.35f, 8.2f, 0.35f), archMaterial, northRig);
        }

        private void BuildCornerFloodlights(FStudio.Data.DayTimes dayTime) {
            var field = ResolveFieldSize();
            var poleMaterial = CreateMaterial(new Color(0.22f, 0.24f, 0.27f), Color.clear, 0f);
            var floodColor = dayTime == FStudio.Data.DayTimes.Night
                ? new Color(0.87f, 0.92f, 1f)
                : new Color(1f, 0.95f, 0.9f);

            CreateFloodlightTower("FloodlightNW", new Vector3(-7f, 0f, -7f), poleMaterial, floodColor, ResolveFieldCenter());
            CreateFloodlightTower("FloodlightNE", new Vector3(field.x + 7f, 0f, -7f), poleMaterial, floodColor, ResolveFieldCenter());
            CreateFloodlightTower("FloodlightSW", new Vector3(-7f, 0f, field.y + 7f), poleMaterial, floodColor, ResolveFieldCenter());
            CreateFloodlightTower("FloodlightSE", new Vector3(field.x + 7f, 0f, field.y + 7f), poleMaterial, floodColor, ResolveFieldCenter());
        }

        private void CreateFloodlightTower(string towerName, Vector3 position, Material poleMaterial, Color floodColor, Vector3 target) {
            var tower = CreateRoot(towerName, position);
            CreateCube("Pole", new Vector3(0f, 9f, 0f), new Vector3(0.55f, 18f, 0.55f), poleMaterial, tower);
            CreateCube("Head", new Vector3(0f, 18.4f, 0f), new Vector3(2.8f, 0.65f, 1.2f), poleMaterial, tower);

            var lightObject = new GameObject("Floodlight");
            lightObject.transform.SetParent(tower, false);
            lightObject.transform.localPosition = new Vector3(0f, 18.2f, 0f);
            lightObject.transform.LookAt(target);

            var light = lightObject.AddComponent<Light>();
            light.type = LightType.Spot;
            light.color = floodColor;
            light.intensity = 5.5f;
            light.range = 130f;
            light.spotAngle = 72f;
            light.shadows = LightShadows.Soft;
        }

        private void BuildCrowd(MatchCreateRequest matchData) {
            if (TryBuildImportedCrowd()) {
                Debug.Log("[GTEX Atmosphere] Crowd mode -> imported.");
                return;
            }

            Debug.LogWarning("[GTEX Atmosphere] Crowd mode -> fallback primitives.");

            var field = ResolveFieldSize();
            var variant = (config != null ? config.stadiumVariant : "broadcast") ?? "broadcast";
            int sideColumns = string.Equals(variant, "arena", System.StringComparison.OrdinalIgnoreCase) ? 26 : 20;
            int endColumns = string.Equals(variant, "arena", System.StringComparison.OrdinalIgnoreCase) ? 18 : 14;
            int rows = string.Equals(variant, "classic", System.StringComparison.OrdinalIgnoreCase) ? 3 : 4;

            var home = matchData.homeTeam.HomeKit != null ? matchData.homeTeam.HomeKit.Color1 : new Color(0.25f, 0.55f, 0.95f);
            var away = matchData.awayTeam.HomeKit != null ? matchData.awayTeam.HomeKit.Color1 : new Color(0.9f, 0.35f, 0.22f);
            var neutral = new Color(0.25f, 0.27f, 0.31f);
            var bright = Color.Lerp(home, away, 0.5f);

            var materials = new[] {
                CreateMaterial(home, home * 0.25f, 0.1f),
                CreateMaterial(away, away * 0.25f, 0.1f),
                CreateMaterial(bright, bright * 0.3f, 0.1f),
                CreateMaterial(neutral, Color.clear, 0f)
            };

            BuildCrowdSide("NorthStand", new Vector3(field.x * 0.5f, 0f, -6f), sideColumns, rows, true, field.x, materials);
            BuildCrowdSide("WestStand", new Vector3(-6f, 0f, field.y * 0.5f), endColumns, rows, false, field.y, materials);
            BuildCrowdSide("EastStand", new Vector3(field.x + 6f, 0f, field.y * 0.5f), endColumns, rows, false, field.y, materials);
        }

        private void BuildCrowdSide(string sideName, Vector3 basePosition, int columns, int rows, bool alongX, float span, Material[] materials) {
            var stand = CreateRoot(sideName, basePosition);
            var stepDepth = alongX ? Vector3.back : Vector3.left;
            var lateral = alongX ? Vector3.right : Vector3.forward;
            var startOffset = -((columns - 1) * 1.45f) * 0.5f;

            for (int row = 0; row < rows; row += 1) {
                var elevation = 0.9f + row * 1.1f;
                var depthOffset = row * 1.1f;
                for (int column = 0; column < columns; column += 1) {
                    var memberPosition =
                        lateral * (startOffset + column * 1.45f) +
                        stepDepth * depthOffset +
                        Vector3.up * elevation;

                    var crowd = CreateCapsule(
                        "Crowd_" + row + "_" + column,
                        memberPosition,
                        new Vector3(0.45f, 0.85f, 0.45f),
                        materials[Random.Range(0, materials.Length)],
                        stand);

                    crowdMembers.Add(new CrowdMember {
                        Transform = crowd,
                        BaseLocalPosition = memberPosition,
                        Phase = Random.Range(0f, 6.28318f),
                        BobSpeed = Random.Range(1.2f, 2.4f),
                        BobHeight = Random.Range(0.03f, 0.12f)
                    });
                }
            }

            if (!string.Equals(sideName, "SouthStand", System.StringComparison.OrdinalIgnoreCase)) {
                var seatMaterial = CreateMaterial(new Color(0.14f, 0.16f, 0.2f), Color.clear, 0f);
                CreateCube(
                    "SeatBase",
                    alongX ? new Vector3(0f, 0.22f, -2.5f) : new Vector3(-2.5f, 0.22f, 0f),
                    alongX ? new Vector3(span + 4f, 0.45f, rows * 1.4f + 2.8f) : new Vector3(rows * 1.4f + 2.8f, 0.45f, span + 4f),
                    seatMaterial,
                    stand);
            }
        }

        private bool TryBuildImportedCrowd() {
            if (crowdPrefabs.Count == 0) {
                return false;
            }

            var field = ResolveFieldSize();
            var variant = (config != null ? config.stadiumVariant : "broadcast") ?? "broadcast";
            int sideColumns = string.Equals(variant, "arena", System.StringComparison.OrdinalIgnoreCase) ? 14 : 12;
            int endColumns = string.Equals(variant, "arena", System.StringComparison.OrdinalIgnoreCase) ? 10 : 8;
            int rows = string.Equals(variant, "classic", System.StringComparison.OrdinalIgnoreCase) ? 2 : 3;

            BuildImportedCrowdSide("NorthStand", new Vector3(field.x * 0.5f, 0f, -6f), sideColumns, rows, true, field.x);
            BuildImportedCrowdSide("WestStand", new Vector3(-6f, 0f, field.y * 0.5f), endColumns, rows, false, field.y);
            BuildImportedCrowdSide("EastStand", new Vector3(field.x + 6f, 0f, field.y * 0.5f), endColumns, rows, false, field.y);
            return true;
        }

        private void BuildImportedCrowdSide(string sideName, Vector3 basePosition, int columns, int rows, bool alongX, float span) {
            var stand = CreateRoot(sideName, basePosition);
            var stepDepth = alongX ? Vector3.back : Vector3.left;
            var lateral = alongX ? Vector3.right : Vector3.forward;
            var startOffset = -((columns - 1) * 2.1f) * 0.5f;
            var fieldCenter = ResolveFieldCenter();

            for (int row = 0; row < rows; row += 1) {
                var elevation = 0.55f + row * 1.05f;
                var depthOffset = row * 1.2f;

                for (int column = 0; column < columns; column += 1) {
                    var memberPosition =
                        lateral * (startOffset + column * 2.1f) +
                        stepDepth * depthOffset +
                        Vector3.up * elevation;

                    var crowdPrefab = crowdPrefabs[Random.Range(0, crowdPrefabs.Count)];
                    var crowd = Instantiate(crowdPrefab, stand, false).transform;
                    crowd.name = "Crowd_" + row + "_" + column;
                    crowd.localPosition = memberPosition;
                    crowd.localRotation = Quaternion.identity;

                    SanitizeImportedHierarchy(crowd, new Color(0.8f, 0.8f, 0.78f), false);
                    FitTransformHeight(crowd, 1.55f);

                    var randomScale = Random.Range(0.92f, 1.06f);
                    crowd.localScale *= randomScale;

                    AlignTransformToGround(crowd, elevation);

                    var lookTarget = fieldCenter;
                    lookTarget.y = crowd.position.y;
                    crowd.LookAt(lookTarget);

                    DisableColliders(crowd);

                    crowdMembers.Add(new CrowdMember {
                        Transform = crowd,
                        BaseLocalPosition = crowd.localPosition,
                        Phase = Random.Range(0f, 6.28318f),
                        BobSpeed = Random.Range(0.7f, 1.6f),
                        BobHeight = Random.Range(0.01f, 0.05f)
                    });
                }
            }

            if (!string.Equals(sideName, "SouthStand", System.StringComparison.OrdinalIgnoreCase)) {
                var seatMaterial = CreateMaterial(new Color(0.14f, 0.16f, 0.2f), Color.clear, 0f);
                CreateCube(
                    "SeatBase",
                    alongX ? new Vector3(0f, 0.22f, -2.6f) : new Vector3(-2.6f, 0.22f, 0f),
                    alongX ? new Vector3(span + 6f, 0.45f, rows * 1.6f + 3.4f) : new Vector3(rows * 1.6f + 3.4f, 0.45f, span + 6f),
                    seatMaterial,
                    stand);
            }
        }

        private Material CreateMaterial(Color baseColor, Color emissionColor, float emissionPower) {
            var shader =
                Shader.Find("Universal Render Pipeline/Lit") ??
                Shader.Find("Standard") ??
                Shader.Find("Sprites/Default");

            if (shader == null) {
                shader = Shader.Find("Diffuse");
            }

            var material = new Material(shader);
            material.color = baseColor;

            if (material.HasProperty("_EmissionColor")) {
                material.EnableKeyword("_EMISSION");
                material.SetColor("_EmissionColor", emissionColor * emissionPower);
            }

            runtimeMaterials.Add(material);
            return material;
        }

        private void SanitizeImportedHierarchy(Transform root, Color fallbackColor, bool stripPitchPlane) {
            var field = ResolveFieldSize();
            var renderers = root.GetComponentsInChildren<Renderer>(true);
            var strippedFieldSurfaceCount = 0;
            var strippedSouthOccluderCount = 0;
            for (int index = 0; index < renderers.Length; index += 1) {
                var renderer = renderers[index];
                if (renderer == null) {
                    continue;
                }

                if (stripPitchPlane) {
                    if (IsImportedFieldSurfaceRenderer(renderer, field)) {
                        renderer.enabled = false;
                        strippedFieldSurfaceCount += 1;
                        continue;
                    }

                    if (IsImportedSouthCameraOccluder(renderer, field)) {
                        renderer.enabled = false;
                        strippedSouthOccluderCount += 1;
                        continue;
                    }
                }

                var sourceMaterials = renderer.sharedMaterials;
                if (sourceMaterials == null || sourceMaterials.Length == 0) {
                    renderer.sharedMaterial = CreateImportedMaterial(null, fallbackColor);
                    continue;
                }

                var replacementMaterials = new Material[sourceMaterials.Length];
                for (int materialIndex = 0; materialIndex < sourceMaterials.Length; materialIndex += 1) {
                    replacementMaterials[materialIndex] = CreateImportedMaterial(sourceMaterials[materialIndex], fallbackColor);
                }

                renderer.sharedMaterials = replacementMaterials;
            }

            if (stripPitchPlane) {
                Debug.Log(
                    "[GTEX Atmosphere] Imported stadium sanitized. Renderers=" +
                    renderers.Length +
                    ", fieldSurfaceStripped=" +
                    strippedFieldSurfaceCount +
                    ", southOccludersStripped=" +
                    strippedSouthOccluderCount);
            }
        }

        private static bool IsImportedFieldSurfaceRenderer(Renderer renderer, Vector2 fieldSize) {
            if (renderer == null) {
                return false;
            }

            var name = renderer.gameObject.name != null
                ? renderer.gameObject.name.ToLowerInvariant()
                : string.Empty;

            if (name.Contains("pitch") || name.Contains("field") || name.Contains("grass")) {
                return true;
            }

            var bounds = renderer.bounds;
            return bounds.size.x >= fieldSize.x * 0.7f &&
                   bounds.size.z >= fieldSize.y * 0.7f &&
                   bounds.min.y <= 0.5f &&
                   bounds.max.y <= 6f;
        }

        private static bool IsImportedSouthCameraOccluder(Renderer renderer, Vector2 fieldSize) {
            if (renderer == null) {
                return false;
            }

            var name = renderer.gameObject.name != null
                ? renderer.gameObject.name.ToLowerInvariant()
                : string.Empty;
            if (name.Contains("goal")) {
                return false;
            }

            var bounds = renderer.bounds;
            if (bounds.max.z < fieldSize.y * 0.72f || bounds.min.y > 11f) {
                return false;
            }

            var nameSuggestsOccluder =
                name.Contains("rail") ||
                name.Contains("barrier") ||
                name.Contains("fence") ||
                name.Contains("wall") ||
                name.Contains("front") ||
                name.Contains("board") ||
                name.Contains("post") ||
                name.Contains("pole");

            var wideRail =
                bounds.size.x >= fieldSize.x * 0.22f &&
                bounds.size.y <= 2.6f &&
                bounds.size.z <= 4.5f &&
                bounds.center.y <= 3.4f;

            var lowWall =
                bounds.size.x >= fieldSize.x * 0.4f &&
                bounds.size.y <= 4.2f &&
                bounds.size.z <= 8f &&
                bounds.center.y <= 4.5f;

            var supportPost =
                bounds.size.x <= 1.6f &&
                bounds.size.z <= 1.6f &&
                bounds.size.y >= 2.4f &&
                bounds.size.y <= 9.5f;

            var cornerWedge =
                bounds.min.z >= fieldSize.y - 0.25f &&
                bounds.max.y <= 12f &&
                bounds.center.y <= 7f &&
                bounds.size.z >= 4f &&
                (bounds.max.x >= fieldSize.x + 1.5f || bounds.min.x <= -1.5f);

            var midSouthRail =
                bounds.center.z >= fieldSize.y * 0.62f &&
                bounds.size.x >= fieldSize.x * 0.35f &&
                bounds.size.y <= 3.5f &&
                bounds.center.y <= 4.5f;

            var southFrontStructure =
                bounds.center.z >= fieldSize.y * 0.55f &&
                bounds.size.z <= 12f &&
                bounds.size.y <= 6f &&
                bounds.center.y <= 5.5f;

            var southTouchlineBlocker =
                bounds.center.z >= fieldSize.y * 0.5f &&
                bounds.max.y <= 8f &&
                bounds.size.y <= 8f &&
                bounds.size.x >= 1.5f;

            var southViewportBandOccluder =
                bounds.center.z >= fieldSize.y * 0.74f &&
                bounds.max.y <= 11f &&
                bounds.size.z <= 20f &&
                bounds.size.x >= fieldSize.x * 0.12f;

            var southStandLip =
                bounds.center.z >= fieldSize.y * 0.78f &&
                bounds.center.y <= 8.5f &&
                bounds.size.y <= 10f &&
                bounds.size.x >= fieldSize.x * 0.08f;

            var southLowStructureBand =
                bounds.center.z >= fieldSize.y * 0.68f &&
                bounds.max.y <= 14f &&
                bounds.size.x >= fieldSize.x * 0.04f &&
                bounds.size.z <= 24f;

            return wideRail ||
                   lowWall ||
                   cornerWedge ||
                   midSouthRail ||
                   southFrontStructure ||
                   southTouchlineBlocker ||
                   southViewportBandOccluder ||
                   southStandLip ||
                   southLowStructureBand ||
                   (nameSuggestsOccluder && supportPost);
        }

        private Material CreateImportedMaterial(Material sourceMaterial, Color fallbackColor) {
            if (sourceMaterial != null && importedMaterialMap.TryGetValue(sourceMaterial, out var cachedMaterial) && cachedMaterial != null) {
                return cachedMaterial;
            }

            var shader =
                Shader.Find("Universal Render Pipeline/Lit") ??
                Shader.Find("Standard") ??
                Shader.Find("Diffuse") ??
                Shader.Find("Sprites/Default");

            var material = new Material(shader);
            var color = ResolveImportedColor(sourceMaterial, fallbackColor);
            var mainTexture = ResolveImportedTexture(sourceMaterial);

            if (material.HasProperty("_BaseColor")) {
                material.SetColor("_BaseColor", color);
            }

            if (material.HasProperty("_Color")) {
                material.SetColor("_Color", color);
            }

            if (mainTexture != null) {
                if (material.HasProperty("_BaseMap")) {
                    material.SetTexture("_BaseMap", mainTexture);
                }

                if (material.HasProperty("_MainTex")) {
                    material.SetTexture("_MainTex", mainTexture);
                }
            }

            if (material.HasProperty("_EmissionColor")) {
                material.SetColor("_EmissionColor", Color.black);
                material.DisableKeyword("_EMISSION");
            }

            runtimeMaterials.Add(material);

            if (sourceMaterial != null) {
                importedMaterialMap[sourceMaterial] = material;
            }

            return material;
        }

        private static Texture ResolveImportedTexture(Material sourceMaterial) {
            if (sourceMaterial == null) {
                return null;
            }

            if (sourceMaterial.HasProperty("_BaseMap")) {
                var texture = sourceMaterial.GetTexture("_BaseMap");
                if (texture != null) {
                    return texture;
                }
            }

            if (sourceMaterial.HasProperty("_MainTex")) {
                var texture = sourceMaterial.GetTexture("_MainTex");
                if (texture != null) {
                    return texture;
                }
            }

            return sourceMaterial.mainTexture;
        }

        private static Color ResolveImportedColor(Material sourceMaterial, Color fallbackColor) {
            if (sourceMaterial == null) {
                return fallbackColor;
            }

            Color color;
            if (sourceMaterial.HasProperty("_BaseColor")) {
                color = sourceMaterial.GetColor("_BaseColor");
                if (color.a > 0f) {
                    return color;
                }
            }

            if (sourceMaterial.HasProperty("_Color")) {
                color = sourceMaterial.GetColor("_Color");
                if (color.a > 0f) {
                    return color;
                }
            }

            return fallbackColor;
        }

        private Transform CreateRoot(string rootName, Vector3 position) {
            var root = new GameObject(rootName).transform;
            root.SetParent(transform, false);
            root.position = position;
            return root;
        }

        private Transform CreateCube(string objectName, Vector3 localPosition, Vector3 localScale, Material material, Transform parent) {
            var cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
            cube.name = objectName;
            cube.transform.SetParent(parent, false);
            cube.transform.localPosition = localPosition;
            cube.transform.localScale = localScale;

            var renderer = cube.GetComponent<MeshRenderer>();
            if (renderer != null) {
                renderer.sharedMaterial = material;
            }

            var collider = cube.GetComponent<Collider>();
            if (collider != null) {
                Destroy(collider);
            }

            return cube.transform;
        }

        private Transform CreateQuad(string objectName, Vector3 localPosition, Quaternion localRotation, Vector3 localScale, Material material, Transform parent) {
            var quad = GameObject.CreatePrimitive(PrimitiveType.Quad);
            quad.name = objectName;
            quad.transform.SetParent(parent, false);
            quad.transform.localPosition = localPosition;
            quad.transform.localRotation = localRotation;
            quad.transform.localScale = localScale;

            var renderer = quad.GetComponent<MeshRenderer>();
            if (renderer != null) {
                renderer.sharedMaterial = material;
            }

            var collider = quad.GetComponent<Collider>();
            if (collider != null) {
                Destroy(collider);
            }

            return quad.transform;
        }

        private Transform CreateCapsule(string objectName, Vector3 localPosition, Vector3 localScale, Material material, Transform parent) {
            var capsule = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            capsule.name = objectName;
            capsule.transform.SetParent(parent, false);
            capsule.transform.localPosition = localPosition;
            capsule.transform.localScale = localScale;

            var renderer = capsule.GetComponent<MeshRenderer>();
            if (renderer != null) {
                renderer.sharedMaterial = material;
            }

            var collider = capsule.GetComponent<Collider>();
            if (collider != null) {
                Destroy(collider);
            }

            return capsule.transform;
        }

        private void FitStadiumToField(Transform stadium, Vector2 field, Vector3 fieldCenter) {
            stadium.rotation = Quaternion.identity;

            if (!TryGetRenderBounds(stadium, out var defaultBounds)) {
                return;
            }

            var targetWidth = field.x + 18f;
            var targetDepth = field.y + 18f;
            var defaultScale = ResolveScale(defaultBounds.size.x, defaultBounds.size.z, targetWidth, targetDepth);

            stadium.rotation = Quaternion.Euler(0f, 90f, 0f);
            if (!TryGetRenderBounds(stadium, out var rotatedBounds)) {
                stadium.rotation = Quaternion.identity;
                rotatedBounds = defaultBounds;
            }

            var rotatedScale = ResolveScale(rotatedBounds.size.x, rotatedBounds.size.z, targetWidth, targetDepth);
            var chosenScale = defaultScale;

            if (rotatedScale > defaultScale) {
                chosenScale = rotatedScale;
            } else {
                stadium.rotation = Quaternion.identity;
            }

            stadium.localScale = Vector3.one * Mathf.Clamp(chosenScale, 0.5f, 6f);

            if (!TryGetRenderBounds(stadium, out var scaledBounds)) {
                return;
            }

            var positionOffset = fieldCenter - scaledBounds.center;
            positionOffset.y = -scaledBounds.min.y + 0.02f;
            stadium.position += positionOffset;
        }

        private float ResolveScale(float sourceWidth, float sourceDepth, float targetWidth, float targetDepth) {
            if (sourceWidth <= 0.01f || sourceDepth <= 0.01f) {
                return 1f;
            }

            return Mathf.Min(targetWidth / sourceWidth, targetDepth / sourceDepth);
        }

        private bool TryGetRenderBounds(Transform root, out Bounds bounds) {
            var renderers = root.GetComponentsInChildren<Renderer>(true);
            bool hasBounds = false;
            bounds = default;

            for (int index = 0; index < renderers.Length; index += 1) {
                var renderer = renderers[index];
                if (renderer == null) {
                    continue;
                }

                if (!hasBounds) {
                    bounds = renderer.bounds;
                    hasBounds = true;
                    continue;
                }

                bounds.Encapsulate(renderer.bounds);
            }

            return hasBounds;
        }

        private void FitTransformHeight(Transform target, float desiredHeight) {
            if (!TryGetRenderBounds(target, out var bounds) || bounds.size.y <= 0.01f) {
                return;
            }

            var scaleFactor = desiredHeight / bounds.size.y;
            target.localScale *= scaleFactor;
        }

        private void AlignTransformToGround(Transform target, float groundHeight) {
            if (!TryGetRenderBounds(target, out var bounds)) {
                return;
            }

            var position = target.position;
            position.y += groundHeight - bounds.min.y;
            target.position = position;
        }

        private void DisableColliders(Transform root) {
            var colliders = root.GetComponentsInChildren<Collider>(true);
            for (int index = 0; index < colliders.Length; index += 1) {
                if (colliders[index] != null) {
                    Destroy(colliders[index]);
                }
            }
        }

        private void HandleControllerEvent(GtexMatchEvent matchEvent) {
            switch (matchEvent.Name) {
                case "legacy-first-whistle":
                    FirstWhistle();
                    break;
                case "legacy-final-whistle":
                    FinalWhistle();
                    break;
                case "legacy-referee-short-whistle":
                    RefereeShortWhistle();
                    break;
                case "legacy-referee-long-whistle":
                    RefereeLongWhistle();
                    break;
                case "legacy-referee-last-whistle":
                    RefereeLastWhistle();
                    break;
            }
        }

        private void FirstWhistle() {
            if (effectsSource != null && ambienceAccentClip != null) {
                effectsSource.PlayOneShot(ambienceAccentClip, 0.12f);
            }
        }

        private void FinalWhistle() {
            finalCuePlayed = true;
            PlayCheer(0.18f);
        }

        private void RefereeShortWhistle() {
            PlayWhistleCue(0.16f);
        }

        private void RefereeLongWhistle() {
            PlayWhistleCue(0.2f);
        }

        private void RefereeLastWhistle() {
            finalCuePlayed = true;
            PlayWhistleCue(0.22f);
        }

        private void LiveStateUpdated(GtexLiveStateSignal signal) {
            var state = signal.State;
            if (state == null) {
                return;
            }

            state.Normalize();

            var scoreChanged =
                hasLiveSnapshot &&
                (state.homeScore != lastLiveHomeScore || state.awayScore != lastLiveAwayScore);

            var activeEvent = state.ResolveActiveEvent();
            var hasNewSequence =
                activeEvent != null &&
                activeEvent.sequence >= 0 &&
                activeEvent.sequence != lastLiveSequence;

            bool cheerPlayed = false;

            if (!signal.IsFallback) {
                if (hasNewSequence) {
                    cheerPlayed = TryCueForLiveEvent(activeEvent);
                }

                if (!cheerPlayed && scoreChanged) {
                    PlayCheer(0.18f);
                    cheerPlayed = true;
                }

                if (!finalCuePlayed && IsFinalLiveState(state, activeEvent)) {
                    PlayWhistleCue(0.22f);
                    if (!cheerPlayed) {
                        PlayCheer(0.18f);
                    }
                    finalCuePlayed = true;
                }
            }

            if (activeEvent != null && activeEvent.sequence >= 0) {
                lastLiveSequence = activeEvent.sequence;
            }

            lastLiveHomeScore = state.homeScore;
            lastLiveAwayScore = state.awayScore;
            hasLiveSnapshot = true;
        }

        private bool TryCueForLiveEvent(Event activeEvent) {
            if (activeEvent == null) {
                return false;
            }

            var type = (activeEvent.type ?? string.Empty).ToLowerInvariant();

            if (type.Contains("goal")) {
                PlayCheer(0.2f);
                return true;
            }

            if (type.Contains("whistle") ||
                type.Contains("kick") ||
                type.Contains("half") ||
                type.Contains("foul") ||
                type.Contains("offside")) {
                PlayWhistleCue(0.16f);
            }

            return false;
        }

        private bool IsFinalLiveState(MatchResponse state, Event activeEvent) {
            var status = (state.status ?? string.Empty).ToLowerInvariant();
            var phase = (state.phase ?? string.Empty).ToLowerInvariant();
            var eventType = activeEvent != null ? (activeEvent.type ?? string.Empty).ToLowerInvariant() : string.Empty;

            return status.Contains("final") ||
                   status.Contains("complete") ||
                   status.Contains("finished") ||
                   status.Contains("ended") ||
                   phase.Contains("final") ||
                   phase.Contains("full") ||
                   eventType.Contains("final") ||
                   eventType.Contains("full") ||
                   state.clockMinute >= 90f;
        }

        private void PlayWhistleCue(float volume) {
            if (Time.unscaledTime - lastWhistleCueAt < 0.75f) {
                return;
            }

            lastWhistleCueAt = Time.unscaledTime;
            PlayWhistle(volume);
        }

        private void PlayCheer(float volume) {
            if (effectsSource == null || cheerClip == null) {
                return;
            }

            if (Time.unscaledTime - lastCheerCueAt < 0.75f) {
                return;
            }

            lastCheerCueAt = Time.unscaledTime;
            effectsSource.PlayOneShot(cheerClip, volume);
        }

        private void PlayWhistle(float volume) {
            if (effectsSource == null || whistleClip == null) {
                return;
            }

            effectsSource.PlayOneShot(whistleClip, volume);
        }

        private Color ResolveAccentColor(KitEntry homeKit, KitEntry awayKit) {
            var home = homeKit != null ? homeKit.Color1 : new Color(0.22f, 0.56f, 0.94f);
            var away = awayKit != null ? awayKit.Color1 : new Color(0.95f, 0.42f, 0.2f);
            return Color.Lerp(home, away, 0.5f);
        }

        private Vector2 ResolveFieldSize() {
            var fieldSize = GtexMatchController.MatchManagerAdapter.FieldSize;
            if (fieldSize != Vector2.zero) {
                return fieldSize;
            }

            return new Vector2(85f, 60f);
        }

        private Vector3 ResolveFieldCenter() {
            var field = ResolveFieldSize();
            return new Vector3(field.x * 0.5f, 0f, field.y * 0.5f);
        }

        private void ClearRuntimeChildren() {
            crowdMembers.Clear();
            hasLiveSnapshot = false;
            finalCuePlayed = false;
            lastLiveSequence = -1;
            lastLiveHomeScore = -1;
            lastLiveAwayScore = -1;
            lastWhistleCueAt = -10f;
            lastCheerCueAt = -10f;

            if (effectsSource != null) {
                effectsSource.Stop();
            }

            for (int index = 0; index < runtimeMaterials.Count; index += 1) {
                if (runtimeMaterials[index] != null) {
                    Destroy(runtimeMaterials[index]);
                }
            }

            runtimeMaterials.Clear();
            importedMaterialMap.Clear();

            for (int index = transform.childCount - 1; index >= 0; index -= 1) {
                Destroy(transform.GetChild(index).gameObject);
            }
        }
    }
}
