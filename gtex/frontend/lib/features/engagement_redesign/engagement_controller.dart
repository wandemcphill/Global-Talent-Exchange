import 'engagement_models.dart';

class GtexEngagementController {
  GtexEngagementController();

  List<GtexNotificationItem> loadDemoNotifications() {
    final DateTime now = DateTime.now();
    return <GtexNotificationItem>[
      GtexNotificationItem(
        id: 'n1',
        title: 'Shortlist total changed',
        body: 'Three Arsenal players in your basket moved by +4.2% since your last visit. Review your basket before purchase.',
        kind: GtexNotificationKind.market,
        createdAt: now.subtract(const Duration(minutes: 12)),
        relatedLabel: 'Player Market',
        actionLabel: 'Review basket',
      ),
      GtexNotificationItem(
        id: 'n2',
        title: 'KYC review requested',
        body: 'Compliance needs one clearer address document before withdrawals can be enabled.',
        kind: GtexNotificationKind.kyc,
        createdAt: now.subtract(const Duration(hours: 1)),
        relatedLabel: 'Wallet/KYC',
        actionLabel: 'Upload document',
      ),
      GtexNotificationItem(
        id: 'n3',
        title: 'GTEX U20 World Cup rental pool open',
        body: 'Nigeria, England, Ghana and Brazil eligible rental pools are now open for short-term national-team competition entries.',
        kind: GtexNotificationKind.competition,
        createdAt: now.subtract(const Duration(hours: 3)),
        isRead: true,
        relatedLabel: 'National Teams',
        actionLabel: 'Browse rentals',
      ),
      GtexNotificationItem(
        id: 'n4',
        title: 'Regen contract response',
        body: 'Kaito Mensah accepted your performance-bonus structure but wants a higher release clause.',
        kind: GtexNotificationKind.regen,
        createdAt: now.subtract(const Duration(hours: 5)),
        relatedLabel: 'Regen World',
        actionLabel: 'Open contract',
      ),
      GtexNotificationItem(
        id: 'n5',
        title: 'Jackpot winner announced',
        body: 'A GTEX user won the weekly football market jackpot after a live cup final result.',
        kind: GtexNotificationKind.jackpot,
        createdAt: now.subtract(const Duration(days: 1)),
        isRead: true,
        relatedLabel: 'Jackpot',
        actionLabel: 'View story',
      ),
    ];
  }

  List<GtexConversation> loadDemoConversations() {
    final DateTime now = DateTime.now();
    return <GtexConversation>[
      GtexConversation(
        id: 'c1',
        title: 'Admin Support — KYC Review',
        kind: GtexConversationKind.admin,
        lastMessage: 'Please upload a sharper address document and we will complete the review.',
        updatedAt: now.subtract(const Duration(minutes: 7)),
        unreadCount: 2,
        contextLabel: 'KYC #KYC-2184',
        isEscalated: true,
      ),
      GtexConversation(
        id: 'c2',
        title: 'Order Desk — Arsenal shortlist',
        kind: GtexConversationKind.order,
        lastMessage: 'Your shortlist basket is reserved for 18 minutes while pricing is refreshed.',
        updatedAt: now.subtract(const Duration(hours: 1)),
        contextLabel: 'Order #ORD-9231',
      ),
      GtexConversation(
        id: 'c3',
        title: 'Club Share Support',
        kind: GtexConversationKind.club,
        lastMessage: 'The public club share purchase was confirmed and added to your portfolio.',
        updatedAt: now.subtract(const Duration(hours: 4)),
        contextLabel: 'Club: Lagos Galaxy',
      ),
      GtexConversation(
        id: 'c4',
        title: 'Dispute Desk',
        kind: GtexConversationKind.dispute,
        lastMessage: 'Evidence received. Admin review is scheduled for the next operations window.',
        updatedAt: now.subtract(const Duration(days: 1)),
        contextLabel: 'DSP-1193',
      ),
    ];
  }

  List<GtexChatMessage> loadDemoMessages(String conversationId) {
    final DateTime now = DateTime.now();
    return <GtexChatMessage>[
      GtexChatMessage(
        id: 'm1',
        sender: 'GTEX System',
        message: 'Conversation linked to $conversationId. All actions are recorded for audit.',
        sentAt: now.subtract(const Duration(hours: 2)),
        system: true,
      ),
      GtexChatMessage(
        id: 'm2',
        sender: 'GTEX Admin',
        message: 'We reviewed the case. Please confirm whether the club wallet transaction was initiated by you.',
        sentAt: now.subtract(const Duration(minutes: 44)),
      ),
      GtexChatMessage(
        id: 'm3',
        sender: 'You',
        message: 'Yes, I initiated the transaction, but the order status did not update after payment.',
        sentAt: now.subtract(const Duration(minutes: 18)),
        isMine: true,
      ),
      GtexChatMessage(
        id: 'm4',
        sender: 'GTEX Admin',
        message: 'Understood. We are matching payment confirmation to the player order and will update the timeline here.',
        sentAt: now.subtract(const Duration(minutes: 6)),
      ),
    ];
  }

  List<GtexNewsArticle> loadDemoArticles() {
    final DateTime now = DateTime.now();
    return <GtexNewsArticle>[
      GtexNewsArticle(
        id: 'a1',
        title: 'Lagos Galaxy build a title-ready shortlist from England',
        summary: 'A newly formed club has added four Premier League players to a live GTEX shortlist basket.',
        body: 'Lagos Galaxy are moving aggressively in the GTEX player market. Sources inside the platform indicate the club is browsing by country, league, division and club, with Arsenal players currently sitting at the top of its shortlist basket. The total basket cost is visible to the owner and will continue to update as player values move.',
        category: GtexNewsCategory.transfers,
        publishedAt: now.subtract(const Duration(minutes: 22)),
        heroLabel: 'Market Watch',
        relatedEntity: 'Lagos Galaxy',
        isBreaking: true,
        trustScore: 0.96,
      ),
      GtexNewsArticle(
        id: 'a2',
        title: 'Regen World celebrates new teenage playmaker',
        summary: 'A 16-year-old regen from Ghana enters the weekly awards shortlist after a standout tournament run.',
        body: 'The GTEX regen universe continues to grow. Kaito Mensah, a creative midfielder with a high ambition profile, is now being tracked by multiple user-created clubs. His representatives are expected to request a performance-based contract with a protected release clause.',
        category: GtexNewsCategory.regens,
        publishedAt: now.subtract(const Duration(hours: 2)),
        heroLabel: 'Regen Breakthrough',
        relatedEntity: 'Kaito Mensah',
        trustScore: 0.91,
      ),
      GtexNewsArticle(
        id: 'a3',
        title: 'GTEX U20 World Cup rental pools open for national squads',
        summary: 'Eligible real players and pre-seeded regens are now available for national team rental baskets.',
        body: 'National team competition entries have opened, with countries now able to mix real players and pre-seeded regens when player supply is low. Rentals are available through the national team rental screen, where users can build a squad basket and review total rental cost before payment.',
        category: GtexNewsCategory.nationalTeams,
        publishedAt: now.subtract(const Duration(hours: 4)),
        heroLabel: 'National Teams',
        relatedEntity: 'GTEX U20 World Cup',
        trustScore: 0.94,
      ),
      GtexNewsArticle(
        id: 'a4',
        title: 'Weekly jackpot creates a new club finance story',
        summary: 'A jackpot notification triggered a wave of wallet top-ups and club share purchases.',
        body: 'GTEX jackpot activity has spilled into the club economy. After the latest winning notification, several users moved funds into wallet balances and purchased club shares. Admin coin monitoring remains active across all jackpot-linked wallet activity.',
        category: GtexNewsCategory.jackpot,
        publishedAt: now.subtract(const Duration(days: 1)),
        heroLabel: 'Jackpot',
        relatedEntity: 'Weekly Jackpot',
        trustScore: 0.89,
      ),
    ];
  }

  List<GtexNewsroomQueueItem> loadDemoNewsroomQueue() {
    final DateTime now = DateTime.now();
    return <GtexNewsroomQueueItem>[
      GtexNewsroomQueueItem(
        id: 'q1',
        title: 'Creator tournament final recap',
        status: 'Review',
        category: GtexNewsCategory.tournaments,
        updatedAt: now.subtract(const Duration(minutes: 14)),
        audience: 'All users',
      ),
      GtexNewsroomQueueItem(
        id: 'q2',
        title: 'High-value player order alert',
        status: 'Draft',
        category: GtexNewsCategory.market,
        updatedAt: now.subtract(const Duration(hours: 1)),
        riskLabel: 'Needs compliance check',
        audience: 'Admins only',
      ),
      GtexNewsroomQueueItem(
        id: 'q3',
        title: 'Create-a-son request spotlight',
        status: 'Scheduled',
        category: GtexNewsCategory.regens,
        updatedAt: now.subtract(const Duration(hours: 3)),
        audience: 'Regen followers',
      ),
    ];
  }
}
