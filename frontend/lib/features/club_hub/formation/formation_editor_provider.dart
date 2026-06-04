import 'package:flutter/foundation.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';

import 'formation_editor_models.dart';

enum FormationEditorLoadState {
  blocked,
  syncing,
  ready,
  empty,
  degraded,
  error,
}

class FormationEditorController extends ChangeNotifier {
  FormationEditorController({
    required this.clubId,
    required this.baseUrl,
    this.accessToken,
    GteTransport? transport,
  }) : _transport = transport ?? GteHttpTransport();

  final String clubId;
  final String baseUrl;
  final String? accessToken;
  final GteTransport _transport;

  FormationEditorLoadState state = FormationEditorLoadState.syncing;
  FormationEditorSnapshot? snapshot;
  String? errorMessage;
  bool isSaving = false;
  bool isPublishing = false;

  Future<void> load() async {
    if (baseUrl.trim().isEmpty) {
      state = FormationEditorLoadState.blocked;
      errorMessage = 'Formation provider is missing an API base URL.';
      notifyListeners();
      return;
    }
    state = FormationEditorLoadState.syncing;
    errorMessage = null;
    notifyListeners();
    try {
      final FormationEditorSnapshot loaded = await _fetchSnapshot();
      snapshot = loaded;
      state = _stateForSnapshot(loaded);
    } on GteApiException catch (error) {
      snapshot = null;
      final bool blocked = _isBlockedBackendGap(error);
      state =
          blocked
              ? FormationEditorLoadState.blocked
              : FormationEditorLoadState.error;
      errorMessage =
          blocked
              ? 'Formation endpoint is not mounted for this club yet.'
              : error.message;
    } catch (error) {
      snapshot = null;
      state = FormationEditorLoadState.error;
      errorMessage = 'Unable to sync formation data. $error';
    } finally {
      notifyListeners();
    }
  }

  Future<void> saveDraft() async {
    final FormationEditorSnapshot? current = snapshot;
    if (current == null || !current.canSaveDraft) {
      return;
    }
    await _mutate(
      saving: true,
      method: 'PATCH',
      path: '/api/v2/clubs/$clubId/formation/draft',
      body: <String, Object?>{
        'sync_token': current.syncToken,
        'formation_id': current.formationId,
        'version': current.version,
      },
    );
  }

  Future<void> publish() async {
    final FormationEditorSnapshot? current = snapshot;
    if (current == null || !current.canPublish) {
      return;
    }
    await _mutate(
      publishing: true,
      method: 'POST',
      path: '/api/v2/clubs/$clubId/formation/publish',
      body: <String, Object?>{
        'sync_token': current.syncToken,
        'formation_id': current.formationId,
        'version': current.version,
      },
    );
  }

  Future<FormationEditorSnapshot> _fetchSnapshot() async {
    final Object? payload = await _request(
      'GET',
      '/api/v2/clubs/$clubId/formation',
    );
    return FormationEditorSnapshot.fromJson(payload);
  }

  Future<void> _mutate({
    required String method,
    required String path,
    Object? body,
    bool saving = false,
    bool publishing = false,
  }) async {
    isSaving = saving;
    isPublishing = publishing;
    errorMessage = null;
    notifyListeners();
    try {
      final Object? payload = await _request(method, path, body: body);
      final FormationEditorSnapshot updated = FormationEditorSnapshot.fromJson(
        payload,
      );
      snapshot = updated;
      state = _stateForSnapshot(updated);
    } on GteApiException catch (error) {
      final bool blocked = _isBlockedBackendGap(error);
      state =
          blocked
              ? FormationEditorLoadState.blocked
              : FormationEditorLoadState.error;
      errorMessage =
          blocked
              ? 'Formation endpoint is not mounted for this club yet.'
              : error.message;
    } catch (error) {
      state = FormationEditorLoadState.error;
      errorMessage = 'Unable to update formation. $error';
    } finally {
      isSaving = false;
      isPublishing = false;
      notifyListeners();
    }
  }

  Future<Object?> _request(String method, String path, {Object? body}) async {
    final Map<String, String> headers = <String, String>{
      'Accept': 'application/json',
    };
    if (body != null) {
      headers['Content-Type'] = 'application/json';
    }
    final String token = accessToken?.trim() ?? '';
    if (token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }
    final GteTransportResponse response = await _transport.send(
      GteTransportRequest(
        method: method,
        uri: _uriForFormationPath(path),
        headers: headers,
        body: body,
      ),
    );
    if (response.statusCode >= 400) {
      throw GteApiException(
        type: _errorTypeFromStatus(response.statusCode),
        message: _errorMessage(response.body),
        statusCode: response.statusCode,
        cause: response.body,
      );
    }
    return gteApiSuccessPayload(response.body);
  }

  static FormationEditorLoadState _stateForSnapshot(
    FormationEditorSnapshot snapshot,
  ) {
    switch (snapshot.snapshotState) {
      case FormationSnapshotState.blocked:
        return FormationEditorLoadState.blocked;
      case FormationSnapshotState.empty:
        return FormationEditorLoadState.empty;
      case FormationSnapshotState.degraded:
        return FormationEditorLoadState.degraded;
      case FormationSnapshotState.draft:
      case FormationSnapshotState.published:
        return snapshot.health.isHealthy
            ? FormationEditorLoadState.ready
            : FormationEditorLoadState.degraded;
    }
  }

  Uri _uriForFormationPath(String path) {
    final Uri base = Uri.parse(baseUrl);
    final String normalizedPath =
        path.startsWith('/') ? path : '/${path.trim()}';
    return base.replace(path: normalizedPath);
  }

  static bool _isBlockedBackendGap(GteApiException error) {
    return error.statusCode == 404 ||
        error.type == GteApiErrorType.notFound ||
        error.type == GteApiErrorType.unavailable;
  }

  static GteApiErrorType _errorTypeFromStatus(int statusCode) {
    if (statusCode == 401 || statusCode == 403) {
      return GteApiErrorType.unauthorized;
    }
    if (statusCode == 404) {
      return GteApiErrorType.notFound;
    }
    if (statusCode == 422) {
      return GteApiErrorType.validation;
    }
    if (statusCode >= 500) {
      return GteApiErrorType.unavailable;
    }
    return GteApiErrorType.unknown;
  }

  static String _errorMessage(Object? body) {
    if (body is Map<String, Object?>) {
      final Object? detail = body['detail'] ?? body['message'] ?? body['error'];
      if (detail != null && detail.toString().trim().isNotEmpty) {
        return detail.toString();
      }
    }
    if (body is Map) {
      final Object? detail = body['detail'] ?? body['message'] ?? body['error'];
      if (detail != null && detail.toString().trim().isNotEmpty) {
        return detail.toString();
      }
    }
    return 'Formation backend returned an error.';
  }
}
