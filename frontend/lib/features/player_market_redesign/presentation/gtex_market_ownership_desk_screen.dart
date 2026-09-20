import 'dart:async';

import 'package:flutter/material.dart';

import '../../../controllers/gtex_watchlist_controller.dart';
import '../../../data/gte_exchange_models.dart';
import '../../../data/player_card_watchlist_api.dart';
import '../../../domain/ownership/gtex_ownership_models.dart';
import '../../navigation/routing/gte_navigation_route.dart';
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
    this.watchlistController,
    this.onOpenTransferCalendar,
    this.onModeChanged,
  });

  final GteExchangeController controller;
  final ValueChanged<String> onOpenPlayer;
  final VoidCallback onOpenLogin;
  final GtexMarketDeskMode initialMode;
  final GtexWatchlistController? watchlistController;
  final VoidCallback? onOpenTransferCalendar;
  final ValueChanged<GtexMarketDeskMode>? onModeChanged;

  @override
  State<GtexMarketOwnershipDeskScreen> createState() =>
      _GtexMarketOwnershipDeskScreenState();
}

class _GtexMarketOwnershipDeskScreenState
    extends State<GtexMarketOwnershipDeskScreen> {
  late GtexMarketDeskMode _mode;
  late GtexWatchlistController _watchlistController;
  bool _ownsWatchlistController = false;

  @override
  void initState() {
    super.initState();
    _mode = widget.initialMode;
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

        if (_mode == GtexMarketDeskMode.market) {
          return GtexPlayerMarketRedesignScreen(
            controller: widget.controller,
            watchlistController: _watchlistController,
            activeMode: _mode,
            squadCount: squadCount,
            watchlistCount: watchlistCount,
            onSelectMode: _switchMode,
            onOpenPlayer: widget.onOpenPlayer,
            onOpenLogin: widget.onOpenLogin,
            onOpenTransferCalendar: widget.onOpenTransferCalendar,
          );
        }

        return Scaffold(
          backgroundColor: GtexColors.surfaceBase,
          body: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Column(
              children: <Widget>[
                Padding(
                  padding: const EdgeInsets.fromLTRB(0, 12, 0, 8),
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
                    ],
                  ),
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

class ModeChipButton extends StatelessWidget {
  const ModeChipButton({
    super.key,
    required this.label,
    required this.icon,
    required this.accent,
    required this.isActive,
    required this.onPressed,
    this.badge,
  });

  final String label;
  final IconData icon;
  final Color accent;
  final bool isActive;
  final VoidCallback onPressed;
  final String? badge;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(GtexSpacing.radiusPill),
        onTap: onPressed,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 140),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: isActive
                ? accent.withValues(alpha: 0.16)
                : GtexColors.surfaceOverlay,
            borderRadius: BorderRadius.circular(GtexSpacing.radiusPill),
            border: Border.all(
              color: isActive ? accent : GtexColors.surfaceBorder,
              width: isActive ? 1.5 : 1,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Icon(
                icon,
                size: 15,
                color: isActive ? accent : GtexColors.textMuted,
              ),
              const SizedBox(width: 5),
              Text(
                label,
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: isActive ? GtexColors.textPrimary : GtexColors.textMuted,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0.5,
                      fontSize: 11,
                    ),
              ),
              if (badge != null) ...<Widget>[
                const SizedBox(width: 5),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                  decoration: BoxDecoration(
                    color: isActive
                        ? accent.withValues(alpha: 0.28)
                        : GtexColors.surfaceBase,
                    borderRadius:
                        BorderRadius.circular(GtexSpacing.radiusPill),
                  ),
                  child: Text(
                    badge!,
                    style: TextStyle(
                      color: isActive ? accent : GtexColors.textMuted,
                      fontSize: 9,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
