import 'package:flutter/material.dart';

import '../constants/app_spacing.dart';
import '../services/feedback_service.dart';
import '../theme/app_colors.dart';
import '../utils/app_formatters.dart';
import '../../models/player_avatar.dart';
import '../../widgets/player_card_avatar.dart';
import 'badge_icon.dart';
import 'gtex_surface_card.dart';

enum PlayerCardLayout { compact, horizontal }

class PlayerCardMetric {
  const PlayerCardMetric({required this.label, required this.value});

  final String label;
  final String value;
}

class PlayerCard extends StatefulWidget {
  const PlayerCard({
    super.key,
    required this.name,
    this.rating = 0,
    this.image = '',
    this.playerAvatar,
    this.position,
    this.country,
    this.subtitle,
    this.valueInMillions,
    this.heroTag,
    this.highlighted = false,
    this.onTap,
    this.trailing,
    this.avatarSize = 60,
    this.layout = PlayerCardLayout.compact,
    this.showRating = true,
    this.accentColor,
    this.badgeLabels = const <String>[],
    this.metrics = const <PlayerCardMetric>[],
    this.footer,
    this.actions = const <Widget>[],
  });

  final String name;
  final int rating;
  final String image;
  final PlayerAvatar? playerAvatar;
  final String? position;
  final String? country;
  final String? subtitle;
  final double? valueInMillions;
  final String? heroTag;
  final bool highlighted;
  final VoidCallback? onTap;
  final Widget? trailing;
  final double avatarSize;
  final PlayerCardLayout layout;
  final bool showRating;
  final Color? accentColor;
  final List<String> badgeLabels;
  final List<PlayerCardMetric> metrics;
  final Widget? footer;
  final List<Widget> actions;

  @override
  State<PlayerCard> createState() => _PlayerCardState();
}

class _PlayerCardState extends State<PlayerCard> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final Widget avatar = PlayerCardAvatar(
      avatar: widget.playerAvatar,
      imageUrl: widget.image,
      size: widget.avatarSize,
    );

    final Color accent = widget.accentColor ?? AppColors.primary;
    final Widget card = GtexSurfaceCard(
      glowColor: widget.highlighted || _hovered ? accent : null,
      onTap:
          widget.onTap == null
              ? null
              : () async {
                await FeedbackService.tap();
                widget.onTap?.call();
              },
      child:
          widget.layout == PlayerCardLayout.horizontal
              ? _HorizontalPlayerCardContent(
                widget: widget,
                avatar: avatar,
                accent: accent,
              )
              : _CompactPlayerCardContent(
                widget: widget,
                avatar: avatar,
                accent: accent,
              ),
    );

    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: AnimatedScale(
        scale: _hovered ? 1.05 : 1,
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeOutCubic,
        child: card,
      ),
    );
  }
}

class _CompactPlayerCardContent extends StatelessWidget {
  const _CompactPlayerCardContent({
    required this.widget,
    required this.avatar,
    required this.accent,
  });

  final PlayerCard widget;
  final Widget avatar;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            if (widget.heroTag case final String heroTag)
              Hero(tag: heroTag, child: avatar)
            else
              avatar,
            const Spacer(),
            if (widget.highlighted) const BadgeIcon.fire(),
            if (widget.trailing != null) widget.trailing!,
          ],
        ),
        const SizedBox(height: spacingSM),
        _PlayerCardName(name: widget.name, maxLines: 1, onTap: widget.onTap),
        if (_subtitleFor(widget) case final String subtitle) ...<Widget>[
          const SizedBox(height: spacingXS),
          _PlayerCardSubtitle(subtitle: subtitle),
        ],
        const SizedBox(height: spacingSM),
        Row(
          children: <Widget>[
            if (widget.showRating) ...<Widget>[
              Text(
                '${widget.rating}',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color: accent,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(width: spacingSM),
            ],
            Expanded(
              child: Text(
                widget.valueInMillions == null
                    ? 'Overall rating'
                    : AppFormatters.money(widget.valueInMillions!),
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ),
          ],
        ),
        if (widget.metrics.isNotEmpty) ...<Widget>[
          const SizedBox(height: spacingSM),
          _PlayerCardMetrics(metrics: widget.metrics),
        ],
        if (widget.footer != null) ...<Widget>[
          const SizedBox(height: spacingMD),
          widget.footer!,
        ],
        if (widget.actions.isNotEmpty) ...<Widget>[
          const SizedBox(height: spacingMD),
          Wrap(
            spacing: spacingSM,
            runSpacing: spacingSM,
            children: widget.actions,
          ),
        ],
      ],
    );
  }
}

class _HorizontalPlayerCardContent extends StatelessWidget {
  const _HorizontalPlayerCardContent({
    required this.widget,
    required this.avatar,
    required this.accent,
  });

  final PlayerCard widget;
  final Widget avatar;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final Widget resolvedAvatar =
        widget.heroTag == null
            ? avatar
            : Hero(tag: widget.heroTag!, child: avatar);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            SizedBox(
              width: widget.avatarSize + 12,
              child: Column(
                children: <Widget>[
                  resolvedAvatar,
                  if (widget.badgeLabels.isNotEmpty) ...<Widget>[
                    const SizedBox(height: spacingSM),
                    Wrap(
                      alignment: WrapAlignment.center,
                      spacing: spacingXS,
                      runSpacing: spacingXS,
                      children: widget.badgeLabels
                          .map((String label) => _PlayerCardBadge(label: label))
                          .toList(growable: false),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(width: spacingMD),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      if (widget.showRating) ...<Widget>[
                        _PlayerCardRatingBox(
                          rating: widget.rating,
                          accent: accent,
                        ),
                        const SizedBox(width: spacingSM),
                      ],
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            _PlayerCardName(
                              name: widget.name,
                              maxLines: 2,
                              onTap: widget.onTap,
                            ),
                            if (_subtitleFor(widget)
                                case final String subtitle) ...<Widget>[
                              const SizedBox(height: spacingXS),
                              _PlayerCardSubtitle(subtitle: subtitle),
                            ],
                          ],
                        ),
                      ),
                      if (widget.trailing != null) ...<Widget>[
                        const SizedBox(width: spacingSM),
                        widget.trailing!,
                      ],
                    ],
                  ),
                  if (widget.metrics.isNotEmpty) ...<Widget>[
                    const SizedBox(height: spacingMD),
                    _PlayerCardMetrics(metrics: widget.metrics),
                  ],
                ],
              ),
            ),
          ],
        ),
        if (widget.footer != null) ...<Widget>[
          const SizedBox(height: spacingMD),
          widget.footer!,
        ],
        if (widget.actions.isNotEmpty) ...<Widget>[
          const SizedBox(height: spacingMD),
          Wrap(
            spacing: spacingSM,
            runSpacing: spacingSM,
            children: widget.actions,
          ),
        ],
      ],
    );
  }
}

class _PlayerCardName extends StatelessWidget {
  const _PlayerCardName({
    required this.name,
    required this.maxLines,
    this.onTap,
  });

  final String name;
  final int maxLines;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final Widget label = Text(
      name,
      style: Theme.of(
        context,
      ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
      maxLines: maxLines,
      overflow: TextOverflow.ellipsis,
    );
    if (onTap == null) {
      return label;
    }
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: label,
    );
  }
}

class _PlayerCardSubtitle extends StatelessWidget {
  const _PlayerCardSubtitle({required this.subtitle});

  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Text(
      subtitle,
      style: Theme.of(context).textTheme.bodySmall,
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
    );
  }
}

class _PlayerCardRatingBox extends StatelessWidget {
  const _PlayerCardRatingBox({required this.rating, required this.accent});

  final int rating;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final ColorScheme colorScheme = Theme.of(context).colorScheme;
    return Container(
      width: 54,
      padding: const EdgeInsets.symmetric(vertical: spacingSM),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        color: accent,
      ),
      child: Column(
        children: <Widget>[
          Text(
            rating.toString(),
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
              color: colorScheme.onPrimary,
              fontWeight: FontWeight.w800,
            ),
          ),
          Text(
            'OVR',
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: colorScheme.onPrimary.withValues(alpha: 0.78),
            ),
          ),
        ],
      ),
    );
  }
}

class _PlayerCardBadge extends StatelessWidget {
  const _PlayerCardBadge({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: spacingSM, vertical: 4),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(6),
        color: Theme.of(context).colorScheme.secondaryContainer,
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
          color: Theme.of(context).colorScheme.onSecondaryContainer,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _PlayerCardMetrics extends StatelessWidget {
  const _PlayerCardMetrics({required this.metrics});

  final List<PlayerCardMetric> metrics;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: spacingSM,
      runSpacing: spacingSM,
      children: metrics
          .map(
            (PlayerCardMetric metric) => Container(
              padding: const EdgeInsets.symmetric(
                horizontal: spacingSM,
                vertical: 7,
              ),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(6),
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
              ),
              child: RichText(
                text: TextSpan(
                  style: Theme.of(context).textTheme.labelMedium,
                  children: <TextSpan>[
                    TextSpan(text: '${metric.label} '),
                    TextSpan(
                      text: metric.value,
                      style: const TextStyle(fontWeight: FontWeight.w800),
                    ),
                  ],
                ),
              ),
            ),
          )
          .toList(growable: false),
    );
  }
}

String? _subtitleFor(PlayerCard widget) {
  if (widget.subtitle != null && widget.subtitle!.trim().isNotEmpty) {
    return widget.subtitle!.trim();
  }
  final String composed = <String>[
    if (widget.position != null && widget.position!.trim().isNotEmpty)
      widget.position!.trim(),
    if (widget.country != null && widget.country!.trim().isNotEmpty)
      widget.country!.trim(),
  ].join(' / ');
  return composed.isEmpty ? null : composed;
}
