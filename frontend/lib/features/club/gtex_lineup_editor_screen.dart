import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../data/club_lineup_repository.dart';
import '../../data/gte_api_repository.dart';
import '../match/widgets/gtex_matchday_ad_slot.dart';
import '../player_detail/gtex_player_navigator.dart';

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
  String? _selectedSubstituteId;

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
      final List<LineupSquadPlayer> squad = await _repo.fetchSquad(
        widget.clubId,
      );
      final ClubLineupPlan plan = await _repo.fetchLineup(widget.clubId);
      final List<String?> slots = List<String?>.filled(11, null);
      for (int i = 0; i < plan.starterPlayerIds.length && i < 11; i += 1) {
        slots[i] = plan.starterPlayerIds[i];
      }
      setState(() {
        _squad = squad;
        _formation =
            _formations.contains(plan.formation) ? plan.formation : '4-3-3';
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
    for (
      int m = 0;
      m <
          lines
              .sublist(1, lines.length - 1)
              .fold<int>(0, (int a, int b) => a + b);
      m += 1
    ) {
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
    final Set<String> taken =
        _slots.whereType<String>().toSet()..remove(_slots[index]);
    final List<LineupSquadPlayer> available =
        _squad
            .where((LineupSquadPlayer p) => !taken.contains(p.playerId))
            .toList();
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
                  style: TextStyle(
                    color: _text,
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              if (_slots[index] != null)
                ListTile(
                  leading: const Icon(Icons.close, color: _textMuted),
                  title: const Text(
                    'Clear slot',
                    style: TextStyle(color: _textSecondary),
                  ),
                  onTap: () => Navigator.of(context).pop('__clear__'),
                ),
              ...available.map(
                (LineupSquadPlayer p) => ListTile(
                  title: Text(p.name, style: const TextStyle(color: _text)),
                  subtitle:
                      p.position == null
                          ? null
                          : Text(
                            p.position!,
                            style: const TextStyle(color: _textMuted),
                          ),
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
        _squad
            .where((LineupSquadPlayer p) => !taken.contains(p.playerId))
            .toList();
    int poolIndex = 0;
    setState(() {
      for (int i = 0; i < 11; i += 1) {
        if (_slots[i] == null && poolIndex < pool.length) {
          _slots[i] = pool[poolIndex++].playerId;
        }
      }
    });
  }

  List<LineupSquadPlayer> get _substitutes {
    final Set<String> starterIds = _slots.whereType<String>().toSet();
    return _squad
        .where(
          (LineupSquadPlayer player) => !starterIds.contains(player.playerId),
        )
        .toList(growable: false);
  }

  void _selectSubstitute(String playerId) {
    setState(() {
      _selectedSubstituteId =
          _selectedSubstituteId == playerId ? null : playerId;
    });
  }

  void _assignSelectedSubstitute(int index) {
    final String? playerId = _selectedSubstituteId;
    if (playerId == null) {
      _assignSlot(index);
      return;
    }
    setState(() {
      _slots[index] = playerId;
      _selectedSubstituteId = null;
    });
  }

  Future<void> _save() async {
    final List<String> starters = _slots.whereType<String>().toList();
    final Set<String> startSet = starters.toSet();
    final List<String> bench =
        _squad
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
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Lineup saved')));
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
            child: const Text(
              'Auto-fill',
              style: TextStyle(color: _textSecondary),
            ),
          ),
        ],
      ),
      body:
          _loading
              ? const Center(child: CircularProgressIndicator())
              : _error != null
              ? _ErrorState(message: _error!, onRetry: _load)
              : _buildEditor(),
      bottomNavigationBar:
          _loading || _error != null
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
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ),
              ),
    );
  }


  Widget _buildEditor() {
    final List<String> roles = _slotRoles;
    final int selectedCount = _slots.whereType<String>().toSet().length;
    final Widget formationSelector = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const Text(
          'CHOOSE YOUR SHAPE',
          style: TextStyle(color: _textMuted, fontSize: 11, letterSpacing: 1),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: _formations.map((String formation) {
            final bool selected = formation == _formation;
            return Semantics(
              button: true,
              selected: selected,
              label: '$formation formation',
              child: InkWell(
                borderRadius: BorderRadius.circular(9),
                onTap: () => setState(() => _formation = formation),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
                  decoration: BoxDecoration(
                    color: selected
                        ? _green.withValues(alpha: 0.16)
                        : _panel,
                    borderRadius: BorderRadius.circular(9),
                    border: Border.all(
                      color: selected ? _green : _border,
                      width: selected ? 1.5 : 0.7,
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      if (selected) ...<Widget>[
                        const Icon(Icons.check_circle, size: 14, color: _green),
                        const SizedBox(width: 6),
                      ],
                      Text(
                        formation,
                        style: TextStyle(
                          fontFamily: _condensed,
                          color: selected ? _green : _textSecondary,
                          fontSize: 16,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          }).toList(growable: false),
        ),
      ],
    );

    final Widget tacticalPitch = _buildTacticalPitch();
    final Widget startingXiList = ExpansionTile(
      key: const Key('gtex-lineup-list-fallback'),
      tilePadding: const EdgeInsets.symmetric(horizontal: 12),
      childrenPadding: const EdgeInsets.fromLTRB(8, 0, 8, 10),
      collapsedBackgroundColor: _panel,
      backgroundColor: _panel,
      iconColor: _green,
      collapsedIconColor: _textSecondary,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: const BorderSide(color: _border),
      ),
      collapsedShape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: const BorderSide(color: _border),
      ),
      title: const Text(
        'Starting XI · list view',
        style: TextStyle(color: _text, fontWeight: FontWeight.w800),
      ),
      subtitle: const Text(
        'Accessible alternative for assigning each position',
        style: TextStyle(color: _textMuted, fontSize: 11),
      ),
      children: List<Widget>.generate(
        11,
        (int index) => _slotTile(index, roles[index]),
      ),
    );

    final Widget substitutes = GtexLineupSubstitutes(
      players: _substitutes,
      selectedPlayerId: _selectedSubstituteId,
      onSelect: _selectSubstitute,
    );

    final Widget managerCard = Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: _panel,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: _border),
      ),
      child: Row(
        children: <Widget>[
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: const Color(0xFFF0C66B).withValues(alpha: 0.11),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(
              Icons.sports_outlined,
              color: Color(0xFFF0C66B),
            ),
          ),
          const SizedBox(width: 12),
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'MANAGER & COACHING STAFF',
                  style: TextStyle(
                    color: _text,
                    fontWeight: FontWeight.w900,
                    fontSize: 12,
                    letterSpacing: 0.65,
                  ),
                ),
                SizedBox(height: 4),
                Text(
                  'Choose a coach whose tactical style fits this formation.',
                  style: TextStyle(color: _textSecondary, fontSize: 11),
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          OutlinedButton.icon(
            key: const Key('gtex-lineup-open-coaches'),
            onPressed: () => context.push('/coaches'),
            icon: const Icon(Icons.manage_accounts_outlined, size: 17),
            label: const Text('Select'),
          ),
        ],
      ),
    );

    return ListView(
      key: const Key('gtex-tactical-setup-list'),
      padding: const EdgeInsets.fromLTRB(14, 8, 14, 20),
      children: <Widget>[
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: <Color>[Color(0xFF182638), Color(0xFF0D151F)],
            ),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: const Color(0xFF3A4D61)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Text(
                'TACTICAL SETUP',
                style: TextStyle(
                  color: Color(0xFFF0C66B),
                  fontSize: 11,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 1.4,
                ),
              ),
              const SizedBox(height: 5),
              Text(
                _formation,
                style: const TextStyle(
                  color: _text,
                  fontFamily: _condensed,
                  fontSize: 29,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 5),
              Text(
                '$selectedCount of 11 starting positions assigned · ${_substitutes.length} players available for the bench',
                style: const TextStyle(color: _textSecondary, fontSize: 12),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: <Widget>[
                  _setupTag(Icons.grid_3x3, 'Formation'),
                  _setupTag(Icons.groups_2_outlined, 'Starting XI'),
                  _setupTag(Icons.compare_arrows, 'Substitutions'),
                  _setupTag(Icons.sports, 'Manager'),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        managerCard,
        const SizedBox(height: 18),
        formationSelector,
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: _panel,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: _border),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  const Icon(Icons.sports_soccer, color: _green, size: 18),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text(
                      'FORMATION BOARD',
                      style: TextStyle(
                        color: _text,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0.8,
                        fontSize: 12,
                      ),
                    ),
                  ),
                  Text(
                    _selectedSubstituteId == null
                        ? 'Tap a position to edit'
                        : 'Tap a position to assign',
                    style: const TextStyle(color: _green, fontSize: 10),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              tacticalPitch,
              const SizedBox(height: 10),
              startingXiList,
            ],
          ),
        ),
        const SizedBox(height: 14),
        GtexMatchdayAdSlot(placement: 'Pre-match lineup & formation board'),
        const SizedBox(height: 16),
        substitutes,
      ],
    );
  }

  Widget _setupTag(IconData icon, String label) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(7),
        border: Border.all(color: Colors.white.withValues(alpha: 0.09)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(icon, color: _textSecondary, size: 13),
          const SizedBox(width: 5),
          Text(
            label,
            style: const TextStyle(
              color: _textSecondary,
              fontSize: 10,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }

  List<({int index, int count, int ordinal, double y})> get _pitchPositions {
    final List<int> parts = _formation
        .split('-')
        .map((String part) => int.tryParse(part) ?? 0)
        .toList(growable: false);
    if (parts.length < 3 || parts.any((int count) => count <= 0)) {
      return <({int index, int count, int ordinal, double y})>[
        (index: 0, count: 1, ordinal: 0, y: 0.89),
        for (int i = 1; i < 11; i++)
          (index: i, count: 10, ordinal: i - 1, y: 0.52),
      ];
    }

    final List<({int index, int count, int ordinal, double y})> placements =
        <({int index, int count, int ordinal, double y})>[];
    placements.add((index: 0, count: 1, ordinal: 0, y: 0.89));

    final int defenders = parts.first;
    for (int slot = 0; slot < defenders; slot++) {
      placements.add((
        index: 1 + slot,
        count: defenders,
        ordinal: slot,
        y: 0.72,
      ));
    }

    int nextIndex = 1 + defenders;
    final List<int> midfieldRows = parts.sublist(1, parts.length - 1);
    for (int line = 0; line < midfieldRows.length; line++) {
      final int count = midfieldRows[line];
      final double y = midfieldRows.length == 1
          ? 0.49
          : 0.57 - line * (0.22 / (midfieldRows.length - 1));
      for (int slot = 0; slot < count; slot++) {
        placements.add((
          index: nextIndex + slot,
          count: count,
          ordinal: slot,
          y: y,
        ));
      }
      nextIndex += count;
    }

    final int forwards = parts.last;
    for (int slot = 0; slot < forwards; slot++) {
      placements.add((
        index: nextIndex + slot,
        count: forwards,
        ordinal: slot,
        y: 0.19,
      ));
    }
    return placements;
  }

  Widget _buildTacticalPitch() {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints outer) {
        final double width = outer.maxWidth;
        final double height = width / 0.82;
        return SizedBox(
          width: width,
          height: height,
          child: LayoutBuilder(
            builder: (BuildContext context, BoxConstraints bounds) {
              return ClipRRect(
                borderRadius: BorderRadius.circular(10),
                child: Stack(
                  fit: StackFit.expand,
                  children: <Widget>[
                    const Positioned.fill(child: CustomPaint(painter: _LineupPitchPainter())),
                    const Positioned(
                      top: 7,
                      left: 10,
                      child: Text(
                        'ATTACK ↑',
                        style: TextStyle(
                          color: Colors.white70,
                          fontSize: 9,
                          fontWeight: FontWeight.w900,
                          letterSpacing: 1,
                        ),
                      ),
                    ),
                    const Positioned(
                      bottom: 7,
                      right: 10,
                      child: Text(
                        'DEFEND ↓',
                        style: TextStyle(
                          color: Colors.white70,
                          fontSize: 9,
                          fontWeight: FontWeight.w900,
                          letterSpacing: 1,
                        ),
                      ),
                    ),
                    for (final placement in _pitchPositions)
                      _buildPitchMarker(
                        constraints: bounds,
                        index: placement.index,
                        count: placement.count,
                        ordinal: placement.ordinal,
                        y: placement.y,
                      ),
                  ],
                ),
              );
            },
          ),
        );
      },
    );
  }

  Widget _buildPitchMarker({
    required BoxConstraints constraints,
    required int index,
    required int count,
    required int ordinal,
    required double y,
  }) {
    final double markerWidth =
        (constraints.maxWidth / (count + 0.75)).clamp(50.0, 88.0).toDouble();
    final double x = count == 1 ? 0.5 : 0.08 + ordinal * (0.84 / (count - 1));
    final double left = (x * constraints.maxWidth - markerWidth / 2)
        .clamp(1.0, constraints.maxWidth - markerWidth - 1.0)
        .toDouble();
    final double top = (y * constraints.maxHeight - 27)
        .clamp(0.0, constraints.maxHeight - 55.0)
        .toDouble();
    final String role = _slotRoles[index];

    return Positioned(
      left: left,
      top: top,
      width: markerWidth,
      height: 55,
      child: _pitchPlayerMarker(index: index, role: role, width: markerWidth),
    );
  }

  Widget _pitchPlayerMarker({
    required int index,
    required String role,
    required double width,
  }) {
    final String? id = _slots[index];
    final LineupSquadPlayer? player = _playerForId(id);
    final bool filled = player != null;
    final bool selectedTarget = id != null && id == _selectedSubstituteId;
    final String tokenLabel = player?.shirtNumber?.toString() ?? role;
    final List<String> meta = <String>[
      if (player?.rating != null) player!.rating!.toStringAsFixed(0),
      if (player?.form != null && player!.form!.trim().isNotEmpty) player.form!,
    ];
    return Semantics(
      button: true,
      label: '$role · ${player?.name ?? 'Add player'}',
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          key: Key('gtex-pitch-slot-$index'),
          borderRadius: BorderRadius.circular(7),
          onTap: () => _assignSelectedSubstitute(index),
          child: Container(
            padding: const EdgeInsets.fromLTRB(3, 3, 3, 2),
            decoration: BoxDecoration(
              color: selectedTarget
                  ? const Color(0xFF493817)
                  : filled
                      ? const Color(0xE9131D28)
                      : const Color(0xCC07111B),
              borderRadius: BorderRadius.circular(7),
              border: Border.all(
                color: selectedTarget
                    ? const Color(0xFFF0C66B)
                    : filled
                        ? Colors.white.withValues(alpha: 0.36)
                        : _green.withValues(alpha: 0.86),
                width: selectedTarget ? 1.6 : 0.9,
              ),
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: <Widget>[
                Container(
                  constraints: const BoxConstraints(minWidth: 20, minHeight: 16),
                  alignment: Alignment.center,
                  padding: const EdgeInsets.symmetric(horizontal: 3, vertical: 1),
                  decoration: BoxDecoration(
                    color: filled ? _green : _green.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    filled ? tokenLabel : '+',
                    maxLines: 1,
                    style: TextStyle(
                      color: filled ? const Color(0xFF07120D) : _green,
                      fontSize: 9,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  player?.name ?? 'Add ${role.toLowerCase()}',
                  maxLines: 2,
                  textAlign: TextAlign.center,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: _text,
                    fontSize: 8.5,
                    height: 1.0,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                if (meta.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 1),
                  Text(
                    meta.join(' · '),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Color(0xFFF0C66B),
                      fontSize: 7.5,
                      height: 1.0,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  LineupSquadPlayer? _playerForId(String? id) {
    if (id == null) return null;
    for (final LineupSquadPlayer player in _squad) {
      if (player.playerId == id) return player;
    }
    return null;
  }

  Widget _slotTile(int index, String role) {
    final String? id = _slots[index];
    final bool filled = id != null;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: () => _assignSelectedSubstitute(index),
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
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: filled ? _text : _textMuted,
                    fontSize: 15,
                    fontWeight: filled ? FontWeight.w600 : FontWeight.w400,
                  ),
                ),
              ),
              if (filled && GtexPlayerNavigator.tapToOpen(context, id) != null) ...<Widget>[
                IconButton(
                  icon: const Icon(Icons.badge_outlined, size: 18, color: _textSecondary),
                  tooltip: 'Player Profile',
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
                  onPressed: GtexPlayerNavigator.tapToOpen(context, id),
                ),
                const SizedBox(width: 4),
              ],
              Icon(
                filled
                    ? Icons.swap_horiz_rounded
                    : Icons.add_circle_outline_rounded,
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

/// Responsive substitute pattern for the active lineup editor. On narrow
/// screens it uses a two-column grid, so every player remains visible and
/// touchable without relying on an off-screen horizontal row.
class GtexLineupSubstitutes extends StatelessWidget {
  const GtexLineupSubstitutes({
    super.key,
    required this.players,
    required this.selectedPlayerId,
    required this.onSelect,
  });

  final List<LineupSquadPlayer> players;
  final String? selectedPlayerId;
  final ValueChanged<String> onSelect;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      label: 'Substitutes',
      child: Container(
        decoration: BoxDecoration(
          color: _panel,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: _border),
        ),
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const Text(
              'SUBSTITUTES',
              style: TextStyle(
                color: _textMuted,
                fontSize: 11,
                letterSpacing: 1,
              ),
            ),
            const SizedBox(height: 4),
            const Text(
              'Select a substitute, then tap a starter position to assign them.',
              style: TextStyle(color: _textSecondary, fontSize: 12),
            ),
            const SizedBox(height: 10),
            if (players.isEmpty)
              const Text(
                'No substitutes available.',
                style: TextStyle(color: _textMuted),
              )
            else
              LayoutBuilder(
                builder: (BuildContext context, BoxConstraints constraints) {
                  final int columns = constraints.maxWidth >= 560 ? 3 : 2;
                  return GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: players.length,
                    gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: columns,
                      mainAxisSpacing: 8,
                      crossAxisSpacing: 8,
                      childAspectRatio: columns == 2 ? 2.15 : 2.35,
                    ),
                    itemBuilder: (BuildContext context, int index) {
                      final LineupSquadPlayer player = players[index];
                      final bool selected = player.playerId == selectedPlayerId;
                      return Semantics(
                        button: true,
                        selected: selected,
                        label: 'Substitute ${player.name}',
                        child: InkWell(
                          borderRadius: BorderRadius.circular(10),
                          onTap: () => onSelect(player.playerId),
                          child: Ink(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 10,
                              vertical: 8,
                            ),
                            decoration: BoxDecoration(
                              color:
                                  selected
                                      ? _green.withValues(alpha: 0.16)
                                      : _bg,
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(
                                color: selected ? _green : _border,
                              ),
                            ),
                            child: Row(
                              children: <Widget>[
                                Expanded(
                                  child: Text(
                                    player.name,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                      color: _text,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ),
                                if (player.position != null) ...<Widget>[
                                  const SizedBox(width: 6),
                                  Text(
                                    player.position!,
                                    style: const TextStyle(
                                      color: _textMuted,
                                      fontSize: 11,
                                    ),
                                  ),
                                ],
                              ],
                            ),
                          ),
                        ),
                      );
                    },
                  );
                },
              ),
          ],
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
