import 'package:flutter/material.dart';

enum GtexNotificationKind {
  transfers,
  matches,
  market,
  traders,
  club,
  competition,
  regen,
  wallet,
  gifts,
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
      case GtexNotificationKind.transfers:
        return Icons.swap_horiz_outlined;
      case GtexNotificationKind.matches:
        return Icons.sports_soccer_outlined;
      case GtexNotificationKind.market:
        return Icons.shopping_basket_outlined;
      case GtexNotificationKind.traders:
        return Icons.currency_exchange_outlined;
      case GtexNotificationKind.club:
        return Icons.shield_outlined;
      case GtexNotificationKind.competition:
        return Icons.emoji_events_outlined;
      case GtexNotificationKind.regen:
        return Icons.auto_awesome_outlined;
      case GtexNotificationKind.wallet:
        return Icons.account_balance_wallet_outlined;
      case GtexNotificationKind.gifts:
        return Icons.card_giftcard_outlined;
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

  String get kindLabel {
    switch (kind) {
      case GtexNotificationKind.transfers:
        return 'TRANSFERS';
      case GtexNotificationKind.matches:
        return 'MATCHES';
      case GtexNotificationKind.market:
        return 'MARKET';
      case GtexNotificationKind.traders:
        return 'TRADERS';
      case GtexNotificationKind.club:
        return 'CLUB';
      case GtexNotificationKind.competition:
        return 'COMPETITIONS';
      case GtexNotificationKind.regen:
        return 'REGENS';
      case GtexNotificationKind.wallet:
        return 'WALLET';
      case GtexNotificationKind.gifts:
        return 'GIFTS';
      case GtexNotificationKind.kyc:
        return 'KYC';
      case GtexNotificationKind.dispute:
        return 'DISPUTES';
      case GtexNotificationKind.jackpot:
        return 'JACKPOT';
      case GtexNotificationKind.system:
        return 'SYSTEM';
    }
  }
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
    this.reactionCount = 0,
    this.commentCount = 0,
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
  final int reactionCount;
  final int commentCount;

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
