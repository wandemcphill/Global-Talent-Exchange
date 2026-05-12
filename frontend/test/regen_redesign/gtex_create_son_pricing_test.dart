import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/regen_redesign/models/gtex_regen_models.dart';

void main() {
  test('Create-a-Son draft estimates customization pricing', () {
    const GtexCreateSonPricing pricing = GtexCreateSonPricing(
      baseCostCoin: 100,
      nameCustomizationCoin: 10,
      nationalityCustomizationCoin: 20,
      positionCustomizationCoin: 30,
      specialRequestMinimumCoin: 40,
    );

    const GtexCreateSonDraft draft = GtexCreateSonDraft(
      parentPlayerId: 'p1',
      paymentMethod: 'wallet',
      requestedName: 'Junior',
      requestedCountryCode: 'NGA',
      requestedPosition: 'ST',
      specialRequest: 'Captain personality',
    );

    expect(draft.estimateCost(pricing), 200);
  });
}
