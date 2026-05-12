import 'package:flutter/material.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/shared/data/gte_feature_support.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

class GtexAwardsScreenV2 extends StatefulWidget {
  const GtexAwardsScreenV2({
    super.key,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.backendMode = GteBackendMode.live,
    this.accessToken,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;

  @override
  State<GtexAwardsScreenV2> createState() => _GtexAwardsScreenV2State();
}

class _GtexAwardsScreenV2State extends State<GtexAwardsScreenV2> {
  late GteAuthedApi _api;
  late Future<_AwardsSnapshot> _future;

  @override
  void initState() {
    super.initState();
    _hydrate();
  }

  @override
  void didUpdateWidget(covariant GtexAwardsScreenV2 oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.baseUrl != widget.baseUrl ||
        oldWidget.backendMode != widget.backendMode ||
        oldWidget.accessToken != widget.accessToken) {
      _hydrate();
    }
  }

  void _hydrate() {
    _api = createFeatureApi(
      baseUrl: widget.baseUrl,
      mode: widget.backendMode,
      accessToken: widget.accessToken,
    );
    _future = _loadAwards();
  }

  Future<_AwardsSnapshot> _loadAwards() {
    return _api.withFallback<_AwardsSnapshot>(() async {
      final List<dynamic> payload =
          await Future.wait<dynamic>(<Future<dynamic>>[
            _api.getList('/api/awards/categories', auth: false),
            _api.getList('/api/awards/nominees', auth: false),
            _api.getList('/api/awards/winners', auth: false),
            _api.getMap('/api/awards/ceremony', auth: false),
          ]);
      return _AwardsSnapshot(
        categories: _maps(payload[0]),
        nomineeBuckets: _maps(payload[1]),
        winners: _maps(payload[2]),
        ceremony: _map(payload[3]),
      );
    }, () => const _AwardsSnapshot.empty());
  }

  void _refresh() {
    setState(() {
      _future = _loadAwards();
    });
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<_AwardsSnapshot>(
      future: _future,
      builder: (BuildContext context, AsyncSnapshot<_AwardsSnapshot> snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(
            child: CircularProgressIndicator(color: GtexColors.gold),
          );
        }
        if (snapshot.hasError || !snapshot.hasData) {
          return GtexEmptyState(
            title: 'Awards unavailable',
            message: AppFeedback.messageFor(snapshot.error ?? 'Unknown error'),
            icon: Icons.emoji_events_outlined,
            accent: GtexColors.gold,
            actionLabel: 'Retry',
            onAction: _refresh,
          );
        }

        final _AwardsSnapshot data = snapshot.data!;
        return GtexMasterDetailScaffold(
          title: 'GTEX Awards',
          subtitle:
              'Seasonal awards, nominee shortlists, winners, and awards-night broadcast state from the live awards engine.',
          accent: GtexColors.gold,
          mobileLeftTitle: 'Awards lanes',
          leftPanel: _AwardsLeftPanel(data: data),
          detail: _AwardsDetailPanel(data: data),
          rightPanel: _AwardsCeremonyPanel(data: data),
          actions: <Widget>[
            GtexActionButton(
              label: 'Refresh',
              icon: Icons.refresh_outlined,
              accent: GtexColors.gold,
              secondary: true,
              onPressed: _refresh,
            ),
          ],
        );
      },
    );
  }
}

class _AwardsLeftPanel extends StatelessWidget {
  const _AwardsLeftPanel({required this.data});

  final _AwardsSnapshot data;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        GtexPanel(
          title: 'Awards pulse',
          subtitle: data.isEmpty ? 'No awards data loaded' : 'Live engine',
          accent: GtexColors.gold,
          child: Column(
            children: <Widget>[
              GtexMetricTile(
                label: 'Categories',
                value: '${data.categories.length}',
                icon: Icons.category_outlined,
                accent: GtexColors.gold,
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexMetricTile(
                label: 'Shortlists',
                value: '${data.nomineeBuckets.length}',
                icon: Icons.format_list_numbered_outlined,
                accent: GtexColors.purple,
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexMetricTile(
                label: 'Winner groups',
                value: '${data.winners.length}',
                icon: Icons.workspace_premium_outlined,
                accent: GtexColors.cyan,
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Categories',
          subtitle: 'Equivalent football awards',
          accent: GtexColors.gold,
          child:
              data.categories.isEmpty
                  ? const Text('No award categories available.')
                  : Column(
                    children: data.categories
                        .take(8)
                        .map((Map<String, dynamic> item) {
                          return _CompactAwardLine(
                            title: _text(item, <String>[
                              'award_name',
                              'awardName',
                            ]),
                            subtitle: _text(item, <String>[
                              'equivalent_name',
                              'equivalentName',
                              'category_group',
                            ]),
                            icon: Icons.emoji_events_outlined,
                          );
                        })
                        .toList(growable: false),
                  ),
        ),
      ],
    );
  }
}

class _AwardsDetailPanel extends StatelessWidget {
  const _AwardsDetailPanel({required this.data});

  final _AwardsSnapshot data;

  @override
  Widget build(BuildContext context) {
    if (data.nomineeBuckets.isEmpty && data.winners.isEmpty) {
      return GtexEmptyState(
        title: 'No awards board yet',
        message:
            'The awards route is live, but the backend has not returned nominees or winner groups yet.',
        icon: Icons.emoji_events_outlined,
        accent: GtexColors.gold,
      );
    }

    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.lg),
      children: <Widget>[
        for (final Map<String, dynamic> bucket in data.nomineeBuckets.take(8))
          _NomineeBucketCard(bucket: bucket),
        if (data.winners.isNotEmpty) ...<Widget>[
          const SizedBox(height: GtexSpacing.md),
          GtexPanel(
            title: 'Winner groups',
            subtitle: 'Confirmed winners and finalists',
            accent: GtexColors.cyan,
            child: Column(
              children: data.winners
                  .take(8)
                  .map((Map<String, dynamic> winner) {
                    final List<Map<String, dynamic>> winners = _maps(
                      winner['winners'],
                    );
                    return _CompactAwardLine(
                      title: _text(winner, <String>[
                        'award_name',
                        'awardName',
                        'equivalent_name',
                      ]),
                      subtitle:
                          winners.isEmpty
                              ? 'No winner returned'
                              : winners
                                  .map(
                                    (Map<String, dynamic> item) =>
                                        _text(item, <String>['display_name']),
                                  )
                                  .join(', '),
                      icon: Icons.workspace_premium_outlined,
                    );
                  })
                  .toList(growable: false),
            ),
          ),
        ],
      ],
    );
  }
}

class _NomineeBucketCard extends StatelessWidget {
  const _NomineeBucketCard({required this.bucket});

  final Map<String, dynamic> bucket;

  @override
  Widget build(BuildContext context) {
    final List<Map<String, dynamic>> stages = _maps(bucket['stages']);
    final List<Map<String, dynamic>> nominees =
        stages.isEmpty
            ? const <Map<String, dynamic>>[]
            : _maps(stages.first['nominees']);
    return Padding(
      padding: const EdgeInsets.only(bottom: GtexSpacing.md),
      child: GtexPanel(
        title: _text(bucket, <String>['award_name', 'equivalent_name']),
        subtitle: _text(bucket, <String>['category_group', 'entity_type']),
        accent: GtexColors.gold,
        child:
            nominees.isEmpty
                ? const Text('No nominees returned for this award.')
                : Column(
                  children: nominees
                      .take(5)
                      .map((Map<String, dynamic> nominee) {
                        return _CompactAwardLine(
                          title: _text(nominee, <String>['display_name']),
                          subtitle:
                              'Rank ${_text(nominee, <String>['rank'])} - score ${_text(nominee, <String>['nomination_score'])}',
                          icon: Icons.person_search_outlined,
                        );
                      })
                      .toList(growable: false),
                ),
      ),
    );
  }
}

class _AwardsCeremonyPanel extends StatelessWidget {
  const _AwardsCeremonyPanel({required this.data});

  final _AwardsSnapshot data;

  @override
  Widget build(BuildContext context) {
    final Map<String, dynamic> ceremony = data.ceremony;
    final List<Map<String, dynamic>> segments = _maps(ceremony['segments']);
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        GtexPanel(
          title: _text(ceremony, <String>['title'], fallback: 'Awards night'),
          subtitle:
              'Season ${_text(ceremony, <String>['season_number'], fallback: '-')}.',
          accent: GtexColors.gold,
          child: Column(
            children: <Widget>[
              GtexMetricTile(
                label: 'Segments',
                value: '${segments.length}',
                icon: Icons.live_tv_outlined,
                accent: GtexColors.gold,
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexMetricTile(
                label: 'Tickets sold',
                value: _text(ceremony, <String>['tickets_sold'], fallback: '0'),
                icon: Icons.confirmation_number_outlined,
                accent: GtexColors.cyan,
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexMetricTile(
                label: 'Live vote',
                value:
                    ceremony['live_vote_enabled'] == true ? 'Enabled' : 'Off',
                icon: Icons.how_to_vote_outlined,
                accent: GtexColors.purple,
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Ceremony flow',
          subtitle: 'Broadcast segments',
          accent: GtexColors.purple,
          child:
              segments.isEmpty
                  ? const Text('No ceremony segments returned.')
                  : Column(
                    children: segments
                        .take(8)
                        .map((Map<String, dynamic> segment) {
                          return _CompactAwardLine(
                            title: _text(segment, <String>['title']),
                            subtitle: _text(segment, <String>[
                              'presenter',
                              'reveal_style',
                            ]),
                            icon: Icons.theater_comedy_outlined,
                          );
                        })
                        .toList(growable: false),
                  ),
        ),
      ],
    );
  }
}

class _CompactAwardLine extends StatelessWidget {
  const _CompactAwardLine({
    required this.title,
    required this.subtitle,
    required this.icon,
  });

  final String title;
  final String subtitle;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(icon, color: GtexColors.gold, size: 20),
          const SizedBox(width: GtexSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  subtitle,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: GtexColors.textMuted),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _AwardsSnapshot {
  const _AwardsSnapshot({
    required this.categories,
    required this.nomineeBuckets,
    required this.winners,
    required this.ceremony,
  });

  const _AwardsSnapshot.empty()
    : categories = const <Map<String, dynamic>>[],
      nomineeBuckets = const <Map<String, dynamic>>[],
      winners = const <Map<String, dynamic>>[],
      ceremony = const <String, dynamic>{};

  final List<Map<String, dynamic>> categories;
  final List<Map<String, dynamic>> nomineeBuckets;
  final List<Map<String, dynamic>> winners;
  final Map<String, dynamic> ceremony;

  bool get isEmpty =>
      categories.isEmpty &&
      nomineeBuckets.isEmpty &&
      winners.isEmpty &&
      ceremony.isEmpty;
}

List<Map<String, dynamic>> _maps(Object? raw) {
  if (raw is! Iterable) {
    return const <Map<String, dynamic>>[];
  }
  return raw
      .whereType<Map>()
      .map((Map<dynamic, dynamic> item) => Map<String, dynamic>.from(item))
      .toList(growable: false);
}

Map<String, dynamic> _map(Object? raw) {
  if (raw is Map) {
    return Map<String, dynamic>.from(raw);
  }
  return const <String, dynamic>{};
}

String _text(
  Map<String, dynamic> source,
  List<String> keys, {
  String fallback = '-',
}) {
  for (final String key in keys) {
    final Object? value = source[key];
    final String text = value?.toString().trim() ?? '';
    if (text.isNotEmpty) {
      return text;
    }
  }
  return fallback;
}
