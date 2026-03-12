import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/screens/competitions/competition_publish_preview_screen.dart';
import 'package:gte_frontend/screens/competitions/competition_rule_builder_screen.dart';
import 'package:gte_frontend/widgets/competitions/competition_financial_breakdown_card.dart';
import 'package:gte_frontend/widgets/competitions/competition_payout_card.dart';
import 'package:gte_frontend/widgets/competitions/competition_type_picker.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class CompetitionCreateScreen extends StatefulWidget {
  const CompetitionCreateScreen({
    super.key,
    required this.controller,
  });

  final CompetitionController controller;

  @override
  State<CompetitionCreateScreen> createState() => _CompetitionCreateScreenState();
}

class _CompetitionCreateScreenState extends State<CompetitionCreateScreen> {
  late final TextEditingController _nameController;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.controller.draft.name);
    _nameController.addListener(_handleNameChanged);
  }

  @override
  void dispose() {
    _nameController
      ..removeListener(_handleNameChanged)
      ..dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Create competition'),
      ),
      body: AnimatedBuilder(
        animation: widget.controller,
        builder: (BuildContext context, Widget? child) {
          final draft = widget.controller.draft;
          return ListView(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
            children: <Widget>[
              GteSurfacePanel(
                emphasized: true,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Create a creator competition',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Choose a skill league or skill cup, set clear entry fees, publish rules, and preview the transparent payout before sharing.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              CompetitionTypePicker(
                value: draft.format,
                onChanged: widget.controller.updateDraftFormat,
              ),
              const SizedBox(height: 20),
              GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Basic details',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: _nameController,
                      decoration: const InputDecoration(
                        labelText: 'Competition name',
                        hintText: 'Example: Friday Skill League',
                      ),
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'Visibility',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: <Widget>[
                        _VisibilityChip(
                          label: 'Public',
                          selected: draft.visibility == CompetitionVisibility.public,
                          onTap: () => widget.controller
                              .updateDraftVisibility(CompetitionVisibility.public),
                        ),
                        _VisibilityChip(
                          label: 'Private',
                          selected: draft.visibility == CompetitionVisibility.private,
                          onTap: () => widget.controller
                              .updateDraftVisibility(CompetitionVisibility.private),
                        ),
                        _VisibilityChip(
                          label: 'Invite only',
                          selected:
                              draft.visibility == CompetitionVisibility.inviteOnly,
                          onTap: () => widget.controller.updateDraftVisibility(
                            CompetitionVisibility.inviteOnly,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    SwitchListTile.adaptive(
                      value: draft.beginnerFriendly,
                      contentPadding: EdgeInsets.zero,
                      onChanged: widget.controller.updateDraftBeginnerFriendly,
                      title: const Text('Beginner friendly'),
                      subtitle: const Text(
                        'Mark this community competition as approachable for first-time creators and players.',
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Financial setup',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 16),
                    _SliderField(
                      title: 'Entry fee',
                      subtitle:
                          '${draft.entryFee.toStringAsFixed(draft.entryFee == draft.entryFee.roundToDouble() ? 0 : 2)} credits per player',
                      value: draft.entryFee,
                      min: 0,
                      max: 100,
                      divisions: 20,
                      onChanged: widget.controller.updateDraftEntryFee,
                    ),
                    _SliderField(
                      title: 'Platform service fee',
                      subtitle:
                          '${(draft.platformFeePct * 100).toStringAsFixed(0)}% of collected entry fees',
                      value: draft.platformFeePct * 100,
                      min: 0,
                      max: 20,
                      divisions: 20,
                      onChanged: (double pct) {
                        widget.controller.updateDraftPlatformFee(pct / 100);
                      },
                    ),
                    _SliderField(
                      title: 'Host fee',
                      subtitle:
                          '${(draft.hostFeePct * 100).toStringAsFixed(0)}% of collected entry fees',
                      value: draft.hostFeePct * 100,
                      min: 0,
                      max: 15,
                      divisions: 15,
                      onChanged: (double pct) {
                        widget.controller.updateDraftHostFee(pct / 100);
                      },
                    ),
                    _SliderField(
                      title: 'Capacity',
                      subtitle: '${draft.capacity} players',
                      value: draft.capacity.toDouble(),
                      min: 2,
                      max: 64,
                      divisions: 31,
                      onChanged: (double count) {
                        widget.controller.updateDraftCapacity(count.round());
                      },
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Transparent payout',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<int>(
                      initialValue: widget.controller.draft.payoutRules.length,
                      decoration: const InputDecoration(
                        labelText: 'Paid places',
                      ),
                      items: const <DropdownMenuItem<int>>[
                        DropdownMenuItem<int>(value: 1, child: Text('1 place')),
                        DropdownMenuItem<int>(value: 2, child: Text('2 places')),
                        DropdownMenuItem<int>(value: 3, child: Text('3 places')),
                        DropdownMenuItem<int>(value: 4, child: Text('4 places')),
                        DropdownMenuItem<int>(value: 5, child: Text('5 places')),
                      ],
                      onChanged: (int? count) {
                        if (count == null) {
                          return;
                        }
                        widget.controller.updateDraftPayoutPreset(count);
                      },
                    ),
                    const SizedBox(height: 16),
                    CompetitionPayoutCard(
                      title: 'Projected payout at full capacity',
                      currency: draft.currency,
                      payouts: widget.controller.previewSummary.payoutStructure,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              CompetitionFinancialBreakdownCard(
                title: 'Projected fee summary',
                entryFee: widget.controller.previewFinancials.entryFee,
                participantCount: widget.controller.previewFinancials.participantCount,
                platformFeePct: draft.platformFeePct,
                platformFeeAmount:
                    widget.controller.previewFinancials.platformFeeAmount,
                hostFeePct: draft.hostFeePct,
                hostFeeAmount: widget.controller.previewFinancials.hostFeeAmount,
                prizePool: widget.controller.previewFinancials.prizePool,
                currency: draft.currency,
                projected: true,
                lockNotice:
                    'After the first paid entry clears, fee settings and payout structure lock for participant safety.',
              ),
              const SizedBox(height: 16),
              if (widget.controller.draftErrors.isNotEmpty)
                GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: widget.controller.draftErrors
                        .map(
                          (String error) => Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: Text(
                              '• $error',
                              style: Theme.of(context).textTheme.bodyMedium,
                            ),
                          ),
                        )
                        .toList(growable: false),
                  ),
                ),
              const SizedBox(height: 20),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: <Widget>[
                  FilledButton.tonalIcon(
                    onPressed: _openRuleBuilder,
                    icon: const Icon(Icons.rule_folder_outlined),
                    label: const Text('Rules builder'),
                  ),
                  FilledButton(
                    onPressed: _openPreview,
                    child: const Text('Preview & publish'),
                  ),
                ],
              ),
            ],
          );
        },
      ),
    );
  }

  void _handleNameChanged() {
    widget.controller.updateDraftName(_nameController.text);
  }

  Future<void> _openRuleBuilder() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => CompetitionRuleBuilderScreen(
          controller: widget.controller,
        ),
      ),
    );
  }

  Future<void> _openPreview() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => CompetitionPublishPreviewScreen(
          controller: widget.controller,
        ),
      ),
    );
  }
}

class _VisibilityChip extends StatelessWidget {
  const _VisibilityChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: ChoiceChip(
        label: Text(label),
        selected: selected,
        onSelected: (_) => onTap(),
      ),
    );
  }
}

class _SliderField extends StatelessWidget {
  const _SliderField({
    required this.title,
    required this.subtitle,
    required this.value,
    required this.min,
    required this.max,
    required this.divisions,
    required this.onChanged,
  });

  final String title;
  final String subtitle;
  final double value;
  final double min;
  final double max;
  final int divisions;
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
          onChanged: onChanged,
        ),
        const SizedBox(height: 8),
      ],
    );
  }
}
