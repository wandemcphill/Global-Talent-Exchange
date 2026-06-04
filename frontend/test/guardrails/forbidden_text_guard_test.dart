import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/navigation/app_destinations.dart';

void main() {
  group('frontend forbidden text guardrails', () {
    test('production frontend does not expose forbidden provider text', () {
      final List<_ScanHit> hits = _scanProductionSources(<_ForbiddenRule>[
        _ForbiddenRule(
          name: 'retired payment provider exposure',
          pattern: RegExp(r'\bpaystack\b', caseSensitive: false),
          guidance:
              'Payment provider names must stay behind backend rail internals, '
              'not frontend product copy or canonical route contracts.',
        ),
      ]);

      expect(hits, isEmpty, reason: _formatHits(hits));
    });

    test('production frontend exposes only supported payment rails', () {
      final List<_ScanHit> hits = _scanProductionSources(<_ForbiddenRule>[
        _ForbiddenRule(
          name: 'unsupported payment rail exposure',
          pattern: RegExp(
            r'\b(?:flutterwave|paypal|monnify|opay|coinbase|'
            r'mobile\s+money|m-?pesa)\b|'
            r'\b(?:payment|provider|checkout|gateway|rail)s?\b[^\n]{0,48}\b'
            r'(?:stripe|crypto(?:currency)?)\b|'
            r'\b(?:stripe|crypto(?:currency)?)\b[^\n]{0,48}\b'
            r'(?:payment|provider|checkout|gateway|rail)s?\b',
            caseSensitive: false,
          ),
          guidance:
              'Production payment rails must be KoraPay or manual bank '
              'transfer only.',
        ),
      ]);

      expect(hits, isEmpty, reason: _formatHits(hits));
    });

    test('production frontend does not promote legacy Unity routes', () {
      final List<_ScanHit> hits = _scanProductionSources(<_ForbiddenRule>[
        _ForbiddenRule(
          name: 'legacy runtime endpoint exposure',
          pattern: RegExp(r'''/(?:api/)?matches?/[^"'\s]+/unity-access\b'''),
          guidance:
              'Legacy runtime access endpoints must not be surfaced from the '
              'frontend launch app.',
        ),
        _ForbiddenRule(
          name: 'legacy runtime token exposure',
          pattern: RegExp(r'\bunity-access\b', caseSensitive: false),
          guidance:
              'Legacy runtime access wording must stay out of frontend source.',
        ),
        _ForbiddenRule(
          name: 'verify_unity_routes command exposure',
          pattern: RegExp(r'\bverify_unity_routes\b', caseSensitive: false),
          guidance:
              'The removed Unity route verifier must not be reintroduced as a '
              'frontend guard or user-facing command.',
        ),
        _ForbiddenRule(
          name: 'legacy runtime promotion',
          pattern: RegExp(
            r'\bunity\b|unity_match_3d|match_3d/unity_activity',
            caseSensitive: false,
          ),
          guidance:
              'Legacy runtime identifiers are allowed only inside documented, '
              'deprecated quarantine code paths.',
          allow: _isDocumentedLegacy3dQuarantine,
        ),
      ]);

      expect(hits, isEmpty, reason: _formatHits(hits));
    });

    test('production frontend does not promote blocked 3D routes or CTAs', () {
      final List<_ScanHit> hits = _scanProductionSources(<_ForbiddenRule>[
        _ForbiddenRule(
          name: 'production 3D match route',
          pattern: RegExp(
            r'''["']/(?:matches/3d|matches/native-3d)(?::|/|["'])''',
            caseSensitive: false,
          ),
          guidance:
              'Launch routing must keep 3D match routes quarantined behind '
              'internal legacy paths or blocked disclosure screens.',
        ),
        _ForbiddenRule(
          name: '3D runtime badge label',
          pattern: RegExp(r'\b(?:FLUTTER_3D|NATIVE_3D|PSEUDO_3D)\b'),
          guidance:
              'Runtime labels must not promote retired rendering modes as '
              'production match surfaces.',
        ),
        _ForbiddenRule(
          name: 'promoted 3D CTA',
          pattern: RegExp(
            r'\b(?:open|launch|watch|view|start|play|enter)\s+3d\b',
            caseSensitive: false,
          ),
          guidance:
              'CTA copy must send launch users to the 2D tactical viewer, not '
              'a promoted 3D route.',
        ),
        _ForbiddenRule(
          name: 'promoted 3D surface copy',
          pattern: RegExp(
            r'\b(?:3d lane|3d match viewer|native 3d|flutter 3d)\b',
            caseSensitive: false,
          ),
          guidance:
              '3D copy is allowed only as blocked/deprecated internal '
              'quarantine language, not production surface promotion.',
          allow: _isDocumentedLegacy3dQuarantine,
        ),
      ]);

      expect(hits, isEmpty, reason: _formatHits(hits));
    });

    test('production modules cannot import quarantined 3D sources', () {
      final RegExp legacy3dImportPattern = RegExp(
        r'''^\s*(?:import|export)\s+['"][^'"]*(?:package:gte_frontend/features/3d/|features/3d/|\.\.?/3d/)[^'"]*['"]''',
      );
      final List<String> hits = <String>[];

      for (final File file in _dartFilesUnder('lib')) {
        final String path = _normalizedPath(file.path);
        if (path.startsWith('lib/features/3d/')) {
          continue;
        }

        final List<String> lines = file.readAsStringSync().split('\n');
        for (int index = 0; index < lines.length; index += 1) {
          final String line = lines[index];
          if (legacy3dImportPattern.hasMatch(line)) {
            hits.add('$path:${index + 1} ${line.trim()}');
          }
        }
      }

      expect(
        hits,
        isEmpty,
        reason:
            'Legacy 3D code is quarantined under lib/features/3d and must '
            'not be imported by canonical production modules.\n'
            '${hits.join('\n')}',
      );
    });

    test(
      'production frontend does not expose deprecated dimensional labels',
      () {
        final List<_ScanHit> hits = _scanProductionSources(<_ForbiddenRule>[
          _ForbiddenRule(
            name: 'deprecated dimensional user-facing label',
            pattern: RegExp(r'\bpseudo[- ]3d\b', caseSensitive: false),
            guidance:
                'Deprecated dimensional wording may exist only as an internal '
                'identifier; visible launch copy must say 2D.',
          ),
        ]);

        expect(hits, isEmpty, reason: _formatHits(hits));
      },
    );

    test('production frontend does not ship fake authority data', () {
      final List<_ScanHit> hits = _scanProductionSources(<_ForbiddenRule>[
        _ForbiddenRule(
          name: 'fake production authority data',
          pattern: RegExp(
            r'\b(?:fake|mock|dummy|sample|hardcoded|synthetic|'
            r'client[- ]generated|client[- ]side|local[- ]only|fallback)\s+'
            r'(?:balances?|scores?|bids?|rankings?|fixtures?)\b|'
            r'\b(?:balances?|scores?|bids?|rankings?|fixtures?)\s+'
            r'(?:fake|mock|dummy|sample|hardcoded|synthetic|'
            r'client[- ]generated|client[- ]side|local[- ]only|fallback)\b',
            caseSensitive: false,
          ),
          guidance:
              'Balances, scores, bids, rankings, and fixtures must be '
              'backend-owned in production surfaces.',
          allow: _isDisabledAuthorityReference,
        ),
      ]);

      expect(hits, isEmpty, reason: _formatHits(hits));
    });

    test('production frontend cannot activate fixture mode', () {
      final List<_ScanHit> hits = _scanProductionSources(<_ForbiddenRule>[
        _ForbiddenRule(
          name: 'production fixture mode activation',
          pattern: RegExp(
            r'\b(?:kFixtureMode|GtexFixtureMode|fixtureMode|'
            r'enableFixtureMode|enableCapitalFixtures)\b\s*[:=]\s*true\b|'
            r'\b(?:mode|backendMode)\s*:\s*GteBackendMode\.fixture\b|'
            r'\ballowFixtureMode\s*\?\s*GteBackendMode\.fixture\b|'
            r'\bbool\.fromEnvironment\([^\n)]*(?:fixtureMode|FixtureMode|'
            r'GtexFixtureMode|kFixtureMode)[^\n)]*defaultValue\s*:\s*true',
            caseSensitive: false,
          ),
          guidance:
              'Fixture mode may exist for tests, but production source must '
              'not enable it or default it on.',
          allow: _isFixtureModeTestOnlyReference,
        ),
      ]);

      expect(hits, isEmpty, reason: _formatHits(hits));
    });

    test('capital wallet presentation stays behind wallet facade', () {
      final List<_ScanHit> hits = _scanProductionSources(<_ForbiddenRule>[
        _ForbiddenRule(
          name: 'direct shared exchange API in capital wallet presentation',
          pattern: RegExp(
            r'\b(?:widget\.)?controller\.api\.',
            caseSensitive: false,
          ),
          guidance:
              'Capital wallet presentation must use CapitalWalletApi or '
              'controller.walletApi, not shared exchange transport calls.',
        ),
      ], relativeRoot: 'lib/features/capital/wallet/presentation');

      expect(hits, isEmpty, reason: _formatHits(hits));
    });

    test('capital disputes presentation stays behind dispute facade', () {
      final List<_ScanHit> hits = _scanProductionSources(<_ForbiddenRule>[
        _ForbiddenRule(
          name: 'direct shared exchange API in capital disputes presentation',
          pattern: RegExp(
            r'\b(?:widget\.)?controller\.api\.',
            caseSensitive: false,
          ),
          guidance:
              'Capital disputes presentation must use CapitalDisputeApi or '
              'controller.disputeApi, not shared exchange transport calls.',
        ),
      ], relativeRoot: 'lib/features/capital/disputes/presentation');

      expect(hits, isEmpty, reason: _formatHits(hits));
    });

    test('capital features stay behind capital facades', () {
      final List<_ScanHit> hits = _scanProductionSources(<_ForbiddenRule>[
        _ForbiddenRule(
          name: 'direct shared exchange API in capital feature',
          pattern: RegExp(
            r'\b(?:widget\.)?controller\.api\.',
            caseSensitive: false,
          ),
          guidance:
              'Capital features must use capital-owned facades instead of '
              'shared exchange transport calls.',
        ),
      ], relativeRoot: 'lib/features/capital');

      expect(hits, isEmpty, reason: _formatHits(hits));
    });

    test(
      'internal match runtime routes stay hidden from launch navigation',
      () {
        final List<AppRouteSurface> runtimeSurfaces =
            appRouteInventory
                .where(
                  (AppRouteSurface surface) =>
                      surface.location == AppRoutes.legacyMatchRuntime ||
                      surface.location == AppRoutes.legacyBlockedMatchRuntime,
                )
                .toList();

        expect(runtimeSurfaces, hasLength(2));

        for (final AppRouteSurface surface in runtimeSurfaces) {
          expect(surface.state, AppRouteSurfaceState.hidden);
          expect(surface.primaryNav, isFalse);
          expect(surface.quickAction, isFalse);
          expect(surface.showInPrimaryNav, isFalse);
          expect(surface.showInQuickActions, isFalse);
          expect(
            RegExp(
              r'\b(?:3d|unity|native 3d|flutter 3d|pseudo[- ]3d)\b',
              caseSensitive: false,
            ).hasMatch('${surface.label} ${surface.summary}'),
            isFalse,
            reason:
                'Hidden internal runtime routes must not advertise legacy '
                'rendering modes through inventory copy.',
          );
        }
      },
    );
  });
}

typedef _AllowHit = bool Function(_ScanHit hit, String fileSource);

class _ForbiddenRule {
  const _ForbiddenRule({
    required this.name,
    required this.pattern,
    required this.guidance,
    this.allow,
  });

  final String name;
  final RegExp pattern;
  final String guidance;
  final _AllowHit? allow;
}

class _ScanHit {
  const _ScanHit({
    required this.path,
    required this.lineNumber,
    required this.columnNumber,
    required this.match,
    required this.rule,
  });

  final String path;
  final int lineNumber;
  final int columnNumber;
  final String match;
  final _ForbiddenRule rule;
}

List<_ScanHit> _scanProductionSources(
  List<_ForbiddenRule> rules, {
  String relativeRoot = 'lib',
}) {
  final List<_ScanHit> hits = <_ScanHit>[];
  for (final File file in _dartFilesUnder(relativeRoot)) {
    final String source = file.readAsStringSync();
    final List<String> lines = source.split('\n');
    for (int lineIndex = 0; lineIndex < lines.length; lineIndex += 1) {
      final String line = lines[lineIndex];
      for (final _ForbiddenRule rule in rules) {
        for (final RegExpMatch match in rule.pattern.allMatches(line)) {
          final _ScanHit hit = _ScanHit(
            path: _normalizedPath(file.path),
            lineNumber: lineIndex + 1,
            columnNumber: match.start + 1,
            match: match.group(0) ?? '',
            rule: rule,
          );
          if (rule.allow?.call(hit, source) ?? false) {
            continue;
          }
          hits.add(hit);
        }
      }
    }
  }
  return hits;
}

bool _isDocumentedLegacy3dQuarantine(_ScanHit hit, String fileSource) {
  final bool isLegacyRuntimeFile =
      hit.path ==
      'lib/features/3d/widgets/match_3d/native_match_3d_surface.dart';
  if (!isLegacyRuntimeFile) {
    return false;
  }
  final String lowerSource = fileSource.toLowerCase();
  return fileSource.contains('@Deprecated') &&
      fileSource.contains('kGtexLegacy3dRuntimeEnabled') &&
      lowerSource.contains('quarantined');
}

bool _isDisabledAuthorityReference(_ScanHit hit, String fileSource) {
  final List<String> lines = fileSource.split('\n');
  if (hit.lineNumber < 1 || hit.lineNumber > lines.length) {
    return false;
  }
  final String line = lines[hit.lineNumber - 1].toLowerCase();
  if (!RegExp(r'\b(?:fake|mock|fixture|fallback)\b').hasMatch(line)) {
    return false;
  }
  return line.contains(' disabled') ||
      line.contains(' is disabled') ||
      line.contains('disabled.') ||
      line.contains('blocked') ||
      line.contains('reject') ||
      line.contains('never ') ||
      line.contains(' no ') ||
      line.contains(' not ') ||
      line.contains('without ') ||
      line.contains('removed');
}

bool _isFixtureModeTestOnlyReference(_ScanHit hit, String fileSource) {
  if (hit.path == 'lib/app/gte_app_config.dart') {
    return fileSource.contains('allowFixtureMode: isFlutterTestRuntime') &&
        fileSource.contains(
          'return allowFixtureMode ? GteBackendMode.fixture : GteBackendMode.live',
        );
  }

  final List<String> lines = fileSource.split('\n');
  final int index = hit.lineNumber - 1;
  final int start = index < 32 ? 0 : index - 32;
  final String context =
      lines
          .sublist(start, index + 1 > lines.length ? lines.length : index + 1)
          .join('\n')
          .toLowerCase();
  if (RegExp(r'factory\s+\w+(?:\.\w+)?\.fixture\b').hasMatch(context)) {
    return true;
  }
  if (hit.path == 'lib/data/gte_mock_api.dart' &&
      context.contains('factory gtemockapi.capitalfixtures')) {
    return true;
  }
  return false;
}

List<File> _dartFilesUnder(String relativeRoot) {
  final Directory root = Directory(relativeRoot);
  if (!root.existsSync()) {
    throw TestFailure('Expected scan root to exist: $relativeRoot');
  }
  return root
      .listSync(recursive: true, followLinks: false)
      .whereType<File>()
      .where((File file) => file.path.endsWith('.dart'))
      .toList()
    ..sort((File left, File right) => left.path.compareTo(right.path));
}

String _formatHits(List<_ScanHit> hits) {
  if (hits.isEmpty) {
    return '';
  }
  return hits
      .map(
        (_ScanHit hit) =>
            '${hit.path}:${hit.lineNumber}:${hit.columnNumber} '
            '${hit.rule.name} matched "${hit.match}". ${hit.rule.guidance}',
      )
      .join('\n');
}

String _normalizedPath(String path) {
  return path.replaceAll('\\', '/');
}
