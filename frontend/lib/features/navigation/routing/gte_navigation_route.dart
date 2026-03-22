import 'package:flutter/material.dart';
import 'package:gte_frontend/features/competitions_hub/routing/competition_hub_destination.dart';

enum GtePrimaryDestination {
  home,
  market,
  competitions,
  community,
  club,
  wallet,
}

extension GtePrimaryDestinationX on GtePrimaryDestination {
  String get label {
    switch (this) {
      case GtePrimaryDestination.home:
        return 'Home';
      case GtePrimaryDestination.market:
        return 'Trade';
      case GtePrimaryDestination.competitions:
        return 'Arena';
      case GtePrimaryDestination.community:
        return 'Community';
      case GtePrimaryDestination.club:
        return 'Club';
      case GtePrimaryDestination.wallet:
        return 'Wallet';
    }
  }

  String get pathSegment {
    switch (this) {
      case GtePrimaryDestination.home:
        return 'home';
      case GtePrimaryDestination.market:
        return 'market';
      case GtePrimaryDestination.competitions:
        return 'competitions';
      case GtePrimaryDestination.community:
        return 'community';
      case GtePrimaryDestination.club:
        return 'club';
      case GtePrimaryDestination.wallet:
        return 'wallet';
    }
  }

  String get routePath => '/app/$pathSegment';

  IconData get icon {
    switch (this) {
      case GtePrimaryDestination.home:
        return Icons.home_outlined;
      case GtePrimaryDestination.market:
        return Icons.show_chart_outlined;
      case GtePrimaryDestination.competitions:
        return Icons.emoji_events_outlined;
      case GtePrimaryDestination.community:
        return Icons.forum_outlined;
      case GtePrimaryDestination.club:
        return Icons.shield_outlined;
      case GtePrimaryDestination.wallet:
        return Icons.account_balance_wallet_outlined;
    }
  }



  Color get accentColor {
    switch (this) {
      case GtePrimaryDestination.home:
        return const Color(0xFF72F0D8);
      case GtePrimaryDestination.market:
        return const Color(0xFF72F0D8);
      case GtePrimaryDestination.competitions:
        return const Color(0xFFB26DFF);
      case GtePrimaryDestination.community:
        return const Color(0xFF5FE3A1);
      case GtePrimaryDestination.club:
        return const Color(0xFF85B8FF);
      case GtePrimaryDestination.wallet:
        return const Color(0xFFFFD66B);
    }
  }

  IconData get selectedIcon {
    switch (this) {
      case GtePrimaryDestination.home:
        return Icons.home;
      case GtePrimaryDestination.market:
        return Icons.show_chart;
      case GtePrimaryDestination.competitions:
        return Icons.emoji_events;
      case GtePrimaryDestination.community:
        return Icons.forum;
      case GtePrimaryDestination.club:
        return Icons.shield;
      case GtePrimaryDestination.wallet:
        return Icons.account_balance_wallet;
    }
  }
}

class GteNavigationRoute {
  const GteNavigationRoute._({
    required this.primaryDestination,
    this.competitionDestination,
  });

  const GteNavigationRoute.home()
      : this._(primaryDestination: GtePrimaryDestination.home);

  const GteNavigationRoute.market()
      : this._(primaryDestination: GtePrimaryDestination.market);

  const GteNavigationRoute.competitions({
    CompetitionHubDestination destination = CompetitionHubDestination.overview,
  }) : this._(
          primaryDestination: GtePrimaryDestination.competitions,
          competitionDestination: destination,
        );

  const GteNavigationRoute.community()
      : this._(primaryDestination: GtePrimaryDestination.community);

  const GteNavigationRoute.club()
      : this._(primaryDestination: GtePrimaryDestination.club);

  const GteNavigationRoute.wallet()
      : this._(primaryDestination: GtePrimaryDestination.wallet);

  final GtePrimaryDestination primaryDestination;
  final CompetitionHubDestination? competitionDestination;

  CompetitionHubDestination get effectiveCompetitionDestination =>
      competitionDestination ?? CompetitionHubDestination.overview;

  bool get isCompetitions =>
      primaryDestination == GtePrimaryDestination.competitions;

  String get path {
    if (isCompetitions) {
      return '/app/competitions/${effectiveCompetitionDestination.pathSegment}';
    }
    return primaryDestination.routePath;
  }

  GteNavigationRoute withPrimaryDestination(GtePrimaryDestination destination) {
    switch (destination) {
      case GtePrimaryDestination.home:
        return const GteNavigationRoute.home();
      case GtePrimaryDestination.market:
        return const GteNavigationRoute.market();
      case GtePrimaryDestination.competitions:
        return GteNavigationRoute.competitions(
          destination: effectiveCompetitionDestination,
        );
      case GtePrimaryDestination.community:
        return const GteNavigationRoute.community();
      case GtePrimaryDestination.club:
        return const GteNavigationRoute.club();
      case GtePrimaryDestination.wallet:
        return const GteNavigationRoute.wallet();
    }
  }

  GteNavigationRoute withCompetitionDestination(
    CompetitionHubDestination destination,
  ) {
    return GteNavigationRoute.competitions(destination: destination);
  }

  static GteNavigationRoute parse(String? rawPath) {
    final String normalized = (rawPath ?? '').trim();
    if (normalized.isEmpty || normalized == '/') {
      return const GteNavigationRoute.home();
    }

    final Uri? uri = Uri.tryParse(
      normalized.startsWith('/') ? normalized : '/$normalized',
    );
    if (uri == null) {
      return const GteNavigationRoute.home();
    }
    final List<String> segments =
        uri.pathSegments.where((String item) => item.isNotEmpty).toList();
    if (segments.isEmpty) {
      return const GteNavigationRoute.home();
    }

    final List<String> normalizedSegments = segments.isNotEmpty && segments.first.toLowerCase() == 'app'
        ? segments.sublist(1)
        : segments;
    if (normalizedSegments.isEmpty) {
      return const GteNavigationRoute.home();
    }

    switch (normalizedSegments.first.toLowerCase()) {
      case 'market':
        return const GteNavigationRoute.market();
      case 'competitions':
        return GteNavigationRoute.competitions(
          destination: competitionHubDestinationFromPathSegment(
            normalizedSegments.length > 1 ? normalizedSegments[1] : null,
          ),
        );
      case 'community':
        return const GteNavigationRoute.community();
      case 'club':
        return const GteNavigationRoute.club();
      case 'wallet':
        return const GteNavigationRoute.wallet();
      case 'home':
      default:
        return const GteNavigationRoute.home();
    }
  }

  @override
  bool operator ==(Object other) {
    return other is GteNavigationRoute &&
        other.primaryDestination == primaryDestination &&
        other.competitionDestination == competitionDestination;
  }

  @override
  int get hashCode => Object.hash(primaryDestination, competitionDestination);
}
