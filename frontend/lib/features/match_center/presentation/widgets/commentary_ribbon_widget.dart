import 'package:flutter/material.dart';

class CommentaryRibbonWidget extends StatelessWidget {
  const CommentaryRibbonWidget({
    super.key,
    required this.headline,
    required this.detail,
    this.trailing,
    this.label,
    this.accentColor = const Color(0xFFF97316),
  });

  final String headline;
  final String detail;
  final String? trailing;
  final String? label;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    final bool showMetaRow =
        (label != null && label!.trim().isNotEmpty) ||
        (trailing != null && trailing!.trim().isNotEmpty);
    return DecoratedBox(
      key: const Key('commentary-ribbon'),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        gradient: const LinearGradient(
          begin: Alignment.centerLeft,
          end: Alignment.centerRight,
          colors: <Color>[Color(0xF10A1116), Color(0xEF122030)],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.18),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            if (showMetaRow) ...<Widget>[
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: <Widget>[
                  if (label != null && label!.trim().isNotEmpty)
                    _RibbonMetaChip(label: label!, accentColor: accentColor),
                  if (trailing != null && trailing!.trim().isNotEmpty)
                    _RibbonMetaChip(
                      label: trailing!,
                      accentColor: const Color(0xFFFDB022),
                    ),
                ],
              ),
              const SizedBox(height: 10),
            ],
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Container(
                  width: 6,
                  height: 48,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(999),
                    color: accentColor,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      Text(
                        headline,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(
                          context,
                        ).textTheme.titleMedium?.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        detail,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.white70,
                          height: 1.32,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _RibbonMetaChip extends StatelessWidget {
  const _RibbonMetaChip({required this.label, required this.accentColor});

  final String label;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: accentColor.withValues(alpha: 0.16),
        border: Border.all(color: accentColor.withValues(alpha: 0.32)),
      ),
      child: Text(
        label,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
          color: Colors.white,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.4,
        ),
      ),
    );
  }
}
