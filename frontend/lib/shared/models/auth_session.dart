class AuthSession {
  const AuthSession({
    required this.userName,
    required this.role,
    required this.clubName,
    required this.avatarAsset,
    required this.notifications,
    this.accessToken,
  });

  final String userName;
  final String role;
  final String clubName;
  final String avatarAsset;
  final int notifications;
  final String? accessToken;
}
