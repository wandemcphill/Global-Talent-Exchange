import 'package:flutter/material.dart';

class CommentaryRibbonWidget extends StatelessWidget {
  const CommentaryRibbonWidget({
    super.key,
    required this.headline,
    required this.detail,
    this.trailing,
  });

  final String headline;
  final String detail;
  final String? trailing;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      key: const Key('commentary-ribbon'),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        gradient: const LinearGradient(
          begin: Alignment.centerLeft,
          end: Alignment.centerRight,
          colors: <Color>[Color(0xEE0A1016), Color(0xEE132131)],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(
          children: <Widget>[
            Container(
              width: 6,
              height: 44,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(999),
                color: const Color(0xFFF97316),
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
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
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
                      height: 1.3,
                    ),
                  ),
                ],
              ),
            ),
            if (trailing != null && trailing!.trim().isNotEmpty) ...<Widget>[
              const SizedBox(width: 12),
              Text(
                trailing!,
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: const Color(0xFFFDB022),
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
