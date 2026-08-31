import 'package:flutter/material.dart';

import '../../../ui_gtex/ui_gtex.dart';
import '../models/gtex_market_browse_models.dart';

class GtexMarketContextPanel extends StatelessWidget {
  const GtexMarketContextPanel({
    super.key,
    required this.searchController,
    required this.positionController,
    required this.minValueController,
    required this.maxValueController,
    required this.minAgeController,
    required this.maxAgeController,
    required this.summary,
    required this.selectedCountry,
    required this.selectedLeague,
    required this.selectedDivision,
    required this.selectedClub,
    required this.selectedAvailability,
    required this.basketCount,
    required this.onSearchSubmitted,
    required this.onAdvancedSubmitted,
    required this.onClearFilters,
    required this.onCountrySelected,
    required this.onLeagueSelected,
    required this.onDivisionSelected,
    required this.onClubSelected,
    required this.onAvailabilitySelected,
  });

  final TextEditingController searchController;
  final TextEditingController positionController;
  final TextEditingController minValueController;
  final TextEditingController maxValueController;
  final TextEditingController minAgeController;
  final TextEditingController maxAgeController;
  final GtexMarketBrowseSummary summary;
  final String? selectedCountry;
  final String? selectedLeague;
  final String? selectedDivision;
  final String? selectedClub;
  final String selectedAvailability;
  final int basketCount;
  final ValueChanged<String> onSearchSubmitted;
  final VoidCallback onAdvancedSubmitted;
  final VoidCallback onClearFilters;
  final ValueChanged<String?> onCountrySelected;
  final ValueChanged<String?> onLeagueSelected;
  final ValueChanged<String?> onDivisionSelected;
  final ValueChanged<String?> onClubSelected;
  final ValueChanged<String> onAvailabilitySelected;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        Text(
          'Transfer Hub',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
            color: GtexColors.text,
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: GtexSpacing.xs),
        Text(
          'Transfer, loan, swap, loan-to-buy, expiring contracts, trending targets, watchlist, and negotiations.',
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: GtexColors.textMuted),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexSearchField(
          controller: searchController,
          hintText: 'Search player, club, league, nationality',
          onSubmitted: onSearchSubmitted,
        ),
        const SizedBox(height: GtexSpacing.sm),
        Row(
          children: <Widget>[
            Expanded(
              child: GtexActionButton(
                label: 'Apply',
                icon: Icons.search,
                compact: true,
                onPressed: () => onSearchSubmitted(searchController.text),
              ),
            ),
            const SizedBox(width: GtexSpacing.xs),
            IconButton.filledTonal(
              tooltip: 'Clear filters',
              onPressed: onClearFilters,
              icon: const Icon(Icons.filter_alt_off_outlined),
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'My Shortlist',
          subtitle:
              '$basketCount player${basketCount == 1 ? '' : 's'} selected',
          child: Row(
            children: <Widget>[
              const Icon(
                Icons.shopping_basket_outlined,
                color: GtexColors.gold,
              ),
              const SizedBox(width: GtexSpacing.sm),
              Expanded(
                child: Text(
                  basketCount == 0
                      ? 'Pin transfer targets before negotiating.'
                      : 'Shortlist stays visible on the right.',
                  style: const TextStyle(
                    color: GtexColors.textMuted,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        _AvailabilitySection(
          selected: selectedAvailability,
          onSelected: onAvailabilitySelected,
        ),
        const SizedBox(height: GtexSpacing.md),
        _AdvancedFiltersSection(
          positionController: positionController,
          minValueController: minValueController,
          maxValueController: maxValueController,
          minAgeController: minAgeController,
          maxAgeController: maxAgeController,
          onSubmitted: onAdvancedSubmitted,
        ),
        const SizedBox(height: GtexSpacing.md),
        _BrowseSection(
          title: 'Countries / Nationalities',
          icon: Icons.flag_outlined,
          selected: selectedCountry,
          options: summary.countries,
          emptyMessage: 'No nationality data is available yet.',
          onSelected: onCountrySelected,
        ),
        const SizedBox(height: GtexSpacing.md),
        _BrowseSection(
          title: 'Leagues',
          icon: Icons.public_outlined,
          selected: selectedLeague,
          options: _leagueOptions,
          emptyMessage: 'No leagues match the selected country yet.',
          onSelected: onLeagueSelected,
        ),
        const SizedBox(height: GtexSpacing.md),
        _BrowseSection(
          title: 'Divisions',
          icon: Icons.account_tree_outlined,
          selected: selectedDivision,
          options: _divisionOptions,
          emptyMessage: 'No divisions match the current market lane yet.',
          onSelected: onDivisionSelected,
        ),
        const SizedBox(height: GtexSpacing.md),
        _BrowseSection(
          title: 'Clubs',
          icon: Icons.shield_outlined,
          selected: selectedClub,
          options: _clubOptions,
          emptyMessage: 'No clubs match the current market lane yet.',
          onSelected: onClubSelected,
        ),
      ],
    );
  }

  List<GtexMarketBrowseOption> get _leagueOptions {
    final String? country = selectedCountry?.trim();
    if (country == null || country.isEmpty) {
      return summary.leagues;
    }
    return summary.leagues
        .where(
          (GtexMarketBrowseOption option) =>
              option.countryId == country || option.parentId == country,
        )
        .toList(growable: false);
  }

  List<GtexMarketBrowseOption> get _divisionOptions {
    final String? league = selectedLeague?.trim();
    final String? country = selectedCountry?.trim();
    return summary.divisions
        .where((GtexMarketBrowseOption option) {
          if (league != null && league.isNotEmpty) {
            return option.leagueId == league || option.parentId == league;
          }
          if (country != null && country.isNotEmpty) {
            return option.countryId == country;
          }
          return true;
        })
        .toList(growable: false);
  }

  List<GtexMarketBrowseOption> get _clubOptions {
    final String? division = selectedDivision?.trim();
    final String? league = selectedLeague?.trim();
    final String? country = selectedCountry?.trim();
    return summary.clubs
        .where((GtexMarketBrowseOption option) {
          if (division != null && division.isNotEmpty) {
            return option.divisionId == division || option.parentId == division;
          }
          if (league != null && league.isNotEmpty) {
            return option.leagueId == league || option.parentId == league;
          }
          if (country != null && country.isNotEmpty) {
            return option.countryId == country;
          }
          return true;
        })
        .toList(growable: false);
  }
}

class _AvailabilitySection extends StatelessWidget {
  const _AvailabilitySection({
    required this.selected,
    required this.onSelected,
  });

  final String selected;
  final ValueChanged<String> onSelected;

  static const List<_AvailabilityOption> _options = <_AvailabilityOption>[
    _AvailabilityOption('all', 'All players', Icons.groups_outlined),
    _AvailabilityOption('transfer', 'Transfer listed', Icons.sync_alt),
    _AvailabilityOption('loan', 'Loan listed', Icons.schedule_outlined),
    _AvailabilityOption('swap', 'Swap listed', Icons.swap_horiz),
    _AvailabilityOption(
      'swap_plus_cash',
      'Swap + cash',
      Icons.price_change_outlined,
    ),
    _AvailabilityOption('loan_to_buy', 'Loan-to-buy', Icons.handshake_outlined),
    _AvailabilityOption(
      'temporary_rental',
      'Temporary rental',
      Icons.hourglass_top_outlined,
    ),
    _AvailabilityOption(
      'open_offer',
      'Open offers',
      Icons.local_offer_outlined,
    ),
    _AvailabilityOption(
      'private_negotiation',
      'Private negotiation',
      Icons.lock_open_outlined,
    ),
    _AvailabilityOption(
      'contracts',
      'Expiring contracts',
      Icons.event_busy_outlined,
    ),
    _AvailabilityOption('trending', 'Trending', Icons.trending_up),
    _AvailabilityOption('watchlist', 'My watchlist', Icons.star_border),
    _AvailabilityOption(
      'negotiations',
      'My negotiations',
      Icons.forum_outlined,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      title: 'Availability',
      subtitle: 'Transfer paths',
      child: Wrap(
        spacing: GtexSpacing.xs,
        runSpacing: GtexSpacing.xs,
        children: _options
            .map((_AvailabilityOption option) {
              final bool isSelected = option.value == selected;
              return ChoiceChip(
                selected: isSelected,
                avatar: Icon(option.icon, size: 16),
                label: Text(option.label),
                onSelected: (_) => onSelected(option.value),
                labelStyle: TextStyle(
                  color: isSelected ? Colors.black : GtexColors.text,
                  fontWeight: FontWeight.w800,
                ),
                selectedColor: GtexColors.gold,
                backgroundColor: GtexColors.panelStrong,
                side: BorderSide(
                  color: isSelected ? GtexColors.gold : GtexColors.line,
                ),
              );
            })
            .toList(growable: false),
      ),
    );
  }
}

class _AvailabilityOption {
  const _AvailabilityOption(this.value, this.label, this.icon);

  final String value;
  final String label;
  final IconData icon;
}

class _AdvancedFiltersSection extends StatelessWidget {
  const _AdvancedFiltersSection({
    required this.positionController,
    required this.minValueController,
    required this.maxValueController,
    required this.minAgeController,
    required this.maxAgeController,
    required this.onSubmitted,
  });

  final TextEditingController positionController;
  final TextEditingController minValueController;
  final TextEditingController maxValueController;
  final TextEditingController minAgeController;
  final TextEditingController maxAgeController;
  final VoidCallback onSubmitted;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      title: 'Advanced filters',
      subtitle: 'Position, age, and value',
      child: Column(
        children: <Widget>[
          _FilterTextField(
            controller: positionController,
            label: 'Position',
            hintText: 'FW, winger, goalkeeper',
            icon: Icons.sports_soccer_outlined,
            onSubmitted: onSubmitted,
          ),
          const SizedBox(height: GtexSpacing.sm),
          Row(
            children: <Widget>[
              Expanded(
                child: _FilterTextField(
                  controller: minAgeController,
                  label: 'Min age',
                  hintText: '18',
                  icon: Icons.cake_outlined,
                  keyboardType: TextInputType.number,
                  onSubmitted: onSubmitted,
                ),
              ),
              const SizedBox(width: GtexSpacing.xs),
              Expanded(
                child: _FilterTextField(
                  controller: maxAgeController,
                  label: 'Max age',
                  hintText: '30',
                  icon: Icons.cake,
                  keyboardType: TextInputType.number,
                  onSubmitted: onSubmitted,
                ),
              ),
            ],
          ),
          const SizedBox(height: GtexSpacing.sm),
          Row(
            children: <Widget>[
              Expanded(
                child: _FilterTextField(
                  controller: minValueController,
                  label: 'Min value',
                  hintText: '100000',
                  icon: Icons.payments_outlined,
                  keyboardType: TextInputType.number,
                  onSubmitted: onSubmitted,
                ),
              ),
              const SizedBox(width: GtexSpacing.xs),
              Expanded(
                child: _FilterTextField(
                  controller: maxValueController,
                  label: 'Max value',
                  hintText: '5000000',
                  icon: Icons.price_check_outlined,
                  keyboardType: TextInputType.number,
                  onSubmitted: onSubmitted,
                ),
              ),
            ],
          ),
          const SizedBox(height: GtexSpacing.sm),
          Align(
            alignment: Alignment.centerRight,
            child: GtexActionButton(
              label: 'Apply advanced',
              icon: Icons.tune,
              compact: true,
              secondary: true,
              onPressed: onSubmitted,
            ),
          ),
        ],
      ),
    );
  }
}

class _FilterTextField extends StatelessWidget {
  const _FilterTextField({
    required this.controller,
    required this.label,
    required this.hintText,
    required this.icon,
    required this.onSubmitted,
    this.keyboardType,
  });

  final TextEditingController controller;
  final String label;
  final String hintText;
  final IconData icon;
  final VoidCallback onSubmitted;
  final TextInputType? keyboardType;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      keyboardType: keyboardType,
      textInputAction: TextInputAction.done,
      onSubmitted: (_) => onSubmitted(),
      style: const TextStyle(
        color: GtexColors.text,
        fontWeight: FontWeight.w800,
      ),
      decoration: InputDecoration(
        labelText: label,
        hintText: hintText,
        prefixIcon: Icon(icon, size: 18),
        isDense: true,
        filled: true,
        fillColor: GtexColors.panelStrong,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
          borderSide: const BorderSide(color: GtexColors.line),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
          borderSide: const BorderSide(color: GtexColors.line),
        ),
      ),
    );
  }
}

class _BrowseSection extends StatelessWidget {
  const _BrowseSection({
    required this.title,
    required this.icon,
    required this.selected,
    required this.options,
    required this.emptyMessage,
    required this.onSelected,
  });

  final String title;
  final IconData icon;
  final String? selected;
  final List<GtexMarketBrowseOption> options;
  final String emptyMessage;
  final ValueChanged<String?> onSelected;

  @override
  Widget build(BuildContext context) {
    final List<GtexMarketBrowseOption> visibleOptions = options
        .take(14)
        .toList(growable: false);
    final bool hasMore = options.length > 14;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Icon(icon, color: GtexColors.pitch, size: 18),
            const SizedBox(width: GtexSpacing.xs),
            Expanded(
              child: Text(
                hasMore ? '$title (${options.length})' : title,
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  color: GtexColors.text,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
            if (selected != null)
              TextButton(
                onPressed: () => onSelected(null),
                child: const Text('Clear'),
              ),
          ],
        ),
        const SizedBox(height: GtexSpacing.xs),
        if (visibleOptions.isEmpty)
          Text(
            emptyMessage,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: GtexColors.textMuted),
          )
        else
          ...visibleOptions.map(
            (GtexMarketBrowseOption option) => Padding(
              padding: const EdgeInsets.only(bottom: 7),
              child: _BrowseOptionTile(
                option: option,
                selected: selected == option.id,
                onTap: () => onSelected(option.id),
              ),
            ),
          ),
      ],
    );
  }
}

class _BrowseOptionTile extends StatelessWidget {
  const _BrowseOptionTile({
    required this.option,
    required this.selected,
    required this.onTap,
  });

  final GtexMarketBrowseOption option;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.symmetric(
            horizontal: GtexSpacing.sm,
            vertical: 9,
          ),
          decoration: BoxDecoration(
            color:
                selected
                    ? GtexColors.pitch.withValues(alpha: 0.12)
                    : GtexColors.panelStrong.withValues(alpha: 0.62),
            borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
            border: Border.all(
              color:
                  selected
                      ? GtexColors.pitch.withValues(alpha: 0.72)
                      : GtexColors.line.withValues(alpha: 0.56),
            ),
          ),
          child: Row(
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      option.label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color:
                            selected ? GtexColors.text : GtexColors.textMuted,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    if (option.subtitle?.trim().isNotEmpty == true) ...<Widget>[
                      const SizedBox(height: 2),
                      Text(
                        option.subtitle!.trim(),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: GtexColors.textMuted,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              GtexStatusChip(
                label: '${option.count}',
                compact: true,
                color: selected ? GtexColors.pitch : GtexColors.cyan,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
