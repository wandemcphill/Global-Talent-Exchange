const String gtexAccountSelectRoute = '/account/select';

const String gtexLegacyAuthRoutePrefix = '/auth';
const String gtexLegacyAccountSelectSegment = 'select-account';

String get gtexLegacyAccountSelectRoute =>
    '$gtexLegacyAuthRoutePrefix/$gtexLegacyAccountSelectSegment';
