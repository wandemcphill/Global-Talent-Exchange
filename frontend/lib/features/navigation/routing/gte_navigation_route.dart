import 'package:flutter/material.dart';
import 'package:gte_frontend/features/compete/domain/competition_hub_destination.dart';

enum GtePrimaryDestination {
  home,
  market,
  club,
  competitions,
  wallet,
  community,
  hub,
  admin,
}

extension GtePrimaryDestinationX on GtePrimaryDestination {
  String get label {
    switch (this) {
      case GtePrimaryDestination.home:
        return 'World';
      case GtePrimaryDestination.market:
        return 'Market';
      case GtePrimaryDestination.club:
        return 'Club';
      case GtePrimaryDestination.competitions:
        return 'Compete';
      case GtePrimaryDestination.wallet:
        return 'Capital';
      case GtePrimaryDestination.community:
        return 'Community';
      case GtePrimaryDestination.hub:
        return 'Creator';
      case GtePrimaryDestination.admin:
        return 'Admin';
    }
  }

  String get pathSegment {
    switch (this) {
      case GtePrimaryDestination.home:
        return 'world';
      case GtePrimaryDestination.market:
        return 'market';
      case GtePrimaryDestination.club:
        return 'club';
      case GtePrimaryDestination.competitions:
        return 'compete';
      case GtePrimaryDestination.wallet:
        return 'capital';
      case GtePrimaryDestination.community:
        return 'community';
      case GtePrimaryDestination.hub:
        return 'creator';
      case GtePrimaryDestination.admin:
        return 'admin';
    }
  }

  String get routePath => '/app/$pathSegment';

  IconData get icon {
    switch (this) {
      case GtePrimaryDestination.home:
        return Icons.public_outlined;
      case GtePrimaryDestination.market:
        return Icons.storefront_outlined;
      case GtePrimaryDestination.club:
        return Icons.shield_outlined;
      case GtePrimaryDestination.competitions:
        return Icons.emoji_events_outlined;
      case GtePrimaryDestination.wallet:
        return Icons.account_balance_wallet_outlined;
      case GtePrimaryDestination.community:
        return Icons.forum_outlined;
      case GtePrimaryDestination.hub:
        return Icons.campaign_outlined;
      case GtePrimaryDestination.admin:
        return Icons.admin_panel_settings_outlined;
    }
  }

  Color get accentColor {
    switch (this) {
      case GtePrimaryDestination.home:
        return const Color(0xFF69F3A4);
      case GtePrimaryDestination.market:
        return const Color(0xFF66D7FF);
      case GtePrimaryDestination.club:
        return const Color(0xFFB7F05A);
      case GtePrimaryDestination.competitions:
        return const Color(0xFFFFD75B);
      case GtePrimaryDestination.wallet:
        return const Color(0xFFFFD66B);
      case GtePrimaryDestination.community:
        return const Color(0xFF5FE3A1);
      case GtePrimaryDestination.hub:
        return const Color(0xFFB26DFF);
      case GtePrimaryDestination.admin:
        return const Color(0xFFFF7B5C);
    }
  }

  IconData get selectedIcon {
    switch (this) {
      case GtePrimaryDestination.home:
        return Icons.public;
      case GtePrimaryDestination.market:
        return Icons.storefront;
      case GtePrimaryDestination.club:
        return Icons.shield;
      case GtePrimaryDestination.competitions:
        return Icons.emoji_events;
      case GtePrimaryDestination.wallet:
        return Icons.account_balance_wallet;
      case GtePrimaryDestination.community:
        return Icons.forum;
      case GtePrimaryDestination.hub:
        return Icons.campaign;
      case GtePrimaryDestination.admin:
        return Icons.admin_panel_settings;
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

  const GteNavigationRoute.hub()
    : this._(primaryDestination: GtePrimaryDestination.hub);

  const GteNavigationRoute.club()
    : this._(primaryDestination: GtePrimaryDestination.club);

  const GteNavigationRoute.wallet()
    : this._(primaryDestination: GtePrimaryDestination.wallet);

  const GteNavigationRoute.admin()
    : this._(primaryDestination: GtePrimaryDestination.admin);

  final GtePrimaryDestination primaryDestination;
  final CompetitionHubDestination? competitionDestination;

  CompetitionHubDestination get effectiveCompetitionDestination =>
      competitionDestination ?? CompetitionHubDestination.overview;

  bool get isCompetitions =>
      primaryDestination == GtePrimaryDestination.competitions;

  String get path {
    if (isCompetitions) {
      if (effectiveCompetitionDestination ==
          CompetitionHubDestination.overview) {
        return primaryDestination.routePath;
      }
      return '/app/compete/${effectiveCompetitionDestination.pathSegment}';
    }
    return primaryDestination.routePath;
  }

  GteNavigationRoute withPrimaryDestination(GtePrimaryDestination destination) {
    switch (destination) {
      case GtePrimaryDestination.home:
        return const GteNavigationRoute.home();
      case GtePrimaryDestination.market:
        return const GteNavigationRoute.market();
      case GtePrimaryDestination.club:
        return const GteNavigationRoute.club();
      case GtePrimaryDestination.competitions:
        return GteNavigationRoute.competitions(
          destination: effectiveCompetitionDestination,
        );
      case GtePrimaryDestination.wallet:
        return const GteNavigationRoute.wallet();
      case GtePrimaryDestination.community:
        return const GteNavigationRoute.community();
      case GtePrimaryDestination.hub:
        return const GteNavigationRoute.hub();
      case GtePrimaryDestination.admin:
        return const GteNavigationRoute.admin();
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
      case 'compete':
      case 'competitions':
        return GteNavigationRoute.competitions(
          destination: competitionHubDestinationFromPathSegment(
            normalizedSegments.length > 1 ? normalizedSegments[1] : null,
          ),
        );
      case 'world':
      case 'home':
        return const GteNavigationRoute.home();
      case 'market':
        return const GteNavigationRoute.market();
      case 'creator':
      case 'studio':
      case 'hub':
        return const GteNavigationRoute.hub();
      case 'community':
        return const GteNavigationRoute.community();
      case 'club':
        return const GteNavigationRoute.club();
      case 'capital':
      case 'wallet':
        return const GteNavigationRoute.wallet();
      case 'admin':
        return const GteNavigationRoute.admin();
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
