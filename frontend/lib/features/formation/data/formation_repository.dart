import 'dart:async';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/formation/domain/formation_models.dart';

abstract class IFormationRepository {
  Future<FormationDto?> getActiveFormation(String clubId);
  Future<FormationDto> saveFormationDraft(
    String clubId,
    FormationSaveRequest request,
  );
  Future<FormationDto> publishFormation(String clubId, String formationId);
  Future<List<FormationHistoryItemDto>> getFormationHistory(String clubId);
  Future<FormationDto> getFormationDetail(String formationId);
  Future<FormationDto> restoreFormationDraft(
    String clubId,
    String sourceFormationId,
  );
  Future<List<FormationSelectionReadyPlayerDto>> getSelectionReadyPlayers(
    String clubId,
  );
  Stream<FormationWsEvent> subscribeToFormationEvents(String clubId);
}

sealed class FormationWsEvent {
  const FormationWsEvent();
}

class FormationActiveUpdated extends FormationWsEvent {
  const FormationActiveUpdated(this.formation);

  final FormationDto formation;
}

class FormationChemistryAlert extends FormationWsEvent {
  const FormationChemistryAlert(this.warnings);

  final List<String> warnings;
}

class FormationApiRepository implements IFormationRepository {
  const FormationApiRepository({required GteAuthedApi client})
    : _client = client;

  final GteAuthedApi _client;

  @override
  Future<FormationDto?> getActiveFormation(String clubId) async {
    try {
      final Object? payload = await _client.request(
        'GET',
        '/clubs/$clubId/formation/active',
      );
      if (payload == null) {
        return null;
      }
      return FormationDto.fromJson(_unwrapMap(payload, 'formation'));
    } on GteApiException catch (error) {
      if (error.type == GteApiErrorType.notFound || error.statusCode == 404) {
        return null;
      }
      rethrow;
    }
  }

  @override
  Future<FormationDto> saveFormationDraft(
    String clubId,
    FormationSaveRequest request,
  ) async {
    final Object? payload = await _client.post(
      '/clubs/$clubId/formations/draft',
      body: request.toJson(),
    );
    return FormationDto.fromJson(_unwrapMap(payload, 'formation'));
  }

  @override
  Future<FormationDto> publishFormation(
    String clubId,
    String formationId,
  ) async {
    final Object? payload = await _client.post(
      '/clubs/$clubId/formations/$formationId/publish',
      body: const <String, Object?>{},
    );
    return FormationDto.fromJson(_unwrapMap(payload, 'formation'));
  }

  @override
  Future<List<FormationHistoryItemDto>> getFormationHistory(
    String clubId,
  ) async {
    final Object? payload = await _client.request(
      'GET',
      '/clubs/$clubId/formations',
    );
    return _unwrapList(payload, const <String>[
      'formations',
      'items',
      'data',
    ]).map(FormationHistoryItemDto.fromJson).toList(growable: false);
  }

  @override
  Future<FormationDto> getFormationDetail(String formationId) async {
    final Object? payload = await _client.request(
      'GET',
      '/formations/$formationId',
    );
    return FormationDto.fromJson(_unwrapMap(payload, 'formation'));
  }

  @override
  Future<FormationDto> restoreFormationDraft(
    String clubId,
    String sourceFormationId,
  ) async {
    final Object? payload = await _client.post(
      '/clubs/$clubId/formations/$sourceFormationId/restore',
      body: const <String, Object?>{},
    );
    return FormationDto.fromJson(_unwrapMap(payload, 'formation'));
  }

  @override
  Future<List<FormationSelectionReadyPlayerDto>> getSelectionReadyPlayers(
    String clubId,
  ) async {
    final Object? payload = await _client.request(
      'GET',
      '/clubs/$clubId/squad/selection-ready',
    );
    return _unwrapList(payload, const <String>['players', 'items', 'data'])
        .map(FormationSelectionReadyPlayerDto.fromJson)
        .where((FormationSelectionReadyPlayerDto player) => player.eligible)
        .toList(growable: false);
  }

  @override
  Stream<FormationWsEvent> subscribeToFormationEvents(String clubId) {
    return const Stream<FormationWsEvent>.empty();
  }
}

Object? _unwrapMap(Object? payload, String key) {
  if (payload is Map) {
    final Map<String, Object?> json = Map<String, Object?>.from(payload);
    return GteJson.value(json, <String>[key]) ?? json;
  }
  return payload;
}

List<Object?> _unwrapList(Object? payload, List<String> keys) {
  if (payload is List) {
    return payload.cast<Object?>();
  }
  if (payload is Map) {
    final Map<String, Object?> json = Map<String, Object?>.from(payload);
    for (final String key in keys) {
      final Object? value = json[key];
      if (value is List) {
        return value.cast<Object?>();
      }
    }
  }
  return const <Object?>[];
}
