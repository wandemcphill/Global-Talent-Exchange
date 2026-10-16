import 'package:flutter/material.dart';

import '../../features/system_profile_redesign/presentation/gtex_profile_controller.dart';
import '../../features/system_profile_redesign/widgets/gtex_system_state_panel.dart';

class GtexSystemStatesGalleryV2 extends StatelessWidget {
  const GtexSystemStatesGalleryV2({
    super.key,
    this.controller = const GtexProfileController(),
  });

  final GtexProfileController controller;

  @override
  Widget build(BuildContext context) {
    final states = controller.systemStateGallery();
    return Scaffold(
      backgroundColor: const Color(0xFF050B08),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'GTEX system states',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Use these reusable states across market, wallet, KYC, admin, news, match, and club flows.',
                style: TextStyle(color: Colors.white60),
              ),
              const SizedBox(height: 18),
              Expanded(
                child: GridView.builder(
                  gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                    maxCrossAxisExtent: 420,
                    mainAxisExtent: 380,
                    mainAxisSpacing: 16,
                    crossAxisSpacing: 16,
                  ),
                  itemCount: states.length,
                  itemBuilder:
                      (context, index) =>
                          GtexSystemStatePanel(spec: states[index]),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
