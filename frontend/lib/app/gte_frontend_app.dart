import 'package:flutter/material.dart';

import '../data/gte_exchange_api_client.dart';
import '../providers/gte_exchange_controller.dart';
import '../screens/gte_exchange_shell_screen.dart';
import '../widgets/gte_shell_theme.dart';
import 'gte_app_config.dart';

class GteFrontendApp extends StatefulWidget {
  const GteFrontendApp({
    super.key,
    this.controller,
    this.config,
  });

  final GteExchangeController? controller;
  final GteAppConfig? config;

  @override
  State<GteFrontendApp> createState() => _GteFrontendAppState();
}

class _GteFrontendAppState extends State<GteFrontendApp> {
  late final GteAppConfig _config;
  late final GteExchangeController _controller;
  late final bool _ownsController;

  @override
  void initState() {
    super.initState();
    _config = widget.config ?? GteAppConfig.fromEnvironment();
    _ownsController = widget.controller == null;
    _controller = widget.controller ??
        GteExchangeController(
          api: GteExchangeApiClient.standard(
            baseUrl: _config.apiBaseUrl,
            mode: _config.backendMode,
          ),
        );
  }

  @override
  void dispose() {
    if (_ownsController) {
      _controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Global Talent Exchange',
      theme: GteShellTheme.build(),
      home: GteExchangeShellScreen(
        controller: _controller,
        apiBaseUrl: _config.apiBaseUrl,
        backendMode: _config.backendMode,
      ),
    );
  }
}
