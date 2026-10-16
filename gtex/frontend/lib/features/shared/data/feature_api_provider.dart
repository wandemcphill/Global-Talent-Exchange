import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/gte_authed_api.dart';
import '../../../shared/providers/auth_provider.dart';

typedef FeatureApiFactory<T> = T Function(GteAuthedApi client);

Provider<T> createFeatureApiProvider<T>(FeatureApiFactory<T> factory) {
  return Provider<T>((Ref ref) => factory(ref.watch(authedApiProvider)));
}
