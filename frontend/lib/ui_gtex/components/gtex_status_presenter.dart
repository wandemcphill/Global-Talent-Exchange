import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';

/// Semantic tone used by [GtexStatusPresenter] across all GTEX shell surfaces.
enum GtexSemanticStatusKind {
  warning,
  info,
  success,
  danger,
  dangerOutline,
  live,
  neutral,
}

/// Optional presentation context that refines the human-readable status label
/// (Document F10: "Pending" / "In review" / "Awaiting you").
enum GtexStatusContext {
  general,
  review,
  decisionRequired,
  offer,
  transfer,
  financial,
}

/// Immutable presentation descriptor produced by [GtexStatusPresenter].
@immutable
class GtexPresentedStatus {
  const GtexPresentedStatus({
    required this.rawValue,
    required this.normalizedValue,
    required this.label,
    required this.kind,
    required this.color,
    required this.icon,
    this.outlined = false,
    this.pulsing = false,
    this.isUnknown = false,
    this.isPendingLike = false,
    this.isTerminal = false,
  });

  final String rawValue;
  final String normalizedValue;
  final String label;
  final GtexSemanticStatusKind kind;
  final Color color;
  final IconData icon;
  final bool outlined;
  final bool pulsing;
  final bool isUnknown;
  final bool isPendingLike;
  final bool isTerminal;
}

/// Canonical status presenter (Master Plan Document F10).
///
/// Maps every backend status value to a deterministic label, colour, and icon
/// so status is never communicated by colour alone.
class GtexStatusPresenter {
  const GtexStatusPresenter._();

  static final Set<String> _loggedUnknownStatuses = <String>{};

  static const Set<String> _warningPendingValues = <String>{
    'pending',
    'requested',
    'awaiting_payment',
    'payment_submitted',
    'draft',
    'pending_kyc',
    'pending_review',
    'under_review',
    'reviewing',
    'open',
    'recommended',
    'scheduled',
    'awaiting_contract_offer',
    'player_delayed',
    'counter_offer',
  };

  static const Set<String> _processingInfoValues = <String>{
    'processing',
    'held',
  };

  static const Set<String> _confirmedSuccessValues = <String>{
    'verified',
    'committed',
    'confirmed',
    'completed',
    'paid',
    'approved',
    'accepted',
    'executed',
    'published',
    'finished',
  };

  static const Set<String> _failedDangerValues = <String>{
    'failed',
    'rejected',
    'cancelled',
    'canceled',
    'expired',
    'blocked',
    'coach_blocked',
    'collapsed',
  };

  static const Set<String> _reversedDangerOutlineValues = <String>{
    'reversed',
    'retracted',
    'disputed',
  };

  /// Normalize a raw backend status string into snake_case lower ASCII.
  static String normalize(String? rawStatus) {
    final String trimmed = (rawStatus ?? '').trim().toLowerCase();
    if (trimmed.isEmpty) {
      return '';
    }
    return trimmed
        .replaceAll(RegExp(r'[\s\-]+'), '_')
        .replaceAll(RegExp(r'_+'), '_');
  }

  /// Resolve a backend status string into a [GtexPresentedStatus].
  static GtexPresentedStatus present(
    String? rawStatus, {
    GtexStatusContext context = GtexStatusContext.general,
  }) {
    final String raw = (rawStatus ?? '').trim();
    final String normalized = normalize(raw);

    if (_warningPendingValues.contains(normalized)) {
      return GtexPresentedStatus(
        rawValue: raw,
        normalizedValue: normalized,
        label: _resolvePendingLabel(normalized, context),
        kind: GtexSemanticStatusKind.warning,
        color: GtexColors.navy.warning,
        icon: Icons.schedule_rounded,
        isPendingLike: true,
      );
    }

    if (_processingInfoValues.contains(normalized)) {
      final bool isHeld = normalized == 'held';
      return GtexPresentedStatus(
        rawValue: raw,
        normalizedValue: normalized,
        label: isHeld ? 'On hold' : 'Processing',
        kind: GtexSemanticStatusKind.info,
        color: GtexColors.navy.info,
        icon:
            isHeld
                ? Icons.pause_circle_outline_rounded
                : Icons.sync_rounded,
        isPendingLike: true,
      );
    }

    if (_confirmedSuccessValues.contains(normalized)) {
      return GtexPresentedStatus(
        rawValue: raw,
        normalizedValue: normalized,
        label: _resolveConfirmedLabel(normalized, context),
        kind: GtexSemanticStatusKind.success,
        color: GtexColors.navy.success,
        icon: Icons.check_circle_outline_rounded,
        isTerminal: true,
      );
    }

    if (_failedDangerValues.contains(normalized)) {
      return GtexPresentedStatus(
        rawValue: raw,
        normalizedValue: normalized,
        label: _resolveDangerLabel(normalized),
        kind: GtexSemanticStatusKind.danger,
        color: GtexColors.navy.danger,
        icon: Icons.cancel_outlined,
        isTerminal: true,
      );
    }

    if (_reversedDangerOutlineValues.contains(normalized)) {
      return GtexPresentedStatus(
        rawValue: raw,
        normalizedValue: normalized,
        label: _resolveReversedLabel(normalized),
        kind: GtexSemanticStatusKind.dangerOutline,
        color: GtexColors.navy.danger,
        icon:
            normalized == 'disputed'
                ? Icons.flag_outlined
                : Icons.undo_rounded,
        outlined: true,
        isTerminal: normalized != 'disputed',
      );
    }

    if (normalized == 'countered') {
      return GtexPresentedStatus(
        rawValue: raw,
        normalizedValue: normalized,
        label: 'Countered',
        kind: GtexSemanticStatusKind.info,
        color: GtexColors.navy.info,
        icon: Icons.swap_horiz_rounded,
        isPendingLike: true,
      );
    }

    if (normalized == 'live') {
      return GtexPresentedStatus(
        rawValue: raw,
        normalizedValue: normalized,
        label: 'Live',
        kind: GtexSemanticStatusKind.live,
        color: GtexColors.navy.live,
        icon: Icons.sensors_rounded,
        pulsing: true,
      );
    }

    final String humanized = humanizeUnknown(raw);
    if (normalized.isNotEmpty && _loggedUnknownStatuses.add(normalized)) {
      debugPrint(
        '[GtexStatusPresenter] Unknown backend status "$raw" humanized as "$humanized".',
      );
    }
    return GtexPresentedStatus(
      rawValue: raw,
      normalizedValue: normalized,
      label: humanized,
      kind: GtexSemanticStatusKind.neutral,
      color: GtexColors.navy.textSecondary,
      icon: Icons.info_outline_rounded,
      isUnknown: true,
    );
  }

  /// Humanize an unknown backend status into sentence case.
  static String humanizeUnknown(String? rawStatus) {
    final String normalized = normalize(rawStatus);
    if (normalized.isEmpty) {
      return 'Unknown';
    }
    final List<String> words = normalized
        .split('_')
        .where((String segment) => segment.isNotEmpty)
        .toList(growable: false);
    if (words.isEmpty) {
      return 'Unknown';
    }
    final String first = words.first;
    final String firstCapitalized =
        '${first[0].toUpperCase()}${first.substring(1)}';
    if (words.length == 1) {
      return firstCapitalized;
    }
    return '$firstCapitalized ${words.skip(1).join(' ')}';
  }

  static String _resolvePendingLabel(
    String normalized,
    GtexStatusContext context,
  ) {
    switch (normalized) {
      case 'pending_review':
      case 'under_review':
      case 'reviewing':
      case 'pending_kyc':
      case 'payment_submitted':
        return 'In review';
      case 'recommended':
        return context == GtexStatusContext.decisionRequired
            ? 'Awaiting you'
            : 'Pending';
      case 'open':
        return context == GtexStatusContext.decisionRequired
            ? 'Awaiting you'
            : 'Pending';
      case 'awaiting_contract_offer':
        return 'Awaiting Contract Offer';
      case 'player_delayed':
        return 'Player Delayed';
      case 'counter_offer':
        return 'Counter Offer';
      default:
        if (context == GtexStatusContext.review) {
          return 'In review';
        }
        if (context == GtexStatusContext.decisionRequired) {
          return 'Awaiting you';
        }
        return 'Pending';
    }
  }

  static String _resolveConfirmedLabel(
    String normalized,
    GtexStatusContext context,
  ) {
    switch (normalized) {
      case 'completed':
      case 'executed':
      case 'finished':
        return 'Done';
      default:
        return context == GtexStatusContext.financial
            ? 'Confirmed'
            : 'Confirmed';
    }
  }

  static String _resolveDangerLabel(String normalized) {
    switch (normalized) {
      case 'rejected':
        return 'Rejected';
      case 'coach_blocked':
        return 'Coach Blocked';
      case 'collapsed':
        return 'Collapsed';
      case 'expired':
        return 'Expired';
      case 'blocked':
        return 'Blocked';
      case 'cancelled':
      case 'canceled':
        return 'Cancelled';
      default:
        return 'Failed';
    }
  }

  static String _resolveReversedLabel(String normalized) {
    switch (normalized) {
      case 'retracted':
        return 'Retracted';
      case 'disputed':
        return 'Disputed';
      default:
        return 'Reversed';
    }
  }
}
