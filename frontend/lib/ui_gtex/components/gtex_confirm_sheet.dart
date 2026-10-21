import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';
import '../theme/gtex_typography.dart';

/// Variants for [GtexConfirmSheet] (Document F8).
enum GtexConfirmVariant {
  standard,
  financial,
  destructive,
}

/// Lifecycle states for [GtexConfirmSheet] (Document F8).
enum GtexConfirmSubmissionState {
  idle,
  submitting,
  success,
  error,
}

/// Financial breakdown shown by [GtexConfirmSheet] when
/// [GtexConfirmVariant.financial] is used.
@immutable
class GtexConfirmFinancialDetails {
  const GtexConfirmFinancialDetails({
    required this.amountLabel,
    required this.currencyCode,
    this.feeLabel,
    this.balanceAfterLabel,
    this.idempotencyKey,
  });

  final String amountLabel;
  final String currencyCode;
  final String? feeLabel;
  final String? balanceAfterLabel;
  final String? idempotencyKey;
}

/// Callback invoked when the user confirms an action in [GtexConfirmSheet].
///
/// Receives a deterministic or caller-supplied `idempotencyKey` so financial
/// and consequential requests can attach `Idempotency-Key` headers safely.
typedef GtexConfirmSubmitCallback = Future<void> Function(
  String idempotencyKey,
);

/// Canonical confirmation bottom sheet / dialog for consequential actions
/// (Master Plan Document F8 & M2).
///
/// Enforces:
/// - Single-request lock on double-tap (`_inFlight` guard).
/// - Deterministic or caller-supplied `idempotencyKey` passed to [onConfirm].
/// - Explicit financial summary (`amount`, `fee`, `balanceAfter`, `currencyCode`)
///   for financial actions.
class GtexConfirmSheet extends StatefulWidget {
  const GtexConfirmSheet({
    super.key,
    required this.title,
    required this.summary,
    required this.confirmLabel,
    required this.onConfirm,
    this.cancelLabel = 'Cancel',
    this.variant = GtexConfirmVariant.standard,
    this.financialDetails,
    this.idempotencyKey,
    this.publicAnnouncementNotice,
    this.requireReason = false,
    this.reasonHint = 'Provide reason for audit log',
    this.onSuccessClose = false,
  });

  final String title;
  final String summary;
  final String confirmLabel;
  final String cancelLabel;
  final GtexConfirmVariant variant;
  final GtexConfirmFinancialDetails? financialDetails;
  final String? idempotencyKey;
  final String? publicAnnouncementNotice;
  final bool requireReason;
  final String reasonHint;
  final bool onSuccessClose;
  final GtexConfirmSubmitCallback onConfirm;

  /// Helper to present [GtexConfirmSheet] as a modal bottom sheet.
  static Future<bool?> show(
    BuildContext context, {
    required String title,
    required String summary,
    required String confirmLabel,
    required GtexConfirmSubmitCallback onConfirm,
    String cancelLabel = 'Cancel',
    GtexConfirmVariant variant = GtexConfirmVariant.standard,
    GtexConfirmFinancialDetails? financialDetails,
    String? idempotencyKey,
    String? publicAnnouncementNotice,
    bool requireReason = false,
  }) {
    return showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: GtexColors.navy.bgRaised,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(GtexRadius.sheet),
        ),
      ),
      builder: (BuildContext sheetContext) {
        return GtexConfirmSheet(
          title: title,
          summary: summary,
          confirmLabel: confirmLabel,
          cancelLabel: cancelLabel,
          variant: variant,
          financialDetails: financialDetails,
          idempotencyKey: idempotencyKey,
          publicAnnouncementNotice: publicAnnouncementNotice,
          requireReason: requireReason,
          onSuccessClose: true,
          onConfirm: onConfirm,
        );
      },
    );
  }

  @override
  State<GtexConfirmSheet> createState() => _GtexConfirmSheetState();
}

class _GtexConfirmSheetState extends State<GtexConfirmSheet> {
  GtexConfirmSubmissionState _state = GtexConfirmSubmissionState.idle;
  bool _inFlight = false;
  String? _errorMessage;
  late final String _resolvedIdempotencyKey;
  late final TextEditingController _reasonController;

  @override
  void initState() {
    super.initState();
    _reasonController = TextEditingController();
    _resolvedIdempotencyKey =
        (widget.idempotencyKey ??
                widget.financialDetails?.idempotencyKey ??
                'gtex-idem-${DateTime.now().microsecondsSinceEpoch}')
            .trim();
  }

  @override
  void dispose() {
    _reasonController.dispose();
    super.dispose();
  }

  Future<void> _handleConfirm() async {
    if (_inFlight || _state == GtexConfirmSubmissionState.submitting) {
      return;
    }
    if (widget.requireReason && _reasonController.text.trim().isEmpty) {
      setState(() {
        _state = GtexConfirmSubmissionState.error;
        _errorMessage = 'A reason is required before confirming this action.';
      });
      return;
    }
    _inFlight = true;
    setState(() {
      _state = GtexConfirmSubmissionState.submitting;
      _errorMessage = null;
    });

    try {
      await widget.onConfirm(_resolvedIdempotencyKey);
      if (!mounted) {
        return;
      }
      setState(() {
        _state = GtexConfirmSubmissionState.success;
      });
      if (widget.onSuccessClose && Navigator.of(context).canPop()) {
        Navigator.of(context).pop(true);
      }
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _state = GtexConfirmSubmissionState.error;
        _errorMessage = _sanitizeErrorMessage(error);
      });
    } finally {
      _inFlight = false;
    }
  }

  String _sanitizeErrorMessage(Object error) {
    final String raw = error.toString().trim();
    if (raw.isEmpty) {
      return 'Action could not be completed. Please try again.';
    }
    final String firstLine = raw.split('\n').first.trim();
    return firstLine.replaceFirst(RegExp(r'^Exception:\s*'), '');
  }

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    final Color primaryAccent = switch (widget.variant) {
      GtexConfirmVariant.destructive => navy.danger,
      GtexConfirmVariant.financial || GtexConfirmVariant.standard =>
        navy.gold500,
    };
    final Color primaryForeground = switch (widget.variant) {
      GtexConfirmVariant.destructive => navy.textPrimary,
      GtexConfirmVariant.financial || GtexConfirmVariant.standard =>
        navy.bgBase,
    };

    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          GtexSpacing.md,
          GtexSpacing.md,
          GtexSpacing.md,
          GtexSpacing.md + MediaQuery.viewInsetsOf(context).bottom,
        ),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: navy.bgRaised,
            borderRadius: BorderRadius.circular(GtexRadius.sheet),
            border: Border.all(color: navy.lineSubtle),
          ),
          child: Padding(
            padding: GtexSpacing.cardPadding,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    Icon(
                      switch (widget.variant) {
                        GtexConfirmVariant.destructive =>
                          Icons.warning_amber_rounded,
                        GtexConfirmVariant.financial =>
                          Icons.account_balance_wallet_outlined,
                        GtexConfirmVariant.standard =>
                          Icons.verified_user_outlined,
                      },
                      color: primaryAccent,
                      size: 22,
                    ),
                    const SizedBox(width: GtexSpacing.xs),
                    Expanded(
                      child: Text(
                        widget.title,
                        style: GtexTypography.titleM(color: navy.textPrimary),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: GtexSpacing.xs),
                Text(
                  widget.summary,
                  style: GtexTypography.body(color: navy.textSecondary),
                ),
                if (widget.financialDetails != null) ...<Widget>[
                  const SizedBox(height: GtexSpacing.sm),
                  _FinancialBreakdownBox(
                    details: widget.financialDetails!,
                    idempotencyKey: _resolvedIdempotencyKey,
                  ),
                ],
                if ((widget.publicAnnouncementNotice ?? '')
                    .trim()
                    .isNotEmpty) ...<Widget>[
                  const SizedBox(height: GtexSpacing.sm),
                  Container(
                    padding: const EdgeInsets.all(GtexSpacing.sm),
                    decoration: BoxDecoration(
                      color: navy.bgInset,
                      borderRadius: BorderRadius.circular(GtexRadius.chip),
                      border: Border.all(color: navy.lineSubtle),
                    ),
                    child: Row(
                      children: <Widget>[
                        Icon(
                          Icons.campaign_outlined,
                          size: 18,
                          color: navy.info,
                        ),
                        const SizedBox(width: GtexSpacing.xs),
                        Expanded(
                          child: Text(
                            widget.publicAnnouncementNotice!.trim(),
                            style: GtexTypography.bodyS(
                              color: navy.textSecondary,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
                if (widget.requireReason) ...<Widget>[
                  const SizedBox(height: GtexSpacing.sm),
                  TextField(
                    key: const Key('gtex-confirm-reason-input'),
                    controller: _reasonController,
                    style: GtexTypography.body(color: navy.textPrimary),
                    decoration: InputDecoration(
                      hintText: widget.reasonHint,
                      hintStyle: GtexTypography.bodyS(color: navy.textTertiary),
                      filled: true,
                      fillColor: navy.bgInset,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(GtexRadius.chip),
                        borderSide: BorderSide(color: navy.lineSubtle),
                      ),
                    ),
                  ),
                ],
                if (_state == GtexConfirmSubmissionState.error &&
                    _errorMessage != null) ...<Widget>[
                  const SizedBox(height: GtexSpacing.sm),
                  Container(
                    key: const Key('gtex-confirm-error-banner'),
                    padding: const EdgeInsets.all(GtexSpacing.sm),
                    decoration: BoxDecoration(
                      color: navy.danger.withValues(alpha: 0.14),
                      borderRadius: BorderRadius.circular(GtexRadius.chip),
                      border: Border.all(color: navy.danger),
                    ),
                    child: Row(
                      children: <Widget>[
                        Icon(
                          Icons.error_outline_rounded,
                          color: navy.danger,
                          size: 18,
                        ),
                        const SizedBox(width: GtexSpacing.xs),
                        Expanded(
                          child: Text(
                            _errorMessage!,
                            style: GtexTypography.bodyS(color: navy.danger),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
                if (_state == GtexConfirmSubmissionState.success) ...<Widget>[
                  const SizedBox(height: GtexSpacing.sm),
                  Container(
                    key: const Key('gtex-confirm-success-banner'),
                    padding: const EdgeInsets.all(GtexSpacing.sm),
                    decoration: BoxDecoration(
                      color: navy.success.withValues(alpha: 0.14),
                      borderRadius: BorderRadius.circular(GtexRadius.chip),
                      border: Border.all(color: navy.success),
                    ),
                    child: Row(
                      children: <Widget>[
                        Icon(
                          Icons.check_circle_outline_rounded,
                          color: navy.success,
                          size: 18,
                        ),
                        const SizedBox(width: GtexSpacing.xs),
                        Expanded(
                          child: Text(
                            'Confirmed by server.',
                            style: GtexTypography.bodyS(color: navy.success),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: GtexSpacing.md),
                Row(
                  children: <Widget>[
                    Expanded(
                      child: SizedBox(
                        height: GtexSpacing.minTouchTarget,
                        child: OutlinedButton(
                          key: const Key('gtex-confirm-cancel-button'),
                          onPressed:
                              _state == GtexConfirmSubmissionState.submitting
                                  ? null
                                  : () {
                                    if (Navigator.of(context).canPop()) {
                                      Navigator.of(context).pop(false);
                                    }
                                  },
                          style: OutlinedButton.styleFrom(
                            foregroundColor: navy.textPrimary,
                            side: BorderSide(color: navy.lineStrong),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(
                                GtexRadius.chip,
                              ),
                            ),
                          ),
                          child: Text(widget.cancelLabel),
                        ),
                      ),
                    ),
                    const SizedBox(width: GtexSpacing.sm),
                    Expanded(
                      child: SizedBox(
                        height: GtexSpacing.minTouchTarget,
                        child: ElevatedButton(
                          key: const Key('gtex-confirm-submit-button'),
                          onPressed: _handleConfirm,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: primaryAccent,
                            foregroundColor: primaryForeground,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(
                                GtexRadius.chip,
                              ),
                            ),
                          ),
                          child:
                              _state == GtexConfirmSubmissionState.submitting
                                  ? Row(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: <Widget>[
                                      SizedBox(
                                        width: 16,
                                        height: 16,
                                        child: CircularProgressIndicator(
                                          strokeWidth: 2,
                                          color: primaryForeground,
                                        ),
                                      ),
                                      const SizedBox(width: GtexSpacing.xs),
                                      const Text('Submitting...'),
                                    ],
                                  )
                                  : Text(widget.confirmLabel),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _FinancialBreakdownBox extends StatelessWidget {
  const _FinancialBreakdownBox({
    required this.details,
    required this.idempotencyKey,
  });

  final GtexConfirmFinancialDetails details;
  final String idempotencyKey;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    return Container(
      key: const Key('gtex-confirm-financial-box'),
      padding: const EdgeInsets.all(GtexSpacing.sm),
      decoration: BoxDecoration(
        color: navy.bgInset,
        borderRadius: BorderRadius.circular(GtexRadius.card),
        border: Border.all(color: navy.lineSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          _FinancialRow(
            label: 'Amount (${details.currencyCode})',
            value: '${details.amountLabel} ${details.currencyCode}',
            highlight: true,
          ),
          if (details.feeLabel != null) ...<Widget>[
            const SizedBox(height: GtexSpacing.xxs),
            _FinancialRow(
              label: 'Fee',
              value: '${details.feeLabel} ${details.currencyCode}',
            ),
          ],
          if (details.balanceAfterLabel != null) ...<Widget>[
            const SizedBox(height: GtexSpacing.xxs),
            _FinancialRow(
              label: 'Balance after',
              value: '${details.balanceAfterLabel} ${details.currencyCode}',
            ),
          ],
          const SizedBox(height: GtexSpacing.xxs),
          Text(
            'Ref: $idempotencyKey',
            key: const Key('gtex-confirm-idempotency-ref'),
            style: GtexTypography.numericS(color: navy.textTertiary),
          ),
        ],
      ),
    );
  }
}

class _FinancialRow extends StatelessWidget {
  const _FinancialRow({
    required this.label,
    required this.value,
    this.highlight = false,
  });

  final String label;
  final String value;
  final bool highlight;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: <Widget>[
        Text(label, style: GtexTypography.bodyS(color: navy.textSecondary)),
        Text(
          value,
          style:
              highlight
                  ? GtexTypography.numericM(color: navy.gold300)
                  : GtexTypography.numericS(color: navy.textPrimary),
        ),
      ],
    );
  }
}
