import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/core/theme/app_theme.dart';
import 'package:gte_frontend/features/viral_feed/data/viral_feed_repository.dart';
import 'package:gte_frontend/features/viral_feed/presentation/viral_feed_screen.dart';

void main() {
  testWidgets('viral feed renders hook, share CTA, and debate copy', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.dark(),
        home: ViralFeedScreen(repository: ViralFeedApiRepository.fixture()),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.byKey(const Key('viral-feed-page-view')), findsOneWidget);
    expect(find.text('FOR YOU'), findsOneWidget);
    expect(find.text("89' and the whole match flipped 😳🔥"), findsOneWidget);
    expect(find.text('Share to WhatsApp'), findsOneWidget);
    expect(find.text('Royal Lagos spark post-match chaos'), findsOneWidget);
  });
}
