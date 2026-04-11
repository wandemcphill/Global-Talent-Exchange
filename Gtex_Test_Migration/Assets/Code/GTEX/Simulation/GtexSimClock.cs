using System;

namespace FStudio.GTEX.Simulation
{
    public sealed class GtexSimClock
    {
        private readonly float fullMatchMinutes;
        private readonly float halfLengthMinutes;
        private readonly float targetRealDurationSeconds;

        public GtexSimClock(float fullMatchMinutes, float halfLengthMinutes, float targetRealDurationMinutes)
        {
            if (fullMatchMinutes <= 0f)
            {
                throw new ArgumentOutOfRangeException(nameof(fullMatchMinutes), "Full match minutes must be greater than zero.");
            }

            if (halfLengthMinutes <= 0f || halfLengthMinutes >= fullMatchMinutes)
            {
                throw new ArgumentOutOfRangeException(nameof(halfLengthMinutes), "Half length must be greater than zero and lower than full match length.");
            }

            if (targetRealDurationMinutes <= 0f)
            {
                throw new ArgumentOutOfRangeException(nameof(targetRealDurationMinutes), "Target real duration must be greater than zero.");
            }

            this.fullMatchMinutes = fullMatchMinutes;
            this.halfLengthMinutes = halfLengthMinutes;
            targetRealDurationSeconds = targetRealDurationMinutes * 60f;
        }

        public float CurrentMatchMinute { get; private set; }

        public float ElapsedRealSeconds { get; private set; }

        public float FullMatchMinutes => fullMatchMinutes;

        public float HalfLengthMinutes => halfLengthMinutes;

        public float TargetRealDurationSeconds => targetRealDurationSeconds;

        public float MatchMinutesPerSecond => fullMatchMinutes / targetRealDurationSeconds;

        public float NormalizedProgress => fullMatchMinutes <= 0f ? 1f : CurrentMatchMinute / fullMatchMinutes;

        public bool IsComplete => CurrentMatchMinute >= fullMatchMinutes;

        public void Reset()
        {
            CurrentMatchMinute = 0f;
            ElapsedRealSeconds = 0f;
        }

        public float Advance(float deltaTimeSeconds)
        {
            if (deltaTimeSeconds < 0f)
            {
                throw new ArgumentOutOfRangeException(nameof(deltaTimeSeconds), "Delta time must not be negative.");
            }

            if (deltaTimeSeconds == 0f || IsComplete)
            {
                return 0f;
            }

            var previousMatchMinute = CurrentMatchMinute;
            ElapsedRealSeconds += deltaTimeSeconds;
            CurrentMatchMinute = Math.Min(fullMatchMinutes, ElapsedRealSeconds * MatchMinutesPerSecond);
            return CurrentMatchMinute - previousMatchMinute;
        }
    }
}
