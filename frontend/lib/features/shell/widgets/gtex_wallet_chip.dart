import 'package:flutter/material.dart';

import '../domain/gtex_surface_state.dart';
import 'gtex_state_panel.dart';

class GtexWalletChip extends StatelessWidget {
  const GtexWalletChip({
    super.key,
    this.balance,
    this.currencyCode,
    this.state,
    this.isLoading = false,
    this.isBlocked = false,
    this.onTap,
  });

  final double? balance;
  final String? currencyCode;
  final GtexSurfaceState? state;
  final bool isLoading;
  final bool isBlocked;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final GtexSurfaceState effectiveState = _effectiveState();
    final Color tone = gtexSurfaceToneFor(theme, effectiveState);
    final String label = _labelFor(effectiveState);
    return Tooltip(
      message: 'Wallet summary: $label',
      child: Semantics(
        liveRegion: effectiveState.requiresAttention,
        button: onTap != null,
        label: 'Wallet $label',
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(8),
            onTap: onTap,
            child: Container(
              height: 38,
              constraints: const BoxConstraints(maxWidth: 190),
              padding: const EdgeInsets.symmetric(horizontal: 12),
              decoration: BoxDecoration(
                color: tone.withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: tone.withValues(alpha: 0.28)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  if (_isProgressState(effectiveState)) ...[
                    SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: tone,
                      ),
                    ),
                  ] else ...[
                    Icon(
                      effectiveState == GtexSurfaceState.blocked
                          ? Icons.account_balance_wallet_outlined
                          : gtexSurfaceIconFor(effectiveState),
                      size: 17,
                      color: tone,
                    ),
                  ],
                  const SizedBox(width: 8),
                  Flexible(
                    child: Text(
                      label,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.labelLarge?.copyWith(
                        color: tone,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  GtexSurfaceState _effectiveState() {
    if (state != null) {
      return state!;
    }
    if (isBlocked) {
      return GtexSurfaceState.blocked;
    }
    if (isLoading) {
      return GtexSurfaceState.syncing;
    }
    if (balance == null) {
      return GtexSurfaceState.empty;
    }
    return GtexSurfaceState.confirmed;
  }

  String _labelFor(GtexSurfaceState state) {
    if (balance != null &&
        (state == GtexSurfaceState.confirmed ||
            state == GtexSurfaceState.data)) {
      return '${currencyCode ?? 'GTE'} ${balance!.toStringAsFixed(2)}';
    }
    switch (state) {
      case GtexSurfaceState.loading:
      case GtexSurfaceState.syncing:
      case GtexSurfaceState.reconnecting:
        return 'Wallet syncing';
      case GtexSurfaceState.empty:
      case GtexSurfaceState.pending:
        return 'Wallet pending';
      case GtexSurfaceState.blocked:
        return 'Wallet blocked';
      case GtexSurfaceState.degraded:
        return 'Wallet degraded';
      case GtexSurfaceState.confirmed:
        return '${currencyCode ?? 'GTE'} ${(balance ?? 0).toStringAsFixed(2)}';
      case GtexSurfaceState.error:
        return 'Wallet error';
    }
  }

  bool _isProgressState(GtexSurfaceState state) {
    switch (state) {
      case GtexSurfaceState.loading:
      case GtexSurfaceState.syncing:
      case GtexSurfaceState.reconnecting:
        return true;
      case GtexSurfaceState.empty:
      case GtexSurfaceState.blocked:
      case GtexSurfaceState.pending:
      case GtexSurfaceState.degraded:
      case GtexSurfaceState.confirmed:
      case GtexSurfaceState.error:
        return false;
    }
  }
}
