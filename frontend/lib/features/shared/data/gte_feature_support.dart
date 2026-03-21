import '../../../data/gte_api_repository.dart';
import '../../../data/gte_authed_api.dart';
import '../../../data/gte_http_transport.dart';
import '../../../data/gte_models.dart';

typedef JsonMap = Map<String, Object?>;

GteAuthedApi createFeatureApi({
  required String baseUrl,
  required GteBackendMode mode,
  required String? accessToken,
}) {
  return GteAuthedApi(
    config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
    transport: GteHttpTransport(),
    accessToken: accessToken,
    mode: mode,
  );
}

JsonMap jsonMap(
  Object? value, {
  String label = 'payload',
  JsonMap fallback = const <String, Object?>{},
}) {
  return GteJson.map(value, label: label, fallback: fallback);
}

JsonMap? jsonMapOrNull(Object? value) {
  if (value == null) {
    return null;
  }
  return GteJson.map(value);
}

List<Object?> jsonList(Object? value, {String label = 'payload'}) {
  return GteJson.list(value, label: label);
}

List<T> parseList<T>(
  Object? value,
  T Function(Object? value) parser, {
  String label = 'payload',
}) {
  return jsonList(value, label: label).map(parser).toList(growable: false);
}

List<JsonMap> jsonMapList(Object? value, {String label = 'payload'}) {
  return jsonList(value, label: label)
      .map((Object? item) => jsonMap(item, label: label))
      .toList(growable: false);
}

String? stringOrNullValue(Object? value) {
  if (value == null) {
    return null;
  }
  final String parsed = value.toString().trim();
  return parsed.isEmpty ? null : parsed;
}

String stringValue(
  Object? value, {
  String fallback = '',
}) {
  return stringOrNullValue(value) ?? fallback;
}

double numberValue(
  Object? value, {
  double fallback = 0,
}) {
  if (value == null) {
    return fallback;
  }
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value.toString()) ?? fallback;
}

int intValue(
  Object? value, {
  int fallback = 0,
}) {
  if (value == null) {
    return fallback;
  }
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  return int.tryParse(value.toString()) ?? fallback;
}

bool boolValue(
  Object? value, {
  bool fallback = false,
}) {
  if (value == null) {
    return fallback;
  }
  if (value is bool) {
    return value;
  }
  final String normalized = value.toString().trim().toLowerCase();
  if (<String>{'1', 'true', 'yes', 'on'}.contains(normalized)) {
    return true;
  }
  if (<String>{'0', 'false', 'no', 'off'}.contains(normalized)) {
    return false;
  }
  return fallback;
}

DateTime? dateTimeValue(Object? value) {
  if (value == null) {
    return null;
  }
  if (value is DateTime) {
    return value.toUtc();
  }
  return DateTime.tryParse(value.toString())?.toUtc();
}

String? dateQueryValue(DateTime? value) {
  if (value == null) {
    return null;
  }
  return value.toUtc().toIso8601String().split('T').first;
}

List<String> stringListValue(Object? value) {
  return jsonList(value)
      .map(stringValue)
      .where((String item) => item.isNotEmpty)
      .toList(growable: false);
}

Map<String, Object?> compactQuery(Map<String, Object?> input) {
  final Map<String, Object?> query = <String, Object?>{};
  for (final MapEntry<String, Object?> entry in input.entries) {
    final Object? value = entry.value;
    if (value == null) {
      continue;
    }
    if (value is String && value.trim().isEmpty) {
      continue;
    }
    if (value is Iterable<Object?> && value.isEmpty) {
      continue;
    }
    query[entry.key] = value;
  }
  return query;
}

Map<String, dynamic> dynamicMap(JsonMap value) {
  return Map<String, dynamic>.from(value);
}

bool isNotFoundError(Object error) {
  return error is GteApiException && error.type == GteApiErrorType.notFound;
}
