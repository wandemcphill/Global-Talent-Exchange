import 'package:flutter/material.dart';

import '../../controllers/referral_controller.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/referrals/milestone_progress_card.dart';
import '../../widgets/referrals/referral_summary_card.dart';
import '../../widgets/referrals/reward_history_list.dart';

class ReferralRewardsScreen extends StatefulWidget {
  const ReferralRewardsScreen({
    super.key,
    required this.controller,
  });

  final ReferralController controller;

  @override
  State<ReferralRewardsScreen> createState() => _ReferralRewardsScreenState();
}

class _ReferralRewardsScreenState extends State<ReferralRewardsScreen> {
  @override
  void initState() {
    super.initState();
    widget.controller.load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Referral rewards')),
      body: AnimatedBuilder(
        animation: widget.controller,
        builder: (BuildContext context, _) {
          if (widget.controller.isLoading && !widget.controller.hasData) {
            return const Padding(
              padding: EdgeInsets.all(20),
              child: GteStatePanel(
                title: 'Loading referral rewards',
                message:
                    'Gathering milestone rewards, badge unlocks, and participation credits.',
                icon: Icons.workspace_premium_outlined,
              ),
            );
          }
          if (widget.controller.errorMessage != null &&
              !widget.controller.hasData) {
            return Padding(
              padding: const EdgeInsets.all(20),
              child: GteStatePanel(
                title: 'Referral rewards unavailable',
                message: widget.controller.errorMessage!,
                icon: Icons.error_outline,
              ),
            );
          }

          final hub = widget.controller.hub!;
          return SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                ReferralSummaryCard(
                  summary: hub.summary,
                  creatorHandle: hub.creatorHandle,
                ),
                const SizedBox(height: 16),
                MilestoneProgressCard(milestones: hub.milestones),
                const SizedBox(height: 16),
                RewardHistoryList(entries: hub.rewardHistory),
              ],
            ),
          );
        },
      ),
    );
  }
}
