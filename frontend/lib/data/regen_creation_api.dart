import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import '../models/regen_creation_models.dart';

class RegenCreationApi {
  RegenCreationApi({required this.client});

  final GteAuthedApi client;

  factory RegenCreationApi.standard({
    required String baseUrl,
    GteBackendMode mode = GteBackendMode.live,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    return RegenCreationApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
        transport: GteHttpTransport(),
        mode: resolvedMode,
      ),
    );
  }

  Future<RequestSonOptions> fetchRequestSonOptions() async {
    final Map<String, dynamic> payload = await client.getMap(
      '/regens/request-son/options',
      auth: true,
    );
    return RequestSonOptions.fromJson(payload);
  }

  Future<RegenCreationOrderList> listCreationOrders({int limit = 20}) async {
    final Map<String, dynamic> payload = await client.getMap(
      '/regens/creation-orders',
      query: <String, Object?>{'limit': limit},
      auth: true,
    );
    return RegenCreationOrderList.fromJson(payload);
  }

  Future<RequestSonPreview> previewRequestSon(
    RequestSonPreviewDraft draft,
  ) async {
    final Object? payload = await client.post(
      '/regens/request-son/preview',
      body: draft.toJson(),
      auth: true,
    );
    return RequestSonPreview.fromJson(payload);
  }

  Future<RegenCreationOrder> fetchCreationOrder(String orderId) async {
    final Map<String, dynamic> payload = await client.getMap(
      '/regens/creation-orders/$orderId',
      auth: true,
    );
    return RegenCreationOrder.fromJson(payload);
  }

  Future<RegenCreationOrder> createRequestSonOrder(
    RequestSonOrderDraft draft,
  ) async {
    final Object? payload = await client.post(
      '/regens/request-son',
      body: draft.toJson(),
      auth: true,
    );
    return RegenCreationOrder.fromJson(payload);
  }

  Future<RegenCreationOrder> payWithWallet(String orderId) async {
    final Object? payload = await client.post(
      '/regens/creation-orders/$orderId/pay-with-wallet',
      auth: true,
    );
    return RegenCreationOrder.fromJson(payload);
  }

  Future<RegenCreationOrder> cancelCreationOrder(String orderId) async {
    final Object? payload = await client.post(
      '/regens/creation-orders/$orderId/cancel',
      auth: true,
    );
    return RegenCreationOrder.fromJson(payload);
  }

  Future<RegenCreationOrder> generateAfterPayment(String orderId) async {
    final Object? payload = await client.post(
      '/regens/creation-orders/$orderId/generate-after-payment',
      auth: true,
    );
    return RegenCreationOrder.fromJson(payload);
  }
}
