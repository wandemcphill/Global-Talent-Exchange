import 'package:flutter/material.dart';

import '../../../ui_gtex/ui_gtex.dart';

enum GtexTrustModule { wallet, orders, kyc, disputes }

enum GtexTrustStatus { healthy, pending, attention, blocked, resolved }

class GtexTrustOpsState {
  const GtexTrustOpsState({
    required this.wallet,
    required this.transactions,
    required this.orders,
    required this.kycCases,
    required this.disputes,
    this.operationsReadiness,
  });

  final GtexWalletSummary wallet;
  final List<GtexTransactionRecord> transactions;
  final List<GtexOrderRecord> orders;
  final List<GtexKycCaseRecord> kycCases;
  final List<GtexDisputeRecord> disputes;
  final GtexOperationsReadinessSnapshot? operationsReadiness;

  int get pendingKycCount =>
      kycCases
          .where(
            (GtexKycCaseRecord item) => item.status == GtexTrustStatus.pending,
          )
          .length;
  int get openDisputeCount =>
      disputes
          .where(
            (GtexDisputeRecord item) => item.status != GtexTrustStatus.resolved,
          )
          .length;
  int get pendingOrderCount =>
      orders
          .where(
            (GtexOrderRecord item) => item.status == GtexTrustStatus.pending,
          )
          .length;
}

class GtexOperationsReadinessSnapshot {
  const GtexOperationsReadinessSnapshot({
    required this.generatedAt,
    required this.status,
    required this.totals,
    required this.queues,
    required this.launchGates,
  });

  final DateTime generatedAt;
  final String status;
  final Map<String, Object?> totals;
  final List<GtexOperationsReadinessQueue> queues;
  final List<GtexOperationsLaunchGate> launchGates;

  factory GtexOperationsReadinessSnapshot.fromJson(Map<String, Object?> json) {
    return GtexOperationsReadinessSnapshot(
      generatedAt:
          DateTime.tryParse(_readString(json['generated_at'])) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      status: _readString(json['status'], fallback: 'ok'),
      totals: _readMap(json['totals']),
      queues: _readList(
        json['queues'],
      ).map(GtexOperationsReadinessQueue.fromJson).toList(growable: false),
      launchGates: _readList(
        json['launch_gates'],
      ).map(GtexOperationsLaunchGate.fromJson).toList(growable: false),
    );
  }
}

class GtexOperationsReadinessQueue {
  const GtexOperationsReadinessQueue({
    required this.key,
    required this.title,
    required this.description,
    required this.status,
    required this.route,
    required this.owner,
    required this.metrics,
    required this.alerts,
    required this.actionRoutes,
  });

  final String key;
  final String title;
  final String description;
  final String status;
  final String? route;
  final String owner;
  final List<GtexOperationsReadinessMetric> metrics;
  final List<String> alerts;
  final List<String> actionRoutes;

  factory GtexOperationsReadinessQueue.fromJson(Map<String, Object?> json) {
    return GtexOperationsReadinessQueue(
      key: _readString(json['key']),
      title: _readString(json['title']),
      description: _readString(json['description']),
      status: _readString(json['status'], fallback: 'ok'),
      route: _readNullableString(json['route']),
      owner: _readString(json['owner']),
      metrics: _readList(
        json['metrics'],
      ).map(GtexOperationsReadinessMetric.fromJson).toList(growable: false),
      alerts: _readStringList(json['alerts']),
      actionRoutes: _readStringList(json['action_routes']),
    );
  }

  GtexOperationsReadinessMetric? metric(String key) {
    for (final GtexOperationsReadinessMetric metric in metrics) {
      if (metric.key == key) return metric;
    }
    return null;
  }
}

class GtexOperationsReadinessMetric {
  const GtexOperationsReadinessMetric({
    required this.key,
    required this.label,
    required this.value,
    required this.displayValue,
    required this.unit,
    required this.status,
    required this.route,
    required this.metadata,
  });

  final String key;
  final String label;
  final double value;
  final String displayValue;
  final String? unit;
  final String status;
  final String? route;
  final Map<String, Object?> metadata;

  factory GtexOperationsReadinessMetric.fromJson(Map<String, Object?> json) {
    return GtexOperationsReadinessMetric(
      key: _readString(json['key']),
      label: _readString(json['label']),
      value: _readDouble(json['value']),
      displayValue: _readString(json['display_value']),
      unit: _readNullableString(json['unit']),
      status: _readString(json['status'], fallback: 'ok'),
      route: _readNullableString(json['route']),
      metadata: _readMap(json['metadata']),
    );
  }
}

class GtexOperationsLaunchGate {
  const GtexOperationsLaunchGate({
    required this.featureKey,
    required this.title,
    required this.enabled,
    required this.launchState,
    required this.audience,
    required this.killSwitchEnabled,
    required this.maintenanceMessage,
    required this.route,
  });

  final String featureKey;
  final String title;
  final bool enabled;
  final String launchState;
  final String audience;
  final bool killSwitchEnabled;
  final String? maintenanceMessage;
  final String? route;

  factory GtexOperationsLaunchGate.fromJson(Map<String, Object?> json) {
    return GtexOperationsLaunchGate(
      featureKey: _readString(json['feature_key']),
      title: _readString(json['title']),
      enabled: json['enabled'] == true,
      launchState: _readString(json['launch_state'], fallback: 'public'),
      audience: _readString(json['audience'], fallback: 'global'),
      killSwitchEnabled: json['kill_switch_enabled'] == true,
      maintenanceMessage: _readNullableString(json['maintenance_message']),
      route: _readNullableString(json['route']),
    );
  }
}

class GtexWalletSummary {
  const GtexWalletSummary({
    required this.balanceCredits,
    required this.availableCredits,
    required this.pendingWithdrawalCredits,
    required this.kycStatus,
    required this.lastUpdatedLabel,
  });

  final double balanceCredits;
  final double availableCredits;
  final double pendingWithdrawalCredits;
  final String kycStatus;
  final String lastUpdatedLabel;

  String get balanceLabel => GtexTrustFormatters.credits(balanceCredits);
  String get availableLabel => GtexTrustFormatters.credits(availableCredits);
  String get pendingWithdrawalLabel =>
      GtexTrustFormatters.credits(pendingWithdrawalCredits);
}

class GtexTransactionRecord {
  const GtexTransactionRecord({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.amountCredits,
    required this.status,
    required this.timestampLabel,
    required this.type,
  });

  final String id;
  final String title;
  final String subtitle;
  final double amountCredits;
  final GtexTrustStatus status;
  final String timestampLabel;
  final String type;

  String get amountLabel => GtexTrustFormatters.signedCredits(amountCredits);
}

class GtexOrderRecord {
  const GtexOrderRecord({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.totalCredits,
    required this.status,
    required this.createdLabel,
    required this.itemCount,
  });

  final String id;
  final String title;
  final String subtitle;
  final double totalCredits;
  final GtexTrustStatus status;
  final String createdLabel;
  final int itemCount;

  String get totalLabel => GtexTrustFormatters.credits(totalCredits);
}

class GtexKycCaseRecord {
  const GtexKycCaseRecord({
    required this.id,
    required this.userName,
    required this.country,
    required this.level,
    required this.status,
    required this.submittedLabel,
    required this.riskLabel,
    required this.notes,
  });

  final String id;
  final String userName;
  final String country;
  final String level;
  final GtexTrustStatus status;
  final String submittedLabel;
  final String riskLabel;
  final String notes;
}

class GtexDisputeRecord {
  const GtexDisputeRecord({
    required this.id,
    required this.title,
    required this.counterparty,
    required this.status,
    required this.amountCredits,
    required this.openedLabel,
    required this.summary,
  });

  final String id;
  final String title;
  final String counterparty;
  final GtexTrustStatus status;
  final double amountCredits;
  final String openedLabel;
  final String summary;

  String get amountLabel => GtexTrustFormatters.credits(amountCredits);
}

class GtexTrustFormatters {
  const GtexTrustFormatters._();

  static String credits(double value) {
    final double abs = value.abs();
    if (abs >= 1000000000) {
      return '₵${(value / 1000000000).toStringAsFixed(1)}B';
    }
    if (abs >= 1000000) {
      return '₵${(value / 1000000).toStringAsFixed(1)}M';
    }
    if (abs >= 1000) {
      return '₵${(value / 1000).toStringAsFixed(1)}K';
    }
    return '₵${value.toStringAsFixed(0)}';
  }

  static String signedCredits(double value) {
    final String prefix =
        value > 0
            ? '+'
            : value < 0
            ? '-'
            : '';
    return '$prefix${credits(value.abs())}';
  }

  static Color statusColor(GtexTrustStatus status) {
    switch (status) {
      case GtexTrustStatus.healthy:
        return GtexColors.pitch;
      case GtexTrustStatus.pending:
        return GtexColors.gold;
      case GtexTrustStatus.attention:
        return GtexColors.orange;
      case GtexTrustStatus.blocked:
        return GtexColors.red;
      case GtexTrustStatus.resolved:
        return GtexColors.cyan;
    }
  }

  static String statusLabel(GtexTrustStatus status) {
    switch (status) {
      case GtexTrustStatus.healthy:
        return 'Healthy';
      case GtexTrustStatus.pending:
        return 'Pending';
      case GtexTrustStatus.attention:
        return 'Needs attention';
      case GtexTrustStatus.blocked:
        return 'Blocked';
      case GtexTrustStatus.resolved:
        return 'Resolved';
    }
  }
}

Map<String, Object?> _readMap(Object? value) {
  if (value is Map) return Map<String, Object?>.from(value);
  return const <String, Object?>{};
}

List<Map<String, Object?>> _readList(Object? value) {
  if (value is! List) return const <Map<String, Object?>>[];
  return value
      .whereType<Map>()
      .map((Map<dynamic, dynamic> item) => Map<String, Object?>.from(item))
      .toList(growable: false);
}

List<String> _readStringList(Object? value) {
  if (value is! List) return const <String>[];
  return value
      .map((Object? item) => item?.toString() ?? '')
      .where((String item) => item.isNotEmpty)
      .toList(growable: false);
}

String _readString(Object? value, {String fallback = ''}) {
  final String text = value?.toString() ?? '';
  return text.isEmpty ? fallback : text;
}

String? _readNullableString(Object? value) {
  final String text = value?.toString() ?? '';
  return text.isEmpty ? null : text;
}

double _readDouble(Object? value) {
  if (value is num) return value.toDouble();
  return double.tryParse(value?.toString() ?? '') ?? 0;
}
