import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../data/owner_ops_api.dart';
import '../widgets/owner_admin_review_section.dart';
import 'owner_setup_section.dart';

typedef ClubOption = (String, String);

/// Club actions: facilities, treasury moves, commercial and disclosures.
class ClubOpsPanel extends StatelessWidget {
  const ClubOpsPanel({super.key, required this.client, required this.clubId, required this.clubs, required this.onChanged});

  final OwnerOpsClient client;
  final String clubId;
  final List<ClubOption> clubs;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) => OpsLoader(
    key: ValueKey<String>('owner-club-ops-$clubId'),
    label: 'Club',
    load: () => client.get('/owner/clubs/$clubId'),
    builder: (BuildContext context, Map<String, dynamic> club, VoidCallback reload) {
      void changed() {
        reload();
        onChanged();
      }

      final Map<String, dynamic> health = opsMap(club['health']);
      return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
        GtexPanel(
          key: const Key('owner-club-summary'),
          title: opsStr(club['club_name']),
          subtitle: opsStr(opsMap(club['ownership_group'])['label'], ''),
          accent: GtexColors.pitch,
          child: Wrap(spacing: GtexSpacing.md, runSpacing: GtexSpacing.sm, children: <Widget>[
            OpsStat('Club value', opsGtx(club['value'])),
            OpsStat('Fans', opsFmt(health['fans'])),
            OpsStat('Prestige', opsStr(health['prestige'])),
            OpsStat('Squad', opsStr(health['squad_size'])),
            OpsStat('Manager', opsStr(opsMap(club['manager'])['name'])),
            OpsStat('Status', opsStr(club['stage'])),
          ]),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          key: const Key('owner-club-facilities'),
          title: 'Facilities',
          accent: GtexColors.cyan,
          child: Column(children: <Widget>[
            for (final MapEntry<String, dynamic> f in opsMap(club['facilities']).entries)
              OpsLine(
                title: '${opsLabel(f.key)} · L${opsMap(f.value)['level']}/5',
                accent: GtexColors.cyan,
                trailing: GtexActionButton(
                  key: Key('owner-upgrade-${f.key}'),
                  label: opsMap(f.value)['next_cost'] == null ? 'Max level' : 'Upgrade · ${opsGtx(opsMap(f.value)['next_cost'])}',
                  compact: true,
                  secondary: true,
                  onPressed: opsMap(f.value)['next_cost'] == null
                      ? null
                      : () async {
                          final String? ok = await confirmOwnerAction(context, title: 'Upgrade ${opsLabel(f.key)}?', message: 'Costs ${opsGtx(opsMap(f.value)['next_cost'])} from club cash.', confirmLabel: 'Upgrade');
                          if (ok == null || !context.mounted) return;
                          if (await runOwnerAction(context, () => client.post('/owner/clubs/$clubId/facilities/${f.key}/upgrade'), success: (Map<String, dynamic> r) => '${opsLabel(f.key)} level ${r['level']}. ${opsStr(r['effect'], '')}') != null) changed();
                        },
                ),
              ),
          ]),
        ),
        const SizedBox(height: GtexSpacing.md),
        _CapitalPanel(client: client, club: club, clubs: clubs, onDone: changed),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          key: const Key('owner-club-sponsors'),
          title: 'Sponsors',
          subtitle: 'Commercial · 70/30 split',
          accent: GtexColors.gold,
          child: Column(children: <Widget>[
            if (opsMaps(club['sponsors']).isEmpty) const OpsNote('No sponsors. Sponsor offers arrive in your inbox as fans and commercial level grow.'),
            for (final Map<String, dynamic> s in opsMaps(club['sponsors']))
              OpsLine(title: opsStr(s['sponsor']), subtitle: '${opsStr(s['slot'])} · ${s['matches_remaining']} matches left', trailing: Text('${opsGtx(s['club_share'])} / match', style: const TextStyle(color: GtexColors.gold))),
          ]),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          key: const Key('owner-club-supporters'),
          title: 'Gift leaderboard',
          accent: GtexColors.purple,
          child: OpsLoader(
            label: 'Supporters',
            load: () => client.get('/owner/clubs/$clubId/supporters'),
            builder: (BuildContext context, Map<String, dynamic> d, _) => Column(children: <Widget>[
              if (opsMaps(d['leaderboard']).isEmpty) const OpsNote('No gifts yet. Fans gift during and after matches.'),
              for (final (int i, Map<String, dynamic> r) in opsMaps(d['leaderboard']).indexed)
                OpsLine(title: '${i + 1}. ${opsStr(r['username'])}', accent: GtexColors.purple, trailing: Text('${opsFmt(r['fan_coin_sent'])} FAN', style: const TextStyle(color: GtexColors.gold))),
            ]),
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          key: const Key('owner-club-disclosures'),
          title: 'Related-party history',
          accent: GtexColors.gold,
          child: Column(children: <Widget>[
            if (opsMaps(club['disclosures']).isEmpty) const OpsNote('No related-party transfers disclosed.'),
            for (final Map<String, dynamic> x in opsMaps(club['disclosures']))
              OpsLine(title: opsStr(x['player_name']), subtitle: 'fee ${opsFmt(x['fee'])} (fair value ${opsFmt(x['fair_value'])})', accent: GtexColors.gold),
          ]),
        ),
      ]);
    },
  );
}

class _CapitalPanel extends StatefulWidget {
  const _CapitalPanel({required this.client, required this.club, required this.clubs, required this.onDone});

  final OwnerOpsClient client;
  final Map<String, dynamic> club;
  final List<ClubOption> clubs;
  final VoidCallback onDone;

  @override
  State<_CapitalPanel> createState() => _CapitalPanelState();
}

class _CapitalPanelState extends State<_CapitalPanel> {
  final TextEditingController _amount = TextEditingController(text: '1000');
  String? _target;

  @override
  void dispose() {
    _amount.dispose();
    super.dispose();
  }

  Future<void> _run(String path, Map<String, Object?> body, String ok) async {
    final String? confirmed = await confirmOwnerAction(context, title: ok, message: '${opsGtx(_amount.text)} will move on the unified ledger.', confirmLabel: 'Confirm');
    if (confirmed == null || !mounted) return;
    if (await runOwnerAction(context, () => widget.client.post(path, body: body), success: (_) => ok) != null) widget.onDone();
  }

  @override
  Widget build(BuildContext context) {
    final String clubId = '${widget.club['club_id']}';
    final Map<String, dynamic> econ = opsMap(widget.club['economy']);
    final List<ClubOption> sisters = widget.clubs.where((ClubOption c) => c.$1 != clubId).toList();
    final double amount = opsNum(_amount.text);
    return GtexPanel(
      key: const Key('owner-club-capital'),
      title: 'Treasury',
      subtitle: 'Approved capital actions',
      accent: GtexColors.pitch,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        Wrap(spacing: GtexSpacing.md, children: <Widget>[OpsStat('Club cash', opsGtx(econ['cash_gtex'])), OpsStat('Pending payouts', opsGtx(econ['pending_payouts']))]),
        const SizedBox(height: GtexSpacing.sm),
        Wrap(spacing: GtexSpacing.sm, runSpacing: GtexSpacing.sm, crossAxisAlignment: WrapCrossAlignment.center, children: <Widget>[
          OpsField(key: const Key('owner-capital-amount'), controller: _amount, label: 'Amount (GTX)', number: true, width: 150, onChanged: (_) => setState(() {})),
          GtexActionButton(key: const Key('owner-capital-inject'), label: 'Inject from wallet', compact: true, secondary: true, onPressed: amount > 0 ? () => _run('/owner/capital/inject', <String, Object?>{'club_id': clubId, 'amount': amount}, 'Capital injected from your wallet.') : null),
          GtexActionButton(key: const Key('owner-capital-distribute'), label: 'Distribute earnings', compact: true, secondary: true, onPressed: amount > 0 ? () => _run('/owner/capital/distribute', <String, Object?>{'club_id': clubId, 'amount': amount}, 'Distributed earned revenue to your wallet.') : null),
        ]),
        const OpsNote('Only earned club revenue (gate, prizes, sponsors, sales) can be distributed. Launch grants stay in the club.'),
        if (sisters.isNotEmpty) ...<Widget>[
          const SizedBox(height: GtexSpacing.sm),
          const Text('Move to sister club (capped 25%, disclosed)', style: TextStyle(color: GtexColors.textSecondary, fontSize: 12)),
          Wrap(spacing: GtexSpacing.sm, crossAxisAlignment: WrapCrossAlignment.center, children: <Widget>[
            OpsSelect(key: const Key('owner-sister-club-select'), value: _target, options: sisters, hint: 'Select club', onChanged: (String? v) => setState(() => _target = v)),
            GtexActionButton(key: const Key('owner-sister-capital-move'), label: 'Move', compact: true, secondary: true, onPressed: _target == null || amount <= 0 ? null : () => _run('/owner/capital/sister-transfer', <String, Object?>{'from_club_id': clubId, 'to_club_id': _target, 'amount': amount}, 'Related-party capital move ledgered.')),
          ]),
        ],
      ]),
    );
  }
}

/// Manager sheet, hire/fire, default mentality, squad list, signings and sister-club player moves.
class SquadOpsPanel extends StatelessWidget {
  const SquadOpsPanel({super.key, required this.client, required this.clubId, required this.clubs, required this.onChanged});

  final OwnerOpsClient client;
  final String clubId;
  final List<ClubOption> clubs;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) => OpsLoader(
    key: ValueKey<String>('owner-squad-ops-$clubId'),
    label: 'Squad',
    load: () => client.get('/owner/clubs/$clubId'),
    builder: (BuildContext context, Map<String, dynamic> club, VoidCallback reload) {
      void changed() {
        reload();
        onChanged();
      }

      final Map<String, dynamic> m = opsMap(club['manager_profile']);
      final List<Map<String, dynamic>> squad = opsMaps(club['squad']);
      return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
        GtexPanel(
          key: const Key('owner-manager-sheet'),
          title: opsStr(m['name'], 'Manager'),
          subtitle: 'Manager realism engine',
          accent: GtexColors.cyan,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
            Wrap(spacing: GtexSpacing.xs, runSpacing: GtexSpacing.xs, children: <Widget>[
              for (final String k in <String>['tactical_preference', 'temperament', 'discipline_style', 'media_style', 'transfer_preference'])
                if (m[k] != null) GtexStatusChip(label: '${opsLabel(k)}: ${opsLabel(m[k])}', color: GtexColors.cyan, compact: true),
            ]),
            const SizedBox(height: GtexSpacing.sm),
            Wrap(spacing: GtexSpacing.md, runSpacing: GtexSpacing.sm, children: <Widget>[
              OpsStat('Mood', '${opsStr(m['mood'])}/100', key: const Key('owner-manager-mood')),
              for (final String k in <String>['ambition', 'loyalty', 'youth_development', 'tactical_quality']) OpsStat(opsLabel(k), '${opsStr(m[k])}/20'),
            ]),
            OpsNote(opsStr(m['philosophy'], '')),
            if (m['is_default'] != true)
              GtexActionButton(
                key: const Key('owner-fire-manager'),
                label: 'Dismiss manager',
                compact: true,
                secondary: true,
                accent: GtexColors.red,
                onPressed: () async {
                  final String? ok = await confirmOwnerAction(context, title: 'Dismiss ${opsStr(m['name'])}?', message: 'Dismissing the manager triggers compensation and unsettles the squad.', confirmLabel: 'Dismiss');
                  if (ok == null || !context.mounted) return;
                  if (await runOwnerAction(context, () => client.post('/owner/clubs/$clubId/manager/fire'), success: (Map<String, dynamic> r) => 'Paid ${opsGtx(r['compensation'])} compensation. ${opsStr(r['why'], '')}') != null) changed();
                },
              ),
          ]),
        ),
        if (m['is_default'] == true) ...<Widget>[
          const SizedBox(height: GtexSpacing.md),
          GtexPanel(
            key: const Key('owner-hire-manager'),
            title: 'Available managers',
            accent: GtexColors.cyan,
            child: OpsLoader(
              label: 'Managers',
              load: () => client.get('/managers/catalog', query: const <String, Object?>{'limit': 6}),
              builder: (BuildContext context, Map<String, dynamic> d, _) => Column(children: <Widget>[
                for (final Map<String, dynamic> x in opsMaps(d['items']))
                  OpsLine(
                    title: opsStr(x['display_name']),
                    subtitle: '${opsStr(x['rarity'])} · ${opsStr(x['mentality'])}',
                    trailing: GtexActionButton(
                      key: Key('owner-hire-${x['manager_id']}'),
                      label: 'Appoint',
                      compact: true,
                      secondary: true,
                      onPressed: () async {
                        if (await runOwnerAction(context, () => client.post('/owner/clubs/$clubId/manager', body: <String, Object?>{'manager': managerBody(x)}), success: (_) => '${opsStr(x['display_name'])} appointed') != null) changed();
                      },
                    ),
                  ),
              ]),
            ),
          ),
        ],
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          key: const Key('owner-squad-list'),
          title: 'Squad',
          subtitle: '${squad.length} players · default mentality ${opsStr(club['mentality'])}',
          accent: GtexColors.pitch,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
            Wrap(spacing: GtexSpacing.xs, children: <Widget>[
              for (final String x in <String>['defensive', 'balanced', 'attacking'])
                GtexActionButton(
                  key: Key('owner-default-mentality-$x'),
                  label: x,
                  compact: true,
                  secondary: club['mentality'] != x,
                  onPressed: () async {
                    if (await runOwnerAction(context, () => client.put('/owner/clubs/$clubId/mentality', body: <String, Object?>{'mentality': x}), success: (_) => 'Default mentality: $x') != null) changed();
                  },
                ),
            ]),
            const SizedBox(height: GtexSpacing.sm),
            for (final Map<String, dynamic> p in squad)
              OpsLine(
                key: Key('owner-squad-player-${p['id']}'),
                title: '${opsStr(p['name'])}${p['is_regen'] == true ? ' · regen' : ''}${p['status'] == 'listed' ? ' · listed' : ''}${opsInt(p['injured_days']) > 0 ? ' · injured' : ''}',
                subtitle: '${opsStr(p['position'])} · age ${opsStr(p['age'])} · ${opsStr(p['rating'])}/${opsStr(p['potential'])} · morale ${opsStr(p['morale'])} · ${opsStr(p['minutes'])} mins',
                accent: opsInt(p['morale']) >= 65 ? GtexColors.pitch : opsInt(p['morale']) >= 45 ? GtexColors.gold : GtexColors.red,
                trailing: Text(opsGtx(p['value_coin']), style: const TextStyle(color: GtexColors.textSecondary, fontSize: 12)),
              ),
          ]),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          key: const Key('owner-squad-signings'),
          title: 'Sign players',
          subtitle: 'Fees are paid from club cash and recorded on the unified ledger',
          accent: GtexColors.gold,
          child: OwnerMarketSignList(client: client, clubId: clubId, signedRefs: squad.map((Map<String, dynamic> p) => '${p['player_ref']}').toSet(), onSigned: (_) => changed()),
        ),
        const SizedBox(height: GtexSpacing.md),
        _SisterTransfer(client: client, clubId: clubId, squad: squad, sisters: clubs.where((ClubOption c) => c.$1 != clubId).toList(), onDone: changed),
      ]);
    },
  );
}

class _SisterTransfer extends StatefulWidget {
  const _SisterTransfer({required this.client, required this.clubId, required this.squad, required this.sisters, required this.onDone});

  final OwnerOpsClient client;
  final String clubId;
  final List<Map<String, dynamic>> squad;
  final List<ClubOption> sisters;
  final VoidCallback onDone;

  @override
  State<_SisterTransfer> createState() => _SisterTransferState();
}

class _SisterTransferState extends State<_SisterTransfer> {
  final TextEditingController _fee = TextEditingController();
  String? _player;
  String? _to;
  Map<String, dynamic>? _check;

  @override
  void dispose() {
    _fee.dispose();
    super.dispose();
  }

  Map<String, Object?> _body() => <String, Object?>{'player_id': _player, 'to_club_id': _to, 'fee': opsNum(_fee.text)};

  @override
  Widget build(BuildContext context) {
    final Map<String, dynamic>? c = _check;
    return GtexPanel(
      key: const Key('owner-sister-transfer'),
      title: 'Sister-club transfer',
      subtitle: 'Related-party · anti-collusion',
      accent: GtexColors.gold,
      child: widget.sisters.isEmpty
          ? const OpsNote('Own a second club to move players between sister clubs. Related-party rules apply: no free transfers, fee within 80-130% of fair value, 14-day reciprocal cooldown, and repeated shuffling is flagged.')
          : Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              Wrap(spacing: GtexSpacing.sm, runSpacing: GtexSpacing.sm, crossAxisAlignment: WrapCrossAlignment.center, children: <Widget>[
                OpsSelect(key: const Key('owner-sister-player'), value: _player, hint: 'Player', options: <ClubOption>[for (final Map<String, dynamic> p in widget.squad) ('${p['id']}', '${opsStr(p['name'])} · value ${opsFmt(p['value_coin'])}')], onChanged: (String? v) => setState(() {
                  _player = v;
                  _check = null;
                })),
                OpsSelect(key: const Key('owner-sister-target'), value: _to, hint: 'To club', options: widget.sisters, onChanged: (String? v) => setState(() {
                  _to = v;
                  _check = null;
                })),
                OpsField(key: const Key('owner-sister-fee'), controller: _fee, label: 'Fee (GTX)', number: true, width: 120, onChanged: (_) => setState(() => _check = null)),
              ]),
              const SizedBox(height: GtexSpacing.sm),
              Wrap(spacing: GtexSpacing.xs, children: <Widget>[
                GtexActionButton(
                  key: const Key('owner-sister-check'),
                  label: 'Check fair-value rules',
                  compact: true,
                  secondary: true,
                  onPressed: _player == null || _to == null
                      ? null
                      : () async {
                          final Map<String, dynamic>? r = await runOwnerAction(context, () => widget.client.post('/owner/transfers/internal/check', body: _body()));
                          if (r != null && mounted) setState(() => _check = r);
                        },
                ),
                GtexActionButton(
                  key: const Key('owner-sister-execute'),
                  label: 'Execute transfer',
                  compact: true,
                  onPressed: c?['allowed'] != true
                      ? null
                      : () async {
                          final Map<String, dynamic>? r = await runOwnerAction(context, () => widget.client.post('/owner/transfers/internal', body: _body()), success: (Map<String, dynamic> r) => 'Transfer complete. ${(r['notes'] as List<dynamic>? ?? const <dynamic>[]).join(' ')}');
                          if (r != null) {
                            setState(() => _check = null);
                            widget.onDone();
                          }
                        },
                ),
              ]),
              if (c != null) ...<Widget>[
                OpsNote('Fair value ${opsFmt(c['fair_value'])} · allowed band ${opsFmt((c['band'] as List<dynamic>?)?.first)}-${opsFmt((c['band'] as List<dynamic>?)?.last)}', key: const Key('owner-sister-check-result'), color: GtexColors.textSecondary),
                Wrap(spacing: GtexSpacing.xs, children: <Widget>[
                  for (final MapEntry<String, dynamic> r in opsMap(c['rules']).entries) GtexStatusChip(label: opsLabel(r.key), color: r.value == true ? GtexColors.pitch : GtexColors.red, compact: true),
                ]),
                if (c['shuffle_flag_risk'] == true) const OpsNote("Warning: this would be a repeated related-party move. It will be flagged and the player's morale will drop.", color: GtexColors.gold),
              ],
            ]),
    );
  }
}

const List<String> _traits = <String>['ambition', 'loyalty', 'marketability', 'professionalism', 'adaptability', 'growth_responsiveness', 'environment_sensitivity'];

/// Academy intake, world-day advance and regen growth cards.
class AcademyOpsPanel extends StatelessWidget {
  const AcademyOpsPanel({super.key, required this.client, required this.clubId, required this.onChanged});

  final OwnerOpsClient client;
  final String clubId;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) => OpsLoader(
    key: ValueKey<String>('owner-academy-ops-$clubId'),
    label: 'Academy',
    load: () => client.get('/owner/clubs/$clubId'),
    builder: (BuildContext context, Map<String, dynamic> club, VoidCallback reload) {
      void changed() {
        reload();
        onChanged();
      }

      final Map<String, dynamic> fac = opsMap(club['facilities']);
      final int academyLevel = opsInt(opsMap(fac['academy'])['level']);
      final List<Map<String, dynamic>> regens = opsMaps(club['squad']).where((Map<String, dynamic> p) => p['is_regen'] == true).toList();
      return GtexPanel(
        key: const Key('owner-academy-ops'),
        title: 'The youth pipeline',
        subtitle: 'Regens grow from facilities, manager youth skill, minutes, competition quality, morale and prestige',
        accent: GtexColors.pitch,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
          Wrap(spacing: GtexSpacing.md, runSpacing: GtexSpacing.sm, children: <Widget>[
            OpsStat('Training', 'L${opsMap(fac['training'])['level']}'),
            OpsStat('Academy', 'L$academyLevel'),
            OpsStat('Manager youth skill', '${opsStr(opsMap(club['manager_profile'])['youth_development'])}/20'),
            OpsStat('Prestige', opsStr(opsMap(club['health'])['prestige'])),
            OpsStat('Academy value', opsGtx(regens.fold<double>(0, (double s, Map<String, dynamic> p) => s + opsNum(p['value_coin'])))),
          ]),
          const SizedBox(height: GtexSpacing.sm),
          Wrap(spacing: GtexSpacing.xs, children: <Widget>[
            GtexActionButton(
              key: const Key('owner-academy-intake'),
              label: 'Scout intake · ${opsFmt(1500 * academyLevel)} GTX',
              icon: Icons.spa_rounded,
              compact: true,
              onPressed: () async {
                final String? ok = await confirmOwnerAction(context, title: 'Run a scouting intake?', message: 'Costs ${opsFmt(1500 * academyLevel)} GTX from club cash.', confirmLabel: 'Scout');
                if (ok == null || !context.mounted) return;
                if (await runOwnerAction(context, () => client.post('/owner/clubs/$clubId/academy/intake'), success: (Map<String, dynamic> r) => '${opsMaps(r['regens']).length} new regens joined the academy') != null) changed();
              },
            ),
            GtexActionButton(
              key: const Key('owner-academy-advance'),
              label: 'Advance world day',
              compact: true,
              secondary: true,
              onPressed: () async {
                if (await runOwnerAction(context, () => client.post('/owner/clubs/$clubId/advance'), success: (_) => 'World day advanced: growth applied') != null) changed();
              },
            ),
          ]),
          const SizedBox(height: GtexSpacing.sm),
          if (regens.isEmpty) const OpsNote('No regens yet. Run a scouting intake to bring in your first academy prospects.'),
          for (final Map<String, dynamic> p in regens) _RegenCard(p: p),
        ]),
      );
    },
  );
}

class _RegenCard extends StatelessWidget {
  const _RegenCard({required this.p});

  final Map<String, dynamic> p;

  @override
  Widget build(BuildContext context) {
    final Map<String, dynamic> t = opsMap(p['personality']);
    final List<Map<String, dynamic>> log = opsMaps(p['growth_log']);
    final int pressure = opsInt(t['transfer_pressure']);
    final int ceiling = (opsInt(p['potential']) - opsInt(p['rating'])).clamp(0, 99);
    final String badge = pressure >= 60 ? 'Unsettled' : ceiling >= 15 ? 'Wonderkid' : 'Academy';
    return Container(
      key: Key('owner-regen-${p['id']}'),
      margin: const EdgeInsets.only(bottom: GtexSpacing.sm),
      padding: const EdgeInsets.all(GtexSpacing.sm),
      decoration: BoxDecoration(color: GtexColors.panelStrong, borderRadius: BorderRadius.circular(8)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        Row(children: <Widget>[
          Expanded(child: Text('${opsStr(p['name'])} · ${opsStr(p['position'])} · ${opsStr(p['age'])}', style: const TextStyle(color: GtexColors.text, fontWeight: FontWeight.w800))),
          GtexStatusChip(label: badge, color: badge == 'Unsettled' ? GtexColors.red : badge == 'Wonderkid' ? GtexColors.gold : GtexColors.pitch, compact: true),
        ]),
        const SizedBox(height: 4),
        LinearProgressIndicator(value: (opsNum(p['rating']) / (opsNum(p['potential']) == 0 ? 1 : opsNum(p['potential']))).clamp(0, 1), color: GtexColors.pitch, backgroundColor: GtexColors.line),
        OpsNote('Rating ${opsStr(p['rating'])}/${opsStr(p['potential'])} · ceiling +$ceiling · morale ${opsStr(p['morale'])} · ${opsStr(p['minutes'])} mins · value ${opsGtx(p['value_coin'])}', color: GtexColors.textSecondary),
        Wrap(spacing: GtexSpacing.sm, children: <Widget>[
          for (final String k in _traits) Text('${opsLabel(k)} ${opsStr(t[k], '0')}', style: const TextStyle(color: GtexColors.textMuted, fontSize: 11)),
          Text('transfer pressure $pressure', style: TextStyle(color: pressure >= 60 ? GtexColors.red : GtexColors.textMuted, fontSize: 11)),
        ]),
        if (log.isNotEmpty) OpsNote('Day ${log.last['day']} · +${log.last['gain']} · ${opsStr(log.last['explanation'], '')}', color: GtexColors.textSecondary),
      ]),
    );
  }
}
