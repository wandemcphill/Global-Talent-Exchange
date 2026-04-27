using System.Collections;
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

        public string GtexPlayerId { get; private set; } = string.Empty;

        public PlayerBase Player { get; private set; }

        public Transform Root => root != null ? root : transform;

        public bool HasBall => Player != null && Player.IsHoldingBall;

        public bool IsGoalkeeper => Player != null && Player.IsGK;

        public void Initialize(string gtexPlayerId, PlayerBase player)
        {
            GtexPlayerId = gtexPlayerId ?? string.Empty;
            Player = player;
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

            if (!Player.IsHoldingBall)
            {
                GiveBall();
            }

            StartMoveRoutine(target, 2.75f, MovementType.Normal);
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

            GroundPassToPointInternal(receiver.Root.position, receiver.Player);
        }

        public void GroundPassToPoint(Vector3 point)
        {
            GroundPassToPointInternal(point, Player != null ? Player.PassingTarget : null);
        }

        private void GroundPassToPointInternal(Vector3 point, PlayerBase receiver)
        {
            if (Player == null)
            {
                return;
            }

            if (!Player.IsHoldingBall)
            {
                GiveBall();
            }

            var target = point;
            target.y = Player.Position.y;
            if (animator == null && TryCallOriginalGroundPass(target, receiver))
            {
                return;
            }

            PassToPointFlat(target, receiver);
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

            MoveToSupportPoint(target);
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

        private bool TryCallOriginalGroundPass(Vector3 groundTarget, PlayerBase receiver)
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

            StartGroundPassRoutine(groundTarget, receiver, groundPassReleaseDelay);
            return true;
        }

        private bool TryCallOriginalLoftPass(Vector3 targetPoint)
        {
            if (Player == null)
            {
                return false;
            }

            if (!Player.IsHoldingBall)
            {
                GiveBall();
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

            if (!Player.IsHoldingBall)
            {
                GiveBall();
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
            if (!string.IsNullOrWhiteSpace(outcome) &&
                outcome.ToLowerInvariant().Contains("on_target"))
            {
                velocity *= 1.05f;
            }

            velocity.y = Mathf.Max(velocity.y, Mathf.Lerp(2.2f, 5.5f, powerSkill));
            Player.Shoot(velocity);
            return Player.ballHitAnimationEvent == BallHitAnimationEvent.Shoot;
        }

        private void PassToPointFlat(Vector3 groundTarget, PlayerBase receiver)
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

            StartGroundPassRoutine(groundTarget, receiver, 0.05f);
        }

        private void StartGroundPassRoutine(Vector3 groundTarget, PlayerBase receiver, float delay)
        {
            if (groundPassRoutine != null)
            {
                StopCoroutine(groundPassRoutine);
            }

            groundPassRoutine = StartCoroutine(ReleaseGroundPassRoutine(groundTarget, receiver, delay));
        }

        private IEnumerator ReleaseGroundPassRoutine(Vector3 groundTarget, PlayerBase receiver, float delay)
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

            var velocity = ComputeGroundPassVelocity(groundTarget, ball.transform.position);
            if (!TryInvokeBallHit(ball, Player, velocity))
            {
                ClearPendingGroundPass(receiver);
                groundPassRoutine = null;
                yield break;
            }

            MatchManager.Current?.DelayBehaviourSelectionByReactionSkill();
            ClearPendingGroundPass(receiver);
            groundPassRoutine = null;
        }

        private Vector3 ComputeGroundPassVelocity(Vector3 groundTarget, Vector3 origin)
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

            var distance = flatDirection.magnitude;
            var passingSkill = Player != null && Player.MatchPlayer != null
                ? Mathf.Clamp01(Player.MatchPlayer.ActualPassing / 100f)
                : 0.6f;
            var speed = Mathf.Lerp(groundPassMinSpeed, groundPassMaxSpeed, passingSkill);
            speed *= Mathf.Clamp(distance / 16f, 0.72f, 1.35f);

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

        private static bool TryInvokeBallHit(Ball ball, PlayerBase hitter, Vector3 velocity)
        {
            if (ball == null || hitter == null || BallHitMethod == null)
            {
                return false;
            }

            try
            {
                BallHitMethod.Invoke(ball, new object[] { hitter, velocity, false });
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
