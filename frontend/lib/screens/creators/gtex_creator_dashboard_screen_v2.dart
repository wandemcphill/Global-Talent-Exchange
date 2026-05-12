import 'package:flutter/material.dart';

import '../../features/creator_social_redesign/models/gtex_creator_social_models.dart';
import '../../features/creator_social_redesign/presentation/gtex_creator_social_controller.dart';
import '../../features/creator_social_redesign/widgets/gtex_creator_competition_panel.dart';
import '../../features/creator_social_redesign/widgets/gtex_creator_metric_grid.dart';
import '../../features/creator_social_redesign/widgets/gtex_creator_social_visuals.dart';

class GtexCreatorDashboardScreenV2 extends StatefulWidget {
  const GtexCreatorDashboardScreenV2({super.key});

  @override
  State<GtexCreatorDashboardScreenV2> createState() =>
      _GtexCreatorDashboardScreenV2State();
}

class _GtexCreatorDashboardScreenV2State
    extends State<GtexCreatorDashboardScreenV2> {
  late final GtexCreatorSocialController controller;

  @override
  void initState() {
    super.initState();
    controller = GtexCreatorSocialController();
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder:
          (context, _) => Theme(
            data: Theme.of(context).copyWith(
              scaffoldBackgroundColor: gtexCreatorBg,
              textTheme: Theme.of(context).textTheme.apply(
                bodyColor: Colors.white,
                displayColor: Colors.white,
              ),
            ),
            child: Scaffold(
              backgroundColor: gtexCreatorBg,
              body: SafeArea(
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final isWide = constraints.maxWidth >= 760;
                    if (!isWide) return _MobileCreator(controller: controller);
                    return Row(
                      children: [
                        SizedBox(
                          width: 330,
                          child: _CreatorLeftPanel(controller: controller),
                        ),
                        Expanded(
                          child: _CreatorMainWorkspace(controller: controller),
                        ),
                      ],
                    );
                  },
                ),
              ),
            ),
          ),
    );
  }
}

class _CreatorLeftPanel extends StatelessWidget {
  const _CreatorLeftPanel({required this.controller});

  final GtexCreatorSocialController controller;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFF090F19),
        border: Border(right: BorderSide(color: Colors.white.withOpacity(.07))),
      ),
      child: ListView(
        children: [
          const Text(
            'Creator Studio',
            style: TextStyle(fontSize: 25, fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 4),
          Text(
            controller.snapshot.creatorHandle,
            style: const TextStyle(
              color: gtexCreatorGreen,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 18),
          ...GtexCreatorModule.values.map(
            (module) => _CreatorModuleTile(
              module: module,
              selected: controller.creatorModule == module,
              onTap: () => controller.selectCreatorModule(module),
            ),
          ),
          const SizedBox(height: 12),
          GtexPanel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const GtexPill(label: 'Creator health'),
                const SizedBox(height: 10),
                const Text(
                  'Ready to host, monetize, publish, and grow your football audience.',
                  style: TextStyle(color: gtexCreatorTextSoft),
                ),
                const SizedBox(height: 12),
                FilledButton.icon(
                  onPressed: () {},
                  icon: const Icon(Icons.add_rounded),
                  label: const Text('Create competition'),
                  style: FilledButton.styleFrom(
                    backgroundColor: gtexCreatorGreen,
                    foregroundColor: Colors.black,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _CreatorModuleTile extends StatelessWidget {
  const _CreatorModuleTile({
    required this.module,
    required this.selected,
    required this.onTap,
  });

  final GtexCreatorModule module;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final label = switch (module) {
      GtexCreatorModule.overview => 'Overview',
      GtexCreatorModule.competitions => 'Hosted competitions',
      GtexCreatorModule.monetization => 'Monetization',
      GtexCreatorModule.analytics => 'Analytics',
      GtexCreatorModule.profile => 'Creator profile',
      GtexCreatorModule.audience => 'Audience',
      GtexCreatorModule.shares => 'Creator shares',
    };
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          decoration: BoxDecoration(
            color:
                selected
                    ? gtexCreatorGreen.withOpacity(.12)
                    : Colors.transparent,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color:
                  selected
                      ? gtexCreatorGreen.withOpacity(.35)
                      : Colors.transparent,
            ),
          ),
          child: Row(
            children: [
              Icon(
                Icons.radio_button_checked_rounded,
                size: 16,
                color: selected ? gtexCreatorGreen : Colors.white38,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  label,
                  style: TextStyle(
                    color: selected ? Colors.white : Colors.white70,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CreatorMainWorkspace extends StatelessWidget {
  const _CreatorMainWorkspace({required this.controller});

  final GtexCreatorSocialController controller;

  @override
  Widget build(BuildContext context) {
    final snapshot = controller.snapshot;
    return SingleChildScrollView(
      padding: const EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      snapshot.creatorName,
                      style: const TextStyle(
                        fontSize: 34,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Host competitions, monetize football attention, grow community, and publish creator-led GTEX moments.',
                      style: TextStyle(color: gtexCreatorTextSoft),
                    ),
                  ],
                ),
              ),
              const GtexPill(label: 'Verified creator', color: gtexCreatorGold),
            ],
          ),
          const SizedBox(height: 18),
          GtexCreatorMetricGrid(metrics: snapshot.metrics),
          const SizedBox(height: 16),
          GtexCreatorCompetitionPanel(
            competitions: snapshot.competitions,
            revenueItems: snapshot.revenueItems,
          ),
        ],
      ),
    );
  }
}

class _MobileCreator extends StatelessWidget {
  const _MobileCreator({required this.controller});

  final GtexCreatorSocialController controller;

  @override
  Widget build(BuildContext context) {
    return _CreatorMainWorkspace(controller: controller);
  }
}
