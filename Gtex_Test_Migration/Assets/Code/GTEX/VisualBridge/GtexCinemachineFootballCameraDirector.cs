using System;
using System.Collections;
using System.Collections.Generic;
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
        private Behaviour brain;
        private Behaviour footballCamera;
        private Component targetGroup;
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
        private bool missingCinemachineLogged;
        private static Type cachedBrainType;
        private static Type cachedCameraType;
        private static Type cachedTargetGroupType;
        private static Type cachedFollowType;
        private static Type cachedRotationComposerType;
        private static Type cachedGroupFramingType;
        private static bool cinemachineTypesResolved;

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
            if (outputCamera == null || !TryResolveCinemachineRuntime())
            {
                return;
            }

            brain = GetOptionalComponent(outputCamera.gameObject, cachedBrainType) as Behaviour;
            if (brain == null)
            {
                brain = AddOptionalComponent(outputCamera.gameObject, cachedBrainType) as Behaviour;
            }

            brain.enabled = true;
            SetOptionalMember(brain, "ShowDebugText", false);

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
                targetGroup = AddOptionalComponent(groupObject, cachedTargetGroupType);
            }
            else if (targetGroup == null)
            {
                targetGroup = GetOptionalComponent(groupMarkerRoot.gameObject, cachedTargetGroupType);
                if (targetGroup == null)
                {
                    targetGroup = AddOptionalComponent(groupMarkerRoot.gameObject, cachedTargetGroupType);
                }
            }

            focusAnchor = EnsureMarker(focusAnchor, "GTEX_CinemachineFocusAnchor");
            worldPassTargetMarker = EnsureMarker(worldPassTargetMarker, "GTEX_CinemachineWorldPassTarget");
            attackingGoalMarker = EnsureMarker(attackingGoalMarker, "GTEX_CinemachineAttackingGoal");

            if (footballCamera == null)
            {
                var cameraObject = new GameObject("GTEX_CinemachineFootballCamera");
                cameraObject.transform.SetParent(runtimeRoot, false);
                cameraObject.transform.position = outputCamera.transform.position;
                cameraObject.transform.rotation = outputCamera.transform.rotation;
                footballCamera = AddOptionalComponent(cameraObject, cachedCameraType) as Behaviour;
                SetOptionalMember(footballCamera, "Priority", 100);
            }

            ConfigurePipeline();
            SetOptionalMember(footballCamera, "Follow", focusAnchor);
            SetOptionalMember(footballCamera, "LookAt", groupMarkerRoot);
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

        private void ConfigurePipeline()
        {
            if (footballCamera == null)
            {
                return;
            }

            var positionComposer = GetOptionalComponent(footballCamera.gameObject, ResolveType("Unity.Cinemachine.CinemachinePositionComposer"));
            if (positionComposer != null)
            {
                if (positionComposer is Behaviour positionComposerBehaviour)
                {
                    positionComposerBehaviour.enabled = false;
                }
            }

            var follow = GetOptionalComponent(footballCamera.gameObject, cachedFollowType);
            if (follow == null)
            {
                follow = AddOptionalComponent(footballCamera.gameObject, cachedFollowType);
            }

            SetOptionalMember(follow, "FollowOffset", midfieldFollowOffset);

            var rotationComposer = GetOptionalComponent(footballCamera.gameObject, cachedRotationComposerType);
            if (rotationComposer == null)
            {
                rotationComposer = AddOptionalComponent(footballCamera.gameObject, cachedRotationComposerType);
            }

            SetOptionalMember(rotationComposer, "TargetOffset", new Vector3(0f, 1.15f, 0f));
            SetOptionalMember(rotationComposer, "Damping", aimDamping);
            SetOptionalMember(rotationComposer, "CenterOnActivate", true);

            var groupFraming = GetOptionalComponent(footballCamera.gameObject, cachedGroupFramingType);
            if (groupFraming == null)
            {
                groupFraming = AddOptionalComponent(footballCamera.gameObject, cachedGroupFramingType);
            }

            SetOptionalMember(groupFraming, "FramingSize", framingSize);
            SetOptionalMember(groupFraming, "CenterOffset", new Vector2(0f, 0.02f));
            SetOptionalMember(groupFraming, "Damping", 0.2f);
            SetOptionalMember(groupFraming, "DollyRange", new Vector2(0f, 0f));
            SetOptionalMember(groupFraming, "FovRange", new Vector2(32f, 48f));
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

            var follow = footballCamera != null ? GetOptionalComponent(footballCamera.gameObject, cachedFollowType) : null;
            if (follow != null)
            {
                SetOptionalMember(follow, "FollowOffset", ResolveFollowOffset(focus));
            }
        }

        private void RebuildTargetGroup()
        {
            if (!HasBoundCamera)
            {
                return;
            }

            groupMemberIds.Clear();
            ClearTargetGroupMembers();

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

            _ = GetOptionalMember(targetGroup, "IsEmpty");
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

            InvokeOptionalMethod(targetGroup, "AddMember", target, weight, radius);
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

        private static void EnsureCinemachineTypesResolved()
        {
            if (cinemachineTypesResolved)
            {
                return;
            }

            cinemachineTypesResolved = true;
            cachedBrainType = ResolveType("Unity.Cinemachine.CinemachineBrain");
            cachedCameraType = ResolveType("Unity.Cinemachine.CinemachineCamera");
            cachedTargetGroupType = ResolveType("Unity.Cinemachine.CinemachineTargetGroup");
            cachedFollowType = ResolveType("Unity.Cinemachine.CinemachineFollow");
            cachedRotationComposerType = ResolveType("Unity.Cinemachine.CinemachineRotationComposer");
            cachedGroupFramingType = ResolveType("Unity.Cinemachine.CinemachineGroupFraming");
        }

        private bool TryResolveCinemachineRuntime()
        {
            EnsureCinemachineTypesResolved();
            var resolved =
                cachedBrainType != null &&
                cachedCameraType != null &&
                cachedTargetGroupType != null;
            if (!resolved && !missingCinemachineLogged)
            {
                missingCinemachineLogged = true;
                Debug.LogWarning("[GTEX Camera] Cinemachine package types were not resolved. Director will stay inactive.");
            }

            return resolved;
        }

        private static Type ResolveType(string fullName)
        {
            if (string.IsNullOrWhiteSpace(fullName))
            {
                return null;
            }

            var direct = Type.GetType(fullName, false);
            if (direct != null)
            {
                return direct;
            }

            var assemblies = AppDomain.CurrentDomain.GetAssemblies();
            for (var index = 0; index < assemblies.Length; index += 1)
            {
                var type = assemblies[index].GetType(fullName, false);
                if (type != null)
                {
                    return type;
                }
            }

            return null;
        }

        private static Component GetOptionalComponent(GameObject target, Type componentType)
        {
            return target != null && componentType != null ? target.GetComponent(componentType) : null;
        }

        private static Component AddOptionalComponent(GameObject target, Type componentType)
        {
            return target != null && componentType != null ? target.AddComponent(componentType) : null;
        }

        private static object GetOptionalMember(object target, string memberName)
        {
            if (target == null || string.IsNullOrWhiteSpace(memberName))
            {
                return null;
            }

            var targetType = target.GetType();
            var property = targetType.GetProperty(memberName);
            if (property != null && property.CanRead)
            {
                return property.GetValue(target, null);
            }

            var field = targetType.GetField(memberName);
            return field != null ? field.GetValue(target) : null;
        }

        private static void SetOptionalMember(object target, string memberName, object value)
        {
            if (target == null || string.IsNullOrWhiteSpace(memberName))
            {
                return;
            }

            var targetType = target.GetType();
            var property = targetType.GetProperty(memberName);
            if (property != null && property.CanWrite && value != null && property.PropertyType.IsAssignableFrom(value.GetType()))
            {
                property.SetValue(target, value, null);
                return;
            }

            if (property != null && property.CanWrite && value == null)
            {
                property.SetValue(target, null, null);
                return;
            }

            var field = targetType.GetField(memberName);
            if (field != null && value != null && field.FieldType.IsAssignableFrom(value.GetType()))
            {
                field.SetValue(target, value);
                return;
            }

            if (field != null && value == null)
            {
                field.SetValue(target, null);
            }
        }

        private static void InvokeOptionalMethod(object target, string methodName, params object[] args)
        {
            if (target == null || string.IsNullOrWhiteSpace(methodName))
            {
                return;
            }

            var methods = target.GetType().GetMethods();
            for (var index = 0; index < methods.Length; index += 1)
            {
                var method = methods[index];
                if (!string.Equals(method.Name, methodName, StringComparison.Ordinal))
                {
                    continue;
                }

                var parameters = method.GetParameters();
                if (parameters.Length != (args != null ? args.Length : 0))
                {
                    continue;
                }

                var compatible = true;
                for (var parameterIndex = 0; parameterIndex < parameters.Length; parameterIndex += 1)
                {
                    var argument = args[parameterIndex];
                    if (argument == null)
                    {
                        continue;
                    }

                    if (!parameters[parameterIndex].ParameterType.IsAssignableFrom(argument.GetType()))
                    {
                        compatible = false;
                        break;
                    }
                }

                if (!compatible)
                {
                    continue;
                }

                method.Invoke(target, args);
                return;
            }
        }

        private void ClearTargetGroupMembers()
        {
            if (targetGroup == null)
            {
                return;
            }

            var targetsValue = GetOptionalMember(targetGroup, "Targets");
            if (targetsValue is IList targetsList)
            {
                targetsList.Clear();
            }
        }
    }
}
