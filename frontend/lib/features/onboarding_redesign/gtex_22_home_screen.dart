import 'dart:async';

import 'package:flutter/material.dart';
import 'package:gte_frontend/app/gte_app_config.dart';
import 'package:gte_frontend/data/public_pulse_api.dart';

import 'components/gtex_club_ownership_section.dart';
import 'components/gtex_club_valuation_section.dart';
import 'components/gtex_competitions_and_jackpot_section.dart';
import 'components/gtex_conversion_and_footer_section.dart';
import 'components/gtex_hero_section.dart';
import 'components/gtex_home_nav.dart';
import 'components/gtex_home_shared_widgets.dart';
import 'components/gtex_how_it_works_section.dart';
import 'components/gtex_living_world_section.dart';
import 'components/gtex_platform_map_section.dart';
import 'components/gtex_regen_economy_section.dart';
import 'components/gtex_trust_and_integrity_section.dart';
import 'components/gtex_tv_and_finance_section.dart';
import 'components/gtex_wider_universe_section.dart';

/// GTEX 2027 Public Homepage & Football Universe Experience.
///
/// Communicates club ownership, TV revenue mechanics, regen economy,
/// active competitions, luxury showroom aviation, and the wider football universe.
class Gtex22HomeScreen extends StatefulWidget {
  const Gtex22HomeScreen({
    super.key,
    this.onSignup,
    this.onLogin,
    this.onCreatorSignup,
    this.onTraderSignup,
    this.onExploreMarket,
    this.pulseApi,
  });

  final VoidCallback? onSignup;
  final VoidCallback? onLogin;
  final VoidCallback? onCreatorSignup;
  final VoidCallback? onTraderSignup;
  final VoidCallback? onExploreMarket;
  final PublicPulseApi? pulseApi;

  @override
  State<Gtex22HomeScreen> createState() => _Gtex22HomeScreenState();
}

class _Gtex22HomeScreenState extends State<Gtex22HomeScreen> {
  final ScrollController _scrollController = ScrollController();
  final GlobalKey _heroKey = GlobalKey();
  final GlobalKey _platformMapKey = GlobalKey();
  final GlobalKey _worldKey = GlobalKey();
  final GlobalKey _ownershipKey = GlobalKey();
  final GlobalKey _financeKey = GlobalKey();
  final GlobalKey _regensKey = GlobalKey();
  final GlobalKey _competitionsKey = GlobalKey();
  final GlobalKey _universeKey = GlobalKey();
  final GlobalKey _trustKey = GlobalKey();

  GtexLiveWorldPulse? _pulse;
  String? _jackpotLabel;
  String? _jackpotBalance;
  DateTime? _failsafeAt;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _loadPulse();
    _loadJackpot();
    _refreshTimer = Timer.periodic(const Duration(seconds: 45), (_) {
      _loadPulse();
      _loadJackpot();
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadPulse() async {
    try {
      final GteAppConfig config = GteAppConfig.fromRuntimeEnvironment();
      final PublicPulseApi api =
          widget.pulseApi ??
          PublicPulseApi.standard(
            baseUrl: config.apiBaseUrl,
            mode: config.activeShellBackendMode,
          );
      final GtexLiveWorldPulse pulse = await api.fetchLiveStats();
      if (!mounted) {
        return;
      }
      setState(() => _pulse = pulse);
    } catch (_) {
      // Gracefully silent: never invent fake numbers when network is unreachable
    }
  }

  Future<void> _loadJackpot() async {
    try {
      final GteAppConfig config = GteAppConfig.fromRuntimeEnvironment();
      final PublicPulseApi api =
          widget.pulseApi ??
          PublicPulseApi.standard(
            baseUrl: config.apiBaseUrl,
            mode: config.activeShellBackendMode,
          );
      final Map<String, dynamic> state = await api.client.getMap(
        '/jackpot/state',
        auth: false,
      );
      if (!mounted) {
        return;
      }
      final Object? balance = state['balance'] ?? state['current_balance'];
      final Object? rawFailsafe = state['failsafe_at'] ?? state['failsafeAt'];
      String label = 'Jackpot';
      String? balanceStr;
      if (balance != null) {
        balanceStr = '$balance GTC';
        label = 'Jackpot $balance';
      }
      final DateTime? due = rawFailsafe == null
          ? null
          : DateTime.tryParse(rawFailsafe.toString())?.toUtc();
      if (due != null) {
        final Duration remaining = due.difference(DateTime.now().toUtc());
        if (!remaining.isNegative) {
          final String hh = remaining.inHours.toString().padLeft(2, '0');
          final String mm = (remaining.inMinutes % 60).toString().padLeft(2, '0');
          final String ss = (remaining.inSeconds % 60).toString().padLeft(2, '0');
          label = 'Drop $hh:$mm:$ss';
        }
      }
      setState(() {
        _jackpotLabel = label;
        _jackpotBalance = balanceStr;
        _failsafeAt = due;
      });
    } catch (_) {
      if (mounted) {
        setState(() {
          _jackpotLabel = null;
        });
      }
    }
  }

  void _scrollToSection(String sectionKey) {
    GlobalKey? targetKey;
    switch (sectionKey) {
      case 'hero':
        targetKey = _heroKey;
        break;
      case 'platform':
        targetKey = _platformMapKey;
        break;
      case 'world':
        targetKey = _worldKey;
        break;
      case 'ownership':
        targetKey = _ownershipKey;
        break;
      case 'finance':
        targetKey = _financeKey;
        break;
      case 'regens':
        targetKey = _regensKey;
        break;
      case 'competitions':
        targetKey = _competitionsKey;
        break;
      case 'universe':
        targetKey = _universeKey;
        break;
      case 'trust':
        targetKey = _trustKey;
        break;
    }

    if (targetKey?.currentContext != null) {
      Scrollable.ensureVisible(
        targetKey!.currentContext!,
        duration: const Duration(milliseconds: 600),
        curve: Curves.easeInOutCubic,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kNavyBase,
      body: SelectionArea(
        child: CustomScrollView(
          controller: _scrollController,
          slivers: <Widget>[
            // 1. World-Class Sticky Nav
            SliverToBoxAdapter(
              child: GtexHomeNav(
                onLogin: widget.onLogin,
                onSignup: widget.onSignup,
                pulse: _pulse,
                jackpotLabel: _jackpotLabel,
                onScrollToSection: _scrollToSection,
              ),
            ),

            // 2. Cinematic Hero & Live Pulse
            SliverToBoxAdapter(
              key: _heroKey,
              child: GtexHeroSection(
                onSignup: widget.onSignup,
                onExplore: widget.onExploreMarket ?? () => _scrollToSection('platform'),
                pulse: _pulse,
              ),
            ),

            // 3. Clarity Strip (Preserves exact tested signal words)
            const SliverToBoxAdapter(
              child: GtexClarityStrip(),
            ),

            // 4. Platform Map Section (Immediately following hero & clarity strip)
            SliverToBoxAdapter(
              key: _platformMapKey,
              child: GtexPlatformMapSection(
                onSignup: widget.onSignup,
              ),
            ),

            // 5. Living GTEX World (Ticker & Grounded Newsroom)
            SliverToBoxAdapter(
              key: _worldKey,
              child: const GtexLivingWorldSection(),
            ),

            // 6. Club Ownership & Simulation Life (Stages & Luxury Aviation)
            SliverToBoxAdapter(
              key: _ownershipKey,
              child: GtexClubOwnershipSection(
                onClaimClub: widget.onSignup,
              ),
            ),

            // 7. The Business of Owning a Club: TV Revenue & Financial Stories
            SliverToBoxAdapter(
              key: _financeKey,
              child: const GtexTvAndFinanceSection(),
            ),

            // 8. Regen Discovery, Development & Marketplace
            SliverToBoxAdapter(
              key: _regensKey,
              child: const GtexRegenEconomySection(),
            ),

            // 9. Competitions, Prize Pools & 4 Scheduled Daily Jackpots
            SliverToBoxAdapter(
              key: _competitionsKey,
              child: GtexCompetitionsAndJackpotSection(
                initialJackpotBalance: _jackpotBalance,
                initialFailsafeAt: _failsafeAt,
              ),
            ),

            // 10. Wider Football Universe (National Teams, Managers & Tribes)
            SliverToBoxAdapter(
              key: _universeKey,
              child: const GtexWiderUniverseSection(),
            ),

            // 11. Club Valuations, Eligible Ownership Sales & Commercial Rights
            const SliverToBoxAdapter(
              child: GtexClubValuationSection(),
            ),

            // 12. Platform Architecture & How GTEX Works (GTC/GTX, Ledgers)
            const SliverToBoxAdapter(
              child: GtexHowItWorksSection(),
            ),

            // 13. Trust, Regulatory Compliance & Fair-Play Architecture
            SliverToBoxAdapter(
              key: _trustKey,
              child: const GtexTrustAndIntegritySection(),
            ),

            // 14. Conversion Pathways & Editorial Footer
            SliverToBoxAdapter(
              child: GtexConversionAndFooterSection(
                onSignup: widget.onSignup,
                onTraderSignup: widget.onTraderSignup,
                onCreatorSignup: widget.onCreatorSignup,
                onExploreMarket: widget.onExploreMarket,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
