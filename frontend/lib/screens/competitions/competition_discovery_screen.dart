import 'package:flutter/material.dart';

import '../../controllers/competition_controller.dart';
import '../../data/competition_api.dart';
import '../../data/gte_api_repository.dart';
import '../../models/competition_models.dart';
import '../../widgets/competitions/competition_status_badge.dart';
import '../../widgets/competitions/competition_visibility_chip.dart';
import '../../widgets/gte_metric_chip.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
import '../../widgets/gtex_branding.dart';
import 'competition_create_screen.dart';
import 'competition_detail_screen.dart';

class CompetitionDiscoveryScreen extends StatefulWidget {
  const CompetitionDiscoveryScreen({
    super.key,
    this.controller,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.backendMode = GteBackendMode.liveThenFixture,
    required this.currentUserId,
    this.currentUserName,
    this.isAuthenticated = false,
    this.onOpenLogin,
  });

  final CompetitionController? controller;
  final String baseUrl;
  final GteBackendMode backendMode;
  final String currentUserId;
  final String? currentUserName;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;

  @override
  State<CompetitionDiscoveryScreen> createState() => _CompetitionDiscoveryScreenState();
}

class _CompetitionDiscoveryScreenState extends State<CompetitionDiscoveryScreen> {
  late final CompetitionController _controller;
  late final bool _ownsController;
  late final TextEditingController _searchController;

  @override
  void initState() {
    super.initState();
    _ownsController = widget.controller == null;
    _controller = widget.controller ??
        CompetitionController(
          api: CompetitionApi.standard(baseUrl: widget.baseUrl, mode: widget.backendMode),
          currentUserId: widget.currentUserId,
          currentUserName: widget.currentUserName,
        );
    _searchController = TextEditingController(text: _controller.searchQuery);
    _searchController.addListener(_handleSearchChanged);
    _controller.bootstrap();
  }

  @override
  void didUpdateWidget(covariant CompetitionDiscoveryScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.currentUserId != widget.currentUserId || oldWidget.currentUserName != widget.currentUserName) {
      _controller.updateCurrentUser(userId: widget.currentUserId, userName: widget.currentUserName);
      _controller.loadDiscovery();
    }
  }

  @override
  void dispose() {
    _searchController
      ..removeListener(_handleSearchChanged)
      ..dispose();
    if (_ownsController) {
      _controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (BuildContext context, Widget? child) {
        final List<CompetitionSummary> featured = _controller.visibleCompetitions.take(3).toList(growable: false);
        return RefreshIndicator(
          onRefresh: _controller.loadDiscovery,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
            children: <Widget>[
              GtexHeroBanner(
                eyebrow: 'LIVE MATCH CENTER',
                title: 'Fixtures, tournaments, and creator-hosted football nights with arena energy.',
                description: 'Competition mode is cinematic on purpose. It prioritizes stories, stakes, fixture flow, and watchability instead of looking like a market terminal.',
                accent: GteShellTheme.accentArena,
                chips: <Widget>[
                  GteMetricChip(label: 'Visible', value: _controller.visibleCompetitions.length.toString()),
                  GteMetricChip(
                    label: 'Hosted by you',
                    value: _controller.competitions.where((CompetitionSummary item) => item.creatorId == _controller.currentUserId).length.toString(),
                  ),
                  GteMetricChip(
                    label: 'Arena pass',
                    value: widget.isAuthenticated ? 'LIVE' : 'PREVIEW',
                    positive: widget.isAuthenticated,
                  ),
                ],
                actions: <Widget>[
                  FilledButton.icon(
                    onPressed: _openCreateFlow,
                    icon: const Icon(Icons.add),
                    label: const Text('Create competition'),
                  ),
                  if (!widget.isAuthenticated && widget.onOpenLogin != null)
                    FilledButton.tonal(
                      onPressed: widget.onOpenLogin,
                      child: const Text('Sign in for live publish'),
                    ),
                ],
                sidePanel: Column(
                  children: <Widget>[
                    TextField(
                      controller: _searchController,
                      decoration: InputDecoration(
                        hintText: 'Search creator competition, skill league, or skill cup',
                        prefixIcon: const Icon(Icons.search),
                        suffixIcon: _searchController.text.trim().isEmpty
                            ? null
                            : IconButton(onPressed: _searchController.clear, icon: const Icon(Icons.close)),
                      ),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: <Widget>[
                        Expanded(
                          child: _ArenaSignalTile(
                            label: 'Featured fixture',
                            value: featured.isEmpty ? 'QUEUEING' : 'SPOTLIT',
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: _ArenaSignalTile(
                            label: 'Publish state',
                            value: widget.isAuthenticated ? 'OPEN' : 'LOCKED',
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              if (featured.isNotEmpty) ...<Widget>[
                const GtexSectionHeader(
                  eyebrow: 'FEATURED NOW',
                  title: 'The headline fixtures and hosted competitions worth opening first.',
                  description: 'The live match center leads with story, stakes, and watchability. Featured cards are meant to feel like floodlights, not filters.',
                  accent: GteShellTheme.accentArena,
                ),
                const SizedBox(height: 14),
                SizedBox(
                  height: 196,
                  child: ListView.separated(
                    scrollDirection: Axis.horizontal,
                    itemCount: featured.length,
                    separatorBuilder: (_, __) => const SizedBox(width: 12),
                    itemBuilder: (BuildContext context, int index) {
                      final CompetitionSummary item = featured[index];
                      return SizedBox(width: 320, child: _FeaturedArenaCard(competition: item, onOpen: () => _openCompetition(item.id)));
                    },
                  ),
                ),
              ],
              const SizedBox(height: 20),
              const GtexSectionHeader(
                eyebrow: 'ARENA BROWSE',
                title: 'Filter competitions by mood, format, and creator energy.',
                description: 'Browse stays cinematic, but the information architecture is cleaner now. Status, access, and joinability should land in one glance.',
                accent: GteShellTheme.accentArena,
              ),
              const SizedBox(height: 14),
              _SectionPicker(current: _controller.section, onChanged: _controller.setSection),
              const SizedBox(height: 20),
              if (_controller.discoveryError != null && _controller.competitions.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(bottom: 16),
                  child: GteSurfacePanel(
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        const Icon(Icons.info_outline),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            'Showing the last successful competition feed. ${_controller.discoveryError!}',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              if (_controller.isLoadingDiscovery && _controller.competitions.isEmpty)
                const GteSurfacePanel(
                  accentColor: GteShellTheme.accentArena,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      GtexSectionBadge(label: 'BUILDING THE ARENA BOARD', color: GteShellTheme.accentArena),
                      SizedBox(height: 14),
                      LinearProgressIndicator(),
                      SizedBox(height: 14),
                      Text('Refreshing featured fixtures, creator competitions, and the latest join windows so the live match center opens with a crisp card stack.'),
                    ],
                  ),
                )
              else if (_controller.discoveryError != null && _controller.competitions.isEmpty)
                GteStatePanel(
                  title: 'Competition discovery unavailable',
                  message: 'The live match center could not confirm a fresh arena board. ${_controller.discoveryError!}',
                  actionLabel: 'Retry arena feed',
                  onAction: _controller.loadDiscovery,
                  icon: Icons.groups_outlined,
                )
              else if (_controller.visibleCompetitions.isEmpty)
                GteStatePanel(
                  title: 'No competitions match this arena view',
                  message: 'Try a different section or clear the search to pull more creator competitions into the spotlight.',
                  actionLabel: _searchController.text.trim().isEmpty ? 'Reset arena browse' : 'Clear search',
                  onAction: () {
                    if (_searchController.text.trim().isNotEmpty) {
                      _searchController.clear();
                    }
                    _controller.setSection(CompetitionDiscoverySection.trending);
                  },
                  icon: Icons.search_off,
                )
              else
                ..._controller.visibleCompetitions.map(
                  (CompetitionSummary item) => Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: _CompetitionDiscoveryCard(competition: item, onOpen: () => _openCompetition(item.id)),
                  ),
                ),
            ],
          ),
        );
      },
    );
  }

  void _handleSearchChanged() {
    _controller.setSearchQuery(_searchController.text);
    if (mounted) {
      setState(() {});
    }
  }

  Future<void> _openCompetition(String competitionId) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(builder: (BuildContext context) => CompetitionDetailScreen(controller: _controller, competitionId: competitionId)),
    );
  }

  Future<void> _openCreateFlow() async {
    _controller.startNewDraft();
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(builder: (BuildContext context) => CompetitionCreateScreen(controller: _controller)),
    );
  }
}

class _SectionPicker extends StatelessWidget {
  const _SectionPicker({required this.current, required this.onChanged});

  final CompetitionDiscoverySection current;
  final ValueChanged<CompetitionDiscoverySection> onChanged;

  @override
  Widget build(BuildContext context) {
    const List<MapEntry<CompetitionDiscoverySection, String>> sections = <MapEntry<CompetitionDiscoverySection, String>>[
      MapEntry<CompetitionDiscoverySection, String>(CompetitionDiscoverySection.trending, 'Trending'),
      MapEntry<CompetitionDiscoverySection, String>(CompetitionDiscoverySection.newest, 'New'),
      MapEntry<CompetitionDiscoverySection, String>(CompetitionDiscoverySection.freeToJoin, 'Free to join'),
      MapEntry<CompetitionDiscoverySection, String>(CompetitionDiscoverySection.paid, 'Paid competitions'),
      MapEntry<CompetitionDiscoverySection, String>(CompetitionDiscoverySection.creator, 'Creator competitions'),
      MapEntry<CompetitionDiscoverySection, String>(CompetitionDiscoverySection.leagues, 'Leagues'),
      MapEntry<CompetitionDiscoverySection, String>(CompetitionDiscoverySection.cups, 'Cups'),
    ];

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: sections.map((MapEntry<CompetitionDiscoverySection, String> item) {
          final bool selected = current == item.key;
          return Padding(
            padding: const EdgeInsets.only(right: 10),
            child: Material(
              color: Colors.transparent,
              child: ChoiceChip(selected: selected, label: Text(item.value), onSelected: (_) => onChanged(item.key)),
            ),
          );
        }).toList(growable: false),
      ),
    );
  }
}

class _FeaturedArenaCard extends StatelessWidget {
  const _FeaturedArenaCard({required this.competition, required this.onOpen});

  final CompetitionSummary competition;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      onTap: onOpen,
      emphasized: true,
      accentColor: GteShellTheme.accentArena,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              CompetitionStatusBadge(status: competition.status),
              const Spacer(),
              CompetitionVisibilityChip(visibility: competition.visibility),
            ],
          ),
          const Spacer(),
          Text(competition.name, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text('${competition.safeFormatLabel} • ${competition.creatorLabel}', style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 14),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              GteMetricChip(label: 'Entry', value: _formatAmount(competition.entryFee, competition.currency)),
              GteMetricChip(label: 'Prize', value: _formatAmount(competition.prizePool, competition.currency)),
            ],
          ),
        ],
      ),
    );
  }
}

class _CompetitionDiscoveryCard extends StatelessWidget {
  const _CompetitionDiscoveryCard({required this.competition, required this.onOpen});

  final CompetitionSummary competition;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      onTap: onOpen,
      accentColor: GteShellTheme.accentArena,
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
                    Text(competition.name, style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 6),
                    Text('${competition.safeFormatLabel} • Creator competition by ${competition.creatorLabel}', style: Theme.of(context).textTheme.bodyMedium),
                  ],
                ),
              ),
              const SizedBox(width: 16),
              CompetitionStatusBadge(status: competition.status),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              CompetitionVisibilityChip(visibility: competition.visibility),
              Chip(label: Text('Arena state: ${_statusLabel(competition.status)}')),
              Chip(label: Text(competition.joinEligibility.eligible ? 'Join window open' : 'Review eligibility')),
              if (competition.beginnerFriendly == true) const Chip(label: Text('Beginner friendly')),
            ],
          ),
          const SizedBox(height: 16),
          Text(competition.rulesSummary, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 16),
          Row(
            children: <Widget>[
              Expanded(child: _QuickStat(label: 'Entry fee', value: _formatAmount(competition.entryFee, competition.currency))),
              const SizedBox(width: 10),
              Expanded(child: _QuickStat(label: 'Prize pool', value: _formatAmount(competition.prizePool, competition.currency))),
              const SizedBox(width: 10),
              Expanded(child: _QuickStat(label: 'Players', value: '${competition.participantCount}/${competition.capacity}')),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: <Widget>[
              FilledButton.tonalIcon(onPressed: onOpen, icon: const Icon(Icons.open_in_new), label: const Text('Open arena')),
              const Spacer(),
              Text(competition.joinEligibility.eligible ? 'Open to join now' : 'Review rules and eligibility', style: Theme.of(context).textTheme.bodyMedium),
            ],
          ),
        ],
      ),
    );
  }

  String _statusLabel(CompetitionStatus value) {
    return value.name
        .replaceAllMapped(RegExp(r'([a-z])([A-Z])'), (Match match) => '${match.group(1)} ${match.group(2)}')
        .replaceAll('_', ' ');
  }
}

class _QuickStat extends StatelessWidget {
  const _QuickStat({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFF2A3A56)),
        color: Colors.white.withValues(alpha: 0.03),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 4),
          Text(value, style: Theme.of(context).textTheme.titleMedium),
        ],
      ),
    );
  }
}

class _ArenaSignalTile extends StatelessWidget {
  const _ArenaSignalTile({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        color: Colors.white.withValues(alpha: 0.04),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 6),
          Text(value, style: Theme.of(context).textTheme.titleMedium?.copyWith(color: GteShellTheme.accentArena)),
        ],
      ),
    );
  }
}

String _formatAmount(double value, String currency) {
  final bool whole = value == value.roundToDouble();
  final String number = value.toStringAsFixed(whole ? 0 : 2);
  if (currency.toLowerCase() == 'credit') {
    return '$number cr';
  }
  return '$number ${currency.toUpperCase()}';
}
