namespace FStudio.GTEX
{
    public static class GtexRuntimeTelemetry
    {
        public static int DeadBindingBlocks { get; private set; }

        public static int ScoreAuthorityUpdates { get; private set; }

        public static int LegacyScoreWritesBlocked { get; private set; }

        public static int KinematicVelocityWritesBlocked { get; private set; }

        public static int CameraFocusClamps { get; private set; }

        public static void Reset()
        {
            DeadBindingBlocks = 0;
            ScoreAuthorityUpdates = 0;
            LegacyScoreWritesBlocked = 0;
            KinematicVelocityWritesBlocked = 0;
            CameraFocusClamps = 0;
        }

        public static void RegisterDeadBindingBlock()
        {
            DeadBindingBlocks += 1;
        }

        public static void RegisterScoreAuthorityUpdate()
        {
            ScoreAuthorityUpdates += 1;
        }

        public static void RegisterLegacyScoreWriteBlocked()
        {
            LegacyScoreWritesBlocked += 1;
        }

        public static void RegisterKinematicVelocityWriteBlocked()
        {
            KinematicVelocityWritesBlocked += 1;
        }

        public static void RegisterCameraFocusClamp()
        {
            CameraFocusClamps += 1;
        }
    }
}
