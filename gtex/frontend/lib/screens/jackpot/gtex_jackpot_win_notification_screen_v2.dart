import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class GtexJackpotWinNotificationScreenV2 extends StatelessWidget {
  const GtexJackpotWinNotificationScreenV2({
    super.key,
    this.clubName = 'Lagos Phoenix FC',
    this.amountLabel = '₵8,400,000',
    this.roundLabel = 'Weekend GTEX Jackpot',
  });

  final String clubName;
  final String amountLabel;
  final String roundLabel;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF070B12),
      body: SafeArea(
        child: Center(
          child: Container(
            constraints: const BoxConstraints(maxWidth: 720),
            margin: const EdgeInsets.all(24),
            padding: const EdgeInsets.all(30),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [
                  Color(0xFF201428),
                  Color(0xFF0D241B),
                  Color(0xFF070B12),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(34),
              border: Border.all(
                color: const Color(0xFFFFD166).withOpacity(.4),
              ),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFFFFD166).withOpacity(.14),
                  blurRadius: 60,
                  offset: const Offset(0, 28),
                ),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 118,
                  height: 118,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: const Color(0xFFFFD166).withOpacity(.14),
                    border: Border.all(
                      color: const Color(0xFFFFD166).withOpacity(.5),
                    ),
                  ),
                  child: const Icon(
                    Icons.emoji_events_rounded,
                    color: Color(0xFFFFD166),
                    size: 62,
                  ),
                ),
                const SizedBox(height: 22),
                const Text(
                  'JACKPOT WON',
                  style: TextStyle(
                    color: Color(0xFFFFD166),
                    fontWeight: FontWeight.w900,
                    letterSpacing: 3,
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  amountLabel,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 48,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  '$clubName has won the $roundLabel.',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.white70,
                    fontSize: 18,
                    height: 1.35,
                  ),
                ),
                const SizedBox(height: 24),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    ElevatedButton.icon(
                      onPressed: () {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text(
                              'Open Wallet activity to review claim settlement and ledger proof.',
                            ),
                          ),
                        );
                      },
                      icon: const Icon(Icons.account_balance_wallet_rounded),
                      label: const Text('Review claim'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF2DFF87),
                        foregroundColor: const Color(0xFF06100B),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 22,
                          vertical: 16,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(18),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    OutlinedButton.icon(
                      onPressed: () async {
                        await Clipboard.setData(
                          ClipboardData(
                            text: '$clubName won $amountLabel in $roundLabel.',
                          ),
                        );
                        if (!context.mounted) return;
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Jackpot win copied.')),
                        );
                      },
                      icon: const Icon(Icons.ios_share_rounded),
                      label: const Text('Share win'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.white,
                        side: BorderSide(color: Colors.white.withOpacity(.2)),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 22,
                          vertical: 16,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(18),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
