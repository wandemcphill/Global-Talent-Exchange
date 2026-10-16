import 'package:gte_frontend/data/gte_models.dart';

class RiskOverview {
  const RiskOverview({
    required this.openAmlCases,
    required this.openFraudCases,
    required this.openSystemEvents,
    required this.highRiskUsers,
    required this.activeScans,
    required this.lastScanSummary,
  });

  final int openAmlCases;
  final int openFraudCases;
  final int openSystemEvents;
  final int highRiskUsers;
  final int activeScans;
  final String? lastScanSummary;

  factory RiskOverview.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'risk overview');
    return RiskOverview(
      openAmlCases: GteJson.integer(
          json, <String>['open_aml_cases', 'openAmlCases'],
          fallback: 0),
      openFraudCases: GteJson.integer(
          json, <String>['open_fraud_cases', 'openFraudCases'],
          fallback: 0),
      openSystemEvents: GteJson.integer(
          json, <String>['open_system_events', 'openSystemEvents'],
          fallback: 0),
      highRiskUsers: GteJson.integer(
          json, <String>['high_risk_users', 'highRiskUsers'],
          fallback: 0),
      activeScans: GteJson.integer(
          json, <String>['active_scans', 'activeScans'],
          fallback: 0),
      lastScanSummary:
          GteJson.stringOrNull(json, <String>['last_scan_summary', 'lastScanSummary']),
    );
  }
}
