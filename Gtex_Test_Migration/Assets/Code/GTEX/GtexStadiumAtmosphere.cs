using System.Collections.Generic;
using FStudio.Database;
using FStudio.MatchEngine;
using FStudio.UI.MatchThemes.MatchEvents;
using Shared.Responses;
using UnityEngine;

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

        private GtexMatchConfig config;

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

        private void Apply(MatchCreateRequest matchData, GtexMatchConfig config) {
            this.config = config;
            ClearRuntimeChildren();
            ApplyEnvironment(matchData.dayTime);
            BuildPerimeterBoards();
            BuildCornerFloodlights(matchData.dayTime);

            if (config == null || config.enableStadiumUpgrade) {
                BuildBroadcastScaffolding(matchData);
            }

            if (config == null || config.showCrowd) {
                BuildCrowd(matchData);
            }
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
            for (int index = 0; index < runtimeMaterials.Count; index += 1) {
                if (runtimeMaterials[index] != null) {
                    Destroy(runtimeMaterials[index]);
                }
            }

            runtimeMaterials.Clear();
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
            var boardMaterial = CreateMaterial(new Color(0.07f, 0.11f, 0.16f), new Color(0.2f, 0.8f, 1f), 1.8f);

            CreateCube("LED North", new Vector3(field.x * 0.5f, 0.55f, -1.1f), new Vector3(field.x + 6f, 1.1f, 0.22f), boardMaterial, transform);
            CreateCube("LED South", new Vector3(field.x * 0.5f, 0.55f, field.y + 1.1f), new Vector3(field.x + 6f, 1.1f, 0.22f), boardMaterial, transform);
            CreateCube("LED West", new Vector3(-1.1f, 0.55f, field.y * 0.5f), new Vector3(0.22f, 1.1f, field.y + 6f), boardMaterial, transform);
            CreateCube("LED East", new Vector3(field.x + 1.1f, 0.55f, field.y * 0.5f), new Vector3(0.22f, 1.1f, field.y + 6f), boardMaterial, transform);
        }

        private void BuildBroadcastScaffolding(MatchCreateRequest matchData) {
            var field = ResolveFieldSize();
            var accent = ResolveAccentColor(matchData.homeTeam.HomeKit, matchData.awayTeam.HomeKit);
            var archMaterial = CreateMaterial(new Color(0.12f, 0.14f, 0.17f), accent, 0.9f);

            var northRig = CreateRoot("BroadcastRigNorth", new Vector3(field.x * 0.5f, 0f, -8f));
            CreateCube("North Bar", new Vector3(0f, 7.5f, 0f), new Vector3(field.x * 0.55f, 0.35f, 0.35f), archMaterial, northRig);
            CreateCube("North Leg Left", new Vector3(-field.x * 0.25f, 3.6f, 0f), new Vector3(0.45f, 7.2f, 0.45f), archMaterial, northRig);
            CreateCube("North Leg Right", new Vector3(field.x * 0.25f, 3.6f, 0f), new Vector3(0.45f, 7.2f, 0.45f), archMaterial, northRig);

            var southRig = CreateRoot("BroadcastRigSouth", new Vector3(field.x * 0.5f, 0f, field.y + 8f));
            CreateCube("South Bar", new Vector3(0f, 7.5f, 0f), new Vector3(field.x * 0.55f, 0.35f, 0.35f), archMaterial, southRig);
            CreateCube("South Leg Left", new Vector3(-field.x * 0.25f, 3.6f, 0f), new Vector3(0.45f, 7.2f, 0.45f), archMaterial, southRig);
            CreateCube("South Leg Right", new Vector3(field.x * 0.25f, 3.6f, 0f), new Vector3(0.45f, 7.2f, 0.45f), archMaterial, southRig);
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
            BuildCrowdSide("SouthStand", new Vector3(field.x * 0.5f, 0f, field.y + 6f), sideColumns, rows, true, field.x, materials);
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

            var seatMaterial = CreateMaterial(new Color(0.14f, 0.16f, 0.2f), Color.clear, 0f);
            CreateCube(
                "SeatBase",
                alongX ? new Vector3(0f, 0.22f, -2.5f) : new Vector3(-2.5f, 0.22f, 0f),
                alongX ? new Vector3(span + 4f, 0.45f, rows * 1.4f + 2.8f) : new Vector3(rows * 1.4f + 2.8f, 0.45f, span + 4f),
                seatMaterial,
                stand);
        }

        private Material CreateMaterial(Color baseColor, Color emissionColor, float emissionPower) {
            var shader =
                Shader.Find("Standard") ??
                Shader.Find("Universal Render Pipeline/Lit") ??
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

        private Color ResolveAccentColor(KitEntry homeKit, KitEntry awayKit) {
            var home = homeKit != null ? homeKit.Color1 : new Color(0.22f, 0.56f, 0.94f);
            var away = awayKit != null ? awayKit.Color1 : new Color(0.95f, 0.42f, 0.2f);
            return Color.Lerp(home, away, 0.5f);
        }

        private Vector2 ResolveFieldSize() {
            if (MatchManager.Current != null) {
                return new Vector2(MatchManager.Current.fieldEndX, MatchManager.Current.fieldEndY);
            }

            return new Vector2(85f, 60f);
        }

        private Vector3 ResolveFieldCenter() {
            var field = ResolveFieldSize();
            return new Vector3(field.x * 0.5f, 0f, field.y * 0.5f);
        }

        private void ClearRuntimeChildren() {
            crowdMembers.Clear();

            for (int index = 0; index < runtimeMaterials.Count; index += 1) {
                if (runtimeMaterials[index] != null) {
                    Destroy(runtimeMaterials[index]);
                }
            }

            runtimeMaterials.Clear();

            for (int index = transform.childCount - 1; index >= 0; index -= 1) {
                Destroy(transform.GetChild(index).gameObject);
            }
        }
    }
}
