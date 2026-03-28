using UnityEngine;

namespace Gtex.Match3D.Runtime
{
    [DefaultExecutionOrder(-1000)]
    public sealed class MatchSceneBootstrap : MonoBehaviour
    {
        [SerializeField] private bool bootstrapOnAwake = true;
        [SerializeField] private MatchController matchController;
        [SerializeField] private FlutterUnityBridge flutterUnityBridge;
        [SerializeField] private PitchController pitchController;
        [SerializeField] private BallController ballController;
        [SerializeField] private CameraController cameraController;
        [SerializeField] private Transform playersRoot;
        [SerializeField] private PlayerController playerPrototype;
        [SerializeField] private ReplayRecorder replayRecorder;
        [SerializeField] private ReplayPlayer replayPlayer;

        private void Awake()
        {
            if (bootstrapOnAwake)
            {
                Bootstrap();
            }
        }

        [ContextMenu("Bootstrap Match Scene")]
        public void Bootstrap()
        {
            Transform pitchRoot = EnsureChild("Pitch");
            Transform ballRoot = EnsureChild("Ball");
            playersRoot = EnsureChild("Players");
            Transform camerasRoot = EnsureChild("Cameras");
            Transform lightingRoot = EnsureChild("Lighting");
            Transform controllerRoot = EnsureChild("MatchController");

            pitchController = EnsurePitch(pitchRoot);
            ballController = EnsureBall(ballRoot);
            cameraController = EnsureCamera(camerasRoot);
            EnsureLighting(lightingRoot);
            playerPrototype = EnsurePlayerPrototype(playersRoot);

            matchController = EnsureComponent<MatchController>(controllerRoot.gameObject);
            replayRecorder = EnsureComponent<ReplayRecorder>(controllerRoot.gameObject);
            replayPlayer = EnsureComponent<ReplayPlayer>(controllerRoot.gameObject);
            flutterUnityBridge = EnsureComponent<FlutterUnityBridge>(controllerRoot.gameObject);

            matchController.ConfigureScene(
                pitchController,
                ballController,
                cameraController,
                playersRoot,
                playerPrototype,
                replayRecorder,
                replayPlayer);

            flutterUnityBridge.SetController(matchController);
            replayPlayer.SetMatchController(matchController);
        }

        private Transform EnsureChild(string childName)
        {
            Transform child = transform.Find(childName);
            if (child != null)
            {
                return child;
            }

            GameObject childObject = new GameObject(childName);
            childObject.transform.SetParent(transform, false);
            return childObject.transform;
        }

        private PitchController EnsurePitch(Transform pitchRoot)
        {
            PitchController existing = pitchRoot.GetComponent<PitchController>();
            if (existing != null)
            {
                existing.ApplyDimensions(105f, 68f);
                return existing;
            }

            GameObject plane = GameObject.CreatePrimitive(PrimitiveType.Plane);
            plane.name = "Surface";
            plane.transform.SetParent(pitchRoot, false);
            plane.transform.localPosition = Vector3.zero;
            plane.transform.localRotation = Quaternion.identity;

            PitchController controller = pitchRoot.gameObject.AddComponent<PitchController>();
            controller.SetSurfaceTransform(plane.transform);
            controller.ApplyDimensions(105f, 68f);

            Renderer renderer = plane.GetComponent<Renderer>();
            if (renderer != null)
            {
                renderer.material.color = new Color(0.08f, 0.40f, 0.14f);
            }

            return controller;
        }

        private BallController EnsureBall(Transform ballRoot)
        {
            BallController existing = ballRoot.GetComponent<BallController>();
            if (existing != null)
            {
                return existing;
            }

            GameObject sphere = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            sphere.name = "Model";
            sphere.transform.SetParent(ballRoot, false);
            sphere.transform.localScale = Vector3.one * 0.22f;

            Renderer renderer = sphere.GetComponent<Renderer>();
            if (renderer != null)
            {
                renderer.material.color = Color.white;
            }

            return ballRoot.gameObject.AddComponent<BallController>();
        }

        private CameraController EnsureCamera(Transform camerasRoot)
        {
            CameraController existing = camerasRoot.GetComponentInChildren<CameraController>(true);
            if (existing != null)
            {
                return existing;
            }

            GameObject cameraObject = new GameObject("MainCamera");
            cameraObject.transform.SetParent(camerasRoot, false);
            cameraObject.transform.localPosition = new Vector3(-14f, 18f, -18f);
            cameraObject.transform.LookAt(Vector3.zero);
            cameraObject.tag = "MainCamera";

            Camera cameraComponent = cameraObject.AddComponent<Camera>();
            cameraComponent.fieldOfView = 50f;

            AudioListener listener = cameraObject.AddComponent<AudioListener>();
            if (listener != null)
            {
                AudioListener[] listeners = FindObjectsOfType<AudioListener>();
                if (listeners.Length > 1)
                {
                    listener.enabled = false;
                }
            }

            return cameraObject.AddComponent<CameraController>();
        }

        private void EnsureLighting(Transform lightingRoot)
        {
            Light existing = lightingRoot.GetComponentInChildren<Light>(true);
            if (existing != null)
            {
                return;
            }

            GameObject lightObject = new GameObject("DirectionalLight");
            lightObject.transform.SetParent(lightingRoot, false);
            lightObject.transform.rotation = Quaternion.Euler(45f, -35f, 0f);
            Light light = lightObject.AddComponent<Light>();
            light.type = LightType.Directional;
            light.intensity = 1.35f;
            light.color = new Color(1f, 0.97f, 0.92f);
        }

        private PlayerController EnsurePlayerPrototype(Transform playersContainer)
        {
            PlayerController existing = playersContainer.GetComponentInChildren<PlayerController>(true);
            if (existing != null)
            {
                return existing;
            }

            GameObject playerObject = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            playerObject.name = "PlayerPrototype";
            playerObject.transform.SetParent(playersContainer, false);
            playerObject.transform.localScale = new Vector3(0.60f, 0.90f, 0.60f);
            PlayerController controller = playerObject.AddComponent<PlayerController>();
            playerObject.SetActive(false);
            return controller;
        }

        private static T EnsureComponent<T>(GameObject target) where T : Component
        {
            T component = target.GetComponent<T>();
            if (component == null)
            {
                component = target.AddComponent<T>();
            }

            return component;
        }
    }
}
