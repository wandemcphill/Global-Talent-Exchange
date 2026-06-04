import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/data/live_match_canonical.dart';

void main() {
  group('canonical live match overlays', () {
    test('degrades pending backend xG payloads without inventing values', () {
      final GtexLiveMatchSnapshot snapshot = GtexLiveMatchSnapshot.fromJson(
        _payload(
          overlays: <String, Object?>{
            'xg': <String, Object?>{
              'status': 'pending',
              'message': 'Backend xG worker has not published yet.',
            },
          },
        ),
      );

      final GtexOverlayReadiness readiness = snapshot.overlay(
        GtexLiveOverlayMode.xG,
      );

      expect(readiness.status, GtexOverlayStatus.degraded);
      expect(readiness.message, 'Backend xG worker has not published yet.');
      expect(readiness.isConfirmed, isFalse);
    });

    test('blocks non-empty xG overlay payloads that omit xG truth', () {
      final GtexLiveMatchSnapshot snapshot = GtexLiveMatchSnapshot.fromJson(
        _payload(
          stats: <String, Object?>{
            'shot_map': <Object?>[
              <String, Object?>{
                'x': 72,
                'y': 40,
                'team': 'home',
                'outcome': 'blocked',
              },
            ],
          },
          overlays: <String, Object?>{
            'xg': <String, Object?>{'provider': 'xg-worker'},
          },
        ),
      );

      final GtexOverlayReadiness readiness = snapshot.overlay(
        GtexLiveOverlayMode.xG,
      );

      expect(readiness.status, GtexOverlayStatus.blocked);
      expect(readiness.message, contains('xG totals or weighted shots'));
      expect(readiness.isConfirmed, isFalse);
    });

    test('confirms backend xG totals, including nil-nil xG', () {
      final GtexLiveMatchSnapshot snapshot = GtexLiveMatchSnapshot.fromJson(
        _payload(
          stats: <String, Object?>{
            'xg': <String, Object?>{'home': 0, 'away': 0},
          },
        ),
      );

      final GtexOverlayReadiness readiness = snapshot.overlay(
        GtexLiveOverlayMode.xG,
      );

      expect(readiness.status, GtexOverlayStatus.confirmed);
      expect(readiness.isConfirmed, isTrue);
    });

    test(
      'confirms shot markers only when the backend supplies an xG field',
      () {
        final GtexLiveMatchSnapshot snapshot = GtexLiveMatchSnapshot.fromJson(
          _payload(
            stats: <String, Object?>{
              'shot_map': <Object?>[
                <String, Object?>{'x': 72, 'y': 40, 'team': 'home', 'xg': 0},
              ],
            },
          ),
        );

        final GtexOverlayReadiness readiness = snapshot.overlay(
          GtexLiveOverlayMode.xG,
        );

        expect(readiness.status, GtexOverlayStatus.confirmed);
        expect(readiness.isConfirmed, isTrue);
      },
    );
  });
}

Map<String, Object?> _payload({
  Map<String, Object?> stats = const <String, Object?>{},
  Map<String, Object?> overlays = const <String, Object?>{},
}) {
  return <String, Object?>{
    'match_id': 'match-1',
    'clock': <String, Object?>{'minute': 12, 'status': 'first_half'},
    'home': <String, Object?>{'name': 'Lagos United', 'score': 0},
    'away': <String, Object?>{'name': 'Accra City', 'score': 0},
    if (stats.isNotEmpty) 'stats': stats,
    if (overlays.isNotEmpty) 'overlays': overlays,
  };
}
