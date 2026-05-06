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
  final String? canonical = gteApiCanonicalPathByAlias[normalized];
  if (canonical == null) {
    throw StateError(
      'Endpoint $normalized is not present in shared/api_contract.json.',
    );
  }
  return canonical;
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
