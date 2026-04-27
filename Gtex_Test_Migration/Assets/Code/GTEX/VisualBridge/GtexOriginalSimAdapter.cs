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

        [SerializeField] private Transform originalMatchRoot;
        [SerializeField] private Camera originalCamera;
        [SerializeField] private GtexPlayerVisualMap playerMap;
        [SerializeField] private GtexOriginalPitchVisualFallback pitchVisualFallback;
        [SerializeField] private GtexOriginalActionCameraDriver actionCameraDriver;
        [SerializeField] private GtexOriginalFallbackFollowCamera fallbackFollowCamera;
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

        private void LateUpdate()
        {
            if (!GtexOriginalVisualRuntimePolicy.IsOriginalVisualRuntime())
            {
                return;
            }

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
            if (!PlayerMap.TryGetProxy(playerId, out var player))
            {
                return;
            }

            PrepareForCommandAction();
            player.GiveBall();
            UpdateCameraBallOwner(playerId);
            ClearCameraPassTarget();
            FocusToBall();
            Debug.Log("[GTEX VisualBridge] Possession -> " + playerId);
        }

        public void ExecuteCarry(string actorId, Vector3 targetPoint)
        {
            if (!PlayerMap.TryGetProxy(actorId, out var actor))
            {
                return;
            }

            PrepareForCommandAction();
            actor.DribbleToward(ResolveTarget(actor, targetPoint, 6f));
            UpdateCameraBallOwner(actorId);
            ClearCameraPassTarget();
            FocusToBall();
        }

        public void ExecuteSupportRun(GtexVisualCommand command)
        {
            if (command == null)
            {
                return;
            }

            var actor = PlayerMap.ResolveProxy(command.actorPlayerId);
            if (actor == null)
            {
                return;
            }

            PrepareForCommandAction();
            actor.MoveToSupportPoint(ClampToPitch(command.targetWorldPosition), command.urgency, command.duration);
            FocusToBall();
            Debug.Log("[GTEX VisualBridge] SupportRun -> " + command.actorPlayerId + " to " + command.targetWorldPosition);
        }

        public void ExecuteMarkPlayer(GtexVisualCommand command)
        {
            if (command == null)
            {
                return;
            }

            var defender = PlayerMap.ResolveProxy(command.actorPlayerId);
            var target = PlayerMap.ResolveProxy(command.targetPlayerId);
            if (defender == null || target == null)
            {
                return;
            }

            PrepareForCommandAction();
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

            var defender = PlayerMap.ResolveProxy(command.actorPlayerId);
            var carrier = PlayerMap.ResolveProxy(command.targetPlayerId);
            if (defender == null || carrier == null)
            {
                return;
            }

            PrepareForCommandAction();
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

            var actor = PlayerMap.ResolveProxy(command.actorPlayerId);
            if (actor == null)
            {
                return;
            }

            PrepareForCommandAction();
            var targetPoint = command.targetWorldPosition.sqrMagnitude > 0.001f
                ? ClampToPitch(command.targetWorldPosition)
                : actor.Root.position;
            actor.HoldShape(targetPoint, command.duration);
        }

        public void ExecuteCoverSpace(GtexVisualCommand command)
        {
            if (command == null)
            {
                return;
            }

            var actor = PlayerMap.ResolveProxy(command.actorPlayerId);
            if (actor == null)
            {
                return;
            }

            PrepareForCommandAction();
            actor.CoverSpace(ClampToPitch(command.targetWorldPosition), command.urgency, command.duration);
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

            var actor = PlayerMap.ResolveProxy(command.actorPlayerId);
            var receiver = PlayerMap.ResolveProxy(command.targetPlayerId);
            if (actor == null)
            {
                Debug.LogWarning("[GTEX VisualBridge] Pass failed: actor=" + command.actorPlayerId + ", target=" + command.targetPlayerId);
                return;
            }

            PrepareForCommandAction();
            UpdateCameraBallOwner(command.actorPlayerId);

            var groundTarget = command.targetWorldPosition != Vector3.zero
                ? ResolveTarget(actor, command.targetWorldPosition, 10f)
                : receiver != null
                    ? receiver.Root.position
                    : ResolveTarget(actor, command.targetWorldPosition, 10f);

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

                    actor.GroundPassToPoint(groundTarget);
                    break;
                case GtexVisualPassStyle.Ground:
                default:
                    if (receiver != null)
                    {
                        UpdateCameraPassTarget(command.targetPlayerId);
                    }
                    else
                    {
                        UpdateCameraWorldPassTarget(groundTarget, "ground");
                    }

                    if (receiver != null)
                    {
                        actor.GroundPassTo(receiver);
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
                ", target=" + command.targetPlayerId);
        }

        public void ExecuteShot(string actorId, Vector3 targetPoint, string outcome)
        {
            if (!PlayerMap.TryGetProxy(actorId, out var actor))
            {
                return;
            }

            PrepareForCommandAction();
            var shotTarget = ResolveShotTarget(actor, targetPoint);
            var cameraShotTarget = Vector3.Lerp(actor.Root.position, shotTarget, 0.58f);
            cameraShotTarget.y = actor.Root.position.y;
            UpdateCameraBallOwner(actorId);
            UpdateCameraWorldPassTarget(cameraShotTarget, "shot");
            actor.ShootAt(shotTarget, outcome);
            QueuePassTargetClear(null, 0.8f);
            FocusToBall();
            Debug.Log("[GTEX VisualBridge] Shot -> actor=" + actorId + ", outcome=" + outcome + ", target=" + shotTarget);

            if (!string.IsNullOrWhiteSpace(outcome) &&
                outcome.ToLowerInvariant().Contains("save"))
            {
                var keeper = PlayerMap.FindGoalkeeper(string.Empty);
                keeper?.KeeperReactToShot(targetPoint);
            }
        }

        public void ExecuteKeeperSave(string keeperId, Vector3 shotTarget)
        {
            if (!PlayerMap.TryGetProxy(keeperId, out var keeper))
            {
                keeper = PlayerMap.FindGoalkeeper(string.Empty);
            }

            PrepareForCommandAction();
            UpdateCameraBallOwner(keeperId);
            ClearCameraPassTarget();
            keeper?.KeeperReactToShot(shotTarget);
            FocusToBall();
        }

        public void ExecuteKeeperClaim(string keeperId)
        {
            if (!PlayerMap.TryGetProxy(keeperId, out var keeper))
            {
                keeper = PlayerMap.FindGoalkeeper(string.Empty);
            }

            PrepareForCommandAction();
            UpdateCameraBallOwner(keeperId);
            ClearCameraPassTarget();
            keeper?.KeeperClaim();
            FocusToBall();
        }

        public void PlayGoal(string teamId, string scorerId)
        {
            if (PlayerMap.TryGetProxy(scorerId, out var scorer))
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

            MatchManager.SetGlobalCommandDrivenVisualHold(true);
            manager.SetExternalPlayback(false);
            manager.MatchFlags = MatchStatus.WaitingForKickOff;

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
                MatchManager.SetGlobalCommandDrivenVisualHold(true);
                MatchManager.Current.MatchFlags = MatchStatus.Playing;
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
            ResetKickoff();
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
            return ClampToPitch(point);
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

        public Vector3 ClampToPitch(Vector3 point)
        {
            var manager = MatchManager.Current;
            if (manager == null)
            {
                return point;
            }

            var maxX = manager.fieldEndX > 0f ? manager.fieldEndX : manager.SizeOfField.x;
            var maxZ = manager.fieldEndY > 0f ? manager.fieldEndY : manager.SizeOfField.y;
            point.x = Mathf.Clamp(point.x, 0.5f, Mathf.Max(0.5f, maxX - 0.5f));
            point.z = Mathf.Clamp(point.z, 0.5f, Mathf.Max(0.5f, maxZ - 0.5f));
            return point;
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
            var camera = ResolveActiveCamera();
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

            if (actionCameraDriver == null || actionCameraDriver.gameObject != camera.gameObject)
            {
                actionCameraDriver = camera.gameObject.GetComponent<GtexOriginalActionCameraDriver>();
                if (actionCameraDriver == null)
                {
                    actionCameraDriver = camera.gameObject.AddComponent<GtexOriginalActionCameraDriver>();
                }
            }

            originalCamera = camera;
            DisableFallbackFollowCamera();
            usingFallbackCamera = false;

            var ballTransform = ResolveOriginalBallTransform();
            var playerTransforms = ResolveAllPlayerTransforms();
            var goalkeeperTransforms = ResolveGoalkeeperTransforms();
            actionCameraDriver.Bind(
                camera,
                ballTransform,
                playerTransforms,
                ResolveOriginalBallTransform,
                ResolveCurrentAttackingGoal,
                goalkeeperTransforms);

            if (Ball.Current != null && Ball.Current.HolderPlayer != null &&
                PlayerMap.TryGetProxy(Ball.Current.HolderPlayer, out var holderProxy))
            {
                UpdateCameraBallOwner(holderProxy.GtexPlayerId);
            }

            gameplayCameraReady = actionCameraDriver.HasBoundCamera && actionCameraDriver.HasValidFocus;
            var baseMode = CameraSystem.Current != null && !string.IsNullOrWhiteSpace(CameraSystem.Current.CurrentCameraType)
                ? CameraSystem.Current.CurrentCameraType
                : camera.name;
            activeCameraMode = baseMode + "+" + actionCameraDriver.ModeName;

            var bindingKey = camera.GetInstanceID() + ":" +
                             (ballTransform != null ? ballTransform.GetInstanceID() : 0) + ":" +
                             playerTransforms.Count;
            if (!string.Equals(lastActionCameraBindingKey, bindingKey))
            {
                lastActionCameraBindingKey = bindingKey;
                Debug.Log(
                    "[GTEX VisualBridge] Action camera follow enabled. " +
                    "camera=" + camera.name +
                    ", ball=" + (ballTransform != null) +
                    ", players=" + playerTransforms.Count);
            }

            var ballBound = ballTransform != null;
            if (!lastCameraBallBoundState.HasValue || lastCameraBallBoundState.Value != ballBound)
            {
                lastCameraBallBoundState = ballBound;
                Debug.Log("[GTEX VisualBridge] Camera ball bound: " + ballBound);
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

        private void UpdateCameraBallOwner(string playerId)
        {
            currentBallOwnerId = playerId ?? string.Empty;
            if (actionCameraDriver == null)
            {
                return;
            }

            if (string.IsNullOrWhiteSpace(playerId))
            {
                actionCameraDriver.SetBallOwner(null, string.Empty);
                return;
            }

            var proxy = PlayerMap.ResolveProxy(playerId);
            if (proxy != null)
            {
                actionCameraDriver.SetBallOwner(proxy.Root, proxy.GtexPlayerId);
            }
        }

        private void UpdateCameraPassTarget(string targetPlayerId)
        {
            if (actionCameraDriver == null)
            {
                return;
            }

            var target = PlayerMap.ResolveProxy(targetPlayerId);
            if (target != null)
            {
                currentCameraPassTargetId = target.GtexPlayerId;
                actionCameraDriver.SetPassTarget(target.Root, target.GtexPlayerId);
            }
            else
            {
                ClearCameraPassTarget();
            }
        }

        private void UpdateCameraWorldPassTarget(Vector3 targetPoint, string targetId)
        {
            if (actionCameraDriver == null)
            {
                return;
            }

            currentCameraPassTargetId = targetId ?? string.Empty;
            actionCameraDriver.SetWorldPassTarget(targetPoint, currentCameraPassTargetId);
        }

        private void ClearCameraPassTarget()
        {
            currentCameraPassTargetId = string.Empty;
            if (actionCameraDriver != null)
            {
                actionCameraDriver.ClearPassTarget();
            }
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

            if (actionCameraDriver != null)
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

        private Camera ResolveActiveCamera()
        {
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

        private static Vector3 ResolveShotTarget(GtexOriginalPlayerVisualProxy actor, Vector3 requested)
        {
            if (requested.sqrMagnitude > 0.001f)
            {
                return requested;
            }

            var manager = MatchManager.Current;
            if (manager != null && actor != null && actor.Player != null)
            {
                var opponentGoal = actor.Player.GameTeam == manager.GameTeam1
                    ? manager.goalNet2
                    : manager.goalNet1;
                if (opponentGoal != null)
                {
                    return opponentGoal.Position + Vector3.up * 1.2f;
                }
            }

            return ResolveTarget(actor, requested, 22f) + Vector3.up * 1.2f;
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

        private static void PrepareForCommandAction()
        {
            MatchManager.SetGlobalCommandDrivenVisualHold(true);

            if (MatchManager.Current != null)
            {
                MatchManager.Current.MatchFlags = MatchStatus.Playing;
            }
        }
    }
}
