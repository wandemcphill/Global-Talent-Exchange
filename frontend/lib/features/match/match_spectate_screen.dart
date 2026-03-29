import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/app_feedback.dart';
import '../../core/constants/app_spacing.dart';
import '../../data/gte_api_repository.dart';
import '../../data/gte_authed_api.dart';
import '../../features/shared/data/gte_feature_support.dart';
import '../../models/competition_models.dart';
import '../../models/match_type.dart';
import '../../models/match_view_state.dart';
import '../../models/match_viewer_presentation.dart';
import '../../screens/match/gtex_match_viewer_screen.dart';
import '../../services/match_3d_monetization_service.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';

class MatchSpectateScreen extends ConsumerStatefulWidget {
  const MatchSpectateScreen({super.key});

  @override
  ConsumerState<MatchSpectateScreen> createState() =>
      _MatchSpectateScreenState();
}

class _MatchSpectateScreenState extends ConsumerState<MatchSpectateScreen> {
  final TextEditingController _matchKeyController = TextEditingController(
    text: 'live-match-001',
  );
  JsonMap? _viewerMetadata;
  String? _blockedReason;
  bool _probing = false;

  @override
  void dispose() {
    _matchKeyController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final DataSourceStatus status =
        _blockedReason == null
            ? DataSourceStatus.live
            : DataSourceStatus.blocked;
    return AppPageLayout(
      title: 'Spectate',
      subtitle:
          'This route probes the live match-viewer contract and opens the existing 2D/Broadcast+/3D viewer only when a real session payload is available.',
      trailing: DataSourceBadge(status: status),
      children: <Widget>[
        Card(
          child: Padding(
            padding: const EdgeInsets.all(spacingLG),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                TextField(
                  controller: _matchKeyController,
                  decoration: const InputDecoration(labelText: 'Match key'),
                ),
                const SizedBox(height: spacingMD),
                Wrap(
                  spacing: spacingSM,
                  runSpacing: spacingSM,
                  children: <Widget>[
                    FilledButton(
                      onPressed: _probing ? null : _probeAndOpen,
                      child: Text(_probing ? 'Probing...' : 'Open live viewer'),
                    ),
                    OutlinedButton(
                      onPressed: _probing ? null : _probeOnly,
                      child: const Text('Probe only'),
                    ),
                  ],
                ),
                if (_blockedReason != null) ...<Widget>[
                  const SizedBox(height: spacingMD),
                  Text(
                    _blockedReason!,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ],
                if (_viewerMetadata != null) ...<Widget>[
                  const SizedBox(height: spacingMD),
                  Text(
                    _viewerMetadata!.entries
                        .take(12)
                        .map(
                          (MapEntry<String, Object?> entry) =>
                              '${entry.key}: ${entry.value}',
                        )
                        .join('\n'),
                  ),
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }

  Future<void> _probeOnly() async {
    await _runProbe(openViewer: false);
  }

  Future<void> _probeAndOpen() async {
    await _runProbe(openViewer: true);
  }

  Future<void> _runProbe({required bool openViewer}) async {
    setState(() {
      _probing = true;
      _blockedReason = null;
    });
    final String matchKey = _matchKeyController.text.trim();
    try {
      final JsonMap viewer = await _fetchFirstMap(
        ref.read(authedApiProvider),
        <String>['/api/match-viewer/$matchKey', '/match-viewer/$matchKey'],
        auth: false,
      );
      await _fetchFirstMap(ref.read(authedApiProvider), <String>[
        '/api/match-viewer/$matchKey/session',
        '/match-viewer/$matchKey/session',
      ], auth: false);
      if (ref.read(isAuthenticatedProvider)) {
        try {
          await ref
              .read(authedApiProvider)
              .post('/api/matches/$matchKey/spectate');
        } catch (_) {
          // Viewer probing remains the source of truth. Spectate bootstrap is best-effort.
        }
      }
      if (!mounted) {
        return;
      }
      setState(() {
        _viewerMetadata = viewer;
      });
      if (openViewer) {
        await Navigator.of(context).push<void>(
          MaterialPageRoute<void>(
            builder:
                (BuildContext context) => GtexMatchViewerScreen(
                  competition: _placeholderCompetition(matchKey, viewer),
                  matchKey: matchKey,
                  presentationMode: MatchViewerPresentationMode.broadcast,
                  renderMode: RenderMode.auto,
                  isSpectator: true,
                  isMajorMatch: true,
                  viewStateLoader: () => _loadViewState(matchKey),
                  continuationLoader:
                      ({
                        required String matchKey,
                        required String continuationToken,
                      }) => _loadViewState(
                        matchKey,
                        continuationToken: continuationToken,
                      ),
                ),
          ),
        );
      }
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _blockedReason = AppFeedback.messageFor(error);
      });
    } finally {
      if (mounted) {
        setState(() {
          _probing = false;
        });
      }
    }
  }

  Future<MatchViewState> _loadViewState(
    String matchKey, {
    String? continuationToken,
  }) async {
    final JsonMap session = await _fetchFirstMap(
      ref.read(authedApiProvider),
      <String>[
        '/api/match-viewer/$matchKey/session',
        '/match-viewer/$matchKey/session',
      ],
      auth: false,
      query: <String, Object?>{
        if (continuationToken != null && continuationToken.isNotEmpty)
          'token': continuationToken,
      },
    );
    return MatchViewState.fromJson(session);
  }

  Future<JsonMap> _fetchFirstMap(
    GteAuthedApi api,
    List<String> paths, {
    required bool auth,
    Map<String, Object?> query = const <String, Object?>{},
  }) async {
    GteApiException? lastError;
    for (final String path in paths) {
      try {
        return await api.getMap(path, auth: auth, query: query);
      } on GteApiException catch (error) {
        lastError = error;
        if (error.statusCode == 404 || error.statusCode == 405) {
          continue;
        }
        rethrow;
      }
    }
    throw lastError ??
        const GteApiException(
          type: GteApiErrorType.notFound,
          message:
              'No live match viewer endpoint responded for this match key.',
        );
  }

  CompetitionSummary _placeholderCompetition(String matchKey, JsonMap viewer) {
    final DateTime now = DateTime.now().toUtc();
    final String title = stringValue(
      viewer['title'],
      fallback:
          stringOrNullValue(viewer['match_label']) ?? 'Live match spectate',
    );
    return CompetitionSummary(
      id: matchKey,
      name: title,
      format: CompetitionFormat.cup,
      visibility: CompetitionVisibility.public,
      status: CompetitionStatus.inProgress,
      creatorId: 'gtex-live',
      creatorName: 'GTEX Live',
      participantCount: 2,
      capacity: 2,
      currency: 'coin',
      entryFee: 0,
      platformFeePct: 0,
      hostFeePct: 0,
      platformFeeAmount: 0,
      hostFeeAmount: 0,
      prizePool: 0,
      payoutStructure: const <CompetitionPayoutBreakdown>[],
      rulesSummary:
          'Live match spectate route backed by match-viewer payloads.',
      matchType: MatchType.gtexHosted,
      joinEligibility: const CompetitionJoinEligibility(
        eligible: false,
        reason: 'spectate_only',
      ),
      beginnerFriendly: true,
      createdAt: now,
      updatedAt: now,
    );
  }
}
