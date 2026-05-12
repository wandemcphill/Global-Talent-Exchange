import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';

import 'club_lifecycle_models.dart';

class GtexClubLifecycleApi {
  GtexClubLifecycleApi({required this.client, required this.fixtures});

  final GteAuthedApi client;
  final GtexClubLifecycleFixtures fixtures;

  factory GtexClubLifecycleApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.live,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    return GtexClubLifecycleApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: resolvedMode,
      ),
      fixtures: GtexClubLifecycleFixtures.seed(),
    );
  }

  factory GtexClubLifecycleApi.fixture() {
    return GtexClubLifecycleApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      fixtures: GtexClubLifecycleFixtures.seed(),
    );
  }

  Future<GtexClubOperatingDashboard> fetchDashboard(String clubId) {
    final String encodedClubId = Uri.encodeComponent(clubId);
    return client.withFallback<GtexClubOperatingDashboard>(() async {
      final Map<String, dynamic> payload = await client.getMap(
        '/api/clubs/$encodedClubId/operating-dashboard',
      );
      return GtexClubOperatingDashboard.fromJson(payload);
    }, () => fixtures.dashboard(clubId));
  }

  Future<GtexClubSquadRegistration> syncSquadRegistration(String clubId) {
    final String encodedClubId = Uri.encodeComponent(clubId);
    return client.withFallback<GtexClubSquadRegistration>(() async {
      final Object? payload = await client.post(
        '/api/clubs/$encodedClubId/squad-registration',
        body: <String, Object?>{
          'season_label': 'launch',
          'player_ids': const <String>[],
        },
      );
      return GtexClubSquadRegistration.fromJson(payload);
    }, () => fixtures.syncSquadRegistration(clubId));
  }

  Future<GtexClubSquadRegistration> submitSquadRegistration(String clubId) {
    final String encodedClubId = Uri.encodeComponent(clubId);
    return client.withFallback<GtexClubSquadRegistration>(() async {
      final Object? payload = await client.post(
        '/api/clubs/$encodedClubId/squad-registration/submit',
      );
      return GtexClubSquadRegistration.fromJson(payload);
    }, () => fixtures.submitSquadRegistration(clubId));
  }

  Future<GtexClubSquadRegistration> lockSquadRegistration(String clubId) {
    final String encodedClubId = Uri.encodeComponent(clubId);
    return client.withFallback<GtexClubSquadRegistration>(() async {
      final Object? payload = await client.post(
        '/api/clubs/$encodedClubId/squad-registration/lock',
      );
      return GtexClubSquadRegistration.fromJson(payload);
    }, () => fixtures.lockSquadRegistration(clubId));
  }

  Future<GtexClubLifecycle> advanceLifecycle(String clubId) {
    final String encodedClubId = Uri.encodeComponent(clubId);
    return client.withFallback<GtexClubLifecycle>(() async {
      final Object? payload = await client.post(
        '/api/clubs/$encodedClubId/advance-lifecycle',
        body: const <String, Object?>{
          'reason': 'Advanced from the GTEX club lifecycle dashboard.',
        },
      );
      return GtexClubLifecycle.fromJson(payload);
    }, () => fixtures.advanceLifecycle(clubId));
  }
}

class GtexClubLifecycleFixtures {
  GtexClubLifecycleFixtures(this._dashboard);

  GtexClubOperatingDashboard _dashboard;

  static GtexClubLifecycleFixtures seed() {
    final DateTime now = DateTime.parse('2026-05-11T10:30:00Z');
    return GtexClubLifecycleFixtures(
      GtexClubOperatingDashboard(
        clubId: 'fixture-club',
        lifecycle: GtexClubLifecycle(
          clubId: 'fixture-club',
          state: GtexClubLifecycleState.squadReady,
          previousState: GtexClubLifecycleState.squadBuilding,
          readinessScore: 88,
          blockedReason: 'squad_registered',
          metadata: const <String, Object?>{},
          updatedAt: now,
          readiness: GtexClubReadiness(
            clubId: 'fixture-club',
            readinessScore: 88,
            recommendedState: GtexClubLifecycleState.squadReady,
            competitionEligible: false,
            checklist: <GtexClubReadinessItem>[
              const GtexClubReadinessItem(
                key: 'profile_complete',
                label: 'Club profile complete',
                complete: true,
                detail: 'Name, slug, colors, and home venue are present.',
              ),
              const GtexClubReadinessItem(
                key: 'identity_ready',
                label: 'Badge or kit identity selected',
                complete: true,
                detail: 'Crest or jersey design is present.',
              ),
              const GtexClubReadinessItem(
                key: 'wallet_funded',
                label: 'Wallet funded',
                complete: true,
                detail: 'Owner wallet has a positive balance.',
              ),
              const GtexClubReadinessItem(
                key: 'minimum_squad',
                label: 'Minimum squad size reached',
                complete: true,
                detail: '11 of 11 required players assigned.',
              ),
              const GtexClubReadinessItem(
                key: 'position_balance',
                label: 'Position balance valid',
                complete: true,
                detail:
                    'goalkeeper: 1/1, defender: 4/3, midfielder: 3/3, forward: 3/1',
              ),
              const GtexClubReadinessItem(
                key: 'owner_kyc_verified',
                label: 'Owner KYC verified',
                complete: true,
                detail: 'Owner must have a full verified KYC state.',
              ),
              const GtexClubReadinessItem(
                key: 'no_outstanding_blocks',
                label: 'No outstanding disputes or restrictions',
                complete: true,
                detail: 'Eligibility flags must be clear.',
              ),
              const GtexClubReadinessItem(
                key: 'squad_registered',
                label: 'Squad registration submitted',
                complete: false,
                detail:
                    'Submit and lock the launch squad before competition entry.',
              ),
            ],
            blockers: const <String>['squad_registered'],
            updatedAt: now,
          ),
        ),
        squadRegistration: GtexClubSquadRegistration(
          id: 'fixture-registration',
          clubId: 'fixture-club',
          seasonLabel: 'launch',
          status: GtexSquadRegistrationStatus.draft,
          players: const <GtexClubSquadPlayer>[
            GtexClubSquadPlayer(
              playerId: 'p-1',
              name: 'Fixture Keeper',
              position: 'GK',
              positionGroup: 'goalkeeper',
            ),
            GtexClubSquadPlayer(
              playerId: 'p-2',
              name: 'Fixture Forward',
              position: 'ST',
              positionGroup: 'forward',
            ),
          ],
          positionSummary: const <String, int>{
            'goalkeeper': 1,
            'defender': 4,
            'midfielder': 3,
            'forward': 3,
          },
          submittedAt: null,
          lockedAt: null,
          updatedAt: now,
        ),
        moduleLinks: const <Map<String, String>>[
          <String, String>{'label': 'Squad registration', 'route': '/app/club'},
        ],
        counts: const <String, int>{'players': 11, 'registered': 2},
        alerts: const <String>['squad_registered'],
        updatedAt: now,
      ),
    );
  }

  Future<GtexClubOperatingDashboard> dashboard(String clubId) async {
    return _dashboard;
  }

  Future<GtexClubSquadRegistration> syncSquadRegistration(String clubId) async {
    return _replaceRegistration(GtexSquadRegistrationStatus.draft);
  }

  Future<GtexClubSquadRegistration> submitSquadRegistration(
    String clubId,
  ) async {
    return _replaceRegistration(GtexSquadRegistrationStatus.submitted);
  }

  Future<GtexClubSquadRegistration> lockSquadRegistration(String clubId) async {
    return _replaceRegistration(GtexSquadRegistrationStatus.locked);
  }

  Future<GtexClubLifecycle> advanceLifecycle(String clubId) async {
    _dashboard = _dashboard.copyWithLifecycle(
      GtexClubLifecycle(
        clubId: _dashboard.clubId,
        state: GtexClubLifecycleState.competitionReady,
        previousState: _dashboard.lifecycle.state,
        readinessScore: _dashboard.lifecycle.readinessScore,
        blockedReason: null,
        metadata: _dashboard.lifecycle.metadata,
        updatedAt: DateTime.now().toUtc(),
        readiness: _dashboard.lifecycle.readiness,
      ),
    );
    return _dashboard.lifecycle;
  }

  GtexClubSquadRegistration _replaceRegistration(
    GtexSquadRegistrationStatus status,
  ) {
    final GtexClubSquadRegistration previous = _dashboard.squadRegistration!;
    final GtexClubSquadRegistration registration = GtexClubSquadRegistration(
      id: previous.id,
      clubId: previous.clubId,
      seasonLabel: previous.seasonLabel,
      status: status,
      players: previous.players,
      positionSummary: previous.positionSummary,
      submittedAt:
          status == GtexSquadRegistrationStatus.draft
              ? null
              : DateTime.now().toUtc(),
      lockedAt:
          status == GtexSquadRegistrationStatus.locked
              ? DateTime.now().toUtc()
              : previous.lockedAt,
      updatedAt: DateTime.now().toUtc(),
    );
    _dashboard = _dashboard.copyWithRegistration(registration);
    return registration;
  }
}

extension _GtexClubOperatingDashboardCopy on GtexClubOperatingDashboard {
  GtexClubOperatingDashboard copyWithRegistration(
    GtexClubSquadRegistration registration,
  ) {
    return GtexClubOperatingDashboard(
      clubId: clubId,
      lifecycle: lifecycle,
      squadRegistration: registration,
      moduleLinks: moduleLinks,
      counts: counts,
      alerts: alerts,
      updatedAt: DateTime.now().toUtc(),
    );
  }

  GtexClubOperatingDashboard copyWithLifecycle(GtexClubLifecycle value) {
    return GtexClubOperatingDashboard(
      clubId: clubId,
      lifecycle: value,
      squadRegistration: squadRegistration,
      moduleLinks: moduleLinks,
      counts: counts,
      alerts: alerts,
      updatedAt: DateTime.now().toUtc(),
    );
  }
}
