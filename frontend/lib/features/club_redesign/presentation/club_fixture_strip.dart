import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';

class ClubFixtureStrip extends StatefulWidget {
  const ClubFixtureStrip({
    super.key,
    required this.clubId,
    required this.clubName,
    required this.baseUrl,
    required this.backendMode,
    this.accessToken,
  });

  final String clubId;
  final String clubName;
  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;

  @override
  State<ClubFixtureStrip> createState() => _ClubFixtureStripState();
}

class _ClubFixtureStripState extends State<ClubFixtureStrip> {
  List<Map<String, dynamic>> _fixtures = const <Map<String, dynamic>>[];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final GteAuthedApi client = GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: widget.baseUrl, mode: widget.backendMode),
        transport: GteHttpTransport(),
        accessToken: widget.accessToken,
        mode: widget.backendMode,
      );
      final Map<String, dynamic> payload = await client.getMap(
        '/api/competitions/fixtures',
        auth: widget.accessToken != null,
        query: <String, Object?>{'club': widget.clubName, 'limit': 8},
      );
      final List<dynamic> rows = payload['fixtures'] as List<dynamic>? ?? <dynamic>[];
      if (!mounted) {
        return;
      }
      setState(() {
        _fixtures = rows.whereType<Map>().map((Map row) => Map<String, dynamic>.from(row)).toList();
        _loading = false;
      });
    } catch (_) {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading || _fixtures.isEmpty) {
      return const SizedBox.shrink();
    }
    return Column(
      key: const Key('gtex-club-fixtures'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text('Matches', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        for (final Map<String, dynamic> fixture in _fixtures)
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text('${fixture['home_name']} vs ${fixture['away_name']}'),
            subtitle: Text('${fixture['competition_name'] ?? ''} · ${fixture['status'] ?? ''}'),
            onTap: () {
              final String? id = fixture['id']?.toString();
              if (id != null && id.isNotEmpty) {
                context.push('/app/match/$id');
              }
            },
          ),
      ],
    );
  }
}

