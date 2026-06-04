enum GtexSurfaceState {
  loading,
  empty,
  blocked,
  pending,
  syncing,
  reconnecting,
  degraded,
  confirmed,
  error;

  static const GtexSurfaceState data = GtexSurfaceState.confirmed;
}

extension GtexSurfaceStateX on GtexSurfaceState {
  bool get isOperational {
    switch (this) {
      case GtexSurfaceState.confirmed:
      case GtexSurfaceState.syncing:
      case GtexSurfaceState.pending:
        return true;
      case GtexSurfaceState.loading:
      case GtexSurfaceState.empty:
      case GtexSurfaceState.blocked:
      case GtexSurfaceState.reconnecting:
      case GtexSurfaceState.degraded:
      case GtexSurfaceState.error:
        return false;
    }
  }

  bool get requiresAttention {
    switch (this) {
      case GtexSurfaceState.blocked:
      case GtexSurfaceState.reconnecting:
      case GtexSurfaceState.degraded:
      case GtexSurfaceState.error:
        return true;
      case GtexSurfaceState.loading:
      case GtexSurfaceState.empty:
      case GtexSurfaceState.pending:
      case GtexSurfaceState.syncing:
      case GtexSurfaceState.confirmed:
        return false;
    }
  }
}
