import 'package:flutter/material.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/regen_creation_api.dart';
import 'package:gte_frontend/data/regen_universe_api.dart';
import 'package:gte_frontend/features/regen_redesign/data/gtex_regen_repository.dart';

import '../regen_redesign/presentation/gtex_regen_world_screen_v2.dart';

class RegensScreenV2 extends StatelessWidget {
  const RegensScreenV2({
    super.key,
    this.baseUrl,
    this.backendMode = GteBackendMode.live,
    this.accessToken,
    this.isAuthenticated = false,
    this.isAdmin = false,
    this.onOpenAwards,
  });

  final String? baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final bool isAuthenticated;
  final bool isAdmin;
  final VoidCallback? onOpenAwards;

  @override
  Widget build(BuildContext context) {
    final String? resolvedBaseUrl = baseUrl?.trim();
    if (resolvedBaseUrl == null || resolvedBaseUrl.isEmpty) {
      return GtexRegenWorldScreenV2(
        isAdmin: isAdmin,
        onOpenAwards: onOpenAwards,
      );
    }

    return GtexRegenWorldScreenV2(
      repository: LiveGtexRegenRepository(
        universeApi: RegenUniverseApi.standard(
          baseUrl: resolvedBaseUrl,
          mode: backendMode,
        ),
        creationApi: RegenCreationApi.standard(
          baseUrl: resolvedBaseUrl,
          mode: backendMode,
          accessToken: accessToken,
        ),
        isAuthenticated: isAuthenticated,
      ),
      isAdmin: isAdmin,
      onOpenAwards: onOpenAwards,
    );
  }
}
