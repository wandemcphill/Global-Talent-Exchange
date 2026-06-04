enum GtexMatchViewType { twoD }

GtexMatchViewType gtexMatchViewTypeFromString(String? raw) {
  switch (raw?.trim().toLowerCase()) {
    case '2d':
    case 'twod':
    case 'two_d':
    default:
      return GtexMatchViewType.twoD;
  }
}

extension GtexMatchViewTypeX on GtexMatchViewType {
  String get label {
    switch (this) {
      case GtexMatchViewType.twoD:
        return '2D';
    }
  }

  GtexMatchViewType get canonical => GtexMatchViewType.twoD;

  bool get isLegacyQuarantined => false;

  bool get isAlternateProjection => false;
}
