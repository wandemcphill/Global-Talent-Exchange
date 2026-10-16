import 'package:flutter/foundation.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/community_api.dart';

class CreatorClubFollowController extends ChangeNotifier {
  CreatorClubFollowController({
    required CommunityApi api,
    required String clubId,
    required bool isAuthenticated,
  }) : _api = api,
       clubId = clubId.trim(),
       _isAuthenticated = isAuthenticated;

  final CommunityApi _api;
  final String clubId;
  final bool _isAuthenticated;

  bool isLoading = false;
  bool isUpdating = false;
  bool? isFollowing;
  String? errorMessage;

  bool get isAuthenticated => _isAuthenticated;

  Future<void> load() async {
    if (!_isAuthenticated || clubId.isEmpty) {
      isFollowing = null;
      errorMessage = null;
      notifyListeners();
      return;
    }
    isLoading = true;
    errorMessage = null;
    notifyListeners();
    try {
      isFollowing = await _api.fetchCreatorClubFollowing(clubId: clubId);
    } catch (error) {
      isFollowing = null;
      errorMessage = AppFeedback.messageFor(error);
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  Future<bool?> toggleFollow() async {
    if (!_isAuthenticated || clubId.isEmpty || isUpdating) {
      return isFollowing;
    }
    final bool nextValue = !(isFollowing ?? false);
    isUpdating = true;
    errorMessage = null;
    notifyListeners();
    try {
      if (nextValue) {
        await _api.followCreatorClub(clubId: clubId);
      } else {
        await _api.unfollowCreatorClub(clubId: clubId);
      }
      isFollowing = nextValue;
      return isFollowing;
    } catch (error) {
      errorMessage = AppFeedback.messageFor(error);
      return null;
    } finally {
      isUpdating = false;
      notifyListeners();
    }
  }
}
