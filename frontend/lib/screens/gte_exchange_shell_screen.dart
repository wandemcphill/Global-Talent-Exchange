import 'package:flutter/widgets.dart';

import '../data/gte_api_repository.dart';
import '../features/navigation/presentation/gte_navigation_shell_screen.dart';
import '../providers/gte_exchange_controller.dart';

class GteExchangeShellScreen extends StatelessWidget {
  const GteExchangeShellScreen({
    super.key,
    required this.controller,
    required this.apiBaseUrl,
    required this.backendMode,
    this.initialPath = '/app/world',
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
      initialPath: initialPath,
    );
  }

  final GteExchangeController controller;
  final String apiBaseUrl;
  final GteBackendMode backendMode;
  final String initialPath;

  @override
  Widget build(BuildContext context) {
    return GteNavigationShellScreen.fromPath(
      controller: controller,
      apiBaseUrl: apiBaseUrl,
      backendMode: backendMode,
      initialPath: initialPath,
    );
  }
}
