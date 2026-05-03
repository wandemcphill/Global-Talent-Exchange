
using FStudio.MatchEngine.Enums;
using FStudio.GTEX.Core;

using UnityEngine;

using System.Collections.Generic;
using System.Linq;

namespace FStudio.MatchEngine.Players.Behaviours {
    public class BecomeAPassOptionBehaviour : BaseBehaviour {
        private const float RANGE_FOR_PASS_OPTION = 10f;
        private static Vector3 BOX_CAST_SIZE_FOR_CHECK = new Vector3(3,1f,3);
        private const float MIN_DISTANCE_FOR_PASS_OPTION = 15f;
        private const float MAX_DISTANCE_FOR_PASS_OPTION = 35f;
        private const float PASS_OPTION_DELAY_AS_SECONDS = 10f;
        private const float MIN_X_DIFFERENCE = 10f;

        private const int DIRECTION_COUNT = 8;

        private static Vector3[] DIRECTIONS = new Vector3[DIRECTION_COUNT] { 
            new Vector3(1,0,0),
            new Vector3(1,0,1),
            new Vector3(1,0,-1),
            new Vector3(-1,0,0),
            new Vector3(-1,0,1),
            new Vector3(-1,0,-1),
            new Vector3(0,0,1),
            new Vector3(0,0,-1),
        };

        private readonly Collider[] m_alloc = new Collider[10];
        private float nextPassOption;
        private Vector3 targetPosition;

        private bool IsInBounds (in Vector3 position) {
            if (position.x <= 0 || position.x >= fieldEndX || position.z >= fieldEndY || position.z < 0) {
                return false;
            }

            return true;
        }

        public override bool Behave(bool isAlreadyActive) {
            if (GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime()) {
                return BehaveOriginalRuntime(isAlreadyActive);
            }

            if (Player.IsHoldingBall) {
                return false;
            }

            if (!isAlreadyActive) {
                if (ball.HolderPlayer == null || ball.HolderPlayer.GameTeam != Player.GameTeam) {
                    return false;
                }

                if (nextPassOption < time) {
                    // find a spot to run to take the ball.
                    var holderPlayerPosition = ball.HolderPlayer.Position;

                    var closestTeammate = teammates.Where(x => x != ball.HolderPlayer &&
                    !x.IsGK &&
                    Vector3.Distance(holderPlayerPosition, x.Position) < MAX_DISTANCE_FOR_PASS_OPTION &&
                    Vector3.Distance(holderPlayerPosition, x.Position) > MIN_DISTANCE_FOR_PASS_OPTION &&
                    Mathf.Abs (holderPlayerPosition.x - x.Position.x) > MIN_X_DIFFERENCE
                    ).
                    OrderBy(x => Vector3.Distance(x.Position, holderPlayerPosition)).FirstOrDefault();
                    
                    if (closestTeammate != Player) {
                        return false;
                    }

                    var myPosition = Player.Position;

                    // order by closest direction, then take 3 of them.
                    var possibleDirs = DIRECTIONS.
                        Select(x => new Vector3(x.x * Player.toGoalXDirection, 0f, x.z)).
                        OrderBy(x => Vector3.Distance(holderPlayerPosition + x * RANGE_FOR_PASS_OPTION, myPosition)).
                        Take (3);

                    foreach (var dir in possibleDirs) {
                        var checkPos = holderPlayerPosition + dir * RANGE_FOR_PASS_OPTION;
                        if (!IsInBounds(checkPos)) {
                            continue;
                        }

                        int count = Physics.OverlapBoxNonAlloc(
                            checkPos,
                            BOX_CAST_SIZE_FOR_CHECK, m_alloc,
                            Quaternion.identity, 1 << LayerMask.NameToLayer(Tags.PLAYER_LAYER));

                        if (count == 0 || (count == 1 && m_alloc[0].transform == ball.HolderPlayer.PlayerController.UnityObject.transform)) {
                            Debug.Log("[BECOMEAPASSOPTION] Become a pass option started.");

                            isAlreadyActive = true;
                            targetPosition = checkPos;
                            nextPassOption = time + PASS_OPTION_DELAY_AS_SECONDS;

                            Player.CurrentAct = Acts.BecomeAPassOption;
                            break;
                        }
                    }
                }
            }

            if (isAlreadyActive) {
                if (Player.IsInOffside) {
                    return false;
                }

                if (IsTheBallGoingOutside()) {
                    return false;
                }

                Player.AvoidMarkers(teammates, ref targetPosition, 5);

                if (!Player.MoveTo(in deltaTime, targetPosition, false)) {
                    Debug.Log("[BECOMEAPASSOPTION] Become a pass option reached.");
                    return false;
                } else {
                    return true;
                }
            }

            return false;
        }

        private bool BehaveOriginalRuntime(bool isAlreadyActive) {
            if (!OriginalRuntimeRoleAwareness.CanUseOpenPlayBehaviour(matchStatus) ||
                Player.IsHoldingBall ||
                Player.IsGK ||
                ball.HolderPlayer == null ||
                ball.HolderPlayer == Player ||
                ball.HolderPlayer.GameTeam != Player.GameTeam ||
                ball.HolderPlayer.IsGK) {
                return false;
            }

            if (!isAlreadyActive || time >= nextPassOption || Vector3.Distance(Player.Position, targetPosition) < 1.35f) {
                var holder = ball.HolderPlayer;
                var rankedCandidates = teammates.
                    Where(x =>
                        x != null &&
                        x != holder &&
                        !x.IsGK &&
                        !x.IsInOffside &&
                        x.PlayerController != null &&
                        x.PlayerController.IsPhysicsEnabled).
                    Select(x => (player: x, score: ResolveOriginalSupportScore(holder, x))).
                    Where(x => !float.IsPositiveInfinity(x.score)).
                    OrderBy(x => x.score).
                    Take(7).
                    ToArray();

                var candidates = new List<(PlayerBase player, float score)>(3);
                for (int i = 0; i < rankedCandidates.Length && candidates.Count < 3; i++) {
                    var candidate = rankedCandidates[i];
                    if (!OriginalRuntimeRoleAwareness.CanOfferSupport(candidate.player, holder, teammates, candidates.Count)) {
                        continue;
                    }

                    candidates.Add(candidate);
                }

                var supportIndex = candidates.FindIndex(x => x.player == Player);
                if (supportIndex < 0) {
                    return false;
                }

                targetPosition = ResolveOriginalSupportPoint(holder, supportIndex);
                nextPassOption = time + 1.15f;
                isAlreadyActive = true;
                Player.CurrentAct = Acts.BecomeAPassOption;
                Debug.Log(
                    "[GTEX AI] Support -> player=" + Player +
                    " holder=" + holder +
                    " index=" + supportIndex +
                    " point=" + targetPosition);
            }

            if (isAlreadyActive) {
                if (Player.IsInOffside || IsTheBallGoingOutside()) {
                    return false;
                }

                var target = targetPosition;
                Player.AvoidMarkers(opponents, ref target, 2.5f);
                Player.AvoidMarkers(teammates, ref target, 2.25f);
                KeepInField(ref target);

                Player.CurrentAct = Acts.BecomeAPassOption;
                Player.MoveTo(in deltaTime, target, false);
                Player.FocusToBall(in deltaTime, ball);
                return true;
            }

            return false;
        }

        private float ResolveOriginalSupportScore(PlayerBase holder, PlayerBase candidate) {
            var distance = Vector3.Distance(holder.Position, candidate.Position);
            if (distance < 5f || distance > 32f) {
                return float.PositiveInfinity;
            }

            var centralityPenalty = Mathf.Abs(candidate.Position.z - fieldEndY * 0.5f) * 0.05f;
            var distancePenalty = Mathf.Abs(distance - 15f) * 0.2f;
            var forwardDot = Vector3.Dot(holder.GoalDirection.normalized, (candidate.Position - holder.Position).normalized);
            var offsidePenalty = candidate.IsInOffside ? 100f : 0f;
            var role = OriginalRuntimeRoleAwareness.RoleOf(candidate);
            var rolePenalty =
                role == OriginalRuntimePlayerRole.Defender ? 6f :
                role == OriginalRuntimePlayerRole.Midfielder ? 0f :
                1.25f;
            var boundaryPenalty =
                candidate.Position.x < 3f ||
                candidate.Position.x > fieldEndX - 3f ||
                candidate.Position.z < 3f ||
                candidate.Position.z > fieldEndY - 3f
                    ? 8f
                    : 0f;

            return distancePenalty + centralityPenalty + boundaryPenalty + offsidePenalty + rolePenalty - forwardDot * 1.8f;
        }

        private Vector3 ResolveOriginalSupportPoint(PlayerBase holder, int supportIndex) {
            var holderPosition = holder.Position;
            var toGoal = targetGoalNet.Position - holderPosition;
            toGoal.y = 0f;
            if (toGoal.sqrMagnitude <= 0.01f) {
                toGoal = holder.GoalDirection;
            }

            toGoal.Normalize();
            var right = Vector3.Cross(Vector3.up, toGoal).normalized;
            var playerSide = Mathf.Sign(Vector3.Dot(Player.Position - holderPosition, right));
            if (Mathf.Abs(playerSide) < 0.1f) {
                playerSide = supportIndex % 2 == 0 ? 1f : -1f;
            }

            Vector3 point;
            switch (supportIndex) {
                case 0:
                    point = holderPosition - toGoal * 6.5f + right * playerSide * 4.5f;
                    break;
                case 1:
                    point = holderPosition + toGoal * 8f - right * playerSide * 5.5f;
                    break;
                default:
                    point = holderPosition + right * playerSide * 11f + toGoal * 2.5f;
                    break;
            }

            point.y = Player.Position.y;
            point.x = Mathf.Clamp(point.x, 3f, fieldEndX - 3f);
            point.z = Mathf.Clamp(point.z, 3f, fieldEndY - 3f);
            return point;
        }
    }
}
