import 'dart:convert';

import 'package:http/http.dart' as http;

import 'gte_api_repository.dart';

typedef GteHttpClientFactory = http.Client Function();

class GteHttpTransport implements GteTransport {
  GteHttpTransport({
    Duration? connectionTimeout,
    http.Client? client,
  })  : connectionTimeout = connectionTimeout ?? const Duration(seconds: 5),
        _client = client;

  final Duration connectionTimeout;
  final http.Client? _client;

  static GteHttpClientFactory clientFactory = http.Client.new;

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    final http.Client client = _client ?? clientFactory();
    final bool ownsClient = _client == null;
    try {
      final http.Request httpRequest = http.Request(request.method, request.uri)
        ..headers.addAll(request.headers);
      if (request.body != null) {
        httpRequest.body = jsonEncode(request.body);
      }
      final http.StreamedResponse response =
          await client.send(httpRequest).timeout(connectionTimeout);
      final String text = await response.stream.bytesToString();
      final Object? decodedBody =
          text.trim().isEmpty ? null : _decodeBody(text);
      return GteTransportResponse(
        statusCode: response.statusCode,
        body: decodedBody,
        headers: response.headers,
      );
    } finally {
      if (ownsClient) {
        client.close();
      }
    }
  }

  Object _decodeBody(String text) {
    try {
      return jsonDecode(text);
    } on FormatException {
      return text;
    }
  }
}

class GteFileTokenStore implements GteTokenStore {
  GteFileTokenStore([this.storageKey = 'gte_access_token']);

  final String storageKey;
  static final Map<String, String> _tokens = <String, String>{};

  @override
  Future<String?> readToken() async {
    final String token = (_tokens[storageKey] ?? '').trim();
    return token.isEmpty ? null : token;
  }

  @override
  Future<void> writeToken(String? token) async {
    if (token == null || token.isEmpty) {
      _tokens.remove(storageKey);
      return;
    }
    _tokens[storageKey] = token;
  }
}
