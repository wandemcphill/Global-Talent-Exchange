using System;
using System.Collections.Generic;
using UnityEngine;

namespace FStudio.GTEX.VisualBridge
{
    public sealed class GtexOriginalActionCameraDriver : MonoBehaviour
    {
        [Header("Targets")]
        [SerializeField] private Transform ball;
        [SerializeField] private Transform ballOwner;
        [SerializeField] private Transform passTarget;
        [SerializeField] private string ballOwnerId = string.Empty;
        [SerializeField] private string passTargetId = string.Empty;
        [SerializeField] private Vector3 worldPassTarget;
        [SerializeField] private bool hasWorldPassTarget;

        [Header("Camera")]
        [SerializeField] private Camera controlledCamera;
        [SerializeField] private Vector3 midfieldOffset = new Vector3(0f, 33f, -38f);
        [SerializeField] private Vector3 finalThirdOffset = new Vector3(0f, 31f, -43f);
        [SerializeField] private float smoothPosition = 5.5f;
        [SerializeField] private float smoothRotation = 7.5f;
        [SerializeField] private float maxFocusDistanceFromBall = 24f;
        [SerializeField] private float nearbyClusterRadius = 32f;
        [SerializeField] private int nearbyClusterPlayerLimit = 8;
        [SerializeField] private float finalThirdGoalDistance = 36f;
        [SerializeField] private float penaltyAreaGoalkeeperDistance = 24f;
        [SerializeField] private bool logCameraDebug = true;
        [SerializeField] private float debugLogInterval = 3f;

        private readonly List<Transform> activePlayers = new List<Transform>();
        private readonly HashSet<int> goalkeeperTransformIds = new HashSet<int>();
        private Vector3 focusVelocity;
        private Vector3 smoothedFocus;
        private Vector3 lastResolvedFocus;
        private float nextDebugLogAt;
        private bool lastFocusClamped;
        private bool lastUsedFallbackCluster;
        private Func<Transform> ballResolver;
        private Func<Vector3?> attackingGoalResolver;

        public bool HasBoundCamera => controlledCamera != null;

        public bool HasValidFocus => IsUsableTransform(ball) || IsUsableTransform(ballOwner) || CountValidPlayers() > 0;

        public string ModeName => "ActionFollow";

        public void Bind(
            Camera camera,
            Transform ballTransform,
            IEnumerable<Transform> players,
            Func<Transform> resolveBall = null,
            Func<Vector3?> resolveAttackingGoal = null,
            IEnumerable<Transform> goalkeeperTransforms = null)
        {
            controlledCamera = camera;
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

            if (smoothedFocus == Vector3.zero || !IsFinite(smoothedFocus))
            {
                smoothedFocus = ResolveFocus(out _, out _);
            }
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
            hasWorldPassTarget = target.sqrMagnitude > 0.001f;
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
            if (controlledCamera == null)
            {
                controlledCamera = Camera.main;
            }

            if (controlledCamera == null)
            {
                return;
            }

            RebindBallIfNeeded();
            var focus = ResolveFocus(out var usedFallbackCluster, out var focusClampedToBall);
            smoothedFocus = Vector3.SmoothDamp(smoothedFocus, focus, ref focusVelocity, 0.16f);

            var desiredPosition = smoothedFocus + ResolveOffset();
            controlledCamera.transform.position = Vector3.Lerp(
                controlledCamera.transform.position,
                desiredPosition,
                Time.deltaTime * smoothPosition);

            var look = smoothedFocus - controlledCamera.transform.position;
            if (look.sqrMagnitude <= 0.01f)
            {
                return;
            }

            var desiredRotation = Quaternion.LookRotation(look.normalized, Vector3.up);
            controlledCamera.transform.rotation = Quaternion.Slerp(
                controlledCamera.transform.rotation,
                desiredRotation,
                Time.deltaTime * smoothRotation);

            lastResolvedFocus = focus;
            lastFocusClamped = focusClampedToBall;
            lastUsedFallbackCluster = usedFallbackCluster;
            LogDebugStateIfNeeded();
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

        private Vector3 ResolveFocus(out bool usedFallbackCluster, out bool focusClampedToBall)
        {
            usedFallbackCluster = false;
            focusClampedToBall = false;

            if (IsUsableTransform(ball))
            {
                var ballPosition = ball.position;
                if (!IsFinite(ballPosition))
                {
                    Debug.LogWarning("[GTEX Camera] WARNING ball position invalid, using player cluster fallback");
                    usedFallbackCluster = true;
                    return ResolveFallbackClusterCenter();
                }

                Vector3 focus = ballPosition * 0.42f;
                float weight = 0.42f;

                if (IsUsableTransform(ballOwner))
                {
                    focus += ballOwner.position * 0.24f;
                    weight += 0.24f;
                }

                if (TryResolvePassTargetPosition(out var targetPosition))
                {
                    focus += targetPosition * 0.18f;
                    weight += 0.18f;
                }

                var nearbyCluster = ResolveNearbyPlayerCluster(ballPosition, out var nearbyClusterValid);
                if (nearbyClusterValid)
                {
                    focus += nearbyCluster * 0.16f;
                    weight += 0.16f;
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
                        IsBallInFinalThird(ballPosition, attackingGoal.Value))
                    {
                        focus = Vector3.Lerp(focus, attackingGoal.Value, 0.06f);
                    }
                }

                var planarFromBall = focus - ballPosition;
                planarFromBall.y = 0f;
                if (planarFromBall.magnitude > maxFocusDistanceFromBall)
                {
                    focus = ballPosition + planarFromBall.normalized * maxFocusDistanceFromBall;
                    focus.y = Mathf.Lerp(focus.y, ballPosition.y, 0.35f);
                    focusClampedToBall = true;
                }

                return focus;
            }

            usedFallbackCluster = true;
            return ResolveFallbackClusterCenter();
        }

        private Vector3 ResolveNearbyPlayerCluster(Vector3 ballPosition, out bool valid)
        {
            var maxDistanceSq = nearbyClusterRadius * nearbyClusterRadius;
            var includeGoalkeepers = IsBallNearPenaltyArea(ballPosition);
            var nearestPlayers = new Transform[Mathf.Max(1, nearbyClusterPlayerLimit)];
            var nearestDistances = new float[nearestPlayers.Length];
            for (var index = 0; index < nearestDistances.Length; index += 1)
            {
                nearestDistances[index] = float.PositiveInfinity;
            }

            for (var index = 0; index < activePlayers.Count; index += 1)
            {
                var player = activePlayers[index];
                if (!IsUsableTransform(player))
                {
                    continue;
                }

                if (!includeGoalkeepers && goalkeeperTransformIds.Contains(player.GetInstanceID()))
                {
                    continue;
                }

                var distanceSq = (player.position - ballPosition).sqrMagnitude;
                if (distanceSq > maxDistanceSq)
                {
                    continue;
                }

                InsertNearestPlayer(nearestPlayers, nearestDistances, player, distanceSq);
            }

            Vector3 sum = Vector3.zero;
            var count = 0;
            for (var index = 0; index < nearestPlayers.Length; index += 1)
            {
                var player = nearestPlayers[index];
                if (!IsUsableTransform(player))
                {
                    continue;
                }

                sum += player.position;
                count += 1;
            }

            valid = count > 0;
            return valid ? sum / count : ballPosition;
        }

        private Vector3 ResolveFallbackClusterCenter()
        {
            var seed = Vector3.zero;
            var seedCount = 0;
            for (var index = 0; index < activePlayers.Count; index += 1)
            {
                var player = activePlayers[index];
                if (!IsUsableTransform(player))
                {
                    continue;
                }

                if (goalkeeperTransformIds.Contains(player.GetInstanceID()) && CountValidPlayers() > 4)
                {
                    continue;
                }

                seed += player.position;
                seedCount += 1;
            }

            if (seedCount == 0)
            {
                return Vector3.zero;
            }

            seed /= seedCount;

            var nearestPlayers = new Transform[Mathf.Max(1, nearbyClusterPlayerLimit)];
            var nearestDistances = new float[nearestPlayers.Length];
            for (var index = 0; index < nearestDistances.Length; index += 1)
            {
                nearestDistances[index] = float.PositiveInfinity;
            }

            for (var index = 0; index < activePlayers.Count; index += 1)
            {
                var player = activePlayers[index];
                if (!IsUsableTransform(player))
                {
                    continue;
                }

                if (goalkeeperTransformIds.Contains(player.GetInstanceID()) && seedCount > 4)
                {
                    continue;
                }

                var distanceSq = (player.position - seed).sqrMagnitude;
                InsertNearestPlayer(nearestPlayers, nearestDistances, player, distanceSq);
            }

            Vector3 sum = Vector3.zero;
            var count = 0;
            for (var index = 0; index < nearestPlayers.Length; index += 1)
            {
                var player = nearestPlayers[index];
                if (!IsUsableTransform(player))
                {
                    continue;
                }

                sum += player.position;
                count += 1;
            }

            return count > 0 ? sum / count : seed;
        }

        private Vector3 ResolveOffset()
        {
            if (!IsUsableTransform(ball) || attackingGoalResolver == null)
            {
                return midfieldOffset;
            }

            var attackingGoal = attackingGoalResolver();
            if (attackingGoal.HasValue &&
                IsFinite(attackingGoal.Value) &&
                IsBallInFinalThird(ball.position, attackingGoal.Value))
            {
                return finalThirdOffset;
            }

            return midfieldOffset;
        }

        private bool TryResolvePassTargetPosition(out Vector3 targetPosition)
        {
            if (IsUsableTransform(passTarget))
            {
                targetPosition = passTarget.position;
                return true;
            }

            if (hasWorldPassTarget && IsFinite(worldPassTarget))
            {
                targetPosition = worldPassTarget;
                return true;
            }

            targetPosition = Vector3.zero;
            return false;
        }

        private bool IsBallInFinalThird(Vector3 ballPosition, Vector3 goalPosition)
        {
            ballPosition.y = 0f;
            goalPosition.y = 0f;
            return Vector3.Distance(ballPosition, goalPosition) <= finalThirdGoalDistance;
        }

        private bool IsBallNearPenaltyArea(Vector3 ballPosition)
        {
            if (attackingGoalResolver == null)
            {
                return false;
            }

            var attackingGoal = attackingGoalResolver();
            if (!attackingGoal.HasValue || !IsFinite(attackingGoal.Value))
            {
                return false;
            }

            return Vector3.Distance(new Vector3(ballPosition.x, 0f, ballPosition.z), new Vector3(attackingGoal.Value.x, 0f, attackingGoal.Value.z)) <= penaltyAreaGoalkeeperDistance;
        }

        private void LogDebugStateIfNeeded()
        {
            if (!logCameraDebug || Time.unscaledTime < nextDebugLogAt)
            {
                return;
            }

            nextDebugLogAt = Time.unscaledTime + Mathf.Max(0.5f, debugLogInterval);

            if (!IsUsableTransform(ball))
            {
                Debug.Log("[GTEX Camera] WARNING ball=null, using player cluster fallback");
            }

            if (lastFocusClamped)
            {
                Debug.Log("[GTEX Camera] WARNING focus clamped to ball radius");
            }

            var activeCameraName = controlledCamera != null ? controlledCamera.name : "(missing)";
            var ballText = IsUsableTransform(ball) ? ball.position.ToString("F2") : "(null)";
            var ownerText = string.IsNullOrWhiteSpace(ballOwnerId) ? "(none)" : ballOwnerId;
            var targetText = string.IsNullOrWhiteSpace(passTargetId) ? "(none)" : passTargetId;
            Debug.Log(
                "[GTEX Camera] ball=" + ballText +
                " owner=" + ownerText +
                " target=" + targetText +
                " focus=" + lastResolvedFocus.ToString("F2") +
                " activeCamera=" + activeCameraName +
                " mode=" + ModeName +
                (lastUsedFallbackCluster ? " fallback=cluster" : string.Empty));
        }

        private static void InsertNearestPlayer(Transform[] nearestPlayers, float[] nearestDistances, Transform candidate, float distanceSq)
        {
            for (var slot = 0; slot < nearestDistances.Length; slot += 1)
            {
                if (distanceSq >= nearestDistances[slot])
                {
                    continue;
                }

                for (var shift = nearestDistances.Length - 1; shift > slot; shift -= 1)
                {
                    nearestDistances[shift] = nearestDistances[shift - 1];
                    nearestPlayers[shift] = nearestPlayers[shift - 1];
                }

                nearestDistances[slot] = distanceSq;
                nearestPlayers[slot] = candidate;
                break;
            }
        }

        private int CountValidPlayers()
        {
            var count = 0;
            for (var index = 0; index < activePlayers.Count; index += 1)
            {
                if (IsUsableTransform(activePlayers[index]))
                {
                    count += 1;
                }
            }

            return count;
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
