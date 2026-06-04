enum DataSourceStatus { live, blocked }

extension DataSourceStatusLabel on DataSourceStatus {
  String get label {
    return switch (this) {
      DataSourceStatus.live => 'LIVE',
      DataSourceStatus.blocked => 'BLOCKED',
    };
  }
}
