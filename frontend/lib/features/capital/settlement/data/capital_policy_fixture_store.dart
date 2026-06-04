import 'package:gte_frontend/data/gte_models.dart';

class CapitalPolicyFixtureStore {
  CapitalPolicyFixtureStore.seeded()
    : documents = List<GtePolicyDocumentDetail>.of(
        seedPolicyDocuments,
        growable: true,
      ),
      acceptances = List<GtePolicyAcceptanceSummary>.of(
        seedPolicyAcceptances,
        growable: true,
      );

  final List<GtePolicyDocumentDetail> documents;
  final List<GtePolicyAcceptanceSummary> acceptances;

  List<GtePolicyDocumentSummary> fetchPolicyDocuments({
    bool mandatoryOnly = false,
  }) {
    final Iterable<GtePolicyDocumentDetail> docs =
        mandatoryOnly
            ? documents.where((GtePolicyDocumentDetail doc) => doc.isMandatory)
            : documents;
    return docs
        .map(
          (GtePolicyDocumentDetail doc) => GtePolicyDocumentSummary(
            id: doc.id,
            documentKey: doc.documentKey,
            title: doc.title,
            isMandatory: doc.isMandatory,
            active: doc.active,
            latestVersion: doc.latestVersion,
          ),
        )
        .toList(growable: false);
  }

  GtePolicyDocumentDetail fetchPolicyDocument(
    String documentKey, {
    String? versionLabel,
  }) {
    return documents.firstWhere(
      (GtePolicyDocumentDetail doc) => doc.documentKey == documentKey,
      orElse: () => throw StateError('Unknown policy document: $documentKey'),
    );
  }

  GteComplianceStatus fetchComplianceStatus({required String countryCode}) {
    final List<GtePolicyRequirementSummary> missing =
        currentMissingPolicyRequirements();
    return GteComplianceStatus(
      countryCode: countryCode,
      countryPolicyBucket: 'regulated_market_disabled',
      depositsEnabled: true,
      marketTradingEnabled: true,
      platformRewardWithdrawalsEnabled: true,
      complianceStatus: 'verified',
      requiredPolicyAcceptancesMissing: missing.length,
      missingPolicyAcceptances: missing,
      canDeposit: true,
      canWithdrawPlatformRewards: true,
      canTradeMarket: true,
    );
  }

  List<GtePolicyRequirementSummary> currentMissingPolicyRequirements() {
    final Set<String> acceptedKeys =
        acceptances
            .map((GtePolicyAcceptanceSummary item) => item.documentKey)
            .toSet();
    return documents
        .where(
          (GtePolicyDocumentDetail doc) =>
              doc.isMandatory && !acceptedKeys.contains(doc.documentKey),
        )
        .map(
          (GtePolicyDocumentDetail doc) => GtePolicyRequirementSummary(
            documentKey: doc.documentKey,
            title: doc.title,
            versionLabel: doc.latestVersion?.versionLabel ?? 'v1.0',
            isMandatory: doc.isMandatory,
            effectiveAt: doc.latestVersion?.effectiveAt,
          ),
        )
        .toList(growable: false);
  }

  List<GtePolicyAcceptanceSummary> fetchMyPolicyAcceptances() {
    return List<GtePolicyAcceptanceSummary>.of(acceptances, growable: false);
  }

  GtePolicyAcceptanceSummary acceptPolicyDocument({
    required String documentKey,
    required String versionLabel,
    required DateTime acceptedAt,
  }) {
    final GtePolicyDocumentDetail document = fetchPolicyDocument(documentKey);
    final int existingIndex = acceptances.indexWhere(
      (GtePolicyAcceptanceSummary item) => item.documentKey == documentKey,
    );
    final GtePolicyAcceptanceSummary acceptance = GtePolicyAcceptanceSummary(
      documentKey: documentKey,
      title: document.title,
      versionLabel: versionLabel,
      acceptedAt: acceptedAt,
    );
    if (existingIndex >= 0) {
      acceptances[existingIndex] = acceptance;
    } else {
      acceptances.add(acceptance);
    }
    return acceptance;
  }

  static final List<GtePolicyDocumentDetail> seedPolicyDocuments =
      <GtePolicyDocumentDetail>[
        GtePolicyDocumentDetail(
          id: 'policy-terms',
          documentKey: 'terms_and_conditions',
          title: 'Terms & Conditions',
          isMandatory: true,
          active: true,
          latestVersion: GtePolicyDocumentVersionSummary(
            id: 'policy-terms-v1',
            versionLabel: 'v1.0',
            effectiveAt: DateTime.utc(2026, 3, 1),
            publishedAt: DateTime.utc(2026, 3, 1),
            changelog: 'Initial public release.',
          ),
          bodyMarkdown: '''# Terms & Conditions

GTEX is a rules-driven football competition and exchange platform. Use of wallet, competition, and reward surfaces is subject to market rules, integrity controls, and local availability.''',
        ),
        GtePolicyDocumentDetail(
          id: 'policy-privacy',
          documentKey: 'privacy_policy',
          title: 'Privacy Policy',
          isMandatory: true,
          active: true,
          latestVersion: GtePolicyDocumentVersionSummary(
            id: 'policy-privacy-v1',
            versionLabel: 'v1.0',
            effectiveAt: DateTime.utc(2026, 3, 1),
            publishedAt: DateTime.utc(2026, 3, 1),
            changelog: 'Initial public release.',
          ),
          bodyMarkdown: '''# Privacy Policy

We collect account, KYC, payment proof, and gameplay telemetry needed to operate GTEX, detect abuse, and satisfy moderation, anti-fraud, and regional controls.''',
        ),
        GtePolicyDocumentDetail(
          id: 'policy-withdrawal',
          documentKey: 'withdrawal_policy',
          title: 'Withdrawal Policy',
          isMandatory: true,
          active: true,
          latestVersion: GtePolicyDocumentVersionSummary(
            id: 'policy-withdrawal-v1',
            versionLabel: 'v1.0',
            effectiveAt: DateTime.utc(2026, 3, 1),
            publishedAt: DateTime.utc(2026, 3, 1),
            changelog:
                'Clarifies KYC, bank account, and regional restrictions.',
          ),
          bodyMarkdown: '''# Withdrawal Policy

Withdrawals depend on KYC state, verified bank details, active policy acceptance, treasury review, and regional feature flags.''',
        ),
      ];

  static final List<GtePolicyAcceptanceSummary> seedPolicyAcceptances =
      <GtePolicyAcceptanceSummary>[
        GtePolicyAcceptanceSummary(
          documentKey: 'terms_and_conditions',
          title: 'Terms & Conditions',
          versionLabel: 'v1.0',
          acceptedAt: DateTime.utc(2026, 3, 2, 10),
        ),
      ];
}
