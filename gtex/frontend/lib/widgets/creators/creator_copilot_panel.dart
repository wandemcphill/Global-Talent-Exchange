import 'package:flutter/material.dart';

import '../../controllers/creator_controller.dart';
import '../../models/creator_models.dart';
import '../gte_state_panel.dart';
import '../gte_surface_panel.dart';

class CreatorCopilotPanel extends StatelessWidget {
  const CreatorCopilotPanel({super.key, required this.controller});

  final CreatorController controller;

  @override
  Widget build(BuildContext context) {
    final CreatorCopilotDraft? draft = controller.copilotDraft;
    if (draft == null) {
      return const GteStatePanel(
        eyebrow: 'AI CREATOR COPILOT',
        title: 'Preparing upload copilot',
        message:
            'Seeding a starter draft so predictions, format guidance, and posting timing can load.',
        icon: Icons.auto_awesome_outlined,
      );
    }

    final ThemeData theme = Theme.of(context);
    final Color accent = const Color(0xFF24C3A7);
    final CreatorCopilotAnalysis? analysis = controller.copilotAnalysis;

    return GteSurfacePanel(
      emphasized: true,
      accentColor: accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'AI CREATOR COPILOT',
                      style: theme.textTheme.labelLarge?.copyWith(
                        color: accent,
                        letterSpacing: 1.1,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Predict before you post.',
                      style: theme.textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 10),
                    Text(
                      'Tune the draft, run the model, and let the copilot tell you whether to post now, change format, or tighten the hook first.',
                      style: theme.textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 16),
              FilledButton.tonalIcon(
                onPressed:
                    controller.isAnalyzingCopilot
                        ? null
                        : () => controller.analyzeCopilot(),
                icon: const Icon(Icons.auto_awesome),
                label: Text(
                  controller.isAnalyzingCopilot
                      ? 'Analyzing...'
                      : 'Optimize with AI',
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          _SelectorRow(
            title: 'Event type',
            options: const <String>['goal', 'analysis', 'reaction', 'upset'],
            selected: draft.eventType,
            onSelected:
                (String value) => controller.setCopilotDraft(
                  draft.copyWith(eventType: value),
                ),
          ),
          const SizedBox(height: 14),
          _SelectorRow(
            title: 'Preferred format',
            options: const <String>[
              'meme',
              'instant',
              'debate',
              'tactical',
              'cinematic',
            ],
            selected: draft.preferredFormat,
            onSelected:
                (String value) => controller.setCopilotDraft(
                  draft.copyWith(preferredFormat: value),
                ),
          ),
          const SizedBox(height: 18),
          _MetricSlider(
            title: 'Clip length',
            valueLabel: '${draft.durationSeconds.round()}s',
            value: draft.durationSeconds,
            min: 8,
            max: 45,
            divisions: 37,
            onChanged:
                (double value) => controller.setCopilotDraft(
                  draft.copyWith(durationSeconds: value),
                ),
          ),
          _MetricSlider(
            title: 'Intro length',
            valueLabel: '${draft.introSeconds.toStringAsFixed(1)}s',
            value: draft.introSeconds,
            min: 0,
            max: 4,
            divisions: 20,
            onChanged:
                (double value) => controller.setCopilotDraft(
                  draft.copyWith(introSeconds: value),
                ),
          ),
          _MetricSlider(
            title: 'Visual intensity',
            valueLabel: '${(draft.visualIntensity * 100).round()}%',
            value: draft.visualIntensity,
            min: 0,
            max: 1,
            divisions: 20,
            onChanged:
                (double value) => controller.setCopilotDraft(
                  draft.copyWith(visualIntensity: value),
                ),
          ),
          _MetricSlider(
            title: 'Event density',
            valueLabel: '${(draft.eventDensity * 100).round()}%',
            value: draft.eventDensity,
            min: 0,
            max: 1,
            divisions: 20,
            onChanged:
                (double value) => controller.setCopilotDraft(
                  draft.copyWith(eventDensity: value),
                ),
          ),
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              color: theme.colorScheme.surface.withValues(alpha: 0.28),
              border: Border.all(
                color: theme.colorScheme.outlineVariant.withValues(alpha: 0.45),
              ),
            ),
            child: Row(
              children: <Widget>[
                const Expanded(child: Text('Reaction overlay')),
                Switch.adaptive(
                  value: draft.hasReactionOverlay,
                  onChanged:
                      (bool value) => controller.setCopilotDraft(
                        draft.copyWith(hasReactionOverlay: value),
                      ),
                ),
              ],
            ),
          ),
          if (controller.copilotErrorMessage != null) ...<Widget>[
            const SizedBox(height: 14),
            Text(
              controller.copilotErrorMessage!,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.error,
              ),
            ),
          ],
          if (analysis != null) ...<Widget>[
            const SizedBox(height: 22),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: <Widget>[
                _StatTile(
                  label: 'Viral score',
                  value: '${analysis.prediction.viralScorePercent}%',
                  helper: 'Probability',
                ),
                _StatTile(
                  label: 'Expected views',
                  value: analysis.prediction.expectedViews.toString(),
                  helper: 'First window',
                ),
                _StatTile(
                  label: 'Best format',
                  value: analysis.prediction.bestFormat,
                  helper: 'Model winner',
                ),
                _StatTile(
                  label: 'Hook',
                  value: '${analysis.hookAnalysis.hookScorePercent}%',
                  helper: analysis.hookAnalysis.introStrength,
                ),
              ],
            ),
            if (analysis.prediction.riskFlags.isNotEmpty) ...<Widget>[
              const SizedBox(height: 16),
              Text('Risk flags', style: theme.textTheme.titleMedium),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: analysis.prediction.riskFlags
                    .map((String item) => _SignalChip(label: item))
                    .toList(growable: false),
              ),
            ],
            const SizedBox(height: 18),
            Text('Recommended variants', style: theme.textTheme.titleMedium),
            const SizedBox(height: 10),
            for (final CreatorCopilotVariantRecommendation item
                in analysis.variantStrategy.recommendedVariants) ...<Widget>[
              _VariantTile(item: item),
              if (item != analysis.variantStrategy.recommendedVariants.last)
                const SizedBox(height: 10),
            ],
            const SizedBox(height: 18),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Expanded(
                  child: _InsightBox(
                    title: 'Timing intelligence',
                    body:
                        analysis.timing.postNow
                            ? 'Post now. ${analysis.timing.reason}.'
                            : 'Wait ${analysis.timing.bestTimeInMinutes} minutes. ${analysis.timing.reason}.',
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _InsightBox(
                    title: 'Hook guidance',
                    body: analysis.hookAnalysis.suggestion,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 18),
            _InsightBox(
              title: 'Strategy profile',
              body: analysis.strategyProfile.summary,
              footer:
                  analysis.strategyProfile.winningFormats.isEmpty
                      ? null
                      : 'Winning formats: ${analysis.strategyProfile.winningFormats.join(', ')}',
            ),
            const SizedBox(height: 12),
            _InsightBox(
              title: analysis.liveCoaching.headline,
              body: analysis.liveCoaching.message,
              footer: analysis.liveCoaching.recommendedAction,
            ),
            if (analysis.actionPlan.isNotEmpty) ...<Widget>[
              const SizedBox(height: 18),
              Text('Action plan', style: theme.textTheme.titleMedium),
              const SizedBox(height: 8),
              for (final String item in analysis.actionPlan) ...<Widget>[
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    const Padding(
                      padding: EdgeInsets.only(top: 6),
                      child: Icon(Icons.circle, size: 7),
                    ),
                    const SizedBox(width: 10),
                    Expanded(child: Text(item)),
                  ],
                ),
                if (item != analysis.actionPlan.last) const SizedBox(height: 8),
              ],
            ],
          ],
        ],
      ),
    );
  }
}

class _SelectorRow extends StatelessWidget {
  const _SelectorRow({
    required this.title,
    required this.options,
    required this.selected,
    required this.onSelected,
  });

  final String title;
  final List<String> options;
  final String selected;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(title, style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: options
              .map(
                (String option) => ChoiceChip(
                  label: Text(option),
                  selected: selected == option,
                  onSelected: (_) => onSelected(option),
                ),
              )
              .toList(growable: false),
        ),
      ],
    );
  }
}

class _MetricSlider extends StatelessWidget {
  const _MetricSlider({
    required this.title,
    required this.valueLabel,
    required this.value,
    required this.min,
    required this.max,
    required this.divisions,
    required this.onChanged,
  });

  final String title;
  final String valueLabel;
  final double value;
  final double min;
  final double max;
  final int divisions;
  final ValueChanged<double> onChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        Row(children: <Widget>[Expanded(child: Text(title)), Text(valueLabel)]),
        Slider(
          value: value.clamp(min, max),
          min: min,
          max: max,
          divisions: divisions,
          onChanged: onChanged,
        ),
      ],
    );
  }
}

class _StatTile extends StatelessWidget {
  const _StatTile({
    required this.label,
    required this.value,
    required this.helper,
  });

  final String label;
  final String value;
  final String helper;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 160,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: Theme.of(context).colorScheme.surface.withValues(alpha: 0.25),
        border: Border.all(
          color: Theme.of(
            context,
          ).colorScheme.outlineVariant.withValues(alpha: 0.45),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 6),
          Text(value, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 4),
          Text(helper, style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}

class _SignalChip extends StatelessWidget {
  const _SignalChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: Theme.of(
          context,
        ).colorScheme.errorContainer.withValues(alpha: 0.35),
      ),
      child: Text(label),
    );
  }
}

class _VariantTile extends StatelessWidget {
  const _VariantTile({required this.item});

  final CreatorCopilotVariantRecommendation item;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: Theme.of(context).colorScheme.surface.withValues(alpha: 0.24),
        border: Border.all(
          color: Theme.of(
            context,
          ).colorScheme.outlineVariant.withValues(alpha: 0.42),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  '${item.type} ${item.exploratory ? '(explore)' : '(lead)'}',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                const SizedBox(height: 6),
                Text(item.reason),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Text('${(item.confidence * 100).round()}%'),
        ],
      ),
    );
  }
}

class _InsightBox extends StatelessWidget {
  const _InsightBox({required this.title, required this.body, this.footer});

  final String title;
  final String body;
  final String? footer;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: Theme.of(context).colorScheme.surface.withValues(alpha: 0.24),
        border: Border.all(
          color: Theme.of(
            context,
          ).colorScheme.outlineVariant.withValues(alpha: 0.42),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 8),
          Text(body),
          if (footer != null) ...<Widget>[
            const SizedBox(height: 8),
            Text(footer!, style: Theme.of(context).textTheme.bodySmall),
          ],
        ],
      ),
    );
  }
}
