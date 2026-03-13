import 'package:flutter/material.dart';

import '../data/gte_api_repository.dart';

class AppFeedback {
  static String messageFor(Object error, {String fallback = 'Something went wrong. Please try again.'}) {
    if (error is GteApiException) {
      final String message = error.message.trim();
      return message.isEmpty ? fallback : _clean(message);
    }
    final String text = error.toString().trim();
    if (text.isEmpty) {
      return fallback;
    }
    return _clean(
      text
          .replaceFirst('Exception: ', '')
          .replaceFirst('HttpException: ', '')
          .replaceFirst(RegExp(r'^GteApiException\([^)]*\):\s*'), ''),
    );
  }

  static void showSuccess(BuildContext context, String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(_clean(message))),
    );
  }

  static void showError(BuildContext context, Object error, {String fallback = 'Something went wrong. Please try again.'}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(messageFor(error, fallback: fallback))),
    );
  }

  static String _clean(String value) {
    final String cleaned = value.trim();
    if (cleaned.isEmpty) {
      return 'Something went wrong. Please try again.';
    }
    return cleaned[0].toUpperCase() + cleaned.substring(1);
  }
}
