using System;
using FStudio.GTEX.Core;
using Shared.Responses;

namespace FStudio.GTEX.Playback
{
    public sealed class GtexPlaybackApplier
    {
        private const float ClockRegressionToleranceMinutes = 0.10f;

        private readonly Func<bool> isSceneReady;
        private readonly Func<bool> needsBindingRefresh;
        private readonly Action bindPlayers;
        private readonly Action<float> drivePlayers;
        private readonly Action driveBall;
        private readonly Action<MatchResponse, bool> beforeApplyFrame;
        private readonly Action<MatchResponse> applySceneState;
        private readonly Action<MatchResponse, bool> applyCameraPreset;
        private readonly Action<MatchResponse, MatchResponse> updateBallIntent;
        private readonly Action<MatchResponse, MatchResponse, bool> tryStartSyntheticBallTransit;
        private readonly Action<MatchResponse, MatchResponse> tryTriggerBallAction;
        private readonly Action<MatchResponse, MatchResponse> tryTriggerEventAction;
        private readonly Action snapScene;

        public GtexPlaybackApplier(
            Func<bool> isSceneReady,
            Func<bool> needsBindingRefresh,
            Action bindPlayers,
            Action<float> drivePlayers,
            Action driveBall,
            Action<MatchResponse, bool> beforeApplyFrame,
            Action<MatchResponse> applySceneState,
            Action<MatchResponse, bool> applyCameraPreset,
            Action<MatchResponse, MatchResponse> updateBallIntent,
            Action<MatchResponse, MatchResponse, bool> tryStartSyntheticBallTransit,
            Action<MatchResponse, MatchResponse> tryTriggerBallAction,
            Action<MatchResponse, MatchResponse> tryTriggerEventAction,
            Action snapScene)
        {
            this.isSceneReady = isSceneReady;
            this.needsBindingRefresh = needsBindingRefresh;
            this.bindPlayers = bindPlayers;
            this.drivePlayers = drivePlayers;
            this.driveBall = driveBall;
            this.beforeApplyFrame = beforeApplyFrame;
            this.applySceneState = applySceneState;
            this.applyCameraPreset = applyCameraPreset;
            this.updateBallIntent = updateBallIntent;
            this.tryStartSyntheticBallTransit = tryStartSyntheticBallTransit;
            this.tryTriggerBallAction = tryTriggerBallAction;
            this.tryTriggerEventAction = tryTriggerEventAction;
            this.snapScene = snapScene;
        }

        public GtexMatchConfig Config { get; private set; }
        public MatchResponse CurrentState { get; private set; }
        public MatchResponse PreviousState { get; private set; }
        public bool IsSceneReady => isSceneReady == null || isSceneReady();

        public void Initialize(GtexMatchConfig config)
        {
            Config = config;
        }

        private bool IsAuthoritativeLivePlayback =>
            Config != null && Config.ResolveRuntimeMode() == GtexRuntimeMode.LivePlayback;

        public bool ApplyFrame(MatchResponse state, bool forceSnap = false)
        {
            if (state == null)
            {
                return false;
            }

            if (!forceSnap && CurrentState != null)
            {
                if (!string.IsNullOrWhiteSpace(state.frameId) &&
                    !string.IsNullOrWhiteSpace(CurrentState.frameId) &&
                    string.Equals(state.frameId, CurrentState.frameId, StringComparison.Ordinal))
                {
                    return false;
                }

                if (state.clockMinute + ClockRegressionToleranceMinutes < CurrentState.clockMinute)
                {
                    return false;
                }
            }

            PreviousState = CurrentState;
            CurrentState = state;

            beforeApplyFrame?.Invoke(state, forceSnap);
            applySceneState?.Invoke(state);

            if (needsBindingRefresh != null && needsBindingRefresh())
            {
                bindPlayers?.Invoke();
            }

            applyCameraPreset?.Invoke(state, forceSnap);

            // LivePlayback is a presentation of an already-decided GTEX match.
            // Never invent a second local intent or synthetic transit layer here.
            if (!IsAuthoritativeLivePlayback)
            {
                updateBallIntent?.Invoke(PreviousState, state);
                tryStartSyntheticBallTransit?.Invoke(PreviousState, state, forceSnap);
            }

            // Keep action/event presentation so pass, shot, save, goal, replay
            // and HUD reactions can still respond to authoritative events.
            tryTriggerBallAction?.Invoke(PreviousState, state);
            tryTriggerEventAction?.Invoke(PreviousState, state);

            if (forceSnap)
            {
                snapScene?.Invoke();
            }

            return true;
        }

        public void Tick(float deltaTime)
        {
            if (CurrentState == null || !IsSceneReady)
            {
                return;
            }

            if (needsBindingRefresh != null && needsBindingRefresh())
            {
                bindPlayers?.Invoke();
            }

            drivePlayers?.Invoke(deltaTime);
            driveBall?.Invoke();
        }

        public void Reset()
        {
            CurrentState = null;
            PreviousState = null;
        }
    }
}
