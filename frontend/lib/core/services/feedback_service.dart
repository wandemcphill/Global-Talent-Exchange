import 'package:flutter/services.dart';

class FeedbackService {
  const FeedbackService._();

  static Future<void> tap() => HapticFeedback.selectionClick();

  static Future<void> confirm() => HapticFeedback.lightImpact();
}
