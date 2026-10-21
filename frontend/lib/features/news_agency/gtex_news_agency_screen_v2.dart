import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';

import '../../data/story_feed_api.dart';
import '../../models/story_feed_models.dart';
import '../../ui_gtex/ui_gtex.dart';
import '../engagement_redesign/engagement_controller.dart';
import '../engagement_redesign/engagement_models.dart';
import '../engagement_redesign/engagement_widgets.dart';
import '../home/data/gtex_story_feed_ticker_provider.dart';

/// Canonical grounding disclosure label for the GTEX Newsroom (Document I3).
const String kGtexNewsroomGroundingLabel =
    'Generated from verified match and ledger events';

const Set<String> _kScrubbedArticleKeys = <String>{
  'owner_user_id',
  'ownerUserId',
  'club_cash',
  'clubCash',
  'cash_balance',
  'cashBalance',
  'transfer_budget',
  'transferBudget',
  'wage_budget',
  'wageBudget',
};

/// Grounded Newsroom article model extending [GtexNewsArticle] with
/// `established_facts`, `grounding_report`, `status` (`published` / `retracted`),
/// and Decision O-09 verified price & owner display fields.
class GtexGroundedNewsArticle extends GtexNewsArticle {
  const GtexGroundedNewsArticle({
    required super.id,
    required super.title,
    required super.summary,
    required super.body,
    required super.category,
    required super.publishedAt,
    super.heroLabel,
    super.byline,
    super.relatedEntity,
    super.relatedRoute,
    super.shareUrl,
    super.isBreaking = false,
    super.isFeatured = false,
    super.trustScore = 0.92,
    super.reactionCount = 0,
    super.commentCount = 0,
    this.status = 'published',
    this.establishedFacts = const <String, Object?>{},
    this.groundingReport = const <String, Object?>{},
    this.verifiedPriceGtex,
    this.ownerDisplayName,
  });

  factory GtexGroundedNewsArticle.fromBase(
    GtexNewsArticle base, {
    String status = 'published',
    Map<String, Object?> establishedFacts = const <String, Object?>{},
    Map<String, Object?> groundingReport = const <String, Object?>{},
    String? verifiedPriceGtex,
    String? ownerDisplayName,
  }) {
    if (base is GtexGroundedNewsArticle) {
      return base;
    }
    return GtexGroundedNewsArticle(
      id: base.id,
      title: base.title,
      summary: base.summary,
      body: base.body,
      category: base.category,
      publishedAt: base.publishedAt,
      heroLabel: base.heroLabel,
      byline: base.byline,
      relatedEntity: base.relatedEntity,
      relatedRoute: base.relatedRoute,
      shareUrl: base.shareUrl,
      isBreaking: base.isBreaking,
      isFeatured: base.isFeatured,
      trustScore: base.trustScore,
      reactionCount: base.reactionCount,
      commentCount: base.commentCount,
      status: status,
      establishedFacts: establishedFacts,
      groundingReport: groundingReport,
      verifiedPriceGtex: verifiedPriceGtex,
      ownerDisplayName: ownerDisplayName,
    );
  }

  final String status;
  final Map<String, Object?> establishedFacts;
  final Map<String, Object?> groundingReport;
  final String? verifiedPriceGtex;
  final String? ownerDisplayName;

  bool get isRetracted =>
      GtexStatusPresenter.normalize(status) == 'retracted';

  bool get hasEstablishedFacts => establishedFacts.isNotEmpty;
}

class GtexNewsAgencyScreenV2 extends StatefulWidget {
  const GtexNewsAgencyScreenV2({
    super.key,
    this.controller,
    this.api,
    this.allowFixtureData = false,
    this.initialStories,
    this.initialArticles,
  });

  final GtexEngagementController? controller;
  final StoryFeedApi? api;
  final bool allowFixtureData;
  final List<StoryFeedItem>? initialStories;
  final List<GtexNewsArticle>? initialArticles;

  @override
  State<GtexNewsAgencyScreenV2> createState() => _GtexNewsAgencyScreenV2State();
}

class _GtexNewsAgencyScreenV2State extends State<GtexNewsAgencyScreenV2> {
  late final GtexEngagementController _controller;
  late Future<List<GtexGroundedNewsArticle>> _articlesFuture;
  GtexNewsCategory? _category;
  GtexGroundedNewsArticle? _selected;
  String _query = '';

  @override
  void initState() {
    super.initState();
    _controller = widget.controller ?? GtexEngagementController();
    _articlesFuture = _loadArticles();
  }

  @override
  void didUpdateWidget(covariant GtexNewsAgencyScreenV2 oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.api != widget.api ||
        oldWidget.controller != widget.controller ||
        oldWidget.initialStories != widget.initialStories ||
        oldWidget.initialArticles != widget.initialArticles) {
      _selected = null;
      _articlesFuture = _loadArticles();
    }
  }

  Future<List<GtexGroundedNewsArticle>> _loadArticles() async {
    if (widget.initialStories != null) {
      return buildGroundedNewsroomArticles(widget.initialStories!);
    }
    if (widget.initialArticles != null) {
      return deduplicateNewsroomArticles(widget.initialArticles!);
    }
    final StoryFeedApi? api = widget.api;
    if (api == null) {
      if (widget.allowFixtureData) {
        return deduplicateNewsroomArticles(_controller.loadDemoArticles());
      }
      throw StateError('Live story feed API is required for GTEX News Agency.');
    }
    final List<StoryFeedItem> stories = await api.listFeed(limit: 100);
    return buildGroundedNewsroomArticles(stories);
  }

  void _refresh() {
    setState(() {
      _selected = null;
      _articlesFuture = _loadArticles();
    });
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<GtexGroundedNewsArticle>>(
      future: _articlesFuture,
      builder: (
        BuildContext context,
        AsyncSnapshot<List<GtexGroundedNewsArticle>> snapshot,
      ) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return GtexEmptyState(
            title: 'News agency unavailable',
            message: snapshot.error.toString(),
            icon: Icons.article_outlined,
            accent: GtexColors.gold,
            actionLabel: 'Retry',
            onAction: _refresh,
          );
        }
        final List<GtexGroundedNewsArticle> articles =
            snapshot.data ?? const <GtexGroundedNewsArticle>[];
        if (articles.isEmpty) {
          return GtexEmptyState(
            title: 'No GTEX stories yet',
            message:
                'Live transfer, club, regen, tournament and jackpot stories will appear here when the story feed publishes them.',
            icon: Icons.newspaper_outlined,
            accent: GtexColors.gold,
            actionLabel: 'Refresh',
            onAction: _refresh,
          );
        }
        final String query = _query.trim().toLowerCase();
        final List<GtexGroundedNewsArticle> visible = articles
            .where((GtexGroundedNewsArticle article) {
              final bool categoryMatches =
                  _category == null || article.category == _category;
              if (!categoryMatches) {
                return false;
              }
              if (query.isEmpty) {
                return true;
              }
              return <String?>[
                article.title,
                article.summary,
                article.body,
                article.relatedEntity,
                article.heroLabel,
                article.categoryLabel,
              ].whereType<String>().join(' ').toLowerCase().contains(query);
            })
            .toList(growable: false);
        final GtexGroundedNewsArticle selected =
            _selected != null &&
                    visible.any(
                      (GtexGroundedNewsArticle article) =>
                          article.id == _selected!.id,
                    )
                ? visible.firstWhere(
                  (GtexGroundedNewsArticle article) =>
                      article.id == _selected!.id,
                )
                : (visible.isEmpty ? articles.first : visible.first);

        return GtexMasterDetailScaffold(
          title: 'Newsroom',
          subtitle:
              'Live football economy desk: transfers, clubs, regens, tournaments, rentals, gifts and market movement from backend story feed.',
          accent: GtexColors.gold,
          mobileLeftTitle: 'Headlines',
          leftPanelWidth: 350,
          rightPanelWidth: 320,
          actions: <Widget>[
            GtexActionButton(
              label: 'Refresh',
              icon: Icons.sync_outlined,
              onPressed: _refresh,
              accent: GtexColors.gold,
              secondary: true,
            ),
          ],
          leftPanel: _NewsLeftPanel(
            articles: visible,
            selected: selected,
            category: _category,
            query: _query,
            onQueryChanged:
                (String value) => setState(() {
                  _query = value;
                  _selected = null;
                }),
            onCategoryChanged:
                (GtexNewsCategory? category) =>
                    setState(() => _category = category),
            onSelected:
                (GtexGroundedNewsArticle article) =>
                    setState(() => _selected = article),
          ),
          detail: _NewsArticleDetail(article: selected, articles: articles),
          rightPanel: _NewsRightRail(article: selected, articles: articles),
        );
      },
    );
  }
}

/// Converts backend [StoryFeedItem] records into [GtexGroundedNewsArticle]s,
/// deduplicating by `id` (Document I3) and sorting featured/breaking first.
List<GtexGroundedNewsArticle> buildGroundedNewsroomArticles(
  Iterable<StoryFeedItem> stories,
) {
  final List<GtexGroundedNewsArticle> mapped = stories
      .map(groundedArticleFromStory)
      .toList(growable: false);
  return deduplicateNewsroomArticles(mapped);
}

/// Deduplicates Newsroom [articles] by `id` (Document I3).
///
/// If multiple entries share the same `id`, preserves any `retracted` status
/// and merges non-empty `establishedFacts`.
List<GtexGroundedNewsArticle> deduplicateNewsroomArticles(
  Iterable<GtexNewsArticle> articles,
) {
  final Map<String, GtexGroundedNewsArticle> dedupedById =
      <String, GtexGroundedNewsArticle>{};

  for (final GtexNewsArticle rawArticle in articles) {
    final GtexGroundedNewsArticle article =
        GtexGroundedNewsArticle.fromBase(rawArticle);
    final String id = article.id.trim();
    if (id.isEmpty) {
      continue;
    }
    final GtexGroundedNewsArticle? existing = dedupedById[id];
    if (existing == null) {
      dedupedById[id] = article;
    } else {
      final bool isRetracted = existing.isRetracted || article.isRetracted;
      final Map<String, Object?> mergedFacts = <String, Object?>{
        ...existing.establishedFacts,
        ...article.establishedFacts,
      };
      final GtexGroundedNewsArticle newer =
          article.publishedAt.isAfter(existing.publishedAt)
              ? article
              : existing;
      dedupedById[id] = GtexGroundedNewsArticle(
        id: id,
        title: newer.title,
        summary: newer.summary,
        body: newer.body,
        category: newer.category,
        publishedAt: newer.publishedAt,
        heroLabel: newer.heroLabel ?? existing.heroLabel,
        byline: newer.byline ?? existing.byline,
        relatedEntity: newer.relatedEntity ?? existing.relatedEntity,
        relatedRoute: newer.relatedRoute ?? existing.relatedRoute,
        shareUrl: newer.shareUrl ?? existing.shareUrl,
        isBreaking: existing.isBreaking || article.isBreaking,
        isFeatured: existing.isFeatured || article.isFeatured,
        trustScore: newer.trustScore,
        reactionCount: newer.reactionCount,
        commentCount: newer.commentCount,
        status: isRetracted ? 'retracted' : newer.status,
        establishedFacts: Map<String, Object?>.unmodifiable(mergedFacts),
        groundingReport:
            newer.groundingReport.isNotEmpty
                ? newer.groundingReport
                : existing.groundingReport,
        verifiedPriceGtex:
            newer.verifiedPriceGtex ?? existing.verifiedPriceGtex,
        ownerDisplayName:
            newer.ownerDisplayName ?? existing.ownerDisplayName,
      );
    }
  }

  final List<GtexGroundedNewsArticle> result =
      dedupedById.values.toList(growable: true)
        ..sort((GtexGroundedNewsArticle a, GtexGroundedNewsArticle b) {
          final int featuredCmp =
              (b.isFeatured || b.isBreaking ? 1 : 0) -
              (a.isFeatured || a.isBreaking ? 1 : 0);
          if (featuredCmp != 0) {
            return featuredCmp;
          }
          return b.publishedAt.compareTo(a.publishedAt);
        });
  return List<GtexGroundedNewsArticle>.unmodifiable(result);
}

/// Maps a [StoryFeedItem] into a [GtexGroundedNewsArticle] while enforcing
/// Document I2/I3 grounding and Decision O-09 privacy rules.
GtexGroundedNewsArticle groundedArticleFromStory(StoryFeedItem story) {
  final Map<String, Object?> metadata = story.metadata;
  final Map<String, Object?> rawFacts = _extractMap(metadata, const <String>[
    'established_facts',
    'established_facts_json',
    'establishedFacts',
  ]);
  final String? rawOwnerUserId =
      _metadataString(metadata, const <String>[
        'owner_user_id',
        'ownerUserId',
      ]) ??
      _metadataString(rawFacts, const <String>[
        'owner_user_id',
        'ownerUserId',
      ]);
  final String? ownerDisplayName =
      _metadataString(metadata, const <String>[
        'owner_display_name',
        'ownerDisplayName',
      ]) ??
      _metadataString(rawFacts, const <String>[
        'owner_display_name',
        'ownerDisplayName',
      ]);

  final Object? rawPrice =
      metadata['verified_price_gtex'] ??
      metadata['verifiedPriceGtex'] ??
      rawFacts['verified_price_gtex'] ??
      rawFacts['verifiedPriceGtex'];
  final String? formattedPrice = formatVerifiedPriceGtex(rawPrice);

  final Map<String, Object?> cleanFacts = <String, Object?>{};
  for (final MapEntry<String, Object?> entry in rawFacts.entries) {
    if (_kScrubbedArticleKeys.contains(entry.key) || entry.value == null) {
      continue;
    }
    if (entry.key == 'verified_price_gtex' ||
        entry.key == 'verifiedPriceGtex') {
      cleanFacts['verified_price_gtex'] =
          formattedPrice ?? entry.value.toString();
      continue;
    }
    if (entry.value is String) {
      final String trimmed = (entry.value as String).trim();
      if (trimmed.isEmpty) {
        continue;
      }
      cleanFacts[entry.key] = _scrubOwnerUserId(
        trimmed,
        rawOwnerUserId: rawOwnerUserId,
        ownerDisplayName: ownerDisplayName,
      );
    } else {
      cleanFacts[entry.key] = entry.value;
    }
  }

  final Map<String, Object?> groundingReport = _extractMap(
    metadata,
    const <String>[
      'grounding_report',
      'grounding_report_json',
      'groundingReport',
    ],
  );

  final String rawTitle =
      story.title.trim().isNotEmpty
          ? story.title.trim()
          : (_metadataString(metadata, const <String>['headline', 'title']) ??
              'GTEX Story');
  final String rawBody =
      story.body.trim().isNotEmpty
          ? story.body.trim()
          : (_metadataString(metadata, const <String>[
                'editorial_narration',
                'editorialNarration',
                'body',
              ]) ??
              '');
  final String cleanTitle = _scrubOwnerUserId(
    rawTitle,
    rawOwnerUserId: rawOwnerUserId,
    ownerDisplayName: ownerDisplayName,
  );
  final String cleanBody = _scrubOwnerUserId(
    rawBody,
    rawOwnerUserId: rawOwnerUserId,
    ownerDisplayName: ownerDisplayName,
  );
  final String summary = _scrubOwnerUserId(
    _metadataString(metadata, const <String>[
          'summary',
          'subheadline',
          'dek',
          'excerpt',
        ]) ??
        _summarize(cleanBody),
    rawOwnerUserId: rawOwnerUserId,
    ownerDisplayName: ownerDisplayName,
  );
  final String? journalist = _metadataString(metadata, const <String>[
    'journalist',
    'byline',
    'author',
    'reporter',
  ]);
  final String resolvedStatus = _resolveArticleStatus(story);
  final bool isRetracted =
      GtexStatusPresenter.normalize(resolvedStatus) == 'retracted';

  final String? rawRelatedEntity =
      _metadataString(metadata, const <String>[
        'related_entity',
        'relatedEntity',
        'subject_label',
        'subjectLabel',
        'player_name',
        'club_name',
        'club',
      ]) ??
      _metadataString(cleanFacts, const <String>[
        'club_name',
        'home_club',
        'player_name',
      ]) ??
      ((rawOwnerUserId != null && story.subjectId == rawOwnerUserId)
          ? null
          : story.subjectId) ??
      story.countryCode;

  return GtexGroundedNewsArticle(
    id: story.id.trim(),
    title: cleanTitle,
    summary: summary,
    body: cleanBody,
    category: _categoryFromStory(story),
    publishedAt: story.createdAt,
    heroLabel:
        _metadataString(metadata, const <String>['hero_label', 'heroLabel']) ??
        _humanize(story.storyType),
    byline: journalist ?? 'GTEX Wire',
    relatedEntity:
        rawRelatedEntity == null
            ? null
            : _scrubOwnerUserId(
              rawRelatedEntity,
              rawOwnerUserId: rawOwnerUserId,
              ownerDisplayName: ownerDisplayName,
            ),
    relatedRoute: _metadataString(metadata, const <String>[
      'related_route',
      'relatedRoute',
      'route',
      'deep_link',
      'deepLink',
    ]),
    shareUrl: _metadataString(metadata, const <String>[
      'share_url',
      'shareUrl',
      'url',
      'canonical_url',
      'canonicalUrl',
    ]),
    isBreaking:
        !isRetracted &&
        (story.featured || story.storyType.toLowerCase().contains('break')),
    isFeatured: story.featured,
    trustScore: _metadataDouble(metadata, const <String>[
      'trust_score',
      'trustScore',
    ]),
    reactionCount: _metadataInt(metadata, const <String>[
      'reaction_count',
      'reactionCount',
      'reactions',
      'reactions_count',
      'reactionsCount',
    ]),
    commentCount: _metadataInt(metadata, const <String>[
      'comment_count',
      'commentCount',
      'comments',
      'comments_count',
      'commentsCount',
    ]),
    status: resolvedStatus,
    establishedFacts: Map<String, Object?>.unmodifiable(cleanFacts),
    groundingReport: Map<String, Object?>.unmodifiable(groundingReport),
    verifiedPriceGtex: formattedPrice,
    ownerDisplayName: ownerDisplayName,
  );
}

String _resolveArticleStatus(StoryFeedItem story) {
  final String? metaStatus = _metadataString(story.metadata, const <String>[
    'status',
    'moderation_status',
    'moderationStatus',
    'article_status',
    'articleStatus',
  ]);
  if (metaStatus != null &&
      GtexStatusPresenter.normalize(metaStatus) == 'retracted') {
    return 'retracted';
  }
  if (GtexStatusPresenter.normalize(story.moderationStatus) == 'retracted') {
    return 'retracted';
  }
  return metaStatus ?? story.moderationStatus;
}

Map<String, Object?> _extractMap(
  Map<String, Object?> source,
  List<String> keys,
) {
  for (final String key in keys) {
    final Object? value = source[key];
    if (value is Map) {
      return value.map(
        (Object? k, Object? v) => MapEntry<String, Object?>(k.toString(), v),
      );
    }
    if (value is Iterable) {
      final Map<String, Object?> listMap = <String, Object?>{};
      int idx = 1;
      for (final Object? entry in value) {
        if (entry != null && entry.toString().trim().isNotEmpty) {
          listMap['fact_$idx'] = entry.toString().trim();
          idx += 1;
        }
      }
      if (listMap.isNotEmpty) {
        return listMap;
      }
    }
  }
  return const <String, Object?>{};
}

String _scrubOwnerUserId(
  String input, {
  required String? rawOwnerUserId,
  required String? ownerDisplayName,
}) {
  if (rawOwnerUserId == null || rawOwnerUserId.isEmpty) {
    return input;
  }
  return input.replaceAll(
    rawOwnerUserId,
    ownerDisplayName ?? 'Club Ownership',
  );
}

GtexNewsCategory _categoryFromStory(StoryFeedItem story) {
  final String metaCategory =
      _metadataString(story.metadata, const <String>['category']) ?? '';
  final String raw =
      '${story.storyType} $metaCategory ${story.subjectType ?? ''}'
          .trim()
          .toLowerCase();
  if (raw.contains('break') || raw.contains('app_update')) {
    return GtexNewsCategory.breaking;
  }
  if (raw.contains('exit_petition') ||
      raw.contains('transfer') ||
      raw.contains('here_we_go')) {
    return GtexNewsCategory.transfers;
  }
  if (raw.contains('club') ||
      raw.contains('fleet_aviation') ||
      raw.contains('infrastructure') ||
      raw.contains('squad_culture') ||
      raw.contains('private_jet') ||
      raw.contains('facility_upgrade') ||
      raw.contains('player_gift')) {
    return GtexNewsCategory.clubs;
  }
  if (raw.contains('regen') ||
      raw.contains('newgen') ||
      raw.contains('rising') ||
      raw.contains('scouting')) {
    return GtexNewsCategory.regens;
  }
  if (raw.contains('award')) return GtexNewsCategory.awards;
  if (raw.contains('tournament') ||
      raw.contains('competition') ||
      raw.contains('match_report')) {
    return GtexNewsCategory.tournaments;
  }
  if (raw.contains('national')) return GtexNewsCategory.nationalTeams;
  if (raw.contains('jackpot')) return GtexNewsCategory.jackpot;
  if (raw.contains('creator')) return GtexNewsCategory.creators;
  if (raw.contains('dispute')) return GtexNewsCategory.disputes;
  if (raw.contains('market') || raw.contains('order') || raw.contains('leak')) {
    return GtexNewsCategory.market;
  }
  return story.featured ? GtexNewsCategory.breaking : GtexNewsCategory.market;
}

String _summarize(String body) {
  final String trimmed = body.trim().replaceAll(RegExp(r'\s+'), ' ');
  if (trimmed.length <= 160) {
    return trimmed;
  }
  return '${trimmed.substring(0, 157)}...';
}

String _humanize(String raw) {
  final String normalized = raw.trim();
  if (normalized.isEmpty) {
    return 'GTEX Story';
  }
  return normalized
      .split(RegExp(r'[_\s-]+'))
      .where((String part) => part.isNotEmpty)
      .map(
        (String part) =>
            '${part[0].toUpperCase()}${part.substring(1).toLowerCase()}',
      )
      .join(' ');
}

String? _metadataString(Map<String, Object?> metadata, List<String> keys) {
  for (final String key in keys) {
    final Object? value = metadata[key];
    if (value is String && value.trim().isNotEmpty) {
      return value.trim();
    }
  }
  return null;
}

double _metadataDouble(Map<String, Object?> metadata, List<String> keys) {
  for (final String key in keys) {
    final Object? value = metadata[key];
    if (value is num) {
      return value.toDouble();
    }
    if (value is String) {
      final double? parsed = double.tryParse(value);
      if (parsed != null) {
        return parsed;
      }
    }
  }
  return 0.92;
}

int _metadataInt(Map<String, Object?> metadata, List<String> keys) {
  for (final String key in keys) {
    final Object? value = metadata[key];
    if (value is int) {
      return value;
    }
    if (value is num) {
      return value.round();
    }
    if (value is String) {
      final int? parsed = int.tryParse(value);
      if (parsed != null) {
        return parsed;
      }
    }
  }
  return 0;
}

class _NewsLeftPanel extends StatelessWidget {
  const _NewsLeftPanel({
    required this.articles,
    required this.selected,
    required this.category,
    required this.query,
    required this.onQueryChanged,
    required this.onCategoryChanged,
    required this.onSelected,
  });

  final List<GtexGroundedNewsArticle> articles;
  final GtexGroundedNewsArticle selected;
  final GtexNewsCategory? category;
  final String query;
  final ValueChanged<String> onQueryChanged;
  final ValueChanged<GtexNewsCategory?> onCategoryChanged;
  final ValueChanged<GtexGroundedNewsArticle> onSelected;

  @override
  Widget build(BuildContext context) {
    final String? firstUnselectedRetractedId =
        selected.isRetracted
            ? null
            : articles
                .where((GtexGroundedNewsArticle item) => item.isRetracted)
                .map((GtexGroundedNewsArticle item) => item.id)
                .firstOrNull;

    return Column(
      children: <Widget>[
        GtexSearchField(hintText: 'Search newsroom', onChanged: onQueryChanged),
        const SizedBox(height: GtexSpacing.md),
        SizedBox(
          height: 42,
          child: ListView(
            scrollDirection: Axis.horizontal,
            children: <Widget>[
              Padding(
                padding: const EdgeInsets.only(right: GtexSpacing.xs),
                child: ChoiceChip(
                  selected: category == null,
                  label: const Text('All'),
                  onSelected: (_) => onCategoryChanged(null),
                ),
              ),
              for (final GtexNewsCategory item in GtexNewsCategory.values)
                Padding(
                  padding: const EdgeInsets.only(right: GtexSpacing.xs),
                  child: ChoiceChip(
                    selected: category == item,
                    label: Text(_categoryFilterLabel(item)),
                    onSelected: (_) => onCategoryChanged(item),
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        Expanded(
          child: ListView(
            children: <Widget>[
              for (final GtexGroundedNewsArticle article in articles)
                GtexSectionListTile(
                  title: article.title,
                  subtitle:
                      article.byline == null
                          ? article.summary
                          : '${article.byline} · ${article.summary}',
                  icon:
                      article.isRetracted
                          ? Icons.undo_rounded
                          : article.isBreaking
                          ? Icons.bolt_outlined
                          : article.isFeatured
                          ? Icons.push_pin_outlined
                          : Icons.article_outlined,
                  accent:
                      article.isRetracted
                          ? GtexColors.navy.danger
                          : newsCategoryColor(article.category),
                  isSelected: article.id == selected.id,
                  onTap: () => onSelected(article),
                  trailing:
                      article.isRetracted &&
                              article.id == firstUnselectedRetractedId
                          ? GtexStatusChip.fromBackendStatus(
                            'retracted',
                            key: const Key('gtex-newsroom-retracted-badge'),
                            compact: true,
                          )
                          : article.isBreaking
                          ? const GtexStatusChip(
                            label: 'LIVE',
                            color: GtexColors.red,
                            compact: true,
                          )
                          : article.isFeatured
                          ? const GtexStatusChip(
                            label: 'PIN',
                            color: GtexColors.gold,
                            compact: true,
                          )
                          : null,
                ),
            ],
          ),
        ),
      ],
    );
  }
}

String _categoryFilterLabel(GtexNewsCategory category) {
  switch (category) {
    case GtexNewsCategory.breaking:
      return 'Breaking';
    case GtexNewsCategory.transfers:
      return 'Transfers';
    case GtexNewsCategory.clubs:
      return 'Clubs';
    case GtexNewsCategory.regens:
      return 'Regens';
    case GtexNewsCategory.awards:
      return 'Awards';
    case GtexNewsCategory.tournaments:
      return 'Tournaments';
    case GtexNewsCategory.nationalTeams:
      return 'National';
    case GtexNewsCategory.jackpot:
      return 'Jackpot';
    case GtexNewsCategory.market:
      return 'Market';
    case GtexNewsCategory.creators:
      return 'Creators';
    case GtexNewsCategory.disputes:
      return 'Disputes';
  }
}

class _NewsArticleDetail extends StatelessWidget {
  const _NewsArticleDetail({required this.article, required this.articles});

  final GtexGroundedNewsArticle article;
  final List<GtexGroundedNewsArticle> articles;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.lg),
      children: <Widget>[
        _NewsroomGroundingBanner(article: article, navy: navy),
        const SizedBox(height: GtexSpacing.md),
        if (article.hasEstablishedFacts) ...<Widget>[
          _EstablishedFactsBox(
            facts: article.establishedFacts,
            navy: navy,
          ),
          const SizedBox(height: GtexSpacing.md),
        ],
        _LiveTransferTicker(articles: articles),
        const SizedBox(height: GtexSpacing.md),
        GtexArticleHero(article: article),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'GTEX story intelligence',
          subtitle:
              'Related entities and explainability come from backend story metadata.',
          accent: newsCategoryColor(article.category),
          child: Wrap(
            spacing: GtexSpacing.sm,
            runSpacing: GtexSpacing.sm,
            children: <Widget>[
              if (article.relatedEntity != null)
                GtexStatusChip(
                  label: article.relatedEntity!,
                  color: GtexColors.pitch,
                  icon: Icons.link_outlined,
                ),
              if (article.ownerDisplayName != null)
                GtexStatusChip(
                  label: article.ownerDisplayName!,
                  color: navy.gold500,
                  icon: Icons.verified_user_outlined,
                ),
              if (article.verifiedPriceGtex != null)
                GtexStatusChip(
                  label: article.verifiedPriceGtex!,
                  color: navy.info,
                  icon: Icons.paid_outlined,
                ),
              if (article.heroLabel != null)
                GtexStatusChip(
                  label: article.heroLabel!,
                  color: GtexColors.gold,
                  icon: Icons.star_border_outlined,
                ),
              const GtexStatusChip(
                label: 'SOURCE CHECKED',
                color: GtexColors.cyan,
                icon: Icons.auto_awesome_outlined,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _NewsroomGroundingBanner extends StatelessWidget {
  const _NewsroomGroundingBanner({
    required this.article,
    required this.navy,
  });

  final GtexGroundedNewsArticle article;
  final GtexColorTokens navy;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: GtexSpacing.md,
        vertical: GtexSpacing.sm,
      ),
      decoration: BoxDecoration(
        color: navy.bgSurface,
        borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
        border: Border.all(
          color: article.isRetracted ? navy.danger : navy.lineSubtle,
        ),
      ),
      child: Wrap(
        spacing: GtexSpacing.sm,
        runSpacing: GtexSpacing.xs,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: <Widget>[
          Row(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Icon(
                Icons.verified_outlined,
                size: 16,
                color: navy.info,
              ),
              const SizedBox(width: GtexSpacing.xs),
              Flexible(
                child: Text(
                  kGtexNewsroomGroundingLabel,
                  key: const Key('gtex-newsroom-grounding-label'),
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: navy.textPrimary,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
          if (article.isRetracted)
            GtexStatusChip.fromBackendStatus(
              'retracted',
              key: const Key('gtex-newsroom-retracted-badge'),
            ),
        ],
      ),
    );
  }
}

class _EstablishedFactsBox extends StatelessWidget {
  const _EstablishedFactsBox({
    required this.facts,
    required this.navy,
  });

  final Map<String, Object?> facts;
  final GtexColorTokens navy;

  @override
  Widget build(BuildContext context) {
    final List<MapEntry<String, String>> entries = <MapEntry<String, String>>[];
    for (final MapEntry<String, Object?> entry in facts.entries) {
      if (_kScrubbedArticleKeys.contains(entry.key) || entry.value == null) {
        continue;
      }
      final String formattedValue = _formatFactValue(entry.key, entry.value);
      if (formattedValue.isEmpty) {
        continue;
      }
      entries.add(
        MapEntry<String, String>(_humanize(entry.key), formattedValue),
      );
    }

    return Container(
      key: const Key('gtex-newsroom-established-facts'),
      padding: const EdgeInsets.all(GtexSpacing.md),
      decoration: BoxDecoration(
        color: navy.bgSurface,
        borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
        border: Border.all(color: navy.gold500.withValues(alpha: 0.45)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(
                Icons.fact_check_outlined,
                size: 18,
                color: navy.gold500,
              ),
              const SizedBox(width: GtexSpacing.xs),
              Text(
                'Established Facts',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  color: navy.textPrimary,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
          const SizedBox(height: GtexSpacing.sm),
          Wrap(
            spacing: GtexSpacing.md,
            runSpacing: GtexSpacing.xs,
            children: entries
                .map(
                  (MapEntry<String, String> fact) => Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: GtexSpacing.sm,
                      vertical: GtexSpacing.xs,
                    ),
                    decoration: BoxDecoration(
                      color: navy.bgInset,
                      borderRadius: BorderRadius.circular(GtexSpacing.radiusSm),
                      border: Border.all(color: navy.lineSubtle),
                    ),
                    child: Text(
                      '${fact.key}: ${fact.value}',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: navy.textSecondary,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                )
                .toList(growable: false),
          ),
        ],
      ),
    );
  }

  String _formatFactValue(String key, Object? value) {
    if (value == null) {
      return '';
    }
    if (key == 'verified_price_gtex' || key == 'verifiedPriceGtex') {
      return formatVerifiedPriceGtex(value) ?? value.toString().trim();
    }
    return value.toString().trim();
  }
}

class _LiveTransferTicker extends StatelessWidget {
  const _LiveTransferTicker({required this.articles});

  final List<GtexGroundedNewsArticle> articles;

  @override
  Widget build(BuildContext context) {
    final List<GtexGroundedNewsArticle> tickerItems = articles
        .where(
          (GtexGroundedNewsArticle article) =>
              !article.isRetracted &&
              (article.category == GtexNewsCategory.transfers ||
                  article.category == GtexNewsCategory.market ||
                  article.isBreaking),
        )
        .take(6)
        .toList(growable: false);
    return GtexPanel(
      title: 'Live transfer ticker',
      subtitle:
          tickerItems.isEmpty
              ? 'No backend transfer ticker items are live yet.'
              : 'Backend-published market movement and breaking stories.',
      accent: GtexColors.pitch,
      child:
          tickerItems.isEmpty
              ? Text(
                'The ticker stays empty until live transfer or market stories arrive from the story feed.',
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: GtexColors.textMuted),
              )
              : Wrap(
                spacing: GtexSpacing.sm,
                runSpacing: GtexSpacing.sm,
                children: tickerItems
                    .map(
                      (GtexGroundedNewsArticle item) => GtexStatusChip(
                        label: item.title,
                        color: newsCategoryColor(item.category),
                        icon: Icons.trending_up_outlined,
                      ),
                    )
                    .toList(growable: false),
              ),
    );
  }
}

class _NewsRightRail extends StatelessWidget {
  const _NewsRightRail({required this.article, required this.articles});

  final GtexGroundedNewsArticle article;
  final List<GtexGroundedNewsArticle> articles;

  @override
  Widget build(BuildContext context) {
    final bool hasRelatedRoute = article.relatedRoute != null;
    final bool hasShareUrl = article.shareUrl != null;
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        GtexPanel(
          title: 'Story actions',
          subtitle:
              'Actions appear only when story metadata provides a live target.',
          accent: newsCategoryColor(article.category),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              if (hasRelatedRoute)
                GtexActionButton(
                  label: 'Open related object',
                  icon: Icons.open_in_new_outlined,
                  accent: newsCategoryColor(article.category),
                  onPressed: () => context.go(article.relatedRoute!),
                ),
              if (hasRelatedRoute && hasShareUrl)
                const SizedBox(height: GtexSpacing.sm),
              if (hasShareUrl)
                GtexActionButton(
                  label: 'Copy share link',
                  icon: Icons.ios_share_outlined,
                  accent: GtexColors.cyan,
                  secondary: true,
                  onPressed: () async {
                    await Clipboard.setData(
                      ClipboardData(text: article.shareUrl!),
                    );
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Story link copied')),
                      );
                    }
                  },
                ),
              if (!hasRelatedRoute && !hasShareUrl)
                _StoryActionStatus(
                  accent: newsCategoryColor(article.category),
                  relatedEntity: article.relatedEntity,
                ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Trending now',
          subtitle: 'Top platform events.',
          child: Column(
            children: <Widget>[
              for (final GtexGroundedNewsArticle item in articles.take(3))
                Padding(
                  padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
                  child: Row(
                    children: <Widget>[
                      Icon(
                        Icons.trending_up_outlined,
                        color: newsCategoryColor(item.category),
                        size: 18,
                      ),
                      const SizedBox(width: GtexSpacing.xs),
                      Expanded(
                        child: Text(
                          item.title,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.bodySmall
                              ?.copyWith(color: GtexColors.textSecondary),
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _StoryActionStatus extends StatelessWidget {
  const _StoryActionStatus({required this.accent, this.relatedEntity});

  final Color accent;
  final String? relatedEntity;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(GtexSpacing.md),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
        border: Border.all(color: accent.withValues(alpha: 0.28)),
      ),
      child: Row(
        children: <Widget>[
          Icon(Icons.link_off_outlined, color: accent),
          const SizedBox(width: GtexSpacing.sm),
          Expanded(
            child: Text(
              relatedEntity == null
                  ? 'This story has no live route metadata yet.'
                  : 'Related entity: $relatedEntity',
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: GtexColors.textMuted),
            ),
          ),
        ],
      ),
    );
  }
}
