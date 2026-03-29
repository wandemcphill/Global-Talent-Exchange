class AuthSession {
  const AuthSession({
    required this.userId,
    required this.accessToken,
    required this.sessionId,
  });

  final String userId;
  final String accessToken;
  final String sessionId;

  factory AuthSession.fromJson(Map<String, Object?> json) {
    return AuthSession(
      userId: (json['user_id'] ?? json['userId'] ?? '').toString(),
      accessToken:
          (json['access_token'] ?? json['accessToken'] ?? '').toString(),
      sessionId: (json['session_id'] ?? json['sessionId'] ?? '').toString(),
    );
  }

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'user_id': userId,
      'access_token': accessToken,
      'session_id': sessionId,
    };
  }
}
