import 'package:flutter/material.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/competition_rule_models.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class CompetitionRuleEditor extends StatelessWidget {
  const CompetitionRuleEditor({
    super.key,
    required this.format,
    required this.value,
    required this.onChanged,
  });

  final CompetitionFormat format;
  final CompetitionRuleSet value;
  final ValueChanged<CompetitionRuleSet> onChanged;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Rules', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(
            'Keep creator competitions skill-based, verified, and easy to understand before publishing.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 20),
          SwitchListTile.adaptive(
            value: value.allowLateJoin,
            contentPadding: EdgeInsets.zero,
            title: const Text('Allow late entries'),
            subtitle: Text(
              format == CompetitionFormat.league
                  ? 'Useful for longer skill leagues before the first scoring window closes.'
                  : 'Most skill cups stay closed once the bracket starts.',
            ),
            onChanged: (bool enabled) {
              onChanged(value.copyWith(allowLateJoin: enabled));
            },
          ),
          const SizedBox(height: 12),
          _SliderRow(
            title: 'Lineup lock',
            subtitle:
                '${value.lineupLockMinutes} minutes before each scoring window',
            min: 15,
            max: 180,
            divisions: 11,
            value: value.lineupLockMinutes.toDouble(),
            onChanged: (double minutes) {
              onChanged(
                value.copyWith(
                  lineupLockMinutes: ((minutes / 15).round() * 15).clamp(15, 180),
                ),
              );
            },
          ),
          const SizedBox(height: 12),
          _SliderRow(
            title: 'Review window',
            subtitle: '${value.reviewWindowHours} hours for result review',
            min: 2,
            max: 48,
            divisions: 23,
            value: value.reviewWindowHours.toDouble(),
            onChanged: (double hours) {
              onChanged(
                value.copyWith(
                  reviewWindowHours: ((hours / 2).round() * 2).clamp(2, 48),
                ),
              );
            },
          ),
          const SizedBox(height: 16),
          DropdownButtonFormField<CompetitionTieBreaker>(
            initialValue: value.tieBreaker,
            decoration: const InputDecoration(
              labelText: 'Tie-break rule',
            ),
            items: const <DropdownMenuItem<CompetitionTieBreaker>>[
              DropdownMenuItem<CompetitionTieBreaker>(
                value: CompetitionTieBreaker.headToHead,
                child: Text('Head-to-head first'),
              ),
              DropdownMenuItem<CompetitionTieBreaker>(
                value: CompetitionTieBreaker.scoreDifference,
                child: Text('Score difference first'),
              ),
              DropdownMenuItem<CompetitionTieBreaker>(
                value: CompetitionTieBreaker.playoffRound,
                child: Text('Extra playoff round'),
              ),
            ],
            onChanged: (CompetitionTieBreaker? next) {
              if (next == null) {
                return;
              }
              onChanged(value.copyWith(tieBreaker: next));
            },
          ),
          const SizedBox(height: 16),
          SwitchListTile.adaptive(
            value: value.requireVerification,
            contentPadding: EdgeInsets.zero,
            title: const Text('Require verified results'),
            subtitle: const Text(
              'Use verified scoring and a published review window before payouts settle.',
            ),
            onChanged: (bool enabled) {
              onChanged(value.copyWith(requireVerification: enabled));
            },
          ),
          SwitchListTile.adaptive(
            value: value.showEscrowLedger,
            contentPadding: EdgeInsets.zero,
            title: const Text('Show secure escrow language'),
            subtitle: const Text(
              'Keep entry fee movement clear before users join or share invites.',
            ),
            onChanged: (bool enabled) {
              onChanged(value.copyWith(showEscrowLedger: enabled));
            },
          ),
          const SizedBox(height: 16),
          Text('Rules summary', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          ...value.bullets(format).map(
                (String bullet) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      const Padding(
                        padding: EdgeInsets.only(top: 5),
                        child: Icon(Icons.circle, size: 8),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          bullet,
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
        ],
      ),
    );
  }
}

class _SliderRow extends StatelessWidget {
  const _SliderRow({
    required this.title,
    required this.subtitle,
    required this.min,
    required this.max,
    required this.divisions,
    required this.value,
    required this.onChanged,
  });

  final String title;
  final String subtitle;
  final double min;
  final double max;
  final int divisions;
  final double value;
  final ValueChanged<double> onChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(title, style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 4),
        Text(subtitle, style: Theme.of(context).textTheme.bodyMedium),
        Slider(
          value: value.clamp(min, max),
          min: min,
          max: max,
          divisions: divisions,
          label: value.round().toString(),
          onChanged: onChanged,
        ),
      ],
    );
  }
}
