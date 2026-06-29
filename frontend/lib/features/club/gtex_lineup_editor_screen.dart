import 'package:flutter/material.dart';

import '../../data/club_lineup_repository.dart';
import '../../data/gte_api_repository.dart';

const Color _bg = Color(0xFF0E1217);
const Color _panel = Color(0xFF141A21);
const Color _border = Color(0xFF283039);
const Color _text = Color(0xFFF4F6F8);
const Color _textSecondary = Color(0xFF9AA7B4);
const Color _textMuted = Color(0xFF7F8C99);
const Color _green = Color(0xFF21C77A);
const Color _pitch = Color(0xFF0F3D2A);

const String _condensed = 'BarlowCondensed';

const List<String> _formations = <String>[
  '4-3-3',
  '4-4-2',
  '4-2-3-1',
  '4-5-1',
  '5-3-2',
  '3-5-2',
];

/// Owner-facing lineup editor: pick a formation, tap-to-assign the starting XI
/// from the club squad, and save. Consumed by the match engine via
/// PUT /clubs/{id}/lineup (with safe fallback if the saved XI can't be fielded).
class GtexLineupEditorScreen extends StatefulWidget {
  const GtexLineupEditorScreen({
    super.key,
    required this.clubId,
    required this.baseUrl,
    required this.accessToken,
    this.backendMode = GteBackendMode.live,
  });

  final String clubId;
  final String baseUrl;
  final String accessToken;
  final GteBackendMode backendMode;

  @override
  State<GtexLineupEditorScreen> createState() => _GtexLineupEditorScreenState();
}

class _GtexLineupEditorScreenState extends State<GtexLineupEditorScreen> {
  late final ClubLineupRepository _repo = ClubLineupRepository.standard(
    baseUrl: widget.baseUrl,
    accessToken: widget.accessToken,
    mode: widget.backendMode,
  );

  bool _loading = true;
  String? _error;
  bool _saving = false;

  String _formation = '4-3-3';
  List<LineupSquadPlayer> _squad = const <LineupSquadPlayer>[];
  List<String?> _slots = List<String?>.filled(11, null);

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final List<LineupSquadPlayer> squad = await _repo.fetchSquad(widget.clubId);
      final ClubLineupPlan plan = await _repo.fetchLineup(widget.clubId);
      final List<String?> slots = List<String?>.filled(11, null);
      for (int i = 0; i < plan.starterPlayerIds.length && i < 11; i += 1) {
        slots[i] = plan.starterPlayerIds[i];
      }
      setState(() {
        _squad = squad;
        _formation = _formations.contains(plan.formation) ? plan.formation : '4-3-3';
        _slots = slots;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = 'Could not load your squad and lineup.';
        _loading = false;
      });
    }
  }

  List<String> get _slotRoles {
    final List<int> lines = _formation.split('-').map(int.parse).toList();
    final List<String> roles = <String>['GK'];
    for (int d = 0; d < lines.first; d += 1) {
      roles.add('DEF');
    }
    for (int m = 0; m < lines.sublist(1, lines.length - 1).fold<int>(0, (int a, int b) => a + b); m += 1) {
      roles.add('MID');
    }
    for (int f = 0; f < lines.last; f += 1) {
      roles.add('FWD');
    }
    return roles;
  }

  String _playerName(String? id) {
    if (id == null) return 'Tap to assign';
    return _squad
        .firstWhere(
          (LineupSquadPlayer p) => p.playerId == id,
          orElse: () => LineupSquadPlayer(playerId: id, name: 'Unknown'),
        )
        .name;
  }

  Future<void> _assignSlot(int index) async {
    final Set<String> taken = _slots.whereType<String>().toSet()..remove(_slots[index]);
    final List<LineupSquadPlayer> available =
        _squad.where((LineupSquadPlayer p) => !taken.contains(p.playerId)).toList();
    final String? chosen = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: _panel,
      isScrollControlled: true,
      builder: (BuildContext context) {
        return SafeArea(
          child: ListView(
            shrinkWrap: true,
            children: <Widget>[
              const Padding(
                padding: EdgeInsets.all(14),
                child: Text(
                  'Assign player',
                  style: TextStyle(color: _text, fontSize: 16, fontWeight: FontWeight.w700),
                ),
              ),
              if (_slots[index] != null)
                ListTile(
                  leading: const Icon(Icons.close, color: _textMuted),
                  title: const Text('Clear slot', style: TextStyle(color: _textSecondary)),
                  onTap: () => Navigator.of(context).pop('__clear__'),
                ),
              ...available.map(
                (LineupSquadPlayer p) => ListTile(
                  title: Text(p.name, style: const TextStyle(color: _text)),
                  subtitle: p.position == null
                      ? null
                      : Text(p.position!, style: const TextStyle(color: _textMuted)),
                  onTap: () => Navigator.of(context).pop(p.playerId),
                ),
              ),
            ],
          ),
        );
      },
    );
    if (chosen == null) return;
    setState(() {
      _slots[index] = chosen == '__clear__' ? null : chosen;
    });
  }

  void _autoFill() {
    final Set<String> taken = _slots.whereType<String>().toSet();
    final List<LineupSquadPlayer> pool =
        _squad.where((LineupSquadPlayer p) => !taken.contains(p.playerId)).toList();
    int poolIndex = 0;
    setState(() {
      for (int i = 0; i < 11; i += 1) {
        if (_slots[i] == null && poolIndex < pool.length) {
          _slots[i] = pool[poolIndex++].playerId;
        }
      }
    });
  }

  Future<void> _save() async {
    final List<String> starters = _slots.whereType<String>().toList();
    final Set<String> startSet = starters.toSet();
    final List<String> bench = _squad
        .where((LineupSquadPlayer p) => !startSet.contains(p.playerId))
        .map((LineupSquadPlayer p) => p.playerId)
        .take(7)
        .toList();
    setState(() => _saving = true);
    try {
      await _repo.saveLineup(
        widget.clubId,
        formation: _formation,
        starterPlayerIds: starters,
        benchPlayerIds: bench,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Lineup saved')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Couldn't save the lineup. Try again.")),
      );
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(
        backgroundColor: _bg,
        foregroundColor: _text,
        elevation: 0,
        title: const Text('Lineup and formation'),
        actions: <Widget>[
          TextButton(
            onPressed: _loading || _saving ? null : _autoFill,
            child: const Text('Auto-fill', style: TextStyle(color: _textSecondary)),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
          ? _ErrorState(message: _error!, onRetry: _load)
          : _buildEditor(),
      bottomNavigationBar: _loading || _error != null
          ? null
          : SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: FilledButton(
                  onPressed: _saving ? null : _save,
                  style: FilledButton.styleFrom(
                    backgroundColor: _green,
                    foregroundColor: const Color(0xFF06140C),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                  child: Text(
                    _saving ? 'Saving…' : 'Save lineup',
                    style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800),
                  ),
                ),
              ),
            ),
    );
  }

  Widget _buildEditor() {
    final List<String> roles = _slotRoles;
    return ListView(
      padding: const EdgeInsets.fromLTRB(14, 8, 14, 8),
      children: <Widget>[
        const Text('FORMATION', style: TextStyle(color: _textMuted, fontSize: 11, letterSpacing: 1)),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: _formations.map((String f) {
            final bool selected = f == _formation;
            return GestureDetector(
              onTap: () => setState(() => _formation = f),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                decoration: BoxDecoration(
                  color: selected ? _green.withValues(alpha: 0.16) : _panel,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: selected ? _green : _border, width: selected ? 1.5 : 0.5),
                ),
                child: Text(
                  f,
                  style: TextStyle(
                    fontFamily: _condensed,
                    color: selected ? _green : _textSecondary,
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            );
          }).toList(growable: false),
        ),
        const SizedBox(height: 18),
        Container(
          decoration: BoxDecoration(
            color: _pitch.withValues(alpha: 0.35),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: _border),
          ),
          padding: const EdgeInsets.all(8),
          child: Column(
            children: List<Widget>.generate(11, (int i) => _slotTile(i, roles[i])),
          ),
        ),
      ],
    );
  }

  Widget _slotTile(int index, String role) {
    final String? id = _slots[index];
    final bool filled = id != null;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: () => _assignSlot(index),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 6),
          child: Row(
            children: <Widget>[
              Container(
                width: 42,
                padding: const EdgeInsets.symmetric(vertical: 4),
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: _bg,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: _border),
                ),
                child: Text(
                  role,
                  style: const TextStyle(
                    fontFamily: _condensed,
                    color: _textSecondary,
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  _playerName(id),
                  style: TextStyle(
                    color: filled ? _text : _textMuted,
                    fontSize: 15,
                    fontWeight: filled ? FontWeight.w600 : FontWeight.w400,
                  ),
                ),
              ),
              Icon(
                filled ? Icons.swap_horiz_rounded : Icons.add_circle_outline_rounded,
                color: filled ? _textMuted : _green,
                size: 20,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Text(message, style: const TextStyle(color: _text)),
          const SizedBox(height: 12),
          OutlinedButton(onPressed: onRetry, child: const Text('Retry')),
        ],
      ),
    );
  }
}
