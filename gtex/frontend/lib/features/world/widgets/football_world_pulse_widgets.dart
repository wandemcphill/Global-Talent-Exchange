import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../ui_gtex/theme/gtex_colors.dart';
import '../../../ui_gtex/theme/gtex_spacing.dart';
import '../football_world_pulse_provider.dart';

class FootballWorldPulseTicker extends ConsumerWidget {
  const FootballWorldPulseTicker({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<FootballWorldPulseData> value = ref.watch(
      footballWorldPulseProvider,
    );
    if (!value.hasValue) {
      return _TickerStatusBar(
        status: value.hasError ? 'ERROR' : 'LOADING',
        detail:
            value.hasError
                ? 'Live world pulse unavailable'
                : 'Syncing live world pulse',
      );
    }
    final FootballWorldPulseData pulse = value.requireValue;
    final List<FootballPulseItem> items = <FootballPulseItem>[
      ...pulse.transferTicker.take(4),
      ...pulse.competitionCountdowns.take(2),
      ...pulse.globalActivity.take(2),
    ];
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool compact = constraints.maxWidth < 560;
        return Container(
          key: const Key('football-world-pulse-ticker'),
          height: 44,
          padding: EdgeInsets.symmetric(
            horizontal: compact ? GtexSpacing.md : GtexSpacing.lg,
          ),
          decoration: BoxDecoration(
            color: GtexColors.stadiumBlack.withValues(alpha: 0.52),
            border: Border(
              bottom: BorderSide(
                color: GtexColors.line.withValues(alpha: 0.36),
              ),
            ),
          ),
          child: Row(
            children: <Widget>[
              const _LiveDot(),
              const SizedBox(width: GtexSpacing.sm),
              if (!compact) ...<Widget>[
                Text(
                  'WORLD PULSE',
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: GtexColors.pitch,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0,
                  ),
                ),
                const SizedBox(width: GtexSpacing.md),
              ],
              Expanded(child: ClipRect(child: _TickerItemRail(items: items))),
              if (!compact) ...<Widget>[
                const SizedBox(width: GtexSpacing.sm),
                _HeatBadge(label: 'heat', value: pulse.marketHeat),
                const SizedBox(width: GtexSpacing.xs),
                _HeatBadge(label: 'density', value: pulse.userDensity),
              ],
            ],
          ),
        );
      },
    );
  }
}

class FootballWorldPulseRail extends ConsumerWidget {
  const FootballWorldPulseRail({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<FootballWorldPulseData> value = ref.watch(
      footballWorldPulseProvider,
    );
    if (!value.hasValue) {
      return _PulseRailBlocked(
        title:
            value.hasError
                ? 'Live World Pulse Unavailable'
                : 'Loading World Pulse',
        detail:
            value.hasError
                ? 'The shell could not load live market, competition, and community activity.'
                : 'Waiting for live backend authority.',
      );
    }
    final FootballWorldPulseData pulse = value.requireValue;
    return Container(
      key: const Key('football-world-pulse-rail'),
      width: 318,
      decoration: BoxDecoration(
        color: GtexColors.stadiumBlack.withValues(alpha: 0.50),
        border: Border(
          left: BorderSide(color: GtexColors.line.withValues(alpha: 0.34)),
        ),
      ),
      child: SafeArea(
        left: false,
        top: false,
        bottom: false,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            GtexSpacing.md,
            GtexSpacing.md,
            GtexSpacing.md,
            GtexSpacing.lg,
          ),
          children: <Widget>[
            _RailHeader(pulse: pulse),
            const SizedBox(height: GtexSpacing.sm),
            _RouteOverlay(routes: pulse.transferRoutes),
            const SizedBox(height: GtexSpacing.md),
            _PulseSection(
              title: 'Transfer ticker',
              icon: Icons.swap_horiz_rounded,
              items: pulse.transferTicker,
            ),
            _PulseSection(
              title: 'Live negotiations',
              icon: Icons.handshake_outlined,
              items: pulse.negotiations,
            ),
            _PulseSection(
              title: 'Competition countdown',
              icon: Icons.timer_outlined,
              items: pulse.competitionCountdowns,
            ),
            _PulseSection(
              title: 'Market movers',
              icon: Icons.trending_up_rounded,
              items: pulse.marketMovers,
            ),
            _PulseSection(
              title: 'Discussion rooms',
              icon: Icons.forum_outlined,
              items: pulse.discussionPreviews,
            ),
            _PulseSection(
              title: 'Rivalry activity',
              icon: Icons.local_fire_department_outlined,
              items: pulse.rivalryCards,
            ),
            _PulseSection(
              title: 'Ranking movement',
              icon: Icons.leaderboard_outlined,
              items: pulse.rankingMovements,
            ),
            _PulseSection(
              title: 'Online clubs',
              icon: Icons.sensors_rounded,
              items: pulse.onlineClubs,
            ),
          ],
        ),
      ),
    );
  }
}

class _TickerItemRail extends StatelessWidget {
  const _TickerItemRail({required this.items});

  final List<FootballPulseItem> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return Text(
        'No live pulse events returned',
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
          color: GtexColors.textSecondary,
          fontWeight: FontWeight.w800,
          letterSpacing: 0,
        ),
      );
    }
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      physics: const BouncingScrollPhysics(),
      child: Row(
        children: items
            .map(
              (FootballPulseItem item) => Padding(
                padding: const EdgeInsets.only(right: GtexSpacing.md),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    Container(
                      width: 6,
                      height: 6,
                      decoration: BoxDecoration(
                        color: _heatColor(item.intensity),
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: GtexSpacing.xs),
                    Text(
                      item.label,
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: GtexColors.text,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0,
                      ),
                    ),
                    const SizedBox(width: GtexSpacing.xs),
                    Text(
                      item.metric,
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: GtexColors.textSecondary,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0,
                      ),
                    ),
                  ],
                ),
              ),
            )
            .toList(growable: false),
      ),
    );
  }
}

class _RailHeader extends StatelessWidget {
  const _RailHeader({required this.pulse});

  final FootballWorldPulseData pulse;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(GtexSpacing.md),
      decoration: BoxDecoration(
        color: GtexColors.panel.withValues(alpha: 0.72),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: GtexColors.line.withValues(alpha: 0.42)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              const Icon(
                Icons.public_rounded,
                color: GtexColors.pitch,
                size: 18,
              ),
              const SizedBox(width: GtexSpacing.xs),
              Expanded(
                child: Text(
                  'Football world layer',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: GtexSpacing.sm),
          Row(
            children: <Widget>[
              Expanded(
                child: _RailMeter(
                  label: 'Market heat',
                  value: pulse.marketHeat,
                ),
              ),
              const SizedBox(width: GtexSpacing.sm),
              Expanded(
                child: _RailMeter(
                  label: 'Club density',
                  value: pulse.userDensity,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _RouteOverlay extends StatefulWidget {
  const _RouteOverlay({required this.routes});

  final List<FootballPulseRoute> routes;

  @override
  State<_RouteOverlay> createState() => _RouteOverlayState();
}

class _RouteOverlayState extends State<_RouteOverlay>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  bool _isAnimating = false;

  bool get _isTestBinding =>
      WidgetsBinding.instance.runtimeType.toString().contains('Test');

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 12),
    )..value = 0.4;
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _syncMotion();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _syncMotion() {
    final bool shouldAnimate =
        !_isTestBinding &&
        TickerMode.of(context) &&
        !MediaQuery.of(context).disableAnimations;
    if (shouldAnimate == _isAnimating) {
      return;
    }
    _isAnimating = shouldAnimate;
    if (shouldAnimate) {
      _controller.repeat();
    } else {
      _controller.stop();
      _controller.value = 0.4;
    }
  }

  @override
  Widget build(BuildContext context) {
    final List<FootballPulseRoute> routes = widget.routes;
    return Container(
      height: 138,
      decoration: BoxDecoration(
        color: GtexColors.midnight.withValues(alpha: 0.62),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: GtexColors.line.withValues(alpha: 0.34)),
      ),
      child: AnimatedBuilder(
        animation: _controller,
        builder: (BuildContext context, Widget? child) {
          return CustomPaint(
            key: const Key('football-world-transfer-route-overlay'),
            painter: _RouteOverlayPainter(
              routes: routes,
              progress: _controller.value,
            ),
            child: child,
          );
        },
        child: Padding(
          padding: const EdgeInsets.all(GtexSpacing.md),
          child: Align(
            alignment: Alignment.bottomLeft,
            child: Text(
              routes.isEmpty
                  ? 'No live transfer routes returned'
                  : 'Animated transfer routes',
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: GtexColors.textSecondary,
                fontWeight: FontWeight.w800,
                letterSpacing: 0,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _TickerStatusBar extends StatelessWidget {
  const _TickerStatusBar({required this.status, required this.detail});

  final String status;
  final String detail;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const Key('football-world-pulse-ticker'),
      height: 44,
      padding: const EdgeInsets.symmetric(horizontal: GtexSpacing.lg),
      decoration: BoxDecoration(
        color: GtexColors.stadiumBlack.withValues(alpha: 0.52),
        border: Border(
          bottom: BorderSide(color: GtexColors.line.withValues(alpha: 0.36)),
        ),
      ),
      child: Row(
        children: <Widget>[
          Icon(
            status == 'ERROR' ? Icons.error_outline : Icons.sync_rounded,
            color: status == 'ERROR' ? GtexColors.gold : GtexColors.pitch,
            size: 16,
          ),
          const SizedBox(width: GtexSpacing.sm),
          Text(
            status,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: GtexColors.text,
              fontWeight: FontWeight.w900,
              letterSpacing: 0,
            ),
          ),
          const SizedBox(width: GtexSpacing.sm),
          Expanded(
            child: Text(
              detail,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: GtexColors.textSecondary,
                fontWeight: FontWeight.w800,
                letterSpacing: 0,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PulseRailBlocked extends StatelessWidget {
  const _PulseRailBlocked({required this.title, required this.detail});

  final String title;
  final String detail;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const Key('football-world-pulse-rail'),
      width: 318,
      padding: const EdgeInsets.all(GtexSpacing.md),
      decoration: BoxDecoration(
        color: GtexColors.stadiumBlack.withValues(alpha: 0.50),
        border: Border(
          left: BorderSide(color: GtexColors.line.withValues(alpha: 0.34)),
        ),
      ),
      child: SafeArea(
        left: false,
        top: false,
        bottom: false,
        child: Align(
          alignment: Alignment.topCenter,
          child: Container(
            padding: const EdgeInsets.all(GtexSpacing.md),
            decoration: BoxDecoration(
              color: GtexColors.panel.withValues(alpha: 0.72),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: GtexColors.line.withValues(alpha: 0.42),
              ),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0,
                  ),
                ),
                const SizedBox(height: GtexSpacing.xs),
                Text(
                  detail,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: GtexColors.textSecondary,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _RouteOverlayPainter extends CustomPainter {
  const _RouteOverlayPainter({required this.routes, required this.progress});

  final List<FootballPulseRoute> routes;
  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    final Paint pitchLine =
        Paint()
          ..color = GtexColors.line.withValues(alpha: 0.42)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1;
    final RRect pitch = RRect.fromRectAndRadius(
      Offset.zero & size,
      const Radius.circular(8),
    );
    canvas.drawRRect(pitch.deflate(14), pitchLine);
    canvas.drawLine(
      Offset(size.width / 2, 14),
      Offset(size.width / 2, size.height - 14),
      pitchLine,
    );

    final Paint routePaint =
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round
          ..strokeWidth = 2.2;
    final Paint pointPaint = Paint()..style = PaintingStyle.fill;

    for (int index = 0; index < math.min(routes.length, 5); index += 1) {
      final FootballPulseRoute route = routes[index];
      final double lane = (index + 1) / (math.min(routes.length, 5) + 1);
      final Offset start = Offset(22, size.height * lane);
      final Offset end = Offset(
        size.width - 22,
        size.height * (1 - lane * 0.72),
      );
      final Offset control = Offset(
        size.width * (0.36 + index * 0.04),
        size.height * (0.18 + (index % 3) * 0.24),
      );
      final Path path =
          Path()
            ..moveTo(start.dx, start.dy)
            ..quadraticBezierTo(control.dx, control.dy, end.dx, end.dy);
      routePaint.color = _heatColor(route.intensity).withValues(alpha: 0.58);
      canvas.drawPath(path, routePaint);

      final double dotT = (progress + index * 0.17) % 1;
      final Offset dot = _quadraticPoint(start, control, end, dotT);
      pointPaint.color = _heatColor(route.intensity).withValues(alpha: 0.92);
      canvas.drawCircle(dot, 3.2 + route.intensity * 2, pointPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _RouteOverlayPainter oldDelegate) {
    return oldDelegate.progress != progress || oldDelegate.routes != routes;
  }
}

Offset _quadraticPoint(Offset start, Offset control, Offset end, double t) {
  final double x =
      math.pow(1 - t, 2) * start.dx +
      2 * (1 - t) * t * control.dx +
      math.pow(t, 2) * end.dx;
  final double y =
      math.pow(1 - t, 2) * start.dy +
      2 * (1 - t) * t * control.dy +
      math.pow(t, 2) * end.dy;
  return Offset(x, y);
}

class _PulseSection extends StatelessWidget {
  const _PulseSection({
    required this.title,
    required this.icon,
    required this.items,
  });

  final String title;
  final IconData icon;
  final List<FootballPulseItem> items;

  @override
  Widget build(BuildContext context) {
    final List<FootballPulseItem> visible = items
        .take(4)
        .toList(growable: false);
    if (visible.isEmpty) {
      return const SizedBox.shrink();
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: GtexSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(icon, size: 15, color: GtexColors.textSecondary),
              const SizedBox(width: GtexSpacing.xs),
              Text(
                title,
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: GtexColors.text,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 0,
                ),
              ),
            ],
          ),
          const SizedBox(height: GtexSpacing.xs),
          ...visible.map((FootballPulseItem item) => _PulseRow(item: item)),
        ],
      ),
    );
  }
}

class _PulseRow extends StatelessWidget {
  const _PulseRow({required this.item});

  final FootballPulseItem item;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: GtexSpacing.xs),
      padding: const EdgeInsets.all(GtexSpacing.sm),
      decoration: BoxDecoration(
        color: GtexColors.panel.withValues(alpha: 0.56),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: GtexColors.line.withValues(alpha: 0.26)),
      ),
      child: Row(
        children: <Widget>[
          Container(
            width: 4,
            height: 32,
            decoration: BoxDecoration(
              color: _heatColor(item.intensity),
              borderRadius: BorderRadius.circular(4),
            ),
          ),
          const SizedBox(width: GtexSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  item.label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  item.detail,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: GtexColors.textMuted,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: GtexSpacing.xs),
          Text(
            item.metric,
            textAlign: TextAlign.right,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: _heatColor(item.intensity),
              fontWeight: FontWeight.w900,
              letterSpacing: 0,
            ),
          ),
        ],
      ),
    );
  }
}

class _RailMeter extends StatelessWidget {
  const _RailMeter({required this.label, required this.value});

  final String label;
  final double value;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          label,
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
            color: GtexColors.textMuted,
            fontWeight: FontWeight.w800,
            letterSpacing: 0,
          ),
        ),
        const SizedBox(height: GtexSpacing.xs),
        ClipRRect(
          borderRadius: BorderRadius.circular(999),
          child: LinearProgressIndicator(
            minHeight: 6,
            value: value.clamp(0.0, 1.0),
            backgroundColor: GtexColors.line.withValues(alpha: 0.32),
            color: _heatColor(value),
          ),
        ),
      ],
    );
  }
}

class _HeatBadge extends StatelessWidget {
  const _HeatBadge({required this.label, required this.value});

  final String label;
  final double value;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minWidth: 66),
      padding: const EdgeInsets.symmetric(
        horizontal: GtexSpacing.xs,
        vertical: 5,
      ),
      decoration: BoxDecoration(
        color: _heatColor(value).withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: _heatColor(value).withValues(alpha: 0.36)),
      ),
      child: Text(
        '${(value * 100).round()} $label',
        textAlign: TextAlign.center,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
          color: GtexColors.text,
          fontWeight: FontWeight.w900,
          letterSpacing: 0,
        ),
      ),
    );
  }
}

class _LiveDot extends StatelessWidget {
  const _LiveDot();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 10,
      height: 10,
      decoration: BoxDecoration(
        color: GtexColors.pitch,
        shape: BoxShape.circle,
        boxShadow: <BoxShadow>[
          GtexColors.glow(GtexColors.pitch, opacity: 0.22),
        ],
      ),
    );
  }
}

Color _heatColor(double value) {
  final double normalized = value.clamp(0.0, 1.0);
  if (normalized > 0.72) {
    return GtexColors.gold;
  }
  if (normalized > 0.44) {
    return GtexColors.pitch;
  }
  return GtexColors.cyan;
}
