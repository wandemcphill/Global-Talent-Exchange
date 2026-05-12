import 'package:flutter/material.dart';

import '../models/gtex_admin_command_models.dart';
import 'gtex_admin_visuals.dart';

class GtexAdminModuleList extends StatelessWidget {
  const GtexAdminModuleList({
    super.key,
    required this.modules,
    required this.selected,
    required this.onSelected,
    this.shrinkWrap = false,
    this.physics,
  });

  final List<GtexAdminModule> modules;
  final GtexAdminModuleType selected;
  final ValueChanged<GtexAdminModuleType> onSelected;
  final bool shrinkWrap;
  final ScrollPhysics? physics;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      shrinkWrap: shrinkWrap,
      physics: physics,
      itemCount: modules.length,
      separatorBuilder: (_, __) => const SizedBox(height: 8),
      itemBuilder: (context, index) {
        final module = modules[index];
        final isSelected = selected == module.type;
        final color = gtexAdminSeverityColor(module.severity);

        return InkWell(
          borderRadius: BorderRadius.circular(18),
          onTap: () => onSelected(module.type),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color:
                  isSelected
                      ? const Color(0xFF142A25)
                      : const Color(0xFF0E1624),
              borderRadius: BorderRadius.circular(18),
              border: Border.all(
                color:
                    isSelected
                        ? const Color(0xFF2DFF87).withOpacity(.55)
                        : Colors.white.withOpacity(.07),
              ),
            ),
            child: Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: color.withOpacity(.14),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Icon(_iconFor(module.type), color: color, size: 19),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        module.title,
                        style: const TextStyle(fontWeight: FontWeight.w900),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        module.description,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: Colors.white60,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                GtexAdminStatusPill(
                  label: module.countLabel,
                  severity: module.severity,
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  IconData _iconFor(GtexAdminModuleType type) {
    switch (type) {
      case GtexAdminModuleType.overview:
        return Icons.dashboard_rounded;
      case GtexAdminModuleType.users:
        return Icons.people_alt_rounded;
      case GtexAdminModuleType.clubs:
        return Icons.shield_rounded;
      case GtexAdminModuleType.players:
        return Icons.sports_soccer_rounded;
      case GtexAdminModuleType.regens:
        return Icons.auto_awesome_rounded;
      case GtexAdminModuleType.kyc:
        return Icons.verified_user_rounded;
      case GtexAdminModuleType.orders:
        return Icons.receipt_long_rounded;
      case GtexAdminModuleType.disputes:
        return Icons.gavel_rounded;
      case GtexAdminModuleType.tournaments:
        return Icons.emoji_events_rounded;
      case GtexAdminModuleType.jackpot:
        return Icons.stars_rounded;
      case GtexAdminModuleType.coinEconomy:
        return Icons.account_balance_wallet_rounded;
      case GtexAdminModuleType.transferHub:
        return Icons.swap_horiz_rounded;
      case GtexAdminModuleType.coinTraders:
        return Icons.currency_exchange_rounded;
      case GtexAdminModuleType.clubLifecycle:
        return Icons.flag_circle_rounded;
      case GtexAdminModuleType.staffMarketplace:
        return Icons.badge_rounded;
      case GtexAdminModuleType.academy:
        return Icons.school_rounded;
      case GtexAdminModuleType.sponsorships:
        return Icons.handshake_rounded;
      case GtexAdminModuleType.federations:
        return Icons.public_rounded;
      case GtexAdminModuleType.fanEconomy:
        return Icons.groups_2_rounded;
      case GtexAdminModuleType.broadcast:
        return Icons.live_tv_rounded;
      case GtexAdminModuleType.ticketing:
        return Icons.confirmation_number_rounded;
      case GtexAdminModuleType.playerCards:
        return Icons.style_rounded;
      case GtexAdminModuleType.globalSearch:
        return Icons.manage_search_rounded;
      case GtexAdminModuleType.operationsReadiness:
        return Icons.fact_check_rounded;
      case GtexAdminModuleType.creators:
        return Icons.video_camera_front_rounded;
      case GtexAdminModuleType.newsroom:
        return Icons.newspaper_rounded;
      case GtexAdminModuleType.moderation:
        return Icons.admin_panel_settings_rounded;
      case GtexAdminModuleType.launchControl:
        return Icons.tune_rounded;
      case GtexAdminModuleType.systemHealth:
        return Icons.monitor_heart_rounded;
    }
  }
}
