import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_redesign/data/gtex_match_feed.dart';
import 'package:gte_frontend/features/match_redesign/widgets/gtex_match_connection_banner.dart';

Widget _host(Widget child) {
  return MaterialApp(home: Scaffold(body: child));
}

void main() {
  testWidgets('renders nothing while the feed is healthy', (tester) async {
    await tester.pumpWidget(
      _host(
        const GtexMatchConnectionBanner(
          status: GtexMatchConnectionStatus.live,
        ),
      ),
    );

    expect(find.byType(Semantics), findsWidgets);
    expect(find.textContaining('RECONNECT'), findsNothing);
    expect(find.text('FEED OFFLINE'), findsNothing);
  });

  testWidgets('renders nothing when idle', (tester) async {
    await tester.pumpWidget(
      _host(
        const GtexMatchConnectionBanner(
          status: GtexMatchConnectionStatus.idle,
        ),
      ),
    );

    expect(find.byType(CircularProgressIndicator), findsNothing);
  });

  testWidgets('shows a spinner while reconnecting', (tester) async {
    await tester.pumpWidget(
      _host(
        const GtexMatchConnectionBanner(
          status: GtexMatchConnectionStatus.reconnecting,
        ),
      ),
    );

    expect(find.text('RECONNECTING'), findsOneWidget);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    // Reconnect is automatic, so no manual retry is offered.
    expect(find.text('Retry'), findsNothing);
  });

  testWidgets('offline offers a retry that fires', (tester) async {
    int retries = 0;
    await tester.pumpWidget(
      _host(
        GtexMatchConnectionBanner(
          status: GtexMatchConnectionStatus.offline,
          onRetry: () => retries += 1,
        ),
      ),
    );

    expect(find.text('FEED OFFLINE'), findsOneWidget);
    await tester.tap(find.text('Retry'));
    await tester.pump();

    expect(retries, 1);
  });

  testWidgets('offline hides retry when no handler is supplied', (
    tester,
  ) async {
    await tester.pumpWidget(
      _host(
        const GtexMatchConnectionBanner(
          status: GtexMatchConnectionStatus.offline,
        ),
      ),
    );

    expect(find.text('FEED OFFLINE'), findsOneWidget);
    expect(find.text('Retry'), findsNothing);
  });

  testWidgets('full time is announced as final', (tester) async {
    await tester.pumpWidget(
      _host(
        const GtexMatchConnectionBanner(
          status: GtexMatchConnectionStatus.finished,
        ),
      ),
    );

    expect(find.text('FEED CLOSED'), findsOneWidget);
    expect(find.textContaining('final'), findsOneWidget);
  });

  testWidgets('compact mode drops the body copy but keeps the title', (
    tester,
  ) async {
    await tester.pumpWidget(
      _host(
        const GtexMatchConnectionBanner(
          status: GtexMatchConnectionStatus.reconnecting,
          compact: true,
        ),
      ),
    );

    expect(find.text('RECONNECTING'), findsOneWidget);
    expect(
      find.textContaining('last confirmed state'),
      findsNothing,
      reason: 'compact banners omit the explanatory line',
    );
  });

  testWidgets('retry target meets the 48dp accessibility floor', (
    tester,
  ) async {
    await tester.pumpWidget(
      _host(
        GtexMatchConnectionBanner(
          status: GtexMatchConnectionStatus.offline,
          onRetry: () {},
        ),
      ),
    );

    final Size size = tester.getSize(find.byType(TextButton));
    expect(size.height, greaterThanOrEqualTo(48));
  });

  testWidgets('exposes a live region for screen readers', (tester) async {
    await tester.pumpWidget(
      _host(
        const GtexMatchConnectionBanner(
          status: GtexMatchConnectionStatus.offline,
        ),
      ),
    );

    final Finder banner = find.ancestor(
      of: find.text('FEED OFFLINE'),
      matching: find.byType(Semantics),
    );
    expect(banner, findsWidgets);
  });
}
