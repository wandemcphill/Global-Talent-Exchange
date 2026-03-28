import 'package:flutter/material.dart';

import '../constants/app_spacing.dart';
import '../services/feedback_service.dart';
import '../theme/app_colors.dart';
import '../utils/app_formatters.dart';
import 'badge_icon.dart';
import 'gtex_surface_card.dart';

class PlayerCard extends StatefulWidget {
  const PlayerCard({
    super.key,
    required this.name,
    required this.rating,
    required this.image,
    this.position,
    this.country,
    this.valueInMillions,
    this.heroTag,
    this.highlighted = false,
    this.onTap,
    this.trailing,
  });

  final String name;
  final int rating;
  final String image;
  final String? position;
  final String? country;
  final double? valueInMillions;
  final String? heroTag;
  final bool highlighted;
  final VoidCallback? onTap;
  final Widget? trailing;

  @override
  State<PlayerCard> createState() => _PlayerCardState();
}

class _PlayerCardState extends State<PlayerCard> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final ImageProvider<Object>? imageProvider = _resolveImage(widget.image);
    final Widget avatar = CircleAvatar(
      radius: 30,
      backgroundColor: AppColors.background,
      backgroundImage: imageProvider,
      child: imageProvider == null
          ? Text(
              widget.name
                  .split(' ')
                  .where((String part) => part.isNotEmpty)
                  .take(2)
                  .map((String part) => part.substring(0, 1))
                  .join(),
              style: const TextStyle(
                color: AppColors.primary,
                fontWeight: FontWeight.w700,
              ),
            )
          : null,
    );

    final Widget card = GtexSurfaceCard(
      glowColor: widget.highlighted || _hovered ? AppColors.primary : null,
      onTap: widget.onTap == null
          ? null
          : () async {
              await FeedbackService.tap();
              widget.onTap?.call();
            },
      child: Column(
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
          Text(
            widget.name,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          if (widget.position != null || widget.country != null) ...<Widget>[
            const SizedBox(height: spacingXS),
            Text(
              <String>[
                if (widget.position != null) widget.position!,
                if (widget.country != null) widget.country!,
              ].join(' / '),
              style: Theme.of(context).textTheme.bodySmall,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
          const SizedBox(height: spacingSM),
          Row(
            children: <Widget>[
              Text(
                '${widget.rating}',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      color: AppColors.primary,
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const SizedBox(width: spacingSM),
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
        ],
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

  ImageProvider<Object>? _resolveImage(String source) {
    if (source.startsWith('http')) {
      return NetworkImage(source);
    }
    if (source.isNotEmpty) {
      return AssetImage(source);
    }
    return null;
  }
}
