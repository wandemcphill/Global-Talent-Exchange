import 'package:flutter/foundation.dart';
import '../core/app_feedback.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/models/academy_models.dart';
import 'package:gte_frontend/models/club_finance_models.dart';
import 'package:gte_frontend/models/scouting_models.dart';
import 'package:gte_frontend/models/sponsorship_models.dart';

class ClubOpsController extends ChangeNotifier {
  ClubOpsController({
    required ClubOpsApi api,
    required this.clubId,
    this.clubName,
  }) : _api = api;

  final ClubOpsApi _api;
  final GteRequestGate _clubGate = GteRequestGate();
  final GteRequestGate _adminGate = GteRequestGate();
  final String clubId;
  final String? clubName;

  bool isLoadingClubData = false;
  bool isLoadingAdminData = false;
  String? clubErrorMessage;
  String? adminErrorMessage;

  ClubFinanceSnapshot? finance;
  SponsorshipDashboard? sponsorships;
  AcademyDashboard? academy;
  ScoutingDashboard? scouting;
  YouthPipelineSnapshot? youthPipeline;

  ClubOpsAdminSnapshot? adminSummary;
  ClubFinanceAnalyticsSnapshot? financeAnalytics;
  SponsorshipAnalyticsSnapshot? sponsorshipAnalytics;
  AcademyAnalyticsSnapshot? academyAnalytics;
  ScoutingAnalyticsSnapshot? scoutingAnalytics;

  bool get hasClubData =>
      finance != null ||
      sponsorships != null ||
      academy != null ||
      scouting != null ||
      youthPipeline != null;

  bool get hasAdminData =>
      adminSummary != null ||
      financeAnalytics != null ||
      sponsorshipAnalytics != null ||
      academyAnalytics != null ||
      scoutingAnalytics != null;

  String get displayClubName =>
      finance?.clubName ??
      sponsorships?.clubName ??
      academy?.clubName ??
      scouting?.clubName ??
      clubName ??
      clubId
          .split('-')
          .where((String fragment) => fragment.isNotEmpty)
          .map((String fragment) =>
              '${fragment[0].toUpperCase()}${fragment.substring(1)}')
          .join(' ');

  Future<void> loadClubData({bool force = false}) async {
    if (isLoadingClubData) {
      return;
    }
    if (hasClubData && !force) {
      return;
    }
    final int requestId = _clubGate.begin();
    isLoadingClubData = true;
    clubErrorMessage = null;
    notifyListeners();

    try {
      final List<Object?> payload = await Future.wait<Object?>(<Future<Object?>>[
        _api.fetchFinance(clubId: clubId, clubName: clubName),
        _api.fetchSponsorships(clubId: clubId, clubName: clubName),
        _api.fetchAcademy(clubId: clubId, clubName: clubName),
        _api.fetchScouting(clubId: clubId, clubName: clubName),
        _api.fetchYouthPipeline(clubId: clubId, clubName: clubName),
      ]);
      if (!_clubGate.isActive(requestId)) {
        return;
      }
      finance = payload[0] as ClubFinanceSnapshot;
      sponsorships = payload[1] as SponsorshipDashboard;
      academy = payload[2] as AcademyDashboard;
      scouting = payload[3] as ScoutingDashboard;
      youthPipeline = payload[4] as YouthPipelineSnapshot;
      clubErrorMessage = null;
    } catch (error) {
      if (_clubGate.isActive(requestId)) {
        clubErrorMessage = AppFeedback.messageFor(error);
      }
    } finally {
      if (_clubGate.isActive(requestId)) {
        isLoadingClubData = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadAdminData({bool force = false}) async {
    if (isLoadingAdminData) {
      return;
    }
    if (hasAdminData && !force) {
      return;
    }
    final int requestId = _adminGate.begin();
    isLoadingAdminData = true;
    adminErrorMessage = null;
    notifyListeners();

    try {
      final List<Object?> payload = await Future.wait<Object?>(<Future<Object?>>[
        _api.fetchClubOpsAdmin(),
        _api.fetchFinanceAnalytics(),
        _api.fetchSponsorshipAnalytics(),
        _api.fetchAcademyAnalytics(),
        _api.fetchScoutingAnalytics(),
      ]);
      if (!_adminGate.isActive(requestId)) {
        return;
      }
      adminSummary = payload[0] as ClubOpsAdminSnapshot;
      financeAnalytics = payload[1] as ClubFinanceAnalyticsSnapshot;
      sponsorshipAnalytics = payload[2] as SponsorshipAnalyticsSnapshot;
      academyAnalytics = payload[3] as AcademyAnalyticsSnapshot;
      scoutingAnalytics = payload[4] as ScoutingAnalyticsSnapshot;
      adminErrorMessage = null;
    } catch (error) {
      if (_adminGate.isActive(requestId)) {
        adminErrorMessage = AppFeedback.messageFor(error);
      }
    } finally {
      if (_adminGate.isActive(requestId)) {
        isLoadingAdminData = false;
        notifyListeners();
      }
    }
  }

  Future<void> refreshClubData() => loadClubData(force: true);

  Future<void> refreshAdminData() => loadAdminData(force: true);

  SponsorshipContract? contractById(String contractId) {
    for (final SponsorshipContract contract
        in sponsorships?.contracts ?? const <SponsorshipContract>[]) {
      if (contract.id == contractId) {
        return contract;
      }
    }
    return null;
  }

  AcademyPlayer? playerById(String playerId) {
    for (final AcademyPlayer player
        in academy?.players ?? const <AcademyPlayer>[]) {
      if (player.id == playerId) {
        return player;
      }
    }
    return null;
  }

  Prospect? prospectById(String prospectId) {
    for (final Prospect prospect
        in scouting?.prospects ?? const <Prospect>[]) {
      if (prospect.id == prospectId) {
        return prospect;
      }
    }
    return null;
  }

  ProspectReport? reportForProspect(String prospectId) {
    for (final ProspectReport report
        in scouting?.reports ?? const <ProspectReport>[]) {
      if (report.prospectId == prospectId) {
        return report;
      }
    }
    return null;
  }
}
