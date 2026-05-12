import 'package:flutter/foundation.dart';
import 'package:gte_frontend/data/gte_models.dart';

@immutable
class GtexMatchdayEconomyOverview {
  const GtexMatchdayEconomyOverview({
    required this.generatedAt,
    required this.audience,
    required this.sections,
    required this.totals,
  });

  final DateTime? generatedAt;
  final String audience;
  final List<GtexMatchdayEconomySection> sections;
  final Map<String, Object?> totals;

  factory GtexMatchdayEconomyOverview.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'matchday economy overview',
    );
    return GtexMatchdayEconomyOverview(
      generatedAt: GteJson.dateTimeOrNull(json, const <String>[
        'generated_at',
        'generatedAt',
      ]),
      audience: GteJson.string(json, const <String>[
        'audience',
      ], fallback: 'guest'),
      sections: GteJson.typedList(json, const <String>[
        'sections',
      ], GtexMatchdayEconomySection.fromJson),
      totals: GteJson.map(
        json,
        keys: const <String>['totals'],
        fallback: const <String, Object?>{},
      ),
    );
  }

  GtexMatchdayEconomySection? section(String key) {
    for (final GtexMatchdayEconomySection item in sections) {
      if (item.key == key) {
        return item;
      }
    }
    return null;
  }
}

@immutable
class GtexMatchdayEconomySection {
  const GtexMatchdayEconomySection({
    required this.key,
    required this.title,
    required this.description,
    required this.featureKey,
    required this.route,
    required this.launchState,
    required this.enabled,
    required this.healthStatus,
    required this.metrics,
    required this.alerts,
  });

  final String key;
  final String title;
  final String description;
  final String featureKey;
  final String route;
  final String launchState;
  final bool enabled;
  final String healthStatus;
  final List<GtexMatchdayEconomyMetric> metrics;
  final List<String> alerts;

  bool get needsAttention =>
      alerts.isNotEmpty ||
      healthStatus == 'kill_switch' ||
      healthStatus == 'maintenance' ||
      healthStatus == 'paused';

  factory GtexMatchdayEconomySection.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'matchday economy section',
    );
    return GtexMatchdayEconomySection(
      key: GteJson.string(json, const <String>['key']),
      title: GteJson.string(json, const <String>['title']),
      description: GteJson.string(json, const <String>[
        'description',
      ], fallback: ''),
      featureKey: GteJson.string(json, const <String>[
        'feature_key',
        'featureKey',
      ]),
      route: GteJson.string(json, const <String>['route'], fallback: ''),
      launchState: GteJson.string(json, const <String>[
        'launch_state',
        'launchState',
      ], fallback: 'not_configured'),
      enabled: GteJson.boolean(json, const <String>['enabled']),
      healthStatus: GteJson.string(json, const <String>[
        'health_status',
        'healthStatus',
      ], fallback: 'not_configured'),
      metrics: GteJson.typedList(json, const <String>[
        'metrics',
      ], GtexMatchdayEconomyMetric.fromJson),
      alerts: GteJson.typedList(json, const <String>[
        'alerts',
      ], (Object? item) => item?.toString() ?? ''),
    );
  }
}

@immutable
class GtexMatchdayEconomyMetric {
  const GtexMatchdayEconomyMetric({
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

  factory GtexMatchdayEconomyMetric.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'matchday economy metric',
    );
    return GtexMatchdayEconomyMetric(
      key: GteJson.string(json, const <String>['key']),
      label: GteJson.string(json, const <String>['label']),
      value: GteJson.number(json, const <String>['value']),
      displayValue: GteJson.string(json, const <String>[
        'display_value',
        'displayValue',
      ]),
      unit: GteJson.stringOrNull(json, const <String>['unit']),
      status: GteJson.string(json, const <String>['status'], fallback: 'ok'),
      route: GteJson.stringOrNull(json, const <String>['route']),
      metadata: GteJson.map(
        json,
        keys: const <String>['metadata'],
        fallback: const <String, Object?>{},
      ),
    );
  }
}

@immutable
class GtexMatchdayEconomyAction {
  const GtexMatchdayEconomyAction({
    required this.action,
    required this.status,
    required this.resourceId,
    required this.message,
    required this.metrics,
    required this.metadata,
  });

  final String action;
  final String status;
  final String resourceId;
  final String message;
  final Map<String, double> metrics;
  final Map<String, Object?> metadata;

  bool get succeeded => status == 'ok' || status == 'completed';

  factory GtexMatchdayEconomyAction.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'matchday economy action',
    );
    return GtexMatchdayEconomyAction(
      action: GteJson.string(json, const <String>['action']),
      status: GteJson.string(json, const <String>['status'], fallback: 'ok'),
      resourceId: GteJson.string(json, const <String>[
        'resource_id',
        'resourceId',
      ]),
      message: GteJson.string(json, const <String>['message'], fallback: ''),
      metrics: _numberMap(
        GteJson.value(json, const <String>['metrics']) ??
            const <String, Object?>{},
      ),
      metadata: GteJson.map(
        json,
        keys: const <String>['metadata'],
        fallback: const <String, Object?>{},
      ),
    );
  }
}

Map<String, double> _numberMap(Object? value) {
  if (value is! Map) {
    return const <String, double>{};
  }
  final Map<String, double> parsed = <String, double>{};
  value.forEach((Object? key, Object? rawValue) {
    if (key == null) {
      return;
    }
    final double? number =
        rawValue is num ? rawValue.toDouble() : double.tryParse('$rawValue');
    if (number != null) {
      parsed[key.toString()] = number;
    }
  });
  return Map<String, double>.unmodifiable(parsed);
}
