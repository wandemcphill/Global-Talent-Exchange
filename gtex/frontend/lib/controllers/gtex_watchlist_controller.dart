import 'package:flutter/foundation.dart';

import '../data/player_card_watchlist_api.dart';

class GtexWatchlistController extends ChangeNotifier {
  GtexWatchlistController({required this.api});

  final PlayerCardWatchlistApi api;

  List<PlayerCardWatchlistEntry> _entries = <PlayerCardWatchlistEntry>[];
  bool _isLoading = false;
  bool _isMutating = false;
  String? _error;
  DateTime? _syncedAt;

  List<PlayerCardWatchlistEntry> get entries => List<PlayerCardWatchlistEntry>.unmodifiable(_entries);
  bool get isLoading => _isLoading;
  bool get isMutating => _isMutating;
  String? get error => _error;
  DateTime? get syncedAt => _syncedAt;

  Set<String> get watchlistedPlayerIds => _entries
      .map((PlayerCardWatchlistEntry e) => e.playerId)
      .whereType<String>()
      .where((String id) => id.trim().isNotEmpty)
      .toSet();

  bool isWatchlisted(String playerId) {
    final String target = playerId.trim();
    if (target.isEmpty) {
      return false;
    }
    return watchlistedPlayerIds.contains(target);
  }

  String? watchlistIdForPlayer(String playerId) {
    final String target = playerId.trim();
    if (target.isEmpty) {
      return null;
    }
    for (final PlayerCardWatchlistEntry entry in _entries) {
      if (entry.playerId == target) {
        return entry.id;
      }
    }
    return null;
  }

  Future<void> load({bool force = false}) async {
    if (_isLoading) {
      return;
    }
    if (!force && _syncedAt != null && _error == null) {
      return;
    }

    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final List<PlayerCardWatchlistEntry> items = await api.fetchWatchlist();
      _entries = items;
      _syncedAt = DateTime.now();
      _error = null;
    } catch (err) {
      _error = 'Failed to load watchlist: ${err.toString()}';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> addToWatchlist(String playerId, {String? notes}) async {
    final String target = playerId.trim();
    if (target.isEmpty || _isMutating) {
      return false;
    }

    _isMutating = true;
    _error = null;
    notifyListeners();

    try {
      final PlayerCardWatchlistEntry entry = await api.addWatchlist(
        playerId: target,
        notes: notes,
      );
      _entries = <PlayerCardWatchlistEntry>[
        ..._entries.where((PlayerCardWatchlistEntry e) => e.playerId != target),
        entry,
      ];
      _syncedAt = DateTime.now();
      _error = null;
      return true;
    } catch (err) {
      _error = 'Could not add player to watchlist: ${err.toString()}';
      return false;
    } finally {
      _isMutating = false;
      notifyListeners();
    }
  }

  Future<bool> removeFromWatchlist(String playerId) async {
    final String target = playerId.trim();
    if (target.isEmpty || _isMutating) {
      return false;
    }

    final String? watchlistId = watchlistIdForPlayer(target);
    if (watchlistId == null) {
      // Optimistically remove if ID not matched
      _entries = _entries.where((PlayerCardWatchlistEntry e) => e.playerId != target).toList();
      notifyListeners();
      return true;
    }

    _isMutating = true;
    _error = null;
    notifyListeners();

    try {
      await api.removeWatchlist(watchlistId);
      _entries = _entries.where((PlayerCardWatchlistEntry e) => e.id != watchlistId && e.playerId != target).toList();
      _syncedAt = DateTime.now();
      _error = null;
      return true;
    } catch (err) {
      _error = 'Could not remove player from watchlist: ${err.toString()}';
      return false;
    } finally {
      _isMutating = false;
      notifyListeners();
    }
  }

  Future<bool> toggleWatchlist(String playerId, {String? notes}) async {
    if (isWatchlisted(playerId)) {
      return removeFromWatchlist(playerId);
    } else {
      return addToWatchlist(playerId, notes: notes);
    }
  }
}
