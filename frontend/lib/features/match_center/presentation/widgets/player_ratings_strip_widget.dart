import 'package:flutter/material.dart';

import 'package:gte_frontend/features/match_center/models/match_event.dart';
import '../broadcast_package_models.dart';

enum MatchRailShortcut { tactics, subs, shape, setPiece, timeline }

extension MatchRailShortcutX on MatchRailShortcut {
  String get label {
    return switch (this) {
      MatchRailShortcut.tactics => 'Tactics',
      MatchRailShortcut.subs => 'Subs',
      MatchRailShortcut.shape => 'Shape',
      MatchRailShortcut.setPiece => 'Set-piece',
      MatchRailShortcut.timeline => 'Replay timeline',
    };
  }

  IconData get icon {
    return switch (this) {
      MatchRailShortcut.tactics => Icons.tune_rounded,
      MatchRailShortcut.subs => Icons.swap_horiz_rounded,
      MatchRailShortcut.shape => Icons.grid_view_rounded,
      MatchRailShortcut.setPiece => Icons.adjust_rounded,
      MatchRailShortcut.timeline => Icons.timeline_rounded,
    };
  }
}

class PlayerRatingsStripWidget extends StatelessWidget {
  const PlayerRatingsStripWidget({
    super.key,
    required this.players,
    this.homeTeam,
    this.awayTeam,
    this.events = const <MatchEvent>[],
    this.activeEventId,
    this.phaseLabel,
    this.activeShortcut,
    this.onShortcutSelected,
  });

  final List<MatchPresentationPlayer> players;
  final MatchPresentationTeam? homeTeam;
  final MatchPresentationTeam? awayTeam;
  final List<MatchEvent> events;
  final String? activeEventId;
  final String? phaseLabel;
  final MatchRailShortcut? activeShortcut;
  final ValueChanged<MatchRailShortcut>? onShortcutSelected;

  @override
  Widget build(BuildContext context) {
    final bool hasRatings = players.isNotEmpty;
    final bool hasRecap = events.isNotEmpty;
    final bool hasShortcuts = onShortcutSelected != null;
    final bool hasFormSummary =
        homeTeam?.recentForm != null || awayTeam?.recentForm != null;
    if (!hasRatings && !hasRecap && !hasShortcuts && !hasFormSummary) {
      return const SizedBox.shrink();
    }

    final List<MatchEvent> recapEvents = events
        .where(
          (MatchEvent event) =>
              event.type != MatchViewerEventType.neutral &&
              event.type != MatchViewerEventType.attack,
        )
        .take(8)
        .toList(growable: false);

    return DecoratedBox(
      key: const Key('player-ratings-strip'),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        color: const Color(0xE1091018),
        border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              children: <Widget>[
                Expanded(
                  child: Text(
                    'Bottom match rail',
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
                if (phaseLabel != null && phaseLabel!.trim().isNotEmpty)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 7,
                    ),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(999),
                      color: const Color(0x1FFDB022),
                      border: Border.all(color: const Color(0x55FDB022)),
                    ),
                    child: Text(
                      phaseLabel!,
                      style: Theme.of(context).textTheme.labelMedium?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
              ],
            ),
            if (hasFormSummary) ...<Widget>[
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: <Widget>[
                  if (homeTeam?.recentForm != null)
                    _RailMetaChip(
                      label:
                          '${homeTeam!.shortName} form ${homeTeam!.recentForm}',
                      accent: _teamAccent(homeTeam!, const Color(0xFF22C55E)),
                    ),
                  if (awayTeam?.recentForm != null)
                    _RailMetaChip(
                      label:
                          '${awayTeam!.shortName} form ${awayTeam!.recentForm}',
                      accent: _teamAccent(awayTeam!, const Color(0xFFF97316)),
                    ),
                ],
              ),
            ],
            if (hasRatings) ...<Widget>[
              const SizedBox(height: 12),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: players
                      .map(
                        (MatchPresentationPlayer player) => Padding(
                          padding: const EdgeInsets.only(right: 8),
                          child: _PlayerRatingPill(
                            player: player,
                            accent: _playerAccent(player),
                          ),
                        ),
                      )
                      .toList(growable: false),
                ),
              ),
            ],
            if (hasShortcuts) ...<Widget>[
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: MatchRailShortcut.values
                    .map(
                      (MatchRailShortcut shortcut) => ChoiceChip(
                        avatar: Icon(
                          shortcut.icon,
                          size: 16,
                          color:
                              activeShortcut == shortcut
                                  ? Colors.white
                                  : Colors.white70,
                        ),
                        label: Text(shortcut.label),
                        selected: activeShortcut == shortcut,
                        onSelected: (_) => onShortcutSelected!(shortcut),
                        selectedColor: const Color(0x3322C55E),
                        backgroundColor: Colors.white.withValues(alpha: 0.04),
                        labelStyle: Theme.of(
                          context,
                        ).textTheme.labelMedium?.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    )
                    .toList(growable: false),
              ),
            ],
            if (hasRecap && recapEvents.isNotEmpty) ...<Widget>[
              const SizedBox(height: 12),
              Text(
                'Event recap',
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: Colors.white70,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 8),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: recapEvents
                      .map(
                        (MatchEvent event) => Padding(
                          padding: const EdgeInsets.only(right: 8),
                          child: _EventMarker(
                            event: event,
                            isActive: event.id == activeEventId,
                          ),
                        ),
                      )
                      .toList(growable: false),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Color _playerAccent(MatchPresentationPlayer player) {
    if (homeTeam != null && _teamContainsPlayer(homeTeam!, player)) {
      return _teamAccent(homeTeam!, const Color(0xFF22C55E));
    }
    if (awayTeam != null && _teamContainsPlayer(awayTeam!, player)) {
      return _teamAccent(awayTeam!, const Color(0xFFF97316));
    }
    return const Color(0xFF53B1FD);
  }

  bool _teamContainsPlayer(
    MatchPresentationTeam team,
    MatchPresentationPlayer player,
  ) {
    final String? playerId = player.playerId;
    if (playerId != null) {
      for (final MatchPresentationPlayer candidate in <MatchPresentationPlayer>[
        ...team.starters,
        ...team.bench,
      ]) {
        if (candidate.playerId == playerId) {
          return true;
        }
      }
    }
    return team.starters.any(
          (MatchPresentationPlayer candidate) =>
              candidate.playerName == player.playerName,
        ) ||
        team.bench.any(
          (MatchPresentationPlayer candidate) =>
              candidate.playerName == player.playerName,
        );
  }

  Color _teamAccent(MatchPresentationTeam team, Color fallback) {
    final String? raw = team.accentColorHex;
    if (raw == null || raw.trim().isEmpty) {
      return fallback;
    }
    String normalized = raw.trim().replaceFirst('#', '');
    if (normalized.length == 6) {
      normalized = 'FF$normalized';
    }
    final int? parsed = int.tryParse(normalized, radix: 16);
    return parsed == null ? fallback : Color(parsed);
  }
}

class _PlayerRatingPill extends StatelessWidget {
  const _PlayerRatingPill({required this.player, required this.accent});

  final MatchPresentationPlayer player;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final String role = _roleAbbreviation(player.role);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        color: Colors.white.withValues(alpha: 0.05),
        border: Border.all(color: accent.withValues(alpha: 0.24)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Container(
            width: 30,
            height: 30,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: accent.withValues(alpha: 0.18),
            ),
            alignment: Alignment.center,
            child: Text(
              role,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Text(
                player.playerName,
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                player.rating?.toStringAsFixed(1) ?? '--',
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: accent,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _EventMarker extends StatelessWidget {
  const _EventMarker({required this.event, required this.isActive});

  final MatchEvent event;
  final bool isActive;

  @override
  Widget build(BuildContext context) {
    final Color accent =
        isActive
            ? const Color(0xFFFDB022)
            : Colors.white.withValues(alpha: 0.24);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        color:
            isActive
                ? const Color(0x26FDB022)
                : Colors.white.withValues(alpha: 0.04),
        border: Border.all(color: accent),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(event.icon, size: 16, color: isActive ? accent : Colors.white70),
          const SizedBox(width: 8),
          Text(
            '${event.clockLabel} ${event.bannerText}',
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _RailMetaChip extends StatelessWidget {
  const _RailMetaChip({required this.label, required this.accent});

  final String label;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: accent.withValues(alpha: 0.14),
        border: Border.all(color: accent.withValues(alpha: 0.30)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
          color: Colors.white,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

String _roleAbbreviation(String? role) {
  final String normalized = role?.trim().toLowerCase() ?? '';
  return switch (normalized) {
    'goalkeeper' => 'GK',
    'defender' => 'DF',
    'midfielder' => 'MF',
    'forward' => 'FW',
    _ => 'PL',
  };
}
