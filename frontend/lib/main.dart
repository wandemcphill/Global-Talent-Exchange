import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/theme/app_theme.dart';
import 'navigation/app_router.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ProviderScope(child: GtexApp()));
}

class GtexApp extends ConsumerWidget {
  const GtexApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp.router(
      debugShowCheckedModeBanner: false,
      title: 'GTEX',
      theme: AppTheme.dark(),
      routerConfig: ref.watch(appRouterProvider),
    );
  }
}
