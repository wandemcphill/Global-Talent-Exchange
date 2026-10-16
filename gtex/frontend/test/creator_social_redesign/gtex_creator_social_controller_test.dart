import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/creator_social_redesign/models/gtex_creator_social_models.dart';
import 'package:gte_frontend/features/creator_social_redesign/presentation/gtex_creator_social_controller.dart';

void main() {
  test('creator social controller switches modules', () {
    final controller = GtexCreatorSocialController();
    expect(controller.creatorModule, GtexCreatorModule.overview);
    expect(controller.hasLiveSnapshot, isFalse);

    controller.selectCreatorModule(GtexCreatorModule.monetization);
    expect(controller.creatorModule, GtexCreatorModule.monetization);
  });

  test('award category filters nominees', () {
    final controller = GtexCreatorSocialController(allowFixtureData: true);
    controller.selectAwardCategory(GtexAwardCategory.regen);

    expect(
      controller.nominees.every(
        (nominee) => nominee.category == GtexAwardCategory.regen,
      ),
      isTrue,
    );
  });

  test('social search filters stories', () {
    final controller = GtexCreatorSocialController(allowFixtureData: true);
    controller.updateSearch('regen');

    expect(controller.stories, isNotEmpty);
    expect(
      controller.stories.any(
        (story) =>
            story.title.toLowerCase().contains('regen') ||
            story.body.toLowerCase().contains('regen'),
      ),
      isTrue,
    );
  });
}
