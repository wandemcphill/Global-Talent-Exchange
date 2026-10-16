import 'package:flutter/material.dart';

import 'package:gte_frontend/domain/match/match_weight_presets.dart';
import 'package:gte_frontend/domain/match/match_weights.dart';

class MatchWeightsSheet extends StatefulWidget {
  const MatchWeightsSheet({
    super.key,
    required this.initial,
    required this.onApply,
  });

  final MatchWeights initial;
  final ValueChanged<MatchWeights> onApply;

  @override
  State<MatchWeightsSheet> createState() => _MatchWeightsSheetState();
}

class _MatchWeightsSheetState extends State<MatchWeightsSheet> {
  late MatchWeights _draft;

  @override
  void initState() {
    super.initState();
    _draft = widget.initial;
  }

  @override
  void didUpdateWidget(covariant MatchWeightsSheet oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.initial.cacheKey != widget.initial.cacheKey) {
      _draft = widget.initial;
    }
  }

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final MatchWeights normalized = _draft.normalize();
    final MatchWeightPreset? activePreset = MatchWeightPresets.resolve(_draft);

    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          16,
          16,
          16,
          16 + MediaQuery.of(context).viewInsets.bottom,
        ),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Tune Matching Logic',
                style: theme.textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                activePreset == null
                    ? 'Custom Mix'
                    : '${activePreset.badgeLabel} Mode',
                style: theme.textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w700,
                  color: theme.colorScheme.primary,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'Adjust the emphasis for each factor. The mix is normalized when you apply it.',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: MatchWeightPresets.all
                    .map(
                      (MatchWeightPreset preset) => ChoiceChip(
                        label: Text(preset.label),
                        selected: activePreset?.badgeLabel == preset.badgeLabel,
                        onSelected: (_) {
                          setState(() {
                            _draft = preset.weights;
                          });
                        },
                      ),
                    )
                    .toList(growable: false),
              ),
              const SizedBox(height: 16),
              _WeightSliderRow(
                label: 'Position',
                value: _draft.position,
                normalizedValue: normalized.position,
                onChanged: (double value) {
                  setState(() {
                    _draft = _draft.copyWith(position: value);
                  });
                },
              ),
              _WeightSliderRow(
                label: 'Age',
                value: _draft.age,
                normalizedValue: normalized.age,
                onChanged: (double value) {
                  setState(() {
                    _draft = _draft.copyWith(age: value);
                  });
                },
              ),
              _WeightSliderRow(
                label: 'Country',
                value: _draft.country,
                normalizedValue: normalized.country,
                onChanged: (double value) {
                  setState(() {
                    _draft = _draft.copyWith(country: value);
                  });
                },
              ),
              _WeightSliderRow(
                label: 'Height',
                value: _draft.height,
                normalizedValue: normalized.height,
                onChanged: (double value) {
                  setState(() {
                    _draft = _draft.copyWith(height: value);
                  });
                },
              ),
              _WeightSliderRow(
                label: 'Foot',
                value: _draft.foot,
                normalizedValue: normalized.foot,
                onChanged: (double value) {
                  setState(() {
                    _draft = _draft.copyWith(foot: value);
                  });
                },
              ),
              _WeightSliderRow(
                label: 'Availability',
                value: _draft.availability,
                normalizedValue: normalized.availability,
                onChanged: (double value) {
                  setState(() {
                    _draft = _draft.copyWith(availability: value);
                  });
                },
              ),
              const SizedBox(height: 16),
              Row(
                children: <Widget>[
                  TextButton(
                    onPressed: () {
                      setState(() {
                        _draft = MatchWeights.defaultWeights();
                      });
                    },
                    child: const Text('Reset'),
                  ),
                  const Spacer(),
                  FilledButton(
                    onPressed: () => widget.onApply(_draft.normalize()),
                    child: const Text('Apply'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _WeightSliderRow extends StatelessWidget {
  const _WeightSliderRow({
    required this.label,
    required this.value,
    required this.normalizedValue,
    required this.onChanged,
  });

  final String label;
  final double value;
  final double normalizedValue;
  final ValueChanged<double> onChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: <Widget>[
            Text(label),
            Text('${(normalizedValue * 100).round()}%'),
          ],
        ),
        Slider(
          value: value.clamp(0, 1).toDouble(),
          min: 0,
          max: 1,
          divisions: 20,
          onChanged: onChanged,
        ),
      ],
    );
  }
}
