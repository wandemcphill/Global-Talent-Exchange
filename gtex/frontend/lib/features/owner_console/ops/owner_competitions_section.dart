import 'dart:async';

import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../data/owner_ops_api.dart';
import '../widgets/owner_admin_review_section.dart';

const List<(String, String, int)> ownerGifts = <(String, String, int)>[
  ('stadium_roar', 'Stadium Roar', 10), ('captains_armband', "Captain's Armband", 20), ('home_end_banner', 'Home End Banner', 30),
  ('golden_boot', 'Golden Boot', 50), ('floodlights', 'Floodlights', 100), ('legendary_stadium', 'Legendary Stadium', 1000),
];

/// Competitions list, hosting, join-by-code, detail with play-next, and the match center.
class CompetitionsSection extends StatefulWidget {
  const CompetitionsSection({super.key, required this.client, required this.clubId, required this.onChanged});

  final OwnerOpsClient client;
  final String? clubId;
  final VoidCallback onChanged;

  @override
  State<CompetitionsSection> createState() => _CompetitionsSectionState();
}

class _CompetitionsSectionState extends State<CompetitionsSection> {
  String? _competitionId;
  String? _matchId;
  bool _live = false;

  void _openMatch(String id, {bool live = false}) => setState(() {
    _matchId = id;
    _live = live;
  });

  @override
  Widget build(BuildContext context) {
    if (_matchId != null) {
      return OwnerMatchCenter(key: ValueKey<String>('match-$_matchId'), client: widget.client, matchId: _matchId!, clubId: widget.clubId, live: _live, onBack: () => setState(() => _matchId = null));
    }
    if (_competitionId != null) {
      return _CompetitionDetail(
        key: ValueKey<String>('comp-$_competitionId'),
        client: widget.client,
        competitionId: _competitionId!,
        fallbackClubId: widget.clubId,
        onBack: () => setState(() => _competitionId = null),
        onOpenMatch: _openMatch,
        onChanged: widget.onChanged,
      );
    }
    return OpsLoader(
      key: const Key('owner-competitions'),
      label: 'Competitions',
      load: () => widget.client.get('/owner/competitions'),
      builder: (BuildContext context, Map<String, dynamic> d, VoidCallback reload) {
        final List<Map<String, dynamic>> all = opsMaps(d['competitions']);
        Widget cards(Iterable<Map<String, dynamic>> list) => Column(children: <Widget>[
          for (final Map<String, dynamic> c in list) _CompetitionCard(c: c, client: widget.client, clubId: widget.clubId, onOpen: () => setState(() => _competitionId = '${c['id']}'), onEntered: () {
            reload();
            widget.onChanged();
          }),
        ]);
        final List<Map<String, dynamic>> user = all.where((Map<String, dynamic> c) => c['host_type'] == 'user').toList();
        return opsList(<Widget>[
          GtexPanel(key: const Key('owner-competitions-gtex'), title: 'Platform competitions', subtitle: 'GTEX-hosted', accent: GtexColors.pitch, child: cards(all.where((Map<String, dynamic> c) => c['host_type'] == 'gtex'))),
          _HostForm(client: widget.client, onDone: reload),
          _JoinCode(client: widget.client, clubId: widget.clubId, onDone: reload),
          GtexPanel(
            key: const Key('owner-competitions-user'),
            title: 'Your user-hosted competitions',
            accent: GtexColors.cyan,
            child: user.isEmpty ? const OpsNote('None yet. Host one above or join with an invite code.') : cards(user),
          ),
        ]);
      },
    );
  }
}

class _CompetitionCard extends StatelessWidget {
  const _CompetitionCard({required this.c, required this.client, required this.clubId, required this.onOpen, required this.onEntered});

  final Map<String, dynamic> c;
  final OwnerOpsClient client;
  final String? clubId;
  final VoidCallback onOpen;
  final VoidCallback onEntered;

  @override
  Widget build(BuildContext context) {
    final bool entered = (c['my_club_ids'] as List<dynamic>? ?? const <dynamic>[]).isNotEmpty;
    return OpsLine(
      key: Key('owner-competition-${c['id']}'),
      title: opsStr(c['name']),
      subtitle: <String>[
        opsStr(c['format']), opsStr(c['status']), 'entry ${opsGtx(c['entry_fee'])}', 'pool ${opsGtx(c['prize_pool'])}', '${c['entrants']}/${c['max_clubs']} clubs',
        if (c['allow_same_owner'] == true) 'same-owner allowed',
        if (c['invite_code'] != null) 'invite ${c['invite_code']}',
      ].join(' · '),
      accent: c['status'] == 'running' ? GtexColors.pitch : c['status'] == 'open' ? GtexColors.gold : GtexColors.textMuted,
      onTap: onOpen,
      trailing: Wrap(spacing: GtexSpacing.xs, children: <Widget>[
        GtexActionButton(key: Key('owner-competition-view-${c['id']}'), label: 'View', compact: true, secondary: true, onPressed: onOpen),
        if (c['status'] == 'open' && !entered)
          GtexActionButton(
            key: Key('owner-competition-enter-${c['id']}'),
            label: 'Enter',
            compact: true,
            onPressed: clubId == null
                ? null
                : () async {
                    final String? ok = await confirmOwnerAction(context, title: 'Enter ${opsStr(c['name'])}?', message: 'Entry fee ${opsGtx(c['entry_fee'])} is paid from club cash.', confirmLabel: 'Enter');
                    if (ok == null || !context.mounted) return;
                    if (await runOwnerAction(context, () => client.post('/owner/competitions/${c['id']}/enter', body: <String, Object?>{'club_id': clubId}), success: (_) => 'Entered ${opsStr(c['name'])}') != null) onEntered();
                  },
          ),
      ]),
    );
  }
}

class _HostForm extends StatefulWidget {
  const _HostForm({required this.client, required this.onDone});

  final OwnerOpsClient client;
  final VoidCallback onDone;

  @override
  State<_HostForm> createState() => _HostFormState();
}

class _HostFormState extends State<_HostForm> {
  final TextEditingController _name = TextEditingController();
  final TextEditingController _fee = TextEditingController(text: '0');
  String _format = 'league';
  String _size = '4';
  bool _sameOwner = false;

  @override
  void dispose() {
    _name.dispose();
    _fee.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => GtexPanel(
    key: const Key('owner-host-competition'),
    title: 'Host a friend competition',
    subtitle: 'Platform fee on entry fees: 10%',
    accent: GtexColors.cyan,
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
      Wrap(spacing: GtexSpacing.sm, runSpacing: GtexSpacing.sm, crossAxisAlignment: WrapCrossAlignment.center, children: <Widget>[
        OpsField(key: const Key('owner-host-name'), controller: _name, label: 'Competition name', width: 240, onChanged: (_) => setState(() {})),
        OpsSelect(key: const Key('owner-host-format'), value: _format, options: const <(String, String)>[('league', 'League'), ('knockout', 'Knockout')], hint: 'Format', onChanged: (String? v) => setState(() => _format = v ?? 'league')),
        OpsField(key: const Key('owner-host-fee'), controller: _fee, label: 'Entry fee', number: true, width: 110),
        OpsSelect(key: const Key('owner-host-size'), value: _size, options: const <(String, String)>[('2', '2 clubs'), ('4', '4 clubs'), ('6', '6 clubs'), ('8', '8 clubs')], hint: 'Size', onChanged: (String? v) => setState(() => _size = v ?? '4')),
      ]),
      CheckboxListTile(
        key: const Key('owner-host-same-owner'),
        contentPadding: EdgeInsets.zero,
        value: _sameOwner,
        onChanged: (bool? v) => setState(() => _sameOwner = v ?? false),
        title: const Text('Allow clubs under common ownership (publicly labelled "Same-owner allowed")', style: TextStyle(color: GtexColors.textSecondary, fontSize: 12)),
      ),
      GtexActionButton(
        key: const Key('owner-host-submit'),
        label: 'Host',
        compact: true,
        onPressed: _name.text.trim().length < 3
            ? null
            : () async {
                final Map<String, dynamic>? r = await runOwnerAction(
                  context,
                  () => widget.client.post('/owner/competitions', body: <String, Object?>{'name': _name.text.trim(), 'format': _format, 'entry_fee': opsNum(_fee.text), 'max_clubs': int.parse(_size), 'allow_same_owner': _sameOwner}),
                  success: (Map<String, dynamic> r) => 'Hosted. Share invite code ${r['invite_code']} with friends.',
                );
                if (r != null) widget.onDone();
              },
      ),
    ]),
  );
}

class _JoinCode extends StatefulWidget {
  const _JoinCode({required this.client, required this.clubId, required this.onDone});

  final OwnerOpsClient client;
  final String? clubId;
  final VoidCallback onDone;

  @override
  State<_JoinCode> createState() => _JoinCodeState();
}

class _JoinCodeState extends State<_JoinCode> {
  final TextEditingController _code = TextEditingController();

  @override
  void dispose() {
    _code.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => GtexPanel(
    key: const Key('owner-join-code'),
    title: 'Join with a code',
    accent: GtexColors.cyan,
    child: Wrap(spacing: GtexSpacing.sm, crossAxisAlignment: WrapCrossAlignment.center, children: <Widget>[
      OpsField(key: const Key('owner-join-code-input'), controller: _code, label: 'Invite code', width: 160, onChanged: (_) => setState(() {})),
      GtexActionButton(
        key: const Key('owner-join-code-button'),
        label: 'Join',
        compact: true,
        secondary: true,
        onPressed: _code.text.trim().length < 4 || widget.clubId == null
            ? null
            : () async {
                if (await runOwnerAction(context, () => widget.client.post('/owner/competitions/join-by-code', body: <String, Object?>{'code': _code.text.trim().toUpperCase(), 'club_id': widget.clubId}), success: (_) => 'Joined friend competition') != null) widget.onDone();
              },
      ),
    ]),
  );
}

class _CompetitionDetail extends StatelessWidget {
  const _CompetitionDetail({super.key, required this.client, required this.competitionId, required this.fallbackClubId, required this.onBack, required this.onOpenMatch, required this.onChanged});

  final OwnerOpsClient client;
  final String competitionId;
  final String? fallbackClubId;
  final VoidCallback onBack;
  final void Function(String id, {bool live}) onOpenMatch;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) => OpsLoader(
    key: const Key('owner-competition-detail'),
    label: 'Competition',
    load: () => client.get('/owner/competitions/$competitionId'),
    builder: (BuildContext context, Map<String, dynamic> comp, VoidCallback reload) {
      final List<String> myIds = (comp['my_club_ids'] as List<dynamic>? ?? const <dynamic>[]).map((dynamic e) => '$e').toList();
      final String? myClub = myIds.isNotEmpty ? myIds.first : fallbackClubId;
      final List<Map<String, dynamic>> fixtures = opsMaps(comp['fixtures']);
      return opsList(<Widget>[
        Align(alignment: Alignment.centerLeft, child: GtexActionButton(key: const Key('owner-competition-back'), label: 'All competitions', icon: Icons.arrow_back_rounded, compact: true, secondary: true, onPressed: onBack)),
        GtexPanel(
          title: opsStr(comp['name']),
          subtitle: '${comp['host_type'] == 'gtex' ? 'GTEX-hosted' : 'User-hosted'} · ${opsStr(comp['format'])} · pool ${opsGtx(comp['prize_pool'])} · round ${comp['current_round'] ?? 0}/${comp['total_rounds'] ?? '-'}',
          accent: GtexColors.pitch,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
            if (opsStr(comp['description'], '').isNotEmpty) OpsNote(opsStr(comp['description'])),
            const SizedBox(height: GtexSpacing.sm),
            for (final (int i, Map<String, dynamic> r) in opsMaps(comp['standings']).indexed)
              OpsLine(
                title: '${r['final_position'] ?? i + 1}. ${opsStr(r['club_name'])}${r['is_ai'] == true ? ' (AI)' : ''}${r['eliminated'] == true ? ' · out' : ''}',
                subtitle: 'P${r['played']} W${r['won']} D${r['drawn']} L${r['lost']} · GD ${opsInt(r['gf']) - opsInt(r['ga'])}',
                accent: myIds.contains('${r['club_id']}') ? GtexColors.pitch : GtexColors.textMuted,
                trailing: Text('${r['points']} pts', style: const TextStyle(color: GtexColors.pitch, fontWeight: FontWeight.w900)),
              ),
          ]),
        ),
        GtexPanel(
          key: const Key('owner-competition-play-panel'),
          title: 'Owner decisions',
          subtitle: 'Pre-match',
          accent: GtexColors.gold,
          child: myIds.isEmpty || myClub == null
              ? const OpsNote("You haven't entered this competition.")
              : _PlayPanel(client: client, comp: comp, clubId: myClub, onPlayed: (String matchId) {
                  onChanged();
                  onOpenMatch(matchId, live: true);
                }, onForfeit: () {
                  reload();
                  onChanged();
                }),
        ),
        GtexPanel(
          key: const Key('owner-competition-fixtures'),
          title: 'Fixtures',
          accent: GtexColors.cyan,
          child: Column(children: <Widget>[
            if (fixtures.isEmpty) const OpsNote('Schedule is generated at kick-off.'),
            for (final Map<String, dynamic> m in fixtures)
              OpsLine(
                key: Key('owner-fixture-${m['id']}'),
                title: '${opsStr(m['home_name'])} – ${opsStr(m['away_name'])}',
                subtitle: 'Round ${m['round']}',
                trailing: Text(m['status'] == 'scheduled' ? 'vs' : '${m['home_goals']}-${m['away_goals']}', style: const TextStyle(color: GtexColors.pitch, fontWeight: FontWeight.w800)),
                onTap: m['status'] == 'scheduled' ? null : () => onOpenMatch('${m['id']}'),
              ),
          ]),
        ),
      ]);
    },
  );
}

class _PlayPanel extends StatefulWidget {
  const _PlayPanel({required this.client, required this.comp, required this.clubId, required this.onPlayed, required this.onForfeit});

  final OwnerOpsClient client;
  final Map<String, dynamic> comp;
  final String clubId;
  final ValueChanged<String> onPlayed;
  final VoidCallback onForfeit;

  @override
  State<_PlayPanel> createState() => _PlayPanelState();
}

class _PlayPanelState extends State<_PlayPanel> {
  String _mentality = 'balanced';
  String _lineup = 'strongest';
  bool _busy = false;

  @override
  Widget build(BuildContext context) {
    final Map<String, dynamic> comp = widget.comp;
    if (comp['status'] == 'finished') return const OpsNote('Competition finished. Prizes were paid to club treasuries via the ledger (held if under integrity review).');
    final Map<String, dynamic>? next = opsMaps(comp['fixtures']).where((Map<String, dynamic> m) => m['status'] == 'scheduled' && <dynamic>[m['home_club_id'], m['away_club_id']].contains(widget.clubId)).firstOrNull;
    Widget choice(String key, String value, String group, ValueChanged<String> pick) => GtexActionButton(key: Key('owner-$key-$value'), label: value, compact: true, secondary: group != value, onPressed: () => setState(() => pick(value)));
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
      Text(
        next != null ? 'Next: ${opsStr(next['home_name'])} vs ${opsStr(next['away_name'])} (Round ${next['round']})' : comp['status'] == 'open' ? 'Kick-off fills remaining slots with AI clubs and generates the schedule.' : 'No fixture for your club this round.',
        key: const Key('owner-next-fixture'),
        style: const TextStyle(color: GtexColors.text),
      ),
      const SizedBox(height: GtexSpacing.sm),
      Wrap(spacing: GtexSpacing.xs, children: <Widget>[for (final String m in <String>['defensive', 'balanced', 'attacking']) choice('mentality', m, _mentality, (String v) => _mentality = v)]),
      const SizedBox(height: GtexSpacing.xs),
      Wrap(spacing: GtexSpacing.xs, children: <Widget>[for (final String m in <String>['strongest', 'rotate']) choice('lineup', m, _lineup, (String v) => _lineup = v)]),
      if (_lineup == 'rotate' && comp['prize_sensitive'] == true)
        const OpsNote('Rotating in a prize-sensitive competition is monitored. Repeated weakening (or against a sister club) triggers an integrity review.', color: GtexColors.gold),
      const SizedBox(height: GtexSpacing.sm),
      Wrap(spacing: GtexSpacing.xs, children: <Widget>[
        GtexActionButton(
          key: const Key('owner-play-next'),
          label: _busy ? 'Simulating...' : 'Play next match',
          onPressed: _busy || (next == null && comp['status'] != 'open')
              ? null
              : () async {
                  setState(() => _busy = true);
                  final Map<String, dynamic>? r = await runOwnerAction(context, () => widget.client.post('/owner/competitions/${comp['id']}/play-next', body: <String, Object?>{'club_id': widget.clubId, 'mentality': _mentality, 'lineup_mode': _lineup}));
                  if (mounted) setState(() => _busy = false);
                  if (r != null) widget.onPlayed('${opsMap(r['match'])['id']}');
                },
        ),
        if (next != null)
          GtexActionButton(
            key: const Key('owner-forfeit'),
            label: 'Forfeit',
            secondary: true,
            accent: GtexColors.red,
            onPressed: () async {
              final String? ok = await confirmOwnerAction(context, title: 'Forfeit this match?', message: 'Forfeiting costs a 0-3 loss, -3 points and an integrity flag.', confirmLabel: 'Forfeit');
              if (ok == null || !context.mounted) return;
              if (await runOwnerAction(context, () => widget.client.post('/owner/matches/${next['id']}/forfeit', body: <String, Object?>{'club_id': widget.clubId}), success: (Map<String, dynamic> r) => opsStr(r['penalty'], 'Forfeited')) != null) widget.onForfeit();
            },
          ),
      ]),
    ]);
  }
}

/// Replays a simulated match, then shows the owner view and the gift rail.
class OwnerMatchCenter extends StatefulWidget {
  const OwnerMatchCenter({super.key, required this.client, required this.matchId, required this.clubId, required this.live, required this.onBack});

  final OwnerOpsClient client;
  final String matchId;
  final String? clubId;
  final bool live;
  final VoidCallback onBack;

  @override
  State<OwnerMatchCenter> createState() => _OwnerMatchCenterState();
}

class _OwnerMatchCenterState extends State<OwnerMatchCenter> {
  late int _minute = widget.live ? 0 : 120;
  Timer? _clock;
  final List<String> _feed = <String>[];

  @override
  void initState() {
    super.initState();
    if (widget.live) {
      _clock = Timer.periodic(const Duration(milliseconds: 380), (Timer t) {
        if (!mounted) return;
        setState(() => _minute += 3);
        if (_minute >= 120) t.cancel();
      });
    }
  }

  @override
  void dispose() {
    _clock?.cancel();
    super.dispose();
  }

  void _skip() {
    _clock?.cancel();
    setState(() => _minute = 120);
  }

  @override
  Widget build(BuildContext context) => OpsLoader(
    key: const Key('owner-match-center'),
    label: 'Match',
    load: () => widget.client.get('/owner/matches/${widget.matchId}'),
    builder: (BuildContext context, Map<String, dynamic> m, _) {
      final List<Map<String, dynamic>> shown = opsMaps(m['events']).where((Map<String, dynamic> e) => opsInt(e['minute']) <= _minute).toList();
      final int home = shown.where((Map<String, dynamic> e) => e['type'] == 'goal' && e['team'] == 'home').length;
      final int away = shown.where((Map<String, dynamic> e) => e['type'] == 'goal' && e['team'] == 'away').length;
      final bool done = _minute >= 90;
      final Map<String, dynamic> narrative = opsMap(m['narrative']);
      final String side = m['home_club_id'] == widget.clubId ? 'home' : m['away_club_id'] == widget.clubId ? 'away' : narrative['home_owner_view'] != null ? 'home' : 'away';
      final Map<String, dynamic> view = opsMap(narrative['${side}_owner_view']);
      return opsList(<Widget>[
        Wrap(spacing: GtexSpacing.xs, children: <Widget>[
          GtexActionButton(key: const Key('owner-match-back'), label: 'Back to competition', icon: Icons.arrow_back_rounded, compact: true, secondary: true, onPressed: widget.onBack),
          if (!done) GtexActionButton(key: const Key('owner-match-skip'), label: 'Skip to full time', compact: true, secondary: true, onPressed: _skip),
        ]),
        GtexPanel(
          title: done ? 'Full time' : "Live · ${_minute.clamp(0, 90)}'",
          accent: done ? GtexColors.textMuted : GtexColors.pitch,
          child: Column(children: <Widget>[
            Text('${opsStr(m['home_name'])}  $home – $away  ${opsStr(m['away_name'])}', key: const Key('owner-match-score'), textAlign: TextAlign.center, style: const TextStyle(color: GtexColors.text, fontSize: 24, fontWeight: FontWeight.w900)),
            OpsNote('Mentality: ${opsStr(opsMap(narrative['mentality'])['home'])} vs ${opsStr(opsMap(narrative['mentality'])['away'])}'),
          ]),
        ),
        GtexPanel(
          key: const Key('owner-match-feed'),
          title: 'Event feed',
          accent: GtexColors.cyan,
          child: Column(children: <Widget>[
            for (final Map<String, dynamic> e in shown.reversed)
              OpsLine(title: "${e['minute']}'  ${opsStr(e['text'])}", accent: e['type'] == 'goal' ? GtexColors.pitch : GtexColors.textMuted),
          ]),
        ),
        if (done && view.isNotEmpty)
          GtexPanel(
            key: const Key('owner-match-owner-view'),
            title: opsStr(view['headline']),
            subtitle: 'Post-match · owner view',
            accent: GtexColors.gold,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              OpsNote(opsStr(view['manager_reaction'], ''), color: GtexColors.textSecondary),
              for (final Map<String, dynamic> w in opsMaps(view['why']))
                OpsLine(title: '${opsStr(w['factor'])}: ${opsStr(w['value'])}', accent: w['impact'] == 'positive' ? GtexColors.pitch : w['impact'] == 'negative' ? GtexColors.red : GtexColors.textMuted),
              for (final dynamic a in view['next_actions'] as List<dynamic>? ?? const <dynamic>[]) OpsNote('• $a', color: GtexColors.text),
              if ((view['revenue_notes'] as List<dynamic>? ?? const <dynamic>[]).isNotEmpty) OpsNote('Revenue: ${(view['revenue_notes'] as List<dynamic>).join(' · ')}. Sponsor income is split 70/30.'),
            ]),
          ),
        _GiftRail(client: widget.client, match: m, clubId: widget.clubId, feed: _feed, onSent: (String line) => setState(() => _feed.insert(0, line))),
      ]);
    },
  );
}

class _GiftRail extends StatefulWidget {
  const _GiftRail({required this.client, required this.match, required this.clubId, required this.feed, required this.onSent});

  final OwnerOpsClient client;
  final Map<String, dynamic> match;
  final String? clubId;
  final List<String> feed;
  final ValueChanged<String> onSent;

  @override
  State<_GiftRail> createState() => _GiftRailState();
}

class _GiftRailState extends State<_GiftRail> {
  String? _target;

  @override
  Widget build(BuildContext context) {
    final Map<String, dynamic> m = widget.match;
    final List<(String, String)> targets = <(String, String)>[
      for (final String side in <String>['home', 'away'])
        if (!'${m['${side}_club_id']}'.startsWith('ai:')) ('${m['${side}_club_id']}', opsStr(m['${side}_name'])),
    ];
    if (targets.isEmpty) return const SizedBox.shrink();
    final String target = _target ?? (targets.any(((String, String) t) => t.$1 == widget.clubId) ? widget.clubId! : targets.first.$1);
    return GtexPanel(
      key: const Key('owner-gift-rail'),
      title: 'Back your club',
      subtitle: 'Gift rail · Fan Coin · 70% to the club, 30% platform',
      accent: GtexColors.gold,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        if (targets.length > 1) OpsSelect(key: const Key('owner-gift-target'), value: target, options: targets, hint: 'Club', onChanged: (String? v) => setState(() => _target = v)),
        Wrap(spacing: GtexSpacing.xs, runSpacing: GtexSpacing.xs, children: <Widget>[
          for (final (String code, String name, int cost) in ownerGifts)
            GtexActionButton(
              key: Key('owner-gift-$code'),
              label: '$name · $cost FAN',
              compact: true,
              secondary: true,
              accent: GtexColors.gold,
              onPressed: () async {
                final Map<String, dynamic>? r = await runOwnerAction(context, () => widget.client.post('/owner/gifts/send', body: <String, Object?>{'club_id': target, 'gift_code': code, 'match_id': m['id']}));
                if (r != null) widget.onSent('${opsStr(r['sender'], 'You')} sent $name');
              },
            ),
        ]),
        for (final String f in widget.feed.take(5)) OpsNote(f, color: GtexColors.gold),
      ]),
    );
  }
}
