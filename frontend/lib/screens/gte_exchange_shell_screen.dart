import 'package:flutter/material.dart';

import '../controllers/creator_controller.dart';
import '../controllers/referral_controller.dart';
import '../data/creator_api.dart';
import '../data/gte_api_repository.dart';
import '../data/referral_api.dart';
import '../providers/gte_exchange_controller.dart';
import '../widgets/gte_shell_theme.dart';
import '../widgets/gte_surface_panel.dart';
import '../widgets/gtex_branding.dart';
import 'clubs/club_profile_screen.dart';
import 'competitions/competition_discovery_screen.dart';
import 'gte_exchange_player_detail_screen.dart';
import 'gte_login_screen.dart';
import 'gte_market_players_screen.dart';
import 'gte_portfolio_screen.dart';
import 'referrals/referral_hub_screen.dart';

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

  static const List<_ShellTabMeta> _tabs = <_ShellTabMeta>[
    _ShellTabMeta('Market', 'Trading floor', Icons.candlestick_chart, Color(0xFF72F0D8)),
    _ShellTabMeta('Portfolio', 'Capital room', Icons.account_balance_wallet_outlined, Color(0xFFFFD66B)),
    _ShellTabMeta('Club', 'Identity lab', Icons.shield_outlined, Color(0xFF85B8FF)),
    _ShellTabMeta('Competitions', 'Live match center', Icons.stadium_outlined, Color(0xFFB26DFF)),
    _ShellTabMeta('Community', 'Creator network', Icons.campaign_outlined, Color(0xFFFF8C9E)),
  ];

  @override
  void initState() {
    super.initState();
    _creatorController = CreatorController(
      api: CreatorApi.standard(
        baseUrl: widget.apiBaseUrl,
        accessToken: widget.controller.session?.accessToken,
        mode: widget.backendMode,
      ),
    );
    _referralController = ReferralController(
      api: ReferralApi.standard(baseUrl: widget.apiBaseUrl, mode: widget.backendMode),
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
    final _ShellTabMeta activeTab = _tabs[_tabIndex];
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          toolbarHeight: 88,
          titleSpacing: 20,
          title: Row(
            children: <Widget>[
              const Expanded(child: GtexWordmark(compact: true)),
              const SizedBox(width: 12),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(16),
                  color: activeTab.color.withValues(alpha: 0.12),
                  border: Border.all(color: activeTab.color.withValues(alpha: 0.22)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    Text(activeTab.kicker, style: Theme.of(context).textTheme.bodySmall?.copyWith(color: activeTab.color)),
                    Text(activeTab.label, style: Theme.of(context).textTheme.titleMedium),
                  ],
                ),
              ),
            ],
          ),
          actions: <Widget>[
            Padding(
              padding: const EdgeInsets.only(right: 20),
              child: AnimatedBuilder(
                animation: widget.controller,
                builder: (BuildContext context, Widget? child) {
                  if (widget.controller.isAuthenticated) {
                    return Row(
                      children: <Widget>[
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(16),
                            color: Colors.white.withValues(alpha: 0.04),
                            border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
                          ),
                          child: Text(widget.controller.session!.user.username),
                        ),
                        const SizedBox(width: 12),
                        FilledButton.tonal(
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
                      ],
                    );
                  }
                  return FilledButton.icon(
                    onPressed: _openLogin,
                    icon: const Icon(Icons.login),
                    label: const Text('Sign in'),
                  );
                },
              ),
            ),
          ],
        ),
        body: Column(
          children: <Widget>[
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
              child: GteSurfacePanel(
                emphasized: true,
                accentColor: activeTab.color,
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: <Widget>[
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(18),
                        color: activeTab.color.withValues(alpha: 0.12),
                      ),
                      child: Icon(activeTab.icon, color: activeTab.color),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(activeTab.bannerTitle, style: Theme.of(context).textTheme.titleLarge),
                          const SizedBox(height: 4),
                          Text(activeTab.bannerBody, style: Theme.of(context).textTheme.bodyMedium),
                        ],
                      ),
                    ),
                    const SizedBox(width: 12),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(16),
                        color: Colors.white.withValues(alpha: 0.04),
                        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
                      ),
                      child: Text(widget.apiBaseUrl, style: Theme.of(context).textTheme.bodySmall),
                    ),
                  ],
                ),
              ),
            ),
            Expanded(
              child: AnimatedBuilder(
                animation: widget.controller,
                builder: (BuildContext context, Widget? child) {
                  if (widget.controller.isBootstrapping && widget.controller.players.isEmpty) {
                    return const Center(child: CircularProgressIndicator());
                  }

                  switch (_tabIndex) {
                    case 1:
                      return GtePortfolioScreen(
                        controller: widget.controller,
                        onOpenPlayer: _openPlayer,
                        onOpenLogin: () => _openLogin(targetTab: 1),
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
                        onOpenPlayer: _openPlayer,
                        onOpenLogin: _openLogin,
                      );
                  }
                },
              ),
            ),
          ],
        ),
        bottomNavigationBar: NavigationBar(
          height: 78,
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
            NavigationDestination(icon: Icon(Icons.candlestick_chart_outlined), selectedIcon: Icon(Icons.candlestick_chart), label: 'Market'),
            NavigationDestination(icon: Icon(Icons.account_balance_wallet_outlined), selectedIcon: Icon(Icons.account_balance_wallet), label: 'Portfolio'),
            NavigationDestination(icon: Icon(Icons.shield_outlined), selectedIcon: Icon(Icons.shield), label: 'Club'),
            NavigationDestination(icon: Icon(Icons.stadium_outlined), selectedIcon: Icon(Icons.stadium), label: 'Arena'),
            NavigationDestination(icon: Icon(Icons.campaign_outlined), selectedIcon: Icon(Icons.campaign), label: 'Community'),
          ],
        ),
      ),
    );
  }

  Future<void> _openLogin({int? targetTab}) async {
    final bool? signedIn = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(builder: (BuildContext context) => GteLoginScreen(controller: widget.controller)),
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
          onRequireLogin: _openLogin,
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
    final String? displayName = widget.controller.session?.user.displayName?.trim();
    if (displayName != null && displayName.isNotEmpty) {
      return displayName;
    }
    final String username = widget.controller.session?.user.username.trim() ?? '';
    if (username.isNotEmpty) {
      return username;
    }
    return 'Demo Fan';
  }

  String _clubProfileId() {
    final String? displayName = widget.controller.session?.user.displayName?.trim();
    if (displayName != null && displayName.isNotEmpty) {
      return _slugifyClub(displayName);
    }
    final String username = widget.controller.session?.user.username.trim() ?? '';
    if (username.isNotEmpty) {
      return _slugifyClub(username);
    }
    return 'royal-lagos-fc';
  }

  String _clubProfileName() {
    final String? displayName = widget.controller.session?.user.displayName?.trim();
    if (displayName != null && displayName.isNotEmpty) {
      return displayName;
    }
    final String username = widget.controller.session?.user.username.trim() ?? '';
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

class _ShellTabMeta {
  const _ShellTabMeta(this.label, this.kicker, this.icon, this.color);

  final String label;
  final String kicker;
  final IconData icon;
  final Color color;

  String get bannerTitle => switch (label) {
        'Market' => 'Trade mode is tight, analytical, and terminal-fast.',
        'Portfolio' => 'Capital mode is calm, precise, and trust-first.',
        'Club' => 'Club mode is identity, dynasty, and long-horizon control.',
        'Competitions' => 'Arena mode is cinematic, live, and match-story driven.',
        _ => 'Community mode connects creators, referrals, and growth loops.',
      };

  String get bannerBody => switch (label) {
        'Market' => 'Scan quotes, movement, and demand with zero arena clutter.',
        'Portfolio' => 'Track available cash, reserved capital, holdings, and order readiness.',
        'Club' => 'Shape the institution behind the badge, not just the next trade.',
        'Competitions' => 'Step into fixtures, highlights, live cards, and creator-hosted tournaments.',
        _ => 'Promoters, creators, and fans keep the GTEX flywheel turning.',
      };
}
