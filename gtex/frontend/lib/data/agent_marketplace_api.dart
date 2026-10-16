import 'agent_marketplace_models.dart';
import 'gte_api_repository.dart';
import 'gte_authed_api.dart';

class AgentMarketplaceApi {
  AgentMarketplaceApi({
    required GteRepositoryConfig config,
    required this.transport,
    required this.accessToken,
    GteBackendMode mode = GteBackendMode.live,
  }) : config = GteRepositoryConfig(
         baseUrl: config.baseUrl,
         mode: gteProductionBackendMode(config.mode),
       ),
       mode = gteProductionBackendMode(mode);

  final GteRepositoryConfig config;
  final GteTransport transport;
  final String? accessToken;
  final GteBackendMode mode;

  GteAuthedApi get _client => GteAuthedApi(
    config: config,
    transport: transport,
    accessToken: accessToken,
    mode: mode,
  );

  Future<List<GteConversationSummary>> fetchConversations() async {
    final List<dynamic> payload = await _client.getList(
      '/conversations',
      auth: true,
    );
    return payload.map(GteConversationSummary.fromJson).toList(growable: false);
  }

  Future<GteConversationDetail> fetchConversationDetail(
    String conversationId,
  ) async {
    final Map<String, dynamic> payload = await _client.getMap(
      '/conversations/$conversationId/messages',
      auth: true,
    );
    return GteConversationDetail.fromJson(payload);
  }

  Future<GteConversationDetail> startConversation({
    required String playerId,
    required String message,
    String? actorRole,
  }) async {
    final Object? payload = await _client.post(
      '/conversations/start',
      auth: true,
      body: <String, Object?>{
        'player_id': playerId,
        'message': message,
        if (actorRole != null && actorRole.trim().isNotEmpty)
          'actor_role': actorRole.trim(),
      },
    );
    return GteConversationDetail.fromJson(payload);
  }

  Future<GteConversationDetail> sendMessage({
    required String conversationId,
    required String message,
  }) async {
    final Object? payload = await _client.post(
      '/conversations/$conversationId/message',
      auth: true,
      body: <String, Object?>{'message': message},
    );
    return GteConversationDetail.fromJson(payload);
  }
}
