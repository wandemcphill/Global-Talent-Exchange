import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/gte_app_config.dart';
import '../../app/test_runtime_detector.dart';
import '../../data/admin_command_center_api.dart';
import '../../data/club_api.dart';
import '../../data/gte_authed_api.dart';
import '../../data/gte_api_repository.dart';
import '../../data/gte_exchange_api_client.dart';
import '../../data/national_team_api.dart';
import '../../features/match_redesign/data/gtex_match_api_repository.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../shared/models/auth_session.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/providers/live_clients_provider.dart';
import 'gtex_realtime_client.dart';
import 'gtex_runtime_models.dart';

void validateGtexStrictLiveStartup(GteAppConfig config) {
  if (isFlutterTestRuntime) return;
  final List<String> blockedReasons = <String>[];
  final String rawMode = config.rawBackendMode.trim().toLowerCase();
  final String baseUrl = config.apiBaseUrl.trim().toLowerCase();
  if (config.backendMode != GteBackendMode.live || config.activeShellBackendMode != GteBackendMode.live) {
    blockedReasons.add('fixture_backend_mode');
  }
  if (rawMode == 'fixture' || rawMode == 'livethenfixture') blockedReasons.add('forbidden_backend_mode:$rawMode');
  if (baseUrl.isEmpty || baseUrl.contains('fixture.invalid') || baseUrl.contains('mock.') || baseUrl.contains('demo.')) {
    blockedReasons.add('non_live_api_base_url');
  }
  const String demoCapabilities = String.fromEnvironment('GTE_ENABLE_DEMO_CAPABILITIES', defaultValue: 'false');
  if (_compileTimeBool(demoCapabilities)) blockedReasons.add('demo_capabilities_enabled');
  if (blockedReasons.isNotEmpty) throw StateError('GTEX strict-live startup gate blocked boot: ${blockedReasons.join(', ')}.');
}

void validateGtexRuntimeAdapterGraph(GtexRuntime runtime, {bool allowFlutterTestBypass = true}) {
  if (allowFlutterTestBypass && isFlutterTestRuntime) return;
  final List<String> blockedReasons = <String>[];
  final String baseUrl = runtime.apiBaseUrl.trim().toLowerCase();
  if (!runtime.readiness.strictLive || runtime.capabilities.fixtureMode) blockedReasons.add('fixture_runtime_capability_registered');
  if (baseUrl.isEmpty || baseUrl.contains('fixture.invalid') || baseUrl.contains('mock.') || baseUrl.contains('demo.')) blockedReasons.add('non_live_api_base_url');
  if (runtime.websocket == null) blockedReasons.add('missing_live_realtime_client');
  if (runtime.repositories.matches is GtexUnavailableMatchRepository || _runtimeTypeLooksSynthetic(runtime.repositories.matches)) blockedReasons.add('synthetic_match_repository_registered');
  if (runtime.repositories.clubs.config.mode != GteBackendMode.live || runtime.repositories.clubs.hasRegisteredFixtures) blockedReasons.add('synthetic_club_repository_registered');
  final GteExchangeApiClient exchangeApi = runtime.controllers.exchange.api;
  if (exchangeApi.config.mode != GteBackendMode.live || _exchangeRegistersFixtureRepository(exchangeApi)) blockedReasons.add('synthetic_exchange_repository_registered');
  if (runtime.repositories.competitions.config.mode != GteBackendMode.live || runtime.repositories.competitions.hasRegisteredFixtures) blockedReasons.add('synthetic_competition_repository_registered');
  if (runtime.repositories.nationalTeams.client.mode != GteBackendMode.live || runtime.repositories.nationalTeams.hasRegisteredFixtures) blockedReasons.add('synthetic_national_repository_registered');
  final AdminCommandCenterApi? admin = runtime.controllers.admin;
  if (admin != null && admin.client.mode != GteBackendMode.live) blockedReasons.add('synthetic_admin_repository_registered');
  if (!runtime.capabilities.paystack) blockedReasons.add('paystack_disabled_in_strict_live');
  if (blockedReasons.isNotEmpty) throw StateError('GTEX strict-live runtime graph blocked boot: ${blockedReasons.join(', ')}.');
}

final Provider<GtexRuntime> gtexRuntimeProvider = Provider<GtexRuntime>((Ref ref) {
  final GteAppConfig config = ref.watch(appConfigProvider);
  validateGtexStrictLiveStartup(config);
  final String? accessToken = ref.watch(accessTokenProvider);
  final GteAuthedApi authedApi = ref.watch(authedApiProvider);
  final bool fixtureMode = config.activeShellBackendMode == GteBackendMode.fixture;
  final GtexRealtimeClient? realtime = fixtureMode ? null : GtexRealtimeClient(
    apiBaseUrl: config.apiBaseUrl,
    accessTokenProvider: () => ref.read(accessTokenProvider),
    authRefresh: () async {
      try { await authedApi.getMap('/api/session/bootstrap'); } catch (_) { return null; }
      return ref.read(accessTokenProvider);
    },
  );
  final GteExchangeApiClient exchangeApi = ref.watch(exchangeApiClientProvider);
  final GteExchangeController exchangeController = GteExchangeController(api: exchangeApi);
  final AuthSession? session = ref.watch(authProvider);
  final bool isAdmin = session?.isAdmin ?? false;
  final GtexRuntime runtime = GtexRuntime(
    env: _runtimeEnv(),
    apiBaseUrl: config.apiBaseUrl,
    accessToken: accessToken,
    websocket: realtime,
    repositories: GtexRuntimeRepositories(
      matches: fixtureMode ? const GtexUnavailableMatchRepository() : ApiBackedMatchRepository(client: authedApi, realtimeEvents: realtime?.subscribeMatch),
      clubs: ClubApi.standard(baseUrl: config.apiBaseUrl, accessToken: accessToken, mode: config.activeShellBackendMode),
      competitions: ref.watch(competitionApiProvider),
      nationalTeams: NationalTeamApi.standard(baseUrl: config.apiBaseUrl, accessToken: accessToken, mode: config.activeShellBackendMode),
    ),
    controllers: GtexRuntimeControllers(
      exchange: exchangeController,
      admin: isAdmin && accessToken != null && accessToken.trim().isNotEmpty ? AdminCommandCenterApi.standard(baseUrl: config.apiBaseUrl, accessToken: accessToken, mode: config.activeShellBackendMode, client: authedApi) : null,
    ),
    capabilities: GtexRuntimeCapabilities(
      korapay: !fixtureMode,
      manualPayment: !fixtureMode,
      paystack: !fixtureMode,
      fixtureMode: fixtureMode,
    ),
    readiness: GtexRuntimeReadiness(
      strictLive: !fixtureMode,
      blockedReasons: <String>[if (fixtureMode) 'fixture_runtime_enabled_for_test_only', if (config.apiBaseUrl.trim().isEmpty) 'missing_api_base_url'],
    ),
    observability: GtexRuntimeObservability(
      liveEndpointProvenance: const <String, String>{'session': '/api/session/bootstrap', 'match_v2': '/api/matches/{match_id}/state', 'national_v2': '/api/national-team-engine/competitions', 'admin_v2': '/api/admin/operations-readiness'},
      websocketSourceTrace: const <String, String>{'matches': '/ws/matches/{match_id}', 'notifications': '/realtime/stream'},
      sourceOfTruthTag: 'persisted_backend_authority',
      stalePayloadThreshold: const Duration(seconds: 45),
      healthOverlayEnabled: _compileTimeBool(const String.fromEnvironment('GTE_RUNTIME_HEALTH_OVERLAY', defaultValue: 'false')),
    ),
    session: session,
  );
  validateGtexRuntimeAdapterGraph(runtime);
  return runtime;
});

bool _exchangeRegistersFixtureRepository(GteExchangeApiClient exchangeApi) {
  final GteApiRepository repository = exchangeApi.repository;
  if (repository is! GteModeAwareApiRepository) return _runtimeTypeLooksSynthetic(repository);
  return repository.fixtures is! GteFixtureRepositoryUnavailable;
}

bool _runtimeTypeLooksSynthetic(Object value) {
  final String type = value.runtimeType.toString().toLowerCase();
  return type.contains('mock') || type.contains('demo') || type.contains('fixture');
}

bool _compileTimeBool(String value) => const <String>{'1', 'true', 'yes', 'on'}.contains(value.trim().toLowerCase());

GtexRuntimeEnv _runtimeEnv() {
  const String rawEnv = String.fromEnvironment('GTE_RUNTIME_ENV', defaultValue: 'production');
  switch (rawEnv.trim().toLowerCase()) {
    case 'development':
    case 'dev': return GtexRuntimeEnv.development;
    case 'staging': return GtexRuntimeEnv.staging;
    default: return GtexRuntimeEnv.production;
  }
}
