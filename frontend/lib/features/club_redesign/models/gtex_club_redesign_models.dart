import 'package:flutter/material.dart';

@immutable
class GtexClubMember {
  const GtexClubMember({
    required this.id,
    required this.name,
    required this.position,
    required this.nationality,
    required this.valueCredits,
    required this.rating,
    this.imageUrl,
    this.isRegen = false,
  });

  final String id;
  final String name;
  final String position;
  final String nationality;
  final int valueCredits;
  final double rating;
  final String? imageUrl;
  final bool isRegen;
}

@immutable
class GtexClubNewsItem {
  const GtexClubNewsItem({
    required this.id,
    required this.headline,
    required this.category,
    required this.timestampLabel,
    required this.summary,
  });

  final String id;
  final String headline;
  final String category;
  final String timestampLabel;
  final String summary;
}

@immutable
class GtexClubOrderItem {
  const GtexClubOrderItem({
    required this.id,
    required this.title,
    required this.status,
    required this.amountCredits,
    required this.timestampLabel,
  });

  final String id;
  final String title;
  final String status;
  final int amountCredits;
  final String timestampLabel;
}

@immutable
class GtexClubTrophy {
  const GtexClubTrophy({
    required this.id,
    required this.title,
    required this.season,
    required this.tier,
  });

  final String id;
  final String title;
  final String season;
  final String tier;
}

@immutable
class GtexClubFinancialSnapshot {
  const GtexClubFinancialSnapshot({
    required this.walletCredits,
    required this.squadValueCredits,
    required this.openOrdersCredits,
    required this.monthlyRevenueCredits,
    required this.sharePriceCredits,
  });

  final int walletCredits;
  final int squadValueCredits;
  final int openOrdersCredits;
  final int monthlyRevenueCredits;
  final int sharePriceCredits;
}

@immutable
class GtexClubWorkspaceSnapshot {
  const GtexClubWorkspaceSnapshot({
    required this.clubId,
    required this.clubName,
    required this.shortCode,
    required this.country,
    required this.division,
    required this.ownerName,
    required this.followers,
    required this.shareholders,
    required this.finances,
    required this.squad,
    required this.news,
    required this.orders,
    required this.trophies,
    required this.identityTags,
    required this.activity,
  });

  final String clubId;
  final String clubName;
  final String shortCode;
  final String country;
  final String division;
  final String ownerName;
  final int followers;
  final int shareholders;
  final GtexClubFinancialSnapshot finances;
  final List<GtexClubMember> squad;
  final List<GtexClubNewsItem> news;
  final List<GtexClubOrderItem> orders;
  final List<GtexClubTrophy> trophies;
  final List<String> identityTags;
  final List<String> activity;

  int get squadValueCredits => finances.squadValueCredits;
  int get totalClubValueCredits =>
      finances.walletCredits + finances.squadValueCredits - finances.openOrdersCredits;

  static GtexClubWorkspaceSnapshot demo({
    String clubId = 'gtex-club-demo',
    String? clubName,
  }) {
    final String resolvedName = (clubName == null || clubName.trim().isEmpty)
        ? 'Lagos Eclipse FC'
        : clubName.trim();
    return GtexClubWorkspaceSnapshot(
      clubId: clubId,
      clubName: resolvedName,
      shortCode: _shortCode(resolvedName),
      country: 'Nigeria',
      division: 'GTEX Founders Division',
      ownerName: 'Club owner',
      followers: 18420,
      shareholders: 712,
      finances: const GtexClubFinancialSnapshot(
        walletCredits: 245000,
        squadValueCredits: 1680000,
        openOrdersCredits: 92000,
        monthlyRevenueCredits: 126500,
        sharePriceCredits: 35,
      ),
      squad: const <GtexClubMember>[
        GtexClubMember(
          id: 'p-001',
          name: 'Samuel Okoro',
          position: 'ST',
          nationality: 'Nigeria',
          valueCredits: 420000,
          rating: 83.4,
        ),
        GtexClubMember(
          id: 'p-002',
          name: 'Ethan Clarke',
          position: 'CM',
          nationality: 'England',
          valueCredits: 360000,
          rating: 81.2,
        ),
        GtexClubMember(
          id: 'r-117',
          name: 'Kaito Mensah',
          position: 'RW',
          nationality: 'Ghana',
          valueCredits: 190000,
          rating: 77.8,
          isRegen: true,
        ),
        GtexClubMember(
          id: 'p-004',
          name: 'Lucas Ferreira',
          position: 'CB',
          nationality: 'Brazil',
          valueCredits: 310000,
          rating: 79.6,
        ),
      ],
      news: const <GtexClubNewsItem>[
        GtexClubNewsItem(
          id: 'n-001',
          headline: 'Eclipse FC enter the market for a left-footed playmaker',
          category: 'Transfer room',
          timestampLabel: '12 min ago',
          summary:
              'The club scouting lane has pushed three Premier League options into the shortlist basket.',
        ),
        GtexClubNewsItem(
          id: 'n-002',
          headline: 'Regen winger Kaito Mensah named rising star of the week',
          category: 'Regen world',
          timestampLabel: '1 hr ago',
          summary:
              'Supporters are tracking the 17-year-old after two decisive creator-cup performances.',
        ),
      ],
      orders: const <GtexClubOrderItem>[
        GtexClubOrderItem(
          id: 'o-1001',
          title: 'Shortlist basket: Arsenal prospects',
          status: 'Awaiting payment',
          amountCredits: 92000,
          timestampLabel: 'Today',
        ),
        GtexClubOrderItem(
          id: 'o-1002',
          title: 'National rental: Nigeria U20 pool',
          status: 'Approved',
          amountCredits: 45000,
          timestampLabel: 'Yesterday',
        ),
      ],
      trophies: const <GtexClubTrophy>[
        GtexClubTrophy(
          id: 't-001',
          title: 'GTEX Founder Cup',
          season: '2026',
          tier: 'Gold',
        ),
        GtexClubTrophy(
          id: 't-002',
          title: 'Lagos Community Shield',
          season: '2026',
          tier: 'Silver',
        ),
      ],
      identityTags: const <String>[
        'Electric green home kit',
        'Midnight badge',
        'Youth-first recruitment',
        'AI newsroom active',
      ],
      activity: const <String>[
        'Added 4 players to shortlist basket',
        'Received 28 new club followers',
        'Share purchase window opened',
        'National rental pool refreshed',
      ],
    );
  }

  static String _shortCode(String name) {
    final List<String> parts = name
        .split(RegExp(r'\s+'))
        .where((String part) => part.trim().isNotEmpty)
        .toList(growable: false);
    if (parts.isEmpty) {
      return 'GTX';
    }
    return parts.take(3).map((String part) => part[0].toUpperCase()).join();
  }
}

String gtexFormatCredits(num credits) {
  final int value = credits.round();
  if (value >= 1000000) {
    return '${(value / 1000000).toStringAsFixed(value % 1000000 == 0 ? 0 : 1)}M cr';
  }
  if (value >= 1000) {
    return '${(value / 1000).toStringAsFixed(value % 1000 == 0 ? 0 : 1)}k cr';
  }
  return '$value cr';
}
