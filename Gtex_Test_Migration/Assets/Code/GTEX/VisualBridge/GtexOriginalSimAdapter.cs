using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using FStudio.GTEX;
using FStudio.GTEX.Core;
using FStudio.MatchEngine;
using FStudio.MatchEngine.Balls;
using FStudio.MatchEngine.Cameras;
using FStudio.MatchEngine.Enums;
using FStudio.MatchEngine.Players;
using Shared.Responses;
using UnityEngine;
using UnityEngine.Rendering;

namespace FStudio.GTEX.VisualBridge
{
    public sealed class GtexOriginalSimAdapter : MonoBehaviour
    {
        private static readonly string[] PreferredCameraModes = { "Broadcast", "Gameplay", "Match", "Default", "Stadium" };
        private static readonly string[] OriginalCameraNameHints = { "matchcamera", "match camera", "stadium", "broadcast" };

        [SerializeField] private Transform originalMatchRoot;
        [SerializeField] private Camera originalCamera;
        [SerializeField] private GtexPlayerVisualMap playerMap;
        [SerializeField] private GtexOriginalPitchVisualFallback pitchVisualFallback;
        [SerializeField] private GtexCinemachineFootballCameraDirector cinemachineFootballCameraDirector;
        [SerializeField] private GtexOriginalActionCameraDriver actionCameraDriver;
        [SerializeField] private GtexOriginalFallbackFollowCamera fallbackFollowCamera;
        [SerializeField] private bool preferCinemachineFootballCamera = true;
        [SerializeField] private bool createFallbackFollowCameraIfNeeded = true;

        private bool pitchReady;
        private bool lightingReady;
        private bool gameplayCameraReady;
        private bool usingFallbackCamera;
        private bool cameraActivationInProgress;
        private bool isRuntimeReady;
        private string activeCameraMode = string.Empty;
        private Coroutine clearPassTargetRoutine;
        private string lastActionCameraBindingKey = string.Empty;
        private string currentBallOwnerId = string.Empty;
        private string currentCameraPassTargetId = string.Empty;
        private Vector3 currentCameraWorldPassTarget;
        private bool hasCurrentCameraWorldPassTarget;
        private Vector3 lastResolvedShotTarget;
        private bool hasLastResolvedShotTarget;
        private bool? lastCameraBallBoundState;

        public GtexPlayerVisualMap PlayerMap
        {
            get
            {
                if (playerMap == null)
                {
                    playerMap = GetComponent<GtexPlayerVisualMap>();
                    if (playerMap == null)
                    {
                        playerMap = gameObject.AddComponent<GtexPlayerVisualMap>();
                    }
                }

                return playerMap;
            }
        }

        public bool IsPitchReady => pitchReady;

        public bool IsLightingReady => lightingReady;

        public bool IsRuntimeReady
        {
            get => isRuntimeReady;
            private set => isRuntimeReady = value;
        }

        public string CurrentBallOwnerId => currentBallOwnerId;

        public bool IsBallReady
        {
            get
            {
                if (Ball.Current == null)
                {
                    return false;
                }

                var rendererReady = HasEnabledRenderer(Ball.Current.transform);
                return rendererReady && Ball.Current.transform.position.y >= -0.1f;
            }
        }

        public bool IsCameraReady
        {
            get
            {
                var camera = ResolveActiveCamera();
                return camera != null && gameplayCameraReady && !string.IsNullOrWhiteSpace(activeCameraMode);
            }
        }

        public string ActiveCameraMode => activeCameraMode;

        public bool IsMatchActivelyPlaying
        {
            get
            {
                var manager = MatchManager.Current;
                return manager != null && manager.MatchFlags == MatchStatus.Playing;
            }
        }

        private void LateUpdate()
        {
            if (!GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime())
            {
                return;
            }

            SyncCurrentBallOwnerFromBall();
            MaintainGameplayCameraTarget();
        }

        public void ConfigureOriginalRuntime()
        {
            Debug.Log("[GTEX VisualBridge] OriginalSimAdapter ConfigureOriginalRuntime");
            EnsureHelpers();
            GtexRuntimeFlags.SetMode(GtexBootMode.OriginalVisualRuntime, true);
            IsRuntimeReady = false;

            if (MatchManager.Current != null)
            {
                MatchManager.Current.SetExternalPlayback(false);
                Debug.Log("[GTEX VisualBridge] MatchManager.SetExternalPlayback(false)");
            }

            if (Ball.Current != null)
            {
                Ball.Current.SetExternalPlayback(false);
            }

            RefreshRuntimeVisualEssentials();
            ActivateOriginalGameplayCamera();
        }

        public void RebuildPlayerMap(MatchResponse state = null)
        {
            PlayerMap.RebuildFromCurrentMatch(state);
            RefreshRuntimeVisualEssentials();
            LogRuntimeReadiness();
        }

        public void SetTeams(string home, string away)
        {
            GtexScoreAuthority.SetTeams(home, away);
        }

        public void SetClock(float minute)
        {
            var score = GtexScoreAuthority.Current;
            GtexScoreAuthority.SetScore(score.homeScore, score.awayScore, minute, score.lastEvent);
        }

        public void SetScore(int home, int away, float minute = 0f, string lastEvent = null)
        {
            GtexScoreAuthority.SetScore(home, away, minute, lastEvent);
        }

        public void GiveBallTo(string playerId)
        {
            if (!TryResolveCommandProxy(playerId, "actor", GtexVisualCommandType.AssignPossession, out var player))
            {
                return;
            }

            PrepareForCommandAction();
            player.GiveBall();
            UpdateCameraBallOwner(player.GtexPlayerId);
            ClearCameraPassTarget();
            FocusToBall();
            Debug.Log("[GTEX VisualBridge] Possession -> " + player.GtexPlayerId);
        }

        public void ExecuteCarry(string actorId, Vector3 targetPoint)
        {
            if (!TryResolveCommandProxy(actorId, "actor", GtexVisualCommandType.CarryBall, out var actor))
            {
                return;
            }

            PrepareForCommandAction();
            actor.DribbleToward(ResolveTarget(actor, targetPoint, 6f));
            UpdateCameraBallOwner(actor.GtexPlayerId);
            ClearCameraPassTarget();
            FocusToBall();
        }

        public void ExecuteSupportRun(GtexVisualCommand command)
        {
            if (command == null)
            {
                return;
            }

            if (!TryResolveCommandProxy(command.actorPlayerId, "actor", command.type, out var actor))
            {
                return;
            }

            PrepareForCommandAction(false);
            actor.MoveToSupportPoint(ClampToPitch(command.targetWorldPosition, 4f), command.urgency, command.duration);
            FocusToBall();
            Debug.Log("[GTEX VisualBridge] SupportRun -> " + command.actorPlayerId + " to " + command.targetWorldPosition);
        }

        public void ExecuteMarkPlayer(GtexVisualCommand command)
        {
            if (command == null)
            {
                return;
            }

            if (!TryResolveCommandProxy(command.actorPlayerId, "actor", command.type, out var defender) ||
                !TryResolveCommandProxy(command.targetPlayerId, "target", command.type, out var target))
            {
                return;
            }

            PrepareForCommandAction(false);
            defender.MarkTarget(target, command.urgency, command.duration);
            FocusToBall();
            Debug.Log("[GTEX VisualBridge] MarkPlayer -> " + command.actorPlayerId + " marks " + command.targetPlayerId);
        }

        public void ExecutePressBallCarrier(GtexVisualCommand command)
        {
            if (command == null)
            {
                return;
            }

            if (!TryResolveCommandProxy(command.actorPlayerId, "actor", command.type, out var defender) ||
                !TryResolveCommandProxy(command.targetPlayerId, "target", command.type, out var carrier))
            {
                return;
            }

            PrepareForCommandAction(false);
            defender.PressTarget(carrier, command.urgency, command.duration);
            FocusToBall();
            Debug.Log("[GTEX VisualBridge] Press -> " + command.actorPlayerId + " presses " + command.targetPlayerId);
        }

        public void ExecuteHoldShape(GtexVisualCommand command)
        {
            if (command == null)
            {
                return;
            }

            if (!TryResolveCommandProxy(command.actorPlayerId, "actor", command.type, out var actor))
            {
                return;
            }

            PrepareForCommandAction(false);
            var targetPoint = command.targetWorldPosition.sqrMagnitude > 0.001f
                ? ClampToPitch(command.targetWorldPosition, 4f)
                : actor.Root.position;
            actor.HoldShape(targetPoint, command.duration);
        }

        public void ExecuteCoverSpace(GtexVisualCommand command)
        {
            if (command == null)
            {
                return;
            }

            if (!TryResolveCommandProxy(command.actorPlayerId, "actor", command.type, out var actor))
            {
                return;
            }

            PrepareForCommandAction(false);
            actor.CoverSpace(ClampToPitch(command.targetWorldPosition, 4f), command.urgency, command.duration);
            FocusToBall();
        }

        public void ExecutePass(string actorId, string receiverId, bool successful)
        {
            ExecutePass(new GtexVisualCommand
            {
                type = GtexVisualCommandType.Pass,
                actorPlayerId = actorId,
                targetPlayerId = receiverId,
                isSuccessful = successful,
                passStyle = GtexVisualPassStyle.Ground
            });
        }

        public void ExecuteThroughPass(string actorId, string receiverId, Vector3 targetPoint)
        {
            ExecutePass(new GtexVisualCommand
            {
                type = GtexVisualCommandType.ThroughPass,
                actorPlayerId = actorId,
                targetPlayerId = receiverId,
                targetWorldPosition = targetPoint,
                passStyle = GtexVisualPassStyle.ThroughGround,
                isSuccessful = true
            });
        }

        public void ExecuteCross(string actorId, Vector3 targetPoint)
        {
            ExecutePass(new GtexVisualCommand
            {
                type = GtexVisualCommandType.Cross,
                actorPlayerId = actorId,
                targetWorldPosition = targetPoint,
                passStyle = GtexVisualPassStyle.Cross,
                isSuccessful = true
            });
        }

        public void ExecutePass(GtexVisualCommand command)
        {
            if (command == null)
            {
                return;
            }

            if (!TryResolveCommandProxy(command.actorPlayerId, "actor", command.type, out var actor))
            {
                Debug.LogWarning("[GTEX VisualBridge] Pass failed: actor=" + command.actorPlayerId + ", target=" + command.targetPlayerId);
                return;
            }

            var receiver = command.type == GtexVisualCommandType.ThroughPass &&
                           string.IsNullOrWhiteSpace(command.targetPlayerId) &&
                           command.targetWorldPosition.sqrMagnitude > 0.001f
                ? null
                : ResolvePassReceiver(actor, command.targetPlayerId);

            PrepareForCommandAction();
            UpdateCameraBallOwner(actor.GtexPlayerId);

            var groundTarget = ResolvePassTarget(actor, receiver, command);
            if (command.passStyle == GtexVisualPassStyle.Ground &&
                receiver != null &&
                IsGroundPassTargetBehindPasser(actor, groundTarget))
            {
                Debug.LogWarning(
                    "[GTEX PASS] rejected actor=" + actor.GtexPlayerId +
                    " target=" + receiver.GtexPlayerId +
                    " reason=behind-passer point=" + groundTarget.ToString("F2"));
                return;
            }

            if (receiver != null &&
                (command.passStyle == GtexVisualPassStyle.Ground || command.passStyle == GtexVisualPassStyle.ThroughGround))
            {
                var receiveUrgency = command.passStyle == GtexVisualPassStyle.ThroughGround ? 0.72f : 0.32f;
                var receiveDuration = command.passStyle == GtexVisualPassStyle.ThroughGround ? 1.1f : 0.65f;
                receiver.PrepareToReceive(
                    groundTarget,
                    receiveUrgency,
                    receiveDuration);
            }

            switch (command.passStyle)
            {
                case GtexVisualPassStyle.Cross:
                    UpdateCameraWorldPassTarget(ResolveTarget(actor, command.targetWorldPosition, 18f), "cross");
                    actor.CrossTo(ResolveTarget(actor, command.targetWorldPosition, 18f));
                    break;
                case GtexVisualPassStyle.Lofted:
                    if (receiver != null)
                    {
                        UpdateCameraPassTarget(command.targetPlayerId);
                    }
                    else
                    {
                        UpdateCameraWorldPassTarget(ResolveTarget(actor, command.targetWorldPosition, 18f), "lofted");
                    }

                    if (receiver != null)
                    {
                        actor.LoftPassTo(receiver);
                    }
                    else
                    {
                        actor.CrossTo(ResolveTarget(actor, command.targetWorldPosition, 18f));
                    }

                    break;
                case GtexVisualPassStyle.ThroughGround:
                    UpdateCameraWorldPassTarget(groundTarget, string.IsNullOrWhiteSpace(command.targetPlayerId) ? "space" : command.targetPlayerId);
                    if (receiver != null)
                    {
                        if (actor.Player != null)
                        {
                            actor.Player.PassingTarget = receiver.Player;
                        }

                        receiver.MoveToSupportPoint(groundTarget, 0.8f, 1f);
                    }

                    if (receiver != null)
                    {
                        actor.GroundPassTo(receiver, groundTarget);
                    }
                    else
                    {
                        actor.GroundPassToPoint(groundTarget);
                    }

                    break;
                case GtexVisualPassStyle.Ground:
                default:
                    if (receiver != null)
                    {
                        UpdateCameraPassTarget(receiver.GtexPlayerId);
                    }
                    else
                    {
                        UpdateCameraWorldPassTarget(groundTarget, "ground");
                    }

                    if (receiver != null)
                    {
                        actor.GroundPassTo(receiver, groundTarget);
                    }
                    else
                    {
                        actor.GroundPassToPoint(groundTarget);
                    }

                    break;
            }

            QueuePassTargetClear(command.isSuccessful ? receiver : null, 1.0f);
            FocusToBall();

            var passLabel = command.type == GtexVisualCommandType.ThroughPass
                ? "Through pass"
                : command.type == GtexVisualCommandType.Cross
                    ? "Cross"
                    : "Pass";
            Debug.Log(
                "[GTEX VisualBridge] " + passLabel + " visual -> style=" + command.passStyle +
                ", actor=" + command.actorPlayerId +
                ", target=" + command.targetPlayerId +
                ", receivePoint=" + groundTarget.ToString("F2"));
        }

        public void ExecuteShot(string actorId, Vector3 targetPoint, string outcome)
        {
            if (!TryResolveCommandProxy(actorId, "actor", GtexVisualCommandType.Shoot, out var actor))
            {
                return;
            }

            PrepareForCommandAction();
            var shotTarget = ResolveSafeShotTarget(actor, targetPoint, outcome);
            lastResolvedShotTarget = shotTarget;
            hasLastResolvedShotTarget = true;
            var cameraShotTarget = Vector3.Lerp(actor.Root.position, shotTarget, 0.58f);
            cameraShotTarget.y = actor.Root.position.y;
            UpdateCameraBallOwner(actor.GtexPlayerId);
            UpdateCameraWorldPassTarget(cameraShotTarget, "shot");
            actor.ShootAt(shotTarget, outcome);
            QueuePassTargetClear(null, 0.8f);
            FocusToBall();
            Debug.Log("[GTEX VisualBridge] Shot -> actor=" + actor.GtexPlayerId + ", outcome=" + outcome + ", target=" + shotTarget);

            if (!string.IsNullOrWhiteSpace(outcome) &&
                outcome.ToLowerInvariant().Contains("save"))
            {
                var keeper = ResolveOpposingKeeper(actor);
                keeper?.KeeperReactToShot(shotTarget);
            }
        }

        public void ExecuteKeeperSave(string keeperId, Vector3 shotTarget)
        {
            if (!TryResolveCommandProxy(keeperId, "actor", GtexVisualCommandType.KeeperSave, out var keeper))
            {
                return;
            }

            PrepareForCommandAction();
            var resolvedShotTarget = hasLastResolvedShotTarget ? lastResolvedShotTarget : shotTarget;
            UpdateCameraBallOwner(keeper.GtexPlayerId);
            UpdateCameraWorldPassTarget(resolvedShotTarget, "keeper-save");
            keeper?.KeeperReactToShot(resolvedShotTarget);
            FocusToBall();
        }

        public void ExecuteKeeperClaim(string keeperId)
        {
            if (!TryResolveCommandProxy(keeperId, "actor", GtexVisualCommandType.KeeperClaim, out var keeper))
            {
                return;
            }

            PrepareForCommandAction();
            UpdateCameraBallOwner(keeper.GtexPlayerId);
            ClearCameraPassTarget();
            keeper?.KeeperClaim();
            hasLastResolvedShotTarget = false;
            FocusToBall();
        }

        public void PlayGoal(string teamId, string scorerId)
        {
            if (!string.IsNullOrWhiteSpace(scorerId) &&
                TryResolveCommandProxy(scorerId, "actor", GtexVisualCommandType.Goal, out var scorer))
            {
                scorer.PlayCelebration();
            }
        }

        public void ResetKickoff()
        {
            var manager = MatchManager.Current;
            if (manager == null)
            {
                return;
            }

            var nativePlay = FStudio.GTEX.Core.GtexOriginalVisualRuntimePolicy.NativeAutonomousPlay;
            MatchManager.SetGlobalCommandDrivenVisualHold(!nativePlay);
            manager.SetExternalPlayback(false);
            manager.MatchFlags = MatchStatus.WaitingForKickOff;

            if (!CanPrepareKickoffState())
            {
                RefreshRuntimeVisualEssentials();
                return;
            }

            if (Ball.Current != null)
            {
                var midPoint = new Vector3(manager.fieldEndX / 2f, 0f, manager.fieldEndY / 2f);
                Ball.Current.ResetBall(midPoint);
            }

            manager.PrePositionTeamsForKickOff();
            UpdateCameraBallOwner(string.Empty);
            ClearCameraPassTarget();
            RefreshRuntimeVisualEssentials();
            FocusToBall();
        }

        public void StartMatch()
        {
            ConfigureOriginalRuntime();
            if (MatchManager.Current != null)
            {
                // Native autonomous play: drop the command-driven hold so the asset AI runs freely.
                // Force Playing so out-of-play detection (throw-ins/corners) and AI decisions are live
                // immediately; the asset's nearest player picks up the centre ball and open play emerges.
                var nativePlay = FStudio.GTEX.Core.GtexOriginalVisualRuntimePolicy.NativeAutonomousPlay;
                MatchManager.SetGlobalCommandDrivenVisualHold(!nativePlay);
                MatchManager.Current.MatchFlags = MatchStatus.Playing;

                if (nativePlay)
                {
                    // The original-visual bootstrap leaves the goal/sideline trigger volumes disabled
                    // (SetExternalPlayback(false) never re-enables them). Without these the ball never
                    // trips the GoalAction/OutAction/ThrowInAction triggers, so goals/throw-ins/corners
                    // are never detected and the ball just rolls out and the match stalls. Re-enable them
                    // exactly like the asset's native match init does.
                    MatchManager.Current.SetGoalColliders(true);
                    MatchManager.Current.SetOutColliders(true);
                }
            }
        }

        public void EndHalf()
        {
            if (MatchManager.Current != null)
            {
                MatchManager.Current.MatchFlags = MatchStatus.Freeze | MatchStatus.Special;
            }
        }

        public void EndMatch()
        {
            if (MatchManager.Current != null)
            {
                MatchManager.Current.MatchFlags = MatchStatus.Special;
            }
        }

        public async void SetCameraMode(string cameraType)
        {
            if (CameraSystem.Current == null || string.IsNullOrWhiteSpace(cameraType))
            {
                return;
            }

            await CameraSystem.Current.SwitchCamera(cameraType);
            activeCameraMode = CameraSystem.Current.CurrentCamera != null ? CameraSystem.Current.CurrentCameraType : string.Empty;
            gameplayCameraReady = CameraSystem.Current.CurrentCamera != null;
            EnsureActionCameraFollow();
            FocusToBall();
        }

        public void FocusToBall()
        {
            MaintainGameplayCameraTarget();
        }

        public void HoldCommandDrivenReadyState()
        {
            if (MatchManager.Current == null)
            {
                return;
            }

            MatchManager.SetGlobalCommandDrivenVisualHold(true);
            if (CanPrepareKickoffState())
            {
                ResetKickoff();
            }
            else
            {
                RefreshRuntimeVisualEssentials();
            }

            MatchManager.Current.MatchFlags = MatchStatus.WaitingForKickOff;
        }

        public bool IsVerificationReady(out string reason)
        {
            RefreshRuntimeVisualEssentials();
            IsRuntimeReady = false;

            var counts = ResolvePlayerCounts();
            if (counts.total < 22)
            {
                reason = "player map incomplete";
                return false;
            }

            if (!IsBallReady)
            {
                reason = "ball missing or renderer disabled";
                return false;
            }

            if (!IsPitchReady)
            {
                reason = "pitch renderer unavailable";
                return false;
            }

            if (!IsLightingReady)
            {
                reason = "lighting not ready";
                return false;
            }

            if (!IsCameraReady)
            {
                reason = "gameplay camera not ready";
                return false;
            }

            if (MatchManager.Current == null)
            {
                reason = "match manager missing";
                return false;
            }

            if (MatchManager.Current.ExternalPlaybackEnabled)
            {
                reason = "external playback still enabled";
                return false;
            }

            reason = null;
            IsRuntimeReady = true;
            return true;
        }

        private bool CanPrepareKickoffState()
        {
            var manager = MatchManager.Current;
            if (manager == null ||
                manager.GameTeam1 == null ||
                manager.GameTeam2 == null ||
                Ball.Current == null)
            {
                return false;
            }

            var counts = ResolvePlayerCounts();
            return counts.total >= 22 && IsBallReady;
        }

        public (int home, int away, int total) ResolvePlayerCounts()
        {
            var manager = MatchManager.Current;
            if (manager == null)
            {
                return (0, 0, 0);
            }

            var proxies = PlayerMap.Proxies.Where(proxy => proxy != null && proxy.Player != null).ToArray();
            var homeCount = proxies.Count(proxy => proxy.Player.GameTeam == manager.GameTeam1);
            var awayCount = proxies.Count(proxy => proxy.Player.GameTeam == manager.GameTeam2);
            return (homeCount, awayCount, proxies.Length);
        }

        public void LogRuntimeReadiness()
        {
            var counts = ResolvePlayerCounts();
            Debug.Log("[GTEX VisualBridge] Player map ready: home=" + counts.home + " away=" + counts.away + " total=" + counts.total);

            if (Ball.Current != null)
            {
                var ballPosition = Ball.Current.transform.position;
                Debug.Log("[GTEX VisualBridge] Ball ready: " + IsBallReady + " position=" + ballPosition);
            }
            else
            {
                Debug.Log("[GTEX VisualBridge] Ball ready: false position=(missing)");
            }

            Debug.Log("[GTEX VisualBridge] Pitch renderer ready: " + IsPitchReady);
            Debug.Log("[GTEX VisualBridge] Lighting ready: " + IsLightingReady);
            Debug.Log("[GTEX VisualBridge] Active camera ready: " + IsCameraReady + " mode=" + activeCameraMode);
        }

        public int GetPlayerTeam(string playerId)
        {
            var manager = MatchManager.Current;
            var proxy = PlayerMap.ResolveProxy(playerId);
            if (manager == null || proxy == null || proxy.Player == null || proxy.Player.GameTeam == null)
            {
                return -1;
            }

            if (proxy.Player.GameTeam == manager.GameTeam1)
            {
                return 0;
            }

            if (proxy.Player.GameTeam == manager.GameTeam2)
            {
                return 1;
            }

            return proxy.Player.GameTeam.TeamId;
        }

        public Vector3 GetPlayerPosition(string playerId)
        {
            var proxy = PlayerMap.ResolveProxy(playerId);
            return proxy != null ? proxy.Root.position : Vector3.zero;
        }

        public Vector3 GetPlayerForward(string playerId)
        {
            var proxy = PlayerMap.ResolveProxy(playerId);
            if (proxy == null)
            {
                return Vector3.zero;
            }

            if (proxy.Player != null && proxy.Player.PlayerController != null)
            {
                return proxy.Player.PlayerController.Forward;
            }

            return proxy.Root.forward;
        }

        public float GetPlayerFieldProgress(string playerId)
        {
            var proxy = PlayerMap.ResolveProxy(playerId);
            return proxy != null && proxy.Player != null
                ? proxy.Player.PlayerFieldProgress
                : 0f;
        }

        public Vector3 GetBallPosition()
        {
            if (Ball.Current != null)
            {
                return Ball.Current.transform.position;
            }

            var owner = PlayerMap.ResolveProxy(currentBallOwnerId);
            return owner != null ? owner.Root.position : Vector3.zero;
        }

        public Vector3 GetAttackingGoalCenter(int possessionTeam)
        {
            return ResolveGoalCenter(possessionTeam, true) + Vector3.up * 1.2f;
        }

        public List<string> GetNearestTeamPlayers(int teamId, Vector3 origin, string excludePlayerId, int maxCount)
        {
            if (maxCount <= 0)
            {
                return new List<string>();
            }

            var excluded = string.IsNullOrWhiteSpace(excludePlayerId)
                ? string.Empty
                : excludePlayerId.Trim().ToLowerInvariant();

            return PlayerMap.Proxies
                .Where(proxy =>
                    proxy != null &&
                    proxy.Player != null &&
                    !proxy.IsGoalkeeper &&
                    GetPlayerTeam(proxy.GtexPlayerId) == teamId &&
                    (string.IsNullOrWhiteSpace(excluded) ||
                     !string.Equals(proxy.GtexPlayerId, excluded, StringComparison.OrdinalIgnoreCase)))
                .OrderBy(proxy => Vector3.SqrMagnitude(proxy.Root.position - origin))
                .Take(maxCount)
                .Select(proxy => proxy.GtexPlayerId)
                .ToList();
        }

        public bool IsPlayerHoldingBall(string playerId)
        {
            var proxy = PlayerMap.ResolveProxy(playerId);
            return proxy != null && proxy.Player != null && Ball.Current != null && Ball.Current.HolderPlayer == proxy.Player;
        }

        public bool IsGoalkeeper(string playerId)
        {
            var proxy = PlayerMap.ResolveProxy(playerId);
            return proxy != null && proxy.IsGoalkeeper;
        }

        public float GetNearestOpponentDistance(int possessionTeam, Vector3 origin)
        {
            var nearest = PlayerMap.Proxies
                .Where(proxy =>
                    proxy != null &&
                    proxy.Player != null &&
                    !proxy.IsGoalkeeper &&
                    GetPlayerTeam(proxy.GtexPlayerId) != possessionTeam)
                .Select(proxy => DistanceXZ(proxy.Root.position, origin))
                .DefaultIfEmpty(-1f)
                .Min();

            return nearest;
        }

        public bool IsNearPitchBoundary(Vector3 point, float distance)
        {
            var manager = MatchManager.Current;
            if (manager == null)
            {
                return false;
            }

            var maxX = manager.fieldEndX > 0f ? manager.fieldEndX : manager.SizeOfField.x;
            var maxZ = manager.fieldEndY > 0f ? manager.fieldEndY : manager.SizeOfField.y;
            return point.x <= distance ||
                   point.z <= distance ||
                   point.x >= maxX - distance ||
                   point.z >= maxZ - distance;
        }

        public bool IsWideAttackingCrossPosition(string playerId, Vector3 point)
        {
            var manager = MatchManager.Current;
            if (manager == null || GetPlayerFieldProgress(playerId) < 0.58f)
            {
                return false;
            }

            var maxZ = manager.fieldEndY > 0f ? manager.fieldEndY : manager.SizeOfField.y;
            return point.z <= 12f || point.z >= maxZ - 12f;
        }

        public string FindBestIntentPassTarget(int possessionTeam, string ballOwnerId, Vector3 attackingGoal)
        {
            var owner = PlayerMap.ResolveProxy(ballOwnerId);
            if (owner == null || owner.Player == null)
            {
                return string.Empty;
            }

            var ownerPosition = owner.Root.position;
            var toGoal = attackingGoal - ownerPosition;
            toGoal.y = 0f;
            if (toGoal.sqrMagnitude <= 0.01f)
            {
                toGoal = GetPlayerForward(ballOwnerId);
                toGoal.y = 0f;
            }

            if (toGoal.sqrMagnitude <= 0.01f)
            {
                toGoal = Vector3.right;
            }

            toGoal.Normalize();
            var ownerProgress = GetPlayerFieldProgress(ballOwnerId);
            var ownerIsGoalkeeper = owner.IsGoalkeeper;

            return PlayerMap.Proxies
                .Where(proxy =>
                    proxy != null &&
                    proxy != owner &&
                    proxy.Player != null &&
                    !proxy.IsGoalkeeper &&
                    GetPlayerTeam(proxy.GtexPlayerId) == possessionTeam)
                .Select(proxy => new
                {
                    proxy,
                    score = ResolveIntentPassScore(proxy, ownerPosition, toGoal, ownerProgress, ownerIsGoalkeeper)
                })
                .OrderBy(item => item.score)
                .Select(item => item.proxy.GtexPlayerId)
                .FirstOrDefault() ?? string.Empty;
        }

        public string FindBestIntentCrossTarget(int possessionTeam, string ballOwnerId, Vector3 attackingGoal)
        {
            var owner = PlayerMap.ResolveProxy(ballOwnerId);
            var manager = MatchManager.Current;
            if (owner == null || owner.Player == null || manager == null)
            {
                return string.Empty;
            }

            var centerZ = (manager.fieldEndY > 0f ? manager.fieldEndY : manager.SizeOfField.y) * 0.5f;
            var ownerProgress = GetPlayerFieldProgress(ballOwnerId);

            return PlayerMap.Proxies
                .Where(proxy =>
                    proxy != null &&
                    proxy != owner &&
                    proxy.Player != null &&
                    !proxy.IsGoalkeeper &&
                    GetPlayerTeam(proxy.GtexPlayerId) == possessionTeam &&
                    GetPlayerFieldProgress(proxy.GtexPlayerId) >= ownerProgress - 0.08f)
                .OrderBy(proxy =>
                {
                    var distanceToGoal = DistanceXZ(proxy.Root.position, attackingGoal);
                    var centrality = Mathf.Abs(proxy.Root.position.z - centerZ);
                    var distanceFromCrosser = DistanceXZ(proxy.Root.position, owner.Root.position);
                    var progress = GetPlayerFieldProgress(proxy.GtexPlayerId);
                    return distanceToGoal * 0.48f +
                           centrality * 0.22f +
                           distanceFromCrosser * 0.05f -
                           progress * 8f;
                })
                .Select(proxy => proxy.GtexPlayerId)
                .FirstOrDefault() ?? string.Empty;
        }

        private float ResolveIntentPassScore(
            GtexOriginalPlayerVisualProxy candidate,
            Vector3 ownerPosition,
            Vector3 toGoal,
            float ownerProgress,
            bool ownerIsGoalkeeper)
        {
            var offset = candidate.Root.position - ownerPosition;
            offset.y = 0f;

            var distance = offset.magnitude;
            if (distance < 3.5f)
            {
                return 1000f + (3.5f - distance) * 20f;
            }

            var forwardScore = distance > 0.01f ? Vector3.Dot(toGoal, offset / distance) : 0f;
            var receiverProgress = GetPlayerFieldProgress(candidate.GtexPlayerId);
            var progressGain = receiverProgress - ownerProgress;
            var boundaryPenalty = ResolveBoundaryPenalty(candidate.Root.position, 6f) * 4.5f;

            if (ownerIsGoalkeeper)
            {
                var shortDistributionScore = Mathf.Abs(distance - 14f) * 0.72f;
                var tooShortPenalty = distance < 7f ? (7f - distance) * 3f : 0f;
                var keeperTooLongPenalty = distance > 22f ? (distance - 22f) * 4.5f : 0f;

                return shortDistributionScore +
                       tooShortPenalty +
                       keeperTooLongPenalty +
                       boundaryPenalty -
                       forwardScore * 1.2f -
                       Mathf.Max(0f, progressGain) * 2.2f;
            }

            var distanceScore = Mathf.Abs(distance - 13f) * 0.42f;
            var tooLongPenalty = distance > 24f ? (distance - 24f) * 2.4f : 0f;
            var backwardPenalty = progressGain < -0.08f ? Mathf.Abs(progressGain) * 9f : 0f;

            return distanceScore +
                   tooLongPenalty +
                   boundaryPenalty +
                   backwardPenalty -
                   forwardScore * 3.8f -
                   Mathf.Max(0f, progressGain) * 7f;
        }

        public string FindBestMarkTarget(string defenderId, List<string> attackers)
        {
            var defender = PlayerMap.ResolveProxy(defenderId);
            if (defender == null || attackers == null || attackers.Count == 0)
            {
                return string.Empty;
            }

            var defendingTeam = GetPlayerTeam(defenderId);
            var ownGoal = ResolveGoalCenter(defendingTeam, false);
            var defenderPos = defender.Root.position;
            var bestScore = float.MaxValue;
            var bestTargetId = string.Empty;

            for (var index = 0; index < attackers.Count; index += 1)
            {
                var targetId = attackers[index];
                var attacker = PlayerMap.ResolveProxy(targetId);
                if (attacker == null)
                {
                    continue;
                }

                var attackerPos = attacker.Root.position;
                var score =
                    Vector3.SqrMagnitude(attackerPos - defenderPos) +
                    Vector3.SqrMagnitude(attackerPos - ownGoal) * 0.2f;

                if (score < bestScore)
                {
                    bestScore = score;
                    bestTargetId = targetId;
                }
            }

            return bestTargetId;
        }

        public string FindNearestDefenderToBall(int defendingTeam, Vector3 ballPos)
        {
            return GetNearestTeamPlayers(defendingTeam, ballPos, null, 1).FirstOrDefault() ?? string.Empty;
        }

        public Vector3 ResolveSupportPoint(string supportPlayerId, string ballOwnerId, Vector3 attackingGoal, int supportIndex)
        {
            var support = PlayerMap.ResolveProxy(supportPlayerId);
            var owner = PlayerMap.ResolveProxy(ballOwnerId);
            if (support == null || owner == null)
            {
                return Vector3.zero;
            }

            var ownerPos = owner.Root.position;
            var toGoal = attackingGoal - ownerPos;
            toGoal.y = 0f;

            if (toGoal.sqrMagnitude < 0.01f)
            {
                toGoal = GetPlayerForward(ballOwnerId);
                toGoal.y = 0f;
            }

            if (toGoal.sqrMagnitude < 0.01f)
            {
                toGoal = Vector3.right;
            }

            toGoal.Normalize();
            var right = Vector3.Cross(Vector3.up, toGoal).normalized;

            Vector3 point;
            switch (supportIndex)
            {
                case 0:
                    point = ownerPos - toGoal * 7f + right * 4f;
                    break;
                case 1:
                    point = ownerPos + toGoal * 9f - right * 5f;
                    break;
                case 2:
                    point = ownerPos + right * 11f;
                    break;
                default:
                    point = support.Root.position;
                    break;
            }

            point.y = support.Root.position.y;
            return ClampToPitch(point, 4f);
        }

        public bool HasShootingLane(string shooterId, Vector3 goalTarget)
        {
            var shooter = PlayerMap.ResolveProxy(shooterId);
            if (shooter == null)
            {
                return false;
            }

            var start = shooter.Root.position + Vector3.up * 0.35f;
            var end = goalTarget + Vector3.up * 0.5f;
            var direction = end - start;
            var distance = direction.magnitude;
            if (distance < 0.1f)
            {
                return false;
            }

            return !IsOpponentBlockingShotLine(shooterId, start, end, 2.2f);
        }

        public Vector3 ClampToPitch(Vector3 point, float margin = 0.5f)
        {
            var manager = MatchManager.Current;
            if (manager == null)
            {
                return point;
            }

            var maxX = manager.fieldEndX > 0f ? manager.fieldEndX : manager.SizeOfField.x;
            var maxZ = manager.fieldEndY > 0f ? manager.fieldEndY : manager.SizeOfField.y;
            var safeMargin = Mathf.Clamp(margin, 0.5f, Mathf.Min(maxX, maxZ) * 0.25f);
            point.x = Mathf.Clamp(point.x, safeMargin, Mathf.Max(safeMargin, maxX - safeMargin));
            point.z = Mathf.Clamp(point.z, safeMargin, Mathf.Max(safeMargin, maxZ - safeMargin));
            return point;
        }

        private static float ResolveBoundaryPenalty(Vector3 point, float safeMargin)
        {
            var manager = MatchManager.Current;
            if (manager == null)
            {
                return 0f;
            }

            var maxX = manager.fieldEndX > 0f ? manager.fieldEndX : manager.SizeOfField.x;
            var maxZ = manager.fieldEndY > 0f ? manager.fieldEndY : manager.SizeOfField.y;
            var edgeDistance = Mathf.Min(point.x, point.z, maxX - point.x, maxZ - point.z);
            return Mathf.Max(0f, safeMargin - edgeDistance);
        }

        private void EnsureHelpers()
        {
            if (pitchVisualFallback == null)
            {
                pitchVisualFallback = GetComponent<GtexOriginalPitchVisualFallback>();
                if (pitchVisualFallback == null)
                {
                    pitchVisualFallback = gameObject.AddComponent<GtexOriginalPitchVisualFallback>();
                }
            }

            if (cinemachineFootballCameraDirector == null)
            {
                cinemachineFootballCameraDirector = GetComponent<GtexCinemachineFootballCameraDirector>();
                if (cinemachineFootballCameraDirector == null)
                {
                    cinemachineFootballCameraDirector = gameObject.AddComponent<GtexCinemachineFootballCameraDirector>();
                }
            }
        }

        private void RefreshRuntimeVisualEssentials()
        {
            EnsureHelpers();
            EnsurePitchVisible();
            EnsureMatchLighting();
            EnsureActionCameraFollow();
            MaintainGameplayCameraTarget();
        }

        private void EnsurePitchVisible()
        {
            var fieldLength = MatchManager.Current != null ? Mathf.Max(10f, MatchManager.Current.fieldEndX) : 105f;
            var fieldWidth = MatchManager.Current != null ? Mathf.Max(10f, MatchManager.Current.fieldEndY) : 68f;
            pitchReady = pitchVisualFallback != null && pitchVisualFallback.EnsurePitchVisible(fieldLength, fieldWidth);
        }

        private void EnsureMatchLighting()
        {
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.55f, 0.55f, 0.55f, 1f);

            var lights = FindObjectsByType<Light>(FindObjectsInactive.Include, FindObjectsSortMode.None);
            var existingSun = lights.FirstOrDefault(light => light != null && light.type == LightType.Directional);

            if (existingSun == null)
            {
                var sun = new GameObject("GTEX_OriginalVisualRuntime_Sun");
                existingSun = sun.AddComponent<Light>();
                existingSun.type = LightType.Directional;
                existingSun.transform.rotation = Quaternion.Euler(50f, -30f, 0f);
            }

            existingSun.enabled = true;
            existingSun.intensity = Mathf.Max(existingSun.intensity, 1.1f);
            lightingReady = true;
        }

        private async void ActivateOriginalGameplayCamera()
        {
            if (cameraActivationInProgress)
            {
                return;
            }

            cameraActivationInProgress = true;
            gameplayCameraReady = false;
            activeCameraMode = string.Empty;

            try
            {
                if (CameraSystem.Current != null)
                {
                    CameraSystem.Current.enabled = true;

                    for (var index = 0; index < PreferredCameraModes.Length; index += 1)
                    {
                        var mode = PreferredCameraModes[index];
                        await CameraSystem.Current.SwitchCamera(mode, true);
                        if (CameraSystem.Current.CurrentCamera == null)
                        {
                            continue;
                        }

                        usingFallbackCamera = false;
                        DisableFallbackFollowCamera();
                        activeCameraMode = CameraSystem.Current.CurrentCameraType;
                        gameplayCameraReady = true;
                        EnsureActionCameraFollow();
                        MaintainGameplayCameraTarget();
                        Debug.Log("[GTEX OriginalVisualRuntime] Gameplay camera activated: " + activeCameraMode + ".");
                        return;
                    }
                }

                Debug.LogWarning("[GTEX OriginalVisualRuntime] CameraSystem missing or no gameplay camera mode resolved; using action follow camera.");
                EnsureActionCameraFollow();
            }
            finally
            {
                cameraActivationInProgress = false;
            }
        }

        private void EnsureActionCameraFollow()
        {
            var camera = ResolveOriginalMatchCamera() ?? ResolveActiveCamera();
            if (camera == null)
            {
                camera = FindFirstObjectByType<Camera>();
                if (camera == null)
                {
                    gameplayCameraReady = false;
                    activeCameraMode = string.Empty;
                    return;
                }
            }

            EnsureSingleGameplayCamera(camera);
            originalCamera = camera;
            DisableFallbackFollowCamera();
            usingFallbackCamera = false;

            var ballTransform = ResolveOriginalBallTransform();
            var playerTransforms = ResolveAllPlayerTransforms();
            var goalkeeperTransforms = ResolveGoalkeeperTransforms();

            if (preferCinemachineFootballCamera &&
                TryEnableCinemachineFootballCamera(camera, ballTransform, playerTransforms, goalkeeperTransforms))
            {
                UpdateActionCameraBindingLog(
                    camera,
                    ballTransform,
                    playerTransforms.Count,
                    cinemachineFootballCameraDirector != null ? cinemachineFootballCameraDirector.ModeName : "CinemachineFootball");
                return;
            }

            EnsureLegacyActionCameraFollow(camera, ballTransform, playerTransforms, goalkeeperTransforms);
        }

        private bool TryEnableCinemachineFootballCamera(
            Camera camera,
            Transform ballTransform,
            List<Transform> playerTransforms,
            List<Transform> goalkeeperTransforms)
        {
            if (cinemachineFootballCameraDirector == null)
            {
                return false;
            }

            cinemachineFootballCameraDirector.Bind(
                camera,
                ballTransform,
                playerTransforms,
                ResolveOriginalBallTransform,
                ResolveCurrentAttackingGoal,
                goalkeeperTransforms);
            cinemachineFootballCameraDirector.SetCameraActive(true);

            SyncPrimaryActionCameraTargets();

            if (!cinemachineFootballCameraDirector.HasBoundCamera)
            {
                return false;
            }

            if (CameraSystem.Current != null)
            {
                CameraSystem.Current.enabled = false;
            }

            DisableLegacyActionCameraDriver();
            gameplayCameraReady = cinemachineFootballCameraDirector.HasValidFocus;
            activeCameraMode = ResolveBaseCameraMode(camera) + "+" + cinemachineFootballCameraDirector.ModeName;
            return true;
        }

        private void EnsureLegacyActionCameraFollow(
            Camera camera,
            Transform ballTransform,
            List<Transform> playerTransforms,
            List<Transform> goalkeeperTransforms)
        {
            cinemachineFootballCameraDirector?.SetCameraActive(false);

            if (CameraSystem.Current != null)
            {
                CameraSystem.Current.enabled = true;
            }

            if (actionCameraDriver == null || actionCameraDriver.gameObject != camera.gameObject)
            {
                actionCameraDriver = camera.gameObject.GetComponent<GtexOriginalActionCameraDriver>();
                if (actionCameraDriver == null)
                {
                    actionCameraDriver = camera.gameObject.AddComponent<GtexOriginalActionCameraDriver>();
                }
            }

            actionCameraDriver.enabled = true;
            actionCameraDriver.Bind(
                camera,
                ballTransform,
                playerTransforms,
                ResolveOriginalBallTransform,
                ResolveCurrentAttackingGoal,
                goalkeeperTransforms);

            SyncPrimaryActionCameraTargets();

            gameplayCameraReady = actionCameraDriver.HasBoundCamera && actionCameraDriver.HasValidFocus;
            activeCameraMode = ResolveBaseCameraMode(camera) + "+" + actionCameraDriver.ModeName;

            UpdateActionCameraBindingLog(camera, ballTransform, playerTransforms.Count, actionCameraDriver.ModeName);
        }

        private void SyncPrimaryActionCameraTargets()
        {
            if (Ball.Current != null && Ball.Current.HolderPlayer != null &&
                PlayerMap.TryGetProxy(Ball.Current.HolderPlayer, out var holderProxy))
            {
                UpdateCameraBallOwner(holderProxy.GtexPlayerId);
            }
            else if (!string.IsNullOrWhiteSpace(currentBallOwnerId))
            {
                UpdateCameraBallOwner(currentBallOwnerId);
            }

            if (!string.IsNullOrWhiteSpace(currentCameraPassTargetId))
            {
                if (hasCurrentCameraWorldPassTarget)
                {
                    UpdateCameraWorldPassTarget(currentCameraWorldPassTarget, currentCameraPassTargetId);
                }
                else
                {
                    UpdateCameraPassTarget(currentCameraPassTargetId);
                }
            }
        }

        private void UpdateActionCameraBindingLog(Camera camera, Transform ballTransform, int playerCount, string modeName)
        {
            var bindingKey = camera.GetInstanceID() + ":" +
                             (ballTransform != null ? ballTransform.GetInstanceID() : 0) + ":" +
                             playerCount + ":" + modeName;
            if (!string.Equals(lastActionCameraBindingKey, bindingKey))
            {
                lastActionCameraBindingKey = bindingKey;
                Debug.Log(
                    "[GTEX VisualBridge] Action camera follow enabled. " +
                    "camera=" + camera.name +
                    ", mode=" + modeName +
                    ", ball=" + (ballTransform != null) +
                    ", players=" + playerCount);
            }

            var ballBound = ballTransform != null;
            if (!lastCameraBallBoundState.HasValue || lastCameraBallBoundState.Value != ballBound)
            {
                lastCameraBallBoundState = ballBound;
                Debug.Log("[GTEX VisualBridge] Camera ball bound: " + ballBound);
            }
        }

        private void DisableLegacyActionCameraDriver()
        {
            if (actionCameraDriver != null)
            {
                actionCameraDriver.enabled = false;
            }
        }

        private void EnsureFallbackFollowCamera()
        {
            if (!createFallbackFollowCameraIfNeeded)
            {
                gameplayCameraReady = false;
                activeCameraMode = string.Empty;
                return;
            }

            var camera = ResolveActiveCamera();
            if (camera == null)
            {
                gameplayCameraReady = false;
                activeCameraMode = string.Empty;
                return;
            }

            if (CameraSystem.Current != null)
            {
                CameraSystem.Current.enabled = false;
            }

            cinemachineFootballCameraDirector?.SetCameraActive(false);
            DisableLegacyActionCameraDriver();
            if (fallbackFollowCamera == null || fallbackFollowCamera.gameObject != camera.gameObject)
            {
                fallbackFollowCamera = camera.GetComponent<GtexOriginalFallbackFollowCamera>();
                if (fallbackFollowCamera == null)
                {
                    fallbackFollowCamera = camera.gameObject.AddComponent<GtexOriginalFallbackFollowCamera>();
                }
            }

            fallbackFollowCamera.enabled = true;
            fallbackFollowCamera.Bind(Ball.Current != null ? Ball.Current.transform : null, ResolvePlayerTransforms());
            usingFallbackCamera = true;
            gameplayCameraReady = fallbackFollowCamera.HasValidFocus;
            activeCameraMode = fallbackFollowCamera.ModeName;
        }

        private void DisableFallbackFollowCamera()
        {
            if (fallbackFollowCamera != null)
            {
                fallbackFollowCamera.enabled = false;
            }
        }

        private void MaintainGameplayCameraTarget()
        {
            if (usingFallbackCamera)
            {
                if (fallbackFollowCamera != null)
                {
                    fallbackFollowCamera.Bind(Ball.Current != null ? Ball.Current.transform : null, ResolvePlayerTransforms());
                    gameplayCameraReady = fallbackFollowCamera.HasValidFocus;
                    activeCameraMode = fallbackFollowCamera.ModeName;
                }

                return;
            }

            if (cinemachineFootballCameraDirector != null && cinemachineFootballCameraDirector.HasBoundCamera)
            {
                if (Ball.Current != null && Ball.Current.HolderPlayer != null &&
                    PlayerMap.TryGetProxy(Ball.Current.HolderPlayer, out var holderProxy))
                {
                    UpdateCameraBallOwner(holderProxy.GtexPlayerId);
                }

                if (CameraSystem.Current != null)
                {
                    CameraSystem.Current.enabled = false;
                }

                DisableLegacyActionCameraDriver();
                gameplayCameraReady = cinemachineFootballCameraDirector.HasValidFocus;
                activeCameraMode = ResolveBaseCameraMode(originalCamera != null ? originalCamera : ResolveActiveCamera()) + "+" + cinemachineFootballCameraDirector.ModeName;
                return;
            }

            if (actionCameraDriver != null && actionCameraDriver.HasBoundCamera)
            {
                if (Ball.Current != null && Ball.Current.HolderPlayer != null &&
                    PlayerMap.TryGetProxy(Ball.Current.HolderPlayer, out var holderProxy))
                {
                    UpdateCameraBallOwner(holderProxy.GtexPlayerId);
                }

                gameplayCameraReady = actionCameraDriver.HasValidFocus;
            }

            if (CameraSystem.Current == null || CameraSystem.Current.CurrentCamera == null)
            {
                EnsureActionCameraFollow();
                return;
            }

            if (Ball.Current != null)
            {
                if (CameraSystem.Current.target != Ball.Current.transform || CameraSystem.Current.TargetPosition.HasValue)
                {
                    CameraSystem.Current.FocusToBall(false);
                }
            }
            else
            {
                CameraSystem.Current.FocusToPosition(CalculatePlayerClusterCenter(), false);
            }

            gameplayCameraReady = true;
            if (actionCameraDriver != null && actionCameraDriver.HasBoundCamera)
            {
                activeCameraMode = CameraSystem.Current.CurrentCameraType + "+" + actionCameraDriver.ModeName;
            }
            else
            {
                activeCameraMode = CameraSystem.Current.CurrentCameraType;
            }
        }

        private IEnumerable<Transform> ResolvePlayerTransforms()
        {
            return PlayerMap.Proxies
                .Where(proxy => proxy != null && proxy.Root != null)
                .Select(proxy => proxy.Root);
        }

        private Transform ResolveOriginalBallTransform()
        {
            if (Ball.Current != null)
            {
                return Ball.Current.transform;
            }

            var balls = FindObjectsByType<Ball>(FindObjectsSortMode.None);
            for (var index = 0; index < balls.Length; index += 1)
            {
                if (balls[index] != null && balls[index].gameObject.activeInHierarchy)
                {
                    return balls[index].transform;
                }
            }

            var ballObject = GameObject.Find("Ball");
            return ballObject != null ? ballObject.transform : null;
        }

        private List<Transform> ResolveAllPlayerTransforms()
        {
            var results = new List<Transform>();
            foreach (var proxy in FindObjectsByType<GtexOriginalPlayerVisualProxy>(FindObjectsSortMode.None))
            {
                if (proxy != null && proxy.Root != null)
                {
                    results.Add(proxy.Root);
                }
            }

            if (results.Count == 0)
            {
                foreach (var animator in FindObjectsByType<Animator>(FindObjectsSortMode.None))
                {
                    if (animator == null || !animator.gameObject.activeInHierarchy)
                    {
                        continue;
                    }

                    if (animator.name.ToLowerInvariant().Contains("player"))
                    {
                        results.Add(animator.transform);
                    }
                }
            }

            return results;
        }

        private List<Transform> ResolveGoalkeeperTransforms()
        {
            return PlayerMap.Proxies
                .Where(proxy => proxy != null && proxy.IsGoalkeeper && proxy.Root != null)
                .Select(proxy => proxy.Root)
                .ToList();
        }

        private void SyncCurrentBallOwnerFromBall()
        {
            if (Ball.Current == null)
            {
                if (!string.IsNullOrWhiteSpace(currentBallOwnerId))
                {
                    UpdateCameraBallOwner(string.Empty);
                }

                return;
            }

            if (Ball.Current.HolderPlayer != null &&
                PlayerMap.TryGetProxy(Ball.Current.HolderPlayer, out var holderProxy))
            {
                if (!string.Equals(currentBallOwnerId, holderProxy.GtexPlayerId, StringComparison.OrdinalIgnoreCase))
                {
                    UpdateCameraBallOwner(holderProxy.GtexPlayerId);
                }

                return;
            }

            if (string.IsNullOrWhiteSpace(currentBallOwnerId))
            {
                return;
            }

            var currentOwner = PlayerMap.ResolveProxy(currentBallOwnerId);
            if (currentOwner == null || currentOwner.Root == null ||
                DistanceXZ(currentOwner.Root.position, Ball.Current.transform.position) > 2.4f)
            {
                UpdateCameraBallOwner(string.Empty);
            }
        }

        private void UpdateCameraBallOwner(string playerId)
        {
            currentBallOwnerId = playerId ?? string.Empty;
            Transform ownerTransform = null;
            var ownerKey = string.Empty;

            if (string.IsNullOrWhiteSpace(playerId))
            {
                cinemachineFootballCameraDirector?.SetBallOwner(null, string.Empty);
                actionCameraDriver?.SetBallOwner(null, string.Empty);
                return;
            }

            var proxy = PlayerMap.ResolveProxy(playerId);
            if (proxy != null)
            {
                ownerTransform = proxy.Root;
                ownerKey = proxy.GtexPlayerId;
                currentBallOwnerId = ownerKey;
            }

            cinemachineFootballCameraDirector?.SetBallOwner(ownerTransform, ownerKey);
            actionCameraDriver?.SetBallOwner(ownerTransform, ownerKey);
        }

        private void UpdateCameraPassTarget(string targetPlayerId)
        {
            var target = PlayerMap.ResolveProxy(targetPlayerId);
            if (target != null)
            {
                currentCameraPassTargetId = target.GtexPlayerId;
                currentCameraWorldPassTarget = Vector3.zero;
                hasCurrentCameraWorldPassTarget = false;
                cinemachineFootballCameraDirector?.SetPassTarget(target.Root, target.GtexPlayerId);
                actionCameraDriver?.SetPassTarget(target.Root, target.GtexPlayerId);
            }
            else
            {
                ClearCameraPassTarget();
            }
        }

        private void UpdateCameraWorldPassTarget(Vector3 targetPoint, string targetId)
        {
            currentCameraPassTargetId = targetId ?? string.Empty;
            currentCameraWorldPassTarget = targetPoint;
            hasCurrentCameraWorldPassTarget = true;
            cinemachineFootballCameraDirector?.SetWorldPassTarget(targetPoint, currentCameraPassTargetId);
            actionCameraDriver?.SetWorldPassTarget(targetPoint, currentCameraPassTargetId);
        }

        private void ClearCameraPassTarget()
        {
            currentCameraPassTargetId = string.Empty;
            currentCameraWorldPassTarget = Vector3.zero;
            hasCurrentCameraWorldPassTarget = false;
            cinemachineFootballCameraDirector?.ClearPassTarget();
            actionCameraDriver?.ClearPassTarget();
        }

        private void QueuePassTargetClear(GtexOriginalPlayerVisualProxy nextOwner, float delay)
        {
            if (clearPassTargetRoutine != null)
            {
                StopCoroutine(clearPassTargetRoutine);
            }

            clearPassTargetRoutine = StartCoroutine(ClearPassTargetAfterDelay(delay, nextOwner));
        }

        private IEnumerator ClearPassTargetAfterDelay(float delay, GtexOriginalPlayerVisualProxy nextOwner)
        {
            yield return new WaitForSeconds(delay);

            if (cinemachineFootballCameraDirector != null || actionCameraDriver != null)
            {
                if (nextOwner != null)
                {
                    UpdateCameraBallOwner(nextOwner.GtexPlayerId);
                }

                ClearCameraPassTarget();
            }

            clearPassTargetRoutine = null;
        }

        private Vector3 CalculatePlayerClusterCenter()
        {
            var transforms = ResolvePlayerTransforms().ToArray();
            if (transforms.Length == 0)
            {
                return Vector3.zero;
            }

            Vector3 sum = Vector3.zero;
            var count = 0;
            for (var index = 0; index < transforms.Length; index += 1)
            {
                if (transforms[index] == null)
                {
                    continue;
                }

                sum += transforms[index].position;
                count += 1;
            }

            return count > 0 ? sum / count : Vector3.zero;
        }

        private string ResolveBaseCameraMode(Camera camera)
        {
            if (CameraSystem.Current != null && !string.IsNullOrWhiteSpace(CameraSystem.Current.CurrentCameraType))
            {
                return CameraSystem.Current.CurrentCameraType;
            }

            return camera != null ? camera.name : "Camera";
        }

        private Camera ResolveActiveCamera()
        {
            var originalMatchCamera = ResolveOriginalMatchCamera();
            if (originalMatchCamera != null)
            {
                return originalMatchCamera;
            }

            if (CameraSystem.Current != null && CameraSystem.Current.camera != null)
            {
                return CameraSystem.Current.camera;
            }

            if (originalCamera != null)
            {
                return originalCamera;
            }

            if (Camera.main != null)
            {
                return Camera.main;
            }

            return FindObjectsByType<Camera>(FindObjectsInactive.Include, FindObjectsSortMode.None).FirstOrDefault();
        }

        private Camera ResolveOriginalMatchCamera()
        {
            if (IsOriginalGameplayCameraCandidate(originalCamera))
            {
                return originalCamera;
            }

            if (CameraSystem.Current != null && IsOriginalGameplayCameraCandidate(CameraSystem.Current.camera))
            {
                originalCamera = CameraSystem.Current.camera;
                return originalCamera;
            }

            var cameraSystems = FindObjectsByType<CameraSystem>(FindObjectsInactive.Include, FindObjectsSortMode.None);
            for (var index = 0; index < cameraSystems.Length; index += 1)
            {
                var cameraSystem = cameraSystems[index];
                if (cameraSystem == null || !IsOriginalGameplayCameraCandidate(cameraSystem.camera))
                {
                    continue;
                }

                originalCamera = cameraSystem.camera;
                return originalCamera;
            }

            var cameras = FindObjectsByType<Camera>(FindObjectsInactive.Include, FindObjectsSortMode.None);
            Camera fallbackCandidate = null;
            for (var index = 0; index < cameras.Length; index += 1)
            {
                var camera = cameras[index];
                if (!IsOriginalGameplayCameraCandidate(camera))
                {
                    continue;
                }

                var lowerName = camera.gameObject.name.ToLowerInvariant();
                if (OriginalCameraNameHints.Any(hint => lowerName.Contains(hint)))
                {
                    originalCamera = camera;
                    return originalCamera;
                }

                if (fallbackCandidate == null)
                {
                    fallbackCandidate = camera;
                }
            }

            originalCamera = fallbackCandidate;
            return originalCamera;
        }

        private static bool IsOriginalGameplayCameraCandidate(Camera camera)
        {
            if (camera == null || camera.targetTexture != null)
            {
                return false;
            }

            var lowerName = (camera.gameObject.name ?? string.Empty).ToLowerInvariant();
            if (lowerName.Contains("ui"))
            {
                return false;
            }

            return camera.GetComponentInParent<Canvas>() == null;
        }

        private Vector3? ResolveCurrentAttackingGoal()
        {
            var manager = MatchManager.Current;
            if (manager == null)
            {
                return null;
            }

            var owner = ResolveCurrentBallOwner();
            if (owner != null && owner.GameTeam != null)
            {
                var goal = owner.GameTeam == manager.GameTeam1 ? manager.goalNet2 : manager.goalNet1;
                return goal != null ? goal.Position : null;
            }

            var ballTransform = ResolveOriginalBallTransform();
            if (ballTransform == null)
            {
                return null;
            }

            var halfFieldX = manager.fieldEndX > 0f ? manager.fieldEndX * 0.5f : manager.SizeOfField.x * 0.5f;
            var fallbackGoal = ballTransform.position.x <= halfFieldX ? manager.goalNet2 : manager.goalNet1;
            return fallbackGoal != null ? fallbackGoal.Position : null;
        }

        private PlayerBase ResolveCurrentBallOwner()
        {
            if (!string.IsNullOrWhiteSpace(currentBallOwnerId) &&
                PlayerMap.TryGetProxy(currentBallOwnerId, out var proxy) &&
                proxy != null)
            {
                return proxy.Player;
            }

            if (Ball.Current != null && Ball.Current.HolderPlayer != null)
            {
                return Ball.Current.HolderPlayer;
            }

            if (Ball.Current != null && Ball.Current.LastTouchedPlayer != null)
            {
                return Ball.Current.LastTouchedPlayer;
            }

            return null;
        }

        private static void EnsureSingleGameplayCamera(Camera chosen)
        {
            if (chosen == null)
            {
                return;
            }

            var allCameras = UnityEngine.Object.FindObjectsByType<Camera>(FindObjectsInactive.Include, FindObjectsSortMode.None);
            for (var index = 0; index < allCameras.Length; index += 1)
            {
                var camera = allCameras[index];
                if (camera == null)
                {
                    continue;
                }

                if (camera == chosen)
                {
                    camera.enabled = true;
                    continue;
                }

                if (camera.targetTexture != null)
                {
                    continue;
                }

                var lowerName = camera.gameObject.name.ToLowerInvariant();
                if (lowerName.Contains("ui") || camera.GetComponentInParent<Canvas>() != null)
                {
                    continue;
                }

                camera.enabled = false;
            }
        }

        private static bool HasEnabledRenderer(Transform root)
        {
            if (root == null)
            {
                return false;
            }

            var renderers = root.GetComponentsInChildren<Renderer>(true);
            for (var index = 0; index < renderers.Length; index += 1)
            {
                if (renderers[index] != null && renderers[index].enabled)
                {
                    return true;
                }
            }

            return false;
        }

        private static Vector3 ResolveTarget(GtexOriginalPlayerVisualProxy actor, Vector3 requested, float fallbackDistance)
        {
            if (requested.sqrMagnitude > 0.001f)
            {
                return requested;
            }

            var forward = actor != null && actor.Player != null && actor.Player.PlayerController != null
                ? actor.Player.PlayerController.Forward
                : Vector3.forward;

            return actor != null
                ? actor.Root.position + forward.normalized * fallbackDistance
                : forward.normalized * fallbackDistance;
        }

        private GtexOriginalPlayerVisualProxy ResolvePassReceiver(GtexOriginalPlayerVisualProxy actor, string requestedReceiverId)
        {
            GtexOriginalPlayerVisualProxy receiver = null;
            if (!string.IsNullOrWhiteSpace(requestedReceiverId) &&
                !PlayerMap.TryGetCommandProxy(requestedReceiverId, out receiver, out var reason))
            {
                Debug.LogWarning("[GTEX VisualBridge] Pass receiver skipped: " + requestedReceiverId + " (" + reason + ").");
            }

            if (actor == null || actor.Player == null)
            {
                return receiver;
            }

            if (receiver != null &&
                receiver != actor &&
                receiver.Player != null &&
                receiver.Player.GameTeam == actor.Player.GameTeam)
            {
                return receiver;
            }

            return ResolveSaferPassReceiver(actor);
        }

        private GtexOriginalPlayerVisualProxy ResolveSaferPassReceiver(GtexOriginalPlayerVisualProxy actor)
        {
            if (actor == null || actor.Player == null || actor.Player.GameTeam == null)
            {
                return null;
            }

            var attackDirection = actor.Player.GoalDirection;
            attackDirection.y = 0f;
            if (attackDirection.sqrMagnitude <= 0.01f)
            {
                attackDirection = actor.Root.forward;
                attackDirection.y = 0f;
            }

            if (attackDirection.sqrMagnitude <= 0.01f)
            {
                attackDirection = Vector3.right;
            }

            var forward = attackDirection.normalized;
            var actorFieldProgress = actor.Player.PlayerFieldProgress;
            var candidates = PlayerMap.Proxies
                .Where(proxy =>
                    proxy != null &&
                    proxy != actor &&
                    proxy.Player != null &&
                    !proxy.IsGoalkeeper &&
                    proxy.Player.GameTeam == actor.Player.GameTeam)
                .ToArray();
            if (candidates.Length == 0)
            {
                return null;
            }

            var progressiveCandidates = candidates
                .Where(proxy => proxy.Player.PlayerFieldProgress + 0.05f >= actorFieldProgress)
                .ToArray();
            var pool = progressiveCandidates.Length > 0 ? progressiveCandidates : candidates;

            return pool
                .OrderByDescending(proxy =>
                {
                    var offset = proxy.Root.position - actor.Root.position;
                    offset.y = 0f;

                    var distance = offset.magnitude;
                    var directionScore = distance > 0.01f
                        ? Vector3.Dot(forward, offset / distance)
                        : 0f;

                    return directionScore * 8f +
                           proxy.Player.PlayerFieldProgress * 5f -
                           distance * 0.65f;
                })
                .FirstOrDefault();
        }

        private bool TryResolveCommandProxy(
            string playerUid,
            string role,
            GtexVisualCommandType commandType,
            out GtexOriginalPlayerVisualProxy proxy)
        {
            if (PlayerMap.TryGetCommandProxy(playerUid, out proxy, out var reason))
            {
                return true;
            }

            Debug.LogWarning("[GTEX VisualBridge] " + commandType + " skipped: invalid " + role + " PlayerUid '" + playerUid + "' (" + reason + ").");
            return false;
        }

        private Vector3 ResolvePassTarget(GtexOriginalPlayerVisualProxy actor, GtexOriginalPlayerVisualProxy receiver, GtexVisualCommand command)
        {
            var requestedTarget = command.targetWorldPosition != Vector3.zero
                ? ResolveTarget(actor, command.targetWorldPosition, 10f)
                : receiver != null
                    ? receiver.Root.position
                    : ResolveTarget(actor, command.targetWorldPosition, 10f);

            if (receiver == null || receiver.Player == null || actor == null || actor.Player == null)
            {
                return requestedTarget;
            }

            var feetTarget = ResolveReceiverFeetTarget(actor, receiver);
            if (command.passStyle == GtexVisualPassStyle.Ground)
            {
                return ClampToPitch(ResolveGroundPassFeetTarget(actor, receiver, feetTarget), 3.25f);
            }

            var predicted = PlayerBase.Predicter(actor.Player, receiver.Player);
            predicted.y = receiver.Root.position.y;
            var maxLeadDistance = command.passStyle == GtexVisualPassStyle.ThroughGround ? 3.2f : 0.75f;
            var predictedOffset = predicted - receiver.Root.position;
            predictedOffset.y = 0f;
            if (predictedOffset.sqrMagnitude > maxLeadDistance * maxLeadDistance)
            {
                predicted = receiver.Root.position + predictedOffset.normalized * maxLeadDistance;
                predicted.y = receiver.Root.position.y;
            }

            switch (command.passStyle)
            {
                case GtexVisualPassStyle.ThroughGround:
                {
                    var goalDirection = receiver.Player.GoalDirection;
                    goalDirection.y = 0f;
                    if (goalDirection.sqrMagnitude > 0.01f)
                    {
                        predicted += goalDirection.normalized * 1.35f;
                    }

                    var requestedOffset = requestedTarget - feetTarget;
                    requestedOffset.y = 0f;
                    if (requestedOffset.sqrMagnitude > 4.2f * 4.2f)
                    {
                        requestedTarget = feetTarget + requestedOffset.normalized * 4.2f;
                        requestedTarget.y = feetTarget.y;
                    }

                    return ClampToPitch(Vector3.Lerp(feetTarget, Vector3.Lerp(requestedTarget, predicted, 0.45f), 0.72f), 3.25f);
                }
                default:
                    return requestedTarget;
            }
        }

        private Vector3 ResolveReceiverFeetTarget(GtexOriginalPlayerVisualProxy actor, GtexOriginalPlayerVisualProxy receiver)
        {
            var target = receiver.Root.position;
            if (receiver.Player != null)
            {
                target.y = receiver.Player.Position.y;
            }

            return target;
        }

        private Vector3 ResolveGroundPassFeetTarget(
            GtexOriginalPlayerVisualProxy actor,
            GtexOriginalPlayerVisualProxy receiver,
            Vector3 feetTarget)
        {
            if (actor == null || receiver == null || receiver.Player == null)
            {
                return feetTarget;
            }

            var receiverVelocity = receiver.Player.Velocity;
            receiverVelocity.y = 0f;
            if (receiverVelocity.sqrMagnitude < 0.2f * 0.2f)
            {
                return feetTarget;
            }

            var forward = receiver.Player.GoalDirection;
            forward.y = 0f;
            if (forward.sqrMagnitude < 0.01f)
            {
                return feetTarget;
            }

            forward.Normalize();
            if (Vector3.Dot(receiverVelocity.normalized, forward) <= 0.35f)
            {
                return feetTarget;
            }

            var leadDistance = Mathf.Clamp(receiverVelocity.magnitude * 0.12f, 0f, 0.65f);
            return feetTarget + forward * leadDistance;
        }

        private static bool IsGroundPassTargetBehindPasser(GtexOriginalPlayerVisualProxy actor, Vector3 target)
        {
            if (actor == null || actor.Player == null)
            {
                return false;
            }

            var toTarget = target - actor.Root.position;
            toTarget.y = 0f;
            if (toTarget.magnitude < 7.5f)
            {
                return false;
            }

            var forward = actor.Player.GoalDirection;
            forward.y = 0f;
            if (forward.sqrMagnitude < 0.01f)
            {
                forward = actor.Player.PlayerController != null ? actor.Player.PlayerController.Forward : Vector3.forward;
                forward.y = 0f;
            }

            if (forward.sqrMagnitude < 0.01f)
            {
                return false;
            }

            return Vector3.Dot(toTarget.normalized, forward.normalized) < -0.35f;
        }

        private Vector3 ResolveSafeShotTarget(GtexOriginalPlayerVisualProxy actor, Vector3 requested, string outcome)
        {
            var manager = MatchManager.Current;
            if (manager != null && actor != null && actor.Player != null)
            {
                ResolveGoalsForActor(actor, out var ownGoal, out var opponentGoal);
                if (opponentGoal != null)
                {
                    var normalizedOutcome = (outcome ?? string.Empty).ToLowerInvariant();
                    if (normalizedOutcome.Contains("save"))
                    {
                        return ResolveKeeperInterceptionShotTarget(actor, opponentGoal);
                    }

                    var safeGoalTarget = opponentGoal.Position + Vector3.up * 1.2f;
                    var shooterSide = Mathf.Sign(actor.Root.position.z - opponentGoal.Position.z);
                    if (normalizedOutcome.Contains("goal"))
                    {
                        safeGoalTarget.z -= shooterSide * 2.2f;
                    }
                    else if (normalizedOutcome.Contains("save") || normalizedOutcome.Contains("on_target"))
                    {
                        safeGoalTarget.z -= shooterSide * 1.1f;
                    }

                    if (requested.sqrMagnitude <= 0.001f)
                    {
                        return safeGoalTarget;
                    }

                    var towardsGoal = opponentGoal.Position - actor.Root.position;
                    towardsGoal.y = 0f;
                    var towardsRequested = requested - actor.Root.position;
                    towardsRequested.y = 0f;
                    var pointsAwayFromGoal =
                        towardsGoal.sqrMagnitude > 0.01f &&
                        towardsRequested.sqrMagnitude > 0.01f &&
                        Vector3.Dot(towardsGoal.normalized, towardsRequested.normalized) < 0.25f;
                    var closerToOwnGoal =
                        ownGoal != null &&
                        Vector3.SqrMagnitude(requested - ownGoal.Position) < Vector3.SqrMagnitude(requested - opponentGoal.Position);
                    if (pointsAwayFromGoal || closerToOwnGoal)
                    {
                        return safeGoalTarget;
                    }

                    safeGoalTarget.z = Mathf.Lerp(safeGoalTarget.z, requested.z, 0.35f);
                    return safeGoalTarget;
                }
            }

            return ResolveTarget(actor, requested, 22f) + Vector3.up * 1.2f;
        }

        private void ResolveGoalsForActor(GtexOriginalPlayerVisualProxy actor, out GoalNet ownGoal, out GoalNet opponentGoal)
        {
            ownGoal = null;
            opponentGoal = null;

            var manager = MatchManager.Current;
            if (manager == null || actor == null)
            {
                return;
            }

            var reference = ResolveTeamDefensiveReference(actor);
            if (manager.goalNet1 != null && manager.goalNet2 != null && reference.sqrMagnitude > 0.001f)
            {
                var goal1Distance = Vector3.SqrMagnitude(reference - manager.goalNet1.Position);
                var goal2Distance = Vector3.SqrMagnitude(reference - manager.goalNet2.Position);
                ownGoal = goal1Distance <= goal2Distance ? manager.goalNet1 : manager.goalNet2;
                opponentGoal = ownGoal == manager.goalNet1 ? manager.goalNet2 : manager.goalNet1;
                return;
            }

            if (actor.Player != null && actor.Player.GameTeam == manager.GameTeam1)
            {
                ownGoal = manager.goalNet1;
                opponentGoal = manager.goalNet2;
                return;
            }

            ownGoal = manager.goalNet2;
            opponentGoal = manager.goalNet1;
        }

        private Vector3 ResolveTeamDefensiveReference(GtexOriginalPlayerVisualProxy actor)
        {
            if (actor == null || actor.Player == null || actor.Player.GameTeam == null)
            {
                return Vector3.zero;
            }

            var teamPlayers = PlayerMap.Proxies
                .Where(proxy => proxy != null && proxy.Player != null && proxy.Player.GameTeam == actor.Player.GameTeam)
                .ToArray();

            var keeper = teamPlayers.FirstOrDefault(proxy => proxy.IsGoalkeeper);
            if (keeper != null)
            {
                return keeper.Root.position;
            }

            if (teamPlayers.Length == 0)
            {
                return actor.Root.position;
            }

            var sum = Vector3.zero;
            foreach (var proxy in teamPlayers)
            {
                sum += proxy.Root.position;
            }

            return sum / teamPlayers.Length;
        }

        private Vector3 ResolveKeeperInterceptionShotTarget(GtexOriginalPlayerVisualProxy actor, GoalNet opponentGoal)
        {
            if (actor == null || opponentGoal == null)
            {
                return Vector3.zero;
            }

            var fromGoalToShooter = actor.Root.position - opponentGoal.Position;
            fromGoalToShooter.y = 0f;
            if (fromGoalToShooter.sqrMagnitude <= 0.001f)
            {
                fromGoalToShooter = -opponentGoal.Direction;
                fromGoalToShooter.y = 0f;
            }

            if (fromGoalToShooter.sqrMagnitude <= 0.001f)
            {
                fromGoalToShooter = Vector3.left;
            }

            fromGoalToShooter.Normalize();
            var shooterSide = Mathf.Sign(actor.Root.position.z - opponentGoal.Position.z);
            if (Mathf.Abs(shooterSide) < 0.01f)
            {
                shooterSide = 1f;
            }

            var baseTarget = opponentGoal.Position + fromGoalToShooter * 3.6f;
            var offsets = new[] { shooterSide * 2.2f, -shooterSide * 2.2f, shooterSide * 1.2f, -shooterSide * 1.2f };
            var start = actor.Root.position + Vector3.up * 0.45f;

            var bestTarget = baseTarget;
            var bestScore = float.MinValue;
            for (var index = 0; index < offsets.Length; index += 1)
            {
                var candidate = baseTarget;
                candidate.z = opponentGoal.Position.z + offsets[index];
                candidate.y = actor.Root.position.y + 0.95f;
                candidate = ClampToPitch(candidate);

                var blocked = IsOpponentBlockingShotLine(actor.GtexPlayerId, start, candidate, 0.75f);
                var score = blocked ? -100f : 20f;
                score += Mathf.Abs(offsets[index]) * 0.35f;
                score -= Vector3.Distance(actor.Root.position, candidate) * 0.02f;

                if (score > bestScore)
                {
                    bestScore = score;
                    bestTarget = candidate;
                }
            }

            return bestTarget;
        }

        private GtexOriginalPlayerVisualProxy ResolveOpposingKeeper(GtexOriginalPlayerVisualProxy actor)
        {
            var manager = MatchManager.Current;
            if (actor == null)
            {
                return PlayerMap.FindGoalkeeper(string.Empty);
            }

            var actorSide = GtexPlayerVisualMap.ResolveTeamSide(actor.GtexPlayerId);
            if (string.Equals(actorSide, "home", StringComparison.OrdinalIgnoreCase))
            {
                return PlayerMap.FindGoalkeeper("away");
            }

            if (string.Equals(actorSide, "away", StringComparison.OrdinalIgnoreCase))
            {
                return PlayerMap.FindGoalkeeper("home");
            }

            if (manager == null || actor.Player == null || actor.Player.GameTeam == null)
            {
                return PlayerMap.FindGoalkeeper(string.Empty);
            }

            var opposingSide = actor.Player.GameTeam == manager.GameTeam1 ? "away" : "home";
            return PlayerMap.FindGoalkeeper(opposingSide);
        }

        private Vector3 ResolveGoalCenter(int teamId, bool attacking)
        {
            var manager = MatchManager.Current;
            if (manager == null)
            {
                return Vector3.zero;
            }

            GoalNet goal = null;
            if (attacking)
            {
                goal = teamId == 0 ? manager.goalNet2 : manager.goalNet1;
            }
            else
            {
                goal = teamId == 0 ? manager.goalNet1 : manager.goalNet2;
            }

            if (goal != null)
            {
                return goal.Position;
            }

            var fieldX = manager.fieldEndX > 0f ? manager.fieldEndX : manager.SizeOfField.x;
            var fieldZ = manager.fieldEndY > 0f ? manager.fieldEndY : manager.SizeOfField.y;
            var x = attacking
                ? teamId == 0 ? fieldX : 0f
                : teamId == 0 ? 0f : fieldX;
            return new Vector3(x, 0f, fieldZ * 0.5f);
        }

        private bool IsOpponentBlockingShotLine(string shooterId, Vector3 start, Vector3 end, float threshold)
        {
            var shootingTeam = GetPlayerTeam(shooterId);
            if (shootingTeam < 0)
            {
                return false;
            }

            foreach (var proxy in PlayerMap.Proxies)
            {
                if (proxy == null || proxy.Player == null || proxy.IsGoalkeeper)
                {
                    continue;
                }

                if (GetPlayerTeam(proxy.GtexPlayerId) == shootingTeam)
                {
                    continue;
                }

                if (DistancePointToSegmentXZ(proxy.Root.position, start, end) <= threshold)
                {
                    return true;
                }
            }

            return false;
        }

        private static float DistancePointToSegmentXZ(Vector3 point, Vector3 start, Vector3 end)
        {
            var segment = new Vector2(end.x - start.x, end.z - start.z);
            var lengthSquared = segment.sqrMagnitude;
            if (lengthSquared <= 0.0001f)
            {
                return Vector2.Distance(new Vector2(point.x, point.z), new Vector2(start.x, start.z));
            }

            var pointOffset = new Vector2(point.x - start.x, point.z - start.z);
            var t = Mathf.Clamp01(Vector2.Dot(pointOffset, segment) / lengthSquared);
            var closest = new Vector2(start.x, start.z) + segment * t;
            return Vector2.Distance(new Vector2(point.x, point.z), closest);
        }

        private static float DistanceXZ(Vector3 a, Vector3 b)
        {
            a.y = 0f;
            b.y = 0f;
            return Vector3.Distance(a, b);
        }

        private static void PrepareForCommandAction(bool forcePlaying = true)
        {
            if (!forcePlaying)
            {
                return;
            }

            if (MatchManager.Current != null)
            {
                MatchManager.SetGlobalCommandDrivenVisualHold(true);
                MatchManager.Current.MatchFlags = MatchStatus.Playing;
            }
        }
    }
}
