import 'package:flutter/material.dart';

import 'gte_state_panel.dart';

/// One-liner for the full async matrix: loading → success | empty | error.
///
/// Screens across GTEX re-implemented this ladder by hand and kept dropping a
/// case, which is how blank surfaces reached production. Routing everything
/// through a single widget guarantees that every async lane renders *some*
/// deliberate state, and that error always carries a retry.
///
/// It composes [GteStatePanel] rather than introducing a second visual
/// language, so existing screens keep their look when they migrate.
class GteAsyncView<T> extends StatelessWidget {
  const GteAsyncView({
    super.key,
    required this.snapshot,
    required this.builder,
    required this.onRetry,
    this.isEmpty,
    this.loadingTitle = 'Loading',
    this.loadingMessage = 'Fetching the latest state from GTEX.',
    this.emptyTitle = 'Nothing here yet',
    this.emptyMessage = 'There is no data to show for this view right now.',
    this.errorTitle = 'Something went wrong',
    this.emptyIcon = Icons.inbox_outlined,
    this.errorIcon = Icons.error_outline,
    this.retryLabel = 'Retry',
    this.emptyActionLabel,
    this.onEmptyAction,
  });

  /// Current state of the async operation.
  final AsyncSnapshot<T> snapshot;

  /// Builds the success surface. Only called with non-null, non-empty data.
  final Widget Function(BuildContext context, T data) builder;

  /// Invoked by the error state's retry button. Required, because an error
  /// with no way forward is a dead end.
  final VoidCallback onRetry;

  /// Decides whether loaded data should render as empty. Defaults to treating
  /// empty [Iterable]s and [Map]s as empty.
  final bool Function(T data)? isEmpty;

  final String loadingTitle;
  final String loadingMessage;
  final String emptyTitle;
  final String emptyMessage;
  final String errorTitle;
  final IconData emptyIcon;
  final IconData errorIcon;
  final String retryLabel;

  /// Optional call-to-action on the empty state (e.g. "Browse competitions").
  final String? emptyActionLabel;
  final VoidCallback? onEmptyAction;

  @override
  Widget build(BuildContext context) {
    if (snapshot.connectionState == ConnectionState.waiting &&
        !snapshot.hasData) {
      return GteStatePanel(
        title: loadingTitle,
        message: loadingMessage,
        isLoading: true,
      );
    }

    if (snapshot.hasError && !snapshot.hasData) {
      return GteStatePanel(
        eyebrow: 'ERROR',
        title: errorTitle,
        message: _describeError(snapshot.error),
        icon: errorIcon,
        actionLabel: retryLabel,
        onAction: onRetry,
      );
    }

    final T? data = snapshot.data;
    if (data == null) {
      return GteStatePanel(
        eyebrow: 'EMPTY',
        title: emptyTitle,
        message: emptyMessage,
        icon: emptyIcon,
        actionLabel: emptyActionLabel ?? retryLabel,
        onAction: onEmptyAction ?? onRetry,
      );
    }

    if (_resolveEmpty(data)) {
      return GteStatePanel(
        eyebrow: 'EMPTY',
        title: emptyTitle,
        message: emptyMessage,
        icon: emptyIcon,
        actionLabel: emptyActionLabel ?? retryLabel,
        onAction: onEmptyAction ?? onRetry,
      );
    }

    return builder(context, data);
  }

  bool _resolveEmpty(T data) {
    final bool Function(T data)? predicate = isEmpty;
    if (predicate != null) {
      return predicate(data);
    }
    if (data is Iterable) {
      return data.isEmpty;
    }
    if (data is Map) {
      return data.isEmpty;
    }
    return false;
  }

  /// Keeps raw exception noise out of the UI while staying specific enough to
  /// be actionable.
  static String _describeError(Object? error) {
    if (error == null) {
      return 'The request failed. Check your connection and try again.';
    }
    final String raw = error.toString().trim();
    if (raw.isEmpty) {
      return 'The request failed. Check your connection and try again.';
    }
    // Strip the conventional Dart "Exception: " prefix for readability.
    const String exceptionPrefix = 'Exception: ';
    final String cleaned =
        raw.startsWith(exceptionPrefix)
            ? raw.substring(exceptionPrefix.length)
            : raw;
    return cleaned.length > 400 ? '${cleaned.substring(0, 400)}…' : cleaned;
  }
}
