import 'package:flutter/foundation.dart';
import 'package:gte_frontend/data/gte_models.dart';

@immutable
class GtexGlobalSearchResult {
  const GtexGlobalSearchResult({
    required this.type,
    required this.id,
    required this.title,
    required this.subtitle,
    required this.imageUrl,
    required this.route,
    required this.score,
    required this.permissionRequired,
    required this.metadata,
  });

  final String type;
  final String id;
  final String title;
  final String subtitle;
  final String? imageUrl;
  final String route;
  final double score;
  final String? permissionRequired;
  final Map<String, Object?> metadata;

  bool get adminOnly => permissionRequired == 'admin';

  factory GtexGlobalSearchResult.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'global search result',
    );
    return GtexGlobalSearchResult(
      type: GteJson.string(json, const <String>['type']),
      id: GteJson.string(json, const <String>['id']),
      title: GteJson.string(json, const <String>['title']),
      subtitle: GteJson.string(json, const <String>['subtitle'], fallback: ''),
      imageUrl: GteJson.stringOrNull(json, const <String>[
        'image_url',
        'imageUrl',
      ]),
      route: GteJson.string(json, const <String>[
        'route',
      ], fallback: '/app/home'),
      score: GteJson.number(json, const <String>['score']),
      permissionRequired: GteJson.stringOrNull(json, const <String>[
        'permission_required',
        'permissionRequired',
      ]),
      metadata: GteJson.map(
        json,
        keys: const <String>['metadata'],
        fallback: const <String, Object?>{},
      ),
    );
  }
}

String gtexGlobalSearchTypeLabel(String type) {
  final String normalized = type.replaceAll('_', ' ').trim();
  if (normalized.isEmpty) {
    return type;
  }
  return normalized
      .split(RegExp(r'\s+'))
      .map(
        (String part) =>
            part.isEmpty
                ? part
                : '${part[0].toUpperCase()}${part.substring(1)}',
      )
      .join(' ');
}

String gtexCanonicalGlobalSearchRoute(String route, {required bool isAdmin}) {
  final String trimmed = route.trim();
  if (trimmed.isEmpty) {
    return '/app/home';
  }
  final Uri? parsed = Uri.tryParse(trimmed);
  Uri uri =
      parsed ?? Uri(path: trimmed.startsWith('/') ? trimmed : '/$trimmed');
  if (uri.hasScheme || uri.hasAuthority) {
    uri = Uri(path: uri.path, query: uri.query.isEmpty ? null : uri.query);
  }
  final String path = uri.path.trim().isEmpty ? '/app/home' : uri.path;
  final String canonicalPath = switch (path.toLowerCase()) {
    '/broadcast' => '/broadcast/live',
    '/admin/ops' ||
    '/admin/risk-ops' ||
    '/admin/policies' ||
    '/admin/moderation' ||
    '/admin/disputes' ||
    '/admin/ops/audit' => '/admin/trust-ops',
    _ => path,
  };
  if (canonicalPath.toLowerCase().startsWith('/admin') && !isAdmin) {
    return '/app/home';
  }
  return uri.replace(path: canonicalPath).toString();
}
