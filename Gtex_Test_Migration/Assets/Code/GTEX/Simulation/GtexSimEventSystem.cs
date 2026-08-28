using System;
using System.Collections.Generic;

namespace FStudio.GTEX.Simulation
{
    public sealed class GtexSimEventSystem
    {
        private const float MinimumEventSeparationMinutes = 1.1f;
        private readonly GtexSimConfig config;
        private readonly List<GtexSimEvent> history = new List<GtexSimEvent>();
        private readonly Random random;
        private int nextWindowIndex;
        private float lastEventMinute = -999f;

        public GtexSimEventSystem(GtexSimConfig config, Random random = null)
        {
            this.config = config ?? throw new ArgumentNullException(nameof(config));
            this.config.Validate();
            this.random = random ?? new Random(this.config.RandomSeed);
        }

        public event Action<GtexSimEvent> EventGenerated;

        public IReadOnlyList<GtexSimEvent> History => history;

        public int HomeScore { get; private set; }

        public int AwayScore { get; private set; }

        public void Reset()
        {
            history.Clear();
            HomeScore = 0;
            AwayScore = 0;
            nextWindowIndex = 0;
            lastEventMinute = -999f;
            config.Log("Event system reset.");
        }

        public void GenerateEvents(float startMinute, float endMinute, GtexSimState state)
        {
            if (!IsLiveState(state) || endMinute <= startMinute)
            {
                return;
            }

            var windowSize = config.EventCheckWindowMinutes;
            while (((nextWindowIndex + 1) * windowSize) <= endMinute)
            {
                var windowStart = nextWindowIndex * windowSize;
                var windowEnd = windowStart + windowSize;
                nextWindowIndex += 1;

                if (windowEnd <= startMinute)
                {
                    continue;
                }

                TryGenerateWindowEvent(windowStart, windowEnd);
            }
        }

        private void TryGenerateWindowEvent(float windowStart, float windowEnd)
        {
            var intensity = 1d + (windowStart / config.FullMatchMinutes) * 0.25d;
            var eventChance = Clamp(config.BaseEventChancePerWindow * intensity, 0d, 0.82d);
            if (random.NextDouble() > eventChance)
            {
                return;
            }

            var eventTime = Lerp(windowStart, windowEnd, random.NextDouble());
            if (eventTime - lastEventMinute < MinimumEventSeparationMinutes)
            {
                return;
            }

            var team = random.NextDouble() >= 0.5d
                ? GtexSimTeamSide.Home
                : GtexSimTeamSide.Away;
            var eventRoll = random.NextDouble();

            if (eventRoll < 0.20d)
            {
                EmitGoal(eventTime, team);
                return;
            }

            if (eventRoll < 0.65d)
            {
                Emit(new GtexMissedChanceEvent(eventTime, team, (float)Lerp(0.45d, 0.98d, random.NextDouble())));
                return;
            }

            if (eventRoll < 0.90d)
            {
                Emit(new GtexFoulEvent(eventTime, team, (float)Lerp(0.25d, 1d, random.NextDouble())));
                return;
            }

            Emit(new GtexCardEvent(
                eventTime,
                team,
                random.NextDouble() < 0.84d ? GtexSimCardType.Yellow : GtexSimCardType.Red));
        }

        private void EmitGoal(float eventTime, GtexSimTeamSide team)
        {
            if (team == GtexSimTeamSide.Home)
            {
                HomeScore += 1;
            }
            else
            {
                AwayScore += 1;
            }

            Emit(new GtexGoalEvent(eventTime, team, HomeScore, AwayScore));
        }

        private void Emit(GtexSimEvent matchEvent)
        {
            lastEventMinute = matchEvent != null ? matchEvent.Minute : lastEventMinute;
            history.Add(matchEvent);
            config.Log("Generated event: " + matchEvent);
            EventGenerated?.Invoke(matchEvent);
        }

        private static bool IsLiveState(GtexSimState state)
        {
            return state == GtexSimState.FirstHalf || state == GtexSimState.SecondHalf;
        }

        private static double Clamp(double value, double minimum, double maximum)
        {
            return Math.Max(minimum, Math.Min(maximum, value));
        }

        private static float Lerp(float start, float end, double t)
        {
            return (float)(start + ((end - start) * Clamp(t, 0d, 1d)));
        }

        private static double Lerp(double start, double end, double t)
        {
            return start + ((end - start) * Clamp(t, 0d, 1d));
        }
    }
}
