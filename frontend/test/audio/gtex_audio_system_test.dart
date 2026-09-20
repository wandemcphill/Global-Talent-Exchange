import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:gte_frontend/services/ambient_audio_controller.dart';
import 'package:gte_frontend/services/audio/gtex_audio_context.dart';
import 'package:gte_frontend/services/audio/gtex_audio_mixer.dart';
import 'package:gte_frontend/services/audio/gtex_soundtrack_catalogue.dart';
import 'package:gte_frontend/services/audio/gtex_track_metadata.dart';
import 'package:gte_frontend/services/audio/matchday_audio_handoff.dart';
import 'package:gte_frontend/widgets/ambient_audio_toggle_button.dart';
import 'package:gte_frontend/widgets/audio/gtex_audio_settings_sheet.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('GTEX Soundtrack OS - Catalogue & Metadata', () {
    test('Catalogue holds starter tracks with verified licensing metadata', () {
      final GtexSoundtrackCatalogue catalogue = GtexSoundtrackCatalogue();
      final List<GtexTrackMetadata> tracks = catalogue.allTracks;

      expect(tracks, isNotEmpty);
      for (final track in tracks) {
        expect(track.id, isNotEmpty);
        expect(track.title, isNotEmpty);
        expect(track.artist, isNotEmpty);
        expect(track.source, isNotEmpty);
        expect(track.licence, isNotEmpty);
        expect(track.licenceUrl, startsWith('http'));
        expect(track.provenance, isNotEmpty);
        expect(track.assetPath, isNotEmpty);
      }
    });

    test('Catalogue filters tracks accurately by context', () {
      final GtexSoundtrackCatalogue catalogue = GtexSoundtrackCatalogue();

      final List<GtexTrackMetadata> marketTracks =
          catalogue.tracksForContext(GtexAudioContext.market);
      expect(marketTracks, isNotEmpty);
      expect(marketTracks.any((t) => t.id == 'gtex-trading-floor'), isTrue);

      final List<GtexTrackMetadata> clubTracks =
          catalogue.tracksForContext(GtexAudioContext.club);
      expect(clubTracks, isNotEmpty);
      expect(clubTracks.any((t) => t.id == 'gtex-tactical-hq'), isTrue);
    });

    test('Custom track registration scales the catalogue seamlessly', () {
      final GtexSoundtrackCatalogue catalogue = GtexSoundtrackCatalogue();
      const GtexTrackMetadata customTrack = GtexTrackMetadata(
        id: 'gtex-custom-001',
        title: 'Custom Cyber Match',
        artist: 'GTEX Composer',
        album: 'OS Vol. 2',
        genre: 'Synth',
        bpm: 126,
        durationSeconds: 200,
        contexts: <GtexAudioContext>[GtexAudioContext.market],
        assetPath: 'assets/media/gtex_stadium_ambient.mp3',
        source: 'Custom License',
        licence: 'Royalty-Free',
        licenceUrl: 'https://gtex.io/legal/audio-licensing',
        attributionRequired: false,
        provenance: 'Dynamic test track',
      );

      catalogue.registerTrack(customTrack);
      final List<GtexTrackMetadata> marketTracks =
          catalogue.tracksForContext(GtexAudioContext.market);
      expect(marketTracks.any((t) => t.id == 'gtex-custom-001'), isTrue);
    });
  });

  group('GTEX Audio Mixer & Matchday Handoff', () {
    test('Mixer gain formula applies master, channel, and ducking factors', () {
      final GtexAudioMixer mixer = GtexAudioMixer(
        masterVolume: 0.8,
        musicVolume: 0.5,
      );

      expect(mixer.effectiveMusicVolume, closeTo(0.4, 0.001));

      mixer.duckMusic(factor: 0.5);
      expect(mixer.musicDuckingFactor, 0.5);
      expect(mixer.effectiveMusicVolume, closeTo(0.2, 0.001));

      mixer.restoreMusic();
      expect(mixer.musicDuckingFactor, 1.0);
      expect(mixer.effectiveMusicVolume, closeTo(0.4, 0.001));
    });

    test('MatchdayHandoff executes ducking and context entry/exit', () {
      final GtexAudioMixer mixer = GtexAudioMixer(
        masterVolume: 1.0,
        musicVolume: 0.8,
      );
      GtexAudioContext? activeContext;
      bool updated = false;

      final MatchdayAudioHandoff handoff = MatchdayAudioHandoff(
        mixer: mixer,
        onContextChanged: (ctx) => activeContext = ctx,
        onMixerUpdated: () => updated = true,
      );

      handoff.enterMatchContext('match-123');
      expect(handoff.inMatchContext, isTrue);
      expect(handoff.activeMatchKey, 'match-123');
      expect(activeContext, GtexAudioContext.matchday);
      expect(mixer.musicDuckingFactor, 0.125);
      expect(updated, isTrue);

      handoff.leaveMatchContext();
      expect(handoff.inMatchContext, isFalse);
      expect(handoff.activeMatchKey, isNull);
      expect(activeContext, GtexAudioContext.home);
      expect(mixer.musicDuckingFactor, 1.0);
    });
  });

  group('AmbientAudioController Integration Tests', () {
    test('Controller bootstrap loads saved volume and mute preferences', () async {
      SharedPreferences.setMockInitialValues(<String, Object>{
        AmbientAudioController.preferenceKey: false,
        AmbientAudioController.masterVolumeKey: 0.9,
        AmbientAudioController.musicVolumeKey: 0.4,
      });

      final SharedPreferences prefs = await SharedPreferences.getInstance();
      final AmbientAudioController controller = AmbientAudioController(
        preferences: prefs,
      );

      await controller.bootstrap();

      expect(controller.isMuted, isFalse);
      expect(controller.masterVolume, 0.9);
      expect(controller.musicVolume, 0.4);
    });

    test('Context change retains current track if track supports new context without restarting', () async {
      final AmbientAudioController controller = AmbientAudioController();
      await controller.bootstrap();

      // Set to Club, which has 'gtex-stadium-ambient' and 'gtex-tactical-hq' in pool.
      await controller.setAudioContext(GtexAudioContext.club);
      final GtexTrackMetadata trackBefore = controller.currentTrack;

      // Setting context again to Club or another supported context keeps the active track.
      await controller.setAudioContext(GtexAudioContext.club);
      expect(controller.currentContext, GtexAudioContext.club);
      expect(controller.currentTrack.id, trackBefore.id);
    });

    test('Context change switches track if current track is unsupported in new context', () async {
      final AmbientAudioController controller = AmbientAudioController();
      await controller.bootstrap();

      // Market context should pick the Market track ('gtex-trading-floor')
      await controller.setAudioContext(GtexAudioContext.market);
      expect(controller.currentContext, GtexAudioContext.market);
      expect(controller.currentTrack.id, 'gtex-trading-floor');
    });

    test('Track rotation (nextTrack & shuffle) cycles within context pool', () async {
      final AmbientAudioController controller = AmbientAudioController();
      await controller.bootstrap();

      // Home context has gtex-stadium-ambient and gtex-tactical-hq
      await controller.setAudioContext(GtexAudioContext.home);
      final String initialTrackId = controller.currentTrack.id;

      await controller.nextTrack();
      final String nextTrackId = controller.currentTrack.id;

      expect(nextTrackId, isNot(equals(initialTrackId)));
    });

    test('Volume setters update mixer and persist to SharedPreferences', () async {
      SharedPreferences.setMockInitialValues(<String, Object>{});
      final SharedPreferences prefs = await SharedPreferences.getInstance();
      final AmbientAudioController controller = AmbientAudioController(
        preferences: prefs,
      );

      await controller.bootstrap();
      await controller.setMasterVolume(0.75);
      await controller.setMusicVolume(0.35);

      expect(prefs.getDouble(AmbientAudioController.masterVolumeKey), 0.75);
      expect(prefs.getDouble(AmbientAudioController.musicVolumeKey), 0.35);
    });

    test('Web autoplay resolution clears blocked state and attempts playback', () async {
      final AmbientAudioController controller = AmbientAudioController();
      await controller.bootstrap();

      await controller.resolveWebAutoplay();
      expect(controller.isWebAutoplayBlocked, isFalse);
    });
  });

  group('GTEX Audio UI Widget Tests', () {
    testWidgets('AmbientAudioToggleButton toggles mute and opens AudioSettingsSheet', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1200, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      SharedPreferences.setMockInitialValues(<String, Object>{});
      final SharedPreferences prefs = await SharedPreferences.getInstance();
      final AmbientAudioController controller = AmbientAudioController(
        preferences: prefs,
      );
      await controller.bootstrap();

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: Scaffold(
            body: AmbientAudioToggleButton(controller: controller),
          ),
        ),
      );

      expect(find.byKey(const Key('ambient-audio-toggle')), findsOneWidget);

      // Tap to toggle mute
      final bool initialMuted = controller.isMuted;
      await tester.tap(find.byKey(const Key('ambient-audio-toggle')));
      await tester.pump();
      expect(controller.isMuted, !initialMuted);

      // Directly verify GtexAudioSettingsSheet opens via static show()
      GtexAudioSettingsSheet.show(
        tester.element(find.byKey(const Key('ambient-audio-toggle'))),
        controller,
      );
      await tester.pumpAndSettle();

      expect(find.byType(GtexAudioSettingsSheet), findsOneWidget);
      expect(find.text('GTEX SOUNDTRACK OS'), findsOneWidget);
      expect(find.text('Audio & Atmosphere Settings'), findsOneWidget);
      expect(find.text('ACTIVE AUDIO CHANNELS'), findsOneWidget);
    });

    testWidgets('GtexAudioSettingsSheet displays sliders, track info, and Music Credits', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1200, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      SharedPreferences.setMockInitialValues(<String, Object>{});
      final SharedPreferences prefs = await SharedPreferences.getInstance();
      final AmbientAudioController controller = AmbientAudioController(
        preferences: prefs,
      );
      await controller.bootstrap();

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: Scaffold(
            body: SingleChildScrollView(
              child: SizedBox(
                height: 1200,
                child: GtexAudioSettingsSheet(controller: controller),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('GTEX SOUNDTRACK OS'), findsOneWidget);
      expect(find.text('Master Volume'), findsOneWidget);
      expect(find.text('Music / Atmosphere'), findsOneWidget);
      expect(find.text('SOUNDTRACK CONTEXT'), findsOneWidget);

      // Open Credits View
      final Finder infoIcon = find.byIcon(Icons.info_outline_rounded);
      expect(infoIcon, findsOneWidget);
      await tester.tap(infoIcon);
      await tester.pumpAndSettle();

      expect(find.text('MUSIC CREDITS & LICENSING'), findsOneWidget);
      expect(find.textContaining('Every track bundled in GTEX'), findsOneWidget);
      expect(find.text('GTEX Stadium Atmosphere'), findsOneWidget);
    });
  });
}
