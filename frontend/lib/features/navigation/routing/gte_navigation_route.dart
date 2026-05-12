import 'package:flutter/material.dart';
import 'package:gte_frontend/features/competitions_hub/routing/competition_hub_destination.dart';

enum GtePrimaryDestination {
  home,
  competitions,
  market,
  hub,
  community,
  club,
  wallet,
}

enum GteCapitalDestination {
  wallet,
  orders,
  holdings,
  coinTraders,
  traderDashboard,
}

extension GteCapitalDestinationX on GteCapitalDestination {
  String get pathSegment {
    switch (this) {
      case GteCapitalDestination.wallet:
        return 'capital';
      case GteCapitalDestination.orders:
        return 'orders';
      case GteCapitalDestination.holdings:
        return 'holdings';
      case GteCapitalDestination.coinTraders:
        return 'coin-traders';
      case GteCapitalDestination.traderDashboard:
        return 'trader-dashboard';
    }
  }
}

extension GtePrimaryDestinationX on GtePrimaryDestination {
  String get label {
    switch (this) {
      case GtePrimaryDestination.home:
        return 'Home';
      case GtePrimaryDestination.competitions:
        return 'Matchday';
      case GtePrimaryDestination.market:
        return 'Transfer Hub';
      case GtePrimaryDestination.hub:
        return 'Studio';
      case GtePrimaryDestination.community:
        return 'Social';
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
      case GtePrimaryDestination.competitions:
        return 'play';
      case GtePrimaryDestination.market:
        return 'market';
      case GtePrimaryDestination.hub:
        return 'hub';
      case GtePrimaryDestination.community:
        return 'community';
      case GtePrimaryDestination.club:
        return 'club';
      case GtePrimaryDestination.wallet:
        return 'capital';
    }
  }

  String get routePath => '/app/$pathSegment';

  IconData get icon {
    switch (this) {
      case GtePrimaryDestination.home:
        return Icons.home_outlined;
      case GtePrimaryDestination.competitions:
        return Icons.play_circle_outline;
      case GtePrimaryDestination.market:
        return Icons.storefront_outlined;
      case GtePrimaryDestination.hub:
        return Icons.dashboard_outlined;
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
      case GtePrimaryDestination.competitions:
        return const Color(0xFFB26DFF);
      case GtePrimaryDestination.market:
        return const Color(0xFFFFA860);
      case GtePrimaryDestination.hub:
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
      case GtePrimaryDestination.competitions:
        return Icons.play_circle;
      case GtePrimaryDestination.market:
        return Icons.storefront;
      case GtePrimaryDestination.hub:
        return Icons.dashboard;
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
    this.capitalDestination = GteCapitalDestination.wallet,
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

  const GteNavigationRoute.hub()
    : this._(primaryDestination: GtePrimaryDestination.hub);

  const GteNavigationRoute.club()
    : this._(primaryDestination: GtePrimaryDestination.club);

  const GteNavigationRoute.wallet({
    GteCapitalDestination capitalDestination = GteCapitalDestination.wallet,
  }) : this._(
         primaryDestination: GtePrimaryDestination.wallet,
         capitalDestination: capitalDestination,
       );

  final GtePrimaryDestination primaryDestination;
  final CompetitionHubDestination? competitionDestination;
  final GteCapitalDestination capitalDestination;

  CompetitionHubDestination get effectiveCompetitionDestination =>
      competitionDestination ?? CompetitionHubDestination.overview;

  bool get isCompetitions =>
      primaryDestination == GtePrimaryDestination.competitions;

  String get path {
    if (isCompetitions) {
      return '/app/play/${effectiveCompetitionDestination.pathSegment}';
    }
    if (primaryDestination == GtePrimaryDestination.wallet) {
      switch (capitalDestination) {
        case GteCapitalDestination.wallet:
          return GtePrimaryDestination.wallet.routePath;
        case GteCapitalDestination.orders:
        case GteCapitalDestination.holdings:
          return '/app/capital/${capitalDestination.pathSegment}';
        case GteCapitalDestination.coinTraders:
        case GteCapitalDestination.traderDashboard:
          return '/app/${capitalDestination.pathSegment}';
      }
    }
    return primaryDestination.routePath;
  }

  GteNavigationRoute withPrimaryDestination(GtePrimaryDestination destination) {
    switch (destination) {
      case GtePrimaryDestination.home:
        return const GteNavigationRoute.home();
      case GtePrimaryDestination.competitions:
        return GteNavigationRoute.competitions(
          destination: effectiveCompetitionDestination,
        );
      case GtePrimaryDestination.market:
        return const GteNavigationRoute.market();
      case GtePrimaryDestination.hub:
        return const GteNavigationRoute.hub();
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

    final List<String> normalizedSegments =
        segments.isNotEmpty && segments.first.toLowerCase() == 'app'
            ? segments.sublist(1)
            : segments;
    if (normalizedSegments.isEmpty) {
      return const GteNavigationRoute.home();
    }

    switch (normalizedSegments.first.toLowerCase()) {
      case 'play':
      case 'competitions':
        return GteNavigationRoute.competitions(
          destination: competitionHubDestinationFromPathSegment(
            normalizedSegments.length > 1 ? normalizedSegments[1] : null,
          ),
        );
      case 'market':
      case 'transfer-hub':
        return const GteNavigationRoute.market();
      case 'coin-traders':
        return const GteNavigationRoute.wallet(
          capitalDestination: GteCapitalDestination.coinTraders,
        );
      case 'orders':
        return const GteNavigationRoute.wallet(
          capitalDestination: GteCapitalDestination.orders,
        );
      case 'holdings':
        return const GteNavigationRoute.wallet(
          capitalDestination: GteCapitalDestination.holdings,
        );
      case 'trader-dashboard':
        return const GteNavigationRoute.wallet(
          capitalDestination: GteCapitalDestination.traderDashboard,
        );
      case 'hub':
        return const GteNavigationRoute.hub();
      case 'community':
      case 'social':
        return const GteNavigationRoute.community();
      case 'club':
        return const GteNavigationRoute.club();
      case 'capital':
      case 'wallet':
        if (normalizedSegments.length > 1) {
          switch (normalizedSegments[1].toLowerCase()) {
            case 'orders':
              return const GteNavigationRoute.wallet(
                capitalDestination: GteCapitalDestination.orders,
              );
            case 'holdings':
              return const GteNavigationRoute.wallet(
                capitalDestination: GteCapitalDestination.holdings,
              );
            case 'coin-traders':
              return const GteNavigationRoute.wallet(
                capitalDestination: GteCapitalDestination.coinTraders,
              );
            case 'trader-dashboard':
              return const GteNavigationRoute.wallet(
                capitalDestination: GteCapitalDestination.traderDashboard,
              );
          }
        }
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
        other.competitionDestination == competitionDestination &&
        other.capitalDestination == capitalDestination;
  }

  @override
  int get hashCode => Object.hash(
    primaryDestination,
    competitionDestination,
    capitalDestination,
  );
}
