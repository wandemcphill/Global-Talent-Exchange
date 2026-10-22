import 'package:flutter/material.dart';

import '../../player_detail/gtex_player_navigator.dart';
import '../../match/widgets/gtex_matchday_ad_slot.dart';
import '../data/gtex_match_models.dart';
import 'gtex_match_visual_tokens.dart';

class GtexMatchLineups extends StatelessWidget {
  const GtexMatchLineups({super.key, required this.home, required this.away});

  final GtexMatchTeam home;
  final GtexMatchTeam away;

  @override
  Widget build(BuildContext context) {
    if (home.players.isEmpty && away.players.isEmpty) {
      return const GtexMatchEmptyFeed(
        icon: Icons.format_list_numbered_rtl_rounded,
        title: 'Lineups unavailable',
        message:
            'The match authority has not supplied player lineups for this fixture.',
      );
    }

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _LineupTeam(team: home),
        const SizedBox(height: 14),
        _LineupTeam(team: away),
        const SizedBox(height: 14),
        const GtexMatchdayAdSlot(
          placement: 'Official team-sheet bulletin',
          compact: true,
        ),
      ],
    );
  }
}

class _LineupTeam extends StatelessWidget {
  const _LineupTeam({required this.team});

  final GtexMatchTeam team;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: GtexMatchVisualTokens.panelDecoration(
        background: GtexMatchVisualTokens.surfaceOverlay,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 4,
                height: 28,
                decoration: BoxDecoration(
                  color: team.primaryColor ?? GtexMatchVisualTokens.live,
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      team.name,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: GtexMatchVisualTokens.textPrimary,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      team.formation.toUpperCase(),
                      style: GtexMatchVisualTokens.labelStyle,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 7,
            runSpacing: 7,
            children: <Widget>[
              if (team.managerName?.trim().isNotEmpty == true)
                _MicroTag(
                  label: 'MANAGER · ${team.managerName!.trim()}',
                  color: GtexMatchVisualTokens.amber,
                ),
              if (team.recentFormPercent != null)
                _MicroTag(
                  label: 'FORM · ${team.recentFormPercent}%',
                  color: GtexMatchVisualTokens.live,
                ),
              if (team.mentality?.trim().isNotEmpty == true)
                _MicroTag(
                  label: team.mentality!.replaceAll('_', ' '),
                  color: GtexMatchVisualTokens.blue,
                ),
              for (final String instruction in team.instructionSummary.take(2))
                _MicroTag(
                  label: instruction,
                  color: GtexMatchVisualTokens.textSecondary,
                ),
            ],
          ),
          const SizedBox(height: 12),
          if (team.players.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 8),
              child: Text(
                'No lineup records returned for this club.',
                style: TextStyle(color: GtexMatchVisualTokens.textSecondary),
              ),
            )
          else
            for (final GtexLineupPlayer player in team.players)
              // A lineup name was dead text: the match knew exactly which
              // footballer it was and there was no way to go and look at
              // them. It now opens the same canonical player detail as the
              // market and the portfolio.
              _OpenLineupPlayer(
                player: player,
                child: Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    color: GtexMatchVisualTokens.surfaceRaised,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: GtexMatchVisualTokens.border),
                  ),
                  child: Row(
                    children: [
                      SizedBox(
                        width: 34,
                        child: Text(
                          '#${player.shirtNumber}',
                          style: const TextStyle(
                            color: GtexMatchVisualTokens.live,
                            fontFamily: 'JetBrains Mono',
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Row(
                              children: <Widget>[
                                Expanded(
                                  child: Text(
                                    player.name,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                      color: GtexMatchVisualTokens.textPrimary,
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                ),
                                if (player.isRegen) ...<Widget>[
                                  const SizedBox(width: 6),
                                  const _MicroTag(
                                    label: 'REGEN',
                                    color: GtexMatchVisualTokens.regen,
                                  ),
                                ],
                              ],
                            ),
                            const SizedBox(height: 5),
                            Wrap(
                              spacing: 5,
                              runSpacing: 4,
                              children: <Widget>[
                                _MicroTag(
                                  label: player.position,
                                  color: GtexMatchVisualTokens.textSecondary,
                                ),
                                if (player.formLabel?.trim().isNotEmpty == true)
                                  _MicroTag(
                                    label: player.formLabel!.trim(),
                                    color: GtexMatchVisualTokens.amber,
                                  ),
                                if (player.fitnessPct != null)
                                  _MicroTag(
                                    label: 'FIT ${player.fitnessPct!.round()}%',
                                    color: GtexMatchVisualTokens.live,
                                  ),
                              ],
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        player.rating > 0
                            ? player.rating.toStringAsFixed(1)
                            : '--',
                        style: const TextStyle(
                          color: GtexMatchVisualTokens.textPrimary,
                          fontFamily: 'JetBrains Mono',
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
          if (team.bench.isNotEmpty) ...<Widget>[
            const SizedBox(height: 10),
            const Divider(color: GtexMatchVisualTokens.border),
            const SizedBox(height: 8),
            Row(
              children: <Widget>[
                const Icon(Icons.sync_alt_rounded, color: GtexMatchVisualTokens.amber, size: 16),
                const SizedBox(width: 8),
                const Expanded(
                  child: Text(
                    'SUBSTITUTES',
                    style: TextStyle(
                      color: GtexMatchVisualTokens.textPrimary,
                      fontWeight: FontWeight.w900,
                      fontSize: 11,
                      letterSpacing: .7,
                    ),
                  ),
                ),
                Text(
                  '${team.bench.length} listed',
                  style: const TextStyle(color: GtexMatchVisualTokens.textSecondary, fontSize: 11),
                ),
              ],
            ),
            const SizedBox(height: 7),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: team.bench.map((GtexLineupPlayer player) {
                return Container(
                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 7),
                  decoration: BoxDecoration(
                    color: GtexMatchVisualTokens.surfaceRaised,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: GtexMatchVisualTokens.border),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      Text(
                        '#${player.shirtNumber}',
                        style: const TextStyle(
                          color: GtexMatchVisualTokens.amber,
                          fontWeight: FontWeight.w900,
                          fontFamily: 'JetBrains Mono',
                          fontSize: 10,
                        ),
                      ),
                      const SizedBox(width: 5),
                      ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 150),
                        child: Text(
                          player.name,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: GtexMatchVisualTokens.textPrimary,
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      const SizedBox(width: 6),
                      _MicroTag(
                        label: player.position,
                        color: GtexMatchVisualTokens.textSecondary,
                      ),
                    ],
                  ),
                );
              }).toList(growable: false),
            ),
          ],
        ],
      ),
    );
  }
}

/// Wraps a lineup row so it opens the canonical player detail. The row is
/// only made tappable when the fixture actually carried a player id - the
/// repository falls back to the player's name when the feed omits one, and
/// a name is not something the profile can be looked up by.
class _OpenLineupPlayer extends StatelessWidget {
  const _OpenLineupPlayer({required this.player, required this.child});

  final GtexLineupPlayer player;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final bool hasRealId =
        player.id.trim().isNotEmpty && player.id.trim() != player.name.trim();
    final VoidCallback? onTap =
        hasRealId ? GtexPlayerNavigator.tapToOpen(context, player.id) : null;
    if (onTap == null) {
      return child;
    }
    return Semantics(
      button: true,
      label: 'Open ${player.name}',
      child: InkWell(
        key: Key('gtex-lineup-open-${player.id}'),
        borderRadius: BorderRadius.circular(6),
        onTap: onTap,
        child: child,
      ),
    );
  }
}

class _MicroTag extends StatelessWidget {
  const _MicroTag({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(.12),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withOpacity(.28)),
      ),
      child: Text(
        label.toUpperCase(),
        style: TextStyle(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.w900,
          letterSpacing: .5,
        ),
      ),
    );
  }
}

extension on GtexMatchTeam {
  Color? get primaryColor {
    final String? raw = primaryColorHex;
    if (raw == null || raw.trim().isEmpty) {
      return null;
    }
    final String normalized = raw.replaceFirst('#', '');
    final int? value = int.tryParse(normalized, radix: 16);
    if (value == null) {
      return null;
    }
    return Color(0xFF000000 | value);
  }
}
