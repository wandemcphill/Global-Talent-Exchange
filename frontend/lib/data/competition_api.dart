import 'dart:math';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/competition_rule_models.dart';

class CompetitionApi {
  CompetitionApi({
    required this.config,
    required this.transport,
  }) : _fixtureStore = _CompetitionFixtureStore.seed();

  CompetitionApi._({
    required this.config,
    required this.transport,
    required _CompetitionFixtureStore fixtureStore,
  }) : _fixtureStore = fixtureStore;

  final GteRepositoryConfig config;
  final GteTransport transport;
  final _CompetitionFixtureStore _fixtureStore;

  factory CompetitionApi.standard({
    required String baseUrl,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
  }) {
    return CompetitionApi(
      config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
      transport: GteHttpTransport(),
    );
  }

  factory CompetitionApi.fixture() {
    return CompetitionApi._(
      config: const GteRepositoryConfig(
        baseUrl: 'http://127.0.0.1:8000',
        mode: GteBackendMode.fixture,
      ),
      transport: _UnsupportedCompetitionTransport(),
      fixtureStore: _CompetitionFixtureStore.seed(),
    );
  }

  Future<CompetitionListResponse> fetchCompetitions({
    String? userId,
  }) {
    return _withFallback<CompetitionListResponse>(
      () async {
        final Object? payload = await _sendBest(
          'GET',
          const <String>['/api/competitions'],
        );
        return CompetitionListResponse.fromJson(payload);
      },
      () async => _fixtureStore.list(userId: userId),
    );
  }

  Future<CompetitionSummary> fetchCompetition(
    String competitionId, {
    String? userId,
    String? inviteCode,
  }) {
    return _withFallback<CompetitionSummary>(
      () async {
        final Object? payload = await _sendBest(
          'GET',
          <String>['/api/competitions/$competitionId'],
          query: <String, Object?>{
            if (userId != null && userId.trim().isNotEmpty) 'viewer_id': userId,
            if (inviteCode != null && inviteCode.trim().isNotEmpty)
              'invite_code': inviteCode,
          },
        );
        return CompetitionSummary.fromJson(payload);
      },
      () async => _fixtureStore.get(
        competitionId,
        userId: userId,
        inviteCode: inviteCode,
      ),
    );
  }

  Future<CompetitionFinancialSummary> fetchFinancials(
    String competitionId, {
    String? userId,
  }) {
    return _withFallback<CompetitionFinancialSummary>(
      () async {
        final Object? payload = await _sendBest(
          'GET',
          <String>['/api/competitions/$competitionId/financials'],
        );
        return CompetitionFinancialSummary.fromJson(payload);
      },
      () async => _fixtureStore.financials(competitionId),
    );
  }

  Future<CompetitionSummary> createCompetition(CompetitionDraft draft) {
    return _withFallback<CompetitionSummary>(
      () async {
        final Object? payload = await _sendBest(
          'POST',
          const <String>['/api/competitions'],
          body: draft.toCreateRequestJson(),
        );
        return CompetitionSummary.fromJson(payload);
      },
      () async => _fixtureStore.create(draft),
    );
  }

  Future<CompetitionSummary> publishCompetition(
    String competitionId, {
    bool openForJoin = true,
    String? userId,
  }) {
    return _withFallback<CompetitionSummary>(
      () async {
        final Object? payload = await _sendBest(
          'POST',
          <String>['/api/competitions/$competitionId/publish'],
          body: <String, Object?>{'open_for_join': openForJoin},
        );
        return CompetitionSummary.fromJson(payload);
      },
      () async => _fixtureStore.publish(
        competitionId,
        openForJoin: openForJoin,
        userId: userId,
      ),
    );
  }

  Future<CompetitionSummary> joinCompetition(
    String competitionId, {
    required String userId,
    String? userName,
    String? inviteCode,
  }) {
    return _withFallback<CompetitionSummary>(
      () async {
        final Object? payload = await _sendBest(
          'POST',
          <String>['/api/competitions/$competitionId/join'],
          body: <String, Object?>{
            'user_id': userId,
            if (userName != null && userName.trim().isNotEmpty)
              'user_name': userName.trim(),
            if (inviteCode != null && inviteCode.trim().isNotEmpty)
              'invite_code': inviteCode.trim(),
          },
        );
        return CompetitionSummary.fromJson(payload);
      },
      () async => _fixtureStore.join(
        competitionId,
        userId: userId,
        userName: userName,
        inviteCode: inviteCode,
      ),
    );
  }

  Future<CompetitionInviteView> createInvite(
    String competitionId, {
    required String issuedBy,
    int maxUses = 25,
    DateTime? expiresAt,
    String? note,
  }) {
    return _withFallback<CompetitionInviteView>(
      () async {
        final Object? payload = await _sendBest(
          'POST',
          <String>['/api/competitions/$competitionId/invites'],
          body: <String, Object?>{
            'issued_by': issuedBy,
            'max_uses': maxUses,
            if (expiresAt != null) 'expires_at': expiresAt.toUtc().toIso8601String(),
            if (note != null && note.trim().isNotEmpty) 'note': note.trim(),
          },
        );
        return CompetitionInviteView.fromJson(payload);
      },
      () async => _fixtureStore.createInvite(
        competitionId,
        issuedBy: issuedBy,
        maxUses: maxUses,
        expiresAt: expiresAt,
        note: note,
      ),
    );
  }

  Future<T> _withFallback<T>(
    Future<T> Function() liveCall,
    Future<T> Function() fixtureCall,
  ) async {
    if (config.mode == GteBackendMode.fixture) {
      return fixtureCall();
    }
    try {
      return await liveCall();
    } on GteApiException catch (error) {
      if (_supportsFixtureFallback(error)) {
        return fixtureCall();
      }
      rethrow;
    }
  }

  bool _supportsFixtureFallback(GteApiException error) {
    if (config.mode != GteBackendMode.liveThenFixture) {
      return false;
    }
    return error.type == GteApiErrorType.network ||
        error.type == GteApiErrorType.unavailable ||
        error.type == GteApiErrorType.parsing ||
        error.type == GteApiErrorType.notFound;
  }

  Future<Object?> _sendBest(
    String method,
    List<String> paths, {
    Map<String, Object?> query = const <String, Object?>{},
    Object? body,
  }) async {
    GteApiException? lastError;
    for (final String path in paths) {
      try {
        return await _request(
          method,
          path,
          query: query,
          body: body,
        );
      } on GteApiException catch (error) {
        lastError = error;
        if (error.statusCode == 404 || error.statusCode == 405) {
          continue;
        }
        rethrow;
      }
    }
    throw lastError ??
        const GteApiException(
          type: GteApiErrorType.notFound,
          message: 'Competition endpoint not found.',
        );
  }

  Future<Object?> _request(
    String method,
    String path, {
    Map<String, Object?> query = const <String, Object?>{},
    Object? body,
  }) async {
    final Map<String, String> headers = <String, String>{
      'Accept': 'application/json',
      if (body != null) 'Content-Type': 'application/json',
    };
    try {
      final GteTransportResponse response = await transport.send(
        GteTransportRequest(
          method: method,
          uri: config.uriFor(path, query),
          headers: headers,
          body: body,
        ),
      );
      if (response.statusCode >= 400) {
        throw GteApiException(
          type: _errorTypeFromStatusCode(response.statusCode),
          message: _errorMessage(response.body),
          statusCode: response.statusCode,
          cause: response.body,
        );
      }
      return response.body;
    } on GteParsingException catch (error) {
      throw GteApiException(
        type: GteApiErrorType.parsing,
        message: error.message,
        cause: error,
      );
    } on GteApiException {
      rethrow;
    } catch (error) {
      throw GteApiException(
        type: GteApiErrorType.network,
        message: 'Unable to reach the competition backend.',
        cause: error,
      );
    }
  }
}

class _UnsupportedCompetitionTransport implements GteTransport {
  @override
  Future<GteTransportResponse> send(GteTransportRequest request) {
    throw const GteApiException(
      type: GteApiErrorType.unavailable,
      message: 'Competition transport is disabled in fixture mode.',
    );
  }
}

class _CompetitionRecord {
  _CompetitionRecord({
    required this.summary,
    required this.participantIds,
    required this.invites,
  });

  CompetitionSummary summary;
  Set<String> participantIds;
  List<CompetitionInviteView> invites;
}

class _CompetitionFixtureStore {
  _CompetitionFixtureStore({
    required Map<String, _CompetitionRecord> records,
  }) : _records = records;

  final Map<String, _CompetitionRecord> _records;
  int _idSequence = 400;
  final Random _random = Random(42);

  factory _CompetitionFixtureStore.seed() {
    final Map<String, _CompetitionRecord> records =
        <String, _CompetitionRecord>{};
    for (final CompetitionSummary item in _seedCompetitions) {
      records[item.id] = _CompetitionRecord(
        summary: item,
        participantIds: _seedParticipantIds[item.id] ?? <String>{},
        invites: <CompetitionInviteView>[
          if (item.visibility == CompetitionVisibility.inviteOnly)
            CompetitionInviteView(
              inviteCode: 'OPEN-${item.id.substring(item.id.length - 4).toUpperCase()}',
              issuedBy: item.creatorId,
              createdAt: item.updatedAt,
              expiresAt: item.updatedAt.add(const Duration(days: 14)),
              maxUses: 24,
              uses: 2,
              note: 'Creator competition invite',
            ),
        ],
      );
    }
    return _CompetitionFixtureStore(records: records);
  }

  CompetitionListResponse list({String? userId}) {
    final List<CompetitionSummary> items = _records.values
        .map((_CompetitionRecord record) => _viewFor(record, userId: userId))
        .toList(growable: true)
      ..sort((CompetitionSummary left, CompetitionSummary right) {
        final int participantCompare =
            right.participantCount.compareTo(left.participantCount);
        if (participantCompare != 0) {
          return participantCompare;
        }
        return right.updatedAt.compareTo(left.updatedAt);
      });
    return CompetitionListResponse(total: items.length, items: items);
  }

  CompetitionSummary get(
    String competitionId, {
    String? userId,
    String? inviteCode,
  }) {
    final _CompetitionRecord? record = _records[competitionId];
    if (record == null) {
      throw const GteApiException(
        type: GteApiErrorType.notFound,
        message: 'Competition not found.',
      );
    }
    return _viewFor(record, userId: userId, inviteCode: inviteCode);
  }

  CompetitionFinancialSummary financials(String competitionId) {
    final _CompetitionRecord? record = _records[competitionId];
    if (record == null) {
      throw const GteApiException(
        type: GteApiErrorType.notFound,
        message: 'Competition not found.',
      );
    }
    final CompetitionSummary summary = record.summary;
    return CompetitionFinancialSummary(
      competitionId: summary.id,
      participantCount: summary.participantCount,
      entryFee: summary.entryFee,
      grossPool: summary.entryFee * summary.participantCount,
      platformFeeAmount: summary.platformFeeAmount,
      hostFeeAmount: summary.hostFeeAmount,
      prizePool: summary.prizePool,
      payoutStructure: summary.payoutStructure,
      currency: summary.currency,
    );
  }

  CompetitionSummary create(CompetitionDraft draft) {
    final String id = 'ugc-${_idSequence++}';
    final DateTime now = DateTime.now().toUtc();
    final CompetitionSummary summary = CompetitionSummary(
      id: id,
      name: draft.name.trim(),
      format: draft.format,
      visibility: draft.visibility,
      status: CompetitionStatus.draft,
      creatorId: draft.creatorId,
      creatorName: draft.creatorName,
      participantCount: 0,
      capacity: draft.capacity,
      currency: draft.currency,
      entryFee: draft.entryFee,
      platformFeePct: draft.platformFeePct,
      hostFeePct: draft.hostFeePct,
      platformFeeAmount: 0,
      hostFeeAmount: 0,
      prizePool: 0,
      payoutStructure: draft.payoutRules
          .map(
            (CompetitionDraftPayoutRule rule) => CompetitionPayoutBreakdown(
              place: rule.place,
              percent: rule.percent,
              amount: 0,
            ),
          )
          .toList(growable: false),
      rulesSummary: draft.rulesSummary,
      joinEligibility: const CompetitionJoinEligibility(
        eligible: false,
        reason: 'competition_not_open',
      ),
      beginnerFriendly: draft.beginnerFriendly,
      createdAt: now,
      updatedAt: now,
    );
    _records[id] = _CompetitionRecord(
      summary: summary,
      participantIds: <String>{},
      invites: <CompetitionInviteView>[],
    );
    return summary;
  }

  CompetitionSummary publish(
    String competitionId, {
    required bool openForJoin,
    String? userId,
  }) {
    final _CompetitionRecord record = _requireRecord(competitionId);
    record.summary = _recalculateFinancials(
      record.summary.copyWith(
        status: openForJoin
            ? CompetitionStatus.openForJoin
            : CompetitionStatus.published,
        updatedAt: DateTime.now().toUtc(),
      ),
    );
    return _viewFor(record, userId: userId);
  }

  CompetitionSummary join(
    String competitionId, {
    required String userId,
    String? userName,
    String? inviteCode,
  }) {
    final _CompetitionRecord record = _requireRecord(competitionId);
    final CompetitionJoinEligibility eligibility = _eligibilityFor(
      record,
      userId: userId,
      inviteCode: inviteCode,
    );
    if (!eligibility.eligible) {
      return record.summary.copyWith(joinEligibility: eligibility);
    }
    record.participantIds.add(userId);
    final int participantCount = record.participantIds.length;
    record.summary = _recalculateFinancials(
      record.summary.copyWith(
        participantCount: participantCount,
        status: participantCount >= record.summary.capacity
            ? CompetitionStatus.filled
            : CompetitionStatus.openForJoin,
        updatedAt: DateTime.now().toUtc(),
      ),
    );
    return _viewFor(record, userId: userId, inviteCode: inviteCode);
  }

  CompetitionInviteView createInvite(
    String competitionId, {
    required String issuedBy,
    int maxUses = 25,
    DateTime? expiresAt,
    String? note,
  }) {
    final _CompetitionRecord record = _requireRecord(competitionId);
    final CompetitionInviteView invite = CompetitionInviteView(
      inviteCode: _nextInviteCode(),
      issuedBy: issuedBy,
      createdAt: DateTime.now().toUtc(),
      expiresAt: expiresAt ?? DateTime.now().toUtc().add(const Duration(days: 14)),
      maxUses: maxUses,
      uses: 0,
      note: note,
    );
    record.invites.insert(0, invite);
    return invite;
  }

  _CompetitionRecord _requireRecord(String competitionId) {
    final _CompetitionRecord? record = _records[competitionId];
    if (record == null) {
      throw const GteApiException(
        type: GteApiErrorType.notFound,
        message: 'Competition not found.',
      );
    }
    return record;
  }

  CompetitionSummary _viewFor(
    _CompetitionRecord record, {
    String? userId,
    String? inviteCode,
  }) {
    return record.summary.copyWith(
      joinEligibility: _eligibilityFor(
        record,
        userId: userId,
        inviteCode: inviteCode,
      ),
    );
  }

  CompetitionJoinEligibility _eligibilityFor(
    _CompetitionRecord record, {
    String? userId,
    String? inviteCode,
  }) {
    final CompetitionSummary summary = record.summary;
    if (userId != null && record.participantIds.contains(userId)) {
      return const CompetitionJoinEligibility(
        eligible: true,
        reason: 'already_joined',
      );
    }
    if (summary.status != CompetitionStatus.openForJoin) {
      return const CompetitionJoinEligibility(
        eligible: false,
        reason: 'competition_not_open',
      );
    }
    if (summary.participantCount >= summary.capacity) {
      return const CompetitionJoinEligibility(
        eligible: false,
        reason: 'competition_full',
      );
    }
    if (summary.visibility == CompetitionVisibility.inviteOnly) {
      final bool validInvite = inviteCode != null &&
          record.invites.any(
            (CompetitionInviteView invite) =>
                invite.inviteCode == inviteCode && invite.uses < invite.maxUses,
          );
      if (!validInvite) {
        return const CompetitionJoinEligibility(
          eligible: false,
          reason: 'invite_required',
          requiresInvite: true,
        );
      }
    }
    return const CompetitionJoinEligibility(eligible: true);
  }

  CompetitionSummary _recalculateFinancials(CompetitionSummary summary) {
    final double grossPool = summary.entryFee * summary.participantCount;
    final double platformFee = grossPool * summary.platformFeePct;
    final double hostFee = grossPool * summary.hostFeePct;
    final double prizePool = grossPool - platformFee - hostFee;
    final List<CompetitionPayoutBreakdown> payouts = summary.payoutStructure
        .map(
          (CompetitionPayoutBreakdown payout) => payout.copyWith(
            amount: prizePool * payout.percent,
          ),
        )
        .toList(growable: false);
    return summary.copyWith(
      platformFeeAmount: platformFee,
      hostFeeAmount: hostFee,
      prizePool: prizePool,
      payoutStructure: payouts,
    );
  }

  String _nextInviteCode() {
    const String alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    return List<String>.generate(
      8,
      (_) => alphabet[_random.nextInt(alphabet.length)],
    ).join();
  }
}

GteApiErrorType _errorTypeFromStatusCode(int statusCode) {
  if (statusCode == 401 || statusCode == 403) {
    return GteApiErrorType.unauthorized;
  }
  if (statusCode == 404) {
    return GteApiErrorType.notFound;
  }
  if (statusCode >= 500) {
    return GteApiErrorType.unavailable;
  }
  if (statusCode >= 400) {
    return GteApiErrorType.validation;
  }
  return GteApiErrorType.unknown;
}

String _errorMessage(Object? payload) {
  if (payload is String && payload.trim().isNotEmpty) {
    return payload.trim();
  }
  if (payload is Map) {
    final Map<String, Object?> json = GteJson.map(payload);
    final String? detail = GteJson.stringOrNull(
      json,
      <String>['detail', 'message', 'error'],
    );
    if (detail != null) {
      return detail;
    }
  }
  return 'Competition request failed.';
}

final List<CompetitionSummary> _seedCompetitions = <CompetitionSummary>[
  CompetitionSummary(
    id: 'ugc-101',
    name: 'Midnight Skill League',
    format: CompetitionFormat.league,
    visibility: CompetitionVisibility.public,
    status: CompetitionStatus.openForJoin,
    creatorId: 'studio-kai',
    creatorName: 'Studio Kai',
    participantCount: 8,
    capacity: 12,
    currency: 'credit',
    entryFee: 15,
    platformFeePct: 0.10,
    hostFeePct: 0.03,
    platformFeeAmount: 12,
    hostFeeAmount: 3.6,
    prizePool: 104.4,
    payoutStructure: const <CompetitionPayoutBreakdown>[
      CompetitionPayoutBreakdown(place: 1, percent: 0.50, amount: 52.2),
      CompetitionPayoutBreakdown(place: 2, percent: 0.30, amount: 31.32),
      CompetitionPayoutBreakdown(place: 3, percent: 0.20, amount: 20.88),
    ],
    rulesSummary:
        'Skill league standings use verified performance totals. Lineups lock 30 minutes before each scoring window. Result review stays open for 12 hours. Entry fees move into secure escrow until results settle.',
    joinEligibility: CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: false,
    createdAt: DateTime.utc(2026, 3, 9, 20),
    updatedAt: DateTime.utc(2026, 3, 12, 1, 30),
  ),
  CompetitionSummary(
    id: 'ugc-102',
    name: 'Coastal Creator Cup',
    format: CompetitionFormat.cup,
    visibility: CompetitionVisibility.public,
    status: CompetitionStatus.openForJoin,
    creatorId: 'demo-user',
    creatorName: 'Demo Fan',
    participantCount: 24,
    capacity: 32,
    currency: 'credit',
    entryFee: 0,
    platformFeePct: 0,
    hostFeePct: 0,
    platformFeeAmount: 0,
    hostFeeAmount: 0,
    prizePool: 0,
    payoutStructure: const <CompetitionPayoutBreakdown>[
      CompetitionPayoutBreakdown(place: 1, percent: 1.0, amount: 0),
    ],
    rulesSummary:
        'Skill cup advancement follows verified head-to-head results. Entries lock before the first scoring window begins. Results are verified before the transparent payout settles.',
    joinEligibility: CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 3, 11, 18),
    updatedAt: DateTime.utc(2026, 3, 12, 0, 40),
  ),
  CompetitionSummary(
    id: 'ugc-103',
    name: 'Rookie Community League',
    format: CompetitionFormat.league,
    visibility: CompetitionVisibility.public,
    status: CompetitionStatus.openForJoin,
    creatorId: 'academy-lab',
    creatorName: 'Academy Lab',
    participantCount: 5,
    capacity: 20,
    currency: 'credit',
    entryFee: 5,
    platformFeePct: 0.08,
    hostFeePct: 0.00,
    platformFeeAmount: 2.0,
    hostFeeAmount: 0,
    prizePool: 23.0,
    payoutStructure: const <CompetitionPayoutBreakdown>[
      CompetitionPayoutBreakdown(place: 1, percent: 0.45, amount: 10.35),
      CompetitionPayoutBreakdown(place: 2, percent: 0.30, amount: 6.90),
      CompetitionPayoutBreakdown(place: 3, percent: 0.25, amount: 5.75),
    ],
    rulesSummary:
        'Skill league standings use verified performance totals. Late entries remain available until the first scoring window closes. Result review stays open for 12 hours.',
    joinEligibility: CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 3, 12, 4),
    updatedAt: DateTime.utc(2026, 3, 12, 4, 20),
  ),
  CompetitionSummary(
    id: 'ugc-104',
    name: 'Verified Skill Cup Night',
    format: CompetitionFormat.cup,
    visibility: CompetitionVisibility.inviteOnly,
    status: CompetitionStatus.openForJoin,
    creatorId: 'verified-host',
    creatorName: 'Verified Host',
    participantCount: 10,
    capacity: 16,
    currency: 'credit',
    entryFee: 20,
    platformFeePct: 0.10,
    hostFeePct: 0.05,
    platformFeeAmount: 20,
    hostFeeAmount: 10,
    prizePool: 170,
    payoutStructure: const <CompetitionPayoutBreakdown>[
      CompetitionPayoutBreakdown(place: 1, percent: 0.60, amount: 102),
      CompetitionPayoutBreakdown(place: 2, percent: 0.25, amount: 42.5),
      CompetitionPayoutBreakdown(place: 3, percent: 0.15, amount: 25.5),
    ],
    rulesSummary:
        'Skill cup advancement follows verified head-to-head results. Entries lock before the first scoring window begins. Ties trigger an extra playoff round under the published rules.',
    joinEligibility: CompetitionJoinEligibility(
      eligible: false,
      reason: 'invite_required',
      requiresInvite: true,
    ),
    beginnerFriendly: false,
    createdAt: DateTime.utc(2026, 3, 10, 15),
    updatedAt: DateTime.utc(2026, 3, 11, 22),
  ),
  CompetitionSummary(
    id: 'ugc-105',
    name: 'City Ladder League',
    format: CompetitionFormat.league,
    visibility: CompetitionVisibility.public,
    status: CompetitionStatus.filled,
    creatorId: 'urban-scouts',
    creatorName: 'Urban Scouts',
    participantCount: 18,
    capacity: 18,
    currency: 'credit',
    entryFee: 9,
    platformFeePct: 0.10,
    hostFeePct: 0,
    platformFeeAmount: 16.2,
    hostFeeAmount: 0,
    prizePool: 145.8,
    payoutStructure: const <CompetitionPayoutBreakdown>[
      CompetitionPayoutBreakdown(place: 1, percent: 0.50, amount: 72.9),
      CompetitionPayoutBreakdown(place: 2, percent: 0.30, amount: 43.74),
      CompetitionPayoutBreakdown(place: 3, percent: 0.20, amount: 29.16),
    ],
    rulesSummary:
        'Skill league standings use verified performance totals. Entries lock before the first scoring window begins. Results are verified before the transparent payout settles.',
    joinEligibility: CompetitionJoinEligibility(
      eligible: false,
      reason: 'competition_full',
    ),
    beginnerFriendly: false,
    createdAt: DateTime.utc(2026, 3, 7, 12),
    updatedAt: DateTime.utc(2026, 3, 11, 19),
  ),
  CompetitionSummary(
    id: 'ugc-106',
    name: 'Weekend Creator Cup',
    format: CompetitionFormat.cup,
    visibility: CompetitionVisibility.public,
    status: CompetitionStatus.published,
    creatorId: 'demo-user',
    creatorName: 'Demo Fan',
    participantCount: 0,
    capacity: 8,
    currency: 'credit',
    entryFee: 12,
    platformFeePct: 0.10,
    hostFeePct: 0.02,
    platformFeeAmount: 0,
    hostFeeAmount: 0,
    prizePool: 0,
    payoutStructure: const <CompetitionPayoutBreakdown>[
      CompetitionPayoutBreakdown(place: 1, percent: 0.65, amount: 0),
      CompetitionPayoutBreakdown(place: 2, percent: 0.35, amount: 0),
    ],
    rulesSummary:
        'Skill cup advancement follows verified head-to-head results. Entries lock before the first scoring window begins. Entry fees move into secure escrow until results settle.',
    joinEligibility: CompetitionJoinEligibility(
      eligible: false,
      reason: 'competition_not_open',
    ),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 3, 11, 13),
    updatedAt: DateTime.utc(2026, 3, 11, 13, 5),
  ),
];

final Map<String, Set<String>> _seedParticipantIds = <String, Set<String>>{
  'ugc-101': <String>{
    'alpha',
    'bravo',
    'charlie',
    'delta',
    'echo',
    'foxtrot',
    'golf',
    'hotel',
  },
  'ugc-102': <String>{
    'demo-user',
    'atlas',
    'nova',
    'zen',
    'drift',
    'sol',
    'flux',
    'cairo',
    'lyra',
    'rio',
    'luna',
    'mesh',
    'opal',
    'kite',
    'halo',
    'nile',
    'sterling',
    'ember',
    'echo',
    'iris',
    'glow',
    'onyx',
    'mica',
    'aero',
  },
  'ugc-103': <String>{'rookie1', 'rookie2', 'rookie3', 'rookie4', 'rookie5'},
  'ugc-104': <String>{
    'invite1',
    'invite2',
    'invite3',
    'invite4',
    'invite5',
    'invite6',
    'invite7',
    'invite8',
    'invite9',
    'invite10',
  },
  'ugc-105': <String>{
    'one',
    'two',
    'three',
    'four',
    'five',
    'six',
    'seven',
    'eight',
    'nine',
    'ten',
    'eleven',
    'twelve',
    'thirteen',
    'fourteen',
    'fifteen',
    'sixteen',
    'seventeen',
    'eighteen',
  },
  'ugc-106': <String>{'demo-user'},
};
