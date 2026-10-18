import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../data/owner_ops_api.dart';

String clubPageUrl(String clubId, [Uri? base]) {
  final Uri b = base ?? Uri.base;
  return '${b.origin}${b.path}#/club-page/$clubId';
}

String clubLocation(Map<String, dynamic> o) =>
    <String>[opsStr(o['city'], ''), opsStr(o['country_code'], ''), opsStr(opsMap(o['continent'])['label'], '')].where((String s) => s.isNotEmpty).join(' · ');

Color _hex(Object? v, Color fallback) {
  final String s = '${v ?? ''}'.replaceAll('#', '');
  final int? n = s.length == 6 ? int.tryParse(s, radix: 16) : null;
  return n == null ? fallback : Color(0xFF000000 | n);
}

Widget _tabList(List<Widget> children) => ListView(padding: const EdgeInsets.symmetric(vertical: GtexSpacing.md), children: children);

Widget _empty(String text) => OpsNote(text);

class _ClubHeader extends StatelessWidget {
  const _ClubHeader({required this.o});

  final Map<String, dynamic> o;

  @override
  Widget build(BuildContext context) {
    final Color primary = _hex(o['primary_color'], GtexColors.pitch);
    final String crest = opsStr(o['crest_url'], '');
    final Widget shield = Icon(Icons.shield_rounded, color: primary, size: 52);
    return Row(children: <Widget>[
      crest.startsWith('http') ? Image.network(crest, width: 52, height: 52, errorBuilder: (_, __, ___) => shield) : shield,
      const SizedBox(width: GtexSpacing.sm),
      Expanded(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
          Text(opsStr(o['club_name']), key: const Key('club-page-name'), style: TextStyle(color: primary, fontSize: 26, fontWeight: FontWeight.w900)),
          Text(clubLocation(o), key: const Key('club-page-location'), style: const TextStyle(color: GtexColors.textSecondary)),
        ]),
      ),
    ]);
  }
}

List<Widget> _overview(Map<String, dynamic> o) => <Widget>[
  Wrap(spacing: GtexSpacing.md, runSpacing: GtexSpacing.sm, children: <Widget>[
    OpsStat('Status', opsLabel(o['status'])),
    OpsStat('Prestige', opsStr(o['prestige'])),
    OpsStat('Fans', opsFmt(o['fans'])),
    OpsStat('Fan engagement', '${opsStr(o['fan_engagement'])}/100'),
    OpsStat('Squad size', opsStr(o['squad_size'])),
    OpsStat('Academy players', opsStr(o['academy_players'])),
    OpsStat('Founded', opsStr(o['founded'])),
    OpsStat('Home venue', opsStr(o['venue'])),
  ]),
  if (opsStr(o['description'], '').isNotEmpty) OpsNote(opsStr(o['description']), color: GtexColors.textSecondary),
];

List<Widget> _honours(Map<String, dynamic> h) {
  const List<Color> medals = <Color>[Color(0xFFF4C24D), Color(0xFFC0C7D1), Color(0xFFCD7F32)];
  return <Widget>[
    const Text('TROPHY CABINET', style: TextStyle(color: GtexColors.gold, fontSize: 11, letterSpacing: 2, fontWeight: FontWeight.w900)),
    if (opsMaps(h['trophies']).isEmpty) _empty('No podium finishes yet.'),
    for (final Map<String, dynamic> t in opsMaps(h['trophies']))
      OpsLine(title: opsStr(t['competition']), subtitle: '${opsInt(t['position']) == 1 ? 'Winners' : 'Finished #${t['position']}'} · ${opsStr(t['year'], '')}', accent: medals[(opsInt(t['position']) - 1).clamp(0, 2)]),
    const SizedBox(height: GtexSpacing.sm),
    const Text('MILESTONES', style: TextStyle(color: GtexColors.cyan, fontSize: 11, letterSpacing: 2, fontWeight: FontWeight.w900)),
    if (opsMaps(h['milestones']).isEmpty) _empty('History starts with the first season.'),
    for (final Map<String, dynamic> m in opsMaps(h['milestones'])) OpsLine(title: opsStr(m['label']), subtitle: opsStr(m['year'], ''), accent: GtexColors.cyan),
    const SizedBox(height: GtexSpacing.sm),
    const Text('COMPETITION RECORD', style: TextStyle(color: GtexColors.pitch, fontSize: 11, letterSpacing: 2, fontWeight: FontWeight.w900)),
    if (opsMaps(h['record']).isEmpty) _empty('No competitions entered yet.'),
    for (final Map<String, dynamic> r in opsMaps(h['record']))
      OpsLine(
        title: '${opsStr(r['competition'])} · ${opsStr(r['tier'], '')}',
        subtitle: 'P${opsStr(r['played'], '0')} W${opsStr(r['won'], '0')} D${opsStr(r['drawn'], '0')} L${opsStr(r['lost'], '0')} · ${opsStr(r['goals_for'], '0')}-${opsStr(r['goals_against'], '0')}${r['position'] == null ? ' · in progress' : ' · finished #${r['position']}'}',
        accent: GtexColors.pitch,
      ),
  ];
}

List<Widget> _staff(Map<String, dynamic> s) => <Widget>[
  OpsLine(title: 'Owner', subtitle: opsStr(s['owner']), accent: GtexColors.gold),
  for (final Map<String, dynamic> e in opsMaps(s['executives'])) OpsLine(title: opsStr(e['role_label']), subtitle: '${opsStr(e['name'])} · quality ${opsStr(e['quality'])}/20 · ${opsLabel(e['style'])}', accent: GtexColors.cyan),
  if (opsMaps(s['executives']).isEmpty) _empty('No General Manager or Head of Youth Development hired yet.'),
  if (s['manager'] != null)
    OpsLine(title: 'Football Manager', subtitle: '${opsStr(opsMap(s['manager'])['name'])} · ${opsLabel(opsMap(s['manager'])['temperament'])} · ${opsLabel(opsMap(s['manager'])['tactical_preference'])}', accent: GtexColors.pitch),
];

List<Widget> _facilities(Map<String, dynamic> f) => <Widget>[
  for (final MapEntry<String, dynamic> e in f.entries)
    Padding(
      padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        Text('${opsLabel(e.key)} · level ${e.value}/5', style: const TextStyle(color: GtexColors.text, fontWeight: FontWeight.w700)),
        const SizedBox(height: 4),
        LinearProgressIndicator(value: (opsNum(e.value) / 5).clamp(0, 1), color: GtexColors.cyan, backgroundColor: GtexColors.line),
      ]),
    ),
];

List<Widget> _commercial(Map<String, dynamic> c) => <Widget>[
  Wrap(spacing: GtexSpacing.md, children: <Widget>[OpsStat('Fans', opsFmt(c['fans'])), OpsStat('Support-unit holders', opsStr(c['supporter_holders'], '0'))]),
  const SizedBox(height: GtexSpacing.sm),
  if (opsMaps(c['sponsors']).isEmpty) _empty('No active sponsors.'),
  for (final Map<String, dynamic> s in opsMaps(c['sponsors'])) OpsLine(title: opsStr(s['sponsor']), subtitle: opsLabel(s['slot']), accent: GtexColors.purple),
];

/// Club page with public tabs; owners can pass extra private tabs.
class ClubPageTabs extends StatelessWidget {
  const ClubPageTabs({super.key, required this.data, this.extra = const <(String, Widget)>[]});

  final Map<String, dynamic> data;
  final List<(String, Widget)> extra;

  @override
  Widget build(BuildContext context) {
    final List<(String, Widget)> tabs = <(String, Widget)>[
      ('Overview', _tabList(_overview(opsMap(data['overview'])))),
      ('Honours & history', _tabList(_honours(opsMap(data['honours'])))),
      ('Staff', _tabList(_staff(opsMap(data['staff'])))),
      ('Facilities', _tabList(_facilities(opsMap(data['facilities'])))),
      ('Commercial', _tabList(_commercial(opsMap(data['commercial'])))),
      ...extra,
    ];
    return DefaultTabController(
      length: tabs.length,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
        _ClubHeader(o: opsMap(data['overview'])),
        const SizedBox(height: GtexSpacing.sm),
        TabBar(
          isScrollable: true,
          tabAlignment: TabAlignment.start,
          labelColor: GtexColors.pitch,
          unselectedLabelColor: GtexColors.textSecondary,
          indicatorColor: GtexColors.pitch,
          tabs: <Widget>[for (final (String label, _) in tabs) Tab(key: Key('club-page-tab-${label.toLowerCase().replaceAll(RegExp(r'[^a-z]+'), '-')}'), text: label)],
        ),
        Expanded(child: TabBarView(children: <Widget>[for (final (_, Widget w) in tabs) w])),
      ]),
    );
  }
}

/// Public club page supporters open without signing in.
class PublicClubPageScreen extends StatelessWidget {
  const PublicClubPageScreen({super.key, required this.load});

  final Future<Map<String, dynamic>> Function() load;

  @override
  Widget build(BuildContext context) => Scaffold(
    key: const Key('public-club-page'),
    backgroundColor: GtexColors.surfaceBase,
    body: SafeArea(
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 980),
          child: Padding(
            padding: const EdgeInsets.all(GtexSpacing.md),
            child: OpsLoader(label: 'Club page', load: load, builder: (BuildContext context, Map<String, dynamic> d, _) => ClubPageTabs(data: d)),
          ),
        ),
      ),
    ),
  );
}

class _NetWorthTab extends StatelessWidget {
  const _NetWorthTab({required this.client});

  final OwnerOpsClient client;

  @override
  Widget build(BuildContext context) => OpsLoader(
    label: 'Net worth',
    load: () => client.get('/owner/net-worth'),
    builder: (BuildContext context, Map<String, dynamic> d, _) => _tabList(<Widget>[
      Wrap(spacing: GtexSpacing.md, runSpacing: GtexSpacing.sm, children: <Widget>[
        OpsStat('Net worth', opsGtx(d['net_worth']), key: const Key('owner-net-worth-total'), color: GtexColors.gold),
        OpsStat('Personal cash', opsGtx(d['personal_cash'])),
        OpsStat('Club equity', opsGtx(d['equity'])),
        OpsStat('Liabilities', opsGtx(d['liabilities'])),
        OpsStat('Fan Coin (not counted)', '${opsFmt(d['fan_coin'])} FAN'),
      ]),
      const SizedBox(height: GtexSpacing.sm),
      for (final Map<String, dynamic> c in opsMaps(d['clubs']))
        OpsLine(
          key: Key('owner-net-worth-club-${c['club_id']}'),
          title: '${opsStr(c['club_name'])} · your stake ${opsStr(c['stake_pct'])}%',
          subtitle: 'Valuation ${opsGtx(opsMap(c['valuation'])['total'])} = squad ${opsFmt(opsMap(c['valuation'])['squad'])} + facilities ${opsFmt(opsMap(c['valuation'])['facilities'])} + 50% cash ${opsFmt(opsMap(c['valuation'])['cash'])} + fan base ${opsFmt(opsMap(c['valuation'])['fan_base'])}',
          accent: GtexColors.gold,
          trailing: Text(opsGtx(c['stake_value']), style: const TextStyle(color: GtexColors.gold, fontWeight: FontWeight.w800)),
        ),
      OpsNote(opsStr(d['method'], '')),
    ]),
  );
}

class _MoneyHistoryTab extends StatelessWidget {
  const _MoneyHistoryTab({required this.client, required this.clubId});

  final OwnerOpsClient client;
  final String clubId;

  @override
  Widget build(BuildContext context) => OpsLoader(
    label: 'Money history',
    load: () => client.get('/owner/clubs/$clubId/money-history'),
    builder: (BuildContext context, Map<String, dynamic> d, _) => _tabList(<Widget>[
      Wrap(spacing: GtexSpacing.md, children: <Widget>[
        OpsStat('Lifetime income', opsGtx(d['lifetime_income']), key: const Key('owner-money-income'), color: GtexColors.pitch),
        OpsStat('Lifetime spend', opsGtx(d['lifetime_spend']), key: const Key('owner-money-spend'), color: GtexColors.red),
      ]),
      Wrap(spacing: GtexSpacing.xs, runSpacing: GtexSpacing.xs, children: <Widget>[
        for (final MapEntry<String, dynamic> e in opsMap(d['income_by_type']).entries) GtexStatusChip(label: '+ ${opsLabel(e.key)} ${opsFmt(e.value)}', color: GtexColors.pitch, compact: true),
        for (final MapEntry<String, dynamic> e in opsMap(d['spend_by_type']).entries) GtexStatusChip(label: '- ${opsLabel(e.key)} ${opsFmt(e.value)}', color: GtexColors.red, compact: true),
      ]),
      const SizedBox(height: GtexSpacing.sm),
      if (opsMaps(d['events']).isEmpty) _empty('No club money movements yet.'),
      for (final Map<String, dynamic> e in opsMaps(d['events']))
        OpsLine(
          title: '${e['direction'] == 'in' ? '+' : '-'}${opsGtx(e['amount'])} · ${opsLabel(e['event_type'])}',
          subtitle: '${opsStr(e['memo'], '')} · balance ${opsFmt(e['balance_after'])} · ${opsStr(e['created_at'], '').split('T').first}',
          accent: e['direction'] == 'in' ? GtexColors.pitch : GtexColors.red,
        ),
    ]),
  );
}

/// Owner view: the public club page plus private Net worth and Money history tabs.
class OwnerClubPageSection extends StatelessWidget {
  const OwnerClubPageSection({super.key, required this.client, required this.clubId});

  final OwnerOpsClient client;
  final String clubId;

  @override
  Widget build(BuildContext context) => Padding(
    key: const Key('owner-club-page'),
    padding: const EdgeInsets.all(GtexSpacing.md),
    child: OpsLoader(
      label: 'Club page',
      load: () => client.get('/owner/public/clubs/$clubId'),
      builder: (BuildContext context, Map<String, dynamic> d, _) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
        Align(
          alignment: Alignment.centerRight,
          child: GtexActionButton(
            key: const Key('owner-club-page-copy-link'),
            label: 'Copy public page link',
            icon: Icons.link_rounded,
            compact: true,
            secondary: true,
            onPressed: () async {
              await Clipboard.setData(ClipboardData(text: clubPageUrl(clubId)));
              if (context.mounted) ScaffoldMessenger.maybeOf(context)?.showSnackBar(const SnackBar(key: Key('owner-ops-snackbar'), content: Text('Public club page link copied')));
            },
          ),
        ),
        Expanded(child: ClubPageTabs(data: d, extra: <(String, Widget)>[('Net worth', _NetWorthTab(client: client)), ('Money history', _MoneyHistoryTab(client: client, clubId: clubId))])),
      ]),
    ),
  );
}
