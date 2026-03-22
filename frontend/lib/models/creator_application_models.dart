import '../data/gte_models.dart';

class CreatorApplicationSubmitRequest {
  const CreatorApplicationSubmitRequest({
    required this.requestedHandle,
    required this.displayName,
    required this.platform,
    required this.followerCount,
    required this.socialLinks,
  });

  final String requestedHandle;
  final String displayName;
  final String platform;
  final int followerCount;
  final List<String> socialLinks;

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'requested_handle': requestedHandle.trim().toLowerCase(),
      'display_name': displayName.trim(),
      'platform': platform.trim().toLowerCase(),
      'follower_count': followerCount,
      'social_links': socialLinks
          .map((String item) => item.trim())
          .where((String item) => item.isNotEmpty)
          .toList(growable: false),
    };
  }
}

class CreatorContactVerificationStatus {
  const CreatorContactVerificationStatus({
    this.userId,
    this.emailVerifiedAt,
    this.phoneVerifiedAt,
  });

  final String? userId;
  final DateTime? emailVerifiedAt;
  final DateTime? phoneVerifiedAt;

  bool get isEmailVerified => emailVerifiedAt != null;

  bool get isPhoneVerified => phoneVerifiedAt != null;

  CreatorContactVerificationStatus copyWith({
    String? userId,
    DateTime? emailVerifiedAt,
    DateTime? phoneVerifiedAt,
    bool keepEmailVerifiedAt = true,
    bool keepPhoneVerifiedAt = true,
  }) {
    return CreatorContactVerificationStatus(
      userId: userId ?? this.userId,
      emailVerifiedAt: keepEmailVerifiedAt
          ? (emailVerifiedAt ?? this.emailVerifiedAt)
          : null,
      phoneVerifiedAt: keepPhoneVerifiedAt
          ? (phoneVerifiedAt ?? this.phoneVerifiedAt)
          : null,
    );
  }

  factory CreatorContactVerificationStatus.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'creator contact verification');
    return CreatorContactVerificationStatus(
      userId: GteJson.stringOrNull(json, <String>['user_id', 'userId']),
      emailVerifiedAt: GteJson.dateTimeOrNull(
          json, <String>['email_verified_at', 'emailVerifiedAt']),
      phoneVerifiedAt: GteJson.dateTimeOrNull(
          json, <String>['phone_verified_at', 'phoneVerifiedAt']),
    );
  }

  factory CreatorContactVerificationStatus.fromCurrentUserJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'current user verification');
    return CreatorContactVerificationStatus(
      userId: GteJson.stringOrNull(json, <String>['id']),
      emailVerifiedAt: GteJson.dateTimeOrNull(
          json, <String>['email_verified_at', 'emailVerifiedAt']),
      phoneVerifiedAt: GteJson.dateTimeOrNull(
          json, <String>['phone_verified_at', 'phoneVerifiedAt']),
    );
  }
}

class CreatorProvisioningView {
  const CreatorProvisioningView({
    required this.creatorProfileId,
    required this.clubId,
    required this.stadiumId,
    required this.creatorSquadId,
    required this.creatorRegenId,
    required this.provisionStatus,
  });

  final String creatorProfileId;
  final String clubId;
  final String stadiumId;
  final String creatorSquadId;
  final String creatorRegenId;
  final String provisionStatus;

  factory CreatorProvisioningView.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'creator provisioning');
    return CreatorProvisioningView(
      creatorProfileId: GteJson.string(
          json, <String>['creator_profile_id', 'creatorProfileId']),
      clubId: GteJson.string(json, <String>['club_id', 'clubId']),
      stadiumId: GteJson.string(json, <String>['stadium_id', 'stadiumId']),
      creatorSquadId:
          GteJson.string(json, <String>['creator_squad_id', 'creatorSquadId']),
      creatorRegenId:
          GteJson.string(json, <String>['creator_regen_id', 'creatorRegenId']),
      provisionStatus: GteJson.string(
          json, <String>['provision_status', 'provisionStatus'],
          fallback: 'active'),
    );
  }
}

class CreatorApplicationView {
  const CreatorApplicationView({
    required this.applicationId,
    required this.userId,
    required this.requestedHandle,
    required this.displayName,
    required this.platform,
    required this.followerCount,
    required this.socialLinks,
    required this.emailVerifiedAt,
    required this.phoneVerifiedAt,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    this.reviewNotes,
    this.decisionReason,
    this.reviewedByUserId,
    this.reviewedAt,
    this.verificationRequestedAt,
    this.approvedAt,
    this.rejectedAt,
    this.provisioning,
  });

  final String applicationId;
  final String userId;
  final String requestedHandle;
  final String displayName;
  final String platform;
  final int followerCount;
  final List<String> socialLinks;
  final DateTime? emailVerifiedAt;
  final DateTime? phoneVerifiedAt;
  final String status;
  final String? reviewNotes;
  final String? decisionReason;
  final String? reviewedByUserId;
  final DateTime? reviewedAt;
  final DateTime? verificationRequestedAt;
  final DateTime? approvedAt;
  final DateTime? rejectedAt;
  final DateTime createdAt;
  final DateTime updatedAt;
  final CreatorProvisioningView? provisioning;

  bool get isApproved => status == 'approved';

  bool get isPending => status == 'pending';

  bool get needsVerificationUpdate => status == 'verification_requested';

  bool get isRejected => status == 'rejected';

  bool get canResubmit => needsVerificationUpdate || isRejected;

  CreatorApplicationView copyWith({
    DateTime? emailVerifiedAt,
    DateTime? phoneVerifiedAt,
    String? status,
    String? reviewNotes,
    String? decisionReason,
    String? reviewedByUserId,
    DateTime? reviewedAt,
    DateTime? verificationRequestedAt,
    DateTime? approvedAt,
    DateTime? rejectedAt,
    DateTime? updatedAt,
    CreatorProvisioningView? provisioning,
  }) {
    return CreatorApplicationView(
      applicationId: applicationId,
      userId: userId,
      requestedHandle: requestedHandle,
      displayName: displayName,
      platform: platform,
      followerCount: followerCount,
      socialLinks: socialLinks,
      emailVerifiedAt: emailVerifiedAt ?? this.emailVerifiedAt,
      phoneVerifiedAt: phoneVerifiedAt ?? this.phoneVerifiedAt,
      status: status ?? this.status,
      reviewNotes: reviewNotes ?? this.reviewNotes,
      decisionReason: decisionReason ?? this.decisionReason,
      reviewedByUserId: reviewedByUserId,
      reviewedAt: reviewedAt ?? this.reviewedAt,
      verificationRequestedAt:
          verificationRequestedAt ?? this.verificationRequestedAt,
      approvedAt: approvedAt ?? this.approvedAt,
      rejectedAt: rejectedAt ?? this.rejectedAt,
      createdAt: createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      provisioning: provisioning ?? this.provisioning,
    );
  }

  factory CreatorApplicationView.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'creator application');
    return CreatorApplicationView(
      applicationId:
          GteJson.string(json, <String>['application_id', 'applicationId']),
      userId: GteJson.string(json, <String>['user_id', 'userId']),
      requestedHandle:
          GteJson.string(json, <String>['requested_handle', 'requestedHandle']),
      displayName:
          GteJson.string(json, <String>['display_name', 'displayName']),
      platform: GteJson.string(json, <String>['platform']),
      followerCount:
          GteJson.integer(json, <String>['follower_count', 'followerCount']),
      socialLinks: GteJson.typedList<String>(
        json,
        <String>['social_links', 'socialLinks'],
        (Object? value) => value.toString(),
      ),
      emailVerifiedAt: GteJson.dateTimeOrNull(
          json, <String>['email_verified_at', 'emailVerifiedAt']),
      phoneVerifiedAt: GteJson.dateTimeOrNull(
          json, <String>['phone_verified_at', 'phoneVerifiedAt']),
      status: GteJson.string(json, <String>['status'], fallback: 'pending'),
      reviewNotes:
          GteJson.stringOrNull(json, <String>['review_notes', 'reviewNotes']),
      decisionReason: GteJson.stringOrNull(
          json, <String>['decision_reason', 'decisionReason']),
      reviewedByUserId: GteJson.stringOrNull(
          json, <String>['reviewed_by_user_id', 'reviewedByUserId']),
      reviewedAt:
          GteJson.dateTimeOrNull(json, <String>['reviewed_at', 'reviewedAt']),
      verificationRequestedAt: GteJson.dateTimeOrNull(json,
          <String>['verification_requested_at', 'verificationRequestedAt']),
      approvedAt:
          GteJson.dateTimeOrNull(json, <String>['approved_at', 'approvedAt']),
      rejectedAt:
          GteJson.dateTimeOrNull(json, <String>['rejected_at', 'rejectedAt']),
      createdAt: GteJson.dateTimeOrNull(
            json,
            <String>['created_at', 'createdAt'],
          ) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      updatedAt: GteJson.dateTimeOrNull(
            json,
            <String>['updated_at', 'updatedAt'],
          ) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      provisioning: GteJson.value(json, <String>['provisioning']) == null
          ? null
          : CreatorProvisioningView.fromJson(
              GteJson.value(json, <String>['provisioning']),
            ),
    );
  }
}
