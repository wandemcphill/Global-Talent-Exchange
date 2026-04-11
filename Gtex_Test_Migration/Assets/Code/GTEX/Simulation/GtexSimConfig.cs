using System;

namespace FStudio.GTEX.Simulation
{
    public sealed class GtexSimConfig
    {
        public const float DefaultFullMatchMinutes = 90f;
        public const float DefaultHalfLengthMinutes = 45f;
        public const float DefaultTargetRealDurationMinutes = 15f;
        public const float DefaultEventCheckWindowMinutes = 1f;
        public const double DefaultEventChancePerWindow = 0.42d;
        public const int DefaultRandomSeed = 1337;

        public float FullMatchMinutes { get; set; } = DefaultFullMatchMinutes;

        public float HalfLengthMinutes { get; set; } = DefaultHalfLengthMinutes;

        public float TargetRealDurationMinutes { get; set; } = DefaultTargetRealDurationMinutes;

        public float EventCheckWindowMinutes { get; set; } = DefaultEventCheckWindowMinutes;

        public double BaseEventChancePerWindow { get; set; } = DefaultEventChancePerWindow;

        public int RandomSeed { get; set; } = DefaultRandomSeed;

        public Action<string> Logger { get; set; } = delegate { };

        public static GtexSimConfig CreateDefault()
        {
            return new GtexSimConfig();
        }

        public void Validate()
        {
            if (FullMatchMinutes <= 0f)
            {
                throw new InvalidOperationException("FullMatchMinutes must be greater than zero.");
            }

            if (HalfLengthMinutes <= 0f || HalfLengthMinutes >= FullMatchMinutes)
            {
                throw new InvalidOperationException("HalfLengthMinutes must be greater than zero and lower than FullMatchMinutes.");
            }

            if (TargetRealDurationMinutes <= 0f)
            {
                throw new InvalidOperationException("TargetRealDurationMinutes must be greater than zero.");
            }

            if (EventCheckWindowMinutes <= 0f)
            {
                throw new InvalidOperationException("EventCheckWindowMinutes must be greater than zero.");
            }

            if (BaseEventChancePerWindow < 0d || BaseEventChancePerWindow > 1d)
            {
                throw new InvalidOperationException("BaseEventChancePerWindow must stay between 0 and 1.");
            }
        }

        internal void Log(string message)
        {
            Logger?.Invoke("[GTEX Sim] " + message);
        }
    }
}
