import 'package:flutter/material.dart';

import 'package:gte_frontend/features/match_center/models/real_match_engine_presentation.dart';

class MatchMomentBannerWidget extends StatelessWidget {
  const MatchMomentBannerWidget({super.key, required this.banner});

  final MatchEngineBanner banner;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      key: const Key('match-moment-banner'),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: const Color(0xE40A131B),
        border: Border.all(color: banner.accentColor.withValues(alpha: 0.55)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: banner.accentColor.withValues(alpha: 0.18),
            blurRadius: 18,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(banner.icon, color: banner.accentColor),
            const SizedBox(width: 10),
            Flexible(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  Text(
                    banner.label,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    banner.detail,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(
                      context,
                    ).textTheme.bodySmall?.copyWith(color: Colors.white70),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
