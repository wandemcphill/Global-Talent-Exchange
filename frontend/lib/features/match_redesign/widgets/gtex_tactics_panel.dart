import 'package:flutter/material.dart';

import '../data/gtex_match_models.dart';
import 'gtex_match_visual_tokens.dart';

class GtexTacticsPanel extends StatefulWidget {
  const GtexTacticsPanel({
    super.key,
    required this.isSending,
    required this.onSubmit,
  });

  final bool isSending;
  final ValueChanged<GtexTacticalInstruction> onSubmit;

  @override
  State<GtexTacticsPanel> createState() => _GtexTacticsPanelState();
}

class _GtexTacticsPanelState extends State<GtexTacticsPanel> {
  double press = 62;
  double line = 54;
  double tempo = 68;
  double risk = 48;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Container(
          padding: const EdgeInsets.all(14),
          decoration: GtexMatchVisualTokens.panelDecoration(
            background: GtexMatchVisualTokens.surfaceOverlay,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'TACTICAL COMMAND',
                style: TextStyle(
                  color: GtexMatchVisualTokens.textPrimary,
                  fontWeight: FontWeight.w900,
                  fontSize: 14,
                  letterSpacing: .8,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Instructions are submitted to the live match authority and remain pending until accepted.',
                style: TextStyle(
                  color: GtexMatchVisualTokens.textSecondary,
                  height: 1.3,
                ),
              ),
              const SizedBox(height: 16),
              _TacticalSlider(
                label: 'PRESS INTENSITY',
                value: press,
                onChanged: (double value) => setState(() => press = value),
              ),
              _TacticalSlider(
                label: 'DEFENSIVE LINE',
                value: line,
                onChanged: (double value) => setState(() => line = value),
              ),
              _TacticalSlider(
                label: 'TEMPO',
                value: tempo,
                onChanged: (double value) => setState(() => tempo = value),
              ),
              _TacticalSlider(
                label: 'RISK LEVEL',
                value: risk,
                onChanged: (double value) => setState(() => risk = value),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: widget.isSending ? null : _submitInstruction,
                  icon:
                      widget.isSending
                          ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                          : const Icon(Icons.send_rounded),
                  label: Text(
                    widget.isSending ? 'SUBMITTING' : 'SEND TO MATCH AUTHORITY',
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
              overlayColor: GtexMatchVisualTokens.live.withOpacity(.12),
              trackHeight: 4,
            ),
            child: Slider(value: value, min: 0, max: 100, onChanged: onChanged),
          ),
        ],
      ),
    );
  }
}
