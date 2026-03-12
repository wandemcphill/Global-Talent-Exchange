import 'package:flutter/material.dart';

import '../controllers/creator_controller.dart';
import '../controllers/referral_controller.dart';
import '../data/gte_api_repository.dart';
import '../data/creator_api.dart';
import '../data/referral_api.dart';
import '../providers/gte_exchange_controller.dart';
import '../widgets/gte_shell_theme.dart';
import 'clubs/club_profile_screen.dart';
import 'competitions/competition_discovery_screen.dart';
import 'referrals/referral_hub_screen.dart';
import 'gte_exchange_player_detail_screen.dart';
import 'gte_login_screen.dart';
import 'gte_market_players_screen.dart';
import 'gte_portfolio_screen.dart';

class GteExchangeShellScreen extends StatefulWidget {
  const GteExchangeShellScreen({
    super.key,
    required this.controller,
    required this.apiBaseUrl,
    required this.backendMode,
  });

  final GteExchangeController controller;
  final String apiBaseUrl;
  final GteBackendMode backendMode;

  @override
  State<GteExchangeShellScreen> createState() => _GteExchangeShellScreenState();
}

class _GteExchangeShellScreenState extends State<GteExchangeShellScreen> {
  int _tabIndex = 0;
  late final CreatorController _creatorController;
  late final ReferralController _referralController;

  @override
  void initState() {
    super.initState();
    _creatorController = CreatorController(
      api: CreatorApi.standard(
        baseUrl: widget.apiBaseUrl,
        mode: widget.backendMode,
      ),
    );
    _referralController = ReferralController(
      api: ReferralApi.standard(
        baseUrl: widget.apiBaseUrl,
        mode: widget.backendMode,
      ),
    );
    widget.controller.bootstrap();
  }

  @override
  void dispose() {
    _creatorController.dispose();
    _referralController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Text('Global Talent Exchange'),
              Text(
                widget.apiBaseUrl,
                style: const TextStyle(fontSize: 12),
              ),
            ],
          ),
          actions: <Widget>[
            AnimatedBuilder(
              animation: widget.controller,
              builder: (BuildContext context, Widget? child) {
                if (widget.controller.isAuthenticated) {
                  return Row(
                    children: <Widget>[
                      Padding(
                        padding: const EdgeInsets.only(right: 12),
                        child: Center(
                          child: Text(widget.controller.session!.user.username),
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.only(right: 16),
                        child: FilledButton.tonal(
                          onPressed: () async {
                            await widget.controller.signOut();
                            if (!mounted) {
                              return;
                            }
                            setState(() {
                              _tabIndex = 0;
                            });
                          },
                          child: const Text('Sign out'),
                        ),
                      ),
                    ],
                  );
                }
                return Padding(
                  padding: const EdgeInsets.only(right: 16),
                  child: FilledButton(
                    onPressed: () {
                      _openLogin();
                    },
                    child: const Text('Sign in'),
                  ),
                );
              },
            ),
          ],
        ),
        body: AnimatedBuilder(
          animation: widget.controller,
          builder: (BuildContext context, Widget? child) {
            if (widget.controller.isBootstrapping &&
                widget.controller.players.isEmpty) {
              return const Center(child: CircularProgressIndicator());
            }

            switch (_tabIndex) {
              case 1:
                return GtePortfolioScreen(
                  controller: widget.controller,
                  onOpenPlayer: (String playerId) {
                    _openPlayer(playerId);
                  },
                  onOpenLogin: () {
                    _openLogin(targetTab: 1);
                  },
                );
              case 2:
                return ClubProfileScreen(
                  clubId: _clubProfileId(),
                  clubName: _clubProfileName(),
                  baseUrl: widget.apiBaseUrl,
                  backendMode: widget.backendMode,
                  isAuthenticated: widget.controller.isAuthenticated,
                  onOpenLogin: () => _openLogin(targetTab: 2),
                );
              case 3:
                return CompetitionDiscoveryScreen(
                  baseUrl: widget.apiBaseUrl,
                  backendMode: widget.backendMode,
                  currentUserId: _competitionUserId(),
                  currentUserName: _competitionUserName(),
                  isAuthenticated: widget.controller.isAuthenticated,
                  onOpenLogin: () => _openLogin(targetTab: 3),
                );
              case 4:
                return ReferralHubScreen(
                  referralController: _referralController,
                  creatorController: _creatorController,
                );
              case 0:
              default:
                return GteMarketPlayersScreen(
                  controller: widget.controller,
                  onOpenPlayer: (String playerId) {
                    _openPlayer(playerId);
                  },
                  onOpenLogin: () {
                    _openLogin();
                  },
                );
            }
          },
        ),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _tabIndex,
          onDestinationSelected: (int index) {
            setState(() {
              _tabIndex = index;
            });
            if (index == 1 && widget.controller.isAuthenticated) {
              widget.controller.refreshAccount();
            }
          },
          destinations: const <NavigationDestination>[
            NavigationDestination(
              icon: Icon(Icons.groups_outlined),
              selectedIcon: Icon(Icons.groups),
              label: 'Market',
            ),
            NavigationDestination(
              icon: Icon(Icons.account_balance_wallet_outlined),
              selectedIcon: Icon(Icons.account_balance_wallet),
              label: 'Portfolio',
            ),
            NavigationDestination(
              icon: Icon(Icons.shield_outlined),
              selectedIcon: Icon(Icons.shield),
              label: 'Club',
            ),
            NavigationDestination(
              icon: Icon(Icons.emoji_events_outlined),
              selectedIcon: Icon(Icons.emoji_events),
              label: 'Competitions',
            ),
            NavigationDestination(
              icon: Icon(Icons.campaign_outlined),
              selectedIcon: Icon(Icons.campaign),
              label: 'Community',
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _openLogin({
    int? targetTab,
  }) async {
    final bool? signedIn = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (BuildContext context) =>
            GteLoginScreen(controller: widget.controller),
      ),
    );
    if (!mounted || signedIn != true || targetTab == null) {
      return;
    }
    setState(() {
      _tabIndex = targetTab;
    });
  }

  Future<void> _openPlayer(String playerId) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => GteExchangePlayerDetailScreen(
          controller: widget.controller,
          playerId: playerId,
          onRequireLogin: () {
            _openLogin();
          },
        ),
      ),
    );
  }

  String _competitionUserId() {
    final String? sessionUserId = widget.controller.session?.user.id.trim();
    if (sessionUserId != null && sessionUserId.isNotEmpty) {
      return sessionUserId;
    }
    return 'demo-user';
  }

  String _competitionUserName() {
    final String? displayName =
        widget.controller.session?.user.displayName?.trim();
    if (displayName != null && displayName.isNotEmpty) {
      return displayName;
    }
    final String username =
        widget.controller.session?.user.username.trim() ?? '';
    if (username.isNotEmpty) {
      return username;
    }
    return 'Demo Fan';
  }

  String _clubProfileId() {
    final String? displayName =
        widget.controller.session?.user.displayName?.trim();
    if (displayName != null && displayName.isNotEmpty) {
      return _slugifyClub(displayName);
    }
    final String username =
        widget.controller.session?.user.username.trim() ?? '';
    if (username.isNotEmpty) {
      return _slugifyClub(username);
    }
    return 'royal-lagos-fc';
  }

  String _clubProfileName() {
    final String? displayName =
        widget.controller.session?.user.displayName?.trim();
    if (displayName != null && displayName.isNotEmpty) {
      return displayName;
    }
    final String username =
        widget.controller.session?.user.username.trim() ?? '';
    if (username.isNotEmpty) {
      return username;
    }
    return 'Royal Lagos FC';
  }

  String _slugifyClub(String raw) {
    final String slug = raw
        .toLowerCase()
        .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
        .replaceAll(RegExp(r'^-+|-+$'), '');
    return slug.isEmpty ? 'royal-lagos-fc' : slug;
  }
}
