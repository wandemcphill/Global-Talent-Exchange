namespace FStudio.GTEX.Engine
{
    public interface IGtexClockSource
    {
        float CurrentMatchMinute { get; }

        GtexMatchPhase Phase { get; }

        bool IsRunning { get; }
    }
}
