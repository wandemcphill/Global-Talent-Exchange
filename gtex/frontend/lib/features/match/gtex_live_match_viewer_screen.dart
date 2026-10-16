import 'dart:async';

import 'package:flutter/material.dart';

import '../../data/gte_api_repository.dart';
import '../../data/live_match_repository.dart';

const Color _bg = Color(0xFF0E1217);
const Color _panel = Color(0xFF141A21);
const Color _border = Color(0xFF283039);
const Color _text = Color(0xFFF4F6F8);
const Color _textSecondary = Color(0xFF9AA7B4);
const Color _textMuted = Color(0xFF7F8C99);
const Color _green = Color(0xFF21C77A);
const Color _amber = Color(0xFFE3B23C);
const String _condensed = 'BarlowCondensed';
const List<String> _formations = <String>['4-3-3', '4-4-2', '4-2-3-1', '4-5-1', '5-3-2', '3-5-2'];
const List<String> _mentalities = <String>['attacking', 'balanced', 'defensive'];

/// Live (tick-based) match viewer. The match advances server-side; this polls
/// read-only state. Either user can change their own tactics at any time
/// (non-disruptive: the opponent's view is never touched, the match never
/// pauses). Halftime shows a countdown; both pressing Done resumes early.
class GtexLiveMatchViewerScreen extends StatefulWidget {
  const GtexLiveMatchViewerScreen({
    super.key,
    required this.matchId,
    required this.side,
    required this.baseUrl,
    required this.accessToken,
    this.backendMode = GteBackendMode.live,
  });

  final String matchId;
  final String side; // 'home' | 'away' — the team this user manages
  final String baseUrl;
  final String accessToken;
  final GteBackendMode backendMode;

  @override
  State<GtexLiveMatchViewerScreen> createState() => _GtexLiveMatchViewerScreenState();
}

class _GtexLiveMatchViewerScreenState extends State<GtexLiveMatchViewerScreen> {
  late final LiveMatchRepository _repo = LiveMatchRepository.standard(
    baseUrl: widget.baseUrl,
    accessToken: widget.accessToken,
    mode: widget.backendMode,
  );
  Timer? _poll;
  LiveMatchState? _state;
  String? _error;
  bool _halftimeDoneSent = false;
  bool _settleAttempted = false;
  Map<String, dynamic>? _settlement;

  @override
  void initState() {
    super.initState();
    _refresh();
    _poll = Timer.periodic(const Duration(seconds: 2), (_) => _refresh());
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  Future<void> _refresh() async {
    try {
      final LiveMatchState state = await _repo.fetchState(widget.matchId);
      if (!mounted) return;
      setState(() {
        _state = state;
        _error = null;
        if (state.phase != 'half_time') _halftimeDoneSent = false;
      });
      if (state.isFullTime) {
        // Match is over — stop polling and settle once (initiator only).
        _poll?.cancel();
        await _settleIfNeeded(state);
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = 'Reconnecting…');
    }
  }

  Future<void> _settleIfNeeded(LiveMatchState state) async {
    // Only the initiator (home side) settles; matches the backend ownership gate.
    if (_settleAttempted || widget.side != 'home') return;
    _settleAttempted = true;
    try {
      final Map<String, dynamic> result = await _repo.settleMatch(widget.matchId);
      if (mounted) setState(() => _settlement = result);
    } catch (_) {
      // Settlement is idempotent server-side; a transient failure can be retried
      // on the next viewing. Don't block the full-time UI on it.
    }
  }

  String get _myFormation =>
      widget.side == 'home' ? (_state?.homeFormation ?? '4-3-3') : (_state?.awayFormation ?? '4-3-3');

  Future<void> _openTactics() async {
    String formation = _myFormation;
    String mentality = 'balanced';
    final bool? applied = await showModalBottomSheet<bool>(
      context: context,
      backgroundColor: _panel,
      isScrollControlled: true,
      builder: (BuildContext sheetContext) {
        return StatefulBuilder(
          builder: (BuildContext context, void Function(void Function()) setSheet) {
            return SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    const Text('Your tactics',
                        style: TextStyle(color: _text, fontSize: 17, fontWeight: FontWeight.w700)),
                    const SizedBox(height: 2),
                    const Text('Applies to your team only. The match keeps playing.',
                        style: TextStyle(color: _textMuted, fontSize: 12)),
                    const SizedBox(height: 14),
                    const Text('FORMATION', style: TextStyle(color: _textMuted, fontSize: 11, letterSpacing: 1)),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: _formations.map((String f) {
                        final bool sel = f == formation;
                        return GestureDetector(
                          onTap: () => setSheet(() => formation = f),
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 7),
                            decoration: BoxDecoration(
                              color: sel ? _green.withValues(alpha: 0.16) : _bg,
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: sel ? _green : _border, width: sel ? 1.5 : 0.5),
                            ),
                            child: Text(f,
                                style: TextStyle(
                                    fontFamily: _condensed,
                                    color: sel ? _green : _textSecondary,
                                    fontSize: 15,
                                    fontWeight: FontWeight.w800)),
                          ),
                        );
                      }).toList(growable: false),
                    ),
                    const SizedBox(height: 16),
                    const Text('MENTALITY', style: TextStyle(color: _textMuted, fontSize: 11, letterSpacing: 1)),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      children: _mentalities.map((String m) {
                        final bool sel = m == mentality;
                        return GestureDetector(
                          onTap: () => setSheet(() => mentality = m),
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 7),
                            decoration: BoxDecoration(
                              color: sel ? _amber.withValues(alpha: 0.16) : _bg,
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: sel ? _amber : _border, width: sel ? 1.5 : 0.5),
                            ),
                            child: Text(m[0].toUpperCase() + m.substring(1),
                                style: TextStyle(color: sel ? _amber : _textSecondary, fontWeight: FontWeight.w700)),
                          ),
                        );
                      }).toList(growable: false),
                    ),
                    const SizedBox(height: 18),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton(
                        style: FilledButton.styleFrom(
                            backgroundColor: _green, foregroundColor: const Color(0xFF06140C)),
                        onPressed: () => Navigator.of(sheetContext).pop(true),
                        child: const Text('Apply changes'),
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
    if (applied == true) {
      try {
        final LiveMatchState state = await _repo.setTactics(
          widget.matchId,
          side: widget.side,
          formation: formation,
          mentality: mentality,
        );
        if (mounted) setState(() => _state = state);
      } catch (_) {
        if (mounted) {
          ScaffoldMessenger.of(context)
              .showSnackBar(const SnackBar(content: Text("Couldn't apply tactics. Try again.")));
        }
      }
    }
  }

  Future<void> _halftimeDone() async {
    setState(() => _halftimeDoneSent = true);
    try {
      final LiveMatchState state = await _repo.markHalftimeReady(widget.matchId, side: widget.side);
      if (mounted) setState(() => _state = state);
    } catch (_) {
      if (mounted) setState(() => _halftimeDoneSent = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final LiveMatchState? s = _state;
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(
        backgroundColor: _bg,
        foregroundColor: _text,
        elevation: 0,
        title: const Text('Live match'),
        actions: <Widget>[
          if (s != null && !s.isFullTime)
            TextButton.icon(
              onPressed: _openTactics,
              icon: const Icon(Icons.dashboard_customize_rounded, size: 18, color: _green),
              label: const Text('Tactics', style: TextStyle(color: _green)),
            ),
        ],
      ),
      body: s == null
          ? Center(child: _error == null ? const CircularProgressIndicator() : Text(_error!, style: const TextStyle(color: _textSecondary)))
          : Stack(
              children: <Widget>[
                _matchBody(s),
                if (s.isHalftime) _halftimeOverlay(s),
              ],
            ),
    );
  }

  Widget _matchBody(LiveMatchState s) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: <Widget>[
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(color: _panel, borderRadius: BorderRadius.circular(14), border: Border.all(color: _border)),
          child: Column(
            children: <Widget>[
              Text(
                s.isFullTime ? 'FULL TIME' : "${s.minute}'  ·  ${_phaseLabel(s.phase)}",
                style: const TextStyle(color: _amber, fontFamily: _condensed, fontSize: 14, fontWeight: FontWeight.w800, letterSpacing: 1),
              ),
              const SizedBox(height: 10),
              Row(
                children: <Widget>[
                  Expanded(child: _teamSide(s.homeName, s.homeFormation, widget.side == 'home')),
                  Text('${s.homeScore} - ${s.awayScore}',
                      style: const TextStyle(color: _text, fontFamily: _condensed, fontSize: 34, fontWeight: FontWeight.w900)),
                  Expanded(child: _teamSide(s.awayName, s.awayFormation, widget.side == 'away', alignEnd: true)),
                ],
              ),
            ],
          ),
        ),
        if (s.isFullTime && _settlement != null) ...<Widget>[
          const SizedBox(height: 16),
          _settlementCard(_settlement!),
        ],
        const SizedBox(height: 16),
        const Text('TIMELINE', style: TextStyle(color: _textMuted, fontSize: 11, letterSpacing: 1)),
        const SizedBox(height: 8),
        ...s.events.reversed.take(20).map(_eventRow),
      ],
    );
  }

  Widget _teamSide(String name, String formation, bool isYou, {bool alignEnd = false}) {
    return Column(
      crossAxisAlignment: alignEnd ? CrossAxisAlignment.end : CrossAxisAlignment.start,
      children: <Widget>[
        Text(name, maxLines: 1, overflow: TextOverflow.ellipsis,
            style: const TextStyle(color: _text, fontWeight: FontWeight.w700, fontSize: 15)),
        const SizedBox(height: 2),
        Text(isYou ? '$formation · you' : formation,
            style: TextStyle(color: isYou ? _green : _textMuted, fontSize: 11)),
      ],
    );
  }

  Widget _eventRow(Map<String, dynamic> e) {
    final String type = (e['type'] ?? '').toString();
    final int minute = (e['minute'] as num?)?.toInt() ?? 0;
    late final IconData icon;
    late final Color color;
    late final String label;
    switch (type) {
      case 'goal':
        icon = Icons.sports_soccer; color = _green; label = 'Goal — ${e['team'] ?? ''} (${e['score'] ?? ''})';
        break;
      case 'tactical_change':
        icon = Icons.dashboard_customize_rounded; color = _amber;
        label = 'Tactical change — ${e['side'] ?? ''} → ${e['formation'] ?? ''}';
        break;
      case 'half_time':
        icon = Icons.timer_outlined; color = _textSecondary; label = 'Half time';
        break;
      case 'second_half':
        icon = Icons.play_arrow_rounded; color = _textSecondary; label = 'Second half';
        break;
      case 'full_time':
        icon = Icons.flag_rounded; color = _textSecondary; label = 'Full time';
        break;
      default:
        icon = Icons.circle; color = _textMuted; label = type;
    }
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        children: <Widget>[
          SizedBox(width: 32, child: Text("$minute'", style: const TextStyle(color: _textMuted, fontSize: 12))),
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 8),
          Expanded(child: Text(label, style: const TextStyle(color: _textSecondary, fontSize: 13))),
        ],
      ),
    );
  }

  Widget _halftimeOverlay(LiveMatchState s) {
    final int remaining = s.halftimeSecondsRemaining ?? 0;
    final bool waiting = _halftimeDoneSent || s.halftimeReady.contains(widget.side);
    return Positioned.fill(
      child: ColoredBox(
        color: const Color(0xCC0E1217),
        child: Center(
          child: Container(
            margin: const EdgeInsets.all(28),
            padding: const EdgeInsets.all(22),
            decoration: BoxDecoration(color: _panel, borderRadius: BorderRadius.circular(16), border: Border.all(color: _border)),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                const Text('HALF TIME',
                    style: TextStyle(color: _amber, fontFamily: _condensed, fontSize: 22, fontWeight: FontWeight.w900, letterSpacing: 1)),
                const SizedBox(height: 6),
                Text('Back to the match in ${remaining}s',
                    style: const TextStyle(color: _textSecondary, fontSize: 13)),
                const SizedBox(height: 8),
                Text('${s.homeScore} - ${s.awayScore}',
                    style: const TextStyle(color: _text, fontFamily: _condensed, fontSize: 30, fontWeight: FontWeight.w900)),
                const SizedBox(height: 16),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    OutlinedButton.icon(
                      onPressed: _openTactics,
                      icon: const Icon(Icons.dashboard_customize_rounded, size: 18),
                      label: const Text('Adjust tactics'),
                    ),
                    const SizedBox(width: 10),
                    FilledButton(
                      style: FilledButton.styleFrom(backgroundColor: _green, foregroundColor: const Color(0xFF06140C)),
                      onPressed: waiting ? null : _halftimeDone,
                      child: Text(waiting ? 'Waiting for opponent…' : 'Done'),
                    ),
                  ],
                ),
                if (s.halftimeReady.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 10),
                  Text('${s.halftimeReady.length}/2 ready',
                      style: const TextStyle(color: _textMuted, fontSize: 12)),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _settlementCard(Map<String, dynamic> settlement) {
    final String result = (settlement['result'] ?? '').toString();
    final int remaining = (settlement['free_matches_remaining'] as num?)?.toInt() ?? 0;
    final bool charged = settlement['charge_required_now'] == true;
    final Color color = result == 'win'
        ? _green
        : result == 'loss'
            ? const Color(0xFFE3563C)
            : _amber;
    final String headline = result == 'win'
        ? 'You won'
        : result == 'loss'
            ? 'You lost'
            : 'Draw';
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: _panel,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withValues(alpha: 0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(headline,
              style: TextStyle(
                  color: color, fontFamily: _condensed, fontSize: 20, fontWeight: FontWeight.w900, letterSpacing: 1)),
          const SizedBox(height: 6),
          Text(
            charged
                ? 'Fan Coin entry fee applied. $remaining free matches left.'
                : 'Free match. $remaining free matches left.',
            style: const TextStyle(color: _textSecondary, fontSize: 13),
          ),
        ],
      ),
    );
  }

  String _phaseLabel(String phase) {
    switch (phase) {
      case 'first_half':
        return 'First half';
      case 'second_half':
        return 'Second half';
      case 'half_time':
        return 'Half time';
      case 'pre_match':
        return 'Kick off soon';
      default:
        return phase;
    }
  }
}
