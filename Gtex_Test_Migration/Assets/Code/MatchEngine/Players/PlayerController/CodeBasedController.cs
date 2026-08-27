using FStudio.MatchEngine.Balls;
using FStudio.MatchEngine.Enums;
using FStudio.MatchEngine;
using FStudio.GTEX.Engine;
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

        public Vector3 Position
        {
            get
            {
                if (this == null || gameObject == null || !gameObject)
                {
                    return lastKnownPosition;
                }
                if (transform == null)
                {
                    return lastKnownPosition;
                }
                lastKnownPosition = transform.position;
                return lastKnownPosition;
            }
        }
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
                if (rigidbody != null && !externalPlaybackEnabled) rigidbody.isKinematic = !value;
                if (collider != null && !externalPlaybackEnabled) collider.enabled = value;
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
        private Vector2 targetAnimatorDirection;
        private Vector3 targetPosition;
        private Vector3 lastKnownPosition;
        private bool externalPlaybackEnabled;
        private bool hasExternalPlaybackPose;
        private Vector3 externalPlaybackTargetPosition;
        private Quaternion externalPlaybackTargetRotation = Quaternion.identity;
        [SerializeField] private float externalPlaybackMoveSpeed = 24f;
        [SerializeField] private float externalPlaybackTurnSpeed = 16f;
        [SerializeField] private float externalPlaybackTeleportDistance = 4f;
        private const float LegacyAnimatorParameterLerpSpeed = 4f;
        private const float LegacyMovementDirectionSpeedLeaningModifier = 2f;
        private const float LegacyMovementDirectionAngleLeaningModifier = 0.05f;
        private const float LegacyDirectionRecoveryWhenStop = 5f;
        private const float LegacyStoppingSpeed = 5f;
        private const float LegacyMinMoveSpeedToMove = 0.5f;
        private const float LegacyLookApprovalAngle = 60f;
        private const float LegacyLookBallHeightApprovalBonus = 60f;
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
            lastKnownPosition = transform != null ? transform.position : Vector3.zero;
        }
        private void FixedUpdate()
        {
            if (externalPlaybackEnabled) return;
        }
        private void Start() { ApplyBasePlayerPresentation(); }
        private void OnDestroy() { if (shadow != null) shadow.gameObject.SetActive(false); }
        private void OnValidate() { rigidbody = GetComponent<Rigidbody>(); collider = GetComponent<CapsuleCollider>(); }
        public void SetAsLineReferee() { playerGraphic.SetRefereeFlag(true); }
        public bool IsAnimationABlocker(in string[] clips) { return playerAnimator.IsCurrentClipBlocker(clips); }
        public void SetOffside(bool isInOffide) { playerUI.SetBool(PlayerUI.UIAnimatorVariable.ShowOffside, isInOffide); }
        public void SetUI(bool value) { playerUI.SetBool(PlayerUI.UIAnimatorVariable.ShowName, value); }
        public void SetInstantPosition(Vector3 position)
        {
            position.y = ResolveGroundedY(); transform.position = position; lastKnownPosition = position; if (rigidbody != null) rigidbody.position = position;
        }
        public void SetInstantRotation(Quaternion rotation) { if (rigidbody != null) rigidbody.rotation = rotation; transform.rotation = rotation; }
        public void SetExternalPlayback(bool value)
        {
            externalPlaybackEnabled = value;
            if (value) m_IsPhysicsEnabled = true;
            if (rigidbody != null)
            {
                GtexPlaybackPhysicsUtil.SafeSetRigidbodyVelocity(rigidbody, Vector3.zero, Vector3.zero);
                rigidbody.isKinematic = value || !m_IsPhysicsEnabled;
                rigidbody.interpolation = value ? RigidbodyInterpolation.None : RigidbodyInterpolation.Interpolate;
            }
            if (collider != null) collider.enabled = value ? false : m_IsPhysicsEnabled;
            hasExternalPlaybackPose = false;
        }
        public void SetExternalPlaybackPose(Vector3 position, Quaternion rotation, bool snap = false)
        {
            rotation = Quaternion.Euler(0f, rotation.eulerAngles.y, 0f);
            externalPlaybackTargetPosition = position;
            externalPlaybackTargetRotation = rotation;
            hasExternalPlaybackPose = true;
            if (!externalPlaybackEnabled || rigidbody == null) { SetInstantPosition(position); SetInstantRotation(rotation); return; }
            GtexPlaybackPhysicsUtil.ApplyExternalPlaybackPosition(transform, rigidbody, position, rotation, snap);
            lastKnownPosition = transform.position;
        }
        public void SetPosition(Vector3 position)
        {
            position.y = ResolveGroundedY(); lastKnownPosition = position; if (rigidbody != null) rigidbody.position = position; transform.position = position;
        }
        private static float ResolveGroundedY()
        {
            var pitchSpace = MatchManager.Current != null ? MatchManager.Current.ExternalPlaybackPitchSpace : null;
            return pitchSpace != null ? pitchSpace.GrassY : 0f;
        }
        private float ResolveExternalPlaybackTeleportDistance() => MatchManager.Current != null ? Mathf.Max(0.5f, MatchManager.Current.ExternalPlaybackTeleportDistance) : Mathf.Max(0.5f, externalPlaybackTeleportDistance);
        public void SetRotation(Quaternion rotation)
        {
            rotation.eulerAngles = new Vector3(0, rotation.eulerAngles.y, 0); if (rigidbody != null) rigidbody.rotation = rotation; transform.rotation = rotation;
        }
        public void LerpRotation(in float deltaTime, Quaternion rotation, float agility)
        {
            if (rigidbody == null) return; rigidbody.rotation = Quaternion.Slerp(transform.rotation, rotation, deltaTime * agility); transform.rotation = rigidbody.rotation;
        }
        public void SetHeadLook(in float dT, Vector3 target, float weight) { playerAnimator.SetLook(in dT, target, weight); }
        private (float turnResult, float angleDifferency) AgileToDirection(Vector3 targetDirection)
        {
            targetDirection.y = 0f; if (targetDirection.sqrMagnitude <= 0.0001f) return (1f, 0f); targetDirection.Normalize(); var currentDirection = Direction; currentDirection.y = 0f; if (currentDirection.sqrMagnitude <= 0.0001f) currentDirection = transform.forward; currentDirection.y = 0f; if (currentDirection.sqrMagnitude <= 0.0001f) currentDirection = targetDirection; else currentDirection.Normalize(); var angleDifferency = Mathf.Abs(Vector3.SignedAngle(currentDirection, targetDirection, Vector3.up)); var agility = BasePlayer != null && BasePlayer.MatchPlayer != null ? Mathf.Max(0.25f, BasePlayer.MatchPlayer.GetAgility()) : 4f; var settings = EngineSettings.Current; var moveHardness = settings != null && settings.AgileToDirectionMoveSpeedHardness != null ? settings.AgileToDirectionMoveSpeedHardness.Evaluate(MoveSpeed) : Mathf.Lerp(0.8f, 1.8f, Mathf.Clamp01(MoveSpeed / 6f)); var angleHardness = settings != null && settings.AgileToDirectionAngleDifferencyHardness != null ? settings.AgileToDirectionAngleDifferencyHardness.Evaluate(angleDifferency) : Mathf.Lerp(0.6f, 2.25f, Mathf.InverseLerp(0f, 180f, angleDifferency)); var turnDifficulty = Mathf.Max(0.1f, moveHardness * angleHardness); var turnResult = Mathf.Clamp(agility / (turnDifficulty + 1f), 0.25f, 12f); return (turnResult, angleDifferency);
        }
        private void CalculateAnimatorDirection()
        {
            var forward = transform.forward; forward.y = 0f; if (forward.sqrMagnitude <= 0.0001f) forward = Vector3.forward; else forward.Normalize(); var desiredDirection = Direction; desiredDirection.y = 0f; if (desiredDirection.sqrMagnitude <= 0.0001f) { targetAnimatorDirection = Vector2.zero; return; } desiredDirection.Normalize(); var angle = Vector3.SignedAngle(forward, desiredDirection, Vector3.up); targetAnimatorDirection = new Vector2(Mathf.Cos(angle * Mathf.Deg2Rad), Mathf.Sin(angle * Mathf.Deg2Rad));
        }
        public void SetPlayer(int number, PlayerBase basePlayer, Material kitMaterial)
        {
            BasePlayer = basePlayer; if (playerGraphic != null && basePlayer != null && basePlayer.MatchPlayer != null) playerGraphic.SetPlayer(number, kitMaterial, basePlayer.MatchPlayer.Player); ApplyBasePlayerPresentation(); if (shadow == null && ShadowRenderer.Current != null) shadow = ShadowRenderer.Current.Get();
        }
        private void ApplyBasePlayerPresentation()
        {
            if (BasePlayer == null || BasePlayer.MatchPlayer == null || BasePlayer.MatchPlayer.Player == null) return; gameObject.name = BasePlayer.MatchPlayer.Player.Name; if (playerAnimator != null) playerAnimator.SetFloat(PlayerAnimatorVariable.Agility, BasePlayer.MatchPlayer.ActualAgility / 100f); if (UI != null) UI.SetName(BasePlayer.MatchPlayer.Player.Name);
        }
        public bool MoveTo(in float deltaTime, Vector3 targetPosition, bool faceTowards = true, MovementType movementType = MovementType.BestHeCanDo)
        {
            if (externalPlaybackEnabled) return false; this.targetPosition = targetPosition; targetPosition.y = ResolveGroundedY(); var distance = Vector3.Distance(Position, targetPosition); var targetDirection = targetPosition - Position; targetDirection.y = 0f; var reachRadius = collider != null ? collider.radius : 0.35f; if (distance > reachRadius) { if (targetDirection.sqrMagnitude <= 0.0001f) { targetDirection = transform.forward; targetDirection.y = 0f; } targetDirection.Normalize(); var newRotation = Quaternion.LookRotation(targetDirection); var directionAgile = AgileToDirection(targetDirection); if (Direction.sqrMagnitude > 0.0001f) { var currentRotation = Quaternion.LookRotation(Direction.normalized); Direction = Quaternion.Slerp(currentRotation, newRotation, Mathf.Max(deltaTime, 0f) * directionAgile.turnResult) * Vector3.forward; } else Direction = newRotation * Vector3.forward; var targetMovement = 1f - (directionAgile.angleDifferency / 180f); switch (movementType) { case MovementType.Relax: targetMovement *= 0.25f; break; case MovementType.Normal: targetMovement *= 0.75f; break; } TargetMoveSpeed = Mathf.Clamp01(targetMovement); } else { Stop(in deltaTime); return true; } if (faceTowards) LookTo(in deltaTime, targetPosition - Position); return false;
        }
        public bool LookTo(in float deltaTime, Vector3 lookDirection)
        {
            if (externalPlaybackEnabled) return false; lookDirection.y = 0f; if (lookDirection.sqrMagnitude <= 0.0001f) return true; lookDirection.Normalize(); var agileSpeed = AgileToDirection(lookDirection).turnResult; var holdingBallModifier = BasePlayer != null && BasePlayer.IsHoldingBall ? Mathf.Max(1f, EngineSettings.Current != null ? EngineSettings.Current.AgileToDirectionWhenHoldingBallModifier : 1f) : 1f; LerpRotation(in deltaTime, Quaternion.LookRotation(lookDirection, Vector3.up), agileSpeed * holdingBallModifier); var angle = Vector3.SignedAngle(transform.forward, lookDirection, Vector3.up); var ballHeightMod = 0f; if (BasePlayer != null && BasePlayer.IsHoldingBall && !BasePlayer.IsThrowHolder && Ball.Current != null) ballHeightMod = Ball.Current.transform.position.y * LegacyLookBallHeightApprovalBonus; var approvalAngle = BasePlayer != null && BasePlayer.IsThrowHolder ? 10f : LegacyLookApprovalAngle + ballHeightMod; return Mathf.Abs(angle) <= approvalAngle;
        }
        public void Stop(in float deltaTime) { if (externalPlaybackEnabled) return; TargetMoveSpeed = Mathf.Lerp(TargetMoveSpeed, 0f, Mathf.Max(deltaTime, 0f) * LegacyStoppingSpeed); Direction = Vector3.Lerp(Direction, transform.forward, Mathf.Max(deltaTime, 0f) * LegacyDirectionRecoveryWhenStop); }
        public void ProcessMovement(in float time, in float deltaTime)
        {
            if (externalPlaybackEnabled) return; var safeDeltaTime = Mathf.Max(deltaTime, 0f); var animatorLerpSpeed = safeDeltaTime * LegacyAnimatorParameterLerpSpeed; var dribbleModifier = BasePlayer != null && BasePlayer.MatchPlayer != null ? BasePlayer.MatchPlayer.GetDribbleSpeedModifier() : 1f; var topSpeed = BasePlayer != null && BasePlayer.MatchPlayer != null ? BasePlayer.MatchPlayer.GetTopSpeed() : 4.5f; var finalSpeed = TargetMoveSpeed * topSpeed * (BasePlayer != null && BasePlayer.IsHoldingBall ? dribbleModifier : 1f); var shouldMove = finalSpeed > MoveSpeed; var acceleration = finalSpeed < MoveSpeed ? 3f : (BasePlayer != null && BasePlayer.MatchPlayer != null ? BasePlayer.MatchPlayer.GetAcceleration() : 6f); MoveSpeed = Mathf.Lerp(MoveSpeed, finalSpeed, safeDeltaTime * acceleration); var angle = Direction.sqrMagnitude > 0.0001f ? Mathf.Abs(Vector3.SignedAngle(transform.forward, Direction, Vector3.up)) : 0f; var movementLean = Mathf.Abs(finalSpeed - MoveSpeed) * LegacyMovementDirectionSpeedLeaningModifier + angle * LegacyMovementDirectionAngleLeaningModifier; movementLean /= angle / 90f + 1f; var shouldStop = !enabled || MatchManager.Current == null || (!MatchManager.Current.MatchFlags.HasFlag(MatchStatus.Playing) && !MatchManager.Current.MatchFlags.HasFlag(MatchStatus.Special)); ApplyLegacyLocomotionAnimator(shouldStop ? Vector3.zero : Direction, shouldStop ? 0f : MoveSpeed, animatorLerpSpeed, shouldStop); if (shouldStop) return; if (Direction.sqrMagnitude > 0.0001f && (shouldMove || MoveSpeed > LegacyMinMoveSpeedToMove)) { var moveDirection = Direction.normalized; var nextPosition = Position + moveDirection * Mathf.Min(finalSpeed, MoveSpeed + movementLean * 0.08f) * safeDeltaTime; SetPosition(nextPosition); }
        }
        public void Up(in float dT, MatchStatus matchStatus, Ball ball)
        {
            if (externalPlaybackEnabled || playerAnimator == null || BasePlayer == null || ball == null || !BasePlayer.IsHoldingBall || (!BasePlayer.IsThrowHolder && matchStatus != MatchStatus.Playing)) return; var followSpeedMod = 1f; if (BasePlayer.ActiveBehaviour is ChipShootingBehaviour || BasePlayer.ActiveBehaviour is ShootingBehaviour || BasePlayer.ActiveBehaviour is PassingBehaviour || BasePlayer.ActiveBehaviour is CrossingBehaviour) followSpeedMod = 1f - ball.transform.position.y; followSpeedMod = Mathf.Clamp(followSpeedMod, 0.4f, 1f); var ballHolderSituation = PlayerBallPoint.Situation.Normal; if (BasePlayer.IsThrowHolder) ballHolderSituation = PlayerBallPoint.Situation.ThrowIn; else if (BasePlayer.IsGKUntouchable && !BasePlayer.IsGoalKickHolder) ballHolderSituation = PlayerBallPoint.Situation.GK; var holdingPosition = playerAnimator.BallPosition(ballHolderSituation); var holdingRotation = playerAnimator.BallRotation(ballHolderSituation); ball.HolderBehave(holdingPosition, holdingRotation, in dT, followSpeedMod);
        }
        public bool HitBall(in Vector3 targetVelocity, PlayerAnimatorVariable animatorVariable, out PlayerAnimatorVariable result, in float ballHoldTime, bool disableVolley = false) { if (playerAnimator == null) { result = animatorVariable; return false; } return playerAnimator.PlayBallHitAnimation(in targetVelocity, animatorVariable, out result, in ballHoldTime, disableVolley); }
        private void OnCollisionEnter(Collision collision) { CollisionEnterEvent?.Invoke(collision); }
        private void LateUpdate() { if (transform != null) lastKnownPosition = transform.position; if (shadow != null) shadow.position = Position; }
        public void BallHitEvent() { BasePlayer?.BallHitEvent(); }
        private void ApplyLegacyLocomotionAnimator(Vector3 worldDirection, float moveSpeed, float animatorLerpSpeed, bool shouldStop)
        {
            if (playerAnimator == null) return; playerAnimator.SetFloat(PlayerAnimatorVariable.MoveSpeed, shouldStop ? 0f : Mathf.Max(LegacyMinMoveSpeedToMove, moveSpeed)); Direction = worldDirection.sqrMagnitude > 0.0001f ? worldDirection.normalized : Direction; CalculateAnimatorDirection(); if (shouldStop) targetAnimatorDirection = Vector2.zero; if (Mathf.Abs(targetAnimatorDirection.x) < 0.001f) targetAnimatorDirection.x = 0f; if (Mathf.Abs(targetAnimatorDirection.y) < 0.001f) targetAnimatorDirection.y = 0f; targetAnimatorDirection *= Mathf.Clamp01(TargetMoveSpeed); var currentAnimatorHorizontal = playerAnimator.GetFloat(PlayerAnimatorVariable.Horizontal); var currentAnimatorVertical = playerAnimator.GetFloat(PlayerAnimatorVariable.Vertical); currentAnimatorHorizontal = Mathf.Lerp(currentAnimatorHorizontal, targetAnimatorDirection.y, animatorLerpSpeed); currentAnimatorVertical = Mathf.Lerp(currentAnimatorVertical, targetAnimatorDirection.x, animatorLerpSpeed); playerAnimator.SetFloat(PlayerAnimatorVariable.Horizontal, currentAnimatorHorizontal); playerAnimator.SetFloat(PlayerAnimatorVariable.Vertical, currentAnimatorVertical); playerAnimator.SetBool(PlayerAnimatorVariable.IsHoldingBall, BasePlayer != null && BasePlayer.IsHoldingBall);
        }
    }
}
