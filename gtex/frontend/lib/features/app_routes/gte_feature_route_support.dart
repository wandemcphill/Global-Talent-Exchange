import 'package:flutter/material.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

enum GteFeatureRouteAccess {
  public,
  authenticated,
  admin,
}

enum GteFeatureRouteResultKind {
  ready,
  empty,
  unavailable,
  forbidden,
}

class GteFeatureRouteMetric {
  const GteFeatureRouteMetric({
    required this.label,
    required this.value,
    this.positive = false,
  });

  final String label;
  final String value;
  final bool positive;
}

class GteFeatureRouteAction {
  const GteFeatureRouteAction({
    required this.label,
    required this.icon,
    required this.onPressed,
    this.primary = false,
  });

  final String label;
  final IconData icon;
  final Future<void> Function(BuildContext context) onPressed;
  final bool primary;
}

class GteFeatureRouteContent {
  const GteFeatureRouteContent({
    required this.eyebrow,
    required this.title,
    required this.description,
    required this.icon,
    required this.accentColor,
    this.metrics = const <GteFeatureRouteMetric>[],
    this.highlights = const <String>[],
    this.notes = const <String>[],
    this.actions = const <GteFeatureRouteAction>[],
  });

  final String eyebrow;
  final String title;
  final String description;
  final IconData icon;
  final Color accentColor;
  final List<GteFeatureRouteMetric> metrics;
  final List<String> highlights;
  final List<String> notes;
  final List<GteFeatureRouteAction> actions;
}

class GteFeatureRouteResult {
  const GteFeatureRouteResult._({
    required this.kind,
    required this.title,
    required this.message,
    required this.icon,
    required this.accentColor,
    this.content,
    this.actionLabel,
    this.onAction,
  });

  final GteFeatureRouteResultKind kind;
  final String title;
  final String message;
  final IconData icon;
  final Color accentColor;
  final GteFeatureRouteContent? content;
  final String? actionLabel;
  final Future<void> Function(BuildContext context)? onAction;

  GteFeatureRouteResult.ready(
    GteFeatureRouteContent content,
  ) : this._(
          kind: GteFeatureRouteResultKind.ready,
          title: '',
          message: '',
          icon: Icons.check_circle_outline,
          accentColor: content.accentColor,
          content: content,
        );

  const GteFeatureRouteResult.empty({
    required String title,
    required String message,
    required IconData icon,
    required Color accentColor,
    String? actionLabel,
    Future<void> Function(BuildContext context)? onAction,
  }) : this._(
          kind: GteFeatureRouteResultKind.empty,
          title: title,
          message: message,
          icon: icon,
          accentColor: accentColor,
          actionLabel: actionLabel,
          onAction: onAction,
        );

  const GteFeatureRouteResult.unavailable({
    required String title,
    required String message,
    required IconData icon,
    required Color accentColor,
    String? actionLabel,
    Future<void> Function(BuildContext context)? onAction,
  }) : this._(
          kind: GteFeatureRouteResultKind.unavailable,
          title: title,
          message: message,
          icon: icon,
          accentColor: accentColor,
          actionLabel: actionLabel,
          onAction: onAction,
        );

  const GteFeatureRouteResult.forbidden({
    required String title,
    required String message,
    required IconData icon,
    required Color accentColor,
    String? actionLabel,
    Future<void> Function(BuildContext context)? onAction,
  }) : this._(
          kind: GteFeatureRouteResultKind.forbidden,
          title: title,
          message: message,
          icon: icon,
          accentColor: accentColor,
          actionLabel: actionLabel,
          onAction: onAction,
        );
}

class GteAsyncFeatureRouteScreen extends StatefulWidget {
  const GteAsyncFeatureRouteScreen({
    super.key,
    required this.dependencies,
    required this.access,
    required this.loadingTitle,
    required this.lockedTitle,
    required this.lockedMessage,
    required this.lockedIcon,
    required this.lockedAccentColor,
    required this.forbiddenTitle,
    required this.forbiddenMessage,
    required this.forbiddenIcon,
    required this.forbiddenAccentColor,
    required this.load,
    this.forbiddenActionLabel,
    this.onForbiddenAction,
  });

  final GteNavigationDependencies dependencies;
  final GteFeatureRouteAccess access;
  final String loadingTitle;
  final String lockedTitle;
  final String lockedMessage;
  final IconData lockedIcon;
  final Color lockedAccentColor;
  final String forbiddenTitle;
  final String forbiddenMessage;
  final IconData forbiddenIcon;
  final Color forbiddenAccentColor;
  final Future<GteFeatureRouteResult> Function() load;
  final String? forbiddenActionLabel;
  final Future<void> Function(BuildContext context)? onForbiddenAction;

  @override
  State<GteAsyncFeatureRouteScreen> createState() =>
      _GteAsyncFeatureRouteScreenState();
}

class _GteAsyncFeatureRouteScreenState
    extends State<GteAsyncFeatureRouteScreen> {
  GteFeatureRouteResult? _result;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _loadIfAllowed();
  }

  Future<void> _loadIfAllowed() async {
    if (!_canLoad) {
      return;
    }
    await _load();
  }

  Future<void> _load() async {
    setState(() {
      _result = null;
      _error = null;
    });
    try {
      final GteFeatureRouteResult result = await widget.load();
      if (!mounted) {
        return;
      }
      setState(() {
        _result = result;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = error;
      });
    }
  }

  bool get _needsAuthentication =>
      widget.access != GteFeatureRouteAccess.public &&
      !widget.dependencies.isAuthenticated;

  bool get _needsAdmin =>
      widget.access == GteFeatureRouteAccess.admin &&
      !widget.dependencies.isAdminRole;

  bool get _canLoad => !_needsAuthentication && !_needsAdmin;

  Future<void> _openLogin() async {
    final bool signedIn =
        await widget.dependencies.onOpenLogin?.call(context) ?? false;
    if (!mounted || !signedIn) {
      return;
    }
    await _load();
  }

  Future<void> _handleResultAction(
    Future<void> Function(BuildContext context)? action,
  ) async {
    if (action == null) {
      await _load();
      return;
    }
    await action(context);
    if (mounted) {
      await _loadIfAllowed();
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_needsAuthentication) {
      return _FeatureRouteScaffold(
        child: GteStatePanel(
          eyebrow: 'PROTECTED ROUTE',
          title: widget.lockedTitle,
          message: widget.lockedMessage,
          actionLabel: 'Sign in',
          onAction: _openLogin,
          icon: widget.lockedIcon,
          accentColor: widget.lockedAccentColor,
        ),
      );
    }

    if (_needsAdmin) {
      return _FeatureRouteScaffold(
        child: GteStatePanel(
          eyebrow: 'PERMISSION REQUIRED',
          title: widget.forbiddenTitle,
          message: widget.forbiddenMessage,
          actionLabel: widget.forbiddenActionLabel,
          onAction: widget.onForbiddenAction == null
              ? null
              : () => _handleResultAction(widget.onForbiddenAction),
          icon: widget.forbiddenIcon,
          accentColor: widget.forbiddenAccentColor,
        ),
      );
    }

    if (_error != null) {
      return _FeatureRouteScaffold(
        child: GteStatePanel(
          eyebrow: 'ROUTE ERROR',
          title: 'Feature route unavailable',
          message: _error.toString(),
          actionLabel: 'Retry',
          onAction: _load,
          icon: Icons.route_outlined,
          accentColor: GteShellTheme.negative,
        ),
      );
    }

    if (_result == null) {
      return _FeatureLoadingScaffold(title: widget.loadingTitle);
    }

    final GteFeatureRouteResult result = _result!;
    if (result.kind == GteFeatureRouteResultKind.ready &&
        result.content != null) {
      return _FeatureReadyScaffold(
        content: result.content!,
        onRefresh: _load,
      );
    }

    return _FeatureRouteScaffold(
      child: GteStatePanel(
        eyebrow: result.kind == GteFeatureRouteResultKind.empty
            ? 'EMPTY STATE'
            : result.kind == GteFeatureRouteResultKind.forbidden
                ? 'PERMISSION REQUIRED'
                : 'BACKEND UNAVAILABLE',
        title: result.title,
        message: result.message,
        actionLabel: result.actionLabel ?? 'Retry',
        onAction: () => _handleResultAction(result.onAction),
        icon: result.icon,
        accentColor: result.accentColor,
      ),
    );
  }
}

class _FeatureLoadingScaffold extends StatelessWidget {
  const _FeatureLoadingScaffold({
    required this.title,
  });

  final String title;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              const CircularProgressIndicator(),
              const SizedBox(height: 16),
              Text(title, style: Theme.of(context).textTheme.titleMedium),
            ],
          ),
        ),
      ),
    );
  }
}

class _FeatureRouteScaffold extends StatelessWidget {
  const _FeatureRouteScaffold({
    required this.child,
  });

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 620),
              child: child,
            ),
          ),
        ),
      ),
    );
  }
}

class _FeatureReadyScaffold extends StatelessWidget {
  const _FeatureReadyScaffold({
    required this.content,
    required this.onRefresh,
  });

  final GteFeatureRouteContent content;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: RefreshIndicator(
          onRefresh: onRefresh,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 120),
            children: <Widget>[
              GteSurfacePanel(
                emphasized: true,
                accentColor: content.accentColor,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      content.eyebrow,
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                            color: content.accentColor,
                            letterSpacing: 1.1,
                          ),
                    ),
                    const SizedBox(height: 10),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Icon(content.icon, color: content.accentColor),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text(
                                content.title,
                                style:
                                    Theme.of(context).textTheme.headlineSmall,
                              ),
                              const SizedBox(height: 8),
                              Text(
                                content.description,
                                style: Theme.of(context).textTheme.bodyMedium,
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    if (content.metrics.isNotEmpty) ...<Widget>[
                      const SizedBox(height: 14),
                      Wrap(
                        spacing: 10,
                        runSpacing: 10,
                        children: content.metrics
                            .map(
                              (GteFeatureRouteMetric metric) => GteMetricChip(
                                label: metric.label,
                                value: metric.value,
                                positive: metric.positive,
                              ),
                            )
                            .toList(growable: false),
                      ),
                    ],
                    if (content.actions.isNotEmpty) ...<Widget>[
                      const SizedBox(height: 14),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: content.actions
                            .map(
                              (GteFeatureRouteAction action) => action.primary
                                  ? FilledButton.icon(
                                      onPressed: () =>
                                          action.onPressed(context),
                                      icon: Icon(action.icon),
                                      label: Text(action.label),
                                    )
                                  : FilledButton.tonalIcon(
                                      onPressed: () =>
                                          action.onPressed(context),
                                      icon: Icon(action.icon),
                                      label: Text(action.label),
                                    ),
                            )
                            .toList(growable: false),
                      ),
                    ],
                  ],
                ),
              ),
              if (content.highlights.isNotEmpty) ...<Widget>[
                const SizedBox(height: 18),
                GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'What is wired',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 12),
                      for (final String line in content.highlights) ...<Widget>[
                        Text(line,
                            style: Theme.of(context).textTheme.bodyMedium),
                        if (line != content.highlights.last)
                          const SizedBox(height: 8),
                      ],
                    ],
                  ),
                ),
              ],
              if (content.notes.isNotEmpty) ...<Widget>[
                const SizedBox(height: 18),
                GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Resilience notes',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 12),
                      for (final String line in content.notes) ...<Widget>[
                        Text(line,
                            style: Theme.of(context).textTheme.bodyMedium),
                        if (line != content.notes.last)
                          const SizedBox(height: 8),
                      ],
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
