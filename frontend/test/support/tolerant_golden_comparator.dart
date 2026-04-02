import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';

class TolerantGoldenFileComparator extends LocalFileComparator {
  TolerantGoldenFileComparator(
    super.testFile, {
    required double precisionTolerance,
  }) : assert(
         0 <= precisionTolerance && precisionTolerance <= 1,
         'precisionTolerance must be between 0 and 1',
       ),
       _precisionTolerance = precisionTolerance;

  final double _precisionTolerance;

  @override
  Future<bool> compare(Uint8List imageBytes, Uri golden) async {
    final ComparisonResult result = await GoldenFileComparator.compareLists(
      imageBytes,
      await getGoldenBytes(golden),
    );

    if (result.passed || result.diffPercent <= _precisionTolerance) {
      result.dispose();
      return true;
    }

    final String error = await generateFailureOutput(result, golden, basedir);
    result.dispose();
    throw FlutterError(
      '$error\n'
      'Allowed diff: ${(_precisionTolerance * 100).toStringAsFixed(2)}%',
    );
  }
}

void installTolerantGoldenComparator({
  required String testFilePath,
  required double precisionTolerance,
}) {
  final GoldenFileComparator previousComparator = goldenFileComparator;
  goldenFileComparator = TolerantGoldenFileComparator(
    Uri.parse(testFilePath),
    precisionTolerance: precisionTolerance,
  );
  addTearDown(() => goldenFileComparator = previousComparator);
}
