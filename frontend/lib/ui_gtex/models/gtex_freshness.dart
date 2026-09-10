enum GtexFreshnessStatus {
  live,
  recent,
  pendingRecalculation,
  stale,
  unknown,
}

class GtexFreshnessInfo {
  const GtexFreshnessInfo({
    required this.status,
    this.asOf,
    this.label,
    this.pendingReason,
    this.staleReason,
  });

  final GtexFreshnessStatus status;
  final DateTime? asOf;
  final String? label;
  final String? pendingReason;
  final String? staleReason;

  factory GtexFreshnessInfo.fromJson(Map<String, dynamic>? json) {
    if (json == null) {
      return const GtexFreshnessInfo(status: GtexFreshnessStatus.unknown);
    }

    final String? rawStatus = json['status'] as String?;
    final GtexFreshnessStatus status = switch (rawStatus) {
      'LIVE' => GtexFreshnessStatus.live,
      'RECENT' => GtexFreshnessStatus.recent,
      'PENDING_RECALCULATION' => GtexFreshnessStatus.pendingRecalculation,
      'STALE' => GtexFreshnessStatus.stale,
      _ => GtexFreshnessStatus.unknown,
    };

    final String? rawAsOf = json['as_of'] as String?;
    final DateTime? asOf = rawAsOf != null ? DateTime.tryParse(rawAsOf) : null;

    return GtexFreshnessInfo(
      status: status,
      asOf: asOf,
      label: json['label'] as String?,
      pendingReason: json['pending_reason'] as String?,
      staleReason: json['stale_reason'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'status': status.name.toUpperCase(),
      if (asOf != null) 'as_of': asOf!.toIso8601String(),
      if (label != null) 'label': label,
      if (pendingReason != null) 'pending_reason': pendingReason,
      if (staleReason != null) 'stale_reason': staleReason,
    };
  }
}
