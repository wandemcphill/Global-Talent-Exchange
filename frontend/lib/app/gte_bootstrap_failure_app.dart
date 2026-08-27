import 'package:flutter/material.dart';

import '../theme/gte_theme_controller.dart';
import '../theme/gte_theme_registry.dart';
import '../theme/gte_theme_scope.dart';
import '../widgets/gte_shell_theme.dart';
import '../widgets/gte_state_panel.dart';

class GteBootstrapFailureApp extends StatelessWidget {
  const GteBootstrapFailureApp({
    super.key,
    required this.themeController,
    required this.failure,
  });

  final GteThemeController themeController;
  final GteBootstrapFailure failure;

  @override
  Widget build(BuildContext context) {
    return GteThemeControllerScope(
      controller: themeController,
      child: AnimatedBuilder(
        animation: themeController,
        builder: (BuildContext context, Widget? child) {
          return MaterialApp(
            debugShowCheckedModeBanner: false,
            title: 'GTEX Football Universe',
            theme: GteShellTheme.build(themeController.activeTheme),
            home: _GteBootstrapFailureScreen(failure: failure),
          );
        },
      ),
    );
  }
}

class GteBootstrapFailure {
  const GteBootstrapFailure({
    required this.title,
    required this.message,
    required this.command,
    this.followUp,
  });

  final String title;
  final String message;
  final String command;
  final String? followUp;

  factory GteBootstrapFailure.fromError(Object error) {
    final String errorText = error.toString();
    if (errorText.contains('GTE_API_BASE_URL must be set')) {
      return const GteBootstrapFailure(
        title: 'Live configuration missing',
        message:
            'This build cannot open the live GTEX shell because '
            'GTE_API_BASE_URL was not compiled into the app. No routes were '
            'mounted, and the 3D lane never opened.',
        command:
            'flutter run -d <device> '
            '--dart-define=GTE_API_BASE_URL=<reachable-backend-url> '
            '--dart-define=GTE_BACKEND_MODE=live',
        followUp:
            'Provide the deployed or otherwise reachable backend URL for the '
            'target device. Local development may use a guarded fixture or '
            'device-specific transport configuration outside production builds (e.g. adb reverse tcp:8000 tcp:8000).',
      );
    }
    return GteBootstrapFailure(
      title: 'App bootstrap blocked',
      message:
          'GTEX could not finish bootstrapping the app shell, so no live or '
          'fixture routes were mounted.',
      command: errorText,
    );
  }
}

class _GteBootstrapFailureScreen extends StatelessWidget {
  const _GteBootstrapFailureScreen({required this.failure});

  final GteBootstrapFailure failure;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Color muted = GteShellTheme.tokensOf(context).textMuted;
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 760),
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    GteStatePanel(
                      eyebrow: 'CONFIG BLOCKED',
                      title: failure.title,
                      message: failure.message,
                      icon: Icons.warning_amber_rounded,
                      accentColor: GteThemeRegistry.defaultTheme.accentColor,
                    ),
                    const SizedBox(height: 18),
                    DecoratedBox(
                      decoration: BoxDecoration(
                        color: Colors.black.withValues(alpha: 0.24),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(
                          color: Colors.white.withValues(alpha: 0.08),
                        ),
                      ),
                      child: Padding(
                        padding: const EdgeInsets.all(18),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(
                              'Run with',
                              style: theme.textTheme.labelLarge?.copyWith(
                                color: Colors.white,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                            const SizedBox(height: 10),
                            SelectableText(
                              failure.command,
                              style: theme.textTheme.bodyMedium?.copyWith(
                                color: Colors.white,
                                fontFamily: 'Courier',
                                height: 1.45,
                              ),
                            ),
                            if (failure.followUp != null) ...<Widget>[
                              const SizedBox(height: 12),
                              Text(
                                failure.followUp!,
                                style: theme.textTheme.bodySmall?.copyWith(
                                  color: muted,
                                  height: 1.5,
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
