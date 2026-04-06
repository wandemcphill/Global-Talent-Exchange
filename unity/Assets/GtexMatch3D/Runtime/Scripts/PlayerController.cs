using System;
using System.Collections.Generic;
using UnityEngine;

namespace Gtex.Match3D.Runtime
{
    public sealed class PlayerController : MonoBehaviour
    {
        [Serializable]
        public struct AnimationBinding
        {
            public string runtimeState;
            public string animatorState;
        }

        [SerializeField] private Animator animator;
        [SerializeField] private Renderer[] renderers;
        [SerializeField] private float positionLerpSpeed = 12f;
        [SerializeField] private float rotationLerpSpeed = 14f;
        [SerializeField] private Color homeColor = new Color(0.10f, 0.38f, 0.93f);
        [SerializeField] private Color awayColor = new Color(0.92f, 0.20f, 0.20f);
        [SerializeField] private Color highlightBoost = new Color(0.22f, 0.18f, 0.02f);
        [SerializeField] private AnimationBinding[] animationBindings =
        {
            new AnimationBinding { runtimeState = "idle", animatorState = "idle" },
            new AnimationBinding { runtimeState = "run", animatorState = "run" },
            new AnimationBinding { runtimeState = "sprint", animatorState = "sprint" },
            new AnimationBinding { runtimeState = "receive", animatorState = "receive" },
            new AnimationBinding { runtimeState = "pass", animatorState = "pass" },
            new AnimationBinding { runtimeState = "shoot", animatorState = "shoot" },
            new AnimationBinding { runtimeState = "tackle", animatorState = "tackle" },
            new AnimationBinding { runtimeState = "celebrate", animatorState = "celebrate" },
            new AnimationBinding { runtimeState = "intercept", animatorState = "intercept" },
            new AnimationBinding { runtimeState = "recover", animatorState = "recover" }
        };

        private readonly Dictionary<string, string> _animationMap =
            new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        private readonly HashSet<int> _floatParameters = new HashSet<int>();
        private readonly HashSet<int> _boolParameters = new HashSet<int>();

        private Vector3 _targetPosition;
        private Quaternion _targetRotation = Quaternion.identity;
        private Vector3 _targetVelocity;
        private string _currentAnimatorState;
        private float _speedRatio;
        private bool _highlighted;
        private bool _hasPossession;

        public string EntityId { get; private set; }
        public string PlayerId { get; private set; }
        public string TeamId { get; private set; }
        public string Side { get; private set; }
        public string PlayerLabel { get; private set; }
        public int ShirtNumber { get; private set; }

        public Vector3 TargetPosition
        {
            get { return _targetPosition; }
        }

        private void Awake()
        {
            if (animator == null)
            {
                animator = GetComponentInChildren<Animator>();
            }

            if (renderers == null || renderers.Length == 0)
            {
                renderers = GetComponentsInChildren<Renderer>(true);
            }

            BuildAnimationMap();
            CacheAnimatorParameters();
            _targetPosition = transform.position;
            _targetRotation = transform.rotation;
        }

        private void Update()
        {
            float positionFactor = DampingFactor(positionLerpSpeed, Time.deltaTime);
            float rotationFactor = DampingFactor(rotationLerpSpeed, Time.deltaTime);
            transform.position = Vector3.Lerp(transform.position, _targetPosition, positionFactor);
            transform.rotation = Quaternion.Slerp(transform.rotation, _targetRotation, rotationFactor);

            if (animator != null && HasFloatParameter("speed"))
            {
                animator.SetFloat("speed", _speedRatio);
            }

            if (animator != null && HasBoolParameter("highlighted"))
            {
                animator.SetBool("highlighted", _highlighted);
            }

            if (animator != null && HasBoolParameter("hasPossession"))
            {
                animator.SetBool("hasPossession", _hasPossession);
            }
        }

        public void ApplySceneNode(MatchSceneNodeDto node, bool immediate)
        {
            if (node == null)
            {
                return;
            }

            MatchScenePayloadDto payload = node.payload ?? new MatchScenePayloadDto();
            EntityId = node.id;
            PlayerId = StripEntityPrefix(node.id);
            TeamId = payload.teamId;
            Side = payload.side;
            PlayerLabel = payload.label;
            ShirtNumber = payload.shirtNumber;

            _targetPosition = node.position != null ? node.position.ToVector3() : transform.position;
            _targetRotation = node.rotation != null ? node.rotation.ToQuaternion() : transform.rotation;
            _targetVelocity = node.velocity != null ? node.velocity.ToVector3() : Vector3.zero;
            _speedRatio = Mathf.Clamp01(payload.speedRatio);
            _highlighted = payload.highlighted;
            _hasPossession = payload.hasPossession;

            if (immediate || Vector3.Distance(transform.position, _targetPosition) > 8f)
            {
                SnapTo(_targetPosition, _targetRotation);
            }

            gameObject.name = string.IsNullOrWhiteSpace(payload.label) ? node.id : payload.label;
            gameObject.SetActive(payload.active);

            ApplyVisualState(payload.side, payload.highlighted, payload.hasPossession);
            ApplyAnimationBlend(payload.animation);
        }

        public void ApplyReplayFrame(ReplayPlayerFrameData frame, bool immediate)
        {
            if (frame == null)
            {
                return;
            }

            EntityId = frame.id;
            PlayerId = StripEntityPrefix(frame.id);
            _targetPosition = frame.position;
            _targetRotation = frame.rotation;
            _targetVelocity = frame.velocity;
            _highlighted = frame.highlighted;
            _hasPossession = frame.hasPossession;

            if (immediate)
            {
                SnapTo(_targetPosition, _targetRotation);
            }

            ApplyVisualState(Side, frame.highlighted, frame.hasPossession);
            if (!string.IsNullOrWhiteSpace(frame.animationState))
            {
                PlayAnimation(frame.animationState, 0.10f);
            }
        }

        public void ApplySimulationPose(
            string entityId,
            string teamId,
            string side,
            string label,
            int shirtNumber,
            Vector3 position,
            Quaternion rotation,
            float speedRatio,
            bool highlighted,
            bool hasPossession,
            bool immediate)
        {
            EntityId = entityId;
            PlayerId = StripEntityPrefix(entityId);
            TeamId = teamId;
            Side = side;
            PlayerLabel = label;
            ShirtNumber = shirtNumber;

            _targetPosition = position;
            _targetRotation = rotation;
            _targetVelocity = (position - transform.position) * Mathf.Max(1f, speedRatio);
            _speedRatio = Mathf.Clamp01(speedRatio);
            _highlighted = highlighted;
            _hasPossession = hasPossession;

            if (immediate || Vector3.Distance(transform.position, _targetPosition) > 8f)
            {
                SnapTo(_targetPosition, _targetRotation);
            }

            gameObject.name = string.IsNullOrWhiteSpace(label) ? entityId : label;
            gameObject.SetActive(true);

            ApplyVisualState(side, highlighted, hasPossession);
            PlayAnimation(ResolveLocomotionState(speedRatio), immediate ? 0.01f : 0.12f);
        }

        public void PlayAnimation(string runtimeState, float blendDuration = 0.20f)
        {
            if (animator == null || string.IsNullOrWhiteSpace(runtimeState))
            {
                return;
            }

            string animatorState = ResolveAnimatorState(runtimeState);
            if (string.Equals(_currentAnimatorState, animatorState, StringComparison.Ordinal))
            {
                return;
            }

            _currentAnimatorState = animatorState;
            animator.CrossFade(animatorState, Mathf.Max(0.01f, blendDuration), 0);
        }

        public ReplayPlayerFrameData BuildReplayFrame()
        {
            ReplayPlayerFrameData frame = new ReplayPlayerFrameData();
            frame.id = EntityId;
            frame.position = transform.position;
            frame.rotation = transform.rotation;
            frame.velocity = _targetVelocity;
            frame.animationState = _currentAnimatorState;
            frame.highlighted = _highlighted;
            frame.hasPossession = _hasPossession;
            return frame;
        }

        public void SnapTo(Vector3 position, Quaternion rotation)
        {
            transform.position = position;
            transform.rotation = rotation;
            _targetPosition = position;
            _targetRotation = rotation;
        }

        private void ApplyAnimationBlend(MatchAnimationBlendDto animation)
        {
            if (animation == null)
            {
                return;
            }

            string desiredState = !string.IsNullOrWhiteSpace(animation.targetState)
                ? animation.targetState
                : animation.currentState;

            if (string.IsNullOrWhiteSpace(desiredState))
            {
                return;
            }

            float blendDuration = animation.durationMs > 0 ? animation.durationMs / 1000f : 0.16f;
            PlayAnimation(desiredState, blendDuration);
        }

        private void ApplyVisualState(string side, bool highlighted, bool hasPossession)
        {
            if (renderers == null)
            {
                return;
            }

            Color baseColor = string.Equals(side, "away", StringComparison.OrdinalIgnoreCase)
                ? awayColor
                : homeColor;

            if (highlighted)
            {
                baseColor += highlightBoost;
            }

            if (hasPossession)
            {
                baseColor = Color.Lerp(baseColor, Color.white, 0.15f);
            }

            for (int index = 0; index < renderers.Length; index += 1)
            {
                Renderer renderer = renderers[index];
                if (renderer == null)
                {
                    continue;
                }

                Material material = renderer.material;
                if (material.HasProperty("_BaseColor"))
                {
                    material.SetColor("_BaseColor", baseColor);
                }

                if (material.HasProperty("_Color"))
                {
                    material.color = baseColor;
                }
            }
        }

        private void BuildAnimationMap()
        {
            _animationMap.Clear();
            for (int index = 0; index < animationBindings.Length; index += 1)
            {
                AnimationBinding binding = animationBindings[index];
                if (string.IsNullOrWhiteSpace(binding.runtimeState) ||
                    string.IsNullOrWhiteSpace(binding.animatorState))
                {
                    continue;
                }

                _animationMap[binding.runtimeState] = binding.animatorState;
            }
        }

        private void CacheAnimatorParameters()
        {
            _floatParameters.Clear();
            _boolParameters.Clear();

            if (animator == null)
            {
                return;
            }

            AnimatorControllerParameter[] parameters = animator.parameters;
            for (int index = 0; index < parameters.Length; index += 1)
            {
                AnimatorControllerParameter parameter = parameters[index];
                if (parameter.type == AnimatorControllerParameterType.Float)
                {
                    _floatParameters.Add(parameter.nameHash);
                }
                else if (parameter.type == AnimatorControllerParameterType.Bool)
                {
                    _boolParameters.Add(parameter.nameHash);
                }
            }
        }

        private bool HasFloatParameter(string name)
        {
            return _floatParameters.Contains(Animator.StringToHash(name));
        }

        private bool HasBoolParameter(string name)
        {
            return _boolParameters.Contains(Animator.StringToHash(name));
        }

        private string ResolveAnimatorState(string runtimeState)
        {
            string mappedState;
            if (_animationMap.TryGetValue(runtimeState, out mappedState))
            {
                return mappedState;
            }

            return runtimeState;
        }

        private static string ResolveLocomotionState(float speedRatio)
        {
            if (speedRatio >= 0.8f)
            {
                return "sprint";
            }

            if (speedRatio >= 0.2f)
            {
                return "run";
            }

            return "idle";
        }

        private static string StripEntityPrefix(string entityId)
        {
            if (string.IsNullOrWhiteSpace(entityId))
            {
                return null;
            }

            int separatorIndex = entityId.IndexOf(':');
            return separatorIndex >= 0 ? entityId.Substring(separatorIndex + 1) : entityId;
        }

        private static float DampingFactor(float speed, float deltaTime)
        {
            if (speed <= 0f)
            {
                return 1f;
            }

            return 1f - Mathf.Exp(-speed * deltaTime);
        }
    }
}
