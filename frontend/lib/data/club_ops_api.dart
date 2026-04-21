import 'package:gte_frontend/data/club_ops_fixtures.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/shared/auth/auth_identity_store.dart';
import 'package:gte_frontend/models/academy_models.dart';
import 'package:gte_frontend/models/club_finance_models.dart';
import 'package:gte_frontend/models/player_avatar.dart';
import 'package:gte_frontend/models/scouting_models.dart';
import 'package:gte_frontend/models/sponsorship_models.dart';

class ClubOpsApi {
  ClubOpsApi._({
    required this.config,
    required this.transport,
    required this.latency,
    required this.accessToken,
    required this.authSessionStore,
  });

  final GteRepositoryConfig config;
  final GteTransport transport;
  final Duration latency;
  final String? accessToken;
  final AuthSessionStore? authSessionStore;

  factory ClubOpsApi.standard({
    required String baseUrl,
    GteBackendMode mode = GteBackendMode.live,
    String? accessToken,
    AuthSessionStore? authSessionStore,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    return ClubOpsApi._(
      config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
      transport: GteHttpTransport(),
      latency: const Duration(milliseconds: 200),
      accessToken: accessToken,
      authSessionStore: authSessionStore ?? SecureAuthSessionStore(),
    );
  }

  factory ClubOpsApi.fixture({
    String baseUrl = 'http://127.0.0.1:8000',
    Duration latency = Duration.zero,
  }) {
    return ClubOpsApi._(
      config: GteRepositoryConfig(
        baseUrl: baseUrl,
        mode: GteBackendMode.fixture,
      ),
      transport: _UnsupportedClubOpsTransport(),
      latency: latency,
      accessToken: null,
      authSessionStore: null,
    );
  }

  Future<ClubFinanceSnapshot> fetchFinance({
    required String clubId,
    String? clubName,
  }) {
    return _withFallback<ClubFinanceSnapshot>(
      () async => _parseFinance(
        _asMap(await _request('GET', '/api/clubs/$clubId/finances')),
        fallbackClubId: clubId,
        fallbackClubName: clubName,
      ),
      () async {
        await Future<void>.delayed(latency);
        return fixtureClubFinance(clubId, clubName);
      },
    );
  }

  Future<SponsorshipDashboard> fetchSponsorships({
    required String clubId,
    String? clubName,
  }) {
    return _withFallback<SponsorshipDashboard>(
      () async => _mergeSponsorships(
        overview: _asMap(
          await _request('GET', '/api/clubs/$clubId/sponsorships'),
        ),
        catalog: _asMap(
          await _request('GET', '/api/clubs/$clubId/sponsorships/catalog'),
        ),
        fallbackClubId: clubId,
        fallbackClubName: clubName,
      ),
      () async {
        await Future<void>.delayed(latency);
        return fixtureSponsorships(clubId, clubName);
      },
    );
  }

  Future<SponsorshipContract> createSponsorshipContract({
    required String clubId,
    required SponsorshipApplicationDraft draft,
    Map<String, String> packageNamesByCode = const <String, String>{},
  }) async {
    final Map<String, Object?> payload = _asMap(
      await _request(
        'POST',
        '/api/clubs/$clubId/sponsorships/contracts',
        body: draft.toJson(),
      ),
    );
    return _parseSponsorshipContract(
      payload,
      packageNamesByCode: packageNamesByCode,
    );
  }

  Future<SponsorshipContract> updateSponsorshipContract({
    required String clubId,
    required String contractId,
    required SponsorshipContractUpdateDraft draft,
    Map<String, String> packageNamesByCode = const <String, String>{},
  }) async {
    final Map<String, Object?> payload = _asMap(
      await _request(
        'PATCH',
        '/api/clubs/$clubId/sponsorships/contracts/$contractId',
        body: draft.toJson(),
      ),
    );
    return _parseSponsorshipContract(
      payload,
      packageNamesByCode: packageNamesByCode,
    );
  }

  Future<AcademyDashboard> fetchAcademy({
    required String clubId,
    String? clubName,
  }) {
    return _withFallback<AcademyDashboard>(
      () async => _parseAcademy(
        _asMap(await _request('GET', '/api/clubs/$clubId/academy')),
        fallbackClubId: clubId,
        fallbackClubName: clubName,
      ),
      () async {
        await Future<void>.delayed(latency);
        return fixtureAcademy(clubId, clubName);
      },
    );
  }

  Future<ScoutingDashboard> fetchScouting({
    required String clubId,
    String? clubName,
  }) {
    return _withFallback<ScoutingDashboard>(
      () async => _parseScouting(
        _asMap(await _request('GET', '/api/clubs/$clubId/scouting')),
        fallbackClubId: clubId,
        fallbackClubName: clubName,
      ),
      () async {
        await Future<void>.delayed(latency);
        return fixtureScouting(clubId, clubName);
      },
    );
  }

  Future<YouthPipelineSnapshot> fetchYouthPipeline({
    required String clubId,
    String? clubName,
  }) {
    return _withFallback<YouthPipelineSnapshot>(
      () async => _parseYouthPipeline(
        _asMap(await _request('GET', '/api/clubs/$clubId/youth-pipeline')),
      ),
      () async {
        await Future<void>.delayed(latency);
        return fixtureYouthPipeline(clubId, clubName);
      },
    );
  }

  Future<ClubOpsAdminSnapshot> fetchClubOpsAdmin() {
    return _withFallback<ClubOpsAdminSnapshot>(
      () async => _parseAdminSnapshot(
        _asMap(await _request('GET', '/api/admin/clubs/ops-summary')),
      ),
      () async {
        await Future<void>.delayed(latency);
        return fixtureClubOpsAdmin();
      },
    );
  }

  Future<ClubFinanceAnalyticsSnapshot> fetchFinanceAnalytics() {
    return _withFallback<ClubFinanceAnalyticsSnapshot>(
      () async => _parseFinanceAnalytics(
        _asMap(await _request('GET', '/api/admin/clubs/finance-analytics')),
      ),
      () async {
        await Future<void>.delayed(latency);
        return fixtureFinanceAnalytics();
      },
    );
  }

  Future<SponsorshipAnalyticsSnapshot> fetchSponsorshipAnalytics() {
    return _withFallback<SponsorshipAnalyticsSnapshot>(
      () async => _parseSponsorshipAnalytics(
        _asMap(await _request('GET', '/api/admin/clubs/sponsorship-analytics')),
      ),
      () async {
        await Future<void>.delayed(latency);
        return fixtureSponsorshipAnalytics();
      },
    );
  }

  Future<AcademyAnalyticsSnapshot> fetchAcademyAnalytics() {
    return _withFallback<AcademyAnalyticsSnapshot>(
      () async => _parseAcademyAnalytics(
        _asMap(await _request('GET', '/api/admin/clubs/academy-analytics')),
      ),
      () async {
        await Future<void>.delayed(latency);
        return fixtureAcademyAnalytics();
      },
    );
  }

  Future<ScoutingAnalyticsSnapshot> fetchScoutingAnalytics() {
    return _withFallback<ScoutingAnalyticsSnapshot>(
      () async => _parseScoutingAnalytics(
        _asMap(await _request('GET', '/api/admin/clubs/scouting-analytics')),
      ),
      () async {
        await Future<void>.delayed(latency);
        return fixtureScoutingAnalytics();
      },
    );
  }

  Future<T> _withFallback<T>(
    Future<T> Function() liveCall,
    Future<T> Function() fixtureCall,
  ) async {
    if (config.mode == GteBackendMode.fixture) {
      return fixtureCall();
    }
    return liveCall();
  }

  Future<Object?> _request(
    String method,
    String path, {
    Map<String, Object?> query = const <String, Object?>{},
    Object? body,
  }) async {
    try {
      final String? resolvedAccessToken = await _readAccessToken();
      final Map<String, String> headers = <String, String>{
        'Accept': 'application/json',
      };
      if (body != null) {
        headers['Content-Type'] = 'application/json';
      }
      if (resolvedAccessToken != null &&
          resolvedAccessToken.trim().isNotEmpty) {
        headers['Authorization'] = 'Bearer ${resolvedAccessToken.trim()}';
      }
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
          type: _errorTypeFromStatus(response.statusCode),
          message: _errorMessage(response.body),
          statusCode: response.statusCode,
          cause: response.body,
        );
      }
      return gteApiSuccessPayload(response.body);
    } on GteApiException {
      rethrow;
    } catch (error) {
      throw GteApiException(
        type: GteApiErrorType.network,
        message: 'Unable to reach the club operations backend.',
        cause: error,
      );
    }
  }

  Future<String?> _readAccessToken() async {
    final String direct = accessToken?.trim() ?? '';
    if (direct.isNotEmpty) {
      return direct;
    }
    final AuthSessionStore? store = authSessionStore;
    if (store == null) {
      return null;
    }
    try {
      final session = await store.readSession();
      final String resolved = session?.accessToken.trim() ?? '';
      return resolved.isEmpty ? null : resolved;
    } catch (_) {
      return null;
    }
  }

  ClubFinanceSnapshot _parseFinance(
    Map<String, Object?> json, {
    required String fallbackClubId,
    String? fallbackClubName,
  }) {
    if (!json.containsKey('balance_summary') &&
        !json.containsKey('budget_allocations') &&
        !json.containsKey('ledger_entries')) {
      throw const GteParsingException(
        'Finance payload missing summary fields.',
      );
    }
    final Map<String, Object?> balance = _asMap(
      json['balance_summary'] ?? json['summary'],
    );
    return ClubFinanceSnapshot(
      clubId: _string(json, <String>['club_id', 'clubId'], fallbackClubId),
      clubName: _string(json, <String>[
        'club_name',
        'clubName',
      ], fallbackClubName ?? clubOpsDisplayClubName(fallbackClubId)),
      balanceSummary: ClubBalanceSummary(
        currentBalance: _number(balance, <String>[
          'current_balance',
          'currentBalance',
        ], 0),
        operatingBudget: _number(balance, <String>[
          'operating_budget',
          'operatingBudget',
        ], 0),
        reserveTarget: _number(balance, <String>[
          'reserve_target',
          'reserveTarget',
        ], 0),
        monthlyIncome: _number(balance, <String>[
          'monthly_income',
          'monthlyIncome',
        ], 0),
        monthlyExpenses: _number(balance, <String>[
          'monthly_expenses',
          'monthlyExpenses',
        ], 0),
        payrollCommitment: _number(balance, <String>[
          'payroll_commitment',
          'payrollCommitment',
        ], 0),
        nextPayrollDate: _dateTime(balance, <String>[
          'next_payroll_date',
          'nextPayrollDate',
        ], DateTime.utc(2026, 3, 25)),
        nextPayrollAmount: _number(balance, <String>[
          'next_payroll_amount',
          'nextPayrollAmount',
        ], 0),
        cashRunwayMonths: _number(balance, <String>[
          'cash_runway_months',
          'cashRunwayMonths',
        ], 0),
        balanceDeltaPercent: _number(balance, <String>[
          'balance_delta_percent',
          'balanceDeltaPercent',
        ], 0),
      ),
      budgetAllocations: _categoryList(
        json['budget_allocations'] ?? json['budgetAllocation'],
      ),
      incomeBreakdown: _categoryList(
        json['income_breakdown'] ?? json['incomeBreakdown'],
      ),
      expenseBreakdown: _categoryList(
        json['expense_breakdown'] ?? json['expenseBreakdown'],
      ),
      cashflow: _cashflowList(json['cashflow']),
      ledgerEntries: _ledgerList(json['ledger_entries'] ?? json['ledger']),
      financeNotes: _stringList(json['finance_notes'] ?? json['notes']),
    );
  }

  SponsorshipDashboard _mergeSponsorships({
    required Map<String, Object?> overview,
    required Map<String, Object?> catalog,
    required String fallbackClubId,
    String? fallbackClubName,
  }) {
    if (!overview.containsKey('contracts') &&
        !overview.containsKey('visible_assets')) {
      throw const GteParsingException(
        'Sponsorship overview payload missing contracts and assets.',
      );
    }
    if (!catalog.containsKey('packages')) {
      throw const GteParsingException(
        'Sponsorship catalog payload missing packages.',
      );
    }
    final List<SponsorshipPackage> packages = _packageList(catalog['packages']);
    final Map<String, String> packageNamesByCode = <String, String>{
      for (final SponsorshipPackage package in packages)
        package.code: package.name,
    };
    final List<SponsorshipContract> contracts = _contractList(
      overview['contracts'],
      packageNamesByCode: packageNamesByCode,
    );
    return SponsorshipDashboard(
      clubId: _string(overview, <String>['club_id', 'clubId'], fallbackClubId),
      clubName: _string(overview, <String>[
        'club_name',
        'clubName',
      ], fallbackClubName ?? clubOpsDisplayClubName(fallbackClubId)),
      activeContractValue: contracts
          .where(
            (SponsorshipContract contract) =>
                contract.status == SponsorshipContractStatus.active,
          )
          .fold<double>(
            0,
            (double total, SponsorshipContract contract) =>
                total + contract.totalValue,
          ),
      activeContractCount: _integer(
        overview,
        <String>['active_contract_count', 'activeContractCount'],
        contracts
            .where(
              (SponsorshipContract contract) =>
                  contract.status == SponsorshipContractStatus.active,
            )
            .length,
      ),
      settledRevenue: _minorToMajor(
        _integer(overview, <String>[
          'total_settled_revenue_minor',
          'totalSettledRevenueMinor',
        ], 0),
      ),
      packages: packages,
      contracts: contracts,
      assetSlots: _assetSlotList(
        overview['visible_assets'] ??
            overview['asset_slots'] ??
            overview['assetSlots'],
      ),
      notes: _stringList(overview['notes']),
    );
  }

  AcademyDashboard _parseAcademy(
    Map<String, Object?> json, {
    required String fallbackClubId,
    String? fallbackClubName,
  }) {
    if (!json.containsKey('pathway_summary') &&
        !json.containsKey('programs') &&
        !json.containsKey('players')) {
      throw const GteParsingException(
        'Academy payload missing pathway summary fields.',
      );
    }
    final Map<String, Object?> pathway = _asMap(
      json['pathway_summary'] ?? json['summary'],
    );
    return AcademyDashboard(
      clubId: _string(json, <String>['club_id', 'clubId'], fallbackClubId),
      clubName: _string(json, <String>[
        'club_name',
        'clubName',
      ], fallbackClubName ?? clubOpsDisplayClubName(fallbackClubId)),
      pathwaySummary: AcademyPathwaySummary(
        developmentBudget: _number(pathway, <String>[
          'development_budget',
          'developmentBudget',
        ], 0),
        squadSize: _integer(pathway, <String>['squad_size', 'squadSize'], 0),
        promotionsThisSeason: _integer(pathway, <String>[
          'promotions_this_season',
          'promotionsThisSeason',
        ], 0),
        graduationRatePercent: _number(pathway, <String>[
          'graduation_rate_percent',
          'graduationRatePercent',
        ], 0),
        staffCoverageLabel: _string(pathway, <String>[
          'staff_coverage_label',
          'staffCoverageLabel',
        ], 'Full-time multidisciplinary team'),
        facilityLabel: _string(pathway, <String>[
          'facility_label',
          'facilityLabel',
        ], 'Regional performance centre'),
      ),
      programs: _academyProgramList(json['programs']),
      players: _academyPlayerList(json['players']),
      trainingCycles: _trainingCycleList(
        json['training_cycles'] ?? json['trainingCycles'],
      ),
      promotions: _academyPromotionList(json['promotions']),
      notes: _stringList(json['notes']),
    );
  }

  ScoutingDashboard _parseScouting(
    Map<String, Object?> json, {
    required String fallbackClubId,
    String? fallbackClubName,
  }) {
    if (!json.containsKey('assignments') &&
        !json.containsKey('prospects') &&
        !json.containsKey('reports')) {
      throw const GteParsingException(
        'Scouting payload missing assignment and prospect fields.',
      );
    }
    return ScoutingDashboard(
      clubId: _string(json, <String>['club_id', 'clubId'], fallbackClubId),
      clubName: _string(json, <String>[
        'club_name',
        'clubName',
      ], fallbackClubName ?? clubOpsDisplayClubName(fallbackClubId)),
      openAssignments: _integer(json, <String>[
        'open_assignments',
        'openAssignments',
      ], 0),
      activeRegions: _integer(json, <String>[
        'active_regions',
        'activeRegions',
      ], 0),
      liveProspects: _integer(json, <String>[
        'live_prospects',
        'liveProspects',
      ], 0),
      trialsScheduled: _integer(json, <String>[
        'trials_scheduled',
        'trialsScheduled',
      ], 0),
      assignments: _assignmentList(json['assignments']),
      prospects: _prospectList(json['prospects']),
      reports: _reportList(json['reports']),
      notes: _stringList(json['notes']),
    );
  }

  YouthPipelineSnapshot _parseYouthPipeline(Map<String, Object?> json) {
    if (!json.containsKey('stages') &&
        !json.containsKey('tracked_prospects') &&
        !json.containsKey('trackedProspects')) {
      throw const GteParsingException('Youth pipeline payload missing stages.');
    }
    return YouthPipelineSnapshot(
      trackedProspects: _integer(json, <String>[
        'tracked_prospects',
        'trackedProspects',
      ], 0),
      shortlistedProspects: _integer(json, <String>[
        'shortlisted_prospects',
        'shortlistedProspects',
      ], 0),
      trialists: _integer(json, <String>['trialists'], 0),
      scholarshipOffers: _integer(json, <String>[
        'scholarship_offers',
        'scholarshipOffers',
      ], 0),
      promotedPlayers: _integer(json, <String>[
        'promoted_players',
        'promotedPlayers',
      ], 0),
      conversionPercent: _number(json, <String>[
        'conversion_percent',
        'conversionPercent',
      ], 0),
      stages: _pipelineStages(json['stages']),
      notes: _stringList(json['notes']),
    );
  }

  ClubOpsAdminSnapshot _parseAdminSnapshot(Map<String, Object?> json) {
    if (!json.containsKey('clubs_monitored') &&
        !json.containsKey('clubsMonitored')) {
      throw const GteParsingException(
        'Club ops admin payload missing summary.',
      );
    }
    return ClubOpsAdminSnapshot(
      clubsMonitored: _integer(json, <String>[
        'clubs_monitored',
        'clubsMonitored',
      ], 0),
      totalOperatingBudget: _number(json, <String>[
        'total_operating_budget',
        'totalOperatingBudget',
      ], 0),
      activeContracts: _integer(json, <String>[
        'active_contracts',
        'activeContracts',
      ], 0),
      academyPromotions: _integer(json, <String>[
        'academy_promotions',
        'academyPromotions',
      ], 0),
      activeAssignments: _integer(json, <String>[
        'active_assignments',
        'activeAssignments',
      ], 0),
      youthConversionPercent: _number(json, <String>[
        'youth_conversion_percent',
        'youthConversionPercent',
      ], 0),
      statusNotes: _stringList(
        json['status_notes'] ?? json['statusNotes'] ?? json['notes'],
      ),
    );
  }

  ClubFinanceAnalyticsSnapshot _parseFinanceAnalytics(
    Map<String, Object?> json,
  ) {
    if (!json.containsKey('average_monthly_balance') &&
        !json.containsKey('averageMonthlyBalance')) {
      throw const GteParsingException(
        'Finance analytics payload missing key metrics.',
      );
    }
    return ClubFinanceAnalyticsSnapshot(
      averageMonthlyBalance: _number(json, <String>[
        'average_monthly_balance',
        'averageMonthlyBalance',
      ], 0),
      operatingMarginPercent: _number(json, <String>[
        'operating_margin_percent',
        'operatingMarginPercent',
      ], 0),
      payrollSharePercent: _number(json, <String>[
        'payroll_share_percent',
        'payrollSharePercent',
      ], 0),
      developmentSharePercent: _number(json, <String>[
        'development_share_percent',
        'developmentSharePercent',
      ], 0),
      commercialSharePercent: _number(json, <String>[
        'commercial_share_percent',
        'commercialSharePercent',
      ], 0),
      revenueReliabilityLabel: _string(json, <String>[
        'revenue_reliability_label',
        'revenueReliabilityLabel',
      ], 'Stable renewals and matchday collections'),
      topExpenseLabel: _string(json, <String>[
        'top_expense_label',
        'topExpenseLabel',
      ], 'Payroll'),
      categoryMix: _categoryList(json['category_mix'] ?? json['categoryMix']),
      quarterlyCashflow: _cashflowList(
        json['quarterly_cashflow'] ?? json['quarterlyCashflow'],
      ),
    );
  }

  SponsorshipAnalyticsSnapshot _parseSponsorshipAnalytics(
    Map<String, Object?> json,
  ) {
    if (!json.containsKey('total_revenue') &&
        !json.containsKey('totalRevenue')) {
      throw const GteParsingException(
        'Sponsorship analytics payload missing revenue totals.',
      );
    }
    return SponsorshipAnalyticsSnapshot(
      totalRevenue: _number(json, <String>['total_revenue', 'totalRevenue'], 0),
      averageContractValue: _number(json, <String>[
        'average_contract_value',
        'averageContractValue',
      ], 0),
      renewalRatePercent: _number(json, <String>[
        'renewal_rate_percent',
        'renewalRatePercent',
      ], 0),
      assetUtilizationPercent: _number(json, <String>[
        'asset_utilization_percent',
        'assetUtilizationPercent',
      ], 0),
      pendingReviews: _integer(json, <String>[
        'pending_reviews',
        'pendingReviews',
      ], 0),
      flaggedAssets: _integer(json, <String>[
        'flagged_assets',
        'flaggedAssets',
      ], 0),
      topContracts: _contractList(
        json['top_contracts'] ?? json['topContracts'],
      ),
      reviewQueue: _assetSlotList(json['review_queue'] ?? json['reviewQueue']),
    );
  }

  AcademyAnalyticsSnapshot _parseAcademyAnalytics(Map<String, Object?> json) {
    if (!json.containsKey('conversion_rate_percent') &&
        !json.containsKey('conversionRatePercent')) {
      throw const GteParsingException(
        'Academy analytics payload missing conversion metrics.',
      );
    }
    return AcademyAnalyticsSnapshot(
      conversionRatePercent: _number(json, <String>[
        'conversion_rate_percent',
        'conversionRatePercent',
      ], 0),
      retentionRatePercent: _number(json, <String>[
        'retention_rate_percent',
        'retentionRatePercent',
      ], 0),
      averageReadinessScore: _integer(json, <String>[
        'average_readiness_score',
        'averageReadinessScore',
      ], 0),
      promotionsThisSeason: _integer(json, <String>[
        'promotions_this_season',
        'promotionsThisSeason',
      ], 0),
      pathwayHealthLabel: _string(json, <String>[
        'pathway_health_label',
        'pathwayHealthLabel',
      ], 'Balanced intake and promotion cadence'),
      programMix: _academyProgramList(
        json['program_mix'] ?? json['programMix'],
      ),
    );
  }

  ScoutingAnalyticsSnapshot _parseScoutingAnalytics(Map<String, Object?> json) {
    if (!json.containsKey('assignment_completion_percent') &&
        !json.containsKey('assignmentCompletionPercent')) {
      throw const GteParsingException(
        'Scouting analytics payload missing funnel metrics.',
      );
    }
    return ScoutingAnalyticsSnapshot(
      assignmentCompletionPercent: _number(json, <String>[
        'assignment_completion_percent',
        'assignmentCompletionPercent',
      ], 0),
      regionalCoveragePercent: _number(json, <String>[
        'regional_coverage_percent',
        'regionalCoveragePercent',
      ], 0),
      shortlistToTrialPercent: _number(json, <String>[
        'shortlist_to_trial_percent',
        'shortlistToTrialPercent',
      ], 0),
      trialToScholarshipPercent: _number(json, <String>[
        'trial_to_scholarship_percent',
        'trialToScholarshipPercent',
      ], 0),
      youthConversionPercent: _number(json, <String>[
        'youth_conversion_percent',
        'youthConversionPercent',
      ], 0),
      funnel: _pipelineStages(json['funnel']),
      assignmentLoad: _assignmentList(
        json['assignment_load'] ?? json['assignmentLoad'],
      ),
    );
  }

  List<FinanceCategoryBreakdown> _categoryList(Object? value) {
    return _asList(value)
        .map((Object? item) {
          final Map<String, Object?> json = _asMap(item);
          return FinanceCategoryBreakdown(
            label: _string(json, <String>['label', 'name'], 'Unlabeled'),
            amount: _number(json, <String>['amount', 'value'], 0),
            sharePercent: _number(json, <String>[
              'share_percent',
              'sharePercent',
            ], 0),
            detail: _nullableString(json, <String>['detail', 'note']),
          );
        })
        .toList(growable: false);
  }

  List<CashflowPoint> _cashflowList(Object? value) {
    return _asList(value)
        .map((Object? item) {
          final Map<String, Object?> json = _asMap(item);
          return CashflowPoint(
            label: _string(json, <String>['label'], 'Window'),
            inflow: _number(json, <String>['inflow'], 0),
            outflow: _number(json, <String>['outflow'], 0),
            closingBalance: _number(json, <String>[
              'closing_balance',
              'closingBalance',
            ], 0),
          );
        })
        .toList(growable: false);
  }

  List<LedgerEntry> _ledgerList(Object? value) {
    return _asList(value)
        .map((Object? item) {
          final Map<String, Object?> json = _asMap(item);
          final String typeValue =
              _string(json, <String>['type'], 'expense').toLowerCase();
          return LedgerEntry(
            id: _string(json, <String>['id'], 'ledger'),
            title: _string(json, <String>['title'], 'Ledger entry'),
            category: _string(json, <String>['category'], 'General'),
            counterparty: _string(json, <String>[
              'counterparty',
            ], 'Club operations'),
            type:
                typeValue == 'income'
                    ? LedgerEntryType.income
                    : LedgerEntryType.expense,
            amount: _number(json, <String>['amount'], 0),
            runningBalance: _number(json, <String>[
              'running_balance',
              'runningBalance',
            ], 0),
            occurredAt: _dateTime(json, <String>[
              'occurred_at',
              'occurredAt',
            ], DateTime.utc(2026, 3, 1)),
            note: _string(json, <String>['note'], ''),
          );
        })
        .toList(growable: false);
  }

  List<SponsorshipPackage> _packageList(Object? value) {
    return _asList(value)
        .map((Object? item) {
          final Map<String, Object?> json = _asMap(item);
          final String assetType = _string(json, <String>[
            'asset_type',
            'assetType',
          ], 'club_banner');
          final String payoutSchedule = _string(json, <String>[
            'payout_schedule',
            'payoutSchedule',
          ], 'monthly');
          final int durationMonths = _integer(json, <String>[
            'duration_months',
            'durationMonths',
            'default_duration_months',
            'defaultDurationMonths',
          ], 12);
          return SponsorshipPackage(
            id: _string(json, <String>['id'], 'package'),
            code: _string(json, <String>[
              'code',
              'package_code',
              'packageCode',
            ], _string(json, <String>['id'], 'package')),
            name: _string(json, <String>['name'], 'Package'),
            tierLabel: _string(json, <String>[
              'tier_label',
              'tierLabel',
            ], _assetTypeLabel(assetType)),
            description: _string(json, <String>[
              'description',
            ], 'Sponsorship package'),
            value: _number(
              json,
              <String>['value'],
              _minorToMajor(
                _integer(json, <String>[
                  'base_amount_minor',
                  'baseAmountMinor',
                ], 0),
              ),
            ),
            currency: _string(json, <String>['currency'], 'USD'),
            durationMonths: durationMonths,
            assetCount: _integer(json, <String>[
              'asset_count',
              'assetCount',
            ], 1),
            assetType: assetType,
            payoutSchedule: payoutSchedule,
            inventorySummary: _string(
              json,
              <String>['inventory_summary', 'inventorySummary'],
              '${_assetTypeLabel(assetType)} placement | ${_scheduleLabel(payoutSchedule)} payouts',
            ),
            deliverables: _stringList(
              json['deliverables'] ??
                  json['deliverableList'] ??
                  <Object?>[
                    '$durationMonths-month default term',
                    '${_scheduleLabel(payoutSchedule)} payout cadence',
                  ],
            ),
            isFeatured: _boolean(json, <String>[
              'is_featured',
              'isFeatured',
            ], false),
          );
        })
        .toList(growable: false);
  }

  List<SponsorshipContract> _contractList(
    Object? value, {
    Map<String, String> packageNamesByCode = const <String, String>{},
  }) {
    return _asList(value)
        .map((Object? item) {
          final Map<String, Object?> json = _asMap(item);
          return _parseSponsorshipContract(
            json,
            packageNamesByCode: packageNamesByCode,
          );
        })
        .toList(growable: false);
  }

  SponsorshipContract _parseSponsorshipContract(
    Map<String, Object?> json, {
    Map<String, String> packageNamesByCode = const <String, String>{},
  }) {
    final String packageCode = _string(json, <String>[
      'package_code',
      'packageCode',
      'package_name',
      'packageName',
    ], 'package');
    final String payoutSchedule = _string(json, <String>[
      'payout_schedule',
      'payoutSchedule',
    ], 'monthly');
    final List<String> assetSlotCodes = _stringList(
      json['asset_slot_codes'] ?? json['assetSlotCodes'],
    );
    final String assetType = _string(json, <String>[
      'asset_type',
      'assetType',
    ], 'club_banner');
    final int durationMonths = _integer(json, <String>[
      'duration_months',
      'durationMonths',
    ], 0);
    final int outstandingAmountMinor = _integer(json, <String>[
      'outstanding_amount_minor',
      'outstandingAmountMinor',
    ], 0);
    final int settledAmountMinor = _integer(json, <String>[
      'settled_amount_minor',
      'settledAmountMinor',
    ], 0);
    final String currency = _string(json, <String>['currency'], 'USD');
    final String? customCopy = _nullableString(json, <String>[
      'custom_copy',
      'customCopy',
    ]);
    final String? customLogoUrl = _nullableString(json, <String>[
      'custom_logo_url',
      'customLogoUrl',
    ]);
    final bool moderationRequired = _boolean(json, <String>[
      'moderation_required',
      'moderationRequired',
    ], false);
    final List<String> notes = _stringList(
      json['notes'] ??
          <Object?>[
            if (moderationRequired) 'Moderation required before activation.',
            if (outstandingAmountMinor > 0)
              'Outstanding balance: ${_formatMinorCurrency(outstandingAmountMinor, currency)}',
            if (customCopy != null) 'Submitted copy: $customCopy',
            if (customLogoUrl != null) 'Submitted logo: $customLogoUrl',
          ],
    );
    return SponsorshipContract(
      id: _string(json, <String>['id'], 'contract'),
      sponsorName: _string(json, <String>[
        'sponsor_name',
        'sponsorName',
      ], 'Sponsor'),
      packageCode: packageCode,
      packageName:
          packageNamesByCode[packageCode] ??
          _string(json, <String>[
            'package_name',
            'packageName',
          ], _humanizeToken(packageCode)),
      status: _contractStatus(
        _string(json, <String>['status'], 'active').toLowerCase(),
      ),
      totalValue: _number(
        json,
        <String>['total_value', 'totalValue'],
        _minorToMajor(
          _integer(json, <String>[
            'contract_amount_minor',
            'contractAmountMinor',
          ], 0),
        ),
      ),
      currency: currency,
      payoutSchedule: payoutSchedule,
      startDate: _dateTime(json, <String>[
        'start_at',
        'start_date',
        'startDate',
      ], DateTime.utc(2026, 1, 1)),
      endDate: _dateTime(json, <String>[
        'end_at',
        'end_date',
        'endDate',
      ], DateTime.utc(2026, 12, 31)),
      assetSlotCodes: assetSlotCodes,
      renewalWindowLabel: _string(
        json,
        <String>['renewal_window_label', 'renewalWindowLabel'],
        '$durationMonths-month term | ${_scheduleLabel(payoutSchedule)} payouts',
      ),
      visibilityLabel: _string(
        json,
        <String>['visibility_label', 'visibilityLabel'],
        assetSlotCodes.isEmpty
            ? _assetTypeLabel(assetType)
            : 'Slots: ${assetSlotCodes.join(', ')}',
      ),
      contactName: _string(json, <String>['contact_name', 'contactName'], ''),
      moderationState: _moderationState(
        _string(json, <String>[
          'moderation_status',
          'moderation_state',
          'moderationStatus',
          'moderationState',
        ], 'approved'),
      ),
      moderationRequired: moderationRequired,
      settledValue: _minorToMajor(settledAmountMinor),
      outstandingValue: _minorToMajor(outstandingAmountMinor),
      deliverables: _stringList(
        json['deliverables'] ??
            <Object?>[
              _assetTypeLabel(assetType),
              if (assetSlotCodes.isNotEmpty)
                'Slots: ${assetSlotCodes.join(', ')}',
              '${_scheduleLabel(payoutSchedule)} payouts',
            ],
      ),
      notes: notes,
      customCopy: customCopy,
      customLogoUrl: customLogoUrl,
    );
  }

  List<SponsorAssetSlot> _assetSlotList(Object? value) {
    return _asList(value)
        .map((Object? item) {
          final Map<String, Object?> json = _asMap(item);
          final String assetType = _string(json, <String>[
            'asset_type',
            'assetType',
          ], 'club_banner');
          final String slotCode = _string(json, <String>[
            'slot_code',
            'slotCode',
          ], _string(json, <String>['id'], 'slot'));
          final bool isVisible = _boolean(json, <String>[
            'is_visible',
            'isVisible',
          ], true);
          return SponsorAssetSlot(
            id: _string(json, <String>['id'], 'slot'),
            slotCode: slotCode,
            assetType: assetType,
            isVisible: isVisible,
            surfaceName: _string(json, <String>[
              'surface_name',
              'surfaceName',
            ], _assetTypeLabel(assetType)),
            placementLabel: _string(json, <String>[
              'placement_label',
              'placementLabel',
            ], _humanizeToken(slotCode)),
            visibilityLabel: _string(
              json,
              <String>['visibility_label', 'visibilityLabel'],
              isVisible
                  ? 'Visible in live inventory'
                  : 'Hidden from live inventory',
            ),
            moderationState: _moderationState(
              _string(json, <String>[
                'moderation_status',
                'moderation_state',
                'moderationStatus',
                'moderationState',
              ], 'approved'),
            ),
            sponsorName: _nullableString(json, <String>[
              'rendered_text',
              'sponsor_name',
              'sponsorName',
            ]),
            note:
                _nullableString(json, <String>['note']) ??
                _nullableString(json, <String>['asset_url', 'assetUrl']),
          );
        })
        .toList(growable: false);
  }

  List<AcademyProgram> _academyProgramList(Object? value) {
    return _asList(value)
        .map((Object? item) {
          final Map<String, Object?> json = _asMap(item);
          return AcademyProgram(
            id: _string(json, <String>['id'], 'program'),
            name: _string(json, <String>['name'], 'Program'),
            ageBand: _string(json, <String>['age_band', 'ageBand'], ''),
            focusArea: _string(json, <String>['focus_area', 'focusArea'], ''),
            staffLead: _string(json, <String>['staff_lead', 'staffLead'], ''),
            weeklyHours: _integer(json, <String>[
              'weekly_hours',
              'weeklyHours',
            ], 0),
            enrolledPlayers: _integer(json, <String>[
              'enrolled_players',
              'enrolledPlayers',
            ], 0),
            statusLabel: _string(json, <String>[
              'status_label',
              'statusLabel',
            ], ''),
            outcomeLabel: _string(json, <String>[
              'outcome_label',
              'outcomeLabel',
            ], ''),
            description: _string(json, <String>['description'], ''),
          );
        })
        .toList(growable: false);
  }

  List<AcademyPlayer> _academyPlayerList(Object? value) {
    return _asList(value)
        .map((Object? item) {
          final Map<String, Object?> json = _asMap(item);
          return AcademyPlayer(
            id: _string(json, <String>['id'], 'player'),
            name: _string(json, <String>['name'], 'Academy player'),
            position: _string(json, <String>['position'], 'CM'),
            age: _integer(json, <String>['age'], 0),
            pathwayStage: _string(json, <String>[
              'pathway_stage',
              'pathwayStage',
            ], ''),
            potentialBand: _string(json, <String>[
              'potential_band',
              'potentialBand',
            ], ''),
            developmentProgressPercent: _number(json, <String>[
              'development_progress_percent',
              'developmentProgressPercent',
            ], 0),
            readinessScore: _integer(json, <String>[
              'readiness_score',
              'readinessScore',
            ], 0),
            minutesTarget: _integer(json, <String>[
              'minutes_target',
              'minutesTarget',
            ], 0),
            statusLabel: _string(json, <String>[
              'status_label',
              'statusLabel',
            ], ''),
            nextMilestone: _string(json, <String>[
              'next_milestone',
              'nextMilestone',
            ], ''),
            strengths: _stringList(json['strengths']),
            focusAreas: _stringList(json['focus_areas'] ?? json['focusAreas']),
            playerId: _nullableString(json, <String>[
              'player_id',
              'playerId',
              'canonical_player_id',
              'canonicalPlayerId',
            ]),
            secondaryPositions: _stringList(
              json['secondary_positions'] ?? json['secondaryPositions'],
            ),
            nationality: _nullableString(json, <String>['nationality']),
            nationalityCode: _nullableString(json, <String>[
              'nationality_code',
              'nationalityCode',
            ]),
            dominantFoot: _nullableString(json, <String>[
              'dominant_foot',
              'dominantFoot',
              'preferred_foot',
              'preferredFoot',
            ]),
            roleArchetype: _nullableString(json, <String>[
              'role_archetype',
              'roleArchetype',
              'archetype',
            ]),
            formationSlots: _stringList(
              json['formation_slots'] ?? json['formationSlots'],
            ),
            squadEligible: _nullableBoolean(json, <String>[
              'squad_eligible',
              'squadEligible',
            ]),
            avatarSeedToken: _nullableString(json, <String>[
              'avatar_seed_token',
              'avatarSeedToken',
            ]),
            avatarDnaSeed: _nullableString(json, <String>[
              'avatar_dna_seed',
              'avatarDnaSeed',
            ]),
            avatar: PlayerAvatar.fromJsonOrNull(json['avatar']),
            currentValueCredits: _nullableNumber(json, <String>[
              'current_value_credits',
              'currentValueCredits',
              'latest_value_credits',
              'latestValueCredits',
            ]),
            promotedToSenior: _boolean(json, <String>[
              'promoted_to_senior',
              'promotedToSenior',
            ], false),
          );
        })
        .toList(growable: false);
  }

  List<TrainingCycle> _trainingCycleList(Object? value) {
    return _asList(value)
        .map((Object? item) {
          final Map<String, Object?> json = _asMap(item);
          return TrainingCycle(
            id: _string(json, <String>['id'], 'cycle'),
            title: _string(json, <String>['title'], 'Training cycle'),
            phaseLabel: _string(json, <String>[
              'phase_label',
              'phaseLabel',
            ], ''),
            focus: _string(json, <String>['focus'], ''),
            cohortLabel: _string(json, <String>[
              'cohort_label',
              'cohortLabel',
            ], ''),
            startDate: _dateTime(json, <String>[
              'start_date',
              'startDate',
            ], DateTime.utc(2026, 3, 1)),
            endDate: _dateTime(json, <String>[
              'end_date',
              'endDate',
            ], DateTime.utc(2026, 3, 14)),
            attendancePercent: _number(json, <String>[
              'attendance_percent',
              'attendancePercent',
            ], 0),
            intensityLabel: _string(json, <String>[
              'intensity_label',
              'intensityLabel',
            ], ''),
            expectedPromotionCount: _integer(json, <String>[
              'expected_promotion_count',
              'expectedPromotionCount',
            ], 0),
            objective: _string(json, <String>['objective'], ''),
          );
        })
        .toList(growable: false);
  }

  List<AcademyPromotion> _academyPromotionList(Object? value) {
    return _asList(value)
        .map((Object? item) {
          final Map<String, Object?> json = _asMap(item);
          return AcademyPromotion(
            playerName: _string(json, <String>[
              'player_name',
              'playerName',
            ], ''),
            destination: _string(json, <String>['destination'], 'Senior squad'),
            occurredAt: _dateTime(json, <String>[
              'occurred_at',
              'occurredAt',
            ], DateTime.utc(2026, 3, 1)),
            note: _string(json, <String>['note'], ''),
          );
        })
        .toList(growable: false);
  }

  List<ScoutAssignment> _assignmentList(Object? value) {
    return _asList(value)
        .map((Object? item) {
          final Map<String, Object?> json = _asMap(item);
          return ScoutAssignment(
            id: _string(json, <String>['id'], 'assignment'),
            scoutName: _string(json, <String>['scout_name', 'scoutName'], ''),
            region: _string(json, <String>['region'], ''),
            competition: _string(json, <String>[
              'competition',
            ], 'Youth competition'),
            focusArea: _string(json, <String>['focus_area', 'focusArea'], ''),
            priorityLabel: _string(json, <String>[
              'priority_label',
              'priorityLabel',
            ], ''),
            statusLabel: _string(json, <String>[
              'status_label',
              'statusLabel',
            ], ''),
            dueDate: _dateTime(json, <String>[
              'due_date',
              'dueDate',
            ], DateTime.utc(2026, 3, 20)),
            activeProspects: _integer(json, <String>[
              'active_prospects',
              'activeProspects',
            ], 0),
            travelWindow: _string(json, <String>[
              'travel_window',
              'travelWindow',
            ], ''),
            objective: _string(json, <String>['objective'], ''),
          );
        })
        .toList(growable: false);
  }

  List<Prospect> _prospectList(Object? value) {
    return _asList(value)
        .map((Object? item) {
          final Map<String, Object?> json = _asMap(item);
          return Prospect(
            id: _string(json, <String>['id'], 'prospect'),
            name: _string(json, <String>['name'], 'Prospect'),
            position: _string(json, <String>['position'], 'CM'),
            age: _integer(json, <String>['age'], 0),
            region: _string(json, <String>['region'], ''),
            currentClub: _string(json, <String>[
              'current_club',
              'currentClub',
            ], ''),
            stage: _prospectStage(
              _string(json, <String>['stage'], 'monitored'),
            ),
            readinessScore: _integer(json, <String>[
              'readiness_score',
              'readinessScore',
            ], 0),
            developmentProjection: _string(json, <String>[
              'development_projection',
              'developmentProjection',
            ], ''),
            pathwayFitLabel: _string(json, <String>[
              'pathway_fit_label',
              'pathwayFitLabel',
            ], ''),
            nextAction: _string(json, <String>[
              'next_action',
              'nextAction',
            ], ''),
            availabilityLabel: _string(json, <String>[
              'availability_label',
              'availabilityLabel',
            ], ''),
            lastUpdated: _dateTime(json, <String>[
              'last_updated',
              'lastUpdated',
            ], DateTime.utc(2026, 3, 1)),
            strengths: _stringList(json['strengths']),
            focusAreas: _stringList(json['focus_areas'] ?? json['focusAreas']),
          );
        })
        .toList(growable: false);
  }

  List<ProspectReport> _reportList(Object? value) {
    return _asList(value)
        .map((Object? item) {
          final Map<String, Object?> json = _asMap(item);
          return ProspectReport(
            id: _string(json, <String>['id'], 'report'),
            prospectId: _string(json, <String>[
              'prospect_id',
              'prospectId',
            ], ''),
            scoutName: _string(json, <String>['scout_name', 'scoutName'], ''),
            headline: _string(json, <String>['headline'], ''),
            createdAt: _dateTime(json, <String>[
              'created_at',
              'createdAt',
            ], DateTime.utc(2026, 3, 1)),
            overallFit: _string(json, <String>[
              'overall_fit',
              'overallFit',
            ], ''),
            technicalNote: _string(json, <String>[
              'technical_note',
              'technicalNote',
            ], ''),
            physicalNote: _string(json, <String>[
              'physical_note',
              'physicalNote',
            ], ''),
            characterNote: _string(json, <String>[
              'character_note',
              'characterNote',
            ], ''),
            recommendation: _string(json, <String>['recommendation'], ''),
          );
        })
        .toList(growable: false);
  }

  List<YouthPipelineStage> _pipelineStages(Object? value) {
    return _asList(value)
        .map((Object? item) {
          final Map<String, Object?> json = _asMap(item);
          return YouthPipelineStage(
            label: _string(json, <String>['label'], 'Stage'),
            count: _integer(json, <String>['count'], 0),
            description: _string(json, <String>['description'], ''),
          );
        })
        .toList(growable: false);
  }
}

Map<String, Object?> _asMap(Object? value) {
  if (value is Map<String, Object?>) {
    return value;
  }
  if (value is Map) {
    return value.map(
      (Object? key, Object? nestedValue) =>
          MapEntry<String, Object?>(key.toString(), nestedValue),
    );
  }
  return <String, Object?>{};
}

List<Object?> _asList(Object? value) {
  if (value is List<Object?>) {
    return value;
  }
  if (value is List) {
    return List<Object?>.from(value);
  }
  return const <Object?>[];
}

String _string(Map<String, Object?> json, List<String> keys, String fallback) {
  final String? value = _nullableString(json, keys);
  return value ?? fallback;
}

String? _nullableString(Map<String, Object?> json, List<String> keys) {
  for (final String key in keys) {
    final Object? raw = json[key];
    if (raw == null) {
      continue;
    }
    final String parsed = raw.toString().trim();
    if (parsed.isNotEmpty) {
      return parsed;
    }
  }
  return null;
}

double _number(Map<String, Object?> json, List<String> keys, double fallback) {
  for (final String key in keys) {
    final Object? raw = json[key];
    if (raw == null) {
      continue;
    }
    if (raw is num) {
      return raw.toDouble();
    }
    final double? parsed = double.tryParse(raw.toString());
    if (parsed != null) {
      return parsed;
    }
  }
  return fallback;
}

double? _nullableNumber(Map<String, Object?> json, List<String> keys) {
  for (final String key in keys) {
    final Object? raw = json[key];
    if (raw == null) {
      continue;
    }
    if (raw is num) {
      return raw.toDouble();
    }
    final double? parsed = double.tryParse(raw.toString());
    if (parsed != null) {
      return parsed;
    }
  }
  return null;
}

int _integer(Map<String, Object?> json, List<String> keys, int fallback) {
  for (final String key in keys) {
    final Object? raw = json[key];
    if (raw == null) {
      continue;
    }
    if (raw is int) {
      return raw;
    }
    if (raw is num) {
      return raw.round();
    }
    final int? parsed = int.tryParse(raw.toString());
    if (parsed != null) {
      return parsed;
    }
  }
  return fallback;
}

bool _boolean(Map<String, Object?> json, List<String> keys, bool fallback) {
  for (final String key in keys) {
    final Object? raw = json[key];
    if (raw == null) {
      continue;
    }
    if (raw is bool) {
      return raw;
    }
    final String normalized = raw.toString().toLowerCase().trim();
    if (<String>{'true', '1', 'yes'}.contains(normalized)) {
      return true;
    }
    if (<String>{'false', '0', 'no'}.contains(normalized)) {
      return false;
    }
  }
  return fallback;
}

bool? _nullableBoolean(Map<String, Object?> json, List<String> keys) {
  for (final String key in keys) {
    final Object? raw = json[key];
    if (raw == null) {
      continue;
    }
    if (raw is bool) {
      return raw;
    }
    final String normalized = raw.toString().toLowerCase().trim();
    if (<String>{'true', '1', 'yes'}.contains(normalized)) {
      return true;
    }
    if (<String>{'false', '0', 'no'}.contains(normalized)) {
      return false;
    }
  }
  return null;
}

DateTime _dateTime(
  Map<String, Object?> json,
  List<String> keys,
  DateTime fallback,
) {
  for (final String key in keys) {
    final Object? raw = json[key];
    if (raw == null) {
      continue;
    }
    if (raw is DateTime) {
      return raw;
    }
    final DateTime? parsed = DateTime.tryParse(raw.toString());
    if (parsed != null) {
      return parsed.toUtc();
    }
  }
  return fallback;
}

List<String> _stringList(Object? value) {
  return _asList(value)
      .map((Object? item) => item?.toString().trim() ?? '')
      .where((String item) => item.isNotEmpty)
      .toList(growable: false);
}

double _minorToMajor(int amountMinor) {
  return amountMinor / 100;
}

String _formatMinorCurrency(int amountMinor, String currency) {
  final double amount = _minorToMajor(amountMinor);
  if (currency.toUpperCase() == 'USD') {
    return '\$${amount.toStringAsFixed(2)}';
  }
  return '${amount.toStringAsFixed(2)} ${currency.toUpperCase()}';
}

String _assetTypeLabel(String raw) {
  return _humanizeToken(raw);
}

String _scheduleLabel(String raw) {
  switch (raw.toLowerCase()) {
    case 'upfront':
      return 'Upfront';
    case 'quarterly':
      return 'Quarterly';
    case 'monthly':
    default:
      return 'Monthly';
  }
}

String _humanizeToken(String raw) {
  final List<String> parts = raw
      .split(RegExp(r'[_\-\s]+'))
      .where((String part) => part.isNotEmpty)
      .toList(growable: false);
  if (parts.isEmpty) {
    return raw;
  }
  return parts
      .map(
        (String part) =>
            '${part[0].toUpperCase()}${part.substring(1).toLowerCase()}',
      )
      .join(' ');
}

SponsorshipContractStatus _contractStatus(String raw) {
  switch (raw) {
    case 'renewal_due':
    case 'renewaldue':
      return SponsorshipContractStatus.renewalDue;
    case 'pending_approval':
    case 'pendingapproval':
      return SponsorshipContractStatus.pendingApproval;
    case 'completed':
      return SponsorshipContractStatus.completed;
    case 'active':
    default:
      return SponsorshipContractStatus.active;
  }
}

SponsorModerationState _moderationState(String raw) {
  switch (raw.toLowerCase()) {
    case 'pending':
    case 'under_review':
    case 'underreview':
      return SponsorModerationState.underReview;
    case 'not_required':
    case 'notrequired':
      return SponsorModerationState.approved;
    case 'needs_changes':
    case 'needschanges':
      return SponsorModerationState.needsChanges;
    case 'blocked':
      return SponsorModerationState.blocked;
    case 'approved':
    default:
      return SponsorModerationState.approved;
  }
}

ProspectStage _prospectStage(String raw) {
  switch (raw.toLowerCase()) {
    case 'shortlisted':
      return ProspectStage.shortlisted;
    case 'trial':
      return ProspectStage.trial;
    case 'scholarship':
      return ProspectStage.scholarship;
    case 'promoted':
      return ProspectStage.promoted;
    case 'monitored':
    default:
      return ProspectStage.monitored;
  }
}

GteApiErrorType _errorTypeFromStatus(int statusCode) {
  if (statusCode == 401) {
    return GteApiErrorType.unauthorized;
  }
  if (statusCode == 404) {
    return GteApiErrorType.notFound;
  }
  if (statusCode == 422) {
    return GteApiErrorType.validation;
  }
  if (statusCode >= 500) {
    return GteApiErrorType.unavailable;
  }
  return GteApiErrorType.unknown;
}

String _errorMessage(Object? payload) {
  if (payload is Map) {
    final Map<String, Object?> map = _asMap(payload);
    return _nullableString(map, <String>['detail', 'message', 'error']) ??
        'Backend request failed.';
  }
  final String text = payload?.toString().trim() ?? '';
  return text.isEmpty ? 'Backend request failed.' : text;
}

class _UnsupportedClubOpsTransport implements GteTransport {
  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    throw UnsupportedError('Transport is unavailable in fixture mode.');
  }
}
