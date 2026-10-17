import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../data/owner_ops_api.dart';

String showroomShareUrl(String code, [Uri? base]) {
  final Uri b = base ?? Uri.base;
  return '${b.origin}${b.path}#/showroom/$code';
}

Color _hex(Object? v, Color fallback) {
  final String s = '${v ?? ''}'.replaceAll('#', '');
  final int? n = s.length == 6 ? int.tryParse(s, radix: 16) : null;
  return n == null ? fallback : Color(0xFF000000 | n);
}

/// A lightweight perspective trophy cabinet; drag sideways to turn it.
class ShowroomCabinet extends StatefulWidget {
  const ShowroomCabinet({super.key, required this.data});

  final Map<String, dynamic> data;

  @override
  State<ShowroomCabinet> createState() => _ShowroomCabinetState();
}

class _ShowroomCabinetState extends State<ShowroomCabinet> {
  double _angle = -0.18;

  Widget _shelf(String title, List<Widget> items, Color accent) => Container(
    margin: const EdgeInsets.only(bottom: GtexSpacing.sm),
    padding: const EdgeInsets.all(GtexSpacing.sm),
    decoration: BoxDecoration(
      gradient: LinearGradient(colors: <Color>[accent.withValues(alpha: 0.16), Colors.black.withValues(alpha: 0.35)], begin: Alignment.topCenter, end: Alignment.bottomCenter),
      border: Border(bottom: BorderSide(color: accent, width: 4)),
      borderRadius: BorderRadius.circular(6),
    ),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
      Text(title.toUpperCase(), style: TextStyle(color: accent, fontSize: 11, letterSpacing: 2, fontWeight: FontWeight.w900)),
      const SizedBox(height: 6),
      if (items.isEmpty) const Text('Space reserved for future glory', style: TextStyle(color: GtexColors.textMuted, fontSize: 12)) else Wrap(spacing: 10, runSpacing: 10, children: items),
    ]),
  );

  Widget _piece(IconData icon, Color color, String label, String sub) => SizedBox(
    width: 120,
    child: Column(children: <Widget>[
      Icon(icon, color: color, size: 34, shadows: <Shadow>[Shadow(color: color.withValues(alpha: 0.6), blurRadius: 12)]),
      Text(label, textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: GtexColors.text, fontSize: 12, fontWeight: FontWeight.w700)),
      Text(sub, textAlign: TextAlign.center, style: const TextStyle(color: GtexColors.textMuted, fontSize: 10)),
    ]),
  );

  Widget _crest(Map<String, dynamic> d, Color primary) {
    final Widget shield = Icon(Icons.shield_rounded, key: const Key('owner-showroom-crest'), color: primary, size: 56, shadows: <Shadow>[Shadow(color: primary.withValues(alpha: 0.6), blurRadius: 16)]);
    final String url = opsStr(d['crest_url'], '');
    if (!url.startsWith('http')) return shield;
    return Image.network(url, key: const Key('owner-showroom-crest'), width: 56, height: 56, fit: BoxFit.contain, errorBuilder: (_, __, ___) => shield);
  }

  @override
  Widget build(BuildContext context) {
    final Map<String, dynamic> d = widget.data;
    final Color primary = _hex(d['primary_color'], GtexColors.pitch);
    const List<Color> medals = <Color>[Color(0xFFF4C24D), Color(0xFFC0C7D1), Color(0xFFCD7F32)];
    return GestureDetector(
      key: const Key('owner-showroom-cabinet'),
      onHorizontalDragUpdate: (DragUpdateDetails u) => setState(() => _angle = (_angle + u.delta.dx / 300).clamp(-0.6, 0.6)),
      child: Transform(
        alignment: Alignment.center,
        transform: Matrix4.identity()
          ..setEntry(3, 2, 0.0012)
          ..rotateY(_angle)
          ..rotateX(0.04 * math.cos(_angle)),
        child: Container(
          padding: const EdgeInsets.all(GtexSpacing.md),
          decoration: BoxDecoration(
            color: const Color(0xFF0B0F14),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: primary.withValues(alpha: 0.7), width: 2),
            boxShadow: <BoxShadow>[BoxShadow(color: primary.withValues(alpha: 0.25), blurRadius: 30, spreadRadius: 2)],
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
            Row(children: <Widget>[
              _crest(d, primary),
              const SizedBox(width: GtexSpacing.sm),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                  Text(opsStr(d['club_name']), key: const Key('owner-showroom-name'), style: TextStyle(color: primary, fontSize: 26, fontWeight: FontWeight.w900)),
                  Text(<String>[opsStr(d['city'], ''), opsStr(d['country_code'], ''), if (d['founded'] != null) 'est. ${d['founded']}', if (d.containsKey('fans')) '${opsFmt(d['fans'])} fans', if (d.containsKey('prestige')) 'prestige ${opsStr(d['prestige'])}'].where((String s) => s.isNotEmpty).join(' · '), style: const TextStyle(color: GtexColors.textSecondary)),
                ]),
              ),
            ]),
            const SizedBox(height: GtexSpacing.md),
            _shelf('Trophies & honours', <Widget>[
              for (final Map<String, dynamic> t in opsMaps(d['trophies']))
                _piece(opsInt(t['position']) == 1 ? Icons.emoji_events_rounded : Icons.military_tech_rounded, medals[(opsInt(t['position']) - 1).clamp(0, 2)], opsStr(t['competition']), '${opsInt(t['position']) == 1 ? 'Winners' : '#${t['position']}'} ${opsStr(t['year'], '')}'),
            ], const Color(0xFFF4C24D)),
            if (d.containsKey('facilities')) _shelf('Facilities', <Widget>[
              for (final MapEntry<String, dynamic> f in opsMap(d['facilities']).entries) _piece(Icons.stadium_rounded, GtexColors.cyan, opsLabel(f.key), 'Level ${f.value}/5'),
            ], GtexColors.cyan),
            if (d.containsKey('sponsors')) _shelf('Partners', <Widget>[
              for (final Map<String, dynamic> s in opsMaps(d['sponsors'])) _piece(Icons.handshake_rounded, GtexColors.purple, opsStr(s['sponsor']), opsLabel(s['slot'])),
            ], GtexColors.purple),
            if (d.containsKey('top_players')) _shelf('Stars of the squad', <Widget>[
              for (final Map<String, dynamic> p in opsMaps(d['top_players'])) _piece(p['is_regen'] == true ? Icons.auto_awesome_rounded : Icons.person_rounded, primary, opsStr(p['name']), '${opsStr(p['position'])} · ${opsStr(p['rating'])} · ${opsStr(p['age'])}y'),
            ], primary),
          ]),
        ),
      ),
    );
  }
}

/// Owner preview of the showroom with a public share link.
class OwnerShowroomPanel extends StatefulWidget {
  const OwnerShowroomPanel({super.key, required this.client, required this.clubId});

  final OwnerOpsClient client;
  final String clubId;

  @override
  State<OwnerShowroomPanel> createState() => _OwnerShowroomPanelState();
}

class _OwnerShowroomPanelState extends State<OwnerShowroomPanel> {
  String? _link;

  @override
  Widget build(BuildContext context) => GtexPanel(
    key: const Key('owner-showroom'),
    title: 'Club showroom',
    subtitle: 'Drag to turn the cabinet · share it with supporters',
    accent: GtexColors.gold,
    child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
      OpsLoader(label: 'Showroom', load: () => widget.client.get('/owner/clubs/${widget.clubId}/showroom'), builder: (BuildContext context, Map<String, dynamic> d, _) => ShowroomCabinet(data: d)),
      const SizedBox(height: GtexSpacing.sm),
      Wrap(spacing: GtexSpacing.sm, crossAxisAlignment: WrapCrossAlignment.center, children: <Widget>[
        GtexActionButton(
          key: const Key('owner-showroom-share'),
          label: 'Share showroom link',
          icon: Icons.ios_share_rounded,
          compact: true,
          onPressed: () async {
            final Map<String, dynamic>? r = await runOwnerAction(context, () => widget.client.post('/owner/clubs/${widget.clubId}/showroom/share'), success: (_) => 'Showroom link copied');
            if (r == null) return;
            final String url = showroomShareUrl('${r['code']}');
            await Clipboard.setData(ClipboardData(text: url));
            if (mounted) setState(() => _link = url);
          },
        ),
        if (_link != null) SelectableText(_link!, key: const Key('owner-showroom-link'), style: const TextStyle(color: GtexColors.cyan, fontSize: 12)),
      ]),
    ]),
  );
}

/// Public showroom page supporters open without signing in.
class PublicShowroomScreen extends StatelessWidget {
  const PublicShowroomScreen({super.key, required this.load});

  final Future<Map<String, dynamic>> Function() load;

  @override
  Widget build(BuildContext context) => Scaffold(
    key: const Key('public-showroom'),
    backgroundColor: GtexColors.surfaceBase,
    body: SafeArea(
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 980),
          child: ListView(padding: const EdgeInsets.all(GtexSpacing.md), children: <Widget>[
            const Text('GTEX CLUB SHOWROOM', style: TextStyle(color: GtexColors.gold, letterSpacing: 3, fontWeight: FontWeight.w900, fontSize: 12)),
            const SizedBox(height: GtexSpacing.sm),
            OpsLoader(label: 'Showroom', load: load, builder: (BuildContext context, Map<String, dynamic> d, _) => ShowroomCabinet(data: d)),
          ]),
        ),
      ),
    ),
  );
}
