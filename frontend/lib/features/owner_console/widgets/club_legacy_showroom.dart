import 'dart:math' as math;
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../data/owner_console_api.dart';
import '../data/showroom_glb.dart';

/// Lightweight club showroom. Match 3D stays on the match scene.
/// Reduced motion uses the static card instead of the turntable.
class ClubLegacyShowroom extends StatefulWidget {
  const ClubLegacyShowroom({
    super.key,
    required this.exhibits,
    this.forceStatic = false,
  });

  final List<ShowroomExhibit> exhibits;
  final bool forceStatic;

  @override
  State<ClubLegacyShowroom> createState() => _ClubLegacyShowroomState();
}

class _ClubLegacyShowroomState extends State<ClubLegacyShowroom> {
  int _index = 0;
  double _yaw = 0;
  int _ticket = 0;
  ShowroomGlb? _model;
  Object? _loadError;
  final TransformationController _transform = TransformationController();

  @override
  void initState() {
    super.initState();
    _loadCurrent();
  }

  @override
  void dispose() {
    _transform.dispose();
    super.dispose();
  }

  ShowroomExhibit? get _current =>
      widget.exhibits.isEmpty
          ? null
          : widget.exhibits[_index.clamp(0, widget.exhibits.length - 1)];

  void _reset() {
    setState(() => _yaw = 0);
    _transform.value = Matrix4.identity();
  }

  void _turn(double delta) => setState(() => _yaw += delta);

  Future<void> _loadCurrent() async {
    final ShowroomExhibit? exhibit = _current;
    if (exhibit == null) {
      return;
    }
    final int ticket = ++_ticket;
    final String path = exhibitModelPath(
      category: exhibit.category,
      modelFile: exhibit.modelFile,
    );
    try {
      final ShowroomGlb model = await loadShowroomGlb(path);
      if (!mounted || ticket != _ticket) {
        return;
      }
      setState(() {
        _model = model;
        _loadError = null;
      });
    } catch (error) {
      if (!mounted || ticket != _ticket) {
        return;
      }
      setState(() => _loadError = error);
    }
  }

  Future<void> _openFullscreen(ShowroomExhibit exhibit, bool reduceMotion) {
    return showDialog<void>(
      context: context,
      builder:
          (BuildContext context) =>
              _ShowroomFullscreen(exhibit: exhibit, reduceMotion: reduceMotion),
    );
  }

  @override
  Widget build(BuildContext context) {
    final bool reduceMotion =
        widget.forceStatic || MediaQuery.disableAnimationsOf(context);
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
                onSelected: (_) {
                  setState(() => _index = i);
                  _reset();
                  _loadCurrent();
                },
              ),
          ],
        ),
      ],
    );
  }

  Widget _stage(ShowroomExhibit exhibit, bool reduceMotion) {
    final Widget card =
        reduceMotion ? _staticCard(exhibit) : _turntable(exhibit);
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
            style: const TextStyle(
              color: GtexColors.text,
              fontWeight: FontWeight.w900,
            ),
          ),
          Text(
            _statusLine(exhibit),
            key: const Key('club-showroom-model-file'),
            style: const TextStyle(
              color: GtexColors.textSecondary,
              fontSize: 12,
            ),
          ),
          Text(
            exhibit.fallbackLabel,
            style: const TextStyle(
              color: GtexColors.textSecondary,
              fontSize: 12,
            ),
          ),
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
            Text(
              'Turn ${_yaw.toStringAsFixed(1)}',
              key: const Key('club-showroom-yaw'),
            ),
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
            Text(
              exhibit.fallbackLabel,
              style: const TextStyle(color: GtexColors.text),
            ),
          ],
        ),
      ),
    );
  }

  String _statusLine(ShowroomExhibit exhibit) {
    final String path = exhibitModelPath(
      category: exhibit.category,
      modelFile: exhibit.modelFile,
    );
    if (_loadError != null) {
      return 'Could not read $path';
    }
    if (_model == null || _model!.assetPath != path) {
      return 'Loading $path';
    }
    return _model!.loadedLabel;
  }

  Widget _turntable(ShowroomExhibit exhibit) {
    final String path = exhibitModelPath(
      category: exhibit.category,
      modelFile: exhibit.modelFile,
    );
    final ShowroomGlb? model = _model;
    if (_loadError != null) {
      return _staticCard(exhibit);
    }
    if (model == null || model.assetPath != path) {
      return const Center(
        child: CircularProgressIndicator(key: Key('club-showroom-loading')),
      );
    }
    return InteractiveViewer(
      key: const Key('club-showroom-zoom'),
      transformationController: _transform,
      minScale: 0.8,
      maxScale: 2.5,
      child: Center(
        child: CustomPaint(
          key: const Key('club-showroom-model-loaded'),
          size: const Size(220, 160),
          painter: _MeshPainter(
            model.displayPositions,
            model.displayIndices,
            _yaw,
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
  const _ShowroomFullscreen({
    required this.exhibit,
    required this.reduceMotion,
  });

  final ShowroomExhibit exhibit;
  final bool reduceMotion;

  @override
  State<_ShowroomFullscreen> createState() => _ShowroomFullscreenState();
}

class _ShowroomFullscreenState extends State<_ShowroomFullscreen> {
  double _yaw = 0;
  ShowroomGlb? _model;
  Object? _loadError;
  final TransformationController _transform = TransformationController();

  @override
  void initState() {
    super.initState();
    loadShowroomGlb(
      exhibitModelPath(
        category: widget.exhibit.category,
        modelFile: widget.exhibit.modelFile,
      ),
    ).then(
      (ShowroomGlb model) {
        if (mounted) {
          setState(() => _model = model);
        }
      },
      onError: (Object error) {
        if (mounted) {
          setState(() => _loadError = error);
        }
      },
    );
  }

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
            Text(
              exhibit.name,
              style: const TextStyle(
                color: GtexColors.text,
                fontSize: 22,
                fontWeight: FontWeight.w900,
              ),
            ),
            Text(
              exhibit.ownershipLabel,
              key: const Key('club-showroom-fullscreen-ownership'),
              style: const TextStyle(
                color: GtexColors.gold,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: GtexSpacing.sm),
            SizedBox(
              height: 360,
              child:
                  widget.reduceMotion
                      ? const SizedBox.shrink()
                      : _loadError != null
                      ? Text(
                        widget.exhibit.fallbackLabel,
                        key: const Key('club-showroom-fullscreen-static'),
                      )
                      : _model == null
                      ? const Center(child: CircularProgressIndicator())
                      : InteractiveViewer(
                        transformationController: _transform,
                        minScale: 0.8,
                        maxScale: 2.5,
                        child: Center(
                          child: CustomPaint(
                            key: const Key('club-showroom-fullscreen-model'),
                            size: const Size(280, 180),
                            painter: _MeshPainter(
                              _model!.displayPositions,
                              _model!.displayIndices,
                              _yaw,
                            ),
                          ),
                        ),
                      ),
            ),
            if (widget.reduceMotion)
              Text(
                exhibit.fallbackLabel,
                key: const Key('club-showroom-fullscreen-static'),
              ),
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
            if (!widget.reduceMotion)
              Text(
                'Turn ${_yaw.toStringAsFixed(1)}',
                key: const Key('club-showroom-fullscreen-yaw'),
              ),
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
      builder: (
        BuildContext context,
        AsyncSnapshot<List<ShowroomExhibit>> snap,
      ) {
        if (snap.connectionState != ConnectionState.done) {
          return const Padding(
            padding: EdgeInsets.all(GtexSpacing.md),
            child: GtexSkeleton.box(height: 220),
          );
        }
        if (snap.hasError || snap.data == null) {
          return const ClubLegacyShowroom(
            forceStatic: true,
            exhibits: <ShowroomExhibit>[
              ShowroomExhibit(
                id: 'catalogue:gtex-jet-harbour',
                name: 'Harbour Jet',
                category: 'jet',
                ownershipLabel: 'Not owned',
                fallbackLabel: 'Static jet card',
              ),
              ShowroomExhibit(
                id: 'catalogue:gtex-coach-lagoon',
                name: 'Lagoon Coach',
                category: 'coach',
                ownershipLabel: 'Not owned',
                fallbackLabel: 'Static coach card',
              ),
              ShowroomExhibit(
                id: 'catalogue:gtex-watch-icon',
                name: 'Icon Watch',
                category: 'watch',
                ownershipLabel: 'Not owned',
                fallbackLabel: 'Static watch card',
              ),
            ],
          );
        }
        return ClubLegacyShowroom(exhibits: snap.data!);
      },
    );
  }
}

class _MeshPainter extends CustomPainter {
  _MeshPainter(this.positions, this.indices, this.yaw);

  final Float32List positions;
  final Uint32List indices;
  final double yaw;

  @override
  void paint(Canvas canvas, Size size) {
    if (positions.length < 3 || indices.length < 3) {
      return;
    }
    double minX = double.infinity;
    double minY = double.infinity;
    double minZ = double.infinity;
    double maxX = -double.infinity;
    double maxY = -double.infinity;
    double maxZ = -double.infinity;
    for (int i = 0; i < positions.length; i += 3) {
      final double x = positions[i];
      final double y = positions[i + 1];
      final double z = positions[i + 2];
      minX = math.min(minX, x);
      minY = math.min(minY, y);
      minZ = math.min(minZ, z);
      maxX = math.max(maxX, x);
      maxY = math.max(maxY, y);
      maxZ = math.max(maxZ, z);
    }
    final double extent = math.max(
      maxX - minX,
      math.max(maxY - minY, maxZ - minZ),
    );
    final double scale =
        extent == 0 ? 1 : math.min(size.width, size.height) * 0.86 / extent;
    final double midX = (minX + maxX) / 2;
    final double midY = (minY + maxY) / 2;
    final double midZ = (minZ + maxZ) / 2;
    final double cx = size.width / 2;
    final double cy = size.height / 2;
    final double cosY = math.cos(yaw);
    final double sinY = math.sin(yaw);
    final int vertexCount = positions.length ~/ 3;
    final int triangleCount = indices.length ~/ 3;

    (Offset, double) project(int vertex) {
      final double x = positions[vertex * 3] - midX;
      final double y = positions[vertex * 3 + 1] - midY;
      final double z = positions[vertex * 3 + 2] - midZ;
      final double xr = x * cosY + z * sinY;
      final double zr = -x * sinY + z * cosY;
      final double perspective = 3.2 / (3.2 + zr);
      return (
        Offset(cx + xr * scale * perspective, cy - y * scale * perspective),
        zr,
      );
    }

    final List<({Path path, double depth})> drawn =
        <({Path path, double depth})>[];
    for (int triangle = 0; triangle < triangleCount; triangle++) {
      final int index = triangle * 3;
      final int a = indices[index];
      final int b = indices[index + 1];
      final int c = indices[index + 2];
      if (a >= vertexCount || b >= vertexCount || c >= vertexCount) {
        continue;
      }
      final (Offset pa, double da) = project(a);
      final (Offset pb, double db) = project(b);
      final (Offset pc, double dc) = project(c);
      drawn.add((
        path:
            Path()
              ..moveTo(pa.dx, pa.dy)
              ..lineTo(pb.dx, pb.dy)
              ..lineTo(pc.dx, pc.dy)
              ..close(),
        depth: (da + db + dc) / 3,
      ));
    }
    drawn.sort(
      (({Path path, double depth}) left, ({Path path, double depth}) right) =>
          right.depth.compareTo(left.depth),
    );
    final Paint fill = Paint();
    final Paint line =
        Paint()
          ..color = const Color(0xFF1A1408)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 0.6;
    final double far = drawn.isEmpty ? 0 : drawn.first.depth;
    final double near = drawn.isEmpty ? 1 : drawn.last.depth;
    final double span = (near - far).abs() < 0.001 ? 1 : (near - far).abs();
    for (final ({Path path, double depth}) triangle in drawn) {
      final double shade = ((triangle.depth - far) / span).clamp(0.0, 1.0);
      fill.color =
          Color.lerp(const Color(0xFFE0B84A), const Color(0xFFFFF1C2), shade)!;
      canvas.drawPath(triangle.path, fill);
      canvas.drawPath(triangle.path, line);
    }
  }

  @override
  bool shouldRepaint(covariant _MeshPainter oldDelegate) =>
      oldDelegate.yaw != yaw || oldDelegate.positions != positions;
}
