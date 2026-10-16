class AuthPresentation {
  const AuthPresentation({
    required this.userName,
    required this.role,
    required this.clubName,
    required this.avatarAsset,
    required this.notifications,
  });

  final String userName;
  final String role;
  final String clubName;
  final String avatarAsset;
  final int notifications;
}
