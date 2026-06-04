import 'package:gte_frontend/data/regen_creation_api.dart';
import 'package:gte_frontend/features/capital/wallet/data/capital_wallet_api.dart';
import 'package:gte_frontend/models/regen_creation_models.dart';

abstract interface class BuildASonCreationClient {
  Future<RequestSonOptions> fetchRequestSonOptions();

  Future<RequestSonPreview> previewRequestSon(RequestSonPreviewDraft draft);

  Future<RegenCreationOrder> fetchCreationOrder(String orderId);

  Future<RegenCreationOrder> createRequestSonOrder(RequestSonOrderDraft draft);

  Future<RegenCreationOrder> payWithWallet(String orderId);

  Future<RegenCreationOrder> cancelCreationOrder(String orderId);

  Future<RegenCreationOrder> generateAfterPayment(String orderId);

  Future<void> refreshWalletTruth();
}

class RegenCreationApiBuildASonClient implements BuildASonCreationClient {
  const RegenCreationApiBuildASonClient({
    required this.api,
    required this.walletApi,
    this.refreshWalletAvailability,
  });

  final RegenCreationApi api;
  final CapitalWalletApi walletApi;
  final Future<void> Function()? refreshWalletAvailability;

  @override
  Future<RequestSonOptions> fetchRequestSonOptions() {
    return api.fetchRequestSonOptions();
  }

  @override
  Future<RequestSonPreview> previewRequestSon(RequestSonPreviewDraft draft) {
    return api.previewRequestSon(draft);
  }

  @override
  Future<RegenCreationOrder> fetchCreationOrder(String orderId) {
    return api.fetchCreationOrder(orderId);
  }

  @override
  Future<RegenCreationOrder> createRequestSonOrder(RequestSonOrderDraft draft) {
    return api.createRequestSonOrder(draft);
  }

  @override
  Future<RegenCreationOrder> payWithWallet(String orderId) {
    return api.payWithWallet(orderId);
  }

  @override
  Future<RegenCreationOrder> cancelCreationOrder(String orderId) {
    return api.cancelCreationOrder(orderId);
  }

  @override
  Future<RegenCreationOrder> generateAfterPayment(String orderId) {
    return api.generateAfterPayment(orderId);
  }

  @override
  Future<void> refreshWalletTruth() async {
    final Future<void> Function()? refreshWalletAvailability =
        this.refreshWalletAvailability;
    if (refreshWalletAvailability != null) {
      await refreshWalletAvailability();
      return;
    }
    await walletApi.fetchAvailability();
  }
}
