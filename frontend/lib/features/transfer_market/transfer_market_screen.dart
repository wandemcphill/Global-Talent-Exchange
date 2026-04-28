import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../navigation/app_destinations.dart';
import '../../shared/providers/auth_provider.dart';
import '../player_card_marketplace/presentation/player_card_marketplace_screen.dart';

class TransferMarketScreen extends ConsumerWidget {
  const TransferMarketScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return PlayerCardMarketplaceScreen(
      baseUrl: ref.watch(apiBaseUrlProvider),
      backendMode: ref.watch(criticalBackendModeProvider),
      accessToken: ref.watch(accessTokenProvider),
      currentUserId: ref.watch(currentUserIdProvider),
      onOpenLogin: () => context.push(AppRoutes.profileLogin),
    );
  }
}
