import 'dart:convert';
import 'dart:io';

import 'gte_api_repository.dart';

class GteHttpTransport implements GteTransport {
  GteHttpTransport({
    Duration? connectionTimeout,
  }) : connectionTimeout = connectionTimeout ?? const Duration(seconds: 5);

  final Duration connectionTimeout;

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    final HttpClient client = HttpClient()
      ..connectionTimeout = connectionTimeout;
    try {
      final HttpClientRequest httpRequest =
          await client.openUrl(request.method, request.uri);
      request.headers.forEach(httpRequest.headers.add);
      if (request.body != null) {
        httpRequest.write(jsonEncode(request.body));
      }
      final HttpClientResponse response = await httpRequest.close();
      final String text = await response.transform(utf8.decoder).join();
      final Object? decodedBody =
          text.trim().isEmpty ? null : _decodeBody(text);
      final Map<String, String> responseHeaders = <String, String>{};
      response.headers.forEach((String name, List<String> values) {
        responseHeaders[name] = values.join(', ');
      });
      return GteTransportResponse(
        statusCode: response.statusCode,
        body: decodedBody,
        headers: responseHeaders,
      );
    } finally {
      client.close(force: true);
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
  GteFileTokenStore(this.file);

  final File file;

  @override
  Future<String?> readToken() async {
    if (!await file.exists()) {
      return null;
    }
    final String token = (await file.readAsString()).trim();
    return token.isEmpty ? null : token;
  }

  @override
  Future<void> writeToken(String? token) async {
    if (token == null || token.isEmpty) {
      if (await file.exists()) {
        await file.delete();
      }
      return;
    }
    await file.parent.create(recursive: true);
    await file.writeAsString(token);
  }
}
