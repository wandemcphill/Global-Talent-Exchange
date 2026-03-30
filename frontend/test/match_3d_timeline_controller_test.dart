import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/match_3d_timeline_controller.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_type.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/services/match_viewer_mapper.dart';

void main() {
  testWidgets('VAR pauses, resumes, and commits the score only on confirmation',
      (WidgetTester tester) async {
    final CompetitionSummary competition = _buildCompetition(
      id: 'match-controller-var',
    );
    final MatchViewState viewState = await _loadFallbackState(competition);
    final MatchTimelineFrame checkingFrame = viewState.frames.firstWhere(
      (MatchTimelineFrame frame) => frame.overlayText == 'Checking...',
    );
    final MatchTimelineFrame confirmedFrame = viewState.frames.firstWhere(
      (MatchTimelineFrame frame) => frame.overlayText == 'Confirmed',
    );
    late TickerProvider vsync;

    await tester.pumpWidget(
      _TickerHost(
        onReady: (TickerProvider provider) {
          vsync = provider;
        },
      ),
    );

    final Match3dTimelineController controller = Match3dTimelineController(
      vsync: vsync,
      viewState: viewState,
      autoplay: false,
    );

    controller.seekTo(checkingFrame.timeSeconds - 0.05);
    controller.play();
    await tester.pump(const Duration(milliseconds: 100));

    expect(controller.isAutoPaused, isTrue);
    expect(controller.overlayText, 'Checking...');
    expect(controller.displayFrame.homeScore, 0);
    expect(controller.displayFrame.awayScore, 0);

    final double pausedAt = controller.positionSeconds;
    await tester.pump(const Duration(milliseconds: 50));
    expect(controller.positionSeconds, closeTo(pausedAt, 0.001));

    await tester.pump(const Duration(milliseconds: 400));
    expect(controller.isAutoPaused, isFalse);

    controller.seekTo(confirmedFrame.timeSeconds);
    expect(controller.overlayText, 'Confirmed');
    expect(controller.displayFrame.homeScore, 1);
    expect(controller.displayFrame.awayScore, 0);

    controller.dispose();
    await tester.pumpWidget(const SizedBox.shrink());
  });

  testWidgets('OFFSIDE cue pauses playback and then resumes automatically',
      (WidgetTester tester) async {
    final CompetitionSummary competition = _buildCompetition(
      id: 'match-controller-offside',
    );
    final MatchViewState viewState = await _loadFallbackState(competition);
    final MatchTimelineFrame offsideFrame = viewState.frames.firstWhere(
      (MatchTimelineFrame frame) => frame.overlayText == 'OFFSIDE',
    );
    final MatchEvent offsideEvent = viewState.events.firstWhere(
      (MatchEvent event) => event.type == MatchViewerEventType.offside,
    );
    late TickerProvider vsync;

    await tester.pumpWidget(
      _TickerHost(
        onReady: (TickerProvider provider) {
          vsync = provider;
        },
      ),
    );

    final Match3dTimelineController controller = Match3dTimelineController(
      vsync: vsync,
      viewState: viewState,
      autoplay: false,
    );

    controller.seekTo(offsideFrame.timeSeconds - 0.05);
    controller.play();
    await tester.pump(const Duration(milliseconds: 100));

    expect(controller.isAutoPaused, isTrue);
    expect(controller.overlayText, 'OFFSIDE');
    expect(controller.displayFrame.flagAnimation, isTrue);
    expect(controller.activeEvent?.id, offsideEvent.id);

    final double pausedAt = controller.positionSeconds;
    await tester.pump(const Duration(milliseconds: 50));
    expect(controller.positionSeconds, closeTo(pausedAt, 0.001));

    await tester.pump(const Duration(milliseconds: 400));
    expect(controller.isAutoPaused, isFalse);
    expect(controller.positionSeconds, greaterThan(pausedAt));

    controller.dispose();
    await tester.pumpWidget(const SizedBox.shrink());
  });
}

CompetitionSummary _buildCompetition({required String id}) {
  return CompetitionSummary(
    id: id,
    name: 'GTEX Replay Test',
    format: CompetitionFormat.league,
    visibility: CompetitionVisibility.public,
    status: CompetitionStatus.completed,
    creatorId: 'creator-1',
    creatorName: 'GTEX',
    participantCount: 8,
    capacity: 8,
    currency: 'USD',
    entryFee: 0,
    platformFeePct: 0,
    hostFeePct: 0,
    platformFeeAmount: 0,
    hostFeeAmount: 0,
    prizePool: 0,
    payoutStructure: const <CompetitionPayoutBreakdown>[],
    rulesSummary: 'Replay validation fixture',
    matchType: MatchType.gtexHosted,
    joinEligibility: const CompetitionJoinEligibility(eligible: true),
    beginnerFriendly: true,
    createdAt: DateTime.utc(2026, 1, 1),
    updatedAt: DateTime.utc(2026, 1, 2),
  );
}

Future<MatchViewState> _loadFallbackState(CompetitionSummary competition) {
  final LiveMatchSnapshot snapshot = LiveMatchFixtures.buildSnapshot(
    competition,
  );
  return MatchViewerMapper.load(
    competition: competition,
    matchKey: competition.id,
    fallbackSnapshot: snapshot,
    preferFallback: true,
  );
}

class _TickerHost extends StatefulWidget {
  const _TickerHost({
    required this.onReady,
  });

  final ValueChanged<TickerProvider> onReady;

  @override
  State<_TickerHost> createState() => _TickerHostState();
}

class _TickerHostState extends State<_TickerHost>
    with SingleTickerProviderStateMixin {
  @override
  void initState() {
    super.initState();
    widget.onReady(this);
  }

  @override
  Widget build(BuildContext context) {
    return const SizedBox.shrink();
  }
}
