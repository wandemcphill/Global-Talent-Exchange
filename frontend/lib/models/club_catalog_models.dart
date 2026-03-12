enum CatalogOwnershipStatus {
  available,
  owned,
  equipped,
}

extension CatalogOwnershipStatusX on CatalogOwnershipStatus {
  String get label {
    switch (this) {
      case CatalogOwnershipStatus.available:
        return 'Available';
      case CatalogOwnershipStatus.owned:
        return 'Owned';
      case CatalogOwnershipStatus.equipped:
        return 'Equipped';
    }
  }
}

class ClubCatalogItem {
  const ClubCatalogItem({
    required this.id,
    required this.title,
    required this.category,
    required this.slot,
    required this.description,
    required this.priceCredits,
    required this.highlightColor,
    required this.previewLabel,
    required this.transparencyNote,
    required this.ownershipStatus,
    this.isFeatured = false,
  });

  final String id;
  final String title;
  final String category;
  final String slot;
  final String description;
  final double priceCredits;
  final String highlightColor;
  final String previewLabel;
  final String transparencyNote;
  final CatalogOwnershipStatus ownershipStatus;
  final bool isFeatured;

  bool get canPurchase => ownershipStatus == CatalogOwnershipStatus.available;
  bool get canEquip => ownershipStatus == CatalogOwnershipStatus.owned;

  ClubCatalogItem copyWith({
    CatalogOwnershipStatus? ownershipStatus,
  }) {
    return ClubCatalogItem(
      id: id,
      title: title,
      category: category,
      slot: slot,
      description: description,
      priceCredits: priceCredits,
      highlightColor: highlightColor,
      previewLabel: previewLabel,
      transparencyNote: transparencyNote,
      ownershipStatus: ownershipStatus ?? this.ownershipStatus,
      isFeatured: isFeatured,
    );
  }
}

class ClubPurchaseRecord {
  const ClubPurchaseRecord({
    required this.id,
    required this.itemId,
    required this.itemTitle,
    required this.category,
    required this.purchasedAt,
    required this.priceCredits,
    required this.confirmationLabel,
    required this.statusLabel,
    required this.transparencyNote,
    required this.equipped,
  });

  final String id;
  final String itemId;
  final String itemTitle;
  final String category;
  final DateTime purchasedAt;
  final double priceCredits;
  final String confirmationLabel;
  final String statusLabel;
  final String transparencyNote;
  final bool equipped;

  ClubPurchaseRecord copyWith({
    bool? equipped,
    String? statusLabel,
  }) {
    return ClubPurchaseRecord(
      id: id,
      itemId: itemId,
      itemTitle: itemTitle,
      category: category,
      purchasedAt: purchasedAt,
      priceCredits: priceCredits,
      confirmationLabel: confirmationLabel,
      statusLabel: statusLabel ?? this.statusLabel,
      transparencyNote: transparencyNote,
      equipped: equipped ?? this.equipped,
    );
  }
}
