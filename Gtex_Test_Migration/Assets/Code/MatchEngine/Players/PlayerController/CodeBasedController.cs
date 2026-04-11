using FStudio.MatchEngine.Balls;
using FStudio.MatchEngine.Enums;
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

                if (rigidbody != null)
                    rigidbody.isKinematic = !value;

                if (collider != null)
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

        private void Awake()
        {
            rigidbody = GetComponent<Rigidbody>();
            collider = GetComponent<CapsuleCollider>();

            if (rigidbody != null)
            {
                rigidbody.collisionDetectionMode = CollisionDetectionMode.ContinuousSpeculative;
                rigidbody.interpolation = RigidbodyInterpolation.Extrapolate;
                rigidbody.linearDamping = 1;
                rigidbody.constraints = RigidbodyConstraints.FreezeRotation | RigidbodyConstraints.FreezePositionY;
            }
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
            position.y = 0;
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

        public void SetPosition(Vector3 position)
        {
            position.y = 0;

            if (rigidbody != null)
                rigidbody.position = position;

            transform.position = position;
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
