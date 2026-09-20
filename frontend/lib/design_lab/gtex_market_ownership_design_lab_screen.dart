import 'package:flutter/material.dart';

import '../ui_gtex/ui_gtex.dart';

/// Isolated visual exploration for GTEX Market & Ownership Command Surface.
///
/// The fixtures below are never read by production routes or live providers;
/// `/design-lab/market-ownership` is intentionally unlinked from production shell
/// navigation and exists for design review, visual regression capture, and
/// component hierarchy verification.
class GtexMarketOwnershipDesignLabScreen extends StatefulWidget {
  const GtexMarketOwnershipDesignLabScreen({super.key, this.initialDirection});

  final String? initialDirection;

  @override
  State<GtexMarketOwnershipDesignLabScreen> createState() =>
      _GtexMarketOwnershipDesignLabScreenState();
}

class _GtexMarketOwnershipDesignLabScreenState
    extends State<GtexMarketOwnershipDesignLabScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs = TabController(
    length: 3,
    vsync: this,
    initialIndex: _initialDirectionIndex(),
  );

  int _initialDirectionIndex() {
    final Uri baseUri = Uri.base;
    final String fragment = baseUri.fragment;
    final int fragmentQueryStart = fragment.indexOf('?');
    final String? requestedDirection =
        widget.initialDirection ??
        baseUri.queryParameters['direction'] ??
        (fragmentQueryStart < 0
            ? null
            : Uri.splitQueryString(
              fragment.substring(fragmentQueryStart + 1),
            )['direction']);
    switch (requestedDirection) {
      case 'ownership':
        return 1;
      case 'composite':
        return 2;
      case 'market':
      default:
        return 0;
    }
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: GtexColors.surfaceBase,
      appBar: AppBar(
        backgroundColor: GtexColors.surfaceBase,
        foregroundColor: GtexColors.textPrimary,
        title: const Text('GTEX Market + Ownership Design Lab'),
        bottom: TabBar(
          controller: _tabs,
          isScrollable: true,
          tabs: const <Widget>[
            Tab(text: 'A · Market Floor & Intelligence'),
            Tab(text: 'B · Squad Ownership & Identity'),
            Tab(text: 'C · Composite Command Desk (Selected)'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabs,
        children: const <Widget>[
          _DesignLabDirection(direction: _MarketDesignDirection.marketFirst),
          _DesignLabDirection(direction: _MarketDesignDirection.ownershipFirst),
          _DesignLabDirection(direction: _MarketDesignDirection.compositeDesk),
        ],
      ),
    );
  }
}

enum _MarketDesignDirection { marketFirst, ownershipFirst, compositeDesk }

class _DesignLabDirection extends StatelessWidget {
  const _DesignLabDirection({required this.direction});

  final _MarketDesignDirection direction;

  @override
  Widget build(BuildContext context) {
    final _LabDirectionData data = _LabDirectionData.forDirection(direction);
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 20, 16, 60),
      children: <Widget>[
        Semantics(
          label: 'Design Lab fixtures only',
          child: Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: GtexCommandTokens.pending.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
              border: Border.all(
                color: GtexCommandTokens.pending.withValues(alpha: 0.4),
              ),
            ),
            child: Text(
              'ISOLATED FIXTURE MODE · No live GTEX market data or wallet balances rendered here.',
              style: GtexText.labelSM.copyWith(
                color: GtexCommandTokens.pending,
              ),
            ),
          ),
        ),
        const SizedBox(height: 16),
        GtexCommandCenterMasthead(
          eyebrow: 'Direction ${data.letter} · ${data.name}',
          identity: data.identity,
          identityDetail: data.identityDetail,
          title: data.title,
          summary: data.summary,
          statusLabel: data.status,
          status: data.statusState,
          metrics: data.metrics,
          primaryAction: GtexCommandAction(
            label: data.primaryAction,
            icon: data.primaryIcon,
            onPressed: () {},
          ),
          secondaryAction: GtexCommandAction(
            label: 'Explore direction',
            icon: Icons.auto_awesome_outlined,
            onPressed: () {},
            secondary: true,
            accent: data.accent,
          ),
        ),
        const SizedBox(height: 20),
        _DirectionBoard(data: data),
      ],
    );
  }
}

class _DirectionBoard extends StatelessWidget {
  const _DirectionBoard({required this.data});

  final _LabDirectionData data;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool wide = constraints.maxWidth >= 920;
        final List<Widget> focus = data.focus
            .map(
              (_LabFocus item) => GtexCommandFocusTile(
                kicker: item.kicker,
                title: item.title,
                detail: item.detail,
                icon: item.icon,
                accent: item.accent,
                onTap: () {},
              ),
            )
            .toList(growable: false);
        final Widget story = _StorySurface(data: data);
        if (!wide) {
          return Column(
            children: <Widget>[
              story,
              const SizedBox(height: 12),
              ...focus.map(
                (Widget item) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: item,
                ),
              ),
            ],
          );
        }
        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Expanded(flex: 5, child: story),
            const SizedBox(width: 16),
            Expanded(
              flex: 4,
              child: Column(
                children: focus
                    .map(
                      (Widget item) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: item,
                      ),
                    )
                    .toList(growable: false),
              ),
            ),
          ],
        );
      },
    );
  }
}

class _StorySurface extends StatelessWidget {
  const _StorySurface({required this.data});

  final _LabDirectionData data;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(GtexSpacing.lg),
      decoration: BoxDecoration(
        color: GtexColors.surfaceRaised,
        borderRadius: BorderRadius.circular(GtexCommandTokens.panelRadius),
        border: Border.all(color: data.accent.withValues(alpha: 0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(data.storyIcon, color: data.accent, size: 24),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  data.storyKicker.toUpperCase(),
                  style: GtexText.labelSM.copyWith(color: data.accent),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: GtexCommandTokens.settled.withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  'FIXTURE',
                  style: GtexText.labelSM.copyWith(
                    color: GtexCommandTokens.settled,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          Text(
            data.storyTitle,
            style: GtexText.displayLG.copyWith(color: GtexColors.textPrimary),
          ),
          const SizedBox(height: 8),
          Text(
            data.storyDetail,
            style: GtexText.bodyMD.copyWith(color: GtexColors.textSecondary),
          ),
          const SizedBox(height: 20),
          _SpecimenPlayerCard(direction: data.direction),
        ],
      ),
    );
  }
}

class _SpecimenPlayerCard extends StatelessWidget {
  const _SpecimenPlayerCard({required this.direction});

  final _MarketDesignDirection direction;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: GtexColors.surfaceOverlay,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: GtexColors.surfaceBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'CANONICAL GTEX PLAYER CARD WITH TELEMETRY',
            style: GtexText.labelSM.copyWith(color: GtexCommandTokens.coin),
          ),
          const SizedBox(height: 12),
          const GtexPlayerCard(
            name: 'Victor Osimhen',
            position: 'ST',
            clubName: 'Galatasaray',
            nationality: 'NGA',
            priceLabel: 'GTC 142.5K',
            valuationLabel: 'Value EUR 75.0M',
            ratingLabel: 'OVR 88',
            gsiLabel: 'GSI 94',
            ageLabel: 'AGE 26',
            isOwned: true,
            ownershipLabel: '15 shares owned · Cost Avg GTC 120.0K',
            scale: GtexPlayerCardScale.compact,
          ),
        ],
      ),
    );
  }
}

class _LabFocus {
  const _LabFocus(this.kicker, this.title, this.detail, this.icon, this.accent);

  final String kicker;
  final String title;
  final String detail;
  final IconData icon;
  final Color accent;
}

class _LabDirectionData {
  const _LabDirectionData({
    required this.direction,
    required this.letter,
    required this.name,
    required this.identity,
    required this.identityDetail,
    required this.title,
    required this.summary,
    required this.status,
    required this.statusState,
    required this.primaryAction,
    required this.primaryIcon,
    required this.metrics,
    required this.storyKicker,
    required this.storyTitle,
    required this.storyDetail,
    required this.storyIcon,
    required this.accent,
    required this.focus,
  });

  final _MarketDesignDirection direction;
  final String letter;
  final String name;
  final String identity;
  final String identityDetail;
  final String title;
  final String summary;
  final String status;
  final GtexCommandStatus statusState;
  final String primaryAction;
  final IconData primaryIcon;
  final List<GtexCommandMetric> metrics;
  final String storyKicker;
  final String storyTitle;
  final String storyDetail;
  final IconData storyIcon;
  final Color accent;
  final List<_LabFocus> focus;

  factory _LabDirectionData.forDirection(_MarketDesignDirection direction) =>
      switch (direction) {
        _MarketDesignDirection.marketFirst => _LabDirectionData(
          direction: direction,
          letter: 'A',
          name: 'Market Floor & Intelligence',
          identity: 'Scout Desk',
          identityDetail: 'Real-time Player Share & Transfer Discovery',
          title: 'High-signal market discovery and price movement.',
          summary:
              'Focuses on live movers, price depth, transfer opportunities, and active bidding wars.',
          status: 'Market active',
          statusState: GtexCommandStatus.live,
          primaryAction: 'Scout Market',
          primaryIcon: Icons.radar_rounded,
          metrics: const <GtexCommandMetric>[
            GtexCommandMetric(
              label: 'Listings',
              value: '1,420',
              detail: 'Active on floor',
              accent: GtexCommandTokens.coin,
              icon: Icons.storefront_outlined,
            ),
            GtexCommandMetric(
              label: 'Top Mover',
              value: '+14.2%',
              detail: 'Osimhen 24h',
              accent: GtexCommandTokens.pitch,
              icon: Icons.trending_up_rounded,
            ),
            GtexCommandMetric(
              label: 'Bids Active',
              value: '18',
              detail: 'Pending response',
              accent: GtexCommandTokens.pending,
              icon: Icons.gavel_outlined,
            ),
            GtexCommandMetric(
              label: 'Watchlist',
              value: '24',
              detail: 'Shortlisted players',
              accent: GtexCommandTokens.prestige,
              icon: Icons.star_border_rounded,
            ),
          ],
          storyKicker: 'Market discovery',
          storyTitle: 'Live ticker and transfer opportunities lead.',
          storyDetail:
              'Gives high-frequency insight into market trends, price shifts, and liquidity.',
          storyIcon: Icons.insights_outlined,
          accent: GtexCommandTokens.coin,
          focus: const <_LabFocus>[
            _LabFocus(
              'Gainers',
              'Top movers today',
              'Player share prices reacting to matchday ratings.',
              Icons.trending_up_rounded,
              GtexCommandTokens.pitch,
            ),
            _LabFocus(
              'Watchlist',
              'Target shortlist',
              'Real backend watchlists tracking target contract updates.',
              Icons.star_rounded,
              GtexCommandTokens.prestige,
            ),
            _LabFocus(
              'Bids',
              'Open contract offers',
              'Transfer bids requiring decision before deadline.',
              Icons.gavel_outlined,
              GtexCommandTokens.pending,
            ),
          ],
        ),
        _MarketDesignDirection.ownershipFirst => _LabDirectionData(
          direction: direction,
          letter: 'B',
          name: 'Squad Ownership & Identity',
          identity: 'My Squad & Holdings',
          identityDetail: 'Lagos Comets · Owner & Scout Desk',
          title: 'Football identity, squad holdings, and prestige.',
          summary:
              'Organizes owned players into a squad view with matchday form, P&L, and club stakes.',
          status: 'Squad synced',
          statusState: GtexCommandStatus.active,
          primaryAction: 'Manage Squad',
          primaryIcon: Icons.groups_2_outlined,
          metrics: const <GtexCommandMetric>[
            GtexCommandMetric(
              label: 'Squad Size',
              value: '14',
              detail: 'Owned players',
              accent: GtexCommandTokens.ownership,
              icon: Icons.groups_outlined,
            ),
            GtexCommandMetric(
              label: 'Squad Value',
              value: 'GTC 480K',
              detail: 'Mark value',
              accent: GtexCommandTokens.coin,
              icon: Icons.account_balance_wallet_outlined,
            ),
            GtexCommandMetric(
              label: 'Unrealized P/L',
              value: '+GTC 62K',
              detail: '+14.8% return',
              accent: GtexCommandTokens.pitch,
              icon: Icons.auto_graph_rounded,
            ),
            GtexCommandMetric(
              label: 'Club Stakes',
              value: '2',
              detail: 'Equity holdings',
              accent: GtexCommandTokens.reward,
              icon: Icons.apartment_outlined,
            ),
          ],
          storyKicker: 'Football identity',
          storyTitle: 'Positions are owned players, not abstract ticker rows.',
          storyDetail:
              'Reinforces football identity with matchday context, club affiliations, and performance yield.',
          storyIcon: Icons.shield_outlined,
          accent: GtexCommandTokens.ownership,
          focus: const <_LabFocus>[
            _LabFocus(
              'Matchday',
              '3 owned players starting',
              'Match performance directly driving value snapshots.',
              Icons.sports_soccer_rounded,
              GtexCommandTokens.pitch,
            ),
            _LabFocus(
              'Equity',
              'Club dividend yield',
              'Quarterly distributions from club performance.',
              Icons.apartment_outlined,
              GtexCommandTokens.reward,
            ),
            _LabFocus(
              'P&L',
              'Realized vs Unrealized',
              'Clear distinction between holding gains and settled trades.',
              Icons.show_chart_rounded,
              GtexCommandTokens.coin,
            ),
          ],
        ),
        _MarketDesignDirection.compositeDesk => _LabDirectionData(
          direction: direction,
          letter: 'C',
          name: 'Composite Command Desk',
          identity: 'Market & Ownership Command',
          identityDetail: 'Dual-Mode Transfer Intelligence & Squad Desk',
          title: 'The complete GTEX football ownership command surface.',
          summary:
              'Combines Transfer Intelligence and Squad Ownership into a seamless tabbed command desk.',
          status: 'Command ready',
          statusState: GtexCommandStatus.live,
          primaryAction: 'Open Command Desk',
          primaryIcon: Icons.dashboard_outlined,
          metrics: const <GtexCommandMetric>[
            GtexCommandMetric(
              label: 'Market Mode',
              value: 'Intelligence',
              detail: 'Discovery & Bids',
              accent: GtexCommandTokens.coin,
              icon: Icons.radar_rounded,
            ),
            GtexCommandMetric(
              label: 'Ownership Mode',
              value: 'My Squad',
              detail: 'Holdings & Identity',
              accent: GtexCommandTokens.ownership,
              icon: Icons.groups_outlined,
            ),
            GtexCommandMetric(
              label: 'Watchlist',
              value: 'Live',
              detail: 'Real API wired',
              accent: GtexCommandTokens.prestige,
              icon: Icons.star_rounded,
            ),
            GtexCommandMetric(
              label: 'Responsive',
              value: 'Fluid',
              detail: '390 / 768 / 1440',
              accent: GtexCommandTokens.pitch,
              icon: Icons.devices_rounded,
            ),
          ],
          storyKicker: 'Selected production composition',
          storyTitle: 'Dual-Mode Market & Ownership Command Center.',
          storyDetail:
              'Preserves all backend contracts without flattening domains. Switches cleanly between Transfer Intelligence and Squad Ownership.',
          storyIcon: Icons.tune_rounded,
          accent: GtexCommandTokens.pitch,
          focus: const <_LabFocus>[
            _LabFocus(
              'Transfer Hub',
              'Mode 1: Intelligence',
              'Discovery, movers, depth, bids, watchlist, and opportunities.',
              Icons.storefront_outlined,
              GtexCommandTokens.coin,
            ),
            _LabFocus(
              'Squad Desk',
              'Mode 2: My Ownership',
              'Owned players, value, P&L, matchday relevance, and identity.',
              Icons.shield_outlined,
              GtexCommandTokens.ownership,
            ),
            _LabFocus(
              'Watchlist',
              'Backend Watchlist',
              'Real add/remove, state sync, error, and retry.',
              Icons.star_rounded,
              GtexCommandTokens.prestige,
            ),
          ],
        ),
      };
}
