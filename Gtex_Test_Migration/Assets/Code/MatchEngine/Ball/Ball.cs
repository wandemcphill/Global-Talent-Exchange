using FStudio.Animation;
using FStudio.GTEX.Engine;
using FStudio.MatchEngine.Players;
using FStudio.Utilities;

using System;
using UnityEngine;
using URandom = UnityEngine.Random;
using FStudio.Events;
using FStudio.MatchEngine.Events;
using FStudio.MatchEngine.EngineOptions;
using FStudio.GTEX.Playback;
using System.Linq;
using System.Threading.Tasks;
using FStudio.Data;
using FStudio.MatchEngine.Players.PlayerController;
using FStudio.MatchEngine.Graphics.EventRenderer;
using FStudio.MatchEngine.Utilities;

namespace FStudio.MatchEngine.Balls {
    [ExecuteInEditMode]
    [RequireComponent (typeof (Rigidbody))]
    [RequireComponent (typeof (CapsuleCollider))]
    public partial class Ball : SceneObjectSingleton <Ball> {
        private const string BALL_POSITION_SHADER_VARIABLE = "_BallPosition";
        private const string NETS_FACTOR_SHADER_VARIABLE = "_NetsFactor";
        private const string BALL_SHADOW_POWER = "_Power";

        private const float NETS_FACTOR_SPEED = 5, NETS_FACTOR_DISABLED_SPEED = 0.5f;

        private const float IGNORE_COLLISION_TIME_FOR_BALL_HITTER = 1f;

        private const float BALL_COLLIDE_DELAY = 0.25f;

        private const float MAX_WORLD_POW = 200;

        private const float MAX_VELOCTIY_POW = 200;

#pragma warning disable 0109
        [SerializeField] private new Rigidbody rigidbody = default;
#pragma warning restore 0109

        private Vector3 externalPlaybackVelocity;
        private bool hasExternalPlaybackTarget;
        private Vector3 externalPlaybackTargetPosition;
        private Quaternion externalPlaybackTargetRotation = Quaternion.identity;
        private float nextExternalPlaybackValidationAt;

        [SerializeField] private float externalPlaybackMoveSpeed = 30f;
        [SerializeField] private float externalPlaybackTeleportDistance = 6f;
        [SerializeField] private float externalPlaybackHolderFollowSpeed = 22f;
        [SerializeField] private float externalPlaybackHolderSnapDistance = 1.25f;
        [SerializeField] private float externalPlaybackHolderForwardOffset = 0.22f;
        [SerializeField] private float externalPlaybackHolderHeight = 0.06f;
        [SerializeField] private float externalPlaybackHolderLateralOffset = 0.28f;
        [SerializeField] private float externalPlaybackHolderIdleForwardScale = 0.34f;
        [SerializeField] private float externalPlaybackHolderRunForwardScale = 0.84f;
        [SerializeField] private float externalPlaybackHolderDribbleFrequency = 8.2f;
        [SerializeField] private float externalPlaybackHolderDribbleLift = 0.035f;
        [Header("GTEX Controlled Ball Visuals")]
        [SerializeField] private float controlledForwardOffset = 0.46f;
        [SerializeField] private float controlledSideOffset = 0.15f;
        [SerializeField] private float controlledBallRadius = 0.11f;
        [SerializeField] private float controlledFollowSharpness = 22f;
        [SerializeField] private LayerMask pitchGroundMask = ~0;
        private Vector3 _controlledBallVelocity;

        public Vector3 Velocity => ExternalPlaybackEnabled ? externalPlaybackVelocity : rigidbody.linearVelocity;

        public CapsuleCollider Collider;
        public bool ExternalPlaybackEnabled { get; private set; }

        public Transform ballAssetPoint;

        [SerializeField] private Transform ballShadow;
        [SerializeField] private Material shadowMaterial;

        private float nextCollision;

        private bool m_isOnCrossMode;

        private float crossHeight;

        public bool IsOnCrossMode {
            private set {
                m_isOnCrossMode = value;

                if (crossIndicator != null) {
                    crossIndicator.SetActive(value);
                }
            }
            get { return m_isOnCrossMode; }
        }

        public Vector3 CrossTarget { private set; get; }

        [SerializeField] private GameObject crossIndicator;

        private float crossCollisionCheck;

        public PlayerBase LastTouchedPlayer {
            private set;
            get;
        }

        public PlayerBase LastHolder {
            private set;
            get;
        }

        private Vector3 holdedPosition;
        private float followSpeedProgress;
        private float followSpeed;

        [SerializeField] private AnimationCurve followSpeedCurve;
        [SerializeField] private float holdedBallFollowSpeed = 1f;

        private AnimationQuery holdBlocker;

        [SerializeField] private bool isOnGoal;
        #region events
        public Action<PlayerBase> OnBallHold;
        public Action<GameTeam> OnBallHit;
        #endregion

        /// <summary>
        /// Current holder of the ball.
        /// </summary>
        public PlayerBase HolderPlayer { get; private set; }

        /// <summary>
        /// If the ball holded by a player, this is the team of the player.
        /// </summary>
        public GameTeam HolderTeam {
            get {
                if (HolderPlayer != null) {
                    return HolderPlayer.GameTeam;
                }
                
                return null;
            }
        }

        /// <summary>
        /// Returns the BallPosition, or ball drop point.
        /// </summary>
        public Vector3 BallPosition (PlayerBase player, float relaxation = 0) {
            return Predicter (player, relaxation);
        }

        private void OnValidate() {
            rigidbody = GetComponent<Rigidbody>();
            Collider = GetComponent<CapsuleCollider>();
        }

        private void Awake()
        {
            ConfigureExternalPlaybackPhysics();
        }

        protected override void OnEnable () {
            if (Application.isPlaying) {
                EventManager.Subscribe<GoalEvent>(OnGoal);
            }
        }

        private void OnDisable() {
            if (Application.isPlaying) {
                EventManager.UnSubscribe<GoalEvent>(OnGoal);
            }
        }

        private async void OnGoal (GoalEvent goal) {
            isOnGoal = true;
            await Task.Delay((int) (250 / Time.timeScale));
            isOnGoal = false;
        }

        private void LateUpdate() {
            var factor = Shader.GetGlobalFloat(NETS_FACTOR_SHADER_VARIABLE);
            factor = Mathf.Lerp(factor, isOnGoal ? 1 : 0, Time.deltaTime * (isOnGoal ? NETS_FACTOR_SPEED : NETS_FACTOR_DISABLED_SPEED));
            Shader.SetGlobalFloat(NETS_FACTOR_SHADER_VARIABLE, factor);

            Shader.SetGlobalVector(BALL_POSITION_SHADER_VARIABLE, transform.position);
            
            // keep it in limits.
            var ballPos = transform.position;
            var ballVel = Velocity;

            ballPos.x = Mathf.Clamp(ballPos.x, -MAX_WORLD_POW, MAX_WORLD_POW);
            ballPos.y = Mathf.Clamp(ballPos.y, -MAX_WORLD_POW, MAX_WORLD_POW);
            ballPos.z = Mathf.Clamp(ballPos.z, -MAX_WORLD_POW, MAX_WORLD_POW);

            transform.position = ballPos;

            ballVel.x = Mathf.Clamp(ballVel.x, -MAX_VELOCTIY_POW, MAX_VELOCTIY_POW);
            ballVel.y = Mathf.Clamp(ballVel.y, -MAX_VELOCTIY_POW, MAX_VELOCTIY_POW);
            ballVel.z = Mathf.Clamp(ballVel.z, -MAX_VELOCTIY_POW, MAX_VELOCTIY_POW);

            if (ExternalPlaybackEnabled) {
                externalPlaybackVelocity = ballVel;
            } else if (CanWritePhysicsVelocity()) {
                rigidbody.linearVelocity = ballVel;
            }

            if (ballShadow != null) {
                ballShadow.position = ballPos;
            }
            // ball shadow power.
            float height = ballPos.y;
            ballPos.y = 0;
            float heightPow = Mathf.Max (0, 0.6f - height);
            if (shadowMaterial != null) {
                shadowMaterial.SetFloat(BALL_SHADOW_POWER, heightPow);
            }
        }

        private void FixedUpdate()
        {
            if (!ExternalPlaybackEnabled || rigidbody == null)
            {
                return;
            }

            if (HolderPlayer != null)
            {
                DriveExternalPlaybackHolderAnchor();
                return;
            }

            if (!hasExternalPlaybackTarget)
            {
                return;
            }

            var nextPosition = Vector3.MoveTowards(
                rigidbody.position,
                externalPlaybackTargetPosition,
                externalPlaybackMoveSpeed * Time.fixedDeltaTime);

            GtexPlaybackPhysicsUtil.ApplyExternalPlaybackPosition(
                transform,
                rigidbody,
                nextPosition,
                externalPlaybackTargetRotation);
        }

        /// <summary>
        /// Ball holded by player.
        /// </summary>
        /// <param name="basePlayer"></param>
        public void Hold(PlayerBase basePlayer) {
            if (HolderPlayer != null) {
                Release();
            }

            LastTouchedPlayer = basePlayer;

            MatchManager.Current.ResetOffsides();

            Debug.LogFormat("[Ball] Hold by {0}", basePlayer);

            HolderPlayer = basePlayer;

            holdedPosition = transform.position;
            externalPlaybackVelocity = Vector3.zero;
            if (!rigidbody.isKinematic) {
                rigidbody.linearVelocity = Vector3.zero;
                rigidbody.angularVelocity = Vector3.zero;
            }

            rigidbody.isKinematic = true;
            Collider.enabled = false;

            followSpeedProgress = 0;

            basePlayer.OnBallHold();

            MatchManager.Current.ResetBehaviours();
        }

        /// <summary>
        /// Release the ball.
        /// </summary>
        public void Release() {
            rigidbody.isKinematic = ExternalPlaybackEnabled;
            Collider.enabled = !ExternalPlaybackEnabled;

            if (HolderPlayer != null) {
                IgnoreCollisionTemporary(HolderPlayer);
            }

            LastHolder = HolderPlayer;

            if (HolderPlayer != null) {
                HolderPlayer.OnBallRelease();
            }

            HolderPlayer = null;

            if (holdBlocker != null) {
                holdBlocker.Stop();
                holdBlocker = null;
            }

            #region ;disable player collision for 0.5 seconds;
            holdBlocker = new AnimationQuery();
            holdBlocker.AddToQuery(new TimerAction(0.25f));
            holdBlocker.Start(this, () => { 
                holdBlocker = null;
            });
            #endregion
        }

        public void SetExternalPlayback(bool value) {
            ExternalPlaybackEnabled = value;
            hasExternalPlaybackTarget = false;
            if (!value) {
                externalPlaybackVelocity = Vector3.zero;
            }

            if (HolderPlayer != null) {
                rigidbody.isKinematic = true;
                Collider.enabled = false;
                return;
            }

            rigidbody.isKinematic = value;
            Collider.enabled = !value;
        }

        public void ApplyExternalState(Vector3 targetPosition, Vector3 targetVelocity, PlayerBase holder = null) {
            if (!ExternalPlaybackEnabled) {
                return;
            }

            if (MatchManager.Current != null && MatchManager.Current.ExternalPlaybackSanitizer != null) {
                if (!MatchManager.Current.ExternalPlaybackSanitizer.TrySanitizeBallPosition(targetPosition, out targetPosition)) {
                    Debug.LogWarning("[Ball] Rejected invalid external playback ball position. Using sanitized fallback.");
                }
            } else if (MatchManager.Current != null) {
                targetPosition.x = Mathf.Clamp(targetPosition.x, 0, MatchManager.Current.SizeOfField.x);
                targetPosition.z = Mathf.Clamp(targetPosition.z, 0, MatchManager.Current.SizeOfField.y);
                targetPosition.y = Mathf.Max(0.1f, targetPosition.y);
            } else {
                targetPosition.y = Mathf.Max(0.1f, targetPosition.y);
            }

            if (MatchManager.Current != null && MatchManager.Current.ExternalPlaybackPitchZones != null) {
                targetPosition = MatchManager.Current.ExternalPlaybackPitchZones.ClampToPlayableGrass(targetPosition, 0.18f);
                targetPosition.y = Mathf.Max(ResolveExternalPlaybackHolderY(), targetPosition.y);
            }

            if (!GtexPlaybackSanitizer.IsFinite(targetVelocity)) {
                targetVelocity = Vector3.zero;
            }

            if (holder != null) {
                var holderChanged = HolderPlayer != holder;
                if (holderChanged) {
                    Hold(holder);
                }

                hasExternalPlaybackTarget = false;
                externalPlaybackVelocity = Vector3.zero;
                rigidbody.isKinematic = true;
                Collider.enabled = false;

                if (holderChanged ||
                    Vector3.Distance(rigidbody.position, ResolveExternalPlaybackHolderAnchor(holder)) >= ResolveExternalPlaybackHolderSnapDistance() * 1.75f)
                {
                    SnapExternalPlaybackHolderAnchor(holder);
                }

                return;
            }

            if (HolderPlayer != null) {
                Release();
            }

            rigidbody.isKinematic = true;
            Collider.enabled = false;
            externalPlaybackVelocity = targetVelocity;
            externalPlaybackTargetPosition = targetPosition;
            externalPlaybackTargetRotation = ResolveExternalPlaybackRotation(targetVelocity);

            if (!hasExternalPlaybackTarget ||
                Vector3.Distance(rigidbody.position, targetPosition) >= ResolveExternalPlaybackTeleportDistance()) {
                GtexPlaybackPhysicsUtil.ApplyExternalPlaybackPosition(
                    transform,
                    rigidbody,
                    targetPosition,
                    externalPlaybackTargetRotation);
            }

            hasExternalPlaybackTarget = true;
        }

        public Vector3 ResolveExternalPlaybackReleaseAnchor(
            PlayerBase holder,
            Vector3 releaseDirection,
            Vector3 fallbackPosition)
        {
            if (holder == null)
            {
                return fallbackPosition;
            }

            var forward = releaseDirection;
            forward.y = 0f;
            if (forward.sqrMagnitude <= 0.0001f)
            {
                forward = ResolveExternalPlaybackHolderForward(holder);
            }
            else
            {
                forward.Normalize();
            }

            var hasAnimatorBallPoint = TryResolveAnimatorControlledBallPoint(holder, out var anchor);
            if (!hasAnimatorBallPoint)
            {
                anchor = ResolveControlledBallTarget(
                    holder.PlayerController != null && holder.PlayerController.UnityObject != null
                        ? holder.PlayerController.UnityObject.transform
                        : null,
                    null,
                    ResolveExternalPlaybackHolderFootBias(holder) >= 0f);
            }

            anchor += forward * (hasAnimatorBallPoint ? 0.04f : 0.08f);

            if (MatchManager.Current != null && MatchManager.Current.ExternalPlaybackSanitizer != null)
            {
                anchor = MatchManager.Current.ExternalPlaybackSanitizer.SanitizeBallPosition(anchor, 0f);
            }

            if (MatchManager.Current != null && MatchManager.Current.ExternalPlaybackPitchZones != null)
            {
                anchor = MatchManager.Current.ExternalPlaybackPitchZones.ClampToPlayableGrass(anchor, 0.12f);
                anchor.y = Mathf.Max(ResolveExternalPlaybackHolderY(), anchor.y);
            }

            return GtexPlaybackSanitizer.IsFinite(anchor) ? anchor : fallbackPosition;
        }

        public void ReleaseFromControlledFoot(
            Transform carrier,
            Transform dominantFootSocket,
            bool rightFooted,
            Vector3 releaseVelocity)
        {
            var releasePoint = ResolveControlledBallTarget(carrier, dominantFootSocket, rightFooted);
            transform.position = releasePoint;
            _controlledBallVelocity = Vector3.zero;
            if (rigidbody == null)
            {
                return;
            }

            rigidbody.isKinematic = false;
            GtexPlaybackPhysicsUtil.SafeSetRigidbodyVelocity(rigidbody, releaseVelocity, Vector3.zero);
        }

        private bool TryResolveAnimatorControlledBallPoint(PlayerBase holder, out Vector3 target)
        {
            target = Vector3.zero;
            var animator = holder != null && holder.PlayerController != null ? holder.PlayerController.Animator : null;
            if (animator == null)
            {
                return false;
            }

            var situation =
                holder != null &&
                holder.MatchPlayer != null &&
                holder.MatchPlayer.Position == Positions.GK
                    ? PlayerBallPoint.Situation.GK
                    : PlayerBallPoint.Situation.Normal;

            target = animator.BallPosition(situation);
            if (!GtexPlaybackSanitizer.IsFinite(target))
            {
                return false;
            }

            var carrierY =
                holder != null &&
                holder.PlayerController != null &&
                holder.PlayerController.UnityObject != null
                    ? holder.PlayerController.UnityObject.transform.position.y
                    : transform.position.y;
            target = ResolveBallGroundHeight(target, carrierY);
            return true;
        }

        private Vector3 ResolveControlledBallTarget(
            Transform carrier,
            Transform dominantFootSocket,
            bool rightFooted)
        {
            if (carrier == null)
            {
                return transform.position;
            }

            Vector3 target;
            if (dominantFootSocket != null)
            {
                target = dominantFootSocket.position + carrier.forward * 0.08f;
            }
            else
            {
                var side = rightFooted ? controlledSideOffset : -controlledSideOffset;
                target =
                    carrier.position +
                    carrier.forward * controlledForwardOffset +
                    carrier.right * side;
            }

            return ResolveBallGroundHeight(target, carrier.position.y);
        }

        private Vector3 ResolveBallGroundHeight(Vector3 target, float fallbackCarrierY)
        {
            var rayStart = target + Vector3.up * 1.25f;
            if (Physics.Raycast(rayStart, Vector3.down, out var hit, 3f, pitchGroundMask, QueryTriggerInteraction.Ignore))
            {
                target.y = hit.point.y + controlledBallRadius;
            }
            else
            {
                target.y = fallbackCarrierY + controlledBallRadius;
            }

            return target;
        }

        /// <summary>
        /// Behave ball for holder. Returns true if progress is completed.
        /// </summary>
        /// <param name="deltaTime"></param>
        /// <returns></returns>
        public bool HolderBehave (Vector3 position, Quaternion rotation, in float deltaTime, float speedMod) {
            if (HolderPlayer != null) {
                if (MatchManager.Current.MatchFlags == Enums.MatchStatus.WaitingForKickOff || 
                    MatchManager.Current.MatchFlags == Enums.MatchStatus.NotPlaying) {
                    return false;
                }

                followSpeedProgress = Mathf.Min (1, 
                    followSpeedProgress + deltaTime * holdedBallFollowSpeed * speedMod);

                followSpeed = followSpeedCurve.Evaluate(followSpeedProgress) * 1;

                externalPlaybackVelocity = Vector3.zero;

                var targetPosition = Vector3.Lerp(
                    holdedPosition,
                     position,
                        followSpeed);

                if (MatchManager.Current != null && MatchManager.Current.ExternalPlaybackSanitizer != null) {
                    targetPosition = MatchManager.Current.ExternalPlaybackSanitizer.SanitizeBallPosition(targetPosition, 0f);
                } else if (MatchManager.Current.MatchFlags.HasFlag (Enums.MatchStatus.Playing)) {
                    // ball should be in the size of field when holded by someone.
                    var sizeOfField = MatchManager.Current.SizeOfField;
                    targetPosition.x = Mathf.Clamp(targetPosition.x, 0, sizeOfField.x);
                    targetPosition.z = Mathf.Clamp(targetPosition.z, 0, sizeOfField.y);
                    //
                }

                transform.position = targetPosition;
                transform.rotation = rotation;

                return followSpeed >= 1;
            }

            return false;
        }
        
        private void IgnoreCollisionTemporary (PlayerBase playerBase) {
            var playerCollider = playerBase.PlayerController.UnityCollider;
            Physics.IgnoreCollision(Collider, playerCollider, true);

            new TimerAction(IGNORE_COLLISION_TIME_FOR_BALL_HITTER).GetQuery().Start(this, ()=> {
                if (playerCollider != null) {
                    Physics.IgnoreCollision(Collider, playerCollider, false);
                }
            });
        }

        private void ApplyError (ref Vector3 target, float skill) {
            Vector3 position = transform.position;
            var dir = (target - position).normalized;
            float distance = Vector3.Distance(target, position);
            dir = ApplyDirectionError(dir, skill);
            target = position + dir * distance;
        }

        /// <summary>
        /// Send a curved pass to the target spot.
        /// </summary>
        /// <param name="target"></param>
        /// <param name="hitter"></param>
        public void Cross (Vector3 target, PlayerBase playerBase, bool ignoreOffside = false) {
            var crossingSkill = playerBase.MatchPlayer.GetLongBall();

            ApplyError(ref target, crossingSkill);

            target = EngineOptions_CrossBallSettings.Current.CrossPoint(playerBase.Position, target);

            crossHeight = EngineSettings.Current.CrossHeight(Vector3.Distance(target, playerBase.Position)) + 
                transform.position.y - HeightRemovalByHeight ().magnitude;

            var requiredVelocity = calcBallisticVelocityVector(
            transform.position,
            target,
            crossHeight);

            crossHeight = requiredVelocity.y;

            BallHit (playerBase, requiredVelocity, ignoreOffside);

            // Reset behaviours for normal pass.
            MatchManager.Current.DelayBehaviourSelectionByReactionSkill ();

            if (!playerBase.IsThrowHolder) {
                EventManager.Trigger(new PlayerCrossEvent(playerBase, requiredVelocity.magnitude));
            }

            CrossTarget = EngineOptions_CrossBallSettings.Current.TargetPointForDrag (playerBase.Position, target);

            // reset y.
            CrossTarget = new Vector3(CrossTarget.x, 0, CrossTarget.z);
            target.y = 0;
            //

            // keep in field.
            target.x = Mathf.Clamp(target.x, 1, MatchManager.Current.SizeOfField.x - 1);
            target.z = Mathf.Clamp(target.z, 1, MatchManager.Current.SizeOfField.y - 1);
            //

            if (crossIndicator != null) {
                crossIndicator.transform.position = target + Vector3.up * 0.05f;
            }

            IsOnCrossMode = true;

            crossCollisionCheck = Time.time + Time.fixedDeltaTime * 2;

            Debug.LogFormat("[Ball] Cross => {0} magniute", requiredVelocity.magnitude);
        }

        public void Pass (
            Vector3 target, 
            PlayerBase hitter, 
            float speedMod = 1, 
            bool ignoreOffside = false) {

            var distance = Vector3.Distance(transform.position, target);

            var longBallPercentage = 
                EngineSettings.Current.LongBallSkillPercentageAtDistance(distance);

            var longBallSkill = longBallPercentage * hitter.MatchPlayer.ActualPassing;
            var passingSkill = (1 - longBallPercentage) * hitter.MatchPlayer.ActualLongBall;

            ApplyError (ref target, longBallSkill + passingSkill);

            var pos = transform.position;
            pos.y = 0;

            var requiredVelocity = calcBallisticVelocityVector(
            pos,
            target,
            EngineSettings.Current.PassHeight (distance));

            Debug.LogFormat("[Ball] Pass => {0} required salt velocity.", requiredVelocity.magnitude);

            requiredVelocity *= EngineSettings.Current.PassPowerDistanceCurve.Evaluate (distance);
            requiredVelocity *= speedMod;

            if (!hitter.IsThrowHolder) {
                EventManager.Trigger(new PlayerPassEvent(hitter, requiredVelocity.magnitude));
            }
            //

            BallHit (hitter, requiredVelocity, ignoreOffside);

            // delay behaviours for normal pass.
            MatchManager.Current.DelayBehaviourSelectionByReactionSkill();

            Debug.LogFormat ("[Ball] Pass => {0} magniute", requiredVelocity.magnitude);
        }

        public void Shoot (Vector3 velocity, PlayerBase hitter) {
            Debug.Log("[Ball] Shoot");

            EventManager.Trigger(new PlayerShootEvent (hitter, velocity.magnitude));

            BallHit(hitter, velocity, false);
        }

        /// <summary>
        /// Get direction error. Target dir should not be normalized since we gonna use its magnitude on calculation.
        /// </summary>
        /// <returns>Returns a direction vector (not normalized). It has same velocity magnitude with the given vector</returns>
        public static Vector3 ApplyDirectionError (Vector3 targetDir, float skill, in float maxErrorAngle = -1) {
            var dirError = GetDirectionError(targetDir.magnitude, skill, in maxErrorAngle);
            return dirError * targetDir;
        }

        public static Quaternion GetDirectionError (float velocityMagnitude, float skill, in float maxAngleError = -1) {
            if (!EngineSettings.Current.IsDirectionErrorEnabled) {
                return Quaternion.identity;
            }

            var maxDirError = EngineSettings.Current.DirectionErrorModByVelocityCurve.Evaluate(velocityMagnitude) * 
                EngineSettings.Current.DirectionErrorSkillModCurve.Evaluate (skill/100f);

            var @error = URandom.Range(maxDirError / 4f, maxDirError);

            var @sideForward = URandom.Range(0, 10) > 4 ? -1 : 1;
            var @sideUp  = URandom.Range(0, 10) > 4 ? -1 : 1;

            if (maxAngleError > 0) {
                // clamp error.
                error = Mathf.Min(maxAngleError, error);
            }

            return Quaternion.Euler(error * sideUp, error * sideForward, 0);
        }

        private void AssignOffsides (PlayerBase hitter, bool ignoreOffside = false) {
            if (MatchManager.Current != null) {
                if (!ignoreOffside) {
                    MatchManager.Current.AssignOffsides(hitter.GameTeam, hitter);
                } else {
                    MatchManager.Current.ResetOffsides();
                }

                MatchManager.Current.MatchFlags = Enums.MatchStatus.Playing;
            }
        }

        private void ClampVelocity (ref Vector3 velocity) {
            // Clamp.
            if (velocity.magnitude < EngineSettings.Current.Ball_MinHitVelocity) {
                velocity = velocity.normalized * EngineSettings.Current.Ball_MinHitVelocity;
            }
            //
        }

        private Vector3 HeightRemovalByHeight () {
            return Vector3.up * EngineSettings.Current.ShootHeightByBallHeightCurve.Evaluate(transform.position.y);
        }

        private void BallHit (
            PlayerBase hitter,
            Vector3 velocity, 
            bool ignoreOffside = false) {

            if (float.IsNaN(velocity.magnitude)) {
                return;
            }

            var ballPos = transform.position;
            if (ballPos.y < 0.2f) {
                if (UnityEngine.Random.Range (0, 100) < velocity.magnitude) {
                    DirtRenderer.Current.SetPosition(0, transform.position);
                }
            }

            var heightVector = HeightRemovalByHeight();
            velocity -= heightVector;

            AssignOffsides(hitter, ignoreOffside);

            // release ball and hit.
            Release();

            if (CanWritePhysicsVelocity()) {
                rigidbody.linearVelocity = Vector3.zero;
            }

            ClampVelocity(ref velocity);

            Debug.LogFormat("[Ball] Velocity => {0}", velocity);

            if (CanWritePhysicsVelocity()) {
                rigidbody.angularVelocity = velocity;
                rigidbody.AddForce(velocity, ForceMode.VelocityChange);
            } else {
                externalPlaybackVelocity = velocity;
            }

            OnBallHit?.Invoke(hitter.GameTeam);
        }

        private bool CheckPlayerTouch (Collision collision) {
            var player = collision.collider.GetComponent<IPlayerController>();
            if (!player.IsPhysicsEnabled) {
                return false;
            }

            if (player.BasePlayer.CaughtInOffside) {
                return false;
            }
			
			var impulse = rigidbody.linearVelocity;
			impulse.y = 0;

            // check hit angle.
            var contactPoint = collision.contacts.First().normal;
            var angle = Mathf.Abs (Vector3.SignedAngle(-contactPoint, transform.forward, Vector3.up));

            if (angle > 180) { // not possible to hold.
                return false;
            }

            if (player.BasePlayer.OnBallTouch (transform.position.y, impulse.magnitude, this)) {
                Hold(player.BasePlayer);

                if (player.BasePlayer.IsGK) {
                    EventManager.Trigger(new KeeperSavesTheBallEvent(player.BasePlayer, collision.impulse.magnitude));
                } else {
                    EventManager.Trigger(new PlayerControlBallEvent(player.BasePlayer, collision.impulse.magnitude));
                }

                return true;
            }
            
            if (player.BasePlayer.IsGK) {
                EventManager.Trigger(new KeeperHitTheBallButCouldNotControlEvent(player.BasePlayer, rigidbody.linearVelocity.magnitude));
            }

            // throw ball here.
            var playerPos = player.Position;
            playerPos.y = transform.position.y;
            var dir = transform.position - playerPos;
            rigidbody.AddForce(dir * (rigidbody.linearVelocity.magnitude + 1));

            return false;
        }

        public void ResetBall (Vector3 target) {
            Debug.Log("Ball Reset ()");
            if (MatchManager.Current != null && MatchManager.Current.ExternalPlaybackSanitizer != null) {
                target = MatchManager.Current.ExternalPlaybackSanitizer.SanitizeBallPosition(target);
            } else {
                target.y = 0.1f;
            }
            hasExternalPlaybackTarget = false;
            externalPlaybackTargetPosition = target;
            externalPlaybackTargetRotation = transform.rotation;
            externalPlaybackVelocity = Vector3.zero;
            if (!rigidbody.isKinematic) {
                rigidbody.linearVelocity = Vector3.zero;
                rigidbody.angularVelocity = Vector3.zero;
            }
            transform.position = target;
            GtexPlaybackPhysicsUtil.ApplyExternalPlaybackPosition(
                transform,
                rigidbody,
                target,
                externalPlaybackTargetRotation,
                true);
            LastHolder = null;
            LastTouchedPlayer = null;

            if (ExternalPlaybackEnabled) {
                if (HolderPlayer != null) {
                    Release();
                }

                rigidbody.isKinematic = true;
                Collider.enabled = false;
            } else {
                Release();
            }
        }

        private void ConfigureExternalPlaybackPhysics()
        {
            if (!Application.isPlaying || rigidbody == null)
            {
                return;
            }

            rigidbody.interpolation = RigidbodyInterpolation.Interpolate;
        }

        private Quaternion ResolveExternalPlaybackRotation(Vector3 targetVelocity)
        {
            var planarVelocity = new Vector3(targetVelocity.x, 0f, targetVelocity.z);
            if (planarVelocity.sqrMagnitude <= 0.0001f)
            {
                return rigidbody != null ? rigidbody.rotation : transform.rotation;
            }

            return Quaternion.LookRotation(planarVelocity.normalized, Vector3.up);
        }

        private void DriveExternalPlaybackHolderAnchor()
        {
            if (HolderPlayer == null || rigidbody == null)
            {
                return;
            }

            var targetPosition = ResolveExternalPlaybackHolderAnchor(HolderPlayer);
            var targetRotation = ResolveExternalPlaybackHolderRotation(HolderPlayer);
            holdedPosition = targetPosition;
            externalPlaybackVelocity = Vector3.zero;
            rigidbody.isKinematic = true;
            Collider.enabled = false;

            if ((Application.isEditor || Debug.isDebugBuild) &&
                Time.unscaledTime >= nextExternalPlaybackValidationAt &&
                Vector3.Distance(transform.position, targetPosition) > 0.95f)
            {
                nextExternalPlaybackValidationAt = Time.unscaledTime + 1.25f;
                Debug.LogWarning(
                    "[Ball][Validate] controlled_ball_far_from_foot holder=" +
                    HolderPlayer +
                    " distance=" + Vector3.Distance(transform.position, targetPosition).ToString("0.##"));
            }

            if (Vector3.Distance(rigidbody.position, targetPosition) >= ResolveExternalPlaybackHolderSnapDistance())
            {
                GtexPlaybackPhysicsUtil.ApplyExternalPlaybackPosition(
                    transform,
                    rigidbody,
                    targetPosition,
                    targetRotation,
                    true);
                return;
            }

            var nextPosition = Vector3.SmoothDamp(
                rigidbody.position,
                targetPosition,
                ref _controlledBallVelocity,
                Mathf.Max(0.01f, 1f / controlledFollowSharpness),
                Mathf.Infinity,
                Time.fixedDeltaTime);
            nextPosition = Vector3.Lerp(
                nextPosition,
                targetPosition,
                (1f - Mathf.Exp(-controlledFollowSharpness * Time.fixedDeltaTime)) * 0.35f);

            var turnT = 1f - Mathf.Exp(-18f * Time.fixedDeltaTime);
            var nextRotation = Quaternion.Slerp(rigidbody.rotation, targetRotation, turnT);

            GtexPlaybackPhysicsUtil.ApplyExternalPlaybackPosition(
                transform,
                rigidbody,
                nextPosition,
                nextRotation);
            holdedPosition = nextPosition;
        }

        private void SnapExternalPlaybackHolderAnchor(PlayerBase holder)
        {
            if (holder == null || rigidbody == null)
            {
                return;
            }

            var targetPosition = ResolveExternalPlaybackHolderAnchor(holder);
            var targetRotation = ResolveExternalPlaybackHolderRotation(holder);
            holdedPosition = targetPosition;
            GtexPlaybackPhysicsUtil.SafeSetRigidbodyVelocity(rigidbody, Vector3.zero, Vector3.zero);
            GtexPlaybackPhysicsUtil.ApplyExternalPlaybackPosition(
                transform,
                rigidbody,
                targetPosition,
                targetRotation,
                true);
        }

        private Vector3 ResolveExternalPlaybackHolderAnchor(PlayerBase holder)
        {
            var carrierTransform =
                holder != null && holder.PlayerController != null && holder.PlayerController.UnityObject != null
                    ? holder.PlayerController.UnityObject.transform
                    : null;
            var hasAnimatorBallPoint = TryResolveAnimatorControlledBallPoint(holder, out var anchor);
            if (!hasAnimatorBallPoint)
            {
                anchor =
                    ResolveControlledBallTarget(
                        carrierTransform,
                        null,
                        ResolveExternalPlaybackHolderFootBias(holder) >= 0f);
            }
            var forward = ResolveExternalPlaybackHolderForward(holder);
            var lateral = Vector3.Cross(Vector3.up, forward).normalized;
            var planarVelocity = holder != null ? holder.Velocity : Vector3.zero;
            planarVelocity.y = 0f;
            var speed01 = Mathf.Clamp01(planarVelocity.magnitude / 5.4f);
            var footBias = ResolveExternalPlaybackHolderFootBias(holder);
            var dribblePhase = ResolveExternalPlaybackHolderDribblePhase(holder, speed01);
            var footPhase = Mathf.Lerp(footBias, dribblePhase, Mathf.Clamp01(speed01 * 1.2f));
            var forwardOffsetScale =
                Mathf.Lerp(
                    externalPlaybackHolderIdleForwardScale * 0.88f,
                    externalPlaybackHolderRunForwardScale * 1.08f,
                    speed01);
            var forwardOffset =
                forward *
                externalPlaybackHolderForwardOffset *
                forwardOffsetScale;
            var lateralOffset =
                lateral *
                Mathf.Lerp(externalPlaybackHolderLateralOffset * 0.28f, externalPlaybackHolderLateralOffset * 0.74f, speed01) *
                footPhase;

            var anchorForwardWeight = hasAnimatorBallPoint ? 0.16f : 0.32f;
            var anchorLateralWeight = hasAnimatorBallPoint ? 0.24f : 0.6f;
            anchor += forwardOffset * anchorForwardWeight + lateralOffset * anchorLateralWeight;
            anchor.y = Mathf.Max(
                ResolveExternalPlaybackHolderY(),
                anchor.y + Mathf.Abs(footPhase) * externalPlaybackHolderDribbleLift * speed01 * 0.46f);

            if (MatchManager.Current != null && MatchManager.Current.ExternalPlaybackSanitizer != null)
            {
                anchor = MatchManager.Current.ExternalPlaybackSanitizer.SanitizeBallPosition(anchor, 0f);
            }

            if (MatchManager.Current != null && MatchManager.Current.ExternalPlaybackPitchZones != null)
            {
                anchor = MatchManager.Current.ExternalPlaybackPitchZones.ClampToPlayableGrass(anchor, 0.12f);
                anchor.y = Mathf.Max(ResolveExternalPlaybackHolderY(), anchor.y);
            }
            else if (MatchManager.Current != null)
            {
                anchor.x = Mathf.Clamp(anchor.x, 0, MatchManager.Current.SizeOfField.x);
                anchor.z = Mathf.Clamp(anchor.z, 0, MatchManager.Current.SizeOfField.y);
                anchor.y = Mathf.Max(0.1f, anchor.y);
            }
            else
            {
                anchor.y = Mathf.Max(0.1f, anchor.y);
            }

            return anchor;
        }

        private float ResolveExternalPlaybackHolderDribblePhase(PlayerBase holder, float speed01)
        {
            var dominantFootBias = ResolveExternalPlaybackHolderFootBias(holder);
            if (speed01 <= 0.08f)
            {
                return dominantFootBias;
            }

            var phaseSeed = holder != null && holder.MatchPlayer != null
                ? holder.MatchPlayer.Number * 0.73f
                : 0f;
            return Mathf.Sin(Time.unscaledTime * Mathf.Lerp(0f, externalPlaybackHolderDribbleFrequency, speed01) + phaseSeed);
        }

        private static float ResolveExternalPlaybackHolderFootBias(PlayerBase holder)
        {
            if (holder != null && holder.MatchPlayer != null && holder.MatchPlayer.Number > 0)
            {
                return (holder.MatchPlayer.Number & 1) == 0 ? -1f : 1f;
            }

            return 1f;
        }

        private Quaternion ResolveExternalPlaybackHolderRotation(PlayerBase holder)
        {
            var forward = ResolveExternalPlaybackHolderForward(holder);
            if (forward.sqrMagnitude <= 0.0001f)
            {
                return rigidbody != null ? rigidbody.rotation : transform.rotation;
            }

            return Quaternion.LookRotation(forward, Vector3.up);
        }

        private Vector3 ResolveExternalPlaybackHolderForward(PlayerBase holder)
        {
            if (holder == null)
            {
                return Vector3.forward;
            }

            var movementDirection = holder.Direction;
            movementDirection.y = 0f;
            if (movementDirection.sqrMagnitude > 0.0001f)
            {
                return movementDirection.normalized;
            }

            if (holder.PlayerController != null)
            {
                var controllerForward = holder.PlayerController.Forward;
                controllerForward.y = 0f;
                if (controllerForward.sqrMagnitude > 0.0001f)
                {
                    return controllerForward.normalized;
                }
            }

            var rotationForward = holder.Rotation * Vector3.forward;
            rotationForward.y = 0f;
            return rotationForward.sqrMagnitude > 0.0001f
                ? rotationForward.normalized
                : Vector3.forward;
        }

        private float ResolveExternalPlaybackHolderY()
        {
            var pitchSpace = MatchManager.Current != null ? MatchManager.Current.ExternalPlaybackPitchSpace : null;
            var grassY = pitchSpace != null ? pitchSpace.GrassY : 0f;
            return grassY + Mathf.Max(0.08f, externalPlaybackHolderHeight);
        }

        private float ResolveExternalPlaybackHolderSnapDistance()
        {
            return Mathf.Max(
                0.75f,
                Mathf.Min(ResolveExternalPlaybackTeleportDistance(), externalPlaybackHolderSnapDistance));
        }

        private float ResolveExternalPlaybackTeleportDistance()
        {
            if (MatchManager.Current != null)
            {
                return Mathf.Max(4f, MatchManager.Current.ExternalPlaybackTeleportDistance * 1.85f);
            }

            return Mathf.Max(4f, externalPlaybackTeleportDistance);
        }

        private bool CanWritePhysicsVelocity()
        {
            return rigidbody != null && !rigidbody.isKinematic && !ExternalPlaybackEnabled;
        }

        private void OnCollisionEnter (Collision collision) {
            if (ExternalPlaybackEnabled) {
                return;
            }

            if (crossCollisionCheck < Time.time) {
                IsOnCrossMode = false;
            }

            var colliderLayer = collision.collider.gameObject.layer;
            var colliderTag = collision.collider.gameObject.tag;

            if (colliderTag.Equals(Tags.GOALNET_TAG)) {
                EventManager.Trigger(new BallHitNetEvent(collision.impulse.magnitude));
            } else if (colliderTag.Equals(Tags.GOALOUT_TAG)) {
                EventManager.Trigger(new BallOutByNetEvent(collision.impulse.magnitude));
            } else if (colliderTag.Equals(Tags.WOODWORK_TAG)) {
                EventManager.Trigger(new BallHitTheWoodWorkEvent(collision.impulse.magnitude));
            }

            if (MatchManager.Current == null ||
                !MatchManager.Current.MatchFlags.HasFlag(Enums.MatchStatus.Playing)) {
                return; //rest is for player ball control
            }

            if (colliderLayer == LayerMask.NameToLayer (Tags.PLAYER_LAYER)) {
                var playerController = collision.collider.gameObject.GetComponent<IPlayerController>();
                if (playerController == null) {
                    return;
                }

                LastTouchedPlayer = playerController.BasePlayer;

                float time = Time.time;
                if (nextCollision > time) {
                    return;
                }

                nextCollision = time + BALL_COLLIDE_DELAY;

                // check for new ball taker.
                if (holdBlocker == null) {
                    if (CheckPlayerTouch(collision)) {
                        return;
                    }
                }
            }
        }

        private void OnCollisionStay(Collision collision) {
            OnCollisionEnter(collision);
        }
    }
}
