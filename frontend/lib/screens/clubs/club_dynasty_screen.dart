import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/features/club_identity/dynasty/widgets/dynasty_status_banner.dart';
import 'package:gte_frontend/widgets/clubs/dynasty_milestone_card.dart';
import 'package:gte_frontend/widgets/clubs/dynasty_progress_timeline.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';

class ClubDynastyScreen extends StatelessWidget {
  const ClubDynastyScreen({
    super.key,
    required this.controller,
  });

  final ClubController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (BuildContext context, _) {
        final data = controller.data;
        return Container(
          decoration: gteBackdropDecoration(),
          child: Scaffold(
            backgroundColor: Colors.transparent,
            appBar: AppBar(
              title: const Text('Dynasty progression'),
            ),
            body: data == null
                ? Padding(
                    padding: const EdgeInsets.all(20),
                    child: GteStatePanel(
                      title: 'Dynasty progression unavailable',
                      message: controller.errorMessage ??
                          'Load the club profile before opening this screen.',
                      icon: Icons.timeline_outlined,
                    ),
                  )
                : RefreshIndicator(
                    onRefresh: controller.refresh,
                    child: ListView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                      children: <Widget>[
                        DynastyStatusBanner(profile: data.dynastyProfile),
                        const SizedBox(height: 18),
                        DynastyProgressTimeline(profile: data.dynastyProfile),
                        const SizedBox(height: 18),
                        Text(
                          'Legacy milestones',
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 14,
                          runSpacing: 14,
                          children: data.legacyMilestones.map((milestone) {
                            return SizedBox(
                              width: 280,
                              child: DynastyMilestoneCard(milestone: milestone),
                            );
                          }).toList(growable: false),
                        ),
                      ],
                    ),
                  ),
          ),
        );
      },
    );
  }
}
