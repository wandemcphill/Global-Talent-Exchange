import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_feedback.dart';
import '../../core/constants/app_spacing.dart';
import '../../features/app_routes/gte_route_data.dart';
import '../../features/build_a_son/build_a_son.dart';
import '../../models/regen_creation_models.dart';
import '../../models/regen_universe_models.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/providers/regen_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import '../../shared/widgets/gtex_premium_panels.dart';
import '../../widgets/football_player_card.dart';
import '../../widgets/gte_state_panel.dart';

class RegensScreen extends ConsumerWidget {
  const RegensScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<RegenUniverseHubData> value = ref.watch(
      regenUniverseHubProvider,
    );
    final bool authenticated = ref.watch(isAuthenticatedProvider);
    return AppPageLayout(
      title: 'Scout Prospects',
      subtitle:
          'Scout rising prospects, national-pool depth, form, potential, and club-building stories.',
      trailing: DataSourceBadge(
        status:
            value.hasError ? DataSourceStatus.blocked : DataSourceStatus.live,
      ),
      children: <Widget>[
        value.when(
          data:
              (RegenUniverseHubData data) => Column(
                children: <Widget>[
                  _Hero(
                    data: data,
                    authenticated: authenticated,
                    onOpenBuildASon:
                        authenticated ? () => _openBuildASon(context) : null,
                  ),
                  const SizedBox(height: spacingMD),
                  _RegenWorldDiscoveryPanel(data: data),
                  const SizedBox(height: spacingMD),
                  _BloodlinesPanel(bloodlines: data.bloodlines),
                  const SizedBox(height: spacingMD),
                  _AwardsPanel(awards: data.awards),
                  const SizedBox(height: spacingMD),
                  _NationalPoolPanel(nationalRegens: data.nationalRegens),
                  const SizedBox(height: spacingMD),
                  _RisingStarsPanel(stars: data.risingStars),
                  const SizedBox(height: spacingMD),
                  _RequestedSonsPanel(
                    authenticated: authenticated,
                    orders: data.requestedSonOrders,
                  ),
                  const SizedBox(height: spacingMD),
                  _ScoutingFeedPanel(items: data.scoutingFeed),
                  const SizedBox(height: spacingMD),
                  _TrackingPanel(tracking: data.tracking),
                ],
              ),
          loading:
              () => const GteStatePanel(
                eyebrow: 'SCOUT',
                title: 'Loading prospects',
                message:
                    'Syncing rising stars, awards, national-pool depth, and request-son orders.',
                icon: Icons.auto_awesome_rounded,
                isLoading: true,
              ),
          error:
              (Object error, StackTrace stackTrace) => GteStatePanel(
                eyebrow: 'SCOUT',
                title: 'Prospect scouting is blocked',
                message: AppFeedback.messageFor(
                  error,
                  fallback: 'Live prospect scouting is unavailable right now.',
                ),
                icon: Icons.warning_amber_rounded,
              ),
        ),
      ],
    );
  }
}

class _Hero extends StatelessWidget {
  const _Hero({
    required this.data,
    required this.authenticated,
    this.onOpenBuildASon,
  });

  final RegenUniverseHubData data;
  final bool authenticated;
  final VoidCallback? onOpenBuildASon;

  @override
  Widget build(BuildContext context) {
    return GtexHeroPanel(
      eyebrow: 'LIVE TALENT MAP',
      title: 'Scout the next wave of football talent.',
      description:
          'Review ratings, form, potential, national-pool depth, and request-son prospects with clean football card visuals.',
      metrics: <Widget>[
        _MetricChip(
          label: 'Awards',
          value: '${data.awards.length}',
          tone: GtexSurfaceTone.warning,
        ),
        _MetricChip(
          label: 'National pool',
          value: '${data.nationalRegens.length}',
          tone: GtexSurfaceTone.info,
        ),
        _MetricChip(
          label: 'Rising stars',
          value: '${data.risingStars.length}',
          tone: GtexSurfaceTone.live,
        ),
        _MetricChip(
          label: 'Requested sons',
          value:
              authenticated
                  ? '${data.generatedRequestedSons.length}'
                  : 'Sign in',
          tone: GtexSurfaceTone.success,
        ),
      ],
      actions: <Widget>[
        FilledButton.icon(
          onPressed: onOpenBuildASon,
          icon: const Icon(Icons.family_restroom_rounded),
          label: const Text('Build-a-Son'),
        ),
        OutlinedButton.icon(
          onPressed: null,
          icon: const Icon(Icons.account_tree_rounded),
          label: const Text('Lineage map'),
        ),
      ],
    );
  }
}

void _openBuildASon(BuildContext context) {
  final String location = const RegenBuildASonRouteData().toUri().toString();
  if (GoRouter.maybeOf(context) != null) {
    context.push(location);
    return;
  }
  Navigator.of(context).push<void>(
    MaterialPageRoute<void>(
      settings: const RouteSettings(name: '/world/regens/build-a-son'),
      builder: (BuildContext context) => const BuildASonScreen(),
    ),
  );
}

enum _GenerationFilter { all, gen1, gen2, gen3 }

enum _RegenSort { potential, value, newest }

class _RegenWorldDiscoveryPanel extends StatefulWidget {
  const _RegenWorldDiscoveryPanel({required this.data});

  final RegenUniverseHubData data;

  @override
  State<_RegenWorldDiscoveryPanel> createState() =>
      _RegenWorldDiscoveryPanelState();
}

class _RegenWorldDiscoveryPanelState extends State<_RegenWorldDiscoveryPanel> {
  final TextEditingController _searchController = TextEditingController();
  _GenerationFilter _generationFilter = _GenerationFilter.all;
  String _positionFilter = 'all';
  String _nationalityFilter = 'all';
  String _rarityFilter = 'all';
  _RegenSort _sort = _RegenSort.potential;
  String? _selectedId;

  @override
  void initState() {
    super.initState();
    _searchController.addListener(_onSearchChanged);
  }

  @override
  void dispose() {
    _searchController
      ..removeListener(_onSearchChanged)
      ..dispose();
    super.dispose();
  }

  void _onSearchChanged() {
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final List<_RegenWorldEntry> entries = _buildRegenWorldEntries(widget.data);
    final List<String> positions = <String>{
      for (final _RegenWorldEntry entry in entries)
        if (entry.position.trim().isNotEmpty) entry.position,
    }.toList(growable: false)..sort();
    final List<String> nationalities = <String>{
      for (final _RegenWorldEntry entry in entries)
        if (entry.nationality.trim().isNotEmpty) entry.nationality,
    }.toList(growable: false)..sort();
    final List<String> rarities = <String>{
      for (final _RegenWorldEntry entry in entries)
        if ((entry.rarityTier ?? '').trim().isNotEmpty)
          entry.rarityTier!.trim(),
    }.toList(growable: false)..sort();
    final List<_RegenWorldEntry> filtered = _filteredEntries(entries);
    final int eliteCount =
        entries.where((_RegenWorldEntry entry) => entry.potential >= 80).length;
    final int gen3Count =
        entries
            .where((_RegenWorldEntry entry) => entry.generationNumber == 3)
            .length;
    final int syncPendingCount =
        entries
            .where((_RegenWorldEntry entry) => !entry.hasBackendTruth)
            .length;

    return GtexSectionPanel(
      title: 'Regen World',
      subtitle:
          'Discovery, lineage, traits, DNA, value, rarity, and nationality from backend regen feeds only.',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Wrap(
            spacing: spacingSM,
            runSpacing: spacingSM,
            children: <Widget>[
              _MetricChip(
                label: 'Discovered',
                value: '${entries.length}',
                tone: GtexSurfaceTone.live,
              ),
              _MetricChip(
                label: 'Elite POT 80+',
                value: '$eliteCount',
                tone: GtexSurfaceTone.warning,
              ),
              _MetricChip(
                label: 'GEN-3 rare',
                value: '$gen3Count',
                tone: GtexSurfaceTone.info,
              ),
              _MetricChip(
                label: 'Sync pending',
                value: '$syncPendingCount',
                tone:
                    syncPendingCount == 0
                        ? GtexSurfaceTone.success
                        : GtexSurfaceTone.warning,
              ),
            ],
          ),
          const SizedBox(height: spacingMD),
          TextField(
            controller: _searchController,
            decoration: const InputDecoration(
              prefixIcon: Icon(Icons.search_rounded),
              labelText: 'Search regens',
              hintText: 'Search regens by name, trait, or position...',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: spacingSM),
          Wrap(
            spacing: spacingSM,
            runSpacing: spacingSM,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: <Widget>[
              for (final _GenerationFilter filter in _GenerationFilter.values)
                ChoiceChip(
                  label: Text(_generationLabel(filter)),
                  selected: _generationFilter == filter,
                  onSelected:
                      (_) => setState(() {
                        _generationFilter = filter;
                      }),
                ),
              DropdownButton<String>(
                value:
                    positions.contains(_positionFilter)
                        ? _positionFilter
                        : 'all',
                items: <DropdownMenuItem<String>>[
                  const DropdownMenuItem<String>(
                    value: 'all',
                    child: Text('All Positions'),
                  ),
                  for (final String position in positions)
                    DropdownMenuItem<String>(
                      value: position,
                      child: Text(position),
                    ),
                ],
                onChanged:
                    (String? value) => setState(() {
                      _positionFilter = value ?? 'all';
                    }),
              ),
              DropdownButton<String>(
                value:
                    nationalities.contains(_nationalityFilter)
                        ? _nationalityFilter
                        : 'all',
                items: <DropdownMenuItem<String>>[
                  const DropdownMenuItem<String>(
                    value: 'all',
                    child: Text('All Nationalities'),
                  ),
                  for (final String nationality in nationalities)
                    DropdownMenuItem<String>(
                      value: nationality,
                      child: Text(nationality),
                    ),
                ],
                onChanged:
                    (String? value) => setState(() {
                      _nationalityFilter = value ?? 'all';
                    }),
              ),
              DropdownButton<String>(
                value: rarities.contains(_rarityFilter) ? _rarityFilter : 'all',
                items: <DropdownMenuItem<String>>[
                  const DropdownMenuItem<String>(
                    value: 'all',
                    child: Text('All Rarities'),
                  ),
                  for (final String rarity in rarities)
                    DropdownMenuItem<String>(
                      value: rarity,
                      child: Text(rarity),
                    ),
                ],
                onChanged:
                    (String? value) => setState(() {
                      _rarityFilter = value ?? 'all';
                    }),
              ),
              DropdownButton<_RegenSort>(
                value: _sort,
                items: const <DropdownMenuItem<_RegenSort>>[
                  DropdownMenuItem<_RegenSort>(
                    value: _RegenSort.potential,
                    child: Text('Sort: Potential'),
                  ),
                  DropdownMenuItem<_RegenSort>(
                    value: _RegenSort.value,
                    child: Text('Sort: Value'),
                  ),
                  DropdownMenuItem<_RegenSort>(
                    value: _RegenSort.newest,
                    child: Text('Sort: Newest'),
                  ),
                ],
                onChanged:
                    (_RegenSort? value) => setState(() {
                      _sort = value ?? _RegenSort.potential;
                    }),
              ),
            ],
          ),
          const SizedBox(height: spacingMD),
          if (filtered.isEmpty)
            GteStatePanel(
              eyebrow: 'REGEN WORLD',
              title: 'No Regens Found',
              message:
                  'No backend regen records match the current filters. Clear filters to inspect the full synced pool.',
              icon: Icons.search_off_rounded,
              actionLabel: 'Show all',
              onAction: _clearFilters,
            )
          else
            Column(
              children: filtered
                  .map(
                    (_RegenWorldEntry entry) => Padding(
                      padding: const EdgeInsets.only(bottom: spacingSM),
                      child: _RegenWorldEntryCard(
                        entry: entry,
                        selected: _selectedId == entry.id,
                        onToggle:
                            () => setState(() {
                              _selectedId =
                                  _selectedId == entry.id ? null : entry.id;
                            }),
                      ),
                    ),
                  )
                  .toList(growable: false),
            ),
          const SizedBox(height: spacingSM),
          const Text(
            'GEN-1 regens are first generation. GEN-2 and GEN-3 records inherit compounded traits only when the backend publishes lineage truth.',
          ),
        ],
      ),
    );
  }

  List<_RegenWorldEntry> _filteredEntries(List<_RegenWorldEntry> entries) {
    final String query = _searchController.text.trim().toLowerCase();
    final List<_RegenWorldEntry> filtered = entries
        .where((_RegenWorldEntry entry) {
          if (_generationFilter != _GenerationFilter.all &&
              entry.generationNumber != _generationNumber(_generationFilter)) {
            return false;
          }
          if (_positionFilter != 'all' && entry.position != _positionFilter) {
            return false;
          }
          if (_nationalityFilter != 'all' &&
              entry.nationality != _nationalityFilter) {
            return false;
          }
          if (_rarityFilter != 'all' && entry.rarityTier != _rarityFilter) {
            return false;
          }
          if (query.isEmpty) {
            return true;
          }
          return entry.searchableValues.any(
            (String value) => value.toLowerCase().contains(query),
          );
        })
        .toList(growable: false);
    switch (_sort) {
      case _RegenSort.potential:
        filtered.sort(
          (_RegenWorldEntry left, _RegenWorldEntry right) =>
              right.potential.compareTo(left.potential),
        );
        break;
      case _RegenSort.value:
        filtered.sort(
          (_RegenWorldEntry left, _RegenWorldEntry right) =>
              (right.projectedValueCoin ?? -1).compareTo(
                left.projectedValueCoin ?? -1,
              ),
        );
        break;
      case _RegenSort.newest:
        filtered.sort(
          (_RegenWorldEntry left, _RegenWorldEntry right) =>
              right.createdAt.compareTo(left.createdAt),
        );
        break;
    }
    return filtered;
  }

  void _clearFilters() {
    setState(() {
      _searchController.clear();
      _generationFilter = _GenerationFilter.all;
      _positionFilter = 'all';
      _nationalityFilter = 'all';
      _rarityFilter = 'all';
      _sort = _RegenSort.potential;
    });
  }
}

class _RegenWorldEntryCard extends StatelessWidget {
  const _RegenWorldEntryCard({
    required this.entry,
    required this.selected,
    required this.onToggle,
  });

  final _RegenWorldEntry entry;
  final bool selected;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) {
    final String positionLabel =
        entry.position.trim().isEmpty ? 'Position pending' : entry.position;
    final String nationalityLabel =
        entry.nationality.trim().isEmpty
            ? 'Nationality pending'
            : entry.nationality;
    final String truthMessage =
        entry.hasBackendTruth
            ? 'Backend truth complete'
            : 'Missing backend truth: ${entry.missingFields.join(', ')}';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        InkWell(
          borderRadius: BorderRadius.circular(8),
          onTap: onToggle,
          child: GtexListTile(
            title: '${entry.name} / ${entry.generationLabel ?? 'GEN pending'}',
            subtitle:
                '$positionLabel / $nationalityLabel / ${entry.originStory ?? 'Origin story not published'}\n'
                'POT ${entry.potential} / ${entry.projectedValueLabel} / ${entry.rarityTier ?? 'Rarity not published'}\n'
                '${entry.syncStateLabel} / $truthMessage',
            leadingIcon:
                entry.hasBackendTruth
                    ? Icons.auto_awesome_rounded
                    : Icons.sync_problem_rounded,
            tone: entry.surfaceTone,
            trailing: SizedBox(
              width: 280,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  if (entry.dnaProfile == null)
                    const Text('DNA not published')
                  else
                    _DnaIntegritySegments(profile: entry.dnaProfile!),
                  const SizedBox(height: spacingXS),
                  _BadgeWrap(
                    labels: <String>[
                      if (!entry.hasBackendTruth) entry.syncStateLabel,
                      ...entry.traits.take(3),
                      if (entry.traits.length > 3)
                        '+${entry.traits.length - 3}',
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
        if (selected) _RegenWorldDetail(entry: entry),
      ],
    );
  }
}

class _RegenWorldDetail extends StatelessWidget {
  const _RegenWorldDetail({required this.entry});

  final _RegenWorldEntry entry;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: spacingSM),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Backend Sync', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: spacingXS),
          Text(
            entry.hasBackendTruth
                ? 'Backend truth complete.'
                : '${entry.syncStateLabel}: missing ${entry.missingFields.join(', ')}.',
          ),
          const SizedBox(height: spacingSM),
          Text('DNA Breakdown', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: spacingXS),
          if (entry.dnaProfile == null)
            const Text('DNA not published by backend.')
          else
            for (final String code in regenDnaStatCodes)
              _DnaBar(label: code, value: entry.dnaProfile!.valueFor(code)),
          const SizedBox(height: spacingSM),
          Text('Traits', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: spacingXS),
          _BadgeWrap(labels: entry.traits),
          const SizedBox(height: spacingSM),
          Text('Lineage Tree', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: spacingXS),
          Text(
            entry.lineage.isEmpty
                ? 'Lineage not published by backend.'
                : entry.lineage.join(' -> '),
          ),
          const SizedBox(height: spacingSM),
          Text('Origin Story', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: spacingXS),
          Text(entry.originStory ?? 'Origin story not published by backend.'),
        ],
      ),
    );
  }
}

class _DnaIntegritySegments extends StatelessWidget {
  const _DnaIntegritySegments({required this.profile});

  final RegenDnaProfile profile;

  @override
  Widget build(BuildContext context) {
    final int average =
        regenDnaStatCodes
            .map(profile.valueFor)
            .fold<int>(0, (int sum, int value) => sum + value) ~/
        regenDnaStatCodes.length;
    final int filled = (average.clamp(0, 99) / 10).ceil().clamp(1, 10);
    return Row(
      mainAxisAlignment: MainAxisAlignment.end,
      children: <Widget>[
        for (int index = 0; index < 10; index += 1)
          Container(
            width: 12,
            height: 6,
            margin: const EdgeInsets.only(left: 3),
            decoration: BoxDecoration(
              color:
                  index < filled
                      ? Theme.of(context).colorScheme.primary
                      : Theme.of(context).dividerColor.withValues(alpha: 0.28),
              borderRadius: BorderRadius.circular(999),
            ),
          ),
      ],
    );
  }
}

class _DnaBar extends StatelessWidget {
  const _DnaBar({required this.label, required this.value});

  final String label;
  final int value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: spacingXS),
      child: Row(
        children: <Widget>[
          SizedBox(width: 38, child: Text(label)),
          Expanded(
            child: LinearProgressIndicator(
              value: value.clamp(0, 99) / 99,
              minHeight: 7,
            ),
          ),
          const SizedBox(width: spacingSM),
          SizedBox(
            width: 32,
            child: Text('$value', textAlign: TextAlign.right),
          ),
        ],
      ),
    );
  }
}

class _RegenWorldEntry {
  const _RegenWorldEntry({
    required this.id,
    required this.name,
    required this.position,
    required this.nationality,
    required this.potential,
    required this.currentRating,
    required this.source,
    required this.createdAt,
    this.generationNumber,
    this.generationLabel,
    this.rarityTier,
    this.originStory,
    this.projectedValueCoin,
    this.traits = const <String>[],
    this.lineage = const <String>[],
    this.dnaProfile,
  });

  final String id;
  final String name;
  final String position;
  final String nationality;
  final int potential;
  final int currentRating;
  final String source;
  final DateTime createdAt;
  final int? generationNumber;
  final String? generationLabel;
  final String? rarityTier;
  final String? originStory;
  final int? projectedValueCoin;
  final List<String> traits;
  final List<String> lineage;
  final RegenDnaProfile? dnaProfile;

  bool get hasBackendTruth => missingFields.isEmpty;

  bool get hasBlockedBackendTruth => coreMissingFields.isNotEmpty;

  String get syncStateLabel {
    if (hasBackendTruth) {
      return 'Backend truth complete';
    }
    return hasBlockedBackendTruth
        ? 'Backend truth blocked'
        : 'Backend sync pending';
  }

  GtexSurfaceTone get surfaceTone {
    if (hasBackendTruth) {
      return GtexSurfaceTone.live;
    }
    return hasBlockedBackendTruth
        ? GtexSurfaceTone.danger
        : GtexSurfaceTone.warning;
  }

  String get projectedValueLabel =>
      projectedValueCoin == null
          ? 'Value pending'
          : _formatCoin(projectedValueCoin!);

  List<String> get missingFields => <String>[
    if ((generationNumber ?? 0) <= 0 && (generationLabel ?? '').trim().isEmpty)
      'generation',
    if (position.trim().isEmpty) 'position',
    if (potential <= 0) 'potential',
    if (currentRating <= 0) 'current rating',
    if (traits.isEmpty) 'traits',
    if (lineage.isEmpty) 'lineage',
    if (dnaProfile == null) 'DNA',
    if ((originStory ?? '').trim().isEmpty) 'origin story',
    if (projectedValueCoin == null) 'projected value',
    if ((rarityTier ?? '').trim().isEmpty) 'rarity',
    if (nationality.trim().isEmpty) 'nationality',
  ];

  List<String> get coreMissingFields => <String>[
    if (position.trim().isEmpty) 'position',
    if (potential <= 0) 'potential',
    if (currentRating <= 0) 'current rating',
    if (nationality.trim().isEmpty) 'nationality',
  ];

  Iterable<String> get searchableValues sync* {
    yield name;
    yield position;
    yield nationality;
    yield source;
    if (generationLabel != null) {
      yield generationLabel!;
    }
    if (generationNumber != null) {
      yield 'GEN-$generationNumber';
      yield generationNumber.toString();
    }
    if (rarityTier != null) {
      yield rarityTier!;
    }
    if (originStory != null) {
      yield originStory!;
    }
    yield projectedValueLabel;
    if (projectedValueCoin != null) {
      yield projectedValueCoin.toString();
    }
    yield* traits;
    yield* lineage;
    final RegenDnaProfile? profile = dnaProfile;
    if (profile != null) {
      for (final String code in regenDnaStatCodes) {
        final int value = profile.valueFor(code);
        yield code;
        yield '$code $value';
        yield value.toString();
      }
    }
  }

  _RegenWorldEntry copyWith({
    int? generationNumber,
    String? generationLabel,
    String? originStory,
    List<String>? lineage,
  }) {
    final int? resolvedGenerationNumber =
        generationNumber ?? this.generationNumber;
    return _RegenWorldEntry(
      id: id,
      name: name,
      position: position,
      nationality: nationality,
      potential: potential,
      currentRating: currentRating,
      source: source,
      createdAt: createdAt,
      generationNumber: resolvedGenerationNumber,
      generationLabel:
          generationLabel ??
          this.generationLabel ??
          (resolvedGenerationNumber == null
              ? null
              : 'GEN-$resolvedGenerationNumber'),
      rarityTier: rarityTier,
      originStory: originStory ?? this.originStory,
      projectedValueCoin: projectedValueCoin,
      traits: traits,
      lineage: lineage ?? this.lineage,
      dnaProfile: dnaProfile,
    );
  }
}

List<_RegenWorldEntry> _buildRegenWorldEntries(RegenUniverseHubData data) {
  final Map<String, _RegenWorldEntry> entries = <String, _RegenWorldEntry>{};
  for (final NationalRegenSeed seed in data.nationalRegens) {
    entries[seed.id] = _withBloodline(
      _entryFromNationalSeed(seed),
      data.bloodlines,
    );
  }
  for (final RegenRisingStar star in data.risingStars) {
    entries.putIfAbsent(
      star.playerId,
      () => _withBloodline(_entryFromRisingStar(star), data.bloodlines),
    );
  }
  for (final RegenCreationOrder order in data.generatedRequestedSons) {
    final RegenCreationGeneratedPlayer? player = order.generatedPlayer;
    if (player != null) {
      entries[player.playerId] = _withBloodline(
        _entryFromGeneratedSon(order, player),
        data.bloodlines,
      );
    }
  }
  return entries.values.toList(growable: false);
}

_RegenWorldEntry _withBloodline(
  _RegenWorldEntry entry,
  List<RegenBloodlineChain> bloodlines,
) {
  if (entry.lineage.isNotEmpty && (entry.originStory ?? '').trim().isNotEmpty) {
    return entry;
  }
  for (final RegenBloodlineChain chain in bloodlines) {
    final bool matches = chain.entries.any((RegenBloodlinePlayer player) {
      return player.playerId == entry.id ||
          player.regenId == entry.id ||
          player.displayName.toLowerCase() == entry.name.toLowerCase();
    });
    if (!matches) {
      continue;
    }
    final int generationNumber = chain.entries
        .map((RegenBloodlinePlayer player) => player.generationIndex)
        .fold<int>(1, (int max, int value) => value > max ? value : max);
    return entry.copyWith(
      lineage:
          entry.lineage.isEmpty
              ? chain.entries
                  .map((RegenBloodlinePlayer player) => player.displayName)
                  .toList(growable: false)
              : entry.lineage,
      originStory:
          (entry.originStory ?? '').trim().isEmpty
              ? chain.originLabel
              : entry.originStory,
      generationNumber: entry.generationNumber ?? generationNumber,
    );
  }
  return entry;
}

_RegenWorldEntry _entryFromNationalSeed(NationalRegenSeed seed) {
  final RegenWorldDetails details = RegenWorldDetails.fromNationalSeed(seed);
  return _RegenWorldEntry(
    id: seed.id,
    name: seed.displayName,
    position: seed.primaryPosition,
    nationality: seed.countryName,
    potential: seed.potentialRating,
    currentRating: seed.currentRating,
    source: seed.seedType,
    createdAt: DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
    generationNumber: seed.generationIndex > 0 ? seed.generationIndex : null,
    generationLabel: details.generationLabel,
    rarityTier: details.rarityLabel,
    originStory: details.originStory,
    projectedValueCoin: details.projectedValueCoin,
    traits: details.traits,
    lineage: details.lineage,
    dnaProfile: _dnaProfileFromValues(details.dna),
  );
}

_RegenWorldEntry _entryFromRisingStar(RegenRisingStar star) {
  final RegenUniversePlayer player = star.player;
  final RegenWorldDetails? details = star.details;
  final RegenDnaProfile? detailsDnaProfile =
      details == null ? null : _dnaProfileFromValues(details.dna);
  final List<String> detailsTraits = details?.traits ?? const <String>[];
  final List<String> detailsLineage = details?.lineage ?? const <String>[];
  final int? detailsGenerationNumber = _generationNumberFromLabel(
    details?.generationLabel,
  );
  return _RegenWorldEntry(
    id: star.playerId,
    name: player.name,
    position: player.position,
    nationality: player.nationality,
    potential: player.potential,
    currentRating: player.currentRating,
    source: player.sourceType,
    createdAt: DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
    generationNumber: detailsGenerationNumber ?? player.generationNumber,
    generationLabel: details?.generationLabel ?? player.generationLabel,
    rarityTier: details?.rarityLabel ?? player.rarityTier,
    originStory:
        details?.originStory ?? details?.originLabel ?? player.originStory,
    projectedValueCoin:
        details?.projectedValueCoin ??
        player.projectedValueCoin ??
        star.marketValueCoin,
    traits: detailsTraits.isNotEmpty ? detailsTraits : player.traits,
    lineage: detailsLineage.isNotEmpty ? detailsLineage : player.lineage,
    dnaProfile: detailsDnaProfile ?? player.dnaProfile,
  );
}

_RegenWorldEntry _entryFromGeneratedSon(
  RegenCreationOrder order,
  RegenCreationGeneratedPlayer player,
) {
  return _RegenWorldEntry(
    id: player.playerId,
    name: player.fullName,
    position: player.position,
    nationality: player.countryName ?? player.countryCode ?? '',
    potential: player.potentialRating,
    currentRating: player.currentRating,
    source: 'requested_son',
    createdAt: order.generatedAt ?? order.updatedAt,
    generationNumber: player.generationNumber,
    generationLabel: player.generationLabel,
    rarityTier: player.rarityTier,
    originStory: player.originStory,
    projectedValueCoin: player.projectedValueCoin,
    traits: player.traits,
    lineage: player.lineage,
    dnaProfile: player.dnaProfile,
  );
}

String _generationLabel(_GenerationFilter filter) {
  return switch (filter) {
    _GenerationFilter.all => 'All Generations',
    _GenerationFilter.gen1 => 'GEN-1',
    _GenerationFilter.gen2 => 'GEN-2',
    _GenerationFilter.gen3 => 'GEN-3',
  };
}

int? _generationNumber(_GenerationFilter filter) {
  return switch (filter) {
    _GenerationFilter.all => null,
    _GenerationFilter.gen1 => 1,
    _GenerationFilter.gen2 => 2,
    _GenerationFilter.gen3 => 3,
  };
}

RegenDnaProfile? _dnaProfileFromValues(Map<String, double> values) {
  if (values.isEmpty) {
    return null;
  }
  int valueForCode(String code) {
    final double? value =
        values[code] ??
        values[code.toLowerCase()] ??
        values[code.toUpperCase()];
    return value == null ? 0 : value.round().clamp(0, 99);
  }

  return RegenDnaProfile(
    ratings: <String, int>{
      for (final String code in regenDnaStatCodes) code: valueForCode(code),
    },
  );
}

int? _generationNumberFromLabel(String? label) {
  if (label == null) {
    return null;
  }
  final RegExpMatch? match = RegExp(
    r'GEN-?(\d+)',
  ).firstMatch(label.toUpperCase());
  return match == null ? null : int.tryParse(match.group(1) ?? '');
}

String _formatCoin(int value) {
  if (value >= 1000000) {
    return 'GTC ${(value / 1000000).toStringAsFixed(1)}M';
  }
  if (value >= 1000) {
    return 'GTC ${(value / 1000).toStringAsFixed(0)}K';
  }
  return 'GTC $value';
}

class _BloodlinesPanel extends StatelessWidget {
  const _BloodlinesPanel({required this.bloodlines});

  final List<RegenBloodlineChain> bloodlines;

  @override
  Widget build(BuildContext context) {
    return GtexSectionPanel(
      title: 'Lineage',
      subtitle: 'Backend bloodline chains and generation order.',
      child:
          bloodlines.isEmpty
              ? const _EmptyState(
                message: 'No backend bloodline chains are published yet.',
              )
              : Column(
                children: bloodlines
                    .map(
                      (RegenBloodlineChain chain) => Padding(
                        padding: const EdgeInsets.only(bottom: spacingSM),
                        child: GtexListTile(
                          title: chain.originLabel,
                          subtitle: chain.entries
                              .map(
                                (RegenBloodlinePlayer player) =>
                                    'GEN-${player.generationIndex} ${player.displayName} | ${player.primaryPosition} | ${player.currentRating}/${player.potential}',
                              )
                              .join('\n'),
                          leadingIcon: Icons.account_tree_rounded,
                          tone: GtexSurfaceTone.info,
                          trailing: _MetricChip(
                            label: 'Drift',
                            value: chain.driftScore.toStringAsFixed(2),
                            tone: GtexSurfaceTone.info,
                          ),
                        ),
                      ),
                    )
                    .toList(growable: false),
              ),
    );
  }
}

class _AwardsPanel extends StatelessWidget {
  const _AwardsPanel({required this.awards});

  final List<RegenAwardResult> awards;

  @override
  Widget build(BuildContext context) {
    return GtexSectionPanel(
      title: 'Awards',
      subtitle:
          'Prospect awards and form stories. National-pool players can win here without becoming tradable.',
      child:
          awards.isEmpty
              ? const _EmptyState(
                message: 'No live award winners have been published yet.',
              )
              : Column(
                children: awards
                    .map(
                      (RegenAwardResult result) => Padding(
                        padding: const EdgeInsets.only(bottom: spacingSM),
                        child: _AwardTile(result: result),
                      ),
                    )
                    .toList(growable: false),
              ),
    );
  }
}

class _AwardTile extends StatelessWidget {
  const _AwardTile({required this.result});

  final RegenAwardResult result;

  @override
  Widget build(BuildContext context) {
    final RegenAwardWinner? winner =
        result.winners.isEmpty ? null : result.winners.first;
    return GtexListTile(
      title: result.award.name,
      subtitle:
          winner == null
              ? 'Season ${result.season.seasonNumber} | Winner pending'
              : 'Season ${result.season.seasonNumber} | ${winner.playerName} | Score ${winner.rankingScore.toStringAsFixed(1)}',
      leadingIcon: Icons.emoji_events_rounded,
      tone: GtexSurfaceTone.warning,
      trailing:
          winner == null
              ? null
              : SizedBox(
                width: 220,
                child: _BadgeWrap(labels: winner.badgeLabels),
              ),
    );
  }
}

class _NationalPoolPanel extends StatelessWidget {
  const _NationalPoolPanel({required this.nationalRegens});

  final List<NationalRegenSeed> nationalRegens;

  @override
  Widget build(BuildContext context) {
    return GtexSectionPanel(
      title: 'National Pool',
      subtitle: 'National-pool prospects are rental-only squad depth.',
      child:
          nationalRegens.isEmpty
              ? const _EmptyState(
                message: 'No national-pool regens are published yet.',
              )
              : Column(
                children: nationalRegens
                    .map(
                      (NationalRegenSeed seed) => Padding(
                        padding: const EdgeInsets.only(bottom: spacingSM),
                        child: FootballPlayerCard(
                          playerName: seed.displayName,
                          tierLabel: seed.rarityTier,
                          avatar: null,
                          imageUrl: seed.imageUrl,
                          position: seed.primaryPosition,
                          nationalityCode: seed.countryCode,
                          rating: seed.currentRating,
                          ageLabel: '${seed.age ?? '--'}',
                          potentialLabel: '${seed.potentialRating}',
                          attributes: <String>[
                            seed.countryName,
                            seed.ageBand.toUpperCase(),
                            ...seed.badgeLabels.take(2),
                          ],
                        ),
                      ),
                    )
                    .toList(growable: false),
              ),
    );
  }
}

class _RisingStarsPanel extends StatelessWidget {
  const _RisingStarsPanel({required this.stars});

  final List<RegenRisingStar> stars;

  @override
  Widget build(BuildContext context) {
    return GtexSectionPanel(
      title: 'Rising Stars',
      subtitle: 'Scouted rising prospects with form and potential.',
      child:
          stars.isEmpty
              ? const _EmptyState(
                message: 'No rising stars have been published yet.',
              )
              : Column(
                children: stars
                    .map(
                      (RegenRisingStar star) => Padding(
                        padding: const EdgeInsets.only(bottom: spacingSM),
                        child: FootballPlayerCard(
                          playerName: star.player.name,
                          tierLabel: star.player.sourceType,
                          avatar: null,
                          imageUrl: star.player.imageUrl,
                          position: star.player.position,
                          nationalityCode: star.player.nationalityCode,
                          rating: star.player.currentRating,
                          ageLabel: '${star.player.age}',
                          potentialLabel: '${star.player.potential}',
                          attributes: <String>[
                            star.player.nationality,
                            star.momentumLabel,
                            ...star.displayBadges.take(2),
                          ],
                        ),
                      ),
                    )
                    .toList(growable: false),
              ),
    );
  }
}

class _RequestedSonsPanel extends StatelessWidget {
  const _RequestedSonsPanel({
    required this.authenticated,
    required this.orders,
  });

  final bool authenticated;
  final List<RegenCreationOrder> orders;

  @override
  Widget build(BuildContext context) {
    final List<RegenCreationOrder> generated = orders
        .where((RegenCreationOrder order) => order.generatedPlayer != null)
        .toList(growable: false);
    return GtexSectionPanel(
      title: 'Requested Sons',
      subtitle: 'Authenticated order feed for paid request-son prospects.',
      child:
          !authenticated
              ? const _EmptyState(
                message: 'Sign in to load your live request-son orders.',
              )
              : generated.isEmpty
              ? const _EmptyState(
                message: 'No generated request-son players are visible yet.',
              )
              : Column(
                children: generated
                    .map(
                      (RegenCreationOrder order) => Padding(
                        padding: const EdgeInsets.only(bottom: spacingSM),
                        child: FootballPlayerCard(
                          playerName:
                              order.generatedPlayer?.fullName ??
                              'Requested son',
                          tierLabel: 'Requested Son',
                          avatar: null,
                          imageUrl: order.generatedPlayer?.imageUrl,
                          position: order.generatedPlayer?.position,
                          nationalityCode: order.generatedPlayer?.countryCode,
                          rating: order.generatedPlayer?.currentRating,
                          ageLabel: '${order.generatedPlayer?.age ?? '--'}',
                          potentialLabel:
                              '${order.generatedPlayer?.potentialRating ?? '--'}',
                          attributes: <String>[order.status, 'Bloodline Regen'],
                        ),
                      ),
                    )
                    .toList(growable: false),
              ),
    );
  }
}

class _ScoutingFeedPanel extends StatelessWidget {
  const _ScoutingFeedPanel({required this.items});

  final List<RegenScoutingFeedItem> items;

  @override
  Widget build(BuildContext context) {
    return GtexSectionPanel(
      title: 'Scouting Feed',
      subtitle: 'Live `/regen-universe/scouting-feed` discovery stories.',
      child:
          items.isEmpty
              ? const _EmptyState(
                message: 'No live scouting feed items are visible yet.',
              )
              : Column(
                children: items
                    .map(
                      (RegenScoutingFeedItem item) => Padding(
                        padding: const EdgeInsets.only(bottom: spacingSM),
                        child: GtexListTile(
                          title: item.title,
                          subtitle:
                              '${item.summary}\n${item.player?.name ?? 'Unknown prospect'} | ${item.feedType}',
                          leadingIcon: Icons.travel_explore_rounded,
                          tone: GtexSurfaceTone.info,
                          trailing: SizedBox(
                            width: 220,
                            child: _BadgeWrap(labels: item.displayBadges),
                          ),
                        ),
                      ),
                    )
                    .toList(growable: false),
              ),
    );
  }
}

class _TrackingPanel extends StatelessWidget {
  const _TrackingPanel({required this.tracking});

  final RegenGenerationTracking tracking;

  @override
  Widget build(BuildContext context) {
    final RegenGenerationTrackingEntry? leadingCountry =
        tracking.countryDistribution.isEmpty
            ? null
            : tracking.countryDistribution.first;
    return GtexSectionPanel(
      title: 'Tracking',
      subtitle:
          'Live generation totals and country distribution from `/regen-universe/tracking`.',
      child: Wrap(
        spacing: spacingSM,
        runSpacing: spacingSM,
        children: <Widget>[
          _MetricChip(
            label: 'Total tracked',
            value: '${tracking.totalSeededPlayers}',
            tone: GtexSurfaceTone.live,
          ),
          _MetricChip(
            label: 'Peak rating',
            value: '${tracking.globalPeakRating}',
            tone: GtexSurfaceTone.warning,
          ),
          if (leadingCountry != null)
            _MetricChip(
              label: 'Leading country',
              value: '${leadingCountry.bucket} (${leadingCountry.count})',
              tone: GtexSurfaceTone.info,
            ),
        ],
      ),
    );
  }
}

class _MetricChip extends StatelessWidget {
  const _MetricChip({
    required this.label,
    required this.value,
    required this.tone,
  });

  final String label;
  final String value;
  final GtexSurfaceTone tone;

  @override
  Widget build(BuildContext context) {
    return GtexStatTile(label: label, value: value, tone: tone);
  }
}

class _BadgeWrap extends StatelessWidget {
  const _BadgeWrap({required this.labels});

  final List<String> labels;

  @override
  Widget build(BuildContext context) {
    if (labels.isEmpty) {
      return const SizedBox.shrink();
    }
    return Wrap(
      alignment: WrapAlignment.end,
      spacing: spacingXS,
      runSpacing: spacingXS,
      children: labels
          .map(
            (String label) =>
                _BadgeChip(label: label, tone: _toneForBadge(label)),
          )
          .toList(growable: false),
    );
  }

  GtexSurfaceTone _toneForBadge(String label) {
    switch (label) {
      case 'National Pool':
        return GtexSurfaceTone.info;
      case 'Rental Only':
        return GtexSurfaceTone.warning;
      case 'Not Tradable':
        return GtexSurfaceTone.danger;
      case 'Requested Son':
        return GtexSurfaceTone.success;
      case 'Bloodline Regen':
        return GtexSurfaceTone.warning;
      case 'Club Regen':
        return GtexSurfaceTone.live;
      case 'Backend sync pending':
        return GtexSurfaceTone.warning;
      case 'Backend truth blocked':
        return GtexSurfaceTone.danger;
      default:
        return GtexSurfaceTone.neutral;
    }
  }
}

class _BadgeChip extends StatelessWidget {
  const _BadgeChip({required this.label, required this.tone});

  final String label;
  final GtexSurfaceTone tone;

  @override
  Widget build(BuildContext context) {
    final Color toneColor = switch (tone) {
      GtexSurfaceTone.live => Theme.of(context).colorScheme.primary,
      GtexSurfaceTone.info => Theme.of(context).colorScheme.secondary,
      GtexSurfaceTone.success => Colors.greenAccent.shade400,
      GtexSurfaceTone.warning => Colors.amber.shade400,
      GtexSurfaceTone.danger => Theme.of(context).colorScheme.error,
      GtexSurfaceTone.neutral => Colors.white70,
    };
    return ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 140),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
          color: toneColor.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: toneColor.withValues(alpha: 0.3)),
        ),
        child: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
            color: toneColor,
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return GtexListTile(
      title: 'Nothing live yet',
      subtitle: message,
      leadingIcon: Icons.hourglass_empty_rounded,
      tone: GtexSurfaceTone.neutral,
    );
  }
}
