import 'package:flutter/material.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';

class ClubChallengeBar extends StatelessWidget {
  const ClubChallengeBar({
    super.key,
    required this.targetClubId,
    required this.targetClubName,
    required this.baseUrl,
    required this.backendMode,
    this.accessToken,
    this.isAuthenticated = false,
    this.onOpenLogin,
  });

  final String targetClubId;
  final String targetClubName;
  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;

  GteAuthedApi _client() {
    return GteAuthedApi(
      config: GteRepositoryConfig(baseUrl: baseUrl, mode: backendMode),
      transport: GteHttpTransport(),
      accessToken: accessToken,
      mode: backendMode,
    );
  }

  Future<void> _challenge(BuildContext context) async {
    if (!isAuthenticated || (accessToken ?? '').trim().isEmpty) {
      onOpenLogin?.call();
      return;
    }
    final GteAuthedApi client = _client();
    final Map<String, dynamic> owned = await client.getMap('/api/owner/onboarding');
    final List<Map<String, dynamic>> clubs = ((owned['clubs'] as List<dynamic>?) ?? <dynamic>[])
        .whereType<Map>()
        .map((Map row) => Map<String, dynamic>.from(row))
        .toList(growable: false);
    if (!context.mounted) {
      return;
    }
    if (clubs.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('You need a club before you can send a challenge.')),
      );
      return;
    }
    String issuingId = (clubs.first['club_id'] ?? clubs.first['id'] ?? '').toString();
    final TextEditingController message = TextEditingController(
      text: 'We want a match against $targetClubName.',
    );
    final bool? sent = await showDialog<bool>(
      context: context,
      builder: (BuildContext dialogContext) {
        return StatefulBuilder(
          builder: (BuildContext context, StateSetter setLocal) {
            return AlertDialog(
              title: Text('Challenge $targetClubName'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  DropdownButton<String>(
                    isExpanded: true,
                    value: issuingId,
                    items: clubs
                        .map(
                          (Map<String, dynamic> club) => DropdownMenuItem<String>(
                            value: (club['club_id'] ?? club['id']).toString(),
                            child: Text((club['club_name'] ?? club['name'] ?? 'Club').toString()),
                          ),
                        )
                        .toList(growable: false),
                    onChanged: (String? value) {
                      if (value != null) {
                        setLocal(() => issuingId = value);
                      }
                    },
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: message,
                    minLines: 2,
                    maxLines: 4,
                    decoration: const InputDecoration(labelText: 'Message'),
                  ),
                ],
              ),
              actions: <Widget>[
                TextButton(
                  onPressed: () => Navigator.of(dialogContext).pop(false),
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  key: const Key('gtex-send-challenge'),
                  onPressed: () => Navigator.of(dialogContext).pop(true),
                  child: const Text('Send challenge'),
                ),
              ],
            );
          },
        );
      },
    );
    final String body = message.text.trim();
    message.dispose();
    if (sent != true || !context.mounted) {
      return;
    }
    try {
      final Object? raw = await client.request(
        'POST',
        '/api/clubs/$issuingId/challenges',
        body: <String, Object?>{
          'title': 'Challenge $targetClubName',
          'message': body.length < 8 ? 'We want a match against $targetClubName.' : body,
          'target_club_id': targetClubId,
          'visibility': 'private',
          'stakes_text': 'Friendly',
        },
      );
      final Map<String, dynamic> created =
          raw is Map ? Map<String, dynamic>.from(raw) : <String, dynamic>{};
      final String? challengeId =
          (created['challenge'] as Map?)?['id']?.toString() ??
          (created['card'] as Map?)?['challenge_id']?.toString();
      if (challengeId != null && challengeId.isNotEmpty) {
        await client.request('POST', '/api/challenges/$challengeId/publish');
      }
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Challenge sent to $targetClubName.')),
        );
      }
    } catch (_) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('The challenge could not be sent.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: FilledButton.icon(
        key: const Key('gtex-challenge-club'),
        onPressed: () => _challenge(context),
        icon: const Icon(Icons.sports_soccer_outlined),
        label: const Text('Challenge this club'),
      ),
    );
  }
}
