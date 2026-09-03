import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../data/gtex_regen_repository.dart';
import '../models/gtex_regen_dossier.dart';
import '../models/gtex_regen_wire_models.dart';

/// The write half of OWN: list a regen for transfer, and price a contract
/// offer before committing to it.
///
/// These are the only two write verbs the regen lane exposes. Both are
/// authenticated, so the whole block is withheld from an anonymous session
/// rather than shown as controls that would fail on auth. Actually *placing*
/// an offer moves club money and is left to the club and wallet surfaces.
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
              'Listing a regen and pricing a contract offer both need a signed-in '
              'account.',
          severity: GtexBlockedSeverity.locked,
          icon: Icons.lock_outline_rounded,
        ),
      );
    }

    final RegenLifecycleState? lifecycle = widget.dossier.lifecycle;
    if (lifecycle == null) {
      return const SizedBox.shrink();
    }

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
            'Price a contract offer',
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: GtexColors.textSecondary,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: GtexSpacing.xs),
          TextField(
            controller: _clubIdController,
            style: const TextStyle(color: GtexColors.text),
            decoration: const InputDecoration(
              labelText: 'Offering club id',
              isDense: true,
            ),
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
                      : 'Floor: '
                          '${lifecycle.offerMarket!.minimumSalaryFancoinPerYear.toStringAsFixed(0)}',
            ),
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
              // The backend caps contract_years at 1..5; the control cannot
              // offer a value the API would reject.
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
                          : (double value) =>
                              setState(() => _contractYears = value.round()),
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
          GtexActionButton(
            label: 'Get quote',
            icon: Icons.calculate_outlined,
            accent: GtexColors.gold,
            onPressed: _busy ? null : _requestQuote,
          ),
          if (_quote != null) ...<Widget>[
            const SizedBox(height: GtexSpacing.md),
            _QuoteSummary(quote: _quote!),
          ],
        ],
      ),
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
      if (!mounted) {
        return;
      }
      widget.onLifecycleChanged?.call(updated);
      setState(() => _busy = false);
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _error = 'Could not update the transfer listing: $error';
      });
    }
  }

  Future<void> _requestQuote() async {
    final String clubId = _clubIdController.text.trim();
    final double? salary = double.tryParse(_salaryController.text.trim());
    if (clubId.isEmpty || salary == null || salary < 0) {
      setState(
        () =>
            _error = 'Enter an offering club id and a salary before quoting.',
      );
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final RegenOfferQuote quote = await widget.repository.quoteContractOffer(
        widget.dossier.playerId,
        GtexRegenOfferDraft(
          offeringClubId: clubId,
          offeredSalaryFancoinPerYear: salary,
          contractYears: _contractYears,
        ),
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _quote = quote;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _error = 'Could not price this offer: $error';
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
        // The shortfall is the whole point of quoting first, so it is stated
        // plainly either way rather than only on failure.
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
                    ? 'Convertible from '
                        '${quote.gtexRequiredForConversion.toStringAsFixed(0)} GTEX'
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
