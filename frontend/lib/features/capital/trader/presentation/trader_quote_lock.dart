import 'dart:math' as math;

import 'package:flutter/material.dart';

enum TraderQuoteLockPhase { idle, locked, expired }

class TraderQuoteLock {
  const TraderQuoteLock({
    required this.id,
    required this.price,
    required this.amount,
    required this.currency,
    this.validUntil,
    this.lockedUntil,
    this.lockSecondsRemaining,
    this.auditRef,
  });

  final String id;
  final double price;
  final double amount;
  final String currency;
  final DateTime? validUntil;
  final DateTime? lockedUntil;
  final int? lockSecondsRemaining;
  final String? auditRef;
}

class TraderQuoteLockState {
  const TraderQuoteLockState._({
    required this.phase,
    this.quote,
    this.secondsRemaining,
    this.totalSeconds,
    this.message,
  });

  const TraderQuoteLockState.idle()
    : this._(
        phase: TraderQuoteLockPhase.idle,
        message: 'Request a backend quote to lock the price.',
      );

  const TraderQuoteLockState.expired({TraderQuoteLock? quote, String? message})
    : this._(
        phase: TraderQuoteLockPhase.expired,
        quote: quote,
        secondsRemaining: 0,
        totalSeconds: 1,
        message: message ?? 'Quote expired - refresh for new price.',
      );

  const TraderQuoteLockState.locked({
    required TraderQuoteLock quote,
    required int secondsRemaining,
    int? totalSeconds,
  }) : this._(
         phase: TraderQuoteLockPhase.locked,
         quote: quote,
         secondsRemaining: secondsRemaining,
         totalSeconds: totalSeconds,
         message: 'Quote locked by backend.',
       );

  factory TraderQuoteLockState.fromBackend(
    TraderQuoteLock? quote, {
    DateTime? now,
  }) {
    if (quote == null) {
      return const TraderQuoteLockState.idle();
    }

    final int? backendSeconds = quote.lockSecondsRemaining;
    final DateTime? backendLockedUntil = quote.lockedUntil;
    int? secondsRemaining;
    if (backendSeconds != null) {
      secondsRemaining = backendSeconds;
    } else if (backendLockedUntil != null) {
      final DateTime comparisonTime = now ?? DateTime.now().toUtc();
      secondsRemaining =
          backendLockedUntil
              .toUtc()
              .difference(comparisonTime.toUtc())
              .inSeconds;
    }

    if (secondsRemaining == null) {
      return TraderQuoteLockState.expired(
        quote: quote,
        message: 'Quote lock unavailable - refresh for backend lock.',
      );
    }
    if (secondsRemaining <= 0) {
      return TraderQuoteLockState.expired(quote: quote);
    }

    return TraderQuoteLockState.locked(
      quote: quote,
      secondsRemaining: secondsRemaining,
      totalSeconds: math.max(secondsRemaining, 1),
    );
  }

  final TraderQuoteLockPhase phase;
  final TraderQuoteLock? quote;
  final int? secondsRemaining;
  final int? totalSeconds;
  final String? message;

  bool get canConfirm {
    return phase == TraderQuoteLockPhase.locked &&
        quote != null &&
        (secondsRemaining ?? 0) > 0;
  }

  double get progress {
    final int remaining = secondsRemaining ?? 0;
    final int total = math.max(totalSeconds ?? remaining, 1);
    return (remaining / total).clamp(0, 1).toDouble();
  }

  String get statusLabel {
    return switch (phase) {
      TraderQuoteLockPhase.idle => 'Awaiting backend quote lock',
      TraderQuoteLockPhase.locked => '${secondsRemaining ?? 0}s remaining',
      TraderQuoteLockPhase.expired => 'Quote expired',
    };
  }
}

class QuoteLockCard extends StatelessWidget {
  const QuoteLockCard({super.key, required this.state, this.onRefresh});

  final TraderQuoteLockState state;
  final VoidCallback? onRefresh;

  @override
  Widget build(BuildContext context) {
    final Color accent = switch (state.phase) {
      TraderQuoteLockPhase.locked => const Color(0xFF5FE3A1),
      TraderQuoteLockPhase.expired => const Color(0xFFFFD66B),
      TraderQuoteLockPhase.idle => const Color(0xFF79A7FF),
    };
    final TraderQuoteLock? quote = state.quote;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: accent.withValues(alpha: 0.42)),
        color: accent.withValues(alpha: 0.10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(_iconForPhase(state.phase), color: accent, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Quote lock',
                  style: Theme.of(
                    context,
                  ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w900),
                ),
              ),
              Text(
                state.statusLabel,
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: accent,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          LinearProgressIndicator(
            minHeight: 6,
            value:
                state.phase == TraderQuoteLockPhase.idle
                    ? null
                    : state.progress,
            color: accent,
            backgroundColor: Colors.white.withValues(alpha: 0.10),
          ),
          const SizedBox(height: 10),
          Text(
            quote == null
                ? state.message ?? 'Request a backend quote to lock the price.'
                : '${quote.amount.toStringAsFixed(2)} at ${quote.price.toStringAsFixed(4)} ${quote.currency}',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          if (_cleanAuditRef(quote?.auditRef) != null) ...<Widget>[
            const SizedBox(height: 8),
            TraderActionAuditReference(auditRef: quote!.auditRef),
          ],
          if (state.phase == TraderQuoteLockPhase.expired) ...<Widget>[
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: onRefresh,
              icon: const Icon(Icons.refresh),
              label: const Text('Refresh quote'),
            ),
          ],
        ],
      ),
    );
  }
}

class TraderActionAuditReference extends StatelessWidget {
  const TraderActionAuditReference({super.key, required this.auditRef});

  final String? auditRef;

  @override
  Widget build(BuildContext context) {
    final String? ref = _cleanAuditRef(auditRef);
    if (ref == null) {
      return const SizedBox.shrink();
    }
    return Text(
      'Audit reference: $ref',
      style: Theme.of(
        context,
      ).textTheme.labelMedium?.copyWith(fontWeight: FontWeight.w800),
    );
  }
}

class ConfirmOrderBar extends StatelessWidget {
  const ConfirmOrderBar({
    super.key,
    required this.quoteLock,
    required this.balanceAvailable,
    required this.onConfirm,
    this.actionLabel = 'Place order',
  });

  final TraderQuoteLockState quoteLock;
  final bool balanceAvailable;
  final VoidCallback? onConfirm;
  final String actionLabel;

  @override
  Widget build(BuildContext context) {
    final bool enabled =
        quoteLock.canConfirm && balanceAvailable && onConfirm != null;
    return FilledButton.icon(
      key: const ValueKey<String>('trader-confirm-order'),
      onPressed: enabled ? onConfirm : null,
      icon: Icon(enabled ? Icons.verified_outlined : Icons.lock_outline),
      label: Text(_label(enabled)),
    );
  }

  String _label(bool enabled) {
    if (enabled) {
      return actionLabel;
    }
    if (!balanceAvailable) {
      return 'Balance blocked';
    }
    return switch (quoteLock.phase) {
      TraderQuoteLockPhase.expired => 'Quote expired - refresh',
      TraderQuoteLockPhase.idle => 'Awaiting auditable quote',
      TraderQuoteLockPhase.locked => 'Awaiting auditable quote',
    };
  }
}

enum TraderPaymentRail { koraPay, manualBankTransfer }

extension TraderPaymentRailCopy on TraderPaymentRail {
  String get label {
    return switch (this) {
      TraderPaymentRail.koraPay => 'KoraPay',
      TraderPaymentRail.manualBankTransfer => 'Manual bank transfer',
    };
  }

  String get subtitle {
    return switch (this) {
      TraderPaymentRail.koraPay => 'Backend checkout redirect',
      TraderPaymentRail.manualBankTransfer => 'Manual treasury review',
    };
  }
}

class TraderPaymentRailSelector extends StatelessWidget {
  const TraderPaymentRailSelector({
    super.key,
    required this.selected,
    required this.onChanged,
  });

  final TraderPaymentRail selected;
  final ValueChanged<TraderPaymentRail>? onChanged;

  @override
  Widget build(BuildContext context) {
    return SegmentedButton<TraderPaymentRail>(
      segments: TraderPaymentRail.values
          .map(
            (TraderPaymentRail rail) => ButtonSegment<TraderPaymentRail>(
              value: rail,
              icon: Icon(
                rail == TraderPaymentRail.koraPay
                    ? Icons.bolt_outlined
                    : Icons.account_balance_outlined,
              ),
              label: Text(rail.label),
            ),
          )
          .toList(growable: false),
      selected: <TraderPaymentRail>{selected},
      onSelectionChanged:
          onChanged == null
              ? null
              : (Set<TraderPaymentRail> next) => onChanged!(next.first),
    );
  }
}

String? _cleanAuditRef(String? value) {
  final String? ref = value?.trim();
  if (ref == null || ref.isEmpty) {
    return null;
  }
  return ref;
}

IconData _iconForPhase(TraderQuoteLockPhase phase) {
  return switch (phase) {
    TraderQuoteLockPhase.idle => Icons.schedule_outlined,
    TraderQuoteLockPhase.locked => Icons.lock_clock_outlined,
    TraderQuoteLockPhase.expired => Icons.lock_reset_outlined,
  };
}
