import 'package:flutter/material.dart';

import '../models/gtex_admin_command_models.dart';
import 'gtex_admin_visuals.dart';

class GtexAdminQueuePanel extends StatelessWidget {
  const GtexAdminQueuePanel({
    super.key,
    required this.items,
    required this.selectedItem,
    required this.onSelected,
    required this.onApprove,
    required this.onEscalate,
    this.actionBusy = false,
    this.actionMessage,
    this.actionError,
  });

  final List<GtexAdminQueueItem> items;
  final GtexAdminQueueItem? selectedItem;
  final ValueChanged<String> onSelected;
  final VoidCallback onApprove;
  final VoidCallback onEscalate;
  final bool actionBusy;
  final String? actionMessage;
  final String? actionError;

  @override
  Widget build(BuildContext context) {
    return GtexAdminPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const GtexAdminSectionHeader(
            title: 'Live operations queue',
            subtitle:
                'KYC, orders, disputes, create-a-son requests and risk holds.',
          ),
          const SizedBox(height: 16),
          SizedBox(
            height: 240,
            child: ListView.separated(
              itemCount: items.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (context, index) {
                final item = items[index];
                final selected = selectedItem?.id == item.id;
                final color = gtexAdminSeverityColor(item.severity);
                return InkWell(
                  borderRadius: BorderRadius.circular(16),
                  onTap: () => onSelected(item.id),
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color:
                          selected
                              ? const Color(0xFF142A25)
                              : const Color(0xFF0B1220),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                        color:
                            selected
                                ? const Color(0xFF2DFF87).withOpacity(.4)
                                : Colors.white.withOpacity(.06),
                      ),
                    ),
                    child: Row(
                      children: [
                        Icon(Icons.circle, size: 10, color: color),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                item.title,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w900,
                                ),
                              ),
                              const SizedBox(height: 3),
                              Text(
                                item.subtitle,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  color: Colors.white60,
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 8),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            GtexAdminStatusPill(
                              label: item.status,
                              severity: item.severity,
                            ),
                            const SizedBox(height: 4),
                            Text(
                              item.amountLabel ?? item.createdAtLabel,
                              style: const TextStyle(
                                color: Colors.white60,
                                fontSize: 11,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
          const SizedBox(height: 16),
          if (selectedItem != null)
            _SelectedQueueDetail(
              item: selectedItem!,
              onApprove: onApprove,
              onEscalate: onEscalate,
              actionBusy: actionBusy,
            ),
          if (actionMessage != null || actionError != null) ...[
            const SizedBox(height: 10),
            _AdminActionNotice(
              message: actionError ?? actionMessage!,
              isError: actionError != null,
            ),
          ],
        ],
      ),
    );
  }
}

class _SelectedQueueDetail extends StatelessWidget {
  const _SelectedQueueDetail({
    required this.item,
    required this.onApprove,
    required this.onEscalate,
    required this.actionBusy,
  });

  final GtexAdminQueueItem item;
  final VoidCallback onApprove;
  final VoidCallback onEscalate;
  final bool actionBusy;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF101B2B),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: Colors.white.withOpacity(.07)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            item.title,
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 6),
          Text(item.subtitle, style: const TextStyle(color: Colors.white70)),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _AdminActionButton(
                  label: 'Approve / resolve',
                  icon: Icons.check_circle_rounded,
                  onTap: actionBusy ? null : onApprove,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _AdminActionButton(
                  label: actionBusy ? 'Sending...' : 'Escalate',
                  icon: Icons.priority_high_rounded,
                  onTap: actionBusy ? null : onEscalate,
                  danger: true,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _AdminActionButton extends StatelessWidget {
  const _AdminActionButton({
    required this.label,
    required this.icon,
    required this.onTap,
    this.danger = false,
  });

  final String label;
  final IconData icon;
  final VoidCallback? onTap;
  final bool danger;

  @override
  Widget build(BuildContext context) {
    final color = danger ? const Color(0xFFFF8A3D) : const Color(0xFF2DFF87);
    return ElevatedButton.icon(
      onPressed: onTap,
      icon: Icon(icon, size: 18),
      label: Text(label),
      style: ElevatedButton.styleFrom(
        backgroundColor: color.withOpacity(.16),
        foregroundColor: color,
        elevation: 0,
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 12),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      ),
    );
  }
}

class _AdminActionNotice extends StatelessWidget {
  const _AdminActionNotice({required this.message, required this.isError});

  final String message;
  final bool isError;

  @override
  Widget build(BuildContext context) {
    final color = isError ? const Color(0xFFFF4D6D) : const Color(0xFF2DFF87);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: color.withOpacity(.12),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withOpacity(.35)),
      ),
      child: Row(
        children: [
          Icon(
            isError ? Icons.error_outline_rounded : Icons.check_circle_rounded,
            size: 18,
            color: color,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: TextStyle(color: color, fontWeight: FontWeight.w800),
            ),
          ),
        ],
      ),
    );
  }
}
