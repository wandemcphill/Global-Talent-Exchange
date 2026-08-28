using FStudio.GTEX.Core;
using FStudio.MatchEngine;
using FStudio.MatchEngine.Balls;
using FStudio.MatchEngine.Enums;
using FStudio.MatchEngine.Players;
using FStudio.MatchEngine.Players.PlayerController;
using UnityEngine;

namespace FStudio.GTEX.Presentation
{
    /// <summary>
    /// Keeps a held authoritative ball visually attached to its current carrier
    /// between network snapshots. It does not change possession or match state.
    /// </summary>
    [DefaultExecutionOrder(9995)]
    public sealed class GtexLiveHeldBallVisualFollower : MonoBehaviour
    {
        private static GtexLiveHeldBallVisualFollower instance;
        private Ball ball;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Install()
        {
            if (instance != null)
            {
                return;
            }

            var host = new GameObject("GTEX Live Held Ball Visual Follower");
            DontDestroyOnLoad(host);
            instance = host.AddComponent<GtexLiveHeldBallVisualFollower>();
        }

        private void LateUpdate()
        {
            if (!GtexRuntimeState.IsStarted ||
                GtexRuntimeState.ActiveMode != GtexRuntimeMode.LivePlayback)
            {
                return;
            }

            if (ball == null)
            {
                ball = Ball.Current ?? FindFirstObjectByType<Ball>();
            }

            if (ball == null || !ball.ExternalPlaybackEnabled || ball.HolderPlayer == null)
            {
                return;
            }

            var holder = ball.HolderPlayer;
            var playerController = holder.PlayerController;
            if (playerController == null || playerController.UnityObject == null)
            {
                return;
            }

            var target = ResolveHolderBallPoint(holder, playerController);
            if (!GtexPlaybackSanitizer.IsFinite(target))
            {
                target = playerController.UnityObject.transform.position +
                         playerController.UnityObject.transform.forward * 0.35f;
            }

            var pitchZones = MatchManager.Current != null
                ? MatchManager.Current.ExternalPlaybackPitchZones
                : null;
            if (pitchZones != null)
            {
                target = pitchZones.ClampToPlayableGrass(target, 0.12f);
            }

            ball.transform.position = target;
            ball.transform.rotation = playerController.UnityObject.transform.rotation;
        }

        private static Vector3 ResolveHolderBallPoint(
            PlayerBase holder,
            CodeBasedController playerController)
        {
            var animator = playerController.Animator;
            if (animator != null)
            {
                var situation =
                    holder.MatchPlayer != null && holder.MatchPlayer.Position == Positions.GK
                        ? PlayerBallPoint.Situation.GK
                        : PlayerBallPoint.Situation.Normal;
                var animatorPoint = animator.BallPosition(situation);
                if (GtexPlaybackSanitizer.IsFinite(animatorPoint))
                {
                    return animatorPoint;
                }
            }

            var carrier = playerController.UnityObject.transform;
            return carrier.position + carrier.forward * 0.35f + carrier.right * 0.16f;
        }
    }
}
