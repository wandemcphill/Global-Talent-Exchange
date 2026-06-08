import 'package:test/test.dart';

import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/models/community_models.dart';

void main() {
  test('community digest requires backend-authored count fields', () {
    expect(
      () => CommunityDigest.fromJson(<String, Object?>{
        'watchlist_count': 1,
        'live_thread_count': 2,
        'private_thread_count': 3,
      }),
      throwsA(isA<GteParsingException>()),
    );
  });

  test('live thread messages require backend-authored reaction counts', () {
    expect(
      () => LiveThreadMessage.fromJson(<String, Object?>{
        'id': 'msg-1',
        'thread_id': 'thread-1',
        'author_user_id': 'user-1',
        'body': 'Hello',
        'visibility': 'public',
        'created_at': DateTime.utc(2026).toIso8601String(),
        'metadata_json': const <String, Object?>{},
      }),
      throwsA(isA<GteParsingException>()),
    );
  });
}
