import 'package:flutter/material.dart';

import '../data/gtex_match_models.dart';

class GtexTacticsPanel extends StatefulWidget {
  const GtexTacticsPanel({super.key, required this.isSending, required this.onSubmit});

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
        const Text('Live Tactical Controls', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18)),
        const SizedBox(height: 8),
        Text('Send lightweight tactical instructions to the backend. Keep the existing simulation engine as source of truth.', style: TextStyle(color: Colors.white.withOpacity(.58), height: 1.3)),
        const SizedBox(height: 18),
        _slider('Press intensity', press, (v) => setState(() => press = v)),
        _slider('Defensive line', line, (v) => setState(() => line = v)),
        _slider('Tempo', tempo, (v) => setState(() => tempo = v)),
        _slider('Risk level', risk, (v) => setState(() => risk = v)),
        const SizedBox(height: 18),
        ElevatedButton.icon(
          onPressed: widget.isSending
              ? null
              : () => widget.onSubmit(GtexTacticalInstruction(
                    pressIntensity: press.round(),
                    defensiveLine: line.round(),
                    tempo: tempo.round(),
                    riskLevel: risk.round(),
                  )),
          icon: widget.isSending ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.sports_soccer),
          label: Text(widget.isSending ? 'Sending...' : 'Send instruction'),
        ),
      ],
    );
  }

  Widget _slider(String label, double value, ValueChanged<double> onChanged) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(child: Text(label, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800))),
            Text('${value.round()}', style: const TextStyle(color: Color(0xFF18FF88), fontWeight: FontWeight.w900)),
          ],
        ),
        Slider(value: value, min: 0, max: 100, onChanged: onChanged),
      ],
    );
  }
}
