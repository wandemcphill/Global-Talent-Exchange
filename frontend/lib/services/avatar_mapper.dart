import 'dart:convert';
import 'dart:math' as math;

import '../data/gte_exchange_models.dart';
import '../data/live_match_fixtures.dart';
import '../features/player_card_marketplace/data/player_card_marketplace_models.dart';
import '../models/academy_models.dart';
import '../models/player_avatar.dart';

class AvatarMapper {
  const AvatarMapper._();

  static const int _avatarVersion = 1;
  static const String _version = 'fm_v1';
  static const int _fnvOffset = 2166136261;
  static const int _fnvPrime = 16777619;

  static const Set<String> _europeCodes = <String>{
    'AL',
    'AM',
    'AT',
    'AZ',
    'BA',
    'BE',
    'BG',
    'BY',
    'CH',
    'CY',
    'CZ',
    'DE',
    'DK',
    'EE',
    'ES',
    'FI',
    'FR',
    'GB',
    'GE',
    'GR',
    'HR',
    'HU',
    'IE',
    'IS',
    'IT',
    'LT',
    'LU',
    'LV',
    'MD',
    'ME',
    'MK',
    'MT',
    'NL',
    'NO',
    'PL',
    'PT',
    'RO',
    'RS',
    'SE',
    'SI',
    'SK',
    'TR',
    'UA',
  };
  static const Set<String> _africaCodes = <String>{
    'AO',
    'BF',
    'BJ',
    'CD',
    'CG',
    'CI',
    'CM',
    'CV',
    'DZ',
    'EG',
    'ET',
    'GA',
    'GH',
    'GM',
    'GN',
    'KE',
    'LR',
    'LY',
    'MA',
    'ML',
    'MZ',
    'NA',
    'NE',
    'NG',
    'RW',
    'SD',
    'SL',
    'SN',
    'SS',
    'TG',
    'TN',
    'TZ',
    'UG',
    'ZA',
    'ZM',
    'ZW',
  };
  static const Set<String> _southAmericaCodes = <String>{
    'AR',
    'BO',
    'BR',
    'CL',
    'CO',
    'EC',
    'GF',
    'GY',
    'PE',
    'PY',
    'SR',
    'UY',
    'VE',
  };
  static const Set<String> _northAmericaCodes = <String>{
    'CA',
    'CR',
    'CU',
    'DO',
    'GT',
    'HN',
    'HT',
    'JM',
    'MX',
    'NI',
    'PA',
    'SV',
    'TT',
    'US',
  };
  static const Set<String> _asiaPacificCodes = <String>{
    'AU',
    'BD',
    'CN',
    'HK',
    'ID',
    'IN',
    'JP',
    'KH',
    'KR',
    'LA',
    'LK',
    'MM',
    'MN',
    'MY',
    'NZ',
    'PH',
    'PK',
    'SG',
    'TH',
    'TW',
    'VN',
  };
  static const Set<String> _middleEastCodes = <String>{
    'AE',
    'BH',
    'IL',
    'IQ',
    'IR',
    'JO',
    'KW',
    'LB',
    'OM',
    'PS',
    'QA',
    'SA',
    'SY',
    'YE',
  };

  static const Map<String, List<int>> _regionSkinWeights = <String, List<int>>{
    'africa': <int>[1, 2, 6, 18, 28, 34],
    'europe': <int>[30, 28, 18, 9, 3, 1],
    'south_america': <int>[7, 14, 22, 21, 12, 6],
    'north_america': <int>[6, 11, 20, 20, 12, 7],
    'asia_pacific': <int>[19, 24, 22, 10, 3, 1],
    'middle_east': <int>[8, 17, 24, 20, 10, 5],
    'global': <int>[8, 14, 19, 19, 14, 10],
  };
  static const Map<String, List<int>> _regionHairColorWeights =
      <String, List<int>>{
    'africa': <int>[58, 28, 8, 1, 1, 0],
    'europe': <int>[18, 30, 20, 18, 8, 6],
    'south_america': <int>[32, 34, 18, 8, 4, 4],
    'north_america': <int>[26, 28, 18, 14, 5, 9],
    'asia_pacific': <int>[44, 32, 12, 4, 1, 7],
    'middle_east': <int>[40, 34, 14, 5, 2, 5],
    'global': <int>[30, 28, 18, 10, 4, 10],
  };
  static const Map<String, List<int>> _positionFaceWeights =
      <String, List<int>>{
    'goalkeeper': <int>[1, 1, 4, 1, 2],
    'defender': <int>[1, 2, 4, 1, 2],
    'midfielder': <int>[3, 2, 2, 2, 1],
    'forward': <int>[2, 1, 2, 3, 2],
    'utility': <int>[2, 2, 2, 1, 1],
  };
  static const Map<String, List<int>> _positionHairWeights =
      <String, List<int>>{
    'goalkeeper': <int>[18, 22, 16, 8, 10, 2, 18, 3, 3],
    'defender': <int>[18, 22, 24, 7, 8, 2, 14, 2, 3],
    'midfielder': <int>[12, 18, 14, 16, 14, 3, 10, 6, 7],
    'forward': <int>[12, 15, 22, 14, 10, 4, 9, 6, 8],
    'utility': <int>[14, 18, 18, 12, 11, 3, 12, 5, 7],
  };
  static const List<int> _accessoryTypeWeights = <int>[0, 58, 24, 18];

  static PlayerAvatar fromMarketListItem(GteMarketPlayerListItem player) {
    return _resolveAvatar(
      provided: player.avatar,
      seed: PlayerAvatarSeedData(
        playerId: player.playerId,
        playerName: player.playerName,
        position: player.position,
        nationality: player.nationality,
        age: player.age,
      ),
    );
  }

  static PlayerAvatar fromMarketIdentity(
    GteMarketPlayerIdentity identity, {
    required String playerId,
  }) {
    return _resolveAvatar(
      provided: identity.avatar,
      seed: PlayerAvatarSeedData(
        playerId: playerId,
        playerName: identity.playerName,
        position: identity.position,
        normalizedPosition: identity.normalizedPosition,
        nationality: identity.nationality,
        nationalityCode: identity.nationalityCode,
        birthYear: _birthYear(identity.dateOfBirth),
        age: identity.age,
        preferredFoot: identity.preferredFoot,
      ),
    );
  }

  static PlayerAvatar fromMarketplaceListing(
    PlayerCardMarketplaceListing listing,
  ) {
    return _resolveAvatar(
      provided: listing.avatar,
      seed: PlayerAvatarSeedData(
        playerId: listing.playerId,
        playerName: listing.playerName,
        position: listing.position,
        contextLabel: listing.clubName,
      ),
    );
  }

  static PlayerAvatar fromMarketplaceLoanContract(
    PlayerCardMarketplaceLoanContract contract,
  ) {
    return _resolveAvatar(
      provided: contract.avatar,
      seed: PlayerAvatarSeedData(
        playerId: contract.playerId,
        playerName: contract.playerName,
        position: contract.position,
        contextLabel: contract.clubName,
      ),
    );
  }

  static PlayerAvatar fromHolding(PlayerCardHolding holding) {
    return _resolveAvatar(
      provided: holding.avatar,
      seed: PlayerAvatarSeedData(
        playerId: holding.playerId,
        playerName: holding.playerName,
      ),
    );
  }

  static PlayerAvatar fromListing(PlayerCardListing listing) {
    return _resolveAvatar(
      provided: listing.avatar,
      seed: PlayerAvatarSeedData(
        playerId: listing.playerId,
        playerName: listing.playerName,
      ),
    );
  }

  static PlayerAvatar fromAcademyPlayer(AcademyPlayer player) {
    return buildAvatar(
      PlayerAvatarSeedData(
        playerId: player.id,
        playerName: player.name,
        position: player.position,
        age: player.age,
        contextLabel: player.pathwayStage,
      ),
    );
  }

  static PlayerAvatar fromLiveLineupPlayer(
    LiveMatchLineupPlayer player, {
    String? teamName,
    String? matchId,
  }) {
    return _resolveAvatar(
      provided: player.avatar,
      seed: PlayerAvatarSeedData(
        playerId: player.playerId ??
            <String>[
              matchId ?? '',
              teamName ?? '',
              player.name,
            ].where((String value) => value.trim().isNotEmpty).join('|'),
        playerName: player.name,
        position: player.position,
        nationalityCode: player.nationalityCode,
        avatarSeedToken: player.avatarSeedToken,
        avatarDnaSeed: player.avatarDnaSeed,
        contextLabel: teamName,
      ),
    );
  }

  static PlayerAvatar buildAvatar(PlayerAvatarSeedData seed) {
    final String seedToken = _resolveSeedToken(seed);
    final bool useTraitBias = !_hasCanonicalSeed(seed);
    final String region =
        useTraitBias ? _regionForSeed(seed.nationalityCode) : 'global';
    final String positionGroup = useTraitBias
        ? _positionGroup(seed.normalizedPosition ?? seed.position)
        : 'utility';
    final int? age = useTraitBias ? seed.age : null;
    final String? preferredFoot = useTraitBias ? seed.preferredFoot : null;

    final int hairStyle = _pickWeighted(
      _hashSlot(seedToken, 'hair_style'),
      _hairStyleWeights(positionGroup: positionGroup, age: age),
    );
    final int accessoryScore = _percent(seedToken, 'accessory');
    final int accessoryThreshold =
        _accessoryThreshold(positionGroup: positionGroup, age: age);
    int accessoryType = 0;
    if (accessoryScore < accessoryThreshold) {
      accessoryType = _pickWeighted(
        _hashSlot(seedToken, 'accessory_type'),
        _accessoryTypeWeights,
      );
    }

    return PlayerAvatar(
      avatarVersion: _avatarVersion,
      version: _version,
      seedToken: seedToken,
      dnaSeed: _hashToken(seedToken),
      skinTone: _pickWeighted(
        _hashSlot(seedToken, 'skin'),
        _regionSkinWeights[region]!,
      ),
      hairStyle: hairStyle,
      hairColor: _pickWeighted(
        _hashSlot(seedToken, 'hair_color'),
        _regionHairColorWeights[region]!,
      ),
      faceShape: _pickWeighted(
        _hashSlot(seedToken, 'face_shape'),
        _faceShapeWeights(positionGroup: positionGroup, age: age),
      ),
      eyebrowStyle: _pickWeighted(
        _hashSlot(seedToken, 'eyebrows'),
        _eyebrowWeights(positionGroup: positionGroup),
      ),
      eyeType: _pickWeighted(
        _hashSlot(seedToken, 'eyes'),
        _eyeWeights(positionGroup: positionGroup),
      ),
      noseType: _pickWeighted(
        _hashSlot(seedToken, 'nose'),
        _noseWeights(region: region),
      ),
      mouthType: _pickWeighted(
        _hashSlot(seedToken, 'mouth'),
        _mouthWeights(age: age),
      ),
      beardStyle: _pickWeighted(
        _hashSlot(seedToken, 'beard'),
        _beardWeights(age: age, positionGroup: positionGroup),
      ),
      hasAccessory: accessoryType != 0,
      accessoryType: accessoryType,
      jerseyStyle: _pickWeighted(
        _hashSlot(seedToken, 'jersey'),
        _jerseyWeights(positionGroup: positionGroup),
      ),
      accentTone: _pickWeighted(
        _hashSlot(seedToken, 'accent'),
        _accentWeights(
          positionGroup: positionGroup,
          preferredFoot: preferredFoot,
        ),
      ),
    );
  }

  static PlayerAvatar _resolveAvatar({
    required PlayerAvatar? provided,
    required PlayerAvatarSeedData seed,
  }) {
    return provided ?? buildAvatar(seed);
  }

  static int? _birthYear(String? value) {
    if (value == null || value.trim().isEmpty) {
      return null;
    }
    final DateTime? parsed = DateTime.tryParse(value);
    return parsed?.year;
  }

  static String _resolveSeedToken(PlayerAvatarSeedData seed) {
    final String explicitToken = _cleanText(seed.avatarSeedToken);
    if (explicitToken.isNotEmpty) {
      return explicitToken;
    }
    final String explicitSeed = _cleanText(seed.avatarDnaSeed);
    if (explicitSeed.isNotEmpty) {
      return explicitSeed;
    }
    final String playerId = _cleanText(seed.playerId);
    if (playerId.isNotEmpty) {
      return playerId;
    }
    return <String>[
      _cleanText(seed.playerName).isNotEmpty
          ? _cleanText(seed.playerName)
          : 'generic-player',
      _cleanText(seed.nationalityCode).isNotEmpty
          ? _cleanText(seed.nationalityCode)
          : _cleanText(seed.nationality),
      _cleanText(seed.normalizedPosition ?? seed.position),
      seed.birthYear?.toString() ?? '',
    ].join('|');
  }

  static bool _hasCanonicalSeed(PlayerAvatarSeedData seed) {
    return _cleanText(seed.avatarSeedToken).isNotEmpty ||
        _cleanText(seed.avatarDnaSeed).isNotEmpty ||
        _cleanText(seed.playerId).isNotEmpty;
  }

  static String _regionForSeed(String? nationalityCode) {
    final String code = _normalizeCode(nationalityCode);
    if (_africaCodes.contains(code)) {
      return 'africa';
    }
    if (_europeCodes.contains(code)) {
      return 'europe';
    }
    if (_southAmericaCodes.contains(code)) {
      return 'south_america';
    }
    if (_northAmericaCodes.contains(code)) {
      return 'north_america';
    }
    if (_asiaPacificCodes.contains(code)) {
      return 'asia_pacific';
    }
    if (_middleEastCodes.contains(code)) {
      return 'middle_east';
    }
    return 'global';
  }

  static String _positionGroup(String? position) {
    final String normalized = _cleanText(position).toUpperCase();
    if (normalized == 'GK' || normalized == 'GOALKEEPER') {
      return 'goalkeeper';
    }
    if (<String>{'CB', 'RB', 'LB', 'RWB', 'LWB', 'DEF', 'DF'}
        .contains(normalized)) {
      return 'defender';
    }
    if (<String>{'CM', 'CDM', 'CAM', 'LM', 'RM', 'MID', 'MF'}
        .contains(normalized)) {
      return 'midfielder';
    }
    if (<String>{'ST', 'CF', 'LW', 'RW', 'SS', 'FW', 'ATT'}
        .contains(normalized)) {
      return 'forward';
    }
    return 'utility';
  }

  static List<int> _hairStyleWeights({
    required String positionGroup,
    required int? age,
  }) {
    final List<int> weights =
        List<int>.from(_positionHairWeights[positionGroup]!);
    if (age != null && age < 21) {
      weights[6] = math.max(weights[6] - 6, 2);
      weights[3] += 4;
      weights[7] += 3;
    }
    if (age != null && age >= 31) {
      weights[6] += 9;
      weights[0] += 3;
      weights[4] = math.max(weights[4] - 4, 2);
    }
    return weights;
  }

  static List<int> _faceShapeWeights({
    required String positionGroup,
    required int? age,
  }) {
    final List<int> weights =
        List<int>.from(_positionFaceWeights[positionGroup]!);
    if (age != null && age < 21) {
      weights[0] += 2;
      weights[1] += 2;
      weights[2] = math.max(weights[2] - 1, 1);
    }
    if (age != null && age >= 30) {
      weights[2] += 2;
      weights[4] += 1;
    }
    return weights;
  }

  static List<int> _eyebrowWeights({required String positionGroup}) {
    if (positionGroup == 'forward') {
      return <int>[2, 3, 4, 2];
    }
    if (positionGroup == 'goalkeeper') {
      return <int>[2, 2, 4, 2];
    }
    return <int>[3, 4, 3, 2];
  }

  static List<int> _eyeWeights({required String positionGroup}) {
    if (positionGroup == 'midfielder') {
      return <int>[3, 4, 3, 2];
    }
    if (positionGroup == 'forward') {
      return <int>[2, 3, 4, 2];
    }
    return <int>[4, 3, 2, 2];
  }

  static List<int> _noseWeights({required String region}) {
    if (region == 'africa') {
      return <int>[2, 3, 4, 3];
    }
    if (region == 'europe' || region == 'asia_pacific') {
      return <int>[4, 4, 2, 1];
    }
    return <int>[3, 4, 3, 2];
  }

  static List<int> _mouthWeights({required int? age}) {
    if (age != null && age < 21) {
      return <int>[4, 4, 2, 1];
    }
    if (age != null && age >= 30) {
      return <int>[3, 2, 3, 3];
    }
    return <int>[3, 3, 3, 2];
  }

  static List<int> _beardWeights({
    required int? age,
    required String positionGroup,
  }) {
    final int effectiveAge = age ?? 24;
    if (effectiveAge < 21) {
      return <int>[90, 8, 1, 1, 0, 0];
    }
    if (effectiveAge < 27) {
      return <int>[60, 18, 8, 8, 4, 2];
    }
    if (effectiveAge < 32) {
      return <int>[35, 18, 12, 18, 6, 11];
    }
    final List<int> weights = <int>[28, 14, 12, 20, 8, 18];
    if (positionGroup == 'goalkeeper') {
      weights[3] += 4;
      weights[5] += 2;
    }
    return weights;
  }

  static List<int> _jerseyWeights({required String positionGroup}) {
    if (positionGroup == 'goalkeeper') {
      return <int>[4, 1, 1, 2];
    }
    if (positionGroup == 'forward') {
      return <int>[3, 3, 1, 2];
    }
    return <int>[4, 2, 2, 1];
  }

  static List<int> _accentWeights({
    required String positionGroup,
    required String? preferredFoot,
  }) {
    final List<int> weights = <int>[3, 3, 2, 2, 2, 2];
    if (positionGroup == 'goalkeeper') {
      weights[4] += 2;
      weights[5] += 2;
    }
    if (positionGroup == 'forward') {
      weights[0] += 2;
      weights[3] += 1;
    }
    if (_cleanText(preferredFoot).startsWith('left')) {
      weights[2] += 2;
    }
    return weights;
  }

  static int _accessoryThreshold({
    required String positionGroup,
    required int? age,
  }) {
    int threshold = 8;
    if (positionGroup == 'goalkeeper') {
      threshold = 16;
    } else if (positionGroup == 'forward') {
      threshold = 11;
    }
    if (age != null && age < 21) {
      threshold = threshold - 3;
      if (threshold < 4) {
        threshold = 4;
      }
    }
    return threshold;
  }

  static int _percent(String seedToken, String slot) {
    return _hashSlot(seedToken, slot) % 100;
  }

  static int _hashSlot(String seedToken, String slot) {
    return _hashToken('$_version|$seedToken|$slot');
  }

  static int _hashToken(String value) {
    int hashed = _fnvOffset;
    for (final int byte in utf8.encode(value)) {
      hashed ^= byte;
      hashed = (hashed * _fnvPrime) & 0xFFFFFFFF;
    }
    return hashed;
  }

  static int _pickWeighted(int hashed, List<int> weights) {
    final int total = weights.fold<int>(
        0, (int sum, int weight) => sum + (weight > 0 ? weight : 0));
    if (total <= 0) {
      return 0;
    }
    int cursor = hashed % total;
    for (int index = 0; index < weights.length; index += 1) {
      final int weight = weights[index] > 0 ? weights[index] : 0;
      if (cursor < weight) {
        return index;
      }
      cursor -= weight;
    }
    return weights.length - 1;
  }

  static String _cleanText(Object? value) {
    final String raw = value?.toString().trim().toLowerCase() ?? '';
    return raw
        .split(RegExp(r'\s+'))
        .where((String part) => part.isNotEmpty)
        .join(' ');
  }

  static String _normalizeCode(String? value) {
    final String cleaned = _cleanText(value).toUpperCase();
    if (cleaned.length >= 2) {
      return cleaned.substring(0, 2);
    }
    return cleaned;
  }
}
