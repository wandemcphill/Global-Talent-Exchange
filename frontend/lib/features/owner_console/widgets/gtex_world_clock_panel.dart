import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../models/gtex_world_clock_models.dart';

/// Optional capability so existing [OwnerConsoleReader] fakes stay valid.
abstract interface class OwnerWorldClockGateway {
  Future<WorldClock> fetchWorldClock();
}

/// Compact header pill displaying the live synchronized GTEX World Clock.
class GtexWorldClockHeaderPill extends StatefulWidget {
  const GtexWorldClockHeaderPill({
    super.key,
    this.clock,
    this.load,
    this.onTap,
  });

  final WorldClock? clock;
  final Future<WorldClock> Function()? load;
  final VoidCallback? onTap;

  @override
  State<GtexWorldClockHeaderPill> createState() => _GtexWorldClockHeaderPillState();
}

class _GtexWorldClockHeaderPillState extends State<GtexWorldClockHeaderPill> {
  WorldClock? _clock;

  @override
  void initState() {
    super.initState();
    _clock = widget.clock;
    if (_clock == null && widget.load != null) {
      widget.load!().then((WorldClock c) {
        if (mounted) setState(() => _clock = c);
      }).catchError((_) {});
    }
  }

  @override
  void didUpdateWidget(covariant GtexWorldClockHeaderPill oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.clock != null && widget.clock != _clock) {
      _clock = widget.clock;
    }
  }

  @override
  Widget build(BuildContext context) {
    final WorldClock? c = widget.clock ?? _clock;
    final String label = c != null
        ? '${c.currentSeasonLabel} · ${c.displayTime}'
        : 'GTEX World Clock';
    final bool isPaused = c?.isPaused ?? false;

    return Semantics(
      button: true,
      label: 'GTEX World Clock: $label',
      child: InkWell(
        key: const Key('gtex-world-clock-header-pill'),
        onTap: widget.onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
          decoration: BoxDecoration(
            color: GtexColors.panelStrong,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: isPaused
                  ? GtexColors.gold.withValues(alpha: 0.5)
                  : GtexColors.cyan.withValues(alpha: 0.5),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Container(
                width: 7,
                height: 7,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: isPaused ? GtexColors.gold : GtexColors.pitch,
                ),
              ),
              const SizedBox(width: 6),
              const Icon(Icons.public_rounded, size: 13, color: GtexColors.cyan),
              const SizedBox(width: 5),
              Text(
                label,
                style: const TextStyle(
                  color: GtexColors.text,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.3,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Shows the server's world clock. No timers: the value is a snapshot, refreshed on demand.
class GtexWorldClockPanel extends StatefulWidget {
  const GtexWorldClockPanel({super.key, required this.load});

  /// Null when the active reader cannot supply the clock.
  final Future<WorldClock> Function()? load;

  @override
  State<GtexWorldClockPanel> createState() => _GtexWorldClockPanelState();
}

class _GtexWorldClockPanelState extends State<GtexWorldClockPanel> {
  WorldClock? _clock;
  bool _loading = true;
  bool _failed = false;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  Future<void> _refresh() async {
    final Future<WorldClock> Function()? load = widget.load;
    if (load == null) {
      setState(() {
        _loading = false;
        _failed = true;
      });
      return;
    }
    setState(() {
      _loading = true;
      _failed = false;
    });
    try {
      final WorldClock c = await load();
      if (!mounted) return;
      setState(() {
        _clock = c;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _failed = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final WorldClock? c = _clock;
    final Widget body;
    if (c == null && _loading) {
      body = Semantics(
        liveRegion: true,
        label: 'Loading GTEX world time',
        child: const GtexSkeleton.box(key: Key('world-clock-loading'), height: 72),
      );
    } else if (c == null) {
      body = Column(
        key: const Key('world-clock-error'),
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Text(
            'GTEX world time is unavailable right now. No time is shown rather than a guess.',
            style: TextStyle(color: GtexColors.danger),
          ),
          TextButton(
            key: const Key('world-clock-retry'),
            onPressed: _refresh,
            child: const Text('Retry'),
          ),
        ],
      );
    } else {
      body = Semantics(
        liveRegion: true,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              c.displayDate,
              key: const Key('world-clock-date'),
              style: const TextStyle(color: GtexColors.text, fontSize: 24, fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 4),
            Text(
              c.displayTime,
              key: const Key('world-clock-time'),
              style: const TextStyle(color: GtexColors.cyan, fontSize: 16, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: GtexSpacing.sm),
            Wrap(
              spacing: GtexSpacing.xs,
              runSpacing: GtexSpacing.xs,
              children: <Widget>[
                GtexStatusChip(
                  key: const Key('world-clock-status'),
                  label: c.isPaused ? 'Paused' : 'Running',
                  color: c.isPaused ? GtexColors.gold : GtexColors.pitch,
                  icon: c.isPaused ? Icons.pause_circle_outline : Icons.play_circle_outline,
                ),
                GtexStatusChip(
                  key: const Key('world-clock-rate'),
                  label: 'Rate ${c.displayRate}',
                  color: GtexColors.cyan,
                ),
                GtexStatusChip(
                  key: const Key('world-clock-season-length'),
                  label: 'Season: ${c.virtualMonthsPerSeason} virtual months',
                  color: GtexColors.gold,
                ),
                GtexStatusChip(
                  key: const Key('world-clock-season-badge'),
                  label: c.currentSeasonLabel,
                  color: GtexColors.purple,
                  icon: Icons.calendar_today_rounded,
                ),
              ],
            ),
            const SizedBox(height: GtexSpacing.xs),
            const Text(
              'Current season not shown: awaiting the approved season calendar.',
              key: Key('world-clock-season-unavailable'),
              style: TextStyle(color: GtexColors.textMuted, fontSize: 12),
            ),
            if (_failed)
              const Padding(
                padding: EdgeInsets.only(top: GtexSpacing.xs),
                child: Text(
                  'Showing the last server snapshot; the latest refresh failed.',
                  key: Key('world-clock-stale'),
                  style: TextStyle(color: GtexColors.gold, fontSize: 12),
                ),
              ),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                key: const Key('world-clock-refresh'),
                onPressed: _loading ? null : _refresh,
                icon: const Icon(Icons.refresh_rounded, size: 16),
                label: const Text('Refresh from server'),
              ),
            ),
          ],
        ),
      );
    }
    return GtexPanel(
      key: const Key('owner-world-clock'),
      title: 'GTEX world time',
      subtitle: 'Authoritative server clock',
      accent: GtexColors.cyan,
      child: body,
    );
  }
}

/// Daily owner briefing. Cards come only from persisted, verified events.
class GtexOwnerBriefingPanel extends StatelessWidget {
  const GtexOwnerBriefingPanel({
    super.key,
    required this.state,
    required this.onNavigate,
    this.onRetry,
  });

  final BriefingViewState state;
  final ValueChanged<String> onNavigate;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final BriefingViewState s = state;
    final Widget body = switch (s) {
      BriefingLoading() => const GtexSkeleton.box(key: Key('owner-briefing-loading'), height: 72),
      BriefingUnavailable() => const _Note(
          key: Key('owner-briefing-unavailable'),
          title: 'Daily briefing not available yet',
          body: 'Briefings are built from verified, persisted GTEX events. That service has not '
              'been published, so no stories are shown.',
        ),
      BriefingError() => Column(
          key: const Key('owner-briefing-error'),
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const Text('We could not load your briefing.', style: TextStyle(color: GtexColors.danger)),
            if (onRetry != null)
              TextButton(
                key: const Key('owner-briefing-retry'),
                onPressed: onRetry,
                child: const Text('Retry'),
              ),
          ],
        ),
      BriefingEmpty(:final String? worldDate) => _Note(
          key: const Key('owner-briefing-empty'),
          title: 'Nothing to report',
          body: 'No verified events were recorded for your club'
              '${worldDate == null ? '' : ' on $worldDate'}.',
        ),
      BriefingReady(:final OwnerBriefing briefing, :final bool stale) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            if (stale)
              const Padding(
                padding: EdgeInsets.only(bottom: GtexSpacing.xs),
                child: Text(
                  'Showing the last saved briefing; the latest refresh failed.',
                  key: Key('owner-briefing-stale'),
                  style: TextStyle(color: GtexColors.gold, fontSize: 12),
                ),
              ),
            for (final BriefingEvent e in briefing.events)
              _EventCard(event: e, onNavigate: onNavigate),
            if (briefing.rejectedEventCount > 0)
              Text(
                '${briefing.rejectedEventCount} event(s) were hidden because they could not be verified.',
                key: const Key('owner-briefing-rejected'),
                style: const TextStyle(color: GtexColors.textMuted, fontSize: 12),
              ),
            if (briefing.explanation != null)
              Padding(
                padding: const EdgeInsets.only(top: GtexSpacing.xs),
                child: Text(
                  'Commentary (explanatory only): ${briefing.explanation}',
                  key: const Key('owner-briefing-explanation'),
                  style: const TextStyle(color: GtexColors.textSecondary, fontSize: 12, fontStyle: FontStyle.italic),
                ),
              ),
          ],
        ),
    };
    return GtexPanel(
      key: const Key('owner-briefing'),
      title: 'Owner daily briefing',
      subtitle: 'Verified events only',
      accent: GtexColors.gold,
      child: body,
    );
  }
}

class _Note extends StatelessWidget {
  const _Note({super.key, required this.title, required this.body});
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: const TextStyle(color: GtexColors.text, fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          Text(body, style: const TextStyle(color: GtexColors.textSecondary)),
        ],
      );
}

class _EventCard extends StatelessWidget {
  const _EventCard({required this.event, required this.onNavigate});
  final BriefingEvent event;
  final ValueChanged<String> onNavigate;

  @override
  Widget build(BuildContext context) {
    final BriefingTarget? t = event.target;
    return Container(
      key: Key('owner-briefing-card-${event.eventId}'),
      margin: const EdgeInsets.only(bottom: GtexSpacing.sm),
      padding: const EdgeInsets.all(GtexSpacing.sm),
      decoration: BoxDecoration(
        color: GtexColors.panelStrong,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: GtexColors.line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(event.headline, style: const TextStyle(color: GtexColors.text, fontWeight: FontWeight.w800)),
          if (event.detail != null)
            Text(event.detail!, style: const TextStyle(color: GtexColors.textSecondary)),
          Text(event.occurredAt, style: const TextStyle(color: GtexColors.textMuted, fontSize: 11)),
          if (t != null)
            TextButton(
              key: Key('owner-briefing-link-${event.eventId}'),
              onPressed: () => onNavigate(t.route),
              child: Text(t.label),
            ),
        ],
      ),
    );
  }
}
