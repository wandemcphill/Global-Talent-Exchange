import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../data/owner_ops_api.dart';

const List<(String, String)> _steps = <(String, String)>[
  ('not_started', 'Club identity'), ('squad', 'Sign starting squad'), ('manager', 'Appoint manager'), ('competition', 'First competition'),
];

int setupStepIndex(String stage) => const <String, int>{'not_started': 0, 'squad': 1, 'manager': 2, 'competition': 3}[stage] ?? 3;

Map<String, Object?> newClubBody(String name, int stamp) {
  final String slug = '${name.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), '-')}-${stamp.toRadixString(36).substring(stamp.toRadixString(36).length - 4)}';
  return <String, Object?>{
    'club_name': name, 'slug': slug, 'short_name': name.length > 12 ? name.substring(0, 12) : name, 'primary_color': '#0F766E',
    'secondary_color': '#F8FAFC', 'accent_color': '#F59E0B', 'country_code': 'NG', 'city_name': 'Lagos', 'club_type': 'community',
  };
}

/// First-club activation: identity, squad, manager, first competition; plus adding another club.
class ClubSetupSection extends StatelessWidget {
  const ClubSetupSection({super.key, required this.client, required this.onChanged});

  final OwnerOpsClient client;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) {
    return OpsLoader(
      key: const Key('owner-setup'),
      label: 'Club setup',
      load: () => client.get('/owner/onboarding'),
      builder: (BuildContext context, Map<String, dynamic> d, VoidCallback reload) {
        final List<Map<String, dynamic>> clubs = opsMaps(d['clubs']);
        final Map<String, dynamic>? pending = clubs.where((Map<String, dynamic> c) => c['stage'] != 'active').firstOrNull;
        void next() {
          reload();
          onChanged();
        }

        return opsList(<Widget>[
          if (pending != null) _Stepper(index: setupStepIndex('${pending['stage']}')),
          if (pending != null)
            switch (setupStepIndex('${pending['stage']}')) {
              0 => _IdentityStep(client: client, club: pending, grant: opsNum(d['launch_grant']), onDone: next),
              1 => _SquadStep(client: client, clubId: '${pending['club_id']}', minSquad: opsInt(d['min_squad']), onDone: next),
              2 => _ManagerStep(client: client, clubId: '${pending['club_id']}', onDone: next),
              _ => _CompetitionStep(client: client, clubId: '${pending['club_id']}', onDone: next),
            },
          if (pending == null && clubs.isNotEmpty)
            const GtexPanel(key: Key('owner-setup-all-active'), title: 'All clubs are active', accent: GtexColors.pitch, child: OpsNote('Every club you own has finished setup.')),
          if (pending == null && clubs.length < opsInt(d['max_clubs']))
            _NewClubPanel(client: client, count: clubs.length, max: opsInt(d['max_clubs']), onDone: next),
        ]);
      },
    );
  }
}

class _Stepper extends StatelessWidget {
  const _Stepper({required this.index});

  final int index;

  @override
  Widget build(BuildContext context) => Wrap(
    key: const Key('owner-setup-stepper'),
    spacing: GtexSpacing.xs,
    runSpacing: GtexSpacing.xs,
    children: <Widget>[
      for (int i = 0; i < _steps.length; i++)
        GtexStatusChip(
          label: '${i + 1}. ${_steps[i].$2}',
          icon: i < index ? Icons.check_rounded : null,
          color: i == index ? GtexColors.pitch : i < index ? GtexColors.textSecondary : GtexColors.textMuted,
        ),
    ],
  );
}

class _IdentityStep extends StatelessWidget {
  const _IdentityStep({required this.client, required this.club, required this.grant, required this.onDone});

  final OwnerOpsClient client;
  final Map<String, dynamic> club;
  final double grant;
  final VoidCallback onDone;

  @override
  Widget build(BuildContext context) => GtexPanel(
    key: const Key('owner-setup-identity'),
    title: 'Confirm ${opsStr(club['club_name'])}',
    subtitle: 'Step 1 · Club identity',
    accent: GtexColors.pitch,
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
      OpsNote('Activating unlocks a ${opsFmt(grant)} GTEX Coin launch grant in the club treasury (promotional: usable for signings and facilities, not withdrawable) plus 1,000 Fan Coin for gifting.', color: GtexColors.textSecondary),
      const SizedBox(height: GtexSpacing.sm),
      GtexActionButton(
        key: const Key('owner-setup-activate'),
        label: 'Activate club',
        onPressed: () async {
          if (await runOwnerAction(context, () => client.post('/owner/clubs/${club['club_id']}/activate')) != null) onDone();
        },
      ),
    ]),
  );
}

class _SquadStep extends StatelessWidget {
  const _SquadStep({required this.client, required this.clubId, required this.minSquad, required this.onDone});

  final OwnerOpsClient client;
  final String clubId;
  final int minSquad;
  final VoidCallback onDone;

  @override
  Widget build(BuildContext context) => OpsLoader(
    label: 'Club',
    load: () => client.get('/owner/clubs/$clubId'),
    builder: (BuildContext context, Map<String, dynamic> club, VoidCallback reload) {
      final List<Map<String, dynamic>> squad = opsMaps(club['squad']).where((Map<String, dynamic> p) => p['is_regen'] != true).toList();
      final bool hasGk = squad.any((Map<String, dynamic> p) => '${p['position']}'.startsWith('goal'));
      return GtexPanel(
        key: const Key('owner-setup-squad'),
        title: 'Sign your starting squad',
        subtitle: 'Step 2 · Club cash ${opsGtx(opsMap(club['economy'])['cash_gtex'])}',
        accent: GtexColors.gold,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
          Wrap(spacing: GtexSpacing.xs, children: <Widget>[
            GtexStatusChip(key: const Key('owner-setup-squad-count'), label: '${squad.length}/$minSquad players', color: squad.length >= minSquad ? GtexColors.pitch : GtexColors.gold),
            GtexStatusChip(label: hasGk ? 'Goalkeeper signed' : 'Needs a goalkeeper', color: hasGk ? GtexColors.pitch : GtexColors.red),
          ]),
          const OpsNote('A club becomes match-eligible with 11 players including a goalkeeper.'),
          const SizedBox(height: GtexSpacing.sm),
          OwnerMarketSignList(
            client: client,
            clubId: clubId,
            signedRefs: squad.map((Map<String, dynamic> p) => '${p['player_ref']}').toSet(),
            onSigned: (Map<String, dynamic> r) => r['stage'] != 'squad' ? onDone() : reload(),
          ),
        ]),
      );
    },
  );
}

/// World market players with live sign fees; signing pays from club cash.
class OwnerMarketSignList extends StatefulWidget {
  const OwnerMarketSignList({super.key, required this.client, required this.clubId, required this.signedRefs, required this.onSigned});

  final OwnerOpsClient client;
  final String clubId;
  final Set<String> signedRefs;
  final ValueChanged<Map<String, dynamic>> onSigned;

  @override
  State<OwnerMarketSignList> createState() => _OwnerMarketSignListState();
}

class _OwnerMarketSignListState extends State<OwnerMarketSignList> {
  final TextEditingController _search = TextEditingController();
  String _position = '';
  final List<Map<String, dynamic>> _players = <Map<String, dynamic>>[];
  String? _cursor;
  bool _more = false;
  bool _loading = false;
  String? _busy;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load(reset: true);
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  Future<void> _load({bool reset = false}) async {
    setState(() {
      _loading = true;
      _error = null;
      if (reset) {
        _players.clear();
        _cursor = null;
      }
    });
    try {
      final Map<String, dynamic> page = await widget.client.get('/v2/players', query: <String, Object?>{
        'limit': 24, if (_position.isNotEmpty) 'position': _position, if (_search.text.trim().isNotEmpty) 'search': _search.text.trim(), if (_cursor != null) 'cursor': _cursor,
      });
      final List<Map<String, dynamic>> players = opsMaps(page['players']);
      final String ids = players.map((Map<String, dynamic> p) => '${p['player_id']}').join(',');
      final Map<String, dynamic> quotes = ids.isEmpty ? <String, dynamic>{} : opsMap((await widget.client.get('/owner/market/quote', query: <String, Object?>{'player_ids': ids}))['quotes']);
      if (!mounted) return;
      setState(() {
        _players.addAll(players.map((Map<String, dynamic> p) => <String, dynamic>{...p, 'quote': quotes['${p['player_id']}']}));
        _more = page['has_more'] == true;
        _cursor = page['next_cursor'] as String?;
      });
    } catch (e) {
      if (mounted) setState(() => _error = opsError(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _sign(Map<String, dynamic> p) async {
    setState(() => _busy = '${p['player_id']}');
    final Map<String, dynamic>? r = await runOwnerAction(
      context,
      () => widget.client.post('/owner/clubs/${widget.clubId}/sign', body: <String, Object?>{'player_id': p['player_id']}),
      success: (Map<String, dynamic> r) => '${opsStr(opsMap(r['player'])['name'])} signed. Club cash: ${opsGtx(r['cash'])}',
    );
    if (mounted) setState(() => _busy = null);
    if (r != null) widget.onSigned(r);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      key: const Key('owner-market-sign-list'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Wrap(spacing: GtexSpacing.xs, runSpacing: GtexSpacing.xs, crossAxisAlignment: WrapCrossAlignment.center, children: <Widget>[
          SizedBox(
            width: 240,
            child: TextField(
              key: const Key('owner-market-search'),
              controller: _search,
              onSubmitted: (_) => _load(reset: true),
              style: const TextStyle(color: GtexColors.text),
              decoration: const InputDecoration(labelText: 'Search players', isDense: true, prefixIcon: Icon(Icons.search, size: 18), border: OutlineInputBorder()),
            ),
          ),
          for (final String pos in <String>['', 'goalkeeper', 'defender', 'midfielder', 'forward'])
            GtexActionButton(
              key: Key('owner-market-filter-${pos.isEmpty ? 'all' : pos}'),
              label: pos.isEmpty ? 'All' : pos,
              compact: true,
              secondary: _position != pos,
              onPressed: () {
                _position = pos;
                _load(reset: true);
              },
            ),
        ]),
        const SizedBox(height: GtexSpacing.sm),
        if (_error != null) OpsNote(_error!, color: GtexColors.red),
        if (_loading && _players.isEmpty) const GtexSkeleton.box(height: 80),
        if (!_loading && _players.isEmpty && _error == null) const OpsNote('No players found. Try another name or position.'),
        for (final Map<String, dynamic> p in _players)
          OpsLine(
            key: Key('owner-market-player-${p['player_id']}'),
            title: '${opsStr(p['player_name'])} · ${opsStr(p['position'])}',
            subtitle: <String>['age ${opsStr(p['age'])}', opsStr(p['nationality'], ''), opsStr(p['current_club_name'], ''), 'rating ${opsStr(opsMap(p['quote'])['rating'])}'].where((String s) => s.isNotEmpty).join(' · '),
            accent: GtexColors.cyan,
            trailing: widget.signedRefs.contains('${p['player_id']}')
                ? const GtexStatusChip(label: 'In squad', color: GtexColors.pitch, compact: true)
                : GtexActionButton(
                    key: Key('owner-market-sign-${p['player_id']}'),
                    label: _busy == '${p['player_id']}' ? 'Signing...' : 'Sign · ${opsGtx(opsMap(p['quote'])['price'])}',
                    compact: true,
                    onPressed: _busy == null && opsMap(p['quote'])['price'] != null ? () => _sign(p) : null,
                  ),
          ),
        if (_more)
          GtexActionButton(key: const Key('owner-market-load-more'), label: _loading ? 'Loading...' : 'Load more players', compact: true, secondary: true, onPressed: _loading ? null : () => _load()),
      ],
    );
  }
}

Map<String, Object?> managerBody(Map<String, dynamic> m) => <String, Object?>{
  'manager_id': m['manager_id'], 'display_name': m['display_name'], 'rarity': m['rarity'], 'mentality': m['mentality'],
  'tactics': m['tactics'], 'traits': m['traits'], 'philosophy_summary': m['philosophy_summary'],
};

class _ManagerStep extends StatelessWidget {
  const _ManagerStep({required this.client, required this.clubId, required this.onDone});

  final OwnerOpsClient client;
  final String clubId;
  final VoidCallback onDone;

  Future<void> _appoint(BuildContext context, Map<String, dynamic>? m) async {
    if (await runOwnerAction(context, () => client.post('/owner/clubs/$clubId/manager', body: <String, Object?>{'manager': m == null ? null : managerBody(m)})) != null) onDone();
  }

  @override
  Widget build(BuildContext context) => GtexPanel(
    key: const Key('owner-setup-manager'),
    title: 'Appoint a manager',
    subtitle: 'Step 3 · First appointment is covered by the launch package',
    accent: GtexColors.cyan,
    child: OpsLoader(
      label: 'Managers',
      load: () => client.get('/managers/catalog', query: const <String, Object?>{'limit': 3}),
      builder: (BuildContext context, Map<String, dynamic> d, _) => Column(children: <Widget>[
        for (final Map<String, dynamic> m in opsMaps(d['items']))
          OpsLine(
            title: '${opsStr(m['display_name'])} · ${opsStr(m['rarity'])}',
            subtitle: '${opsStr(m['mentality'])} · ${opsStr(m['philosophy_summary'], '')}',
            trailing: GtexActionButton(key: Key('owner-appoint-${m['manager_id']}'), label: 'Appoint', compact: true, secondary: true, onPressed: () => _appoint(context, m)),
          ),
        OpsLine(
          title: 'GTEX staff coach',
          subtitle: 'A steady default manager. You can hire a named manager later from Manager & Squad.',
          accent: GtexColors.textMuted,
          trailing: GtexActionButton(key: const Key('owner-appoint-default'), label: 'Use default', compact: true, secondary: true, onPressed: () => _appoint(context, null)),
        ),
      ]),
    ),
  );
}

class _CompetitionStep extends StatelessWidget {
  const _CompetitionStep({required this.client, required this.clubId, required this.onDone});

  final OwnerOpsClient client;
  final String clubId;
  final VoidCallback onDone;

  @override
  Widget build(BuildContext context) => GtexPanel(
    key: const Key('owner-setup-competition'),
    title: 'Enter your first competition',
    subtitle: 'Step 4',
    accent: GtexColors.gold,
    child: OpsLoader(
      label: 'Competitions',
      load: () => client.get('/owner/competitions'),
      builder: (BuildContext context, Map<String, dynamic> d, _) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        for (final Map<String, dynamic> c in opsMaps(d['competitions']).where((Map<String, dynamic> c) => c['status'] == 'open' && c['host_type'] == 'gtex'))
          OpsLine(
            title: opsStr(c['name']),
            subtitle: '${opsStr(c['tier'], '')} · ${opsStr(c['format'])} · entry ${opsGtx(c['entry_fee'])} · pool ${opsGtx(c['prize_pool'])}',
            accent: GtexColors.gold,
            trailing: GtexActionButton(
              key: Key('owner-setup-enter-${c['id']}'),
              label: 'Enter',
              compact: true,
              onPressed: () async {
                if (await runOwnerAction(context, () => client.post('/owner/competitions/${c['id']}/enter', body: <String, Object?>{'club_id': clubId}), success: (_) => 'Entered. Your fixtures are in Competitions.') != null) onDone();
              },
            ),
          ),
        GtexActionButton(
          key: const Key('owner-setup-skip-competition'),
          label: 'Skip for now',
          compact: true,
          secondary: true,
          onPressed: () async {
            if (await runOwnerAction(context, () => client.post('/owner/clubs/$clubId/finish-onboarding')) != null) onDone();
          },
        ),
      ]),
    ),
  );
}

class _NewClubPanel extends StatefulWidget {
  const _NewClubPanel({required this.client, required this.count, required this.max, required this.onDone});

  final OwnerOpsClient client;
  final int count;
  final int max;
  final VoidCallback onDone;

  @override
  State<_NewClubPanel> createState() => _NewClubPanelState();
}

class _NewClubPanelState extends State<_NewClubPanel> {
  final TextEditingController _name = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => GtexPanel(
    key: const Key('owner-setup-new-club'),
    title: widget.count == 0 ? 'Name your club' : 'Add a club',
    subtitle: '${widget.count}/${widget.max} clubs',
    accent: GtexColors.pitch,
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
      if (widget.count > 0)
        const OpsNote('Owning several clubs makes you a labelled multi-club ownership group. Sister clubs cannot share a prize bracket, and transfers between them must sit inside a fair-value band.'),
      const SizedBox(height: GtexSpacing.xs),
      Wrap(spacing: GtexSpacing.sm, crossAxisAlignment: WrapCrossAlignment.center, children: <Widget>[
        OpsField(key: const Key('owner-new-club-name'), controller: _name, label: 'Club name', width: 260, onChanged: (_) => setState(() {})),
        GtexActionButton(
          key: const Key('owner-new-club-create'),
          label: _busy ? 'Creating...' : 'Create club',
          compact: true,
          onPressed: _name.text.trim().length < 3 || _busy
              ? null
              : () async {
                  setState(() => _busy = true);
                  final Map<String, dynamic>? r = await runOwnerAction(context, () => widget.client.post('/clubs', body: newClubBody(_name.text.trim(), DateTime.now().millisecondsSinceEpoch)));
                  if (mounted) setState(() => _busy = false);
                  if (r != null) widget.onDone();
                },
        ),
      ]),
    ]),
  );
}
