import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_mock_api.dart';

GteApiRepository createCapitalFixtureRepository({
  Duration latency = Duration.zero,
}) {
  return GteMockApi.capitalFixtures(latency: latency);
}
