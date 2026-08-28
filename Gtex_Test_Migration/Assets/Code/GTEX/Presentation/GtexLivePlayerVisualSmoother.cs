using System.Collections.Generic;
using FStudio.GTEX.Core;
using FStudio.MatchEngine.Players.PlayerController;
using UnityEngine;

namespace FStudio.GTEX.Presentation
{
    [DefaultExecutionOrder(10020)]
    public sealed class GtexLivePlayerVisualSmoother : MonoBehaviour
    {
        private const float MaxVisualSpeed = 7.25f;
        private const float MaxVisualTurnDegreesPerSecond = 720f;
        private const float PositionSmoothTime = 0.105f;
        private const float RotationSharpness = 11f;
        private const float HardSnapDistance = 16f;
        private const float IdleSpeed = 0.05f;
        private const float WalkSpeed = 0.55f;

        private static GtexLivePlayerVisualSmoother instance;
        private readonly Dictionary<CodeBasedController, VisualState> states = new Dictionary<CodeBasedController, VisualState>();

        private struct VisualState
        {
            public Vector3 position;
            public Vector3 velocity;
            public Quaternion rotation;
            public bool initialized;
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Install()
        {
            if (instance != null) return;
            var host = new GameObject("GTEX Live Player Visual Smoother");
            DontDestroyOnLoad(host);
            instance = host.AddComponent<GtexLivePlayerVisualSmoother>();
        }

        private void LateUpdate()
        {
            if (!GtexRuntimeState.IsStarted || GtexRuntimeState.ActiveMode != GtexRuntimeMode.LivePlayback)
            {
                states.Clear();
                return;
            }

            var players = FindObjectsByType<CodeBasedController>(FindObjectsSortMode.None);
            var seen = new HashSet<CodeBasedController>();
            var dt = Mathf.Max(Time.unscaledDeltaTime, 1f / 120f);
            for (var index = 0; index < players.Length; index++)
            {
                var player = players[index];
                if (player == null || !player.isActiveAndEnabled || player.UnityObject == null) continue;
                seen.Add(player);
                SmoothPlayer(player, dt);
            }

            var stale = new List<CodeBasedController>();
            foreach (var pair in states)
            {
                if (!seen.Contains(pair.Key) || pair.Key == null) stale.Add(pair.Key);
            }
            for (var index = 0; index < stale.Count; index++) states.Remove(stale[index]);
        }

        private void SmoothPlayer(CodeBasedController player, float dt)
        {
            var transform = player.UnityObject.transform;
            var targetPosition = transform.position;
            var targetRotation = transform.rotation;
            if (!states.TryGetValue(player, out var state) || !state.initialized)
            {
                state.position = targetPosition;
                state.rotation = targetRotation;
                state.velocity = Vector3.zero;
                state.initialized = true;
                states[player] = state;
                return;
            }

            var previousVisualPosition = state.position;
            var targetDelta = targetPosition - previousVisualPosition;
            targetDelta.y = 0f;
            var targetDistance = targetDelta.magnitude;
            if (targetDistance >= HardSnapDistance)
            {
                state.position = targetPosition;
                state.velocity = Vector3.zero;
                state.rotation = targetRotation;
                transform.SetPositionAndRotation(targetPosition, targetRotation);
                states[player] = state;
                return;
            }

            var maxSpeed = MaxVisualSpeed;
            if (targetDistance > 3f)
            {
                maxSpeed = Mathf.Min(MaxVisualSpeed, Mathf.Max(4.5f, targetDistance / PositionSmoothTime * 0.34f));
            }
            state.position = Vector3.SmoothDamp(previousVisualPosition, targetPosition, ref state.velocity, PositionSmoothTime, maxSpeed, dt);
            state.position.y = targetPosition.y;

            var movement = state.position - previousVisualPosition;
            movement.y = 0f;
            var movementSpeed = movement.magnitude / dt;
            var lookDirection = movement.sqrMagnitude > 0.0001f ? movement.normalized : targetRotation * Vector3.forward;
            lookDirection.y = 0f;
            if (lookDirection.sqrMagnitude > 0.0001f)
            {
                var desiredRotation = Quaternion.LookRotation(lookDirection.normalized, Vector3.up);
                var rotationT = 1f - Mathf.Exp(-RotationSharpness * dt);
                state.rotation = Quaternion.Slerp(state.rotation, desiredRotation, rotationT);
                if (Quaternion.Angle(state.rotation, targetRotation) > 1f)
                    state.rotation = Quaternion.RotateTowards(state.rotation, targetRotation, MaxVisualTurnDegreesPerSecond * dt);
            }

            transform.SetPositionAndRotation(state.position, state.rotation);
            var animator = player.Animator;
            if (animator != null)
            {
                var normalizedSpeed = Mathf.Clamp01(movementSpeed / MaxVisualSpeed);
                animator.SetFloat(PlayerAnimatorVariable.MoveSpeed, movementSpeed <= IdleSpeed ? 0f : Mathf.Lerp(WalkSpeed, 1f, normalizedSpeed));
            }
            states[player] = state;
        }
    }
}
