import '../providers/gte_exchange_controller.dart';

class GteSessionIdentity {
  const GteSessionIdentity({
    required this.userId,
    this.userName,
    this.clubId,
    this.clubName,
  });

  final String userId;
  final String? userName;
  final String? clubId;
  final String? clubName;

  static GteSessionIdentity fromExchangeController(
    GteExchangeController controller, {
    String guestUserId = 'demo-user',
    String guestClubId = 'royal-lagos-fc',
    String guestClubName = 'Royal Lagos FC',
  }) {
    final String? trimmedSessionUserId = controller.session?.user.id.trim();
    final String resolvedUserId =
        trimmedSessionUserId != null && trimmedSessionUserId.isNotEmpty
            ? trimmedSessionUserId
            : guestUserId;
    final String? resolvedName = _resolvedUserName(controller);
    return GteSessionIdentity(
      userId: resolvedUserId,
      userName: resolvedName,
      clubId: trimmedSessionUserId != null && trimmedSessionUserId.isNotEmpty
          ? trimmedSessionUserId
          : guestClubId,
      clubName: resolvedName ?? guestClubName,
    );
  }

  static String? _resolvedUserName(GteExchangeController controller) {
    final String? displayName = controller.session?.user.displayName?.trim();
    if (displayName != null && displayName.isNotEmpty) {
      return displayName;
    }
    final String? username = controller.session?.user.username.trim();
    if (username != null && username.isNotEmpty) {
      return username;
    }
    return null;
  }
}
