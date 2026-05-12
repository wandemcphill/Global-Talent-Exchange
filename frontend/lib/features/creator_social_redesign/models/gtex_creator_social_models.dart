import 'package:flutter/foundation.dart';

enum GtexCreatorModule { overview, competitions, monetization, analytics, profile, audience, shares }

enum GtexAwardCategory { player, regen, club, creator, tournament, nationalTeam }

enum GtexSocialModule { feed, followedClubs, fanWars, referrals, shares, community }

@immutable
class GtexCreatorMetric {
  const GtexCreatorMetric({
    required this.label,
    required this.value,
    this.delta,
  });

  final String label;
  final String value;
  final String? delta;
}

@immutable
class GtexCreatorCompetition {
  const GtexCreatorCompetition({
    required this.id,
    required this.title,
    required this.status,
    required this.entriesLabel,
    required this.poolLabel,
    required this.revenueLabel,
  });

  final String id;
  final String title;
  final String status;
  final String entriesLabel;
  final String poolLabel;
  final String revenueLabel;
}

@immutable
class GtexCreatorRevenueItem {
  const GtexCreatorRevenueItem({
    required this.label,
    required this.amountLabel,
    required this.status,
  });

  final String label;
  final String amountLabel;
  final String status;
}

@immutable
class GtexAwardNominee {
  const GtexAwardNominee({
    required this.id,
    required this.name,
    required this.subtitle,
    required this.scoreLabel,
    required this.category,
    this.imageUrl,
    this.badgeLabel,
  });

  final String id;
  final String name;
  final String subtitle;
  final String scoreLabel;
  final GtexAwardCategory category;
  final String? imageUrl;
  final String? badgeLabel;
}

@immutable
class GtexAwardSeason {
  const GtexAwardSeason({
    required this.id,
    required this.title,
    required this.status,
    required this.periodLabel,
    required this.nominees,
  });

  final String id;
  final String title;
  final String status;
  final String periodLabel;
  final List<GtexAwardNominee> nominees;
}

@immutable
class GtexSocialStory {
  const GtexSocialStory({
    required this.id,
    required this.title,
    required this.sourceLabel,
    required this.body,
    required this.timeLabel,
    required this.reactionLabel,
    this.clubLabel,
  });

  final String id;
  final String title;
  final String sourceLabel;
  final String body;
  final String timeLabel;
  final String reactionLabel;
  final String? clubLabel;
}

@immutable
class GtexFollowedClub {
  const GtexFollowedClub({
    required this.id,
    required this.name,
    required this.ownerLabel,
    required this.valueLabel,
    required this.followersLabel,
    required this.sharePriceLabel,
  });

  final String id;
  final String name;
  final String ownerLabel;
  final String valueLabel;
  final String followersLabel;
  final String sharePriceLabel;
}

@immutable
class GtexReferralSnapshot {
  const GtexReferralSnapshot({
    required this.code,
    required this.invitesLabel,
    required this.rewardsLabel,
    required this.pendingLabel,
  });

  final String code;
  final String invitesLabel;
  final String rewardsLabel;
  final String pendingLabel;
}

@immutable
class GtexCreatorSocialSnapshot {
  const GtexCreatorSocialSnapshot({
    required this.creatorName,
    required this.creatorHandle,
    required this.metrics,
    required this.competitions,
    required this.revenueItems,
    required this.awardSeasons,
    required this.socialStories,
    required this.followedClubs,
    required this.referral,
  });

  final String creatorName;
  final String creatorHandle;
  final List<GtexCreatorMetric> metrics;
  final List<GtexCreatorCompetition> competitions;
  final List<GtexCreatorRevenueItem> revenueItems;
  final List<GtexAwardSeason> awardSeasons;
  final List<GtexSocialStory> socialStories;
  final List<GtexFollowedClub> followedClubs;
  final GtexReferralSnapshot referral;

  factory GtexCreatorSocialSnapshot.demo() {
    const nominees = [
      GtexAwardNominee(
        id: 'nominee-1',
        name: 'Ayo Striker',
        subtitle: 'Lagos Royals · 28 goals · Market king',
        scoreLabel: '94.2',
        category: GtexAwardCategory.player,
        badgeLabel: 'World Player',
      ),
      GtexAwardNominee(
        id: 'nominee-2',
        name: 'Mika Regen',
        subtitle: 'Class of 2031 · 17 years · Wonderkid',
        scoreLabel: '91.8',
        category: GtexAwardCategory.regen,
        badgeLabel: 'Regen Star',
      ),
      GtexAwardNominee(
        id: 'nominee-3',
        name: 'Victoria FC',
        subtitle: 'User-owned club · 6 trophies',
        scoreLabel: '88.5',
        category: GtexAwardCategory.club,
        badgeLabel: 'Club Dynasty',
      ),
    ];

    return const GtexCreatorSocialSnapshot(
      creatorName: 'GTEX Creator Studio',
      creatorHandle: '@gtex.creator',
      metrics: [
        GtexCreatorMetric(label: 'Audience', value: '128K', delta: '+18% this month'),
        GtexCreatorMetric(label: 'Hosted comps', value: '24', delta: '6 live'),
        GtexCreatorMetric(label: 'Creator revenue', value: '₵8.4M', delta: '+₵940K today'),
        GtexCreatorMetric(label: 'Engagement', value: '71%', delta: 'Top 5%'),
      ],
      competitions: [
        GtexCreatorCompetition(
          id: 'comp-1',
          title: 'Friday Night Creator Cup',
          status: 'Live',
          entriesLabel: '64 clubs',
          poolLabel: '₵2.5M pool',
          revenueLabel: '₵340K creator share',
        ),
        GtexCreatorCompetition(
          id: 'comp-2',
          title: 'U20 Regen Showcase',
          status: 'Registration',
          entriesLabel: '112 clubs',
          poolLabel: '₵1.2M pool',
          revenueLabel: '₵120K forecast',
        ),
        GtexCreatorCompetition(
          id: 'comp-3',
          title: 'Afro Elite Challenge',
          status: 'Draft',
          entriesLabel: 'Invite only',
          poolLabel: '₵5M target',
          revenueLabel: 'Pending approval',
        ),
      ],
      revenueItems: [
        GtexCreatorRevenueItem(label: 'Competition hosting', amountLabel: '₵4.1M', status: 'Settled'),
        GtexCreatorRevenueItem(label: 'Stadium monetization', amountLabel: '₵2.0M', status: 'Live'),
        GtexCreatorRevenueItem(label: 'Creator share market', amountLabel: '₵1.3M', status: 'Trading'),
        GtexCreatorRevenueItem(label: 'Sponsored news cards', amountLabel: '₵980K', status: 'Review'),
      ],
      awardSeasons: [
        GtexAwardSeason(
          id: 'award-1',
          title: 'GTEX World Player of the Year',
          status: 'Voting open',
          periodLabel: 'Season 2026',
          nominees: nominees,
        ),
        GtexAwardSeason(
          id: 'award-2',
          title: 'GTEX Regen Golden Boy',
          status: 'Shortlist locked',
          periodLabel: 'Q2 2026',
          nominees: nominees,
        ),
      ],
      socialStories: [
        GtexSocialStory(
          id: 'story-1',
          title: 'Victoria FC completed a ₵12.5M striker shortlist',
          sourceLabel: 'AI News Agency',
          body: 'A user-owned club is preparing a major squad rebuild after adding three elite forwards to its basket.',
          timeLabel: '8 min ago',
          reactionLabel: '2.4K reactions',
          clubLabel: 'Victoria FC',
        ),
        GtexSocialStory(
          id: 'story-2',
          title: 'New regen wonderkid enters award race',
          sourceLabel: 'Regen World',
          body: 'Mika Regen moved into the top three after a breakout performance in the U20 showcase.',
          timeLabel: '24 min ago',
          reactionLabel: '918 reactions',
          clubLabel: 'Lagos Royals',
        ),
        GtexSocialStory(
          id: 'story-3',
          title: 'Creator Cup registrations pass 64 clubs',
          sourceLabel: 'Creator Studio',
          body: 'The latest creator-hosted competition is now ready for bracket seeding and sponsor placement.',
          timeLabel: '1h ago',
          reactionLabel: '1.1K reactions',
        ),
      ],
      followedClubs: [
        GtexFollowedClub(
          id: 'club-1',
          name: 'Victoria FC',
          ownerLabel: 'Owned by Ayo',
          valueLabel: '₵84.2M value',
          followersLabel: '18.2K followers',
          sharePriceLabel: '₵42/share',
        ),
        GtexFollowedClub(
          id: 'club-2',
          name: 'Lagos Royals',
          ownerLabel: 'Owned by Trybe',
          valueLabel: '₵63.9M value',
          followersLabel: '11.4K followers',
          sharePriceLabel: '₵31/share',
        ),
      ],
      referral: GtexReferralSnapshot(
        code: 'GTEX-AYO-2026',
        invitesLabel: '418 accepted',
        rewardsLabel: '₵1.8M earned',
        pendingLabel: '27 pending KYC',
      ),
    );
  }
}
