import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/gift_economy_admin/data/gift_economy_admin_models.dart'
    as admin;
import 'package:gte_frontend/models/community_models.dart';

void main() {
  test('community discussion and gift models parse award gift metadata', () {
    final LiveThread thread = LiveThread.fromJson(<String, Object?>{
      'id': 'thread-1',
      'thread_key': 'tactics-room-final',
      'thread_type': 'discussion',
      'category': 'tactics_room',
      'title': 'Who owned the final?',
      'body': 'Midfield control decided the night.',
      'created_by_user_id': 'user-1',
      'status': 'open',
      'pinned': true,
      'visibility': 'public',
      'moderation_status': 'visible',
      'trend_score': 42,
      'metadata_json': <String, Object?>{},
      'created_at': '2026-05-17T10:00:00Z',
      'updated_at': '2026-05-17T10:02:00Z',
    });

    expect(thread.threadType, 'discussion');
    expect(thread.category, 'tactics_room');
    expect(thread.trendScore, 42);

    final GiftCatalogItem gift = GiftCatalogItem.fromJson(<String, Object?>{
      'id': 'gift-ballon',
      'code': 'ballon_dor',
      'display_name': "Ballon d'Or",
      'fallback_display_name': 'Golden Ball Supreme',
      'cost_amount': '10000.0000',
      'currency_label': 'Fan Coin',
      'rarity': 'mythic',
      'tier': 'mythic',
      'is_award_pack': true,
      'legal_status': 'requires_review',
      'animation_key': 'ballon_dor',
      'duration_ms': 8000,
    });

    expect(gift.code, 'ballon_dor');
    expect(gift.isAwardPack, isTrue);
    expect(gift.fallbackDisplayName, 'Golden Ball Supreme');
    expect(gift.animationKey, 'ballon_dor');
  });

  test('gift admin models parse Phase 5 event and abuse surfaces', () {
    final admin.GiftCatalogItem catalog = admin
        .GiftCatalogItem.fromJson(<String, Object?>{
      'id': 'gift-world-best',
      'code': 'world_best_award',
      'display_name': 'World Best Award',
      'cost_amount': '7500.0000',
      'currency_label': 'Fan Coin',
      'rarity': 'legendary',
      'tier': 'legendary',
      'is_award_pack': true,
      'legal_status': 'configurable',
    });
    final admin.GiftEvent event = admin.GiftEvent.fromJson(<String, Object?>{
      'id': 'event-1',
      'sender_user_id': 'sender',
      'recipient_user_id': 'recipient',
      'gift_key': 'world_best_award',
      'gift_display_name': 'World Best Award',
      'rarity': 'legendary',
      'gross_amount': '7500.0000',
      'platform_rake_amount': '2250.0000',
      'recipient_net_amount': '5250.0000',
      'currency_label': 'Fan Coin',
      'status': 'settled',
      'abuse_status': 'clean',
      'created_at': '2026-05-17T10:00:00Z',
    });
    final admin.GiftAbuseFlag flag = admin
        .GiftAbuseFlag.fromJson(<String, Object?>{
      'id': 'flag-1',
      'flag_key': 'wash-1',
      'sender_user_id': 'sender',
      'recipient_type': 'user',
      'recipient_id': 'recipient',
      'flag_type': 'wash_gifting',
      'severity': 'high',
      'description': 'Circular premium gifting.',
      'status': 'open',
      'created_at': '2026-05-17T10:00:00Z',
    });

    expect(catalog.key, 'world_best_award');
    expect(catalog.isAwardPack, isTrue);
    expect(event.giftDisplayName, 'World Best Award');
    expect(event.status, 'settled');
    expect(flag.flagType, 'wash_gifting');
    expect(flag.severity, 'high');
  });
}
