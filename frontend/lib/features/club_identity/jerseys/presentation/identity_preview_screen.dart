import 'package:flutter/material.dart';

import '../../../../widgets/gte_shell_theme.dart';
import '../../../../widgets/gte_state_panel.dart';
import '../widgets/clash_warning_banner.dart';
import '../widgets/identity_preview_panel.dart';
import 'club_identity_controller.dart';

class IdentityPreviewScreen extends StatelessWidget {
  const IdentityPreviewScreen({
    super.key,
    required this.controller,
  });

  final ClubIdentityController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (BuildContext context, _) {
        final identity = controller.identity;
        return Scaffold(
          appBar: AppBar(
            title: const Text('Identity Preview'),
            actions: <Widget>[
              IconButton(
                tooltip: 'Reload',
                onPressed: controller.reload,
                icon: const Icon(Icons.refresh),
              ),
              IconButton(
                tooltip: 'Save',
                onPressed: controller.saveAll,
                icon: const Icon(Icons.save_outlined),
              ),
            ],
          ),
          body: Container(
            decoration: gteBackdropDecoration(),
            child: identity == null
                ? const Padding(
                    padding: EdgeInsets.all(20),
                    child: GteStatePanel(
                      title: 'Preview unavailable',
                      message:
                          'Load a club identity before opening preview surfaces.',
                      icon: Icons.visibility_outlined,
                    ),
                  )
                : SingleChildScrollView(
                    padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Identity surfaces',
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Preview how the same badge, club code, and kit palette compress across football-first UI moments.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 20),
                        ClashWarningBanner(
                          warnings: controller.warnings,
                          title: controller.hasUnsavedChanges
                              ? 'Previewing unsaved changes'
                              : 'Visual readiness',
                        ),
                        const SizedBox(height: 20),
                        IdentityPreviewPanel(identity: identity),
                        if (controller.hasUnsavedChanges) ...<Widget>[
                          const SizedBox(height: 20),
                          Text(
                            'These previews are showing local draft edits. Save to keep them after the next reload.',
                            style: Theme.of(context)
                                .textTheme
                                .bodyMedium
                                ?.copyWith(
                                  color: GteShellTheme.textPrimary,
                                ),
                          ),
                        ],
                      ],
                    ),
                  ),
          ),
        );
      },
    );
  }
}
