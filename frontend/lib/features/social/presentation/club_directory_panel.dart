import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';

class DiscoveredClub {
  const DiscoveredClub({
    required this.id,
    required this.name,
    this.city,
  });

  final String id;
  final String name;
  final String? city;

  factory DiscoveredClub.fromJson(Map<String, dynamic> json) {
    return DiscoveredClub(
      id: (json['id'] ?? '').toString(),
      name: (json['club_name'] ?? json['name'] ?? 'Club').toString(),
      city: json['city_name']?.toString(),
    );
  }
}

typedef ClubDirectorySearch = Future<List<DiscoveredClub>> Function(String query);

class ClubDirectoryPanel extends StatefulWidget {
  const ClubDirectoryPanel({
    super.key,
    required this.baseUrl,
    required this.backendMode,
    this.accessToken,
    this.searchClubs,
    this.onOpenClub,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final ClubDirectorySearch? searchClubs;
  final ValueChanged<DiscoveredClub>? onOpenClub;

  @override
  State<ClubDirectoryPanel> createState() => _ClubDirectoryPanelState();
}

class _ClubDirectoryPanelState extends State<ClubDirectoryPanel> {
  final TextEditingController _query = TextEditingController();
  List<DiscoveredClub> _clubs = const <DiscoveredClub>[];
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _query.dispose();
    super.dispose();
  }

  Future<List<DiscoveredClub>> _search(String query) async {
    final ClubDirectorySearch? injected = widget.searchClubs;
    if (injected != null) {
      return injected(query);
    }
    final GteAuthedApi client = GteAuthedApi(
      config: GteRepositoryConfig(
        baseUrl: widget.baseUrl,
        mode: widget.backendMode,
      ),
      transport: GteHttpTransport(),
      accessToken: widget.accessToken,
      mode: widget.backendMode,
    );
    final Map<String, dynamic> payload = await client.getMap(
      '/api/community/discovery/clubs',
      auth: false,
      query: <String, Object?>{
        if (query.trim().isNotEmpty) 'q': query.trim(),
        'limit': 30,
      },
    );
    final List<dynamic> rows = payload['clubs'] as List<dynamic>? ?? <dynamic>[];
    return rows
        .whereType<Map>()
        .map((Map row) => DiscoveredClub.fromJson(Map<String, dynamic>.from(row)))
        .where((DiscoveredClub club) => club.id.isNotEmpty)
        .toList(growable: false);
  }

  Future<void> _runSearch() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final List<DiscoveredClub> clubs = await _search(_query.text);
      if (!mounted) {
        return;
      }
      setState(() {
        _clubs = clubs;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = 'Club search could not be loaded.';
        _loading = false;
      });
    }
  }

  void _open(DiscoveredClub club) {
    final ValueChanged<DiscoveredClub>? onOpenClub = widget.onOpenClub;
    if (onOpenClub != null) {
      onOpenClub(club);
      return;
    }
    context.push('/clubs/${club.id}/profile');
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      key: const Key('gtex-club-directory'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        Text(
          'Find a club',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        TextField(
          key: const Key('gtex-club-directory-search'),
          controller: _query,
          decoration: const InputDecoration(
            hintText: 'Search clubs by name or city',
            border: OutlineInputBorder(),
          ),
          onSubmitted: (_) => _runSearch(),
        ),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton(
            key: const Key('gtex-club-directory-submit'),
            onPressed: _loading ? null : _runSearch,
            child: Text(_loading ? 'Searching' : 'Search clubs'),
          ),
        ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(_error!),
          ),
        for (final DiscoveredClub club in _clubs)
          ListTile(
            key: Key('gtex-club-directory-${club.id}'),
            title: Text(club.name),
            subtitle: club.city == null ? null : Text(club.city!),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => _open(club),
          ),
      ],
    );
  }
}
