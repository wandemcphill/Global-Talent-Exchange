import 'package:flutter/material.dart';

import '../data/gtex_match_models.dart';
import 'gtex_match_visual_tokens.dart';

enum TacticalStylePreset {
  gegenpress('Gegenpress', Icons.bolt, 85, 78, 82, 72, 'attacking'),
  tikiTaka('Tiki-Taka', Icons.sync_alt, 65, 72, 42, 50, 'balanced'),
  counter('Counter', Icons.arrow_forward, 35, 28, 88, 65, 'attacking'),
  lowBlock('Low Block', Icons.shield, 20, 18, 30, 20, 'defensive'),
  balanced('Balanced', Icons.balance, 50, 50, 50, 50, 'balanced');

  const TacticalStylePreset(
    this.label,
    this.icon,
    this.press,
    this.line,
    this.tempo,
    this.risk,
    this.mentality,
  );

  final String label;
  final IconData icon;
  final double press;
  final double line;
  final double tempo;
  final double risk;
  final String mentality;
}

class _PendingSubstitution {
  const _PendingSubstitution({
    required this.outPlayer,
    required this.inPlayer,
  });

  final GtexLineupPlayer outPlayer;
  final GtexLineupPlayer inPlayer;
}

class GtexTacticsPanel extends StatefulWidget {
  const GtexTacticsPanel({
    super.key,
    required this.isSending,
    required this.onSubmit,
    this.homeTeam,
    this.awayTeam,
    this.currentMinute = 0,
  });

  final bool isSending;
  final ValueChanged<GtexTacticalInstruction> onSubmit;
  final GtexMatchTeam? homeTeam;
  final GtexMatchTeam? awayTeam;
  final int currentMinute;

  @override
  State<GtexTacticsPanel> createState() => _GtexTacticsPanelState();
}

class _GtexTacticsPanelState extends State<GtexTacticsPanel> {
  static const List<String> _availableFormations = <String>[
    '4-3-3',
    '4-2-3-1',
    '4-4-2',
    '3-5-2',
    '5-3-2',
    '4-1-4-1',
  ];

  String selectedSide = 'home';
  TacticalStylePreset? activePreset = TacticalStylePreset.balanced;
  late String formation;
  double press = 50;
  double line = 50;
  double tempo = 50;
  double risk = 50;

  GtexLineupPlayer? selectedStarter;
  final List<_PendingSubstitution> pendingSubs = <_PendingSubstitution>[];

  @override
  void initState() {
    super.initState();
    formation = widget.homeTeam?.formation ?? '4-3-3';
    _applyPreset(TacticalStylePreset.balanced);
  }

  void _applyPreset(TacticalStylePreset preset) {
    setState(() {
      activePreset = preset;
      press = preset.press;
      line = preset.line;
      tempo = preset.tempo;
      risk = preset.risk;
    });
  }

  GtexMatchTeam? get currentTeam =>
      selectedSide == 'home' ? widget.homeTeam : widget.awayTeam;

  String _resolveMentality(double riskVal) {
    if (riskVal >= 80) return 'all_out_attack';
    if (riskVal >= 62) return 'attacking';
    if (riskVal <= 22) return 'park_the_bus';
    if (riskVal <= 38) return 'defensive';
    return 'balanced';
  }

  String _mentalityLabel(double riskVal) {
    if (riskVal >= 80) return 'ALL-OUT ATTACK';
    if (riskVal >= 62) return 'ATTACKING';
    if (riskVal <= 22) return 'PARK THE BUS';
    if (riskVal <= 38) return 'DEFENSIVE';
    return 'BALANCED';
  }

  Color _mentalityColor(double riskVal) {
    if (riskVal >= 62) return GtexMatchVisualTokens.red;
    if (riskVal <= 38) return GtexMatchVisualTokens.blue;
    return GtexMatchVisualTokens.live;
  }

  @override
  Widget build(BuildContext context) {
    final GtexMatchTeam? team = currentTeam;
    final List<GtexLineupPlayer> starters = team?.players ?? const <GtexLineupPlayer>[];
    final List<GtexLineupPlayer> bench = team?.bench ?? const <GtexLineupPlayer>[];

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Team Selector & Header
        Container(
          padding: const EdgeInsets.all(14),
          decoration: GtexMatchVisualTokens.panelDecoration(
            background: GtexMatchVisualTokens.surfaceOverlay,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(
                    Icons.tune,
                    color: GtexMatchVisualTokens.live,
                    size: 18,
                  ),
                  const SizedBox(width: 8),
                  const Text(
                    'TACTICAL COMMAND HUB',
                    style: TextStyle(
                      color: GtexMatchVisualTokens.textPrimary,
                      fontWeight: FontWeight.w900,
                      fontSize: 14,
                      letterSpacing: .8,
                    ),
                  ),
                  const Spacer(),
                  if (widget.homeTeam != null && widget.awayTeam != null)
                    SegmentedButton<String>(
                      segments: [
                        ButtonSegment<String>(
                          value: 'home',
                          label: Text(
                            widget.homeTeam!.shortName,
                            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
                          ),
                        ),
                        ButtonSegment<String>(
                          value: 'away',
                          label: Text(
                            widget.awayTeam!.shortName,
                            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
                          ),
                        ),
                      ],
                      selected: {selectedSide},
                      onSelectionChanged: (Set<String> newSelection) {
                        setState(() {
                          selectedSide = newSelection.first;
                          selectedStarter = null;
                          pendingSubs.clear();
                          final GtexMatchTeam? newTeam = currentTeam;
                          if (newTeam != null) {
                            formation = newTeam.formation;
                          }
                        });
                      },
                      style: const ButtonStyle(
                        visualDensity: VisualDensity.compact,
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 8),
              const Text(
                'Live tactical commands, formation restructuring, and player substitutions broadcast directly to server match authority.',
                style: TextStyle(
                  color: GtexMatchVisualTokens.textSecondary,
                  fontSize: 12,
                  height: 1.35,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),

        // Style Presets Bar
        Container(
          padding: const EdgeInsets.all(14),
          decoration: GtexMatchVisualTokens.panelDecoration(
            background: GtexMatchVisualTokens.surfaceOverlay,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text('TACTICAL PRESETS', style: GtexMatchVisualTokens.labelStyle),
                  const Spacer(),
                  if (activePreset != null)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: GtexMatchVisualTokens.live.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        activePreset!.label.toUpperCase(),
                        style: const TextStyle(
                          color: GtexMatchVisualTokens.live,
                          fontSize: 10,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 10),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: TacticalStylePreset.values.map((TacticalStylePreset preset) {
                    final bool isSelected = activePreset == preset;
                    return Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: ChoiceChip(
                        avatar: Icon(
                          preset.icon,
                          size: 14,
                          color: isSelected ? Colors.white : GtexMatchVisualTokens.textSecondary,
                        ),
                        label: Text(preset.label),
                        selected: isSelected,
                        onSelected: (bool selected) {
                          if (selected) _applyPreset(preset);
                        },
                        selectedColor: GtexMatchVisualTokens.borderStrong,
                        backgroundColor: GtexMatchVisualTokens.surfaceRaised,
                        labelStyle: TextStyle(
                          color: isSelected ? Colors.white : GtexMatchVisualTokens.textSecondary,
                          fontSize: 11,
                          fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),

        // Formation & Interactive Mini Pitch Board
        Container(
          padding: const EdgeInsets.all(14),
          decoration: GtexMatchVisualTokens.panelDecoration(
            background: GtexMatchVisualTokens.surfaceOverlay,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text('FORMATION & SQUAD SHAPE', style: GtexMatchVisualTokens.labelStyle),
                  const Spacer(),
                  DropdownButtonHideUnderline(
                    child: DropdownButton<String>(
                      value: _availableFormations.contains(formation) ? formation : _availableFormations.first,
                      dropdownColor: GtexMatchVisualTokens.surfaceRaised,
                      style: const TextStyle(
                        color: GtexMatchVisualTokens.textPrimary,
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                        fontFamily: 'JetBrains Mono',
                      ),
                      icon: const Icon(Icons.arrow_drop_down, color: GtexMatchVisualTokens.textSecondary),
                      items: _availableFormations.map((String f) {
                        return DropdownMenuItem<String>(
                          value: f,
                          child: Text(f),
                        );
                      }).toList(),
                      onChanged: (String? newFormation) {
                        if (newFormation != null) {
                          setState(() {
                            formation = newFormation;
                            activePreset = null;
                          });
                        }
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              // Mini Pitch Visualizer
              _TacticalPitchBoard(
                formation: formation,
                starters: starters,
                selectedStarter: selectedStarter,
                pendingSubs: pendingSubs,
                onSelectStarter: (GtexLineupPlayer player) {
                  setState(() {
                    if (selectedStarter?.id == player.id) {
                      selectedStarter = null;
                    } else {
                      selectedStarter = player;
                    }
                  });
                },
              ),
              const SizedBox(height: 8),
              if (selectedStarter != null)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: GtexMatchVisualTokens.blue.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: GtexMatchVisualTokens.blue.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.swap_vert_rounded, color: GtexMatchVisualTokens.blue, size: 16),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Selected ${selectedStarter!.name} (#${selectedStarter!.shirtNumber}). Tap a bench player below to sub ON.',
                          style: const TextStyle(
                            color: GtexMatchVisualTokens.textPrimary,
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      GestureDetector(
                        onTap: () => setState(() => selectedStarter = null),
                        child: const Icon(Icons.close, size: 16, color: GtexMatchVisualTokens.textSecondary),
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 12),

        // Live In-Match Substitutions (5 Subs Rule)
        Container(
          padding: const EdgeInsets.all(14),
          decoration: GtexMatchVisualTokens.panelDecoration(
            background: GtexMatchVisualTokens.surfaceOverlay,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text('IN-MATCH SUBSTITUTIONS', style: GtexMatchVisualTokens.labelStyle),
                  const Spacer(),
                  Text(
                    '${5 - pendingSubs.length} / 5 REMAINING',
                    style: TextStyle(
                      color: pendingSubs.length >= 5
                          ? GtexMatchVisualTokens.red
                          : GtexMatchVisualTokens.live,
                      fontSize: 11,
                      fontFamily: 'JetBrains Mono',
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),

              // Pending subs cards
              if (pendingSubs.isNotEmpty) ...[
                const SizedBox(height: 4),
                ...pendingSubs.map((_PendingSubstitution sub) {
                  return Container(
                    margin: const EdgeInsets.only(bottom: 6),
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                    decoration: BoxDecoration(
                      color: GtexMatchVisualTokens.surfaceRaised,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: GtexMatchVisualTokens.amber.withValues(alpha: 0.4)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.swap_horiz_rounded, color: GtexMatchVisualTokens.amber, size: 16),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            'OUT: ${sub.outPlayer.name} (#${sub.outPlayer.shirtNumber}) ➔ IN: ${sub.inPlayer.name} (#${sub.inPlayer.shirtNumber})',
                            style: const TextStyle(
                              color: GtexMatchVisualTokens.textPrimary,
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.delete_outline, size: 16, color: GtexMatchVisualTokens.textSecondary),
                          onPressed: () {
                            setState(() {
                              pendingSubs.remove(sub);
                            });
                          },
                          visualDensity: VisualDensity.compact,
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(),
                        ),
                      ],
                    ),
                  );
                }),
                const SizedBox(height: 8),
              ],

              // Bench list
              const Text(
                'AVAILABLE SUBSTITUTES (BENCH)',
                style: TextStyle(
                  color: GtexMatchVisualTokens.textSecondary,
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  letterSpacing: .6,
                ),
              ),
              const SizedBox(height: 8),
              if (bench.isEmpty)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 8),
                  child: Text(
                    'No bench personnel registered for this squad.',
                    style: TextStyle(color: GtexMatchVisualTokens.textSecondary, fontSize: 11),
                  ),
                )
              else
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: bench.map((GtexLineupPlayer subPlayer) {
                      final bool alreadyUsed = pendingSubs.any((s) => s.inPlayer.id == subPlayer.id);
                      final bool isReadyForSub = selectedStarter != null && !alreadyUsed;

                      return GestureDetector(
                        onTap: alreadyUsed || pendingSubs.length >= 5
                            ? null
                            : () {
                                if (selectedStarter != null) {
                                  setState(() {
                                    pendingSubs.add(
                                      _PendingSubstitution(
                                        outPlayer: selectedStarter!,
                                        inPlayer: subPlayer,
                                      ),
                                    );
                                    selectedStarter = null;
                                  });
                                } else {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text('Select a player on the pitch board to replace with ${subPlayer.name}.'),
                                      duration: const Duration(seconds: 2),
                                      behavior: SnackBarBehavior.floating,
                                    ),
                                  );
                                }
                              },
                        child: Opacity(
                          opacity: alreadyUsed ? 0.35 : 1.0,
                          child: Container(
                            margin: const EdgeInsets.only(right: 8),
                            padding: const EdgeInsets.all(8),
                            width: 110,
                            decoration: BoxDecoration(
                              color: isReadyForSub
                                  ? GtexMatchVisualTokens.blue.withValues(alpha: 0.12)
                                  : GtexMatchVisualTokens.surfaceRaised,
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(
                                color: isReadyForSub
                                    ? GtexMatchVisualTokens.blue
                                    : GtexMatchVisualTokens.border,
                              ),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Container(
                                      width: 20,
                                      height: 20,
                                      alignment: Alignment.center,
                                      decoration: BoxDecoration(
                                        color: GtexMatchVisualTokens.surfaceBase,
                                        borderRadius: BorderRadius.circular(10),
                                      ),
                                      child: Text(
                                        '${subPlayer.shirtNumber}',
                                        style: const TextStyle(
                                          color: GtexMatchVisualTokens.textPrimary,
                                          fontSize: 10,
                                          fontWeight: FontWeight.w900,
                                        ),
                                      ),
                                    ),
                                    const Spacer(),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                                      decoration: BoxDecoration(
                                        color: GtexMatchVisualTokens.surfaceOverlay,
                                        borderRadius: BorderRadius.circular(3),
                                      ),
                                      child: Text(
                                        subPlayer.position,
                                        style: const TextStyle(
                                          color: GtexMatchVisualTokens.textSecondary,
                                          fontSize: 9,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  subPlayer.name,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    color: GtexMatchVisualTokens.textPrimary,
                                    fontSize: 11,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Row(
                                  children: [
                                    const Icon(Icons.flash_on, size: 10, color: GtexMatchVisualTokens.live),
                                    const SizedBox(width: 2),
                                    Text(
                                      '${((subPlayer.fitnessPct ?? 1.0) * 100).round()}%',
                                      style: const TextStyle(
                                        color: GtexMatchVisualTokens.textSecondary,
                                        fontSize: 9,
                                        fontFamily: 'JetBrains Mono',
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 12),

        // Tactical Sliders
        Container(
          padding: const EdgeInsets.all(14),
          decoration: GtexMatchVisualTokens.panelDecoration(
            background: GtexMatchVisualTokens.surfaceOverlay,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text('TACTICAL INSTRUCTIONS', style: GtexMatchVisualTokens.labelStyle),
                  const Spacer(),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: _mentalityColor(risk).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      _mentalityLabel(risk),
                      style: TextStyle(
                        color: _mentalityColor(risk),
                        fontSize: 10,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              _TacticalSlider(
                label: 'PRESS INTENSITY',
                value: press,
                onChanged: (double val) => setState(() {
                  press = val;
                  activePreset = null;
                }),
              ),
              _TacticalSlider(
                label: 'DEFENSIVE LINE',
                value: line,
                onChanged: (double val) => setState(() {
                  line = val;
                  activePreset = null;
                }),
              ),
              _TacticalSlider(
                label: 'TEMPO',
                value: tempo,
                onChanged: (double val) => setState(() {
                  tempo = val;
                  activePreset = null;
                }),
              ),
              _TacticalSlider(
                label: 'RISK & MENTALITY',
                value: risk,
                onChanged: (double val) => setState(() {
                  risk = val;
                  activePreset = null;
                }),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: widget.isSending ? null : _submitInstruction,
                  icon: widget.isSending
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.send_rounded),
                  label: Text(
                    widget.isSending
                        ? 'TRANSMITTING INSTRUCTIONS...'
                        : pendingSubs.isNotEmpty
                            ? 'APPLY TACTICS & ${pendingSubs.length} SUB(S)'
                            : 'SUBMIT TO MATCH AUTHORITY',
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: GtexMatchVisualTokens.live,
                    foregroundColor: Colors.black,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    textStyle: const TextStyle(fontWeight: FontWeight.w900, letterSpacing: .5),
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  void _submitInstruction() {
    widget.onSubmit(
      GtexTacticalInstruction(
        pressIntensity: press.round(),
        defensiveLine: line.round(),
        tempo: tempo.round(),
        riskLevel: risk.round(),
        formation: formation,
        mentality: _resolveMentality(risk),
        side: selectedSide,
        substitutions: pendingSubs
            .map((_PendingSubstitution sub) => <String, dynamic>{
                  'out_player_id': sub.outPlayer.id,
                  'in_player_id': sub.inPlayer.id,
                  'out_player_name': sub.outPlayer.name,
                  'in_player_name': sub.inPlayer.name,
                })
            .toList(),
      ),
    );
    setState(() {
      pendingSubs.clear();
      selectedStarter = null;
    });
  }
}

class _TacticalPitchBoard extends StatelessWidget {
  const _TacticalPitchBoard({
    required this.formation,
    required this.starters,
    required this.selectedStarter,
    required this.pendingSubs,
    required this.onSelectStarter,
  });

  final String formation;
  final List<GtexLineupPlayer> starters;
  final GtexLineupPlayer? selectedStarter;
  final List<_PendingSubstitution> pendingSubs;
  final ValueChanged<GtexLineupPlayer> onSelectStarter;

  List<int> _parseFormationLines(String fmt) {
    final List<String> parts = fmt.split('-');
    final List<int> nums = parts.map((p) => int.tryParse(p) ?? 0).where((n) => n > 0).toList();
    if (nums.isEmpty) return const [1, 4, 3, 3];
    return [1, ...nums];
  }

  @override
  Widget build(BuildContext context) {
    final List<int> lineCounts = _parseFormationLines(formation);

    return Container(
      height: 220,
      width: double.infinity,
      decoration: BoxDecoration(
        color: const Color(0xFF071F14),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF134E35)),
      ),
      child: Stack(
        children: [
          // Pitch markings
          Center(
            child: Container(
              height: 1,
              color: Colors.white.withValues(alpha: 0.12),
            ),
          ),
          Center(
            child: Container(
              width: 50,
              height: 50,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
              ),
            ),
          ),
          // Starting XI arranged by lines
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: List.generate(lineCounts.length, (int lineIdx) {
                // Reversed so GK is at bottom, FW at top
                final int actualLine = lineCounts.length - 1 - lineIdx;
                final int count = lineCounts[actualLine];

                // Calculate slice of starters for this line
                int offset = 0;
                for (int i = 0; i < actualLine; i++) {
                  offset += lineCounts[i];
                }
                final List<GtexLineupPlayer> linePlayers = starters.skip(offset).take(count).toList();

                return Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: List.generate(count, (int playerIdx) {
                    final GtexLineupPlayer? player =
                        playerIdx < linePlayers.length ? linePlayers[playerIdx] : null;

                    if (player == null) {
                      return const SizedBox(width: 32, height: 32);
                    }

                    final bool isSelected = selectedStarter?.id == player.id;
                    final bool isSubbedOut = pendingSubs.any((s) => s.outPlayer.id == player.id);

                    return GestureDetector(
                      onTap: () => onSelectStarter(player),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            width: 30,
                            height: 30,
                            alignment: Alignment.center,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: isSelected
                                  ? GtexMatchVisualTokens.blue
                                  : isSubbedOut
                                      ? GtexMatchVisualTokens.amber
                                      : const Color(0xFF0C3825),
                              border: Border.all(
                                color: isSelected
                                    ? Colors.white
                                    : isSubbedOut
                                        ? GtexMatchVisualTokens.amber
                                        : Colors.white70,
                                width: isSelected ? 2 : 1,
                              ),
                              boxShadow: isSelected
                                  ? [
                                      BoxShadow(
                                        color: GtexMatchVisualTokens.blue.withValues(alpha: 0.6),
                                        blurRadius: 8,
                                      ),
                                    ]
                                  : null,
                            ),
                            child: isSubbedOut
                                ? const Icon(Icons.swap_horiz, size: 14, color: Colors.black)
                                : Text(
                                    '${player.shirtNumber}',
                                    style: TextStyle(
                                      color: isSelected ? Colors.white : Colors.white,
                                      fontSize: 10,
                                      fontWeight: FontWeight.w900,
                                    ),
                                  ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            player.name.split(' ').last,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: isSelected
                                  ? GtexMatchVisualTokens.blue
                                  : Colors.white70,
                              fontSize: 9,
                              fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    );
                  }),
                );
              }),
            ),
          ),
        ],
      ),
    );
  }
}

class _TacticalSlider extends StatelessWidget {
  const _TacticalSlider({
    required this.label,
    required this.value,
    required this.onChanged,
  });

  final String label;
  final double value;
  final ValueChanged<double> onChanged;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(label, style: GtexMatchVisualTokens.labelStyle),
              ),
              Text(
                value.round().toString(),
                style: const TextStyle(
                  color: GtexMatchVisualTokens.live,
                  fontFamily: 'JetBrains Mono',
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
          SliderTheme(
            data: SliderThemeData(
              activeTrackColor: GtexMatchVisualTokens.live,
              inactiveTrackColor: GtexMatchVisualTokens.borderStrong,
              thumbColor: GtexMatchVisualTokens.textPrimary,
              overlayColor: GtexMatchVisualTokens.live.withValues(alpha: 0.12),
              trackHeight: 4,
            ),
            child: Slider(value: value, min: 0, max: 100, onChanged: onChanged),
          ),
        ],
      ),
    );
  }
}
