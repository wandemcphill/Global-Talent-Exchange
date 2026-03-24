import 'package:flutter/material.dart';
import 'package:gte_frontend/models/match/gtex_broadcast_hud_state.dart';
import 'package:gte_frontend/models/match_view_state.dart';

class GtexScoreboardOverlay extends StatelessWidget {
  const GtexScoreboardOverlay({
    super.key,
    required this.viewState,
    required this.hudState,
  });

  final MatchViewState viewState;
  final GtexBroadcastHudState hudState;

  @override
  Widget build(BuildContext context) {
    final bool compact = MediaQuery.sizeOf(context).width < 380;
    final double edgePadding = compact ? 10 : 14;
    final double sectionGap = compact ? 8 : 12;
    return Align(
      alignment: Alignment.topCenter,
      child: Padding(
        padding: const EdgeInsets.only(top: 18),
        child: Container(
          constraints: const BoxConstraints(maxWidth: 420),
          padding: EdgeInsets.symmetric(horizontal: edgePadding, vertical: 12),
          decoration: BoxDecoration(
            color: const Color(0xE6111E2B),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: Colors.white.withValues(alpha: 0.14)),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.22),
                blurRadius: 20,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Row(
            children: <Widget>[
              _TeamCell(
                shortName: viewState.homeTeam.shortName,
                color: _parseColor(viewState.homeTeam.primaryColorHex),
                scoreLabel:
                    hudState.scoreMasked ? '--' : '${hudState.homeScore ?? 0}',
                alignEnd: false,
                compact: compact,
              ),
              Padding(
                padding: EdgeInsets.symmetric(horizontal: sectionGap),
                child: Text(
                  ':',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: Colors.white70,
                        fontWeight: FontWeight.w700,
                      ),
                ),
              ),
              _TeamCell(
                shortName: viewState.awayTeam.shortName,
                color: _parseColor(viewState.awayTeam.primaryColorHex),
                scoreLabel:
                    hudState.scoreMasked ? '--' : '${hudState.awayScore ?? 0}',
                alignEnd: true,
                compact: compact,
              ),
              SizedBox(width: sectionGap),
              Container(
                width: 1,
                height: compact ? 20 : 24,
                color: Colors.white.withValues(alpha: 0.12),
              ),
              SizedBox(width: sectionGap),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  Text(
                    hudState.statusLabel,
                    style: (compact
                            ? Theme.of(context).textTheme.labelSmall
                            : Theme.of(context).textTheme.labelSmall)
                        ?.copyWith(
                      color: Colors.white70,
                      letterSpacing: compact ? 0.8 : 1.1,
                    ),
                  ),
                  Text(
                    hudState.clockLabel,
                    style: (compact
                            ? Theme.of(context).textTheme.titleSmall
                            : Theme.of(context).textTheme.titleMedium)
                        ?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _TeamCell extends StatelessWidget {
  const _TeamCell({
    required this.shortName,
    required this.color,
    required this.scoreLabel,
    required this.alignEnd,
    required this.compact,
  });

  final String shortName;
  final Color color;
  final String scoreLabel;
  final bool alignEnd;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final double gap = compact ? 6 : 8;
    return Expanded(
      child: Row(
        mainAxisAlignment:
            alignEnd ? MainAxisAlignment.end : MainAxisAlignment.start,
        children: <Widget>[
          if (!alignEnd) ...<Widget>[
            _Badge(color: color, compact: compact),
            SizedBox(width: gap),
          ],
          Flexible(
            child: Text(
              shortName,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: (compact
                      ? Theme.of(context).textTheme.labelMedium
                      : Theme.of(context).textTheme.labelLarge)
                  ?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          SizedBox(width: gap),
          Text(
            scoreLabel,
            style: (compact
                    ? Theme.of(context).textTheme.titleMedium
                    : Theme.of(context).textTheme.titleLarge)
                ?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w800,
            ),
          ),
          if (alignEnd) ...<Widget>[
            SizedBox(width: gap),
            _Badge(color: color, compact: compact),
          ],
        ],
      ),
    );
  }
}

class _Badge extends StatelessWidget {
  const _Badge({required this.color, required this.compact});

  final Color color;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: compact ? 18 : 22,
      height: compact ? 18 : 22,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        border: Border.all(color: Colors.white.withValues(alpha: 0.26)),
      ),
    );
  }
}

Color _parseColor(String value) {
  final String normalized = value.replaceAll('#', '').trim();
  final String hex = normalized.length == 6 ? 'FF$normalized' : normalized;
  return Color(int.tryParse(hex, radix: 16) ?? 0xFFFFFFFF);
}
