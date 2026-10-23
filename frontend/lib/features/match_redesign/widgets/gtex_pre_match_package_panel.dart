import 'package:flutter/material.dart';

import '../data/gtex_match_models.dart';
import 'gtex_match_scoreboard.dart';
import 'gtex_match_visual_tokens.dart';

class GtexPreMatchPackagePanel extends StatefulWidget {
  const GtexPreMatchPackagePanel({
    super.key,
    required this.match,
    this.onEnterTactics,
  });

  final GtexLiveMatchState match;
  final VoidCallback? onEnterTactics;

  @override
  State<GtexPreMatchPackagePanel> createState() => _GtexPreMatchPackagePanelState();
}

class _GtexPreMatchPackagePanelState extends State<GtexPreMatchPackagePanel> {
  String? _userPrediction; // 'home', 'draw', 'away'
  bool _showBench = false;

  @override
  Widget build(BuildContext context) {
    final pre = widget.match.preMatch ??
        const GtexPreMatchPackage(
          homeForm: ['W', 'W', 'D', 'W', 'L'],
          awayForm: ['D', 'W', 'L', 'W', 'D'],
          homeWinRate: 65,
          awayWinRate: 52,
          h2hTotal: 6,
          h2hHomeWins: 3,
          h2hDraws: 2,
          h2hAwayWins: 1,
          h2hLastMeeting: '2 - 1',
          homeWinPct: 52,
          drawPct: 26,
          awayWinPct: 22,
          totalVotes: 1450,
        );

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Pre-Match Header Banner
          _PreMatchHeader(
            matchId: widget.match.matchId,
            onEnterTactics: widget.onEnterTactics,
          ),
          const SizedBox(height: 12),

          // Scoreboard / Fixture Card
          GtexMatchScoreboard(match: widget.match),
          const SizedBox(height: 14),

          // Win Probability & Fan Predictions
          _PredictionPollCard(
            pre: pre,
            homeTeam: widget.match.home,
            awayTeam: widget.match.away,
            selectedPrediction: _userPrediction,
            onSelectPrediction: (pred) => setState(() {
              _userPrediction = pred;
            }),
          ),
          const SizedBox(height: 14),

          // Form Guide & Head-to-Head
          _HeadToHeadAndFormCard(
            pre: pre,
            homeTeam: widget.match.home,
            awayTeam: widget.match.away,
          ),
          const SizedBox(height: 14),

          // Key Player Duel (Tactical Matchup)
          if (pre.keyDuel != null) ...[
            _KeyDuelCard(duel: pre.keyDuel!),
            const SizedBox(height: 14),
          ],

          // Tactical Storyline & Preview Notes
          if (pre.storyline != null && pre.storyline!.isNotEmpty) ...[
            _StorylineCard(storyline: pre.storyline!),
            const SizedBox(height: 14),
          ],

          // Official Team Sheets / Lineups Reveal
          _TeamSheetsCard(
            home: widget.match.home,
            away: widget.match.away,
            showBench: _showBench,
            onToggleBench: () => setState(() {
              _showBench = !_showBench;
            }),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

class _PreMatchHeader extends StatelessWidget {
  const _PreMatchHeader({
    required this.matchId,
    this.onEnterTactics,
  });

  final String matchId;
  final VoidCallback? onEnterTactics;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFF101924),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: GtexMatchVisualTokens.border),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
            decoration: BoxDecoration(
              color: const Color(0x33FFB800),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(color: GtexMatchVisualTokens.amber),
            ),
            child: const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.access_time_rounded, size: 12, color: GtexMatchVisualTokens.amber),
                SizedBox(width: 4),
                Text(
                  'PRE-MATCH BRIEFING',
                  style: TextStyle(
                    color: GtexMatchVisualTokens.amber,
                    fontSize: 10,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0.8,
                  ),
                ),
              ],
            ),
          ),
          const Spacer(),
          if (onEnterTactics != null)
            ElevatedButton.icon(
              onPressed: onEnterTactics,
              icon: const Icon(Icons.tune_rounded, size: 14),
              label: const Text('TACTICAL SETUP'),
              style: ElevatedButton.styleFrom(
                backgroundColor: GtexMatchVisualTokens.live,
                foregroundColor: const Color(0xFF0F172A),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                textStyle: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 0.5,
                ),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
              ),
            ),
        ],
      ),
    );
  }
}

class _PredictionPollCard extends StatelessWidget {
  const _PredictionPollCard({
    required this.pre,
    required this.homeTeam,
    required this.awayTeam,
    required this.selectedPrediction,
    required this.onSelectPrediction,
  });

  final GtexPreMatchPackage pre;
  final GtexMatchTeam homeTeam;
  final GtexMatchTeam awayTeam;
  final String? selectedPrediction;
  final ValueChanged<String> onSelectPrediction;

  @override
  Widget build(BuildContext context) {
    final int displayHomePct = selectedPrediction == 'home' ? pre.homeWinPct + 1 : pre.homeWinPct;
    final int displayAwayPct = selectedPrediction == 'away' ? pre.awayWinPct + 1 : pre.awayWinPct;
    final int displayDrawPct = 100 - displayHomePct - displayAwayPct;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF101924),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: GtexMatchVisualTokens.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.query_stats_rounded, size: 16, color: GtexMatchVisualTokens.amber),
              const SizedBox(width: 6),
              const Text(
                'WIN PROBABILITY & FAN PREDICTIONS',
                style: TextStyle(
                  color: GtexMatchVisualTokens.textPrimary,
                  fontSize: 11,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 1.0,
                ),
              ),
              const Spacer(),
              Text(
                '${pre.totalVotes} VOTES',
                style: const TextStyle(
                  color: GtexMatchVisualTokens.textSecondary,
                  fontSize: 10,
                  fontWeight: FontWeight.w800,
                  fontFamily: 'JetBrains Mono',
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Probability Segmented Bar
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: SizedBox(
              height: 10,
              child: Row(
                children: [
                  Expanded(
                    flex: displayHomePct,
                    child: Container(color: GtexMatchVisualTokens.live),
                  ),
                  const SizedBox(width: 2),
                  Expanded(
                    flex: displayDrawPct,
                    child: Container(color: const Color(0xFF475569)),
                  ),
                  const SizedBox(width: 2),
                  Expanded(
                    flex: displayAwayPct,
                    child: Container(color: GtexMatchVisualTokens.amber),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),

          // Percentage Labels
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '${homeTeam.shortName} $displayHomePct%',
                style: const TextStyle(
                  color: GtexMatchVisualTokens.live,
                  fontSize: 11,
                  fontWeight: FontWeight.w900,
                  fontFamily: 'JetBrains Mono',
                ),
              ),
              Text(
                'DRAW $displayDrawPct%',
                style: const TextStyle(
                  color: Color(0xFF94A3B8),
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                  fontFamily: 'JetBrains Mono',
                ),
              ),
              Text(
                '${awayTeam.shortName} $displayAwayPct%',
                style: const TextStyle(
                  color: GtexMatchVisualTokens.amber,
                  fontSize: 11,
                  fontWeight: FontWeight.w900,
                  fontFamily: 'JetBrains Mono',
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),

          // Prediction Buttons
          Row(
            children: [
              Expanded(
                child: _PredictionButton(
                  label: '${homeTeam.shortName} WIN',
                  isSelected: selectedPrediction == 'home',
                  activeColor: GtexMatchVisualTokens.live,
                  onTap: () => onSelectPrediction('home'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _PredictionButton(
                  label: 'DRAW',
                  isSelected: selectedPrediction == 'draw',
                  activeColor: const Color(0xFF94A3B8),
                  onTap: () => onSelectPrediction('draw'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _PredictionButton(
                  label: '${awayTeam.shortName} WIN',
                  isSelected: selectedPrediction == 'away',
                  activeColor: GtexMatchVisualTokens.amber,
                  onTap: () => onSelectPrediction('away'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _PredictionButton extends StatelessWidget {
  const _PredictionButton({
    required this.label,
    required this.isSelected,
    required this.activeColor,
    required this.onTap,
  });

  final String label;
  final bool isSelected;
  final Color activeColor;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        padding: const EdgeInsets.symmetric(vertical: 8),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: isSelected ? activeColor.withOpacity(0.18) : const Color(0xFF162332),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: isSelected ? activeColor : GtexMatchVisualTokens.border,
            width: isSelected ? 1.5 : 1.0,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: isSelected ? activeColor : GtexMatchVisualTokens.textSecondary,
            fontSize: 10,
            fontWeight: FontWeight.w900,
            letterSpacing: 0.5,
          ),
        ),
      ),
    );
  }
}

class _HeadToHeadAndFormCard extends StatelessWidget {
  const _HeadToHeadAndFormCard({
    required this.pre,
    required this.homeTeam,
    required this.awayTeam,
  });

  final GtexPreMatchPackage pre;
  final GtexMatchTeam homeTeam;
  final GtexMatchTeam awayTeam;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF101924),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: GtexMatchVisualTokens.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.history_toggle_off_rounded, size: 16, color: GtexMatchVisualTokens.live),
              SizedBox(width: 6),
              Text(
                'HEAD-TO-HEAD & RECENT FORM',
                style: TextStyle(
                  color: GtexMatchVisualTokens.textPrimary,
                  fontSize: 11,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 1.0,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),

          // Form Comparison Strip
          Row(
            children: [
              // Home Form
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      homeTeam.name.toUpperCase(),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: GtexMatchVisualTokens.live,
                        fontSize: 11,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Row(
                      children: pre.homeForm
                          .map((res) => _FormChip(result: res))
                          .toList(),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${pre.homeWinRate}% Season Win Rate',
                      style: const TextStyle(
                        color: GtexMatchVisualTokens.textTertiary,
                        fontSize: 9.5,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),

              // Away Form
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      awayTeam.name.toUpperCase(),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: GtexMatchVisualTokens.amber,
                        fontSize: 11,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: pre.awayForm
                          .map((res) => _FormChip(result: res))
                          .toList(),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${pre.awayWinRate}% Season Win Rate',
                      style: const TextStyle(
                        color: GtexMatchVisualTokens.textTertiary,
                        fontSize: 9.5,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const Divider(height: 24, color: Color(0xFF1E2D3D)),

          // Historical H2H Statistics Row
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _H2hStatBox(label: '${homeTeam.shortName} WINS', value: '${pre.h2hHomeWins}', color: GtexMatchVisualTokens.live),
              _H2hStatBox(label: 'DRAWS', value: '${pre.h2hDraws}', color: const Color(0xFF94A3B8)),
              _H2hStatBox(label: '${awayTeam.shortName} WINS', value: '${pre.h2hAwayWins}', color: GtexMatchVisualTokens.amber),
            ],
          ),
          const SizedBox(height: 8),
          Center(
            child: Text(
              'Last meeting: ${pre.h2hLastMeeting}',
              style: const TextStyle(
                color: GtexMatchVisualTokens.textTertiary,
                fontSize: 10,
                fontWeight: FontWeight.w700,
                fontFamily: 'JetBrains Mono',
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _FormChip extends StatelessWidget {
  const _FormChip({required this.result});

  final String result;

  @override
  Widget build(BuildContext context) {
    Color bg;
    Color fg;
    switch (result.toUpperCase()) {
      case 'W':
        bg = const Color(0xFF00E87A);
        fg = const Color(0xFF0F172A);
        break;
      case 'D':
        bg = const Color(0xFF64748B);
        fg = Colors.white;
        break;
      case 'L':
      default:
        bg = const Color(0xFFFF4D4D);
        fg = Colors.white;
        break;
    }

    return Container(
      width: 18,
      height: 18,
      margin: const EdgeInsets.only(right: 3),
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(3),
      ),
      child: Text(
        result.toUpperCase(),
        style: TextStyle(
          color: fg,
          fontSize: 9.5,
          fontWeight: FontWeight.w900,
          fontFamily: 'JetBrains Mono',
        ),
      ),
    );
  }
}

class _H2hStatBox extends StatelessWidget {
  const _H2hStatBox({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          value,
          style: TextStyle(
            color: color,
            fontSize: 20,
            fontWeight: FontWeight.w900,
            fontFamily: 'JetBrains Mono',
          ),
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: const TextStyle(
            color: GtexMatchVisualTokens.textSecondary,
            fontSize: 9,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.5,
          ),
        ),
      ],
    );
  }
}

class _KeyDuelCard extends StatelessWidget {
  const _KeyDuelCard({required this.duel});

  final GtexKeyDuel duel;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF101924),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: GtexMatchVisualTokens.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.local_fire_department_rounded, size: 16, color: Color(0xFFFF5252)),
              SizedBox(width: 6),
              Text(
                'KEY PLAYER DUEL · TACTICAL MATCHUP',
                style: TextStyle(
                  color: GtexMatchVisualTokens.textPrimary,
                  fontSize: 11,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 1.0,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),

          // Head-to-Head Player Card Strip
          Row(
            children: [
              // Home Player
              Expanded(
                child: _PlayerDuelProfile(
                  name: duel.homePlayerName,
                  role: duel.homePlayerRole,
                  rating: duel.homePlayerRating,
                  accentColor: GtexMatchVisualTokens.live,
                  alignRight: false,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E2D3D),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: const Text(
                  'VS',
                  style: TextStyle(
                    color: Color(0xFFFF5252),
                    fontSize: 11,
                    fontWeight: FontWeight.w900,
                    fontFamily: 'JetBrains Mono',
                  ),
                ),
              ),
              // Away Player
              Expanded(
                child: _PlayerDuelProfile(
                  name: duel.awayPlayerName,
                  role: duel.awayPlayerRole,
                  rating: duel.awayPlayerRating,
                  accentColor: GtexMatchVisualTokens.amber,
                  alignRight: true,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: const Color(0xFF0B121A),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: const Color(0x33FFFFFF)),
            ),
            child: Text(
              duel.description,
              style: const TextStyle(
                color: Color(0xFFB0BAC5),
                fontSize: 11,
                fontWeight: FontWeight.w600,
                height: 1.35,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PlayerDuelProfile extends StatelessWidget {
  const _PlayerDuelProfile({
    required this.name,
    required this.role,
    required this.rating,
    required this.accentColor,
    required this.alignRight,
  });

  final String name;
  final String role;
  final double rating;
  final Color accentColor;
  final bool alignRight;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: alignRight ? CrossAxisAlignment.end : CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (!alignRight) ...[
              _DuelBadge(rating: rating, color: accentColor),
              const SizedBox(width: 8),
            ],
            Flexible(
              child: Text(
                name,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: GtexMatchVisualTokens.textPrimary,
                  fontSize: 12,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
            if (alignRight) ...[
              const SizedBox(width: 8),
              _DuelBadge(rating: rating, color: accentColor),
            ],
          ],
        ),
        const SizedBox(height: 3),
        Text(
          role.toUpperCase(),
          style: TextStyle(
            color: accentColor,
            fontSize: 9.5,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.5,
          ),
        ),
      ],
    );
  }
}

class _DuelBadge extends StatelessWidget {
  const _DuelBadge({required this.rating, required this.color});

  final double rating;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.18),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color, width: 0.8),
      ),
      child: Text(
        rating.toStringAsFixed(1),
        style: TextStyle(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.w900,
          fontFamily: 'JetBrains Mono',
        ),
      ),
    );
  }
}

class _StorylineCard extends StatelessWidget {
  const _StorylineCard({required this.storyline});

  final String storyline;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF142435), Color(0xFF0D1722)],
        ),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: GtexMatchVisualTokens.border),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.menu_book_rounded, size: 16, color: GtexMatchVisualTokens.amber),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'MATCH STORYLINE',
                  style: TextStyle(
                    color: GtexMatchVisualTokens.amber,
                    fontSize: 10,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0.8,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  storyline,
                  style: const TextStyle(
                    color: GtexMatchVisualTokens.textPrimary,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    height: 1.35,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TeamSheetsCard extends StatelessWidget {
  const _TeamSheetsCard({
    required this.home,
    required this.away,
    required this.showBench,
    required this.onToggleBench,
  });

  final GtexMatchTeam home;
  final GtexMatchTeam away;
  final bool showBench;
  final VoidCallback onToggleBench;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF101924),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: GtexMatchVisualTokens.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.assignment_ind_rounded, size: 16, color: GtexMatchVisualTokens.live),
              const SizedBox(width: 6),
              const Text(
                'OFFICIAL TEAM SHEETS',
                style: TextStyle(
                  color: GtexMatchVisualTokens.textPrimary,
                  fontSize: 11,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 1.0,
                ),
              ),
              const Spacer(),
              InkWell(
                onTap: onToggleBench,
                borderRadius: BorderRadius.circular(4),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  child: Text(
                    showBench ? 'SHOW STARTING XI' : 'SHOW BENCH',
                    style: const TextStyle(
                      color: GtexMatchVisualTokens.live,
                      fontSize: 10,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0.5,
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),

          // Team Lineup Columns Side by Side
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Home Team Sheet
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${home.name} (${home.formation})',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: GtexMatchVisualTokens.live,
                        fontSize: 11,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 8),
                    for (final p in (showBench ? home.bench : home.players).take(11))
                      _LineupPlayerRow(player: p, isHome: true),
                  ],
                ),
              ),
              const SizedBox(width: 14),

              // Away Team Sheet
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${away.name} (${away.formation})',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: GtexMatchVisualTokens.amber,
                        fontSize: 11,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 8),
                    for (final p in (showBench ? away.bench : away.players).take(11))
                      _LineupPlayerRow(player: p, isHome: false),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _LineupPlayerRow extends StatelessWidget {
  const _LineupPlayerRow({required this.player, required this.isHome});

  final GtexLineupPlayer player;
  final bool isHome;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2.5),
      child: Row(
        children: [
          Container(
            width: 18,
            height: 18,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: isHome
                  ? GtexMatchVisualTokens.live.withOpacity(0.18)
                  : GtexMatchVisualTokens.amber.withOpacity(0.18),
              borderRadius: BorderRadius.circular(3),
            ),
            child: Text(
              '${player.shirtNumber}',
              style: TextStyle(
                color: isHome ? GtexMatchVisualTokens.live : GtexMatchVisualTokens.amber,
                fontSize: 9,
                fontWeight: FontWeight.w900,
                fontFamily: 'JetBrains Mono',
              ),
            ),
          ),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              player.name,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: GtexMatchVisualTokens.textPrimary,
                fontSize: 10.5,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          Text(
            player.position,
            style: const TextStyle(
              color: GtexMatchVisualTokens.textTertiary,
              fontSize: 9,
              fontWeight: FontWeight.w800,
              fontFamily: 'JetBrains Mono',
            ),
          ),
        ],
      ),
    );
  }
}
