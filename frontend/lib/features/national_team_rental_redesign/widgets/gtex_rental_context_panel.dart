import 'package:flutter/material.dart';

import '../../../ui_gtex/ui_gtex.dart';
import '../models/gtex_national_team_rental_models.dart';

class GtexRentalContextPanel extends StatelessWidget {
  const GtexRentalContextPanel({
    super.key,
    required this.searchController,
    required this.competitions,
    required this.countries,
    required this.teams,
    required this.selectedCompetitionId,
    required this.selectedConfederation,
    required this.selectedCountryCode,
    required this.selectedTeamId,
    required this.basketCount,
    required this.onSearchChanged,
    required this.onCompetitionSelected,
    required this.onConfederationSelected,
    required this.onCountrySelected,
    required this.onTeamSelected,
    required this.onClearFilters,
  });

  final TextEditingController searchController;
  final List<GtexRentalCompetitionView> competitions;
  final List<GtexRentalCountryView> countries;
  final List<GtexRentalTeamView> teams;
  final String? selectedCompetitionId;
  final String? selectedConfederation;
  final String? selectedCountryCode;
  final String? selectedTeamId;
  final int basketCount;
  final ValueChanged<String> onSearchChanged;
  final ValueChanged<String?> onCompetitionSelected;
  final ValueChanged<String?> onConfederationSelected;
  final ValueChanged<String?> onCountrySelected;
  final ValueChanged<String?> onTeamSelected;
  final VoidCallback onClearFilters;

  @override
  Widget build(BuildContext context) {
    final List<String> confederations = countries
        .map((GtexRentalCountryView item) => item.confederation)
        .toSet()
        .toList(growable: false)
      ..sort();
    final List<GtexRentalCountryView> filteredCountries = selectedConfederation == null
        ? countries
        : countries.where((GtexRentalCountryView item) => item.confederation == selectedConfederation).toList(growable: false);
    final List<GtexRentalTeamView> filteredTeams = teams.where((GtexRentalTeamView item) {
      if (selectedCompetitionId != null && item.competitionId != selectedCompetitionId) return false;
      if (selectedCountryCode != null && item.countryCode != selectedCountryCode) return false;
      return true;
    }).toList(growable: false);

    return Column(
      children: <Widget>[
        Padding(
          padding: const EdgeInsets.all(GtexSpacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              GtexSearchField(
                controller: searchController,
                hintText: 'Search country, team, or player',
                onChanged: onSearchChanged,
              ),
              const SizedBox(height: GtexSpacing.sm),
              Row(
                children: <Widget>[
                  Expanded(
                    child: GtexStatusChip(
                      label: '$basketCount rental picks',
                      color: GtexColors.gold,
                    ),
                  ),
                  TextButton.icon(
                    onPressed: onClearFilters,
                    icon: const Icon(Icons.restart_alt, size: 18),
                    label: const Text('Reset'),
                  ),
                ],
              ),
            ],
          ),
        ),
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(GtexSpacing.md, 0, GtexSpacing.md, GtexSpacing.md),
            children: <Widget>[
              _Section(
                title: 'Competition',
                child: Column(
                  children: competitions.map((GtexRentalCompetitionView item) {
                    return _OptionTile(
                      title: item.title,
                      subtitle: '${item.ageBand} • ${item.seasonLabel} • ${item.entryFeeLabel}',
                      countLabel: item.status.toUpperCase(),
                      isSelected: selectedCompetitionId == item.id,
                      onTap: () => onCompetitionSelected(selectedCompetitionId == item.id ? null : item.id),
                    );
                  }).toList(growable: false),
                ),
              ),
              _Section(
                title: 'Confederation',
                child: Wrap(
                  spacing: GtexSpacing.xs,
                  runSpacing: GtexSpacing.xs,
                  children: confederations.map((String confed) {
                    return ChoiceChip(
                      label: Text(confed),
                      selected: selectedConfederation == confed,
                      onSelected: (_) => onConfederationSelected(selectedConfederation == confed ? null : confed),
                    );
                  }).toList(growable: false),
                ),
              ),
              _Section(
                title: 'Country / Nationality',
                child: Column(
                  children: filteredCountries.map((GtexRentalCountryView item) {
                    return _OptionTile(
                      title: '${item.displayFlag} ${item.countryName}',
                      subtitle: '${item.confederation} • Budget ${item.rentalBudgetLabel}',
                      countLabel: '${item.eligiblePlayers}',
                      isSelected: selectedCountryCode == item.countryCode,
                      onTap: () => onCountrySelected(selectedCountryCode == item.countryCode ? null : item.countryCode),
                    );
                  }).toList(growable: false),
                ),
              ),
              _Section(
                title: 'National Team',
                child: Column(
                  children: filteredTeams.map((GtexRentalTeamView item) {
                    return _OptionTile(
                      title: item.name,
                      subtitle: '${item.ageBand} • ${item.squadRuleLabel}',
                      countLabel: '${item.eligiblePlayerCount}',
                      isSelected: selectedTeamId == item.id,
                      onTap: () => onTeamSelected(selectedTeamId == item.id ? null : item.id),
                    );
                  }).toList(growable: false),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: GtexSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            title.toUpperCase(),
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: GtexColors.textMuted,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 0.9,
                ),
          ),
          const SizedBox(height: GtexSpacing.xs),
          child,
        ],
      ),
    );
  }
}

class _OptionTile extends StatelessWidget {
  const _OptionTile({
    required this.title,
    required this.subtitle,
    required this.countLabel,
    required this.isSelected,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final String countLabel;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      margin: const EdgeInsets.only(bottom: GtexSpacing.xs),
      padding: const EdgeInsets.all(GtexSpacing.sm),
      isSelected: isSelected,
      onTap: onTap,
      child: Row(
        children: <Widget>[
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: GtexColors.text, fontWeight: FontWeight.w900),
                ),
                Text(
                  subtitle,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: GtexColors.textMuted, fontWeight: FontWeight.w700, fontSize: 12),
                ),
              ],
            ),
          ),
          GtexStatusChip(label: countLabel, color: isSelected ? GtexColors.pitch : GtexColors.cyan, compact: true),
        ],
      ),
    );
  }
}
