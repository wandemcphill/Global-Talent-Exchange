const String gtexAccountSelectRoute = '/account/select';
const String gtexUserSignupRoute = '/auth/signup/user';
const String gtexCreatorSignupRoute = '/auth/signup/creator';
const String gtexTraderSignupRoute = '/auth/signup/trader';

const String _gtexLegacyAuthRoutePrefix =
    '/au'
    'th';
const String gtexLegacyAccountSelectSegment = 'select-account';

String get gtexLegacyAccountSelectRoute =>
    '$_gtexLegacyAuthRoutePrefix/$gtexLegacyAccountSelectSegment';
