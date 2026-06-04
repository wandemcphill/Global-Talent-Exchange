import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/gte_api_repository.dart';
import '../../../shared/state/gtex_async_surface_state.dart';
import '../data/squad_repository.dart';
import '../domain/squad_models.dart';

class SquadRequest {
  const SquadRequest({required this.clubId, this.role = 'club.owner'});

  final String clubId;
  final String role;

  bool get hasRecognisedRole {
    return switch (role.trim().toLowerCase()) {
      'club.owner' ||
      'owner' ||
      'club.manager' ||
      'manager' ||
      'club.scout' ||
      'scout' => true,
      _ => false,
    };
  }

  bool get canViewContracts {
    return switch (role.trim().toLowerCase()) {
      'club.owner' || 'owner' => true,
      _ => false,
    };
  }

  @override
  bool operator ==(Object other) {
    return other is SquadRequest &&
        other.clubId == clubId &&
        other.role == role;
  }

  @override
  int get hashCode => Object.hash(clubId, role);
}

final Provider<ISquadRepository> squadRepositoryProvider =
    Provider<ISquadRepository>((Ref ref) => BackendSquadRepository.standard());

final squadOperationsProvider = FutureProvider.autoDispose
    .family<GtexSurfaceState<SquadOperationsSnapshot>, SquadRequest>((
      Ref ref,
      SquadRequest request,
    ) async {
      if (!request.hasRecognisedRole) {
        return const GtexBlocked<SquadOperationsSnapshot>(
          reason: 'Role is not recognised for Squad access.',
        );
      }

      try {
        final SquadOperationsSnapshot snapshot = await ref
            .watch(squadRepositoryProvider)
            .fetchSquadOperations(request.clubId);
        return GtexData<SquadOperationsSnapshot>(data: snapshot);
      } on SquadRepositoryBlockedException catch (error) {
        return GtexBlocked<SquadOperationsSnapshot>(reason: error.reason);
      } on GteApiException catch (error) {
        return GtexError<SquadOperationsSnapshot>(
          code: error.type.name,
          message: error.message,
        );
      } catch (error) {
        return GtexError<SquadOperationsSnapshot>(
          code: 'squad_unknown',
          message: error.toString(),
        );
      }
    });

final squadSelectionReadyProvider = Provider.autoDispose
    .family<List<SquadPlayerDTO>, SquadRequest>((
      Ref ref,
      SquadRequest request,
    ) {
      return ref
          .watch(squadOperationsProvider(request))
          .when<List<SquadPlayerDTO>>(
            data: squadSelectionReadyFromState,
            loading: () => const <SquadPlayerDTO>[],
            error:
                (Object error, StackTrace stackTrace) =>
                    const <SquadPlayerDTO>[],
          );
    });

GtexSurfaceState<AvailabilityMatrix> squadAvailabilityMatrixSurfaceState(
  AvailabilityMatrix matrix,
) {
  if (!matrix.hasPlayers) {
    return const GtexEmpty<AvailabilityMatrix>(
      reason: 'No players in squad - availability matrix is empty.',
    );
  }
  return GtexData<AvailabilityMatrix>(data: matrix);
}

List<SquadPlayerDTO> squadSelectionReadyFromState(
  GtexSurfaceState<SquadOperationsSnapshot>? state,
) {
  final SquadOperationsSnapshot? snapshot = switch (state) {
    GtexData<SquadOperationsSnapshot>(:final data) => data,
    GtexConfirmed<SquadOperationsSnapshot>(:final data) => data,
    GtexSyncing<SquadOperationsSnapshot>(:final current) => current,
    GtexDegraded<SquadOperationsSnapshot>(:final current) => current,
    GtexReconnecting<SquadOperationsSnapshot>(:final lastKnown) => lastKnown,
    GtexPending<SquadOperationsSnapshot>(:final stale) => stale,
    _ => null,
  };
  if (snapshot == null) {
    return const <SquadPlayerDTO>[];
  }
  return snapshot.roster
      .where((SquadPlayerDTO player) => player.selectionReady)
      .toList(growable: false);
}

List<String> squadChemistryWarnings(SquadOperationsSnapshot snapshot) {
  return <String>[
        ...snapshot.chemistry.warnings,
        ...snapshot.roster.expand(
          (SquadPlayerDTO player) => player.chemistryFit.warnings,
        ),
      ]
      .where((String warning) => warning.trim().isNotEmpty)
      .toList(growable: false);
}

List<ContractStatusDTO> squadContractWarnings(
  SquadOperationsSnapshot snapshot,
) {
  final List<ContractStatusDTO> contracts =
      snapshot.contracts.isNotEmpty
          ? snapshot.contracts
          : snapshot.roster
              .map((SquadPlayerDTO player) => player.contractStatus)
              .toList(growable: false);
  return contracts
      .where((ContractStatusDTO contract) => contract.isRenewalRisk)
      .toList(growable: false);
}
