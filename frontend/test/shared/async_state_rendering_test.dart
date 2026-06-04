import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';
import 'package:gte_frontend/shared/widgets/async_state_widget.dart';
import 'package:gte_frontend/shared/widgets/gtex_async_state_view.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('GtexAsyncSurfaceState exposes all canonical variants', () {
    expect(
      GtexAsyncSurfaceState.values.map((GtexAsyncSurfaceState state) {
        return state.name;
      }),
      <String>[
        'loading',
        'empty',
        'blocked',
        'pending',
        'syncing',
        'reconnecting',
        'degraded',
        'confirmed',
        'error',
        'data',
      ],
    );
  });

  testWidgets('async state renderers expose visible UI for every state', (
    WidgetTester tester,
  ) async {
    final List<_AsyncStateCase> cases = <_AsyncStateCase>[
      _AsyncStateCase(
        state: GtexAsyncSurfaceState.loading,
        build: () => const GtexAsyncStateView.loading(),
      ),
      _AsyncStateCase(
        state: GtexAsyncSurfaceState.empty,
        build: () => const GtexAsyncStateView.empty(),
      ),
      _AsyncStateCase(
        state: GtexAsyncSurfaceState.blocked,
        build: () => const GtexAsyncStateView.blocked(),
      ),
      _AsyncStateCase(
        state: GtexAsyncSurfaceState.pending,
        build: () => const GtexAsyncStateView.pending(),
      ),
      _AsyncStateCase(
        state: GtexAsyncSurfaceState.syncing,
        build: () => const GtexAsyncStateView.syncing(),
      ),
      _AsyncStateCase(
        state: GtexAsyncSurfaceState.reconnecting,
        build: () => const GtexAsyncStateView.reconnecting(),
      ),
      _AsyncStateCase(
        state: GtexAsyncSurfaceState.degraded,
        build: () => const GtexAsyncStateView.degraded(),
      ),
      _AsyncStateCase(
        state: GtexAsyncSurfaceState.confirmed,
        build: () => const GtexAsyncStateView.confirmed(),
      ),
      _AsyncStateCase(
        state: GtexAsyncSurfaceState.error,
        build: () => const GtexAsyncStateView.error(),
      ),
      _AsyncStateCase(
        state: GtexAsyncSurfaceState.data,
        build: () => const GtexAsyncStateView.data(),
      ),
    ];

    for (final _AsyncStateCase stateCase in cases) {
      await tester.pumpWidget(_TestApp(child: stateCase.build()));
      await tester.pump();

      expect(
        find.text(stateCase.state.eyebrow),
        findsOneWidget,
        reason: '${stateCase.state.name} should show its status eyebrow',
      );
      expect(
        find.text(stateCase.state.title),
        findsOneWidget,
        reason: '${stateCase.state.name} should show its title',
      );
      expect(
        find.text(stateCase.state.message),
        findsOneWidget,
        reason: '${stateCase.state.name} should show its message',
      );
    }
  });

  testWidgets('compact async state renderer keeps copy visible', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const _TestApp(
        child: GtexAsyncStateView(
          state: GtexAsyncSurfaceState.degraded,
          compact: true,
          actionLabel: 'Retry',
          onAction: _noop,
        ),
      ),
    );

    expect(find.text(GtexAsyncSurfaceState.degraded.eyebrow), findsOneWidget);
    expect(find.text(GtexAsyncSurfaceState.degraded.title), findsOneWidget);
    expect(find.text(GtexAsyncSurfaceState.degraded.message), findsOneWidget);
    expect(find.text('Retry'), findsOneWidget);
  });

  testWidgets('AsyncStateWidget dispatches every GtexSurfaceState branch', (
    WidgetTester tester,
  ) async {
    final List<_SurfaceStateCase> cases = <_SurfaceStateCase>[
      _SurfaceStateCase(
        expectedText: 'loading',
        state: const GtexLoading<String>(),
      ),
      _SurfaceStateCase(
        expectedText: 'empty:no players',
        state: const GtexEmpty<String>(reason: 'no players'),
      ),
      _SurfaceStateCase(
        expectedText: 'blocked:role missing:/app/club',
        state: const GtexBlocked<String>(
          reason: 'role missing',
          ctaRoute: '/app/club',
        ),
      ),
      _SurfaceStateCase(
        expectedText: 'pending:old snapshot',
        state: const GtexPending<String>(stale: 'old snapshot'),
      ),
      _SurfaceStateCase(
        expectedText: 'syncing:current snapshot',
        state: const GtexSyncing<String>(current: 'current snapshot'),
      ),
      _SurfaceStateCase(
        expectedText: 'reconnecting:last known:2',
        state: const GtexReconnecting<String>(
          lastKnown: 'last known',
          attempt: 2,
        ),
      ),
      _SurfaceStateCase(
        expectedText: 'degraded:current data:slow feed',
        state: const GtexDegraded<String>(
          current: 'current data',
          warning: 'slow feed',
        ),
      ),
      _SurfaceStateCase(
        expectedText: 'confirmed:accepted:audit-7',
        state: const GtexConfirmed<String>(
          data: 'accepted',
          auditRef: 'audit-7',
        ),
      ),
      _SurfaceStateCase(
        expectedText: 'error:E_TIMEOUT:Timed out',
        state: const GtexError<String>(code: 'E_TIMEOUT', message: 'Timed out'),
      ),
      _SurfaceStateCase(
        expectedText: 'data:live data',
        state: const GtexData<String>(data: 'live data'),
      ),
    ];

    var retryCount = 0;

    for (final _SurfaceStateCase stateCase in cases) {
      await tester.pumpWidget(
        _TestApp(
          child: AsyncStateWidget<String>(
            state: stateCase.state,
            retry: () => retryCount += 1,
            onLoading: () => const Text('loading'),
            onEmpty: (String? reason) => Text('empty:$reason'),
            onBlocked: (String reason, String? ctaRoute) {
              return Text('blocked:$reason:$ctaRoute');
            },
            onPending: (String? stale) => Text('pending:$stale'),
            onSyncing: (String current) => Text('syncing:$current'),
            onReconnecting: (String? lastKnown, int attempt) {
              return Text('reconnecting:$lastKnown:$attempt');
            },
            onDegraded: (String current, String warning) {
              return Text('degraded:$current:$warning');
            },
            onConfirmed: (String data, String? auditRef) {
              return Text('confirmed:$data:$auditRef');
            },
            onError: (String code, String message, VoidCallback retry) {
              return TextButton(
                onPressed: retry,
                child: Text('error:$code:$message'),
              );
            },
            onData: (String data) => Text('data:$data'),
          ),
        ),
      );

      expect(find.text(stateCase.expectedText), findsOneWidget);

      if (stateCase.state is GtexError<String>) {
        await tester.tap(find.text('error:E_TIMEOUT:Timed out'));
        expect(retryCount, 1);
      }
    }
  });
}

void _noop() {}

class _AsyncStateCase {
  const _AsyncStateCase({required this.state, required this.build});

  final GtexAsyncSurfaceState state;
  final Widget Function() build;
}

class _SurfaceStateCase {
  const _SurfaceStateCase({required this.expectedText, required this.state});

  final String expectedText;
  final GtexSurfaceState<String> state;
}

class _TestApp extends StatelessWidget {
  const _TestApp({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      theme: GteShellTheme.build(),
      home: Scaffold(body: Center(child: child)),
    );
  }
}
