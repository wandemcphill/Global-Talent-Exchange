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
    this.onPurchaseSku,
    this.onOfferGift,
    this.busy = false,
    this.actionMessage,
  });

  final List<ShowroomExhibit> exhibits;
  final bool forceStatic;

  /// Catalogue exhibits use ids `catalogue:{sku}`. Wired to phase-4 purchases.
  final Future<void> Function(String sku)? onPurchaseSku;

  /// Owned exhibits use the asset id. Recipient is collected in a dialog.
  final Future<void> Function(String assetId, String recipientRef)? onOfferGift;

  final bool busy;
  final String? actionMessage;

  @override
  State<ClubLegacyShowroom> createState() => _ClubLegacyShowroomState();
}

class _ClubLegacyShowroomState extends State<ClubLegacyShowroom> {
  int _index = 0;
  double _yaw = 0;
  double _pitch = 0;
  double _zoom = 1;
  int _ticket = 0;
  ShowroomGlb? _model;
  Object? _loadError;

  @override
  void initState() {
    super.initState();
    _loadCurrent();
  }

  ShowroomExhibit? get _current =>
      widget.exhibits.isEmpty
          ? null
          : widget.exhibits[_index.clamp(0, widget.exhibits.length - 1)];

  void _reset() {
    setState(() {
      _yaw = 0;
      _pitch = 0;
      _zoom = 1;
    });
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

  String? _catalogueSku(ShowroomExhibit exhibit) {
    const String prefix = 'catalogue:';
    if (!exhibit.id.startsWith(prefix)) {
      return null;
    }
    final String sku = exhibit.id.substring(prefix.length).trim();
    return sku.isEmpty ? null : sku;
  }

  Future<void> _purchase(ShowroomExhibit exhibit) async {
    final String? sku = _catalogueSku(exhibit);
    final Future<void> Function(String sku)? buy = widget.onPurchaseSku;
    if (sku == null || buy == null || widget.busy) {
      return;
    }
    await buy(sku);
  }

  Future<void> _gift(ShowroomExhibit exhibit) async {
    final Future<void> Function(String assetId, String recipientRef)? gift =
        widget.onOfferGift;
    if (!exhibit.owned || gift == null || widget.busy) {
      return;
    }
    final TextEditingController recipient = TextEditingController();
    final String? recipientRef = await showDialog<String>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          key: const Key('club-showroom-gift-dialog'),
          title: const Text('Gift this asset'),
          content: TextField(
            key: const Key('club-showroom-gift-recipient'),
            controller: recipient,
            decoration: const InputDecoration(
              labelText: 'Recipient player or manager ref',
            ),
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancel'),
            ),
            TextButton(
              key: const Key('club-showroom-gift-confirm'),
              onPressed: () => Navigator.of(context).pop(recipient.text.trim()),
              child: const Text('Offer gift'),
            ),
          ],
        );
      },
    );
    recipient.dispose();
    if (recipientRef == null || recipientRef.isEmpty) {
      return;
    }
    await gift(exhibit.id, recipientRef);
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
    final String? sku = _catalogueSku(exhibit);
    return ListView(
      key: const Key('club-showroom'),
      padding: const EdgeInsets.all(GtexSpacing.sm),
      children: <Widget>[
        _stage(exhibit, reduceMotion),
        if (widget.actionMessage != null) ...<Widget>[
          const SizedBox(height: GtexSpacing.sm),
          Text(
            widget.actionMessage!,
            key: const Key('club-showroom-action-message'),
            style: const TextStyle(color: GtexColors.textSecondary),
          ),
        ],
        if (sku != null && widget.onPurchaseSku != null) ...<Widget>[
          const SizedBox(height: GtexSpacing.sm),
          GtexActionButton(
            key: Key('club-showroom-buy-$sku'),
            label: widget.busy ? 'Purchasing…' : 'Buy from catalogue',
            icon: Icons.shopping_bag_outlined,
            onPressed: widget.busy ? null : () => _purchase(exhibit),
          ),
        ],
        if (exhibit.owned && widget.onOfferGift != null) ...<Widget>[
          const SizedBox(height: GtexSpacing.sm),
          GtexActionButton(
            key: Key('club-showroom-gift-${exhibit.id}'),
            label: widget.busy ? 'Working…' : 'Offer gift',
            icon: Icons.card_giftcard,
            secondary: true,
            onPressed: widget.busy ? null : () => _gift(exhibit),
          ),
        ],
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
    final String preview = exhibitPreviewPath(
      category: exhibit.category,
      previewFile: exhibit.previewFile,
      modelFile: exhibit.modelFile,
    );
    return DecoratedBox(
      key: const Key('club-showroom-static-card'),
      decoration: BoxDecoration(
        color: GtexColors.panelStrong,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: GtexColors.gold.withValues(alpha: 0.5)),
      ),
      child: Image.asset(
        preview,
        key: const Key('club-showroom-preview'),
        fit: BoxFit.contain,
        errorBuilder: (
          BuildContext context,
          Object error,
          StackTrace? stackTrace,
        ) {
          return Center(
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
          );
        },
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
    return GestureDetector(
      key: const Key('club-showroom-zoom'),
      onScaleUpdate: (ScaleUpdateDetails details) {
        setState(() {
          _yaw += details.focalPointDelta.dx * 0.01;
          _pitch = (_pitch + details.focalPointDelta.dy * 0.01).clamp(
            -1.2,
            1.2,
          );
          if (details.pointerCount > 1) {
            _zoom = (_zoom * details.scale).clamp(0.8, 2.5);
          }
        });
      },
      child: Center(
        child: Transform.scale(
          scale: _zoom,
          child: CustomPaint(
            key: const Key('club-showroom-model-loaded'),
            size: const Size(220, 160),
            painter: _MeshPainter(model.parts, _yaw, _pitch),
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
  double _pitch = 0;
  ShowroomGlb? _model;
  Object? _loadError;

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
                  widget.reduceMotion || _loadError != null
                      ? Image.asset(
                        exhibitPreviewPath(
                          category: exhibit.category,
                          previewFile: exhibit.previewFile,
                          modelFile: exhibit.modelFile,
                        ),
                        key: const Key('club-showroom-fullscreen-preview'),
                        fit: BoxFit.contain,
                      )
                      : _model == null
                      ? const Center(child: CircularProgressIndicator())
                      : GestureDetector(
                        onScaleUpdate: (ScaleUpdateDetails details) {
                          setState(() {
                            _yaw += details.focalPointDelta.dx * 0.01;
                            _pitch = (_pitch +
                                    details.focalPointDelta.dy * 0.01)
                                .clamp(-1.2, 1.2);
                          });
                        },
                        child: Center(
                          child: CustomPaint(
                            key: const Key('club-showroom-fullscreen-model'),
                            size: const Size(280, 180),
                            painter: _MeshPainter(_model!.parts, _yaw, _pitch),
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
  const ShowroomSection({
    super.key,
    required this.load,
    this.onPurchaseSku,
    this.onOfferGift,
  });

  final Future<List<ShowroomExhibit>> Function() load;
  final Future<void> Function(String sku)? onPurchaseSku;
  final Future<void> Function(String assetId, String recipientRef)? onOfferGift;

  @override
  State<ShowroomSection> createState() => _ShowroomSectionState();
}

class _ShowroomSectionState extends State<ShowroomSection> {
  late Future<List<ShowroomExhibit>> _exhibits;
  bool _busy = false;
  String? _message;

  @override
  void initState() {
    super.initState();
    _exhibits = widget.load();
  }

  Future<void> _purchase(String sku) async {
    final Future<void> Function(String sku)? buy = widget.onPurchaseSku;
    if (buy == null || _busy) {
      return;
    }
    setState(() {
      _busy = true;
      _message = null;
    });
    try {
      await buy(sku);
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _message = 'Purchased $sku.';
        _exhibits = widget.load();
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _message = '$error';
      });
    }
  }

  Future<void> _gift(String assetId, String recipientRef) async {
    final Future<void> Function(String assetId, String recipientRef)? gift =
        widget.onOfferGift;
    if (gift == null || _busy) {
      return;
    }
    setState(() {
      _busy = true;
      _message = null;
    });
    try {
      await gift(assetId, recipientRef);
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _message = 'Gift offered to $recipientRef.';
        _exhibits = widget.load();
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _busy = false;
        _message = '$error';
      });
    }
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
          return ClubLegacyShowroom(
            forceStatic: true,
            busy: _busy,
            actionMessage: _message ?? 'Showroom unavailable. Catalogue is preview-only until the club legacy API responds.',
            onPurchaseSku: widget.onPurchaseSku == null ? null : _purchase,
            onOfferGift: widget.onOfferGift == null ? null : _gift,
            exhibits: const <ShowroomExhibit>[
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
        return ClubLegacyShowroom(
          exhibits: snap.data!,
          busy: _busy,
          actionMessage: _message,
          onPurchaseSku: widget.onPurchaseSku == null ? null : _purchase,
          onOfferGift: widget.onOfferGift == null ? null : _gift,
        );
      },
    );
  }
}

class _MeshPainter extends CustomPainter {
  _MeshPainter(this.parts, this.yaw, this.pitch);

  final List<ShowroomMeshPart> parts;
  final double yaw;
  final double pitch;

  @override
  void paint(Canvas canvas, Size size) {
    if (parts.isEmpty) {
      return;
    }
    double minX = double.infinity;
    double minY = double.infinity;
    double minZ = double.infinity;
    double maxX = -double.infinity;
    double maxY = -double.infinity;
    double maxZ = -double.infinity;
    for (final ShowroomMeshPart part in parts) {
      for (int i = 0; i < part.positions.length; i += 3) {
        final double x = part.positions[i];
        final double y = part.positions[i + 1];
        final double z = part.positions[i + 2];
        minX = math.min(minX, x);
        minY = math.min(minY, y);
        minZ = math.min(minZ, z);
        maxX = math.max(maxX, x);
        maxY = math.max(maxY, y);
        maxZ = math.max(maxZ, z);
      }
    }
    final double extent = math.max(
      maxX - minX,
      math.max(maxY - minY, maxZ - minZ),
    );
    final double unit = extent == 0 ? 1 : extent;
    final double pixel = math.min(size.width, size.height) * 0.92;
    final double midX = (minX + maxX) / 2;
    final double midY = (minY + maxY) / 2;
    final double midZ = (minZ + maxZ) / 2;
    final double cx = size.width / 2;
    final double cy = size.height / 2;
    final double cosY = math.cos(yaw);
    final double sinY = math.sin(yaw);
    final double cosP = math.cos(pitch);
    final double sinP = math.sin(pitch);

    (Offset, double) project(Float32List positions, int vertex) {
      final double x = (positions[vertex * 3] - midX) / unit;
      final double y = (positions[vertex * 3 + 1] - midY) / unit;
      final double z = (positions[vertex * 3 + 2] - midZ) / unit;
      final double xr = x * cosY + z * sinY;
      final double yr = y;
      final double zr = -x * sinY + z * cosY;
      final double yp = yr * cosP - zr * sinP;
      final double zp = yr * sinP + zr * cosP;
      final double perspective = 2.6 / (2.6 + zp);
      return (
        Offset(cx + xr * pixel * perspective, cy - yp * pixel * perspective),
        zp,
      );
    }

    final List<({Path path, double depth, Color color})> drawn =
        <({Path path, double depth, Color color})>[];
    for (final ShowroomMeshPart part in parts) {
      final int vertexCount = part.positions.length ~/ 3;
      for (int index = 0; index + 2 < part.indices.length; index += 3) {
        final int a = part.indices[index];
        final int b = part.indices[index + 1];
        final int c = part.indices[index + 2];
        if (a >= vertexCount || b >= vertexCount || c >= vertexCount) {
          continue;
        }
        final (Offset pa, double da) = project(part.positions, a);
        final (Offset pb, double db) = project(part.positions, b);
        final (Offset pc, double dc) = project(part.positions, c);
        drawn.add((
          path:
              Path()
                ..moveTo(pa.dx, pa.dy)
                ..lineTo(pb.dx, pb.dy)
                ..lineTo(pc.dx, pc.dy)
                ..close(),
          depth: (da + db + dc) / 3,
          color: part.color,
        ));
      }
    }
    drawn.sort(
      (
        ({Path path, double depth, Color color}) left,
        ({Path path, double depth, Color color}) right,
      ) => right.depth.compareTo(left.depth),
    );
    final Paint fill = Paint();
    final double far = drawn.isEmpty ? 0 : drawn.first.depth;
    final double near = drawn.isEmpty ? 1 : drawn.last.depth;
    final double span = (near - far).abs() < 0.001 ? 1 : (near - far).abs();
    for (final ({Path path, double depth, Color color}) triangle in drawn) {
      final double shade = (0.45 + 0.55 * ((triangle.depth - far) / span))
          .clamp(0.35, 1.0);
      fill.color = Color.lerp(const Color(0xFF1A1408), triangle.color, shade)!;
      canvas.drawPath(triangle.path, fill);
    }
  }

  @override
  bool shouldRepaint(covariant _MeshPainter oldDelegate) =>
      oldDelegate.yaw != yaw ||
      oldDelegate.pitch != pitch ||
      oldDelegate.parts != parts;
}
