import 'package:flutter/material.dart';

import '../../data/gte_api_repository.dart';
import '../../data/gte_exchange_api_client.dart';
import '../../data/gte_exchange_models.dart';
import '../../data/gte_models.dart';
import '../../domain/value/gtex_value_models.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../ui_gtex/ui_gtex.dart';
import '../../widgets/gte_formatters.dart';
import '../../widgets/gte_order_ticket_sheet.dart';
import 'widgets/matchday_form_card.dart';
import 'widgets/ownership_consequence_card.dart';

// The profile draws from the shared GTEX tokens so it sits in the same
// visual language as the market surfaces that link into it.
const Color _bg = GtexColors.surfaceBase;
const Color _panel = GtexColors.surfaceRaised;
const Color _border = GtexColors.surfaceBorder;
const Color _text = GtexColors.textPrimary;
const Color _textSecondary = GtexColors.textSecondary;
const Color _textMuted = GtexColors.textTertiary;
const Color _green = GtexColors.accentPrimary;
const Color _amber = GtexColors.accentAmber;
const Color _orange = GtexColors.accentWarn;
const Color _red = GtexColors.accentRed;
const Color _blue = GtexColors.accentBlue;

const String _condensed = 'BarlowCondensed';

/// Football-Manager-style full player profile: identity + bio (height/foot/
/// positions) + the six colour-coded stats + GSI/OVR/POT + a market panel.
class GtexFmPlayerProfileScreen extends StatefulWidget {
  const GtexFmPlayerProfileScreen({
    super.key,
    required this.playerId,
    required this.baseUrl,
    this.backendMode = GteBackendMode.live,
    this.controller,
    this.onOpenLogin,
    this.apiClient,
  });

  final String playerId;
  final String baseUrl;
  final GteBackendMode backendMode;

  /// Supplied by the app shell so the profile can reach the live trading
  /// flow. Without it the profile stays read-only and says so.
  final GteExchangeController? controller;
  final VoidCallback? onOpenLogin;

  /// Overrides the client used to load the profile. Supplied by tests; the
  /// app leaves it null and gets the standard live client.
  final GteExchangeApiClient? apiClient;

  @override
  State<GtexFmPlayerProfileScreen> createState() =>
      _GtexFmPlayerProfileScreenState();
}

class _GtexFmPlayerProfileScreenState extends State<GtexFmPlayerProfileScreen> {
  late Future<GteMarketPlayerDetailView> _future;

  /// Null until the first form fetch settles, so the card can hold its place
  /// without claiming the player has no football.
  GtexPlayerForm? _form;

  /// The viewer's position in this player. Stays null when signed out, when the
  /// portfolio cannot be read, or when they simply hold none - the card renders
  /// all three as "no position" rather than inventing a holding.
  GtePortfolioHolding? _holding;
  bool _holdingLoaded = false;

  @override
  void initState() {
    super.initState();
    _future = _load();
    _loadTradingSnapshot();
    _loadForm();
    _loadHolding();
  }

  GteExchangeApiClient get _client =>
      widget.apiClient ??
      GteExchangeApiClient.standard(
        baseUrl: widget.baseUrl,
        mode: widget.backendMode,
      );

  Future<GteMarketPlayerDetailView> _load() {
    return _client.fetchPlayerDetail(widget.playerId);
  }

  /// Loaded separately from the profile, for the same reason the trading
  /// snapshot is: matchday form is a secondary read, and a failure fetching it
  /// must not blank out a player's profile. A failed load reports "no sample"
  /// rather than inventing form.
  Future<void> _loadForm() async {
    try {
      final GtexPlayerForm form = await _client.fetchPlayerForm(widget.playerId);
      if (mounted) {
        setState(() => _form = form);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _form = GtexPlayerForm.unknown(widget.playerId));
      }
    }
  }

  /// The viewer's own position, loaded independently of everything else.
  ///
  /// Requires authentication, so a failure here is an ordinary outcome for a
  /// signed-out reader and must be silent rather than an error state.
  Future<void> _loadHolding() async {
    try {
      final GtePortfolioView portfolio = await _client.fetchPortfolio();
      GtePortfolioHolding? match;
      for (final GtePortfolioHolding item in portfolio.holdings) {
        if (item.playerId == widget.playerId) {
          match = item;
          break;
        }
      }
      if (mounted) {
        setState(() {
          _holding = match;
          _holdingLoaded = true;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _holdingLoaded = true);
      }
    }
  }

  /// Loaded separately from the profile itself: the trading snapshot spans
  /// six endpoints, and a failure there must not blank out the profile.
  ///
  /// Deferred to after the frame because `openPlayer` notifies the shared
  /// exchange controller synchronously. Called straight from `initState` -
  /// which runs while the route that is pushing this screen is still being
  /// built - that notification marked the shell's AnimatedBuilder dirty
  /// mid-build and threw "setState() called during build" every time a
  /// player was opened.
  void _loadTradingSnapshot() {
    final GteExchangeController? controller = widget.controller;
    if (controller == null) {
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      controller.openPlayer(widget.playerId);
    });
  }

  /// The player's market listing, when the market list this session already
  /// loaded happens to contain it. Salary, buy clause, swap and loan terms
  /// live on the listing rather than on the player detail payload, and they
  /// used to be visible only in the market's side panel. Nothing is fetched
  /// for this: when the listing is not loaded the terms simply read as
  /// unavailable.
  GteMarketPlayerListItem? get _marketListing {
    final GteExchangeController? controller = widget.controller;
    if (controller == null) {
      return null;
    }
    for (final GteMarketPlayerListItem item in controller.players) {
      if (item.playerId == widget.playerId) {
        return item;
      }
    }
    return null;
  }

  GtePlayerMarketSnapshot? get _snapshot {
    final GteExchangeController? controller = widget.controller;
    if (controller?.selectedPlayer?.detail.playerId == widget.playerId) {
      return controller!.selectedPlayer;
    }
    return null;
  }

  Future<void> _openOrderTicket() async {
    final GteExchangeController? controller = widget.controller;
    final GtePlayerMarketSnapshot? snapshot = _snapshot;
    if (controller == null || snapshot == null) {
      return;
    }
    final GtePlayerShareTradeResult? trade =
        await showModalBottomSheet<GtePlayerShareTradeResult>(
      context: context,
      isScrollControlled: true,
      backgroundColor: GtexColors.panel,
      builder:
          (BuildContext context) =>
              GteOrderTicketSheet(controller: controller, snapshot: snapshot),
    );
    if (!mounted) {
      return;
    }
    if (trade == null) {
      // Either dismissed or rejected; the sheet surfaces its own error.
      return;
    }
    // Reports what the server actually settled, never an estimate.
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        backgroundColor: GtexColors.surfaceOverlay,
        content: Text(
          'Settled for ${snapshot.detail.identity.playerName}: '
          'you now own ${trade.holding.shareCount} '
          '${trade.holding.shareCount == 1 ? 'share' : 'shares'} '
          '(${gteFormatCredits(trade.netAmountCoin)} GTEX Coin).',
          style: const TextStyle(color: _text),
        ),
        action: SnackBarAction(
          label: 'Portfolio',
          onPressed: () => Navigator.of(context).maybePop(),
        ),
      ),
    );
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final GteExchangeController? controller = widget.controller;
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(
        backgroundColor: _bg,
        foregroundColor: _text,
        elevation: 0,
        title: const Text('Player profile'),
      ),
      body: FutureBuilder<GteMarketPlayerDetailView>(
        future: _future,
        builder: (
          BuildContext context,
          AsyncSnapshot<GteMarketPlayerDetailView> snap,
        ) {
          if (snap.connectionState != ConnectionState.done) {
            return const _ProfileSkeleton();
          }
          if (snap.hasError || snap.data == null) {
            return _ErrorState(
              onRetry: () {
                setState(() => _future = _load());
                _loadTradingSnapshot();
              },
            );
          }
          if (controller == null) {
            return _ProfileBody(
              detail: snap.data!,
              actions: null,
              form: _form,
              holding: _holding,
              holdingLoaded: _holdingLoaded,
            );
          }
          return AnimatedBuilder(
            animation: controller,
            builder: (BuildContext context, Widget? _) {
              return _ProfileBody(
                detail: snap.data!,
                form: _form,
                holding: _holding,
                holdingLoaded: _holdingLoaded,
                careerEntries: _snapshot?.careerEntries,
                orderBook: _snapshot?.orderBook,
                overview: _snapshot?.overview,
                listing: _marketListing,
                actions: _TradeActionBar(
                  detail: snap.data!,
                  controller: controller,
                  snapshotReady: _snapshot != null,
                  isLoading: controller.isLoadingPlayer,
                  loadError: controller.playerError,
                  onTrade: _openOrderTicket,
                  onRetry: _loadTradingSnapshot,
                  onOpenLogin: widget.onOpenLogin,
                ),
              );
            },
          );
        },
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          const Icon(Icons.refresh_rounded, color: _textMuted, size: 40),
          const SizedBox(height: 12),
          const Text(
            "We couldn't load this player",
            style: TextStyle(color: _text, fontSize: 16),
          ),
          const SizedBox(height: 12),
          OutlinedButton(onPressed: onRetry, child: const Text('Retry')),
        ],
      ),
    );
  }
}

/// Width at which the profile stops being one column. Below it the football
/// story and the asset case stack; above it they sit side by side, football
/// on the left because that is what the reader is here to understand first.
const double _twoColumnMinWidth = 1100;

class _ProfileBody extends StatelessWidget {
  const _ProfileBody({
    required this.detail,
    required this.actions,
    this.form,
    this.holding,
    this.holdingLoaded = false,
    this.careerEntries,
    this.orderBook,
    this.overview,
    this.listing,
  });

  final GteMarketPlayerDetailView detail;
  final Widget? actions;
  final GtexPlayerForm? form;
  final GtePortfolioHolding? holding;
  final bool holdingLoaded;
  final List<GteCareerEntry>? careerEntries;
  final GteOrderBook? orderBook;
  final GtePlayerOverview? overview;
  final GteMarketPlayerListItem? listing;

  @override
  Widget build(BuildContext context) {
    final GteMarketPlayerIdentity id = detail.identity;
    final GteMarketPlayerAttributes attr = detail.attributes;
    final List<GteCareerEntry> career =
        careerEntries ?? const <GteCareerEntry>[];
    final GteOrderBook? book = orderBook;
    final bool hasDepth =
        book != null && (book.bids.isNotEmpty || book.asks.isNotEmpty);

    // The football half: who this player is, what they can do, where they
    // are going.
    final List<Widget> footballColumn = <Widget>[
      _SectionLabel('FOOTBALL PROFILE'),
      const SizedBox(height: 8),
      _BioCard(identity: id),
      const SizedBox(height: 14),
      _SectionLabel('ATTRIBUTES'),
      const SizedBox(height: 8),
      _AttributesCard(attr: attr),
      const SizedBox(height: 14),
      _SectionLabel('TRAJECTORY'),
      const SizedBox(height: 8),
      _TrajectoryCard(trend: detail.trend, attr: attr),
      // Matchday form is the bridge between the football half of this page and
      // the asset half: it is the only block that states what the player's
      // actual performances are doing to his value. Drawn only once the form
      // fetch has settled, so an in-flight read never reads as "no football".
      if (form != null) ...<Widget>[
        const SizedBox(height: 14),
        _SectionLabel('MATCHDAY FORM'),
        const SizedBox(height: 8),
        MatchdayFormCard(form: form!),
      ],
      // Career is only drawn when the backend actually returned history.
      // Nothing here is synthesised.
      if (career.isNotEmpty) ...<Widget>[
        const SizedBox(height: 14),
        _SectionLabel('CAREER'),
        const SizedBox(height: 8),
        _CareerCard(entries: career),
      ],
    ];

    // The asset half: what the market makes of all that.
    final List<Widget> assetColumn = <Widget>[
      _SectionLabel('ASSET & MARKET INTELLIGENCE'),
      const SizedBox(height: 8),
      _MarketCard(detail: detail),
      // The reader's own stake, drawn only once the portfolio read has settled
      // so an in-flight fetch never reads as "you hold nothing".
      if (holdingLoaded) ...<Widget>[
        const SizedBox(height: 14),
        _SectionLabel('YOUR POSITION'),
        const SizedBox(height: 8),
        OwnershipConsequenceCard(holding: holding, form: form),
      ],
      const SizedBox(height: 14),
      _SectionLabel('TERMS'),
      const SizedBox(height: 8),
      _TermsCard(profile: detail.marketProfile),
      const SizedBox(height: 14),
      _SectionLabel('TRANSFER'),
      const SizedBox(height: 8),
      _TransferCard(overview: overview, listing: listing),
      // Depth is only drawn when the live book actually has levels, so an
      // empty book reads as empty rather than as a flat market.
      if (hasDepth) ...<Widget>[
        const SizedBox(height: 14),
        _SectionLabel('ORDER BOOK'),
        const SizedBox(height: 8),
        _OrderBookCard(book: book),
      ],
    ];

    return Column(
      children: <Widget>[
        Expanded(
          child: LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool twoColumn = constraints.maxWidth >= _twoColumnMinWidth;
              return SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 20),
                child: Center(
                  child: ConstrainedBox(
                    constraints: BoxConstraints(
                      maxWidth: twoColumn ? 1320 : 780,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: <Widget>[
                        _IdentityCard(
                          identity: id,
                          trend: detail.trend,
                          attr: attr,
                        ),
                        const SizedBox(height: 14),
                        if (twoColumn)
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Expanded(
                                flex: 3,
                                child: Column(
                                  crossAxisAlignment:
                                      CrossAxisAlignment.stretch,
                                  children: footballColumn,
                                ),
                              ),
                              const SizedBox(width: 18),
                              Expanded(
                                flex: 2,
                                child: Column(
                                  crossAxisAlignment:
                                      CrossAxisAlignment.stretch,
                                  children: assetColumn,
                                ),
                              ),
                            ],
                          )
                        else
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: <Widget>[
                              ...footballColumn,
                              const SizedBox(height: 14),
                              ...assetColumn,
                            ],
                          ),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ),
        // The trade action stays reachable without scrolling at every size,
        // but it is no longer the first thing the page says about a
        // footballer.
        if (actions != null)
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 780),
                child: actions!,
              ),
            ),
          ),
      ],
    );
  }
}

/// The primary actions for a player. Every state is explicit: the button is
/// only enabled when there is a live order flow behind it, and each disabled
/// state says why.
class _TradeActionBar extends StatelessWidget {
  const _TradeActionBar({
    required this.detail,
    required this.controller,
    required this.snapshotReady,
    required this.isLoading,
    required this.loadError,
    required this.onTrade,
    required this.onRetry,
    required this.onOpenLogin,
  });

  final GteMarketPlayerDetailView detail;
  final GteExchangeController controller;
  final bool snapshotReady;
  final bool isLoading;
  final String? loadError;
  final Future<void> Function() onTrade;
  final VoidCallback onRetry;
  final VoidCallback? onOpenLogin;

  @override
  Widget build(BuildContext context) {
    final bool tradable = detail.marketProfile.isTradable;

    if (!controller.isAuthenticated) {
      return _ActionShell(
        message: 'Sign in to trade ${detail.identity.playerName}.',
        button: GtexActionButton(
          label: 'Sign in to trade',
          icon: Icons.login_outlined,
          onPressed: onOpenLogin,
        ),
      );
    }
    if (!tradable) {
      return const _ActionShell(
        message: 'This player is not currently tradable on the GTEX exchange.',
        button: GtexActionButton(
          label: 'Trading unavailable',
          icon: Icons.lock_outline,
          onPressed: null,
        ),
      );
    }
    if (isLoading && !snapshotReady) {
      return const _ActionShell(
        message: 'Loading live order book and quotes...',
        button: GtexActionButton(
          label: 'Preparing order ticket',
          icon: Icons.hourglass_empty,
          onPressed: null,
        ),
      );
    }
    if (!snapshotReady) {
      return _ActionShell(
        message:
            loadError ?? 'Live market data for this player is unavailable.',
        isError: true,
        button: GtexActionButton(
          label: 'Retry market data',
          icon: Icons.refresh,
          onPressed: onRetry,
          secondary: true,
        ),
      );
    }
    return _ActionShell(
      message: 'Buy or sell this player against the live order book.',
      button: GtexActionButton(
        label: controller.isSubmittingOrder ? 'Submitting...' : 'Trade player',
        icon: Icons.swap_vert,
        onPressed: controller.isSubmittingOrder ? null : () => onTrade(),
      ),
    );
  }
}

class _ActionShell extends StatelessWidget {
  const _ActionShell({
    required this.message,
    required this.button,
    this.isError = false,
  });

  final String message;
  final Widget button;
  final bool isError;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: _panel,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isError ? _red : _green.withValues(alpha: 0.62),
          width: 1.5,
        ),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: (isError ? _red : _green).withValues(alpha: 0.12),
            blurRadius: 10,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          SizedBox(width: double.infinity, child: button),
          const SizedBox(height: 8),
          Text(
            message,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: isError ? _red : _textSecondary,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

/// Live market depth for the player, harvested from the exchange detail
/// screen so the order ticket on this page is not opened blind.
class _OrderBookCard extends StatelessWidget {
  const _OrderBookCard({required this.book});

  final GteOrderBook book;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: _panel,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _border),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Expanded(
            child: _OrderBookSide(
              title: 'BIDS',
              levels: book.bids,
              color: _green,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _OrderBookSide(
              title: 'ASKS',
              levels: book.asks,
              color: _red,
            ),
          ),
        ],
      ),
    );
  }
}

class _OrderBookSide extends StatelessWidget {
  const _OrderBookSide({
    required this.title,
    required this.levels,
    required this.color,
  });

  final String title;
  final List<GteOrderBookLevel> levels;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          title,
          style: TextStyle(
            color: color,
            fontFamily: _condensed,
            fontSize: 12,
            fontWeight: FontWeight.w800,
            letterSpacing: 1.2,
          ),
        ),
        const SizedBox(height: 6),
        if (levels.isEmpty)
          const Text(
            'None',
            style: TextStyle(color: _textMuted, fontSize: 12.5),
          )
        else
          for (final GteOrderBookLevel level in levels.take(5))
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Row(
                children: <Widget>[
                  Expanded(
                    child: Text(
                      level.price.toStringAsFixed(2),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: color,
                        fontSize: 12.5,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  Text(
                    level.quantity.toStringAsFixed(2),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: _textSecondary,
                      fontSize: 12.5,
                    ),
                  ),
                ],
              ),
            ),
      ],
    );
  }
}

class _CareerCard extends StatelessWidget {
  const _CareerCard({required this.entries});

  final List<GteCareerEntry> entries;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: _panel,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _border),
      ),
      child: Column(
        children: <Widget>[
          for (final GteCareerEntry entry in entries.take(8))
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  SizedBox(
                    width: 74,
                    child: Text(
                      entry.seasonLabel,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: _textMuted,
                        fontFamily: _condensed,
                        fontSize: 14,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                  Expanded(
                    child: Text(
                      entry.clubName,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: _text, fontSize: 13.5),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    '${entry.appearances} ap - ${entry.goals}g ${entry.assists}a',
                    style: const TextStyle(
                      color: _textSecondary,
                      fontSize: 12.5,
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _ProfileSkeleton extends StatelessWidget {
  const _ProfileSkeleton();

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'Loading player profile',
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 28),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 780),
            child: const Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                GtexSkeleton.box(height: 96),
                SizedBox(height: 14),
                GtexSkeleton.box(height: 64),
                SizedBox(height: 14),
                GtexSkeleton.box(height: 132),
                SizedBox(height: 14),
                GtexSkeleton.box(height: 108),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _IdentityCard extends StatelessWidget {
  const _IdentityCard({
    required this.identity,
    required this.trend,
    required this.attr,
  });

  final GteMarketPlayerIdentity identity;
  final GteMarketPlayerTrend trend;
  final GteMarketPlayerAttributes attr;

  @override
  Widget build(BuildContext context) {
    final String position =
        identity.normalizedPosition ?? identity.position ?? '\u2014';
    final String club = identity.currentClubName ?? '\u2014';
    final String age = identity.age > 0 ? '${identity.age}y' : '\u2014';
    final int gsi = trend.globalScoutingIndex.round().clamp(0, 99);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: _panel,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _border),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          GtexPlayerPortrait(
            name: identity.playerName,
            imageUrl: identity.imageUrl,
            position: identity.normalizedPosition ?? identity.position,
            nationalityCode: identity.nationalityCode,
            size: 84,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  identity.playerName,
                  style: const TextStyle(
                    fontFamily: _condensed,
                    color: _text,
                    fontSize: 24,
                    fontWeight: FontWeight.w800,
                    height: 1.05,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  '$club \u00b7 $age \u00b7 $position',
                  style: const TextStyle(color: _textSecondary, fontSize: 12.5),
                ),
                if ((identity.nationality ?? '').isNotEmpty) ...<Widget>[
                  const SizedBox(height: 2),
                  Text(
                    identity.nationality!,
                    style: const TextStyle(color: _blue, fontSize: 12),
                  ),
                ],
                if ((identity.currentCompetitionName ?? '')
                    .isNotEmpty) ...<Widget>[
                  const SizedBox(height: 2),
                  Text(
                    identity.currentCompetitionName!,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: _textMuted, fontSize: 12),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: 10),
          _RatingBox(label: 'GSI', value: gsi, color: _green),
          const SizedBox(width: 8),
          // A potential of zero is the API's "not scouted", not a verdict on
          // the player. It is rendered as unknown, never as a number.
          _RatingBox(
            label: 'POT',
            value: attr.potential > 0 ? attr.potential : null,
            color: _blue,
          ),
        ],
      ),
    );
  }
}

class _RatingBox extends StatelessWidget {
  const _RatingBox({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;

  /// Null means the backend has no figure for this player. Unknown is
  /// rendered as unknown - never converted into a zero.
  final int? value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: _bg,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.5)),
      ),
      child: Column(
        children: <Widget>[
          Text(
            value == null ? '\u2014' : '$value',
            style: TextStyle(
              color: value == null ? _textMuted : color,
              fontSize: 22,
              fontWeight: FontWeight.w800,
              height: 1,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: const TextStyle(
              color: _textMuted,
              fontSize: 10,
              letterSpacing: 0.5,
            ),
          ),
        ],
      ),
    );
  }
}

class _BioCard extends StatelessWidget {
  const _BioCard({required this.identity});

  final GteMarketPlayerIdentity identity;

  @override
  Widget build(BuildContext context) {
    final String primary =
        identity.normalizedPosition ?? identity.position ?? '—';
    final String height =
        identity.heightCm == null ? '—' : '${identity.heightCm} cm';
    final String foot = _foot(identity.preferredFoot);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: _panel,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Text(
            'POSITIONS',
            style: TextStyle(
              color: _textMuted,
              fontSize: 10,
              letterSpacing: 0.6,
            ),
          ),
          const SizedBox(height: 6),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: <Widget>[
              _PosChip(label: primary, natural: true),
              ...identity.secondaryPositions
                  .take(4)
                  .map((String p) => _PosChip(label: p, natural: false)),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: <Widget>[
              _BioStat(label: 'Height', value: height),
              _BioStat(label: 'Foot', value: foot),
              _BioStat(label: 'Age', value: '${identity.age}'),
            ],
          ),
        ],
      ),
    );
  }

  String _foot(String? foot) {
    final String? f = foot?.trim();
    if (f == null || f.isEmpty) {
      return '—';
    }
    return f[0].toUpperCase() + f.substring(1).toLowerCase();
  }
}

class _PosChip extends StatelessWidget {
  const _PosChip({required this.label, required this.natural});

  final String label;
  final bool natural;

  @override
  Widget build(BuildContext context) {
    final Color color = natural ? _green : _textSecondary;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(6),
        border: Border.all(
          color: natural ? color.withValues(alpha: 0.5) : _border,
        ),
      ),
      child: Text(
        label.toUpperCase(),
        style: TextStyle(
          color: color,
          fontFamily: _condensed,
          fontSize: 13,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.4,
        ),
      ),
    );
  }
}

class _BioStat extends StatelessWidget {
  const _BioStat({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            label.toUpperCase(),
            style: const TextStyle(
              color: _textMuted,
              fontSize: 10,
              letterSpacing: 0.5,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: const TextStyle(
              color: _text,
              fontSize: 14,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _AttributesCard extends StatelessWidget {
  const _AttributesCard({required this.attr});

  final GteMarketPlayerAttributes attr;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 6),
      decoration: BoxDecoration(
        color: _panel,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _border),
      ),
      child: Column(
        children: attr.sixStats
            .map(
              (MapEntry<String, int> stat) =>
                  _StatBar(label: stat.key, value: stat.value),
            )
            .toList(growable: false),
      ),
    );
  }
}

class _StatBar extends StatelessWidget {
  const _StatBar({required this.label, required this.value});

  final String label;
  final int value;

  /// Football attributes run 1-99. A zero is the API's default for an
  /// attribute it never received, so it is shown as unscouted rather than as
  /// a player who cannot do the thing.
  bool get _isKnown => value > 0;

  Color get _color {
    if (!_isKnown) return _textMuted;
    if (value >= 80) return _green;
    if (value >= 65) return _amber;
    if (value >= 50) return _orange;
    return _red;
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: <Widget>[
          SizedBox(
            width: 80,
            child: Text(
              label,
              style: const TextStyle(color: _textSecondary, fontSize: 13),
            ),
          ),
          SizedBox(
            width: 24,
            child: Text(
              _isKnown ? '$value' : '\u2014',
              style: TextStyle(
                color: _color,
                fontSize: 14,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(3),
              child: LinearProgressIndicator(
                value: _isKnown ? (value / 99).clamp(0.0, 1.0) : 0,
                minHeight: 6,
                backgroundColor: const Color(0xFF1E252E),
                valueColor: AlwaysStoppedAnimation<Color>(_color),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Where the player is heading, from the trend block the backend already
/// computes. Every row is omitted when its figure is absent - the card
/// never fills a gap with a zero.
class _TrajectoryCard extends StatelessWidget {
  const _TrajectoryCard({required this.trend, required this.attr});

  final GteMarketPlayerTrend trend;
  final GteMarketPlayerAttributes attr;

  @override
  Widget build(BuildContext context) {
    final int overall = attr.overall;
    final int potential = attr.potential;
    final int? headroom =
        overall > 0 && potential > 0 ? potential - overall : null;
    final List<GtexTermRow> rows = <GtexTermRow>[
      GtexTermRow(
        'GSI movement',
        _signedPct(trend.globalScoutingIndexMovementPct),
        valueColor: _directionColor(trend.globalScoutingIndexMovementPct),
      ),
      GtexTermRow(
        'Value trend 7d',
        _signedPct(trend.trend7dPct),
        valueColor: _directionColor(trend.trend7dPct),
      ),
      GtexTermRow(
        'Value trend 30d',
        _signedPct(trend.trend30dPct),
        valueColor: _directionColor(trend.trend30dPct),
      ),
      if (headroom == null)
        const GtexTermRow.unknown('Development headroom')
      else
        GtexTermRow(
          'Development headroom',
          '+$headroom to ceiling',
          valueColor: _blue,
        ),
      GtexTermRow.orUnknown('Scouting confidence', trend.confidenceTier),
    ];
    final List<String> tags =
        <String>[
          ...trend.movementTags,
          ...trend.drivers,
        ].where((String tag) => tag.trim().isNotEmpty).take(4).toList();

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: _panel,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          GtexTermsList(rows: rows),
          if (tags.isNotEmpty) ...<Widget>[
            const SizedBox(height: 10),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: <Widget>[
                for (final String tag in tags)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 3,
                    ),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: _border),
                    ),
                    child: Text(
                      tag,
                      style: const TextStyle(
                        color: _textSecondary,
                        fontSize: 11.5,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  static const String _unknown = '\u2014';

  String _signedPct(double? value) {
    if (value == null) {
      return _unknown;
    }
    final String prefix = value > 0 ? '+' : '';
    return '$prefix${value.toStringAsFixed(1)}%';
  }

  Color _directionColor(double? value) {
    if (value == null) {
      return _textMuted;
    }
    if (value > 0) {
      return _green;
    }
    if (value < 0) {
      return _red;
    }
    return _textSecondary;
  }
}

class _TermsCard extends StatelessWidget {
  const _TermsCard({required this.profile});

  final GteMarketPlayerMarketProfile profile;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: _panel,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _border),
      ),
      child: GtexTermsList(
        rows: <GtexTermRow>[
          GtexTermRow.orUnknown('Supply tier', profile.supplyTier),
          GtexTermRow.orUnknown('Liquidity band', profile.liquidityBand),
          GtexTermRow.orUnknown(
            'Top holder share',
            _pct(profile.topHolderSharePct),
            valueColor: _blue,
          ),
          GtexTermRow.orUnknown(
            'Top 3 holder share',
            _pct(profile.top3HolderSharePct),
            valueColor: _blue,
          ),
          GtexTermRow.orUnknown(
            'Trade trust score',
            profile.tradeTrustScore?.toStringAsFixed(1),
            valueColor: _green,
          ),
        ],
      ),
    );
  }

  String? _pct(double? value) =>
      value == null ? null : '${value.toStringAsFixed(1)}%';
}

/// The transfer story: contract, availability and the listing terms a club
/// would actually negotiate on. Contract and availability come from the
/// player's own overview; salary, buy clause, swap and loan terms come from
/// the market listing when this session has it loaded. These used to exist
/// only inside the market's side panel, so the canonical player screen was
/// missing half of what a buyer needs.
class _TransferCard extends StatelessWidget {
  const _TransferCard({required this.overview, required this.listing});

  final GtePlayerOverview? overview;
  final GteMarketPlayerListItem? listing;

  @override
  Widget build(BuildContext context) {
    final GteContractBadgeView? contract = overview?.contractBadge;
    final GteTransferStatusView? transfer = overview?.transferStatus;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: _panel,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          GtexTermsList(
            rows: <GtexTermRow>[
              GtexTermRow.orUnknown(
                'Availability',
                overview?.availabilityBadge.label,
              ),
              GtexTermRow.orUnknown('Contract', contract?.label),
              GtexTermRow.orUnknown('Contract club', contract?.clubName),
              if (transfer == null)
                const GtexTermRow.unknown('Transfer window')
              else
                GtexTermRow(
                  'Transfer window',
                  transfer.windowLabel ??
                      (transfer.windowOpen ? 'Open' : 'Closed'),
                  valueColor: transfer.windowOpen ? _green : _textSecondary,
                ),
              if (transfer != null && transfer.reason != null)
                GtexTermRow('Transfer note', transfer.reason!),
              GtexTermRow.orUnknown('Salary', _salary(listing)),
              GtexTermRow.orUnknown('Buy clause', _buyClause(listing)),
              GtexTermRow.orUnknown('Swap terms', _terms(listing?.swapTerms)),
              GtexTermRow.orUnknown('Loan terms', _terms(listing?.loanTerms)),
            ],
          ),
          if (listing == null) ...<Widget>[
            const SizedBox(height: 8),
            const Text(
              'Listing terms load with the transfer market. Open this player '
              'from the Transfer Hub to see the published terms.',
              style: TextStyle(color: _textMuted, fontSize: 11.5, height: 1.3),
            ),
          ],
        ],
      ),
    );
  }

  String? _salary(GteMarketPlayerListItem? item) {
    final double? amount = item?.salaryAmount;
    if (amount == null || amount <= 0) {
      return null;
    }
    return '${amount.toStringAsFixed(0)} GTC / wk';
  }

  String? _buyClause(GteMarketPlayerListItem? item) {
    final double? amount = item?.buyClauseAmount;
    if (amount == null || amount <= 0) {
      return null;
    }
    return '${amount.toStringAsFixed(0)} GTC';
  }

  String? _terms(Map<String, Object?>? terms) {
    if (terms == null || terms.isEmpty) {
      return null;
    }
    final Iterable<String> parts = terms.entries
        .where((MapEntry<String, Object?> entry) => entry.value != null)
        .take(2)
        .map(
          (MapEntry<String, Object?> entry) => '${entry.key}: ${entry.value}',
        );
    return parts.isEmpty ? null : parts.join(', ');
  }
}

class _MarketCard extends StatelessWidget {
  const _MarketCard({required this.detail});

  final GteMarketPlayerDetailView detail;

  @override
  Widget build(BuildContext context) {
    final GteMarketPlayerMarketProfile mp = detail.marketProfile;
    final String value = _value(mp);
    // A percentage move only means something against a price. On an
    // unpriced asset it asserted a price history that does not exist.
    final bool isPriced = value != _unpricedLabel;
    final double? movement = isPriced ? detail.value.movementPct : null;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: _panel,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Text(
            'VALUE',
            style: TextStyle(
              color: _textMuted,
              fontSize: 10,
              letterSpacing: 0.6,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: const TextStyle(
              color: _text,
              fontSize: 22,
              fontWeight: FontWeight.w800,
            ),
          ),
          if (movement != null) ...<Widget>[
            const SizedBox(height: 2),
            Text(
              '${movement >= 0 ? '+' : ''}${movement.toStringAsFixed(1)}% recent',
              style: TextStyle(
                color: movement >= 0 ? _green : _red,
                fontSize: 12,
              ),
            ),
          ],
          const SizedBox(height: 10),
          Row(
            children: <Widget>[
              _MarketStat(
                label: 'Tradable',
                value: mp.isTradable ? 'Yes' : 'No',
                color: mp.isTradable ? _green : _textMuted,
              ),
              _MarketStat(
                label: 'Holders',
                value: mp.holderCount == null ? '—' : '${mp.holderCount}',
                color: _blue,
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _value(GteMarketPlayerMarketProfile mp) {
    if (mp.marketValueEur != null && mp.marketValueEur! > 0) {
      return '€${_compact(mp.marketValueEur!)}';
    }
    final double? credits =
        mp.quotedMarketPriceCredits ?? mp.snapshotMarketPriceCredits;
    if (credits != null && credits > 0) {
      return '${_compact(credits)} GTC';
    }
    return _unpricedLabel;
  }

  static const String _unpricedLabel = 'Unpriced';

  String _compact(double v) {
    if (v >= 1000000) return '${(v / 1000000).toStringAsFixed(1)}M';
    if (v >= 1000) return '${(v / 1000).toStringAsFixed(1)}K';
    return v.toStringAsFixed(0);
  }
}

class _MarketStat extends StatelessWidget {
  const _MarketStat({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            label.toUpperCase(),
            style: const TextStyle(
              color: _textMuted,
              fontSize: 10,
              letterSpacing: 0.5,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: TextStyle(
              color: color,
              fontSize: 14,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.label);

  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        Flexible(
          child: Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              fontFamily: _condensed,
              color: _textMuted,
              fontSize: 13,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.5,
            ),
          ),
        ),
        const SizedBox(width: 10),
        const Expanded(child: Divider(color: _border, height: 1)),
      ],
    );
  }
}
