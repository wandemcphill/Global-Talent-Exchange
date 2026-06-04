import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('matchday wallpaper is bundled for the shell background', (
    WidgetTester tester,
  ) async {
    final AssetManifest manifest = await AssetManifest.loadFromAssetBundle(
      rootBundle,
    );

    expect(
      manifest.listAssets(),
      contains('assets/media/gtex_matchday_wallpaper.png'),
    );
  });
}
