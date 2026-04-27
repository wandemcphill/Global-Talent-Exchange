using FStudio.MatchEngine.Balls;
using FStudio.MatchEngine.Players;
using FStudio.MatchEngine.Players.PlayerController;
using FStudio.GTEX;
using UnityEngine;

namespace FStudio.GTEX.Engine
{
    public sealed class GtexGoalkeeperBehavior : MonoBehaviour
    {
        public enum GoalkeeperState
        {
            HomeSet,
            BallAngleSet,
            NearPostCover,
            CrossClaim,
            ShotReact,
            DiveAttempt,
            DeflectRecover,
            SweepThroughBall,
            Distribution,
            RecoverHome,
        }

        [Header("Threat detection")]
        public float ThreatRadius = 24f;
        public float BallAngleRadius = 18f;
        public float SweepRadius = 10f;
        public float NearPostRadius = 12f;
        public float ShotReactMinBallSpeed = 4.75f;
        public float DiveMinBallSpeed = 6f;
        public float MaxBallHeightForDive = 3.4f;

        [Header("Timing")]
        public float DiveCooldownSeconds = 2.6f;
        public float RecoverDurationSeconds = 0.9f;
        public float StateSustainSeconds = 0.18f;
        public float TurnSpeedDegreesPerSecond = 540f;

        [Header("References")]
        public PlayerBase Goalkeeper;
        public bool IsHomeTeam;

        public GoalkeeperState CurrentState { get; private set; } = GoalkeeperState.HomeSet;

        private float lastDiveAt = -99f;
        private float enteredCurrentStateAt = -99f;
        private GoalkeeperState previousState = GoalkeeperState.HomeSet;

        private void LateUpdate()
        {
            if (GtexRuntimeFlags.IsOriginalVisualRuntime)
            {
                return;
            }

            if (Goalkeeper == null || Ball.Current == null || Goalkeeper.PlayerController == null)
            {
                return;
            }

            var nextState = ResolveState();
            ApplyState(nextState);
            RotateTowardThreat();
        }

        private GoalkeeperState ResolveState()
        {
            var ballPosition = Ball.Current.transform.position;
            var keeperPosition = Goalkeeper.Position;
            var toBall = ballPosition - keeperPosition;
            var planarToBall = new Vector3(toBall.x, 0f, toBall.z);
            var planarDistance = planarToBall.magnitude;

            var ballVelocity = Ball.Current.Velocity;
            var planarVelocity = new Vector3(ballVelocity.x, 0f, ballVelocity.z);
            var planarSpeed = planarVelocity.magnitude;

            var holder = Ball.Current.HolderPlayer;
            if (holder == Goalkeeper)
            {
                return GoalkeeperState.Distribution;
            }

            var towardKeeper =
                planarVelocity.sqrMagnitude > 0.001f &&
                planarToBall.sqrMagnitude > 0.001f &&
                Vector3.Dot(planarVelocity.normalized, planarToBall.normalized * -1f) > 0.2f;
            var highThreat = towardKeeper && planarSpeed >= ShotReactMinBallSpeed && planarDistance <= ThreatRadius;
            var canDive =
                towardKeeper &&
                planarSpeed >= DiveMinBallSpeed &&
                planarDistance <= ThreatRadius &&
                ballPosition.y <= MaxBallHeightForDive &&
                Time.time >= lastDiveAt + DiveCooldownSeconds;

            if (CurrentState == GoalkeeperState.DiveAttempt &&
                Time.time < enteredCurrentStateAt + RecoverDurationSeconds)
            {
                return GoalkeeperState.DeflectRecover;
            }

            if (CurrentState == GoalkeeperState.CrossClaim &&
                Time.time < enteredCurrentStateAt + RecoverDurationSeconds)
            {
                return GoalkeeperState.RecoverHome;
            }

            if (canDive)
            {
                return GoalkeeperState.DiveAttempt;
            }

            if (highThreat)
            {
                return GoalkeeperState.ShotReact;
            }

            if (planarDistance <= 3.4f && ballPosition.y <= 1.8f)
            {
                return GoalkeeperState.CrossClaim;
            }

            if (planarDistance <= SweepRadius && towardKeeper && holder == null)
            {
                return GoalkeeperState.SweepThroughBall;
            }

            var lateralDistance = Mathf.Abs(planarToBall.z);
            if (planarDistance <= NearPostRadius && lateralDistance >= 3.2f)
            {
                return GoalkeeperState.NearPostCover;
            }

            if (planarDistance <= BallAngleRadius)
            {
                return GoalkeeperState.BallAngleSet;
            }

            if (CurrentState != GoalkeeperState.HomeSet &&
                CurrentState != GoalkeeperState.RecoverHome &&
                Time.time < enteredCurrentStateAt + StateSustainSeconds)
            {
                return CurrentState;
            }

            return CurrentState == GoalkeeperState.DeflectRecover ||
                   CurrentState == GoalkeeperState.SweepThroughBall ||
                   CurrentState == GoalkeeperState.Distribution
                ? GoalkeeperState.RecoverHome
                : GoalkeeperState.HomeSet;
        }

        private void ApplyState(GoalkeeperState nextState)
        {
            var animator = Goalkeeper.PlayerController.Animator;
            if (animator == null)
            {
                CurrentState = nextState;
                return;
            }

            if (CurrentState != nextState)
            {
                previousState = CurrentState;
                CurrentState = nextState;
                enteredCurrentStateAt = Time.time;
                TriggerStateTransition(animator, nextState);
            }

            var stanceMoveSpeed = ResolveMoveSpeed(CurrentState);
            animator.SetBool(PlayerAnimatorVariable.IsHoldingBall, CurrentState == GoalkeeperState.Distribution);
            animator.SetFloat(PlayerAnimatorVariable.MoveSpeed, stanceMoveSpeed);
            animator.SetFloat(PlayerAnimatorVariable.Horizontal, 0f);
            animator.SetFloat(PlayerAnimatorVariable.Vertical, 0f);
        }

        private void TriggerStateTransition(PlayerAnimator animator, GoalkeeperState nextState)
        {
            if (nextState != GoalkeeperState.DiveAttempt)
            {
                return;
            }

            lastDiveAt = Time.time;
            var localBall = transform.InverseTransformPoint(Ball.Current.transform.position);
            if (Mathf.Abs(localBall.x) <= 0.45f && localBall.y <= 1.25f)
            {
                animator.SetTrigger(PlayerAnimatorVariable.GKBallSave_Low);
                return;
            }

            animator.SetTrigger(localBall.x < 0f ? PlayerAnimatorVariable.GKJumpLeft : PlayerAnimatorVariable.GKJumpRight);
        }

        private void RotateTowardThreat()
        {
            var toBall = Ball.Current.transform.position - Goalkeeper.Position;
            toBall.y = 0f;
            if (toBall.sqrMagnitude <= 0.001f)
            {
                return;
            }

            Goalkeeper.PlayerController.LookTo(Time.unscaledDeltaTime, toBall.normalized);
            var desiredRotation = Quaternion.LookRotation(toBall.normalized, Vector3.up);
            transform.rotation = Quaternion.RotateTowards(
                transform.rotation,
                desiredRotation,
                TurnSpeedDegreesPerSecond * Time.unscaledDeltaTime);
        }

        private static float ResolveMoveSpeed(GoalkeeperState state)
        {
            switch (state)
            {
                case GoalkeeperState.BallAngleSet:
                    return 0.12f;
                case GoalkeeperState.NearPostCover:
                    return 0.18f;
                case GoalkeeperState.CrossClaim:
                    return 0.24f;
                case GoalkeeperState.ShotReact:
                    return 0.22f;
                case GoalkeeperState.DiveAttempt:
                    return 0.28f;
                case GoalkeeperState.DeflectRecover:
                    return 0.2f;
                case GoalkeeperState.SweepThroughBall:
                    return 0.26f;
                case GoalkeeperState.Distribution:
                    return 0.1f;
                case GoalkeeperState.RecoverHome:
                    return 0.14f;
                case GoalkeeperState.HomeSet:
                default:
                    return 0.05f;
            }
        }

        public static void AttachToGoalkeeper(PlayerBase player, bool isHomeTeam)
        {
            if (player == null)
            {
                return;
            }

            var unityObject = player.PlayerController != null ? player.PlayerController.UnityObject : null;
            if (unityObject == null)
            {
                return;
            }

            var existing = unityObject.GetComponent<GtexGoalkeeperBehavior>();
            if (existing != null)
            {
                existing.Goalkeeper = player;
                existing.IsHomeTeam = isHomeTeam;
                return;
            }

            var behavior = unityObject.AddComponent<GtexGoalkeeperBehavior>();
            behavior.Goalkeeper = player;
            behavior.IsHomeTeam = isHomeTeam;
            Debug.Log("[GTEX GK] Attached goalkeeper state machine to " + (isHomeTeam ? "home" : "away") + " keeper.");
        }
    }
}
