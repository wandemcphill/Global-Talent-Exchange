import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/app/gte_frontend_app.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/services/ambient_audio_controller.dart';
import 'package:gte_frontend/widgets/ambient_audio_toggle_button.dart';
import 'package:gte_frontend/widgets/cup_lift_hero.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('mute button calls AmbientAudioController.toggleMuted', (
    WidgetTester tester,
  ) async {
    final _FakeAmbientAudioController controller =
        _FakeAmbientAudioController();

    await tester.pumpWidget(
      MaterialApp(
        theme: GteShellTheme.build(),
        home: Scaffold(body: AmbientAudioToggleButton(controller: controller)),
      ),
    );

    await tester.tap(find.byKey(const Key('ambient-audio-toggle')));
    await tester.pump();

    expect(controller.toggleCount, 1);
  });

  testWidgets('CupLiftHero appears on /app/home through the active router', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1600, 2200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final GteExchangeController controller = GteExchangeController(
      api: GteExchangeApiClient.fixture(),
    );
    addTearDown(controller.dispose);
    controller.session = _authenticatedSession(
      userId: 'user-no-club',
      userName: 'No Club Owner',
    );

    await tester.pumpWidget(
      GteFrontendApp(
        controller: controller,
        config: const GteAppConfig(
          apiBaseUrl: 'http://127.0.0.1:8000',
          backendMode: GteBackendMode.fixture,
        ),
        initialPath: '/app/home',
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byType(CupLiftHero), findsOneWidget);
    expect(find.byKey(const Key('cup-lift-hero')), findsOneWidget);
  });

  testWidgets('premium media assets are present in AssetManifest', (
    WidgetTester tester,
  ) async {
    final AssetManifest manifest = await AssetManifest.loadFromAssetBundle(
      rootBundle,
    );
    final List<String> assets = manifest.listAssets();

    expect(assets, contains('assets/media/gtex_stadium_ambient.mp3'));
    expect(assets, contains('assets/media/gtex_cup_lift_hero.mp4'));
    expect(assets, contains('assets/media/gtex_cup_lift_poster.webp'));
  });
}

class _FakeAmbientAudioController extends ChangeNotifier
    implements AmbientAudioState {
  int toggleCount = 0;

  @override
  bool get isLoading => false;

  @override
  bool get isMuted => toggleCount.isEven;

  @override
  bool get isPlaying => !isMuted;

  @override
  bool get isReady => true;

  @override
  Object? get lastError => null;

  @override
  Future<void> bootstrap() async {}

  @override
  Future<void> pause() async {}

  @override
  Future<void> play() async {}

  @override
  Future<void> preload() async {}

  @override
  Future<void> toggleMuted() async {
    toggleCount += 1;
    notifyListeners();
  }
}

GteAuthSession _authenticatedSession({
  required String userId,
  required String userName,
  String? clubId,
  String? clubName,
}) {
  return GteAuthSession.fromJson(<String, Object?>{
    'access_token': 'test-token',
    'token_type': 'bearer',
    'expires_in': 3600,
    if (clubId != null) 'current_club_id': clubId,
    if (clubName != null) 'current_club_name': clubName,
    'user': <String, Object?>{
      'id': userId,
      'email': '$userId@gtex.test',
      'username': userId,
      'display_name': userName,
      'role': 'user',
      if (clubId != null) 'current_club_id': clubId,
      if (clubName != null) 'current_club_name': clubName,
    },
  });
}
