import 'package:flutter/material.dart';

import '../core/app_feedback.dart';
import '../data/competition_control_repository.dart';
import '../data/manager_market_repository.dart';
import '../widgets/gte_shell_theme.dart';
import '../widgets/gte_state_panel.dart';
import '../widgets/gte_surface_panel.dart';

class ManagerMarketScreen extends StatefulWidget {
  const ManagerMarketScreen({
    super.key,
    required this.baseUrl,
    required this.accessToken,
    required this.isAdmin,
    required this.onOpenAdmin,
  });

  final String baseUrl;
  final String accessToken;
  final bool isAdmin;
  final VoidCallback onOpenAdmin;

  @override
  State<ManagerMarketScreen> createState() => _ManagerMarketScreenState();
}

class _ManagerMarketScreenState extends State<ManagerMarketScreen> {
  final TextEditingController _searchController = TextEditingController();
  late final ManagerMarketRepository _managerRepository;
  late final CompetitionControlRepository _competitionRepository;
  bool _isLoading = true;
  bool _isRunningAction = false;
  String? _error;
  String? _tactic;
  String? _trait;
  String? _mentality;
  String? _rarity;
  List<Map<String, dynamic>> _catalog = <Map<String, dynamic>>[];
  List<Map<String, dynamic>> _listings = <Map<String, dynamic>>[];
  List<Map<String, dynamic>> _myListings = <Map<String, dynamic>>[];
  Map<String, dynamic>? _fastLeagueRuntime;
  Map<String, dynamic>? _team;
  Map<String, dynamic>? _recommendation;
  Map<String, dynamic>? _comparison;
  List<Map<String, dynamic>> _tradeHistory = <Map<String, dynamic>>[];
  String? _compareLeftManagerId;
  String? _compareRightManagerId;
  List<String> _availableTactics = <String>[];
  List<String> _availableTraits = <String>[];
  List<String> _availableMentalities = <String>[];
  List<String> _availableRarities = <String>[];

  static const List<String> _fallbackTactics = <String>[
    'tiki_taka',
    'gegenpress',
    'low_block_counter',
    'direct_long_ball',
    'wing_play',
    'inverted_wingers',
    'false_nine',
    'overlapping_fullbacks',
    'double_pivot_control',
    'park_the_bus',
    'high_press_attack',
    'compact_midblock',
    'possession_control',
    'youth_development_system',
    'elite_star_freedom',
    'technical_build_up',
    'physical_duel_game',
    'counter_attack',
  ];

  static const List<String> _fallbackTraits = <String>[
    'develops_young_players',
    'manages_elite_stars',
    'improves_player_discipline',
    'boosts_physicality_focus',
    'technical_coaching',
    'attacking_instinct',
    'defensive_organization',
    'tactical_flexibility',
    'strict_structure',
    'expressive_freedom',
    'quick_substitution',
    'late_substitution',
    'rotation_heavy',
    'loyalty_to_veterans',
    'academy_promotion_bias',
    'balanced_substitution',
  ];

  static const List<String> _fallbackMentalities = <String>[
    'attacking',
    'defensive',
    'balanced',
    'tiki_taka',
    'long_ball',
    'possession',
    'counter_attack',
    'technical',
    'physical',
    'pressing',
    'pragmatic',
  ];

  static const List<String> _fallbackRarities = <String>[
    'legendary',
    'elite_active',
    'popular',
  ];

  @override
  void initState() {
    super.initState();
    _managerRepository = ManagerMarketRepository.standard(
      baseUrl: widget.baseUrl,
      accessToken: widget.accessToken,
    );
    _competitionRepository = CompetitionControlRepository.standard(
      baseUrl: widget.baseUrl,
      accessToken: widget.accessToken,
    );
    _load();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<String> get _tactics =>
      _availableTactics.isNotEmpty ? _availableTactics : _fallbackTactics;

  List<String> get _traits =>
      _availableTraits.isNotEmpty ? _availableTraits : _fallbackTraits;

  List<String> get _mentalities => _availableMentalities.isNotEmpty
      ? _availableMentalities
      : _fallbackMentalities;

  List<String> get _rarities =>
      _availableRarities.isNotEmpty ? _availableRarities : _fallbackRarities;


  Map<String, Object?> _catalogQuery() {
    return <String, Object?>{
      'limit': 500,
      if (_searchController.text.trim().isNotEmpty) 'search': _searchController.text.trim(),
      if (_tactic != null && _tactic!.isNotEmpty) 'tactic': _tactic!,
      if (_trait != null && _trait!.isNotEmpty) 'trait': _trait!,
      if (_mentality != null && _mentality!.isNotEmpty) 'mentality': _mentality!,
      if (_rarity != null && _rarity!.isNotEmpty) 'rarity': _rarity!,
    };
  }

  Future<void> _load() async {
    if (mounted) {
      setState(() {
        _isLoading = true;
        _error = null;
      });
    }
    try {
      final Map<String, dynamic> filterData = await _managerRepository.fetchFilters();
      final Map<String, dynamic> catalogData = await _managerRepository.fetchCatalog(
        search: _searchController.text,
        tactic: _tactic,
        trait: _trait,
        mentality: _mentality,
        rarity: _rarity,
        limit: 500,
      );
      final Map<String, dynamic> nextTeam = await _managerRepository.fetchTeam();
      final int totalOwned = (nextTeam['total_owned'] as int?) ?? 0;
      final int participants = totalOwned < 2 ? 2 : totalOwned;
      final List<Object> payload = await Future.wait<Object>(<Future<Object>>[
        Future<Map<String, dynamic>>.value(catalogData),
        Future<Map<String, dynamic>>.value(nextTeam),
        _managerRepository.fetchListings(),
        _managerRepository.fetchMyListings(),
        _managerRepository.fetchRecommendation(),
        _competitionRepository.fetchRuntime('fast_league', participants: participants),
        _managerRepository.fetchTradeHistory(),
      ]);

      if (!mounted) {
        return;
      }
      setState(() {
        _availableTactics = (filterData['tactics'] as List<dynamic>? ?? <dynamic>[])
            .map((dynamic item) => item.toString())
            .toList();
        _availableTraits = (filterData['traits'] as List<dynamic>? ?? <dynamic>[])
            .map((dynamic item) => item.toString())
            .toList();
        _availableMentalities =
            (filterData['mentalities'] as List<dynamic>? ?? <dynamic>[])
                .map((dynamic item) => item.toString())
                .toList();
        _availableRarities = (filterData['rarities'] as List<dynamic>? ?? <dynamic>[])
            .map((dynamic item) => item.toString())
            .toList();
        _catalog = ((payload[0] as Map<String, dynamic>)['items'] as List<dynamic>? ?? <dynamic>[])
            .whereType<Map>()
            .map((dynamic item) => Map<String, dynamic>.from(item as Map))
            .toList();
        _team = payload[1] as Map<String, dynamic>;
        _listings = (payload[2] as List<dynamic>).cast<Map<String, dynamic>>();
        _myListings = (payload[3] as List<dynamic>).cast<Map<String, dynamic>>();
        _recommendation = payload[4] as Map<String, dynamic>;
        _fastLeagueRuntime = payload[5] as Map<String, dynamic>;
        _tradeHistory = (payload[6] as List<dynamic>).cast<Map<String, dynamic>>();
        final List<Map<String, dynamic>> catalogItems = _catalog;
        if (catalogItems.length >= 2) {
          _compareLeftManagerId ??= (catalogItems.first['manager_id'] ?? '').toString();
          _compareRightManagerId ??= (catalogItems[1]['manager_id'] ?? '').toString();
        }
      });
      await _loadComparison();
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = AppFeedback.messageFor(error);
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _loadComparison() async {
    if (_compareLeftManagerId == null || _compareRightManagerId == null) {
      return;
    }
    try {
      final Map<String, dynamic> comparison = await _managerRepository.compareManagers(
        _compareLeftManagerId!,
        _compareRightManagerId!,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _comparison = comparison;
      });
    } catch (_) {
      // Best-effort comparison panel. Keep market usable if compare is unavailable.
    }
  }

  Future<void> _runAction(
    Future<void> Function() action, {
    String? successMessage,
  }) async {
    if (mounted) {
      setState(() {
        _isRunningAction = true;
      });
    }
    try {
      await action();
      if (!mounted) {
        return;
      }
      if (successMessage != null && successMessage.isNotEmpty) {
        AppFeedback.showSuccess(context, successMessage);
      }
    } catch (error) {
      if (!mounted) {
        return;
      }
      AppFeedback.showError(context, error);
    } finally {
      if (mounted) {
        setState(() {
          _isRunningAction = false;
        });
      }
    }
  }

  Future<void> _recruit(String managerId) async {
    await _runAction(() async {
      await _managerRepository.recruit(managerId);
      await _load();
    }, successMessage: 'Manager recruited.');
  }

  Future<void> _assign(String assetId, String slot) async {
    await _runAction(() async {
      await _managerRepository.assign(assetId, slot);
      await _load();
    }, successMessage: 'Manager assigned.');
  }

  Future<void> _release(String assetId) async {
    await _runAction(() async {
      await _managerRepository.release(assetId);
      await _load();
    }, successMessage: 'Manager released.');
  }

  Future<void> _listForSale(String assetId) async {
    final TextEditingController priceController =
        TextEditingController(text: '100.0000');
    final String? price = await showDialog<String>(
      context: context,
      builder: (BuildContext context) => AlertDialog(
        title: const Text('List manager for trade'),
        content: TextField(
          controller: priceController,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(labelText: 'Asking price GTEX Coin'),
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(priceController.text.trim()),
            child: const Text('List'),
          ),
        ],
      ),
    );
    if (price == null || price.isEmpty) {
      return;
    }
    await _runAction(() async {
      await _managerRepository.createListing(assetId, price);
      await _load();
    }, successMessage: 'Manager listed for trade.');
  }

  Future<void> _buy(String listingId) async {
    await _runAction(() async {
      await _managerRepository.buyListing(listingId);
      await _load();
    }, successMessage: 'Trade completed.');
  }

  Future<void> _cancelListing(String listingId) async {
    await _runAction(() async {
      await _managerRepository.cancelListing(listingId);
      await _load();
    }, successMessage: 'Listing cancelled.');
  }

  Future<void> _swapForListing(String requestedAssetId) async {
    final List<Map<String, dynamic>> bench =
        ((_team?['bench'] as List<dynamic>? ?? <dynamic>[])
            .cast<Map<String, dynamic>>());
    final List<Map<String, dynamic>> owned = <Map<String, dynamic>>[
      if (_team?['main_manager'] != null)
        (_team?['main_manager'] as Map<String, dynamic>),
      if (_team?['academy_manager'] != null)
        (_team?['academy_manager'] as Map<String, dynamic>),
      ...bench,
    ];
    if (owned.isEmpty) {
      AppFeedback.showError(context, 'Recruit at least one manager before offering a swap.');
      return;
    }
    String proposerAssetId = (owned.first['asset_id'] ?? '').toString();
    final TextEditingController cashController = TextEditingController(text: '0');
    final Map<String, dynamic>? result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (BuildContext context) => StatefulBuilder(
        builder: (
          BuildContext context,
          void Function(void Function()) setDialogState,
        ) {
          return AlertDialog(
            title: const Text('Offer manager swap'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                DropdownButtonFormField<String>(
                  value: proposerAssetId,
                  decoration: const InputDecoration(labelText: 'Your manager'),
                  items: owned
                      .map(
                        (Map<String, dynamic> item) => DropdownMenuItem<String>(
                          value: (item['asset_id'] ?? '').toString(),
                          child: Text((item['display_name'] ?? '').toString()),
                        ),
                      )
                      .toList(),
                  onChanged: (String? value) {
                    if (value == null) {
                      return;
                    }
                    setDialogState(() {
                      proposerAssetId = value;
                    });
                  },
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: cashController,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration:
                      const InputDecoration(labelText: 'Cash adjustment (optional)'),
                ),
              ],
            ),
            actions: <Widget>[
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Cancel'),
              ),
              FilledButton(
                onPressed: () => Navigator.of(context).pop(
                  <String, dynamic>{
                    'proposer_asset_id': proposerAssetId,
                    'cash_adjustment_credits': cashController.text.trim().isEmpty
                        ? '0'
                        : cashController.text.trim(),
                  },
                ),
                child: const Text('Submit'),
              ),
            ],
          );
        },
      ),
    );
    if (result == null) {
      return;
    }
    await _runAction(() async {
      await _managerRepository.swap(
        result['proposer_asset_id'].toString(),
        requestedAssetId,
        result['cash_adjustment_credits'].toString(),
      );
      await _load();
    }, successMessage: 'Swap completed.');
  }

  Widget _filterDropdown(
    String label,
    String? value,
    List<String> options,
    ValueChanged<String?> onChanged,
  ) {
    return DropdownButtonFormField<String?>(
      value: value,
      decoration: InputDecoration(labelText: label),
      items: <DropdownMenuItem<String?>>[
        const DropdownMenuItem<String?>(value: null, child: Text('All')),
        ...options.map(
          (String item) => DropdownMenuItem<String?>(
            value: item,
            child: Text(item),
          ),
        ),
      ],
      onChanged: onChanged,
    );
  }

  Widget _sectionHeader(String title, {String? subtitle, Widget? trailing}) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: <Widget>[
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                title,
                style:
                    const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              if (subtitle != null) ...<Widget>[
                const SizedBox(height: 4),
                Text(subtitle, style: Theme.of(context).textTheme.bodySmall),
              ],
            ],
          ),
        ),
        if (trailing != null) trailing,
      ],
    );
  }

  Widget _stateCard({
    required IconData icon,
    required String title,
    required String message,
    String? actionLabel,
    VoidCallback? onAction,
    Color accent = GteShellTheme.accentWarm,
    String? eyebrow,
    bool isLoading = false,
  }) {
    return GteStatePanel(
      eyebrow: eyebrow,
      title: title,
      message: message,
      actionLabel: actionLabel,
      onAction: onAction,
      icon: icon,
      accentColor: accent,
      isLoading: isLoading,
    );
  }

  Widget _buildTeamSection() {
    final Map<String, dynamic>? mainManager =
        _team?['main_manager'] as Map<String, dynamic>?;
    final Map<String, dynamic>? academyManager =
        _team?['academy_manager'] as Map<String, dynamic>?;
    final List<Map<String, dynamic>> bench =
        ((_team?['bench'] as List<dynamic>? ?? <dynamic>[])
            .cast<Map<String, dynamic>>());

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: <Widget>[
            _sectionHeader(
              'Your managers',
              subtitle:
                  'Max two active slots: main team and academy. Bench holdings can still be traded or promoted.',
            ),
            const SizedBox(height: 12),
            if (_team == null)
              _stateCard(
                icon: Icons.sports_soccer_outlined,
                eyebrow: 'TEAM TOUCHLINE',
                title: 'Manager assignment view is unavailable',
                message: 'Your squad manager view could not be loaded yet.',
                actionLabel: 'Retry',
                onAction: _load,
              )
            else ...<Widget>[
              _slotTile('Main team', mainManager),
              _slotTile('Academy', academyManager),
              if (bench.isNotEmpty) ...<Widget>[
                const Divider(height: 24),
                _sectionHeader('Bench managers'),
                const SizedBox(height: 8),
                ...bench.map(_benchTile),
              ] else
                _stateCard(
                  icon: Icons.event_seat_outlined,
                  eyebrow: 'BENCH OUTLOOK',
                  title: 'No reserve coaches are waiting on the bench',
                  message:
                      'Recruit a manager from the catalog to keep tactical options waiting in the tunnel.',
                ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _slotTile(String label, Map<String, dynamic>? item) {
    if (item == null) {
      return ListTile(
        leading: const Icon(Icons.person_off_outlined),
        title: Text('$label manager'),
        subtitle: const Text('No manager assigned to this slot yet. Bench managers can be promoted here instantly.'),
      );
    }
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: const CircleAvatar(child: Icon(Icons.person)),
      title: Text((item['display_name'] ?? '').toString()),
      subtitle: Text(
        '$label • ${(item['mentality'] ?? '').toString()} • ${(item['tactics'] as List<dynamic>? ?? <dynamic>[]).join(', ')}',
      ),
      trailing: PopupMenuButton<String>(
        onSelected: (String value) async {
          switch (value) {
            case 'release':
              await _release((item['asset_id'] ?? '').toString());
              break;
            case 'list':
              await _listForSale((item['asset_id'] ?? '').toString());
              break;
            case 'main':
              await _assign((item['asset_id'] ?? '').toString(), 'main');
              break;
            case 'academy':
              await _assign((item['asset_id'] ?? '').toString(), 'academy');
              break;
          }
        },
        itemBuilder: (BuildContext context) => <PopupMenuEntry<String>>[
          if (label != 'Main team')
            const PopupMenuItem<String>(
              value: 'main',
              child: Text('Promote to main'),
            ),
          if (label != 'Academy')
            const PopupMenuItem<String>(
              value: 'academy',
              child: Text('Move to academy'),
            ),
          const PopupMenuItem<String>(value: 'list', child: Text('List for trade')),
          const PopupMenuItem<String>(value: 'release', child: Text('Release')),
        ],
      ),
    );
  }

  Widget _benchTile(Map<String, dynamic> item) {
    return ListTile(
      contentPadding: EdgeInsets.zero,
      title: Text((item['display_name'] ?? '').toString()),
      subtitle: Text(
        '${(item['mentality'] ?? '').toString()} • ${(item['traits'] as List<dynamic>? ?? <dynamic>[]).join(', ')}',
      ),
      trailing: PopupMenuButton<String>(
        onSelected: (String value) async {
          switch (value) {
            case 'main':
              await _assign((item['asset_id'] ?? '').toString(), 'main');
              break;
            case 'academy':
              await _assign((item['asset_id'] ?? '').toString(), 'academy');
              break;
            case 'list':
              await _listForSale((item['asset_id'] ?? '').toString());
              break;
            case 'release':
              await _release((item['asset_id'] ?? '').toString());
              break;
          }
        },
        itemBuilder: (BuildContext context) => const <PopupMenuEntry<String>>[
          PopupMenuItem<String>(value: 'main', child: Text('Assign to main')),
          PopupMenuItem<String>(value: 'academy', child: Text('Assign to academy')),
          PopupMenuItem<String>(value: 'list', child: Text('List for trade')),
          PopupMenuItem<String>(value: 'release', child: Text('Release')),
        ],
      ),
    );
  }

  Widget _buildCatalogSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: <Widget>[
            _sectionHeader(
              'Manager catalog',
              subtitle:
                  'Legendary copies are scarce, elite active managers are rarer, and every pick carries tactical flavor rather than base price value.',
              trailing: Text('${_catalog.length} loaded'),
            ),
            const SizedBox(height: 12),
            if (_catalog.isEmpty)
              _stateCard(
                icon: Icons.search_off,
                eyebrow: 'CATALOG FILTERS',
                title: 'No coaches matched this market view',
                message:
                    'Try clearing one or more filters. The coach catalog is sourced from the live manager seed pool and will repopulate once this view is widened.',
                actionLabel: 'Clear filters',
                onAction: () {
                  setState(() {
                    _tactic = null;
                    _trait = null;
                    _mentality = null;
                    _rarity = null;
                    _searchController.clear();
                  });
                  _load();
                },
              )
            else
              ..._catalog.take(120).map((Map<String, dynamic> item) {
                final int supplyAvailable = (item['supply_available'] ?? 0) as int? ?? 0;
                return ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text((item['display_name'] ?? '').toString()),
                  subtitle: Text(
                    '${(item['rarity'] ?? '').toString()} • ${(item['mentality'] ?? '').toString()} • '
                    'tactics: ${(item['tactics'] as List<dynamic>? ?? <dynamic>[]).join(', ')}\n'
                    'traits: ${(item['traits'] as List<dynamic>? ?? <dynamic>[]).join(', ')}',
                  ),
                  isThreeLine: true,
                  trailing: FilledButton.tonal(
                    onPressed: supplyAvailable > 0 && !_isRunningAction
                        ? () => _recruit((item['manager_id'] ?? '').toString())
                        : null,
                    child: Text(supplyAvailable > 0 ? 'Recruit' : 'Sold out'),
                  ),
                );
              }),
          ],
        ),
      ),
    );
  }

  Widget _buildListingSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: <Widget>[
            _sectionHeader(
              'Trade listings',
              subtitle:
                  'Peer-to-peer manager trades settle immediately. The platform fee comes out of the trade amount, not the manager base value.',
              trailing: Text('${_listings.length} live'),
            ),
            const SizedBox(height: 12),
            if (_listings.isEmpty)
              _stateCard(
                icon: Icons.storefront_outlined,
                title: 'No active listings',
                message:
                    'Nobody has listed a manager yet. Put one of your bench managers on the board to start the bazaar.',
              )
            else
              ..._listings.map((Map<String, dynamic> item) {
                final bool isOwnListing = _myListings.any(
                  (Map<String, dynamic> myItem) =>
                      myItem['listing_id'].toString() ==
                      item['listing_id'].toString(),
                );
                return ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text((item['display_name'] ?? '').toString()),
                  subtitle: Text(
                    'Seller: ${(item['seller_name'] ?? '').toString()} • Ask: ${(item['asking_price_credits'] ?? '').toString()} GTEX Coin',
                  ),
                  trailing: Wrap(
                    spacing: 8,
                    children: <Widget>[
                      if (isOwnListing)
                        OutlinedButton(
                          onPressed: _isRunningAction
                              ? null
                              : () => _cancelListing((item['listing_id'] ?? '').toString()),
                          child: const Text('Cancel'),
                        )
                      else ...<Widget>[
                        FilledButton.tonal(
                          onPressed: _isRunningAction
                              ? null
                              : () => _swapForListing((item['asset_id'] ?? '').toString()),
                          child: const Text('Swap'),
                        ),
                        FilledButton(
                          onPressed: _isRunningAction
                              ? null
                              : () => _buy((item['listing_id'] ?? '').toString()),
                          child: const Text('Buy'),
                        ),
                      ],
                    ],
                  ),
                );
              }),
          ],
        ),
      ),
    );
  }

  Widget _buildRecommendationSection() {
    final String summary =
        (_recommendation?['summary'] ?? 'No recommendation loaded yet.')
            .toString();
    final String positions =
        ((_recommendation?['recommended_positions'] as List<dynamic>? ?? <dynamic>[])
            .join(' • '));
    final String actions =
        ((_recommendation?['suggested_actions'] as List<dynamic>? ?? <dynamic>[])
            .join(' • '));
    final String rationale =
        ((_recommendation?['rationale'] as List<dynamic>? ?? <dynamic>[]).join(' • '));
    final String risks =
        ((_recommendation?['risk_flags'] as List<dynamic>? ?? <dynamic>[]).join(' • '));
    final int fitScore = (_recommendation?['style_fit_score'] as int?) ?? 0;
    final String selectedTactic = (_recommendation?['selected_tactic'] ?? 'manual').toString();

    return Card(
      child: ListTile(
        leading: const Icon(Icons.psychology_alt_outlined),
        title: const Text('Manager recommendation'),
        subtitle: Text(
          '$summary\n\nPrimary tactic: $selectedTactic • Style fit: $fitScore/99\n'
          'Priority positions: ${positions.isEmpty ? 'None yet' : positions}\n'
          'Suggested actions: ${actions.isEmpty ? 'None yet' : actions}\n'
          'Rationale: ${rationale.isEmpty ? 'Still calculating.' : rationale}\n'
          'Risks: ${risks.isEmpty ? 'No major tactical warnings.' : risks}',
        ),
        isThreeLine: true,
      ),
    );
  }

  Widget _buildComparisonCard() {
    final Map<String, dynamic>? comparison = _comparison;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            _sectionHeader('Manager comparison', subtitle: 'Pit two tactical identities against each other before you recruit or trade.'),
            const SizedBox(height: 12),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: <Widget>[
                SizedBox(
                  width: 220,
                  child: DropdownButtonFormField<String>(
                    value: _compareLeftManagerId,
                    decoration: const InputDecoration(labelText: 'Left manager'),
                    items: _catalog.take(80).map((Map<String, dynamic> item) => DropdownMenuItem<String>(
                      value: (item['manager_id'] ?? '').toString(),
                      child: Text((item['display_name'] ?? '').toString()),
                    )).toList(),
                    onChanged: (String? value) {
                      setState(() => _compareLeftManagerId = value);
                      _loadComparison();
                    },
                  ),
                ),
                SizedBox(
                  width: 220,
                  child: DropdownButtonFormField<String>(
                    value: _compareRightManagerId,
                    decoration: const InputDecoration(labelText: 'Right manager'),
                    items: _catalog.take(80).map((Map<String, dynamic> item) => DropdownMenuItem<String>(
                      value: (item['manager_id'] ?? '').toString(),
                      child: Text((item['display_name'] ?? '').toString()),
                    )).toList(),
                    onChanged: (String? value) {
                      setState(() => _compareRightManagerId = value);
                      _loadComparison();
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (comparison == null)
              const Text('Choose two managers to compare tactical overlap and style fit.')
            else
              Text(
                '${(comparison['left_name'] ?? '').toString()} fit ${(comparison['style_fit_left'] ?? 0).toString()} vs '
                '${(comparison['right_name'] ?? '').toString()} fit ${(comparison['style_fit_right'] ?? 0).toString()}\n'
                'Tactic overlap: ${((comparison['tactic_overlap'] as List<dynamic>? ?? <dynamic>[]).join(', '))}\n'
                'Trait overlap: ${((comparison['trait_overlap'] as List<dynamic>? ?? <dynamic>[]).join(', '))}\n'
                'Verdict: ${(comparison['verdict'] ?? '').toString()}',
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildHistoryCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: <Widget>[
            _sectionHeader('Manager trade history', subtitle: 'Recent settlement trails for your manager market journey.'),
            const SizedBox(height: 12),
            if (_tradeHistory.isEmpty)
              _stateCard(
                icon: Icons.history_toggle_off,
                title: 'No trade history yet',
                message: 'Complete a manager trade or swap to start filling this ledger trail.',
              )
            else
              ..._tradeHistory.take(12).map((Map<String, dynamic> entry) => ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text((entry['display_name'] ?? 'Unknown manager').toString()),
                subtitle: Text('Mode: ${(entry['mode'] ?? '').toString()} • Gross: ${(entry['gross_credits'] ?? '').toString()} GTEX Coin • Fee: ${(entry['fee_credits'] ?? '').toString()} GTEX Coin'),
                trailing: Text((entry['settlement_status'] ?? '').toString()),
              )),
          ],
        ),
      ),
    );
  }

  Widget _buildRuntimeCard() {
    return Card(
      child: ListTile(
        leading: Icon((_fastLeagueRuntime?['can_run'] ?? false)
            ? Icons.emoji_events_outlined
            : Icons.pause_circle_outline),
        title: const Text('Fast League runtime check'),
        subtitle: Text(
          '${(_fastLeagueRuntime?['reason'] ?? 'Runtime check unavailable.').toString()}\n'
          'Fallback used: ${((_fastLeagueRuntime?['fallback_used'] ?? false) as bool) ? 'Yes' : 'No'} • '
          'Preview fixtures: ${((_fastLeagueRuntime?['schedule_preview'] as List<dynamic>? ?? <dynamic>[]).length).toString()}',
        ),
        trailing: Text(
          'Min ${(_fastLeagueRuntime?['minimum_viable_participants'] ?? 2).toString()}',
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final bool hasFilters =
        _tactic != null ||
        _trait != null ||
        _mentality != null ||
        _rarity != null ||
        _searchController.text.trim().isNotEmpty;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Coach Exchange'),
        actions: <Widget>[
          if (widget.isAdmin)
            IconButton(
              tooltip: 'Admin manager controls',
              onPressed: widget.onOpenAdmin,
              icon: const Icon(Icons.tune),
            ),
          IconButton(
            tooltip: 'Refresh market',
            onPressed: _isLoading ? null : _load,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: _isLoading
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: _stateCard(
                  eyebrow: 'MANAGER MARKET',
                  icon: Icons.manage_accounts_outlined,
                  title: 'Loading dugout exchange',
                  message: 'Coach profiles, listings, tactical fit, and runtime checks are being arranged into one premium desk.',
                  actionLabel: 'Refreshing market',
                  onAction: null,
                  accent: GteShellTheme.accentWarm,
                  isLoading: true,
                ),
              ),
            )
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: _stateCard(
                      icon: Icons.warning_amber_rounded,
                      title: 'Manager market unavailable',
                      message: _error!,
                      actionLabel: 'Retry',
                      onAction: _load,
                    ),
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: <Widget>[
                      GteSurfacePanel(
                        accentColor: GteShellTheme.accentWarm,
                        emphasized: true,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(
                              'MANAGER MARKET',
                              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                                color: GteShellTheme.accentWarm,
                                letterSpacing: 1.1,
                              ),
                            ),
                            const SizedBox(height: 10),
                            Text(
                              'Trade tactical identity, not just names on a card.',
                              style: Theme.of(context).textTheme.headlineSmall,
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'This lane stays distinct from player trading by foregrounding mentality, tactical fit, and dugout influence. Filter the board, compare profiles, then move decisively.',
                              style: Theme.of(context).textTheme.bodyMedium,
                            ),
                            const SizedBox(height: 14),
                            Wrap(
                              spacing: 10,
                              runSpacing: 10,
                              children: const <Widget>[
                                Chip(label: Text('Tactical fit first')),
                                Chip(label: Text('Compare dugouts')),
                                Chip(label: Text('Listings and swaps')),
                              ],
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),
                      TextField(
                        controller: _searchController,
                        decoration: InputDecoration(
                          labelText: 'Search managers',
                          helperText:
                              'Filter by manager name, style, or profile keywords.',
                          suffixIcon: IconButton(
                            onPressed: _load,
                            icon: const Icon(Icons.search),
                          ),
                        ),
                        onSubmitted: (_) => _load(),
                      ),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: <Widget>[
                          SizedBox(
                            width: 180,
                            child: _filterDropdown(
                              'Tactic',
                              _tactic,
                              _tactics,
                              (String? value) {
                                setState(() => _tactic = value);
                                _load();
                              },
                            ),
                          ),
                          SizedBox(
                            width: 180,
                            child: _filterDropdown(
                              'Trait',
                              _trait,
                              _traits,
                              (String? value) {
                                setState(() => _trait = value);
                                _load();
                              },
                            ),
                          ),
                          SizedBox(
                            width: 180,
                            child: _filterDropdown(
                              'Mentality',
                              _mentality,
                              _mentalities,
                              (String? value) {
                                  setState(() => _mentality = value);
                                  _load();
                                },
                            ),
                          ),
                          SizedBox(
                            width: 180,
                            child: _filterDropdown(
                              'Rarity',
                              _rarity,
                              _rarities,
                              (String? value) {
                                setState(() => _rarity = value);
                                _load();
                              },
                            ),
                          ),
                          OutlinedButton.icon(
                            onPressed: hasFilters
                                ? () {
                                    setState(() {
                                      _tactic = null;
                                      _trait = null;
                                      _mentality = null;
                                      _rarity = null;
                                      _searchController.clear();
                                    });
                                    _load();
                                  }
                                : null,
                            icon: const Icon(Icons.clear),
                            label: const Text('Clear filters'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      if (_isRunningAction) ...<Widget>[
                        const LinearProgressIndicator(),
                        const SizedBox(height: 16),
                      ],
                      _buildRecommendationSection(),
                      const SizedBox(height: 16),
                      _buildRuntimeCard(),
                      const SizedBox(height: 16),
                      _buildComparisonCard(),
                      const SizedBox(height: 16),
                      _buildTeamSection(),
                      const SizedBox(height: 16),
                      _buildCatalogSection(),
                      const SizedBox(height: 16),
                      _buildListingSection(),
                      const SizedBox(height: 16),
                      _buildHistoryCard(),
                      if (_myListings.isNotEmpty) ...<Widget>[
                        const SizedBox(height: 16),
                        Card(
                          child: Padding(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              children: <Widget>[
                                _sectionHeader(
                                  'My listings',
                                  subtitle:
                                      'These are live listings created from your squad inventory.',
                                ),
                                const SizedBox(height: 12),
                                ..._myListings.map(
                                  (Map<String, dynamic> item) => ListTile(
                                    contentPadding: EdgeInsets.zero,
                                    title: Text(
                                      (item['display_name'] ?? '').toString(),
                                    ),
                                    subtitle: Text(
                                      'Ask ${(item['asking_price_credits'] ?? '').toString()} GTEX Coin',
                                    ),
                                    trailing: OutlinedButton(
                                      onPressed: _isRunningAction
                                          ? null
                                          : () => _cancelListing(
                                                (item['listing_id'] ?? '')
                                                    .toString(),
                                              ),
                                      child: const Text('Cancel'),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
    );
  }
}
