import 'dart:math';

import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import '../models/hosted_competition_models.dart';

class HostedCompetitionApi {
  HostedCompetitionApi({
    required this.client,
    required this.fixtures,
  });

  final GteAuthedApi client;
  final _HostedCompetitionFixtures fixtures;

  factory HostedCompetitionApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
  }) {
    return HostedCompetitionApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: mode,
      ),
      fixtures: _HostedCompetitionFixtures.seed(),
    );
  }

  factory HostedCompetitionApi.fixture() {
    return HostedCompetitionApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      fixtures: _HostedCompetitionFixtures.seed(),
    );
  }

  Future<List<HostedCompetitionTemplate>> listTemplates() {
    return client.withFallback<List<HostedCompetitionTemplate>>(
      () async {
        final List<dynamic> payload =
            await client.getList('/hosted-competitions/templates', auth: false);
        return payload
            .map(HostedCompetitionTemplate.fromJson)
            .toList(growable: false);
      },
      fixtures.templates,
    );
  }

  Future<List<HostedCompetition>> listCompetitions() {
    return client.withFallback<List<HostedCompetition>>(
      () async {
        final Map<String, dynamic> payload =
            await client.getMap('/hosted-competitions', auth: false);
        final List<dynamic> competitions =
            payload['competitions'] as List<dynamic>? ?? <dynamic>[];
        return competitions
            .map(HostedCompetition.fromJson)
            .toList(growable: false);
      },
      fixtures.listCompetitions,
    );
  }

  Future<List<HostedCompetition>> listMyCompetitions() {
    return client.withFallback<List<HostedCompetition>>(
      () async {
        final Map<String, dynamic> payload =
            await client.getMap('/hosted-competitions/mine');
        final List<dynamic> competitions =
            payload['competitions'] as List<dynamic>? ?? <dynamic>[];
        return competitions
            .map(HostedCompetition.fromJson)
            .toList(growable: false);
      },
      fixtures.listMyCompetitions,
    );
  }

  Future<HostedCompetitionDetail> fetchDetail(String competitionId) {
    return client.withFallback<HostedCompetitionDetail>(
      () async {
        final Map<String, dynamic> payload =
            await client.getMap('/hosted-competitions/$competitionId', auth: false);
        return HostedCompetitionDetail.fromJson(payload);
      },
      () async => fixtures.detail(competitionId),
    );
  }

  Future<HostedCompetition> createCompetition({
    required String templateKey,
    required String title,
    String description = '',
    String visibility = 'public',
    int? maxParticipants,
    double? entryFeeFancoin,
    double? rewardPoolFancoin,
  }) {
    return client.withFallback<HostedCompetition>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/hosted-competitions',
          body: <String, Object?>{
            'template_key': templateKey,
            'title': title,
            'description': description,
            'visibility': visibility,
            if (maxParticipants != null) 'max_participants': maxParticipants,
            if (entryFeeFancoin != null) 'entry_fee_fancoin': entryFeeFancoin,
            if (rewardPoolFancoin != null)
              'reward_pool_fancoin': rewardPoolFancoin,
            'metadata_json': <String, Object?>{},
          },
        );
        final Map<String, dynamic> map = payload as Map<String, dynamic>? ?? <String, dynamic>{};
        return HostedCompetition.fromJson(map['competition'] ?? map);
      },
      () async => fixtures.createCompetition(title: title, templateKey: templateKey),
    );
  }

  Future<HostedCompetition> joinCompetition(String competitionId) {
    return client.withFallback<HostedCompetition>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/hosted-competitions/$competitionId/join',
        );
        final Map<String, dynamic> map = payload as Map<String, dynamic>? ?? <String, dynamic>{};
        return HostedCompetition.fromJson(map['competition'] ?? map);
      },
      () async => fixtures.joinCompetition(competitionId),
    );
  }

  Future<List<HostedCompetitionStanding>> listStandings(String competitionId) {
    return client.withFallback<List<HostedCompetitionStanding>>(
      () async {
        final List<dynamic> payload = await client.getList(
          '/hosted-competitions/$competitionId/standings',
          auth: false,
        );
        return payload
            .map(HostedCompetitionStanding.fromJson)
            .toList(growable: false);
      },
      () async => fixtures.standings(competitionId),
    );
  }

  Future<HostedCompetitionFinance> fetchFinance(String competitionId) {
    return client.withFallback<HostedCompetitionFinance>(
      () async {
        final Map<String, dynamic> payload =
            await client.getMap('/hosted-competitions/$competitionId/finance', auth: false);
        return HostedCompetitionFinance.fromJson(payload);
      },
      () async => fixtures.finance(competitionId),
    );
  }

  Future<HostedCompetition> launchCompetition(String competitionId) {
    return client.withFallback<HostedCompetition>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/hosted-competitions/$competitionId/launch',
        );
        final Map<String, dynamic> map = payload as Map<String, dynamic>? ?? <String, dynamic>{};
        return HostedCompetition.fromJson(map['competition'] ?? map);
      },
      () async => fixtures.launchCompetition(competitionId),
    );
  }

  Future<List<HostedCompetitionTemplate>> seedTemplates() {
    return client.withFallback<List<HostedCompetitionTemplate>>(
      () async {
        final List<dynamic> payload =
            await client.getList('/admin/hosted-competitions/seed');
        return payload
            .map(HostedCompetitionTemplate.fromJson)
            .toList(growable: false);
      },
      fixtures.seedTemplates,
    );
  }

  Future<HostedCompetition> finalizeCompetition({
    required String competitionId,
    required List<Map<String, Object?>> placements,
    String note = '',
  }) {
    return client.withFallback<HostedCompetition>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/admin/hosted-competitions/$competitionId/finalize',
          body: <String, Object?>{
            'placements': placements,
            'note': note,
          },
        );
        final Map<String, dynamic> map = payload as Map<String, dynamic>? ?? <String, dynamic>{};
        return HostedCompetition.fromJson(map['competition'] ?? map);
      },
      () async => fixtures.finalizeCompetition(competitionId),
    );
  }
}

class _HostedCompetitionFixtures {
  _HostedCompetitionFixtures(this._templates, this._competitions);

  final List<HostedCompetitionTemplate> _templates;
  final List<HostedCompetition> _competitions;

  static _HostedCompetitionFixtures seed() {
    final List<HostedCompetitionTemplate> templates = <HostedCompetitionTemplate>[
      HostedCompetitionTemplate(
        id: 'tpl-1',
        templateKey: 'creator-cup',
        title: 'Creator Cup',
        description: 'Invite-driven creator cup with a compact bracket.',
        competitionType: 'creator',
        teamType: 'club',
        ageGrade: 'senior',
        cupOrLeague: 'cup',
        participants: 16,
        viewingMode: 'broadcast',
        giftRules: const <String, Object?>{'gift_multiplier': 1.2},
        seedingMethod: 'balanced',
        isUserHostable: true,
        entryFeeFancoin: 5,
        rewardPoolFancoin: 80,
        platformFeeBps: 800,
        metadata: const <String, Object?>{},
        active: true,
      ),
    ];
    final List<HostedCompetition> competitions = <HostedCompetition>[
      HostedCompetition(
        id: 'hosted-1',
        templateId: templates.first.id,
        hostUserId: 'user-1',
        title: 'Friday Night Creator Cup',
        slug: 'friday-night-creator-cup',
        description: 'Fast cup with creator invites.',
        status: 'open',
        visibility: 'public',
        startsAt: DateTime.parse('2026-03-15T18:00:00Z'),
        lockAt: DateTime.parse('2026-03-15T17:30:00Z'),
        maxParticipants: 16,
        entryFeeFancoin: 5,
        rewardPoolFancoin: 80,
        platformFeeAmount: 6,
        metadata: const <String, Object?>{},
        createdAt: DateTime.parse('2026-03-10T12:00:00Z'),
        updatedAt: DateTime.parse('2026-03-12T12:00:00Z'),
      ),
    ];
    return _HostedCompetitionFixtures(templates, competitions);
  }

  Future<List<HostedCompetitionTemplate>> templates() async =>
      List<HostedCompetitionTemplate>.of(_templates, growable: false);

  Future<List<HostedCompetition>> listCompetitions() async =>
      List<HostedCompetition>.of(_competitions, growable: false);

  Future<List<HostedCompetition>> listMyCompetitions() async =>
      List<HostedCompetition>.of(_competitions, growable: false);

  Future<HostedCompetitionDetail> detail(String competitionId) async {
    final HostedCompetition competition = _competitions.first;
    final HostedCompetitionTemplate template = _templates.first;
    final List<HostedCompetitionParticipant> participants =
        List<HostedCompetitionParticipant>.generate(
      min(competition.maxParticipants, 6),
      (int index) => HostedCompetitionParticipant(
        id: 'participant-$index',
        competitionId: competition.id,
        userId: 'user-$index',
        joinedAt: DateTime.now().toUtc(),
        entryFeeFancoin: competition.entryFeeFancoin,
        payoutEligible: true,
        metadata: const <String, Object?>{},
      ),
    );
    return HostedCompetitionDetail(
      competition: competition,
      template: template,
      participants: participants,
      currentParticipants: participants.length,
      joinOpen: true,
    );
  }

  Future<HostedCompetition> createCompetition({
    required String title,
    required String templateKey,
  }) async {
    final HostedCompetition created = HostedCompetition(
      id: 'hosted-${_competitions.length + 1}',
      templateId: _templates.first.id,
      hostUserId: 'user-1',
      title: title,
      slug: title.toLowerCase().replaceAll(' ', '-'),
      description: 'Hosted competition',
      status: 'draft',
      visibility: 'public',
      startsAt: null,
      lockAt: null,
      maxParticipants: 16,
      entryFeeFancoin: 5,
      rewardPoolFancoin: 80,
      platformFeeAmount: 6,
      metadata: const <String, Object?>{},
      createdAt: DateTime.now().toUtc(),
      updatedAt: DateTime.now().toUtc(),
    );
    _competitions.insert(0, created);
    return created;
  }

  Future<HostedCompetition> joinCompetition(String competitionId) async {
    return _competitions.firstWhere(
        (HostedCompetition item) => item.id == competitionId,
        orElse: () => _competitions.first);
  }

  Future<List<HostedCompetitionStanding>> standings(String competitionId) async {
    return <HostedCompetitionStanding>[
      HostedCompetitionStanding(
        id: 'standing-1',
        competitionId: competitionId,
        userId: 'user-1',
        finalRank: 1,
        points: 12,
        wins: 4,
        draws: 0,
        losses: 0,
        goalsFor: 10,
        goalsAgainst: 2,
        payoutAmount: 50,
        metadata: const <String, Object?>{},
        createdAt: DateTime.now().toUtc(),
        updatedAt: DateTime.now().toUtc(),
      ),
    ];
  }

  Future<HostedCompetitionFinance> finance(String competitionId) async {
    return HostedCompetitionFinance(
      currency: 'FAN',
      participantCount: 12,
      entryFeeFancoin: 5,
      grossCollected: 60,
      projectedRewardPool: 80,
      projectedPlatformFee: 6,
      escrowBalance: 54,
      settledPrizes: 0,
      settledPlatformFee: 0,
      status: 'open',
    );
  }

  Future<HostedCompetition> launchCompetition(String competitionId) async {
    final int index = _competitions.indexWhere(
        (HostedCompetition item) => item.id == competitionId);
    if (index == -1) {
      return _competitions.first;
    }
    final HostedCompetition updated = HostedCompetition(
      id: _competitions[index].id,
      templateId: _competitions[index].templateId,
      hostUserId: _competitions[index].hostUserId,
      title: _competitions[index].title,
      slug: _competitions[index].slug,
      description: _competitions[index].description,
      status: 'live',
      visibility: _competitions[index].visibility,
      startsAt: _competitions[index].startsAt,
      lockAt: _competitions[index].lockAt,
      maxParticipants: _competitions[index].maxParticipants,
      entryFeeFancoin: _competitions[index].entryFeeFancoin,
      rewardPoolFancoin: _competitions[index].rewardPoolFancoin,
      platformFeeAmount: _competitions[index].platformFeeAmount,
      metadata: _competitions[index].metadata,
      createdAt: _competitions[index].createdAt,
      updatedAt: DateTime.now().toUtc(),
    );
    _competitions[index] = updated;
    return updated;
  }

  Future<List<HostedCompetitionTemplate>> seedTemplates() async {
    return templates();
  }

  Future<HostedCompetition> finalizeCompetition(String competitionId) async {
    return launchCompetition(competitionId);
  }
}
