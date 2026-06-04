import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/data/live_match_fixtures.dart';
import 'package:gte_frontend/features/match_center/legacy_match_runtime_blocked_screen.dart';
import 'package:gte_frontend/features/match_center/match_center.dart';
import 'package:gte_frontend/features/match_center/blocked_match_runtime_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  group('Thread 3 football operations acceptance scan', () {
    test('canonical view parser collapses legacy 3D requests to 2D', () {
      for (final String raw in <String>[
        '3d',
        'pseudo3d',
        'pseudo_3d',
        'native_3d',
        'unity',
        '2d',
        'broadcast',
        '',
      ]) {
        expect(
          gtexMatchViewTypeFromString(raw),
          GtexMatchViewType.twoD,
          reason: '$raw must not open an alternate production viewer lane.',
        );
      }

      expect(GtexMatchViewType.values, <GtexMatchViewType>[
        GtexMatchViewType.twoD,
      ]);
      expect(GtexMatchViewType.twoD.label, '2D');
      expect(GtexMatchViewType.twoD.canonical, GtexMatchViewType.twoD);
    });

    testWidgets('legacy advanced routes render blocked 2D-only guidance', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(
        _app(const LegacyMatchRuntimeBlockedScreen(matchKey: 'm-1')),
      );

      expect(find.text('Route blocked'), findsWidgets);
      expect(find.textContaining('2D tactical viewer'), findsWidgets);
      expect(find.textContaining(_promotionCopyPattern), findsNothing);

      await tester.pumpWidget(_app(const BlockedMatchRuntimeScreen()));

      expect(find.text('Route blocked'), findsWidgets);
      expect(find.textContaining('2D tactical viewer'), findsWidgets);
      expect(find.textContaining(_promotionCopyPattern), findsNothing);
    });

    testWidgets('canonical 2D surface holds at mobile and desktop widths', (
      WidgetTester tester,
    ) async {
      for (final Size viewport in <Size>[
        const Size(390, 844),
        const Size(1280, 900),
      ]) {
        await _setViewport(tester, viewport);
        await tester.pumpWidget(
          _app(
            SingleChildScrollView(
              padding: const EdgeInsets.all(12),
              child: MatchCenterSurface(match: _snapshot()),
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(find.byKey(const Key('match-center-scorebug')), findsOneWidget);
        expect(find.text('2D pitch shell'), findsOneWidget);
        expect(find.text('Live intelligence'), findsOneWidget);
        expect(find.textContaining(_promotionCopyPattern), findsNothing);
        expect(tester.takeException(), isNull);
      }
    });

    test('football ops display strings do not promote production 3D', () {
      final List<File> files = _ownedProductionFiles();

      final List<String> violations = <String>[];
      for (final File file in files) {
        final List<String> lines = file.readAsLinesSync();
        for (int index = 0; index < lines.length; index += 1) {
          final String trimmed = lines[index].trimLeft();
          if (trimmed.startsWith('import ') ||
              trimmed.startsWith('export ') ||
              trimmed.startsWith('//')) {
            continue;
          }
          if (_forbiddenDisplayPattern.hasMatch(trimmed)) {
            violations.add('${file.path}:${index + 1}: ${trimmed.trim()}');
          }
        }
      }

      expect(
        violations,
        isEmpty,
        reason:
            'Production football ops copy must stay canonical 2D only with no '
            '3D promotion, CTA, monetization, Unity, native, or pseudo-3D label.',
      );
    });

    test('football ops production code does not create local match events', () {
      final List<String> violations = <String>[];
      for (final File file in _ownedProductionFiles()) {
        final List<String> lines = file.readAsLinesSync();
        for (int index = 0; index < lines.length; index += 1) {
          final String trimmed = lines[index].trimLeft();
          if (trimmed.startsWith('import ') ||
              trimmed.startsWith('export ') ||
              trimmed.startsWith('//')) {
            continue;
          }
          if (_forbiddenLocalGenerationPattern.hasMatch(trimmed)) {
            violations.add('${file.path}:${index + 1}: ${trimmed.trim()}');
          }
        }
      }

      expect(
        violations,
        isEmpty,
        reason:
            'Football operations must not fabricate fixtures, match clocks, '
            'scores, stats, or events in production code. Backend/websocket '
            'payloads are authoritative.',
      );
    });
  });
}

final RegExp _promotionCopyPattern = RegExp(
  [
    r'upgrade\s+(?:to|for)\s+3d',
    r'unlock\s+3d',
    r'premium\s+3d',
    r'native\s+3d',
    r'pseudo-?3d',
    r'unity',
    r'3d\s+(?:route|surface|viewer|experience|broadcast)',
  ].join('|'),
  caseSensitive: false,
);

const List<String> _forbiddenDisplayFragments = <String>[
  'upgrade to 3d',
  'upgrade for 3d',
  'unlock 3d',
  'premium 3d',
  'native 3d',
  'native_3d',
  'pseudo3d',
  'pseudo 3d',
  'pseudo-3d',
  'unity',
  '3d viewer',
  '3d route',
  '3d surface',
  '3d experience',
  '3d broadcast',
];

final RegExp _forbiddenDisplayPattern = RegExp(
  _forbiddenDisplayFragments
      .map((String fragment) {
        final String escaped = RegExp.escape(
          fragment,
        ).replaceAll(r'\ ', r'\s+');
        return r'(?<![a-z0-9_])' + escaped + r'(?![a-z0-9_])';
      })
      .join('|'),
  caseSensitive: false,
);

final RegExp _forbiddenLocalGenerationPattern = RegExp(
  [
    r'\bRandom\s*\(',
    r'\bTimer\.periodic\s*\(',
    r'\bStream\.periodic\s*\(',
    r'\bfake\b',
  ].join('|'),
  caseSensitive: false,
);

List<File> _ownedProductionFiles() {
  return <String>[
        'lib/features/club_hub',
        'lib/features/club',
        'lib/features/compete',
        'lib/features/match_center',
      ]
      .map(_sourceDirectory)
      .where((Directory directory) => directory.existsSync())
      .expand(
        (Directory directory) => directory
            .listSync(recursive: true)
            .whereType<File>()
            .where((File file) => file.path.endsWith('.dart')),
      )
      .toList(growable: false);
}

Widget _app(Widget child) {
  return MaterialApp(theme: GteShellTheme.build(), home: Scaffold(body: child));
}

Future<void> _setViewport(WidgetTester tester, Size size) async {
  tester.view.devicePixelRatio = 1;
  tester.view.physicalSize = size;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

Directory _sourceDirectory(String relativePath) {
  final Directory fromFrontend = Directory(relativePath);
  if (fromFrontend.existsSync()) {
    return fromFrontend;
  }
  return Directory('frontend/$relativePath');
}

LiveMatchSnapshot _snapshot() {
  final DateTime expiresAt = DateTime.utc(2026, 1, 1);
  return LiveMatchSnapshot(
    matchId: 'thread-3-responsive-acceptance',
    homeTeam: 'Lagos United',
    awayTeam: 'Accra City',
    homeScore: 2,
    awayScore: 1,
    minute: 64,
    phase: LiveMatchPhase.secondHalf,
    momentum: const <int>[1, 2, 1],
    commentary: const <LiveMatchEvent>[
      LiveMatchEvent(
        minute: 33,
        title: 'Goal - Lagos United',
        detail: 'Verified backend event.',
        team: 'Lagos United',
        type: LiveMatchEventType.goal,
      ),
    ],
    homeLineup: const <LiveMatchLineupPlayer>[
      LiveMatchLineupPlayer(name: 'Ayo Mensah', position: 'GK', rating: 7),
      LiveMatchLineupPlayer(name: 'Tunde Bello', position: 'CB', rating: 7),
      LiveMatchLineupPlayer(name: 'Kofi Ade', position: 'CM', rating: 7),
    ],
    awayLineup: const <LiveMatchLineupPlayer>[
      LiveMatchLineupPlayer(name: 'Kwame Boateng', position: 'GK', rating: 7),
      LiveMatchLineupPlayer(name: 'Yaw Owusu', position: 'CB', rating: 7),
      LiveMatchLineupPlayer(name: 'Kojo Mensah', position: 'FW', rating: 7),
    ],
    substitutions: const <LiveMatchEvent>[],
    cards: const <LiveMatchEvent>[],
    tacticalSuggestions: const <LiveMatchTacticalSuggestion>[],
    keyMoments: const <LiveMatchHighlightClip>[],
    highlights: const <LiveMatchHighlightClip>[],
    standardHighlightExpiresAt: expiresAt,
    premiumHighlightExpiresAt: expiresAt,
    stats: const LiveMatchStatsSnapshot(
      possession: LiveMatchStatPair(home: 58, away: 42, unit: '%'),
      shots: LiveMatchStatPair(home: 9, away: 6),
      shotsOnTarget: LiveMatchStatPair(home: 5, away: 3),
      expectedGoals: LiveMatchStatPair(home: 1.42, away: 0.81),
      territory: LiveMatchStatPair(home: 61, away: 39, unit: '%'),
      pressure: LiveMatchStatPair(home: 67, away: 44),
      marketSignal: 'Home control rising',
      shotMap: <LiveMatchShotMarker>[
        LiveMatchShotMarker(x: 0.78, y: 0.42, xg: 0.34, team: 'home'),
      ],
    ),
    liveIntelligence: const LiveMatchLiveIntelligence(
      status: 'provided',
      summary: 'Live backend signal confirms pressure on the right channel.',
      signals: <LiveMatchIntelligenceSignal>[
        LiveMatchIntelligenceSignal(
          title: 'Press trap forming',
          detail: 'Away build-up is being forced toward the touchline.',
          severity: 'high',
          source: 'ops-feed',
        ),
      ],
    ),
  );
}
