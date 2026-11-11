import 'package:flutter/material.dart';

import '../../core/app_feedback.dart';
import '../../data/gte_authed_api.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_surface_panel.dart';

/// Pause the game clock, start it again, change its speed, and fund one named cup.
class GtexAdminClockAndPrize extends StatefulWidget {
  const GtexAdminClockAndPrize({super.key, required this.api});

  final GteAuthedApi api;

  @override
  State<GtexAdminClockAndPrize> createState() => _GtexAdminClockAndPrizeState();
}

class _GtexAdminClockAndPrizeState extends State<GtexAdminClockAndPrize> {
  final TextEditingController _speed = TextEditingController(text: '1');
  final TextEditingController _first = TextEditingController();
  final TextEditingController _second = TextEditingController();
  final TextEditingController _third = TextEditingController();
  List<Map<String, dynamic>> _cups = <Map<String, dynamic>>[];
  String? _cupId;
  bool _paused = false;
  String _worldDate = '—';
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _speed.dispose();
    _first.dispose();
    _second.dispose();
    _third.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final Map<String, dynamic> clock = await widget.api.getMap('/api/world/clock');
      final Object? cupsBody = await widget.api.request('GET', '/api/admin/national-team-engine/cups');
      final List<Map<String, dynamic>> cups = cupsBody is List
          ? cupsBody.whereType<Map>().map((Map item) => Map<String, dynamic>.from(item)).toList()
          : <Map<String, dynamic>>[];
      if (!mounted) {
        return;
      }
      setState(() {
        _paused = clock['is_paused'] == true;
        _worldDate = clock['world_date']?.toString() ?? '—';
        _speed.text = clock['progression_rate']?.toString() ?? '1';
        _cups = cups;
        _cupId ??= cups.isEmpty ? null : cups.first['id']?.toString();
        _fillPrize();
      });
    } catch (error) {
      if (mounted) {
        AppFeedback.showError(context, error);
      }
    }
  }

  void _fillPrize() {
    final Map<String, dynamic>? cup = _selected;
    if (cup == null) {
      return;
    }
    _first.text = cup['first']?.toString() ?? '';
    _second.text = cup['second']?.toString() ?? '';
    _third.text = cup['third']?.toString() ?? '';
  }

  Map<String, dynamic>? get _selected {
    for (final Map<String, dynamic> cup in _cups) {
      if (cup['id']?.toString() == _cupId) {
        return cup;
      }
    }
    return _cups.isEmpty ? null : _cups.first;
  }

  Future<void> _run(Future<Object?> Function() action, String ok) async {
    setState(() => _busy = true);
    try {
      await action();
      if (mounted) {
        AppFeedback.showSuccess(context, ok);
      }
      await _load();
    } catch (error) {
      if (mounted) {
        AppFeedback.showError(context, error);
      }
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor: GteShellTheme.accentAdmin,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Text('Game clock and cup prize', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          Text(
            _paused
                ? 'The game clock is paused. Game date $_worldDate. Start it again when you want matches and ages to move.'
                : 'The game clock is running. Game date $_worldDate. Speed 1 means one game day is one real day.',
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton(
                onPressed: _busy ? null : () => _run(() => widget.api.post('/api/admin/world/clock/pause'), 'Game clock paused'),
                child: const Text('Pause the clock'),
              ),
              FilledButton(
                onPressed: _busy ? null : () => _run(() => widget.api.post('/api/admin/world/clock/resume'), 'Game clock running again'),
                child: const Text('Start the clock again'),
              ),
              SizedBox(
                width: 140,
                child: TextField(
                  controller: _speed,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(labelText: 'Game speed'),
                ),
              ),
              FilledButton(
                onPressed: _busy
                    ? null
                    : () => _run(
                          () => widget.api.post(
                            '/api/admin/world/clock/speed',
                            body: <String, Object?>{'progression_rate': double.tryParse(_speed.text.trim()) ?? 1},
                          ),
                          'Game speed saved',
                        ),
                child: const Text('Save the speed'),
              ),
            ],
          ),
          const SizedBox(height: 18),
          const Text(
            'Pick a cup and type what 1st, 2nd and 3rd win. The coin is held for that cup. Entry stays free.',
          ),
          const SizedBox(height: 8),
          if (_cups.isEmpty)
            const Text('No cups yet. Create a GTEX competition first.')
          else ...<Widget>[
            DropdownButtonFormField<String>(
              initialValue: _cupId,
              decoration: const InputDecoration(labelText: 'Which cup'),
              items: _cups
                  .map(
                    (Map<String, dynamic> cup) => DropdownMenuItem<String>(
                      value: cup['id']?.toString(),
                      child: Text('${cup['title']} · ${cup['season_label']}'),
                    ),
                  )
                  .toList(),
              onChanged: (String? value) {
                setState(() {
                  _cupId = value;
                  _fillPrize();
                });
              },
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: <Widget>[
                _prizeField('1st prize', _first),
                _prizeField('2nd prize', _second),
                _prizeField('3rd prize', _third),
              ],
            ),
            const SizedBox(height: 8),
            FilledButton(
              onPressed: _busy || _cupId == null
                  ? null
                  : () => _run(
                        () => widget.api.request(
                          'PUT',
                          '/api/admin/national-team-engine/cups/$_cupId/prize',
                          body: <String, Object?>{
                            'first': double.tryParse(_first.text.trim()) ?? 0,
                            'second': double.tryParse(_second.text.trim()) ?? 0,
                            'third': double.tryParse(_third.text.trim()) ?? 0,
                          },
                        ),
                        'Prize saved for this cup',
                      ),
              child: const Text('Put this prize into this cup'),
            ),
          ],
        ],
      ),
    );
  }

  Widget _prizeField(String label, TextEditingController controller) {
    return SizedBox(
      width: 140,
      child: TextField(
        controller: controller,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        decoration: InputDecoration(labelText: label),
      ),
    );
  }
}
