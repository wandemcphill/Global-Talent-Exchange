import 'package:flutter/widgets.dart';

import '../data/gte_api_repository.dart';
import '../features/navigation/presentation/gte_navigation_shell_screen.dart';
import '../features/navigation_guards/gte_navigation_guards.dart';
import '../providers/gte_exchange_controller.dart';
import '../services/ambient_audio_controller.dart';

class GteExchangeShellScreen extends StatelessWidget {
  const GteExchangeShellScreen({
    super.key,
    required this.controller,
    required this.apiBaseUrl,
    required this.backendMode,
    this.ambientAudioController,
    this.initialPath = '/app/home',
    this.navigationDependencies,
  });

  factory GteExchangeShellScreen.fromPath({
    Key? key,
    required GteExchangeController controller,
    required String apiBaseUrl,
    required GteBackendMode backendMode,
    AmbientAudioState? ambientAudioController,
    required String initialPath,
    GteNavigationDependencies? navigationDependencies,
  }) {
    return GteExchangeShellScreen(
      key: key,
      controller: controller,
      apiBaseUrl: apiBaseUrl,
      backendMode: backendMode,
      ambientAudioController: ambientAudioController,
      initialPath: initialPath,
      navigationDependencies: navigationDependencies,
    );
  }

  final GteExchangeController controller;
  final String apiBaseUrl;
  final GteBackendMode backendMode;
  final AmbientAudioState? ambientAudioController;
  final String initialPath;
  final GteNavigationDependencies? navigationDependencies;

  @override
  Widget build(BuildContext context) {
    return GteNavigationShellScreen.fromPath(
      controller: controller,
      apiBaseUrl: apiBaseUrl,
      backendMode: backendMode,
      ambientAudioController: ambientAudioController,
      initialPath: initialPath,
      navigationDependencies: navigationDependencies,
    );
  }
}
