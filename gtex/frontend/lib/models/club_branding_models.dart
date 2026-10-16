class ClubBrandingTheme {
  const ClubBrandingTheme({
    required this.id,
    required this.name,
    required this.description,
    required this.bannerLabel,
    required this.primaryColor,
    required this.secondaryColor,
    required this.accentColor,
  });

  final String id;
  final String name;
  final String description;
  final String bannerLabel;
  final String primaryColor;
  final String secondaryColor;
  final String accentColor;

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'id': id,
      'name': name,
      'description': description,
      'banner_label': bannerLabel,
      'primary_color': primaryColor,
      'secondary_color': secondaryColor,
      'accent_color': accentColor,
    };
  }
}

class ClubShowcaseBackdrop {
  const ClubShowcaseBackdrop({
    required this.id,
    required this.name,
    required this.description,
    required this.gradientColors,
    required this.caption,
  });

  final String id;
  final String name;
  final String description;
  final List<String> gradientColors;
  final String caption;

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'id': id,
      'name': name,
      'description': description,
      'gradient_colors': gradientColors,
      'caption': caption,
    };
  }
}

class ClubBrandingProfile {
  const ClubBrandingProfile({
    required this.selectedThemeId,
    required this.selectedBackdropId,
    required this.motto,
    required this.availableThemes,
    required this.availableBackdrops,
    required this.reviewStatus,
    required this.reviewNote,
  });

  final String selectedThemeId;
  final String selectedBackdropId;
  final String motto;
  final List<ClubBrandingTheme> availableThemes;
  final List<ClubShowcaseBackdrop> availableBackdrops;
  final String reviewStatus;
  final String reviewNote;

  ClubBrandingTheme get selectedTheme {
    return availableThemes.firstWhere(
      (ClubBrandingTheme theme) => theme.id == selectedThemeId,
      orElse: () => availableThemes.first,
    );
  }

  ClubShowcaseBackdrop get selectedBackdrop {
    return availableBackdrops.firstWhere(
      (ClubShowcaseBackdrop backdrop) => backdrop.id == selectedBackdropId,
      orElse: () => availableBackdrops.first,
    );
  }

  ClubBrandingProfile copyWith({
    String? selectedThemeId,
    String? selectedBackdropId,
    String? motto,
    List<ClubBrandingTheme>? availableThemes,
    List<ClubShowcaseBackdrop>? availableBackdrops,
    String? reviewStatus,
    String? reviewNote,
  }) {
    return ClubBrandingProfile(
      selectedThemeId: selectedThemeId ?? this.selectedThemeId,
      selectedBackdropId: selectedBackdropId ?? this.selectedBackdropId,
      motto: motto ?? this.motto,
      availableThemes: availableThemes ?? this.availableThemes,
      availableBackdrops: availableBackdrops ?? this.availableBackdrops,
      reviewStatus: reviewStatus ?? this.reviewStatus,
      reviewNote: reviewNote ?? this.reviewNote,
    );
  }

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'selected_theme_id': selectedThemeId,
      'selected_backdrop_id': selectedBackdropId,
      'motto': motto,
      'available_themes': availableThemes
          .map((ClubBrandingTheme theme) => theme.toJson())
          .toList(growable: false),
      'available_backdrops': availableBackdrops
          .map((ClubShowcaseBackdrop backdrop) => backdrop.toJson())
          .toList(growable: false),
      'review_status': reviewStatus,
      'review_note': reviewNote,
    };
  }
}

class BrandingReviewCase {
  const BrandingReviewCase({
    required this.id,
    required this.clubName,
    required this.submittedAtLabel,
    required this.themeName,
    required this.backdropName,
    required this.motto,
    required this.statusLabel,
    required this.reviewNote,
  });

  final String id;
  final String clubName;
  final String submittedAtLabel;
  final String themeName;
  final String backdropName;
  final String motto;
  final String statusLabel;
  final String reviewNote;

  BrandingReviewCase copyWith({
    String? statusLabel,
    String? reviewNote,
  }) {
    return BrandingReviewCase(
      id: id,
      clubName: clubName,
      submittedAtLabel: submittedAtLabel,
      themeName: themeName,
      backdropName: backdropName,
      motto: motto,
      statusLabel: statusLabel ?? this.statusLabel,
      reviewNote: reviewNote ?? this.reviewNote,
    );
  }
}
