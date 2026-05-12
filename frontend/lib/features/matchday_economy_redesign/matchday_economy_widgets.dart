import 'package:flutter/material.dart';

import '../../data/gte_api_repository.dart';
import '../../ui_gtex/ui_gtex.dart';
import '../../widgets/gte_state_panel.dart';
import 'matchday_economy_api.dart';
import 'matchday_economy_controller.dart';
import 'matchday_economy_models.dart';

class GtexMatchdayEconomyPanel extends StatefulWidget {
  const GtexMatchdayEconomyPanel({
    super.key,
    required this.baseUrl,
    required this.backendMode,
    this.accessToken,
    this.admin = false,
    this.controller,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final bool admin;
  final GtexMatchdayEconomyController? controller;

  @override
  State<GtexMatchdayEconomyPanel> createState() =>
      _GtexMatchdayEconomyPanelState();
}

class _GtexMatchdayEconomyPanelState extends State<GtexMatchdayEconomyPanel> {
  late GtexMatchdayEconomyController _controller;
  late bool _ownsController;

  @override
  void initState() {
    super.initState();
    _ownsController = widget.controller == null;
    _controller = widget.controller ?? _buildController();
    _controller.load(admin: widget.admin);
  }

  @override
  void didUpdateWidget(covariant GtexMatchdayEconomyPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.controller != widget.controller) {
      if (_ownsController) {
        _controller.dispose();
      }
      _ownsController = widget.controller == null;
      _controller = widget.controller ?? _buildController();
      _controller.load(admin: widget.admin);
      return;
    }
    if (_ownsController &&
        (oldWidget.baseUrl != widget.baseUrl ||
            oldWidget.backendMode != widget.backendMode ||
            oldWidget.accessToken != widget.accessToken ||
            oldWidget.admin != widget.admin)) {
      _controller.dispose();
      _controller = _buildController();
      _controller.load(admin: widget.admin);
    }
  }

  @override
  void dispose() {
    if (_ownsController) {
      _controller.dispose();
    }
    super.dispose();
  }

  GtexMatchdayEconomyController _buildController() {
    return GtexMatchdayEconomyController(
      api: GtexMatchdayEconomyApi.standard(
        baseUrl: widget.baseUrl,
        accessToken: widget.accessToken,
        mode: widget.backendMode,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (BuildContext context, Widget? child) {
        final GtexMatchdayEconomyOverview? overview = _controller.overview;
        if (_controller.isLoading && overview == null) {
          return const GteStatePanel(
            title: 'Loading matchday economy',
            message:
                'Syncing federation, fan, broadcast, ticketing, and card economy signals.',
            icon: Icons.query_stats_outlined,
            isLoading: true,
          );
        }
        if (_controller.errorMessage != null && overview == null) {
          return GteStatePanel(
            title: 'Matchday economy unavailable',
            message: _controller.errorMessage!,
            icon: Icons.sync_problem_outlined,
            actionLabel: 'Retry',
            onAction: _controller.load,
          );
        }
        if (overview == null || overview.sections.isEmpty) {
          return const GtexEmptyState(
            title: 'No matchday economy signals',
            message:
                'Launch control is currently hiding every matchday economy module from this session.',
            icon: Icons.visibility_off_outlined,
            accent: GtexColors.mint,
          );
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            GtexPanel(
              title: 'Matchday economy',
              subtitle:
                  '${overview.sections.length} modules synced for ${overview.audience}',
              accent: GtexColors.mint,
              trailing: IconButton(
                tooltip: 'Refresh matchday economy',
                onPressed: _controller.isLoading ? null : _controller.load,
                icon: const Icon(Icons.refresh_outlined),
              ),
              child: Wrap(
                spacing: GtexSpacing.sm,
                runSpacing: GtexSpacing.sm,
                children: overview.sections
                    .map(_sectionChip)
                    .toList(growable: false),
              ),
            ),
            const SizedBox(height: GtexSpacing.md),
            for (final GtexMatchdayEconomySection section in overview.sections)
              Padding(
                padding: const EdgeInsets.only(bottom: GtexSpacing.md),
                child: _MatchdayEconomySectionCard(section: section),
              ),
          ],
        );
      },
    );
  }

  Widget _sectionChip(GtexMatchdayEconomySection section) {
    return GtexStatusChip(
      label: '${section.title}: ${section.healthStatus.toUpperCase()}',
      color: _statusColor(section),
      icon:
          section.needsAttention
              ? Icons.warning_amber_outlined
              : Icons.check_circle_outline,
    );
  }
}

class _MatchdayEconomySectionCard extends StatelessWidget {
  const _MatchdayEconomySectionCard({required this.section});

  final GtexMatchdayEconomySection section;

  @override
  Widget build(BuildContext context) {
    final Color accent = _statusColor(section);
    return GtexPanel(
      title: section.title,
      subtitle: '${section.launchState} - ${section.route}',
      accent: accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            section.description,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: GtexColors.textSecondary,
              height: 1.35,
            ),
          ),
          if (section.alerts.isNotEmpty) ...<Widget>[
            const SizedBox(height: GtexSpacing.sm),
            for (final String alert in section.alerts.take(3))
              Padding(
                padding: const EdgeInsets.only(bottom: GtexSpacing.xs),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Icon(Icons.info_outline, size: 16, color: accent),
                    const SizedBox(width: GtexSpacing.xs),
                    Expanded(
                      child: Text(
                        alert,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: GtexColors.textSecondary,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
          ],
          const SizedBox(height: GtexSpacing.md),
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool compact = constraints.maxWidth < 560;
              final double tileWidth =
                  compact
                      ? constraints.maxWidth
                      : (constraints.maxWidth - 20) / 2;
              return Wrap(
                spacing: GtexSpacing.sm,
                runSpacing: GtexSpacing.sm,
                children: section.metrics
                    .take(6)
                    .map((GtexMatchdayEconomyMetric metric) {
                      return SizedBox(
                        width: tileWidth,
                        child: GtexMetricTile(
                          label: metric.label,
                          value: metric.displayValue,
                          helper: metric.unit ?? metric.status.toUpperCase(),
                          icon: _metricIcon(metric),
                          accent: _metricColor(metric, accent),
                        ),
                      );
                    })
                    .toList(growable: false),
              );
            },
          ),
        ],
      ),
    );
  }
}

Color _statusColor(GtexMatchdayEconomySection section) {
  switch (section.healthStatus) {
    case 'online':
      return GtexColors.mint;
    case 'gated':
      return GtexColors.cyan;
    case 'maintenance':
    case 'paused':
      return GtexColors.gold;
    case 'kill_switch':
    case 'hidden':
    case 'disabled':
      return GtexColors.red;
    default:
      return GtexColors.textSecondary;
  }
}

Color _metricColor(GtexMatchdayEconomyMetric metric, Color fallback) {
  switch (metric.status) {
    case 'live':
      return GtexColors.mint;
    case 'attention':
      return GtexColors.gold;
    case 'blocked':
      return GtexColors.red;
    default:
      return fallback;
  }
}

IconData _metricIcon(GtexMatchdayEconomyMetric metric) {
  switch (metric.key) {
    case 'gross_revenue':
    case 'gross_sales':
      return Icons.payments_outlined;
    case 'open_proposals':
    case 'proposals':
      return Icons.how_to_vote_outlined;
    case 'clip_variants':
      return Icons.movie_filter_outlined;
    case 'open_listings':
      return Icons.storefront_outlined;
    case 'stadium_events':
      return Icons.stadium_outlined;
    default:
      return Icons.query_stats_outlined;
  }
}
