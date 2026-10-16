enum GtexMatchRenderMode {
  quick,
  standard,
  cinematic,
}

GtexMatchRenderMode gtexMatchRenderModeFromString(String? raw) {
  switch (raw?.trim().toLowerCase()) {
    case 'quick':
      return GtexMatchRenderMode.quick;
    case 'cinematic':
      return GtexMatchRenderMode.cinematic;
    case 'standard':
    default:
      return GtexMatchRenderMode.standard;
  }
}

extension GtexMatchRenderModeX on GtexMatchRenderMode {
  String get label {
    switch (this) {
      case GtexMatchRenderMode.quick:
        return 'Quick';
      case GtexMatchRenderMode.standard:
        return 'Standard';
      case GtexMatchRenderMode.cinematic:
        return 'Cinematic';
    }
  }

  int get minimumDurationSeconds {
    switch (this) {
      case GtexMatchRenderMode.quick:
        return 180;
      case GtexMatchRenderMode.standard:
        return 420;
      case GtexMatchRenderMode.cinematic:
        return 600;
    }
  }

  int get maximumDurationSeconds {
    switch (this) {
      case GtexMatchRenderMode.quick:
        return 300;
      case GtexMatchRenderMode.standard:
        return 600;
      case GtexMatchRenderMode.cinematic:
        return 900;
    }
  }

  double get viewerOnlyBeatDensity {
    switch (this) {
      case GtexMatchRenderMode.quick:
        return 0;
      case GtexMatchRenderMode.standard:
        return 0.45;
      case GtexMatchRenderMode.cinematic:
        return 1;
    }
  }

  double get cameraZoomBias {
    switch (this) {
      case GtexMatchRenderMode.quick:
        return 0.02;
      case GtexMatchRenderMode.standard:
        return 0.05;
      case GtexMatchRenderMode.cinematic:
        return 0.08;
    }
  }

  double get baseEventHoldSeconds {
    switch (this) {
      case GtexMatchRenderMode.quick:
        return 1.05;
      case GtexMatchRenderMode.standard:
        return 1.45;
      case GtexMatchRenderMode.cinematic:
        return 1.9;
    }
  }
}
