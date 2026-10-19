import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/owner_console/widgets/club_legacy_desk.dart';

class ShowroomExhibit {
  const ShowroomExhibit({
    required this.id,
    required this.name,
    required this.category,
    required this.ownershipLabel,
    required this.fallbackLabel,
    this.sku,
    this.price,
    this.supplyCap,
    this.mintedCount,
    this.modelFile,
    this.previewFile,
    this.owned = false,
  });

  factory ShowroomExhibit.fromJson(Map<String, dynamic> json) => ShowroomExhibit(
    id: '${json['id']}',
    name: '${json['name'] ?? 'Asset'}',
    category: '${json['category'] ?? 'watch'}',
    ownershipLabel: '${json['ownership_label'] ?? 'Not owned'}',
    fallbackLabel: '${json['fallback_label'] ?? 'Static card'}',
    sku: _text(json['sku']),
    price: _text(json['price']),
    supplyCap: json['supply_cap'] == null ? null : _int(json['supply_cap']),
    mintedCount: json['minted_count'] == null ? null : _int(json['minted_count']),
    modelFile: _text(json['model_file']),
    previewFile: _text(json['preview_file']),
    owned: json['owned'] == true,
  );

  final String id;
  final String name;
  final String category;
  final String ownershipLabel;
  final String fallbackLabel;
  final String? sku;
  final String? price;
  final int? supplyCap;
  final int? mintedCount;
  final String? modelFile;
  final String? previewFile;
  final bool owned;
}

double _num(Object? v) =>
    v is num ? v.toDouble() : double.tryParse('${v ?? ''}') ?? 0;

int _int(Object? v) => v is num ? v.toInt() : int.tryParse('${v ?? ''}') ?? 0;

String? _text(Object? v) {
  final String t = '${v ?? ''}'.trim();
  return t.isEmpty || t == 'null' ? null : t;
}

Map<String, dynamic> _map(Object? v) =>
    v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};

List<Map<String, dynamic>> _maps(Object? v) =>
    (v is List ? v : const <dynamic>[])
        .whereType<Map<dynamic, dynamic>>()
        .map((Map<dynamic, dynamic> m) => Map<String, dynamic>.from(m))
        .toList(growable: false);

class OwnerDecisionAction {
  const OwnerDecisionAction({required this.key, required this.label, this.style = 'ghost'});

  factory OwnerDecisionAction.fromJson(Map<String, dynamic> j) => OwnerDecisionAction(
    key: '${j['key']}',
    label: _text(j['label']) ?? '${j['key']}',
    style: _text(j['style']) ?? 'ghost',
  );

  final String key;
  final String label;
  final String style;

  bool get isPrimary => style == 'primary';
}

class OwnerInboxEntry {
  const OwnerInboxEntry({
    required this.id,
    required this.kind,
    required this.title,
    required this.isDecision,
    this.clubId,
    this.priority,
    this.why,
    this.what,
    this.sender,
    this.status,
    this.outcome,
    this.respondBy,
    this.actions = const <OwnerDecisionAction>[],
  });

  factory OwnerInboxEntry.fromJson(Map<String, dynamic> j) => OwnerInboxEntry(
    id: '${j['id']}',
    kind: _text(j['kind']) ?? 'update',
    title: _text(j['title']) ?? _text(j['what']) ?? 'Update',
    isDecision: j['is_decision'] == true,
    clubId: _text(j['club_id']),
    priority: _text(j['priority']),
    why: _text(j['why']) ?? _text(j['body']),
    what: _text(j['what']),
    sender: _text(j['sender']),
    status: _text(j['status']),
    outcome: _text(j['outcome']),
    respondBy: DateTime.tryParse(_text(j['respond_by']) ?? ''),
    actions: _maps(j['actions']).map(OwnerDecisionAction.fromJson).toList(),
  );

  final String id;
  final String kind;
  final String title;
  final bool isDecision;
  final String? clubId;
  final String? priority;
  final String? why;
  final String? what;
  final String? sender;
  final String? status;
  final String? outcome;
  final DateTime? respondBy;
  final List<OwnerDecisionAction> actions;
}

class PublicTrophy {
  const PublicTrophy({required this.competition, this.tier, this.position, this.year});

  factory PublicTrophy.fromJson(Map<String, dynamic> j) => PublicTrophy(
    competition: _text(j['competition']) ?? 'Honour',
    tier: _text(j['tier']),
    position: j['position'] == null ? null : _int(j['position']),
    year: j['year'] == null ? null : _int(j['year']),
  );

  final String competition;
  final String? tier;
  final int? position;
  final int? year;
}

/// Logged-out club card. Only the public allowlist is read.
class PublicClubCard {
  const PublicClubCard({
    required this.clubName,
    this.shortName,
    this.city,
    this.countryCode,
    this.primaryColor,
    this.secondaryColor,
    this.founded,
    this.crestUrl,
    this.trophies = const <PublicTrophy>[],
  });

  factory PublicClubCard.fromJson(Map<String, dynamic> j) => PublicClubCard(
    clubName: _text(j['club_name']) ?? 'Club',
    shortName: _text(j['short_name']),
    city: _text(j['city']),
    countryCode: _text(j['country_code']),
    primaryColor: _text(j['primary_color']),
    secondaryColor: _text(j['secondary_color']),
    founded: j['founded'] == null ? null : _int(j['founded']),
    crestUrl: _text(j['crest_url']),
    trophies: _maps(j['trophies']).map(PublicTrophy.fromJson).toList(),
  );

  final String clubName;
  final String? shortName;
  final String? city;
  final String? countryCode;
  final String? primaryColor;
  final String? secondaryColor;
  final int? founded;
  final String? crestUrl;
  final List<PublicTrophy> trophies;
}

class OwnerClubCard {
  const OwnerClubCard({
    required this.clubId,
    required this.name,
    required this.value,
    required this.valueTrend,
    this.shortName,
    this.competitionName,
    this.managerName,
    this.managerMood,
    this.countryCode,
    this.stage,
    this.worldDay = 0,
  });

  factory OwnerClubCard.fromJson(Map<String, dynamic> j) {
    final Map<String, dynamic> manager = _map(j['manager']);
    return OwnerClubCard(
      clubId: '${j['club_id']}',
      name: _text(j['club_name']) ?? 'Club',
      value: _num(j['value']),
      valueTrend: _num(j['value_trend']),
      shortName: _text(j['short_name']),
      competitionName: _text(_map(j['competition'])['name']),
      managerName: _text(manager['name']),
      managerMood: manager['mood'] == null ? null : _int(manager['mood']),
      countryCode: _text(j['country_code']),
      stage: _text(j['stage']),
      worldDay: _int(j['world_day']),
    );
  }

  final String clubId;
  final String name;
  final double value;
  final double valueTrend;
  final String? shortName;
  final String? competitionName;
  final String? managerName;
  final int? managerMood;
  final String? countryCode;
  final String? stage;
  final int worldDay;
}

class OwnerClubHealth {
  const OwnerClubHealth({
    required this.clubId,
    required this.clubName,
    required this.cash,
    required this.squadSize,
    required this.squadDepth,
    required this.morale,
    required this.injuries,
    required this.fanEngagement,
  });

  factory OwnerClubHealth.fromJson(Map<String, dynamic> j) => OwnerClubHealth(
    clubId: '${j['club_id']}',
    clubName: _text(j['club_name']) ?? 'Club',
    cash: _num(j['cash']),
    squadSize: _int(j['squad_size']),
    squadDepth: _text(j['squad_depth']) ?? '-',
    morale: _int(j['morale']),
    injuries: _int(j['injuries']),
    fanEngagement: _int(j['fan_engagement']),
  );

  final String clubId;
  final String clubName;
  final double cash;
  final int squadSize;
  final String squadDepth;
  final int morale;
  final int injuries;
  final int fanEngagement;
}

class OwnerFixture {
  const OwnerFixture({
    required this.id,
    required this.round,
    required this.homeName,
    required this.awayName,
    required this.status,
    this.homeClubId,
    this.awayClubId,
    this.homeGoals,
    this.awayGoals,
  });

  factory OwnerFixture.fromJson(Map<String, dynamic> j) => OwnerFixture(
    id: '${j['id']}',
    round: _int(j['round']),
    homeName: _text(j['home_name']) ?? 'Home',
    awayName: _text(j['away_name']) ?? 'Away',
    status: _text(j['status']) ?? 'scheduled',
    homeClubId: _text(j['home_club_id']),
    awayClubId: _text(j['away_club_id']),
    homeGoals: j['home_goals'] == null ? null : _int(j['home_goals']),
    awayGoals: j['away_goals'] == null ? null : _int(j['away_goals']),
  );

  final String id;
  final int round;
  final String homeName;
  final String awayName;
  final String status;
  final String? homeClubId;
  final String? awayClubId;
  final int? homeGoals;
  final int? awayGoals;

  bool involves(String? clubId) =>
      clubId == null || homeClubId == clubId || awayClubId == clubId;
}

class OwnerStandingRow {
  const OwnerStandingRow({
    required this.clubId,
    required this.clubName,
    required this.played,
    required this.won,
    required this.drawn,
    required this.lost,
    required this.points,
  });

  factory OwnerStandingRow.fromJson(Map<String, dynamic> j) => OwnerStandingRow(
    clubId: '${j['club_id']}',
    clubName: _text(j['club_name']) ?? 'Club',
    played: _int(j['played']),
    won: _int(j['won']),
    drawn: _int(j['drawn']),
    lost: _int(j['lost']),
    points: _int(j['points']),
  );

  final String clubId;
  final String clubName;
  final int played;
  final int won;
  final int drawn;
  final int lost;
  final int points;
}

class OwnerBoardTable {
  const OwnerBoardTable({required this.competitionName, required this.rows});

  factory OwnerBoardTable.fromJson(Map<String, dynamic> j) => OwnerBoardTable(
    competitionName:
        _text(_map(j['competition'])['name']) ?? 'Competition',
    rows: _maps(j['standings']).map(OwnerStandingRow.fromJson).toList(),
  );

  final String competitionName;
  final List<OwnerStandingRow> rows;
}

class OwnerControlCenter {
  const OwnerControlCenter({
    required this.displayName,
    required this.role,
    required this.clubs,
    required this.maxClubs,
    required this.decisions,
    required this.inbox,
    required this.inboxOpenCount,
    required this.health,
    required this.upcoming,
    required this.recent,
    required this.board,
    required this.clubCashTotal,
    required this.withdrawable,
    required this.pendingPayouts,
    required this.earnings,
    required this.integrityScore,
    this.legacy = const <OwnerLegacyRating>[],
  });

  factory OwnerControlCenter.fromJson(Map<String, dynamic> j) {
    final Map<String, dynamic> user = _map(j['user']);
    final Map<String, dynamic> fixtures = _map(j['fixtures']);
    final Map<String, dynamic> economy = _map(j['economy']);
    return OwnerControlCenter(
      displayName:
          _text(user['display_name']) ?? _text(user['username']) ?? 'Owner',
      role: _text(user['role']) ?? 'user',
      clubs: _maps(j['clubs']).map(OwnerClubCard.fromJson).toList(),
      maxClubs: _int(j['max_clubs']),
      decisions: _maps(j['decisions']).map(OwnerInboxEntry.fromJson).toList(),
      inbox: _maps(j['inbox']).map(OwnerInboxEntry.fromJson).toList(),
      inboxOpenCount: _int(j['inbox_open_count']),
      health: _maps(j['health']).map(OwnerClubHealth.fromJson).toList(),
      upcoming: _maps(fixtures['upcoming']).map(OwnerFixture.fromJson).toList(),
      recent: _maps(fixtures['recent']).map(OwnerFixture.fromJson).toList(),
      board: _maps(j['board']).map(OwnerBoardTable.fromJson).toList(),
      clubCashTotal: _num(economy['club_cash_total']),
      withdrawable: _num(_map(economy['wallet'])['withdrawable']),
      pendingPayouts: _num(economy['pending_payouts']),
      earnings: _map(economy['earnings_sources']).map(
        (String k, dynamic v) => MapEntry<String, double>(k, _num(v)),
      ),
      integrityScore: _int(_map(j['integrity'])['score']),
      legacy: j['legacy'] is List
          ? _maps(j['legacy']).map(OwnerLegacyRating.fromJson).toList()
          : const <OwnerLegacyRating>[],
    );
  }

  final String displayName;
  final String role;
  final List<OwnerClubCard> clubs;
  final int maxClubs;
  final List<OwnerInboxEntry> decisions;
  final List<OwnerInboxEntry> inbox;
  final int inboxOpenCount;
  final List<OwnerClubHealth> health;
  final List<OwnerFixture> upcoming;
  final List<OwnerFixture> recent;
  final List<OwnerBoardTable> board;
  final double clubCashTotal;
  final double withdrawable;
  final double pendingPayouts;
  final Map<String, double> earnings;
  final int integrityScore;
  final List<OwnerLegacyRating> legacy;
}

class OwnerLegacyRating {
  const OwnerLegacyRating({
    required this.clubId,
    required this.prestige,
    required this.development,
    required this.financialStrength,
    this.continentName,
  });

  factory OwnerLegacyRating.fromJson(Map<String, dynamic> j) => OwnerLegacyRating(
    clubId: '${j['club_id']}',
    prestige: _int(j['prestige']),
    development: _int(j['development']),
    financialStrength: _int(j['financial_strength']),
    continentName: _text(j['continent_name']),
  );

  final String clubId;
  final int prestige;
  final int development;
  final int financialStrength;
  final String? continentName;
}

class OwnerNationalCompetition {
  const OwnerNationalCompetition({
    required this.id,
    required this.title,
    required this.status,
  });

  factory OwnerNationalCompetition.fromJson(Map<String, dynamic> j) =>
      OwnerNationalCompetition(
        id: '${j['id']}',
        title: _text(j['title']) ?? _text(j['key']) ?? 'Tournament',
        status: _text(j['status']) ?? '',
      );

  final String id;
  final String title;
  final String status;
}

class OwnerNationalEntry {
  const OwnerNationalEntry({
    required this.id,
    required this.competitionId,
    required this.countryCode,
    required this.countryName,
  });

  factory OwnerNationalEntry.fromJson(Map<String, dynamic> j) =>
      OwnerNationalEntry(
        id: '${j['id']}',
        competitionId: '${j['competition_id']}',
        countryCode: _text(j['country_code']) ?? '',
        countryName: _text(j['country_name']) ?? 'Nation',
      );

  final String id;
  final String competitionId;
  final String countryCode;
  final String countryName;
}

class OwnerSquadMember {
  const OwnerSquadMember({
    required this.playerId,
    required this.name,
    required this.rating,
    required this.source,
  });

  factory OwnerSquadMember.fromJson(Map<String, dynamic> j) => OwnerSquadMember(
    playerId: '${j['player_id']}',
    name: _text(j['player_name']) ?? 'Player',
    rating: _int(j['overall_rating'] ?? j['rating']),
    source: _text(j['source_type']) ?? _text(j['assigned_slot']) ?? '',
  );

  final String playerId;
  final String name;
  final int rating;
  final String source;
}

class OwnerNationalSquad {
  const OwnerNationalSquad({
    required this.countryName,
    required this.minimumSquadSize,
    required this.members,
  });

  factory OwnerNationalSquad.fromJson(Map<String, dynamic> j) =>
      OwnerNationalSquad(
        countryName: _text(j['country_name']) ?? 'Nation',
        minimumSquadSize: _int(j['minimum_squad_size']),
        members:
            _maps(j['rental_squad_members']).map(OwnerSquadMember.fromJson).toList(),
      );

  final String countryName;
  final int minimumSquadSize;
  final List<OwnerSquadMember> members;
}

class OwnerAutoBuildPlan {
  const OwnerAutoBuildPlan({
    required this.formation,
    required this.selectedCount,
    required this.squadSize,
    required this.totalCost,
    required this.remainingBudget,
    required this.players,
  });

  factory OwnerAutoBuildPlan.fromJson(Map<String, dynamic> j) =>
      OwnerAutoBuildPlan(
        formation: _text(j['formation']) ?? '-',
        selectedCount: _int(j['selected_count']),
        squadSize: _int(j['squad_size']),
        totalCost: _num(j['total_cost_coin']),
        remainingBudget: _num(j['remaining_budget_coin']),
        players: _maps(j['players']).map(OwnerSquadMember.fromJson).toList(),
      );

  final String formation;
  final int selectedCount;
  final int squadSize;
  final double totalCost;
  final double remainingBudget;
  final List<OwnerSquadMember> players;
}

class OwnerWithdrawalReview {
  const OwnerWithdrawalReview({
    required this.id,
    required this.userId,
    required this.amountCoin,
    required this.amountNgn,
    required this.bankName,
    required this.accountLast4,
    required this.accountName,
    required this.status,
    this.createdAt,
    this.risk,
  });

  factory OwnerWithdrawalReview.fromJson(Map<String, dynamic> j) => OwnerWithdrawalReview(
    id: '${j['id']}',
    userId: '${j['user_id']}',
    amountCoin: _num(j['amount_coin']),
    amountNgn: _num(j['amount_ngn']),
    bankName: _text(j['bank_name']) ?? '-',
    accountLast4: _text(j['account_last4']) ?? '----',
    accountName: _text(j['account_name']) ?? '-',
    status: _text(j['status']) ?? 'pending_review',
    createdAt: _text(j['created_at']),
    risk: _text(_map(j['checks'])['risk']),
  );

  final String id;
  final String userId;
  final double amountCoin;
  final double amountNgn;
  final String bankName;
  final String accountLast4;
  final String accountName;
  final String status;
  final String? createdAt;
  final String? risk;
}

class OwnerRiskFlag {
  const OwnerRiskFlag({
    required this.id,
    required this.flagType,
    required this.severity,
    required this.scoreImpact,
    this.userId,
    this.clubId,
    this.detail,
  });

  factory OwnerRiskFlag.fromJson(Map<String, dynamic> j) => OwnerRiskFlag(
    id: '${j['id']}',
    flagType: _text(j['flag_type']) ?? 'flag',
    severity: _text(j['severity']) ?? 'low',
    scoreImpact: _int(j['score_impact']),
    userId: _text(j['user_id']),
    clubId: _text(j['club_id']),
    detail: _text(j['detail']),
  );

  final String id;
  final String flagType;
  final String severity;
  final int scoreImpact;
  final String? userId;
  final String? clubId;
  final String? detail;
}

class OwnerHeldPayout {
  const OwnerHeldPayout({
    required this.id,
    required this.eventType,
    required this.netAmount,
    required this.currency,
    this.clubId,
    this.memo,
  });

  factory OwnerHeldPayout.fromJson(Map<String, dynamic> j) => OwnerHeldPayout(
    id: '${j['id']}',
    eventType: _text(j['event_type']) ?? 'payout',
    netAmount: _num(j['net_amount']),
    currency: _text(j['currency']) ?? 'GTX',
    clubId: _text(j['club_id']),
    memo: _text(j['memo']),
  );

  final String id;
  final String eventType;
  final double netAmount;
  final String currency;
  final String? clubId;
  final String? memo;
}

class OwnerReviewQueue {
  const OwnerReviewQueue({required this.withdrawals, required this.flags, required this.heldPayouts});

  factory OwnerReviewQueue.fromJson(Map<String, dynamic> j) => OwnerReviewQueue(
    withdrawals: _maps(j['withdrawals']).map(OwnerWithdrawalReview.fromJson).toList(),
    flags: _maps(j['flags']).map(OwnerRiskFlag.fromJson).toList(),
    heldPayouts: _maps(j['held_payouts']).map(OwnerHeldPayout.fromJson).toList(),
  );

  final List<OwnerWithdrawalReview> withdrawals;
  final List<OwnerRiskFlag> flags;
  final List<OwnerHeldPayout> heldPayouts;
}

/// Owner Console reads on the existing GTEX backend
/// (`/owner/control-center`, `/owner/inbox`, `/owner/admin/*`, `/national-team-engine/*`).
abstract class OwnerConsoleReader {
  Future<OwnerControlCenter> fetchControlCenter();

  /// Creates and starts the caller's first club, then opens today's decisions.
  Future<void> claimClub({String? city, String? country});

  /// Resolves a Today's Decisions item with one of its own action keys.
  Future<OwnerInboxEntry> decide(String itemId, String action);

  Future<OwnerReviewQueue> fetchReviewQueue();

  Future<void> reviewWithdrawal(String withdrawalId, String decision, {String? note});

  Future<void> decideFlag(String flagId, String decision);

  Future<void> releasePayout(String eventId);

  Future<List<OwnerNationalCompetition>> fetchNationalCompetitions();

  Future<List<OwnerNationalEntry>> fetchManagedEntries();

  Future<OwnerNationalSquad> fetchSquad(String entryId);

  /// Suggestion only - nothing is rented or charged.
  Future<OwnerAutoBuildPlan> suggestSquad({
    required String competitionId,
    required String countryCode,
    required double budgetCoin,
  });

  Future<void> seedDefaultTournaments();

  Future<double> fetchWalletBalance();

  Future<List<ShowroomExhibit>> fetchShowroom({String? clubId});

  Future<ClubLegacyDeskData> fetchDesk({String? clubId});

  Future<void> performDesk(String action, [Map<String, Object?> payload = const <String, Object?>{}, String? clubId]);
}

class OwnerConsoleApi implements OwnerConsoleReader {
  const OwnerConsoleApi({required this.client});

  final GteAuthedApi client;

  @override
  Future<OwnerControlCenter> fetchControlCenter() async =>
      OwnerControlCenter.fromJson(await client.getMap('/owner/control-center'));

  @override
  Future<void> claimClub({String? city, String? country}) async {
    await client.post(
      '/owner/clubs/claim',
      body: <String, Object?>{
        if (city != null && city.trim().isNotEmpty) 'city_name': city.trim(),
        if (country != null && country.trim().isNotEmpty) 'country_code': country.trim(),
      },
    );
  }

  @override
  Future<OwnerInboxEntry> decide(String itemId, String action) async =>
      OwnerInboxEntry.fromJson(
        _map(await client.post('/owner/inbox/$itemId/decide', body: <String, Object?>{'action': action})),
      );

  @override
  Future<OwnerReviewQueue> fetchReviewQueue() async =>
      OwnerReviewQueue.fromJson(await client.getMap('/owner/admin/review-queue'));

  @override
  Future<void> reviewWithdrawal(String withdrawalId, String decision, {String? note}) async {
    await client.post(
      '/owner/admin/withdrawals/$withdrawalId/review',
      body: <String, Object?>{'decision': decision, if (note != null && note.isNotEmpty) 'note': note},
    );
  }

  @override
  Future<void> decideFlag(String flagId, String decision) async {
    await client.post('/owner/admin/flags/$flagId/$decision');
  }

  @override
  Future<void> releasePayout(String eventId) async {
    await client.post('/owner/admin/payouts/$eventId/release');
  }

  @override
  Future<List<OwnerNationalCompetition>> fetchNationalCompetitions() async =>
      _maps(
        await client.getList('/national-team-engine/competitions'),
      ).map(OwnerNationalCompetition.fromJson).toList();

  @override
  Future<List<OwnerNationalEntry>> fetchManagedEntries() async => _maps(
    (await client.getMap('/national-team-engine/me/history'))['managed_entries'],
  ).map(OwnerNationalEntry.fromJson).toList();

  @override
  Future<OwnerNationalSquad> fetchSquad(String entryId) async =>
      OwnerNationalSquad.fromJson(
        await client.getMap('/national-team-engine/entries/$entryId'),
      );

  @override
  Future<OwnerAutoBuildPlan> suggestSquad({
    required String competitionId,
    required String countryCode,
    required double budgetCoin,
  }) async => OwnerAutoBuildPlan.fromJson(
    _map(
      await client.post(
        '/national-team-engine/competitions/$competitionId/auto-build-squad',
        body: <String, Object?>{
          'country_code': countryCode,
          'budget_coin': budgetCoin,
        },
      ),
    ),
  );

  @override
  Future<double> fetchWalletBalance() async =>
      _num((await client.getMap('/wallets/summary'))['available_balance']);

  Future<PublicClubCard> fetchPublicShowroom(String code) async =>
      PublicClubCard.fromJson(await client.getMap('/owner/public/showroom/$code', auth: false));

  @override
  Future<List<ShowroomExhibit>> fetchShowroom({String? clubId}) async {
    final String targetClubId;
    if (clubId != null && clubId.trim().isNotEmpty) {
      targetClubId = clubId.trim();
    } else {
      final Map<String, dynamic> center = await client.getMap('/owner/control-center');
      final List<Map<String, dynamic>> clubs = _maps(center['clubs']);
      if (clubs.isEmpty) {
        return const <ShowroomExhibit>[];
      }
      targetClubId = '${clubs.first['club_id']}';
    }
    final Map<String, dynamic> room = await client.getMap('/owner/legacy/$targetClubId/showroom');
    return _maps(room['exhibits']).map(ShowroomExhibit.fromJson).toList();
  }

  @override
  Future<ClubLegacyDeskData> fetchDesk({String? clubId}) async {
    final String targetClubId;
    if (clubId != null && clubId.trim().isNotEmpty) {
      targetClubId = clubId.trim();
    } else {
      final Map<String, dynamic> center = await client.getMap('/owner/control-center');
      final List<Map<String, dynamic>> clubs = _maps(center['clubs']);
      if (clubs.isEmpty) {
        return ClubLegacyDeskData.fromJson(const <String, dynamic>{});
      }
      targetClubId = '${clubs.first['club_id']}';
    }
    return ClubLegacyDeskData.fromJson(await client.getMap('/owner/legacy/$targetClubId/desk'));
  }

  @override
  Future<void> performDesk(String action, [Map<String, Object?> payload = const <String, Object?>{}, String? clubId]) async {
    final String targetClubId;
    if (clubId != null && clubId.trim().isNotEmpty) {
      targetClubId = clubId.trim();
    } else {
      final Map<String, dynamic> center = await client.getMap('/owner/control-center');
      final List<Map<String, dynamic>> clubs = _maps(center['clubs']);
      if (clubs.isEmpty) {
        return;
      }
      targetClubId = '${clubs.first['club_id']}';
    }
    final Map<String, Object?> body = <String, Object?>{..._deskPayload(action), ...payload};
    await client.post('/owner/legacy/$targetClubId/desk', body: <String, Object?>{'action': action, 'payload': body});
  }

  @override
  Map<String, Object?> _deskPayload(String action) {
    return switch (action) {
      'hire' => <String, Object?>{'role': 'gm', 'name': 'Ada Okonkwo', 'personality': 'cautious', 'wage': '4000'},
      'preset' => <String, Object?>{'preset': 'balanced'},
      'sponsor' => <String, Object?>{'sponsor_name': 'Harbour Trust', 'placement': 'front', 'fee': '1000'},
      'manager' => <String, Object?>{'candidate_name': 'Tunde Bakare', 'wage': '2000', 'prestige': 20, 'ambition': 8, 'seed': 3},
      'case' => <String, Object?>{'rule_code': 'late_wages', 'allegation': 'Wages slipped', 'evidence': 'Ledger'},
      'list_auction' => <String, Object?>{'price': '1500'},
      'place_bid' => <String, Object?>{'amount': '2000'},
      'purchase' => <String, Object?>{'owner_class': 'club'},
      'gift' => <String, Object?>{},
      _ => <String, Object?>{},
    };
  }

  @override
  Future<void> seedDefaultTournaments() async {
    await client.post('/admin/national-team-engine/competitions/seed-defaults');
  }
}
