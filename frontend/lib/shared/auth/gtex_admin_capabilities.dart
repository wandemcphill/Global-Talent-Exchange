import '../../data/gte_models.dart';

/// Client-side mirror of the backend admin capability model
/// (`backend/app/admin/capabilities.py`).
///
/// The backend already resolves the *effective* capability list for a session
/// in `AuthService.resolve_user_permissions` -- including the super-admin
/// fallback set -- and returns it on the login payload. So the honest gate is
/// the session's own permission list; this type deliberately does not re-derive
/// capabilities from the role, which would risk drifting from the server.
///
/// This is a presentation guard only. The API remains the authority and still
/// returns 403; gating here stops the UI from advertising an action the
/// session cannot actually perform.
class GtexAdminCapabilities {
  const GtexAdminCapabilities._(this._granted, this._unchecked);

  /// Applies no gating. Used where a surface is mounted without a resolved
  /// session (tests, previews) so behaviour is unchanged rather than silently
  /// locked down.
  const GtexAdminCapabilities.unchecked()
    : _granted = const <String>{},
      _unchecked = true;

  factory GtexAdminCapabilities.fromSession(GteAuthSession? session) {
    final Iterable<String> raw = session?.permissions ?? const <String>[];
    return GtexAdminCapabilities._(
      raw
          .map((String value) => value.trim().toLowerCase())
          .where((String value) => value.isNotEmpty)
          .toSet(),
      false,
    );
  }

  /// Capability keys verified against the routers this app actually calls.
  static const String managePaymentRails = 'manage_payment_rails';
  static const String manageWithdrawals = 'manage_withdrawals';
  static const String manageCompetitions = 'manage_competitions';

  final Set<String> _granted;
  final bool _unchecked;

  bool allows(String capability) =>
      _unchecked || _granted.contains(capability.trim().toLowerCase());

  /// Copy for the "why is this disabled" affordance, so a scoped admin is told
  /// what they lack instead of meeting a silently dead control.
  static String blockedMessage(String capability) =>
      'This admin session does not carry the $capability permission '
      'required for this action.';
}
