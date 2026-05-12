import 'package:flutter/material.dart';

import '../regen_redesign/presentation/gtex_create_son_screen_v2.dart';

/// Route-compatible Create-a-Son V2 wrapper.
///
/// The existing `RequestSonScreen` constructor takes backend args; keep it in
/// place until Codex wires a live `GtexRegenRepository` adapter.
class RequestSonScreenV2 extends StatelessWidget {
  const RequestSonScreenV2({super.key});

  @override
  Widget build(BuildContext context) {
    return const GtexCreateSonScreenV2();
  }
}
