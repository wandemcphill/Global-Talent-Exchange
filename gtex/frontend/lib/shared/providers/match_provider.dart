import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/live_match.dart';

final Provider<List<LiveMatch>> matchProvider = Provider<List<LiveMatch>>(
  (Ref ref) => const <LiveMatch>[],
);
