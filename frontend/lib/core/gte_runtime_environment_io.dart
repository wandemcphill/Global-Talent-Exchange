import 'dart:io';

bool get isFlutterTestEnvironment =>
    Platform.environment['FLUTTER_TEST'] == 'true';
