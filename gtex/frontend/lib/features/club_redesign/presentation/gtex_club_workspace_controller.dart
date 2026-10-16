import 'package:flutter/foundation.dart';

import '../models/gtex_club_redesign_models.dart';

enum GtexClubOwnerSection {
  overview,
  readiness,
  squad,
  staff,
  academy,
  sponsorships,
  transfers,
  finances,
  competitions,
  identity,
  trophies,
  news,
  orders,
  settings,
}

enum GtexPublicClubSection {
  overview,
  squad,
  trophies,
  news,
  shares,
  community,
}

extension GtexClubOwnerSectionCopy on GtexClubOwnerSection {
  String get label => switch (this) {
    GtexClubOwnerSection.overview => 'Overview',
    GtexClubOwnerSection.readiness => 'Launch',
    GtexClubOwnerSection.squad => 'Squad',
    GtexClubOwnerSection.staff => 'Staff',
    GtexClubOwnerSection.academy => 'Academy',
    GtexClubOwnerSection.sponsorships => 'Sponsors',
    GtexClubOwnerSection.transfers => 'Transfers',
    GtexClubOwnerSection.finances => 'Finances',
    GtexClubOwnerSection.competitions => 'Competitions',
    GtexClubOwnerSection.identity => 'Identity',
    GtexClubOwnerSection.trophies => 'Trophies',
    GtexClubOwnerSection.news => 'News',
    GtexClubOwnerSection.orders => 'Orders',
    GtexClubOwnerSection.settings => 'Settings',
  };

  String get description => switch (this) {
    GtexClubOwnerSection.overview => 'Club health, activity, value',
    GtexClubOwnerSection.readiness => 'Readiness and squad lock',
    GtexClubOwnerSection.squad => 'Owned players and regens',
    GtexClubOwnerSection.staff => 'Managers, agents, scouts',
    GtexClubOwnerSection.academy => 'Prospects and promotion',
    GtexClubOwnerSection.sponsorships => 'Revenue and leads',
    GtexClubOwnerSection.transfers => 'Shortlist, buying, rental impact',
    GtexClubOwnerSection.finances => 'Wallet, orders, shares',
    GtexClubOwnerSection.competitions => 'Tournaments and progress',
    GtexClubOwnerSection.identity => 'Badge, jersey, public brand',
    GtexClubOwnerSection.trophies => 'Honors and dynasty',
    GtexClubOwnerSection.news => 'AI newsroom mentions',
    GtexClubOwnerSection.orders => 'Purchases and operations',
    GtexClubOwnerSection.settings => 'Club preferences and controls',
  };
}

extension GtexPublicClubSectionCopy on GtexPublicClubSection {
  String get label => switch (this) {
    GtexPublicClubSection.overview => 'Overview',
    GtexPublicClubSection.squad => 'Squad',
    GtexPublicClubSection.trophies => 'Trophies',
    GtexPublicClubSection.news => 'News',
    GtexPublicClubSection.shares => 'Shares',
    GtexPublicClubSection.community => 'Community',
  };

  String get description => switch (this) {
    GtexPublicClubSection.overview => 'Public club story',
    GtexPublicClubSection.squad => 'Player showcase',
    GtexPublicClubSection.trophies => 'Honors and history',
    GtexPublicClubSection.news => 'AI newsroom mentions',
    GtexPublicClubSection.shares => 'Follow and buy shares',
    GtexPublicClubSection.community => 'Fans and followers',
  };
}

class GtexClubWorkspaceController extends ChangeNotifier {
  GtexClubWorkspaceController({
    required String clubId,
    String? clubName,
    GtexClubWorkspaceSnapshot? initialSnapshot,
  }) : snapshot =
           initialSnapshot ??
           GtexClubWorkspaceSnapshot.liveUnavailable(
             clubId: clubId,
             clubName: clubName,
           );

  GtexClubWorkspaceSnapshot snapshot;
  GtexClubOwnerSection ownerSection = GtexClubOwnerSection.overview;
  GtexPublicClubSection publicSection = GtexPublicClubSection.overview;
  bool isFollowing = false;
  int selectedShares = 10;

  void replaceSnapshot(GtexClubWorkspaceSnapshot value) {
    if (identical(snapshot, value)) {
      return;
    }
    snapshot = value;
    notifyListeners();
  }

  void selectOwnerSection(GtexClubOwnerSection section) {
    if (ownerSection == section) {
      return;
    }
    ownerSection = section;
    notifyListeners();
  }

  void selectPublicSection(GtexPublicClubSection section) {
    if (publicSection == section) {
      return;
    }
    publicSection = section;
    notifyListeners();
  }

  void toggleFollow() {
    isFollowing = !isFollowing;
    notifyListeners();
  }

  void setSelectedShares(int count) {
    selectedShares = count.clamp(1, 10000);
    notifyListeners();
  }

  int get selectedShareCostCredits =>
      selectedShares * snapshot.finances.sharePriceCredits;
}
