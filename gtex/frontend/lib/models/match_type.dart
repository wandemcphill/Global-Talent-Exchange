enum MatchType { gtexHosted, userHosted, fastMatch }

extension MatchTypeX on MatchType {
  bool get isFree => this == MatchType.gtexHosted;

  bool get requiresWalletPayment => !isFree;

  bool get isFastMatch => this == MatchType.fastMatch;

  String get label {
    switch (this) {
      case MatchType.gtexHosted:
        return 'GTEX hosted';
      case MatchType.userHosted:
        return 'User hosted';
      case MatchType.fastMatch:
        return 'Quick Match';
    }
  }

  String get entryStateLabel {
    switch (this) {
      case MatchType.gtexHosted:
        return 'FREE ENTRY';
      case MatchType.userHosted:
        return 'ENTRY FEE';
      case MatchType.fastMatch:
        return 'QUICK MATCH';
    }
  }

  String get actionLabel {
    switch (this) {
      case MatchType.gtexHosted:
        return 'Join Free';
      case MatchType.userHosted:
      case MatchType.fastMatch:
        return 'Play Quick Match';
    }
  }

  String get walletNotice {
    switch (this) {
      case MatchType.gtexHosted:
        return 'GTEX competitions are free to enter and pay out on published results.';
      case MatchType.userHosted:
        return 'User-hosted matches require an entry fee before your place is confirmed.';
      case MatchType.fastMatch:
        return 'Fast Match entitlement is checked by the server before kickoff. Fan Coin applies only when the backend marks the account paid.';
    }
  }
}
