import 'package:flutter/foundation.dart';

@immutable
class GtexLandingMetric {
  const GtexLandingMetric({required this.label, required this.value, this.detail});

  final String label;
  final String value;
  final String? detail;
}

@immutable
class GtexOnboardingStep {
  const GtexOnboardingStep({
    required this.id,
    required this.title,
    required this.description,
    required this.completed,
    required this.ctaLabel,
  });

  final String id;
  final String title;
  final String description;
  final bool completed;
  final String ctaLabel;
}

@immutable
class GtexRegionOption {
  const GtexRegionOption({
    required this.code,
    required this.name,
    required this.marketCount,
    required this.featuredLeagues,
  });

  final String code;
  final String name;
  final int marketCount;
  final List<String> featuredLeagues;
}

@immutable
class GtexRoleOption {
  const GtexRoleOption({
    required this.id,
    required this.title,
    required this.description,
    required this.highlights,
  });

  final String id;
  final String title;
  final String description;
  final List<String> highlights;
}

@immutable
class GtexOnboardingState {
  const GtexOnboardingState({
    required this.selectedRoleId,
    required this.selectedRegionCode,
    required this.steps,
    required this.regions,
    required this.roles,
  });

  final String selectedRoleId;
  final String selectedRegionCode;
  final List<GtexOnboardingStep> steps;
  final List<GtexRegionOption> regions;
  final List<GtexRoleOption> roles;

  GtexOnboardingState copyWith({
    String? selectedRoleId,
    String? selectedRegionCode,
    List<GtexOnboardingStep>? steps,
    List<GtexRegionOption>? regions,
    List<GtexRoleOption>? roles,
  }) {
    return GtexOnboardingState(
      selectedRoleId: selectedRoleId ?? this.selectedRoleId,
      selectedRegionCode: selectedRegionCode ?? this.selectedRegionCode,
      steps: steps ?? this.steps,
      regions: regions ?? this.regions,
      roles: roles ?? this.roles,
    );
  }
}
