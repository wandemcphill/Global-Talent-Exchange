class AuthSession {
  const AuthSession({
    required this.userId,
    required this.accessToken,
    required this.sessionId,
    this.role = 'guest',
    this.permissions = const <String>[],
    this.userName,
    this.displayName,
    this.clubId,
    this.clubName,
    this.federationId,
    this.federationName,
    this.rawJson = const <String, Object?>{},
  });

  final String userId;
  final String accessToken;
  final String sessionId;
  final String role;
  final List<String> permissions;
  final String? userName;
  final String? displayName;
  final String? clubId;
  final String? clubName;
  final String? federationId;
  final String? federationName;
  final Map<String, Object?> rawJson;

  bool get isAuthenticated => accessToken.trim().isNotEmpty;

  String get normalizedRole => role.trim().toLowerCase();

  Set<String> get normalizedPermissions =>
      permissions
          .map((String value) => value.trim().toLowerCase())
          .where((String value) => value.isNotEmpty)
          .toSet();

  bool get isSuperAdmin =>
      normalizedRole == 'super_admin' || normalizedRole == 'god_mode';

  bool get isDelegatedAdmin =>
      normalizedRole == 'admin' || normalizedRole == 'scoped_admin';

  bool get isAdmin => isSuperAdmin || isDelegatedAdmin;

  bool hasPermission(String permission) {
    final String normalized = permission.trim().toLowerCase();
    if (normalized.isEmpty) {
      return false;
    }
    return normalizedPermissions.contains(normalized);
  }

  bool hasAnyPermission(Iterable<String> values) {
    for (final String value in values) {
      if (hasPermission(value)) {
        return true;
      }
    }
    return false;
  }

  bool get canAccessGodMode => isAuthenticated && isAdmin;

  String get resolvedUserName {
    final String? display = displayName?.trim();
    if (display != null && display.isNotEmpty) {
      return display;
    }
    final String? user = userName?.trim();
    if (user != null && user.isNotEmpty) {
      return user;
    }
    return 'Guest';
  }

  factory AuthSession.fromJson(Map<String, Object?> json) {
    final Map<String, Object?> persistedRaw =
        _mapValue(json['raw_json'] ?? json['rawJson']) ??
        const <String, Object?>{};
    final Map<String, Object?> user =
        _mapValue(
          json['user'] ?? json['current_user'] ?? persistedRaw['user'],
        ) ??
        const <String, Object?>{};
    final Map<String, Object?> mergedRaw = <String, Object?>{
      ...persistedRaw,
      ...json,
      if (user.isNotEmpty) 'user': user,
    };
    final _ResolvedClub? club = _resolveClub(mergedRaw, user);
    final _ResolvedFederation? federation = _resolveFederation(mergedRaw, user);
    return AuthSession(
      userId:
          _firstString(mergedRaw, const <String>['user_id', 'userId', 'id']) ??
          _firstString(user, const <String>['id']) ??
          '',
      accessToken:
          _firstString(mergedRaw, const <String>[
            'access_token',
            'accessToken',
          ]) ??
          '',
      sessionId:
          _firstString(mergedRaw, const <String>['session_id', 'sessionId']) ??
          '',
      role:
          _firstString(mergedRaw, const <String>['role']) ??
          _firstString(user, const <String>['role']) ??
          'guest',
      permissions: _stringList(mergedRaw['permissions'] ?? user['permissions']),
      userName:
          _firstString(mergedRaw, const <String>[
            'username',
            'user_name',
            'userName',
          ]) ??
          _firstString(user, const <String>['username']),
      displayName:
          _firstString(mergedRaw, const <String>[
            'display_name',
            'displayName',
            'full_name',
          ]) ??
          _firstString(user, const <String>[
            'display_name',
            'displayName',
            'full_name',
          ]),
      clubId: club?.id,
      clubName: club?.displayName,
      federationId: federation?.id,
      federationName: federation?.displayName,
      rawJson: Map<String, Object?>.unmodifiable(mergedRaw),
    );
  }

  factory AuthSession.fromTokenPayload(Map<String, Object?> payload) {
    return AuthSession.fromJson(payload);
  }

  AuthSession mergeProfile(Map<String, Object?> profileJson) {
    final Map<String, Object?> nextRaw = <String, Object?>{
      ...rawJson,
      ...profileJson,
      'access_token': accessToken,
      'session_id': sessionId,
      'permissions': permissions,
      if (role.trim().isNotEmpty) 'role': role,
      if (userId.trim().isNotEmpty) 'user_id': userId,
    };
    return AuthSession.fromJson(nextRaw);
  }

  AuthSession copyWith({
    String? userId,
    String? accessToken,
    String? sessionId,
    String? role,
    List<String>? permissions,
    String? userName,
    String? displayName,
    String? clubId,
    String? clubName,
    String? federationId,
    String? federationName,
    Map<String, Object?>? rawJson,
  }) {
    return AuthSession(
      userId: userId ?? this.userId,
      accessToken: accessToken ?? this.accessToken,
      sessionId: sessionId ?? this.sessionId,
      role: role ?? this.role,
      permissions: permissions ?? this.permissions,
      userName: userName ?? this.userName,
      displayName: displayName ?? this.displayName,
      clubId: clubId ?? this.clubId,
      clubName: clubName ?? this.clubName,
      federationId: federationId ?? this.federationId,
      federationName: federationName ?? this.federationName,
      rawJson: rawJson ?? this.rawJson,
    );
  }

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'user_id': userId,
      'access_token': accessToken,
      'session_id': sessionId,
      'role': role,
      'permissions': permissions,
      if (userName != null) 'username': userName,
      if (displayName != null) 'display_name': displayName,
      if (clubId != null) 'club_id': clubId,
      if (clubName != null) 'club_name': clubName,
      if (federationId != null) 'federation_id': federationId,
      if (federationName != null) 'federation_name': federationName,
      'raw_json': rawJson,
    };
  }
}

class ClubContext {
  const ClubContext({required this.id, this.name});

  final String id;
  final String? name;
}

class FederationContext {
  const FederationContext({required this.id, this.name});

  final String id;
  final String? name;
}

String? _firstString(Map<String, Object?> source, List<String> keys) {
  for (final String key in keys) {
    final Object? value = source[key];
    if (value == null) {
      continue;
    }
    final String parsed = value.toString().trim();
    if (parsed.isNotEmpty) {
      return parsed;
    }
  }
  return null;
}

Map<String, Object?>? _mapValue(Object? value) {
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

List<Object?> _listValue(Object? value) {
  if (value is List<Object?>) {
    return value;
  }
  if (value is List) {
    return value.cast<Object?>();
  }
  return const <Object?>[];
}

List<String> _stringList(Object? value) {
  return _listValue(value)
      .map((Object? item) => item?.toString().trim() ?? '')
      .where((String item) => item.isNotEmpty)
      .toList(growable: false);
}

_ResolvedClub? _resolveClub(
  Map<String, Object?> source,
  Map<String, Object?> user,
) {
  final List<Map<String, Object?>> sources = <Map<String, Object?>>[
    source,
    if (user.isNotEmpty) user,
  ];
  for (final Map<String, Object?> current in sources) {
    final _ResolvedClub? candidate = _mergeClubCandidates(
      _clubFromFields(
        current,
        idKeys: const <String>['club_id', 'clubId', 'current_club_id'],
        nameKeys: const <String>['club_name', 'clubName', 'current_club_name'],
        slugKeys: const <String>['club_slug', 'clubSlug', 'current_club_slug'],
      ),
      _clubFromObject(current['club']),
      _clubFromObject(current['current_club'] ?? current['currentClub']),
      _clubFromActiveOrganization(current),
      _clubFromMemberships(current),
    );
    if (candidate != null) {
      return candidate;
    }
  }
  return null;
}

_ResolvedClub? _clubFromActiveOrganization(Map<String, Object?> source) {
  final String? type = _firstString(source, const <String>[
    'active_organization_type',
    'activeOrganizationType',
  ]);
  if (type != null && type.toLowerCase() != 'club') {
    return null;
  }
  return _clubFromFields(
    source,
    idKeys: const <String>['active_organization_id', 'activeOrganizationId'],
    nameKeys: const <String>[
      'active_organization_name',
      'activeOrganizationName',
    ],
    slugKeys: const <String>[
      'active_organization_slug',
      'activeOrganizationSlug',
    ],
  );
}

_ResolvedFederation? _resolveFederation(
  Map<String, Object?> source,
  Map<String, Object?> user,
) {
  final List<Map<String, Object?>> sources = <Map<String, Object?>>[
    source,
    if (user.isNotEmpty) user,
  ];
  for (final Map<String, Object?> current in sources) {
    final _ResolvedFederation? candidate = _mergeFederationCandidates(
      _federationFromFields(
        current,
        idKeys: const <String>[
          'federation_id',
          'federationId',
          'current_federation_id',
        ],
        nameKeys: const <String>[
          'federation_name',
          'federationName',
          'current_federation_name',
        ],
        slugKeys: const <String>[
          'federation_slug',
          'federationSlug',
          'current_federation_slug',
        ],
      ),
      _federationFromObject(current['federation']),
      _federationFromObject(
        current['current_federation'] ?? current['currentFederation'],
      ),
      _federationFromActiveOrganization(current),
    );
    if (candidate != null) {
      return candidate;
    }
  }
  return null;
}

_ResolvedClub? _clubFromMemberships(Map<String, Object?> source) {
  for (final String key in const <String>[
    'memberships',
    'club_memberships',
    'clubMemberships',
    'managed_clubs',
    'managedClubs',
    'owned_clubs',
    'ownedClubs',
  ]) {
    for (final Object? item in _listValue(source[key])) {
      final Map<String, Object?>? membership = _mapValue(item);
      if (membership == null) {
        continue;
      }
      final _ResolvedClub? candidate = _mergeClubCandidates(
        _clubFromFields(
          membership,
          idKeys: const <String>[
            'club_id',
            'clubId',
            'organization_id',
            'organizationId',
          ],
          nameKeys: const <String>[
            'club_name',
            'clubName',
            'organization_name',
            'organizationName',
          ],
          slugKeys: const <String>['club_slug', 'clubSlug', 'slug'],
        ),
        _clubFromObject(membership['club']),
      );
      if (candidate != null) {
        return candidate;
      }
    }
  }
  return null;
}

_ResolvedClub? _clubFromFields(
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

_ResolvedFederation? _federationFromActiveOrganization(
  Map<String, Object?> source,
) {
  final String? type = _firstString(source, const <String>[
    'active_organization_type',
    'activeOrganizationType',
  ]);
  if (type != null && type.toLowerCase() != 'federation') {
    return null;
  }
  return _federationFromFields(
    source,
    idKeys: const <String>['active_organization_id', 'activeOrganizationId'],
    nameKeys: const <String>[
      'active_organization_name',
      'activeOrganizationName',
    ],
    slugKeys: const <String>[
      'active_organization_slug',
      'activeOrganizationSlug',
    ],
  );
}

_ResolvedFederation? _federationFromFields(
  Map<String, Object?> source, {
  required List<String> idKeys,
  required List<String> nameKeys,
  required List<String> slugKeys,
}) {
  final String? id = _firstString(source, idKeys);
  if (id == null) {
    return null;
  }
  return _ResolvedFederation(
    id: id,
    name: _firstString(source, nameKeys),
    slug: _firstString(source, slugKeys),
  );
}

_ResolvedClub? _clubFromObject(Object? value) {
  final Map<String, Object?>? source = _mapValue(value);
  if (source == null) {
    return null;
  }
  return _clubFromFields(
    source,
    idKeys: const <String>['id', 'club_id', 'clubId'],
    nameKeys: const <String>['name', 'club_name', 'clubName', 'display_name'],
    slugKeys: const <String>['slug', 'club_slug', 'clubSlug'],
  );
}

_ResolvedFederation? _federationFromObject(Object? value) {
  final Map<String, Object?>? source = _mapValue(value);
  if (source == null) {
    return null;
  }
  return _federationFromFields(
    source,
    idKeys: const <String>['id', 'federation_id', 'federationId'],
    nameKeys: const <String>[
      'name',
      'federation_name',
      'federationName',
      'display_name',
    ],
    slugKeys: const <String>['slug', 'federation_slug', 'federationSlug'],
  );
}

_ResolvedClub? _mergeClubCandidates(
  _ResolvedClub? first,
  _ResolvedClub? second, [
  _ResolvedClub? third,
  _ResolvedClub? fourth,
  _ResolvedClub? fifth,
]) {
  return _mergeTwoClubs(
    _mergeTwoClubs(
      _mergeTwoClubs(_mergeTwoClubs(first, second), third),
      fourth,
    ),
    fifth,
  );
}

_ResolvedFederation? _mergeFederationCandidates(
  _ResolvedFederation? first,
  _ResolvedFederation? second, [
  _ResolvedFederation? third,
  _ResolvedFederation? fourth,
]) {
  return _mergeTwoFederations(
    _mergeTwoFederations(_mergeTwoFederations(first, second), third),
    fourth,
  );
}

_ResolvedClub? _mergeTwoClubs(_ResolvedClub? first, _ResolvedClub? second) {
  if (first == null) {
    return second;
  }
  if (second == null || second.id != first.id) {
    return first;
  }
  return _ResolvedClub(
    id: first.id,
    name: first.name ?? second.name,
    slug: first.slug ?? second.slug,
  );
}

_ResolvedFederation? _mergeTwoFederations(
  _ResolvedFederation? first,
  _ResolvedFederation? second,
) {
  if (first == null) {
    return second;
  }
  if (second == null || second.id != first.id) {
    return first;
  }
  return _ResolvedFederation(
    id: first.id,
    name: first.name ?? second.name,
    slug: first.slug ?? second.slug,
  );
}

class _ResolvedClub {
  const _ResolvedClub({required this.id, this.name, this.slug});

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

class _ResolvedFederation {
  const _ResolvedFederation({required this.id, this.name, this.slug});

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
