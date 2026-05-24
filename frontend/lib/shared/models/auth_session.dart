class AuthSession {
  const AuthSession({
    required this.userId,
    required this.accessToken,
    required this.refreshToken,
    required this.sessionId,
    this.role = 'guest',
    this.refreshExpiresIn = 0,
    this.permissions = const <String>[],
    this.userName,
    this.displayName,
    this.accountType = 'guest',
    this.creatorProfileId,
    this.creatorStatus,
    this.traderProfileId,
    this.traderStatus,
    this.clubId,
    this.clubName,
    this.noClub = false,
    this.noClubReason,
    this.federationId,
    this.federationName,
    this.rawJson = const <String, Object?>{},
  });

  final String userId;
  final String accessToken;
  final String refreshToken;
  final String sessionId;
  final String role;
  final int refreshExpiresIn;
  final List<String> permissions;
  final String? userName;
  final String? displayName;
  final String accountType;
  final String? creatorProfileId;
  final String? creatorStatus;
  final String? traderProfileId;
  final String? traderStatus;
  final String? clubId;
  final String? clubName;
  final bool noClub;
  final String? noClubReason;
  final String? federationId;
  final String? federationName;
  final Map<String, Object?> rawJson;

  bool get isAuthenticated => accessToken.trim().isNotEmpty;

  bool get bootstrapBlocked =>
      _boolValue(rawJson['_session_bootstrap_blocked']);

  String? get bootstrapError =>
      _firstString(rawJson, const <String>['_session_bootstrap_error']);

  String get normalizedRole => role.trim().toLowerCase();

  Set<String> get normalizedPermissions =>
      permissions
          .map((String value) => value.trim().toLowerCase())
          .where((String value) => value.isNotEmpty)
          .toSet();

  bool get isSuperAdmin => gtexIsSuperAdminRole(normalizedRole);

  bool get isDelegatedAdmin => gtexIsDelegatedAdminRole(normalizedRole);

  bool get isAdmin => gtexIsAdminRole(normalizedRole);

  bool get hasClubContext =>
      clubId != null && clubId!.trim().isNotEmpty && !noClub;

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

  bool get canAccessGodMode =>
      isAuthenticated &&
      (isSuperAdmin ||
          hasAnyPermission(const <String>[
            'view_audit_log',
            'review_audit_log',
          ]));

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
    final Map<String, Object?> onboarding =
        _mapValue(
          mergedRaw['onboarding'] ??
              mergedRaw['onboarding_state'] ??
              mergedRaw['onboardingState'] ??
              user['onboarding'],
        ) ??
        const <String, Object?>{};
    final Map<String, Object?> creatorProfile =
        _mapValue(
          mergedRaw['creator'] ??
              mergedRaw['creator_profile'] ??
              mergedRaw['creatorProfile'] ??
              user['creator'] ??
              user['creator_profile'] ??
              user['creatorProfile'],
        ) ??
        const <String, Object?>{};
    final Map<String, Object?> traderProfile =
        _mapValue(
          mergedRaw['coin_trader'] ??
              mergedRaw['coinTrader'] ??
              mergedRaw['trader_profile'] ??
              mergedRaw['traderProfile'] ??
              user['trader_profile'] ??
              user['traderProfile'] ??
              mergedRaw['coin_trader_profile'] ??
              mergedRaw['coinTraderProfile'] ??
              user['coin_trader'] ??
              user['coinTrader'] ??
              user['coin_trader_profile'] ??
              user['coinTraderProfile'],
        ) ??
        const <String, Object?>{};
    final String resolvedAccountType =
        _firstString(mergedRaw, const <String>[
          'account_type',
          'accountType',
          'type',
        ]) ??
        _firstString(user, const <String>['account_type', 'accountType']) ??
        'guest';
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
      refreshToken:
          _firstString(mergedRaw, const <String>[
            'refresh_token',
            'refreshToken',
          ]) ??
          '',
      sessionId:
          _firstString(mergedRaw, const <String>['session_id', 'sessionId']) ??
          '',
      role:
          _firstString(mergedRaw, const <String>['role']) ??
          _firstString(user, const <String>['role']) ??
          'guest',
      refreshExpiresIn: _intValue(
        mergedRaw['refresh_expires_in'] ?? mergedRaw['refreshExpiresIn'],
      ),
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
      accountType: resolvedAccountType,
      creatorProfileId:
          _firstString(mergedRaw, const <String>[
            'creator_profile_id',
            'creatorProfileId',
            'creator_id',
            'creatorId',
          ]) ??
          _firstString(creatorProfile, const <String>[
            'id',
            'profile_id',
            'profileId',
          ]),
      creatorStatus:
          _firstString(mergedRaw, const <String>[
            'creator_status',
            'creatorStatus',
            'creator_profile_status',
            'creatorProfileStatus',
          ]) ??
          _firstString(creatorProfile, const <String>['status', 'state']),
      traderProfileId:
          _firstString(mergedRaw, const <String>[
            'trader_profile_id',
            'traderProfileId',
            'coin_trader_profile_id',
            'coinTraderProfileId',
            'trader_id',
            'traderId',
          ]) ??
          _firstString(traderProfile, const <String>[
            'id',
            'profile_id',
            'profileId',
          ]),
      traderStatus:
          _firstString(mergedRaw, const <String>[
            'trader_status',
            'traderStatus',
            'trader_profile_status',
            'traderProfileStatus',
            'coin_trader_status',
            'coinTraderStatus',
          ]) ??
          _firstString(traderProfile, const <String>['status', 'state']),
      clubId: club?.id,
      clubName: club?.displayName,
      noClub:
          _boolValue(
            mergedRaw['no_club'] ??
                mergedRaw['noClub'] ??
                mergedRaw['has_no_club'] ??
                mergedRaw['hasNoClub'] ??
                user['no_club'] ??
                user['noClub'],
          ) ||
          _boolValue(
            onboarding['requires_club'] ?? onboarding['requiresClub'],
          ) ||
          (club == null && resolvedAccountType == 'user'),
      noClubReason:
          _firstString(mergedRaw, const <String>[
            'no_club_reason',
            'noClubReason',
            'club_missing_reason',
            'clubMissingReason',
          ]) ??
          _firstString(user, const <String>['no_club_reason', 'noClubReason']),
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
      'refresh_token': refreshToken,
      'session_id': sessionId,
      'refresh_expires_in': refreshExpiresIn,
    };
    if (_firstString(nextRaw, const <String>['role']) == null &&
        role.trim().isNotEmpty) {
      nextRaw['role'] = role;
    }
    if (_firstString(nextRaw, const <String>['user_id', 'userId', 'id']) ==
            null &&
        userId.trim().isNotEmpty) {
      nextRaw['user_id'] = userId;
    }
    final Map<String, Object?> mergedUser =
        _mapValue(nextRaw['user'] ?? nextRaw['current_user']) ??
        const <String, Object?>{};
    final bool hasPermissions =
        _stringList(nextRaw['permissions']).isNotEmpty ||
        _stringList(mergedUser['permissions']).isNotEmpty;
    if (!hasPermissions && permissions.isNotEmpty) {
      nextRaw['permissions'] = permissions;
    }
    return AuthSession.fromJson(nextRaw);
  }

  AuthSession copyWith({
    String? userId,
    String? accessToken,
    String? refreshToken,
    String? sessionId,
    String? role,
    int? refreshExpiresIn,
    List<String>? permissions,
    String? userName,
    String? displayName,
    String? accountType,
    String? creatorProfileId,
    String? creatorStatus,
    String? traderProfileId,
    String? traderStatus,
    String? clubId,
    String? clubName,
    bool? noClub,
    String? noClubReason,
    String? federationId,
    String? federationName,
    Map<String, Object?>? rawJson,
  }) {
    return AuthSession(
      userId: userId ?? this.userId,
      accessToken: accessToken ?? this.accessToken,
      refreshToken: refreshToken ?? this.refreshToken,
      sessionId: sessionId ?? this.sessionId,
      role: role ?? this.role,
      refreshExpiresIn: refreshExpiresIn ?? this.refreshExpiresIn,
      permissions: permissions ?? this.permissions,
      userName: userName ?? this.userName,
      displayName: displayName ?? this.displayName,
      accountType: accountType ?? this.accountType,
      creatorProfileId: creatorProfileId ?? this.creatorProfileId,
      creatorStatus: creatorStatus ?? this.creatorStatus,
      traderProfileId: traderProfileId ?? this.traderProfileId,
      traderStatus: traderStatus ?? this.traderStatus,
      clubId: clubId ?? this.clubId,
      clubName: clubName ?? this.clubName,
      noClub: noClub ?? this.noClub,
      noClubReason: noClubReason ?? this.noClubReason,
      federationId: federationId ?? this.federationId,
      federationName: federationName ?? this.federationName,
      rawJson: rawJson ?? this.rawJson,
    );
  }

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'user_id': userId,
      'access_token': accessToken,
      'refresh_token': refreshToken,
      'session_id': sessionId,
      'role': role,
      'refresh_expires_in': refreshExpiresIn,
      'permissions': permissions,
      if (userName != null) 'username': userName,
      if (displayName != null) 'display_name': displayName,
      'account_type': accountType,
      if (creatorProfileId != null) 'creator_profile_id': creatorProfileId,
      if (creatorStatus != null) 'creator_status': creatorStatus,
      if (traderProfileId != null) 'trader_profile_id': traderProfileId,
      if (traderStatus != null) 'trader_status': traderStatus,
      if (clubId != null) 'club_id': clubId,
      if (clubName != null) 'club_name': clubName,
      'no_club': noClub,
      if (noClubReason != null) 'no_club_reason': noClubReason,
      if (federationId != null) 'federation_id': federationId,
      if (federationName != null) 'federation_name': federationName,
      'raw_json': rawJson,
    };
  }
}

bool gtexIsAdminRole(String? role) {
  final String normalized = role?.trim().toLowerCase() ?? '';
  return gtexIsSuperAdminRole(normalized) ||
      gtexIsDelegatedAdminRole(normalized);
}

bool gtexIsSuperAdminRole(String? role) {
  final String normalized = role?.trim().toLowerCase() ?? '';
  return normalized == 'super_admin' || normalized == 'god_mode';
}

bool gtexIsDelegatedAdminRole(String? role) {
  final String normalized = role?.trim().toLowerCase() ?? '';
  return normalized == 'admin' || normalized == 'scoped_admin';
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

int _intValue(Object? value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  return int.tryParse(value?.toString() ?? '') ?? 0;
}

bool _boolValue(Object? value) {
  if (value is bool) {
    return value;
  }
  if (value is num) {
    return value != 0;
  }
  final String normalized = value?.toString().trim().toLowerCase() ?? '';
  return normalized == 'true' || normalized == '1' || normalized == 'yes';
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
