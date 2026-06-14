import 'package:flutter/material.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/national_team_api.dart';
import 'package:gte_frontend/features/national_team_rental_redesign/national_team_rental_redesign.dart';
import 'package:gte_frontend/models/national_team_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';

class GtexNationalTeamRentalScreenV2 extends StatefulWidget {
  const GtexNationalTeamRentalScreenV2({
    super.key,
    this.controller,
    this.apiBaseUrl,
    this.backendMode = GteBackendMode.live,
    this.nationalTeamApi,
    this.isAuthenticated = false,
    this.onOpenLogin,
  });

  final GteExchangeController? controller;
  final String? apiBaseUrl;
  final GteBackendMode backendMode;
  final NationalTeamApi? nationalTeamApi;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;

  @override
  State<GtexNationalTeamRentalScreenV2> createState() =>
      _GtexNationalTeamRentalScreenV2State();
}

class _GtexNationalTeamRentalScreenV2State
    extends State<GtexNationalTeamRentalScreenV2> {
  List<GtexRentalCompetitionView> _competitions =
      const <GtexRentalCompetitionView>[];
  List<GtexRentalCountryView> _countries = const <GtexRentalCountryView>[];
  List<GtexRentalTeamView> _teams = const <GtexRentalTeamView>[];
  List<GtexRentalPlayerView> _players = const <GtexRentalPlayerView>[];
  String? _selectedCompetitionId;
  String? _selectedCountryCode;
  bool _isLoading = false;
  bool _isSubmitting = false;
  String? _error;
  String? _poolWarning;
  List<String> _poolDiagnostics = const <String>[];
  int _requestSerial = 0;

  bool get _hasLiveDependencies =>
      widget.controller != null &&
      widget.apiBaseUrl != null &&
      widget.apiBaseUrl!.trim().isNotEmpty;

  NationalTeamApi get _nationalTeamApi =>
      widget.nationalTeamApi ??
      NationalTeamApi.standard(
        baseUrl: widget.apiBaseUrl!,
        accessToken: widget.controller?.accessToken,
        mode: widget.backendMode,
      );

  @override
  void initState() {
    super.initState();
    if (_hasLiveDependencies) {
      _loadShellData();
    }
  }

  @override
  void didUpdateWidget(covariant GtexNationalTeamRentalScreenV2 oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.controller?.accessToken != widget.controller?.accessToken ||
        oldWidget.apiBaseUrl != widget.apiBaseUrl ||
        oldWidget.backendMode != widget.backendMode) {
      if (_hasLiveDependencies) {
        _loadShellData();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_hasLiveDependencies) {
      return Scaffold(
        backgroundColor: const Color(0xFF050B08),
        body: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 520),
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    const Icon(
                      Icons.public_outlined,
                      color: Color(0xFF39FF88),
                      size: 42,
                    ),
                    const SizedBox(height: 14),
                    Text(
                      'Live rental pool required',
                      style: Theme.of(
                        context,
                      ).textTheme.titleLarge?.copyWith(color: Colors.white),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'National-team rentals open only when the live runtime supplies API, session, country, team, and eligibility authority.',
                      style: TextStyle(color: Colors.white70),
                      textAlign: TextAlign.center,
                    ),
                    if (!widget.isAuthenticated && widget.onOpenLogin != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 18),
                        child: FilledButton.icon(
                          onPressed: widget.onOpenLogin,
                          icon: const Icon(Icons.login_outlined),
                          label: const Text('Sign in'),
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
    }

    return GtexNationalTeamRentalScreen(
      competitions: _competitions,
      countries: _countries,
      teams: _teams,
      players: _players,
      isLoading: _isLoading || _isSubmitting,
      error: _error,
      warning: _poolWarning,
      diagnostics: _poolDiagnostics,
      isAuthenticated: widget.isAuthenticated,
      onOpenLogin: widget.onOpenLogin,
      onRefresh: _loadCurrentPool,
      onCompetitionSelected: _selectCompetition,
      onCountrySelected: _selectCountry,
      onTeamSelected: _selectTeam,
      onSubmitRentalBasket: _submitRentalBasket,
    );
  }

  Future<void> _loadShellData() async {
    final int serial = ++_requestSerial;
    setState(() {
      _isLoading = true;
      _error = null;
      _poolWarning = null;
      _poolDiagnostics = const <String>[];
    });

    try {
      final List<NationalTeamCompetition> competitions =
          await _nationalTeamApi.listCompetitions();
      if (!mounted || serial != _requestSerial) {
        return;
      }

      final List<GtexRentalCompetitionView> competitionViews = competitions
          .map(_competitionView)
          .toList(growable: false);

      final String? competitionId =
          _openCompetitionId(_selectedCompetitionId, competitionViews) ??
          _firstOpenCompetition(competitionViews);
      final List<GtexRentalCountryView> countryViews =
          await _loadCountryAuthority(competitionId);
      final String? selectedCountryCode =
          _selectedCountryCode ?? _firstCountryCode(countryViews);
      final List<GtexRentalTeamView> teamViews = await _loadTeamAuthority(
        competitionId: competitionId,
        countryCode: selectedCountryCode,
      );

      setState(() {
        _competitions = competitionViews;
        _selectedCompetitionId = competitionId;
        _selectedCountryCode = selectedCountryCode;
        _countries = countryViews;
        _teams = teamViews;
        if (competitionId == null) {
          _players = const <GtexRentalPlayerView>[];
          _error =
              'No open national-team rental competition is available from the live backend.';
        }
      });
      await _loadCurrentPool(serial: serial);
    } catch (error) {
      if (!mounted || serial != _requestSerial) {
        return;
      }
      setState(() {
        _error = _friendlyError(error);
        _isLoading = false;
      });
    }
  }

  Future<void> _loadCurrentPool({int? serial}) async {
    if (!_hasLiveDependencies) {
      return;
    }
    final int activeSerial = serial ?? ++_requestSerial;
    final String? competitionId = _selectedCompetitionId;
    final String? countryCode = _selectedCountryCode;
    if (competitionId == null || competitionId.trim().isEmpty) {
      setState(() {
        _players = const <GtexRentalPlayerView>[];
        _error =
            'Select an open national-team rental competition before loading the live pool.';
        _isLoading = false;
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
      _poolWarning = null;
      _poolDiagnostics = const <String>[];
    });

    try {
      final NationalTeamRentalPlayerCollection pool = await _nationalTeamApi
          .listRentalPool(
            competitionId,
            limit: 200,
            countryCode: countryCode,
            auth: widget.isAuthenticated,
          );
      final List<GtexRentalTeamView> teamViews = await _loadTeamAuthority(
        competitionId: competitionId,
        countryCode: countryCode,
      );
      if (!mounted || activeSerial != _requestSerial) {
        return;
      }

      final List<GtexRentalPlayerView> playerViews = pool.items
          .map(_rentalPlayerView)
          .toList(growable: false);
      final List<String> diagnostics = <String>[
        ...pool.warnings.take(3),
        if (pool.failedCount > pool.warnings.length)
          '${pool.failedCount - pool.warnings.length} more rental records were skipped safely.',
        if (_countries.isEmpty)
          'Country authority returned no countries for this competition.',
        if (teamViews.isEmpty)
          'Team authority returned no teams for this country.',
      ];

      setState(() {
        _teams = teamViews;
        _players = playerViews;
        _poolWarning =
            pool.partial || pool.failedCount > 0
                ? 'Loaded ${playerViews.length} valid rental players. ${pool.failedCount} records need repair.'
                : null;
        _poolDiagnostics = diagnostics;
        _isLoading = false;
      });
    } catch (error) {
      if (!mounted || activeSerial != _requestSerial) {
        return;
      }
      setState(() {
        _players = const <GtexRentalPlayerView>[];
        _error = _friendlyError(error);
        _poolWarning = null;
        _poolDiagnostics = const <String>[];
        _isLoading = false;
      });
    }
  }

  void _selectCompetition(String? competitionId) {
    setState(() {
      _selectedCompetitionId =
          _openCompetitionId(competitionId, _competitions) ??
          _firstOpenCompetition(_competitions);
      _selectedCountryCode = null;
      _teams = const <GtexRentalTeamView>[];
      _players = const <GtexRentalPlayerView>[];
    });
    _loadCurrentPool();
  }

  void _selectCountry(String? countryCode) {
    setState(() {
      _selectedCountryCode = countryCode ?? _firstCountryCode(_countries);
      _teams = const <GtexRentalTeamView>[];
    });
    _loadCurrentPool();
  }

  void _selectTeam(String? teamId) {
    if (teamId == null) {
      _loadCurrentPool();
      return;
    }
    final GtexRentalTeamView? team = _teams
        .where((GtexRentalTeamView candidate) => candidate.id == teamId)
        .cast<GtexRentalTeamView?>()
        .firstWhere(
          (GtexRentalTeamView? candidate) => candidate != null,
          orElse: () => null,
        );
    if (team == null) {
      return;
    }
    setState(() {
      _selectedCompetitionId = _openCompetitionId(
        team.competitionId,
        _competitions,
      );
      _selectedCountryCode = team.countryCode;
    });
    _loadCurrentPool();
  }

  Future<void> _submitRentalBasket(List<GtexRentalPlayerView> players) async {
    if (players.isEmpty) {
      return;
    }
    if (!widget.isAuthenticated) {
      widget.onOpenLogin?.call();
      return;
    }
    final String? competitionId = _selectedCompetitionId;
    final GtexRentalCompetitionView? competition = _competitionForId(
      competitionId,
    );
    final GtexRentalCountryView? country = _countryForCode(
      _selectedCountryCode ?? players.first.countryCode,
    );
    if (competitionId == null || competition?.isOpen != true) {
      _showSnack('Choose an open live competition before payment.');
      return;
    }
    if (country == null) {
      _showSnack('Choose a country before payment.');
      return;
    }

    setState(() => _isSubmitting = true);
    try {
      final NationalTeamEntry entry = await _nationalTeamApi.createRentalEntry(
        competitionId,
        countryCode: country.countryCode,
        countryName: country.countryName,
      );
      for (final GtexRentalPlayerView player in players) {
        await _nationalTeamApi.rentPlayer(
          entryId: entry.id,
          playerId: player.playerId,
        );
      }
      if (!mounted) {
        return;
      }
      _showSnack('Rental confirmed: ${players.length} players added.');
      setState(() => _isSubmitting = false);
    } catch (error) {
      if (!mounted) {
        return;
      }
      _showSnack(_friendlyError(error));
      setState(() => _isSubmitting = false);
    }
  }

  void _showSnack(String message) {
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  GtexRentalCompetitionView _competitionView(
    NationalTeamCompetition competition,
  ) {
    return GtexRentalCompetitionView(
      id: competition.id,
      title: competition.title,
      seasonLabel: competition.seasonLabel,
      ageBand: _ageBandLabel(competition.ageBand),
      status: competition.status,
      entryFeeLabel: 'Live pool',
      description: competition.notes,
    );
  }

  Future<List<GtexRentalCountryView>> _loadCountryAuthority(
    String? competitionId,
  ) async {
    if (competitionId == null || competitionId.trim().isEmpty) {
      return const <GtexRentalCountryView>[];
    }
    final List<Map<String, dynamic>> rows = await _nationalTeamApi
        .listCountries(competitionId: competitionId);
    final List<GtexRentalCountryView> countries = <GtexRentalCountryView>[
      for (final Map<String, dynamic> row in rows)
        if (_mapText(row, const <String>['country_code', 'code']).isNotEmpty)
          GtexRentalCountryView(
            countryCode:
                _mapText(row, const <String>[
                  'country_code',
                  'code',
                ]).toUpperCase(),
            countryName: _mapText(row, const <String>[
              'country_name',
              'display_name',
              'name',
              'label',
            ], fallback: 'Country not returned'),
            confederation: _mapText(row, const <String>[
              'confederation',
              'federation',
              'region',
            ], fallback: 'Backend authority'),
            eligiblePlayers: _mapInt(row, const <String>[
              'eligible_players',
              'eligible_player_count',
              'player_count',
            ]),
            rentalBudgetLabel: _mapText(row, const <String>[
              'rental_budget_label',
              'budget_label',
            ], fallback: 'Backend authority'),
            flagEmoji: _mapText(row, const <String>['flag_emoji', 'flag']),
          ),
    ];
    countries.sort(
      (GtexRentalCountryView left, GtexRentalCountryView right) =>
          left.countryName.compareTo(right.countryName),
    );
    return countries;
  }

  Future<List<GtexRentalTeamView>> _loadTeamAuthority({
    required String? competitionId,
    required String? countryCode,
  }) async {
    if (competitionId == null || competitionId.trim().isEmpty) {
      return const <GtexRentalTeamView>[];
    }
    final List<Map<String, dynamic>> rows = await _nationalTeamApi.listTeams(
      competitionId: competitionId,
      countryCode: countryCode,
    );
    return <GtexRentalTeamView>[
      for (final Map<String, dynamic> row in rows)
        if (_mapText(row, const <String>['id', 'team_id']).isNotEmpty)
          GtexRentalTeamView(
            id: _mapText(row, const <String>['id', 'team_id']),
            countryCode:
                _mapText(row, const <String>[
                  'country_code',
                  'code',
                ], fallback: countryCode ?? '').toUpperCase(),
            name: _mapText(row, const <String>[
              'name',
              'team_name',
              'display_name',
              'country_name',
            ], fallback: 'Team not returned'),
            ageBand: _mapText(row, const <String>[
              'age_band',
              'ageBand',
            ], fallback: 'Open'),
            competitionId: _mapText(row, const <String>[
              'competition_id',
              'competitionId',
            ], fallback: competitionId),
            eligiblePlayerCount: _mapInt(row, const <String>[
              'eligible_players',
              'eligible_player_count',
              'player_count',
            ]),
            minSquadSize: _mapInt(row, const <String>[
              'min_squad_size',
              'minSquadSize',
            ]),
            maxSquadSize: _mapInt(row, const <String>[
              'max_squad_size',
              'maxSquadSize',
            ]),
            entryId: _mapText(row, const <String>['entry_id', 'entryId']),
          ),
    ];
  }

  GtexRentalPlayerView _rentalPlayerView(NationalTeamRentalPlayer player) {
    return GtexRentalPlayerView(
      playerId: player.playerId,
      name: player.playerName,
      position: _notEmpty(player.primaryPosition, fallback: 'POS'),
      age: player.age,
      rating: player.overallRating,
      nationality:
          player.nationality?.trim().isNotEmpty == true
              ? player.nationality!
              : _countryNameFor(player.countryCode),
      countryCode: _notEmpty(player.countryCode, fallback: 'WORLD'),
      clubName: _notEmpty(
        player.currentClubName,
        fallback: 'Club not returned',
      ),
      rentalCostCredits: player.loanPriceCoin,
      sourceBucket: player.sourceBucket,
      imageUrl: player.imageUrl ?? player.portraitUrl,
      portraitUrl: player.portraitUrl,
      portraitStatus: player.portraitStatus,
      portraitMissingReason: player.portraitMissingReason,
      eligibilityNote: _rentalEligibilityNote(player),
      rentalEligible: player.rentalEligible,
      eligibilityReasons: player.eligibility.reasons,
      isPreseededRegen: player.isPreseededNationalRegen || player.isRegen,
    );
  }

  String _rentalEligibilityNote(NationalTeamRentalPlayer player) {
    final String? message = player.eligibility.message;
    if (message != null && message.trim().isNotEmpty) {
      return message;
    }
    if (player.eligibility.reasons.isNotEmpty) {
      return player.eligibility.reasons.join(', ');
    }
    return player.rentalEligible
        ? 'Backend eligible for the selected national-team rental pool.'
        : 'Backend eligibility is unavailable.';
  }

  GtexRentalCountryView? _countryForCode(String? countryCode) {
    if (countryCode == null) {
      return null;
    }
    for (final GtexRentalCountryView country in _countries) {
      if (country.countryCode == countryCode) {
        return country;
      }
    }
    return null;
  }

  String? _firstOpenCompetition(List<GtexRentalCompetitionView> competitions) {
    if (competitions.isEmpty) {
      return null;
    }
    for (final GtexRentalCompetitionView competition in competitions) {
      if (competition.isOpen) {
        return competition.id;
      }
    }
    return null;
  }

  String? _openCompetitionId(
    String? competitionId,
    List<GtexRentalCompetitionView> competitions,
  ) {
    final GtexRentalCompetitionView? competition = _competitionForId(
      competitionId,
      competitions: competitions,
    );
    return competition?.isOpen == true ? competition!.id : null;
  }

  GtexRentalCompetitionView? _competitionForId(
    String? competitionId, {
    List<GtexRentalCompetitionView>? competitions,
  }) {
    if (competitionId == null || competitionId.trim().isEmpty) {
      return null;
    }
    for (final GtexRentalCompetitionView competition
        in competitions ?? _competitions) {
      if (competition.id == competitionId) {
        return competition;
      }
    }
    return null;
  }

  String? _firstCountryCode(List<GtexRentalCountryView> countries) {
    return countries.isEmpty ? null : countries.first.countryCode;
  }

  String _countryNameFor(String? countryCode) {
    return _countryForCode(countryCode)?.countryName ?? 'National team';
  }

  String _ageBandLabel(String value) {
    final String normalized = value.trim().toLowerCase();
    if (normalized == 'senior') {
      return 'Senior';
    }
    return normalized.isEmpty ? 'Open' : normalized.toUpperCase();
  }

  String _friendlyError(Object error) {
    final String message = error.toString().replaceFirst('Exception: ', '');
    return message.trim().isEmpty
        ? 'National-team rentals could not load.'
        : message;
  }

  String _mapText(
    Map<String, dynamic> row,
    List<String> keys, {
    String fallback = '',
  }) {
    for (final String key in keys) {
      final Object? value = row[key];
      if (value == null) {
        continue;
      }
      final String parsed = value.toString().trim();
      if (parsed.isNotEmpty) {
        return parsed;
      }
    }
    return fallback;
  }

  int _mapInt(Map<String, dynamic> row, List<String> keys) {
    for (final String key in keys) {
      final Object? value = row[key];
      if (value is int) {
        return value;
      }
      if (value is num) {
        return value.toInt();
      }
      if (value != null) {
        final int? parsed = int.tryParse(value.toString());
        if (parsed != null) {
          return parsed;
        }
      }
    }
    return 0;
  }

  String _notEmpty(String? value, {required String fallback}) {
    final String? trimmed = value?.trim();
    return trimmed == null || trimmed.isEmpty ? fallback : trimmed;
  }
}
