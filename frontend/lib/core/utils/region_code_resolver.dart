import 'package:flutter/widgets.dart';

String resolveRegionCode({
  String? localeCountryCode,
  String? platformCountryCode,
  String fallback = 'GLOBAL',
}) {
  final String? localeCode = normalizeRegionCode(localeCountryCode);
  if (localeCode != null) {
    return localeCode;
  }
  final String? platformCode = normalizeRegionCode(platformCountryCode);
  if (platformCode != null) {
    return platformCode;
  }
  return normalizeRegionCode(fallback) ?? 'GLOBAL';
}

String resolveRegionCodeForContext(
  BuildContext context, {
  String fallback = 'GLOBAL',
}) {
  return resolveRegionCode(
    localeCountryCode: Localizations.maybeLocaleOf(context)?.countryCode,
    platformCountryCode: WidgetsBinding.instance.platformDispatcher.locale.countryCode,
    fallback: fallback,
  );
}

String? normalizeRegionCode(String? value) {
  final String candidate = value?.trim().toUpperCase() ?? '';
  if (candidate.isEmpty) {
    return null;
  }
  final RegExp validPattern = RegExp(r'^[A-Z]{2,8}$');
  if (!validPattern.hasMatch(candidate)) {
    return null;
  }
  return candidate;
}
