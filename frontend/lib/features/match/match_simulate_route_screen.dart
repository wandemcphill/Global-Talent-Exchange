import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/gte_api_repository.dart';
import '../../shared/providers/auth_provider.dart';
import 'live_match_viewer_route_support.dart';
import 'match_simulate_screen.dart';

class MatchSimulateRouteScreen extends ConsumerWidget {
  const MatchSimulateRouteScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final GteBackendMode mode = ref.watch(criticalBackendModeProvider);
    if (mode == GteBackendMode.fixture) {
      return const MatchSimulateScreen();
    }
    return const MatchRouteBlockedScreen(
      title: 'Simulation sandbox blocked',
      subtitle:
          'The local simulation sandbox is reserved for explicit fixture-mode runs and is disabled in the live shell.',
      reason:
          'This route does not consume live backend state. It is only available when the app is started in fixture mode for local QA, so live shells keep it blocked instead of mounting local simulation data.',
      detailTitle: 'Fixture mode required',
      detailSubtitle:
          'The shipped live shell keeps local-only simulation tools off the active match surface.',
    );
  }
}
