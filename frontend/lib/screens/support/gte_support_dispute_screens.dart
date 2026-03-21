import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/app_feedback.dart';
import '../../data/gte_exchange_api_client.dart';
import '../../data/gte_models.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../widgets/gte_formatters.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';

class GteDisputeHubScreen extends StatefulWidget {
  const GteDisputeHubScreen({
    super.key,
    required this.controller,
  });

  final GteExchangeController controller;

  @override
  State<GteDisputeHubScreen> createState() => _GteDisputeHubScreenState();
}

class _GteDisputeHubScreenState extends State<GteDisputeHubScreen> {
  late Future<List<GteDispute>> _disputesFuture;

  @override
  void initState() {
    super.initState();
    _disputesFuture = widget.controller.api.listDisputes();
  }

  Future<void> _refresh() async {
    setState(() {
      _disputesFuture = widget.controller.api.listDisputes();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Support & disputes'),
        actions: <Widget>[
          IconButton(onPressed: _refresh, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: FutureBuilder<List<GteDispute>>(
        future: _disputesFuture,
        builder:
            (BuildContext context, AsyncSnapshot<List<GteDispute>> snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          final List<GteDispute> disputes = snapshot.data ?? <GteDispute>[];
          if (disputes.isEmpty) {
            return const Center(
              child: GteStatePanel(
                title: 'No disputes yet',
                message:
                    'Open a dispute from a deposit or withdrawal record to start a support thread.',
                icon: Icons.support_agent_outlined,
              ),
            );
          }
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView.separated(
              padding: const EdgeInsets.all(20),
              itemCount: disputes.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (BuildContext context, int index) {
                final GteDispute dispute = disputes[index];
                return GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(dispute.reference,
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 6),
                      Text(
                        'Status: ${_disputeStatusLabel(dispute.status)}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        dispute.subject ??
                            'Support thread for ${dispute.resourceType}',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Last message ${gteFormatDateTime(dispute.lastMessageAt)}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 12),
                      OutlinedButton(
                        onPressed: () {
                          Navigator.of(context).push<void>(
                            MaterialPageRoute<void>(
                              builder: (BuildContext context) =>
                                  GteDisputeThreadScreen(
                                api: widget.controller.api,
                                disputeId: dispute.id,
                              ),
                            ),
                          );
                        },
                        child: const Text('Open thread'),
                      ),
                    ],
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}

class GteDisputeCreateScreen extends StatefulWidget {
  const GteDisputeCreateScreen({
    super.key,
    required this.controller,
    required this.resourceType,
    required this.resourceId,
    required this.reference,
    this.prefillSubject,
    this.prefillMessage,
  });

  final GteExchangeController controller;
  final String resourceType;
  final String resourceId;
  final String reference;
  final String? prefillSubject;
  final String? prefillMessage;

  @override
  State<GteDisputeCreateScreen> createState() => _GteDisputeCreateScreenState();
}

class _GteDisputeCreateScreenState extends State<GteDisputeCreateScreen> {
  late final TextEditingController _subjectController;
  late final TextEditingController _messageController;
  GteAttachment? _attachment;
  bool _isSubmitting = false;
  bool _isUploading = false;
  String? _error;
  String? _whatsappNumber;

  @override
  void initState() {
    super.initState();
    _subjectController =
        TextEditingController(text: widget.prefillSubject ?? '');
    _messageController =
        TextEditingController(text: widget.prefillMessage ?? '');
    _loadWhatsapp();
  }

  @override
  void dispose() {
    _subjectController.dispose();
    _messageController.dispose();
    super.dispose();
  }

  Future<void> _loadWhatsapp() async {
    try {
      final GteTreasurySettings settings =
          await widget.controller.api.fetchTreasurySettings();
      if (!mounted) {
        return;
      }
      setState(() {
        _whatsappNumber = settings.whatsappNumber;
      });
    } catch (_) {
      // Ignore WhatsApp load errors for MVP.
    }
  }

  Future<void> _pickAttachment() async {
    if (_isUploading) {
      return;
    }
    setState(() {
      _isUploading = true;
      _error = null;
    });
    try {
      final FilePickerResult? result = await FilePicker.platform.pickFiles(
        withData: true,
        type: FileType.custom,
        allowedExtensions: const <String>['png', 'jpg', 'jpeg', 'pdf'],
      );
      if (result == null || result.files.isEmpty) {
        return;
      }
      final PlatformFile file = result.files.first;
      final List<int> bytes = file.bytes ?? const <int>[];
      if (bytes.isEmpty) {
        throw Exception('Unable to read the selected file.');
      }
      final GteAttachment attachment =
          await widget.controller.api.uploadAttachment(
        file.name,
        bytes,
        contentType:
            file.extension == null ? null : 'application/${file.extension}',
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _attachment = attachment;
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
          _isUploading = false;
        });
      }
    }
  }

  Future<void> _submit() async {
    final String message = _messageController.text.trim();
    if (message.isEmpty) {
      setState(() {
        _error = 'Describe the issue so we can assist you.';
      });
      return;
    }
    setState(() {
      _isSubmitting = true;
      _error = null;
    });
    try {
      final GteDispute dispute = await widget.controller.api.openDispute(
        GteDisputeCreateRequest(
          resourceType: widget.resourceType,
          resourceId: widget.resourceId,
          reference: widget.reference,
          subject: _subjectController.text.trim().isEmpty
              ? null
              : _subjectController.text.trim(),
          message: message,
          attachmentId: _attachment?.id,
        ),
      );
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Dispute created.')),
      );
      Navigator.of(context).pushReplacement<void, void>(
        MaterialPageRoute<void>(
          builder: (BuildContext context) => GteDisputeThreadScreen(
            api: widget.controller.api,
            disputeId: dispute.id,
          ),
        ),
      );
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
          _isSubmitting = false;
        });
      }
    }
  }

  Future<void> _openWhatsapp() async {
    final String? number = _whatsappNumber;
    if (number == null || number.trim().isEmpty) {
      return;
    }
    final String digits = number.replaceAll(RegExp(r'[^0-9]'), '');
    if (digits.isEmpty) {
      return;
    }
    final String message =
        'Support request for ${widget.reference} (${widget.resourceType}).';
    final Uri uri =
        Uri.parse('https://wa.me/$digits?text=${Uri.encodeComponent(message)}');
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Open dispute')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: <Widget>[
          GteSurfacePanel(
            emphasized: true,
            accentColor: GteShellTheme.warning,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('Dispute summary',
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                Text('Reference: ${widget.reference}',
                    style: Theme.of(context).textTheme.bodyMedium),
                const SizedBox(height: 4),
                Text('Type: ${widget.resourceType}',
                    style: Theme.of(context).textTheme.bodySmall),
                const SizedBox(height: 10),
                if (_whatsappNumber != null)
                  OutlinedButton.icon(
                    onPressed: _openWhatsapp,
                    icon: const Icon(Icons.chat_bubble_outline),
                    label: const Text('Chat on WhatsApp'),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          GteSurfacePanel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('Describe the issue',
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 12),
                TextField(
                  controller: _subjectController,
                  decoration: const InputDecoration(
                    labelText: 'Subject (optional)',
                    prefixIcon: Icon(Icons.title_outlined),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _messageController,
                  maxLines: 4,
                  decoration: const InputDecoration(
                    labelText: 'Message',
                    prefixIcon: Icon(Icons.message_outlined),
                  ),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: <Widget>[
                    OutlinedButton.icon(
                      onPressed: _isUploading ? null : _pickAttachment,
                      icon: const Icon(Icons.attach_file_outlined),
                      label: Text(
                          _isUploading ? 'Uploading...' : 'Add attachment'),
                    ),
                    if (_attachment != null)
                      Chip(label: Text(_attachment!.filename)),
                  ],
                ),
                if (_error != null) ...<Widget>[
                  const SizedBox(height: 12),
                  GteStatePanel(
                    title: 'Dispute error',
                    message: _error!,
                    icon: Icons.warning_amber_rounded,
                  ),
                ],
                const SizedBox(height: 18),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: _isSubmitting ? null : _submit,
                    child:
                        Text(_isSubmitting ? 'Submitting...' : 'Open dispute'),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class GteDisputeThreadScreen extends StatefulWidget {
  const GteDisputeThreadScreen({
    super.key,
    required this.api,
    required this.disputeId,
    this.isAdmin = false,
  });

  final GteExchangeApiClient api;
  final String disputeId;
  final bool isAdmin;

  @override
  State<GteDisputeThreadScreen> createState() => _GteDisputeThreadScreenState();
}

class _GteDisputeThreadScreenState extends State<GteDisputeThreadScreen> {
  late Future<GteDispute> _disputeFuture;
  final TextEditingController _messageController = TextEditingController();
  bool _isSending = false;
  bool _isUploading = false;
  String? _error;
  GteAttachment? _attachment;
  String? _whatsappNumber;

  @override
  void initState() {
    super.initState();
    _disputeFuture = _loadDispute();
    _loadWhatsapp();
  }

  @override
  void dispose() {
    _messageController.dispose();
    super.dispose();
  }

  Future<GteDispute> _loadDispute() async {
    if (widget.isAdmin) {
      return widget.api.fetchAdminDispute(widget.disputeId);
    }
    return widget.api.fetchDispute(widget.disputeId);
  }

  Future<void> _refresh() async {
    setState(() {
      _disputeFuture = _loadDispute();
    });
  }

  Future<void> _loadWhatsapp() async {
    try {
      final GteTreasurySettings settings =
          await widget.api.fetchTreasurySettings();
      if (!mounted) {
        return;
      }
      setState(() {
        _whatsappNumber = settings.whatsappNumber;
      });
    } catch (_) {
      // Ignore WhatsApp load errors for MVP.
    }
  }

  Future<void> _pickAttachment() async {
    if (_isUploading) {
      return;
    }
    setState(() {
      _isUploading = true;
      _error = null;
    });
    try {
      final FilePickerResult? result = await FilePicker.platform.pickFiles(
        withData: true,
        type: FileType.custom,
        allowedExtensions: const <String>['png', 'jpg', 'jpeg', 'pdf'],
      );
      if (result == null || result.files.isEmpty) {
        return;
      }
      final PlatformFile file = result.files.first;
      final List<int> bytes = file.bytes ?? const <int>[];
      if (bytes.isEmpty) {
        throw Exception('Unable to read the selected file.');
      }
      final GteAttachment attachment = await widget.api.uploadAttachment(
        file.name,
        bytes,
        contentType:
            file.extension == null ? null : 'application/${file.extension}',
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _attachment = attachment;
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
          _isUploading = false;
        });
      }
    }
  }

  Future<void> _sendMessage(GteDispute dispute) async {
    final String message = _messageController.text.trim();
    if (message.isEmpty) {
      setState(() {
        _error = 'Type a message before sending.';
      });
      return;
    }
    setState(() {
      _isSending = true;
      _error = null;
    });
    try {
      final request = GteDisputeMessageRequest(
        message: message,
        attachmentId: _attachment?.id,
      );
      if (widget.isAdmin) {
        await widget.api.adminSendDisputeMessage(dispute.id, request);
      } else {
        await widget.api.sendDisputeMessage(dispute.id, request);
      }
      if (!mounted) {
        return;
      }
      _messageController.clear();
      _attachment = null;
      await _refresh();
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
          _isSending = false;
        });
      }
    }
  }

  Future<void> _openWhatsapp(GteDispute dispute) async {
    final String? number = _whatsappNumber;
    if (number == null || number.trim().isEmpty) {
      return;
    }
    final String digits = number.replaceAll(RegExp(r'[^0-9]'), '');
    if (digits.isEmpty) {
      return;
    }
    final String message =
        'Support thread ${dispute.reference} (${dispute.resourceType}).';
    final Uri uri =
        Uri.parse('https://wa.me/$digits?text=${Uri.encodeComponent(message)}');
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.isAdmin ? 'Dispute console' : 'Dispute thread'),
        actions: <Widget>[
          IconButton(onPressed: _refresh, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: FutureBuilder<GteDispute>(
        future: _disputeFuture,
        builder: (BuildContext context, AsyncSnapshot<GteDispute> snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (!snapshot.hasData) {
            return const Center(
              child: GteStatePanel(
                title: 'Dispute unavailable',
                message: 'We could not load this support thread.',
                icon: Icons.support_agent_outlined,
              ),
            );
          }
          final GteDispute dispute = snapshot.data!;
          final List<GteDisputeMessage> messages = dispute.messages;
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: <Widget>[
                GteSurfacePanel(
                  emphasized: true,
                  accentColor: GteShellTheme.warning,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(dispute.reference,
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 6),
                      Text(
                        'Status: ${_disputeStatusLabel(dispute.status)}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        dispute.subject ?? 'Support thread',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 12),
                      if (_whatsappNumber != null)
                        OutlinedButton.icon(
                          onPressed: () => _openWhatsapp(dispute),
                          icon: const Icon(Icons.chat_bubble_outline),
                          label: const Text('Chat on WhatsApp'),
                        ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                if (messages.isEmpty)
                  const GteStatePanel(
                    title: 'No messages yet',
                    message: 'Send a message to start the thread.',
                    icon: Icons.mark_chat_unread_outlined,
                  )
                else
                  ...messages.map(
                    (GteDisputeMessage message) => _MessageBubble(
                      message: message,
                      isOwn: widget.isAdmin
                          ? message.senderRole == 'admin'
                          : message.senderRole == 'user',
                    ),
                  ),
                const SizedBox(height: 12),
                GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text('Send a message',
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _messageController,
                        maxLines: 3,
                        decoration: const InputDecoration(
                          labelText: 'Message',
                          prefixIcon: Icon(Icons.message_outlined),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: <Widget>[
                          OutlinedButton.icon(
                            onPressed: _isUploading ? null : _pickAttachment,
                            icon: const Icon(Icons.attach_file_outlined),
                            label: Text(_isUploading
                                ? 'Uploading...'
                                : 'Add attachment'),
                          ),
                          if (_attachment != null)
                            Chip(label: Text(_attachment!.filename)),
                        ],
                      ),
                      if (_error != null) ...<Widget>[
                        const SizedBox(height: 12),
                        GteStatePanel(
                          title: 'Message error',
                          message: _error!,
                          icon: Icons.warning_amber_rounded,
                        ),
                      ],
                      const SizedBox(height: 18),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton(
                          onPressed:
                              _isSending ? null : () => _sendMessage(dispute),
                          child:
                              Text(_isSending ? 'Sending...' : 'Send message'),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({
    required this.message,
    required this.isOwn,
  });

  final GteDisputeMessage message;
  final bool isOwn;

  @override
  Widget build(BuildContext context) {
    final Color bubbleColor = isOwn
        ? GteShellTheme.accentCapital.withValues(alpha: 0.2)
        : Colors.white.withValues(alpha: 0.06);
    return Align(
      alignment: isOwn ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(14),
        constraints: const BoxConstraints(maxWidth: 520),
        decoration: BoxDecoration(
          color: bubbleColor,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
        ),
        child: Column(
          crossAxisAlignment:
              isOwn ? CrossAxisAlignment.end : CrossAxisAlignment.start,
          children: <Widget>[
            Text(message.message,
                style: Theme.of(context).textTheme.bodyMedium),
            if (message.attachmentId != null) ...<Widget>[
              const SizedBox(height: 8),
              Text('Attachment on file',
                  style: Theme.of(context).textTheme.bodySmall),
            ],
            const SizedBox(height: 6),
            Text(
              gteFormatDateTime(message.createdAt),
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}

String _disputeStatusLabel(GteDisputeStatus status) {
  switch (status) {
    case GteDisputeStatus.open:
      return 'Open';
    case GteDisputeStatus.awaitingUser:
      return 'Awaiting user';
    case GteDisputeStatus.awaitingAdmin:
      return 'Awaiting admin';
    case GteDisputeStatus.resolved:
      return 'Resolved';
    case GteDisputeStatus.closed:
      return 'Closed';
  }
}
