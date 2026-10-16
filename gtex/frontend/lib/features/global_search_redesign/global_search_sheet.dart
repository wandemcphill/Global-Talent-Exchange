import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import 'global_search_controller.dart';
import 'global_search_models.dart';

class GtexGlobalSearchSheet extends StatefulWidget {
  const GtexGlobalSearchSheet({
    super.key,
    required this.controller,
    required this.onOpenRoute,
  });

  final GtexGlobalSearchController controller;
  final ValueChanged<String> onOpenRoute;

  @override
  State<GtexGlobalSearchSheet> createState() => _GtexGlobalSearchSheetState();
}

class _GtexGlobalSearchSheetState extends State<GtexGlobalSearchSheet> {
  late final TextEditingController _textController;

  @override
  void initState() {
    super.initState();
    _textController = TextEditingController();
  }

  @override
  void dispose() {
    _textController.dispose();
    widget.controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: SizedBox(
        height: MediaQuery.sizeOf(context).height * 0.82,
        child: Padding(
          padding: const EdgeInsets.all(GtexSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  const Icon(
                    Icons.manage_search_outlined,
                    color: GtexColors.pitch,
                  ),
                  const SizedBox(width: GtexSpacing.sm),
                  Expanded(
                    child: Text(
                      'Global search',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: GtexColors.text,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ),
                  IconButton(
                    tooltip: 'Close search',
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close, color: GtexColors.text),
                  ),
                ],
              ),
              const SizedBox(height: GtexSpacing.md),
              GtexSearchField(
                controller: _textController,
                hintText:
                    'Search players, clubs, staff, sponsors, federations, clips',
                autofocus: true,
                onChanged: widget.controller.search,
                // Enter should not wait out the debounce window.
                onSubmitted: widget.controller.searchNow,
              ),
              const SizedBox(height: GtexSpacing.md),
              Expanded(
                child: AnimatedBuilder(
                  animation: widget.controller,
                  builder: (BuildContext context, Widget? child) {
                    if (widget.controller.loading &&
                        widget.controller.results.isEmpty) {
                      return const Center(child: CircularProgressIndicator());
                    }
                    if (widget.controller.error != null &&
                        widget.controller.results.isEmpty) {
                      return GtexEmptyState(
                        title: 'Search unavailable',
                        message: widget.controller.error!,
                        icon: Icons.search_off_outlined,
                        accent: GtexColors.red,
                        actionLabel: 'Retry search',
                        onAction: widget.controller.retry,
                      );
                    }
                    if (widget.controller.query.trim().length < 2) {
                      return const GtexEmptyState(
                        title: 'Start typing',
                        message:
                            'Search across GTEX players, clubs, federations, fan wars, predictions, broadcast rights, viral clips, transfers, coin traders, tickets, player cards, news, creators, staff and admin targets.',
                        icon: Icons.travel_explore_outlined,
                        accent: GtexColors.pitch,
                      );
                    }
                    if (widget.controller.results.isEmpty) {
                      return const GtexEmptyState(
                        title: 'No matches',
                        message:
                            'Try a player, club, email, federation, clip, prediction, competition, transfer, ticket, card, or market term.',
                        icon: Icons.search_off_outlined,
                        accent: GtexColors.cyan,
                      );
                    }
                    return ListView.separated(
                      itemCount: widget.controller.results.length,
                      separatorBuilder:
                          (_, __) => const SizedBox(height: GtexSpacing.sm),
                      itemBuilder: (BuildContext context, int index) {
                        final GtexGlobalSearchResult result =
                            widget.controller.results[index];
                        return _GlobalSearchResultTile(
                          result: result,
                          onTap: () {
                            Navigator.of(context).pop();
                            widget.onOpenRoute(result.route);
                          },
                        );
                      },
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _GlobalSearchResultTile extends StatelessWidget {
  const _GlobalSearchResultTile({required this.result, required this.onTap});

  final GtexGlobalSearchResult result;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final Color accent = result.adminOnly ? GtexColors.gold : GtexColors.pitch;
    return GtexPanel(
      accent: accent,
      onTap: onTap,
      child: Row(
        children: <Widget>[
          CircleAvatar(
            backgroundColor: accent.withValues(alpha: 0.14),
            child: Icon(_iconForType(result.type), color: accent),
          ),
          const SizedBox(width: GtexSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  result.title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                if (result.subtitle.trim().isNotEmpty)
                  Text(
                    result.subtitle,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: GtexColors.textMuted),
                  ),
              ],
            ),
          ),
          const SizedBox(width: GtexSpacing.sm),
          GtexStatusChip(
            label: gtexGlobalSearchTypeLabel(result.type),
            icon:
                result.adminOnly
                    ? Icons.admin_panel_settings_outlined
                    : Icons.open_in_new_outlined,
            tone:
                result.adminOnly
                    ? GtexStatusTone.warning
                    : GtexStatusTone.neutral,
          ),
        ],
      ),
    );
  }
}

IconData _iconForType(String type) {
  switch (type) {
    case 'player':
    case 'regen':
      return Icons.sports_soccer_outlined;
    case 'club':
      return Icons.shield_outlined;
    case 'competition':
      return Icons.emoji_events_outlined;
    case 'news':
      return Icons.newspaper_outlined;
    case 'creator':
      return Icons.campaign_outlined;
    case 'staff':
      return Icons.badge_outlined;
    case 'sponsor_package':
      return Icons.handshake_outlined;
    case 'federation':
      return Icons.public_outlined;
    case 'fan_prediction':
      return Icons.fact_check_outlined;
    case 'fan_war':
      return Icons.groups_2_outlined;
    case 'broadcast_auction':
    case 'broadcast_right':
      return Icons.live_tv_outlined;
    case 'viral_clip':
    case 'sponsored_clip':
      return Icons.play_circle_outline;
    case 'transfer_listing':
      return Icons.swap_horiz_outlined;
    case 'coin_trader':
      return Icons.currency_exchange_outlined;
    case 'ticket_event':
    case 'ticket_resale':
      return Icons.confirmation_number_outlined;
    case 'player_card_listing':
      return Icons.style_outlined;
    case 'admin_user':
    case 'admin_dispute':
    case 'admin_notification':
    case 'admin_coin_order':
    case 'admin_command_route':
      return Icons.admin_panel_settings_outlined;
    default:
      return Icons.manage_search_outlined;
  }
}
