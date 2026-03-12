import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/screens/competitions/competition_create_screen.dart';
import 'package:gte_frontend/screens/competitions/competition_detail_screen.dart';
import 'package:gte_frontend/widgets/competitions/competition_status_badge.dart';
import 'package:gte_frontend/widgets/competitions/competition_visibility_chip.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

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
  State<CompetitionDiscoveryScreen> createState() =>
      _CompetitionDiscoveryScreenState();
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
          api: CompetitionApi.standard(
            baseUrl: widget.baseUrl,
            mode: widget.backendMode,
          ),
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
    if (oldWidget.currentUserId != widget.currentUserId ||
        oldWidget.currentUserName != widget.currentUserName) {
      _controller.updateCurrentUser(
        userId: widget.currentUserId,
        userName: widget.currentUserName,
      );
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
        return RefreshIndicator(
          onRefresh: _controller.loadDiscovery,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
            children: <Widget>[
              GteSurfacePanel(
                emphasized: true,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Community competitions',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Discover skill leagues and skill cups with clear entry fees, published rules, transparent payout, and secure escrow language.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 18),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: <Widget>[
                        GteMetricChip(
                          label: 'Visible',
                          value: _controller.visibleCompetitions.length.toString(),
                        ),
                        GteMetricChip(
                          label: 'Creator competitions',
                          value: _controller.competitions
                              .where((CompetitionSummary item) =>
                                  item.creatorId == _controller.currentUserId)
                              .length
                              .toString(),
                        ),
                        GteMetricChip(
                          label: 'Session',
                          value: widget.isAuthenticated ? 'LIVE' : 'DEMO',
                          positive: widget.isAuthenticated,
                        ),
                      ],
                    ),
                    const SizedBox(height: 18),
                    TextField(
                      controller: _searchController,
                      decoration: InputDecoration(
                        hintText:
                            'Search creator competition, skill league, or skill cup',
                        prefixIcon: const Icon(Icons.search),
                        suffixIcon: _searchController.text.trim().isEmpty
                            ? null
                            : IconButton(
                                onPressed: () {
                                  _searchController.clear();
                                },
                                icon: const Icon(Icons.close),
                              ),
                      ),
                    ),
                    const SizedBox(height: 18),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: <Widget>[
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
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              _SectionPicker(
                current: _controller.section,
                onChanged: _controller.setSection,
              ),
              const SizedBox(height: 20),
              if (_controller.discoveryError != null &&
                  _controller.competitions.isNotEmpty)
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
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 48),
                  child: Center(child: CircularProgressIndicator()),
                )
              else if (_controller.discoveryError != null &&
                  _controller.competitions.isEmpty)
                GteStatePanel(
                  title: 'Competition discovery unavailable',
                  message: _controller.discoveryError!,
                  actionLabel: 'Retry',
                  onAction: _controller.loadDiscovery,
                  icon: Icons.groups_outlined,
                )
              else if (_controller.visibleCompetitions.isEmpty)
                GteStatePanel(
                  title: 'No competitions found',
                  message:
                      'Try a different section or clear the search to explore more creator competitions.',
                  actionLabel: _searchController.text.trim().isEmpty
                      ? null
                      : 'Clear search',
                  onAction: _searchController.text.trim().isEmpty
                      ? null
                      : () {
                          _searchController.clear();
                        },
                  icon: Icons.search_off,
                )
              else
                ..._controller.visibleCompetitions.map(
                  (CompetitionSummary item) => Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: _CompetitionDiscoveryCard(
                      competition: item,
                      onOpen: () => _openCompetition(item.id),
                    ),
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
  }

  Future<void> _openCompetition(String competitionId) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => CompetitionDetailScreen(
          controller: _controller,
          competitionId: competitionId,
        ),
      ),
    );
  }

  Future<void> _openCreateFlow() async {
    _controller.startNewDraft();
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => CompetitionCreateScreen(
          controller: _controller,
        ),
      ),
    );
  }
}

class _SectionPicker extends StatelessWidget {
  const _SectionPicker({
    required this.current,
    required this.onChanged,
  });

  final CompetitionDiscoverySection current;
  final ValueChanged<CompetitionDiscoverySection> onChanged;

  @override
  Widget build(BuildContext context) {
    const List<MapEntry<CompetitionDiscoverySection, String>> sections =
        <MapEntry<CompetitionDiscoverySection, String>>[
      MapEntry<CompetitionDiscoverySection, String>(
        CompetitionDiscoverySection.trending,
        'Trending',
      ),
      MapEntry<CompetitionDiscoverySection, String>(
        CompetitionDiscoverySection.newest,
        'New',
      ),
      MapEntry<CompetitionDiscoverySection, String>(
        CompetitionDiscoverySection.freeToJoin,
        'Free to join',
      ),
      MapEntry<CompetitionDiscoverySection, String>(
        CompetitionDiscoverySection.paid,
        'Paid competitions',
      ),
      MapEntry<CompetitionDiscoverySection, String>(
        CompetitionDiscoverySection.creator,
        'Creator competitions',
      ),
      MapEntry<CompetitionDiscoverySection, String>(
        CompetitionDiscoverySection.leagues,
        'Leagues',
      ),
      MapEntry<CompetitionDiscoverySection, String>(
        CompetitionDiscoverySection.cups,
        'Cups',
      ),
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
              child: ChoiceChip(
                selected: selected,
                label: Text(item.value),
                onSelected: (_) => onChanged(item.key),
              ),
            ),
          );
        }).toList(growable: false),
      ),
    );
  }
}

class _CompetitionDiscoveryCard extends StatelessWidget {
  const _CompetitionDiscoveryCard({
    required this.competition,
    required this.onOpen,
  });

  final CompetitionSummary competition;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      onTap: onOpen,
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
                      competition.name,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      '${competition.safeFormatLabel} • Creator competition by ${competition.creatorLabel}',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
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
              Material(
                color: Colors.transparent,
                child: Chip(
                  label: Text('Contest status: ${_statusLabel(competition.status)}'),
                ),
              ),
              if (competition.beginnerFriendly == true)
                const Material(
                  color: Colors.transparent,
                  child: Chip(label: Text('Beginner friendly')),
                ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            competition.rulesSummary,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              _QuickStat(
                label: 'Entry fee',
                value: _formatAmount(competition.entryFee, competition.currency),
              ),
              _QuickStat(
                label: 'Prize pool',
                value: _formatAmount(competition.prizePool, competition.currency),
              ),
              _QuickStat(
                label: 'Players',
                value: '${competition.participantCount}/${competition.capacity}',
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: <Widget>[
              FilledButton.tonalIcon(
                onPressed: onOpen,
                icon: const Icon(Icons.open_in_new),
                label: const Text('View'),
              ),
              const Spacer(),
              Text(
                competition.joinEligibility.eligible
                    ? 'Open to join'
                    : 'Review details',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _statusLabel(CompetitionStatus value) {
    return value.name
        .replaceAllMapped(RegExp(r'([a-z])([A-Z])'), (Match match) {
          return '${match.group(1)} ${match.group(2)}';
        })
        .replaceAll('_', ' ');
  }
}

class _QuickStat extends StatelessWidget {
  const _QuickStat({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFF2A3A56)),
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

String _formatAmount(double value, String currency) {
  final bool whole = value == value.roundToDouble();
  final String number = value.toStringAsFixed(whole ? 0 : 2);
  if (currency.toLowerCase() == 'credit') {
    return '$number cr';
  }
  return '$number ${currency.toUpperCase()}';
}
