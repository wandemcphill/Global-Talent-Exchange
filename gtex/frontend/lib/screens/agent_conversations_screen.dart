import 'package:flutter/material.dart';

import '../core/app_feedback.dart';
import '../data/agent_marketplace_api.dart';
import '../data/agent_marketplace_models.dart';
import '../widgets/gte_formatters.dart';
import 'agent_conversation_screen.dart';

class AgentConversationsScreen extends StatefulWidget {
  const AgentConversationsScreen({
    super.key,
    required this.api,
    required this.currentUserId,
  });

  final AgentMarketplaceApi api;
  final String currentUserId;

  @override
  State<AgentConversationsScreen> createState() =>
      _AgentConversationsScreenState();
}

class _AgentConversationsScreenState extends State<AgentConversationsScreen> {
  List<GteConversationSummary> _conversations =
      const <GteConversationSummary>[];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadConversations();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Conversations')),
      body: RefreshIndicator(
        onRefresh: () => _loadConversations(refresh: true),
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? ListView(
                    children: <Widget>[
                      Padding(
                        padding: const EdgeInsets.all(24),
                        child: _InboxStateCard(
                          title: 'Conversation inbox unavailable',
                          message: _error!,
                          actionLabel: 'Retry',
                          onAction: _loadConversations,
                        ),
                      ),
                    ],
                  )
                : _conversations.isEmpty
                    ? ListView(
                        children: const <Widget>[
                          Padding(
                            padding: EdgeInsets.all(24),
                            child: _InboxStateCard(
                              title: 'No conversations yet',
                              message:
                                  'Start from a listed player card and the player-tied chat will appear here.',
                            ),
                          ),
                        ],
                      )
                    : ListView.separated(
                        padding: const EdgeInsets.all(16),
                        itemBuilder: (BuildContext context, int index) {
                          final GteConversationSummary conversation =
                              _conversations[index];
                          return ListTile(
                            tileColor: const Color(0xFFF3EFE7),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(18),
                            ),
                            title: Text(conversation.player.playerName),
                            subtitle: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                const SizedBox(height: 4),
                                Text(
                                  '${conversation.player.currentClubName ?? 'Free Agent'} • ${gteAskingTypeLabel(conversation.player.askingType)}',
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  conversation.latestMessagePreview ??
                                      'No messages yet',
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ],
                            ),
                            trailing: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              crossAxisAlignment: CrossAxisAlignment.end,
                              children: <Widget>[
                                Text(
                                  conversation.lastMessageAt == null
                                      ? 'Now'
                                      : gteFormatRelativeTime(
                                          conversation.lastMessageAt),
                                  style: const TextStyle(fontSize: 12),
                                ),
                                if (conversation.unreadCount > 0) ...<Widget>[
                                  const SizedBox(height: 6),
                                  CircleAvatar(
                                    radius: 11,
                                    backgroundColor: const Color(0xFFB96B2C),
                                    child: Text(
                                      '${conversation.unreadCount}',
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontSize: 11,
                                        fontWeight: FontWeight.w700,
                                      ),
                                    ),
                                  ),
                                ],
                              ],
                            ),
                            onTap: () => _openConversation(conversation.id),
                          );
                        },
                        separatorBuilder: (BuildContext context, int index) =>
                            const SizedBox(height: 12),
                        itemCount: _conversations.length,
                      ),
      ),
    );
  }

  Future<void> _loadConversations({bool refresh = false}) async {
    if (mounted) {
      setState(() {
        _isLoading = true;
        if (!refresh) {
          _error = null;
        }
      });
    }
    try {
      final List<GteConversationSummary> conversations =
          await widget.api.fetchConversations();
      if (!mounted) {
        return;
      }
      setState(() {
        _conversations = conversations;
        _error = null;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = AppFeedback.messageFor(error);
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _openConversation(String conversationId) async {
    try {
      final GteConversationDetail detail =
          await widget.api.fetchConversationDetail(conversationId);
      if (!mounted) {
        return;
      }
      await Navigator.of(context).push<void>(
        MaterialPageRoute<void>(
          builder: (BuildContext context) => AgentConversationScreen(
            api: widget.api,
            currentUserId: widget.currentUserId,
            initialDetail: detail,
          ),
        ),
      );
      await _loadConversations(refresh: true);
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppFeedback.messageFor(error))),
      );
    }
  }
}

class _InboxStateCard extends StatelessWidget {
  const _InboxStateCard({
    required this.title,
    required this.message,
    this.actionLabel,
    this.onAction,
  });

  final String title;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFFF3EFE7),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(message),
          if (actionLabel != null && onAction != null) ...<Widget>[
            const SizedBox(height: 16),
            FilledButton(
              onPressed: onAction,
              child: Text(actionLabel!),
            ),
          ],
        ],
      ),
    );
  }
}
