using FStudio.Data;
using FStudio.MatchEngine.Players;
using FStudio.MatchEngine.Players.PlayerController;
using UnityEngine;

namespace FStudio.GTEX.Engine
{
    public sealed class GtexLegacyPlayerHandle
    {
        private readonly PlayerBase player;

        public GtexLegacyPlayerHandle(PlayerBase player)
        {
            this.player = player;
        }

        public bool IsValid => player != null && player.PlayerController != null;

        public Vector3 Position => IsValid ? player.Position : Vector3.zero;

        public Quaternion Rotation => IsValid ? player.Rotation : Quaternion.identity;

        public Vector3 Forward => IsValid ? player.PlayerController.Forward : Vector3.forward;

        public Positions PositionRole =>
            player != null && player.MatchPlayer != null ? player.MatchPlayer.Position : default;

        public int ShirtNumber =>
            player != null && player.MatchPlayer != null ? player.MatchPlayer.Number : 0;

        public int? DatabasePlayerId =>
            player != null && player.MatchPlayer != null && player.MatchPlayer.Player != null
                ? player.MatchPlayer.Player.id
                : (int?)null;

        internal PlayerBase RawPlayer => player;

        public void SetInstantPosition(Vector3 position)
        {
            if (!IsValid)
            {
                return;
            }

            player.PlayerController.SetInstantPosition(position);
        }

        public void SetInstantRotation(Quaternion rotation)
        {
            if (!IsValid)
            {
                return;
            }

            player.PlayerController.SetInstantRotation(rotation);
        }

        public Vector3 InverseTransformDirection(Vector3 worldDirection)
        {
            if (!IsValid)
            {
                return worldDirection;
            }

            return player.PlayerController.UnityObject.transform.InverseTransformDirection(worldDirection);
        }

        public void ApplyExternalAnimatorState(bool hasPossession, float moveSpeed, float horizontal, float vertical)
        {
            var animator = IsValid ? player.PlayerController.Animator : null;
            if (animator == null)
            {
                return;
            }

            animator.SetBool(PlayerAnimatorVariable.IsHoldingBall, hasPossession);
            animator.SetFloat(PlayerAnimatorVariable.MoveSpeed, moveSpeed);
            animator.SetFloat(PlayerAnimatorVariable.Horizontal, horizontal);
            animator.SetFloat(PlayerAnimatorVariable.Vertical, vertical);
        }

        public void SetAnimatorBool(PlayerAnimatorVariable variable, bool value)
        {
            var animator = IsValid ? player.PlayerController.Animator : null;
            if (animator == null)
            {
                return;
            }

            animator.SetBool(variable, value);
        }

        public void SetAnimatorTrigger(PlayerAnimatorVariable variable)
        {
            var animator = IsValid ? player.PlayerController.Animator : null;
            if (animator == null)
            {
                return;
            }

            animator.SetTrigger(variable);
        }

        public void PlayExternalBallHit(Vector3 targetVelocity, bool isShot)
        {
            var animator = IsValid ? player.PlayerController.Animator : null;
            if (animator == null)
            {
                return;
            }

            animator.PlayBallHitAnimation(
                targetVelocity,
                isShot ? PlayerAnimatorVariable.Shoot_R : PlayerAnimatorVariable.Pass_R,
                out _,
                Time.time,
                false);
        }
    }
}
