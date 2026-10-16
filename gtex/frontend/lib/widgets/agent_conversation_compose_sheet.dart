import 'package:flutter/material.dart';

import '../data/agent_marketplace_models.dart';

Future<String?> showAgentConversationComposer(
  BuildContext context, {
  required String playerName,
  required String askingType,
}) async {
  final TextEditingController controller = TextEditingController();
  final List<String> templates = <String>[
    'Is $playerName available?',
    'Can we arrange a trial?',
    if (askingType.trim().toLowerCase() == 'loan')
      'Would you consider a loan structure?'
    else
      'What are the expectations for this move?',
  ];

  final String? result = await showModalBottomSheet<String>(
    context: context,
    isScrollControlled: true,
    builder: (BuildContext context) {
      return StatefulBuilder(
        builder: (BuildContext context, StateSetter setModalState) {
          final String trimmedMessage = controller.text.trim();
          return SafeArea(
            child: Padding(
              padding: EdgeInsets.fromLTRB(
                20,
                20,
                20,
                20 + MediaQuery.of(context).viewInsets.bottom,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Contact ${gteAskingTypeLabel(askingType).toLowerCase()} agent',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '$playerName is listed for ${gteAskingTypeLabel(askingType).toLowerCase()}. Start with a quick note tied to this player.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: templates
                        .map(
                          (String template) => ActionChip(
                            label: Text(template),
                            onPressed: () {
                              controller.text = template;
                              controller.selection = TextSelection.collapsed(
                                offset: controller.text.length,
                              );
                              setModalState(() {});
                            },
                          ),
                        )
                        .toList(growable: false),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: controller,
                    maxLines: 4,
                    minLines: 3,
                    autofocus: true,
                    onChanged: (_) => setModalState(() {}),
                    decoration: const InputDecoration(
                      labelText: 'Message',
                      hintText: 'Interested in this player...',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: <Widget>[
                      TextButton(
                        onPressed: () => Navigator.of(context).pop(),
                        child: const Text('Cancel'),
                      ),
                      const Spacer(),
                      FilledButton(
                        onPressed: trimmedMessage.isEmpty
                            ? null
                            : () => Navigator.of(context).pop(trimmedMessage),
                        child: const Text('Start Chat'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          );
        },
      );
    },
  );
  controller.dispose();
  return result;
}
