import 'package:flutter/foundation.dart';

import '../core/app_feedback.dart';
import '../data/creator_application_api.dart';
import '../data/gte_api_repository.dart';
import '../models/creator_application_models.dart';

class CreatorApplicationController extends ChangeNotifier {
  CreatorApplicationController({
    required CreatorApplicationApi api,
  }) : _api = api;

  final CreatorApplicationApi _api;
  final GteRequestGate _loadGate = GteRequestGate();
  final GteRequestGate _submitGate = GteRequestGate();
  final GteRequestGate _emailGate = GteRequestGate();
  final GteRequestGate _phoneGate = GteRequestGate();

  bool hasLoadedOnce = false;
  bool isLoading = false;
  bool isSubmitting = false;
  bool isVerifyingEmail = false;
  bool isVerifyingPhone = false;

  String? errorMessage;
  String? submitError;
  String? verificationError;

  CreatorApplicationView? application;
  CreatorContactVerificationStatus verificationStatus =
      const CreatorContactVerificationStatus();

  Future<void> load({bool force = false}) async {
    if (isLoading && !force) {
      return;
    }
    final int requestId = _loadGate.begin();
    isLoading = true;
    errorMessage = null;
    notifyListeners();

    try {
      final CreatorApplicationView? nextApplication =
          await _api.fetchMyApplication();
      CreatorContactVerificationStatus nextVerification;
      if (nextApplication != null) {
        nextVerification = CreatorContactVerificationStatus(
          userId: nextApplication.userId,
          emailVerifiedAt: nextApplication.emailVerifiedAt,
          phoneVerifiedAt: nextApplication.phoneVerifiedAt,
        );
      } else {
        nextVerification = await _api.fetchVerificationStatus();
      }
      if (!_loadGate.isActive(requestId)) {
        return;
      }
      application = nextApplication;
      verificationStatus = nextVerification;
      hasLoadedOnce = true;
    } catch (error) {
      if (_loadGate.isActive(requestId)) {
        errorMessage = _normalizeMessage(error);
      }
    } finally {
      if (_loadGate.isActive(requestId)) {
        isLoading = false;
        notifyListeners();
      }
    }
  }

  Future<void> verifyEmail() async {
    final int requestId = _emailGate.begin();
    verificationError = null;
    isVerifyingEmail = true;
    notifyListeners();

    try {
      final CreatorContactVerificationStatus nextStatus =
          await _api.verifyEmail();
      if (!_emailGate.isActive(requestId)) {
        return;
      }
      verificationStatus = nextStatus;
      if (application != null) {
        application = application!.copyWith(
          emailVerifiedAt: nextStatus.emailVerifiedAt,
        );
      }
    } catch (error) {
      if (_emailGate.isActive(requestId)) {
        verificationError = _normalizeMessage(error);
      }
    } finally {
      if (_emailGate.isActive(requestId)) {
        isVerifyingEmail = false;
        notifyListeners();
      }
    }
  }

  Future<void> verifyPhone() async {
    final int requestId = _phoneGate.begin();
    verificationError = null;
    isVerifyingPhone = true;
    notifyListeners();

    try {
      final CreatorContactVerificationStatus nextStatus =
          await _api.verifyPhone();
      if (!_phoneGate.isActive(requestId)) {
        return;
      }
      verificationStatus = nextStatus;
      if (application != null) {
        application = application!.copyWith(
          phoneVerifiedAt: nextStatus.phoneVerifiedAt,
        );
      }
    } catch (error) {
      if (_phoneGate.isActive(requestId)) {
        verificationError = _normalizeMessage(error);
      }
    } finally {
      if (_phoneGate.isActive(requestId)) {
        isVerifyingPhone = false;
        notifyListeners();
      }
    }
  }

  Future<void> submitApplication(
    CreatorApplicationSubmitRequest request,
  ) async {
    final int requestId = _submitGate.begin();
    submitError = null;
    isSubmitting = true;
    notifyListeners();

    try {
      final CreatorApplicationView nextApplication =
          await _api.submitApplication(request);
      if (!_submitGate.isActive(requestId)) {
        return;
      }
      application = nextApplication;
      verificationStatus = verificationStatus.copyWith(
        userId: nextApplication.userId,
        emailVerifiedAt: nextApplication.emailVerifiedAt,
        phoneVerifiedAt: nextApplication.phoneVerifiedAt,
      );
      hasLoadedOnce = true;
    } catch (error) {
      if (_submitGate.isActive(requestId)) {
        submitError = _normalizeMessage(error);
      }
    } finally {
      if (_submitGate.isActive(requestId)) {
        isSubmitting = false;
        notifyListeners();
      }
    }
  }

  String _normalizeMessage(Object error) {
    final String message = AppFeedback.messageFor(error);
    switch (message.toLowerCase()) {
      case 'email_verification_required':
        return 'Confirm the account email before you submit a creator request.';
      case 'phone_verification_required':
        return 'Confirm the account phone number before you submit a creator request.';
      case 'phone_number_required_for_creator_verification':
        return 'Add a phone number to this GTEX account before you request creator access.';
      case 'creator_already_approved':
      case 'creator_application_already_approved':
        return 'This account already has creator access.';
      case 'creator_handle_taken':
        return 'That creator handle is already taken.';
      case 'creator_application_not_found':
        return 'We could not find a creator application for this account.';
      default:
        return message;
    }
  }
}
