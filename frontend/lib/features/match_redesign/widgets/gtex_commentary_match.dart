import 'dart:async';

import 'package:flutter/material.dart';

import '../data/gtex_match_models.dart';
import 'gtex_2d_pitch.dart';
import 'gtex_match_visual_tokens.dart';

class GtexLiveMatchStage extends StatefulWidget {
  const GtexLiveMatchStage({
    super.key,
    required this.match,
    required this.onPlayerSelected,
  });

  final GtexLiveMatchState match;
  final ValueChanged<String> onPlayerSelected;

  @override
  State<GtexLiveMatchStage> createState() => _GtexLiveMatchStageState();
}

class _GtexLiveMatchStageState extends State<GtexLiveMatchStage> {
  final CommentaryReveal _reveal = CommentaryReveal();
  List<GtexPitchPlayer>? _frozenPlayers;
  GtexPitchBall? _frozenBall;
  bool _freezePitch = false;
  bool _pitchOn = false;
  Timer? _linger;

  @override
  void initState() {
    super.initState();
    _reveal.sync(widget.match.timeline, initial: true, onChanged: _onReveal, mounted: () => mounted);
    _pitchOn = _reveal.holding;
  }

  @override
  void didUpdateWidget(GtexLiveMatchStage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.match.timeline.length != widget.match.timeline.length) {
      final List<CommentaryLine> incoming = commentaryScript(widget.match.timeline);
      if (incoming.isNotEmpty && incoming.last.holdBefore && incoming.length > _reveal.script.length) {
        _frozenPlayers = oldWidget.match.pitchPlayers;
        _frozenBall = oldWidget.match.ball;
        _freezePitch = true;
      }
      _reveal.sync(widget.match.timeline, initial: false, onChanged: _onReveal, mounted: () => mounted);
      if (_reveal.holding) {
        _linger?.cancel();
        _pitchOn = true;
      }
    }
  }

  @override
  void dispose() {
    _linger?.cancel();
    _reveal.dispose();
    super.dispose();
  }

  void _onReveal() {
    if (_reveal.holding) {
      _linger?.cancel();
      _pitchOn = true;
    } else if (_pitchOn) {
      _freezePitch = false;
      _linger?.cancel();
      _linger = Timer(kHighlightPicture, () {
        if (!mounted || _reveal.holding) return;
        setState(() => _pitchOn = false);
      });
    }
    if (mounted) setState(() {});
  }

  GtexLiveMatchState get _pitchMatch {
    if (_freezePitch && _reveal.holding && _frozenPlayers != null) {
      return widget.match.copyWith(
        pitchPlayers: _frozenPlayers,
        ball: _frozenBall,
        replaceBall: true,
      );
    }
    return widget.match;
  }

  @override
  Widget build(BuildContext context) {
    final String caption = _reveal.sentence ??
        '${widget.match.home.shortName} ${widget.match.home.formation} against ${widget.match.away.shortName} ${widget.match.away.formation}.';
    if (!_pitchOn) {
      return GtexCommentaryMatch(
        match: widget.match,
        revealedLines: _reveal.shown,
        holding: _reveal.holding,
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Expanded(
          child: Gtex2dPitch(
            match: _pitchMatch,
            onPlayerSelected: widget.onPlayerSelected,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          caption,
          key: const Key('classic-caption'),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(color: GtexMatchVisualTokens.textPrimary, fontSize: 13),
        ),
        if (_reveal.holding)
          const Padding(
            padding: EdgeInsets.only(top: 4),
            child: Text(
              'Highlight',
              key: Key('commentary-hold'),
              style: TextStyle(color: GtexMatchVisualTokens.amber, fontSize: 11, fontWeight: FontWeight.w800),
            ),
          ),
      ],
    );
  }
}

/// How long a chance, shot, goal, card, or foul stays on screen before the outcome.
const Duration kCommentaryActionHold = Duration(seconds: 5);

/// How long the 2D picture stays after the finish, before commentary takes over again.
const Duration kHighlightPicture = Duration(seconds: 4);

bool commentaryHoldsForRead(GtexPitchEventType type) {
  switch (type) {
    case GtexPitchEventType.shot:
    case GtexPitchEventType.goal:
    case GtexPitchEventType.save:
    case GtexPitchEventType.foul:
    case GtexPitchEventType.yellowCard:
    case GtexPitchEventType.redCard:
      return true;
    case GtexPitchEventType.kickoff:
    case GtexPitchEventType.pass:
    case GtexPitchEventType.tackle:
    case GtexPitchEventType.substitution:
    case GtexPitchEventType.tacticalChange:
      return false;
  }
}

String commentaryBuildup(GtexMatchTimelineEvent event) {
  final String actor = (event.playerName ?? '').trim();
  if (actor.isNotEmpty) {
    return '$actor is about to act. The move is on.';
  }
  return 'The move is on. Something is about to happen.';
}

class CommentaryLine {
  const CommentaryLine({
    required this.text,
    required this.minute,
    required this.holdBefore,
    this.teamId,
    this.teamName,
  });

  final String text;
  final int minute;
  final bool holdBefore;
  final String? teamId;
  final String? teamName;
}

List<CommentaryLine> commentaryScript(List<GtexMatchTimelineEvent> events) {
  final List<CommentaryLine> lines = <CommentaryLine>[];
  for (final GtexMatchTimelineEvent event in events) {
    if (commentaryHoldsForRead(event.type)) {
      lines.add(
        CommentaryLine(
          text: commentaryBuildup(event),
          minute: event.minute,
          holdBefore: false,
          teamId: event.teamId,
          teamName: event.teamName,
        ),
      );
      lines.add(
        CommentaryLine(
          text: event.description.trim().isEmpty ? event.title : event.description,
          minute: event.minute,
          holdBefore: true,
          teamId: event.teamId,
          teamName: event.teamName,
        ),
      );
    } else {
      final String sentence = event.description.trim().isEmpty ? event.title : event.description;
      lines.add(
        CommentaryLine(
          text: sentence,
          minute: event.minute,
          holdBefore: false,
          teamId: event.teamId,
          teamName: event.teamName,
        ),
      );
    }
  }
  return lines;
}

class CommentaryReveal {
  Timer? _hold;
  List<CommentaryLine> script = const <CommentaryLine>[];
  int visible = 0;

  List<CommentaryLine> get shown => script.take(visible).toList(growable: false);
  bool get holding => visible < script.length && script[visible].holdBefore;
  String? get sentence => shown.isEmpty ? null : shown.last.text;

  void dispose() {
    _hold?.cancel();
  }

  void sync(
    List<GtexMatchTimelineEvent> events, {
    required bool initial,
    required VoidCallback onChanged,
    required bool Function() mounted,
  }) {
    _hold?.cancel();
    final List<CommentaryLine> next = commentaryScript(events);
    if (initial) {
      script = next;
      visible = next.length;
      if (next.isNotEmpty && next.last.holdBefore) {
        visible = next.length - 1;
      }
      _arm(onChanged, mounted);
      return;
    }
    script = next;
    if (visible > next.length) {
      visible = next.length;
    }
    _drain();
    _arm(onChanged, mounted);
  }

  void _drain() {
    while (visible < script.length && !script[visible].holdBefore) {
      visible += 1;
    }
  }

  void _arm(VoidCallback onChanged, bool Function() mounted) {
    if (visible >= script.length || !script[visible].holdBefore) {
      return;
    }
    _hold = Timer(kCommentaryActionHold, () {
      if (!mounted()) return;
      visible += 1;
      _drain();
      onChanged();
      _arm(onChanged, mounted);
    });
  }
}

class GtexCommentaryMatch extends StatefulWidget {
  const GtexCommentaryMatch({
    super.key,
    required this.match,
    this.revealedLines,
    this.holding = false,
  });

  final GtexLiveMatchState match;
  final List<CommentaryLine>? revealedLines;
  final bool holding;

  @override
  State<GtexCommentaryMatch> createState() => _GtexCommentaryMatchState();
}

class _GtexCommentaryMatchState extends State<GtexCommentaryMatch> {
  final CommentaryReveal _reveal = CommentaryReveal();

  bool get _driven => widget.revealedLines != null;

  @override
  void initState() {
    super.initState();
    if (!_driven) {
      _reveal.sync(widget.match.timeline, initial: true, onChanged: _onReveal, mounted: () => mounted);
    }
  }

  @override
  void didUpdateWidget(GtexCommentaryMatch oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_driven) {
      _reveal.dispose();
      return;
    }
    if (oldWidget.match.timeline.length != widget.match.timeline.length) {
      _reveal.sync(widget.match.timeline, initial: false, onChanged: _onReveal, mounted: () => mounted);
    }
  }

  @override
  void dispose() {
    _reveal.dispose();
    super.dispose();
  }

  void _onReveal() {
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final List<CommentaryLine> shown = widget.revealedLines ?? _reveal.shown;
    final bool holding = widget.revealedLines != null ? widget.holding : _reveal.holding;
    return Row(
      key: const Key('commentary-only'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Expanded(
          flex: 3,
          child: _Feed(lines: shown, holding: holding, match: widget.match),
        ),
        const SizedBox(width: 12),
        Expanded(
          flex: 2,
          child: _MatchBoard(match: widget.match),
        ),
      ],
    );
  }
}

class _Feed extends StatelessWidget {
  const _Feed({required this.lines, required this.holding, required this.match});

  final List<CommentaryLine> lines;
  final bool holding;
  final GtexLiveMatchState match;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: GtexMatchVisualTokens.panelDecoration(),
      child: ListView(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 16),
        children: [
          Text(
            '${match.minute}\'  ${match.home.shortName} ${match.home.score}–${match.away.score} ${match.away.shortName}',
            style: const TextStyle(
              color: GtexMatchVisualTokens.amber,
              fontWeight: FontWeight.w900,
              letterSpacing: 0.6,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            '${match.home.formation}  /  ${match.away.formation}',
            style: const TextStyle(color: GtexMatchVisualTokens.textSecondary, fontSize: 12),
          ),
          const SizedBox(height: 12),
          if (lines.isEmpty)
            const Text(
              'The sides are taking their shape. Commentary starts with the first action.',
              style: TextStyle(color: GtexMatchVisualTokens.textSecondary),
            ),
          for (final CommentaryLine line in lines)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Text(
                _commentaryRow(match, line),
                key: Key('commentary-line-${line.minute}-${line.text.hashCode}'),
                style: const TextStyle(
                  color: GtexMatchVisualTokens.textPrimary,
                  fontSize: 15,
                  height: 1.35,
                ),
              ),
            ),
          if (holding)
            const Padding(
              padding: EdgeInsets.only(top: 4),
              child: Text(
                'Reading the move…',
                key: Key('commentary-hold'),
                style: TextStyle(
                  color: GtexMatchVisualTokens.amber,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _MatchBoard extends StatelessWidget {
  const _MatchBoard({required this.match});

  final GtexLiveMatchState match;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: EdgeInsets.zero,
      children: [
        _TacticCard(team: match.home),
        const SizedBox(height: 8),
        _TacticCard(team: match.away),
        const SizedBox(height: 8),
        _StatsCard(match: match),
      ],
    );
  }
}

class _TacticCard extends StatelessWidget {
  const _TacticCard({required this.team});

  final GtexMatchTeam team;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: GtexMatchVisualTokens.panelDecoration(),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${team.shortName}  ${team.formation}',
              style: const TextStyle(
                color: GtexMatchVisualTokens.textPrimary,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Mentality  ${team.mentality ?? 'not filed'}',
              key: Key('tactic-mentality-${team.id}'),
              style: const TextStyle(color: GtexMatchVisualTokens.textSecondary, fontSize: 12),
            ),
            const SizedBox(height: 4),
            Text(
              'Press ${_filed(team.press)}   Line ${_filed(team.defensiveLine)}   Width ${_filed(team.width)}   Tempo ${_filed(team.tempo)}',
              key: Key('tactic-shape-${team.id}'),
              style: const TextStyle(color: GtexMatchVisualTokens.textSecondary, fontSize: 12),
            ),
            if (team.instructionSummary.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(
                team.instructionSummary.join(' · '),
                style: const TextStyle(color: GtexMatchVisualTokens.textSecondary, fontSize: 12),
              ),
            ],
            const SizedBox(height: 8),
            ..._formationXi(team),
          ],
        ),
      ),
    );
  }
}

String _filed(int? value) => value == null ? 'not filed' : '$value';

String _commentarySide(GtexLiveMatchState match, CommentaryLine line) {
  final String filed = (line.teamName ?? '').trim();
  if (filed.isNotEmpty) return filed;
  if (line.teamId != null && line.teamId == match.home.id) return match.home.shortName;
  if (line.teamId != null && line.teamId == match.away.id) return match.away.shortName;
  return '';
}

String _commentaryRow(GtexLiveMatchState match, CommentaryLine line) {
  final String side = _commentarySide(match, line);
  final String lead = side.isEmpty ? "${line.minute}'" : "${line.minute}'  $side";
  return '$lead  ${line.text}';
}

bool _isKeeper(GtexLineupPlayer player) {
  final String role = player.position.toLowerCase();
  return role == 'gk' || role == 'goalkeeper' || role.contains('goal');
}

/// Split a full XI into the formation's lines. A short or unmatched sheet stays one list.
List<List<GtexLineupPlayer>> formationRows(GtexMatchTeam team) {
  final List<GtexLineupPlayer> players = team.players.take(11).toList(growable: false);
  final List<int> parts = team.formation
      .split('-')
      .map((String part) => int.tryParse(part.trim()) ?? 0)
      .where((int count) => count > 0)
      .toList(growable: false);
  final int outfield = parts.fold<int>(0, (int sum, int count) => sum + count);
  if (parts.length < 2 || (outfield != players.length && outfield != players.length - 1)) {
    return <List<GtexLineupPlayer>>[players];
  }
  var ordered = players;
  if (outfield == players.length - 1) {
    final int keeperIndex = players.indexWhere(_isKeeper);
    if (keeperIndex > 0) {
      final GtexLineupPlayer keeper = players[keeperIndex];
      ordered = <GtexLineupPlayer>[
        keeper,
        ...players.where((GtexLineupPlayer player) => player.id != keeper.id),
      ];
    }
    final List<List<GtexLineupPlayer>> rows = <List<GtexLineupPlayer>>[
      <GtexLineupPlayer>[ordered.first],
    ];
    var cursor = 1;
    for (final int count in parts) {
      if (cursor + count > ordered.length) return <List<GtexLineupPlayer>>[players];
      rows.add(ordered.sublist(cursor, cursor + count));
      cursor += count;
    }
    return rows;
  }
  final List<List<GtexLineupPlayer>> rows = <List<GtexLineupPlayer>>[];
  var cursor = 0;
  for (final int count in parts) {
    rows.add(ordered.sublist(cursor, cursor + count));
    cursor += count;
  }
  return rows;
}

List<Widget> _formationXi(GtexMatchTeam team) {
  final List<List<GtexLineupPlayer>> rows = formationRows(team);
  if (rows.length <= 1) {
    return <Widget>[
      for (final GtexLineupPlayer player in team.players.take(11))
        Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: _PlayerRow(player: player),
        ),
    ];
  }
  final List<String> labels = _lineLabels(team.formation, rows.length);
  final List<Widget> widgets = <Widget>[];
  for (var index = 0; index < rows.length; index += 1) {
    widgets.add(
      Padding(
        padding: const EdgeInsets.only(top: 4, bottom: 2),
        child: Text(
          labels[index],
          key: Key('lineup-line-${team.id}-$index'),
          style: const TextStyle(
            color: GtexMatchVisualTokens.amber,
            fontSize: 10,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.4,
          ),
        ),
      ),
    );
    for (final GtexLineupPlayer player in rows[index]) {
      widgets.add(
        Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: _PlayerRow(player: player),
        ),
      );
    }
  }
  return widgets;
}

List<String> _lineLabels(String formation, int rowCount) {
  final List<int> parts = formation
      .split('-')
      .map((String part) => int.tryParse(part.trim()) ?? 0)
      .where((int count) => count > 0)
      .toList(growable: false);
  final List<String> labels = <String>[];
  final bool keeperRow = rowCount == parts.length + 1;
  if (keeperRow) labels.add('GK');
  for (var index = 0; index < parts.length; index += 1) {
    final String role = index == 0
        ? 'DEF'
        : index == parts.length - 1
            ? 'FWD'
            : 'MID';
    labels.add('$role ${parts[index]}');
  }
  if (labels.length != rowCount) {
    return List<String>.generate(rowCount, (int index) => 'LINE ${index + 1}');
  }
  return labels;
}

class _PlayerRow extends StatelessWidget {
  const _PlayerRow({required this.player});

  final GtexLineupPlayer player;

  @override
  Widget build(BuildContext context) {
    final double stamina = (player.fitnessPct ?? 100).clamp(0, 100).toDouble();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '${player.shirtNumber}  ${player.position}  ${player.name}'
          '${player.rating > 0 ? '   ${player.rating.toStringAsFixed(1)}' : ''}'
          '${player.yellowCards > 0 ? '  Y' : ''}${player.redCards > 0 ? '  R' : ''}',
          key: Key('lineup-${player.id}'),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(color: GtexMatchVisualTokens.textPrimary, fontSize: 12),
        ),
        const SizedBox(height: 2),
        Row(
          children: [
            Expanded(
              child: ClipRRect(
                borderRadius: BorderRadius.circular(2),
                child: LinearProgressIndicator(
                  value: stamina / 100,
                  minHeight: 4,
                  backgroundColor: const Color(0xFF1E293B),
                  color: stamina < 40 ? GtexMatchVisualTokens.red : GtexMatchVisualTokens.live,
                ),
              ),
            ),
            const SizedBox(width: 6),
            Text(
              '${stamina.toInt()}% STA',
              key: Key('stamina-${player.id}'),
              style: const TextStyle(color: GtexMatchVisualTokens.textSecondary, fontSize: 10),
            ),
          ],
        ),
      ],
    );
  }
}

class _StatsCard extends StatelessWidget {
  const _StatsCard({required this.match});

  final GtexLiveMatchState match;

  int _count(String teamId, bool Function(GtexMatchTimelineEvent event) test) {
    return match.timeline.where((event) => event.teamId == teamId && test(event)).length;
  }

  bool _mentions(GtexMatchTimelineEvent event, String word) {
    final String haystack = '${event.title} ${event.description}'.toLowerCase();
    return haystack.contains(word);
  }

  @override
  Widget build(BuildContext context) {
    final GtexMatchStats stats = match.stats;
    return DecoratedBox(
      decoration: GtexMatchVisualTokens.panelDecoration(),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'MATCH STATS',
              style: TextStyle(color: GtexMatchVisualTokens.amber, fontWeight: FontWeight.w900, fontSize: 11),
            ),
            const SizedBox(height: 8),
            _StatLine(label: 'Possession', home: '${stats.homePossession}%', away: '${stats.awayPossession}%'),
            _StatLine(label: 'Shots', home: '${stats.homeShots}', away: '${stats.awayShots}'),
            _StatLine(
              label: 'On target',
              home: '${stats.homeShotsOnTarget}',
              away: '${stats.awayShotsOnTarget}',
            ),
            _StatLine(
              label: 'Corners',
              home: '${_count(match.home.id, (event) => _mentions(event, 'corner'))}',
              away: '${_count(match.away.id, (event) => _mentions(event, 'corner'))}',
            ),
            _StatLine(
              label: 'Fouls',
              home: '${_count(match.home.id, (event) => event.type == GtexPitchEventType.foul)}',
              away: '${_count(match.away.id, (event) => event.type == GtexPitchEventType.foul)}',
            ),
            _StatLine(
              label: 'Cards',
              home:
                  '${_count(match.home.id, (event) => event.type == GtexPitchEventType.yellowCard || event.type == GtexPitchEventType.redCard)}',
              away:
                  '${_count(match.away.id, (event) => event.type == GtexPitchEventType.yellowCard || event.type == GtexPitchEventType.redCard)}',
            ),
          ],
        ),
      ),
    );
  }
}

class _StatLine extends StatelessWidget {
  const _StatLine({required this.label, required this.home, required this.away});

  final String label;
  final String home;
  final String away;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        children: [
          SizedBox(width: 28, child: Text(home, style: const TextStyle(color: GtexMatchVisualTokens.textPrimary, fontSize: 12))),
          Expanded(
            child: Text(
              label,
              textAlign: TextAlign.center,
              style: const TextStyle(color: GtexMatchVisualTokens.textSecondary, fontSize: 11),
            ),
          ),
          SizedBox(width: 28, child: Text(away, textAlign: TextAlign.right, style: const TextStyle(color: GtexMatchVisualTokens.textPrimary, fontSize: 12))),
        ],
      ),
    );
  }
}
