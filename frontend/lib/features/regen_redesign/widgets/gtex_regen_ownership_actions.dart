import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../data/gtex_regen_repository.dart';
import '../data/gtex_regen_submission.dart';
import '../models/gtex_regen_dossier.dart';
import '../models/gtex_regen_wire_models.dart';

/// The write half of OWN: list a regen, price an offer, then submit that same
/// canonical offer through the authenticated lifecycle API.
class GtexRegenOwnershipActions extends StatefulWidget {
  const GtexRegenOwnershipActions({
    super.key,
    required this.repository,
    required this.dossier,
    this.onLifecycleChanged,
  });

  final GtexRegenRepository repository;
  final GtexRegenDossier dossier;
  final ValueChanged<RegenLifecycleState?>? onLifecycleChanged;

  @override
  State<GtexRegenOwnershipActions> createState() =>
      _GtexRegenOwnershipActionsState();
}

class _GtexRegenOwnershipActionsState extends State<GtexRegenOwnershipActions> {
  final TextEditingController _clubIdController = TextEditingController();
  final TextEditingController _salaryController = TextEditingController();
  int _contractYears = 3;
  bool _busy = false;
  String? _error;
  RegenOfferQuote? _quote;

  @override
  void dispose() {
    _clubIdController.dispose();
    _salaryController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.repository.canActOnOwnership) {
      return const GtexPanel(
        title: 'Ownership actions',
        accent: GtexColors.mint,
        child: GtexBlockedState(
          compact: true,
          title: 'Sign in to act',
          reason:
              'Listing a regen and submitting a contract offer both need a signed-in account.',
          severity: GtexBlockedSeverity.locked,
          icon: Icons.lock_outline_rounded,
        ),
      );
    }

    final RegenLifecycleState? lifecycle = widget.dossier.lifecycle;
    if (lifecycle == null) {
      return const SizedBox.shrink();
    }

    final bool offerReady = _quote != null;

    return GtexPanel(
      title: 'Ownership actions',
      accent: GtexColors.mint,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          if (_error != null) ...<Widget>[
            GtexErrorBanner(message: _error!),
            const SizedBox(height: GtexSpacing.sm),
          ],
          GtexActionButton(
            label:
                lifecycle.transferListed
                    ? 'Remove from transfer list'
                    : 'List for transfer',
            icon:
                lifecycle.transferListed
                    ? Icons.remove_circle_outline_rounded
                    : Icons.sell_outlined,
            accent: GtexColors.cyan,
            secondary: lifecycle.transferListed,
            onPressed: _busy ? null : () => _toggleListing(!lifecycle.transferListed),
          ),
          const SizedBox(height: GtexSpacing.md),
          Text(
            'Offer a contract',
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: GtexColors.textSecondary,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: GtexSpacing.xs),
          Text(
            'Quote first, then submit the exact same FanCoin salary and term through the canonical transfer lifecycle.',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: GtexColors.textMuted,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: GtexSpacing.sm),
          TextField(
            controller: _clubIdController,
            style: const TextStyle(color: GtexColors.text),
            decoration: const InputDecoration(
              labelText: 'Offering club id',
              isDense: true,
            ),
            onChanged: (_) {
              if (_quote != null) {
                setState(() => _quote = null);
              }
            },
          ),
          const SizedBox(height: GtexSpacing.sm),
          TextField(
            controller: _salaryController,
            keyboardType: TextInputType.number,
            style: const TextStyle(color: GtexColors.text),
            decoration: InputDecoration(
              labelText:
                  'Salary per year (${lifecycle.offerMarket?.salaryCurrencyCode ?? lifecycle.contractCurrency})',
              isDense: true,
              helperText:
                  lifecycle.offerMarket == null
                      ? null
                      : 'Floor: ${lifecycle.offerMarket!.minimumSalaryFancoinPerYear.toStringAsFixed(0)}',
            ),
            onChanged: (_) {
              if (_quote != null) {
                setState(() => _quote = null);
              }
            },
          ),
          const SizedBox(height: GtexSpacing.sm),
          Row(
            children: <Widget>[
              Text(
                'Years',
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: GtexColors.textSecondary,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(width: GtexSpacing.sm),
              Expanded(
                child: Slider(
                  value: _contractYears.toDouble(),
                  min: 1,
                  max: 5,
                  divisions: 4,
                  label: '$_contractYears',
                  activeColor: GtexColors.mint,
                  onChanged:
                      _busy
                          ? null
                          : (double value) => setState(() {
                            _contractYears = value.round();
                            _quote = null;
                          }),
                ),
              ),
              Text(
                '$_contractYears',
                style: const TextStyle(
                  color: GtexColors.text,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
          const SizedBox(height: GtexSpacing.sm),
          Row(
            children: <Widget>[
              Expanded(
                child: GtexActionButton(
                  label: 'Get quote',
                  icon: Icons.calculate_outlined,
                  accent: GtexColors.gold,
                  onPressed: _busy ? null : _requestQuote,
                ),
              ),
              if (offerReady) ...<Widget>[
                const SizedBox(width: GtexSpacing.sm),
                Expanded(
                  child: GtexActionButton(
                    label: 'Submit offer',
                    icon: Icons.send_outlined,
                    accent: GtexColors.mint,
                    onPressed: _busy ? null : _submitOffer,
                  ),
                ),
              ],
            ],
          ),
          if (_quote != null) ...<Widget>[
            const SizedBox(height: GtexSpacing.md),
            _QuoteSummary(quote: _quote!),
          ],
        ],
      ),
    );
  }

  GtexRegenOfferDraft _draft() {
    final String clubId = _clubIdController.text.trim();
    final double? salary = double.tryParse(_salaryController.text.trim());
    if (clubId.isEmpty || salary == null || salary < 0) {
      throw const FormatException('Enter an offering club id and a valid salary.');
    }
    return GtexRegenOfferDraft(
      offeringClubId: clubId,
      offeredSalaryFancoinPerYear: salary,
      contractYears: _contractYears,
    );
  }

  Future<void> _toggleListing(bool listed) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final RegenLifecycleState? updated = await widget.repository
          .setTransferListing(widget.dossier.playerId, listed: listed);
      if (!mounted) return;
      widget.onLifecycleChanged?.call(updated);
      setState(() => _busy = false);
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _error = 'Could not update the transfer listing: $error';
      });
    }
  }

  Future<void> _requestQuote() async {
    late final GtexRegenOfferDraft draft;
    try {
      draft = _draft();
    } on FormatException catch (error) {
      setState(() => _error = error.message);
      return;
    }

    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final RegenOfferQuote quote = await widget.repository.quoteContractOffer(
        widget.dossier.playerId,
        draft,
      );
      if (!mounted) return;
      setState(() {
        _busy = false;
        _quote = quote;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _error = 'Could not price this offer: $error';
      });
    }
  }

  Future<void> _submitOffer() async {
    late final GtexRegenOfferDraft draft;
    try {
      draft = _draft();
    } on FormatException catch (error) {
      setState(() => _error = error.message);
      return;
    }

    if (_quote == null) {
      setState(() => _error = 'Get a fresh quote before submitting the offer.');
      return;
    }

    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final RegenLifecycleState? updated =
          await widget.repository.submitContractOffer(
        widget.dossier.playerId,
        draft,
      );
      if (!mounted) return;
      widget.onLifecycleChanged?.call(updated);
      setState(() {
        _busy = false;
        _quote = null;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _error = 'Could not submit this offer: $error';
      });
    }
  }
}

class _QuoteSummary extends StatelessWidget {
  const _QuoteSummary({required this.quote});

  final RegenOfferQuote quote;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Expanded(
              child: GtexMetricTile(
                label: 'Offer costs',
                value: quote.requiredFancoin.toStringAsFixed(0),
                accent: GtexColors.gold,
              ),
            ),
            const SizedBox(width: GtexSpacing.sm),
            Expanded(
              child: GtexMetricTile(
                label: 'Wallet holds',
                value: quote.currentFancoinBalance.toStringAsFixed(0),
                accent: GtexColors.cyan,
              ),
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.sm),
        GtexStatusChip(
          label:
              quote.isAffordableOutright
                  ? 'Covered by the wallet'
                  : 'Short by ${quote.shortfallFancoin.toStringAsFixed(0)}',
          color:
              quote.isAffordableOutright ? GtexColors.mint : GtexColors.danger,
        ),
        if (!quote.isAffordableOutright) ...<Widget>[
          const SizedBox(height: GtexSpacing.xs),
          GtexStatusChip(
            label:
                quote.canCoverShortfall
                    ? 'Convertible from ${quote.gtexRequiredForConversion.toStringAsFixed(0)} GTEX'
                    : 'Not convertible from the current GTEX balance',
            color: quote.canCoverShortfall ? GtexColors.gold : GtexColors.danger,
            compact: true,
          ),
        ],
        if (quote.premiumNote.isNotEmpty) ...<Widget>[
          const SizedBox(height: GtexSpacing.xs),
          Text(
            quote.premiumNote,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: GtexColors.textMuted,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ],
    );
  }
}
