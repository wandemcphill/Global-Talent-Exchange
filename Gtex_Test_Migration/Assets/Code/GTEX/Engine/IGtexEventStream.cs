using System;

namespace FStudio.GTEX.Engine
{
    public interface IGtexEventStream
    {
        event Action<GtexMatchEvent> EventPublished;

        void Publish(GtexMatchEvent matchEvent);
    }
}
