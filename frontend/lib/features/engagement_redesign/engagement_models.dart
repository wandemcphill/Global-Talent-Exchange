import 'package:flutter/material.dart';

enum GtexNotificationKind {
  market,
  club,
  competition,
  regen,
  wallet,
  kyc,
  dispute,
  jackpot,
  system,
}

enum GtexNewsCategory {
  breaking,
  transfers,
  clubs,
  regens,
  awards,
  tournaments,
  nationalTeams,
  jackpot,
  market,
  creators,
  disputes,
}

enum GtexConversationKind {
  support,
  admin,
  club,
  order,
  dispute,
  player,
  creator,
}

class GtexNotificationItem {
  const GtexNotificationItem({
    required this.id,
    required this.title,
    required this.body,
    required this.kind,
    required this.createdAt,
    this.isRead = false,
    this.relatedLabel,
    this.actionLabel,
  });

  final String id;
  final String title;
  final String body;
  final GtexNotificationKind kind;
  final DateTime createdAt;
  final bool isRead;
  final String? relatedLabel;
  final String? actionLabel;

  IconData get icon {
    switch (kind) {
      case GtexNotificationKind.market:
        return Icons.shopping_basket_outlined;
      case GtexNotificationKind.club:
        return Icons.shield_outlined;
      case GtexNotificationKind.competition:
        return Icons.emoji_events_outlined;
      case GtexNotificationKind.regen:
        return Icons.auto_awesome_outlined;
      case GtexNotificationKind.wallet:
        return Icons.account_balance_wallet_outlined;
      case GtexNotificationKind.kyc:
        return Icons.verified_user_outlined;
      case GtexNotificationKind.dispute:
        return Icons.gavel_outlined;
      case GtexNotificationKind.jackpot:
        return Icons.workspace_premium_outlined;
      case GtexNotificationKind.system:
        return Icons.notifications_active_outlined;
    }
  }

  String get kindLabel => kind.name.toUpperCase();
}

class GtexConversation {
  const GtexConversation({
    required this.id,
    required this.title,
    required this.kind,
    required this.lastMessage,
    required this.updatedAt,
    this.unreadCount = 0,
    this.contextLabel,
    this.isEscalated = false,
  });

  final String id;
  final String title;
  final GtexConversationKind kind;
  final String lastMessage;
  final DateTime updatedAt;
  final int unreadCount;
  final String? contextLabel;
  final bool isEscalated;
}

class GtexChatMessage {
  const GtexChatMessage({
    required this.id,
    required this.sender,
    required this.message,
    required this.sentAt,
    this.isMine = false,
    this.system = false,
  });

  final String id;
  final String sender;
  final String message;
  final DateTime sentAt;
  final bool isMine;
  final bool system;
}

class GtexNewsArticle {
  const GtexNewsArticle({
    required this.id,
    required this.title,
    required this.summary,
    required this.body,
    required this.category,
    required this.publishedAt,
    this.heroLabel,
    this.relatedEntity,
    this.relatedRoute,
    this.shareUrl,
    this.isBreaking = false,
    this.trustScore = 0.92,
  });

  final String id;
  final String title;
  final String summary;
  final String body;
  final GtexNewsCategory category;
  final DateTime publishedAt;
  final String? heroLabel;
  final String? relatedEntity;
  final String? relatedRoute;
  final String? shareUrl;
  final bool isBreaking;
  final double trustScore;

  String get categoryLabel {
    switch (category) {
      case GtexNewsCategory.breaking:
        return 'BREAKING';
      case GtexNewsCategory.transfers:
        return 'TRANSFERS';
      case GtexNewsCategory.clubs:
        return 'CLUBS';
      case GtexNewsCategory.regens:
        return 'REGENS';
      case GtexNewsCategory.awards:
        return 'AWARDS';
      case GtexNewsCategory.tournaments:
        return 'TOURNAMENTS';
      case GtexNewsCategory.nationalTeams:
        return 'NATIONAL TEAMS';
      case GtexNewsCategory.jackpot:
        return 'JACKPOT';
      case GtexNewsCategory.market:
        return 'MARKET';
      case GtexNewsCategory.creators:
        return 'CREATORS';
      case GtexNewsCategory.disputes:
        return 'DISPUTES';
    }
  }
}

class GtexNewsroomQueueItem {
  const GtexNewsroomQueueItem({
    required this.id,
    required this.title,
    required this.status,
    required this.category,
    required this.updatedAt,
    this.riskLabel,
    this.audience = 'All users',
  });

  final String id;
  final String title;
  final String status;
  final GtexNewsCategory category;
  final DateTime updatedAt;
  final String? riskLabel;
  final String audience;
}
