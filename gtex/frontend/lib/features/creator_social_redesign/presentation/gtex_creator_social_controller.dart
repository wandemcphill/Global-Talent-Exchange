import 'package:flutter/foundation.dart';

import '../models/gtex_creator_social_models.dart';

class GtexCreatorSocialController extends ChangeNotifier {
  GtexCreatorSocialController({
    GtexCreatorSocialSnapshot? snapshot,
    bool allowFixtureData = false,
  }) : _hasLiveSnapshot = snapshot != null || allowFixtureData,
       _snapshot =
           snapshot ??
           (allowFixtureData
               ? GtexCreatorSocialSnapshot.demo()
               : _emptyCreatorSocialSnapshot);

  final GtexCreatorSocialSnapshot _snapshot;
  final bool _hasLiveSnapshot;

  GtexCreatorModule _creatorModule = GtexCreatorModule.overview;
  GtexAwardCategory _awardCategory = GtexAwardCategory.player;
  GtexSocialModule _socialModule = GtexSocialModule.feed;
  String _searchQuery = '';

  GtexCreatorSocialSnapshot get snapshot => _snapshot;
  bool get hasLiveSnapshot => _hasLiveSnapshot;
  GtexCreatorModule get creatorModule => _creatorModule;
  GtexAwardCategory get awardCategory => _awardCategory;
  GtexSocialModule get socialModule => _socialModule;
  String get searchQuery => _searchQuery;

  List<GtexAwardNominee> get nominees {
    final all =
        _snapshot.awardSeasons.expand((season) => season.nominees).toList();
    return all
        .where((nominee) => nominee.category == _awardCategory)
        .toList(growable: false);
  }

  List<GtexSocialStory> get stories {
    final query = _searchQuery.trim().toLowerCase();
    if (query.isEmpty) return _snapshot.socialStories;
    return _snapshot.socialStories
        .where((story) {
          return story.title.toLowerCase().contains(query) ||
              story.body.toLowerCase().contains(query) ||
              (story.clubLabel ?? '').toLowerCase().contains(query);
        })
        .toList(growable: false);
  }

  void selectCreatorModule(GtexCreatorModule module) {
    if (_creatorModule == module) return;
    _creatorModule = module;
    notifyListeners();
  }

  void selectAwardCategory(GtexAwardCategory category) {
    if (_awardCategory == category) return;
    _awardCategory = category;
    notifyListeners();
  }

  void selectSocialModule(GtexSocialModule module) {
    if (_socialModule == module) return;
    _socialModule = module;
    notifyListeners();
  }

  void updateSearch(String value) {
    _searchQuery = value;
    notifyListeners();
  }
}

const GtexCreatorSocialSnapshot _emptyCreatorSocialSnapshot =
    GtexCreatorSocialSnapshot(
      creatorName: 'Creator data unavailable',
      creatorHandle: '@live.creator.required',
      metrics: <GtexCreatorMetric>[],
      competitions: <GtexCreatorCompetition>[],
      revenueItems: <GtexCreatorRevenueItem>[],
      awardSeasons: <GtexAwardSeason>[],
      socialStories: <GtexSocialStory>[],
      followedClubs: <GtexFollowedClub>[],
      referral: GtexReferralSnapshot(
        code: '',
        invitesLabel: '0',
        rewardsLabel: '0',
        pendingLabel: '0',
      ),
    );
