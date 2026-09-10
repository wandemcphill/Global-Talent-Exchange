import 'package:flutter/material.dart';

import '../../../domain/value/gtex_value_models.dart';
import '../../../ui_gtex/ui_gtex.dart';
import '../../../widgets/gte_formatters.dart';

const Color _panel = GtexColors.surfaceRaised;
const Color _border = GtexColors.surfaceBorder;
const Color _textSecondary = GtexColors.textSecondary;
const Color _textMuted = GtexColors.textTertiary;
const Color _green = GtexColors.accentPrimary;
const Color _amber = GtexColors.accentAmber;
const Color _red = GtexColors.accentRed;
const Color _blue = GtexColors.accentBlue;

/// Recent GTEX competition form, and the bounded effect it has on valuation.
///
/// This card is the visible half of the chain
/// `match -> performance -> form -> valuation -> market -> ownership`. It is
/// written to be honest in three specific ways, because the alternative is a UI
/// that implies an economy the backend does not actually run:
///
///   * A player with no eligible competition football says so. It does not draw
///     flat form, which would read as "he played and was average".
///   * Form that is not yet moving value says that too, and says what is missing.
///   * When form *is* moving value, the figure shown is the real, bounded
///     adjustment the backend applied, not a restatement of the rating.
class MatchdayFormCard extends StatelessWidget {
  const MatchdayFormCard({super.key, required this.form, this.freshness});

  final GtexPlayerForm form;

  /// Whether the published valuation has caught up with the football listed
  /// here. Optional so the card still renders where a caller has no valuation
  /// to compare against; when absent the card simply makes no timing claim.
  final GtexValuationFreshnessReport? freshness;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: _panel,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _border),
      ),
      child: form.hasSample ? _buildForm(context) : const _MatchdayFormEmpty(),
    );
  }

  Widget _buildForm(BuildContext context) {
    final double? average = form.averageRating;
    final Color trendColor =
        form.isRising
            ? _green
            : form.isFalling
            ? _red
            : _textSecondary;

    final List<GtexTermRow> rows = <GtexTermRow>[
      GtexTermRow(
        'Form rating',
        average == null ? '—' : average.toStringAsFixed(2),
        valueColor: average == null ? null : ratingColor(average),
      ),
      GtexTermRow(
        'Trajectory',
        _trendLabel(form.trend, form.trendDelta),
        valueColor: trendColor,
      ),
      GtexTermRow(
        'Matches counted',
        '${form.matchesCounted} across ${form.competitionsCounted} '
            '${form.competitionsCounted == 1 ? 'competition' : 'competitions'}',
      ),
      GtexTermRow('Minutes', '${form.totalMinutes}'),
      if (form.totalGoals > 0 || form.totalAssists > 0)
        GtexTermRow(
          'Goals / assists',
          '${form.totalGoals} / ${form.totalAssists}',
          valueColor: _green,
        ),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        GtexTermsList(rows: rows),
        if (form.performances.isNotEmpty) ...<Widget>[
          const SizedBox(height: 12),
          _RecentRatingStrip(performances: form.performances),
        ],
        const SizedBox(height: 12),
        _ValuationConsequence(form: form, freshness: freshness),
        if (form.excludedByCompetitionCap > 0) ...<Widget>[
          const SizedBox(height: 8),
          _FormFootnote(
            '${form.excludedByCompetitionCap} further '
            '${form.excludedByCompetitionCap == 1 ? 'match sits' : 'matches sit'} '
            'outside this window: no single competition may fill it.',
          ),
        ],
      ],
    );
  }

  static String _trendLabel(String trend, double delta) {
    final String sign = delta > 0 ? '+' : '';
    switch (trend) {
      case 'rising':
        return 'Rising ($sign${delta.toStringAsFixed(2)})';
      case 'falling':
        return 'Falling (${delta.toStringAsFixed(2)})';
      default:
        return 'Steady';
    }
  }

  /// Shared so the summary rating and the per-match pips agree on what a given
  /// rating looks like.
  static Color ratingColor(double rating) {
    if (rating >= 7.5) {
      return _green;
    }
    if (rating >= 6.5) {
      return _blue;
    }
    if (rating >= 5.5) {
      return _amber;
    }
    return _red;
  }
}

/// The state for a player who has not played eligible GTEX competition football.
///
/// Deliberately explicit. Drawing empty form here would read as "he played and
/// did nothing", which is a different and false claim.
class _MatchdayFormEmpty extends StatelessWidget {
  const _MatchdayFormEmpty();

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          'No GTEX competition football yet',
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: _textSecondary,
            fontWeight: FontWeight.w800,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          'Form is built from completed competition matches. Friendlies and '
          'private simulations are not counted, and do not affect valuation.',
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: _textMuted, height: 1.4),
        ),
      ],
    );
  }
}

/// The one place in the app that states what form is doing to a valuation.
///
/// It must never overstate. When the backend has not applied a signal this says
/// so plainly and says what is missing, rather than hinting at a link.
class _ValuationConsequence extends StatelessWidget {
  const _ValuationConsequence({required this.form, this.freshness});

  final GtexPlayerForm form;
  final GtexValuationFreshnessReport? freshness;

  @override
  Widget build(BuildContext context) {
    final GtexMatchdaySignal? signal = form.signal;

    final String headline;
    final String detail;
    final Color color;

    if (signal == null) {
      headline = 'Not affecting valuation';
      detail =
          'This form is recorded but is not currently feeding this player’s '
          'value.';
      color = _textMuted;
    } else if (!signal.applied) {
      final int remaining = signal.matchesRemaining;
      headline = 'Not affecting valuation yet';
      detail =
          remaining > 0
              ? '$remaining more eligible ${remaining == 1 ? 'match' : 'matches'} '
                  'needed before form counts. One strong match does not move a price.'
              : 'This sample is too thin to move a price.';
      color = _textMuted;
    } else if (!form.movesValuation) {
      headline = 'Valuation effect: none';
      detail =
          'Form is being counted, but sits at the baseline, so it is neither '
          'raising nor lowering this valuation.';
      color = _textSecondary;
    } else {
      final double pct = signal.adjustmentPct * 100;
      final bool positive = pct > 0;
      headline =
          '${positive ? 'Raising' : 'Lowering'} valuation by '
          '${positive ? '+' : ''}${pct.toStringAsFixed(2)}%';
      detail =
          'Applied from ${signal.matchesCounted} counted '
          '${signal.matchesCounted == 1 ? 'match' : 'matches'}. Matchday form is '
          'capped at ±${(signal.effectiveMaxAdjustmentPct * 100).toStringAsFixed(1)}% '
          'so football moves a valuation gradually, never all at once.';
      color = positive ? _green : _red;
    }

    // Matchday form moves the player's *valuation*. It deliberately does not
    // touch the tradable share price, which changes only on trades. Saying so
    // is not a caveat for its own sake: a share-market holder who read
    // "raising valuation" and assumed their tradable shares had moved would
    // have been misled by omission.
    final bool statesAnEffect = signal != null && signal.applied;
    final GtexValuationFreshnessReport? report = freshness;
    final String? timing = _timingNote(report);

    return Container(
      padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.30)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            headline,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: color,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            detail,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: _textMuted, height: 1.4),
          ),
          if (statesAnEffect) ...<Widget>[
            const SizedBox(height: 6),
            Text(
              'This changes the player valuation. It does not change the '
              'tradable share price, which moves only on trades.',
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: _textMuted,
                height: 1.35,
                fontStyle: FontStyle.italic,
              ),
            ),
          ],
          if (timing != null) ...<Widget>[
            const SizedBox(height: 6),
            Text(
              timing,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: report != null && report.isPending ? _amber : _textMuted,
                height: 1.35,
              ),
            ),
          ],
        ],
      ),
    );
  }

  /// What the page may truthfully say about *when* this reaches a valuation.
  ///
  /// Valuations are recalculated on a schedule rather than per match, so a
  /// signal can be live here while the published number still predates the
  /// matches that produced it. Returns null rather than guessing when there is
  /// no recalculation on record to compare against.
  static String? _timingNote(GtexValuationFreshnessReport? report) {
    if (report == null) {
      return null;
    }
    switch (report.state) {
      case GtexValuationFreshness.pending:
        final int count = report.pendingMatchCount;
        return '$count eligible ${count == 1 ? 'match' : 'matches'} '
            '${count == 1 ? 'has' : 'have'} been played since this valuation was '
            'last recalculated on ${gteFormatDateTime(report.lastSnapshotAt)}. '
            'The form above already counts '
            '${count == 1 ? 'it' : 'them'}; the published valuation does not, '
            'until the next recalculation.';
      case GtexValuationFreshness.updated:
        return 'Valuation last recalculated '
            '${gteFormatDateTime(report.lastSnapshotAt)}, which already accounts '
            'for every eligible match listed here.';
      case GtexValuationFreshness.unknown:
        return 'No valuation recalculation is on record for this player, so '
            'this form has not reached a published valuation yet.';
    }
  }
}

/// The last few match ratings, newest first, as a compact readable strip.
///
/// Performances that do not count toward valuation are dimmed rather than
/// hidden: a holder is entitled to see the cameo appearance, and hiding it would
/// be more confusing than showing it as excluded.
class _RecentRatingStrip extends StatelessWidget {
  const _RecentRatingStrip({required this.performances});

  final List<GtexPlayerPerformance> performances;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          'RECENT MATCHES',
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
            color: _textMuted,
            fontWeight: FontWeight.w900,
            letterSpacing: 1.1,
          ),
        ),
        const SizedBox(height: 6),
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children: <Widget>[
            for (final GtexPlayerPerformance item in performances)
              _RatingPip(performance: item),
          ],
        ),
      ],
    );
  }
}

class _RatingPip extends StatelessWidget {
  const _RatingPip({required this.performance});

  final GtexPlayerPerformance performance;

  @override
  Widget build(BuildContext context) {
    final bool counted = performance.eligibleForValuation;
    final Color base = MatchdayFormCard.ratingColor(performance.rating);
    final Color color = counted ? base : _textMuted;

    return Tooltip(
      message: _tooltip(),
      child: Container(
        width: 42,
        padding: const EdgeInsets.symmetric(vertical: 5),
        decoration: BoxDecoration(
          color: color.withValues(alpha: counted ? 0.16 : 0.06),
          borderRadius: BorderRadius.circular(7),
          border: Border.all(
            color: color.withValues(alpha: counted ? 0.5 : 0.25),
          ),
        ),
        child: Text(
          performance.rating.toStringAsFixed(1),
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: color,
            fontWeight: FontWeight.w900,
            fontFamily: 'JetBrains Mono',
          ),
        ),
      ),
    );
  }

  String _tooltip() {
    final StringBuffer buffer =
        StringBuffer()..write('${performance.minutesPlayed} min');
    if (performance.goals > 0) {
      buffer.write(' · ${performance.goals}G');
    }
    if (performance.assists > 0) {
      buffer.write(' · ${performance.assists}A');
    }
    if (!performance.eligibleForValuation) {
      buffer.write(' · does not count toward valuation');
    }
    return buffer.toString();
  }
}

class _FormFootnote extends StatelessWidget {
  const _FormFootnote(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: Theme.of(
        context,
      ).textTheme.labelSmall?.copyWith(color: _textMuted, height: 1.35),
    );
  }
}
