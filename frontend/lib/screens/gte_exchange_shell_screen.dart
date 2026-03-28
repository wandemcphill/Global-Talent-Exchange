import 'package:flutter/widgets.dart';

import '../data/gte_api_repository.dart';
import '../features/gtex_ui_system/presentation/gtex_ui_shell_screen.dart';
import '../providers/gte_exchange_controller.dart';

class GteExchangeShellScreen extends StatelessWidget {
  const GteExchangeShellScreen({
    super.key,
    required this.controller,
    required this.apiBaseUrl,
    required this.backendMode,
    this.initialTab = GtexRootTab.home,
  });

  factory GteExchangeShellScreen.fromPath({
    Key? key,
    required GteExchangeController controller,
    required String apiBaseUrl,
    required GteBackendMode backendMode,
    required String initialPath,
  }) {
    return GteExchangeShellScreen(
      key: key,
      controller: controller,
      apiBaseUrl: apiBaseUrl,
      backendMode: backendMode,
      initialTab: _tabFromPath(initialPath),
    );
  }

  final GteExchangeController controller;
  final String apiBaseUrl;
  final GteBackendMode backendMode;
  final GtexRootTab initialTab;

  @override
  Widget build(BuildContext context) {
    return GtexUiSystemShellScreen(
      controller: controller,
      apiBaseUrl: apiBaseUrl,
      backendMode: backendMode,
      initialTab: initialTab,
    );
  }

  static GtexRootTab _tabFromPath(String rawPath) {
    final String normalized = rawPath.trim().toLowerCase();
    if (normalized.contains('/market')) {
      return GtexRootTab.market;
    }
    if (normalized.contains('/competitions') ||
        normalized.contains('/matches')) {
      return GtexRootTab.matches;
    }
    if (normalized.contains('/community') || normalized.contains('/world')) {
      return GtexRootTab.world;
    }
    if (normalized.contains('/club') ||
        normalized.contains('/wallet') ||
        normalized.contains('/profile')) {
      return GtexRootTab.profile;
    }
    return GtexRootTab.home;
  }
}
