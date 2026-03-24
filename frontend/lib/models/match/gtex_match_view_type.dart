enum GtexMatchViewType {
  twoD,
  pseudo3D,
}

GtexMatchViewType gtexMatchViewTypeFromString(String? raw) {
  switch (raw?.trim().toLowerCase()) {
    case 'pseudo3d':
    case 'pseudo_3d':
    case '3d':
      return GtexMatchViewType.pseudo3D;
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
      case GtexMatchViewType.pseudo3D:
        return 'Broadcast+';
    }
  }

  bool get isPseudo3D => this == GtexMatchViewType.pseudo3D;
}
