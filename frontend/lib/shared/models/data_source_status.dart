enum DataSourceStatus { live, blocked, demo }

extension DataSourceStatusLabel on DataSourceStatus {
  String get label {
    return switch (this) {
      DataSourceStatus.live => 'LIVE',
      DataSourceStatus.blocked => 'BLOCKED',
      DataSourceStatus.demo => 'DEMO',
    };
  }
}
