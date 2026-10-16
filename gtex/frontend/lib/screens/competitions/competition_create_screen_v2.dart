import 'package:flutter/material.dart';

import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/features/competition_redesign/presentation/gtex_competitions_hub_screen_v2.dart';
import 'package:gte_frontend/features/competitions_hub/presentation/gte_competitions_hub_screen_v2.dart';

/// Route-compatible wrapper for existing competition create routes.
class CompetitionCreateScreenV2 extends StatelessWidget {
  const CompetitionCreateScreenV2({
    super.key,
    required this.controller,
    this.isAuthenticated = false,
    this.onOpenLogin,
  });

  final CompetitionController controller;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;

  @override
  Widget build(BuildContext context) {
    return GtexCompetitionCreateScreenV2(
      repository: LiveGtexCompetitionRepositoryAdapter(
        controller: controller,
        isAuthenticated: isAuthenticated,
        onOpenLogin: onOpenLogin,
      ),
    );
  }
}
