import 'package:flutter/widgets.dart';
import 'package:gte_frontend/features/build_a_son/build_a_son.dart'
    as canonical;
import 'package:gte_frontend/models/regen_creation_models.dart';

class BuildASonWizardScreen extends StatelessWidget {
  const BuildASonWizardScreen({super.key, this.onCompleted});

  final Future<void> Function(RegenCreationOrder order)? onCompleted;

  @override
  Widget build(BuildContext context) {
    return canonical.BuildASonScreen(onCompleted: onCompleted);
  }
}

class BuildASonWizard extends StatelessWidget {
  const BuildASonWizard({super.key, required this.client, this.onCompleted});

  final canonical.BuildASonCreationClient client;
  final Future<void> Function(RegenCreationOrder order)? onCompleted;

  @override
  Widget build(BuildContext context) {
    return canonical.BuildASonWizard(client: client, onCompleted: onCompleted);
  }
}
