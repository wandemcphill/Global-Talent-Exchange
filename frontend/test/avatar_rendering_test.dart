import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/features/player_card_marketplace/data/player_card_marketplace_models.dart';
import 'package:gte_frontend/models/academy_models.dart';
import 'package:gte_frontend/models/player_avatar.dart';
import 'package:gte_frontend/services/avatar_mapper.dart';
import 'package:gte_frontend/widgets/player_avatar_widget.dart';

void main() {
  test('same player maps to the same avatar across market surfaces', () {
    const GteMarketPlayerListItem marketItem = GteMarketPlayerListItem(
      playerId: 'player-42',
      playerName: 'Ayo Midfield',
      position: 'CM',
      nationality: 'Nigeria',
      currentClubName: 'Lagos City',
      age: 23,
      currentValueCredits: 1200,
      movementPct: 0.12,
      trendScore: 7.4,
      marketInterestScore: 68,
      averageRating: 7.2,
    );
    const GteMarketPlayerIdentity identity = GteMarketPlayerIdentity(
      playerName: 'Ayo Midfield',
      firstName: 'Ayo',
      lastName: 'Midfield',
      shortName: 'A. Midfield',
      position: 'CM',
      normalizedPosition: 'CM',
      nationality: 'Nigeria',
      nationalityCode: 'NG',
      age: 23,
      dateOfBirth: '2003-03-01',
      preferredFoot: 'right',
      shirtNumber: 8,
      heightCm: 178,
      weightKg: 72,
      currentClubId: 'club-1',
      currentClubName: 'Lagos City',
      currentCompetitionId: 'league-1',
      currentCompetitionName: 'GTEX Premier',
      imageUrl: null,
    );

    final PlayerAvatar fromList = AvatarMapper.fromMarketListItem(marketItem);
    final PlayerAvatar fromDetail = AvatarMapper.fromMarketIdentity(
      identity,
      playerId: 'player-42',
    );

    expect(fromList.seedToken, equals(fromDetail.seedToken));
    expect(fromList.dnaSeed, equals(fromDetail.dnaSeed));
    expect(fromList.hairStyle, equals(fromDetail.hairStyle));
    expect(fromList.skinTone, equals(fromDetail.skinTone));
  });

  test('provided avatar payload wins over fallback generation', () {
    final PlayerCardMarketplaceListing listing =
        PlayerCardMarketplaceListing.fromJson(<String, Object?>{
      'listing_id': 'listing-1',
      'listing_type': 'sale',
      'player_card_id': 'card-1',
      'player_id': 'player-9',
      'player_name': 'Injected Avatar',
      'club_name': 'Abuja Athletic',
      'position': 'ST',
      'average_rating': 7.9,
      'tier_code': 'elite',
      'tier_name': 'Elite',
      'rarity_rank': 1,
      'edition_code': '2026',
      'listing_owner_user_id': 'user-1',
      'status': 'open',
      'availability': 'available',
      'is_negotiable': false,
      'asset_origin': 'standard',
      'is_regen_newgen': false,
      'is_creator_linked': false,
      'quantity': 1,
      'available_quantity': 1,
      'sale_price_credits': 3400,
      'requested_filters_json': <String, Object?>{},
      'created_at': '2026-03-21T10:00:00Z',
      'avatar': <String, Object?>{
        'avatar_version': 1,
        'version': 'fm_v1',
        'seed_token': 'thread-a-token',
        'dna_seed': 123456,
        'skin_tone': 5,
        'hair_style': 8,
        'hair_color': 0,
        'face_shape': 3,
        'eyebrow_style': 2,
        'eye_type': 1,
        'nose_type': 2,
        'mouth_type': 0,
        'beard_style': 4,
        'has_accessory': true,
        'accessory_type': 1,
        'jersey_style': 3,
        'accent_tone': 2,
      },
    });

    final PlayerAvatar avatar = AvatarMapper.fromMarketplaceListing(listing);

    expect(avatar.seedToken, equals('thread-a-token'));
    expect(avatar.dnaSeed, equals(123456));
    expect(avatar.hasAccessory, isTrue);
  });

  test('academy and lineup fallbacks stay deterministic', () {
    const AcademyPlayer academyPlayer = AcademyPlayer(
      id: 'academy-7',
      name: 'Prospect Seven',
      position: 'CB',
      age: 18,
      pathwayStage: 'U19',
      potentialBand: 'High',
      developmentProgressPercent: 0.64,
      readinessScore: 71,
      minutesTarget: 900,
      statusLabel: 'Enrolled',
      nextMilestone: 'First team bench',
      strengths: <String>['Positioning'],
      focusAreas: <String>['Strength'],
    );
    const LiveMatchLineupPlayer lineupPlayer = LiveMatchLineupPlayer(
      playerId: 'academy-7',
      name: 'Prospect Seven',
      position: 'CB',
      rating: 6.8,
      captain: false,
    );

    final PlayerAvatar academyAvatar =
        AvatarMapper.fromAcademyPlayer(academyPlayer);
    final PlayerAvatar lineupAvatar = AvatarMapper.fromLiveLineupPlayer(
      lineupPlayer,
      teamName: 'GTEX B',
      matchId: 'match-1',
    );

    expect(academyAvatar.seedToken, equals(lineupAvatar.seedToken));
    expect(academyAvatar.faceShape, equals(lineupAvatar.faceShape));
    expect(academyAvatar.beardStyle, equals(lineupAvatar.beardStyle));
  });

  testWidgets('shared avatar widget paints without image dependencies',
      (WidgetTester tester) async {
    const PlayerAvatar avatar = PlayerAvatar(
      avatarVersion: 1,
      version: 'fm_v1',
      seedToken: 'widget-seed',
      dnaSeed: 999,
      skinTone: 2,
      hairStyle: 4,
      hairColor: 1,
      faceShape: 2,
      eyebrowStyle: 1,
      eyeType: 3,
      noseType: 2,
      mouthType: 1,
      beardStyle: 0,
      hasAccessory: false,
      accessoryType: 0,
      jerseyStyle: 1,
      accentTone: 4,
    );

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: Center(
            child: PlayerAvatarWidget(
              avatar: avatar,
              size: 72,
              mode: AvatarMode.card,
            ),
          ),
        ),
      ),
    );

    expect(find.byType(PlayerAvatarWidget), findsOneWidget);
    expect(find.byType(CustomPaint), findsWidgets);
  });

  testWidgets('hud minimal avatar mode renders for match overlays',
      (WidgetTester tester) async {
    const PlayerAvatar avatar = PlayerAvatar(
      avatarVersion: 1,
      version: 'fm_v1',
      seedToken: 'hud-seed',
      dnaSeed: 321,
      skinTone: 4,
      hairStyle: 2,
      hairColor: 0,
      faceShape: 1,
      eyebrowStyle: 0,
      eyeType: 0,
      noseType: 0,
      mouthType: 0,
      beardStyle: 0,
      hasAccessory: false,
      accessoryType: 0,
      jerseyStyle: 2,
      accentTone: 1,
    );

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: Center(
            child: PlayerAvatarWidget(
              avatar: avatar,
              size: 36,
              mode: AvatarMode.hudMinimal,
            ),
          ),
        ),
      ),
    );

    expect(find.byType(PlayerAvatarWidget), findsOneWidget);
    expect(find.byType(CustomPaint), findsWidgets);
  });
}
