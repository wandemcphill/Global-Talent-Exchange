import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:gte_frontend/data/club_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/widgets/creator_club_follow_panel.dart';
import 'package:gte_frontend/features/club_redesign/models/gtex_public_club_profile_models.dart';
import 'package:gte_frontend/features/player_detail/gtex_player_navigator.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

const String _stadiumAsset = 'assets/showroom/arena_imperiale_stadium.webp';
const String _campusAsset = 'assets/showroom/apex_performance_campus.webp';

Color _clubColor(String? value, Color fallback) {
  final String hex = (value ?? '').replaceFirst('#', '').trim();
  if (hex.length != 6 && hex.length != 8) return fallback;
  final int? parsed = int.tryParse(hex, radix: 16);
  if (parsed == null) return fallback;
  return Color(hex.length == 8 ? parsed : 0xFF000000 | parsed);
}

String _valueLabel(String? raw, {String currency = 'GTX'}) {
  if (raw == null || raw.trim().isEmpty) return 'Not disclosed';
  final double? value = double.tryParse(raw);
  if (value == null) return raw + ' ' + currency;
  if (value.abs() >= 1000000) return (value / 1000000).toStringAsFixed(1) + 'M ' + currency;
  if (value.abs() >= 1000) return (value / 1000).toStringAsFixed(1) + 'K ' + currency;
  return value.toStringAsFixed(value % 1 == 0 ? 0 : 2) + ' ' + currency;
}

String? _mediaUrl(String? value, String? baseUrl) {
  if (value == null || value.trim().isEmpty) return null;
  final Uri? parsed = Uri.tryParse(value);
  if (parsed != null && (parsed.hasScheme || value.startsWith('//'))) return value;
  if (baseUrl == null || baseUrl.trim().isEmpty) return null;
  final Uri base = Uri.parse(baseUrl.endsWith('/') ? baseUrl : '$baseUrl/');
  return base.resolve(value.startsWith('/') ? value.substring(1) : value).toString();
}

String _location(GtexPublicClubProfileData profile) {
  final List<String> parts = <String>[
    if (profile.cityName?.isNotEmpty == true) profile.cityName!,
    if (profile.regionName?.isNotEmpty == true) profile.regionName!,
    if (profile.countryCode?.isNotEmpty == true) profile.countryCode!,
  ];
  return parts.isEmpty ? 'GTEX Football World' : parts.join(' · ');
}

class GtexPublicClubHomeV3 extends StatelessWidget {
  const GtexPublicClubHomeV3({
    super.key,
    required this.profile,
    required this.baseUrl,
    this.backendMode,
    this.accessToken,
    this.isAuthenticated = false,
    this.onOpenLogin,
  });

  final GtexPublicClubProfileData profile;
  final String baseUrl;
  final GteBackendMode? backendMode;
  final String? accessToken;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;

  @override
  Widget build(BuildContext context) {
    final Color primary = _clubColor(profile.primaryColor, GtexColors.surfaceBase);
    final Color secondary = _clubColor(profile.secondaryColor, GtexColors.gold);
    final Color accent = _clubColor(profile.accentColor, GtexColors.pitch);
    return ColoredBox(
      color: GtexColors.surfaceBase,
      child: ListView(
        key: const Key('gtex-public-club-home-v3'),
        padding: EdgeInsets.zero,
        children: <Widget>[
          _ClubHero(profile: profile, primary: primary, secondary: secondary),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 18, 16, 34),
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1260),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: <Widget>[
                        _Metric(label: 'SQUAD', value: profile.squadPlayerCount.toString(), icon: Icons.groups_2_outlined, accent: accent),
                        _Metric(label: 'ACADEMY PROSPECTS', value: (profile.academy['prospect_count'] ?? 0).toString(), icon: Icons.school_outlined, accent: accent),
                        _Metric(label: 'HONOURS', value: profile.trophies.length.toString(), icon: Icons.emoji_events_outlined, accent: GtexColors.gold),
                        _Metric(label: 'STADIUM', value: profile.stadium['level'] == null ? 'Unrated' : 'Level ' + profile.stadium['level'].toString(), icon: Icons.stadium_outlined, accent: accent),
                      ],
                    ),
                    const SizedBox(height: 14),
                    CreatorClubFollowPanel(
                      baseUrl: baseUrl,
                      backendMode: backendMode ?? GteBackendMode.live,
                      clubId: profile.clubId,
                      clubName: profile.name,
                      accessToken: accessToken,
                      isAuthenticated: isAuthenticated,
                      onOpenLogin: onOpenLogin,
                    ),
                    const SizedBox(height: 10),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: GtexActionButton(
                        label: 'Explore club ownership',
                        icon: Icons.account_balance_outlined,
                        accent: GtexColors.gold,
                        onPressed: () => context.push('/clubs/${profile.clubId}/sale-market'),
                      ),
                    ),
                    const SizedBox(height: 25),
                    const _SectionTitle(kicker: 'THE HOME GROUND', title: 'A stadium with an identity', subtitle: 'The venue, its scale, and the facilities behind the team.'),
                    const SizedBox(height: 12),
                    _StadiumFeature(profile: profile, primary: primary),
                    const SizedBox(height: 25),
                    const _SectionTitle(kicker: 'THE FOOTBALL DEPARTMENT', title: 'The people and talent', subtitle: 'First-team leadership, standout players, and the next generation.'),
                    const SizedBox(height: 12),
                    _PlayerSpotlights(profile: profile, baseUrl: baseUrl),
                    const SizedBox(height: 12),
                    _PublicSquadDirectory(profile: profile),
                    const SizedBox(height: 14),
                    _ManagementPanel(profile: profile, accent: accent),
                    const SizedBox(height: 25),
                    const _SectionTitle(kicker: 'THE FUTURE', title: 'Academy and performance facilities', subtitle: 'Recorded development infrastructure and prospects.'),
                    const SizedBox(height: 12),
                    _AcademyAndFacilities(profile: profile, accent: accent),
                    const SizedBox(height: 25),
                    const _SectionTitle(kicker: 'TEAM TRAVEL', title: 'The club fleet', subtitle: 'Coach buses and transport assets owned by the club.'),
                    const SizedBox(height: 12),
                    _CoachFleet(profile: profile, accent: accent),
                    const SizedBox(height: 25),
                    const _SectionTitle(kicker: 'THE OWNER', title: 'Meet the person behind the badge', subtitle: 'One owner profile for their clubs, net worth, and personal collection.'),
                    const SizedBox(height: 12),
                    _OwnerSpotlight(
                      owner: profile.owner,
                      primary: primary,
                      accent: accent,
                      onOpen: () => context.push(
                        '/owners/${Uri.encodeComponent(profile.owner.id)}/profile',
                      ),
                    ),
                    const SizedBox(height: 25),
                    _TrophyShelf(trophies: profile.trophies, accent: secondary),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ClubHero extends StatelessWidget {
  const _ClubHero({required this.profile, required this.primary, required this.secondary});
  final GtexPublicClubProfileData profile;
  final Color primary;
  final Color secondary;

  @override
  Widget build(BuildContext context) {
    final String initials = (profile.shortName?.isNotEmpty == true ? profile.shortName! : profile.name)
        .split(RegExp(r'\s+')).take(3).map((String part) => part.isEmpty ? '' : part[0].toUpperCase()).join();
    return SizedBox(
      height: 335,
      child: Stack(
        fit: StackFit.expand,
        children: <Widget>[
          Image.asset(_stadiumAsset, key: const Key('gtex-club-stadium-hero-image'), fit: BoxFit.cover,
            errorBuilder: (_, __, ___) => DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(colors: <Color>[primary, GtexColors.surfaceBase, secondary.withValues(alpha: 0.5)])))),
          DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: <Color>[GtexColors.surfaceBase.withValues(alpha: 0.18), primary.withValues(alpha: 0.40), GtexColors.surfaceBase.withValues(alpha: 0.99)]))),
          Positioned(
            left: 18,
            right: 18,
            bottom: 22,
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1220),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: <Widget>[
                    Container(
                      width: 83,
                      height: 98,
                      padding: const EdgeInsets.all(5),
                      decoration: BoxDecoration(color: primary.withValues(alpha: 0.96), border: Border.all(color: secondary, width: 1.5), borderRadius: const BorderRadius.only(topLeft: Radius.circular(22), topRight: Radius.circular(22), bottomLeft: Radius.circular(34), bottomRight: Radius.circular(34))),
                      child: profile.crestUrl == null
                          ? Center(child: Text(initials, textAlign: TextAlign.center, style: TextStyle(color: secondary, fontWeight: FontWeight.w900, fontSize: 23)))
                          : Image.network(profile.crestUrl!, fit: BoxFit.contain, errorBuilder: (_, __, ___) => Center(child: Text(initials, textAlign: TextAlign.center, style: TextStyle(color: secondary, fontWeight: FontWeight.w900, fontSize: 23)))),
                    ),
                    const SizedBox(width: 15),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: <Widget>[
                        Container(padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5), decoration: BoxDecoration(color: secondary.withValues(alpha: 0.18), border: Border.all(color: secondary.withValues(alpha: 0.75)), borderRadius: BorderRadius.circular(5)), child: Text('GTEX CLUB DOSSIER' + (profile.foundedYear == null ? '' : '  ·  EST. ' + profile.foundedYear.toString()), style: TextStyle(color: secondary, fontSize: 10, letterSpacing: 1.2, fontWeight: FontWeight.w900))),
                        const SizedBox(height: 8),
                        Text(profile.name, maxLines: 2, overflow: TextOverflow.ellipsis, style: Theme.of(context).textTheme.headlineMedium?.copyWith(color: Colors.white, fontWeight: FontWeight.w900, height: 0.98, letterSpacing: -0.4)),
                        const SizedBox(height: 7),
                        Text(_location(profile), maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: Colors.white.withValues(alpha: 0.82), fontSize: 13)),
                        if (profile.description != null) ...<Widget>[
                          const SizedBox(height: 6),
                          Text(profile.description!, maxLines: 2, overflow: TextOverflow.ellipsis, style: TextStyle(color: Colors.white.withValues(alpha: 0.88), fontSize: 12)),
                        ],
                      ]),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({required this.label, required this.value, required this.icon, required this.accent});
  final String label;
  final String value;
  final IconData icon;
  final Color accent;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: 190,
    child: Container(
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(color: GtexColors.panel, borderRadius: BorderRadius.circular(9), border: Border.all(color: GtexColors.line.withValues(alpha: 0.75))),
      child: Row(children: <Widget>[
        Icon(icon, size: 24, color: accent),
        const SizedBox(width: 11),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
          Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: GtexColors.textMuted, fontSize: 9, fontWeight: FontWeight.w800, letterSpacing: 0.7)),
          const SizedBox(height: 4),
          Text(value, style: const TextStyle(color: GtexColors.text, fontSize: 18, fontWeight: FontWeight.w900)),
        ])),
      ]),
    ),
  );
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.kicker, required this.title, required this.subtitle});
  final String kicker;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
    Text(kicker, style: const TextStyle(color: GtexColors.gold, fontSize: 10, letterSpacing: 1.7, fontWeight: FontWeight.w900)),
    const SizedBox(height: 5),
    Text(title, style: Theme.of(context).textTheme.titleLarge?.copyWith(color: GtexColors.text, fontWeight: FontWeight.w900)),
    const SizedBox(height: 4),
    Text(subtitle, style: const TextStyle(color: GtexColors.textMuted, height: 1.4, fontSize: 13)),
  ]);
}

class _Tag extends StatelessWidget {
  const _Tag({required this.label});
  final String label;
  @override
  Widget build(BuildContext context) => Container(padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6), decoration: BoxDecoration(color: GtexColors.panelStrong, borderRadius: BorderRadius.circular(5), border: Border.all(color: GtexColors.line)), child: Text(label, style: const TextStyle(color: GtexColors.textSecondary, fontSize: 11, fontWeight: FontWeight.w700)));
}

class _StadiumFeature extends StatelessWidget {
  const _StadiumFeature({required this.profile, required this.primary});
  final GtexPublicClubProfileData profile;
  final Color primary;

  @override
  Widget build(BuildContext context) {
    final Object? capacity = profile.stadium['capacity'];
    final Object? level = profile.stadium['level'];
    final String name = (profile.stadium['name'] ?? profile.homeVenueName ?? 'Venue details unavailable').toString();
    return Container(
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(color: GtexColors.panel, borderRadius: BorderRadius.circular(12), border: Border.all(color: GtexColors.line)),
      child: LayoutBuilder(builder: (BuildContext context, BoxConstraints constraints) {
        final bool stacked = constraints.maxWidth < 600;
        final Widget image = SizedBox(
          height: stacked ? 185 : 230,
          width: stacked ? double.infinity : constraints.maxWidth * 0.46,
          child: Stack(fit: StackFit.expand, children: <Widget>[
            Image.asset(_stadiumAsset, fit: BoxFit.cover, errorBuilder: (_, __, ___) => Container(color: primary)),
            DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(begin: Alignment.centerLeft, end: Alignment.centerRight, colors: <Color>[primary.withValues(alpha: 0.08), primary.withValues(alpha: 0.82)]))),
            const Positioned(left: 15, bottom: 13, child: _ImageLabel('HOME GROUND')),
          ]),
        );
        final Widget info = Padding(
          padding: const EdgeInsets.all(17),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: <Widget>[
            const Icon(Icons.stadium_outlined, color: GtexColors.gold, size: 26),
            const SizedBox(height: 10),
            Text(name, style: Theme.of(context).textTheme.titleLarge?.copyWith(color: GtexColors.text, fontWeight: FontWeight.w900)),
            const SizedBox(height: 12),
            Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
              _Tag(label: capacity == null ? 'Capacity not recorded' : 'Capacity ' + capacity.toString()),
              _Tag(label: level == null ? 'Level not recorded' : 'Stadium level ' + level.toString()),
              if (profile.stadium['theme_key'] != null) _Tag(label: profile.stadium['theme_key'].toString() + ' theme'),
            ]),
            const SizedBox(height: 13),
            const Text('Venue imagery is a GTEX showcase illustration until a club-specific stadium gallery is attached.', style: TextStyle(color: GtexColors.textMuted, fontSize: 11, height: 1.4)),
          ]),
        );
        return stacked ? Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[image, info]) : Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[image, Expanded(child: info)]);
      }),
    );
  }
}

class _ImageLabel extends StatelessWidget {
  const _ImageLabel(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5), decoration: BoxDecoration(color: Colors.black.withValues(alpha: 0.72), borderRadius: BorderRadius.circular(4)), child: Text(text, style: const TextStyle(color: Colors.white, fontSize: 9, letterSpacing: 1.2, fontWeight: FontWeight.w900)));
}

class _PublicSquadDirectory extends StatefulWidget {
  const _PublicSquadDirectory({required this.profile});

  final GtexPublicClubProfileData profile;

  @override
  State<_PublicSquadDirectory> createState() => _PublicSquadDirectoryState();
}

class _PublicSquadDirectoryState extends State<_PublicSquadDirectory> {
  bool _showAll = false;

  @override
  Widget build(BuildContext context) {
    final List<GtexPublicClubPlayer> players = widget.profile.squadPlayers;
    final List<GtexPublicClubPlayer> visiblePlayers =
        _showAll ? players : players.take(6).toList(growable: false);

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: GtexColors.panel,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: GtexColors.line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              const Icon(Icons.groups_2_outlined, color: GtexColors.gold),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    const Text(
                      'SQUAD DIRECTORY',
                      style: TextStyle(
                        color: GtexColors.text,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 1.1,
                        fontSize: 11,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      '${widget.profile.squadPlayerCount} public squad records',
                      style: const TextStyle(
                        color: GtexColors.textMuted,
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          if (players.isEmpty)
            const Text(
              'No squad records are available for public display yet.',
              style: TextStyle(color: GtexColors.textMuted),
            )
          else ...<Widget>[
            for (final GtexPublicClubPlayer player in visiblePlayers)
              _PublicSquadPlayerRow(player: player),
            if (players.length > 6)
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton.icon(
                  onPressed: () => setState(() => _showAll = !_showAll),
                  icon: Icon(
                    _showAll ? Icons.expand_less_rounded : Icons.expand_more_rounded,
                  ),
                  label: Text(
                    _showAll
                        ? 'Show fewer players'
                        : 'View all ${players.length} players',
                  ),
                ),
              ),
          ],
        ],
      ),
    );
  }
}

class _PublicSquadPlayerRow extends StatelessWidget {
  const _PublicSquadPlayerRow({required this.player});

  final GtexPublicClubPlayer player;

  @override
  Widget build(BuildContext context) {
    final VoidCallback? onTap = GtexPlayerNavigator.tapToOpen(
      context,
      player.id,
    );

    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Material(
        color: GtexColors.panelStrong,
        borderRadius: BorderRadius.circular(7),
        child: InkWell(
          key: Key('gtex-public-squad-player-${player.id}'),
          borderRadius: BorderRadius.circular(7),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
            child: Row(
              children: <Widget>[
                Container(
                  width: 36,
                  height: 40,
                  decoration: BoxDecoration(
                    color: player.isRegen
                        ? GtexColors.gold.withValues(alpha: 0.12)
                        : GtexColors.pitch.withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Icon(
                    player.isRegen
                        ? Icons.auto_awesome_outlined
                        : Icons.person_outline_rounded,
                    size: 19,
                    color: player.isRegen ? GtexColors.gold : GtexColors.pitch,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        player.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: GtexColors.text,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        <String?>[
                          player.position,
                          if (player.age != null) 'Age ${player.age}',
                          if (player.isRegen) 'Regen',
                        ].whereType<String>().join(' · '),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: GtexColors.textMuted,
                          fontSize: 10,
                        ),
                      ),
                    ],
                  ),
                ),
                if (player.rating != null) ...<Widget>[
                  const SizedBox(width: 6),
                  _Grade(
                    label: 'RAT',
                    value: player.rating.toString(),
                    accent: GtexColors.text,
                  ),
                ],
                if (player.potential != null) ...<Widget>[
                  const SizedBox(width: 10),
                  _Grade(
                    label: 'POT',
                    value: player.potential.toString(),
                    accent: GtexColors.gold,
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _PlayerSpotlights extends StatelessWidget {
  const _PlayerSpotlights({required this.profile, required this.baseUrl});
  final GtexPublicClubProfileData profile;
  final String baseUrl;
  @override
  Widget build(BuildContext context) => LayoutBuilder(builder: (BuildContext context, BoxConstraints constraints) {
    final double width = constraints.maxWidth < 560 ? constraints.maxWidth : (constraints.maxWidth - 12) / 2;
    return Wrap(spacing: 12, runSpacing: 12, children: <Widget>[
      SizedBox(width: width, child: _PlayerFeature(title: 'BEST PLAYER', player: profile.bestPlayer, baseUrl: baseUrl, accent: GtexColors.gold)),
      SizedBox(width: width, child: _PlayerFeature(title: 'MOST PROMISING', player: profile.mostPromisingPlayer, baseUrl: baseUrl, accent: GtexColors.pitch)),
    ]);
  });
}

class _PlayerFeature extends StatelessWidget {
  const _PlayerFeature({required this.title, required this.player, required this.baseUrl, required this.accent});
  final String title;
  final GtexPublicClubPlayer? player;
  final String baseUrl;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final GtexPublicClubPlayer? person = player;
    final VoidCallback? onTap =
        person == null ? null : GtexPlayerNavigator.tapToOpen(context, person.id);
    return InkWell(
      key: Key('gtex-public-club-player-${person?.id ?? title.toLowerCase().replaceAll(' ', '-')}'),
      borderRadius: BorderRadius.circular(10),
      onTap: onTap,
      child: Container(
      height: 156,
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(color: GtexColors.panel, borderRadius: BorderRadius.circular(10), border: Border.all(color: GtexColors.line)),
      child: person == null
          ? Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: <Widget>[
              Icon(Icons.person_search_outlined, color: accent, size: 25),
              const SizedBox(height: 8),
              Text(title, style: TextStyle(color: accent, fontSize: 10, letterSpacing: 1.2, fontWeight: FontWeight.w900)),
              const SizedBox(height: 5),
              const Text('No squad record available', style: TextStyle(color: GtexColors.text, fontWeight: FontWeight.w800)),
            ]))
          : Row(children: <Widget>[
              SizedBox(width: 116, height: double.infinity, child: Stack(fit: StackFit.expand, children: <Widget>[
                if (_mediaUrl(person.portraitUrl, baseUrl) != null)
                  Image.network(_mediaUrl(person.portraitUrl, baseUrl)!, fit: BoxFit.cover, errorBuilder: (_, __, ___) => Container(color: accent.withValues(alpha: 0.12), child: Icon(Icons.person_outline_rounded, color: accent, size: 44)))
                else
                  Container(color: accent.withValues(alpha: 0.12), child: Icon(Icons.person_outline_rounded, color: accent, size: 44)),
                const DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: <Color>[Colors.transparent, Color(0xAA06101F)]))),
              ])),
              Expanded(child: Padding(padding: const EdgeInsets.all(13), child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: <Widget>[
                Text(title, style: TextStyle(color: accent, fontSize: 9, letterSpacing: 1.1, fontWeight: FontWeight.w900)),
                const SizedBox(height: 7),
                Text(person.name, maxLines: 2, overflow: TextOverflow.ellipsis, style: Theme.of(context).textTheme.titleMedium?.copyWith(color: GtexColors.text, fontWeight: FontWeight.w900)),
                const SizedBox(height: 4),
                Text(<String?>[person.position, if (person.age != null) 'Age ' + person.age.toString(), if (person.isRegen) 'Regen'].whereType<String>().join(' · '), maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: GtexColors.textMuted, fontSize: 11)),
                const SizedBox(height: 9),
                Row(children: <Widget>[
                  if (person.rating != null) _Grade(label: 'RAT', value: person.rating.toString(), accent: GtexColors.text),
                  if (person.potential != null) ...<Widget>[const SizedBox(width: 9), _Grade(label: 'POT', value: person.potential.toString(), accent: accent)],
                ]),
              ]))),
            ]),
      ),
    );
  }
}

class _Grade extends StatelessWidget {
  const _Grade({required this.label, required this.value, required this.accent});
  final String label;
  final String value;
  final Color accent;
  @override
  Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
    Text(label, style: const TextStyle(color: GtexColors.textMuted, fontSize: 8, fontWeight: FontWeight.w800)),
    Text(value, style: TextStyle(color: accent, fontSize: 16, fontWeight: FontWeight.w900)),
  ]);
}

class _ManagementPanel extends StatelessWidget {
  const _ManagementPanel({required this.profile, required this.accent});
  final GtexPublicClubProfileData profile;
  final Color accent;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(color: GtexColors.panel, borderRadius: BorderRadius.circular(11), border: Border.all(color: GtexColors.line)),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
      const Row(children: <Widget>[Icon(Icons.badge_outlined, color: GtexColors.gold), SizedBox(width: 8), Text('CLUB LEADERSHIP', style: TextStyle(color: GtexColors.text, fontWeight: FontWeight.w900, letterSpacing: 1.2, fontSize: 11))]),
      const SizedBox(height: 9),
      for (final GtexPublicClubPerson person in profile.staff)
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 7),
          child: Row(children: <Widget>[
            Container(width: 36, height: 36, decoration: BoxDecoration(color: accent.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(8)), child: Icon(_staffIcon(person.role), color: accent, size: 19)),
            const SizedBox(width: 11),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              Text(person.title, style: const TextStyle(color: GtexColors.textMuted, fontSize: 10, fontWeight: FontWeight.w800)),
              const SizedBox(height: 2),
              Text(person.name ?? 'Not appointed', style: TextStyle(color: person.appointed ? GtexColors.text : GtexColors.textMuted, fontWeight: FontWeight.w800)),
            ])),
            if (person.rating != null) Text(person.rating.toString(), style: TextStyle(color: accent, fontWeight: FontWeight.w900)),
          ]),
        ),
    ]),
  );
  IconData _staffIcon(String role) {
    if (role.contains('youth')) return Icons.school_outlined;
    if (role.contains('general')) return Icons.business_center_outlined;
    if (role.contains('coach')) return Icons.sports_outlined;
    return Icons.sports_soccer_outlined;
  }
}

class _AcademyAndFacilities extends StatelessWidget {
  const _AcademyAndFacilities({required this.profile, required this.accent});
  final GtexPublicClubProfileData profile;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final List<(String, Object?, IconData)> facilities = <(String, Object?, IconData)>[
      ('Training', profile.facilities['training_level'], Icons.fitness_center_outlined),
      ('Academy', profile.facilities['academy_level'] ?? profile.academy['level'], Icons.school_outlined),
      ('Medical', profile.facilities['medical_level'], Icons.medical_services_outlined),
      ('Youth recruitment', profile.facilities['youth_recruitment_level'], Icons.travel_explore_outlined),
      ('Branding', profile.facilities['branding_level'], Icons.palette_outlined),
    ];
    final List<Map<String, Object?>> prospects = _rows(profile.academy['prospects']);
    return Column(children: <Widget>[
      Container(
        clipBehavior: Clip.antiAlias,
        decoration: BoxDecoration(color: GtexColors.panel, borderRadius: BorderRadius.circular(10), border: Border.all(color: GtexColors.line)),
        child: Row(children: <Widget>[
          SizedBox(width: 110, height: 130, child: Image.asset(_campusAsset, fit: BoxFit.cover, errorBuilder: (_, __, ___) => Container(color: GtexColors.panelStrong, child: const Icon(Icons.school_outlined, color: GtexColors.gold, size: 38)))),
          Expanded(child: Padding(padding: const EdgeInsets.all(14), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
            const Text('YOUTH DEVELOPMENT', style: TextStyle(color: GtexColors.gold, fontSize: 9, letterSpacing: 1.3, fontWeight: FontWeight.w900)),
            const SizedBox(height: 6),
            Text(profile.academy['level'] == null ? 'Academy level not recorded' : 'Academy level ' + profile.academy['level'].toString(), style: Theme.of(context).textTheme.titleMedium?.copyWith(color: GtexColors.text, fontWeight: FontWeight.w900)),
            const SizedBox(height: 3),
            Text((profile.academy['prospect_count'] ?? 0).toString() + ' active prospects in the academy record', style: const TextStyle(color: GtexColors.textMuted, fontSize: 11)),
            if (profile.academy['capacity'] != null) Text('Capacity ' + profile.academy['capacity'].toString(), style: const TextStyle(color: GtexColors.textSecondary, fontSize: 11)),
          ]))),
        ]),
      ),
      const SizedBox(height: 10),
      LayoutBuilder(builder: (BuildContext context, BoxConstraints constraints) {
        final double width = constraints.maxWidth < 500 ? (constraints.maxWidth - 8) / 2 : (constraints.maxWidth - 24) / 3;
        return Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
          for (final (String, Object?, IconData) item in facilities)
            SizedBox(width: width, child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: GtexColors.panel, borderRadius: BorderRadius.circular(8), border: Border.all(color: GtexColors.line)),
              child: Row(children: <Widget>[
                Icon(item.$3, color: accent, size: 20),
                const SizedBox(width: 8),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                  Text(item.$1, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: GtexColors.textMuted, fontSize: 10)),
                  const SizedBox(height: 3),
                  Text(item.$2 == null ? 'Not recorded' : 'Level ' + item.$2.toString(), style: const TextStyle(color: GtexColors.text, fontSize: 12, fontWeight: FontWeight.w900)),
                ])),
              ]),
            )),
        ]);
      }),
      if (prospects.isNotEmpty) ...<Widget>[
        const SizedBox(height: 12),
        Align(alignment: Alignment.centerLeft, child: Text('ACADEMY WATCHLIST', style: TextStyle(color: accent, fontSize: 10, letterSpacing: 1.2, fontWeight: FontWeight.w900))),
        const SizedBox(height: 8),
        for (final Map<String, Object?> prospect in prospects.take(3))
          Container(
            margin: const EdgeInsets.only(bottom: 6),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(color: GtexColors.panelStrong, borderRadius: BorderRadius.circular(7)),
            child: Row(children: <Widget>[
              Expanded(child: Text((prospect['name'] ?? 'Academy prospect').toString(), style: const TextStyle(color: GtexColors.text, fontWeight: FontWeight.w800))),
              Text((prospect['position'] ?? '—').toString() + ' · ' + (prospect['age'] ?? '—').toString() + ' yrs', style: const TextStyle(color: GtexColors.textMuted, fontSize: 11)),
              const SizedBox(width: 9),
              Text('POT ' + (prospect['potential'] ?? '—').toString(), style: TextStyle(color: accent, fontWeight: FontWeight.w900, fontSize: 11)),
            ]),
          ),
      ],
    ]);
  }

  List<Map<String, Object?>> _rows(Object? value) => value is List
      ? value.whereType<Map>().map((Map row) => Map<String, Object?>.from(row)).toList(growable: false)
      : const <Map<String, Object?>>[];
}

class _CoachFleet extends StatelessWidget {
  const _CoachFleet({required this.profile, required this.accent});
  final GtexPublicClubProfileData profile;
  final Color accent;
  @override
  Widget build(BuildContext context) {
    if (profile.coachBuses.isEmpty) return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: GtexColors.panel, borderRadius: BorderRadius.circular(9), border: Border.all(color: GtexColors.line)),
      child: const Row(children: <Widget>[Icon(Icons.directions_bus_outlined, color: GtexColors.textMuted, size: 28), SizedBox(width: 11), Expanded(child: Text('No club-owned coach buses are recorded yet.', style: TextStyle(color: GtexColors.textMuted)))]),
    );
    return LayoutBuilder(builder: (BuildContext context, BoxConstraints constraints) {
      final double width = constraints.maxWidth < 560 ? constraints.maxWidth : (constraints.maxWidth - 10) / 2;
      return Wrap(spacing: 10, runSpacing: 10, children: <Widget>[
        for (final GtexPublicClubAsset asset in profile.coachBuses)
          SizedBox(width: width, child: _AssetFeature(asset: asset, accent: accent, icon: Icons.directions_bus_outlined)),
      ]);
    });
  }
}

class _OwnerSpotlight extends StatelessWidget {
  const _OwnerSpotlight({required this.owner, required this.primary, required this.accent, required this.onOpen});
  final GtexPublicOwnerSummary owner;
  final Color primary;
  final Color accent;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) => Material(
    color: GtexColors.panel,
    borderRadius: BorderRadius.circular(11),
    child: InkWell(
      key: const Key('gtex-open-public-owner-profile'),
      borderRadius: BorderRadius.circular(11),
      onTap: onOpen,
      child: Container(
        padding: const EdgeInsets.all(17),
        decoration: BoxDecoration(borderRadius: BorderRadius.circular(11), border: Border.all(color: GtexColors.line)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
          Row(children: <Widget>[
            Container(width: 54, height: 54, decoration: BoxDecoration(color: primary, borderRadius: BorderRadius.circular(9), border: Border.all(color: accent.withValues(alpha: 0.7))), child: const Icon(Icons.person_outline_rounded, color: GtexColors.gold, size: 30)),
            const SizedBox(width: 12),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              Text(owner.displayName, style: Theme.of(context).textTheme.titleMedium?.copyWith(color: GtexColors.text, fontWeight: FontWeight.w900)),
              const SizedBox(height: 3),
              Text(owner.clubCount.toString() + ' clubs owned · ' + owner.luxuryAssetCount.toString() + ' personal luxury assets', style: const TextStyle(color: GtexColors.textMuted, fontSize: 11)),
            ])),
            const Icon(Icons.arrow_forward_rounded, color: GtexColors.gold),
          ]),
          const SizedBox(height: 15),
          Row(children: <Widget>[
            Expanded(child: _OwnerMetric(label: 'PUBLIC NET WORTH', value: _valueLabel(owner.netWorth, currency: owner.netWorthCurrency))),
            const SizedBox(width: 8),
            Expanded(child: _OwnerMetric(label: 'CLUBS ON SHOW', value: owner.publicClubs.length.toString())),
          ]),
          const SizedBox(height: 12),
          const Text('OPEN OWNER PROFILE  →  clubs · net worth · jets · cars · wristwatches', style: TextStyle(color: GtexColors.gold, fontWeight: FontWeight.w900, fontSize: 10, letterSpacing: 0.4)),
        ]),
      ),
    ),
  );
}

class _OwnerMetric extends StatelessWidget {
  const _OwnerMetric({required this.label, required this.value});
  final String label;
  final String value;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(11),
    decoration: BoxDecoration(color: GtexColors.panelStrong, borderRadius: BorderRadius.circular(7)),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
      Text(label, style: const TextStyle(color: GtexColors.textMuted, fontSize: 9, fontWeight: FontWeight.w800)),
      const SizedBox(height: 4),
      Text(value, style: const TextStyle(color: GtexColors.text, fontSize: 15, fontWeight: FontWeight.w900)),
    ]),
  );
}

class _TrophyShelf extends StatelessWidget {
  const _TrophyShelf({required this.trophies, required this.accent});
  final List<GtexPublicClubTrophy> trophies;
  final Color accent;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(15),
    decoration: BoxDecoration(color: GtexColors.panel, borderRadius: BorderRadius.circular(10), border: Border.all(color: GtexColors.line)),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
      Row(children: <Widget>[Icon(Icons.emoji_events_outlined, color: accent, size: 23), const SizedBox(width: 8), const Text('HONOURS CABINET', style: TextStyle(color: GtexColors.text, fontSize: 11, letterSpacing: 1.2, fontWeight: FontWeight.w900))]),
      const SizedBox(height: 10),
      if (trophies.isEmpty) const Text('No honours are recorded for this club yet.', style: TextStyle(color: GtexColors.textMuted)),
      for (final GtexPublicClubTrophy trophy in trophies)
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 6),
          child: Row(children: <Widget>[
            Icon(Icons.workspace_premium_outlined, color: accent, size: 19),
            const SizedBox(width: 9),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              Text(trophy.name, style: const TextStyle(color: GtexColors.text, fontWeight: FontWeight.w800)),
              if (trophy.competition != null || trophy.season != null)
                Text(<String?>[trophy.competition, trophy.season].whereType<String>().join(' · '), style: const TextStyle(color: GtexColors.textMuted, fontSize: 11)),
            ])),
          ]),
        ),
    ]),
  );
}

class _AssetFeature extends StatelessWidget {
  const _AssetFeature({required this.asset, required this.accent, required this.icon});
  final GtexPublicClubAsset asset;
  final Color accent;
  final IconData icon;
  @override
  Widget build(BuildContext context) => Container(
    clipBehavior: Clip.antiAlias,
    decoration: BoxDecoration(color: GtexColors.panel, borderRadius: BorderRadius.circular(9), border: Border.all(color: GtexColors.line)),
    child: Row(children: <Widget>[
      SizedBox(width: 112, height: 104, child: asset.previewFile == null
          ? Container(color: GtexColors.panelStrong, child: Icon(icon, color: accent, size: 35))
          : Image.asset(asset.previewFile!, fit: BoxFit.cover, errorBuilder: (_, __, ___) => Container(color: GtexColors.panelStrong, child: Icon(icon, color: accent, size: 35)))),
      Expanded(child: Padding(padding: const EdgeInsets.all(12), child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: <Widget>[
        Text(asset.category.toUpperCase().replaceAll('_', ' '), style: TextStyle(color: accent, fontSize: 9, letterSpacing: 1.1, fontWeight: FontWeight.w900)),
        const SizedBox(height: 5),
        Text(asset.name, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: GtexColors.text, fontWeight: FontWeight.w900)),
        const SizedBox(height: 4),
        Text('Edition ' + (asset.editionNumber?.toString() ?? '—'), style: const TextStyle(color: GtexColors.textMuted, fontSize: 11)),
      ]))),
    ]),
  );
}

class GtexPublicOwnerProfileScreen extends StatefulWidget {
  const GtexPublicOwnerProfileScreen({super.key, required this.ownerUserId, required this.baseUrl, this.backendMode, this.accessToken, this.isAuthenticated = false, this.onOpenLogin});
  final String ownerUserId;
  final String baseUrl;
  final GteBackendMode? backendMode;
  final String? accessToken;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;
  @override
  State<GtexPublicOwnerProfileScreen> createState() => _GtexPublicOwnerProfileScreenState();
}

class _GtexPublicOwnerProfileScreenState extends State<GtexPublicOwnerProfileScreen> {
  late Future<GtexPublicOwnerProfileData> _future;
  late ClubApi _api;

  ClubApi _createApi() => ClubApi.standard(baseUrl: widget.baseUrl, mode: widget.backendMode ?? GteBackendMode.live, accessToken: widget.accessToken);

  @override
  void initState() {
    super.initState();
    _api = _createApi();
    _future = _api.fetchPublicOwnerProfile(ownerUserId: widget.ownerUserId);
  }

  @override
  void didUpdateWidget(covariant GtexPublicOwnerProfileScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.ownerUserId != widget.ownerUserId || oldWidget.baseUrl != widget.baseUrl || oldWidget.backendMode != widget.backendMode || oldWidget.accessToken != widget.accessToken) {
      _api = _createApi();
      _future = _api.fetchPublicOwnerProfile(ownerUserId: widget.ownerUserId);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: GtexColors.surfaceBase,
    appBar: AppBar(backgroundColor: GtexColors.surfaceBase, foregroundColor: GtexColors.text, title: const Text('Owner profile')),
    body: FutureBuilder<GtexPublicOwnerProfileData>(
      future: _future,
      builder: (BuildContext context, AsyncSnapshot<GtexPublicOwnerProfileData> snapshot) {
        if (snapshot.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
        if (snapshot.hasError || !snapshot.hasData) {
          return Center(child: Padding(padding: const EdgeInsets.all(24), child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
            const Icon(Icons.person_search_outlined, color: GtexColors.gold, size: 42),
            const SizedBox(height: 12),
            const Text('Owner profile unavailable', style: TextStyle(color: GtexColors.text, fontSize: 18, fontWeight: FontWeight.w900)),
            const SizedBox(height: 6),
            Text(snapshot.error?.toString() ?? 'No public owner record was returned.', textAlign: TextAlign.center, style: const TextStyle(color: GtexColors.textMuted)),
            const SizedBox(height: 12),
            FilledButton(onPressed: () => setState(() => _future = _api.fetchPublicOwnerProfile(ownerUserId: widget.ownerUserId)), child: const Text('Retry')),
          ])));
        }
        final GtexPublicOwnerProfileData owner = snapshot.data!;
        return ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 34),
          children: <Widget>[
            Center(child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1180),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
                Container(
                  padding: const EdgeInsets.all(22),
                  decoration: BoxDecoration(gradient: const LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: <Color>[Color(0xFF172740), Color(0xFF0A1323)]), borderRadius: BorderRadius.circular(14), border: Border.all(color: GtexColors.gold.withValues(alpha: 0.55))),
                  child: Row(children: <Widget>[
                    Container(width: 66, height: 66, decoration: BoxDecoration(color: GtexColors.surfaceBase, borderRadius: BorderRadius.circular(12), border: Border.all(color: GtexColors.gold)), child: const Icon(Icons.workspace_premium_outlined, color: GtexColors.gold, size: 37)),
                    const SizedBox(width: 15),
                    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                      const Text('GTEX PUBLIC WEALTH DOSSIER', style: TextStyle(color: GtexColors.gold, fontSize: 9, letterSpacing: 1.3, fontWeight: FontWeight.w900)),
                      const SizedBox(height: 6),
                      Text(owner.displayName, style: Theme.of(context).textTheme.headlineSmall?.copyWith(color: GtexColors.text, fontWeight: FontWeight.w900)),
                      const SizedBox(height: 4),
                      Text(owner.clubCount.toString() + ' clubs owned · ' + owner.luxuryAssetCount.toString() + ' personal assets', style: const TextStyle(color: GtexColors.textMuted)),
                    ])),
                  ]),
                ),
                const SizedBox(height: 12),
                _Metric(label: 'PUBLIC NET WORTH', value: _valueLabel(owner.netWorth, currency: owner.netWorthCurrency), icon: Icons.account_balance_wallet_outlined, accent: GtexColors.gold),
                const SizedBox(height: 24),
                const _SectionTitle(kicker: 'THE EMPIRE', title: 'Clubs under ownership', subtitle: 'Open a club dossier to explore its stadium, squad, leadership and facilities.'),
                const SizedBox(height: 12),
                if (owner.publicClubs.isEmpty) const Text('No public club pages are available.', style: TextStyle(color: GtexColors.textMuted)),
                LayoutBuilder(builder: (BuildContext context, BoxConstraints constraints) {
                  final double width = constraints.maxWidth < 540 ? constraints.maxWidth : (constraints.maxWidth - 12) / 2;
                  return Wrap(spacing: 12, runSpacing: 12, children: <Widget>[
                    for (final GtexPublicClubSummary club in owner.publicClubs)
                      SizedBox(width: width, child: Material(
                        color: GtexColors.panel,
                        borderRadius: BorderRadius.circular(10),
                        child: InkWell(
                          key: Key('gtex-owner-open-club-' + club.id),
                          borderRadius: BorderRadius.circular(10),
                          onTap: () async {
                            try {
                              final GtexPublicClubProfileData detail = await _api.fetchPublicClubProfile(clubId: club.id);
                              if (!context.mounted) return;
                              Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => GtexPublicClubHomeV3(profile: detail, baseUrl: widget.baseUrl, backendMode: widget.backendMode, accessToken: widget.accessToken, isAuthenticated: widget.isAuthenticated, onOpenLogin: widget.onOpenLogin)));
                            } catch (_) {
                              if (!context.mounted) return;
                              ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('This public club page is temporarily unavailable.')));
                            }
                          },
                          child: Padding(padding: const EdgeInsets.all(14), child: Row(children: <Widget>[
                            _MiniCrest(club: club),
                            const SizedBox(width: 11),
                            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                              Text(club.name, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: GtexColors.text, fontWeight: FontWeight.w900)),
                              const SizedBox(height: 4),
                              Text(<String?>[club.city, club.countryCode].whereType<String>().join(' · '), style: const TextStyle(color: GtexColors.textMuted, fontSize: 11)),
                            ])),
                            const Icon(Icons.chevron_right_rounded, color: GtexColors.gold),
                          ])),
                        ),
                      )),
                  ]);
                }),
                const SizedBox(height: 24),
                const _SectionTitle(kicker: 'PERSONAL COLLECTION', title: 'Rare assets and status pieces', subtitle: 'Only assets currently owned by this person appear here. Club-owned buses stay on each club page.'),
                const SizedBox(height: 12),
                if (owner.assets.isEmpty) Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: GtexColors.panel, borderRadius: BorderRadius.circular(9), border: Border.all(color: GtexColors.line)), child: const Text('No personal luxury assets are recorded yet.', style: TextStyle(color: GtexColors.textMuted))),
                LayoutBuilder(builder: (BuildContext context, BoxConstraints constraints) {
                  final double width = constraints.maxWidth < 520 ? constraints.maxWidth : (constraints.maxWidth - 20) / 3;
                  return Wrap(spacing: 10, runSpacing: 10, children: <Widget>[
                    for (final GtexPublicClubAsset asset in owner.assets)
                      SizedBox(width: width, child: _OwnerAssetTile(asset: asset)),
                  ]);
                }),
              ]),
            )),
          ],
        );
      },
    ),
  );
}

class _OwnerAssetTile extends StatelessWidget {
  const _OwnerAssetTile({required this.asset});
  final GtexPublicClubAsset asset;
  IconData _icon() {
    final String category = asset.category.toLowerCase();
    if (category.contains('jet') || category.contains('aircraft')) return Icons.flight_takeoff_rounded;
    if (category.contains('watch')) return Icons.watch_outlined;
    if (category.contains('vehicle') || category.contains('car')) return Icons.directions_car_filled_outlined;
    if (category.contains('coach') || category.contains('bus')) return Icons.directions_bus_outlined;
    return Icons.diamond_outlined;
  }
  @override
  Widget build(BuildContext context) => Container(
    clipBehavior: Clip.antiAlias,
    decoration: BoxDecoration(color: GtexColors.panel, borderRadius: BorderRadius.circular(10), border: Border.all(color: GtexColors.line)),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
      AspectRatio(aspectRatio: 1.28, child: Stack(fit: StackFit.expand, children: <Widget>[
        if (asset.previewFile != null)
          Image.asset(asset.previewFile!, fit: BoxFit.cover, errorBuilder: (_, __, ___) => Container(color: GtexColors.panelStrong, child: Icon(_icon(), color: GtexColors.gold, size: 40)))
        else
          Container(color: GtexColors.panelStrong, child: Icon(_icon(), color: GtexColors.gold, size: 40)),
        const Positioned(left: 9, top: 9, child: _ImageLabel('OWNED')),
      ])),
      Padding(padding: const EdgeInsets.all(12), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        Text(asset.category.toUpperCase().replaceAll('_', ' '), style: const TextStyle(color: GtexColors.gold, fontSize: 9, letterSpacing: 1, fontWeight: FontWeight.w900)),
        const SizedBox(height: 5),
        Text(asset.name, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: GtexColors.text, fontWeight: FontWeight.w900)),
        const SizedBox(height: 5),
        Text('Edition ' + (asset.editionNumber?.toString() ?? '—'), style: const TextStyle(color: GtexColors.textMuted, fontSize: 11)),
        if (asset.catalogPrice != null) ...<Widget>[
          const SizedBox(height: 5),
          Text(
            'Catalogue price · ' + _valueLabel(asset.catalogPrice),
            style: const TextStyle(
              color: GtexColors.textSecondary,
              fontSize: 11,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ])),
    ]),
  );
}

class _MiniCrest extends StatelessWidget {
  const _MiniCrest({required this.club});
  final GtexPublicClubSummary club;
  @override
  Widget build(BuildContext context) {
    final String initials = (club.shortName?.isNotEmpty == true ? club.shortName! : club.name).split(RegExp(r'\s+')).take(3).map((String part) => part.isEmpty ? '' : part[0].toUpperCase()).join();
    return Container(width: 45, height: 49, decoration: BoxDecoration(color: _clubColor(club.primaryColor, GtexColors.panelStrong), border: Border.all(color: _clubColor(club.secondaryColor, GtexColors.gold)), borderRadius: const BorderRadius.only(topLeft: Radius.circular(10), topRight: Radius.circular(10), bottomLeft: Radius.circular(17), bottomRight: Radius.circular(17))), child: Center(child: Text(initials, textAlign: TextAlign.center, style: TextStyle(color: _clubColor(club.secondaryColor, GtexColors.gold), fontWeight: FontWeight.w900, fontSize: 12))));
  }
}
