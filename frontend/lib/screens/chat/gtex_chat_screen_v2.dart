import 'package:flutter/material.dart';

import '../../features/engagement_redesign/engagement_controller.dart';
import '../../features/engagement_redesign/engagement_models.dart';
import '../../features/engagement_redesign/engagement_widgets.dart';
import '../../ui_gtex/ui_gtex.dart';

class GtexChatScreenV2 extends StatefulWidget {
  const GtexChatScreenV2({super.key, this.controller});

  final GtexEngagementController? controller;

  @override
  State<GtexChatScreenV2> createState() => _GtexChatScreenV2State();
}

class _GtexChatScreenV2State extends State<GtexChatScreenV2> {
  late final GtexEngagementController _controller;
  late final List<GtexConversation> _conversations;
  late GtexConversation _selected;

  @override
  void initState() {
    super.initState();
    _controller = widget.controller ?? GtexEngagementController();
    _conversations = _controller.loadDemoConversations();
    _selected = _conversations.first;
  }

  @override
  Widget build(BuildContext context) {
    return GtexMasterDetailScaffold(
      title: 'GTEX Chat',
      subtitle: 'Admin support, order desk, disputes, clubs, creators and player-related conversations.',
      accent: GtexColors.cyan,
      mobileLeftTitle: 'Conversations',
      leftPanel: _ConversationList(
        conversations: _conversations,
        selected: _selected,
        onSelected: (GtexConversation value) => setState(() => _selected = value),
      ),
      detail: _ConversationThread(
        conversation: _selected,
        messages: _controller.loadDemoMessages(_selected.id),
      ),
      rightPanel: _ConversationContext(conversation: _selected),
    );
  }
}

class _ConversationList extends StatelessWidget {
  const _ConversationList({required this.conversations, required this.selected, required this.onSelected});

  final List<GtexConversation> conversations;
  final GtexConversation selected;
  final ValueChanged<GtexConversation> onSelected;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        const GtexSearchField(hintText: 'Search chats, orders, clubs'),
        const SizedBox(height: GtexSpacing.md),
        Expanded(
          child: ListView(
            children: <Widget>[
              for (final GtexConversation conversation in conversations)
                GtexSectionListTile(
                  title: conversation.title,
                  subtitle: conversation.lastMessage,
                  icon: _conversationIcon(conversation.kind),
                  accent: conversation.isEscalated ? GtexColors.red : GtexColors.cyan,
                  isSelected: conversation.id == selected.id,
                  onTap: () => onSelected(conversation),
                  trailing: conversation.unreadCount > 0
                      ? GtexStatusChip(label: '${conversation.unreadCount}', color: GtexColors.pitch, compact: true)
                      : null,
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ConversationThread extends StatelessWidget {
  const _ConversationThread({required this.conversation, required this.messages});

  final GtexConversation conversation;
  final List<GtexChatMessage> messages;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        Padding(
          padding: const EdgeInsets.all(GtexSpacing.md),
          child: GtexPanel(
            title: conversation.title,
            subtitle: conversation.contextLabel,
            accent: conversation.isEscalated ? GtexColors.red : GtexColors.cyan,
            trailing: conversation.isEscalated
                ? const GtexStatusChip(label: 'ESCALATED', color: GtexColors.red, icon: Icons.priority_high_outlined)
                : const GtexStatusChip(label: 'ACTIVE', color: GtexColors.cyan, icon: Icons.chat_bubble_outline),
            child: const SizedBox.shrink(),
          ),
        ),
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.symmetric(horizontal: GtexSpacing.lg, vertical: GtexSpacing.sm),
            itemCount: messages.length,
            itemBuilder: (BuildContext context, int index) {
              final GtexChatMessage message = messages[index];
              return _MessageBubble(message: message);
            },
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(GtexSpacing.md),
          child: Row(
            children: <Widget>[
              Expanded(
                child: TextField(
                  decoration: InputDecoration(
                    hintText: 'Message GTEX...',
                    filled: true,
                    fillColor: GtexColors.panelStrong,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(GtexSpacing.radiusPill),
                      borderSide: const BorderSide(color: GtexColors.line),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: GtexSpacing.sm),
              GtexActionButton(
                label: 'Send',
                icon: Icons.send_outlined,
                accent: GtexColors.cyan,
                onPressed: () {},
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.message});

  final GtexChatMessage message;

  @override
  Widget build(BuildContext context) {
    final Alignment alignment = message.isMine ? Alignment.centerRight : Alignment.centerLeft;
    final Color accent = message.system ? GtexColors.gold : (message.isMine ? GtexColors.pitch : GtexColors.cyan);
    return Align(
      alignment: alignment,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 560),
        margin: const EdgeInsets.only(bottom: GtexSpacing.sm),
        padding: const EdgeInsets.all(GtexSpacing.md),
        decoration: BoxDecoration(
          color: message.isMine ? GtexColors.pitch.withValues(alpha: 0.13) : GtexColors.panelStrong,
          borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
          border: Border.all(color: accent.withValues(alpha: 0.32)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              message.sender,
              style: Theme.of(context).textTheme.labelMedium?.copyWith(color: accent, fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: GtexSpacing.xs),
            Text(
              message.message,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: GtexColors.textSecondary, height: 1.35),
            ),
          ],
        ),
      ),
    );
  }
}

class _ConversationContext extends StatelessWidget {
  const _ConversationContext({required this.conversation});

  final GtexConversation conversation;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        GtexPanel(
          title: 'Conversation context',
          subtitle: conversation.contextLabel ?? 'No linked object',
          accent: conversation.isEscalated ? GtexColors.red : GtexColors.cyan,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              GtexActionButton(label: 'Open linked record', icon: Icons.open_in_new_outlined, onPressed: () {}, accent: GtexColors.cyan),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(label: 'Attach evidence', icon: Icons.attach_file_outlined, onPressed: () {}, accent: GtexColors.cyan, secondary: true),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(label: 'Escalate', icon: Icons.priority_high_outlined, onPressed: () {}, accent: GtexColors.red, secondary: true),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        const GtexPanel(
          title: 'Audit note',
          subtitle: 'All admin/user messages should be attached to the related order, dispute, KYC, player, or club record.',
          child: SizedBox.shrink(),
        ),
      ],
    );
  }
}

IconData _conversationIcon(GtexConversationKind kind) {
  switch (kind) {
    case GtexConversationKind.support:
      return Icons.support_agent_outlined;
    case GtexConversationKind.admin:
      return Icons.admin_panel_settings_outlined;
    case GtexConversationKind.club:
      return Icons.shield_outlined;
    case GtexConversationKind.order:
      return Icons.receipt_long_outlined;
    case GtexConversationKind.dispute:
      return Icons.gavel_outlined;
    case GtexConversationKind.player:
      return Icons.sports_soccer_outlined;
    case GtexConversationKind.creator:
      return Icons.video_camera_front_outlined;
  }
}
