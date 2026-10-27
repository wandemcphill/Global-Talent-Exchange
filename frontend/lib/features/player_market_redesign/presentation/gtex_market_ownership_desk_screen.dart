import 'dart:async';

import 'package:flutter/material.dart';

import '../../../controllers/gtex_watchlist_controller.dart';
import '../../../data/gte_exchange_models.dart';
import '../../../data/player_card_watchlist_api.dart';
import '../../../domain/ownership/gtex_ownership_models.dart';
import '../../navigation/routing/gte_navigation_route.dart';
import '../../player_card_marketplace/presentation/player_card_marketplace_screen.dart';
import '../../../providers/gte_exchange_controller.dart';
import '../../../screens/wallet/gtex_ownership_experience.dart';
import '../../../ui_gtex/ui_gtex.dart';
import '../models/gtex_market_browse_models.dart';
import '../widgets/gtex_market_mode_chip.dart';
import 'gtex_player_market_redesign_screen.dart';

class GtexMarketOwnershipDeskScreen extends StatefulWidget {
  const GtexMarketOwnershipDeskScreen({
    super.key,
    required this.controller,
    required this.onOpenPlayer,
    required this.onOpenLogin,
    this.initialMode = GtexMarketDeskMode.market,
    this.initialSubTab = GtexMarketSubTab.playerShares,
    this.watchlistController,
    this.onOpenTransferCalendar,
    this.onModeChanged,
    this.onOpenWallet,
    this.onQuickTradeConfirmed,
  });

  final GteExchangeController controller;
  final ValueChanged<String> onOpenPlayer;
  final VoidCallback onOpenLogin;
  final GtexMarketDeskMode initialMode;
  final GtexMarketSubTab initialSubTab;
  final GtexWatchlistController? watchlistController;
  final VoidCallback? onOpenTransferCalendar;
  final ValueChanged<GtexMarketDeskMode>? onModeChanged;
  final VoidCallback? onOpenWallet;
  final void Function(GtexMarketPlayerView player, String idempotencyKey)?
  onQuickTradeConfirmed;

  @override
  State<GtexMarketOwnershipDeskScreen> createState() =>
      _GtexMarketOwnershipDeskScreenState();
}

class _GtexMarketOwnershipDeskScreenState
    extends State<GtexMarketOwnershipDeskScreen> {
  late GtexMarketDeskMode _mode;
  late GtexMarketSubTab _subTab;
  late GtexWatchlistController _watchlistController;
  bool _ownsWatchlistController = false;

  @override
  void initState() {
    super.initState();
    _mode = widget.initialMode;
    _subTab = widget.initialSubTab;
    if (widget.watchlistController != null) {
      _watchlistController = widget.watchlistController!;
    } else {
      _watchlistController = GtexWatchlistController(
        api: PlayerCardWatchlistApi.standard(
          baseUrl: widget.controller.api.config.baseUrl,
          accessToken: widget.controller.accessToken,
          mode: widget.controller.api.config.mode,
        ),
      );
      _ownsWatchlistController = true;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (widget.controller.isAuthenticated) {
        _watchlistController.load();
      }
    });
  }

  @override
  void didUpdateWidget(covariant GtexMarketOwnershipDeskScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.initialMode != oldWidget.initialMode &&
        widget.initialMode != _mode) {
      setState(() => _mode = widget.initialMode);
    }
    if (widget.controller.accessToken != oldWidget.controller.accessToken) {
      if (_ownsWatchlistController) {
        _watchlistController.dispose();
        _watchlistController = GtexWatchlistController(
          api: PlayerCardWatchlistApi.standard(
            baseUrl: widget.controller.api.config.baseUrl,
            accessToken: widget.controller.accessToken,
            mode: widget.controller.api.config.mode,
          ),
        );
      }
      if (widget.controller.isAuthenticated) {
        _watchlistController.load(force: true);
      }
    }
  }

  @override
  void dispose() {
    if (_ownsWatchlistController) {
      _watchlistController.dispose();
    }
    super.dispose();
  }

  void _switchMode(GtexMarketDeskMode newMode) {
    if (newMode == _mode) {
      return;
    }
    setState(() => _mode = newMode);
    widget.onModeChanged?.call(newMode);
  }

  void _switchSubTab(GtexMarketSubTab newTab) {
    setState(() {
      _mode = GtexMarketDeskMode.market;
      _subTab = newTab;
    });
  }

  Widget _buildTopModeStrip({
    required int watchlistCount,
    required int squadCount,
  }) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: <Widget>[
            ModeChipButton(
              label: 'TRANSFER INTELLIGENCE',
              icon: Icons.radar_rounded,
              badge: watchlistCount > 0 ? '$watchlistCount watched' : null,
              accent: GtexColors.cyan,
              isActive: _mode == GtexMarketDeskMode.market,
              onPressed: () => _switchMode(GtexMarketDeskMode.market),
            ),
            const SizedBox(width: 8),
            ModeChipButton(
              label: 'MY OWNERSHIP',
              icon: Icons.groups_2_outlined,
              badge: squadCount > 0 ? '$squadCount owned' : '0 owned',
              accent: GtexColors.pitch,
              isActive: _mode == GtexMarketDeskMode.ownership,
              onPressed: () => _switchMode(GtexMarketDeskMode.ownership),
            ),
            const SizedBox(width: 12),
            for (final GtexMarketSubTab tab
                in GtexMarketSubTab.values) ...<Widget>[
              ChoiceChip(
                key: Key('gtex-market-subtab-${tab.name}'),
                avatar: Icon(
                  tab.icon,
                  size: 15,
                  color:
                      _mode == GtexMarketDeskMode.market && _subTab == tab
                          ? GtexColors.gold
                          : GtexColors.textMuted,
                ),
                label: Text(tab.label),
                selected: _mode == GtexMarketDeskMode.market && _subTab == tab,
                onSelected: (_) => _switchSubTab(tab),
              ),
              const SizedBox(width: 6),
            ],
            Container(
              key: const Key('gtex-market-financial-banner'),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: GtexColors.surfaceRaised,
                borderRadius: BorderRadius.circular(GtexSpacing.radiusSm),
                border: Border.all(
                  color: GtexColors.gold.withValues(alpha: 0.45),
                ),
              ),
              child: const Text(
                'Financial market — not sporting transfers',
                style: TextStyle(
                  color: GtexColors.gold,
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
            if (widget.onOpenWallet != null) ...<Widget>[
              const SizedBox(width: 8),
              TextButton.icon(
                key: const Key('gtex-market-open-wallet-btn'),
                onPressed: widget.onOpenWallet,
                icon: const Icon(
                  Icons.account_balance_wallet_outlined,
                  size: 16,
                ),
                label: const Text('Wallet'),
              ),
            ],
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: Listenable.merge(<Listenable>[
        widget.controller,
        _watchlistController,
      ]),
      builder: (BuildContext context, Widget? child) {
        final GtexOwnershipBook book = GtexOwnershipBook.fromPortfolio(
          widget.controller.portfolio,
        );
        final int squadCount = book.length;
        final int watchlistCount =
            _watchlistController.watchlistedPlayerIds.length;

        if (_mode == GtexMarketDeskMode.market &&
            _subTab == GtexMarketSubTab.playerShares) {
          return GtexPlayerMarketRedesignScreen(
            controller: widget.controller,
            watchlistController: _watchlistController,
            activeMode: _mode,
            squadCount: squadCount,
            watchlistCount: watchlistCount,
            onSelectMode: _switchMode,
            selectedSubTab: _subTab,
            onSelectSubTab: _switchSubTab,
            onOpenWallet: widget.onOpenWallet,
            onQuickTradeConfirmed: widget.onQuickTradeConfirmed,
            onOpenPlayer: widget.onOpenPlayer,
            onOpenLogin: widget.onOpenLogin,
            onOpenTransferCalendar: widget.onOpenTransferCalendar,
          );
        }

        if (_mode == GtexMarketDeskMode.market &&
            _subTab == GtexMarketSubTab.cards) {
          return Scaffold(
            backgroundColor: GtexColors.surfaceBase,
            body: Column(
              children: <Widget>[
                _buildTopModeStrip(
                  watchlistCount: watchlistCount,
                  squadCount: squadCount,
                ),
                Expanded(
                  child: KeyedSubtree(
                    key: const Key('gtex-market-cards-view'),
                    child: PlayerCardMarketplaceScreen(
                      baseUrl: widget.controller.api.config.baseUrl,
                      backendMode: widget.controller.api.config.mode,
                      accessToken: widget.controller.accessToken,
                      currentUserId: widget.controller.session?.user.id,
                      onOpenLogin: widget.onOpenLogin,
                      onOpenPlayer: widget.onOpenPlayer,
                    ),
                  ),
                ),
              ],
            ),
          );
        }

        if (_mode == GtexMarketDeskMode.market &&
            _subTab == GtexMarketSubTab.creators) {
          return Scaffold(
            backgroundColor: GtexColors.surfaceBase,
            body: Column(
              children: <Widget>[
                _buildTopModeStrip(
                  watchlistCount: watchlistCount,
                  squadCount: squadCount,
                ),
                Expanded(
                  child: _MarketCreatorsSubTabView(
                    isAuthenticated: widget.controller.isAuthenticated,
                    onOpenLogin: widget.onOpenLogin,
                    onOpenWallet: widget.onOpenWallet,
                  ),
                ),
              ],
            ),
          );
        }

        return Scaffold(
          backgroundColor: GtexColors.surfaceBase,
          body: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Column(
              children: <Widget>[
                _buildTopModeStrip(
                  watchlistCount: watchlistCount,
                  squadCount: squadCount,
                ),
                Expanded(
                  child: GtexOwnershipExperience(
                    book: book,
                    summary: widget.controller.portfolioSummary,
                    walletSummary: widget.controller.walletSummary,
                    ownerName: widget.controller.session?.user.username,
                    identityLookup: (String playerId) {
                      for (final GteMarketPlayerListItem p
                          in widget.controller.players) {
                        if (p.playerId == playerId) {
                          return p;
                        }
                      }
                      return null;
                    },
                    onOpenPlayer: widget.onOpenPlayer,
                    onRetry: () => widget.controller.refreshAccount(),
                    onBrowseMarket: () => _switchMode(GtexMarketDeskMode.market),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _MarketCreatorsSubTabView extends StatelessWidget {
  const _MarketCreatorsSubTabView({
    required this.isAuthenticated,
    required this.onOpenLogin,
    this.onOpenWallet,
  });

  final bool isAuthenticated;
  final VoidCallback onOpenLogin;
  final VoidCallback? onOpenWallet;

  @override
  Widget build(BuildContext context) {
    return ListView(
      key: const Key('gtex-market-creators-view'),
      padding: const EdgeInsets.all(GtexSpacing.lg),
      children: <Widget>[
        GtexPanel(
          title: 'Creator Share Market',
          subtitle:
              'Financial market for verified football creators & media studios (GTC / FNC — separate from club sporting transfers).',
          accent: GtexColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Text(
                'Creator shares trade on the Main Ledger (GTC) and settle into your Wallet holdings. Select a creator circuit or open your Wallet to review creator equity.',
                style: TextStyle(color: GtexColors.textMuted),
              ),
              const SizedBox(height: GtexSpacing.md),
              Wrap(
                spacing: GtexSpacing.sm,
                runSpacing: GtexSpacing.sm,
                children: <Widget>[
                  if (!isAuthenticated)
                    GtexActionButton(
                      label: 'Sign in to trade creator shares',
                      icon: Icons.login,
                      accent: GtexColors.gold,
                      onPressed: onOpenLogin,
                    ),
                  if (onOpenWallet != null)
                    GtexActionButton(
                      label: 'Open Wallet & Holdings',
                      icon: Icons.account_balance_wallet_outlined,
                      accent: GtexColors.cyan,
                      secondary: true,
                      onPressed: onOpenWallet,
                    ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }
}
