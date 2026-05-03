
using FStudio.MatchEngine.Enums;
using FStudio.GTEX.Core;
using UnityEngine;
using System.Linq;
using static FStudio.MatchEngine.Players.PlayerBase;

namespace FStudio.MatchEngine.Players.Behaviours {
    public class PassingBehaviour : BaseBehaviour {
        private PassTarget target;

        private readonly bool onlyIfFrontOfUs;
        private readonly float minBallProgress;
        private readonly float maxBallProgress;
        private readonly float frontXThreshold;
        private readonly bool onlyIfCloserToGoalNet;

        public PassingBehaviour (float maxBallProgress = 1) {
            this.maxBallProgress = maxBallProgress;
        }

        /// <summary>
        /// Pick the targets only if they are closer to target goal net than us.
        /// </summary>
        /// <param name="minBallProgress"></param>
        /// <param name="onlyIfCloserToGoalNet"></param>
        public PassingBehaviour(
            float minBallProgress = 0,
            bool onlyIfCloserToGoalNet = false) {

            this.minBallProgress = minBallProgress;
            this.onlyIfCloserToGoalNet = onlyIfCloserToGoalNet;
        }

        /// <summary>
        /// Construct a passing behaviour with 'front of us' checker.
        /// When you checked 'onlyIfFrontOfUs' the player will pass only if the target is front of us in X Axis (to forward without considering horizontal position). So beware, centre forward can pass to the corner side :-)
        /// </summary>
        /// <param name="minBallProgress">Minimum ball progress to activate. Between 0-1</param>
        /// <param name="onlyIfFrontOfUs">Select if passing point is front of us.</param>
        /// <param name="frontXThreshold">If onlyIfFrontOfUs true, optionally add more X threshold to consider it is 'Front'</param>
        public PassingBehaviour (
            float minBallProgress, 
            bool onlyIfFrontOfUs,
            float frontXThreshold) {
            this.onlyIfFrontOfUs = onlyIfFrontOfUs;
            this.minBallProgress = minBallProgress;
            this.frontXThreshold = frontXThreshold;
        }

        public override bool Behave (bool isAlreadyActive) {
            if (!OriginalRuntimeRoleAwareness.CanUseOpenPlayBehaviour(matchStatus)) {
                return false;
            }

            if (ball.HolderPlayer != Player) {
                return false;
            }

            if (!isAlreadyActive) {
                if (Player.GameTeam.BallProgress < minBallProgress) {
                    return false;
                }

                if (Player.GameTeam.BallProgress > maxBallProgress) {
                    return false;
                }

                var targetGoalNetPosition = targetGoalNet.Position;

                var distanceToTargetGoalNet = Vector3.Distance(Player.Position, targetGoalNetPosition);

                var targets = teammates.Where(x => 
                    IsOriginalRuntimeReceiverCandidate(x) &&
                    (!onlyIfCloserToGoalNet || Vector3.Distance (x.Position, targetGoalNetPosition) < distanceToTargetGoalNet) &&
                    (!onlyIfFrontOfUs || Player.IsFrontOfMe(x.Position, frontXThreshold))).ToArray();

                target = Player.FindPassTarget(in targets, in targetGoalNetPosition);

                if (target.IsValid) {
                    Debug.Log($"[PassingBehaviour] OptionName: {target._OptionName}");
                    isAlreadyActive = true;
                }
            }

            if (isAlreadyActive) {
                Player.CurrentAct = Acts.PassingToBetterOpportunity;

                Player.GameTeam.KeepPlayerBehavioursForAShortTime();

                Player.Stop(in deltaTime);

                if (Player.LookTo(in deltaTime, target._Position - Player.Position)) {
                    // set pass target. after pass target player will behave with BallChasingBehaviour.
                    Player.PassingTarget = target._ActualTarget;

                    float speedMod = Player.SpeedModForPassing();

                    if (target._PassType == PassType.LongPass) {
                        var dir = target._Position - Player.Position;
                        var add = EngineSettings.Current.CrossTargetAdditionNormalByDistance.Evaluate(dir.magnitude);

                        var crossAddition = dir.normalized * add * target._PassPower;

                        if (GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime()) {
                            var drivenTarget = target._Position + crossAddition * 0.25f;
                            Player.Pass(drivenTarget, Mathf.Clamp(speedMod * target._PassPower * 0.95f, 0.78f, 1.14f));
                        } else {
                            Player.Cross(target._Position + crossAddition);
                        }
                    } else {
                        Player.Pass(target._Position, speedMod * target._PassPower);
                    }
                }

                return true;
            }

            return false;
        }

        private bool IsOriginalRuntimeReceiverCandidate(PlayerBase candidate) {
            if (!GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime()) {
                return true;
            }

            if (candidate == null ||
                candidate == Player ||
                candidate.IsGK ||
                candidate.PlayerController == null ||
                !candidate.PlayerController.IsPhysicsEnabled ||
                candidate.IsInOffside) {
                return false;
            }

            var progressDrop = Player.PlayerFieldProgress - candidate.PlayerFieldProgress;
            if (Player.PlayerFieldProgress > 0.35f && progressDrop > 0.18f) {
                return false;
            }

            if ((candidate.Position.x < 2.5f ||
                 candidate.Position.x > fieldEndX - 2.5f ||
                 candidate.Position.z < 2.5f ||
                 candidate.Position.z > fieldEndY - 2.5f) &&
                Player.PlayerFieldProgress > 0.45f) {
                return false;
            }

            return true;
        }
    }
}
