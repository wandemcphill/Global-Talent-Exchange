using System.Linq;
using FStudio.GTEX.Core;
using FStudio.MatchEngine.Enums;
using UnityEngine;

namespace FStudio.MatchEngine.Players.Behaviours {
    public sealed class OriginalRuntimeFootballDecisionBehaviour : BaseBehaviour {
        private enum Decision {
            None,
            Pass,
            Cross,
            Shoot
        }

        private const float MaxDecisionBallHeight = 0.62f;
        private const float PressureRadius = 5.5f;
        private const float BoundaryRiskDistance = 4.25f;
        private const float MinPassDistance = 5.25f;
        private const float MaxPassDistance = 27f;
        private const float IdealPassDistance = 14f;

        private Decision decision;
        private PlayerBase targetPlayer;
        private Vector3 targetPoint;
        private Vector3 shootVelocity;
        private float holdObservedAt;
        private float nextDecisionAt;

        public override bool Behave(bool isAlreadyActive) {
            if (!GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime() ||
                !OriginalRuntimeRoleAwareness.CanUseOpenPlayBehaviour(matchStatus) ||
                ball == null ||
                ball.HolderPlayer != Player ||
                !Player.IsHoldingBall ||
                Player.IsThrowHolder ||
                Player.IsCornerHolder ||
                Player.IsGoalKickHolder ||
                Player.IsGK ||
                ball.transform.position.y > MaxDecisionBallHeight) {
                ResetDecision();
                return false;
            }

            if (holdObservedAt <= 0f) {
                holdObservedAt = time;
            }

            if (!isAlreadyActive || time >= nextDecisionAt || !IsDecisionStillUsable()) {
                ResolveDecision();
                nextDecisionAt = time + 0.45f;
            }

            if (decision == Decision.None) {
                return false;
            }

            Player.GameTeam.KeepPlayerBehavioursForAShortTime();
            Player.Stop(in deltaTime);

            switch (decision) {
                case Decision.Shoot:
                    Player.CurrentAct = Acts.Shoot;
                    if (Player.LookTo(in deltaTime, shootVelocity)) {
                        Player.Shoot(shootVelocity);
                        ResetDecision();
                        return false;
                    }
                    return true;

                case Decision.Cross:
                    Player.CurrentAct = Acts.Crossing;
                    if (targetPlayer == null) {
                        ResetDecision();
                        return false;
                    }

                    targetPoint = ResolveFeetTarget(targetPlayer, 0.16f);
                    if (Player.LookTo(in deltaTime, targetPoint - Player.Position)) {
                        Player.PassingTarget = targetPlayer;
                        Player.Cross(targetPoint);
                        ResetDecision();
                        return false;
                    }
                    return true;

                case Decision.Pass:
                    Player.CurrentAct = Acts.PassingToBetterOpportunity;
                    if (targetPlayer == null) {
                        ResetDecision();
                        return false;
                    }

                    targetPoint = ResolveFeetTarget(targetPlayer, 0.08f);
                    if (Player.LookTo(in deltaTime, targetPoint - Player.Position)) {
                        var distance = Vector3.Distance(Player.Position, targetPoint);
                        var speedMod = Mathf.Lerp(0.82f, 1.04f, Mathf.InverseLerp(7f, 24f, distance));
                        Player.PassingTarget = targetPlayer;
                        Player.Pass(targetPoint, speedMod);
                        ResetDecision();
                        return false;
                    }
                    return true;
            }

            return false;
        }

        private void ResolveDecision() {
            ResetDecision(false);

            var underPressure = IsUnderPressure();
            var nearBoundary = IsNearBoundary(Player.Position, BoundaryRiskDistance);
            var heldLongEnough = time - holdObservedAt >= 0.45f;
            var finalThird = Player.PlayerFieldProgress >= 0.68f;
            var wideFinalThird = finalThird && IsWide(Player.Position);

            if (TryResolveShot(out shootVelocity) &&
                (Player.PlayerFieldProgress >= 0.78f || underPressure || IsCentral(Player.Position))) {
                decision = Decision.Shoot;
                Debug.Log(
                    "[GTEX AI] Decision Shoot -> actor=" + Player +
                    " progress=" + Player.PlayerFieldProgress.ToString("0.00"));
                return;
            }

            if (wideFinalThird && TryResolveCrossTarget(out targetPlayer, out targetPoint)) {
                decision = Decision.Cross;
                Debug.Log(
                    "[GTEX AI] Decision Cross -> actor=" + Player +
                    " target=" + targetPlayer +
                    " distance=" + Vector3.Distance(Player.Position, targetPoint).ToString("0.0"));
                return;
            }

            if ((underPressure || nearBoundary || heldLongEnough || Player.PlayerFieldProgress >= 0.5f) &&
                TryResolvePassTarget(out targetPlayer, out targetPoint)) {
                decision = Decision.Pass;
                Debug.Log(
                    "[GTEX AI] Decision Pass -> actor=" + Player +
                    " target=" + targetPlayer +
                    " distance=" + Vector3.Distance(Player.Position, targetPoint).ToString("0.0") +
                    " pressure=" + underPressure);
            }
        }

        private bool TryResolveShot(out Vector3 velocity) {
            velocity = default;

            if (targetGoalNet == null || ball.transform.position.y > 0.45f) {
                return false;
            }

            var toGoal = targetGoalNet.Position - Player.Position;
            toGoal.y = 0f;

            var distance = toGoal.magnitude;
            if (distance > 24f || distance < 0.1f) {
                return false;
            }

            var angle = Mathf.Abs(Vector3.SignedAngle(Player.GoalDirection, toGoal, Vector3.up));
            if (angle > 58f && distance > 13f) {
                return false;
            }

            if (IsOpponentBlockingLine(Player.Position, targetGoalNet.Position, 1.6f)) {
                return false;
            }

            var shootingTarget = targetGoalNet.GetShootingVector(Player, opponents);
            if (shootingTarget.shootPoint == null) {
                return false;
            }

            velocity = targetGoalNet.GetShootingVectorFromPoint(Player, shootingTarget.shootPoint);
            return velocity.sqrMagnitude > 0.1f;
        }

        private bool TryResolveCrossTarget(out PlayerBase target, out Vector3 point) {
            target = teammates.
                Where(IsEligibleReceiver).
                Where(x => IsCentral(x.Position) && Player.IsFrontOfMe(x.Position, -6f)).
                OrderByDescending(x => x.PlayerFieldProgress * 8f - Vector3.Distance(Player.Position, x.Position) * 0.25f)
                .FirstOrDefault();

            point = target != null ? ResolveFeetTarget(target, 0.12f) : default;
            return target != null;
        }

        private bool TryResolvePassTarget(out PlayerBase target, out Vector3 point) {
            var candidates = teammates.
                Where(IsEligibleReceiver).
                Select(x => (player: x, score: ResolvePassScore(x))).
                Where(x => !float.IsPositiveInfinity(x.score)).
                OrderBy(x => x.score).
                ToArray();

            var selected = candidates.FirstOrDefault();
            target = selected.player;
            point = target != null ? ResolveFeetTarget(target, 0.08f) : default;
            return target != null;
        }

        private float ResolvePassScore(PlayerBase candidate) {
            var offset = candidate.Position - Player.Position;
            offset.y = 0f;

            var distance = offset.magnitude;
            if (distance < MinPassDistance || distance > MaxPassDistance) {
                return float.PositiveInfinity;
            }

            var point = ResolveFeetTarget(candidate, 0.08f);
            var forwardDot = distance > 0.01f ? Vector3.Dot(Player.GoalDirection.normalized, offset / distance) : 0f;
            var linePenalty = IsOpponentBlockingLine(Player.Position, point, 1.35f) ? 9f : 0f;
            var boundaryPenalty = IsNearBoundary(candidate.Position, BoundaryRiskDistance) ? 6f : 0f;
            var centralityPenalty = Mathf.Abs(candidate.Position.z - fieldEndY * 0.5f) * 0.08f;
            var distancePenalty = Mathf.Abs(distance - IdealPassDistance) * 0.28f;
            var backwardPenalty = forwardDot < -0.2f && !IsUnderPressure() ? 5.5f : 0f;
            var progressReward = -candidate.PlayerFieldProgress * 4f;

            return linePenalty + boundaryPenalty + centralityPenalty + distancePenalty + backwardPenalty + progressReward - forwardDot * 2.5f;
        }

        private bool IsEligibleReceiver(PlayerBase candidate) {
            return candidate != null &&
                candidate != Player &&
                !candidate.IsGK &&
                !candidate.IsInOffside &&
                candidate.PlayerController != null &&
                candidate.PlayerController.IsPhysicsEnabled;
        }

        private bool IsDecisionStillUsable() {
            switch (decision) {
                case Decision.Pass:
                case Decision.Cross:
                    return IsEligibleReceiver(targetPlayer);
                case Decision.Shoot:
                    return shootVelocity.sqrMagnitude > 0.1f;
                default:
                    return false;
            }
        }

        private Vector3 ResolveFeetTarget(PlayerBase receiver, float leadSeconds) {
            var point = receiver.Position + receiver.Velocity * leadSeconds;
            point.y = Player.Position.y;
            KeepInField(ref point);
            point.x = Mathf.Clamp(point.x, 2f, fieldEndX - 2f);
            point.z = Mathf.Clamp(point.z, 2f, fieldEndY - 2f);
            return point;
        }

        private bool IsUnderPressure() {
            var playerPosition = Player.Position;
            return opponents.Any(x =>
                x != null &&
                !x.IsGK &&
                x.PlayerController != null &&
                x.PlayerController.IsPhysicsEnabled &&
                Vector3.Distance(x.Position, playerPosition) <= PressureRadius);
        }

        private bool IsOpponentBlockingLine(Vector3 start, Vector3 end, float radius) {
            start.y = 0f;
            end.y = 0f;

            foreach (var opponent in opponents) {
                if (opponent == null ||
                    opponent.IsGK ||
                    opponent.PlayerController == null ||
                    !opponent.PlayerController.IsPhysicsEnabled) {
                    continue;
                }

                if (DistancePointToSegment(opponent.Position, start, end) <= radius) {
                    return true;
                }
            }

            return false;
        }

        private static float DistancePointToSegment(Vector3 point, Vector3 start, Vector3 end) {
            point.y = 0f;
            var segment = end - start;
            segment.y = 0f;

            var lengthSqr = segment.sqrMagnitude;
            if (lengthSqr <= 0.0001f) {
                return Vector3.Distance(point, start);
            }

            var t = Mathf.Clamp01(Vector3.Dot(point - start, segment) / lengthSqr);
            var projection = start + segment * t;
            return Vector3.Distance(point, projection);
        }

        private bool IsNearBoundary(Vector3 position, float distance) {
            return position.x <= distance ||
                position.x >= fieldEndX - distance ||
                position.z <= distance ||
                position.z >= fieldEndY - distance;
        }

        private bool IsWide(Vector3 position) {
            return Mathf.Abs(position.z - fieldEndY * 0.5f) >= fieldEndY * 0.23f;
        }

        private bool IsCentral(Vector3 position) {
            return Mathf.Abs(position.z - fieldEndY * 0.5f) <= fieldEndY * 0.24f;
        }

        private void ResetDecision(bool resetTimer = true) {
            decision = Decision.None;
            targetPlayer = null;
            targetPoint = default;
            shootVelocity = default;

            if (resetTimer) {
                holdObservedAt = 0f;
                nextDecisionAt = 0f;
            }
        }
    }
}
