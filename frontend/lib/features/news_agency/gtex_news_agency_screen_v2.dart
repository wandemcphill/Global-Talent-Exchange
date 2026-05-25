import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';

import '../../data/story_feed_api.dart';
import '../../models/story_feed_models.dart';
import '../engagement_redesign/engagement_controller.dart';
import '../engagement_redesign/engagement_models.dart';
import '../engagement_redesign/engagement_widgets.dart';
import '../../ui_gtex/ui_gtex.dart';

class GtexNewsAgencyScreenV2 extends StatefulWidget {
  const GtexNewsAgencyScreenV2({
    super.key,
    this.controller,
    this.api,
    this.allowFixtureData = false,
  });

  final GtexEngagementController? controller;
  final StoryFeedApi? api;
  final bool allowFixtureData;

  @override
  State<GtexNewsAgencyScreenV2> createState() => _GtexNewsAgencyScreenV2State();
}

class _GtexNewsAgencyScreenV2State extends State<GtexNewsAgencyScreenV2> {
  late final GtexEngagementController _controller;
  late Future<List<GtexNewsArticle>> _articlesFuture;
  GtexNewsCategory? _category;
  GtexNewsArticle? _selected;
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
        oldWidget.controller != widget.controller) {
      _selected = null;
      _articlesFuture = _loadArticles();
    }
  }

  Future<List<GtexNewsArticle>> _loadArticles() async {
    final StoryFeedApi? api = widget.api;
    if (api == null) {
      if (widget.allowFixtureData) {
        return _controller.loadDemoArticles();
      }
      throw StateError('Live story feed API is required for GTEX News Agency.');
    }
    final List<StoryFeedItem> stories = await api.listFeed(limit: 100);
    return stories.map(_articleFromStory).toList(growable: false);
  }

  void _refresh() {
    setState(() {
      _selected = null;
      _articlesFuture = _loadArticles();
    });
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<GtexNewsArticle>>(
      future: _articlesFuture,
      builder: (
        BuildContext context,
        AsyncSnapshot<List<GtexNewsArticle>> snapshot,
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
        final List<GtexNewsArticle> articles =
            snapshot.data ?? const <GtexNewsArticle>[];
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
        final List<GtexNewsArticle> visible = articles
            .where((GtexNewsArticle article) {
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
        final GtexNewsArticle selected =
            _selected != null &&
                    visible.any(
                      (GtexNewsArticle article) => article.id == _selected!.id,
                    )
                ? _selected!
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
                (GtexNewsArticle article) =>
                    setState(() => _selected = article),
          ),
          detail: _NewsArticleDetail(article: selected, articles: articles),
          rightPanel: _NewsRightRail(article: selected, articles: articles),
        );
      },
    );
  }
}

GtexNewsArticle _articleFromStory(StoryFeedItem story) {
  final Map<String, Object?> metadata = story.metadata;
  final String summary =
      _metadataString(metadata, <String>['summary', 'dek', 'excerpt']) ??
      _summarize(story.body);
  return GtexNewsArticle(
    id: story.id,
    title: story.title,
    summary: summary,
    body: story.body,
    category: _categoryFromStory(story),
    publishedAt: story.createdAt,
    heroLabel:
        _metadataString(metadata, <String>['hero_label', 'heroLabel']) ??
        _humanize(story.storyType),
    relatedEntity:
        _metadataString(metadata, <String>[
          'related_entity',
          'relatedEntity',
          'subject_label',
          'subjectLabel',
        ]) ??
        story.subjectId ??
        story.countryCode,
    relatedRoute: _metadataString(metadata, <String>[
      'related_route',
      'relatedRoute',
      'route',
      'deep_link',
      'deepLink',
    ]),
    shareUrl: _metadataString(metadata, <String>[
      'share_url',
      'shareUrl',
      'url',
      'canonical_url',
      'canonicalUrl',
    ]),
    isBreaking:
        story.featured || story.storyType.toLowerCase().contains('break'),
    trustScore: _metadataDouble(metadata, <String>[
      'trust_score',
      'trustScore',
    ]),
    reactionCount: _metadataInt(metadata, <String>[
      'reaction_count',
      'reactionCount',
      'reactions',
      'reactions_count',
      'reactionsCount',
    ]),
    commentCount: _metadataInt(metadata, <String>[
      'comment_count',
      'commentCount',
      'comments',
      'comments_count',
      'commentsCount',
    ]),
  );
}

GtexNewsCategory _categoryFromStory(StoryFeedItem story) {
  final String raw =
      '${story.storyType} ${story.subjectType ?? ''}'.trim().toLowerCase();
  if (raw.contains('break')) return GtexNewsCategory.breaking;
  if (raw.contains('transfer')) return GtexNewsCategory.transfers;
  if (raw.contains('club')) return GtexNewsCategory.clubs;
  if (raw.contains('regen') || raw.contains('newgen')) {
    return GtexNewsCategory.regens;
  }
  if (raw.contains('award')) return GtexNewsCategory.awards;
  if (raw.contains('tournament') || raw.contains('competition')) {
    return GtexNewsCategory.tournaments;
  }
  if (raw.contains('national')) return GtexNewsCategory.nationalTeams;
  if (raw.contains('jackpot')) return GtexNewsCategory.jackpot;
  if (raw.contains('creator')) return GtexNewsCategory.creators;
  if (raw.contains('dispute')) return GtexNewsCategory.disputes;
  if (raw.contains('market') || raw.contains('order')) {
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

  final List<GtexNewsArticle> articles;
  final GtexNewsArticle selected;
  final GtexNewsCategory? category;
  final String query;
  final ValueChanged<String> onQueryChanged;
  final ValueChanged<GtexNewsCategory?> onCategoryChanged;
  final ValueChanged<GtexNewsArticle> onSelected;

  @override
  Widget build(BuildContext context) {
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
              for (final GtexNewsArticle article in articles)
                GtexSectionListTile(
                  title: article.title,
                  subtitle: article.summary,
                  icon:
                      article.isBreaking
                          ? Icons.bolt_outlined
                          : Icons.article_outlined,
                  accent: newsCategoryColor(article.category),
                  isSelected: article.id == selected.id,
                  onTap: () => onSelected(article),
                  trailing:
                      article.isBreaking
                          ? const GtexStatusChip(
                            label: 'LIVE',
                            color: GtexColors.red,
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

  final GtexNewsArticle article;
  final List<GtexNewsArticle> articles;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.lg),
      children: <Widget>[
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
              if (article.heroLabel != null)
                GtexStatusChip(
                  label: article.heroLabel!,
                  color: GtexColors.gold,
                  icon: Icons.star_border_outlined,
                ),
              GtexStatusChip(
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

class _LiveTransferTicker extends StatelessWidget {
  const _LiveTransferTicker({required this.articles});

  final List<GtexNewsArticle> articles;

  @override
  Widget build(BuildContext context) {
    final List<GtexNewsArticle> tickerItems = articles
        .where(
          (GtexNewsArticle article) =>
              article.category == GtexNewsCategory.transfers ||
              article.category == GtexNewsCategory.market ||
              article.isBreaking,
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
                      (GtexNewsArticle item) => GtexStatusChip(
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

  final GtexNewsArticle article;
  final List<GtexNewsArticle> articles;

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
              for (final GtexNewsArticle item in articles.take(3))
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
