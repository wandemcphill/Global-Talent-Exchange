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
    return Align(
      alignment: Alignment.topCenter,
      child: Padding(
        padding: const EdgeInsets.only(top: 18),
        child: Container(
          constraints: const BoxConstraints(maxWidth: 420),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
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
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
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
              ),
              const SizedBox(width: 12),
              Container(
                width: 1,
                height: 24,
                color: Colors.white.withValues(alpha: 0.12),
              ),
              const SizedBox(width: 12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  Text(
                    hudState.statusLabel,
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: Colors.white70,
                          letterSpacing: 1.1,
                        ),
                  ),
                  Text(
                    hudState.clockLabel,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
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
  });

  final String shortName;
  final Color color;
  final String scoreLabel;
  final bool alignEnd;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Row(
        mainAxisAlignment:
            alignEnd ? MainAxisAlignment.end : MainAxisAlignment.start,
        children: <Widget>[
          if (!alignEnd) ...<Widget>[
            _Badge(color: color),
            const SizedBox(width: 8),
          ],
          Text(
            shortName,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(width: 8),
          Text(
            scoreLabel,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                ),
          ),
          if (alignEnd) ...<Widget>[
            const SizedBox(width: 8),
            _Badge(color: color),
          ],
        ],
      ),
    );
  }
}

class _Badge extends StatelessWidget {
  const _Badge({required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 22,
      height: 22,
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
