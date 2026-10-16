import 'generated/gte_api_contract.g.dart';

String gteCanonicalApiPath(String path) {
  final String trimmed = path.trim();
  if (trimmed.isEmpty) {
    return '/api/v2';
  }
  if (_hasUriScheme(trimmed)) {
    return trimmed;
  }
  final String normalized = _normalizePath(trimmed);
  final String? canonical =
      gteApiCanonicalPathByAlias[normalized] ??
      _resolveTemplatedCanonical(normalized);
  if (canonical == null) {
    throw StateError(
      'Endpoint $normalized is not present in shared/api_contract.json.',
    );
  }
  return canonical;
}

String? _resolveTemplatedCanonical(String normalized) {
  for (final MapEntry<String, String> entry
      in gteApiCanonicalPathByAlias.entries) {
    final String alias = entry.key;
    if (!alias.contains('{')) {
      continue;
    }
    if (_matchesTemplatedPath(alias, normalized)) {
      return _materializeCanonical(entry.value, alias, normalized);
    }
  }
  return null;
}

bool _matchesTemplatedPath(String template, String actual) {
  final List<String> templateParts = template.split('/');
  final List<String> actualParts = actual.split('/');
  if (templateParts.length != actualParts.length) {
    return false;
  }
  for (int index = 0; index < templateParts.length; index += 1) {
    final String templatePart = templateParts[index];
    final String actualPart = actualParts[index];
    final bool placeholder =
        templatePart.startsWith('{') && templatePart.endsWith('}');
    if (!placeholder && templatePart != actualPart) {
      return false;
    }
  }
  return true;
}

String _materializeCanonical(
  String canonicalTemplate,
  String aliasTemplate,
  String actual,
) {
  final List<String> aliasParts = aliasTemplate.split('/');
  final List<String> actualParts = actual.split('/');
  final Map<String, String> values = <String, String>{};
  for (int index = 0; index < aliasParts.length; index += 1) {
    final String aliasPart = aliasParts[index];
    if (aliasPart.startsWith('{') && aliasPart.endsWith('}')) {
      values[aliasPart.substring(1, aliasPart.length - 1)] = actualParts[index];
    }
  }
  String resolved = canonicalTemplate;
  values.forEach((String key, String value) {
    resolved = resolved.replaceAll('{$key}', value);
  });
  return resolved;
}

bool gteIsContractExemptPath(String path) {
  final String normalized = _normalizePath(path);
  if (gteApiPublicExemptPaths.contains(normalized)) {
    return true;
  }
  return gteApiPublicExemptPrefixes.any(
    (String prefix) =>
        normalized == prefix || normalized.startsWith('$prefix/'),
  );
}

Map<String, String> gteVersionedApiHeaders([Map<String, String>? existing]) {
  final Map<String, String> headers = <String, String>{
    if (existing != null) ...existing,
  };
  headers.putIfAbsent(gteApiVersionHeaderName, () => gteApiVersionHeaderValue);
  return headers;
}

bool _hasUriScheme(String path) {
  return path.startsWith('http://') ||
      path.startsWith('https://') ||
      path.startsWith('ws://') ||
      path.startsWith('wss://');
}

String _normalizePath(String path) {
  if (path.isEmpty) {
    return '/';
  }
  return path.startsWith('/') ? path : '/$path';
}
