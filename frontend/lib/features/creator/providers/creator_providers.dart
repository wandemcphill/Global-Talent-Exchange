import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../shared/providers/auth_provider.dart';
import '../data/creator_dtos.dart';
import '../data/creator_repository.dart';

final Provider<ICreatorRepository> creatorRepositoryProvider =
    Provider<ICreatorRepository>((Ref ref) {
      return CreatorApiRepository(client: ref.watch(authedApiProvider));
    });

final FutureProvider<CreatorSurfaceState<CreatorProfileDto>>
creatorProfileProvider = FutureProvider<CreatorSurfaceState<CreatorProfileDto>>(
  (Ref ref) {
    return ref.watch(creatorRepositoryProvider).getProfile();
  },
);

final StreamProvider<CreatorSurfaceState<List<CampaignDto>>>
creatorCampaignsProvider =
    StreamProvider<CreatorSurfaceState<List<CampaignDto>>>((Ref ref) async* {
      yield await ref.watch(creatorRepositoryProvider).getCampaigns();
    });

final campaignDetailProvider =
    FutureProvider.family<CreatorSurfaceState<CampaignDto>, String>((
      Ref ref,
      String id,
    ) {
      return ref.watch(creatorRepositoryProvider).getCampaignDetail(id);
    });

final StreamProvider<CreatorSurfaceState<List<SponsoredClipDto>>>
creatorClipsProvider =
    StreamProvider<CreatorSurfaceState<List<SponsoredClipDto>>>((
      Ref ref,
    ) async* {
      yield await ref.watch(creatorRepositoryProvider).getClips();
    });

final creatorAnalyticsProvider = FutureProvider.family<
  CreatorSurfaceState<CreatorAnalyticsDto>,
  AnalyticsPeriod
>((Ref ref, AnalyticsPeriod period) {
  return ref.watch(creatorRepositoryProvider).getAnalytics(period);
});

final StreamProvider<CreatorSurfaceState<CreatorWalletDto>>
creatorWalletProvider = StreamProvider<CreatorSurfaceState<CreatorWalletDto>>((
  Ref ref,
) async* {
  yield await ref.watch(creatorRepositoryProvider).getWallet();
});

final StreamProvider<CreatorSurfaceState<List<SettlementDto>>>
creatorSettlementsProvider =
    StreamProvider<CreatorSurfaceState<List<SettlementDto>>>((Ref ref) async* {
      yield await ref.watch(creatorRepositoryProvider).getSettlements();
    });

final StreamProvider<CreatorSurfaceState<List<ModerationInboxItemDto>>>
creatorModerationProvider =
    StreamProvider<CreatorSurfaceState<List<ModerationInboxItemDto>>>((
      Ref ref,
    ) async* {
      yield await ref.watch(creatorRepositoryProvider).getModerationInbox();
    });
