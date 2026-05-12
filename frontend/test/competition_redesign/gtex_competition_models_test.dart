import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/competition_redesign/models/gtex_competition_models.dart';

void main() {
  test('competition summary exposes labels and joinable state', () {
    const GtexCompetitionSummary summary = GtexCompetitionSummary(
      id: 'test',
      title: 'Test Cup',
      kind: GtexCompetitionKind.userHosted,
      status: GtexCompetitionStatus.registrationOpen,
      regionLabel: 'Nigeria',
      entryFeeCredits: 100,
      prizePoolCredits: 1600,
      registeredClubs: 4,
      maxClubs: 16,
      progressPercent: .25,
      currentStage: 'Registration',
      startsAtLabel: 'Tomorrow',
      description: 'Demo',
    );

    expect(summary.isJoinable, isTrue);
    expect(summary.entryFeeLabel, '100 coins');
    expect(summary.capacityLabel, '4/16 clubs');
  });
}
