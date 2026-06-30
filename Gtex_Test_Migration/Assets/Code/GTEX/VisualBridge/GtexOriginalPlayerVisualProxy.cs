using System.Collections;
using System.Linq;
using System.Reflection;
using FStudio.MatchEngine;
using FStudio.MatchEngine.Balls;
using FStudio.MatchEngine.Players;
using FStudio.MatchEngine.Players.PlayerController;
using UnityEngine;

namespace FStudio.GTEX.VisualBridge
{
    public sealed class GtexOriginalPlayerVisualProxy : MonoBehaviour
    {
        private static readonly MethodInfo BallHitMethod = typeof(Ball).GetMethod("BallHit", BindingFlags.Instance | BindingFlags.NonPublic);

        [SerializeField] private Transform root;
        [SerializeField] private Animator animator;
        [SerializeField] private float groundPassReleaseDelay = 0.11f;
        [SerializeField] private float groundPassMinSpeed = 10.5f;
        [SerializeField] private float groundPassMaxSpeed = 18.5f;
        [SerializeField] private float groundPassVerticalVelocity = 0f;

        private Coroutine movementRoutine;
        private Coroutine groundPassRoutine;
        private Coroutine receiveTrapRoutine;
        private Coroutine keeperSaveTrapRoutine;

        public string GtexPlayerId { get; private set; } = string.Empty;

        public PlayerBase Player { get; private set; }

        public Transform Root => root != null ? root : transform;

        public bool HasBall => Player != null && Player.IsHoldingBall;

        public bool IsGoalkeeper => Player != null && Player.IsGK;

        public void Initialize(string gtexPlayerId, PlayerBase player)
        {
            GtexPlayerId = gtexPlayerId ?? string.Empty;
            Player = player;
            GtexVisualAuthority.RegisterPlayer(player, GtexPlayerId);
            root = player != null && player.PlayerController != null
                ? player.PlayerController.UnityObject.transform
                : transform;

            if (animator == null && player != null && player.PlayerController != null)
            {
                animator = player.PlayerController.UnityObject.GetComponentInChildren<Animator>();
            }
        }

        public void GiveBall()
        {
            if (Player == null || Ball.Current == null)
            {
                return;
            }

            Ball.Current.Hold(Player);
        }

        public void MoveToSupportPoint(Vector3 point)
        {
            MoveToSupportPoint(point, 0.7f, 2.25f);
        }

        public void MoveToSupportPoint(Vector3 point, float urgency, float duration)
        {
            StartIntentRoutine(MoveIntentRoutine(point, urgency, duration, "SupportRun"));
        }

        public void MarkTarget(GtexOriginalPlayerVisualProxy target, float urgency, float duration)
        {
            if (target == null)
            {
                return;
            }

            StartIntentRoutine(MarkRoutine(target, urgency, duration));
        }

        public void PressTarget(GtexOriginalPlayerVisualProxy target, float urgency, float duration)
        {
            if (target == null)
            {
                return;
            }

            StartIntentRoutine(PressRoutine(target, urgency, duration));
        }

        public void HoldShape(Vector3 point, float duration)
        {
            StartIntentRoutine(MoveIntentRoutine(point, 0.25f, duration, "HoldShape"));
        }

        public void CoverSpace(Vector3 point, float urgency, float duration)
        {
            StartIntentRoutine(MoveIntentRoutine(point, urgency, duration, "CoverSpace"));
        }

        public void DribbleToward(Vector3 target)
        {
            if (Player == null)
            {
                return;
            }

            if (!Player.IsHoldingBall && !TryTakeNearbyBallForCommand("CarryBall", 1.85f))
            {
                return;
            }

            var flatTarget = target;
            flatTarget.y = Player.Position.y;
            var flatDistance = Vector3.Distance(Player.Position, flatTarget);
            StartMoveRoutine(
                flatTarget,
                Mathf.Clamp(flatDistance / 3.6f, 0.65f, 2.25f),
                flatDistance > 7.5f ? MovementType.BestHeCanDo : MovementType.Normal);
        }

        public void PassTo(GtexOriginalPlayerVisualProxy receiver)
        {
            GroundPassTo(receiver);
        }

        public void PassToPoint(Vector3 point)
        {
            GroundPassToPoint(point);
        }

        public void GroundPassTo(GtexOriginalPlayerVisualProxy receiver)
        {
            if (receiver == null)
            {
                return;
            }

            if (Player != null)
            {
                Player.PassingTarget = receiver.Player;
            }

            GroundPassToPointInternal(ResolveReceiverFeetPoint(receiver), receiver.Player, receiver.GtexPlayerId);
        }

        public void GroundPassTo(GtexOriginalPlayerVisualProxy receiver, Vector3 receivePoint)
        {
            if (receiver == null)
            {
                GroundPassToPoint(receivePoint);
                return;
            }

            if (Player != null)
            {
                Player.PassingTarget = receiver.Player;
            }

            GroundPassToPointInternal(receivePoint, receiver.Player, receiver.GtexPlayerId);
        }

        public void GroundPassToPoint(Vector3 point)
        {
            GroundPassToPointInternal(point, Player != null ? Player.PassingTarget : null, string.Empty);
        }

        public void PrepareToReceive(Vector3 point, float urgency, float duration)
        {
            StartIntentRoutine(ReceiveRoutine(point, urgency, duration));
        }

        private void GroundPassToPointInternal(Vector3 point, PlayerBase receiver, string receiverUid)
        {
            if (Player == null)
            {
                return;
            }

            if (!Player.IsHoldingBall && !TryTakeNearbyBallForCommand("Pass", 2.4f))
            {
                return;
            }

            var target = point;
            target.y = Player.Position.y;
            if (animator == null && TryCallOriginalGroundPass(target, receiver, receiverUid))
            {
                return;
            }

            PassToPointFlat(target, receiver, receiverUid);
        }

        public void LoftPassTo(GtexOriginalPlayerVisualProxy receiver)
        {
            if (receiver == null)
            {
                return;
            }

            if (Player != null)
            {
                Player.PassingTarget = receiver.Player;
            }

            TryCallOriginalLoftPass(receiver.Root.position);
        }

        public void CrossTo(Vector3 point)
        {
            TryCallOriginalLoftPass(point);
        }

        public void ShootAt(Vector3 target)
        {
            ShootAt(target, string.Empty);
        }

        public void ShootAt(Vector3 target, string outcome)
        {
            if (Player == null)
            {
                return;
            }

            FaceTarget(target);
            if (TryCallOriginalShoot(target, outcome))
            {
                return;
            }

            if (animator != null)
            {
                animator.SetTrigger("Shoot");
            }

            Debug.LogWarning("[GTEX VisualBridge] Shoot fallback used for " + GtexPlayerId);
        }

        public void KeeperReactToShot(Vector3 target)
        {
            if (Player == null)
            {
                return;
            }

            FaceTarget(target);
            StartIntentRoutine(MoveIntentRoutine(target, 1f, 1.1f, "KeeperSave"));
            StartKeeperSaveTrapRoutine(target);
            if (animator != null)
            {
                animator.SetTrigger("GKBallSave_Low");
            }
        }

        public void KeeperClaim()
        {
            GiveBall();
        }

        public void FaceTarget(Vector3 target)
        {
            var direction = target - Root.position;
            direction.y = 0f;
            if (direction.sqrMagnitude <= 0.001f)
            {
                return;
            }

            if (Player != null && Player.PlayerController != null)
            {
                var deltaTime = Time.deltaTime > 0f ? Time.deltaTime : 0.02f;
                Player.LookTo(in deltaTime, direction);
                return;
            }

            Root.rotation = Quaternion.LookRotation(direction.normalized, Vector3.up);
        }

        public void PlayCelebration()
        {
            if (animator != null)
            {
                animator.SetTrigger("Celebrate");
            }
        }

        public void ResetToFormation(Vector3 point)
        {
            if (Player == null || Player.PlayerController == null)
            {
                Root.position = point;
                return;
            }

            Player.PlayerController.SetInstantPosition(point);
            Player.InstantStop();
        }

        private void StartMoveRoutine(Vector3 target, float durationSeconds, MovementType movementType)
        {
            StartIntentRoutine(MoveRoutine(target, durationSeconds, movementType));
        }

        private IEnumerator MoveRoutine(Vector3 target, float durationSeconds, MovementType movementType)
        {
            if (Player == null)
            {
                yield break;
            }

            var deadline = Time.time + Mathf.Max(0.1f, durationSeconds);
            while (Time.time < deadline)
            {
                var deltaTime = Time.deltaTime > 0f ? Time.deltaTime : 0.02f;
                if (Player.MoveTo(in deltaTime, target, true, movementType))
                {
                    break;
                }

                yield return null;
            }
        }

        private void StartIntentRoutine(IEnumerator routine)
        {
            if (movementRoutine != null)
            {
                StopCoroutine(movementRoutine);
            }

            movementRoutine = StartCoroutine(ManagedMovementRoutine(routine));
        }

        private IEnumerator ManagedMovementRoutine(IEnumerator routine)
        {
            yield return routine;
            movementRoutine = null;
        }

        private IEnumerator MarkRoutine(GtexOriginalPlayerVisualProxy target, float urgency, float duration)
        {
            var end = Time.time + Mathf.Max(0.2f, duration);
            while (Time.time < end && target != null)
            {
                var markPoint = ResolveMarkPoint(target.Root.position);
                MoveUsingOriginalController(markPoint, urgency);
                FaceTarget(target.Root.position);
                yield return null;
            }
        }

        private IEnumerator PressRoutine(GtexOriginalPlayerVisualProxy target, float urgency, float duration)
        {
            var end = Time.time + Mathf.Max(0.2f, duration);
            while (Time.time < end && target != null)
            {
                var pressPoint = ResolvePressPoint(target.Root.position);
                MoveUsingOriginalController(pressPoint, urgency);
                FaceTarget(target.Root.position);
                yield return null;
            }
        }

        private IEnumerator MoveIntentRoutine(Vector3 point, float urgency, float duration, string reason)
        {
            var end = Time.time + Mathf.Max(0.2f, duration);
            while (Time.time < end)
            {
                MoveUsingOriginalController(point, urgency);
                yield return null;
            }
        }

        private IEnumerator ReceiveRoutine(Vector3 point, float urgency, float duration)
        {
            var end = Time.time + Mathf.Max(0.2f, duration);
            while (Time.time < end)
            {
                if (HasBall)
                {
                    yield break;
                }

                var flatDelta = point - Root.position;
                flatDelta.y = 0f;
                if (flatDelta.sqrMagnitude <= 0.2f * 0.2f)
                {
                    yield break;
                }

                MoveUsingOriginalController(point, Mathf.Clamp01(Mathf.Lerp(urgency, 0.35f, 0.35f)));
                if (Ball.Current != null)
                {
                    FaceTarget(Ball.Current.transform.position);
                }

                yield return null;
            }
        }

        private void MoveUsingOriginalController(Vector3 point, float urgency)
        {
            if (TryCallOriginalMoveTo(point, urgency))
            {
                return;
            }

            var current = Root.position;
            var target = point;
            target.y = current.y;
            Root.position = Vector3.MoveTowards(
                current,
                target,
                (Time.deltaTime > 0f ? Time.deltaTime : 0.02f) * Mathf.Lerp(1.5f, 4.5f, Mathf.Clamp01(urgency)));
        }

        private bool TryCallOriginalMoveTo(Vector3 point, float urgency)
        {
            if (Player == null)
            {
                return false;
            }

            var target = point;
            target.y = Player.Position.y;
            var deltaTime = Time.deltaTime > 0f ? Time.deltaTime : 0.02f;
            Player.MoveTo(in deltaTime, target, true, ResolveMovementType(urgency));
            return true;
        }

        private bool TryCallOriginalGroundPass(Vector3 groundTarget, PlayerBase receiver, string receiverUid)
        {
            if (Player == null)
            {
                return false;
            }

            FaceTarget(groundTarget);
            Player.Pass(groundTarget);
            if (Player.ballHitAnimationEvent != BallHitAnimationEvent.Pass)
            {
                return false;
            }

            StartGroundPassRoutine(groundTarget, receiver, receiverUid, groundPassReleaseDelay);
            return true;
        }

        private bool TryCallOriginalLoftPass(Vector3 targetPoint)
        {
            if (Player == null)
            {
                return false;
            }

            if (!Player.IsHoldingBall && !TryTakeNearbyBallForCommand("LoftPass", 2.4f))
            {
                return false;
            }

            var target = targetPoint;
            target.y = Player.Position.y;
            Player.Cross(target);
            return true;
        }

        private bool TryCallOriginalShoot(Vector3 targetPoint, string outcome)
        {
            if (Player == null)
            {
                return false;
            }

            if (!Player.IsHoldingBall && !TryTakeNearbyBallForCommand("Shoot", 1.85f))
            {
                return false;
            }

            var normalizedOutcome = (outcome ?? string.Empty).ToLowerInvariant();
            if (normalizedOutcome.Contains("save"))
            {
                Player.Shoot(ComputeDirectShotVelocity(targetPoint, 0.82f));
                return Player.ballHitAnimationEvent == BallHitAnimationEvent.Shoot;
            }

            var opponentGoal = ResolveOpponentGoalNet();
            if (opponentGoal != null)
            {
                var shootPoint = ResolveGoalShootPoint(opponentGoal, targetPoint, outcome);
                if (shootPoint != null)
                {
                    Player.Shoot(opponentGoal.GetShootingVectorFromPoint(Player, shootPoint));
                    return Player.ballHitAnimationEvent == BallHitAnimationEvent.Shoot;
                }
            }

            var origin = Ball.Current != null ? Ball.Current.transform.position : Player.Position;
            var toTarget = targetPoint - origin;
            if (toTarget.sqrMagnitude < 0.01f)
            {
                toTarget = Player.PlayerController != null ? Player.PlayerController.Forward : Root.forward;
            }

            if (toTarget.sqrMagnitude < 0.01f)
            {
                toTarget = Vector3.forward;
            }

            var distance = Mathf.Clamp(toTarget.magnitude, 8f, 35f);
            var powerSkill = Player.MatchPlayer != null ? Player.MatchPlayer.ActualShootPower / 100f : 0.65f;
            var velocity = toTarget.normalized * Mathf.Lerp(18f, 34f, powerSkill) * Mathf.Clamp(distance / 22f, 0.75f, 1.25f);
            if (normalizedOutcome.Contains("on_target"))
            {
                velocity *= 1.05f;
            }

            velocity.y = Mathf.Max(velocity.y, Mathf.Lerp(2.2f, 5.5f, powerSkill));
            Player.Shoot(velocity);
            return Player.ballHitAnimationEvent == BallHitAnimationEvent.Shoot;
        }

        private Vector3 ComputeDirectShotVelocity(Vector3 targetPoint, float powerScale)
        {
            var origin = Ball.Current != null ? Ball.Current.transform.position : Player.Position;
            var toTarget = targetPoint - origin;
            if (toTarget.sqrMagnitude < 0.01f)
            {
                toTarget = Player.PlayerController != null ? Player.PlayerController.Forward : Root.forward;
            }

            if (toTarget.sqrMagnitude < 0.01f)
            {
                toTarget = Vector3.forward;
            }

            var flat = toTarget;
            flat.y = 0f;
            var distance = Mathf.Clamp(flat.magnitude, 8f, 34f);
            var skill = Player.MatchPlayer != null ? Mathf.Clamp01(Player.MatchPlayer.ActualShootPower / 100f) : 0.65f;
            var speed = Mathf.Lerp(16f, 27f, skill) * Mathf.Clamp(distance / 22f, 0.8f, 1.18f) * Mathf.Clamp(powerScale, 0.5f, 1.2f);
            var velocity = toTarget.normalized * speed;
            velocity.y = Mathf.Clamp(toTarget.y * 0.75f + Mathf.Lerp(0.8f, 1.8f, skill), 0.7f, 2.4f);
            return velocity;
        }

        private void PassToPointFlat(Vector3 groundTarget, PlayerBase receiver, string receiverUid)
        {
            if (Player == null)
            {
                return;
            }

            var direction = groundTarget - Root.position;
            direction.y = 0f;
            if (direction.sqrMagnitude < 0.01f)
            {
                return;
            }

            FaceTarget(groundTarget);
            if (animator != null)
            {
                animator.SetBool("IsSprinting", false);
                animator.SetTrigger("Pass");
            }

            StartGroundPassRoutine(groundTarget, receiver, receiverUid, 0.05f);
        }

        private void StartGroundPassRoutine(Vector3 groundTarget, PlayerBase receiver, string receiverUid, float delay)
        {
            if (groundPassRoutine != null)
            {
                StopCoroutine(groundPassRoutine);
            }

            groundPassRoutine = StartCoroutine(ReleaseGroundPassRoutine(groundTarget, receiver, receiverUid, delay));
        }

        private IEnumerator ReleaseGroundPassRoutine(Vector3 groundTarget, PlayerBase receiver, string receiverUid, float delay)
        {
            if (delay > 0f)
            {
                yield return new WaitForSeconds(delay);
            }

            if (this == null || Player == null || Ball.Current == null)
            {
                ClearPendingGroundPass(receiver);
                groundPassRoutine = null;
                yield break;
            }

            var ball = Ball.Current;
            if (ball.HolderPlayer != null && ball.HolderPlayer != Player)
            {
                ClearPendingGroundPass(receiver);
                groundPassRoutine = null;
                yield break;
            }

            var passOrigin = ball.transform.position;
            var velocity = ComputeGroundPassVelocity(groundTarget, passOrigin, out var passDistance, out var passSpeed);
            Debug.Log(
                "[GTEX PASS] actor=" + GtexPlayerId +
                " target=" + ResolveReceiverLogName(receiver, receiverUid) +
                " dist=" + passDistance.ToString("0.0") + "m" +
                " speed=" + passSpeed.ToString("0.0"));

            if (receiver != null)
            {
                var receiveDuration = Mathf.Clamp(passDistance / Mathf.Max(passSpeed, 0.1f) + 0.85f, 1.05f, 2.8f);
                receiver.CommitOriginalRuntimeReceive(Player, groundTarget, receiveDuration);
                ball.TrackOriginalRuntimeReceiver(receiver, groundTarget, receiveDuration);
                receiver.ActivateBehaviour("BallChasingWithoutCondition");
                Debug.Log("[GTEX RECEIVE] receiver=" + ResolveReceiverLogName(receiver, receiverUid) + " moving to intercept");
            }

            if (!TryInvokeBallHit(ball, Player, velocity))
            {
                receiver?.ClearOriginalRuntimeReceiveCommit();
                ClearPendingGroundPass(receiver);
                groundPassRoutine = null;
                yield break;
            }

            MatchManager.Current?.DelayBehaviourSelectionByReactionSkill();
            StartReceiveTrapRoutine(receiver, groundTarget, passOrigin, receiverUid);
            TryTriggerPassAndRun(receiver);
            ClearPendingGroundPass(receiver);
            groundPassRoutine = null;
        }

        private void StartReceiveTrapRoutine(PlayerBase receiver, Vector3 groundTarget, Vector3 passOrigin, string receiverUid)
        {
            if (receiver == null)
            {
                return;
            }

            if (receiveTrapRoutine != null)
            {
                StopCoroutine(receiveTrapRoutine);
            }

            receiveTrapRoutine = StartCoroutine(ReceiveTrapRoutine(receiver, groundTarget, passOrigin, receiverUid));
        }

        private IEnumerator ReceiveTrapRoutine(PlayerBase receiver, Vector3 groundTarget, Vector3 passOrigin, string receiverUid)
        {
            var end = Time.time + 2.6f;
            while (Time.time < end && receiver != null && Ball.Current != null)
            {
                var ball = Ball.Current;
                if (ball.HolderPlayer == receiver)
                {
                    Debug.Log("[GTEX RECEIVE] trap success " + ResolveReceiverLogName(receiver, receiverUid));
                    receiveTrapRoutine = null;
                    yield break;
                }

                if (ball.HolderPlayer != null && ball.HolderPlayer != Player)
                {
                    receiver.ClearOriginalRuntimeReceiveCommit();
                    Debug.Log("[GTEX RECEIVE] trap failed -> loose ball");
                    receiveTrapRoutine = null;
                    yield break;
                }

                var ballPosition = ball.transform.position;
                var interceptPoint = ResolveReceiveInterceptPoint(receiver, ballPosition, passOrigin, groundTarget);
                MoveReceiverTowardIntercept(receiver, interceptPoint, ballPosition);
                var receiverPosition = receiver.Position;

                var receiverDistance = DistanceXZ(ballPosition, receiverPosition);
                var targetDistance = DistanceXZ(ballPosition, groundTarget);
                if (receiverDistance <= 1.9f && targetDistance <= 2.6f)
                {
                    ball.StopDeadBallMotion();
                    ball.Hold(receiver);
                    Debug.Log("[GTEX RECEIVE] trap success " + ResolveReceiverLogName(receiver, receiverUid));
                    receiveTrapRoutine = null;
                    yield break;
                }

                yield return null;
            }

            receiver?.ClearOriginalRuntimeReceiveCommit();
            Debug.Log("[GTEX RECEIVE] trap failed -> loose ball");
            receiveTrapRoutine = null;
        }

        private void StartKeeperSaveTrapRoutine(Vector3 saveTarget)
        {
            if (Player == null || !Player.IsGK)
            {
                return;
            }

            if (keeperSaveTrapRoutine != null)
            {
                StopCoroutine(keeperSaveTrapRoutine);
            }

            keeperSaveTrapRoutine = StartCoroutine(KeeperSaveTrapRoutine(saveTarget));
        }

        private IEnumerator KeeperSaveTrapRoutine(Vector3 saveTarget)
        {
            var end = Time.time + 1.65f;
            while (Time.time < end && Ball.Current != null && Player != null)
            {
                var ball = Ball.Current;
                if (ball.HolderPlayer == Player)
                {
                    keeperSaveTrapRoutine = null;
                    yield break;
                }

                if (ball.HolderPlayer != null && ball.HolderPlayer != Player)
                {
                    keeperSaveTrapRoutine = null;
                    yield break;
                }

                var ballPosition = ball.transform.position;
                var keeperDistance = DistanceXZ(ballPosition, Root.position);
                var savePointDistance = DistanceXZ(ballPosition, saveTarget);
                if (keeperDistance <= 2.35f || savePointDistance <= 1.95f)
                {
                    ball.Hold(Player);
                    SettleKeeperAfterSave(saveTarget);
                    keeperSaveTrapRoutine = null;
                    yield break;
                }

                yield return null;
            }

            keeperSaveTrapRoutine = null;
        }

        private void SettleKeeperAfterSave(Vector3 faceTarget)
        {
            if (Player == null)
            {
                return;
            }

            Player.ResetBehaviours();
            Player.InstantStop();
            FaceTarget(faceTarget);
            StartIntentRoutine(KeeperSettleRoutine(faceTarget, 3f));
        }

        private IEnumerator KeeperSettleRoutine(Vector3 faceTarget, float duration)
        {
            var end = Time.time + Mathf.Max(0.2f, duration);
            while (Time.time < end && Player != null && HasBall)
            {
                Player.ResetBehaviours();
                Player.InstantStop();
                FaceTarget(faceTarget);
                yield return null;
            }
        }

        private Vector3 ComputeGroundPassVelocity(Vector3 groundTarget, Vector3 origin, out float distance, out float speed)
        {
            var flatDirection = groundTarget - origin;
            flatDirection.y = 0f;
            if (flatDirection.sqrMagnitude < 0.01f)
            {
                flatDirection = Player != null && Player.PlayerController != null
                    ? Player.PlayerController.Forward
                    : Root.forward;
                flatDirection.y = 0f;
            }

            if (flatDirection.sqrMagnitude < 0.01f)
            {
                flatDirection = Vector3.forward;
            }

            distance = flatDirection.magnitude;
            var passingSkill = Player != null && Player.MatchPlayer != null
                ? Mathf.Clamp01(Player.MatchPlayer.ActualPassing / 100f)
                : 0.6f;
            var skillSpeed = Mathf.Lerp(groundPassMinSpeed, groundPassMaxSpeed, passingSkill);
            var distanceSpeed = Mathf.Lerp(6.75f, 14.75f, Mathf.InverseLerp(4f, 26f, distance));
            speed = Mathf.Lerp(distanceSpeed, skillSpeed, 0.28f);
            speed *= Mathf.Clamp(distance / 14f, 0.78f, 1.08f);

            var velocity = flatDirection.normalized * speed;
            velocity.y = groundPassVerticalVelocity;
            return velocity;
        }

        private void ClearPendingGroundPass(PlayerBase receiver)
        {
            if (receiver != null)
            {
                receiver.ActivateBehaviour("BallChasingWithoutCondition");
            }

            if (Player != null)
            {
                Player.PassingTarget = null;
            }
        }

        private bool TryTakeNearbyBallForCommand(string commandName, float maxDistance)
        {
            if (Player == null || Ball.Current == null)
            {
                return false;
            }

            var ball = Ball.Current;
            if (ball.HolderPlayer == Player)
            {
                return true;
            }

            if (ball.HolderPlayer != null && ball.HolderPlayer != Player)
            {
                Debug.LogWarning(
                    "[GTEX VisualBridge] " + commandName +
                    " skipped for " + GtexPlayerId +
                    ": ball is held by another player.");
                return false;
            }

            var distance = DistanceXZ(ball.transform.position, Root.position);
            if (distance > maxDistance)
            {
                Debug.LogWarning(
                    "[GTEX VisualBridge] " + commandName +
                    " skipped for " + GtexPlayerId +
                    ": ball too far to claim (" + distance.ToString("0.00") + "m).");
                return false;
            }

            GiveBall();
            return true;
        }

        private static Vector3 ResolveReceiverFeetPoint(GtexOriginalPlayerVisualProxy receiver)
        {
            if (receiver == null)
            {
                return Vector3.zero;
            }

            var target = receiver.Player != null ? receiver.Player.Position : receiver.Root.position;
            target.y = receiver.Player != null ? receiver.Player.Position.y : receiver.Root.position.y;
            return target;
        }

        private static string ResolveReceiverLogName(PlayerBase receiver, string receiverUid)
        {
            if (!string.IsNullOrWhiteSpace(receiverUid))
            {
                return receiverUid;
            }

            return receiver != null ? receiver.ToString() : "none";
        }

        private static Vector3 ResolveReceiveInterceptPoint(
            PlayerBase receiver,
            Vector3 ballPosition,
            Vector3 passOrigin,
            Vector3 groundTarget)
        {
            if (receiver == null)
            {
                return groundTarget;
            }

            var receiverPosition = receiver.Position;
            var start = ballPosition;
            var end = groundTarget;
            var receiverFlat = receiverPosition;
            start.y = 0f;
            end.y = 0f;
            receiverFlat.y = 0f;

            var segment = end - start;
            if (segment.sqrMagnitude < 0.01f)
            {
                end = groundTarget;
                end.y = receiverPosition.y;
                return end;
            }

            var t = Mathf.Clamp01(Vector3.Dot(receiverFlat - start, segment) / segment.sqrMagnitude);
            var intercept = start + segment * t;

            var originToTarget = groundTarget - passOrigin;
            originToTarget.y = 0f;
            if (originToTarget.sqrMagnitude > 0.01f)
            {
                var originFlat = passOrigin;
                originFlat.y = 0f;
                var progress = Mathf.Clamp01(Vector3.Dot(intercept - originFlat, originToTarget) / originToTarget.sqrMagnitude);
                if (progress > 0.68f)
                {
                    var targetFlat = groundTarget;
                    targetFlat.y = 0f;
                    intercept = Vector3.Lerp(intercept, targetFlat, 0.42f);
                }
            }

            intercept.y = receiverPosition.y;
            return intercept;
        }

        private static void MoveReceiverTowardIntercept(PlayerBase receiver, Vector3 interceptPoint, Vector3 ballPosition)
        {
            if (receiver == null || receiver.PlayerController == null)
            {
                return;
            }

            var deltaTime = Time.deltaTime > 0f ? Time.deltaTime : 0.02f;
            interceptPoint.y = receiver.Position.y;
            receiver.MoveTo(in deltaTime, interceptPoint, true, MovementType.Normal);

            var lookDirection = ballPosition - receiver.Position;
            lookDirection.y = 0f;
            if (lookDirection.sqrMagnitude > 0.01f)
            {
                receiver.LookTo(in deltaTime, lookDirection);
            }
        }

        private static float DistanceXZ(Vector3 a, Vector3 b)
        {
            a.y = 0f;
            b.y = 0f;
            return Vector3.Distance(a, b);
        }

        private void TryTriggerPassAndRun(PlayerBase receiver)
        {
            if (Player == null || Player.IsGK || Player.GameTeam == null || Player.GameTeam.Team == null)
            {
                return;
            }

            if (receiver != null)
            {
                var toReceiver = receiver.Position - Player.Position;
                toReceiver.y = 0f;
                if (toReceiver.sqrMagnitude > 0.01f)
                {
                    var attackDirection = Player.GoalDirection;
                    attackDirection.y = 0f;
                    if (attackDirection.sqrMagnitude > 0.01f &&
                        Vector3.Dot(attackDirection.normalized, toReceiver.normalized) < -0.1f)
                    {
                        return;
                    }
                }
            }

            if (Player.GameTeam.Team.TeamTactics.RollPassAndRunChance(Player.GameTeam.BallProgress))
            {
                Player.ActivateBehaviour("PassAndRunBehaviour");
            }
        }

        private GoalNet ResolveOpponentGoalNet()
        {
            var manager = MatchManager.Current;
            if (manager == null || Player == null || Player.GameTeam == null)
            {
                return null;
            }

            if (manager.goalNet1 != null && manager.goalNet2 != null)
            {
                var ownReference = ResolveTeamDefensiveReference();
                if (ownReference.sqrMagnitude > 0.001f)
                {
                    var goal1Distance = Vector3.SqrMagnitude(ownReference - manager.goalNet1.Position);
                    var goal2Distance = Vector3.SqrMagnitude(ownReference - manager.goalNet2.Position);
                    return goal1Distance <= goal2Distance ? manager.goalNet2 : manager.goalNet1;
                }
            }

            return Player.GameTeam == manager.GameTeam1
                ? manager.goalNet2
                : manager.goalNet1;
        }

        private Vector3 ResolveTeamDefensiveReference()
        {
            if (Player == null || Player.GameTeam == null)
            {
                return Vector3.zero;
            }

            var teamPlayers = Player.GameTeam.GamePlayers;
            if (teamPlayers == null || teamPlayers.Length == 0)
            {
                return Root.position;
            }

            var keeper = teamPlayers.FirstOrDefault(candidate => candidate != null && candidate.IsGK);
            if (keeper != null)
            {
                return keeper.Position;
            }

            var sum = Vector3.zero;
            var count = 0;
            for (var index = 0; index < teamPlayers.Length; index += 1)
            {
                var candidate = teamPlayers[index];
                if (candidate == null)
                {
                    continue;
                }

                sum += candidate.Position;
                count += 1;
            }

            return count > 0 ? sum / count : Root.position;
        }

        private Transform ResolveGoalShootPoint(GoalNet goalNet, Vector3 requestedTarget, string outcome)
        {
            if (goalNet == null || goalNet.goalPoints == null || goalNet.goalPoints.Length == 0)
            {
                return null;
            }

            var goalPoints = goalNet.goalPoints.Where(point => point != null).ToArray();
            if (goalPoints.Length == 0)
            {
                return null;
            }

            if (requestedTarget.sqrMagnitude > 0.001f)
            {
                return goalPoints
                    .OrderBy(point => Vector3.SqrMagnitude(point.position - requestedTarget))
                    .FirstOrDefault();
            }

            var suggested = goalNet.GetShootingVector(Player, ResolveOpponents()).shootPoint;
            if (suggested != null)
            {
                return suggested;
            }

            var normalizedOutcome = (outcome ?? string.Empty).ToLowerInvariant();
            if (normalizedOutcome.Contains("save"))
            {
                return goalPoints
                    .OrderBy(point => Mathf.Abs(point.position.z - goalNet.Position.z))
                    .FirstOrDefault();
            }

            return goalPoints
                .OrderByDescending(point => Mathf.Abs(point.position.z - Player.Position.z))
                .FirstOrDefault();
        }

        private PlayerBase[] ResolveOpponents()
        {
            var manager = MatchManager.Current;
            if (manager == null || Player == null || Player.GameTeam == null)
            {
                return new PlayerBase[0];
            }

            var opponentTeam = Player.GameTeam == manager.GameTeam1
                ? manager.GameTeam2
                : manager.GameTeam1;

            return opponentTeam != null && opponentTeam.GamePlayers != null
                ? opponentTeam.GamePlayers
                    .Where(opponent => opponent != null && opponent.PlayerController != null && opponent.PlayerController.IsPhysicsEnabled)
                    .ToArray()
                : new PlayerBase[0];
        }

        private static bool TryInvokeBallHit(Ball ball, PlayerBase hitter, Vector3 velocity)
        {
            if (ball == null || hitter == null || BallHitMethod == null)
            {
                return false;
            }

            try
            {
                var parameterCount = BallHitMethod.GetParameters().Length;
                if (parameterCount == 4)
                {
                    BallHitMethod.Invoke(ball, new object[] { hitter, velocity, false, true });
                }
                else
                {
                    BallHitMethod.Invoke(ball, new object[] { hitter, velocity, false });
                }

                return true;
            }
            catch (TargetInvocationException exception)
            {
                Debug.LogWarning("[GTEX VisualBridge] Flat ground pass invoke failed: " + exception.GetBaseException().Message);
                return false;
            }
            catch (System.Exception exception)
            {
                Debug.LogWarning("[GTEX VisualBridge] Flat ground pass invoke failed: " + exception.Message);
                return false;
            }
        }

        private Vector3 ResolveMarkPoint(Vector3 targetPosition)
        {
            var ownGoal = ResolveOwnGoalCenter();
            var fromGoalToTarget = targetPosition - ownGoal;
            fromGoalToTarget.y = 0f;

            if (fromGoalToTarget.sqrMagnitude < 0.01f)
            {
                return targetPosition;
            }

            var goalSide = fromGoalToTarget.normalized;
            var markPoint = targetPosition - goalSide * 1.7f;
            markPoint.y = Root.position.y;
            return markPoint;
        }

        private Vector3 ResolvePressPoint(Vector3 carrierPosition)
        {
            var toCarrier = carrierPosition - Root.position;
            toCarrier.y = 0f;

            if (toCarrier.sqrMagnitude < 0.01f)
            {
                return Root.position;
            }

            var point = carrierPosition - toCarrier.normalized * 1.2f;
            point.y = Root.position.y;
            return point;
        }

        private Vector3 ResolveOwnGoalCenter()
        {
            var manager = MatchManager.Current;
            if (manager == null || Player == null)
            {
                return Root.position;
            }

            var ownGoal = Player.GameTeam == manager.GameTeam1 ? manager.goalNet1 : manager.goalNet2;
            return ownGoal != null ? ownGoal.Position : Root.position;
        }

        private static MovementType ResolveMovementType(float urgency)
        {
            var clampedUrgency = Mathf.Clamp01(urgency);
            if (clampedUrgency >= 0.8f)
            {
                return MovementType.BestHeCanDo;
            }

            if (clampedUrgency >= 0.45f)
            {
                return MovementType.Normal;
            }

            return MovementType.Relax;
        }
    }
}
