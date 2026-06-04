import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/gte_authed_api.dart';
import '../../features/shared/data/gte_feature_support.dart';
import '../../shared/models/auth_session.dart';
import '../../shared/providers/auth_provider.dart';

class AdminImportProviderNameController extends Notifier<String> {
  @override
  String build() => 'football_data';

  void setProviderName(String value) {
    state = value.trim().isEmpty ? 'football_data' : value.trim();
  }
}

class AdminSelectedBatchController extends Notifier<String?> {
  @override
  String? build() => null;

  void select(String? batchId) {
    final String? normalized = batchId?.trim();
    state = normalized == null || normalized.isEmpty ? null : normalized;
  }
}

class ProfileData {
  const ProfileData({
    required this.authenticated,
    required this.user,
    required this.affinityProfile,
    required this.club,
    required this.followers,
    required this.following,
  });

  const ProfileData.unauthenticated()
    : authenticated = false,
      user = const <String, Object?>{},
      affinityProfile = const <String, Object?>{},
      club = null,
      followers = 0,
      following = 0;

  final bool authenticated;
  final JsonMap user;
  final JsonMap affinityProfile;
  final JsonMap? club;
  final int followers;
  final int following;
}

class AdminImportOverviewData {
  const AdminImportOverviewData({
    required this.providerName,
    required this.health,
    required this.status,
    required this.batches,
    required this.selectedBatch,
    required this.selectedBatchIssues,
    required this.selectedBatchValuation,
  });

  final String providerName;
  final JsonMap health;
  final JsonMap status;
  final List<JsonMap> batches;
  final JsonMap? selectedBatch;
  final List<JsonMap> selectedBatchIssues;
  final JsonMap? selectedBatchValuation;
}

final NotifierProvider<AdminImportProviderNameController, String>
adminImportProviderNameProvider =
    NotifierProvider<AdminImportProviderNameController, String>(
      AdminImportProviderNameController.new,
    );

final NotifierProvider<AdminSelectedBatchController, String?>
adminSelectedBatchIdProvider =
    NotifierProvider<AdminSelectedBatchController, String?>(
      AdminSelectedBatchController.new,
    );

final FutureProvider<ProfileData> profileDataProvider =
    FutureProvider<ProfileData>((Ref ref) async {
      final bool authenticated = ref.watch(isAuthenticatedProvider);
      if (!authenticated) {
        return const ProfileData.unauthenticated();
      }
      final GteAuthedApi api = ref.watch(authedApiProvider);
      final JsonMap me = await api.getMap('/api/v2/auth/me');
      final JsonMap user = await api.getMap('/users/me');
      final JsonMap affinity = await api.getMap('/users/me/profile');
      final String userId = stringValue(
        me['id'],
        fallback: stringValue(user['id']),
      );
      int followers = 0;
      int following = 0;
      try {
        final JsonMap followersPayload = await api.getMap(
          '/users/$userId/followers',
          auth: false,
        );
        followers = intValue(followersPayload['total']);
      } catch (_) {}
      try {
        final JsonMap followingPayload = await api.getMap(
          '/users/$userId/following',
          auth: false,
        );
        following = intValue(followingPayload['total']);
      } catch (_) {}
      final ClubContext? clubContext = ref.watch(clubContextProvider);
      JsonMap? club;
      if (clubContext != null) {
        try {
          club = await api.getMap('/clubs/${clubContext.id}', auth: false);
        } catch (_) {}
      }
      return ProfileData(
        authenticated: true,
        user: <String, Object?>{...user, ...me},
        affinityProfile: affinity,
        club: club,
        followers: followers,
        following: following,
      );
    });

final FutureProvider<AdminImportOverviewData>
adminImportOverviewProvider = FutureProvider<AdminImportOverviewData>((
  Ref ref,
) async {
  final GteAuthedApi api = ref.watch(authedApiProvider);
  final String providerName = ref.watch(adminImportProviderNameProvider);
  final String? selectedBatchId = ref.watch(adminSelectedBatchIdProvider);
  final JsonMap health = await api.getMap(
    '/internal/ingestion/providers/$providerName/health',
  );
  final JsonMap status = await api.getMap(
    '/internal/ingestion/real-players/status',
    query: <String, Object?>{'provider_name': providerName},
  );
  final List<JsonMap> batches = (await api.getList(
        '/internal/ingestion/real-players/batches',
        query: <String, Object?>{'provider_name': providerName},
      ))
      .map((dynamic item) => jsonMap(item, label: 'import batch'))
      .toList(growable: false);
  JsonMap? selectedBatch;
  List<JsonMap> issues = const <JsonMap>[];
  JsonMap? valuation;
  if (selectedBatchId != null && selectedBatchId.trim().isNotEmpty) {
    selectedBatch = await api.getMap(
      '/internal/ingestion/real-players/batches/$selectedBatchId',
    );
    issues = (await api.getList(
          '/internal/ingestion/real-players/batches/$selectedBatchId/issues',
        ))
        .map((dynamic item) => jsonMap(item, label: 'batch issue'))
        .toList(growable: false);
    valuation = await api.getMap(
      '/internal/ingestion/real-players/batches/$selectedBatchId/valuation-status',
    );
  }
  return AdminImportOverviewData(
    providerName: providerName,
    health: health,
    status: status,
    batches: batches,
    selectedBatch: selectedBatch,
    selectedBatchIssues: issues,
    selectedBatchValuation: valuation,
  );
});
