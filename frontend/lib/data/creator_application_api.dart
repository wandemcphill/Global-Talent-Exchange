import '../models/creator_application_models.dart';
import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';

class CreatorApplicationApi {
  CreatorApplicationApi({
    required this.client,
    required this.mode,
    _CreatorApplicationFixtureState? fixtureState,
  }) : _fixtureState = fixtureState ?? _CreatorApplicationFixtureState();

  final GteAuthedApi client;
  final GteBackendMode mode;
  final _CreatorApplicationFixtureState _fixtureState;

  factory CreatorApplicationApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
  }) {
    return CreatorApplicationApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: mode,
      ),
      mode: mode,
    );
  }

  factory CreatorApplicationApi.fixture() {
    return CreatorApplicationApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      mode: GteBackendMode.fixture,
    );
  }

  Future<CreatorContactVerificationStatus> fetchVerificationStatus() async {
    if (mode == GteBackendMode.fixture) {
      return _fixtureState.verification;
    }
    final Map<String, dynamic> payload = await client.getMap(
      '/api/auth/me',
      auth: true,
    );
    return CreatorContactVerificationStatus.fromCurrentUserJson(payload);
  }

  Future<CreatorContactVerificationStatus> verifyEmail() async {
    if (mode == GteBackendMode.fixture) {
      return _fixtureState.verifyEmail();
    }
    final Object? payload = await client.request(
      'POST',
      '/api/creator/verify-email',
      auth: true,
    );
    return CreatorContactVerificationStatus.fromJson(payload);
  }

  Future<CreatorContactVerificationStatus> verifyPhone() async {
    if (mode == GteBackendMode.fixture) {
      return _fixtureState.verifyPhone();
    }
    final Object? payload = await client.request(
      'POST',
      '/api/creator/verify-phone',
      auth: true,
    );
    return CreatorContactVerificationStatus.fromJson(payload);
  }

  Future<CreatorApplicationView?> fetchMyApplication() async {
    if (mode == GteBackendMode.fixture) {
      return _fixtureState.application;
    }
    final Object? payload = await client.request(
      'GET',
      '/api/creator/application',
      auth: true,
    );
    if (payload == null) {
      return null;
    }
    return CreatorApplicationView.fromJson(payload);
  }

  Future<CreatorApplicationView> submitApplication(
    CreatorApplicationSubmitRequest request,
  ) async {
    if (mode == GteBackendMode.fixture) {
      return _fixtureState.submitApplication(request);
    }
    final Object? payload = await client.request(
      'POST',
      '/api/creator/apply',
      auth: true,
      body: request.toJson(),
    );
    return CreatorApplicationView.fromJson(payload);
  }
}

class _CreatorApplicationFixtureState {
  CreatorContactVerificationStatus verification =
      const CreatorContactVerificationStatus(
    userId: 'fixture-user',
  );
  CreatorApplicationView? application;

  CreatorContactVerificationStatus verifyEmail() {
    final DateTime now = DateTime.now().toUtc();
    verification = verification.copyWith(emailVerifiedAt: now);
    if (application != null) {
      application = application!.copyWith(
        emailVerifiedAt: now,
        updatedAt: now,
      );
    }
    return verification;
  }

  CreatorContactVerificationStatus verifyPhone() {
    final DateTime now = DateTime.now().toUtc();
    verification = verification.copyWith(phoneVerifiedAt: now);
    if (application != null) {
      application = application!.copyWith(
        phoneVerifiedAt: now,
        updatedAt: now,
      );
    }
    return verification;
  }

  CreatorApplicationView submitApplication(
    CreatorApplicationSubmitRequest request,
  ) {
    if (!verification.isEmailVerified) {
      throw const GteApiException(
        type: GteApiErrorType.validation,
        message: 'email_verification_required',
      );
    }
    if (!verification.isPhoneVerified) {
      throw const GteApiException(
        type: GteApiErrorType.validation,
        message: 'phone_verification_required',
      );
    }
    if (application != null && application!.isApproved) {
      throw const GteApiException(
        type: GteApiErrorType.validation,
        message: 'creator_application_already_approved',
      );
    }
    final DateTime now = DateTime.now().toUtc();
    application = CreatorApplicationView(
      applicationId:
          application?.applicationId ?? 'fixture-creator-application',
      userId: verification.userId ?? 'fixture-user',
      requestedHandle: request.requestedHandle.trim().toLowerCase(),
      displayName: request.displayName.trim(),
      platform: request.platform.trim().toLowerCase(),
      followerCount: request.followerCount,
      socialLinks: request.socialLinks
          .map((String item) => item.trim())
          .where((String item) => item.isNotEmpty)
          .toList(growable: false),
      emailVerifiedAt: verification.emailVerifiedAt,
      phoneVerifiedAt: verification.phoneVerifiedAt,
      status: 'pending',
      createdAt: application?.createdAt ?? now,
      updatedAt: now,
      reviewNotes: null,
      decisionReason: null,
      reviewedByUserId: null,
      reviewedAt: null,
      verificationRequestedAt: null,
      approvedAt: null,
      rejectedAt: null,
      provisioning: null,
    );
    return application!;
  }
}
