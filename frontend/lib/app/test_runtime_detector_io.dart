import 'dart:io';

bool get isFlutterTestRuntime => Platform.environment['FLUTTER_TEST'] == 'true';
