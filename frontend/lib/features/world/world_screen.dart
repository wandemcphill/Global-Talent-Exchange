import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/app_breakpoints.dart';
import '../../core/constants/app_spacing.dart';
import '../../shared/providers/regen_provider.dart';
import '../../shared/widgets/metric_pill.dart';
import '../../shared/widgets/section_heading.dart';
import 'widgets/world_screen_widgets.dart';

class WorldScreen extends ConsumerStatefulWidget {
  const WorldScreen({super.key});

  @override
  ConsumerState<WorldScreen> createState() => _WorldScreenState();
}

class _WorldScreenState extends ConsumerState<WorldScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  final Set<WorldTab> _loadedTabs = <WorldTab>{};
  final Set<WorldTab> _loadingTabs = <WorldTab>{};
  final Set<String> _joinedFederations = <String>{};
  final Map<WorldTab, Timer> _loadTimers = <WorldTab, Timer>{};

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: WorldTab.values.length, vsync: this);
    _tabController.addListener(_handleTabChanged);

    WidgetsBinding.instance.addPostFrameCallback((_) {
      _ensureTabLoaded(WorldTab.values[_tabController.index]);
    });
  }

  @override
  void dispose() {
    _tabController.removeListener(_handleTabChanged);
    _tabController.dispose();

    for (final Timer timer in _loadTimers.values) {
      timer.cancel();
    }

    super.dispose();
  }

  void _handleTabChanged() {
    _ensureTabLoaded(WorldTab.values[_tabController.index]);
  }

  void _ensureTabLoaded(WorldTab tab) {
    if (_loadedTabs.contains(tab) || _loadingTabs.contains(tab)) {
      return;
    }

    setState(() => _loadingTabs.add(tab));

    final int index = WorldTab.values.indexOf(tab);
    _loadTimers[tab]?.cancel();
    _loadTimers[tab] = Timer(Duration(milliseconds: 360 + (index * 140)), () {
      if (!mounted) {
        return;
      }

      setState(() {
        _loadingTabs.remove(tab);
        _loadedTabs.add(tab);
      });
    });
  }

  void _joinFederation(String federationName) {
    if (_joinedFederations.contains(federationName)) {
      return;
    }

    setState(() => _joinedFederations.add(federationName));
  }

  @override
  Widget build(BuildContext context) {
    final regens = ref.watch(regenProvider);
    final competitions = ref.watch(competitionsProvider);
    final history = ref.watch(historyProvider);
    final federations = ref.watch(federationsProvider);

    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final double horizontalPadding =
            constraints.maxWidth >= AppBreakpoints.medium
                ? spacingLG
                : spacingMD;
        final double bottomPadding = MediaQuery.paddingOf(context).bottom + 88;

        return Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1440),
            child: Padding(
              padding: EdgeInsets.fromLTRB(
                horizontalPadding,
                spacingLG,
                horizontalPadding,
                0,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  const SectionHeading(
                    title: 'World',
                    subtitle:
                        'Regens, competitions, global history, and federation activity in one live world feed.',
                    trailing: MetricPill(
                      label: 'Coverage',
                      value: 'Global',
                      highlight: true,
                    ),
                  ),
                  const SizedBox(height: spacingLG),
                  WorldTabBar(
                    controller: _tabController,
                    onTap:
                        (int index) => _ensureTabLoaded(WorldTab.values[index]),
                  ),
                  const SizedBox(height: spacingLG),
                  Expanded(
                    child: TabBarView(
                      controller: _tabController,
                      physics: const BouncingScrollPhysics(
                        parent: AlwaysScrollableScrollPhysics(),
                      ),
                      children: <Widget>[
                        WorldTabStatePanel(
                          tab: WorldTab.regens,
                          loading: _loadingTabs.contains(WorldTab.regens),
                          isEmpty: regens.isEmpty,
                          loadingLabel: 'Loading regen pathways',
                          emptyTitle: 'No regen prospects found',
                          emptyBody:
                              'The global scouting stream is quiet for this cycle.',
                          emptyIcon: Icons.auto_awesome_rounded,
                          child: RegensGrid(
                            regens: regens,
                            bottomPadding: bottomPadding,
                          ),
                        ),
                        WorldTabStatePanel(
                          tab: WorldTab.competitions,
                          loading: _loadingTabs.contains(WorldTab.competitions),
                          isEmpty: competitions.isEmpty,
                          loadingLabel: 'Loading competition banners',
                          emptyTitle: 'No live competitions',
                          emptyBody:
                              'No world events are currently broadcasting into this feed.',
                          emptyIcon: Icons.emoji_events_rounded,
                          child: CompetitionsList(
                            competitions: competitions,
                            bottomPadding: bottomPadding,
                          ),
                        ),
                        WorldTabStatePanel(
                          tab: WorldTab.history,
                          loading: _loadingTabs.contains(WorldTab.history),
                          isEmpty: history.isEmpty,
                          loadingLabel: 'Loading historical archive',
                          emptyTitle: 'No historical records',
                          emptyBody:
                              'The archive has not surfaced any world records yet.',
                          emptyIcon: Icons.history_edu_rounded,
                          child: HistoryRecordsList(
                            records: history,
                            bottomPadding: bottomPadding,
                          ),
                        ),
                        WorldTabStatePanel(
                          tab: WorldTab.federations,
                          loading: _loadingTabs.contains(WorldTab.federations),
                          isEmpty: federations.isEmpty,
                          loadingLabel: 'Loading federation network',
                          emptyTitle: 'No federations available',
                          emptyBody:
                              'There are no federation alliances ready to join right now.',
                          emptyIcon: Icons.public_rounded,
                          child: FederationsList(
                            federations: federations,
                            joinedFederations: _joinedFederations,
                            onJoin: _joinFederation,
                            bottomPadding: bottomPadding,
                          ),
                        ),
                      ],
                    ),
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
