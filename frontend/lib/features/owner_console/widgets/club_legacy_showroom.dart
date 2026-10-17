import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../data/owner_console_api.dart';

/// Lightweight club showroom. Match 3D stays on the match scene.
/// Reduced motion uses the static card instead of the turntable.
class ClubLegacyShowroom extends StatefulWidget {
  const ClubLegacyShowroom({super.key, required this.exhibits, this.forceStatic = false});

  final List<ShowroomExhibit> exhibits;
  final bool forceStatic;

  @override
  State<ClubLegacyShowroom> createState() => _ClubLegacyShowroomState();
}

class _ClubLegacyShowroomState extends State<ClubLegacyShowroom> {
  int _index = 0;
  double _yaw = 0;
  final TransformationController _transform = TransformationController();

  @override
  void dispose() {
    _transform.dispose();
    super.dispose();
  }

  ShowroomExhibit? get _current => widget.exhibits.isEmpty ? null : widget.exhibits[_index.clamp(0, widget.exhibits.length - 1)];

  void _reset() {
    setState(() => _yaw = 0);
    _transform.value = Matrix4.identity();
  }

  void _turn(double delta) => setState(() => _yaw += delta);

  Future<void> _openFullscreen(ShowroomExhibit exhibit, bool reduceMotion) {
    return showDialog<void>(
      context: context,
      builder: (BuildContext context) => _ShowroomFullscreen(exhibit: exhibit, reduceMotion: reduceMotion),
    );
  }

  @override
  Widget build(BuildContext context) {
    final bool reduceMotion = widget.forceStatic || MediaQuery.disableAnimationsOf(context);
    final ShowroomExhibit? exhibit = _current;
    if (exhibit == null) {
      return const GtexEmptyState(
        key: Key('club-showroom-empty'),
        title: 'Showroom is empty',
        message: 'Claim a club to preview its collection.',
        icon: Icons.museum_outlined,
      );
    }
    return Column(
      key: const Key('club-showroom'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        _stage(exhibit, reduceMotion),
        const SizedBox(height: GtexSpacing.sm),
        Wrap(
          spacing: GtexSpacing.xs,
          runSpacing: GtexSpacing.xs,
          children: <Widget>[
            for (int i = 0; i < widget.exhibits.length; i++)
              ChoiceChip(
                key: Key('club-showroom-pick-${widget.exhibits[i].id}'),
                label: Text(widget.exhibits[i].name),
                selected: i == _index,
                onSelected: (_) => setState(() {
                  _index = i;
                  _reset();
                }),
              ),
          ],
        ),
      ],
    );
  }

  Widget _stage(ShowroomExhibit exhibit, bool reduceMotion) {
    final Widget card = reduceMotion ? _staticCard(exhibit) : _turntable(exhibit);
    return GtexPanel(
      key: Key(reduceMotion ? 'club-showroom-static' : 'club-showroom-stage'),
      title: exhibit.name,
      subtitle: exhibit.ownershipLabel,
      accent: exhibit.owned ? GtexColors.pitch : GtexColors.gold,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          SizedBox(height: 220, child: card),
          const SizedBox(height: GtexSpacing.sm),
          Text(
            exhibit.ownershipLabel,
            key: const Key('club-showroom-ownership'),
            style: const TextStyle(color: GtexColors.text, fontWeight: FontWeight.w900),
          ),
          Text(exhibit.fallbackLabel, style: const TextStyle(color: GtexColors.textSecondary, fontSize: 12)),
          if (!reduceMotion) ...<Widget>[
            const SizedBox(height: GtexSpacing.sm),
            Wrap(
              spacing: GtexSpacing.xs,
              children: <Widget>[
                GtexActionButton(
                  key: const Key('club-showroom-rotate-left'),
                  label: 'Turn left',
                  icon: Icons.rotate_left_rounded,
                  compact: true,
                  secondary: true,
                  onPressed: () => _turn(-0.4),
                ),
                GtexActionButton(
                  key: const Key('club-showroom-rotate-right'),
                  label: 'Turn right',
                  icon: Icons.rotate_right_rounded,
                  compact: true,
                  secondary: true,
                  onPressed: () => _turn(0.4),
                ),
                GtexActionButton(
                  key: const Key('club-showroom-reset'),
                  label: 'Reset',
                  icon: Icons.center_focus_strong_rounded,
                  compact: true,
                  secondary: true,
                  onPressed: _reset,
                ),
                GtexActionButton(
                  key: const Key('club-showroom-fullscreen'),
                  label: 'Full screen',
                  icon: Icons.fullscreen_rounded,
                  compact: true,
                  onPressed: () => _openFullscreen(exhibit, reduceMotion),
                ),
              ],
            ),
            Text('Turn ${_yaw.toStringAsFixed(1)}', key: const Key('club-showroom-yaw')),
          ],
        ],
      ),
    );
  }

  Widget _staticCard(ShowroomExhibit exhibit) {
    return DecoratedBox(
      key: const Key('club-showroom-static-card'),
      decoration: BoxDecoration(
        color: GtexColors.panelStrong,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: GtexColors.gold.withValues(alpha: 0.5)),
      ),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(_icon(exhibit.category), color: GtexColors.gold, size: 64),
            const SizedBox(height: 8),
            Text(exhibit.fallbackLabel, style: const TextStyle(color: GtexColors.text)),
          ],
        ),
      ),
    );
  }

  Widget _turntable(ShowroomExhibit exhibit) {
    return InteractiveViewer(
      key: const Key('club-showroom-zoom'),
      transformationController: _transform,
      minScale: 0.8,
      maxScale: 2.5,
      child: Center(
        child: Transform.rotate(
          angle: _yaw,
          child: CustomPaint(
            key: const Key('club-showroom-model'),
            size: const Size(180, 120),
            painter: _ExhibitPainter(exhibit.category),
          ),
        ),
      ),
    );
  }

  IconData _icon(String category) {
    return switch (category) {
      'jet' => Icons.flight_rounded,
      'coach' => Icons.directions_bus_rounded,
      _ => Icons.watch_rounded,
    };
  }
}

class _ShowroomFullscreen extends StatefulWidget {
  const _ShowroomFullscreen({required this.exhibit, required this.reduceMotion});

  final ShowroomExhibit exhibit;
  final bool reduceMotion;

  @override
  State<_ShowroomFullscreen> createState() => _ShowroomFullscreenState();
}

class _ShowroomFullscreenState extends State<_ShowroomFullscreen> {
  double _yaw = 0;
  final TransformationController _transform = TransformationController();

  @override
  void dispose() {
    _transform.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ShowroomExhibit exhibit = widget.exhibit;
    return Dialog(
      key: const Key('club-showroom-fullscreen-view'),
      backgroundColor: GtexColors.panelStrong,
      child: Padding(
        padding: const EdgeInsets.all(GtexSpacing.md),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Text(exhibit.name, style: const TextStyle(color: GtexColors.text, fontSize: 22, fontWeight: FontWeight.w900)),
            Text(exhibit.ownershipLabel, key: const Key('club-showroom-fullscreen-ownership'), style: const TextStyle(color: GtexColors.gold, fontWeight: FontWeight.w800)),
            const SizedBox(height: GtexSpacing.sm),
            SizedBox(
              height: 360,
              child: widget.reduceMotion
                  ? const SizedBox.shrink()
                  : InteractiveViewer(
                      transformationController: _transform,
                      minScale: 0.8,
                      maxScale: 2.5,
                      child: Center(child: Transform.rotate(angle: _yaw, child: CustomPaint(size: const Size(280, 180), painter: _ExhibitPainter(exhibit.category)))),
                    ),
            ),
            if (widget.reduceMotion) Text(exhibit.fallbackLabel, key: const Key('club-showroom-fullscreen-static')),
            const SizedBox(height: GtexSpacing.sm),
            Wrap(
              spacing: GtexSpacing.xs,
              children: <Widget>[
                if (!widget.reduceMotion)
                  GtexActionButton(
                    key: const Key('club-showroom-fullscreen-rotate'),
                    label: 'Turn',
                    icon: Icons.rotate_right_rounded,
                    compact: true,
                    secondary: true,
                    onPressed: () => setState(() => _yaw += 0.4),
                  ),
                GtexActionButton(
                  key: const Key('club-showroom-fullscreen-close'),
                  label: 'Close',
                  icon: Icons.close_rounded,
                  compact: true,
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
            if (!widget.reduceMotion) Text('Turn ${_yaw.toStringAsFixed(1)}', key: const Key('club-showroom-fullscreen-yaw')),
          ],
        ),
      ),
    );
  }
}

class ShowroomSection extends StatefulWidget {
  const ShowroomSection({super.key, required this.load});

  final Future<List<ShowroomExhibit>> Function() load;

  @override
  State<ShowroomSection> createState() => _ShowroomSectionState();
}

class _ShowroomSectionState extends State<ShowroomSection> {
  late Future<List<ShowroomExhibit>> _exhibits;

  @override
  void initState() {
    super.initState();
    _exhibits = widget.load();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<ShowroomExhibit>>(
      future: _exhibits,
      builder: (BuildContext context, AsyncSnapshot<List<ShowroomExhibit>> snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Padding(padding: EdgeInsets.all(GtexSpacing.md), child: GtexSkeleton.box(height: 220));
        }
        if (snap.hasError || snap.data == null) {
          return const ClubLegacyShowroom(
            forceStatic: true,
            exhibits: <ShowroomExhibit>[
              ShowroomExhibit(id: 'catalogue:gtex-jet-harbour', name: 'Harbour Jet', category: 'jet', ownershipLabel: 'Not owned', fallbackLabel: 'Static jet card'),
              ShowroomExhibit(id: 'catalogue:gtex-coach-lagoon', name: 'Lagoon Coach', category: 'coach', ownershipLabel: 'Not owned', fallbackLabel: 'Static coach card'),
              ShowroomExhibit(id: 'catalogue:gtex-watch-icon', name: 'Icon Watch', category: 'watch', ownershipLabel: 'Not owned', fallbackLabel: 'Static watch card'),
            ],
          );
        }
        return ClubLegacyShowroom(exhibits: snap.data!);
      },
    );
  }
}

class _ExhibitPainter extends CustomPainter {
  _ExhibitPainter(this.category);

  final String category;

  @override
  void paint(Canvas canvas, Size size) {
    final Paint paint = Paint()..color = const Color(0xFFD4A017);
    final Path path = Path();
    if (category == 'jet') {
      path
        ..moveTo(size.width * 0.5, 0)
        ..lineTo(size.width, size.height * 0.7)
        ..lineTo(size.width * 0.5, size.height * 0.5)
        ..lineTo(0, size.height * 0.7)
        ..close();
    } else if (category == 'coach') {
      path.addRRect(RRect.fromRectAndRadius(Rect.fromLTWH(0, size.height * 0.25, size.width, size.height * 0.5), const Radius.circular(12)));
    } else {
      path.addOval(Rect.fromCircle(center: Offset(size.width / 2, size.height / 2), radius: size.shortestSide * 0.35));
    }
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _ExhibitPainter oldDelegate) => oldDelegate.category != category;
}
