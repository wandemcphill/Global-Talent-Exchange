import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';

CapitalDisputeApi capitalDisputeApiForClient(GteExchangeApiClient client) {
  return CapitalDisputeApi(client: client);
}

class CapitalDisputeApi {
  const CapitalDisputeApi({required GteExchangeApiClient client})
    : _client = client;

  final GteExchangeApiClient _client;

  Future<List<GteDispute>> listDisputes() {
    return _client.listDisputes();
  }

  Future<GteDispute> openDispute(GteDisputeCreateRequest request) {
    return _client.openDispute(request);
  }

  Future<GteDispute> fetchDispute(String disputeId) {
    return _client.fetchDispute(disputeId);
  }

  Future<GteDispute> fetchAdminDispute(String disputeId) {
    return _client.fetchAdminDispute(disputeId);
  }

  Future<GteDisputeMessage> sendDisputeMessage(
    String disputeId,
    GteDisputeMessageRequest request,
  ) {
    return _client.sendDisputeMessage(disputeId, request);
  }

  Future<GteDisputeMessage> adminSendDisputeMessage(
    String disputeId,
    GteDisputeMessageRequest request,
  ) {
    return _client.adminSendDisputeMessage(disputeId, request);
  }

  Future<GteAttachment> uploadAttachment(
    String filename,
    List<int> bytes, {
    String? contentType,
  }) {
    return _client.uploadAttachment(filename, bytes, contentType: contentType);
  }

  Future<GteTreasurySettings> fetchTreasurySettings() {
    return _client.fetchTreasurySettings();
  }
}
