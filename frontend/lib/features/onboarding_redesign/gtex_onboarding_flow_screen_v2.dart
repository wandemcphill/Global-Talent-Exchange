import 'package:flutter/material.dart';

import '../../ui_gtex/components/gtex_button.dart';
import '../../ui_gtex/components/gtex_card.dart';
import '../../ui_gtex/components/gtex_status_chip.dart';
import '../../ui_gtex/theme/gtex_colors.dart';
import 'onboarding_redesign_controller.dart';
import 'onboarding_redesign_models.dart';

class GtexOnboardingFlowScreenV2 extends StatefulWidget {
  const GtexOnboardingFlowScreenV2({
    super.key,
    this.controller,
    this.onOpenMarket,
    this.onCreateClub,
    this.onJoinClub,
    this.onStartKyc,
    this.onOpenCompetitions,
  });

  final GtexOnboardingController? controller;
  final VoidCallback? onOpenMarket;
  final VoidCallback? onCreateClub;
  final VoidCallback? onJoinClub;
  final VoidCallback? onStartKyc;
  final VoidCallback? onOpenCompetitions;

  @override
  State<GtexOnboardingFlowScreenV2> createState() => _GtexOnboardingFlowScreenV2State();
}

class _GtexOnboardingFlowScreenV2State extends State<GtexOnboardingFlowScreenV2> {
  late final GtexOnboardingController _controller = widget.controller ?? GtexOnboardingController();
  int _page = 0;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        final state = _controller.state;
        return Scaffold(
          backgroundColor: GtexColors.black,
          body: SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _Header(page: _page),
                  const SizedBox(height: 18),
                  Expanded(
                    child: IndexedStack(
                      index: _page,
                      children: [
                        _RoleSelection(state: state, onSelect: _controller.selectRole),
                        _RegionSelection(state: state, onSelect: _controller.selectRegion),
                        _ClubDecision(onCreateClub: widget.onCreateClub, onJoinClub: widget.onJoinClub),
                        _NewUserDashboard(
                          steps: state.steps,
                          onOpenMarket: widget.onOpenMarket,
                          onStartKyc: widget.onStartKyc,
                          onOpenCompetitions: widget.onOpenCompetitions,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      if (_page > 0) GtexButton(label: 'Back', variant: GtexButtonVariant.secondary, onPressed: () => setState(() => _page--)),
                      const Spacer(),
                      if (_page < 3) GtexButton(label: 'Continue', onPressed: () => setState(() => _page++)),
                    ],
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.page});
  final int page;

  @override
  Widget build(BuildContext context) {
    final labels = ['Role', 'Region', 'Club', 'Dashboard'];
    return Row(
      children: [
        const Text('GTEX Setup', style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w900)),
        const Spacer(),
        Wrap(
          spacing: 8,
          children: List.generate(labels.length, (i) => GtexStatusChip(label: labels[i], tone: i <= page ? GtexStatusTone.success : GtexStatusTone.neutral)),
        ),
      ],
    );
  }
}

class _RoleSelection extends StatelessWidget {
  const _RoleSelection({required this.state, required this.onSelect});
  final GtexOnboardingState state;
  final ValueChanged<String> onSelect;

  @override
  Widget build(BuildContext context) {
    return _FlowPanel(
      title: 'Choose how you want to enter GTEX',
      subtitle: 'This does not remove access to other features. It controls your first dashboard and onboarding checklist.',
      child: Wrap(
        spacing: 16,
        runSpacing: 16,
        children: state.roles.map((role) {
          final selected = role.id == state.selectedRoleId;
          return SizedBox(
            width: 320,
            child: _SelectableCard(
              selected: selected,
              title: role.title,
              subtitle: role.description,
              lines: role.highlights,
              onTap: () => onSelect(role.id),
            ),
          );
        }).toList(),
      ),
    );
  }
}

class _RegionSelection extends StatelessWidget {
  const _RegionSelection({required this.state, required this.onSelect});
  final GtexOnboardingState state;
  final ValueChanged<String> onSelect;

  @override
  Widget build(BuildContext context) {
    return _FlowPanel(
      title: 'Pick your football region',
      subtitle: 'GTEX can later use this for market defaults, player discovery, national-team rentals and local competitions.',
      child: Wrap(
        spacing: 16,
        runSpacing: 16,
        children: state.regions.map((region) {
          final selected = region.code == state.selectedRegionCode;
          return SizedBox(
            width: 300,
            child: _SelectableCard(
              selected: selected,
              title: region.name,
              subtitle: '${region.marketCount} players and prospects indexed',
              lines: region.featuredLeagues,
              onTap: () => onSelect(region.code),
            ),
          );
        }).toList(),
      ),
    );
  }
}

class _ClubDecision extends StatelessWidget {
  const _ClubDecision({this.onCreateClub, this.onJoinClub});
  final VoidCallback? onCreateClub;
  final VoidCallback? onJoinClub;

  @override
  Widget build(BuildContext context) {
    return _FlowPanel(
      title: 'Create or join a club',
      subtitle: 'A club is the core of GTEX. It connects your squad, transfers, wallet, tournaments, shares and public profile.',
      child: Wrap(
        spacing: 16,
        runSpacing: 16,
        children: [
          SizedBox(width: 360, child: _ActionCard(icon: Icons.add_circle_outline, title: 'Create a new club', subtitle: 'Design your identity, build a squad and enter competitions.', action: 'Create club', onTap: onCreateClub)),
          SizedBox(width: 360, child: _ActionCard(icon: Icons.groups_2_outlined, title: 'Join or follow a club', subtitle: 'Find existing clubs, follow their progress or buy shares.', action: 'Find clubs', onTap: onJoinClub)),
        ],
      ),
    );
  }
}

class _NewUserDashboard extends StatelessWidget {
  const _NewUserDashboard({required this.steps, this.onOpenMarket, this.onStartKyc, this.onOpenCompetitions});
  final List<GtexOnboardingStep> steps;
  final VoidCallback? onOpenMarket;
  final VoidCallback? onStartKyc;
  final VoidCallback? onOpenCompetitions;

  @override
  Widget build(BuildContext context) {
    return _FlowPanel(
      title: 'Your first GTEX dashboard',
      subtitle: 'A calm starter command center for new users before they graduate into the full app.',
      child: Column(
        children: [
          ...steps.map((step) {
            final callback = switch (step.id) {
              'verify_profile' => onStartKyc,
              'shortlist_players' => onOpenMarket,
              'join_competition' => onOpenCompetitions,
              _ => null,
            };
            return Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: GtexCard(
                child: Row(
                  children: [
                    Icon(step.completed ? Icons.check_circle : Icons.radio_button_unchecked, color: step.completed ? GtexColors.green : GtexColors.textMuted),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(step.title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900)),
                        const SizedBox(height: 4),
                        Text(step.description, style: const TextStyle(color: GtexColors.textSecondary)),
                      ]),
                    ),
                    const SizedBox(width: 12),
                    GtexButton(label: step.ctaLabel, variant: GtexButtonVariant.secondary, onPressed: callback),
                  ],
                ),
              ),
            );
          }),
        ],
      ),
    );
  }
}

class _FlowPanel extends StatelessWidget {
  const _FlowPanel({required this.title, required this.subtitle, required this.child});
  final String title;
  final String subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(title, style: const TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.w900)),
        const SizedBox(height: 10),
        ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 760),
          child: Text(subtitle, style: const TextStyle(color: GtexColors.textSecondary, height: 1.42)),
        ),
        const SizedBox(height: 24),
        child,
      ]),
    );
  }
}

class _SelectableCard extends StatelessWidget {
  const _SelectableCard({required this.selected, required this.title, required this.subtitle, required this.lines, required this.onTap});
  final bool selected;
  final String title;
  final String subtitle;
  final List<String> lines;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: GtexCard(
        borderColor: selected ? GtexColors.green : null,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(selected ? Icons.check_circle : Icons.circle_outlined, color: selected ? GtexColors.green : GtexColors.textMuted),
            const Spacer(),
            if (selected) const GtexStatusChip(label: 'Selected', tone: GtexStatusTone.success),
          ]),
          const SizedBox(height: 12),
          Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18)),
          const SizedBox(height: 8),
          Text(subtitle, style: const TextStyle(color: GtexColors.textSecondary, height: 1.35)),
          const SizedBox(height: 12),
          ...lines.map((line) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(children: [
                  const Icon(Icons.sports_soccer, color: GtexColors.green, size: 14),
                  const SizedBox(width: 8),
                  Expanded(child: Text(line, style: const TextStyle(color: GtexColors.textMuted, fontSize: 12))),
                ]),
              )),
        ]),
      ),
    );
  }
}

class _ActionCard extends StatelessWidget {
  const _ActionCard({required this.icon, required this.title, required this.subtitle, required this.action, this.onTap});
  final IconData icon;
  final String title;
  final String subtitle;
  final String action;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return GtexCard(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(icon, color: GtexColors.green, size: 34),
        const SizedBox(height: 14),
        Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 20)),
        const SizedBox(height: 8),
        Text(subtitle, style: const TextStyle(color: GtexColors.textSecondary, height: 1.4)),
        const SizedBox(height: 18),
        GtexButton(label: action, onPressed: onTap),
      ]),
    );
  }
}
