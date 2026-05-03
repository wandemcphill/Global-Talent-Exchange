import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/screens/competitions/competition_publish_preview_screen.dart';
import 'package:gte_frontend/screens/competitions/competition_rule_builder_screen.dart';
import 'package:gte_frontend/widgets/competitions/competition_financial_breakdown_card.dart';
import 'package:gte_frontend/widgets/competitions/competition_payout_card.dart';
import 'package:gte_frontend/widgets/competitions/competition_type_picker.dart';
import 'package:gte_frontend/widgets/gte_formatters.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class CompetitionCreateScreen extends StatefulWidget {
  const CompetitionCreateScreen({
    super.key,
    required this.controller,
    this.isAuthenticated = false,
    this.isCheckingHostEligibility = false,
    this.hostEligible = false,
    this.onOpenLogin,
    this.onOpenCreatorAccessRequest,
  });

  final CompetitionController controller;
  final bool isAuthenticated;
  final bool isCheckingHostEligibility;
  final bool hostEligible;
  final VoidCallback? onOpenLogin;
  final VoidCallback? onOpenCreatorAccessRequest;

  @override
  State<CompetitionCreateScreen> createState() =>
      _CompetitionCreateScreenState();
}

class _CompetitionCreateScreenState extends State<CompetitionCreateScreen> {
  late final TextEditingController _nameController;
  late final TextEditingController _passcodeController;
  late final TextEditingController _specialRulesController;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.controller.draft.name);
    _passcodeController = TextEditingController(
      text: widget.controller.draft.passcode ?? '',
    );
    _specialRulesController = TextEditingController(
      text: widget.controller.draft.specialRules ?? '',
    );
    _nameController.addListener(_handleNameChanged);
    _passcodeController.addListener(_handlePasscodeChanged);
    _specialRulesController.addListener(_handleSpecialRulesChanged);
  }

  @override
  void dispose() {
    _nameController
      ..removeListener(_handleNameChanged)
      ..dispose();
    _passcodeController
      ..removeListener(_handlePasscodeChanged)
      ..dispose();
    _specialRulesController
      ..removeListener(_handleSpecialRulesChanged)
      ..dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Create competition')),
      body: AnimatedBuilder(
        animation: widget.controller,
        builder: (BuildContext context, Widget? child) {
          if (!widget.isAuthenticated || widget.isCheckingHostEligibility) {
            return _buildLockedState();
          }
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
                      'Create competition',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Choose a format, set entry requirements, publish the rules, and preview the payout before sharing.',
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
                          selected:
                              draft.visibility == CompetitionVisibility.public,
                          onTap:
                              () => widget.controller.updateDraftVisibility(
                                CompetitionVisibility.public,
                              ),
                        ),
                        _VisibilityChip(
                          label: 'Private',
                          selected:
                              draft.visibility == CompetitionVisibility.private,
                          onTap:
                              () => widget.controller.updateDraftVisibility(
                                CompetitionVisibility.private,
                              ),
                        ),
                        _VisibilityChip(
                          label: 'Invite only',
                          selected:
                              draft.visibility ==
                              CompetitionVisibility.inviteOnly,
                          onTap:
                              () => widget.controller.updateDraftVisibility(
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
                        'Mark this competition as approachable for first-time players.',
                      ),
                    ),
                    const SizedBox(height: 16),
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Start date and time'),
                      subtitle: Text(
                        draft.scheduledStartAt == null
                            ? 'Managers can join until the competition starts.'
                            : draft.scheduledStartAt!
                                .toLocal()
                                .toString()
                                .substring(0, 16),
                      ),
                      trailing: FilledButton.tonal(
                        onPressed: _pickStartTime,
                        child: const Text('Set'),
                      ),
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: _passcodeController,
                      decoration: const InputDecoration(
                        labelText: 'Passcode (optional)',
                        hintText: 'Leave empty for open entry',
                      ),
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: _specialRulesController,
                      maxLines: 3,
                      decoration: const InputDecoration(
                        labelText: 'Special rules',
                        hintText: 'Example: U20 squads only, knockout format',
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
                    const SizedBox(height: 8),
                    Text(
                      'User competition buy-ins and prize pools settle in Fan Coin.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 16),
                    _SliderField(
                      title: 'Entry fee',
                      subtitle:
                          '${gteFormatCompetitionAmount(draft.entryFee, draft.currency)} per player',
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
                        DropdownMenuItem<int>(
                          value: 2,
                          child: Text('2 places'),
                        ),
                        DropdownMenuItem<int>(
                          value: 3,
                          child: Text('3 places'),
                        ),
                        DropdownMenuItem<int>(
                          value: 4,
                          child: Text('4 places'),
                        ),
                        DropdownMenuItem<int>(
                          value: 5,
                          child: Text('5 places'),
                        ),
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
                participantCount:
                    widget.controller.previewFinancials.participantCount,
                platformFeePct: draft.platformFeePct,
                platformFeeAmount:
                    widget.controller.previewFinancials.platformFeeAmount,
                hostFeePct: draft.hostFeePct,
                hostFeeAmount:
                    widget.controller.previewFinancials.hostFeeAmount,
                prizePool: widget.controller.previewFinancials.prizePool,
                currency: draft.currency,
                matchType: widget.controller.previewSummary.matchType,
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
                              '- $error',
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

  Widget _buildLockedState() {
    if (!widget.isAuthenticated) {
      return SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
        child: GteStatePanel(
          eyebrow: 'HOST ACCESS',
          title: 'Sign in to create competitions',
          message:
              'A signed-in account is required before the competition form can be opened.',
          actionLabel: widget.onOpenLogin == null ? null : 'Sign in',
          onAction: widget.onOpenLogin,
          icon: Icons.login_outlined,
        ),
      );
    }
    if (widget.isCheckingHostEligibility) {
      return const SingleChildScrollView(
        padding: EdgeInsets.fromLTRB(20, 12, 20, 120),
        child: GteStatePanel(
          eyebrow: 'HOST ACCESS',
          title: 'Checking competition access',
          message:
              'Confirming whether this account can open the competition builder.',
          icon: Icons.hourglass_top_outlined,
          isLoading: true,
        ),
      );
    }
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
      child: GteStatePanel(
        eyebrow: 'HOST ACCESS',
        title: 'Competition creation unavailable',
        message: 'This account cannot open the competition builder yet.',
        actionLabel:
            widget.onOpenCreatorAccessRequest == null ? null : 'Request access',
        onAction: widget.onOpenCreatorAccessRequest,
        icon: Icons.how_to_reg_outlined,
      ),
    );
  }

  void _handleNameChanged() {
    widget.controller.updateDraftName(_nameController.text);
  }

  void _handlePasscodeChanged() {
    widget.controller.updateDraftPasscode(_passcodeController.text);
  }

  void _handleSpecialRulesChanged() {
    widget.controller.updateDraftSpecialRules(_specialRulesController.text);
  }

  Future<void> _pickStartTime() async {
    final DateTime now = DateTime.now();
    final DateTime initial =
        widget.controller.draft.scheduledStartAt?.toLocal() ??
        now.add(const Duration(hours: 2));
    final DateTime? date = await showDatePicker(
      context: context,
      firstDate: now,
      lastDate: now.add(const Duration(days: 365)),
      initialDate: initial,
    );
    if (date == null || !mounted) {
      return;
    }
    final TimeOfDay? time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(initial),
    );
    if (time == null) {
      return;
    }
    widget.controller.updateDraftScheduledStart(
      DateTime(date.year, date.month, date.day, time.hour, time.minute),
    );
  }

  Future<void> _openRuleBuilder() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) =>
                CompetitionRuleBuilderScreen(controller: widget.controller),
      ),
    );
  }

  Future<void> _openPreview() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) =>
                CompetitionPublishPreviewScreen(controller: widget.controller),
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
