import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/widgets/competitions/competition_rule_editor.dart';

class CompetitionRuleBuilderScreen extends StatelessWidget {
  const CompetitionRuleBuilderScreen({
    super.key,
    required this.controller,
  });

  final CompetitionController controller;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Rules builder'),
      ),
      body: AnimatedBuilder(
        animation: controller,
        builder: (BuildContext context, Widget? child) {
          return ListView(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
            children: <Widget>[
              CompetitionRuleEditor(
                format: controller.draft.format,
                value: controller.draft.rules,
                onChanged: controller.updateDraftRules,
              ),
              const SizedBox(height: 20),
              FilledButton(
                onPressed: () {
                  Navigator.of(context).pop();
                },
                child: const Text('Save rules'),
              ),
            ],
          );
        },
      ),
    );
  }
}
