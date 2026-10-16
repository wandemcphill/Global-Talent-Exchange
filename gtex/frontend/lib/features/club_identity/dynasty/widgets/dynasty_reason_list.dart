import 'package:flutter/material.dart';

import '../../../../widgets/gte_shell_theme.dart';
import '../../../../widgets/gte_state_panel.dart';
import '../../../../widgets/gte_surface_panel.dart';

class DynastyReasonList extends StatelessWidget {
  const DynastyReasonList({
    super.key,
    required this.title,
    required this.reasons,
    this.emptyTitle = 'No dynasty case yet',
    this.emptyMessage =
        'The club is building, but the detector needs a longer run of elite seasons.',
  });

  final String title;
  final List<String> reasons;
  final String emptyTitle;
  final String emptyMessage;

  @override
  Widget build(BuildContext context) {
    if (reasons.isEmpty) {
      return GteStatePanel(
        title: emptyTitle,
        message: emptyMessage,
        icon: Icons.auto_stories_outlined,
      );
    }

    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 14),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: reasons
                .map(
                  (String reason) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Container(
                          width: 10,
                          height: 10,
                          margin: const EdgeInsets.only(top: 5),
                          decoration: const BoxDecoration(
                            shape: BoxShape.circle,
                            color: GteShellTheme.accentWarm,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            reason,
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ),
                      ],
                    ),
                  ),
                )
                .toList(growable: false),
          ),
        ],
      ),
    );
  }
}
