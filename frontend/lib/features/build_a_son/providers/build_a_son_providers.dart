import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/capital/wallet/providers/capital_wallet_providers.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';
import 'package:gte_frontend/shared/providers/regen_provider.dart';
import 'package:gte_frontend/shared/realtime/realtime.dart';

import '../data/build_a_son_creation_client.dart';

const List<String> _buildASonRealtimeTopics = <String>['wallet'];

final Provider<BuildASonCreationClient> buildASonCreationClientProvider =
    Provider<BuildASonCreationClient>((Ref ref) {
      return RegenCreationApiBuildASonClient(
        api: ref.watch(regenCreationApiProvider),
        walletApi: ref.watch(capitalWalletApiProvider),
        refreshWalletAvailability:
            () => ref.refresh(capitalWalletAvailabilityProvider.future),
      );
    });

final Provider<GtexRealtimeClient?> buildASonRealtimeClientProvider =
    Provider<GtexRealtimeClient?>((Ref ref) {
      if (ref.watch(criticalBackendModeProvider) == GteBackendMode.fixture) {
        return null;
      }
      final Uri? socketUri = buildGtexRealtimeUri(
        ref.watch(apiBaseUrlProvider),
        accessToken: ref.watch(accessTokenProvider),
        topics: _buildASonRealtimeTopics,
      );
      if (socketUri == null) {
        return null;
      }
      final GtexRealtimeService service = GtexRealtimeService(
        socketUri: socketUri,
        topics: _buildASonRealtimeTopics,
      )..connect();
      ref.onDispose(() {
        unawaited(service.dispose());
      });
      return service;
    });

final Provider<Stream<BuildASonOrderRealtimeEvent>>
buildASonOrderRealtimeEventsProvider =
    Provider<Stream<BuildASonOrderRealtimeEvent>>((Ref ref) {
      final GtexRealtimeClient? client = ref.watch(
        buildASonRealtimeClientProvider,
      );
      if (client == null) {
        return const Stream<BuildASonOrderRealtimeEvent>.empty();
      }
      return client.events
          .map(BuildASonOrderRealtimeEvent.fromRealtimeEvent)
          .where((BuildASonOrderRealtimeEvent? event) => event != null)
          .cast<BuildASonOrderRealtimeEvent>();
    });

class BuildASonOrderRealtimeEvent {
  const BuildASonOrderRealtimeEvent({
    required this.type,
    required this.topic,
    required this.source,
    this.orderId,
  });

  final String type;
  final String topic;
  final String? orderId;
  final GtexRealtimeEvent source;

  static BuildASonOrderRealtimeEvent? fromRealtimeEvent(
    GtexRealtimeEvent event,
  ) {
    final String normalizedType = _normalizeRealtimeToken(event.type);
    if (!_isRegenCreationOrderRealtimeType(normalizedType)) {
      return null;
    }
    return BuildASonOrderRealtimeEvent(
      type: event.type,
      topic: event.topic,
      orderId: _extractRealtimeOrderId(event.payload),
      source: event,
    );
  }

  bool appliesToOrder(String activeOrderId) {
    final String trimmedActiveOrderId = activeOrderId.trim();
    if (trimmedActiveOrderId.isEmpty) {
      return false;
    }
    final String? trimmedEventOrderId = orderId?.trim();
    return trimmedEventOrderId == null ||
        trimmedEventOrderId.isEmpty ||
        trimmedEventOrderId == trimmedActiveOrderId;
  }
}

bool _isRegenCreationOrderRealtimeType(String normalizedType) {
  return normalizedType == 'regen_creation_order' ||
      normalizedType == 'regen_creation_order_update' ||
      normalizedType.startsWith('regen_creation_order_');
}

String? _extractRealtimeOrderId(Map<String, Object?> payload) {
  final String? direct = _firstPayloadString(payload, const <String>[
    'order_id',
    'orderId',
    'creation_order_id',
    'creationOrderId',
    'regen_creation_order_id',
    'regenCreationOrderId',
    'id',
  ]);
  if (direct != null) {
    return direct;
  }

  for (final String nestedKey in const <String>[
    'order',
    'creation_order',
    'creationOrder',
    'regen_creation_order',
    'regenCreationOrder',
  ]) {
    final Object? nested = payload[nestedKey];
    final Map<String, Object?>? nestedMap = _stringMap(nested);
    if (nestedMap != null) {
      final String? nestedOrderId = _firstPayloadString(
        nestedMap,
        const <String>[
          'id',
          'order_id',
          'orderId',
          'creation_order_id',
          'creationOrderId',
        ],
      );
      if (nestedOrderId != null) {
        return nestedOrderId;
      }
      continue;
    }
    final String? nestedAsString = _nonEmptyString(nested);
    if (nestedAsString != null) {
      return nestedAsString;
    }
  }

  return null;
}

String? _firstPayloadString(
  Map<String, Object?> payload,
  Iterable<String> keys,
) {
  for (final String key in keys) {
    final String? value = _nonEmptyString(payload[key]);
    if (value != null) {
      return value;
    }
  }
  return null;
}

Map<String, Object?>? _stringMap(Object? value) {
  if (value is! Map) {
    return null;
  }
  return <String, Object?>{
    for (final MapEntry<dynamic, dynamic> entry in value.entries)
      entry.key.toString(): entry.value,
  };
}

String? _nonEmptyString(Object? value) {
  final String stringValue = value?.toString().trim() ?? '';
  return stringValue.isEmpty ? null : stringValue;
}

String _normalizeRealtimeToken(String value) {
  return value.trim().toLowerCase().replaceAll(RegExp(r'[\s.\-]+'), '_');
}
