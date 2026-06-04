import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/shell/shell.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('GtexStatePanel renders every canonical surface state', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _Harness(
        child: SingleChildScrollView(
          child: Column(
            children: GtexSurfaceState.values
                .map(
                  (GtexSurfaceState state) => Padding(
                    padding: const EdgeInsets.all(6),
                    child: GtexStatePanel(
                      state: state,
                      eyebrow: state.name.toUpperCase(),
                      title: 'State ${state.name}',
                      message: 'Message for ${state.name}',
                    ),
                  ),
                )
                .toList(growable: false),
          ),
        ),
      ),
    );

    for (final GtexSurfaceState state in GtexSurfaceState.values) {
      expect(find.text(state.name.toUpperCase()), findsWidgets);
      expect(find.text('State ${state.name}'), findsOneWidget);
    }
  });

  testWidgets('GtexAsyncSurface shows child when confirmed', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const _Harness(
        child: GtexAsyncSurface(
          state: GtexSurfaceState.confirmed,
          child: Text('Confirmed operating surface'),
        ),
      ),
    );

    expect(find.text('Confirmed operating surface'), findsOneWidget);
    expect(find.text('CONFIRMED'), findsNothing);
  });

  testWidgets('GtexAsyncSurface renders reconnecting state copy', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const _Harness(
        child: SizedBox(
          width: 640,
          height: 360,
          child: GtexAsyncSurface(
            state: GtexSurfaceState.reconnecting,
            child: Text('Market desk remains visible'),
          ),
        ),
      ),
    );

    expect(find.text('RECONNECTING'), findsOneWidget);
    expect(find.text('Reconnecting'), findsOneWidget);
  });
}

class _Harness extends StatelessWidget {
  const _Harness({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      theme: GteShellTheme.build(),
      home: Scaffold(body: child),
    );
  }
}
