using FStudio.MatchEngine.Balls;
using FStudio.MatchEngine.Players;
using FStudio.MatchEngine.Players.PlayerController;
using UnityEngine;

namespace FStudio.GTEX.Engine
{
    public sealed class GtexGoalkeeperBehavior : MonoBehaviour
    {
        [Header("Threat detection")]
        public float ThreatRadius = 22f;
        public float ThreatMinBallSpeed = 2f;
        public float MaxBallHeightForDive = 3.5f;

        [Header("Ready stance")]
        [Range(0f, 1f)] public float ReadyStanceMoveSpeed = 0.15f;

        [Header("Dive")]
        public float DiveMinBallSpeed = 5.5f;
        public float DiveCooldownSeconds = 2.8f;

        [Header("References")]
        public PlayerBase Goalkeeper;

        private float lastDiveAt = -99f;
        private bool inReadyStance;

        private void LateUpdate()
        {
            if (Goalkeeper == null || Ball.Current == null)
            {
                return;
            }

            var ballPosition = Ball.Current.transform.position;
            var keeperPosition = Goalkeeper.Position;
            var planarDistance = Vector3.Distance(
                new Vector3(keeperPosition.x, 0f, keeperPosition.z),
                new Vector3(ballPosition.x, 0f, ballPosition.z));

            var ballVelocity = Ball.Current.Velocity;
            var planarVelocity = new Vector3(ballVelocity.x, 0f, ballVelocity.z);
            var planarSpeed = planarVelocity.magnitude;
            var towardKeeper =
                planarVelocity.sqrMagnitude > 0.001f &&
                Vector3.Dot((keeperPosition - ballPosition).normalized, planarVelocity.normalized) > 0.3f;
            var isThreat = planarDistance < ThreatRadius && planarSpeed > ThreatMinBallSpeed && towardKeeper;

            if (isThreat && !inReadyStance)
            {
                EnterReadyStance();
            }
            else if (!isThreat && inReadyStance)
            {
                ExitReadyStance();
            }

            if (isThreat &&
                planarSpeed >= DiveMinBallSpeed &&
                ballPosition.y < MaxBallHeightForDive &&
                Time.time > lastDiveAt + DiveCooldownSeconds)
            {
                TriggerDive(ballPosition);
            }
        }

        private void EnterReadyStance()
        {
            inReadyStance = true;
            var animator = Goalkeeper != null && Goalkeeper.PlayerController != null ? Goalkeeper.PlayerController.Animator : null;
            if (animator == null)
            {
                return;
            }

            animator.SetFloat(PlayerAnimatorVariable.MoveSpeed, ReadyStanceMoveSpeed);
            animator.SetBool(PlayerAnimatorVariable.IsHoldingBall, false);
        }

        private void ExitReadyStance()
        {
            inReadyStance = false;
        }

        private void TriggerDive(Vector3 ballPosition)
        {
            lastDiveAt = Time.time;
            var animator = Goalkeeper != null && Goalkeeper.PlayerController != null ? Goalkeeper.PlayerController.Animator : null;
            var unityObject = Goalkeeper != null && Goalkeeper.PlayerController != null ? Goalkeeper.PlayerController.UnityObject : null;
            if (animator == null || unityObject == null)
            {
                return;
            }

            var localBall = unityObject.transform.InverseTransformPoint(ballPosition);
            animator.SetTrigger(localBall.x < 0f ? PlayerAnimatorVariable.GKJumpLeft : PlayerAnimatorVariable.GKJumpRight);
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
                return;
            }

            var behavior = unityObject.AddComponent<GtexGoalkeeperBehavior>();
            behavior.Goalkeeper = player;
            Debug.Log("[GTEX GK] Attached local goalkeeper behavior to " + (isHomeTeam ? "home" : "away") + " keeper.");
        }
    }
}
