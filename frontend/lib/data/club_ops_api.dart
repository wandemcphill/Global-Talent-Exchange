import 'package:gte_frontend/data/club_ops_fixtures.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/models/academy_models.dart';
import 'package:gte_frontend/models/club_finance_models.dart';
import 'package:gte_frontend/models/scouting_models.dart';
import 'package:gte_frontend/models/sponsorship_models.dart';

class ClubOpsApi {
  ClubOpsApi._({
    required this.config,
    required this.transport,
    required this.latency,
  });

  final GteRepositoryConfig config;
  final GteTransport transport;
  final Duration latency;

  factory ClubOpsApi.standard({
    required String baseUrl,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
  }) {
    return ClubOpsApi._(
      config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
      transport: GteHttpTransport(),
      latency: const Duration(milliseconds: 200),
    );
  }

  factory ClubOpsApi.fixture({
    String baseUrl = 'http://127.0.0.1:8000',
    Duration latency = Duration.zero,
  }) {
    return ClubOpsApi._(
      config: GteRepositoryConfig(baseUrl: baseUrl, mode: GteBackendMode.fixture),
      transport: _UnsupportedClubOpsTransport(),
      latency: latency,
    );
  }

  Future<ClubFinanceSnapshot> fetchFinance({
    required String clubId,
    String? clubName,
  }) {
    return _withFallback<ClubFinanceSnapshot>(
      () async => _parseFinance(
        _asMap(await _request('GET', '/api/clubs/$clubId/finance')),
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
      () async => _parseSponsorships(
        _asMap(await _request('GET', '/api/clubs/$clubId/sponsorships')),
        fallbackClubId: clubId,
        fallbackClubName: clubName,
      ),
      () async {
        await Future<void>.delayed(latency);
        return fixtureSponsorships(clubId, clubName);
      },
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
        _asMap(await _request('GET', '/api/admin/club-ops')),
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
        _asMap(await _request('GET', '/api/admin/club-ops/finance')),
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
        _asMap(await _request('GET', '/api/admin/club-ops/sponsorships')),
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
        _asMap(await _request('GET', '/api/admin/club-ops/academy')),
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
        _asMap(await _request('GET', '/api/admin/club-ops/scouting')),
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
    try {
      return await liveCall();
    } on GteApiException catch (error) {
      if (config.mode == GteBackendMode.liveThenFixture &&
          _shouldFallback(error)) {
        return fixtureCall();
      }
      rethrow;
    } on GteParsingException {
      if (config.mode == GteBackendMode.liveThenFixture) {
        return fixtureCall();
      }
      rethrow;
    }
  }

  bool _shouldFallback(GteApiException error) {
    return error.supportsFixtureFallback ||
        error.type == GteApiErrorType.notFound ||
        error.type == GteApiErrorType.validation ||
        error.type == GteApiErrorType.unauthorized;
  }

  Future<Object?> _request(
    String method,
    String path, {
    Map<String, Object?> query = const <String, Object?>{},
  }) async {
    try {
      final GteTransportResponse response = await transport.send(
        GteTransportRequest(
          method: method,
          uri: config.uriFor(path, query),
          headers: const <String, String>{'Accept': 'application/json'},
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
      return response.body;
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

  ClubFinanceSnapshot _parseFinance(
    Map<String, Object?> json, {
    required String fallbackClubId,
    String? fallbackClubName,
  }) {
    if (!json.containsKey('balance_summary') &&
        !json.containsKey('budget_allocations') &&
        !json.containsKey('ledger_entries')) {
      throw const GteParsingException('Finance payload missing summary fields.');
    }
    final Map<String, Object?> balance =
        _asMap(json['balance_summary'] ?? json['summary']);
    return ClubFinanceSnapshot(
      clubId: _string(json, <String>['club_id', 'clubId'], fallbackClubId),
      clubName: _string(
        json,
        <String>['club_name', 'clubName'],
        fallbackClubName ?? clubOpsDisplayClubName(fallbackClubId),
      ),
      balanceSummary: ClubBalanceSummary(
        currentBalance: _number(
            balance, <String>['current_balance', 'currentBalance'], 0),
        operatingBudget:
            _number(balance, <String>['operating_budget', 'operatingBudget'], 0),
        reserveTarget:
            _number(balance, <String>['reserve_target', 'reserveTarget'], 0),
        monthlyIncome:
            _number(balance, <String>['monthly_income', 'monthlyIncome'], 0),
        monthlyExpenses: _number(
            balance, <String>['monthly_expenses', 'monthlyExpenses'], 0),
        payrollCommitment: _number(
            balance, <String>['payroll_commitment', 'payrollCommitment'], 0),
        nextPayrollDate: _dateTime(
          balance,
          <String>['next_payroll_date', 'nextPayrollDate'],
          DateTime.utc(2026, 3, 25),
        ),
        nextPayrollAmount: _number(
            balance, <String>['next_payroll_amount', 'nextPayrollAmount'], 0),
        cashRunwayMonths: _number(
            balance, <String>['cash_runway_months', 'cashRunwayMonths'], 0),
        balanceDeltaPercent: _number(
            balance, <String>['balance_delta_percent', 'balanceDeltaPercent'], 0),
      ),
      budgetAllocations:
          _categoryList(json['budget_allocations'] ?? json['budgetAllocation']),
      incomeBreakdown:
          _categoryList(json['income_breakdown'] ?? json['incomeBreakdown']),
      expenseBreakdown:
          _categoryList(json['expense_breakdown'] ?? json['expenseBreakdown']),
      cashflow: _cashflowList(json['cashflow']),
      ledgerEntries: _ledgerList(json['ledger_entries'] ?? json['ledger']),
      financeNotes: _stringList(json['finance_notes'] ?? json['notes']),
    );
  }

  SponsorshipDashboard _parseSponsorships(
    Map<String, Object?> json, {
    required String fallbackClubId,
    String? fallbackClubName,
  }) {
    if (!json.containsKey('packages') &&
        !json.containsKey('contracts') &&
        !json.containsKey('asset_slots')) {
      throw const GteParsingException(
          'Sponsorship payload missing catalog and contract fields.');
    }
    return SponsorshipDashboard(
      clubId: _string(json, <String>['club_id', 'clubId'], fallbackClubId),
      clubName: _string(
        json,
        <String>['club_name', 'clubName'],
        fallbackClubName ?? clubOpsDisplayClubName(fallbackClubId),
      ),
      activeContractValue: _number(
        json,
        <String>['active_contract_value', 'activeContractValue'],
        0,
      ),
      projectedRenewalValue: _number(
        json,
        <String>['projected_renewal_value', 'projectedRenewalValue'],
        0,
      ),
      packages: _packageList(json['packages']),
      contracts: _contractList(json['contracts']),
      assetSlots: _assetSlotList(json['asset_slots'] ?? json['assetSlots']),
      notes: _stringList(json['notes']),
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
          'Academy payload missing pathway summary fields.');
    }
    final Map<String, Object?> pathway =
        _asMap(json['pathway_summary'] ?? json['summary']);
    return AcademyDashboard(
      clubId: _string(json, <String>['club_id', 'clubId'], fallbackClubId),
      clubName: _string(
        json,
        <String>['club_name', 'clubName'],
        fallbackClubName ?? clubOpsDisplayClubName(fallbackClubId),
      ),
      pathwaySummary: AcademyPathwaySummary(
        developmentBudget: _number(
            pathway, <String>['development_budget', 'developmentBudget'], 0),
        squadSize: _integer(pathway, <String>['squad_size', 'squadSize'], 0),
        promotionsThisSeason: _integer(
            pathway, <String>['promotions_this_season', 'promotionsThisSeason'], 0),
        graduationRatePercent: _number(
            pathway, <String>['graduation_rate_percent', 'graduationRatePercent'], 0),
        staffCoverageLabel: _string(
          pathway,
          <String>['staff_coverage_label', 'staffCoverageLabel'],
          'Full-time multidisciplinary team',
        ),
        facilityLabel: _string(
          pathway,
          <String>['facility_label', 'facilityLabel'],
          'Regional performance centre',
        ),
      ),
      programs: _academyProgramList(json['programs']),
      players: _academyPlayerList(json['players']),
      trainingCycles: _trainingCycleList(
          json['training_cycles'] ?? json['trainingCycles']),
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
          'Scouting payload missing assignment and prospect fields.');
    }
    return ScoutingDashboard(
      clubId: _string(json, <String>['club_id', 'clubId'], fallbackClubId),
      clubName: _string(
        json,
        <String>['club_name', 'clubName'],
        fallbackClubName ?? clubOpsDisplayClubName(fallbackClubId),
      ),
      openAssignments:
          _integer(json, <String>['open_assignments', 'openAssignments'], 0),
      activeRegions:
          _integer(json, <String>['active_regions', 'activeRegions'], 0),
      liveProspects:
          _integer(json, <String>['live_prospects', 'liveProspects'], 0),
      trialsScheduled:
          _integer(json, <String>['trials_scheduled', 'trialsScheduled'], 0),
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
      trackedProspects: _integer(
          json, <String>['tracked_prospects', 'trackedProspects'], 0),
      shortlistedProspects: _integer(
          json, <String>['shortlisted_prospects', 'shortlistedProspects'], 0),
      trialists: _integer(json, <String>['trialists'], 0),
      scholarshipOffers:
          _integer(json, <String>['scholarship_offers', 'scholarshipOffers'], 0),
      promotedPlayers:
          _integer(json, <String>['promoted_players', 'promotedPlayers'], 0),
      conversionPercent:
          _number(json, <String>['conversion_percent', 'conversionPercent'], 0),
      stages: _pipelineStages(json['stages']),
      notes: _stringList(json['notes']),
    );
  }

  ClubOpsAdminSnapshot _parseAdminSnapshot(Map<String, Object?> json) {
    if (!json.containsKey('clubs_monitored') &&
        !json.containsKey('clubsMonitored')) {
      throw const GteParsingException('Club ops admin payload missing summary.');
    }
    return ClubOpsAdminSnapshot(
      clubsMonitored:
          _integer(json, <String>['clubs_monitored', 'clubsMonitored'], 0),
      totalOperatingBudget: _number(
          json, <String>['total_operating_budget', 'totalOperatingBudget'], 0),
      activeContracts:
          _integer(json, <String>['active_contracts', 'activeContracts'], 0),
      academyPromotions: _integer(
          json, <String>['academy_promotions', 'academyPromotions'], 0),
      activeAssignments:
          _integer(json, <String>['active_assignments', 'activeAssignments'], 0),
      youthConversionPercent: _number(
          json, <String>['youth_conversion_percent', 'youthConversionPercent'], 0),
      statusNotes:
          _stringList(json['status_notes'] ?? json['statusNotes'] ?? json['notes']),
    );
  }

  ClubFinanceAnalyticsSnapshot _parseFinanceAnalytics(Map<String, Object?> json) {
    if (!json.containsKey('average_monthly_balance') &&
        !json.containsKey('averageMonthlyBalance')) {
      throw const GteParsingException(
          'Finance analytics payload missing key metrics.');
    }
    return ClubFinanceAnalyticsSnapshot(
      averageMonthlyBalance: _number(
          json, <String>['average_monthly_balance', 'averageMonthlyBalance'], 0),
      operatingMarginPercent: _number(
          json, <String>['operating_margin_percent', 'operatingMarginPercent'], 0),
      payrollSharePercent:
          _number(json, <String>['payroll_share_percent', 'payrollSharePercent'], 0),
      developmentSharePercent: _number(
          json, <String>['development_share_percent', 'developmentSharePercent'], 0),
      commercialSharePercent: _number(
          json, <String>['commercial_share_percent', 'commercialSharePercent'], 0),
      revenueReliabilityLabel: _string(
        json,
        <String>['revenue_reliability_label', 'revenueReliabilityLabel'],
        'Stable renewals and matchday collections',
      ),
      topExpenseLabel:
          _string(json, <String>['top_expense_label', 'topExpenseLabel'], 'Payroll'),
      categoryMix: _categoryList(json['category_mix'] ?? json['categoryMix']),
      quarterlyCashflow: _cashflowList(
          json['quarterly_cashflow'] ?? json['quarterlyCashflow']),
    );
  }

  SponsorshipAnalyticsSnapshot _parseSponsorshipAnalytics(
      Map<String, Object?> json) {
    if (!json.containsKey('total_revenue') &&
        !json.containsKey('totalRevenue')) {
      throw const GteParsingException(
          'Sponsorship analytics payload missing revenue totals.');
    }
    return SponsorshipAnalyticsSnapshot(
      totalRevenue:
          _number(json, <String>['total_revenue', 'totalRevenue'], 0),
      averageContractValue: _number(
          json, <String>['average_contract_value', 'averageContractValue'], 0),
      renewalRatePercent:
          _number(json, <String>['renewal_rate_percent', 'renewalRatePercent'], 0),
      assetUtilizationPercent: _number(
          json, <String>['asset_utilization_percent', 'assetUtilizationPercent'], 0),
      pendingReviews:
          _integer(json, <String>['pending_reviews', 'pendingReviews'], 0),
      flaggedAssets:
          _integer(json, <String>['flagged_assets', 'flaggedAssets'], 0),
      topContracts: _contractList(json['top_contracts'] ?? json['topContracts']),
      reviewQueue:
          _assetSlotList(json['review_queue'] ?? json['reviewQueue']),
    );
  }

  AcademyAnalyticsSnapshot _parseAcademyAnalytics(Map<String, Object?> json) {
    if (!json.containsKey('conversion_rate_percent') &&
        !json.containsKey('conversionRatePercent')) {
      throw const GteParsingException(
          'Academy analytics payload missing conversion metrics.');
    }
    return AcademyAnalyticsSnapshot(
      conversionRatePercent: _number(
          json, <String>['conversion_rate_percent', 'conversionRatePercent'], 0),
      retentionRatePercent: _number(
          json, <String>['retention_rate_percent', 'retentionRatePercent'], 0),
      averageReadinessScore: _integer(
          json, <String>['average_readiness_score', 'averageReadinessScore'], 0),
      promotionsThisSeason: _integer(
          json, <String>['promotions_this_season', 'promotionsThisSeason'], 0),
      pathwayHealthLabel: _string(
        json,
        <String>['pathway_health_label', 'pathwayHealthLabel'],
        'Balanced intake and promotion cadence',
      ),
      programMix:
          _academyProgramList(json['program_mix'] ?? json['programMix']),
    );
  }

  ScoutingAnalyticsSnapshot _parseScoutingAnalytics(Map<String, Object?> json) {
    if (!json.containsKey('assignment_completion_percent') &&
        !json.containsKey('assignmentCompletionPercent')) {
      throw const GteParsingException(
          'Scouting analytics payload missing funnel metrics.');
    }
    return ScoutingAnalyticsSnapshot(
      assignmentCompletionPercent: _number(
          json, <String>['assignment_completion_percent', 'assignmentCompletionPercent'], 0),
      regionalCoveragePercent: _number(
          json, <String>['regional_coverage_percent', 'regionalCoveragePercent'], 0),
      shortlistToTrialPercent: _number(
          json, <String>['shortlist_to_trial_percent', 'shortlistToTrialPercent'], 0),
      trialToScholarshipPercent: _number(
          json, <String>['trial_to_scholarship_percent', 'trialToScholarshipPercent'], 0),
      youthConversionPercent: _number(
          json, <String>['youth_conversion_percent', 'youthConversionPercent'], 0),
      funnel: _pipelineStages(json['funnel']),
      assignmentLoad:
          _assignmentList(json['assignment_load'] ?? json['assignmentLoad']),
    );
  }

  List<FinanceCategoryBreakdown> _categoryList(Object? value) {
    return _asList(value)
        .map((Object? item) {
          final Map<String, Object?> json = _asMap(item);
          return FinanceCategoryBreakdown(
            label: _string(json, <String>['label', 'name'], 'Unlabeled'),
            amount: _number(json, <String>['amount', 'value'], 0),
            sharePercent:
                _number(json, <String>['share_percent', 'sharePercent'], 0),
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
            closingBalance:
                _number(json, <String>['closing_balance', 'closingBalance'], 0),
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
            counterparty:
                _string(json, <String>['counterparty'], 'Club operations'),
            type: typeValue == 'income'
                ? LedgerEntryType.income
                : LedgerEntryType.expense,
            amount: _number(json, <String>['amount'], 0),
            runningBalance:
                _number(json, <String>['running_balance', 'runningBalance'], 0),
            occurredAt:
                _dateTime(json, <String>['occurred_at', 'occurredAt'], DateTime.utc(2026, 3, 1)),
            note: _string(json, <String>['note'], ''),
          );
        })
        .toList(growable: false);
  }

  List<SponsorshipPackage> _packageList(Object? value) {
    return _asList(value)
        .map((Object? item) {
          final Map<String, Object?> json = _asMap(item);
          return SponsorshipPackage(
            id: _string(json, <String>['id'], 'package'),
            name: _string(json, <String>['name'], 'Package'),
            tierLabel: _string(json, <String>['tier_label', 'tierLabel'], 'Club'),
            description:
                _string(json, <String>['description'], 'Sponsorship package'),
            value: _number(json, <String>['value'], 0),
            durationMonths:
                _integer(json, <String>['duration_months', 'durationMonths'], 12),
            assetCount: _integer(json, <String>['asset_count', 'assetCount'], 0),
            inventorySummary: _string(
                json, <String>['inventory_summary', 'inventorySummary'], ''),
            deliverables:
                _stringList(json['deliverables'] ?? json['deliverableList']),
            isFeatured:
                _boolean(json, <String>['is_featured', 'isFeatured'], false),
          );
        })
        .toList(growable: false);
  }

  List<SponsorshipContract> _contractList(Object? value) {
    return _asList(value)
        .map((Object? item) {
          final Map<String, Object?> json = _asMap(item);
          return SponsorshipContract(
            id: _string(json, <String>['id'], 'contract'),
            sponsorName:
                _string(json, <String>['sponsor_name', 'sponsorName'], 'Sponsor'),
            packageName:
                _string(json, <String>['package_name', 'packageName'], 'Package'),
            status: _contractStatus(
                _string(json, <String>['status'], 'active').toLowerCase()),
            totalValue:
                _number(json, <String>['total_value', 'totalValue'], 0),
            startDate:
                _dateTime(json, <String>['start_date', 'startDate'], DateTime.utc(2026, 1, 1)),
            endDate:
                _dateTime(json, <String>['end_date', 'endDate'], DateTime.utc(2026, 12, 31)),
            renewalWindowLabel: _string(
              json,
              <String>['renewal_window_label', 'renewalWindowLabel'],
              'Review 60 days before expiry',
            ),
            visibilityLabel: _string(
              json,
              <String>['visibility_label', 'visibilityLabel'],
              'High visibility',
            ),
            contactName:
                _string(json, <String>['contact_name', 'contactName'], ''),
            moderationState: _moderationState(
              _string(
                json,
                <String>['moderation_state', 'moderationState'],
                'approved',
              ),
            ),
            deliverables: _stringList(json['deliverables']),
            notes: _stringList(json['notes']),
          );
        })
        .toList(growable: false);
  }

  List<SponsorAssetSlot> _assetSlotList(Object? value) {
    return _asList(value)
        .map((Object? item) {
          final Map<String, Object?> json = _asMap(item);
          return SponsorAssetSlot(
            id: _string(json, <String>['id'], 'slot'),
            surfaceName:
                _string(json, <String>['surface_name', 'surfaceName'], 'Asset slot'),
            placementLabel: _string(
                json, <String>['placement_label', 'placementLabel'], ''),
            visibilityLabel: _string(
                json, <String>['visibility_label', 'visibilityLabel'], ''),
            moderationState: _moderationState(
              _string(
                json,
                <String>['moderation_state', 'moderationState'],
                'approved',
              ),
            ),
            sponsorName:
                _nullableString(json, <String>['sponsor_name', 'sponsorName']),
            note: _nullableString(json, <String>['note']),
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
            focusArea:
                _string(json, <String>['focus_area', 'focusArea'], ''),
            staffLead:
                _string(json, <String>['staff_lead', 'staffLead'], ''),
            weeklyHours:
                _integer(json, <String>['weekly_hours', 'weeklyHours'], 0),
            enrolledPlayers: _integer(
                json, <String>['enrolled_players', 'enrolledPlayers'], 0),
            statusLabel:
                _string(json, <String>['status_label', 'statusLabel'], ''),
            outcomeLabel:
                _string(json, <String>['outcome_label', 'outcomeLabel'], ''),
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
            pathwayStage:
                _string(json, <String>['pathway_stage', 'pathwayStage'], ''),
            potentialBand:
                _string(json, <String>['potential_band', 'potentialBand'], ''),
            developmentProgressPercent: _number(
              json,
              <String>[
                'development_progress_percent',
                'developmentProgressPercent'
              ],
              0,
            ),
            readinessScore:
                _integer(json, <String>['readiness_score', 'readinessScore'], 0),
            minutesTarget:
                _integer(json, <String>['minutes_target', 'minutesTarget'], 0),
            statusLabel:
                _string(json, <String>['status_label', 'statusLabel'], ''),
            nextMilestone:
                _string(json, <String>['next_milestone', 'nextMilestone'], ''),
            strengths: _stringList(json['strengths']),
            focusAreas: _stringList(json['focus_areas'] ?? json['focusAreas']),
            promotedToSenior: _boolean(
              json,
              <String>['promoted_to_senior', 'promotedToSenior'],
              false,
            ),
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
            phaseLabel:
                _string(json, <String>['phase_label', 'phaseLabel'], ''),
            focus: _string(json, <String>['focus'], ''),
            cohortLabel:
                _string(json, <String>['cohort_label', 'cohortLabel'], ''),
            startDate:
                _dateTime(json, <String>['start_date', 'startDate'], DateTime.utc(2026, 3, 1)),
            endDate:
                _dateTime(json, <String>['end_date', 'endDate'], DateTime.utc(2026, 3, 14)),
            attendancePercent:
                _number(json, <String>['attendance_percent', 'attendancePercent'], 0),
            intensityLabel: _string(
                json, <String>['intensity_label', 'intensityLabel'], ''),
            expectedPromotionCount: _integer(
              json,
              <String>['expected_promotion_count', 'expectedPromotionCount'],
              0,
            ),
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
            playerName:
                _string(json, <String>['player_name', 'playerName'], ''),
            destination:
                _string(json, <String>['destination'], 'Senior squad'),
            occurredAt:
                _dateTime(json, <String>['occurred_at', 'occurredAt'], DateTime.utc(2026, 3, 1)),
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
            competition:
                _string(json, <String>['competition'], 'Youth competition'),
            focusArea:
                _string(json, <String>['focus_area', 'focusArea'], ''),
            priorityLabel:
                _string(json, <String>['priority_label', 'priorityLabel'], ''),
            statusLabel:
                _string(json, <String>['status_label', 'statusLabel'], ''),
            dueDate:
                _dateTime(json, <String>['due_date', 'dueDate'], DateTime.utc(2026, 3, 20)),
            activeProspects:
                _integer(json, <String>['active_prospects', 'activeProspects'], 0),
            travelWindow:
                _string(json, <String>['travel_window', 'travelWindow'], ''),
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
            currentClub:
                _string(json, <String>['current_club', 'currentClub'], ''),
            stage: _prospectStage(_string(json, <String>['stage'], 'monitored')),
            readinessScore:
                _integer(json, <String>['readiness_score', 'readinessScore'], 0),
            developmentProjection: _string(
              json,
              <String>['development_projection', 'developmentProjection'],
              '',
            ),
            pathwayFitLabel:
                _string(json, <String>['pathway_fit_label', 'pathwayFitLabel'], ''),
            nextAction:
                _string(json, <String>['next_action', 'nextAction'], ''),
            availabilityLabel: _string(
                json, <String>['availability_label', 'availabilityLabel'], ''),
            lastUpdated:
                _dateTime(json, <String>['last_updated', 'lastUpdated'], DateTime.utc(2026, 3, 1)),
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
            prospectId:
                _string(json, <String>['prospect_id', 'prospectId'], ''),
            scoutName: _string(json, <String>['scout_name', 'scoutName'], ''),
            headline: _string(json, <String>['headline'], ''),
            createdAt:
                _dateTime(json, <String>['created_at', 'createdAt'], DateTime.utc(2026, 3, 1)),
            overallFit:
                _string(json, <String>['overall_fit', 'overallFit'], ''),
            technicalNote:
                _string(json, <String>['technical_note', 'technicalNote'], ''),
            physicalNote:
                _string(json, <String>['physical_note', 'physicalNote'], ''),
            characterNote:
                _string(json, <String>['character_note', 'characterNote'], ''),
            recommendation:
                _string(json, <String>['recommendation'], ''),
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
    case 'under_review':
    case 'underreview':
      return SponsorModerationState.underReview;
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
