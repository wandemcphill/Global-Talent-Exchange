import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/app_feedback.dart';
import '../../../core/constants/app_spacing.dart';
import '../../../models/regen_creation_models.dart';
import '../../../models/regen_universe_models.dart';
import '../../../shared/providers/regen_provider.dart';
import '../../../shared/widgets/app_page_layout.dart';
import '../../../shared/widgets/gtex_premium_panels.dart';
import '../../../widgets/gte_shell_theme.dart';
import '../data/regen_world_entry.dart';
import 'regen_world_state_panel.dart';

class RegenWorldScreen extends ConsumerWidget {
  const RegenWorldScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<RegenUniverseHubData> value = ref.watch(
      regenUniverseHubProvider,
    );
    return AppPageLayout(
      title: 'Regen World',
      subtitle:
          'Backend-authoritative regen discovery across lineage, traits, DNA, generation, value, nationality, and rarity.',
      children: <Widget>[
        value.when(
          data:
              (RegenUniverseHubData data) =>
                  RegenWorldDiscoverySurface(data: data),
          loading: RegenWorldStatePanel.loading,
          error:
              (Object error, StackTrace stackTrace) =>
                  RegenWorldStatePanel.error(
                    message: AppFeedback.messageFor(
                      error,
                      fallback:
                          'Live Regen World data is unavailable right now.',
                    ),
                    onAction: () => ref.invalidate(regenUniverseHubProvider),
                  ),
        ),
      ],
    );
  }
}

class RegenWorldDiscoverySurface extends StatefulWidget {
  const RegenWorldDiscoverySurface({super.key, required this.data});

  final RegenUniverseHubData data;

  @override
  State<RegenWorldDiscoverySurface> createState() =>
      _RegenWorldDiscoverySurfaceState();
}

enum _GenerationFilter { all, gen1, gen2, gen3 }

enum _ValueFilter { all, under100k, mid, millionPlus }

enum _RegenSort { potential, value, newest }

class _RegenWorldDiscoverySurfaceState
    extends State<RegenWorldDiscoverySurface> {
  final TextEditingController _searchController = TextEditingController();
  _GenerationFilter _generationFilter = _GenerationFilter.all;
  _ValueFilter _valueFilter = _ValueFilter.all;
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
    final List<RegenWorldEntry> entries = buildRegenWorldEntries(widget.data);
    final List<String> positions = _uniqueSorted(
      entries.map((RegenWorldEntry entry) => entry.position),
    );
    final List<String> nationalities = _uniqueSorted(
      entries.map((RegenWorldEntry entry) => entry.nationality),
    );
    final List<String> rarities = _uniqueSorted(
      entries.map((RegenWorldEntry entry) => entry.rarityTier ?? ''),
    );
    final List<RegenWorldEntry> filtered = _filteredEntries(entries);

    final int completeCount =
        entries.where((RegenWorldEntry entry) => entry.hasBackendTruth).length;
    final int degradedCount =
        entries.where((RegenWorldEntry entry) => entry.isDegraded).length;
    final int blockedCount =
        entries.where((RegenWorldEntry entry) => entry.isBlocked).length;
    final int gen3Count =
        entries
            .where((RegenWorldEntry entry) => entry.generationNumber == 3)
            .length;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        GtexHeroPanel(
          eyebrow: 'Regen World',
          title: 'Discover Regen Talent',
          description:
              'Regen Season Active: scout backend-published bloodlines, trait stacks, DNA profiles, projected value, nationality, and rarity without prototype fixture truth.',
          metrics: <Widget>[
            GtexStatTile(
              label: 'Discovered',
              value: '${entries.length}',
              icon: Icons.travel_explore_rounded,
              tone: GtexSurfaceTone.live,
            ),
            GtexStatTile(
              label: 'Complete',
              value: '$completeCount',
              icon: Icons.verified_rounded,
              tone: GtexSurfaceTone.success,
            ),
            GtexStatTile(
              label: 'Degraded',
              value: '$degradedCount',
              icon: Icons.sync_problem_rounded,
              tone: GtexSurfaceTone.warning,
            ),
            GtexStatTile(
              label: 'Blocked',
              value: '$blockedCount',
              icon: Icons.lock_rounded,
              tone: GtexSurfaceTone.danger,
            ),
            GtexStatTile(
              label: 'GEN-3',
              value: '$gen3Count',
              icon: Icons.account_tree_rounded,
              tone: GtexSurfaceTone.info,
            ),
          ],
        ),
        if (widget.data.hasDegradedFeeds) ...<Widget>[
          const SizedBox(height: spacingMD),
          RegenWorldStatePanel.degraded(
            message: widget.data.degradedFeedsSummary,
          ),
        ],
        const SizedBox(height: spacingMD),
        GtexSectionPanel(
          title: 'Discovery Pool',
          subtitle:
              'Filter by generation, position, value, nationality, rarity, and backend-published search terms.',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              _FilterControls(
                searchController: _searchController,
                generationFilter: _generationFilter,
                valueFilter: _valueFilter,
                positionFilter: _positionFilter,
                nationalityFilter: _nationalityFilter,
                rarityFilter: _rarityFilter,
                sort: _sort,
                positions: positions,
                nationalities: nationalities,
                rarities: rarities,
                onGenerationChanged:
                    (value) => setState(() {
                      _generationFilter = value;
                    }),
                onValueChanged:
                    (value) => setState(() {
                      _valueFilter = value;
                    }),
                onPositionChanged:
                    (value) => setState(() {
                      _positionFilter = value;
                    }),
                onNationalityChanged:
                    (value) => setState(() {
                      _nationalityFilter = value;
                    }),
                onRarityChanged:
                    (value) => setState(() {
                      _rarityFilter = value;
                    }),
                onSortChanged:
                    (value) => setState(() {
                      _sort = value;
                    }),
              ),
              const SizedBox(height: spacingMD),
              if (entries.isEmpty)
                RegenWorldStatePanel.empty()
              else if (filtered.isEmpty)
                RegenWorldStatePanel.empty(onAction: _clearFilters)
              else
                _RegenWorldEntryList(
                  entries: filtered,
                  selectedId: _selectedId,
                  onToggle:
                      (String id) => setState(() {
                        _selectedId = _selectedId == id ? null : id;
                      }),
                ),
              const SizedBox(height: spacingSM),
              const Text(
                'GEN-1 starts the line. GEN-2 and GEN-3 inherit compounded traits only when the backend publishes lineage truth.',
              ),
            ],
          ),
        ),
      ],
    );
  }

  List<RegenWorldEntry> _filteredEntries(List<RegenWorldEntry> entries) {
    final String query = _searchController.text.trim().toLowerCase();
    final List<RegenWorldEntry> filtered = entries
        .where((RegenWorldEntry entry) {
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
          if (!_matchesValueFilter(entry)) {
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
          (RegenWorldEntry left, RegenWorldEntry right) =>
              right.potential.compareTo(left.potential),
        );
        break;
      case _RegenSort.value:
        filtered.sort(
          (RegenWorldEntry left, RegenWorldEntry right) =>
              (right.projectedValueCoin ?? -1).compareTo(
                left.projectedValueCoin ?? -1,
              ),
        );
        break;
      case _RegenSort.newest:
        filtered.sort(
          (RegenWorldEntry left, RegenWorldEntry right) =>
              right.createdAt.compareTo(left.createdAt),
        );
        break;
    }
    return filtered;
  }

  bool _matchesValueFilter(RegenWorldEntry entry) {
    final int? value = entry.projectedValueCoin;
    switch (_valueFilter) {
      case _ValueFilter.all:
        return true;
      case _ValueFilter.under100k:
        return value != null && value < 100000;
      case _ValueFilter.mid:
        return value != null && value >= 100000 && value < 1000000;
      case _ValueFilter.millionPlus:
        return value != null && value >= 1000000;
    }
  }

  void _clearFilters() {
    setState(() {
      _searchController.clear();
      _generationFilter = _GenerationFilter.all;
      _valueFilter = _ValueFilter.all;
      _positionFilter = 'all';
      _nationalityFilter = 'all';
      _rarityFilter = 'all';
      _sort = _RegenSort.potential;
    });
  }
}

class _FilterControls extends StatelessWidget {
  const _FilterControls({
    required this.searchController,
    required this.generationFilter,
    required this.valueFilter,
    required this.positionFilter,
    required this.nationalityFilter,
    required this.rarityFilter,
    required this.sort,
    required this.positions,
    required this.nationalities,
    required this.rarities,
    required this.onGenerationChanged,
    required this.onValueChanged,
    required this.onPositionChanged,
    required this.onNationalityChanged,
    required this.onRarityChanged,
    required this.onSortChanged,
  });

  final TextEditingController searchController;
  final _GenerationFilter generationFilter;
  final _ValueFilter valueFilter;
  final String positionFilter;
  final String nationalityFilter;
  final String rarityFilter;
  final _RegenSort sort;
  final List<String> positions;
  final List<String> nationalities;
  final List<String> rarities;
  final ValueChanged<_GenerationFilter> onGenerationChanged;
  final ValueChanged<_ValueFilter> onValueChanged;
  final ValueChanged<String> onPositionChanged;
  final ValueChanged<String> onNationalityChanged;
  final ValueChanged<String> onRarityChanged;
  final ValueChanged<_RegenSort> onSortChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        TextField(
          controller: searchController,
          decoration: const InputDecoration(
            prefixIcon: Icon(Icons.search_rounded),
            labelText: 'Search regens',
            hintText: 'Name, trait, DNA stat, nationality, or lineage',
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
                label: Text(_generationFilterLabel(filter)),
                selected: generationFilter == filter,
                onSelected: (_) => onGenerationChanged(filter),
              ),
            _StringDropdown(
              value:
                  positions.contains(positionFilter) ? positionFilter : 'all',
              label: 'All Positions',
              values: positions,
              onChanged: onPositionChanged,
            ),
            _ValueDropdown(value: valueFilter, onChanged: onValueChanged),
            _StringDropdown(
              value:
                  nationalities.contains(nationalityFilter)
                      ? nationalityFilter
                      : 'all',
              label: 'All Nationalities',
              values: nationalities,
              onChanged: onNationalityChanged,
            ),
            _StringDropdown(
              value: rarities.contains(rarityFilter) ? rarityFilter : 'all',
              label: 'All Rarities',
              values: rarities,
              onChanged: onRarityChanged,
            ),
            _SortDropdown(value: sort, onChanged: onSortChanged),
          ],
        ),
      ],
    );
  }
}

class _StringDropdown extends StatelessWidget {
  const _StringDropdown({
    required this.value,
    required this.label,
    required this.values,
    required this.onChanged,
  });

  final String value;
  final String label;
  final List<String> values;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    return DropdownButton<String>(
      value: value,
      items: <DropdownMenuItem<String>>[
        DropdownMenuItem<String>(value: 'all', child: Text(label)),
        for (final String item in values)
          DropdownMenuItem<String>(value: item, child: Text(item)),
      ],
      onChanged: (String? next) => onChanged(next ?? 'all'),
    );
  }
}

class _ValueDropdown extends StatelessWidget {
  const _ValueDropdown({required this.value, required this.onChanged});

  final _ValueFilter value;
  final ValueChanged<_ValueFilter> onChanged;

  @override
  Widget build(BuildContext context) {
    return DropdownButton<_ValueFilter>(
      value: value,
      items: const <DropdownMenuItem<_ValueFilter>>[
        DropdownMenuItem<_ValueFilter>(
          value: _ValueFilter.all,
          child: Text('All Values'),
        ),
        DropdownMenuItem<_ValueFilter>(
          value: _ValueFilter.under100k,
          child: Text('Under 100K'),
        ),
        DropdownMenuItem<_ValueFilter>(
          value: _ValueFilter.mid,
          child: Text('100K-1M'),
        ),
        DropdownMenuItem<_ValueFilter>(
          value: _ValueFilter.millionPlus,
          child: Text('1M+'),
        ),
      ],
      onChanged: (_ValueFilter? next) => onChanged(next ?? _ValueFilter.all),
    );
  }
}

class _SortDropdown extends StatelessWidget {
  const _SortDropdown({required this.value, required this.onChanged});

  final _RegenSort value;
  final ValueChanged<_RegenSort> onChanged;

  @override
  Widget build(BuildContext context) {
    return DropdownButton<_RegenSort>(
      value: value,
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
      onChanged: (_RegenSort? next) => onChanged(next ?? _RegenSort.potential),
    );
  }
}

class _RegenWorldEntryList extends StatelessWidget {
  const _RegenWorldEntryList({
    required this.entries,
    required this.selectedId,
    required this.onToggle,
  });

  final List<RegenWorldEntry> entries;
  final String? selectedId;
  final ValueChanged<String> onToggle;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: entries
          .map(
            (RegenWorldEntry entry) => Padding(
              padding: const EdgeInsets.only(bottom: spacingSM),
              child: _RegenWorldCard(
                entry: entry,
                selected: selectedId == entry.id,
                onTap: () => onToggle(entry.id),
              ),
            ),
          )
          .toList(growable: false),
    );
  }
}

class _RegenWorldCard extends StatelessWidget {
  const _RegenWorldCard({
    required this.entry,
    required this.selected,
    required this.onTap,
  });

  final RegenWorldEntry entry;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final Color toneColor = _toneColor(context, entry.truthState);
    return Container(
      decoration: BoxDecoration(
        color: toneColor.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(tokens.radiusMedium),
        border: Border.all(color: toneColor.withValues(alpha: 0.28)),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(tokens.radiusMedium),
          onTap: onTap,
          child: Padding(
            padding: EdgeInsets.all(tokens.spaceMd),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                LayoutBuilder(
                  builder: (BuildContext context, BoxConstraints constraints) {
                    final bool wide = constraints.maxWidth >= 820;
                    final Widget identity = _CardIdentity(entry: entry);
                    final Widget facts = _CardFacts(entry: entry);
                    if (!wide) {
                      return Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          identity,
                          const SizedBox(height: spacingSM),
                          facts,
                        ],
                      );
                    }
                    return Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Expanded(child: identity),
                        const SizedBox(width: spacingMD),
                        SizedBox(width: 360, child: facts),
                      ],
                    );
                  },
                ),
                if (selected) ...<Widget>[
                  const SizedBox(height: spacingMD),
                  _RegenWorldDetail(entry: entry),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _CardIdentity extends StatelessWidget {
  const _CardIdentity({required this.entry});

  final RegenWorldEntry entry;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Wrap(
          spacing: spacingXS,
          runSpacing: spacingXS,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: <Widget>[
            GtexPill(
              label: entry.generationDisplay,
              icon: Icons.account_tree_rounded,
              tone: GtexSurfaceTone.info,
            ),
            GtexPill(
              label: entry.nationalityDisplay,
              icon: Icons.flag_rounded,
              tone: GtexSurfaceTone.live,
            ),
            GtexPill(
              label: entry.positionDisplay,
              icon: Icons.sports_soccer_rounded,
              tone: GtexSurfaceTone.warning,
            ),
            GtexPill(
              label: entry.rarityDisplay,
              icon: Icons.auto_awesome_rounded,
              tone: _pillTone(entry.truthState),
            ),
          ],
        ),
        const SizedBox(height: spacingSM),
        Text(entry.name, style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: spacingXS),
        Text(
          '${entry.positionDisplay} / ${entry.originDisplay}',
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: GteShellTheme.tokensOf(context).textMuted,
          ),
        ),
        const SizedBox(height: spacingSM),
        Wrap(
          spacing: spacingXS,
          runSpacing: spacingXS,
          children: <Widget>[
            GtexPill(
              label: 'POT ${entry.potential > 0 ? entry.potential : '--'}',
              icon: Icons.trending_up_rounded,
              tone: GtexSurfaceTone.warning,
            ),
            GtexPill(
              label: entry.projectedValueLabel,
              icon: Icons.payments_rounded,
              tone: GtexSurfaceTone.success,
            ),
            GtexPill(
              label: entry.marketAccessDisplay,
              icon: _marketAccessIcon(entry),
              tone:
                  entry.hasMarketAccessTruth
                      ? _toneFor(entry.marketAccessDisplay)
                      : GtexSurfaceTone.warning,
            ),
            GtexPill(
              label: entry.truthStateLabel,
              icon: _truthIcon(entry.truthState),
              tone: _pillTone(entry.truthState),
            ),
          ],
        ),
      ],
    );
  }
}

class _CardFacts extends StatelessWidget {
  const _CardFacts({required this.entry});

  final RegenWorldEntry entry;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.end,
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        if (entry.dnaProfile == null)
          const Text('DNA not published')
        else
          _DnaIntegritySegments(profile: entry.dnaProfile!),
        const SizedBox(height: spacingSM),
        _BadgeWrap(
          labels: <String>[
            ...entry.traits.take(3),
            if (entry.traits.length > 3) '+${entry.traits.length - 3}',
            ...entry.badges.take(2),
          ],
        ),
      ],
    );
  }
}

class _RegenWorldDetail extends StatelessWidget {
  const _RegenWorldDetail({required this.entry});

  final RegenWorldEntry entry;

  @override
  Widget build(BuildContext context) {
    final bool showBlocked = entry.truthState == RegenWorldTruthState.blocked;
    final bool showDegraded = entry.truthState == RegenWorldTruthState.degraded;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        if (showBlocked)
          RegenWorldStatePanel.blocked(message: entry.missingFieldsSummary)
        else if (showDegraded)
          RegenWorldStatePanel.degraded(message: entry.missingFieldsSummary),
        if (showBlocked || showDegraded) const SizedBox(height: spacingMD),
        LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final bool wide = constraints.maxWidth >= 760;
            final Widget radar = _DnaRadarPanel(profile: entry.dnaProfile);
            final Widget facts = _DetailFacts(entry: entry);
            if (!wide) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  radar,
                  const SizedBox(height: spacingMD),
                  facts,
                ],
              );
            }
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                SizedBox(width: 300, child: radar),
                const SizedBox(width: spacingMD),
                Expanded(child: facts),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _DnaRadarPanel extends StatelessWidget {
  const _DnaRadarPanel({required this.profile});

  final RegenWorldDnaProfile? profile;

  @override
  Widget build(BuildContext context) {
    final RegenWorldDnaProfile? resolved = profile;
    if (resolved == null) {
      return const _DetailBlock(
        title: 'DNA Radar',
        child: Text('DNA not published by backend.'),
      );
    }
    return _DetailBlock(
      title: 'DNA Radar',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Center(
            child: SizedBox(
              width: 220,
              height: 220,
              child: CustomPaint(painter: _DnaRadarPainter(resolved)),
            ),
          ),
          const SizedBox(height: spacingSM),
          for (final String code in regenDnaStatCodes)
            _DnaBar(label: code, value: resolved.valueFor(code)),
        ],
      ),
    );
  }
}

class _DetailFacts extends StatelessWidget {
  const _DetailFacts({required this.entry});

  final RegenWorldEntry entry;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        _DetailBlock(
          title: 'Traits',
          child:
              entry.traits.isEmpty
                  ? const Text('Traits not published by backend.')
                  : _BadgeWrap(labels: entry.traits),
        ),
        const SizedBox(height: spacingMD),
        _DetailBlock(
          title: 'Lineage Tree',
          child: _LineageTree(lineage: entry.lineage),
        ),
        const SizedBox(height: spacingMD),
        _DetailBlock(
          title: 'Origin Story',
          child: Text(
            (entry.originStory ?? '').trim().isEmpty
                ? 'Origin story not published by backend.'
                : entry.originStory!,
          ),
        ),
        const SizedBox(height: spacingMD),
        _DetailBlock(
          title: 'Market Access',
          child: _MarketAccessBlock(entry: entry),
        ),
        const SizedBox(height: spacingMD),
        _DetailBlock(
          title: 'Backend Fields',
          child: Wrap(
            spacing: spacingXS,
            runSpacing: spacingXS,
            children: <Widget>[
              _FieldPill(label: 'Generation', published: _hasGeneration(entry)),
              _FieldPill(
                label: 'Nationality',
                published: entry.nationality.trim().isNotEmpty,
              ),
              _FieldPill(
                label: 'Rarity',
                published: (entry.rarityTier ?? '').trim().isNotEmpty,
              ),
              _FieldPill(
                label: 'Value',
                published: entry.projectedValueCoin != null,
              ),
              _FieldPill(
                label: 'Market Access',
                published: entry.hasMarketAccessTruth,
              ),
              _FieldPill(label: 'Traits', published: entry.traits.isNotEmpty),
              _FieldPill(label: 'Lineage', published: entry.lineage.isNotEmpty),
              _FieldPill(
                label: 'DNA',
                published:
                    entry.dnaProfile != null && entry.dnaProfile!.isComplete,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _MarketAccessBlock extends StatelessWidget {
  const _MarketAccessBlock({required this.entry});

  final RegenWorldEntry entry;

  @override
  Widget build(BuildContext context) {
    final RegenMarketAccess? access = entry.marketAccess;
    if (access == null || !entry.hasMarketAccessTruth) {
      return RegenWorldStatePanel.degraded(message: entry.marketAccessSummary);
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(entry.marketAccessSummary),
        const SizedBox(height: spacingSM),
        Wrap(
          spacing: spacingXS,
          runSpacing: spacingXS,
          children: <Widget>[
            _AccessStatePill(
              enabled: access.marketEligible,
              enabledLabel: 'Market eligible',
              disabledLabel: 'Market restricted',
            ),
            _AccessStatePill(
              enabled: access.shareMarketEligible,
              enabledLabel: 'Timeline eligible',
              disabledLabel: 'Timeline hidden',
            ),
            _AccessStatePill(
              enabled: access.tradable,
              enabledLabel: 'Tradable',
              disabledLabel: 'Not tradable',
            ),
            _AccessStatePill(
              enabled: access.transferable,
              enabledLabel: 'Transferable',
              disabledLabel: 'Transfer hidden',
            ),
            _AccessStatePill(
              enabled: access.cardMintEligible,
              enabledLabel: 'Card mint eligible',
              disabledLabel: 'Card mint hidden',
            ),
            _AccessStatePill(
              enabled: access.buyable && access.buyCtaAllowed,
              enabledLabel: 'Buy CTA allowed',
              disabledLabel: 'Buy CTA hidden',
            ),
          ],
        ),
        const SizedBox(height: spacingSM),
        Wrap(
          spacing: spacingXS,
          runSpacing: spacingXS,
          children: <Widget>[
            _AccessSurfacePill(
              label: 'View dossier',
              icon: Icons.assignment_ind_rounded,
              enabled: entry.canViewDossier,
            ),
            _AccessSurfacePill(
              label: 'Timeline',
              icon: Icons.timeline_rounded,
              enabled: entry.canViewTimeline,
            ),
            _AccessSurfacePill(
              label: 'Watchlist',
              icon: Icons.bookmark_add_rounded,
              enabled: entry.canUseWatchlist,
            ),
          ],
        ),
      ],
    );
  }
}

class _DetailBlock extends StatelessWidget {
  const _DetailBlock({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(tokens.spaceMd),
      decoration: BoxDecoration(
        color: tokens.panelStrong.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(tokens.radiusMedium),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.72)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: spacingSM),
          child,
        ],
      ),
    );
  }
}

class _LineageTree extends StatelessWidget {
  const _LineageTree({required this.lineage});

  final List<String> lineage;

  @override
  Widget build(BuildContext context) {
    if (lineage.isEmpty) {
      return const Text('Lineage not published by backend.');
    }
    return Wrap(
      spacing: spacingXS,
      runSpacing: spacingXS,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: <Widget>[
        for (int index = 0; index < lineage.length; index += 1) ...<Widget>[
          GtexPill(
            label: lineage[index],
            icon:
                index == lineage.length - 1
                    ? Icons.person_rounded
                    : Icons.family_restroom_rounded,
            tone:
                index == lineage.length - 1
                    ? GtexSurfaceTone.live
                    : GtexSurfaceTone.info,
          ),
          if (index < lineage.length - 1)
            Icon(
              Icons.chevron_right_rounded,
              color: GteShellTheme.tokensOf(context).textMuted,
              size: 20,
            ),
        ],
      ],
    );
  }
}

class _FieldPill extends StatelessWidget {
  const _FieldPill({required this.label, required this.published});

  final String label;
  final bool published;

  @override
  Widget build(BuildContext context) {
    return GtexPill(
      label: published ? '$label published' : '$label pending',
      icon: published ? Icons.check_circle_rounded : Icons.pending_rounded,
      tone: published ? GtexSurfaceTone.success : GtexSurfaceTone.warning,
    );
  }
}

class _AccessStatePill extends StatelessWidget {
  const _AccessStatePill({
    required this.enabled,
    required this.enabledLabel,
    required this.disabledLabel,
  });

  final bool enabled;
  final String enabledLabel;
  final String disabledLabel;

  @override
  Widget build(BuildContext context) {
    return GtexPill(
      label: enabled ? enabledLabel : disabledLabel,
      icon: enabled ? Icons.check_circle_rounded : Icons.block_rounded,
      tone: enabled ? GtexSurfaceTone.success : GtexSurfaceTone.warning,
    );
  }
}

class _AccessSurfacePill extends StatelessWidget {
  const _AccessSurfacePill({
    required this.label,
    required this.icon,
    required this.enabled,
  });

  final String label;
  final IconData icon;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    return GtexPill(
      label: enabled ? label : '$label hidden',
      icon: enabled ? icon : Icons.visibility_off_rounded,
      tone: enabled ? GtexSurfaceTone.info : GtexSurfaceTone.neutral,
    );
  }
}

class _DnaIntegritySegments extends StatelessWidget {
  const _DnaIntegritySegments({required this.profile});

  final RegenWorldDnaProfile profile;

  @override
  Widget build(BuildContext context) {
    final int filled = profile.integritySegments;
    return Row(
      mainAxisAlignment: MainAxisAlignment.end,
      mainAxisSize: MainAxisSize.min,
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
  final int? value;

  @override
  Widget build(BuildContext context) {
    final int? resolved = value;
    return Padding(
      padding: const EdgeInsets.only(bottom: spacingXS),
      child: Row(
        children: <Widget>[
          SizedBox(width: 38, child: Text(label)),
          Expanded(
            child: LinearProgressIndicator(
              value: resolved == null ? 0 : resolved.clamp(0, 99) / 99,
              minHeight: 7,
            ),
          ),
          const SizedBox(width: spacingSM),
          SizedBox(
            width: 68,
            child: Text(
              resolved == null ? 'Pending' : '$resolved',
              textAlign: TextAlign.right,
            ),
          ),
        ],
      ),
    );
  }
}

class _DnaRadarPainter extends CustomPainter {
  const _DnaRadarPainter(this.profile);

  final RegenWorldDnaProfile profile;

  @override
  void paint(Canvas canvas, Size size) {
    final Offset center = Offset(size.width / 2, size.height / 2);
    final double radius = math.min(size.width, size.height) * 0.34;
    final Paint gridPaint =
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1
          ..color = const Color(0x66FFFFFF);
    final Paint axisPaint =
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1
          ..color = const Color(0x44FFFFFF);
    final Paint fillPaint =
        Paint()
          ..style = PaintingStyle.fill
          ..color = const Color(0x663FA7FF);
    final Paint strokePaint =
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2
          ..color = const Color(0xFF6FC8FF);

    for (int ring = 1; ring <= 4; ring += 1) {
      canvas.drawPath(
        _polygonPath(center, radius * ring / 4, const <double>[
          1,
          1,
          1,
          1,
          1,
          1,
        ]),
        gridPaint,
      );
    }

    for (int index = 0; index < regenDnaStatCodes.length; index += 1) {
      final double angle = _angleFor(index);
      final Offset end = Offset(
        center.dx + math.cos(angle) * radius,
        center.dy + math.sin(angle) * radius,
      );
      canvas.drawLine(center, end, axisPaint);
      _paintLabel(canvas, size, regenDnaStatCodes[index], angle, radius + 18);
    }

    final List<double> values = <double>[
      for (final String code in regenDnaStatCodes)
        (profile.valueFor(code) ?? 0).clamp(0, 99) / 99,
    ];
    final Path valuesPath = _polygonPath(center, radius, values);
    canvas
      ..drawPath(valuesPath, fillPaint)
      ..drawPath(valuesPath, strokePaint);
  }

  @override
  bool shouldRepaint(covariant _DnaRadarPainter oldDelegate) {
    return oldDelegate.profile != profile;
  }

  Path _polygonPath(Offset center, double radius, List<double> multipliers) {
    final Path path = Path();
    for (int index = 0; index < regenDnaStatCodes.length; index += 1) {
      final double angle = _angleFor(index);
      final double multiplier = multipliers[index].clamp(0, 1);
      final Offset point = Offset(
        center.dx + math.cos(angle) * radius * multiplier,
        center.dy + math.sin(angle) * radius * multiplier,
      );
      if (index == 0) {
        path.moveTo(point.dx, point.dy);
      } else {
        path.lineTo(point.dx, point.dy);
      }
    }
    path.close();
    return path;
  }

  double _angleFor(int index) {
    return (-math.pi / 2) + (2 * math.pi * index / regenDnaStatCodes.length);
  }

  void _paintLabel(
    Canvas canvas,
    Size size,
    String label,
    double angle,
    double radius,
  ) {
    final TextPainter painter = TextPainter(
      text: TextSpan(
        text: label,
        style: const TextStyle(
          color: Colors.white70,
          fontSize: 11,
          fontWeight: FontWeight.w700,
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    final Offset center = Offset(size.width / 2, size.height / 2);
    final Offset point = Offset(
      center.dx + math.cos(angle) * radius - painter.width / 2,
      center.dy + math.sin(angle) * radius - painter.height / 2,
    );
    painter.paint(canvas, point);
  }
}

class _BadgeWrap extends StatelessWidget {
  const _BadgeWrap({required this.labels});

  final List<String> labels;

  @override
  Widget build(BuildContext context) {
    final List<String> resolved = _dedupe(labels);
    if (resolved.isEmpty) {
      return const Text('Traits not published');
    }
    return Wrap(
      alignment: WrapAlignment.end,
      spacing: spacingXS,
      runSpacing: spacingXS,
      children: resolved
          .map((String label) => GtexPill(label: label, tone: _toneFor(label)))
          .toList(growable: false),
    );
  }
}

List<String> _uniqueSorted(Iterable<String> values) {
  final List<String> resolved = _dedupe(values).toList(growable: false);
  resolved.sort();
  return resolved;
}

List<String> _dedupe(Iterable<String> values) {
  final Set<String> seen = <String>{};
  final List<String> resolved = <String>[];
  for (final String value in values) {
    final String trimmed = value.trim();
    if (trimmed.isEmpty || !seen.add(trimmed.toLowerCase())) {
      continue;
    }
    resolved.add(trimmed);
  }
  return resolved;
}

String _generationFilterLabel(_GenerationFilter filter) {
  switch (filter) {
    case _GenerationFilter.all:
      return 'All Generations';
    case _GenerationFilter.gen1:
      return 'GEN-1';
    case _GenerationFilter.gen2:
      return 'GEN-2';
    case _GenerationFilter.gen3:
      return 'GEN-3';
  }
}

int? _generationNumber(_GenerationFilter filter) {
  switch (filter) {
    case _GenerationFilter.all:
      return null;
    case _GenerationFilter.gen1:
      return 1;
    case _GenerationFilter.gen2:
      return 2;
    case _GenerationFilter.gen3:
      return 3;
  }
}

bool _hasGeneration(RegenWorldEntry entry) {
  return (entry.generationNumber ?? 0) > 0 ||
      (entry.generationLabel ?? '').trim().isNotEmpty;
}

IconData _truthIcon(RegenWorldTruthState state) {
  switch (state) {
    case RegenWorldTruthState.complete:
      return Icons.verified_rounded;
    case RegenWorldTruthState.degraded:
      return Icons.sync_problem_rounded;
    case RegenWorldTruthState.blocked:
      return Icons.lock_rounded;
  }
}

IconData _marketAccessIcon(RegenWorldEntry entry) {
  if (!entry.hasMarketAccessTruth) {
    return Icons.pending_rounded;
  }
  final RegenMarketAccess? access = entry.marketAccess;
  if (access == null) {
    return Icons.pending_rounded;
  }
  if (access.nationalPoolOnly || access.isPreseededNationalRegen) {
    return Icons.flag_rounded;
  }
  if (!access.marketEligible || !access.tradable) {
    return Icons.lock_rounded;
  }
  return Icons.fact_check_rounded;
}

GtexSurfaceTone _pillTone(RegenWorldTruthState state) {
  switch (state) {
    case RegenWorldTruthState.complete:
      return GtexSurfaceTone.success;
    case RegenWorldTruthState.degraded:
      return GtexSurfaceTone.warning;
    case RegenWorldTruthState.blocked:
      return GtexSurfaceTone.danger;
  }
}

GtexSurfaceTone _toneFor(String label) {
  final String normalized = label.toLowerCase();
  if (normalized.contains('not tradable') ||
      normalized.contains('blocked') ||
      normalized.contains('restricted') ||
      normalized.contains('pending')) {
    return GtexSurfaceTone.danger;
  }
  if (normalized.contains('national') || normalized.contains('rental')) {
    return GtexSurfaceTone.info;
  }
  if (normalized.contains('requested') || normalized.contains('bloodline')) {
    return GtexSurfaceTone.warning;
  }
  return GtexSurfaceTone.neutral;
}

Color _toneColor(BuildContext context, RegenWorldTruthState state) {
  final tokens = GteShellTheme.tokensOf(context);
  switch (state) {
    case RegenWorldTruthState.complete:
      return tokens.positive;
    case RegenWorldTruthState.degraded:
      return tokens.warning;
    case RegenWorldTruthState.blocked:
      return tokens.negative;
  }
}
