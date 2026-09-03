import 'package:flutter/material.dart';

import '../../../data/gte_models.dart';
import '../../../domain/value/gtex_value_models.dart';
import '../../../ui_gtex/ui_gtex.dart';

const Color _panel = GtexColors.surfaceRaised;
const Color _border = GtexColors.surfaceBorder;
const Color _textSecondary = GtexColors.textSecondary;
const Color _textMuted = GtexColors.textTertiary;
const Color _green = GtexColors.accentPrimary;
const Color _red = GtexColors.accentRed;

/// The last link of the chain: what this player's football means to *you*.
///
/// Without this the page can tell a reader that a footballer played well, that
/// his form is rising and that his value moved, and still leave the only
/// question that matters unanswered. This card answers it, and only with facts
/// the backend actually returned: it never estimates a position.
class OwnershipConsequenceCard extends StatelessWidget {
  const OwnershipConsequenceCard({
    super.key,
    required this.holding,
    this.form,
  });

  /// The viewer's position in this player, or null when they hold none, are not
  /// signed in, or the portfolio could not be read. All three render as "no
  /// position" rather than as a fabricated zero holding.
  final GtePortfolioHolding? holding;

  final GtexPlayerForm? form;

  @override
  Widget build(BuildContext context) {
    final GtePortfolioHolding? position = holding;

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: _panel,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _border),
      ),
      child:
          position == null || position.quantity <= 0
              ? _buildNoPosition(context)
              : _buildPosition(context, position),
    );
  }

  Widget _buildNoPosition(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          'You hold no shares in this player',
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: _textSecondary,
            fontWeight: FontWeight.w800,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          'His matchday form moves his valuation, but with no position it does '
          'not move your portfolio.',
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: _textMuted, height: 1.4),
        ),
      ],
    );
  }

  Widget _buildPosition(BuildContext context, GtePortfolioHolding position) {
    final bool up = position.unrealizedPl > 0;
    final bool flat = position.unrealizedPl == 0;
    final Color plColor = flat ? _textSecondary : (up ? _green : _red);

    final List<GtexTermRow> rows = <GtexTermRow>[
      GtexTermRow(
        'Shares held',
        _trimmed(position.quantity),
        valueColor: GtexColors.accentBlue,
      ),
      GtexTermRow('Average cost', '${_trimmed(position.averageCost)} cr'),
      GtexTermRow('Current price', '${_trimmed(position.currentPrice)} cr'),
      GtexTermRow('Position value', '${_trimmed(position.marketValue)} cr'),
      GtexTermRow(
        'Unrealised P/L',
        '${up ? '+' : ''}${_trimmed(position.unrealizedPl)} cr '
            '(${up ? '+' : ''}${position.unrealizedPlPercent.toStringAsFixed(2)}%)',
        valueColor: plColor,
      ),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        GtexTermsList(rows: rows),
        if (_formNote(context) case final Widget note) ...<Widget>[
          const SizedBox(height: 10),
          note,
        ],
      ],
    );
  }

  /// Ties the position back to the football, but only when form is genuinely
  /// driving the valuation. When it is not, this stays silent rather than
  /// implying the connection.
  Widget? _formNote(BuildContext context) {
    final GtexPlayerForm? current = form;
    if (current == null || !current.movesValuation) {
      return null;
    }
    final double pct = current.signal!.adjustmentPct * 100;
    final bool positive = pct > 0;
    final Color color = positive ? _green : _red;

    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(9),
        border: Border.all(color: color.withValues(alpha: 0.28)),
      ),
      // The position shown above is priced from the player valuation, which is
      // the field matchday form actually moves — so this claim is true of the
      // numbers on this card. It is scoped to the valuation on purpose: form
      // does not move the tradable share price, and a holder must not read this
      // as their shares having repriced.
      child: Text(
        'His current form is ${positive ? 'adding' : 'taking'} '
        '${positive ? '+' : ''}${pct.toStringAsFixed(2)}% '
        '${positive ? 'to' : 'off'} the valuation this position is priced from. '
        'The tradable share price is unchanged.',
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
          color: color,
          height: 1.4,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }

  /// Credits are carried as doubles but read as money, so trailing noise is
  /// trimmed rather than shown.
  static String _trimmed(double value) {
    if (value == value.roundToDouble() && value.abs() < 1000000) {
      return value.toStringAsFixed(0);
    }
    return value.toStringAsFixed(2);
  }
}
