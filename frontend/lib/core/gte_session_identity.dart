import '../data/gte_models.dart';
import '../providers/gte_exchange_controller.dart';

class GteSessionIdentity {
  const GteSessionIdentity({
    required this.userId,
    this.userName,
    this.clubId,
    this.clubName,
  });

  final String userId;
  final String? userName;
  final String? clubId;
  final String? clubName;

  static GteSessionIdentity fromExchangeController(
    GteExchangeController controller, {
    String guestUserId = 'guest-user',
  }) {
    final GteAuthSession? session = controller.session;
    final String? trimmedSessionUserId = controller.session?.user.id.trim();
    final String resolvedUserId =
        trimmedSessionUserId != null && trimmedSessionUserId.isNotEmpty
            ? trimmedSessionUserId
            : guestUserId;
    final String? resolvedName = _resolvedUserName(controller);
    final _ResolvedClub? resolvedClub = _resolvedClub(session);
    return GteSessionIdentity(
      userId: resolvedUserId,
      userName: resolvedName,
      clubId: resolvedClub?.id,
      clubName: resolvedClub?.displayName,
    );
  }

  static String? _resolvedUserName(GteExchangeController controller) {
    final String? displayName = controller.session?.user.displayName?.trim();
    if (displayName != null && displayName.isNotEmpty) {
      return displayName;
    }
    final String? username = controller.session?.user.username.trim();
    if (username != null && username.isNotEmpty) {
      return username;
    }
    return null;
  }

  static _ResolvedClub? _resolvedClub(GteAuthSession? session) {
    if (session == null) {
      return null;
    }
    final List<Map<String, Object?>> sources = <Map<String, Object?>>[
      if (session.rawJson.isNotEmpty) session.rawJson,
      if (session.user.rawJson.isNotEmpty) session.user.rawJson,
    ];
    for (final Map<String, Object?> source in sources) {
      final _ResolvedClub? currentClub = _enrichClubCandidate(
        source,
        _currentClubCandidate(source),
      );
      if (currentClub != null) {
        return currentClub;
      }
    }
    for (final Map<String, Object?> source in sources) {
      final _ResolvedClub? directClub = _enrichClubCandidate(
        source,
        _directClubCandidate(source),
      );
      if (directClub != null) {
        return directClub;
      }
    }
    for (final Map<String, Object?> source in sources) {
      final _ResolvedClub? membershipClub = _collectionClubCandidate(source);
      if (membershipClub != null) {
        return membershipClub;
      }
    }
    return null;
  }

  static _ResolvedClub? _currentClubCandidate(Map<String, Object?> source) {
    return _mergeClubCandidates(
      _candidateFromDirectFields(
        source,
        idKeys: const <String>['current_club_id', 'currentClubId'],
        nameKeys: const <String>['current_club_name', 'currentClubName'],
        slugKeys: const <String>['current_club_slug', 'currentClubSlug'],
      ),
      _candidateFromClubObject(
        _mapValue(source, const <String>['current_club', 'currentClub']),
      ),
    );
  }

  static _ResolvedClub? _directClubCandidate(Map<String, Object?> source) {
    return _mergeClubCandidates(
      _candidateFromDirectFields(
        source,
        idKeys: const <String>['club_id', 'clubId'],
        nameKeys: const <String>['club_name', 'clubName'],
        slugKeys: const <String>['club_slug', 'clubSlug'],
      ),
      _candidateFromClubObject(_mapValue(source, const <String>['club'])),
    );
  }

  static _ResolvedClub? _collectionClubCandidate(Map<String, Object?> source) {
    for (final String key in const <String>[
      'memberships',
      'club_memberships',
      'clubMemberships',
      'managed_clubs',
      'managedClubs',
      'owned_clubs',
      'ownedClubs',
    ]) {
      final List<Object?> items = _listValue(source[key]);
      if (items.isEmpty) {
        continue;
      }
      for (final Object? item in items) {
        if (_isCurrentMembership(item)) {
          final _ResolvedClub? candidate = _candidateFromMembershipEntry(item);
          if (candidate != null) {
            return candidate;
          }
        }
      }
      for (final Object? item in items) {
        final _ResolvedClub? candidate = _candidateFromMembershipEntry(item);
        if (candidate != null) {
          return candidate;
        }
      }
    }
    return null;
  }

  static _ResolvedClub? _enrichClubCandidate(
    Map<String, Object?> source,
    _ResolvedClub? candidate,
  ) {
    if (candidate == null) {
      return null;
    }
    return _mergeClubCandidates(
      candidate,
      _findMatchingClubCandidate(source, candidate.id),
    );
  }

  static _ResolvedClub? _findMatchingClubCandidate(
    Map<String, Object?> source,
    String clubId,
  ) {
    final List<_ResolvedClub?> candidates = <_ResolvedClub?>[
      _currentClubCandidate(source),
      _directClubCandidate(source),
    ];
    for (final _ResolvedClub? candidate in candidates) {
      if (candidate != null && candidate.id == clubId) {
        return candidate;
      }
    }
    for (final String key in const <String>[
      'memberships',
      'club_memberships',
      'clubMemberships',
      'managed_clubs',
      'managedClubs',
      'owned_clubs',
      'ownedClubs',
    ]) {
      final List<Object?> items = _listValue(source[key]);
      for (final Object? item in items) {
        final _ResolvedClub? candidate = _candidateFromMembershipEntry(item);
        if (candidate != null && candidate.id == clubId) {
          return candidate;
        }
      }
    }
    return null;
  }

  static _ResolvedClub? _candidateFromMembershipEntry(Object? value) {
    if (value is String) {
      final String trimmed = value.trim();
      if (trimmed.isEmpty) {
        return null;
      }
      return _ResolvedClub(id: trimmed);
    }
    final Map<String, Object?>? entry = _mapValue(value, const <String>[]);
    if (entry == null) {
      return null;
    }
    return _mergeClubCandidates(
      _candidateFromDirectFields(
        entry,
        idKeys: const <String>['club_id', 'clubId'],
        nameKeys: const <String>['club_name', 'clubName'],
        slugKeys: const <String>['club_slug', 'clubSlug', 'slug'],
      ),
      _candidateFromClubObject(_mapValue(entry, const <String>['club'])),
    );
  }

  static _ResolvedClub? _candidateFromDirectFields(
    Map<String, Object?> source, {
    required List<String> idKeys,
    required List<String> nameKeys,
    required List<String> slugKeys,
  }) {
    final String? id = _firstString(source, idKeys);
    if (id == null) {
      return null;
    }
    return _ResolvedClub(
      id: id,
      name: _firstString(source, nameKeys),
      slug: _firstString(source, slugKeys),
    );
  }

  static _ResolvedClub? _candidateFromClubObject(Map<String, Object?>? source) {
    if (source == null) {
      return null;
    }
    final String? id = _firstString(
      source,
      const <String>['id', 'club_id', 'clubId'],
    );
    if (id == null) {
      return null;
    }
    return _ResolvedClub(
      id: id,
      name: _firstString(
        source,
        const <String>['name', 'club_name', 'clubName', 'display_name'],
      ),
      slug: _firstString(source, const <String>['slug', 'club_slug']),
    );
  }

  static _ResolvedClub? _mergeClubCandidates(
    _ResolvedClub? primary,
    _ResolvedClub? secondary,
  ) {
    if (primary == null) {
      return secondary;
    }
    if (secondary == null || secondary.id != primary.id) {
      return primary;
    }
    return _ResolvedClub(
      id: primary.id,
      name: primary.name ?? secondary.name,
      slug: primary.slug ?? secondary.slug,
    );
  }

  static bool _isCurrentMembership(Object? value) {
    final Map<String, Object?>? entry = _mapValue(value, const <String>[]);
    if (entry == null) {
      return false;
    }
    for (final String key in const <String>[
      'is_current',
      'isCurrent',
      'current',
      'is_primary',
      'isPrimary',
      'primary',
    ]) {
      final Object? rawValue = entry[key];
      if (rawValue is bool && rawValue) {
        return true;
      }
      if (rawValue != null &&
          rawValue.toString().trim().toLowerCase() == 'true') {
        return true;
      }
    }
    return false;
  }

  static Map<String, Object?>? _mapValue(
    Object? value,
    List<String> keys,
  ) {
    if (keys.isNotEmpty) {
      value = GteJson.value(
          GteJson.map(value, fallback: const <String, Object?>{}), keys);
    }
    if (value is Map<String, Object?>) {
      return value;
    }
    if (value is Map) {
      return value.map(
        (Object? key, Object? entryValue) =>
            MapEntry<String, Object?>(key.toString(), entryValue),
      );
    }
    return null;
  }

  static List<Object?> _listValue(Object? value) {
    if (value is List<Object?>) {
      return value;
    }
    if (value is List) {
      return value.cast<Object?>();
    }
    return const <Object?>[];
  }

  static String? _firstString(
    Map<String, Object?> source,
    List<String> keys,
  ) {
    final String? value = GteJson.stringOrNull(source, keys);
    if (value == null || value.isEmpty) {
      return null;
    }
    return value;
  }
}

class _ResolvedClub {
  const _ResolvedClub({
    required this.id,
    this.name,
    this.slug,
  });

  final String id;
  final String? name;
  final String? slug;

  String? get displayName {
    final String? trimmedName = name?.trim();
    if (trimmedName != null && trimmedName.isNotEmpty) {
      return trimmedName;
    }
    final String? trimmedSlug = slug?.trim();
    if (trimmedSlug != null && trimmedSlug.isNotEmpty) {
      return trimmedSlug;
    }
    return null;
  }
}
