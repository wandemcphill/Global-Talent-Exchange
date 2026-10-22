import 'package:flutter/material.dart';

import '../../../data/match_gift_api.dart';
import '../../../ui_gtex/ui_gtex.dart';

/// Sender-side receipt presentation, shown only after the canonical API has
/// confirmed the gift transaction.
class GtexGiftDeliveryDialog extends StatelessWidget {
  const GtexGiftDeliveryDialog({
    super.key,
    required this.gift,
    required this.receipt,
  });

  final MatchGiftCatalogItem gift;
  final MatchGiftReceipt receipt;

  static Future<void> show(
    BuildContext context, {
    required MatchGiftCatalogItem gift,
    required MatchGiftReceipt receipt,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      barrierColor: Colors.black.withValues(alpha: 0.76),
      builder: (BuildContext context) =>
          GtexGiftDeliveryDialog(gift: gift, receipt: receipt),
    );
  }

  @override
  Widget build(BuildContext context) {
    final Color accent = _accent(gift.rarity);
    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.symmetric(horizontal: 22, vertical: 24),
      child: TweenAnimationBuilder<double>(
        tween: Tween<double>(begin: 0.82, end: 1),
        duration: const Duration(milliseconds: 420),
        curve: Curves.easeOutBack,
        builder: (BuildContext context, double scale, Widget? child) =>
            Transform.scale(scale: scale, child: child),
        child: Container(
          padding: const EdgeInsets.fromLTRB(22, 26, 22, 20),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: <Color>[
                Color(0xFF192942),
                Color(0xFF0B1321),
                Color(0xFF080E18),
              ],
            ),
            borderRadius: BorderRadius.circular(28),
            border: Border.all(color: accent.withValues(alpha: 0.8), width: 1.4),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: accent.withValues(alpha: 0.22),
                blurRadius: 38,
                spreadRadius: 1,
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              const Text(
                'GTEX GIFT DELIVERY',
                style: TextStyle(
                  color: Color(0xFFE8C979),
                  letterSpacing: 3,
                  fontSize: 10,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 18),
              Stack(
                alignment: Alignment.center,
                children: <Widget>[
                  TweenAnimationBuilder<double>(
                    tween: Tween<double>(begin: 0.65, end: 1),
                    duration: const Duration(milliseconds: 850),
                    curve: Curves.easeOutCubic,
                    builder: (BuildContext context, double value, Widget? child) =>
                        Transform.scale(scale: value, child: child),
                    child: Container(
                      width: 156,
                      height: 156,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: RadialGradient(
                          colors: <Color>[
                            accent.withValues(alpha: 0.24),
                            accent.withValues(alpha: 0.05),
                            Colors.transparent,
                          ],
                        ),
                        border: Border.all(color: accent.withValues(alpha: 0.32)),
                      ),
                    ),
                  ),
                  Container(
                    width: 108,
                    height: 108,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(34),
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: <Color>[
                          accent.withValues(alpha: 0.28),
                          const Color(0xFF17243A),
                        ],
                      ),
                      border: Border.all(color: accent, width: 1.6),
                      boxShadow: <BoxShadow>[
                        BoxShadow(color: accent.withValues(alpha: 0.15), blurRadius: 22),
                      ],
                    ),
                    child: Icon(_icon(gift.key), size: 58, color: accent),
                  ),
                  Positioned(
                    right: 8,
                    bottom: 8,
                    child: Container(
                      width: 36,
                      height: 36,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: const Color(0xFF0D1A2A),
                        border: Border.all(color: const Color(0xFF7DE0AD), width: 1.5),
                      ),
                      child: const Icon(Icons.check_rounded, color: Color(0xFF7DE0AD), size: 23),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              const Text(
                'GIFT SENT SUCCESSFULLY',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Color(0xFF7DE0AD),
                  letterSpacing: 1.7,
                  fontSize: 11,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 7),
              Text(
                receipt.giftDisplayName,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 7),
              Text(
                'Sent to ${receipt.recipientLabel}',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Color(0xFFB3C0D2), fontSize: 13),
              ),
              const SizedBox(height: 18),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: 0.18),
                  borderRadius: BorderRadius.circular(15),
                  border: Border.all(color: accent.withValues(alpha: 0.28)),
                ),
                child: Row(
                  children: <Widget>[
                    Icon(Icons.account_balance_wallet_outlined, color: accent, size: 20),
                    const SizedBox(width: 10),
                    const Expanded(
                      child: Text(
                        'Transaction total',
                        style: TextStyle(color: Color(0xFFB3C0D2), fontSize: 12),
                      ),
                    ),
                    Text(
                      '${receipt.grossAmount} ${receipt.currencyLabel}',
                      style: TextStyle(color: accent, fontWeight: FontWeight.w900, fontSize: 13),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'GTEX has confirmed the transaction. Your gift is now recorded in the gifting system.',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Color(0xFF8798AE), fontSize: 11, height: 1.45),
              ),
              const SizedBox(height: 20),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  key: const Key('gtex-gift-delivery-close'),
                  onPressed: () => Navigator.of(context).pop(),
                  style: FilledButton.styleFrom(
                    backgroundColor: accent,
                    foregroundColor: const Color(0xFF10131B),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  ),
                  child: const Text('Back to the match', style: TextStyle(fontWeight: FontWeight.w900)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  static Color _accent(String rarity) {
    switch (rarity.toLowerCase()) {
      case 'rare':
        return const Color(0xFF69C7FF);
      case 'epic':
        return const Color(0xFFC29BFF);
      case 'legendary':
        return const Color(0xFFFFC96B);
      case 'mythic':
        return const Color(0xFFFF8EAB);
      default:
        return GtexColors.gold;
    }
  }

  static IconData _icon(String key) {
    if (key.contains('whistle')) return Icons.sports;
    if (key.contains('chant')) return Icons.campaign_rounded;
    if (key.contains('goal') || key.contains('boot')) return Icons.sports_soccer_rounded;
    if (key.contains('legend') || key.contains('award') || key.contains('dor')) return Icons.workspace_premium_rounded;
    if (key.contains('tactic') || key.contains('midfield')) return Icons.auto_awesome_motion_rounded;
    if (key.contains('trainer') || key.contains('manager')) return Icons.sports_handball_rounded;
    if (key.contains('hands')) return Icons.back_hand_rounded;
    return Icons.card_giftcard_rounded;
  }
}
