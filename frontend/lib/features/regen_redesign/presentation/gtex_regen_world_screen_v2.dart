import 'package:flutter/material.dart';
import 'package:gte_frontend/app/test_runtime_detector.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../data/gtex_regen_repository.dart';
import '../models/gtex_regen_models.dart';
import 'gtex_admin_create_son_screen_v2.dart';
import 'gtex_create_son_screen_v2.dart';

class GtexRegenWorldScreenV2 extends StatefulWidget {
  const GtexRegenWorldScreenV2({
    super.key,
    required this.repository,
    this.isAdmin = false,
    this.onOpenAwards,
    this.allowFixtureData = false,
  });

  factory GtexRegenWorldScreenV2.fixture({
    Key? key,
    GtexRegenRepository repository = const DemoGtexRegenRepository(),
    bool isAdmin = false,
    VoidCallback? onOpenAwards,
  }) {
    assertFixtureFactoryAllowed('GtexRegenWorldScreenV2.fixture');
    return GtexRegenWorldScreenV2(
      key: key,
      repository: repository,
      isAdmin: isAdmin,
      onOpenAwards: onOpenAwards,
      allowFixtureData: true,
    );
  }

  final GtexRegenRepository repository;
  final bool isAdmin;
  final VoidCallback? onOpenAwards;
  final bool allowFixtureData;

  @override
  State<GtexRegenWorldScreenV2> createState() => _GtexRegenWorldScreenV2State();
}

class _GtexRegenWorldScreenV2State extends State<GtexRegenWorldScreenV2> {
  late Future<GtexRegenWorldData> _future;
  String _section = 'prospects';
  String _query = '';
  String _origin = 'All';
  GtexRegenProspect? _selected;

  @override
  void initState() {
    super.initState();
    _future = widget.repository.loadWorld();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<GtexRegenWorldData>(
      future: _future,
      builder: (
        BuildContext context,
        AsyncSnapshot<GtexRegenWorldData> snapshot,
      ) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(
            child: CircularProgressIndicator(color: GtexColors.purple),
          );
        }
        if (snapshot.hasError || !snapshot.hasData) {
          return GtexEmptyState(
            title: 'Regen world unavailable',
            message: 'The live regen universe could not be loaded right now.',
            icon: Icons.warning_amber_rounded,
            accent: GtexColors.purple,
            actionLabel: 'Retry',
            onAction:
                () => setState(() => _future = widget.repository.loadWorld()),
          );
        }

        final GtexRegenWorldData data = snapshot.data!;
        final List<GtexRegenProspect> rawFiltered = _filteredProspects(
          data.prospects,
        );
        final bool hiddenOriginLane =
            rawFiltered.isEmpty &&
            data.prospects.isNotEmpty &&
            _query.trim().isEmpty &&
            _origin != 'All';
        final List<GtexRegenProspect> filtered =
            hiddenOriginLane ? data.prospects : rawFiltered;
        if (hiddenOriginLane) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) {
              setState(() => _origin = 'All');
            }
          });
        }
        _selected ??= filtered.isNotEmpty ? filtered.first : null;

        return GtexMasterDetailScaffold(
          title: 'Regen World',
          subtitle:
              'A living football universe for regens, awards, contracts, personalities, and Create-a-Son orders.',
          accent: GtexColors.purple,
          mobileLeftTitle: 'Regen menu',
          actions: <Widget>[
            GtexActionButton(
              label: 'Create a Son',
              icon: Icons.family_restroom_rounded,
              accent: GtexColors.gold,
              onPressed: () => _openCreateSon(context, data),
            ),
            if (widget.onOpenAwards != null)
              GtexActionButton(
                label: 'Awards',
                icon: Icons.emoji_events_outlined,
                accent: GtexColors.purple,
                secondary: true,
                onPressed: widget.onOpenAwards,
              ),
            if (widget.isAdmin)
              GtexActionButton(
                label: 'Admin Queue',
                icon: Icons.admin_panel_settings_rounded,
                secondary: true,
                accent: GtexColors.cyan,
                onPressed: () => _openAdminCreateSon(context, data),
              ),
          ],
          leftPanel: _RegenLeftPanel(
            data: data,
            section: _section,
            origin: _origin,
            query: _query,
            isAdmin: widget.isAdmin,
            onQueryChanged: (String value) => setState(() => _query = value),
            onSectionChanged:
                (String value) => setState(() => _section = value),
            onOriginChanged: (String value) => setState(() => _origin = value),
          ),
          detail: _buildDetail(data, filtered),
          rightPanel: _RegenRightPanel(
            selected: _selected,
            contracts: data.contracts,
            achievements: data.achievementFeed,
            onCreateSon: () => _openCreateSon(context, data),
          ),
          rightPanelWidth: 370,
        );
      },
    );
  }

  List<GtexRegenProspect> _filteredProspects(
    List<GtexRegenProspect> prospects,
  ) {
    final String normalizedQuery = _query.trim().toLowerCase();
    return prospects
        .where((GtexRegenProspect prospect) {
          final bool originMatches =
              _origin == 'All' || prospect.originLabel == _origin;
          final bool queryMatches =
              normalizedQuery.isEmpty ||
              prospect.displayName.toLowerCase().contains(normalizedQuery) ||
              prospect.countryName.toLowerCase().contains(normalizedQuery) ||
              prospect.position.toLowerCase().contains(normalizedQuery) ||
              prospect.archetype.toLowerCase().contains(normalizedQuery);
          return originMatches && queryMatches;
        })
        .toList(growable: false);
  }

  Widget _buildDetail(
    GtexRegenWorldData data,
    List<GtexRegenProspect> prospects,
  ) {
    switch (_section) {
      case 'awards':
        return _AwardsBoard(awards: data.awards);
      case 'contracts':
        return _ContractBoard(contracts: data.contracts);
      case 'create-son':
        return GtexCreateSonScreenV2(
          repository: widget.repository,
          initialData: data,
          embedded: true,
          allowFixtureData: widget.allowFixtureData,
        );
      case 'achievements':
        return _AchievementBoard(items: data.achievementFeed);
      case 'admin-create-son':
        if (!widget.isAdmin) {
          return const GtexEmptyState(
            title: 'Admin Create-a-Son unavailable',
            message:
                'This live workflow is only available to authorized admin sessions.',
            icon: Icons.admin_panel_settings_outlined,
            accent: GtexColors.danger,
          );
        }
        return GtexAdminCreateSonScreenV2(
          repository: widget.repository,
          initialData: data,
          embedded: true,
          allowFixtureData: widget.allowFixtureData,
        );
      case 'prospects':
      default:
        return _ProspectsBoard(
          prospects: prospects,
          selectedId: _selected?.id,
          onSelected:
              (GtexRegenProspect prospect) =>
                  setState(() => _selected = prospect),
        );
    }
  }

  void _openCreateSon(BuildContext context, GtexRegenWorldData data) {
    Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (_) => GtexCreateSonScreenV2(
              repository: widget.repository,
              initialData: data,
              allowFixtureData: widget.allowFixtureData,
            ),
      ),
    );
  }

  void _openAdminCreateSon(BuildContext context, GtexRegenWorldData data) {
    Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (_) => GtexAdminCreateSonScreenV2(
              repository: widget.repository,
              initialData: data,
              allowFixtureData: widget.allowFixtureData,
            ),
      ),
    );
  }
}

class _RegenLeftPanel extends StatelessWidget {
  const _RegenLeftPanel({
    required this.data,
    required this.section,
    required this.origin,
    required this.query,
    required this.isAdmin,
    required this.onQueryChanged,
    required this.onSectionChanged,
    required this.onOriginChanged,
  });

  final GtexRegenWorldData data;
  final String section;
  final String origin;
  final String query;
  final bool isAdmin;
  final ValueChanged<String> onQueryChanged;
  final ValueChanged<String> onSectionChanged;
  final ValueChanged<String> onOriginChanged;

  @override
  Widget build(BuildContext context) {
    final List<String> origins =
        <String>{
          'All',
          ...data.prospects.map((GtexRegenProspect p) => p.originLabel),
        }.toList();
    return ListView(
      children: <Widget>[
        GtexPanel(
          title: 'World metrics',
          subtitle: 'Live regen universe pulse',
          accent: GtexColors.purple,
          child: Column(
            children: <Widget>[
              GtexMetricTile(
                label: 'Regens',
                value: '${data.stats.totalRegens}',
                icon: Icons.auto_awesome,
                accent: GtexColors.purple,
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexMetricTile(
                label: 'National Pool',
                value: '${data.stats.nationalPoolCount}',
                icon: Icons.flag,
                accent: GtexColors.cyan,
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexMetricTile(
                label: 'Create-a-Son',
                value: '${data.stats.createSonOrders}',
                icon: Icons.family_restroom,
                accent: GtexColors.gold,
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexSearchField(
          hintText: 'Search regens, countries, traits',
          onChanged: onQueryChanged,
        ),
        const SizedBox(height: GtexSpacing.md),
        ...<Widget>[
          _SectionTile(
            label: 'Prospects',
            icon: Icons.auto_awesome,
            selected: section == 'prospects',
            onTap: () => onSectionChanged('prospects'),
          ),
          _SectionTile(
            label: 'Awards',
            icon: Icons.emoji_events,
            selected: section == 'awards',
            onTap: () => onSectionChanged('awards'),
          ),
          _SectionTile(
            label: 'Contracts',
            icon: Icons.assignment_outlined,
            selected: section == 'contracts',
            onTap: () => onSectionChanged('contracts'),
          ),
          _SectionTile(
            label: 'Achievements',
            icon: Icons.timeline,
            selected: section == 'achievements',
            onTap: () => onSectionChanged('achievements'),
          ),
          _SectionTile(
            label: 'Create-a-Son',
            icon: Icons.family_restroom,
            selected: section == 'create-son',
            onTap: () => onSectionChanged('create-son'),
          ),
          if (isAdmin)
            _SectionTile(
              label: 'Admin Create-a-Son',
              icon: Icons.admin_panel_settings,
              selected: section == 'admin-create-son',
              onTap: () => onSectionChanged('admin-create-son'),
            ),
        ],
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Origin filters',
          subtitle: 'Reduce the world to one prospect lane.',
          accent: GtexColors.purple,
          child: Wrap(
            spacing: 8,
            runSpacing: 8,
            children: origins
                .map((String item) {
                  return ChoiceChip(
                    label: Text(item),
                    selected: origin == item,
                    onSelected: (_) => onOriginChanged(item),
                    selectedColor: GtexColors.purple.withValues(alpha: 0.28),
                    backgroundColor: GtexColors.panelStrong,
                    labelStyle: TextStyle(
                      color:
                          origin == item
                              ? GtexColors.text
                              : GtexColors.textSecondary,
                      fontWeight: FontWeight.w800,
                    ),
                  );
                })
                .toList(growable: false),
          ),
        ),
      ],
    );
  }
}

class _SectionTile extends StatelessWidget {
  const _SectionTile({
    required this.label,
    required this.icon,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      margin: const EdgeInsets.only(bottom: GtexSpacing.xs),
      padding: const EdgeInsets.symmetric(
        horizontal: GtexSpacing.sm,
        vertical: GtexSpacing.sm,
      ),
      accent: GtexColors.purple,
      isSelected: selected,
      onTap: onTap,
      child: Row(
        children: <Widget>[
          Icon(
            icon,
            color: selected ? GtexColors.purple : GtexColors.textMuted,
          ),
          const SizedBox(width: GtexSpacing.sm),
          Expanded(
            child: Text(
              label,
              style: TextStyle(
                color: selected ? GtexColors.text : GtexColors.textSecondary,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ProspectsBoard extends StatelessWidget {
  const _ProspectsBoard({
    required this.prospects,
    required this.selectedId,
    required this.onSelected,
  });

  final List<GtexRegenProspect> prospects;
  final String? selectedId;
  final ValueChanged<GtexRegenProspect> onSelected;

  @override
  Widget build(BuildContext context) {
    if (prospects.isEmpty) {
      return const GtexEmptyState(
        title: 'No regens in this lane',
        message: 'Adjust filters or refresh the live regen universe.',
        icon: Icons.auto_awesome,
        accent: GtexColors.purple,
      );
    }
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final int columns =
            constraints.maxWidth > 980
                ? 3
                : constraints.maxWidth > 620
                ? 2
                : 1;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Padding(
              padding: const EdgeInsets.fromLTRB(
                GtexSpacing.md,
                GtexSpacing.md,
                GtexSpacing.md,
                0,
              ),
              child: Text(
                'Prospects',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  color: GtexColors.text,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
            Expanded(
              child: GridView.builder(
                padding: const EdgeInsets.all(GtexSpacing.md),
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: columns,
                  childAspectRatio: columns == 1 ? 2.1 : 1.38,
                  crossAxisSpacing: GtexSpacing.md,
                  mainAxisSpacing: GtexSpacing.md,
                ),
                itemCount: prospects.length,
                itemBuilder: (BuildContext context, int index) {
                  final GtexRegenProspect prospect = prospects[index];
                  return GtexRegenCard(
                    name: prospect.displayName,
                    archetype: prospect.archetype,
                    nationality: prospect.countryName,
                    portraitUrl: prospect.imageUrl,
                    portraitSeed: prospect.id,
                    position: prospect.position,
                    countryCode: prospect.countryCode,
                    gsiLabel: prospect.gsiLabel,
                    gsiTierLabel: prospect.gsiTierLabel,
                    ratingLabel: prospect.currentRatingLabel,
                    potentialLabel: prospect.potentialLabel,
                    ageLabel: prospect.ageLabel,
                    valueLabel: _valueLabelFor(prospect),
                    storyLine: prospect.storyline,
                    isSelected: prospect.id == selectedId,
                    onTap: () => onSelected(prospect),
                  );
                },
              ),
            ),
          ],
        );
      },
    );
  }

  String? _valueLabelFor(GtexRegenProspect prospect) {
    if (prospect.valueCoin <= 0) {
      return null;
    }
    return '${prospect.valueCoin.toStringAsFixed(0)} coin';
  }
}

class _RegenRightPanel extends StatelessWidget {
  const _RegenRightPanel({
    required this.selected,
    required this.contracts,
    required this.achievements,
    required this.onCreateSon,
  });

  final GtexRegenProspect? selected;
  final List<GtexRegenContractOffer> contracts;
  final List<GtexRegenAchievement> achievements;
  final VoidCallback onCreateSon;

  @override
  Widget build(BuildContext context) {
    final GtexRegenProspect? prospect = selected;
    return ListView(
      children: <Widget>[
        if (prospect == null)
          GtexEmptyState(
            title: 'Select a regen',
            message:
                'Choose a prospect to inspect contracts, origin, traits, and personality.',
            icon: Icons.auto_awesome,
            accent: GtexColors.purple,
          )
        else
          _SelectedProspectPanel(prospect: prospect),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Create-a-Son',
          subtitle: 'Generate a premium regen from an eligible parent player.',
          accent: GtexColors.gold,
          child: GtexActionButton(
            label: 'Open request flow',
            icon: Icons.family_restroom,
            accent: GtexColors.gold,
            onPressed: onCreateSon,
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Contract watch',
          subtitle: 'Regens should feel alive in negotiations.',
          accent: GtexColors.cyan,
          child: Column(
            children: contracts
                .take(3)
                .map(
                  (GtexRegenContractOffer offer) =>
                      _MiniContractTile(offer: offer),
                )
                .toList(growable: false),
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Latest achievements',
          accent: GtexColors.purple,
          child: Column(
            children: achievements
                .take(3)
                .map(
                  (GtexRegenAchievement item) =>
                      _AchievementTile(item: item, compact: true),
                )
                .toList(growable: false),
          ),
        ),
      ],
    );
  }
}

class _SelectedProspectPanel extends StatelessWidget {
  const _SelectedProspectPanel({required this.prospect});

  final GtexRegenProspect prospect;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      title: prospect.displayName,
      subtitle:
          '${prospect.countryName} • ${prospect.position} • ${prospect.archetype}',
      accent: GtexColors.purple,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              GtexStatusChip(
                label: prospect.originLabel,
                color: GtexColors.purple,
              ),
              const SizedBox(width: 8),
              GtexStatusChip(
                label: prospect.contractStatusLabel,
                color:
                    prospect.isNationalRentalOnly
                        ? GtexColors.cyan
                        : GtexColors.gold,
              ),
            ],
          ),
          const SizedBox(height: GtexSpacing.md),
          Row(
            children: <Widget>[
              Expanded(
                child: GtexMetricTile(
                  label: 'GSI',
                  value: '${prospect.gsi}',
                  accent: GtexColors.cyan,
                ),
              ),
              const SizedBox(width: GtexSpacing.sm),
              Expanded(
                child: GtexMetricTile(
                  label: 'POT',
                  value: '${prospect.potentialRating}',
                  accent: GtexColors.purple,
                ),
              ),
            ],
          ),
          const SizedBox(height: GtexSpacing.md),
          GtexStatusChip(label: prospect.gsiTierLabel, color: GtexColors.cyan),
          const SizedBox(height: GtexSpacing.md),
          Text(
            prospect.storyline,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: GtexColors.textSecondary,
              height: 1.45,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: GtexSpacing.md),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: prospect.traits
                .map(
                  (String trait) => GtexStatusChip(
                    label: trait,
                    color: GtexColors.mint,
                    compact: true,
                  ),
                )
                .toList(growable: false),
          ),
          const SizedBox(height: GtexSpacing.md),
          GtexStatusChip(
            label:
                prospect.isNationalRentalOnly
                    ? 'National rental only - not tradable'
                    : 'Live contract endpoint unavailable',
            color:
                prospect.isNationalRentalOnly
                    ? GtexColors.cyan
                    : GtexColors.danger,
          ),
        ],
      ),
    );
  }
}

class _AwardsBoard extends StatelessWidget {
  const _AwardsBoard({required this.awards});

  final List<GtexRegenAward> awards;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: const EdgeInsets.all(GtexSpacing.md),
      itemCount: awards.length,
      separatorBuilder: (_, __) => const SizedBox(height: GtexSpacing.md),
      itemBuilder: (BuildContext context, int index) {
        final GtexRegenAward award = awards[index];
        return GtexPanel(
          title: award.name,
          subtitle: '${award.seasonLabel} • ${award.category}',
          accent: GtexColors.gold,
          child: Row(
            children: <Widget>[
              const Icon(Icons.emoji_events, color: GtexColors.gold, size: 38),
              const SizedBox(width: GtexSpacing.md),
              Expanded(
                child: Text(
                  award.winnerName,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
              GtexStatusChip(
                label: 'Score ${award.scoreLabel}',
                color: GtexColors.gold,
              ),
            ],
          ),
        );
      },
    );
  }
}

class _ContractBoard extends StatelessWidget {
  const _ContractBoard({required this.contracts});

  final List<GtexRegenContractOffer> contracts;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: const EdgeInsets.all(GtexSpacing.md),
      itemCount: contracts.length,
      separatorBuilder: (_, __) => const SizedBox(height: GtexSpacing.md),
      itemBuilder: (BuildContext context, int index) {
        final GtexRegenContractOffer offer = contracts[index];
        return GtexPanel(
          title: offer.regenName,
          subtitle: offer.personalityNote,
          accent: GtexColors.cyan,
          trailing: GtexStatusChip(
            label: offer.status.name,
            color: GtexColors.cyan,
          ),
          child: Wrap(
            spacing: GtexSpacing.md,
            runSpacing: GtexSpacing.sm,
            children: <Widget>[
              GtexMetricTile(
                label: 'Weekly',
                value: '${offer.weeklyWageCoin.toStringAsFixed(0)} coin',
                accent: GtexColors.cyan,
              ),
              GtexMetricTile(
                label: 'Bonus',
                value: '${offer.signingBonusCoin.toStringAsFixed(0)} coin',
                accent: GtexColors.gold,
              ),
              GtexMetricTile(
                label: 'Years',
                value: '${offer.durationSeasons}',
                accent: GtexColors.purple,
              ),
            ],
          ),
        );
      },
    );
  }
}

class _AchievementBoard extends StatelessWidget {
  const _AchievementBoard({required this.items});

  final List<GtexRegenAchievement> items;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: const EdgeInsets.all(GtexSpacing.md),
      itemCount: items.length,
      separatorBuilder: (_, __) => const SizedBox(height: GtexSpacing.sm),
      itemBuilder:
          (BuildContext context, int index) =>
              _AchievementTile(item: items[index]),
    );
  }
}

class _AchievementTile extends StatelessWidget {
  const _AchievementTile({required this.item, this.compact = false});

  final GtexRegenAchievement item;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      padding: EdgeInsets.all(compact ? GtexSpacing.sm : GtexSpacing.md),
      accent: GtexColors.purple,
      child: Row(
        children: <Widget>[
          Icon(item.icon, color: GtexColors.purple),
          const SizedBox(width: GtexSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  item.title,
                  style: const TextStyle(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                Text(
                  item.body,
                  maxLines: compact ? 2 : 4,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: GtexColors.textSecondary),
                ),
              ],
            ),
          ),
          Text(
            item.timestampLabel,
            style: const TextStyle(
              color: GtexColors.textMuted,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _MiniContractTile extends StatelessWidget {
  const _MiniContractTile({required this.offer});

  final GtexRegenContractOffer offer;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
      child: Row(
        children: <Widget>[
          const Icon(Icons.assignment_outlined, color: GtexColors.cyan),
          const SizedBox(width: GtexSpacing.sm),
          Expanded(
            child: Text(
              offer.regenName,
              style: const TextStyle(
                color: GtexColors.text,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          Text(
            '${offer.weeklyWageCoin.toStringAsFixed(0)}/wk',
            style: const TextStyle(
              color: GtexColors.cyan,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}
