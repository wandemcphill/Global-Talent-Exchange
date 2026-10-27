import 'package:flutter/material.dart';

import '../data/gtex_match_models.dart';
import 'gtex_match_visual_tokens.dart';

/// Advice package computed dynamically by the in-match Assistant Manager.
class GtexTacticalAdvice {
  const GtexTacticalAdvice({
    required this.coachName,
    required this.situation,
    required this.recommendation,
    required this.buttonLabel,
    required this.instruction,
    required this.accentColor,
    required this.icon,
  });

  final String coachName;
  final String situation;
  final String recommendation;
  final String buttonLabel;
  final GtexTacticalInstruction instruction;
  final Color accentColor;
  final IconData icon;

  static GtexTacticalAdvice compute({
    required GtexLiveMatchState match,
  }) {
    final int homeScore = match.home.score;
    final int awayScore = match.away.score;
    final int minute = match.minute;

    if (minute >= 75 && homeScore > awayScore) {
      // Protecting lead in final minutes
      return GtexTacticalAdvice(
        coachName: 'Coach Karl · Assistant Manager',
        situation: 'Lead Protection Phase (${homeScore}-$awayScore · ${minute}m)',
        recommendation:
            'Opponent is pushing numbers forward. Transition to Low Block 5-3-2 with a deep line to deny space and hit on the break.',
        buttonLabel: 'APPLY LOW BLOCK LOCKDOWN',
        instruction: const GtexTacticalInstruction(
          pressIntensity: 28,
          defensiveLine: 24,
          tempo: 42,
          riskLevel: 22,
          formation: '5-3-2',
          mentality: 'Defensive',
          side: 'home',
        ),
        accentColor: const Color(0xFF60A5FA),
        icon: Icons.shield_rounded,
      );
    } else if (minute >= 60 && homeScore < awayScore) {
      // Chasing game in final third
      return GtexTacticalAdvice(
        coachName: 'Coach Karl · Assistant Manager',
        situation: 'Goal Deficit (${homeScore}-$awayScore · ${minute}m)',
        recommendation:
            'We need an equalizer. Shift into Gegenpress 4-2-4 with aggressive high line and high tempo to force turnovers in their half.',
        buttonLabel: 'APPLY GEGENPRESS OVERLOAD',
        instruction: const GtexTacticalInstruction(
          pressIntensity: 90,
          defensiveLine: 84,
          tempo: 86,
          riskLevel: 82,
          formation: '4-2-4',
          mentality: 'Attacking',
          side: 'home',
        ),
        accentColor: const Color(0xFFFF5722),
        icon: Icons.flash_on_rounded,
      );
    } else if (homeScore < awayScore) {
      // Early deficit
      return GtexTacticalAdvice(
        coachName: 'Coach Karl · Assistant Manager',
        situation: 'Trailing (${homeScore}-$awayScore · ${minute}m)',
        recommendation:
            'Opponent fullbacks are overextending. Switch to Quick Counter 3-4-3 to exploit transitions behind their defensive line.',
        buttonLabel: 'APPLY COUNTER ATTACK',
        instruction: const GtexTacticalInstruction(
          pressIntensity: 45,
          defensiveLine: 40,
          tempo: 90,
          riskLevel: 70,
          formation: '3-4-3',
          mentality: 'Counter',
          side: 'home',
        ),
        accentColor: const Color(0xFFFFB800),
        icon: Icons.compare_arrows_rounded,
      );
    } else if (minute >= 45 && homeScore == awayScore) {
      // Second half deadlock
      return GtexTacticalAdvice(
        coachName: 'Coach Karl · Assistant Manager',
        situation: 'Midfield Stalemate (${homeScore}-$awayScore · ${minute}m)',
        recommendation:
            'Midfield is contested. Switch to Tiki-Taka 4-3-3 with shorter passes and measured tempo to dominate possession and wear them down.',
        buttonLabel: 'APPLY TIKI-TAKA CONTROL',
        instruction: const GtexTacticalInstruction(
          pressIntensity: 65,
          defensiveLine: 66,
          tempo: 50,
          riskLevel: 45,
          formation: '4-3-3',
          mentality: 'Balanced',
          side: 'home',
        ),
        accentColor: const Color(0xFF00E87A),
        icon: Icons.all_inclusive_rounded,
      );
    } else {
      // Default / early balanced assessment
      return GtexTacticalAdvice(
        coachName: 'Coach Karl · Assistant Manager',
        situation: 'Tactical Read (${homeScore}-$awayScore · ${minute}m)',
        recommendation:
            'Initial shape is holding. Maintain Balanced 4-3-3 structure while probing wide channels and testing opponent center-backs.',
        buttonLabel: 'RE-ALIGN BALANCED SHAPE',
        instruction: const GtexTacticalInstruction(
          pressIntensity: 52,
          defensiveLine: 50,
          tempo: 52,
          riskLevel: 50,
          formation: '4-3-3',
          mentality: 'Balanced',
          side: 'home',
        ),
        accentColor: const Color(0xFF00E87A),
        icon: Icons.sports_soccer_rounded,
      );
    }
  }
}

/// In-Match Assistant Manager Tactical Advisor banner.
class GtexTacticalAdvisorWidget extends StatefulWidget {
  const GtexTacticalAdvisorWidget({
    super.key,
    required this.match,
    required this.onApplyInstruction,
    this.compact = false,
  });

  final GtexLiveMatchState match;
  final ValueChanged<GtexTacticalInstruction> onApplyInstruction;
  final bool compact;

  @override
  State<GtexTacticalAdvisorWidget> createState() =>
      _GtexTacticalAdvisorWidgetState();
}

class _GtexTacticalAdvisorWidgetState extends State<GtexTacticalAdvisorWidget> {
  bool _applied = false;
  bool _dismissed = false;
  String _lastAdviceKey = '';

  @override
  Widget build(BuildContext context) {
    if (_dismissed) return const SizedBox.shrink();

    final advice = GtexTacticalAdvice.compute(match: widget.match);
    final String currentAdviceKey = '${advice.situation}-${advice.buttonLabel}';

    // Reset applied state if situation changed significantly
    if (_lastAdviceKey != currentAdviceKey) {
      _lastAdviceKey = currentAdviceKey;
      _applied = false;
    }

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 4),
      padding: EdgeInsets.all(widget.compact ? 10 : 12),
      decoration: BoxDecoration(
        color: const Color(0xF20F172A),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: _applied
              ? const Color(0xFF00E87A)
              : advice.accentColor.withAlpha(140),
          width: 1.2,
        ),
        boxShadow: [
          BoxShadow(
            color: advice.accentColor.withAlpha(20),
            blurRadius: 10,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header: Advisor Badge + Situation + Dismiss button
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(5),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: advice.accentColor.withAlpha(35),
                  border: Border.all(color: advice.accentColor, width: 1.0),
                ),
                child: Icon(advice.icon, size: 13, color: advice.accentColor),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      advice.coachName.toUpperCase(),
                      style: TextStyle(
                        color: advice.accentColor,
                        fontSize: 9.5,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0.6,
                      ),
                    ),
                    Text(
                      advice.situation,
                      style: const TextStyle(
                        color: GtexMatchVisualTokens.textSecondary,
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
              InkWell(
                onTap: () => setState(() => _dismissed = true),
                child: const Padding(
                  padding: EdgeInsets.all(4),
                  child: Icon(
                    Icons.close_rounded,
                    size: 14,
                    color: GtexMatchVisualTokens.textTertiary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),

          // Tactical Recommendation
          Text(
            advice.recommendation,
            style: const TextStyle(
              color: GtexMatchVisualTokens.textPrimary,
              fontSize: 11,
              height: 1.35,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 10),

          // Action Button
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: _applied
                      ? null
                      : () {
                          widget.onApplyInstruction(advice.instruction);
                          setState(() => _applied = true);
                        },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _applied
                        ? const Color(0x3300E87A)
                        : advice.accentColor,
                    foregroundColor: _applied
                        ? const Color(0xFF00E87A)
                        : const Color(0xFF0F172A),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 9,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(6),
                      side: _applied
                          ? const BorderSide(color: Color(0xFF00E87A))
                          : BorderSide.none,
                    ),
                  ),
                  icon: Icon(
                    _applied ? Icons.check_circle_rounded : Icons.bolt_rounded,
                    size: 14,
                    color: _applied ? const Color(0xFF00E87A) : Colors.black87,
                  ),
                  label: Text(
                    _applied ? 'ADVICE APPLIED' : advice.buttonLabel,
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0.6,
                      color: _applied ? const Color(0xFF00E87A) : Colors.black87,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
