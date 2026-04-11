namespace FStudio.GTEX.Core
{
    public enum GtexMode
    {
        Development,
        Production
    }

    public static class GtexConfig
    {
        public const string DevelopmentDefineSymbols = "GTEX_DEV;GTEX_FAST_MODE";
        public const string ProductionDefineSymbols = "GTEX_PROD";
        public const int DevelopmentQualityIndex = 0;
        public const int ProductionQualityIndex = 1;

#if GTEX_DEV
        public static readonly GtexMode Mode = GtexMode.Development;
#else
        public static readonly GtexMode Mode = GtexMode.Production;
#endif

        public static bool IsDev => Mode == GtexMode.Development;

        public static bool IsProd => Mode == GtexMode.Production;

#if GTEX_FAST_MODE
        public const bool IsFastMode = true;
#else
        public const bool IsFastMode = false;
#endif
    }
}
