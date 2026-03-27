import 'dart:async';

import 'package:flutter/material.dart';

import '../core/app_feedback.dart';
import '../data/agent_marketplace_api.dart';
import '../data/agent_marketplace_models.dart';
import '../widgets/gte_formatters.dart';

class AgentConversationScreen extends StatefulWidget {
  const AgentConversationScreen({
    super.key,
    required this.api,
    required this.currentUserId,
    required this.initialDetail,
  });

  final AgentMarketplaceApi api;
  final String currentUserId;
  final GteConversationDetail initialDetail;

  @override
  State<AgentConversationScreen> createState() =>
      _AgentConversationScreenState();
}

class _AgentConversationScreenState extends State<AgentConversationScreen> {
  late final TextEditingController _messageController;
  Timer? _pollTimer;
  late GteConversationDetail _detail;
  bool _isRefreshing = false;
  bool _isSending = false;

  @override
  void initState() {
    super.initState();
    _detail = widget.initialDetail;
    _messageController = TextEditingController();
    _pollTimer = Timer.periodic(
      const Duration(seconds: 4),
      (_) => _refresh(silent: true),
    );
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _messageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final GteConversationSummary conversation = _detail.conversation;
    final GteConversationPlayerContext player = conversation.player;
    final String messageDraft = _messageController.text.trim();
    return Scaffold(
      appBar: AppBar(
        title: Text(player.playerName),
        actions: <Widget>[
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Center(
              child: _StatusBadge(label: _statusLabel(conversation.status)),
            ),
          ),
        ],
      ),
      body: Column(
        children: <Widget>[
          _ConversationContextCard(conversation: conversation),
          Expanded(
            child: RefreshIndicator(
              onRefresh: () => _refresh(silent: false),
              child: ListView.builder(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                itemCount: _detail.messages.length,
                itemBuilder: (BuildContext context, int index) {
                  final GteConversationMessage message =
                      _detail.messages[index];
                  final bool isMine = message.senderId == widget.currentUserId;
                  final bool isLastOutgoing = isMine &&
                      index ==
                          _detail.messages.lastIndexWhere(
                            (GteConversationMessage candidate) =>
                                candidate.senderId == widget.currentUserId,
                          );
                  final DateTime? otherReadAt = _latestOtherReadAt();
                  final String? statusLabel = isLastOutgoing
                      ? (otherReadAt != null &&
                              !otherReadAt.isBefore(message.createdAt)
                          ? 'Read'
                          : 'Sent')
                      : null;
                  return Align(
                    alignment:
                        isMine ? Alignment.centerRight : Alignment.centerLeft,
                    child: Container(
                      margin: const EdgeInsets.only(bottom: 12),
                      constraints: const BoxConstraints(maxWidth: 520),
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: isMine
                            ? const Color(0xFF1F2A44)
                            : const Color(0xFFF3EFE7),
                        borderRadius: BorderRadius.circular(18),
                      ),
                      child: Column(
                        crossAxisAlignment: isMine
                            ? CrossAxisAlignment.end
                            : CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            message.message,
                            style: TextStyle(
                              color: isMine
                                  ? Colors.white
                                  : const Color(0xFF211C16),
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            statusLabel == null
                                ? '${message.senderName} • ${gteFormatRelativeTime(message.createdAt)}'
                                : '$statusLabel • ${gteFormatRelativeTime(message.createdAt)}',
                            style: TextStyle(
                              color: isMine
                                  ? Colors.white70
                                  : const Color(0xFF7B7469),
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
          ),
          _MessageTemplateBar(
            askingType: player.askingType,
            playerName: player.playerName,
            onSelectTemplate: (String template) {
              _messageController.text = template;
              _messageController.selection = TextSelection.collapsed(
                offset: template.length,
              );
              setState(() {});
            },
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            child: Row(
              children: <Widget>[
                Expanded(
                  child: TextField(
                    controller: _messageController,
                    minLines: 1,
                    maxLines: 4,
                    onChanged: (_) => setState(() {}),
                    decoration: const InputDecoration(
                      hintText: 'Reply about this player',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                FilledButton(
                  onPressed: _isSending || messageDraft.isEmpty
                      ? null
                      : () => _sendMessage(messageDraft),
                  child: _isSending
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Send'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  DateTime? _latestOtherReadAt() {
    DateTime? latest;
    for (final GteConversationParticipant participant
        in _detail.conversation.participants) {
      if (participant.userId == widget.currentUserId ||
          participant.lastReadAt == null) {
        continue;
      }
      if (latest == null || participant.lastReadAt!.isAfter(latest)) {
        latest = participant.lastReadAt;
      }
    }
    return latest;
  }

  Future<void> _refresh({required bool silent}) async {
    if (_isRefreshing) {
      return;
    }
    setState(() {
      _isRefreshing = true;
    });
    try {
      final GteConversationDetail detail =
          await widget.api.fetchConversationDetail(
        _detail.conversation.id,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _detail = detail;
      });
    } catch (error) {
      if (!mounted || silent) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppFeedback.messageFor(error))),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isRefreshing = false;
        });
      }
    }
  }

  Future<void> _sendMessage(String message) async {
    setState(() {
      _isSending = true;
    });
    try {
      final GteConversationDetail detail = await widget.api.sendMessage(
        conversationId: _detail.conversation.id,
        message: message,
      );
      if (!mounted) {
        return;
      }
      _messageController.clear();
      setState(() {
        _detail = detail;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppFeedback.messageFor(error))),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isSending = false;
        });
      }
    }
  }

  String _statusLabel(String status) {
    switch (status.trim().toLowerCase()) {
      case 'negotiating':
        return 'Negotiating';
      case 'closed':
        return 'Closed';
      default:
        return 'Active';
    }
  }
}

class _ConversationContextCard extends StatelessWidget {
  const _ConversationContextCard({
    required this.conversation,
  });

  final GteConversationSummary conversation;

  @override
  Widget build(BuildContext context) {
    final GteConversationPlayerContext player = conversation.player;
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFF3EFE7),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Player: ${player.playerName}${player.position == null ? '' : ' (${player.position})'}',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 6),
          Text(
            'Club: ${player.currentClubName ?? 'Free Agent'}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 6),
          Text(
            'Agent: ${player.agentName} • ${gteAskingTypeLabel(player.askingType)}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          if (player.marketplaceNote != null &&
              player.marketplaceNote!.trim().isNotEmpty) ...<Widget>[
            const SizedBox(height: 10),
            Text(
              player.marketplaceNote!,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ],
      ),
    );
  }
}

class _MessageTemplateBar extends StatelessWidget {
  const _MessageTemplateBar({
    required this.askingType,
    required this.playerName,
    required this.onSelectTemplate,
  });

  final String askingType;
  final String playerName;
  final ValueChanged<String> onSelectTemplate;

  @override
  Widget build(BuildContext context) {
    final List<String> templates = <String>[
      'Is $playerName available?',
      'Can we arrange a trial?',
      if (askingType.trim().toLowerCase() == 'loan')
        'Would you consider a loan structure?'
      else
        'What are the expectations for this move?',
    ];
    return SizedBox(
      height: 44,
      child: ListView.separated(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        scrollDirection: Axis.horizontal,
        itemBuilder: (BuildContext context, int index) {
          return ActionChip(
            label: Text(templates[index]),
            onPressed: () => onSelectTemplate(templates[index]),
          );
        },
        separatorBuilder: (BuildContext context, int index) =>
            const SizedBox(width: 8),
        itemCount: templates.length,
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({
    required this.label,
  });

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFFE7E1D6),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: const TextStyle(fontWeight: FontWeight.w700),
      ),
    );
  }
}
