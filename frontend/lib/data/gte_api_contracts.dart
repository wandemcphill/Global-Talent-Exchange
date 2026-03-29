class FeedSource {
  FeedSource._();

  static const String forYou = 'for_you';
  static const String following = 'following';

  static const Set<String> values = <String>{forYou, following};
}

class FeedContractKeys {
  FeedContractKeys._();

  static const String feedSource = 'feed_source';
  static const String items = 'items';
}
