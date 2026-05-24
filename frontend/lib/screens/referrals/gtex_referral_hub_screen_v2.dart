import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../features/creator_social_redesign/models/gtex_creator_social_models.dart';
import '../../features/creator_social_redesign/presentation/gtex_creator_social_controller.dart';
import '../../features/creator_social_redesign/widgets/gtex_creator_social_visuals.dart';

class GtexReferralHubScreenV2 extends StatefulWidget {
  const GtexReferralHubScreenV2({
    super.key,
    this.snapshot,
    this.allowFixtureData = false,
  });

  final GtexCreatorSocialSnapshot? snapshot;
  final bool allowFixtureData;

  @override
  State<GtexReferralHubScreenV2> createState() =>
      _GtexReferralHubScreenV2State();
}

class _GtexReferralHubScreenV2State extends State<GtexReferralHubScreenV2> {
  late final GtexCreatorSocialController controller;

  @override
  void initState() {
    super.initState();
    controller = GtexCreatorSocialController(
      snapshot: widget.snapshot,
      allowFixtureData: widget.allowFixtureData,
    );
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        if (!controller.hasLiveSnapshot) {
          return const Scaffold(
            backgroundColor: gtexCreatorBg,
            body: SafeArea(child: _ReferralBlockedState()),
          );
        }
        final referral = controller.snapshot.referral;
        return Scaffold(
          backgroundColor: gtexCreatorBg,
          body: SafeArea(
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 900),
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Container(
                        height: 96,
                        width: 96,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: const LinearGradient(
                            colors: [gtexCreatorGreen, gtexCreatorGold],
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: gtexCreatorGreen.withOpacity(.22),
                              blurRadius: 42,
                            ),
                          ],
                        ),
                        child: const Icon(
                          Icons.group_add_rounded,
                          color: Colors.black,
                          size: 46,
                        ),
                      ),
                      const SizedBox(height: 20),
                      const Text(
                        'Invite managers into GTEX',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 34,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Share your referral code, grow the football economy, and earn rewards when new users complete onboarding and KYC.',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: gtexCreatorTextSoft),
                      ),
                      const SizedBox(height: 22),
                      GtexPanel(
                        child: Column(
                          children: [
                            const Text(
                              'Your referral code',
                              style: TextStyle(
                                color: gtexCreatorTextSoft,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(height: 10),
                            SelectableText(
                              referral.code,
                              style: const TextStyle(
                                color: gtexCreatorGreen,
                                fontSize: 28,
                                fontWeight: FontWeight.w900,
                                letterSpacing: 2,
                              ),
                            ),
                            const SizedBox(height: 18),
                            Wrap(
                              alignment: WrapAlignment.center,
                              spacing: 12,
                              runSpacing: 12,
                              children: [
                                _ReferralStat(
                                  label: 'Invites',
                                  value: referral.invitesLabel,
                                ),
                                _ReferralStat(
                                  label: 'Rewards',
                                  value: referral.rewardsLabel,
                                ),
                                _ReferralStat(
                                  label: 'Pending',
                                  value: referral.pendingLabel,
                                ),
                              ],
                            ),
                            const SizedBox(height: 18),
                            FilledButton.icon(
                              onPressed: () async {
                                await Clipboard.setData(
                                  ClipboardData(text: referral.code),
                                );
                                if (!context.mounted) return;
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                    content: Text('Referral code copied.'),
                                  ),
                                );
                              },
                              icon: const Icon(Icons.ios_share_rounded),
                              label: const Text('Share code'),
                              style: FilledButton.styleFrom(
                                backgroundColor: gtexCreatorGreen,
                                foregroundColor: Colors.black,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

class _ReferralBlockedState extends StatelessWidget {
  const _ReferralBlockedState();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Padding(
        padding: EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.group_add_rounded, color: gtexCreatorGreen, size: 44),
            SizedBox(height: 14),
            Text(
              'Live referral data unavailable',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white,
                fontSize: 24,
                fontWeight: FontWeight.w900,
              ),
            ),
            SizedBox(height: 8),
            Text(
              'Referral codes and reward totals must come from the live creator/referral backend.',
              textAlign: TextAlign.center,
              style: TextStyle(color: gtexCreatorTextSoft),
            ),
          ],
        ),
      ),
    );
  }
}

class _ReferralStat extends StatelessWidget {
  const _ReferralStat({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 190,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF101B2C),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        children: [
          Text(label, style: const TextStyle(color: gtexCreatorTextSoft)),
          const SizedBox(height: 6),
          Text(
            value,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}
