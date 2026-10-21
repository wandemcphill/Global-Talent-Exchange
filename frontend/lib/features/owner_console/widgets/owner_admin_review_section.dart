import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../data/owner_console_api.dart';

String _amount(double v) =>
    v.toStringAsFixed(v % 1 == 0 || v.abs() >= 100 ? 0 : 2);

/// Returns the (possibly empty) note when confirmed, or null when cancelled.
Future<String?> confirmOwnerAction(
  BuildContext context, {
  required String title,
  required String message,
  String confirmLabel = 'Confirm',
  bool withNote = false,
}) {
  return showDialog<String>(
    context: context,
    builder:
        (_) => _ConfirmDialog(
          title: title,
          message: message,
          confirmLabel: confirmLabel,
          withNote: withNote,
        ),
  );
}

class _ConfirmDialog extends StatefulWidget {
  const _ConfirmDialog({
    required this.title,
    required this.message,
    required this.confirmLabel,
    required this.withNote,
  });

  final String title;
  final String message;
  final String confirmLabel;
  final bool withNote;

  @override
  State<_ConfirmDialog> createState() => _ConfirmDialogState();
}

class _ConfirmDialogState extends State<_ConfirmDialog> {
  final TextEditingController _note = TextEditingController();

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      key: const Key('owner-confirm-dialog'),
      backgroundColor: GtexColors.panelStrong,
      title: Text(
        widget.title,
        style: const TextStyle(
          color: GtexColors.text,
          fontWeight: FontWeight.w900,
        ),
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            widget.message,
            key: const Key('owner-confirm-message'),
            style: const TextStyle(color: GtexColors.textSecondary),
          ),
          if (widget.withNote)
            TextField(
              key: const Key('owner-confirm-note'),
              controller: _note,
              style: const TextStyle(color: GtexColors.text),
              decoration: const InputDecoration(labelText: 'Note (optional)'),
            ),
        ],
      ),
      actions: <Widget>[
        TextButton(
          key: const Key('owner-confirm-cancel'),
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        GtexActionButton(
          key: const Key('owner-confirm-ok'),
          label: widget.confirmLabel,
          compact: true,
          onPressed: () => Navigator.of(context).pop(_note.text.trim()),
        ),
      ],
    );
  }
}

class _ReviewRow extends StatelessWidget {
  const _ReviewRow({
    super.key,
    required this.title,
    required this.subtitle,
    required this.accent,
    required this.actions,
    this.statusChip,
  });

  final String title;
  final String subtitle;
  final Color accent;
  final List<Widget> actions;
  final Widget? statusChip;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: GtexSpacing.xs),
      padding: const EdgeInsets.all(GtexSpacing.sm),
      decoration: BoxDecoration(
        color: GtexColors.panelStrong,
        borderRadius: BorderRadius.circular(8),
        border: Border(left: BorderSide(color: accent, width: 3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              if (statusChip != null) ...<Widget>[
                const SizedBox(width: GtexSpacing.xs),
                statusChip!,
              ],
            ],
          ),
          Text(
            subtitle,
            style: const TextStyle(
              color: GtexColors.textSecondary,
              fontSize: 12,
            ),
          ),
          const SizedBox(height: GtexSpacing.xs),
          Wrap(
            spacing: GtexSpacing.xs,
            runSpacing: GtexSpacing.xs,
            children: actions,
          ),
        ],
      ),
    );
  }
}

class _QuietLine extends StatelessWidget {
  const _QuietLine(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) => Row(
    children: <Widget>[
      const Icon(Icons.check_circle_outline, color: GtexColors.pitch, size: 18),
      const SizedBox(width: 6),
      Text(text, style: const TextStyle(color: GtexColors.textSecondary)),
    ],
  );
}

/// Admin-only Trust & Payouts desk over `/owner/admin/*`.
class AdminReviewSection extends StatefulWidget {
  const AdminReviewSection({
    super.key,
    required this.reader,
    this.canReviewOwnerQueue = true,
  });

  final OwnerConsoleReader reader;
  final bool canReviewOwnerQueue;

  @override
  State<AdminReviewSection> createState() => _AdminReviewSectionState();
}

class _AdminReviewSectionState extends State<AdminReviewSection> {
  Future<OwnerReviewQueue>? _future;
  final Set<String> _done = <String>{};
  String? _busyId;
  String? _message;

  @override
  void initState() {
    super.initState();
    if (widget.canReviewOwnerQueue) {
      _future = widget.reader.fetchReviewQueue();
    }
  }

  void _reload() => setState(() {
    _done.clear();
    _future = widget.reader.fetchReviewQueue();
  });

  Future<void> _run(
    String id,
    Future<void> Function() call,
    String message,
  ) async {
    setState(() {
      _busyId = id;
      _message = null;
    });
    try {
      await call();
      _done.add(id);
      _message = message;
    } catch (error) {
      _message = '$error';
    } finally {
      if (mounted) setState(() => _busyId = null);
    }
  }

  Future<void> _reviewWithdrawal(
    OwnerWithdrawalReview w,
    String decision,
    String label,
  ) async {
    final String? note = await confirmOwnerAction(
      context,
      title: '$label withdrawal?',
      message:
          '${_amount(w.amountCoin)} GTX (₦${_amount(w.amountNgn)}) to ${w.accountName}, ${w.bankName} ••${w.accountLast4}',
      confirmLabel: label,
      withNote: true,
    );
    if (note == null) return;
    await _run(
      w.id,
      () => widget.reader.reviewWithdrawal(w.id, decision, note: note),
      'Withdrawal ${decision == 'approve' ? 'approved' : decision == 'hold' ? 'held' : 'rejected'}',
    );
  }

  Future<void> _release(OwnerHeldPayout p) async {
    final String? ok = await confirmOwnerAction(
      context,
      title: 'Release payout?',
      message:
          '${_amount(p.netAmount)} ${p.currency.toUpperCase()} · ${p.memo ?? p.eventType}',
      confirmLabel: 'Release',
    );
    if (ok == null) return;
    await _run(p.id, () => widget.reader.releasePayout(p.id), 'Payout released');
  }

  Widget _button(
    String key,
    String label,
    VoidCallback onPressed, {
    bool primary = false,
    Color accent = GtexColors.pitch,
  }) {
    return GtexActionButton(
      key: Key(key),
      label: label,
      compact: true,
      secondary: !primary,
      accent: accent,
      onPressed: _busyId == null ? onPressed : null,
    );
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.canReviewOwnerQueue) {
      return ListView(
        padding: const EdgeInsets.all(GtexSpacing.md),
        children: const <Widget>[
          GtexBlockedState(
            key: Key('owner-admin-capability-blocked'),
            title: 'Owner review queue restricted',
            reason:
                'Your admin session does not have the manage_treasury_withdrawals capability required to act on Owner Console payouts and risk flags.',
            severity: GtexBlockedSeverity.warning,
            icon: Icons.lock_outline_rounded,
          ),
        ],
      );
    }

    return FutureBuilder<OwnerReviewQueue>(
      future: _future,
      builder: (BuildContext context, AsyncSnapshot<OwnerReviewQueue> snap) {
        if (snap.connectionState != ConnectionState.done) {
          return ListView(
            padding: const EdgeInsets.all(GtexSpacing.md),
            children: const <Widget>[GtexSkeleton.box(height: 160)],
          );
        }
        if (snap.hasError || !snap.hasData) {
          return ListView(
            padding: const EdgeInsets.all(GtexSpacing.md),
            children: <Widget>[
              GtexBlockedState(
                key: const Key('owner-admin-unavailable'),
                title: 'Review queue unavailable',
                reason: '${snap.error ?? 'no response'}',
                severity: GtexBlockedSeverity.warning,
                icon: Icons.cloud_off_rounded,
                ctaLabel: 'Retry',
                ctaAction: _reload,
              ),
            ],
          );
        }
        final OwnerReviewQueue q = snap.data!;
        final List<OwnerWithdrawalReview> withdrawals =
            q.withdrawals
                .where((OwnerWithdrawalReview w) => !_done.contains(w.id))
                .toList();
        final List<OwnerRiskFlag> flags =
            q.flags.where((OwnerRiskFlag f) => !_done.contains(f.id)).toList();
        final List<OwnerHeldPayout> held =
            q.heldPayouts
                .where((OwnerHeldPayout p) => !_done.contains(p.id))
                .toList();
        return ListView(
          key: const Key('owner-admin-review'),
          padding: const EdgeInsets.all(GtexSpacing.md),
          children: <Widget>[
            Row(
              children: <Widget>[
                const Expanded(
                  child: Text(
                    'Trust & Payouts desk',
                    style: TextStyle(
                      color: GtexColors.text,
                      fontSize: 18,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
                const GtexStatusChip(
                  key: Key('owner-admin-ledger-badge'),
                  label: 'Owner Console Ledger (GTX)',
                  color: GtexColors.gold,
                  compact: true,
                ),
                IconButton(
                  key: const Key('owner-admin-refresh'),
                  tooltip: 'Refresh',
                  onPressed: _reload,
                  icon: const Icon(
                    Icons.refresh_rounded,
                    color: GtexColors.textSecondary,
                  ),
                ),
              ],
            ),
            if (_message != null)
              Padding(
                padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
                child: Text(
                  _message!,
                  key: const Key('owner-admin-message'),
                  style: const TextStyle(
                    color: GtexColors.gold,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            GtexPanel(
              key: const Key('owner-admin-withdrawals'),
              title: 'Withdrawal queue',
              subtitle: '${withdrawals.length} waiting · manual bank transfer',
              accent: GtexColors.gold,
              child: Column(
                children: <Widget>[
                  if (withdrawals.isEmpty)
                    const _QuietLine(
                      'Queue clear',
                      key: Key('owner-admin-withdrawals-clear'),
                    ),
                  for (final OwnerWithdrawalReview w in withdrawals)
                    _ReviewRow(
                      key: Key('owner-admin-withdrawal-${w.id}'),
                      title:
                          '${_amount(w.amountCoin)} GTX · ₦${_amount(w.amountNgn)}',
                      subtitle: <String?>[
                        '${w.accountName} · ${w.bankName} ••${w.accountLast4}',
                        w.status.replaceAll('_', ' '),
                        if (w.risk != null) 'risk ${w.risk}',
                        w.createdAt?.split('T').first,
                      ].whereType<String>().join(' · '),
                      accent:
                          w.status == 'held' ? GtexColors.red : GtexColors.gold,
                      statusChip: GtexStatusChip.fromBackendStatus(
                        w.status,
                        context: GtexStatusContext.financial,
                        compact: true,
                      ),
                      actions: <Widget>[
                        _button(
                          'owner-admin-withdrawal-${w.id}-approve',
                          _busyId == w.id ? 'Working...' : 'Approve',
                          () => _reviewWithdrawal(w, 'approve', 'Approve'),
                          primary: true,
                        ),
                        _button(
                          'owner-admin-withdrawal-${w.id}-hold',
                          'Hold',
                          () => _reviewWithdrawal(w, 'hold', 'Hold'),
                          accent: GtexColors.gold,
                        ),
                        _button(
                          'owner-admin-withdrawal-${w.id}-reject',
                          'Reject',
                          () => _reviewWithdrawal(w, 'reject', 'Reject'),
                          accent: GtexColors.red,
                        ),
                      ],
                    ),
                ],
              ),
            ),
            const SizedBox(height: GtexSpacing.md),
            GtexPanel(
              key: const Key('owner-admin-flags'),
              title: 'Risk flags',
              subtitle: '${flags.length} open',
              accent: GtexColors.red,
              child: Column(
                children: <Widget>[
                  if (flags.isEmpty)
                    const _QuietLine(
                      'No open flags',
                      key: Key('owner-admin-flags-clear'),
                    ),
                  for (final OwnerRiskFlag f in flags)
                    _ReviewRow(
                      key: Key('owner-admin-flag-${f.id}'),
                      title:
                          '${f.flagType.replaceAll('_', ' ')} · ${f.severity}',
                      subtitle: <String?>[
                        f.detail,
                        'score ${f.scoreImpact}',
                        if (f.clubId != null) 'club ${f.clubId}',
                      ].whereType<String>().join(' · '),
                      accent:
                          f.severity == 'high'
                              ? GtexColors.red
                              : GtexColors.gold,
                      actions: <Widget>[
                        _button(
                          'owner-admin-flag-${f.id}-clear',
                          _busyId == f.id ? 'Working...' : 'Clear',
                          () => _run(
                            f.id,
                            () => widget.reader.decideFlag(f.id, 'clear'),
                            'Flag cleared',
                          ),
                          primary: true,
                        ),
                        _button(
                          'owner-admin-flag-${f.id}-action',
                          'Action',
                          () => _run(
                            f.id,
                            () => widget.reader.decideFlag(f.id, 'action'),
                            'Flag actioned',
                          ),
                          accent: GtexColors.red,
                        ),
                      ],
                    ),
                ],
              ),
            ),
            const SizedBox(height: GtexSpacing.md),
            GtexPanel(
              key: const Key('owner-admin-held'),
              title: 'Held payouts',
              subtitle: '${held.length} held',
              accent: GtexColors.cyan,
              child: Column(
                children: <Widget>[
                  if (held.isEmpty)
                    const _QuietLine(
                      'Nothing held',
                      key: Key('owner-admin-held-clear'),
                    ),
                  for (final OwnerHeldPayout p in held)
                    _ReviewRow(
                      key: Key('owner-admin-payout-${p.id}'),
                      title:
                          '${_amount(p.netAmount)} ${p.currency.toUpperCase()} · ${p.eventType.replaceAll('_', ' ')}',
                      subtitle: <String?>[
                        p.memo,
                        if (p.clubId != null) 'club ${p.clubId}',
                      ].whereType<String>().join(' · '),
                      accent: GtexColors.cyan,
                      statusChip: GtexStatusChip.fromBackendStatus(
                        'held',
                        context: GtexStatusContext.financial,
                        compact: true,
                      ),
                      actions: <Widget>[
                        _button(
                          'owner-admin-payout-${p.id}-release',
                          _busyId == p.id ? 'Working...' : 'Release',
                          () => _release(p),
                          primary: true,
                          accent: GtexColors.cyan,
                        ),
                      ],
                    ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}
