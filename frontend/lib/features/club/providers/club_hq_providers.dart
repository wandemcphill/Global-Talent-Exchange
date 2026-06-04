import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/gte_api_repository.dart';
import '../../../shared/state/gtex_async_surface_state.dart';
import '../data/club_hq_repository.dart';
import '../domain/club_hq_models.dart';

class ClubHqRequest {
  const ClubHqRequest({required this.clubId, this.role = 'club.owner'});

  final String clubId;
  final String role;

  ClubHqRole? get resolvedRole => clubHqRoleFromRaw(role);

  @override
  bool operator ==(Object other) {
    return other is ClubHqRequest &&
        other.clubId == clubId &&
        other.role == role;
  }

  @override
  int get hashCode => Object.hash(clubId, role);
}

final Provider<IClubHqRepository> clubHqRepositoryProvider =
    Provider<IClubHqRepository>(
      (Ref ref) => BackendClubHqRepository.standard(),
    );

final clubHqProvider = FutureProvider.autoDispose
    .family<GtexSurfaceState<ClubHqSnapshot>, ClubHqRequest>((
      Ref ref,
      ClubHqRequest request,
    ) async {
      final ClubHqRole? role = request.resolvedRole;
      if (role == null) {
        return const GtexBlocked<ClubHqSnapshot>(
          reason: 'Role is not recognised for Club HQ access.',
        );
      }

      try {
        final ClubHqSnapshot snapshot = await ref
            .watch(clubHqRepositoryProvider)
            .fetchClubHq(request.clubId);
        if (!snapshot.isConfigured) {
          return const GtexEmpty<ClubHqSnapshot>(
            reason: 'Club profile not yet configured.',
          );
        }
        return GtexData<ClubHqSnapshot>(data: snapshot);
      } on ClubHqRepositoryBlockedException catch (error) {
        return GtexBlocked<ClubHqSnapshot>(reason: error.reason);
      } on GteApiException catch (error) {
        return GtexError<ClubHqSnapshot>(
          code: error.type.name,
          message: error.message,
        );
      } catch (error) {
        return GtexError<ClubHqSnapshot>(
          code: 'club_hq_unknown',
          message: error.toString(),
        );
      }
    });

final clubFinanceProvider = FutureProvider.autoDispose
    .family<GtexSurfaceState<ClubFinanceDTO>, ClubHqRequest>((
      Ref ref,
      ClubHqRequest request,
    ) async {
      final ClubHqRole? role = request.resolvedRole;
      if (role == null) {
        return const GtexBlocked<ClubFinanceDTO>(
          reason: 'Role is not recognised for Club HQ access.',
        );
      }
      if (!role.canViewFinance) {
        return const GtexBlocked<ClubFinanceDTO>(
          reason: 'Finance is restricted to club owners.',
        );
      }

      try {
        final ClubFinanceDTO finance = await ref
            .watch(clubHqRepositoryProvider)
            .getFinance(request.clubId);
        return clubFinanceSurfaceState(finance);
      } on ClubHqRepositoryBlockedException catch (error) {
        return GtexBlocked<ClubFinanceDTO>(reason: error.reason);
      } on GteApiException catch (error) {
        return GtexError<ClubFinanceDTO>(
          code: error.type.name,
          message: error.message,
        );
      } catch (error) {
        return GtexError<ClubFinanceDTO>(
          code: 'club_finance_unknown',
          message: error.toString(),
        );
      }
    });

GtexSurfaceState<ClubFinanceDTO> clubFinanceSurfaceState(
  ClubFinanceDTO finance,
) {
  if (!finance.hasBackendBalance) {
    return const GtexBlocked<ClubFinanceDTO>(
      reason: 'Balance data unavailable - sync in progress.',
    );
  }
  return GtexData<ClubFinanceDTO>(data: finance);
}

GtexSurfaceState<List<ClubRankingDTO>> clubRankingsSurfaceState(
  List<ClubRankingDTO> rankings,
) {
  if (rankings.isEmpty) {
    return const GtexEmpty<List<ClubRankingDTO>>(
      reason: 'Club rankings are not available from the backend yet.',
    );
  }
  return GtexData<List<ClubRankingDTO>>(data: rankings);
}
