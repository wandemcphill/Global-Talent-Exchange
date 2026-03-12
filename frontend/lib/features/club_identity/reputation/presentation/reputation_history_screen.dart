import 'package:flutter/material.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

import '../data/reputation_models.dart';
import '../widgets/reputation_loading_skeleton.dart';
import '../widgets/reputation_timeline_list.dart';
import 'reputation_controller.dart';

class ReputationHistoryScreen extends StatelessWidget {
  const ReputationHistoryScreen({
    super.key,
    required this.controller,
  });

  final ReputationController controller;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Reputation history'),
        ),
        body: AnimatedBuilder(
          animation: controller,
          builder: (BuildContext context, Widget? child) {
            if (controller.isLoading && !controller.hasData) {
              return ListView(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                children: const <Widget>[
                  ReputationLoadingSkeleton(lines: 4, emphasized: true),
                  SizedBox(height: 18),
                  ReputationLoadingSkeleton(lines: 5),
                ],
              );
            }
            if (controller.errorMessage != null && !controller.hasData) {
              return Padding(
                padding: const EdgeInsets.all(20),
                child: GteStatePanel(
                  title: 'History unavailable',
                  message: controller.errorMessage!,
                  actionLabel: 'Retry',
                  onAction: controller.load,
                  icon: Icons.timeline,
                ),
              );
            }
            return RefreshIndicator(
              onRefresh: controller.refresh,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                children: <Widget>[
                  GteSurfacePanel(
                    emphasized: true,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          controller.displayClubName,
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Every reputation swing, filtered by where it came from.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 18),
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: ReputationHistoryFilter.values
                              .map(
                                (ReputationHistoryFilter filter) => ChoiceChip(
                                  label: Text(filter.label),
                                  selected: controller.historyFilter == filter,
                                  onSelected: (_) =>
                                      controller.setHistoryFilter(filter),
                                ),
                              )
                              .toList(growable: false),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  ReputationTimelineList(
                    events: controller.filteredEvents,
                    emptyTitle: 'No events in this filter',
                    emptyMessage:
                        'Try another lens to see how league runs, continental nights, and awards changed the club standing.',
                  ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }
}
