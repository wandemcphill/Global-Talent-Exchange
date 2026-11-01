import 'package:flutter/material.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/regen_creation_api.dart';
import 'package:gte_frontend/data/regen_universe_api.dart';
import 'package:gte_frontend/features/regen_redesign/data/gtex_regen_repository.dart';

import '../regen_redesign/presentation/gtex_create_son_screen_v2.dart';

/// Route-compatible Create-a-Son V2 wrapper wired to live GtexRegenRepository.
class RequestSonScreenV2 extends StatelessWidget {
  const RequestSonScreenV2({
    super.key,
    this.baseUrl,
    this.backendMode = GteBackendMode.live,
    this.accessToken,
    this.isAuthenticated = false,
    this.allowFixtureData = false,
  });

  final String? baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final bool isAuthenticated;
  final bool allowFixtureData;

  @override
  Widget build(BuildContext context) {
    final String? resolvedBaseUrl = baseUrl?.trim();
    final GtexRegenRepository? repo = (resolvedBaseUrl != null && resolvedBaseUrl.isNotEmpty)
        ? LiveGtexRegenRepository(
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
          )
        : (allowFixtureData || backendMode == GteBackendMode.fixture
            ? const DemoGtexRegenRepository()
            : null);

    return GtexCreateSonScreenV2(
      repository: repo,
      allowFixtureData: allowFixtureData || backendMode == GteBackendMode.fixture,
    );
  }
}
