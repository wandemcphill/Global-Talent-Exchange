import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_feedback.dart';
import '../../core/constants/app_spacing.dart';
import '../../models/match_viewer_presentation.dart';
import '../../navigation/app_destinations.dart';
import '../../services/match_3d_monetization_service.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import '../shared/data/gte_feature_support.dart';
import '../../screens/match/gtex_match_viewer_screen.dart';
import 'live_match_viewer_route_support.dart';

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
      title: '2D Viewer',
      subtitle:
          'This route probes the live match-viewer contract and opens the existing 2D viewer only when a real session payload is available.',
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
                      child: Text(
                        _probing ? 'Probing...' : 'Open 2D live viewer',
                      ),
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
                  Wrap(
                    spacing: spacingSM,
                    runSpacing: spacingSM,
                    children: <Widget>[
                      OutlinedButton(
                        onPressed:
                            () => context.push(
                              AppRoutes.matchesBroadcastLocation(
                                _matchKeyController.text.trim(),
                              ),
                            ),
                        child: const Text('Open Broadcast+ route'),
                      ),
                      OutlinedButton(
                        onPressed:
                            () => context.push(
                              AppRoutes.matchesThreeDLocation(
                                _matchKeyController.text.trim(),
                              ),
                            ),
                        child: const Text('Open 3D route'),
                      ),
                    ],
                  ),
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
      final LiveMatchViewerBootstrap bootstrap =
          await resolveLiveMatchViewerBootstrap(ref, matchKey);
      if (!mounted) {
        return;
      }
      setState(() {
        _viewerMetadata = bootstrap.viewer;
      });
      if (openViewer) {
        await Navigator.of(context).push<void>(
          MaterialPageRoute<void>(
            builder:
                (BuildContext context) => GtexMatchViewerScreen(
                  competition: bootstrap.competition,
                  matchKey: matchKey,
                  presentationMode: MatchViewerPresentationMode.broadcast,
                  renderMode: RenderMode.twoD,
                  isSpectator: true,
                  isMajorMatch: true,
                  titleOverride: '2D Match Viewer',
                  viewStateLoader: () => loadLiveMatchViewState(ref, matchKey),
                  continuationLoader:
                      ({
                        required String matchKey,
                        required String continuationToken,
                      }) => loadLiveMatchViewState(
                        ref,
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
}
