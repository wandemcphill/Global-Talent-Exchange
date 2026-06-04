import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/build_a_son/build_a_son.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';

@Deprecated(
  'Use BuildASonScreen. This adapter is retained only for legacy route compatibility.',
)
class RequestSonScreen extends StatelessWidget {
  const RequestSonScreen({
    super.key,
    required this.apiBaseUrl,
    required this.backendMode,
    this.onOrderGenerated,
  });

  final String apiBaseUrl;
  final GteBackendMode backendMode;
  final Future<void> Function()? onOrderGenerated;

  @override
  Widget build(BuildContext context) {
    return ProviderScope(
      overrides: [
        apiBaseUrlProvider.overrideWithValue(apiBaseUrl),
        criticalBackendModeProvider.overrideWithValue(backendMode),
      ],
      child: BuildASonScreen(
        onCompleted: (_) async {
          await onOrderGenerated?.call();
        },
      ),
    );
  }
}
