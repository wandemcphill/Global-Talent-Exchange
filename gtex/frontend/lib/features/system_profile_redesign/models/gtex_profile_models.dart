import 'package:flutter/foundation.dart';

@immutable
class GtexProfileSummary {
  const GtexProfileSummary({
    required this.userId,
    required this.displayName,
    required this.email,
    required this.roleLabel,
    required this.countryLabel,
    required this.clubName,
    required this.kycStatus,
    required this.walletStatus,
    required this.unreadNotifications,
    required this.openDisputes,
    required this.securityScore,
    required this.profileCompletion,
    this.avatarUrl,
  });

  final String userId;
  final String displayName;
  final String email;
  final String roleLabel;
  final String countryLabel;
  final String clubName;
  final String kycStatus;
  final String walletStatus;
  final int unreadNotifications;
  final int openDisputes;
  final int securityScore;
  final int profileCompletion;
  final String? avatarUrl;
}

@immutable
class GtexSettingSection {
  const GtexSettingSection({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.items,
  });

  final String id;
  final String title;
  final String subtitle;
  final List<GtexSettingItem> items;
}

@immutable
class GtexSettingItem {
  const GtexSettingItem({
    required this.id,
    required this.title,
    required this.description,
    required this.status,
    this.isDanger = false,
  });

  final String id;
  final String title;
  final String description;
  final String status;
  final bool isDanger;
}

enum GtexSystemStateKind {
  loading,
  empty,
  error,
  offline,
  accessDenied,
  maintenance,
  success,
}

@immutable
class GtexSystemStateSpec {
  const GtexSystemStateSpec({
    required this.kind,
    required this.title,
    required this.message,
    required this.primaryActionLabel,
    this.secondaryActionLabel,
  });

  final GtexSystemStateKind kind;
  final String title;
  final String message;
  final String primaryActionLabel;
  final String? secondaryActionLabel;
}
