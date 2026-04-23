using FStudio.MatchEngine.Balls;
using FStudio.MatchEngine.Enums;
using FStudio.MatchEngine;
using UnityEngine;

using FStudio.MatchEngine.Players.Behaviours;
using FStudio.MatchEngine.Utilities;
using System;
using FStudio.MatchEngine.Graphics.EventRenderer;

namespace FStudio.MatchEngine.Players.PlayerController
{
    [RequireComponent(typeof(Rigidbody))]
    [RequireComponent(typeof(CapsuleCollider))]
    public partial class CodeBasedController : MonoBehaviour, IPlayerController
    {
        public GameObject UnityObject => gameObject;
        public CapsuleCollider UnityCollider => collider;

        public Vector3 Position => transform.position;
        public Quaternion Rotation => transform.rotation;
        public Vector3 Forward => transform.forward;

        public Action<Collision> CollisionEnterEvent { get; set; }

        [SerializeField] private bool debugger;
        public bool IsDebuggerEnabled => debugger;

        public Vector3 Direction { get; private set; }

        private bool m_IsPhysicsEnabled;

        public bool IsPhysicsEnabled
        {
            get => m_IsPhysicsEnabled;
            set
            {
                m_IsPhysicsEnabled = value;

                if (rigidbody != null && !externalPlaybackEnabled)
                    rigidbody.isKinematic = !value;

                if (collider != null && !externalPlaybackEnabled)
                    collider.enabled = value;
            }
        }

        public float MoveSpeed { get; set; }
        public float TargetMoveSpeed { get; set; }

        public PlayerAnimator Animator => playerAnimator;
        public PlayerUI UI => playerUI;

        public PlayerBase BasePlayer { get; set; }

        private Transform shadow;

        [SerializeField] private PlayerAnimator playerAnimator;
        [SerializeField] private PlayerGraphic playerGraphic;
        [SerializeField] private PlayerUI playerUI;

#pragma warning disable 0109
        [HideInInspector][SerializeField] private new Rigidbody rigidbody;
        [HideInInspector][SerializeField] private new CapsuleCollider collider;
#pragma warning restore 0109

        public float Height => collider != null ? collider.height : 0f;

        private Vector3 targetAnimatorDirection;
        private Vector3 targetPosition;
        private bool externalPlaybackEnabled;
        private bool hasExternalPlaybackPose;
        private Vector3 externalPlaybackTargetPosition;
        private Quaternion externalPlaybackTargetRotation = Quaternion.identity;

        [SerializeField] private float externalPlaybackMoveSpeed = 24f;
        [SerializeField] private float externalPlaybackTurnSpeed = 16f;
        [SerializeField] private float externalPlaybackTeleportDistance = 4f;

        private void Awake()
        {
            rigidbody = GetComponent<Rigidbody>();
            collider = GetComponent<CapsuleCollider>();

            if (rigidbody != null)
            {
                rigidbody.collisionDetectionMode = CollisionDetectionMode.ContinuousSpeculative;
                rigidbody.interpolation = RigidbodyInterpolation.Interpolate;
                rigidbody.linearDamping = 1;
                rigidbody.constraints = RigidbodyConstraints.FreezeRotation | RigidbodyConstraints.FreezePositionY;
            }
        }

        private void FixedUpdate()
        {
            if (!externalPlaybackEnabled || !hasExternalPlaybackPose || rigidbody == null)
            {
                return;
            }

            var nextPosition = Vector3.MoveTowards(
                rigidbody.position,
                externalPlaybackTargetPosition,
                externalPlaybackMoveSpeed * Time.fixedDeltaTime);

            var turnT = 1f - Mathf.Exp(-externalPlaybackTurnSpeed * Time.fixedDeltaTime);
            var nextRotation = Quaternion.Slerp(rigidbody.rotation, externalPlaybackTargetRotation, turnT);

            rigidbody.MovePosition(nextPosition);
            rigidbody.MoveRotation(nextRotation);
        }

        private void Start()
        {
            if (BasePlayer != null)
            {
                playerAnimator.SetFloat(PlayerAnimatorVariable.Agility, 0.5f + (BasePlayer.MatchPlayer.ActualAgility / 200f));
                UI.SetName(BasePlayer.MatchPlayer.Player.Name);
            }
        }

        private void OnDestroy()
        {
            if (shadow != null)
            {
                shadow.gameObject.SetActive(false);
            }
        }

        private void OnValidate()
        {
            rigidbody = GetComponent<Rigidbody>();
            collider = GetComponent<CapsuleCollider>();
        }

        public void SetAsLineReferee()
        {
            playerGraphic.SetRefereeFlag(true);
        }

        public bool IsAnimationABlocker(in string[] clips)
        {
            return playerAnimator.IsCurrentClipBlocker(clips);
        }

        public void SetOffside(bool isInOffide)
        {
            playerUI.SetBool(PlayerUI.UIAnimatorVariable.ShowOffside, isInOffide);
        }

        public void SetUI(bool value)
        {
            playerUI.SetBool(PlayerUI.UIAnimatorVariable.ShowName, value);
        }

        public void SetInstantPosition(Vector3 position)
        {
            position.y = ResolveGroundedY();
            transform.position = position;

            if (rigidbody != null)
                rigidbody.position = position;
        }

        public void SetInstantRotation(Quaternion rotation)
        {
            if (rigidbody != null)
                rigidbody.rotation = rotation;

            transform.rotation = rotation;
        }

        public void SetExternalPlayback(bool value)
        {
            externalPlaybackEnabled = value;
            if (value)
            {
                m_IsPhysicsEnabled = true;
            }

            if (rigidbody != null)
            {
                rigidbody.linearVelocity = Vector3.zero;
                rigidbody.angularVelocity = Vector3.zero;
                rigidbody.isKinematic = value || !m_IsPhysicsEnabled;
            }

            if (collider != null)
            {
                collider.enabled = value ? false : m_IsPhysicsEnabled;
            }

            hasExternalPlaybackPose = false;
        }

        public void SetExternalPlaybackPose(Vector3 position, Quaternion rotation, bool snap = false)
        {
            rotation = Quaternion.Euler(0f, rotation.eulerAngles.y, 0f);

            externalPlaybackTargetPosition = position;
            externalPlaybackTargetRotation = rotation;
            hasExternalPlaybackPose = true;

            if (!externalPlaybackEnabled || rigidbody == null)
            {
                SetInstantPosition(position);
                SetInstantRotation(rotation);
                return;
            }

            if (snap || Vector3.Distance(rigidbody.position, position) >= ResolveExternalPlaybackTeleportDistance())
            {
                rigidbody.position = position;
                rigidbody.rotation = rotation;
                transform.SetPositionAndRotation(position, rotation);
            }
        }

        public void SetPosition(Vector3 position)
        {
            position.y = ResolveGroundedY();

            if (rigidbody != null)
                rigidbody.position = position;

            transform.position = position;
        }

        private static float ResolveGroundedY()
        {
            var pitchSpace = MatchManager.Current != null ? MatchManager.Current.ExternalPlaybackPitchSpace : null;
            return pitchSpace != null ? pitchSpace.GrassY : 0f;
        }

        private float ResolveExternalPlaybackTeleportDistance()
        {
            if (MatchManager.Current != null)
            {
                return Mathf.Max(0.5f, MatchManager.Current.ExternalPlaybackTeleportDistance);
            }

            return Mathf.Max(0.5f, externalPlaybackTeleportDistance);
        }

        public void SetRotation(Quaternion rotation)
        {
            rotation.eulerAngles = new Vector3(0, rotation.eulerAngles.y, 0);

            if (rigidbody != null)
                rigidbody.rotation = rotation;

            transform.rotation = rotation;
        }

        public void LerpRotation(in float deltaTime, Quaternion rotation, float agility)
        {
            if (rigidbody == null) return;

            rigidbody.rotation = Quaternion.Slerp(
                transform.rotation,
                rotation,
                deltaTime * agility);

            transform.rotation = rigidbody.rotation;
        }

        public void SetHeadLook(in float dT, Vector3 target, float weight)
        {
            playerAnimator.SetLook(in dT, target, weight);
        }

        public void SetPlayer(int number, PlayerBase basePlayer, Material kitMaterial)
        {
            this.BasePlayer = basePlayer;
            if (playerGraphic != null && basePlayer != null && basePlayer.MatchPlayer != null)
            {
                playerGraphic.SetPlayer(number, kitMaterial, basePlayer.MatchPlayer.Player);
            }
        }

        public bool MoveTo(in float deltaTime, Vector3 targetPosition, bool faceTowards = true, MovementType movementType = MovementType.BestHeCanDo)
        {
            return false;
        }

        public bool LookTo(in float deltaTime, Vector3 lookDirection)
        {
            return true;
        }

        public void Stop(in float deltaTime)
        {
        }

        public void ProcessMovement(in float time, in float deltaTime)
        {
        }

        public void Up(in float dT, MatchStatus matchStatus, Ball ball)
        {
        }

        public bool HitBall(in Vector3 targetVelocity, PlayerAnimatorVariable animatorVariable, out PlayerAnimatorVariable result, in float ballHoldTime, bool disableVolley = false)
        {
            result = animatorVariable;
            return false;
        }

        private void OnCollisionEnter(Collision collision)
        {
            CollisionEnterEvent?.Invoke(collision);
        }

        private void LateUpdate()
        {
            if (shadow != null)
                shadow.position = Position;
        }

        public void BallHitEvent()
        {
            BasePlayer?.BallHitEvent();
        }
    }
}
