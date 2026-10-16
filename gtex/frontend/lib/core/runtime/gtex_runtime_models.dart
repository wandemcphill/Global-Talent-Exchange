import '../../data/admin_command_center_api.dart';
import '../../data/club_api.dart';
import '../../data/competition_api.dart';
import '../../data/national_team_api.dart';
import '../../features/match_redesign/data/gtex_match_repository.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../shared/models/auth_session.dart';
import 'gtex_realtime_client.dart';

enum GtexRuntimeEnv { development, staging, production }

class GtexRuntimeReadiness {
  const GtexRuntimeReadiness({
    required this.strictLive,
    required this.blockedReasons,
  });

  final bool strictLive;
  final List<String> blockedReasons;

  bool get ready => blockedReasons.isEmpty;
}

class GtexRuntimeCapabilities {
  const GtexRuntimeCapabilities({
    required this.korapay,
    required this.manualPayment,
    required this.paystack,
    required this.fixtureMode,
  });

  final bool korapay;
  final bool manualPayment;
  final bool paystack;
  final bool fixtureMode;
}

class GtexRuntimeObservability {
  const GtexRuntimeObservability({
    required this.liveEndpointProvenance,
    required this.websocketSourceTrace,
    required this.sourceOfTruthTag,
    required this.stalePayloadThreshold,
    required this.healthOverlayEnabled,
  });

  final Map<String, String> liveEndpointProvenance;
  final Map<String, String> websocketSourceTrace;
  final String sourceOfTruthTag;
  final Duration stalePayloadThreshold;
  final bool healthOverlayEnabled;
}

class GtexRuntimeRepositories {
  const GtexRuntimeRepositories({
    required this.matches,
    required this.clubs,
    required this.competitions,
    required this.nationalTeams,
  });

  final GtexMatchRepository matches;
  final ClubApi clubs;
  final CompetitionApi competitions;
  final NationalTeamApi nationalTeams;
}

class GtexRuntimeControllers {
  const GtexRuntimeControllers({required this.exchange, this.admin});

  final GteExchangeController exchange;
  final AdminCommandCenterApi? admin;
}

class GtexRuntime {
  const GtexRuntime({
    required this.env,
    required this.apiBaseUrl,
    required this.accessToken,
    required this.websocket,
    required this.repositories,
    required this.controllers,
    required this.capabilities,
    required this.readiness,
    required this.observability,
    required this.session,
  });

  final GtexRuntimeEnv env;
  final String apiBaseUrl;
  final String? accessToken;
  final GtexRealtimeClient? websocket;
  final GtexRuntimeRepositories repositories;
  final GtexRuntimeControllers controllers;
  final GtexRuntimeCapabilities capabilities;
  final GtexRuntimeReadiness readiness;
  final GtexRuntimeObservability observability;
  final AuthSession? session;
}
