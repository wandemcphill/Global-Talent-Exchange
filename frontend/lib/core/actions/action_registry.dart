class ActionRegistration {
  const ActionRegistration({
    required this.action,
    required this.api,
    required this.eventType,
  });

  final String action;
  final String api;
  final String eventType;

  Map<String, String> toJson() {
    return <String, String>{'api': api, 'event_type': eventType};
  }
}

class ActionRegistry {
  ActionRegistry({Map<String, ActionRegistration>? registrations})
    : _registrations = Map<String, ActionRegistration>.unmodifiable(
        registrations ?? defaultRegistrations,
      );

  static const String clipEventsApi = 'POST /events/clip';

  static final Map<String, ActionRegistration> defaultRegistrations =
      <String, ActionRegistration>{
        'like': const ActionRegistration(
          action: 'like',
          api: clipEventsApi,
          eventType: 'like',
        ),
        'share': const ActionRegistration(
          action: 'share',
          api: clipEventsApi,
          eventType: 'share',
        ),
        'scroll': const ActionRegistration(
          action: 'scroll',
          api: clipEventsApi,
          eventType: 'scroll',
        ),
        'complete': const ActionRegistration(
          action: 'complete',
          api: clipEventsApi,
          eventType: 'complete',
        ),
      };

  final Map<String, ActionRegistration> _registrations;

  Map<String, ActionRegistration> get registrations => _registrations;

  ActionRegistration resolve(String action) {
    final ActionRegistration? registration = _registrations[action];
    if (registration != null) {
      return registration;
    }
    final StateError error = StateError(
      'Missing ActionRegistry entry for "$action".',
    );
    assert(() {
      throw error;
    }());
    throw error;
  }
}
