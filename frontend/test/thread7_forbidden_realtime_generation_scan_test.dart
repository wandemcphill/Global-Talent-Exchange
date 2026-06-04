import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('production realtime and notification code does not synthesize events', () {
    final Directory repoRoot = _findRepoRoot();
    final List<File> files = _productionRealtimeFiles(repoRoot);
    final List<String> violations = <String>[];

    for (final File file in files) {
      final String relativePath = _relativePath(repoRoot, file);
      final List<String> lines = file.readAsLinesSync();
      for (int index = 0; index < lines.length; index += 1) {
        final String line = lines[index];
        if (_forbiddenPatterns.any(
          (RegExp pattern) => pattern.hasMatch(line),
        )) {
          violations.add('$relativePath:${index + 1}: ${line.trim()}');
        }
      }
    }

    expect(
      violations,
      isEmpty,
      reason:
          'Production realtime/notification paths must consume backend streams '
          'instead of fake, demo, random, synthetic, or timer-generated events.',
    );
  });
}

final List<RegExp> _forbiddenPatterns = <RegExp>[
  RegExp(r'\bStream\.periodic\b'),
  RegExp(r'\bTimer\.periodic\b'),
  RegExp(r'\bFuture\.delayed\b'),
  RegExp(r'\bRandom\s*\('),
  RegExp(r'''import\s+['"]dart:math['"]'''),
  RegExp(r'\b(fake|demo|synthetic|mock)\b', caseSensitive: false),
];

List<File> _productionRealtimeFiles(Directory repoRoot) {
  final List<String> roots = <String>[
    'frontend/lib/features/shell/realtime',
    'frontend/lib/features/match_center/realtime',
    'frontend/lib/features/notifications',
    'frontend/lib/shared/realtime',
  ];
  final List<String> extraFiles = <String>[
    'frontend/lib/features/shell/providers/gtex_realtime_providers.dart',
    'frontend/lib/features/shell/widgets/gtex_realtime_widgets.dart',
  ];

  final List<File> files = <File>[
    for (final String root in roots)
      if (Directory(_join(repoRoot.path, root)).existsSync())
        ...Directory(_join(repoRoot.path, root))
            .listSync(recursive: true)
            .whereType<File>()
            .where((File file) => file.path.endsWith('.dart')),
    for (final String path in extraFiles) File(_join(repoRoot.path, path)),
  ];
  files.sort((File a, File b) => a.path.compareTo(b.path));
  return files;
}

Directory _findRepoRoot() {
  Directory current = Directory.current;
  while (true) {
    if (File(_join(current.path, 'frontend/pubspec.yaml')).existsSync()) {
      return current;
    }
    final Directory parent = current.parent;
    if (parent.path == current.path) {
      throw StateError(
        'Could not find repository root from ${Directory.current}',
      );
    }
    current = parent;
  }
}

String _relativePath(Directory root, File file) {
  final String rootPath =
      root.path.endsWith(Platform.pathSeparator)
          ? root.path
          : '${root.path}${Platform.pathSeparator}';
  return file.path.startsWith(rootPath)
      ? file.path.substring(rootPath.length)
      : file.path;
}

String _join(String left, String right) {
  final String separator = Platform.pathSeparator;
  final String normalizedRight = right.replaceAll('/', separator);
  return left.endsWith(separator)
      ? '$left$normalizedRight'
      : '$left$separator$normalizedRight';
}
