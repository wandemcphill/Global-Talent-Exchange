import 'package:flutter/foundation.dart';

import 'onboarding_redesign_models.dart';

class GtexOnboardingController extends ChangeNotifier {
  GtexOnboardingController({
    GtexOnboardingState? initialState,
    bool allowFixtureData = false,
  }) : _hasLiveState = initialState != null || allowFixtureData,
       _state =
           initialState ??
           (allowFixtureData ? GtexOnboardingFixtures.state : _emptyState);

  GtexOnboardingState _state;
  final bool _hasLiveState;
  GtexOnboardingState get state => _state;
  bool get hasLiveState => _hasLiveState;

  void selectRole(String id) {
    _state = _state.copyWith(selectedRoleId: id);
    notifyListeners();
  }

  void selectRegion(String code) {
    _state = _state.copyWith(selectedRegionCode: code);
    notifyListeners();
  }

  void markStepComplete(String id) {
    _state = _state.copyWith(
      steps: _state.steps
          .map(
            (step) =>
                step.id == id
                    ? GtexOnboardingStep(
                      id: step.id,
                      title: step.title,
                      description: step.description,
                      completed: true,
                      ctaLabel: step.ctaLabel,
                    )
                    : step,
          )
          .toList(growable: false),
    );
    notifyListeners();
  }
}

class GtexOnboardingFixtures {
  static const metrics = <GtexLandingMetric>[
    GtexLandingMetric(
      label: 'SportMonks universe',
      value: '8k+',
      detail: 'players expected after ingestion',
    ),
    GtexLandingMetric(
      label: 'Club ownership',
      value: 'Create',
      detail: 'build your own GTEX club',
    ),
    GtexLandingMetric(
      label: 'Market path',
      value: 'Country > League > Club',
      detail: 'structured player discovery',
    ),
    GtexLandingMetric(
      label: 'Regen world',
      value: 'Live',
      detail: 'contracts, awards, personalities',
    ),
  ];

  static const state = GtexOnboardingState(
    selectedRoleId: 'club_owner',
    selectedRegionCode: 'NG',
    roles: [
      GtexRoleOption(
        id: 'club_owner',
        title: 'Create a Club',
        description:
            'Build a GTEX club, shortlist players, enter tournaments, and grow your football economy.',
        highlights: ['Squad building', 'Player market', 'Club shares'],
      ),
      GtexRoleOption(
        id: 'creator',
        title: 'Become a Creator',
        description:
            'Host competitions, publish football content, and monetize your GTEX audience.',
        highlights: ['Creator tournaments', 'Analytics', 'Monetization'],
      ),
      GtexRoleOption(
        id: 'fan_investor',
        title: 'Follow and Invest',
        description:
            'Follow clubs, buy shares, read GTEX news, and participate in the football economy.',
        highlights: ['Club shares', 'News agency', 'Rewards'],
      ),
    ],
    regions: [
      GtexRegionOption(
        code: 'NG',
        name: 'Nigeria',
        marketCount: 842,
        featuredLeagues: ['NPFL', 'U20 pool', 'AFCON rentals'],
      ),
      GtexRegionOption(
        code: 'GB',
        name: 'England',
        marketCount: 1480,
        featuredLeagues: ['Premier League', 'Championship', 'U21 pool'],
      ),
      GtexRegionOption(
        code: 'ES',
        name: 'Spain',
        marketCount: 910,
        featuredLeagues: ['LaLiga', 'Segunda', 'U19 pool'],
      ),
      GtexRegionOption(
        code: 'BR',
        name: 'Brazil',
        marketCount: 1096,
        featuredLeagues: ['Serie A', 'Serie B', 'Youth prospects'],
      ),
      GtexRegionOption(
        code: 'ZA',
        name: 'South Africa',
        marketCount: 520,
        featuredLeagues: ['PSL', 'AFCON rentals'],
      ),
    ],
    steps: [
      GtexOnboardingStep(
        id: 'verify_profile',
        title: 'Verify your profile',
        description:
            'Secure your account and prepare for wallet/top-up features.',
        completed: false,
        ctaLabel: 'Start KYC',
      ),
      GtexOnboardingStep(
        id: 'create_club',
        title: 'Create or join a club',
        description:
            'Your club is the center of GTEX ownership, transfers, and tournaments.',
        completed: false,
        ctaLabel: 'Choose club path',
      ),
      GtexOnboardingStep(
        id: 'shortlist_players',
        title: 'Shortlist your first players',
        description:
            'Browse country > league > division > club and build a visible basket.',
        completed: false,
        ctaLabel: 'Open market',
      ),
      GtexOnboardingStep(
        id: 'join_competition',
        title: 'Enter your first competition',
        description:
            'Start with beginner-friendly GTEX tournaments or creator-hosted events.',
        completed: false,
        ctaLabel: 'View tournaments',
      ),
    ],
  );
}

const GtexOnboardingState _emptyState = GtexOnboardingState(
  selectedRoleId: '',
  selectedRegionCode: '',
  roles: <GtexRoleOption>[],
  regions: <GtexRegionOption>[],
  steps: <GtexOnboardingStep>[],
);
