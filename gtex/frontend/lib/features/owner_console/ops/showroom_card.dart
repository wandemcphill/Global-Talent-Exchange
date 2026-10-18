import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';
import 'package:share_plus/share_plus.dart';

import '../data/owner_ops_api.dart';

const double showroomCardSide = 540;

Color _hex(Object? v, Color fallback) {
  final String s = '${v ?? ''}'.replaceAll('#', '');
  final int? n = s.length == 6 ? int.tryParse(s, radix: 16) : null;
  return n == null ? fallback : Color(0xFF000000 | n);
}

/// Square showroom card (540 logical px, exported at 2x = 1080x1080).
class ShowroomShareCard extends StatelessWidget {
  const ShowroomShareCard({super.key, required this.data, required this.link});

  final Map<String, dynamic> data;
  final String link;

  @override
  Widget build(BuildContext context) {
    final Color primary = _hex(data['primary_color'], GtexColors.pitch);
    final List<Map<String, dynamic>> trophies = opsMaps(data['trophies']);
    final int titles = trophies.where((Map<String, dynamic> t) => opsInt(t['position']) == 1).length;
    const List<Color> medals = <Color>[Color(0xFFF4C24D), Color(0xFFC0C7D1), Color(0xFFCD7F32)];
    final String place = <String>[opsStr(data['city'], ''), opsStr(data['country_code'], '')].where((String s) => s.isNotEmpty).join(' · ');
    final String crest = opsStr(data['crest_url'], '');
    final Widget shield = Icon(Icons.shield_rounded, color: primary, size: 92, shadows: <Shadow>[Shadow(color: primary.withValues(alpha: 0.7), blurRadius: 24)]);
    return Container(
      key: const Key('showroom-share-card'),
      width: showroomCardSide,
      height: showroomCardSide,
      padding: const EdgeInsets.all(32),
      decoration: BoxDecoration(
        gradient: RadialGradient(center: const Alignment(-0.6, -0.8), radius: 1.4, colors: <Color>[primary.withValues(alpha: 0.45), const Color(0xFF07090C)]),
        border: Border.all(color: primary, width: 6),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        const Text('GTEX CLUB SHOWROOM', style: TextStyle(color: GtexColors.gold, letterSpacing: 4, fontWeight: FontWeight.w900, fontSize: 14)),
        const SizedBox(height: 20),
        Row(children: <Widget>[
          crest.startsWith('http') ? Image.network(crest, width: 92, height: 92, fit: BoxFit.contain, errorBuilder: (_, __, ___) => shield) : shield,
          const SizedBox(width: 18),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              Text(opsStr(data['club_name']), key: const Key('showroom-card-name'), maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Colors.white, fontSize: 38, height: 1.05, fontWeight: FontWeight.w900)),
              if (place.isNotEmpty) Text(place, style: const TextStyle(color: Color(0xFFB8C0CC), fontSize: 18, fontWeight: FontWeight.w600)),
            ]),
          ),
        ]),
        const SizedBox(height: 26),
        Text(trophies.isEmpty ? 'BUILDING A LEGACY' : '$titles TITLE${titles == 1 ? '' : 'S'} · ${trophies.length} PODIUM FINISH${trophies.length == 1 ? '' : 'ES'}', style: TextStyle(color: primary, fontSize: 15, letterSpacing: 2, fontWeight: FontWeight.w900)),
        const SizedBox(height: 10),
        Expanded(
          child: trophies.isEmpty
              ? const Text('The cabinet is ready for the first trophy.', style: TextStyle(color: Color(0xFF8A94A3), fontSize: 18))
              : Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                  for (final Map<String, dynamic> t in trophies.take(4))
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Row(children: <Widget>[
                        Icon(opsInt(t['position']) == 1 ? Icons.emoji_events_rounded : Icons.military_tech_rounded, color: medals[(opsInt(t['position']) - 1).clamp(0, 2)], size: 32),
                        const SizedBox(width: 10),
                        Expanded(child: Text(opsStr(t['competition']), maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w700))),
                        Text('${opsInt(t['position']) == 1 ? 'Winners' : '#${t['position']}'} ${opsStr(t['year'], '')}', style: const TextStyle(color: Color(0xFFB8C0CC), fontSize: 16)),
                      ]),
                    ),
                  if (trophies.length > 4) Text('+${trophies.length - 4} more in the cabinet', style: const TextStyle(color: Color(0xFF8A94A3), fontSize: 15)),
                ]),
        ),
        Text(link, key: const Key('showroom-card-link'), maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: GtexColors.cyan, fontSize: 14, fontWeight: FontWeight.w700)),
      ]),
    );
  }
}

Future<Uint8List> captureShowroomCard(GlobalKey key) async {
  final RenderRepaintBoundary boundary = key.currentContext!.findRenderObject()! as RenderRepaintBoundary;
  final ui.Image image = await boundary.toImage(pixelRatio: 1080 / showroomCardSide);
  final ByteData? bytes = await image.toByteData(format: ui.ImageByteFormat.png);
  return bytes!.buffer.asUint8List();
}

String showroomCardFileName(Object? clubName) =>
    '${opsStr(clubName, 'club').toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), '-').replaceAll(RegExp(r'^-|-$'), '')}-showroom.png';

/// Previews the card and shares it (phone share sheet) or downloads it (desktop).
Future<void> showShowroomCard(BuildContext context, Map<String, dynamic> data, String link) => showDialog<void>(
  context: context,
  builder: (BuildContext context) => _ShowroomCardDialog(data: data, link: link),
);

class _ShowroomCardDialog extends StatefulWidget {
  const _ShowroomCardDialog({required this.data, required this.link});

  final Map<String, dynamic> data;
  final String link;

  @override
  State<_ShowroomCardDialog> createState() => _ShowroomCardDialogState();
}

class _ShowroomCardDialogState extends State<_ShowroomCardDialog> {
  final GlobalKey _boundary = GlobalKey();
  bool _busy = false;

  Future<void> _share() async {
    setState(() => _busy = true);
    final ScaffoldMessengerState? messenger = ScaffoldMessenger.maybeOf(context);
    try {
      final Uint8List png = await captureShowroomCard(_boundary);
      final String name = showroomCardFileName(widget.data['club_name']);
      await SharePlus.instance.share(ShareParams(files: <XFile>[XFile.fromData(png, mimeType: 'image/png', name: name)], fileNameOverrides: <String>[name], text: widget.link));
      messenger?.showSnackBar(const SnackBar(key: Key('showroom-card-done'), content: Text('Showroom card ready to post')));
    } catch (e) {
      messenger?.showSnackBar(SnackBar(key: const Key('showroom-card-error'), backgroundColor: GtexColors.red, content: Text('Could not share the card: ${opsError(e)}')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Dialog(
    key: const Key('showroom-card-dialog'),
    backgroundColor: GtexColors.surfaceBase,
    child: ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 420),
      child: Padding(
        padding: const EdgeInsets.all(GtexSpacing.md),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
          const Text('Share your trophy cabinet', style: TextStyle(color: GtexColors.text, fontSize: 18, fontWeight: FontWeight.w900)),
          const Text('Square 1080x1080 image for WhatsApp and Instagram', style: TextStyle(color: GtexColors.textSecondary, fontSize: 12)),
          const SizedBox(height: GtexSpacing.sm),
          AspectRatio(
            aspectRatio: 1,
            child: FittedBox(child: RepaintBoundary(key: _boundary, child: ShowroomShareCard(data: widget.data, link: widget.link))),
          ),
          const SizedBox(height: GtexSpacing.sm),
          Wrap(alignment: WrapAlignment.end, spacing: GtexSpacing.sm, children: <Widget>[
            GtexActionButton(key: const Key('showroom-card-close'), label: 'Close', compact: true, secondary: true, onPressed: () => Navigator.of(context).pop()),
            GtexActionButton(key: const Key('showroom-card-share'), label: _busy ? 'Preparing...' : 'Share / download', icon: Icons.ios_share_rounded, compact: true, onPressed: _busy ? null : _share),
          ]),
        ]),
      ),
    ),
  );
}
