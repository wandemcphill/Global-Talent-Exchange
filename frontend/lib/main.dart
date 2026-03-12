import 'package:flutter/material.dart';

import 'app/gte_frontend_app.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  // Canonical MVP entrypoint for the exchange app.
  runApp(const GteFrontendApp());
}
