using System;
using System.Collections.Generic;
using Unity.Cinemachine;
using Unity.Cinemachine.TargetTracking;
using UnityEngine;

namespace FStudio.GTEX.VisualBridge
{
    public sealed class GtexCinemachineFootballCameraDirector : MonoBehaviour
    {
        [Header("Weights")]
        [SerializeField] private float ballWeight = 1f;
        [SerializeField] private float ballCarrierWeight = 0.45f;
        [SerializeField] private float passTargetWeight = 0.4f;
        [SerializeField] private float nearbyPlayerMaxWeight = 0.28f;
        [SerializeField] private float nearbyPlayerMinWeight = 0.18f;
        [SerializeField] private float attackingGoalWeight = 0.2f;

        [Header("Framing")]
        [SerializeField] private int nearbyPlayerLimit = 8;
        [SerializeField] private float nearbyClusterRadius = 36f;
        [SerializeField] private float finalThirdGoalDistance = 42f;
        [SerializeField] private float maxFocusDistanceFromBall = 34f;
        [SerializeField] private Vector3 midfieldFollowOffset = new Vector3(0f, 19f, -31f);
        [SerializeField] private Vector3 finalThirdFollowOffset = new Vector3(0f, 20.5f, -29f);
        [SerializeField] private Vector3 bodyDamping = new Vector3(0.2f, 0.14f, 0.34f);
        [SerializeField] private Vector2 aimDamping = new Vector2(0.16f, 0.14f);
        [SerializeField] private float framingSize = 0.58f;

        private readonly List<Transform> activePlayers = new List<Transform>();
        private readonly HashSet<int> goalkeeperTransformIds = new HashSet<int>();
        private readonly HashSet<int> groupMemberIds = new HashSet<int>();
        private readonly Transform[] nearestPlayers = new Transform[10];
        private readonly float[] nearestPlayerDistances = new float[10];

        private Camera outputCamera;
        private CinemachineBrain brain;
        private CinemachineCamera footballCamera;
        private CinemachineTargetGroup targetGroup;
        private Transform runtimeRoot;
        private Transform groupMarkerRoot;
        private Transform focusAnchor;
        private Transform worldPassTargetMarker;
        private Transform attackingGoalMarker;
        private Transform ball;
        private Transform ballOwner;
        private Transform passTarget;
        private string ballOwnerId = string.Empty;
        private string passTargetId = string.Empty;
        private Vector3 worldPassTarget;
        private bool hasWorldPassTarget;
        private Func<Transform> ballResolver;
        private Func<Vector3?> attackingGoalResolver;

        public bool HasBoundCamera => outputCamera != null && brain != null && footballCamera != null && targetGroup != null;

        public bool HasValidFocus
        {
            get
            {
                if (!HasBoundCamera || footballCamera == null || !footballCamera.enabled)
                {
                    return false;
                }

                if (IsUsableTransform(ball) || IsUsableTransform(ballOwner) || IsUsableTransform(passTarget))
                {
                    return true;
                }

                for (var index = 0; index < activePlayers.Count; index += 1)
                {
                    if (IsUsableTransform(activePlayers[index]))
                    {
                        return true;
                    }
                }

                return hasWorldPassTarget;
            }
        }

        public string ModeName => "CinemachineFootball";

        public void SetCameraActive(bool isActive)
        {
            if (footballCamera != null)
            {
                footballCamera.enabled = isActive;
            }
        }

        public void Bind(
            Camera camera,
            Transform ballTransform,
            IEnumerable<Transform> players,
            Func<Transform> resolveBall = null,
            Func<Vector3?> resolveAttackingGoal = null,
            IEnumerable<Transform> goalkeeperTransforms = null)
        {
            outputCamera = camera;
            ball = ballTransform;
            ballResolver = resolveBall;
            attackingGoalResolver = resolveAttackingGoal;

            activePlayers.Clear();
            if (players != null)
            {
                foreach (var player in players)
                {
                    if (player != null)
                    {
                        activePlayers.Add(player);
                    }
                }
            }

            goalkeeperTransformIds.Clear();
            if (goalkeeperTransforms != null)
            {
                foreach (var goalkeeper in goalkeeperTransforms)
                {
                    if (goalkeeper != null)
                    {
                        goalkeeperTransformIds.Add(goalkeeper.GetInstanceID());
                    }
                }
            }

            EnsureRig();
            RebuildTargetGroup();
        }

        public void SetBallOwner(Transform owner, string ownerId = null)
        {
            ballOwner = owner;
            if (ownerId != null)
            {
                ballOwnerId = ownerId;
            }
        }

        public void SetPassTarget(Transform target, string targetId = null)
        {
            passTarget = target;
            hasWorldPassTarget = false;
            worldPassTarget = Vector3.zero;
            if (targetId != null)
            {
                passTargetId = targetId;
            }
        }

        public void SetWorldPassTarget(Vector3 target, string targetId = null)
        {
            worldPassTarget = target;
            hasWorldPassTarget = IsFinite(target);
            passTarget = null;
            if (targetId != null)
            {
                passTargetId = targetId;
            }
        }

        public void ClearPassTarget()
        {
            passTarget = null;
            passTargetId = string.Empty;
            worldPassTarget = Vector3.zero;
            hasWorldPassTarget = false;
        }

        private void LateUpdate()
        {
            if (!HasBoundCamera || footballCamera == null || !footballCamera.enabled)
            {
                return;
            }

            RebindBallIfNeeded();
            UpdateFocusAnchor();
            RebuildTargetGroup();
        }

        private void EnsureRig()
        {
            if (outputCamera == null)
            {
                return;
            }

            brain = outputCamera.GetComponent<CinemachineBrain>();
            if (brain == null)
            {
                brain = outputCamera.gameObject.AddComponent<CinemachineBrain>();
            }

            brain.enabled = true;
            brain.ShowDebugText = false;
            brain.UpdateMethod = CinemachineBrain.UpdateMethods.LateUpdate;
            brain.BlendUpdateMethod = CinemachineBrain.BrainUpdateMethods.LateUpdate;

            if (runtimeRoot == null)
            {
                var runtimeRootObject = new GameObject("GTEX_CinemachineFootballRig");
                runtimeRootObject.transform.SetParent(transform, false);
                runtimeRoot = runtimeRootObject.transform;
            }

            if (groupMarkerRoot == null)
            {
                var groupObject = new GameObject("GTEX_CinemachineTargetGroup");
                groupObject.transform.SetParent(runtimeRoot, false);
                groupMarkerRoot = groupObject.transform;
                targetGroup = groupObject.AddComponent<CinemachineTargetGroup>();
            }
            else if (targetGroup == null)
            {
                targetGroup = groupMarkerRoot.GetComponent<CinemachineTargetGroup>();
                if (targetGroup == null)
                {
                    targetGroup = groupMarkerRoot.gameObject.AddComponent<CinemachineTargetGroup>();
                }
            }

            targetGroup.PositionMode = CinemachineTargetGroup.PositionModes.GroupAverage;
            targetGroup.RotationMode = CinemachineTargetGroup.RotationModes.Manual;
            targetGroup.UpdateMethod = CinemachineTargetGroup.UpdateMethods.LateUpdate;

            focusAnchor = EnsureMarker(focusAnchor, "GTEX_CinemachineFocusAnchor");
            worldPassTargetMarker = EnsureMarker(worldPassTargetMarker, "GTEX_CinemachineWorldPassTarget");
            attackingGoalMarker = EnsureMarker(attackingGoalMarker, "GTEX_CinemachineAttackingGoal");

            if (footballCamera == null)
            {
                var cameraObject = new GameObject("GTEX_CinemachineFootballCamera");
                cameraObject.transform.SetParent(runtimeRoot, false);
                cameraObject.transform.position = outputCamera.transform.position;
                cameraObject.transform.rotation = outputCamera.transform.rotation;
                footballCamera = cameraObject.AddComponent<CinemachineCamera>();
                footballCamera.Priority = 100;
            }

            ConfigureLens();
            ConfigurePipeline();

            footballCamera.Follow = focusAnchor;
            footballCamera.LookAt = targetGroup.transform;
            footballCamera.enabled = true;
        }

        private Transform EnsureMarker(Transform marker, string name)
        {
            if (marker != null)
            {
                return marker;
            }

            var markerObject = new GameObject(name);
            markerObject.transform.SetParent(runtimeRoot, false);
            return markerObject.transform;
        }

        private void ConfigureLens()
        {
            if (footballCamera == null || outputCamera == null)
            {
                return;
            }

            var lens = footballCamera.Lens;
            lens.FieldOfView = 34f;
            lens.NearClipPlane = outputCamera.nearClipPlane;
            lens.FarClipPlane = outputCamera.farClipPlane;
            lens.Dutch = 0f;
            footballCamera.Lens = lens;
        }

        private void ConfigurePipeline()
        {
            if (footballCamera == null)
            {
                return;
            }

            var positionComposer = footballCamera.GetComponent<CinemachinePositionComposer>();
            if (positionComposer != null)
            {
                positionComposer.enabled = false;
            }

            var follow = footballCamera.GetComponent<CinemachineFollow>();
            if (follow == null)
            {
                follow = footballCamera.gameObject.AddComponent<CinemachineFollow>();
            }

            var trackerSettings = follow.TrackerSettings;
            trackerSettings.BindingMode = BindingMode.WorldSpace;
            trackerSettings.PositionDamping = bodyDamping;
            trackerSettings.AngularDampingMode = AngularDampingMode.Quaternion;
            trackerSettings.RotationDamping = Vector3.zero;
            trackerSettings.QuaternionDamping = 0f;
            follow.TrackerSettings = trackerSettings;
            follow.FollowOffset = midfieldFollowOffset;

            var rotationComposer = footballCamera.GetComponent<CinemachineRotationComposer>();
            if (rotationComposer == null)
            {
                rotationComposer = footballCamera.gameObject.AddComponent<CinemachineRotationComposer>();
            }

            rotationComposer.TargetOffset = new Vector3(0f, 1.15f, 0f);
            rotationComposer.Damping = aimDamping;
            rotationComposer.CenterOnActivate = true;

            var groupFraming = footballCamera.GetComponent<CinemachineGroupFraming>();
            if (groupFraming == null)
            {
                groupFraming = footballCamera.gameObject.AddComponent<CinemachineGroupFraming>();
            }

            groupFraming.FramingMode = CinemachineGroupFraming.FramingModes.HorizontalAndVertical;
            groupFraming.FramingSize = framingSize;
            groupFraming.CenterOffset = new Vector2(0f, 0.02f);
            groupFraming.Damping = 0.2f;
            groupFraming.SizeAdjustment = CinemachineGroupFraming.SizeAdjustmentModes.ZoomOnly;
            groupFraming.LateralAdjustment = CinemachineGroupFraming.LateralAdjustmentModes.ChangePosition;
            groupFraming.DollyRange = new Vector2(0f, 0f);
            groupFraming.FovRange = new Vector2(32f, 48f);
        }

        private void RebindBallIfNeeded()
        {
            if (ballResolver == null)
            {
                return;
            }

            var resolvedBall = ballResolver();
            if (IsUsableTransform(resolvedBall))
            {
                ball = resolvedBall;
            }
            else if (!IsUsableTransform(ball))
            {
                ball = null;
            }
        }

        private void UpdateFocusAnchor()
        {
            if (focusAnchor == null)
            {
                return;
            }

            var focus = ResolveBroadcastFocus();
            if (!IsFinite(focus))
            {
                return;
            }

            if (!IsFinite(focusAnchor.position) || focusAnchor.position == Vector3.zero)
            {
                focusAnchor.position = focus;
            }
            else
            {
                focusAnchor.position = Vector3.Lerp(focusAnchor.position, focus, Time.deltaTime * 7f);
            }

            var follow = footballCamera != null ? footballCamera.GetComponent<CinemachineFollow>() : null;
            if (follow != null)
            {
                follow.FollowOffset = ResolveFollowOffset(focus);
            }
        }

        private void RebuildTargetGroup()
        {
            if (!HasBoundCamera)
            {
                return;
            }

            groupMemberIds.Clear();
            targetGroup.Targets.Clear();

            var focusOrigin = ResolveFocusOrigin();
            AddGroupTarget(ball, ballWeight, 0.38f);
            AddGroupTarget(ballOwner, ballCarrierWeight, 0.82f);

            if (IsUsableTransform(passTarget))
            {
                AddGroupTarget(passTarget, passTargetWeight, 0.82f);
            }
            else if (hasWorldPassTarget && IsFinite(worldPassTarget))
            {
                worldPassTargetMarker.position = worldPassTarget;
                AddGroupTarget(worldPassTargetMarker, passTargetWeight, 1f);
            }

            AddNearbyPlayers(focusOrigin);

            if (attackingGoalResolver != null)
            {
                var attackingGoal = attackingGoalResolver();
                if (attackingGoal.HasValue &&
                    IsFinite(attackingGoal.Value) &&
                    IsInFinalThird(focusOrigin, attackingGoal.Value))
                {
                    attackingGoalMarker.position = attackingGoal.Value;
                    AddGroupTarget(attackingGoalMarker, attackingGoalWeight, 1.5f);
                }
            }

            _ = targetGroup.IsEmpty;
        }

        private Vector3 ResolveBroadcastFocus()
        {
            if (IsUsableTransform(ball))
            {
                var ballPosition = ball.position;
                Vector3 focus = ballPosition * 0.28f;
                var weight = 0.28f;

                if (IsUsableTransform(ballOwner))
                {
                    focus += ballOwner.position * 0.14f;
                    weight += 0.14f;
                }

                if (IsUsableTransform(passTarget))
                {
                    focus += passTarget.position * 0.14f;
                    weight += 0.14f;
                }
                else if (hasWorldPassTarget && IsFinite(worldPassTarget))
                {
                    focus += worldPassTarget * 0.14f;
                    weight += 0.14f;
                }

                var nearbyCluster = ResolveNearbyClusterCenter(ballPosition, out var clusterValid);
                if (clusterValid)
                {
                    focus += nearbyCluster * 0.32f;
                    weight += 0.32f;
                }

                if (weight > 0.001f)
                {
                    focus /= weight;
                }

                if (attackingGoalResolver != null)
                {
                    var attackingGoal = attackingGoalResolver();
                    if (attackingGoal.HasValue &&
                        IsFinite(attackingGoal.Value) &&
                        IsInFinalThird(ballPosition, attackingGoal.Value))
                    {
                        focus = Vector3.Lerp(focus, attackingGoal.Value, 0.04f);
                    }
                }

                var planarFromBall = focus - ballPosition;
                planarFromBall.y = 0f;
                if (planarFromBall.magnitude > maxFocusDistanceFromBall)
                {
                    focus = ballPosition + planarFromBall.normalized * maxFocusDistanceFromBall;
                    focus.y = Mathf.Lerp(focus.y, ballPosition.y, 0.35f);
                }

                return focus;
            }

            return ResolveFocusOrigin();
        }

        private Vector3 ResolveFocusOrigin()
        {
            if (IsUsableTransform(ball))
            {
                return ball.position;
            }

            if (IsUsableTransform(ballOwner))
            {
                return ballOwner.position;
            }

            if (IsUsableTransform(passTarget))
            {
                return passTarget.position;
            }

            if (hasWorldPassTarget && IsFinite(worldPassTarget))
            {
                return worldPassTarget;
            }

            for (var index = 0; index < activePlayers.Count; index += 1)
            {
                if (IsUsableTransform(activePlayers[index]))
                {
                    return activePlayers[index].position;
                }
            }

            return Vector3.zero;
        }

        private void AddNearbyPlayers(Vector3 focusOrigin)
        {
            var count = Mathf.Clamp(nearbyPlayerLimit, 0, nearestPlayers.Length);
            for (var index = 0; index < nearestPlayers.Length; index += 1)
            {
                nearestPlayers[index] = null;
                nearestPlayerDistances[index] = float.PositiveInfinity;
            }

            var maxDistanceSq = nearbyClusterRadius * nearbyClusterRadius;
            for (var index = 0; index < activePlayers.Count; index += 1)
            {
                var player = activePlayers[index];
                if (!IsUsableTransform(player))
                {
                    continue;
                }

                if (player == ballOwner || player == passTarget)
                {
                    continue;
                }

                var distanceSq = (player.position - focusOrigin).sqrMagnitude;
                if (distanceSq > maxDistanceSq)
                {
                    continue;
                }

                InsertNearestPlayer(player, distanceSq, count);
            }

            if (count <= 0)
            {
                return;
            }

            for (var index = 0; index < count; index += 1)
            {
                var player = nearestPlayers[index];
                if (!IsUsableTransform(player))
                {
                    continue;
                }

                var t = count <= 1 ? 0f : index / (float)(count - 1);
                var weight = Mathf.Lerp(nearbyPlayerMaxWeight, nearbyPlayerMinWeight, t);
                var radius = goalkeeperTransformIds.Contains(player.GetInstanceID()) ? 1f : 0.78f;
                AddGroupTarget(player, weight, radius);
            }
        }

        private Vector3 ResolveNearbyClusterCenter(Vector3 focusOrigin, out bool valid)
        {
            var count = Mathf.Clamp(nearbyPlayerLimit, 0, nearestPlayers.Length);
            for (var index = 0; index < nearestPlayers.Length; index += 1)
            {
                nearestPlayers[index] = null;
                nearestPlayerDistances[index] = float.PositiveInfinity;
            }

            var maxDistanceSq = nearbyClusterRadius * nearbyClusterRadius;
            for (var index = 0; index < activePlayers.Count; index += 1)
            {
                var player = activePlayers[index];
                if (!IsUsableTransform(player) || player == ballOwner || player == passTarget)
                {
                    continue;
                }

                var distanceSq = (player.position - focusOrigin).sqrMagnitude;
                if (distanceSq > maxDistanceSq)
                {
                    continue;
                }

                InsertNearestPlayer(player, distanceSq, count);
            }

            Vector3 sum = Vector3.zero;
            var resolvedCount = 0;
            for (var index = 0; index < count; index += 1)
            {
                var player = nearestPlayers[index];
                if (!IsUsableTransform(player))
                {
                    continue;
                }

                sum += player.position;
                resolvedCount += 1;
            }

            valid = resolvedCount > 0;
            return valid ? sum / resolvedCount : focusOrigin;
        }

        private void InsertNearestPlayer(Transform candidate, float distanceSq, int count)
        {
            for (var slot = 0; slot < count; slot += 1)
            {
                if (distanceSq >= nearestPlayerDistances[slot])
                {
                    continue;
                }

                for (var shift = count - 1; shift > slot; shift -= 1)
                {
                    nearestPlayerDistances[shift] = nearestPlayerDistances[shift - 1];
                    nearestPlayers[shift] = nearestPlayers[shift - 1];
                }

                nearestPlayerDistances[slot] = distanceSq;
                nearestPlayers[slot] = candidate;
                break;
            }
        }

        private void AddGroupTarget(Transform target, float weight, float radius)
        {
            if (!IsUsableTransform(target) || weight <= 0f || targetGroup == null)
            {
                return;
            }

            var id = target.GetInstanceID();
            if (!groupMemberIds.Add(id))
            {
                return;
            }

            targetGroup.AddMember(target, weight, radius);
        }

        private Vector3 ResolveFollowOffset(Vector3 focus)
        {
            if (attackingGoalResolver == null)
            {
                return midfieldFollowOffset;
            }

            var attackingGoal = attackingGoalResolver();
            if (attackingGoal.HasValue &&
                IsFinite(attackingGoal.Value) &&
                IsInFinalThird(focus, attackingGoal.Value))
            {
                return finalThirdFollowOffset;
            }

            return midfieldFollowOffset;
        }

        private bool IsInFinalThird(Vector3 focusOrigin, Vector3 goalPosition)
        {
            focusOrigin.y = 0f;
            goalPosition.y = 0f;
            return Vector3.Distance(focusOrigin, goalPosition) <= finalThirdGoalDistance;
        }

        private static bool IsUsableTransform(Transform value)
        {
            return value != null && value.gameObject != null && value.gameObject.activeInHierarchy;
        }

        private static bool IsFinite(Vector3 value)
        {
            return
                !float.IsNaN(value.x) &&
                !float.IsNaN(value.y) &&
                !float.IsNaN(value.z) &&
                !float.IsInfinity(value.x) &&
                !float.IsInfinity(value.y) &&
                !float.IsInfinity(value.z);
        }
    }
}
