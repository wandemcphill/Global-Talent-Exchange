import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/club_creation_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/screens/clubs/club_location_fields.dart';
import 'package:gte_frontend/screens/clubs/create_club_screen.dart';

/// In-memory stand-in for `POST /api/clubs` that echoes what the request
/// contract (`GteCreateClubRequest.toJson`) would persist.
class _FakeClubCreationApi implements ClubCreationApi {
  final List<Map<String, Object?>> posted = <Map<String, Object?>>[];

  @override
  GteAuthedApi get client => throw UnimplementedError();

  @override
  Future<GteCreatedClubProfile> createClub(GteCreateClubRequest request) async {
    final Map<String, Object?> body = Map<String, Object?>.from(
      request.toJson(),
    );
    posted.add(body);
    return GteCreatedClubProfile.fromJson(<String, Object?>{
      'id': 'club-${posted.length}',
      'club_name': body['club_name'],
      'slug': body['slug'],
      'country_code': body['country_code'],
      'region_name': body['region_name'],
      'city_name': body['city_name'],
    });
  }
}

Future<void> _pump(
  WidgetTester tester,
  _FakeClubCreationApi api, {
  Size size = const Size(1200, 2400),
  ValueChanged<GteCreatedClubProfile>? onCreated,
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  await tester.pumpWidget(
    MaterialApp(
      home: CreateClubScreen(
        baseUrl: 'http://localhost',
        accessToken: 'token',
        backendMode: GteBackendMode.live,
        api: api,
        onClubCreated: onCreated,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

Future<void> _fillClub(WidgetTester tester, {required String country, required String city}) async {
  await tester.enterText(find.widgetWithText(TextField, 'Club name'), 'Harbor United');
  await tester.enterText(
    find.descendant(
      of: find.byKey(const ValueKey<String>('club-location-country')),
      matching: find.byType(TextField),
    ),
    country,
  );
  await tester.pumpAndSettle();
  await tester.enterText(
    find.descendant(
      of: find.byWidgetPredicate(
        (Widget w) => w.key.toString().contains('club-location-city-'),
      ),
      matching: find.byType(TextField),
    ),
    city,
  );
  await tester.pumpAndSettle();
}

Future<void> _submit(WidgetTester tester) async {
  final Finder button = find.text('Create club');
  await tester.ensureVisible(button);
  await tester.tap(button);
  await tester.pumpAndSettle();
}

void main() {
  group('club location catalog', () {
    test('resolves labels, names and codes', () {
      expect(resolveClubCountry('Ghana (GH)')?.code, 'GH');
      expect(resolveClubCountry("cote d'ivoire")?.code, 'CI');
      expect(resolveClubCountry('br')?.code, 'BR');
      expect(resolveClubCountry('Atlantis'), isNull);
    });

    test('controller starts empty and normalizes selections', () {
      final ClubLocationController c = ClubLocationController();
      addTearDown(c.dispose);
      expect(c.validate(), isNotNull);
      expect(c.selection, isNull);
      c.setCountryText('Ghana');
      c.setCity('kumasi');
      expect(c.region.text, 'Ashanti');
      final ClubLocationSelection s = c.selection!;
      expect(s.countryCode, 'GH');
      expect(s.cityName, 'Kumasi');
      expect(s.regionName, 'Ashanti');
      c.setCountryText('Spain');
      expect(c.city, '');
      expect(c.region.text, '');
      expect(c.selection, isNull);
    });
  });

  group('CreateClubScreen location', () {
    testWidgets('has no default country and blocks submission', (tester) async {
      final _FakeClubCreationApi api = _FakeClubCreationApi();
      await _pump(tester, api);
      await tester.enterText(find.widgetWithText(TextField, 'Club name'), 'Harbor United');
      await _submit(tester);
      expect(api.posted, isEmpty);
      expect(find.text("Select the club's country."), findsWidgets);
      expect(find.text('Nigeria (NG)'), findsNothing);
    });

    for (final List<String> row in <List<String>>[
      <String>['Ghana (GH)', 'Kumasi', 'GH', 'Ashanti'],
      <String>['Brazil', 'são paulo', 'BR', 'São Paulo'],
      <String>['Nigeria', 'Port Harcourt', 'NG', 'Rivers'],
    ]) {
      testWidgets('persists ${row[0]} / ${row[1]} and reads it back', (tester) async {
        final _FakeClubCreationApi api = _FakeClubCreationApi();
        GteCreatedClubProfile? created;
        await _pump(tester, api, onCreated: (GteCreatedClubProfile p) => created = p);
        await _fillClub(tester, country: row[0], city: row[1]);
        await _submit(tester);

        expect(api.posted, hasLength(1));
        expect(api.posted.single['country_code'], row[2]);
        expect(api.posted.single['region_name'], row[3]);
        expect((api.posted.single['city_name']! as String).toLowerCase(), row[1].toLowerCase());
        // The created profile (what a refresh would read back) carries the same values.
        expect(created?.countryCode, row[2]);
        expect(created?.regionName, row[3]);
      });
    }

    testWidgets('lays out without overflow on a narrow phone', (tester) async {
      final _FakeClubCreationApi api = _FakeClubCreationApi();
      await _pump(tester, api, size: const Size(360, 900));
      expect(tester.takeException(), isNull);
      expect(find.text('Region / state'), findsOneWidget);
    });
  });
}
