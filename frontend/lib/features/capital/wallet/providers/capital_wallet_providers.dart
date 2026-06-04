import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';

import '../data/capital_wallet_api.dart';
import '../data/capital_wallet_availability.dart';

final Provider<CapitalWalletApi> capitalWalletApiProvider =
    Provider<CapitalWalletApi>((Ref ref) {
      return capitalWalletApiForClient(ref.watch(authedApiProvider));
    });

final FutureProvider<CapitalWalletAvailability>
capitalWalletAvailabilityProvider = FutureProvider<CapitalWalletAvailability>((
  Ref ref,
) {
  return ref
      .watch(capitalWalletApiProvider)
      .fetchAvailability(currency: GteLedgerUnit.coin);
});
