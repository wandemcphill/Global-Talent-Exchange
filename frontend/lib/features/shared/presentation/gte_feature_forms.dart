import 'package:flutter/material.dart';

class GteFormFieldSpec {
  const GteFormFieldSpec({
    required this.key,
    required this.label,
    this.initialValue = '',
    this.helper,
    this.keyboardType,
    this.maxLines = 1,
  });

  final String key;
  final String label;
  final String initialValue;
  final String? helper;
  final TextInputType? keyboardType;
  final int maxLines;
}

Future<Map<String, String>?> showGteFormSheet(
  BuildContext context, {
  required String title,
  required List<GteFormFieldSpec> fields,
  required Future<bool> Function(Map<String, String> values) onSubmit,
  String submitLabel = 'Submit',
}) async {
  final Map<String, TextEditingController> controllers =
      <String, TextEditingController>{
    for (final GteFormFieldSpec field in fields)
      field.key: TextEditingController(text: field.initialValue),
  };
  try {
    return showModalBottomSheet<Map<String, String>>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (BuildContext context) {
        final EdgeInsets viewInsets = MediaQuery.of(context).viewInsets;
        return Padding(
          padding: EdgeInsets.fromLTRB(20, 12, 20, viewInsets.bottom + 20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(title, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 16),
              ...fields.map(
                (GteFormFieldSpec field) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: TextField(
                    controller: controllers[field.key],
                    keyboardType: field.keyboardType,
                    maxLines: field.maxLines,
                    decoration: InputDecoration(
                      labelText: field.label,
                      helperText: field.helper,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 8),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: () async {
                    final Map<String, String> values = <String, String>{
                      for (final MapEntry<String, TextEditingController> entry
                          in controllers.entries)
                        entry.key: entry.value.text.trim(),
                    };
                    final bool success = await onSubmit(values);
                    if (success && context.mounted) {
                      Navigator.of(context).pop(values);
                    }
                  },
                  child: Text(submitLabel),
                ),
              ),
            ],
          ),
        );
      },
    );
  } finally {
    for (final TextEditingController controller in controllers.values) {
      controller.dispose();
    }
  }
}
