import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_center/live_match_overview_provider.dart';

void main() {
  test('fromJson preserves backend-authored live overview fields', () {
    final LiveMatchOverview overview = LiveMatchOverview.fromJson(
      <String, Object?>{
        'channels': <Object?>[
          <String, Object?>{
            'channel_id': 'prime',
            'name': 'GTEX Prime',
            'is_live': false,
            'current_program': <String, Object?>{
              'match_id': 'match-001',
              'title': 'Derby Live',
              'subtitle': 'Main event from Lagos.',
              'watch_route': '/matches/match-001/live',
            },
          },
        ],
      },
    );

    expect(overview.entries, hasLength(1));
    expect(overview.entries.single.matchKey, 'match-001');
    expect(overview.entries.single.title, 'Derby Live');
    expect(overview.entries.single.subtitle, 'Main event from Lagos.');
    expect(overview.entries.single.channelLabel, 'GTEX Prime');
    expect(overview.entries.single.isLive, isFalse);
    expect(overview.entries.single.watchRoute, '/matches/match-001/live');
  });

  test('fromJson skips programs with missing backend-authored metadata', () {
    final LiveMatchOverview overview = LiveMatchOverview.fromJson(
      <String, Object?>{
        'featured_channel': <String, Object?>{
          'channel_id': 'featured',
          'name': 'GTEX Prime',
          'current_program': <String, Object?>{
            'match_id': 'missing-subtitle',
            'title': 'No Subtitle',
            'metadata': <String, Object?>{
              'focus_reason': 'This must not become a subtitle.',
            },
          },
        },
        'channels': <Object?>[
          <String, Object?>{
            'channel_id': 'missing-channel',
            'is_live': true,
            'current_program': <String, Object?>{
              'match_id': 'missing-channel-label',
              'title': 'No Channel',
              'subtitle': 'This should stay blocked.',
            },
          },
          <String, Object?>{
            'channel_id': 'missing-live',
            'name': 'GTEX Extra',
            'current_program': <String, Object?>{
              'match_id': 'missing-live-flag',
              'title': 'No Live Flag',
              'subtitle': 'This should stay blocked too.',
            },
          },
        ],
        'match_of_the_moment': <String, Object?>{
          'match_id': 'moment',
          'title': 'Moment',
          'subtitle': 'No is_live truth exists for this payload.',
        },
      },
    );

    expect(overview.entries, isEmpty);
  });
}
