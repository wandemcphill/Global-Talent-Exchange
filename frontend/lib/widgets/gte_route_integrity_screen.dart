import 'package:flutter/material.dart';

import 'gte_shell_theme.dart';
import 'gte_state_panel.dart';

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
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: SafeArea(
          child: Center(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 560),
                child: GteStatePanel(
                  eyebrow: eyebrow,
                  title: title,
                  message: message,
                  actionLabel: actionLabel,
                  onAction: onAction,
                  icon: icon,
                  accentColor: accentColor,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
