import 'package:flutter/material.dart';

import '../../../ui_gtex/ui_gtex.dart';
import '../models/gtex_national_team_rental_models.dart';
import '../widgets/gtex_rental_context_panel.dart';
import '../widgets/gtex_rental_player_grid.dart';
import '../widgets/gtex_rental_summary_panel.dart';

class GtexNationalTeamRentalScreen extends StatefulWidget {
  const GtexNationalTeamRentalScreen({
    super.key,
    this.competitions = const <GtexRentalCompetitionView>[],
    this.countries = const <GtexRentalCountryView>[],
    this.teams = const <GtexRentalTeamView>[],
    this.players = const <GtexRentalPlayerView>[],
    this.isLoading = false,
    this.error,
    this.warning,
    this.diagnostics = const <String>[],
    this.isAuthenticated = false,
    this.onOpenLogin,
    this.onRefresh,
    this.onCompetitionSelected,
    this.onCountrySelected,
    this.onTeamSelected,
    this.onSubmitRentalBasket,
  });

  final List<GtexRentalCompetitionView> competitions;
  final List<GtexRentalCountryView> countries;
  final List<GtexRentalTeamView> teams;
  final List<GtexRentalPlayerView> players;
  final bool isLoading;
  final String? error;
  final String? warning;
  final List<String> diagnostics;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;
  final VoidCallback? onRefresh;
  final ValueChanged<String?>? onCompetitionSelected;
  final ValueChanged<String?>? onCountrySelected;
  final ValueChanged<String?>? onTeamSelected;
  final ValueChanged<List<GtexRentalPlayerView>>? onSubmitRentalBasket;

  @override
  State<GtexNationalTeamRentalScreen> createState() =>
      _GtexNationalTeamRentalScreenState();
}

class _GtexNationalTeamRentalScreenState
    extends State<GtexNationalTeamRentalScreen> {
  late final TextEditingController _searchController;
  String? _selectedCompetitionId;
  String? _selectedConfederation;
  String? _selectedCountryCode;
  String? _selectedTeamId;
  String? _selectedPlayerId;
  bool _showPayment = false;
  GtexRentalBasketState _basketState = const GtexRentalBasketState(
    <String, GtexRentalPlayerView>{},
  );

  @override
  void initState() {
    super.initState();
    _searchController = TextEditingController();
    _selectedCompetitionId = _firstOpenCompetitionId(widget.competitions);
    if (widget.countries.isNotEmpty) {
      _selectedCountryCode = widget.countries.first.countryCode;
    }
  }

  @override
  void didUpdateWidget(covariant GtexNationalTeamRentalScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_selectedCompetitionId == null ||
        !_isOpenCompetitionId(_selectedCompetitionId)) {
      _selectedCompetitionId = _firstOpenCompetitionId(widget.competitions);
    }
    if (_selectedCountryCode == null && widget.countries.isNotEmpty) {
      _selectedCountryCode = widget.countries.first.countryCode;
    }
    if (_selectedTeamId == null && widget.teams.isNotEmpty) {
      final Iterable<GtexRentalTeamView> eligibleTeams = widget.teams.where(
        (GtexRentalTeamView team) =>
            (_selectedCompetitionId == null ||
                team.competitionId == _selectedCompetitionId) &&
            (_selectedCountryCode == null ||
                team.countryCode == _selectedCountryCode),
      );
      if (eligibleTeams.isNotEmpty) {
        _selectedTeamId = eligibleTeams.first.id;
      }
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final List<GtexRentalPlayerView> filteredPlayers = _filteredPlayers();
    final GtexRentalPlayerView? selectedPlayer = _selectedPlayer(
      filteredPlayers,
    );
    final GtexRentalCountryView? country = _selectedCountry();
    final GtexRentalTeamView? team = _selectedTeam();

    return GtexMasterDetailScaffold(
      title: 'National Team Rentals',
      subtitle:
          'Select a competition, inspect backend eligibility, and build a temporary national squad from the live rental pool.',
      mobileLeftTitle: 'Browse countries',
      leftPanelWidth: 330,
      rightPanelWidth: 380,
      accent: GtexColors.cyan,
      actions: <Widget>[
        IconButton.filledTonal(
          tooltip: 'Refresh rental pool',
          onPressed: widget.isLoading ? null : widget.onRefresh,
          icon: const Icon(Icons.sync),
        ),
        if (!widget.isAuthenticated)
          GtexActionButton(
            label: 'Sign in',
            icon: Icons.login,
            compact: true,
            onPressed: widget.onOpenLogin,
          ),
      ],
      leftPanel: GtexRentalContextPanel(
        searchController: _searchController,
        competitions: widget.competitions,
        countries: widget.countries,
        teams: widget.teams,
        selectedCompetitionId: _selectedCompetitionId,
        selectedConfederation: _selectedConfederation,
        selectedCountryCode: _selectedCountryCode,
        selectedTeamId: _selectedTeamId,
        basketCount: _basketState.squadCount,
        onSearchChanged: (_) => setState(() {}),
        onCompetitionSelected: _setCompetition,
        onConfederationSelected: _setConfederation,
        onCountrySelected: _setCountry,
        onTeamSelected: _setTeam,
        onClearFilters: _clearFilters,
      ),
      detail: GtexRentalPlayerGrid(
        players: filteredPlayers,
        selectedPlayerId: _selectedPlayerId,
        basketState: _basketState,
        isLoading: widget.isLoading,
        error: widget.error,
        warning: widget.warning,
        diagnostics: widget.diagnostics,
        selectedCountryName: country?.countryName,
        selectedTeamName: team?.name,
        onSelectPlayer: _selectPlayer,
        onToggleBasket: _toggleBasket,
        onRefresh: widget.onRefresh,
      ),
      rightPanel: GtexRentalSummaryPanel(
        selectedPlayer: selectedPlayer,
        selectedCompetition: _selectedCompetition(),
        selectedTeam: team,
        basketState: _basketState,
        isAuthenticated: widget.isAuthenticated,
        showPayment: _showPayment,
        onOpenLogin: widget.onOpenLogin,
        onToggleBasket: _toggleBasket,
        onRemoveFromBasket: _removeFromBasket,
        onReviewPayment: () => setState(() => _showPayment = true),
        onBackToBasket: () => setState(() => _showPayment = false),
        onConfirmPayment:
            widget.onSubmitRentalBasket == null
                ? null
                : () => widget.onSubmitRentalBasket?.call(_basketState.items),
      ),
    );
  }

  List<GtexRentalPlayerView> _filteredPlayers() {
    final String query = _searchController.text.trim().toLowerCase();
    return widget.players
        .where((GtexRentalPlayerView player) {
          if (_selectedCountryCode != null &&
              player.countryCode != _selectedCountryCode) {
            return false;
          }
          if (query.isNotEmpty) {
            final String haystack =
                '${player.name} ${player.position} ${player.nationality} ${player.clubName} ${player.sourceBucket}'
                    .toLowerCase();
            if (!haystack.contains(query)) return false;
          }
          return true;
        })
        .toList(growable: false);
  }

  GtexRentalPlayerView? _selectedPlayer(List<GtexRentalPlayerView> players) {
    if (players.isEmpty) return null;
    if (_selectedPlayerId == null) return players.first;
    for (final GtexRentalPlayerView player in players) {
      if (player.playerId == _selectedPlayerId) return player;
    }
    return players.first;
  }

  GtexRentalCountryView? _selectedCountry() {
    if (_selectedCountryCode == null) return null;
    for (final GtexRentalCountryView country in widget.countries) {
      if (country.countryCode == _selectedCountryCode) return country;
    }
    return null;
  }

  GtexRentalTeamView? _selectedTeam() {
    if (_selectedTeamId == null) return null;
    for (final GtexRentalTeamView team in widget.teams) {
      if (team.id == _selectedTeamId) return team;
    }
    return null;
  }

  GtexRentalCompetitionView? _selectedCompetition() {
    if (_selectedCompetitionId == null) return null;
    for (final GtexRentalCompetitionView competition in widget.competitions) {
      if (competition.id == _selectedCompetitionId && competition.isOpen) {
        return competition;
      }
    }
    return null;
  }

  void _setCompetition(String? value) {
    setState(() {
      _selectedCompetitionId =
          _isOpenCompetitionId(value)
              ? value
              : _firstOpenCompetitionId(widget.competitions);
      _selectedTeamId = null;
      _selectedPlayerId = null;
      _showPayment = false;
    });
    widget.onCompetitionSelected?.call(_selectedCompetitionId);
  }

  void _setConfederation(String? value) {
    setState(() {
      _selectedConfederation = value;
      _selectedCountryCode = null;
      _selectedTeamId = null;
      _selectedPlayerId = null;
      _showPayment = false;
    });
  }

  void _setCountry(String? value) {
    setState(() {
      _selectedCountryCode = value;
      _selectedTeamId = null;
      _selectedPlayerId = null;
      _showPayment = false;
    });
    widget.onCountrySelected?.call(value);
  }

  void _setTeam(String? value) {
    String? selectedCountryCode;
    setState(() {
      _selectedTeamId = value;
      final GtexRentalTeamView? selected = _selectedTeam();
      if (selected != null) {
        _selectedCountryCode = selected.countryCode;
        selectedCountryCode = selected.countryCode;
      }
      _selectedPlayerId = null;
      _showPayment = false;
    });
    widget.onTeamSelected?.call(value);
    if (selectedCountryCode != null) {
      widget.onCountrySelected?.call(selectedCountryCode);
    }
  }

  void _selectPlayer(GtexRentalPlayerView player) {
    setState(() {
      _selectedPlayerId = player.playerId;
      _showPayment = false;
    });
  }

  void _toggleBasket(GtexRentalPlayerView player) {
    setState(() {
      _basketState = _basketState.toggled(player);
      _selectedPlayerId = player.playerId;
      _showPayment = false;
    });
  }

  void _removeFromBasket(String playerId) {
    setState(() {
      _basketState = _basketState.removed(playerId);
      _showPayment = false;
    });
  }

  void _clearFilters() {
    setState(() {
      _searchController.clear();
      _selectedCompetitionId = _firstOpenCompetitionId(widget.competitions);
      _selectedConfederation = null;
      _selectedCountryCode = null;
      _selectedTeamId = null;
      _selectedPlayerId = null;
      _showPayment = false;
    });
  }

  String? _firstOpenCompetitionId(
    List<GtexRentalCompetitionView> competitions,
  ) {
    for (final GtexRentalCompetitionView competition in competitions) {
      if (competition.isOpen) {
        return competition.id;
      }
    }
    return null;
  }

  bool _isOpenCompetitionId(String? competitionId) {
    if (competitionId == null || competitionId.trim().isEmpty) {
      return false;
    }
    for (final GtexRentalCompetitionView competition in widget.competitions) {
      if (competition.id == competitionId) {
        return competition.isOpen;
      }
    }
    return false;
  }
}
