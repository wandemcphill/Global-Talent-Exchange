import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/platform/gtex_platform_experience_controller.dart';
import 'package:gte_frontend/models/platform/gtex_platform_experience.dart';

void main() {
  test('tv mode auto-switches to the next live channel when a match ends', () {
    final GtexPlatformExperienceController controller =
        GtexPlatformExperienceController(
          mode: GtexPlatformMode.tv,
          channels: const <GtexTvChannel>[
            GtexTvChannel(
              channelId: 'live',
              name: 'Live',
              headline: 'Lagos Stars vs Abuja City',
              subheadline: 'Main feed',
              matchId: 'match-a',
            ),
            GtexTvChannel(
              channelId: 'finals',
              name: 'Finals',
              headline: 'GTEX Cup Final',
              subheadline: 'Ceremonial feed',
              matchId: 'match-b',
            ),
          ],
        );

    final GtexTvChannel? nextChannel = controller.handleMatchFinished();

    expect(nextChannel?.channelId, 'finals');
    expect(controller.currentChannel?.channelId, 'finals');
    expect(controller.autoSwitchMessage, contains('Finals'));
  });

  test('sync state records commentary cursor and watch history', () {
    final GtexPlatformExperienceController controller =
        GtexPlatformExperienceController();

    controller.syncFromExternal(
      sourceDeviceId: 'tv-device',
      sourceDeviceLabel: 'Living Room TV',
      matchId: 'match-a',
      title: 'Lagos Stars vs Abuja City',
      commentaryCursor: 14,
      resumePositionSeconds: 31,
    );

    expect(controller.syncState.sourceDeviceLabel, 'Living Room TV');
    expect(controller.syncState.commentaryCursor, 14);
    expect(controller.syncState.resumeMatchId, 'match-a');
    expect(controller.syncState.watchHistory, hasLength(1));
  });
}
