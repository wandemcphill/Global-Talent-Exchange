using System;

namespace FStudio.GTEX.Simulation
{
    public sealed class GtexSimEngine
    {
        private readonly GtexSimConfig config;

        public GtexSimEngine(GtexSimConfig config = null, Random random = null)
        {
            this.config = config ?? GtexSimConfig.CreateDefault();
            this.config.Validate();

            Clock = new GtexSimClock(
                this.config.FullMatchMinutes,
                this.config.HalfLengthMinutes,
                this.config.TargetRealDurationMinutes);
            EventSystem = new GtexSimEventSystem(this.config, random);
        }

        public event Action<GtexSimState> StateChanged;

        public GtexSimClock Clock { get; }

        public GtexSimEventSystem EventSystem { get; }

        public GtexSimState State { get; private set; } = GtexSimState.Kickoff;

        public bool IsRunning { get; private set; }

        public int HomeScore => EventSystem.HomeScore;

        public int AwayScore => EventSystem.AwayScore;

        public void StartMatch()
        {
            Clock.Reset();
            EventSystem.Reset();
            IsRunning = true;
            SetState(GtexSimState.Kickoff);
            config.Log("Match started.");
        }

        public void UpdateMatch(float deltaTimeSeconds)
        {
            if (!IsRunning)
            {
                return;
            }

            if (deltaTimeSeconds < 0f)
            {
                throw new ArgumentOutOfRangeException(nameof(deltaTimeSeconds), "Delta time must not be negative.");
            }

            if (State == GtexSimState.Kickoff)
            {
                SetState(GtexSimState.FirstHalf);
            }

            var previousMinute = Clock.CurrentMatchMinute;
            Clock.Advance(deltaTimeSeconds);
            var currentMinute = Clock.CurrentMatchMinute;

            ProcessSegments(previousMinute, currentMinute);

            if (Clock.IsComplete)
            {
                EndMatch();
            }
        }

        public void EndMatch()
        {
            if (State == GtexSimState.FullTime)
            {
                IsRunning = false;
                return;
            }

            IsRunning = false;
            SetState(GtexSimState.FullTime);
            config.Log("Full-time. Final score " + HomeScore + "-" + AwayScore + ".");
        }

        private void ProcessSegments(float startMinute, float endMinute)
        {
            if (endMinute <= startMinute)
            {
                return;
            }

            var halfTimeMinute = Clock.HalfLengthMinutes;

            if (startMinute < halfTimeMinute)
            {
                var firstHalfEnd = Math.Min(endMinute, halfTimeMinute);
                SetState(GtexSimState.FirstHalf);
                EventSystem.GenerateEvents(startMinute, firstHalfEnd, GtexSimState.FirstHalf);

                if (endMinute <= halfTimeMinute)
                {
                    return;
                }

                SetState(GtexSimState.HalfTime);
                config.Log("Half-time reached at match minute " + halfTimeMinute.ToString("0.0") + ".");

                SetState(GtexSimState.SecondHalf);
                EventSystem.GenerateEvents(halfTimeMinute, endMinute, GtexSimState.SecondHalf);
                return;
            }

            SetState(GtexSimState.SecondHalf);
            EventSystem.GenerateEvents(startMinute, endMinute, GtexSimState.SecondHalf);
        }

        private void SetState(GtexSimState nextState)
        {
            if (State == nextState)
            {
                return;
            }

            State = nextState;
            config.Log("State changed to " + nextState + ".");
            StateChanged?.Invoke(nextState);
        }
    }
}
