using FStudio.MatchEngine.Players.PlayerController;
using UnityEngine;

namespace FStudio.GTEX.Playback
{
    public enum GtexMoveException
    {
        None,
        Jockey,
        Backpedal,
        DefensiveContain,
        KeeperSetPosition,
        KeeperReadyStance,
        ReceiverMicroAdjust,
    }

    public struct GtexVisualMotionResult
    {
        public Vector3 legalVelocity;
        public bool throttledForRotation;
        public bool blockedBackwardSprint;
        public bool allowedNonForward;
        public float forwardDot;
        public float finalSpeed;
    }

    public static class GtexVisualMotionGuard
    {
        public static GtexVisualMotionResult Resolve(
            Transform body,
            PlayerAnimator animator,
            Vector3 desiredVelocity,
            float deltaTime,
            GtexMoveException moveException,
            bool wantsSprint,
            float turnDegreesPerSecond = 540f,
            float sprintThreshold = 4.5f,
            float nonForwardMaxSpeed = 1.65f)
        {
            var result = new GtexVisualMotionResult();
            if (body == null)
            {
                return result;
            }

            var flatVelocity = Flatten(desiredVelocity);
            var desiredSpeed = flatVelocity.magnitude;
            if (desiredSpeed < 0.025f)
            {
                DriveAnimator(animator, 0f, 0f, 0f, false, false, false, 0f, deltaTime);
                result.legalVelocity = Vector3.zero;
                return result;
            }

            var desiredDirection = flatVelocity / desiredSpeed;
            var forward = Flatten(body.forward);
            if (forward.sqrMagnitude < 0.001f)
            {
                forward = desiredDirection;
            }
            else
            {
                forward.Normalize();
            }

            var forwardDotBeforeTurn = Vector3.Dot(forward, desiredDirection);
            RotateBodyToward(body, desiredDirection, turnDegreesPerSecond, deltaTime);

            forward = Flatten(body.forward);
            if (forward.sqrMagnitude < 0.001f)
            {
                forward = desiredDirection;
            }
            else
            {
                forward.Normalize();
            }

            var right = Flatten(body.right);
            if (right.sqrMagnitude < 0.001f)
            {
                right = Vector3.Cross(Vector3.up, forward).normalized;
            }
            else
            {
                right.Normalize();
            }

            var forwardDot = Vector3.Dot(forward, desiredDirection);
            var sideDot = Vector3.Dot(right, desiredDirection);
            var exceptionAllowsNonForward = moveException != GtexMoveException.None;
            var nonForward = forwardDot < 0.25f;
            var legalSpeed = desiredSpeed;
            var sprintLegal =
                wantsSprint &&
                moveException == GtexMoveException.None &&
                forwardDot >= 0.68f &&
                desiredSpeed >= sprintThreshold;

            if (nonForward && !exceptionAllowsNonForward)
            {
                legalSpeed = 0f;
                result.throttledForRotation = true;
                result.blockedBackwardSprint = wantsSprint;
            }
            else if (!exceptionAllowsNonForward && forwardDot < 0.68f)
            {
                var throttle = Mathf.InverseLerp(0.25f, 0.68f, forwardDot);
                legalSpeed *= throttle;
                result.throttledForRotation = true;
                sprintLegal = false;
            }

            if (exceptionAllowsNonForward)
            {
                legalSpeed = Mathf.Min(legalSpeed, nonForwardMaxSpeed);
                sprintLegal = false;
                result.allowedNonForward = nonForward;
            }

            var legalVelocity = desiredDirection * Mathf.Max(0f, legalSpeed);
            var animForward =
                exceptionAllowsNonForward
                    ? Mathf.Clamp(forwardDot, -1f, 1f)
                    : Mathf.Clamp01(forwardDot);
            var animSide = Mathf.Clamp(sideDot, -1f, 1f);
            var turnAngle = Vector3.SignedAngle(forward, desiredDirection, Vector3.up);
            var jockey =
                moveException == GtexMoveException.Jockey ||
                moveException == GtexMoveException.DefensiveContain ||
                moveException == GtexMoveException.KeeperSetPosition ||
                moveException == GtexMoveException.KeeperReadyStance;
            var backpedal = moveException == GtexMoveException.Backpedal && forwardDot < -0.1f;

            DriveAnimator(
                animator,
                legalSpeed,
                animSide,
                animForward,
                sprintLegal,
                jockey,
                backpedal,
                turnAngle,
                deltaTime);

            result.legalVelocity = legalVelocity;
            result.forwardDot = forwardDotBeforeTurn;
            result.finalSpeed = legalSpeed;
            return result;
        }

        private static void RotateBodyToward(Transform body, Vector3 desiredDirection, float degreesPerSecond, float deltaTime)
        {
            if (desiredDirection.sqrMagnitude < 0.001f)
            {
                return;
            }

            var targetRotation = Quaternion.LookRotation(desiredDirection, Vector3.up);
            body.rotation = Quaternion.RotateTowards(
                body.rotation,
                targetRotation,
                Mathf.Max(1f, degreesPerSecond) * deltaTime);
        }

        private static void DriveAnimator(
            PlayerAnimator animator,
            float speed,
            float moveX,
            float moveY,
            bool sprinting,
            bool jockeying,
            bool backpedaling,
            float turnAngle,
            float deltaTime)
        {
            if (animator == null)
            {
                return;
            }

            var normalizedSpeed = Mathf.Clamp01(speed / 4.5f);
            var finalForward =
                backpedaling || jockeying
                    ? Mathf.Clamp(moveY, -1f, 1f)
                    : Mathf.Clamp01(moveY);

            animator.SetFloat(PlayerAnimatorVariable.MoveSpeed, normalizedSpeed);
            animator.SetFloat(PlayerAnimatorVariable.Horizontal, Mathf.Clamp(moveX, -1f, 1f));
            animator.SetFloat(PlayerAnimatorVariable.Vertical, finalForward);
        }

        private static Vector3 Flatten(Vector3 value)
        {
            value.y = 0f;
            return value;
        }
    }
}
