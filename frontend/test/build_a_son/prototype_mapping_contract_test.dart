import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Build-a-Son prototype mapping contract', () {
    test('docs name the canonical v13 source functions and Flutter files', () {
      final Directory root = _repoRoot();
      final String mapping = _read(
        root,
        'docs/prototype_mapping/wallet_regen_build_a_son_checklist.md',
      );

      expect(mapping, contains('renderBuildASon()'));
      expect(mapping, contains('completeBuildSon()'));
      expect(
        mapping,
        contains(
          'frontend/lib/features/build_a_son/presentation/build_a_son_screen.dart',
        ),
      );
      expect(
        mapping,
        contains(
          'frontend/lib/features/build_a_son/data/build_a_son_creation_client.dart',
        ),
      );
      expect(
        mapping,
        contains(
          'frontend/lib/features/build_a_son/providers/build_a_son_providers.dart',
        ),
      );
      expect(mapping, contains('frontend/lib/data/regen_creation_api.dart'));
      expect(
        mapping,
        contains(
          'Frontend parity tests: `frontend/test/build_a_son/build_a_son_closure_test.dart`',
        ),
      );
    });

    test('current Flutter wizard keeps the v13 four-step lifecycle', () {
      final Directory root = _repoRoot();
      final String screen = _read(
        root,
        'frontend/lib/features/build_a_son/presentation/build_a_son_screen.dart',
      );

      final int chooseParent = _indexOfOrThrow(screen, "'Choose Parent'");
      final int inheritTraits = _indexOfOrThrow(screen, "'Inherit Traits'");
      final int nameAndPosition = _indexOfOrThrow(screen, "'Name & Position'");
      final int confirm = _indexOfOrThrow(screen, "'Confirm'");

      expect(chooseParent, lessThan(inheritTraits));
      expect(inheritTraits, lessThan(nameAndPosition));
      expect(nameAndPosition, lessThan(confirm));
      expect(screen, contains('_selectedTraits.length == 3'));
      expect(screen, contains('RequestSonPreviewDraft('));
      expect(screen, contains('createRequestSonOrder('));
      expect(screen, contains('payWithWallet('));
      expect(screen, contains('cancelCreationOrder('));
      expect(screen, contains('generateAfterPayment('));
      expect(screen, contains('_reconcileGeneratedOrder('));
      expect(screen, contains('fetchCreationOrder('));
    });

    test('backend truth boundary is explicit in the Build-a-Son client', () {
      final Directory root = _repoRoot();
      final String client = _read(
        root,
        'frontend/lib/features/build_a_son/data/build_a_son_creation_client.dart',
      );

      expect(client, contains('fetchRequestSonOptions'));
      expect(client, contains('previewRequestSon'));
      expect(client, contains('createRequestSonOrder'));
      expect(client, contains('payWithWallet'));
      expect(client, contains('cancelCreationOrder'));
      expect(client, contains('generateAfterPayment'));
      expect(client, isNot(contains('Random(')));
      expect(client, isNot(contains('walletGTC')));
    });
  });
}

Directory _repoRoot() {
  Directory current = Directory.current;
  while (true) {
    if (Directory(_join(current.path, 'frontend')).existsSync() &&
        Directory(_join(current.path, 'docs')).existsSync()) {
      return current;
    }
    final Directory parent = current.parent;
    if (parent.path == current.path) {
      throw StateError(
        'Could not locate GTEX repo root from ${Directory.current.path}',
      );
    }
    current = parent;
  }
}

String _read(Directory root, String relativePath) {
  final File file = File(_join(root.path, relativePath));
  expect(file.existsSync(), isTrue, reason: '$relativePath should exist');
  return file.readAsStringSync();
}

int _indexOfOrThrow(String source, String pattern) {
  final int index = source.indexOf(pattern);
  if (index == -1) {
    throw StateError('Missing expected source pattern: $pattern');
  }
  return index;
}

String _join(String left, String right) {
  final String separator = Platform.pathSeparator;
  return left.endsWith(separator) ? '$left$right' : '$left$separator$right';
}
