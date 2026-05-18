import 'package:flutter/material.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';
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
      return GtexNationalTeamRentalScreen(
        isAuthenticated: widget.isAuthenticated,
        onOpenLogin: widget.onOpenLogin,
        onSubmitRentalBasket: _showPreviewOnlyMessage,
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
      final List<Object> payload = await Future.wait<Object>(<Future<Object>>[
        _nationalTeamApi.listCompetitions(),
        widget.controller!.api.fetchMarketNationalTeams(),
      ]);
      if (!mounted || serial != _requestSerial) {
        return;
      }

      final List<NationalTeamCompetition> competitions =
          payload[0] as List<NationalTeamCompetition>;
      final List<GteMarketNationalityBrowseItem> nationalities =
          payload[1] as List<GteMarketNationalityBrowseItem>;
      final List<GtexRentalCompetitionView> competitionViews = competitions
          .map(_competitionView)
          .toList(growable: false);
      final List<GtexRentalCountryView> countryViews = nationalities
          .where(
            (GteMarketNationalityBrowseItem item) =>
                item.countryCode.trim().isNotEmpty,
          )
          .map(_countryView)
          .toList(growable: false);

      final String? competitionId =
          _selectedCompetitionId ?? _firstOpenCompetition(competitionViews);
      final String? countryCode =
          _selectedCountryCode ?? _firstCountryCode(countryViews);
      final List<GtexRentalTeamView> teamViews = _buildTeams(
        competitions: competitionViews,
        countries: countryViews,
      );

      setState(() {
        _competitions = competitionViews;
        _countries = countryViews;
        _teams = teamViews;
        _selectedCompetitionId = competitionId;
        _selectedCountryCode = countryCode;
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
          .listRentalPool(competitionId, limit: 200, countryCode: countryCode);
      final Map<String, GteMarketPlayerListItem> imageLookup =
          await _loadMarketImages(countryCode);
      if (!mounted || activeSerial != _requestSerial) {
        return;
      }

      List<GtexRentalPlayerView> playerViews = pool.items
          .map(
            (NationalTeamRentalPlayer player) =>
                _rentalPlayerView(player, imageLookup[player.playerId]),
          )
          .toList(growable: false);
      if (playerViews.isEmpty && imageLookup.isNotEmpty) {
        playerViews = imageLookup.values
            .map(_marketFallbackRentalPlayerView)
            .toList(growable: false);
      }
      final List<String> diagnostics = <String>[
        ...pool.warnings.take(3),
        if (pool.failedCount > pool.warnings.length)
          '${pool.failedCount - pool.warnings.length} more rental records were skipped safely.',
      ];

      setState(() {
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

  Future<Map<String, GteMarketPlayerListItem>> _loadMarketImages(
    String? countryCode,
  ) async {
    if (countryCode == null || countryCode.trim().isEmpty) {
      return const <String, GteMarketPlayerListItem>{};
    }
    try {
      final GteMarketPlayerListView marketPlayers = await widget.controller!.api
          .fetchMarketNationalTeamEligiblePlayers(countryCode, limit: 200);
      return <String, GteMarketPlayerListItem>{
        for (final GteMarketPlayerListItem player in marketPlayers.items)
          player.playerId: player,
      };
    } catch (_) {
      return const <String, GteMarketPlayerListItem>{};
    }
  }

  void _selectCompetition(String? competitionId) {
    setState(() {
      _selectedCompetitionId =
          competitionId ?? _firstOpenCompetition(_competitions);
    });
    _loadCurrentPool();
  }

  void _selectCountry(String? countryCode) {
    setState(() {
      _selectedCountryCode = countryCode ?? _firstCountryCode(_countries);
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
      _selectedCompetitionId = team.competitionId;
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
    final GtexRentalCountryView? country = _countryForCode(
      _selectedCountryCode ?? players.first.countryCode,
    );
    if (competitionId == null || country == null) {
      _showSnack('Choose a competition and country before payment.');
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

  void _showPreviewOnlyMessage(List<GtexRentalPlayerView> players) {
    _showSnack(
      'Rental preview only: live route dependencies were not provided.',
    );
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

  GtexRentalCountryView _countryView(GteMarketNationalityBrowseItem item) {
    return GtexRentalCountryView(
      countryCode: item.countryCode,
      countryName: item.displayName,
      confederation: _inferConfederation(item.countryCode),
      eligiblePlayers: item.eligiblePlayerCount,
      rentalBudgetLabel: 'Live pricing',
    );
  }

  List<GtexRentalTeamView> _buildTeams({
    required List<GtexRentalCompetitionView> competitions,
    required List<GtexRentalCountryView> countries,
  }) {
    return <GtexRentalTeamView>[
      for (final GtexRentalCompetitionView competition in competitions)
        for (final GtexRentalCountryView country in countries)
          GtexRentalTeamView(
            id: '${competition.id}::${country.countryCode}',
            countryCode: country.countryCode,
            name: '${country.countryName} ${competition.ageBand}',
            ageBand: competition.ageBand,
            competitionId: competition.id,
            eligiblePlayerCount: country.eligiblePlayers,
            minSquadSize: 16,
            maxSquadSize: competition.ageBand.contains('U17') ? 21 : 26,
          ),
    ];
  }

  GtexRentalPlayerView _rentalPlayerView(
    NationalTeamRentalPlayer player,
    GteMarketPlayerListItem? marketPlayer,
  ) {
    final double rentalCost =
        player.loanPriceCoin ??
        ((player.baseValueCoin ?? marketPlayer?.currentValueCredits ?? 0) *
            0.2);
    return GtexRentalPlayerView(
      playerId: player.playerId,
      name: player.playerName,
      position: player.primaryPosition ?? marketPlayer?.position ?? 'POS',
      age: player.age ?? marketPlayer?.age,
      rating: player.overallRating ?? marketPlayer?.averageRating,
      nationality:
          player.nationality ??
          marketPlayer?.nationality ??
          _countryNameFor(player.countryCode),
      countryCode:
          player.countryCode ?? marketPlayer?.nationalityCode ?? 'WORLD',
      clubName:
          player.currentClubName ??
          marketPlayer?.currentClubName ??
          'National rental pool',
      rentalCostCredits: rentalCost,
      sourceBucket: player.sourceBucket,
      imageUrl: player.imageUrl ?? player.portraitUrl ?? marketPlayer?.imageUrl,
      portraitUrl: player.portraitUrl,
      portraitStatus: player.portraitStatus,
      portraitMissingReason: player.portraitMissingReason,
      eligibilityNote: _rentalEligibilityNote(player),
      isPreseededRegen: player.isPreseededNationalRegen || player.isRegen,
    );
  }

  String _rentalEligibilityNote(NationalTeamRentalPlayer player) {
    if (!player.marketEligible) {
      return 'Pending market eligibility review.';
    }
    if ((player.portraitStatus ?? '').contains('missing')) {
      return 'Eligible for rental. Portrait asset is pending, so a football silhouette will be shown.';
    }
    return 'Eligible for the selected national-team rental pool.';
  }

  GtexRentalPlayerView _marketFallbackRentalPlayerView(
    GteMarketPlayerListItem player,
  ) {
    return GtexRentalPlayerView(
      playerId: player.playerId,
      name: player.playerName,
      position: player.position ?? 'POS',
      age: player.age,
      rating: player.averageRating,
      nationality:
          player.nationality ?? _countryNameFor(player.nationalityCode),
      countryCode: player.nationalityCode ?? _selectedCountryCode ?? 'WORLD',
      clubName: player.currentClubName ?? 'National rental pool',
      rentalCostCredits: (player.currentValueCredits ?? 0) * 0.2,
      sourceBucket: 'market',
      imageUrl: player.imageUrl,
      eligibilityNote:
          'Eligible through the live market national-team player endpoint.',
    );
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
    return competitions.first.id;
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

  String _inferConfederation(String countryCode) {
    final String code = countryCode.toUpperCase();
    const Set<String> caf = <String>{
      'NG',
      'GH',
      'SN',
      'CI',
      'CM',
      'EG',
      'MA',
      'ZA',
      'DZ',
      'TN',
    };
    const Set<String> conmebol = <String>{
      'AR',
      'BR',
      'CL',
      'CO',
      'EC',
      'PE',
      'PY',
      'UY',
      'VE',
      'BO',
    };
    const Set<String> concacaf = <String>{
      'US',
      'USA',
      'CA',
      'CAN',
      'MX',
      'MEX',
      'JM',
      'CR',
      'HN',
      'PA',
    };
    const Set<String> afc = <String>{
      'JP',
      'KR',
      'AU',
      'SA',
      'IR',
      'QA',
      'AE',
      'CN',
      'IN',
    };
    if (caf.contains(code)) {
      return 'CAF';
    }
    if (conmebol.contains(code)) {
      return 'CONMEBOL';
    }
    if (concacaf.contains(code)) {
      return 'CONCACAF';
    }
    if (afc.contains(code)) {
      return 'AFC';
    }
    return 'UEFA';
  }

  String _friendlyError(Object error) {
    final String message = error.toString().replaceFirst('Exception: ', '');
    return message.trim().isEmpty
        ? 'National-team rentals could not load.'
        : message;
  }
}
