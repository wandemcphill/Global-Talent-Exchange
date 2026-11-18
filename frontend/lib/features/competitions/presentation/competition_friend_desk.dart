import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';

class CompetitionFriendDesk extends ConsumerStatefulWidget {
  const CompetitionFriendDesk({
    super.key,
    required this.isAuthenticated,
    required this.onOpenLogin,
    required this.onHostCanonical,
    this.onQueryChanged,
    this.searchFixtures,
  });

  final bool isAuthenticated;
  final VoidCallback onOpenLogin;
  final VoidCallback onHostCanonical;
  final ValueChanged<String>? onQueryChanged;
  final Future<List<Map<String, dynamic>>> Function(String query)? searchFixtures;

  @override
  ConsumerState<CompetitionFriendDesk> createState() => _CompetitionFriendDeskState();
}

class _CompetitionFriendDeskState extends ConsumerState<CompetitionFriendDesk> {
  final TextEditingController _name = TextEditingController();
  final TextEditingController _opponentQuery = TextEditingController();
  final TextEditingController _pin = TextEditingController();
  final TextEditingController _joinPin = TextEditingController();
  final TextEditingController _fixtureQuery = TextEditingController();
  List<Map<String, dynamic>> _opponents = const <Map<String, dynamic>>[];
  Map<String, dynamic>? _opponent;
  List<Map<String, dynamic>> _fixtures = const <Map<String, dynamic>>[];
  String? _hostedPin;
  String? _note;

  @override
  void dispose() {
    _name.dispose();
    _opponentQuery.dispose();
    _pin.dispose();
    _joinPin.dispose();
    _fixtureQuery.dispose();
    super.dispose();
  }

  GteAuthedApi get _api => ref.read(authedApiProvider);

  Future<void> _searchOpponents() async {
    final String query = _opponentQuery.text.trim();
    if (query.length < 2) {
      return;
    }
    final Map<String, dynamic> payload = await _api.getMap(
      '/api/community/discovery/clubs',
      auth: false,
      query: <String, Object?>{'q': query, 'limit': 8},
    );
    final List<dynamic> rows = payload['clubs'] as List<dynamic>? ?? <dynamic>[];
    if (!mounted) {
      return;
    }
    setState(() {
      _opponents = rows.whereType<Map>().map((Map row) => Map<String, dynamic>.from(row)).toList();
    });
  }

  Future<void> _hostFriendCup() async {
    if (!widget.isAuthenticated) {
      widget.onOpenLogin();
      return;
    }
    try {
      final Map<String, dynamic> owned = await _api.getMap('/api/owner/clubs');
      final List<dynamic> clubs = owned['clubs'] as List<dynamic>? ?? <dynamic>[];
      if (clubs.isEmpty) {
        widget.onHostCanonical();
        return;
      }
      final Map<String, dynamic> club = Map<String, dynamic>.from(clubs.first as Map);
      final String clubId = (club['club_id'] ?? club['id'] ?? '').toString();
      final Map<String, dynamic> created = await _post('/api/owner/competitions', <String, Object?>{
        'name': _name.text.trim().length < 3 ? 'Friends Cup' : _name.text.trim(),
        'format': 'knockout',
        'max_clubs': 8,
        'club_id': clubId,
        if (_pin.text.trim().isNotEmpty) 'pin': _pin.text.trim(),
        if (_opponent != null) 'opponent_club_id': _opponent!['id'],
        'winner_prize': 0,
        'contribution': 0,
      });
      if (!mounted) {
        return;
      }
      setState(() {
        _hostedPin = (created['invite_code'] ?? '').toString();
        _note = 'Hosted. Share the pin so your friend can join.';
      });
    } catch (_) {
      if (mounted) {
        setState(() => _note = 'The friend competition could not be hosted.');
      }
    }
  }


  Future<Map<String, dynamic>> _post(String path, Map<String, Object?> body) async {
    final Object? raw = await _api.request('POST', path, body: body);
    return raw is Map ? Map<String, dynamic>.from(raw) : <String, dynamic>{};
  }

  Future<void> _joinByPin() async {
    if (!widget.isAuthenticated) {
      widget.onOpenLogin();
      return;
    }
    final Map<String, dynamic> owned = await _api.getMap('/api/owner/clubs');
    final List<dynamic> clubs = owned['clubs'] as List<dynamic>? ?? <dynamic>[];
    if (clubs.isEmpty) {
      setState(() => _note = 'A club is required to join a friend cup. You can still host a user competition.');
      return;
    }
    final Map<String, dynamic> club = Map<String, dynamic>.from(clubs.first as Map);
    await _post('/api/owner/competitions/join-by-code', <String, Object?>{
      'code': _joinPin.text.trim(),
      'club_id': (club['club_id'] ?? club['id']).toString(),
    });
    if (mounted) {
      setState(() => _note = 'Joined the friend competition.');
    }
  }

  Future<void> _searchFixtures() async {
    final String query = _fixtureQuery.text.trim();
    if (query.isEmpty) {
      setState(() => _fixtures = const <Map<String, dynamic>>[]);
      return;
    }
    widget.onQueryChanged?.call(query);
    if (widget.searchFixtures != null) {
      final List<Map<String, dynamic>> rows = await widget.searchFixtures!(query);
      if (!mounted) {
        return;
      }
      setState(() => _fixtures = rows);
      return;
    }
    final Map<String, dynamic> payload = await _api.getMap(
      '/api/competitions/fixtures',
      auth: widget.isAuthenticated,
      query: <String, Object?>{'q': query, 'limit': 20},
    );

    final List<dynamic> rows = payload['fixtures'] as List<dynamic>? ?? <dynamic>[];
    if (!mounted) {
      return;
    }
    setState(() {
      _fixtures = rows.whereType<Map>().map((Map row) => Map<String, dynamic>.from(row)).toList();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      key: const Key('gtex-competition-friend-desk'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        TextField(
          key: const Key('gtex-competition-search'),
          controller: _fixtureQuery,
          decoration: const InputDecoration(
            hintText: 'Find a match by competition, club, or opponent',
            border: OutlineInputBorder(),
          ),
          onSubmitted: (_) => _searchFixtures(),
        ),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerLeft,
          child: Wrap(
            spacing: 8,
            children: <Widget>[
              FilledButton(
                key: const Key('gtex-competition-search-submit'),
                onPressed: _searchFixtures,
                child: const Text('Search matches'),
              ),
              FilledButton.tonal(
                key: const Key('gtex-host-competition'),
                onPressed: widget.isAuthenticated ? widget.onHostCanonical : widget.onOpenLogin,
                child: const Text('Host'),
              ),
            ],
          ),
        ),
        for (final Map<String, dynamic> fixture in _fixtures)
          ListTile(
            title: Text('${fixture['home_name']} vs ${fixture['away_name']}'),
            subtitle: Text('${fixture['competition_name'] ?? ''} · ${fixture['status'] ?? 'scheduled'}'),
          ),
        const SizedBox(height: 16),
        Text('Host a friend competition', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        TextField(
          controller: _name,
          decoration: const InputDecoration(hintText: 'Competition name', border: OutlineInputBorder()),
        ),
        const SizedBox(height: 8),
        TextField(
          controller: _opponentQuery,
          decoration: const InputDecoration(hintText: 'Opponent club', border: OutlineInputBorder()),
          onSubmitted: (_) => _searchOpponents(),
        ),
        for (final Map<String, dynamic> club in _opponents)
          ListTile(
            title: Text((club['club_name'] ?? '').toString()),
            trailing: _opponent?['id'] == club['id'] ? const Icon(Icons.check) : null,
            onTap: () => setState(() => _opponent = club),
          ),
        TextField(
          controller: _pin,
          decoration: const InputDecoration(hintText: 'Pin (optional)', border: OutlineInputBorder()),
        ),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton(onPressed: _hostFriendCup, child: const Text('Host friend cup')),
        ),
        if (_hostedPin != null && _hostedPin!.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text('Pin $_hostedPin'),
          ),
        const SizedBox(height: 12),
        TextField(
          key: const Key('gtex-join-pin'),
          controller: _joinPin,
          decoration: const InputDecoration(hintText: 'Join with a pin', border: OutlineInputBorder()),
        ),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerLeft,
          child: OutlinedButton(onPressed: _joinByPin, child: const Text('Join with pin')),
        ),
        if (_note != null)
          Padding(padding: const EdgeInsets.only(top: 8), child: Text(_note!)),
      ],
    );
  }
}

