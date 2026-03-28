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
        return 'Fast match';
    }
  }

  String get entryStateLabel {
    switch (this) {
      case MatchType.gtexHosted:
        return 'FREE ENTRY';
      case MatchType.userHosted:
        return 'ENTRY FEE';
      case MatchType.fastMatch:
        return 'FAST MATCH';
    }
  }

  String get actionLabel {
    switch (this) {
      case MatchType.gtexHosted:
        return 'Join Free';
      case MatchType.userHosted:
      case MatchType.fastMatch:
        return 'Pay & Join';
    }
  }

  String get walletNotice {
    switch (this) {
      case MatchType.gtexHosted:
        return 'GTEX competitions are free to enter and pay out on published results.';
      case MatchType.userHosted:
        return 'User-hosted matches require an entry fee before your place is confirmed.';
      case MatchType.fastMatch:
        return 'Fast Match is always paid and uses your wallet balance immediately.';
    }
  }
}
