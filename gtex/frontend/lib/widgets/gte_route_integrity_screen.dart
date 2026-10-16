import 'package:flutter/material.dart';

import 'gte_shell_theme.dart';
import 'gte_surface_panel.dart';

class GteRouteIntegrityScreen extends StatelessWidget {
  const GteRouteIntegrityScreen({
    super.key,
    this.eyebrow,
    required this.title,
    required this.message,
    required this.icon,
    this.actionLabel,
    this.onAction,
    this.accentColor,
  });

  const GteRouteIntegrityScreen.blocked({
    super.key,
    this.eyebrow = 'ROUTE BLOCKED',
    required this.title,
    required this.message,
    this.icon = Icons.block_outlined,
    this.actionLabel,
    this.onAction,
    this.accentColor = GteShellTheme.negative,
  });

  const GteRouteIntegrityScreen.preview({
    super.key,
    this.eyebrow = 'PREVIEW ONLY',
    required this.title,
    required this.message,
    this.icon = Icons.visibility_outlined,
    this.actionLabel,
    this.onAction,
    this.accentColor = GteShellTheme.accentWarm,
  });

  const GteRouteIntegrityScreen.hidden({
    super.key,
    this.eyebrow = 'NOT IN ACTIVE SHELL',
    required this.title,
    required this.message,
    this.icon = Icons.visibility_off_outlined,
    this.actionLabel,
    this.onAction,
    this.accentColor = GteShellTheme.textMuted,
  });

  final String? eyebrow;
  final String title;
  final String message;
  final IconData icon;
  final String? actionLabel;
  final VoidCallback? onAction;
  final Color? accentColor;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final theme = GteShellTheme.definitionOf(context);
    final Color accent = accentColor ?? theme.primaryColor;
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: SafeArea(
          child: LayoutBuilder(
            builder: (BuildContext context, BoxConstraints viewport) {
              return SingleChildScrollView(
                padding: const EdgeInsets.all(20),
                child: ConstrainedBox(
                  constraints: BoxConstraints(minHeight: viewport.maxHeight),
                  child: Center(
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 860),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: <Widget>[
                          GteSurfacePanel(
                            emphasized: true,
                            accentColor: accent,
                            padding: const EdgeInsets.all(24),
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                Wrap(
                                  spacing: 10,
                                  runSpacing: 10,
                                  crossAxisAlignment: WrapCrossAlignment.center,
                                  children: <Widget>[
                                    Container(
                                      width: 54,
                                      height: 54,
                                      decoration: BoxDecoration(
                                        borderRadius: BorderRadius.circular(
                                          tokens.radiusMedium,
                                        ),
                                        color: accent.withValues(alpha: 0.16),
                                        border: Border.all(
                                          color: accent.withValues(alpha: 0.28),
                                        ),
                                      ),
                                      child: Icon(
                                        icon,
                                        color: accent,
                                        size: 28,
                                      ),
                                    ),
                                    _IntegrityBadge(
                                      label: eyebrow ?? 'ROUTE STATUS',
                                      accent: accent,
                                    ),
                                    _IntegrityBadge(
                                      label: _surfaceLabel(),
                                      accent: theme.secondaryColor,
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 20),
                                Text(
                                  title,
                                  style: Theme.of(
                                    context,
                                  ).textTheme.headlineMedium?.copyWith(
                                    color: tokens.textPrimary,
                                    fontWeight: FontWeight.w900,
                                  ),
                                ),
                                const SizedBox(height: 12),
                                Text(
                                  message,
                                  style: Theme.of(
                                    context,
                                  ).textTheme.bodyLarge?.copyWith(
                                    color: tokens.textMuted,
                                    height: 1.5,
                                  ),
                                ),
                                if (actionLabel != null &&
                                    onAction != null) ...<Widget>[
                                  const SizedBox(height: 22),
                                  FilledButton.icon(
                                    onPressed: onAction,
                                    icon: const Icon(
                                      Icons.arrow_forward_rounded,
                                    ),
                                    label: Text(actionLabel!),
                                  ),
                                ],
                              ],
                            ),
                          ),
                          const SizedBox(height: 18),
                          GteSurfacePanel(
                            accentColor: theme.secondaryColor,
                            padding: const EdgeInsets.all(20),
                            child: LayoutBuilder(
                              builder: (
                                BuildContext context,
                                BoxConstraints constraints,
                              ) {
                                final bool stacked = constraints.maxWidth < 620;
                                final Widget truthNote = _IntegrityNote(
                                  label: 'Route Truth',
                                  body: _truthMessage(),
                                );
                                final Widget mountedShellNote = _IntegrityNote(
                                  label: 'Mounted Shell',
                                  body:
                                      'The active shell keeps its current route classification intact and avoids fake live or fallback-only behavior here.',
                                );
                                if (stacked) {
                                  return Column(
                                    mainAxisSize: MainAxisSize.min,
                                    children: <Widget>[
                                      truthNote,
                                      const SizedBox(height: 14),
                                      mountedShellNote,
                                    ],
                                  );
                                }
                                return Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: <Widget>[
                                    Expanded(child: truthNote),
                                    const SizedBox(width: 14),
                                    Expanded(child: mountedShellNote),
                                  ],
                                );
                              },
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }

  String _surfaceLabel() {
    final String value = (eyebrow ?? '').toUpperCase();
    if (value.contains('HIDDEN')) {
      return 'ACTIVE SHELL OFF';
    }
    if (value.contains('PREVIEW')) {
      return 'PREVIEW DISCLOSURE';
    }
    if (value.contains('BLOCKED')) {
      return 'LIVE GATE ACTIVE';
    }
    return 'INTEGRITY SURFACE';
  }

  String _truthMessage() {
    final String value = (eyebrow ?? '').toUpperCase();
    if (value.contains('HIDDEN')) {
      return 'This surface remains outside the active shell until the shipped runtime can expose it honestly.';
    }
    if (value.contains('PREVIEW')) {
      return 'This route stays in preview mode so the product can disclose capability without implying live runtime support.';
    }
    return 'This surface remains visibly blocked until the real runtime, permissions, or backend conditions are actually available.';
  }
}

class _IntegrityBadge extends StatelessWidget {
  const _IntegrityBadge({required this.label, required this.accent});

  final String label;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(tokens.radiusPill),
        border: Border.all(color: accent.withValues(alpha: 0.28)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(
          color: accent,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.6,
        ),
      ),
    );
  }
}

class _IntegrityNote extends StatelessWidget {
  const _IntegrityNote({required this.label, required this.body});

  final String label;
  final String body;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: tokens.surfaceHighlight.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(tokens.radiusMedium),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.84)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            label,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: tokens.textPrimary,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            body,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: tokens.textMuted),
          ),
        ],
      ),
    );
  }
}
