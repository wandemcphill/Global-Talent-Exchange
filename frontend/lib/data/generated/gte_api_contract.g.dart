// GENERATED CODE - DO NOT EDIT BY HAND.
// Source: shared/api_contract.json

const String gteApiContractVersion = '2';
const String gteApiVersionHeaderName = 'X-API-Version';
const String gteApiVersionHeaderValue = '2';

const Set<String> gteApiPublicExemptPaths = <String>{
  '/health',
  '/ready',
  '/version',
  '/docs',
  '/openapi.json',
  '/redoc',
};

const Set<String> gteApiPublicExemptPrefixes = <String>{
  '/generated-media',
  '/tts',
};

const Set<String> gteApiCanonicalPaths = <String>{
  '/api/v2/academy',
  '/api/v2/academy/awards',
  '/api/v2/academy/fixtures',
  '/api/v2/academy/generate',
  '/api/v2/academy/promote/{player_id}',
  '/api/v2/academy/qualification',
  '/api/v2/academy/registration',
  '/api/v2/academy/season-summary',
  '/api/v2/academy/standings',
  '/api/v2/admin-engine/bootstrap',
  '/api/v2/admin/access',
  '/api/v2/admin/access/permissions',
  '/api/v2/admin/access/{user_id}/permissions',
  '/api/v2/admin/admin-engine/calendar-rules',
  '/api/v2/admin/admin-engine/feature-flags',
  '/api/v2/admin/admin-engine/reward-rules',
  '/api/v2/admin/admin-engine/schedule-preview',
  '/api/v2/admin/analytics/agent-learning',
  '/api/v2/admin/analytics/anomalies',
  '/api/v2/admin/analytics/funnels',
  '/api/v2/admin/analytics/match-outcomes',
  '/api/v2/admin/analytics/player-matching',
  '/api/v2/admin/analytics/player-matching/recompute-weights',
  '/api/v2/admin/analytics/price-predictions',
  '/api/v2/admin/analytics/summary',
  '/api/v2/admin/analytics/user-segments',
  '/api/v2/admin/ban-user',
  '/api/v2/admin/broadcast-rights/jobs/run',
  '/api/v2/admin/calendar-engine/events',
  '/api/v2/admin/calendar-engine/hosted-competitions/{competition_id}/launch',
  '/api/v2/admin/calendar-engine/national-competitions/{competition_id}/launch',
  '/api/v2/admin/calendar-engine/seasons',
  '/api/v2/admin/club-infra/seed',
  '/api/v2/admin/clubs/academy-analytics',
  '/api/v2/admin/clubs/analytics',
  '/api/v2/admin/clubs/finance-analytics',
  '/api/v2/admin/clubs/ops-summary',
  '/api/v2/admin/clubs/scouting-analytics',
  '/api/v2/admin/clubs/sponsorship-analytics',
  '/api/v2/admin/clubs/summary',
  '/api/v2/admin/clubs/{club_id}',
  '/api/v2/admin/clubs/{club_id}/moderate-branding',
  '/api/v2/admin/competitions',
  '/api/v2/admin/competitions/reminders/dispatch',
  '/api/v2/admin/competitive-integrity/matches/{match_id}/validation',
  '/api/v2/admin/competitive-integrity/workers/run-once',
  '/api/v2/admin/config/liquidity-bands',
  '/api/v2/admin/config/player-card-market-integrity',
  '/api/v2/admin/config/supply-tiers',
  '/api/v2/admin/config/suspicion-thresholds',
  '/api/v2/admin/config/value-controls',
  '/api/v2/admin/config/value-controls/audits',
  '/api/v2/admin/config/value-controls/integrity/candidates',
  '/api/v2/admin/config/value-controls/players/{player_id}',
  '/api/v2/admin/config/value-controls/preview/{player_id}',
  '/api/v2/admin/config/value-controls/recompute',
  '/api/v2/admin/config/value-controls/run-history',
  '/api/v2/admin/creator-campaigns/{campaign_id}/metrics',
  '/api/v2/admin/creator/applications',
  '/api/v2/admin/creator/applications/{application_id}/approve',
  '/api/v2/admin/creator/applications/{application_id}/reject',
  '/api/v2/admin/creator/applications/{application_id}/request-verification',
  '/api/v2/admin/creator/cards/assign',
  '/api/v2/admin/creator/dashboard',
  '/api/v2/admin/creator/fan-share-market/control',
  '/api/v2/admin/discovery/featured-rails',
  '/api/v2/admin/disputes',
  '/api/v2/admin/disputes/{dispute_id}/assign',
  '/api/v2/admin/disputes/{dispute_id}/status',
  '/api/v2/admin/economy/burn-events',
  '/api/v2/admin/economy/fx-rates',
  '/api/v2/admin/economy/gift-catalog',
  '/api/v2/admin/economy/gift-combo-rules',
  '/api/v2/admin/economy/governor',
  '/api/v2/admin/economy/governor/apply',
  '/api/v2/admin/economy/governor/evaluate',
  '/api/v2/admin/economy/governor/policy',
  '/api/v2/admin/economy/regional-pricing',
  '/api/v2/admin/economy/revenue-share-rules',
  '/api/v2/admin/economy/service-pricing',
  '/api/v2/admin/fan-predictions/matches/{match_id}/fixture',
  '/api/v2/admin/fan-predictions/matches/{match_id}/settlement',
  '/api/v2/admin/fan-wars/creator-country-assignments',
  '/api/v2/admin/fan-wars/nations-cup',
  '/api/v2/admin/fan-wars/nations-cup/{competition_id}/advance',
  '/api/v2/admin/fan-wars/points',
  '/api/v2/admin/fan-wars/profiles',
  '/api/v2/admin/fan-wars/profiles/{profile_id}/rivals/{rival_profile_id}',
  '/api/v2/admin/federations/run-jobs',
  '/api/v2/admin/finance/account-controls',
  '/api/v2/admin/finance/account-controls/{user_id}',
  '/api/v2/admin/finance/control-tower',
  '/api/v2/admin/finance/manual-price-overrides',
  '/api/v2/admin/finance/manual-price-overrides/{asset_type}/{asset_id}',
  '/api/v2/admin/finance/match-kill-switches',
  '/api/v2/admin/finance/match-kill-switches/{match_id}',
  '/api/v2/admin/finance/reconciliation',
  '/api/v2/admin/finance/simulate',
  '/api/v2/admin/finance/wallet-protection',
  '/api/v2/admin/flags',
  '/api/v2/admin/football-events/categories',
  '/api/v2/admin/football-events/effects/expire',
  '/api/v2/admin/football-events/events',
  '/api/v2/admin/football-events/events/import',
  '/api/v2/admin/football-events/events/{event_id}/review',
  '/api/v2/admin/football-events/events/{event_id}/severity',
  '/api/v2/admin/football-events/rules',
  '/api/v2/admin/god-mode/audit-events',
  '/api/v2/admin/god-mode/bootstrap',
  '/api/v2/admin/god-mode/commissions',
  '/api/v2/admin/god-mode/competition-controls',
  '/api/v2/admin/god-mode/high-risk-actions',
  '/api/v2/admin/god-mode/liquidity/interventions',
  '/api/v2/admin/god-mode/payment-rails',
  '/api/v2/admin/god-mode/payment-rails/health',
  '/api/v2/admin/god-mode/roles',
  '/api/v2/admin/god-mode/treasury',
  '/api/v2/admin/god-mode/treasury/dashboard',
  '/api/v2/admin/god-mode/treasury/withdrawals',
  '/api/v2/admin/god-mode/withdrawal-controls',
  '/api/v2/admin/god-mode/withdrawals',
  '/api/v2/admin/god-mode/withdrawals/summary',
  '/api/v2/admin/god-mode/withdrawals/{payout_request_id}',
  '/api/v2/admin/governance/proposals/{proposal_id}/status',
  '/api/v2/admin/history-engagement/run-workers',
  '/api/v2/admin/hosted-competitions',
  '/api/v2/admin/hosted-competitions/seed',
  '/api/v2/admin/hosted-competitions/{competition_id}/finalize',
  '/api/v2/admin/hosted-competitions/{competition_id}/launch',
  '/api/v2/admin/integrity-engine/incidents/{incident_id}/resolve',
  '/api/v2/admin/integrity-engine/scan',
  '/api/v2/admin/jackpot/balance',
  '/api/v2/admin/jackpot/runtime',
  '/api/v2/admin/jackpot/trigger',
  '/api/v2/admin/leaderboard/season/archive',
  '/api/v2/admin/leaderboard/season/reset',
  '/api/v2/admin/managers/audit-log',
  '/api/v2/admin/managers/catalog/{manager_id}/supply',
  '/api/v2/admin/managers/competitions',
  '/api/v2/admin/managers/competitions/{code}',
  '/api/v2/admin/managers/competitions/{code}/orchestrate',
  '/api/v2/admin/media-engine/creator-league/clubs/{club_id}/stadium-level',
  '/api/v2/admin/media-engine/creator-league/matches/{match_id}/analytics',
  '/api/v2/admin/media-engine/creator-league/matches/{match_id}/settlement',
  '/api/v2/admin/media-engine/creator-league/stadium-controls',
  '/api/v2/admin/media-engine/exports',
  '/api/v2/admin/media-engine/highlights',
  '/api/v2/admin/media-engine/highlights/{storage_key:path}/archive',
  '/api/v2/admin/media-engine/share-exports/{export_id}/revenue-attributions',
  '/api/v2/admin/media-engine/snapshots',
  '/api/v2/admin/moderation/reports',
  '/api/v2/admin/moderation/reports/summary',
  '/api/v2/admin/moderation/reports/{report_id}/assign',
  '/api/v2/admin/moderation/reports/{report_id}/resolve',
  '/api/v2/admin/national-team-engine/competitions',
  '/api/v2/admin/national-team-engine/competitions/seed-defaults',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads/rotate',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads/{ad_id}',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/entries',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/entries/lock',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/lifecycle/advance',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/rentals/cleanup',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/story-events/generate',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/theme',
  '/api/v2/admin/national-team-engine/entries/{entry_id}/squad',
  '/api/v2/admin/notifications/announcements',
  '/api/v2/admin/ops/alerts',
  '/api/v2/admin/ops/audit',
  '/api/v2/admin/ops/broadcast-expiration',
  '/api/v2/admin/ops/broadcast-revenue',
  '/api/v2/admin/ops/club-market-valuations',
  '/api/v2/admin/ops/dashboard',
  '/api/v2/admin/ops/fan-updates',
  '/api/v2/admin/ops/identity-evolution',
  '/api/v2/admin/ops/integrity-scan',
  '/api/v2/admin/ops/media-generation',
  '/api/v2/admin/ops/media-retention',
  '/api/v2/admin/ops/national-team-rental-cleanup',
  '/api/v2/admin/ops/ownership-groups/reputation',
  '/api/v2/admin/ops/platform-infra',
  '/api/v2/admin/ops/stadium-ad-rotation',
  '/api/v2/admin/ops/tournament-storylines',
  '/api/v2/admin/ownership-groups/reputation-cycle',
  '/api/v2/admin/player-import/card-supply',
  '/api/v2/admin/player-import/card-supply/csv',
  '/api/v2/admin/player-import/jobs',
  '/api/v2/admin/player-import/jobs/{job_id}',
  '/api/v2/admin/player-import/youth/generate',
  '/api/v2/admin/policies/country-policies',
  '/api/v2/admin/policies/documents',
  '/api/v2/admin/policies/documents/versions',
  '/api/v2/admin/policies/regions/override',
  '/api/v2/admin/real-world/providers',
  '/api/v2/admin/real-world/providers/{provider_id}/sync',
  '/api/v2/admin/referrals/analytics/summary',
  '/api/v2/admin/referrals/attributions',
  '/api/v2/admin/referrals/creators',
  '/api/v2/admin/referrals/creators/{creator_id}',
  '/api/v2/admin/referrals/creators/{creator_id}/reward-freeze',
  '/api/v2/admin/referrals/dashboard',
  '/api/v2/admin/referrals/flags',
  '/api/v2/admin/referrals/leaderboard',
  '/api/v2/admin/referrals/rewards/pending',
  '/api/v2/admin/referrals/rewards/{reward_id}/review',
  '/api/v2/admin/referrals/share-codes',
  '/api/v2/admin/referrals/share-codes/{share_code_id}',
  '/api/v2/admin/referrals/share-codes/{share_code_id}/block',
  '/api/v2/admin/regen-universe/jobs/dna-evolution',
  '/api/v2/admin/regen-universe/jobs/rivalry-detection',
  '/api/v2/admin/regen-universe/jobs/story-regeneration',
  '/api/v2/admin/regen-universe/jobs/tournament-scheduling',
  '/api/v2/admin/regen-universe/national-regens/preseed',
  '/api/v2/admin/regen-universe/players/{player_id}/portrait/ban',
  '/api/v2/admin/regen-universe/players/{player_id}/portrait/override',
  '/api/v2/admin/regen-universe/players/{player_id}/portrait/regenerate',
  '/api/v2/admin/regen-universe/seasons',
  '/api/v2/admin/regen-universe/seasons/{season_id}/close',
  '/api/v2/admin/regen-universe/seasons/{season_id}/evolution',
  '/api/v2/admin/regen-universe/youth-tournaments',
  '/api/v2/admin/reward-engine/promo-pool/credits',
  '/api/v2/admin/reward-engine/settlements',
  '/api/v2/admin/risk-ops/actions',
  '/api/v2/admin/risk-ops/actions/{action_id}/release',
  '/api/v2/admin/risk-ops/aml-cases',
  '/api/v2/admin/risk-ops/audit-logs',
  '/api/v2/admin/risk-ops/cases/{case_type}/{case_id}/resolve',
  '/api/v2/admin/risk-ops/evaluate',
  '/api/v2/admin/risk-ops/fraud-cases',
  '/api/v2/admin/risk-ops/overview',
  '/api/v2/admin/risk-ops/scan',
  '/api/v2/admin/risk-ops/signals',
  '/api/v2/admin/risk-ops/system-events',
  '/api/v2/admin/sponsorship/analytics',
  '/api/v2/admin/sponsorship/categories/{category}',
  '/api/v2/admin/sponsorship/contracts/{contract_id}/review',
  '/api/v2/admin/sponsorship/contracts/{contract_id}/settle-next',
  '/api/v2/admin/sponsorship/offers',
  '/api/v2/admin/sponsorship/offers/{offer_id}/assign',
  '/api/v2/admin/sponsorship/offers/{offer_id}/rule',
  '/api/v2/admin/sponsorship/packages',
  '/api/v2/admin/story-feed',
  '/api/v2/admin/streamer-tournaments/policy',
  '/api/v2/admin/streamer-tournaments/risk-signals',
  '/api/v2/admin/streamer-tournaments/risk-signals/{signal_id}/review',
  '/api/v2/admin/streamer-tournaments/{tournament_id}/review',
  '/api/v2/admin/streamer-tournaments/{tournament_id}/settle',
  '/api/v2/admin/treasury/bank-accounts',
  '/api/v2/admin/treasury/bank-accounts/{account_id}',
  '/api/v2/admin/treasury/dashboard',
  '/api/v2/admin/treasury/deposits',
  '/api/v2/admin/treasury/deposits/{deposit_id}/confirm',
  '/api/v2/admin/treasury/deposits/{deposit_id}/reject',
  '/api/v2/admin/treasury/deposits/{deposit_id}/review',
  '/api/v2/admin/treasury/disputes',
  '/api/v2/admin/treasury/disputes/{dispute_id}',
  '/api/v2/admin/treasury/disputes/{dispute_id}/messages',
  '/api/v2/admin/treasury/kyc',
  '/api/v2/admin/treasury/kyc/{profile_id}/review',
  '/api/v2/admin/treasury/settings',
  '/api/v2/admin/treasury/withdrawal-batches',
  '/api/v2/admin/treasury/withdrawals',
  '/api/v2/admin/treasury/withdrawals/{withdrawal_id}/reviews',
  '/api/v2/admin/treasury/withdrawals/{withdrawal_id}/status',
  '/api/v2/admin/wallets/market-topups',
  '/api/v2/admin/wallets/market-topups/quote',
  '/api/v2/admin/wallets/market-topups/{topup_id}/status',
  '/api/v2/admin/wallets/purchase-orders',
  '/api/v2/admin/wallets/purchase-orders/{order_id}/status',
  '/api/v2/admin/world/clubs/{club_id}/context',
  '/api/v2/admin/world/cultures/{culture_key}',
  '/api/v2/admin/world/narratives/{narrative_slug}',
  '/api/v2/ads/create',
  '/api/v2/ads/performance',
  '/api/v2/agents',
  '/api/v2/agents/config',
  '/api/v2/agents/performance',
  '/api/v2/agents/run',
  '/api/v2/agents/summary',
  '/api/v2/ai-manager/autopilot/live-decision',
  '/api/v2/ai-manager/autopilot/run',
  '/api/v2/ai-manager/economy/reward-preview',
  '/api/v2/ai-manager/profiles/{club_id}',
  '/api/v2/ai-reporter/feed',
  '/api/v2/ai-reporter/run',
  '/api/v2/ai/leagues',
  '/api/v2/ai/match/{match_id}',
  '/api/v2/analytics/clip/{clip_id}',
  '/api/v2/analytics/dashboard/drop-off',
  '/api/v2/analytics/dashboard/top-clips',
  '/api/v2/analytics/device-fingerprint',
  '/api/v2/analytics/events',
  '/api/v2/analytics/frontend',
  '/api/v2/analytics/influencer-leaderboard',
  '/api/v2/attachments',
  '/api/v2/attachments/{attachment_id}',
  '/api/v2/auth/change-password',
  '/api/v2/auth/confirm-email',
  '/api/v2/auth/login',
  '/api/v2/auth/logout',
  '/api/v2/auth/me',
  '/api/v2/auth/recovery/request',
  '/api/v2/auth/recovery/reset',
  '/api/v2/auth/refresh',
  '/api/v2/auth/signup/creator',
  '/api/v2/auth/signup/trader',
  '/api/v2/auth/signup/user',
  '/api/v2/awards/categories',
  '/api/v2/awards/ceremony',
  '/api/v2/awards/ceremony/tickets',
  '/api/v2/awards/ceremony/vote',
  '/api/v2/awards/nominees',
  '/api/v2/awards/winners',
  '/api/v2/bank-accounts',
  '/api/v2/bank-accounts/{bank_account_id}',
  '/api/v2/bets/history',
  '/api/v2/bets/odds/{match_id}',
  '/api/v2/bets/place',
  '/api/v2/bets/preferences',
  '/api/v2/broadcast-rights/auctions/{auction_id}/bids',
  '/api/v2/broadcast-rights/competitions/{competition_id}',
  '/api/v2/broadcast-rights/competitions/{competition_id}/acquire',
  '/api/v2/broadcast-rights/competitions/{competition_id}/auctions',
  '/api/v2/broadcast-rights/matches/{match_id}/access',
  '/api/v2/broadcast-rights/matches/{match_id}/distribute',
  '/api/v2/broadcast-rights/{right_id}/grants',
  '/api/v2/broadcast/channels',
  '/api/v2/broadcast/channels/{channel_id}/audio/stems/stream',
  '/api/v2/broadcast/channels/{channel_id}/join',
  '/api/v2/broadcast/channels/{channel_id}/stream',
  '/api/v2/broadcast/home',
  '/api/v2/broadcast/pay',
  '/api/v2/broadcast/{match_id}',
  '/api/v2/calendar-engine/dashboard',
  '/api/v2/calendar-engine/events',
  '/api/v2/calendar-engine/lifecycle-runs',
  '/api/v2/calendar-engine/pause-status',
  '/api/v2/calendar-engine/seasons',
  '/api/v2/campaigns',
  '/api/v2/campaigns/create',
  '/api/v2/campaigns/{id}/accept',
  '/api/v2/campaigns/{id}/apply',
  '/api/v2/campaigns/{id}/performance',
  '/api/v2/career/create',
  '/api/v2/career/retire',
  '/api/v2/career/train',
  '/api/v2/career/transfer',
  '/api/v2/career/{user_id}',
  '/api/v2/challenges/links/{link_code}',
  '/api/v2/challenges/{challenge_id}',
  '/api/v2/challenges/{challenge_id}/accept',
  '/api/v2/challenges/{challenge_id}/links',
  '/api/v2/challenges/{challenge_id}/publish',
  '/api/v2/challenges/{challenge_id}/share-events',
  '/api/v2/champions-league/knockout-bracket',
  '/api/v2/champions-league/league-phase/table',
  '/api/v2/champions-league/playoff-bracket',
  '/api/v2/champions-league/prize-pool/preview',
  '/api/v2/champions-league/qualification-map',
  '/api/v2/club-infra/clubs/{club_id}',
  '/api/v2/club-infra/clubs/{club_id}/support',
  '/api/v2/club-infra/my',
  '/api/v2/club-infra/my/facilities/upgrade',
  '/api/v2/club-infra/my/stadium/upgrade',
  '/api/v2/club/identity',
  '/api/v2/clubs',
  '/api/v2/clubs/catalog',
  '/api/v2/clubs/catalog/purchase',
  '/api/v2/clubs/list',
  '/api/v2/clubs/marketplace',
  '/api/v2/clubs/offer',
  '/api/v2/clubs/sale-market/listings',
  '/api/v2/clubs/{club_id}',
  '/api/v2/clubs/{club_id}/academy',
  '/api/v2/clubs/{club_id}/academy/players',
  '/api/v2/clubs/{club_id}/academy/players/{player_id}',
  '/api/v2/clubs/{club_id}/academy/programs',
  '/api/v2/clubs/{club_id}/academy/training-cycles',
  '/api/v2/clubs/{club_id}/badge',
  '/api/v2/clubs/{club_id}/branding',
  '/api/v2/clubs/{club_id}/buy-tokens',
  '/api/v2/clubs/{club_id}/challenges',
  '/api/v2/clubs/{club_id}/contracts',
  '/api/v2/clubs/{club_id}/dynasty',
  '/api/v2/clubs/{club_id}/dynasty/history',
  '/api/v2/clubs/{club_id}/eras',
  '/api/v2/clubs/{club_id}/fans',
  '/api/v2/clubs/{club_id}/finances',
  '/api/v2/clubs/{club_id}/finances/budget',
  '/api/v2/clubs/{club_id}/finances/cashflow',
  '/api/v2/clubs/{club_id}/finances/ledger',
  '/api/v2/clubs/{club_id}/honors-timeline',
  '/api/v2/clubs/{club_id}/identity',
  '/api/v2/clubs/{club_id}/identity/metrics',
  '/api/v2/clubs/{club_id}/identity/metrics/refresh',
  '/api/v2/clubs/{club_id}/jerseys',
  '/api/v2/clubs/{club_id}/jerseys/{jersey_id}',
  '/api/v2/clubs/{club_id}/ownership',
  '/api/v2/clubs/{club_id}/prestige',
  '/api/v2/clubs/{club_id}/proposals',
  '/api/v2/clubs/{club_id}/purchases',
  '/api/v2/clubs/{club_id}/reputation',
  '/api/v2/clubs/{club_id}/reputation/history',
  '/api/v2/clubs/{club_id}/rivalries',
  '/api/v2/clubs/{club_id}/rivalries/{opponent_club_id}',
  '/api/v2/clubs/{club_id}/sale-market',
  '/api/v2/clubs/{club_id}/sale-market/assistant',
  '/api/v2/clubs/{club_id}/sale-market/history',
  '/api/v2/clubs/{club_id}/sale-market/inquiries',
  '/api/v2/clubs/{club_id}/sale-market/inquiries/{inquiry_id}/respond',
  '/api/v2/clubs/{club_id}/sale-market/listing',
  '/api/v2/clubs/{club_id}/sale-market/listing/cancel',
  '/api/v2/clubs/{club_id}/sale-market/listing/instant-sell',
  '/api/v2/clubs/{club_id}/sale-market/offers',
  '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/accept',
  '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/counter',
  '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/reject',
  '/api/v2/clubs/{club_id}/sale-market/transfer',
  '/api/v2/clubs/{club_id}/scouting',
  '/api/v2/clubs/{club_id}/scouting-intelligence/academy-supply-signals',
  '/api/v2/clubs/{club_id}/scouting-intelligence/assignments',
  '/api/v2/clubs/{club_id}/scouting-intelligence/badges',
  '/api/v2/clubs/{club_id}/scouting-intelligence/lifecycle',
  '/api/v2/clubs/{club_id}/scouting-intelligence/manager-profiles',
  '/api/v2/clubs/{club_id}/scouting-intelligence/missions',
  '/api/v2/clubs/{club_id}/scouting-intelligence/missions/{mission_id}',
  '/api/v2/clubs/{club_id}/scouting-intelligence/missions/{mission_id}/complete',
  '/api/v2/clubs/{club_id}/scouting-intelligence/networks',
  '/api/v2/clubs/{club_id}/scouting-intelligence/planning',
  '/api/v2/clubs/{club_id}/scouting/assignments',
  '/api/v2/clubs/{club_id}/scouting/prospects',
  '/api/v2/clubs/{club_id}/scouting/prospects/{prospect_id}',
  '/api/v2/clubs/{club_id}/season-honors',
  '/api/v2/clubs/{club_id}/sell-tokens',
  '/api/v2/clubs/{club_id}/showcase',
  '/api/v2/clubs/{club_id}/sponsorships',
  '/api/v2/clubs/{club_id}/sponsorships/assets',
  '/api/v2/clubs/{club_id}/sponsorships/catalog',
  '/api/v2/clubs/{club_id}/sponsorships/contracts',
  '/api/v2/clubs/{club_id}/sponsorships/contracts/{contract_id}',
  '/api/v2/clubs/{club_id}/squad',
  '/api/v2/clubs/{club_id}/treasury',
  '/api/v2/clubs/{club_id}/trophies',
  '/api/v2/clubs/{club_id}/trophy-cabinet',
  '/api/v2/clubs/{club_id}/valuation',
  '/api/v2/clubs/{club_id}/vote',
  '/api/v2/clubs/{club_id}/youth-pipeline',
  '/api/v2/commentary/profiles',
  '/api/v2/commentary/select',
  '/api/v2/community/creator-clubs/{club_id}/fan-competitions',
  '/api/v2/community/creator-clubs/{club_id}/fan-groups',
  '/api/v2/community/creator-clubs/{club_id}/fan-state',
  '/api/v2/community/creator-clubs/{club_id}/follow',
  '/api/v2/community/creator-matches/{match_id}/chat-room',
  '/api/v2/community/creator-matches/{match_id}/chat-room/messages',
  '/api/v2/community/creator-matches/{match_id}/fan-wall',
  '/api/v2/community/creator-matches/{match_id}/rivalry-signals',
  '/api/v2/community/creator-matches/{match_id}/tactical-advice',
  '/api/v2/community/digest',
  '/api/v2/community/fan-competitions/{fan_competition_id}/join',
  '/api/v2/community/fan-groups/{group_id}/join',
  '/api/v2/community/live-threads',
  '/api/v2/community/live-threads/{thread_id}',
  '/api/v2/community/live-threads/{thread_id}/messages',
  '/api/v2/community/private-messages/threads',
  '/api/v2/community/private-messages/threads/{thread_id}',
  '/api/v2/community/private-messages/threads/{thread_id}/messages',
  '/api/v2/community/watchlist',
  '/api/v2/community/watchlist/{competition_key}',
  '/api/v2/competitions',
  '/api/v2/competitions/admin',
  '/api/v2/competitions/admin/{code}',
  '/api/v2/competitions/admin/{code}/orchestrate',
  '/api/v2/competitions/create',
  '/api/v2/competitions/join',
  '/api/v2/competitions/players/{subject_id}/progression',
  '/api/v2/competitions/records/{competition_id}',
  '/api/v2/competitions/runtime/{code}',
  '/api/v2/competitions/{competition_id}',
  '/api/v2/competitions/{competition_id}/advance',
  '/api/v2/competitions/{competition_id}/finalize',
  '/api/v2/competitions/{competition_id}/financials',
  '/api/v2/competitions/{competition_id}/fixtures',
  '/api/v2/competitions/{competition_id}/invites',
  '/api/v2/competitions/{competition_id}/invites/accept',
  '/api/v2/competitions/{competition_id}/join',
  '/api/v2/competitions/{competition_id}/launch',
  '/api/v2/competitions/{competition_id}/leave',
  '/api/v2/competitions/{competition_id}/matches/{match_id}/events',
  '/api/v2/competitions/{competition_id}/matches/{match_id}/result',
  '/api/v2/competitions/{competition_id}/publish',
  '/api/v2/competitions/{competition_id}/rewards',
  '/api/v2/competitions/{competition_id}/rounds',
  '/api/v2/competitions/{competition_id}/schedule/jobs',
  '/api/v2/competitions/{competition_id}/schedule/jobs/{job_id}',
  '/api/v2/competitions/{competition_id}/schedule/preview',
  '/api/v2/competitions/{competition_id}/seed',
  '/api/v2/competitions/{competition_id}/standings',
  '/api/v2/competitions/{competition_id}/summary',
  '/api/v2/competitive-integrity/fast-game/runs',
  '/api/v2/competitive-integrity/fast-game/runs/{run_id}',
  '/api/v2/competitive-integrity/fast-game/runs/{run_id}/play',
  '/api/v2/competitive-integrity/managers',
  '/api/v2/competitive-integrity/managers/candidates',
  '/api/v2/competitive-integrity/managers/{manager_id}/instructions',
  '/api/v2/competitive-integrity/matches',
  '/api/v2/competitive-integrity/matches/{match_id}',
  '/api/v2/competitive-integrity/matches/{match_id}/execute',
  '/api/v2/competitive-integrity/notifications/events',
  '/api/v2/config/current',
  '/api/v2/config/update',
  '/api/v2/conversations',
  '/api/v2/conversations/start',
  '/api/v2/conversations/{conversation_id}/message',
  '/api/v2/conversations/{conversation_id}/messages',
  '/api/v2/conversations/{conversation_id}/status',
  '/api/v2/creator-campaigns',
  '/api/v2/creator-campaigns/me',
  '/api/v2/creator-campaigns/{campaign_id}',
  '/api/v2/creator-campaigns/{campaign_id}/metrics',
  '/api/v2/creator-campaigns/{campaign_id}/snapshot',
  '/api/v2/creator-campaigns/{campaign_id}/snapshots',
  '/api/v2/creator-league',
  '/api/v2/creator-league/config',
  '/api/v2/creator-league/financial-report',
  '/api/v2/creator-league/financial-settlements',
  '/api/v2/creator-league/financial-settlements/{settlement_id}/approve',
  '/api/v2/creator-league/live-priority',
  '/api/v2/creator-league/reset',
  '/api/v2/creator-league/season-tiers/{season_tier_id}/standings',
  '/api/v2/creator-league/seasons',
  '/api/v2/creator-league/seasons/{season_id}',
  '/api/v2/creator-league/seasons/{season_id}/pause',
  '/api/v2/creator-league/tiers',
  '/api/v2/creator-league/tiers/{tier_id}',
  '/api/v2/creator/application',
  '/api/v2/creator/apply',
  '/api/v2/creator/cards',
  '/api/v2/creator/cards/listings',
  '/api/v2/creator/cards/listings/{listing_id}/buy',
  '/api/v2/creator/cards/loans/{loan_id}/return',
  '/api/v2/creator/cards/swap',
  '/api/v2/creator/cards/{creator_card_id}/list',
  '/api/v2/creator/cards/{creator_card_id}/loan',
  '/api/v2/creator/clubs/{club_id}/fan-share-market',
  '/api/v2/creator/clubs/{club_id}/fan-share-market/distributions',
  '/api/v2/creator/clubs/{club_id}/fan-share-market/holding',
  '/api/v2/creator/clubs/{club_id}/fan-share-market/purchase',
  '/api/v2/creator/verify-email',
  '/api/v2/creator/verify-phone',
  '/api/v2/creators/marketplace',
  '/api/v2/creators/me/competitions',
  '/api/v2/creators/me/copilot/analyze',
  '/api/v2/creators/me/finance',
  '/api/v2/creators/me/insights',
  '/api/v2/creators/me/reputation',
  '/api/v2/creators/me/summary',
  '/api/v2/creators/profile',
  '/api/v2/creators/profile/me',
  '/api/v2/creators/{handle}',
  '/api/v2/daily-challenges',
  '/api/v2/daily-challenges/me',
  '/api/v2/daily-challenges/{challenge_key}/claim',
  '/api/v2/diagnostics',
  '/api/v2/discovery/home',
  '/api/v2/discovery/saved-searches',
  '/api/v2/discovery/saved-searches/{search_id}',
  '/api/v2/discovery/search',
  '/api/v2/disputes',
  '/api/v2/disputes/me',
  '/api/v2/disputes/{dispute_id}',
  '/api/v2/disputes/{dispute_id}/messages',
  '/api/v2/dynasty',
  '/api/v2/dynasty/leaderboard',
  '/api/v2/economy/fx/quote',
  '/api/v2/economy/gift-catalog',
  '/api/v2/economy/service-pricing',
  '/api/v2/engagement/achievements',
  '/api/v2/engagement/achievements/me',
  '/api/v2/engagement/milestones/me',
  '/api/v2/engagement/sync',
  '/api/v2/enter',
  '/api/v2/events/clip',
  '/api/v2/events/today',
  '/api/v2/events/upcoming',
  '/api/v2/experience/full-simulation',
  '/api/v2/fan-predictions/creator-clubs/{club_id}/leaderboards/weekly',
  '/api/v2/fan-predictions/leaderboards/weekly',
  '/api/v2/fan-predictions/matches/{match_id}',
  '/api/v2/fan-predictions/matches/{match_id}/leaderboard',
  '/api/v2/fan-predictions/matches/{match_id}/submissions',
  '/api/v2/fan-predictions/me/submissions',
  '/api/v2/fan-predictions/me/tokens',
  '/api/v2/fan-wars/leaderboards/{board_type}',
  '/api/v2/fan-wars/nations-cup/{competition_id}',
  '/api/v2/fan-wars/profiles/{profile_id}/dashboard',
  '/api/v2/fan-wars/rivalries/{board_type}',
  '/api/v2/fans/profile',
  '/api/v2/fans/tribe/join',
  '/api/v2/fans/{club_id}',
  '/api/v2/fast-cups/upcoming',
  '/api/v2/fast-cups/{cup_id}/bracket',
  '/api/v2/fast-cups/{cup_id}/countdown',
  '/api/v2/fast-cups/{cup_id}/join',
  '/api/v2/fast-cups/{cup_id}/result-summary',
  '/api/v2/federations',
  '/api/v2/federations/proposals/{proposal_id}/votes',
  '/api/v2/federations/rankings',
  '/api/v2/federations/regional-tournaments',
  '/api/v2/federations/vote',
  '/api/v2/federations/{federation_id}',
  '/api/v2/federations/{federation_id}/governance',
  '/api/v2/federations/{federation_id}/join',
  '/api/v2/federations/{federation_id}/leagues',
  '/api/v2/federations/{federation_id}/memberships',
  '/api/v2/federations/{federation_id}/narratives',
  '/api/v2/federations/{federation_id}/proposals',
  '/api/v2/federations/{federation_id}/sanctions',
  '/api/v2/federations/{federation_id}/treasury/distribute',
  '/api/v2/federations/{federation_id}/validate-action',
  '/api/v2/feed',
  '/api/v2/feed/following',
  '/api/v2/feed/for-you',
  '/api/v2/feed/for-you/refresh',
  '/api/v2/feed/sponsored',
  '/api/v2/finance',
  '/api/v2/follow/{user_id}',
  '/api/v2/football-events/players/{player_id}/events',
  '/api/v2/football-events/players/{player_id}/impact',
  '/api/v2/gift-engine/me/combos',
  '/api/v2/gift-engine/me/summary',
  '/api/v2/gift-engine/me/transactions',
  '/api/v2/gift-engine/send',
  '/api/v2/governance/clubs/{club_id}/panel',
  '/api/v2/governance/me/overview',
  '/api/v2/governance/proposals',
  '/api/v2/governance/proposals/{proposal_id}',
  '/api/v2/governance/proposals/{proposal_id}/vote',
  '/api/v2/gtex/market/buy',
  '/api/v2/gtex/market/sell',
  '/api/v2/hall-of-fame',
  '/api/v2/history/goat-rankings',
  '/api/v2/history/leaderboards',
  '/api/v2/history/records',
  '/api/v2/history/timeline/{subject_type}/{subject_id}',
  '/api/v2/home/dashboard',
  '/api/v2/hosted-competitions',
  '/api/v2/hosted-competitions/mine',
  '/api/v2/hosted-competitions/mine/invites',
  '/api/v2/hosted-competitions/templates',
  '/api/v2/hosted-competitions/{competition_id}',
  '/api/v2/hosted-competitions/{competition_id}/finance',
  '/api/v2/hosted-competitions/{competition_id}/invites',
  '/api/v2/hosted-competitions/{competition_id}/invites/accept',
  '/api/v2/hosted-competitions/{competition_id}/join',
  '/api/v2/hosted-competitions/{competition_id}/launch',
  '/api/v2/hosted-competitions/{competition_id}/standings',
  '/api/v2/infinite-league/economy',
  '/api/v2/infinite-league/livestream',
  '/api/v2/infinite-league/matches',
  '/api/v2/infinite-league/matches/{match_id}',
  '/api/v2/infinite-league/pundits/{match_id}',
  '/api/v2/infinite-league/status',
  '/api/v2/infinite-league/tick',
  '/api/v2/infinite-league/viral-feed',
  '/api/v2/integrations/payments/korapay/webhook',
  '/api/v2/integrations/payments/methods',
  '/api/v2/integrations/payments/orders',
  '/api/v2/integrations/payments/paystack/webhook',
  '/api/v2/integrations/payments/quote',
  '/api/v2/integrity-engine/me/incidents',
  '/api/v2/integrity-engine/me/score',
  '/api/v2/internal/ingestion/bootstrap-sync',
  '/api/v2/internal/ingestion/clubs/{club_external_id}/refresh',
  '/api/v2/internal/ingestion/competitions/{competition_external_id}/refresh',
  '/api/v2/internal/ingestion/cursors/{provider_name}',
  '/api/v2/internal/ingestion/incremental-sync',
  '/api/v2/internal/ingestion/players/{player_external_id}/refresh',
  '/api/v2/internal/ingestion/providers/{provider_name}/health',
  '/api/v2/internal/ingestion/real-players/batches',
  '/api/v2/internal/ingestion/real-players/batches/{batch_id}',
  '/api/v2/internal/ingestion/real-players/batches/{batch_id}/issues',
  '/api/v2/internal/ingestion/real-players/batches/{batch_id}/resume',
  '/api/v2/internal/ingestion/real-players/batches/{batch_id}/valuation-status',
  '/api/v2/internal/ingestion/real-players/import',
  '/api/v2/internal/ingestion/real-players/publish-jobs',
  '/api/v2/internal/ingestion/real-players/publish-jobs/{job_id}',
  '/api/v2/internal/ingestion/real-players/status',
  '/api/v2/internal/ingestion/runs',
  '/api/v2/internal/ingestion/status',
  '/api/v2/jackpot/contribute',
  '/api/v2/jackpot/history',
  '/api/v2/jackpot/state',
  '/api/v2/jobs/{job_id}',
  '/api/v2/kyc',
  '/api/v2/leaderboard/division/{division}',
  '/api/v2/leaderboard/global',
  '/api/v2/leaderboard/player/{player_id}',
  '/api/v2/leaderboard/region/{region}',
  '/api/v2/leaderboards/dynasties',
  '/api/v2/leaderboards/prestige',
  '/api/v2/leaderboards/trophies',
  '/api/v2/leagues/register',
  '/api/v2/leagues/{season_id}/fixtures',
  '/api/v2/leagues/{season_id}/qualification-markers',
  '/api/v2/leagues/{season_id}/standings',
  '/api/v2/leagues/{season_id}/summary',
  '/api/v2/legacy/board',
  '/api/v2/live-events',
  '/api/v2/manager-duels',
  '/api/v2/manager-duels/leaderboard',
  '/api/v2/manager-duels/{duel_id}',
  '/api/v2/managers',
  '/api/v2/managers/assign',
  '/api/v2/managers/catalog',
  '/api/v2/managers/compare',
  '/api/v2/managers/competition-runtime/{code}',
  '/api/v2/managers/create',
  '/api/v2/managers/filters',
  '/api/v2/managers/history',
  '/api/v2/managers/leaderboard',
  '/api/v2/managers/my-trade-listings',
  '/api/v2/managers/recommendation',
  '/api/v2/managers/recruit',
  '/api/v2/managers/swap',
  '/api/v2/managers/team',
  '/api/v2/managers/trade-listings',
  '/api/v2/managers/trade-listings/{listing_id}/buy',
  '/api/v2/managers/trade-listings/{listing_id}/cancel',
  '/api/v2/managers/{asset_id}/release',
  '/api/v2/managers/{manager_id}',
  '/api/v2/managers/{manager_id}/hire',
  '/api/v2/managers/{manager_id}/history',
  '/api/v2/managers/{manager_id}/release',
  '/api/v2/market/bid',
  '/api/v2/market/buy',
  '/api/v2/market/listings',
  '/api/v2/market/listings/{listing_id}/cancel',
  '/api/v2/market/listings/{listing_id}/matches',
  '/api/v2/market/listings/{listing_id}/offers',
  '/api/v2/market/movers',
  '/api/v2/market/offers',
  '/api/v2/market/offers/{offer_id}/accept',
  '/api/v2/market/offers/{offer_id}/counter',
  '/api/v2/market/offers/{offer_id}/reject',
  '/api/v2/market/players',
  '/api/v2/market/players/{player_id}',
  '/api/v2/market/players/{player_id}/candles',
  '/api/v2/market/players/{player_id}/history',
  '/api/v2/market/sell',
  '/api/v2/market/summary/{asset_id}',
  '/api/v2/market/ticker/{player_id}',
  '/api/v2/market/trade-intents',
  '/api/v2/market/trade-intents/{intent_id}/withdraw',
  '/api/v2/market/trending',
  '/api/v2/marketplace/my-players',
  '/api/v2/marketplace/players',
  '/api/v2/marketplace/players/{player_id}',
  '/api/v2/match-engine/analytics',
  '/api/v2/match-engine/analytics/{match_key}',
  '/api/v2/match-engine/highlights/{match_key}',
  '/api/v2/match-engine/live-feed/{match_key}',
  '/api/v2/match-engine/render-sync',
  '/api/v2/match-engine/render-sync/{match_key}',
  '/api/v2/match-engine/replay',
  '/api/v2/match-engine/simulate',
  '/api/v2/match-engine/summary',
  '/api/v2/match-engine/timeline',
  '/api/v2/match-share-links/{share_code}',
  '/api/v2/match-share-links/{share_code}/events',
  '/api/v2/match-viewer/{match_key}',
  '/api/v2/match-viewer/{match_key}/illusion',
  '/api/v2/match-viewer/{match_key}/session',
  '/api/v2/match/find',
  '/api/v2/match/live/active',
  '/api/v2/match/{match_id}/commentary/stream',
  '/api/v2/match/{match_id}/live',
  '/api/v2/match/{match_id}/unity-access',
  '/api/v2/match/{match_id}/unity-access/refresh',
  '/api/v2/matches/complete',
  '/api/v2/matches/live/active',
  '/api/v2/matches/start',
  '/api/v2/matches/{match_id}',
  '/api/v2/matches/{match_id}/analysis',
  '/api/v2/matches/{match_id}/audio/stems/stream',
  '/api/v2/matches/{match_id}/chat',
  '/api/v2/matches/{match_id}/chat/messages',
  '/api/v2/matches/{match_id}/commentary',
  '/api/v2/matches/{match_id}/commentary/stream',
  '/api/v2/matches/{match_id}/fan-experience',
  '/api/v2/matches/{match_id}/highlights',
  '/api/v2/matches/{match_id}/highlights/share-package',
  '/api/v2/matches/{match_id}/live',
  '/api/v2/matches/{match_id}/live-reactions',
  '/api/v2/matches/{match_id}/reactions',
  '/api/v2/matches/{match_id}/replay',
  '/api/v2/matches/{match_id}/share-links',
  '/api/v2/matches/{match_id}/social-warfare',
  '/api/v2/matches/{match_id}/spectate',
  '/api/v2/matches/{match_id}/spectators',
  '/api/v2/matches/{match_id}/stream',
  '/api/v2/matches/{match_id}/tickets',
  '/api/v2/matches/{match_id}/unity-access',
  '/api/v2/matches/{match_id}/unity-access/refresh',
  '/api/v2/me/clubs/sale-market/listings',
  '/api/v2/me/clubs/sale-market/offers',
  '/api/v2/media',
  '/api/v2/media-engine/creator-league/broadcast-modes',
  '/api/v2/media-engine/creator-league/clubs/{club_id}/stadium',
  '/api/v2/media-engine/creator-league/matches/{match_id}/access',
  '/api/v2/media-engine/creator-league/matches/{match_id}/analytics',
  '/api/v2/media-engine/creator-league/matches/{match_id}/gifts',
  '/api/v2/media-engine/creator-league/matches/{match_id}/purchase',
  '/api/v2/media-engine/creator-league/matches/{match_id}/stadium',
  '/api/v2/media-engine/creator-league/matches/{match_id}/stadium/placements',
  '/api/v2/media-engine/creator-league/matches/{match_id}/tickets',
  '/api/v2/media-engine/creator-league/season-passes',
  '/api/v2/media-engine/creator-league/season-passes/me',
  '/api/v2/media-engine/downloads',
  '/api/v2/media-engine/downloads/{token}',
  '/api/v2/media-engine/matches/{match_key}/snapshot',
  '/api/v2/media-engine/me/clip-earnings',
  '/api/v2/media-engine/me/purchases',
  '/api/v2/media-engine/me/share-exports',
  '/api/v2/media-engine/purchases',
  '/api/v2/media-engine/share-exports',
  '/api/v2/media-engine/share-exports/{export_id}/amplifications',
  '/api/v2/media-engine/share-templates',
  '/api/v2/media-engine/views',
  '/api/v2/metrics',
  '/api/v2/moderation/me/reports',
  '/api/v2/moderation/reports',
  '/api/v2/moments/live',
  '/api/v2/national-pool',
  '/api/v2/national-team-engine/competitions',
  '/api/v2/national-team-engine/competitions/{competition_id}',
  '/api/v2/national-team-engine/competitions/{competition_id}/ads/active',
  '/api/v2/national-team-engine/competitions/{competition_id}/auto-build-squad',
  '/api/v2/national-team-engine/competitions/{competition_id}/entries',
  '/api/v2/national-team-engine/competitions/{competition_id}/gifts',
  '/api/v2/national-team-engine/competitions/{competition_id}/lifecycle',
  '/api/v2/national-team-engine/competitions/{competition_id}/presentation',
  '/api/v2/national-team-engine/competitions/{competition_id}/rental-entry',
  '/api/v2/national-team-engine/competitions/{competition_id}/rental-pool',
  '/api/v2/national-team-engine/competitions/{competition_id}/story-events',
  '/api/v2/national-team-engine/competitions/{competition_id}/theme',
  '/api/v2/national-team-engine/entries/{entry_id}',
  '/api/v2/national-team-engine/entries/{entry_id}/free-players/claim',
  '/api/v2/national-team-engine/entries/{entry_id}/rental-status',
  '/api/v2/national-team-engine/entries/{entry_id}/rentals',
  '/api/v2/national-team-engine/me/history',
  '/api/v2/national-team-engine/me/previous-roster',
  '/api/v2/national-team-engine/rankings',
  '/api/v2/news/breaking',
  '/api/v2/news/daily',
  '/api/v2/news/feed',
  '/api/v2/news/personalized',
  '/api/v2/news/{article_id}',
  '/api/v2/notifications',
  '/api/v2/notifications/announcements',
  '/api/v2/notifications/me',
  '/api/v2/notifications/preferences',
  '/api/v2/notifications/read-all',
  '/api/v2/notifications/subscriptions',
  '/api/v2/notifications/subscriptions/{subscription_id}',
  '/api/v2/notifications/{notification_id}/read',
  '/api/v2/objectives/me',
  '/api/v2/observability/config',
  '/api/v2/orchestrator/config',
  '/api/v2/orchestrator/metrics',
  '/api/v2/orders',
  '/api/v2/orders/book/{player_id}',
  '/api/v2/orders/{order_id}',
  '/api/v2/orders/{order_id}/admin-buyback',
  '/api/v2/orders/{order_id}/admin-buyback-preview',
  '/api/v2/orders/{order_id}/cancel',
  '/api/v2/organizations',
  '/api/v2/organizations/invites/accept',
  '/api/v2/organizations/me',
  '/api/v2/organizations/{organization_id}/audit-log',
  '/api/v2/organizations/{organization_id}/invite',
  '/api/v2/ownership-groups',
  '/api/v2/ownership-groups/transfers/validate',
  '/api/v2/ownership-groups/{group_id}',
  '/api/v2/ownership-groups/{group_id}/budget/allocate',
  '/api/v2/ownership-groups/{group_id}/budget/transfer',
  '/api/v2/ownership-groups/{group_id}/clubs',
  '/api/v2/platform/mode',
  '/api/v2/platform/switch',
  '/api/v2/player-cards/admin/preseeded-regens',
  '/api/v2/player-cards/admin/preseeded-regens/mint',
  '/api/v2/player-cards/inventory',
  '/api/v2/player-cards/listings',
  '/api/v2/player-cards/listings/mine',
  '/api/v2/player-cards/listings/{listing_id}/buy',
  '/api/v2/player-cards/listings/{listing_id}/cancel',
  '/api/v2/player-cards/loans',
  '/api/v2/player-cards/loans/contracts/{loan_contract_id}/return',
  '/api/v2/player-cards/loans/{loan_listing_id}/borrow',
  '/api/v2/player-cards/marketplace/listings',
  '/api/v2/player-cards/marketplace/loans',
  '/api/v2/player-cards/marketplace/loans/contracts',
  '/api/v2/player-cards/marketplace/loans/contracts/{contract_id}/return',
  '/api/v2/player-cards/marketplace/loans/contracts/{contract_id}/settle',
  '/api/v2/player-cards/marketplace/loans/negotiations/{negotiation_id}/accept',
  '/api/v2/player-cards/marketplace/loans/negotiations/{negotiation_id}/counter',
  '/api/v2/player-cards/marketplace/loans/{listing_id}/cancel',
  '/api/v2/player-cards/marketplace/loans/{listing_id}/negotiations',
  '/api/v2/player-cards/marketplace/sales',
  '/api/v2/player-cards/marketplace/sales/{listing_id}/buy',
  '/api/v2/player-cards/marketplace/sales/{listing_id}/cancel',
  '/api/v2/player-cards/marketplace/swaps',
  '/api/v2/player-cards/marketplace/swaps/{listing_id}/cancel',
  '/api/v2/player-cards/marketplace/swaps/{listing_id}/execute',
  '/api/v2/player-cards/players',
  '/api/v2/player-cards/players/{player_id}',
  '/api/v2/player-cards/starter-rental',
  '/api/v2/player-cards/watchlist',
  '/api/v2/player-cards/watchlist/{watchlist_id}',
  '/api/v2/player-history',
  '/api/v2/player-history/{player_id}',
  '/api/v2/player-import/youth-prospects/me',
  '/api/v2/player-import/youth-prospects/{club_id}',
  '/api/v2/players',
  '/api/v2/players/events',
  '/api/v2/players/markets',
  '/api/v2/players/match',
  '/api/v2/players/me/match-profile',
  '/api/v2/players/me/shares/holdings',
  '/api/v2/players/real-universe',
  '/api/v2/players/real-universe/search',
  '/api/v2/players/real-universe/{player_id}',
  '/api/v2/players/summaries/recent',
  '/api/v2/players/{player_id}',
  '/api/v2/players/{player_id}/agency',
  '/api/v2/players/{player_id}/agency/contract-decision',
  '/api/v2/players/{player_id}/agency/transfer-decision',
  '/api/v2/players/{player_id}/availability',
  '/api/v2/players/{player_id}/avatar',
  '/api/v2/players/{player_id}/career',
  '/api/v2/players/{player_id}/career-events',
  '/api/v2/players/{player_id}/career/summary',
  '/api/v2/players/{player_id}/contracts',
  '/api/v2/players/{player_id}/contracts/summary',
  '/api/v2/players/{player_id}/contracts/{contract_id}/renew',
  '/api/v2/players/{player_id}/dna',
  '/api/v2/players/{player_id}/events',
  '/api/v2/players/{player_id}/injuries',
  '/api/v2/players/{player_id}/injuries/{injury_id}/recover',
  '/api/v2/players/{player_id}/interviews',
  '/api/v2/players/{player_id}/lifecycle-snapshot',
  '/api/v2/players/{player_id}/overview',
  '/api/v2/players/{player_id}/personality',
  '/api/v2/players/{player_id}/regen',
  '/api/v2/players/{player_id}/regen/big-club-approaches',
  '/api/v2/players/{player_id}/regen/contract-offers/quote',
  '/api/v2/players/{player_id}/regen/offer-market',
  '/api/v2/players/{player_id}/regen/pressure-resolution',
  '/api/v2/players/{player_id}/regen/special-training',
  '/api/v2/players/{player_id}/regen/transfer-listing',
  '/api/v2/players/{player_id}/rivalries',
  '/api/v2/players/{player_id}/shares/buy',
  '/api/v2/players/{player_id}/shares/dividends',
  '/api/v2/players/{player_id}/shares/events',
  '/api/v2/players/{player_id}/shares/issue',
  '/api/v2/players/{player_id}/shares/market',
  '/api/v2/players/{player_id}/shares/performance',
  '/api/v2/players/{player_id}/shares/sell',
  '/api/v2/players/{player_id}/story',
  '/api/v2/players/{player_id}/summary',
  '/api/v2/policies/acceptances',
  '/api/v2/policies/country/{country_code}',
  '/api/v2/policies/documents',
  '/api/v2/policies/documents/{document_key}',
  '/api/v2/policies/me/acceptances',
  '/api/v2/policies/me/compliance',
  '/api/v2/policies/me/region',
  '/api/v2/policies/me/requirements',
  '/api/v2/portfolio',
  '/api/v2/portfolio/snapshot',
  '/api/v2/portfolio/summary',
  '/api/v2/portfolios/me',
  '/api/v2/predictions',
  '/api/v2/predictions/leaderboard',
  '/api/v2/pundits/matches/{match_key}',
  '/api/v2/rankings/clubs',
  '/api/v2/rankings/global',
  '/api/v2/rankings/players',
  '/api/v2/real-world/events',
  '/api/v2/real-world/hybrid-players',
  '/api/v2/real-world/normalize',
  '/api/v2/real-world/players',
  '/api/v2/real-world/players/{real_player_id}',
  '/api/v2/real-world/providers',
  '/api/v2/real-world/settings/me',
  '/api/v2/realtime/matches/{match_id}/gateway',
  '/api/v2/realtime/matches/{match_id}/stream',
  '/api/v2/realtime/status',
  '/api/v2/realtime/stream',
  '/api/v2/realtime/wallet/gateway',
  '/api/v2/realtime/wallet/stream',
  '/api/v2/referrals/attribution',
  '/api/v2/referrals/me/invites',
  '/api/v2/referrals/me/rewards',
  '/api/v2/referrals/me/summary',
  '/api/v2/referrals/share-codes',
  '/api/v2/referrals/share-codes/me',
  '/api/v2/referrals/share-codes/{code}/redeem',
  '/api/v2/referrals/share-codes/{share_code_id}',
  '/api/v2/regen-hype',
  '/api/v2/regen-universe/achievements',
  '/api/v2/regen-universe/awards',
  '/api/v2/regen-universe/bloodlines',
  '/api/v2/regen-universe/hall-of-fame',
  '/api/v2/regen-universe/national-regens',
  '/api/v2/regen-universe/player/{player_id}',
  '/api/v2/regen-universe/players/{player_id}',
  '/api/v2/regen-universe/players/{player_id}/timeline',
  '/api/v2/regen-universe/rankings',
  '/api/v2/regen-universe/rising-stars',
  '/api/v2/regen-universe/scouting-feed',
  '/api/v2/regen-universe/seasons',
  '/api/v2/regen-universe/tracking',
  '/api/v2/regen-universe/youth-tournaments',
  '/api/v2/regen-universe/youth-tournaments/{tournament_id}',
  '/api/v2/regens',
  '/api/v2/regens/awards',
  '/api/v2/regens/awards/{award_id}/vote',
  '/api/v2/regens/creation-orders',
  '/api/v2/regens/creation-orders/{order_id}',
  '/api/v2/regens/creation-orders/{order_id}/generate-after-payment',
  '/api/v2/regens/creation-orders/{order_id}/pay-with-wallet',
  '/api/v2/regens/feed',
  '/api/v2/regens/jobs/{job_name}',
  '/api/v2/regens/request-son',
  '/api/v2/regens/request-son/options',
  '/api/v2/regens/rising',
  '/api/v2/regens/top',
  '/api/v2/regens/{regen_id}/lineage',
  '/api/v2/rent',
  '/api/v2/replays/countdown/{fixture_id}',
  '/api/v2/replays/me',
  '/api/v2/replays/public/featured',
  '/api/v2/replays/{replay_id}',
  '/api/v2/reward-engine/me/settlements',
  '/api/v2/reward-engine/me/summary',
  '/api/v2/risk-ops/me/aml-cases',
  '/api/v2/risk-ops/me/fraud-cases',
  '/api/v2/risk-ops/me/overview',
  '/api/v2/risk-ops/me/restrictions',
  '/api/v2/risk-ops/me/signals',
  '/api/v2/rivalries/matches',
  '/api/v2/scout/report/{player_id}',
  '/api/v2/scouts',
  '/api/v2/scouts/{scout_id}/discover',
  '/api/v2/season-pass',
  '/api/v2/season-pass/claim',
  '/api/v2/season-pass/me',
  '/api/v2/season-pass/rewards/{reward_id}/claim',
  '/api/v2/season/current',
  '/api/v2/season/history',
  '/api/v2/session/bootstrap',
  '/api/v2/shows/debate',
  '/api/v2/shows/post-match/{match_id}',
  '/api/v2/shows/pre-match/{match_id}',
  '/api/v2/simulation-matchmaking/hosted-competitions/preview',
  '/api/v2/simulation-matchmaking/profiles/{user_id}',
  '/api/v2/simulation-matchmaking/quick-game',
  '/api/v2/simulation-matchmaking/quick-tournament',
  '/api/v2/social/clubs/{club_id}/community',
  '/api/v2/social/clubs/{club_id}/community/messages',
  '/api/v2/social/feed',
  '/api/v2/social/follows',
  '/api/v2/social/follows/me',
  '/api/v2/social/profile/me',
  '/api/v2/social/rivalries/{club_a_id}/{club_b_id}',
  '/api/v2/social/rivalries/{club_a_id}/{club_b_id}/banter',
  '/api/v2/sponsors',
  '/api/v2/sponsorship/clubs/{club_id}/contracts',
  '/api/v2/sponsorship/clubs/{club_id}/dashboard',
  '/api/v2/sponsorship/clubs/{club_id}/offers',
  '/api/v2/sponsorship/clubs/{club_id}/sponsors',
  '/api/v2/sponsorship/contracts/request',
  '/api/v2/sponsorship/me/leads',
  '/api/v2/sponsorship/packages',
  '/api/v2/sponsorship/placements',
  '/api/v2/stories',
  '/api/v2/stories/generate',
  '/api/v2/story-feed',
  '/api/v2/story-feed/digest',
  '/api/v2/streamer-tournaments',
  '/api/v2/streamer-tournaments/mine',
  '/api/v2/streamer-tournaments/{tournament_id}',
  '/api/v2/streamer-tournaments/{tournament_id}/invites',
  '/api/v2/streamer-tournaments/{tournament_id}/join',
  '/api/v2/streamer-tournaments/{tournament_id}/publish',
  '/api/v2/streamer-tournaments/{tournament_id}/rewards',
  '/api/v2/surveillance/circular-trade-alerts',
  '/api/v2/surveillance/holder-concentration-alerts',
  '/api/v2/surveillance/suspicious-clusters',
  '/api/v2/surveillance/suspicious-players',
  '/api/v2/surveillance/thin-market-alerts',
  '/api/v2/sync/update',
  '/api/v2/tasks',
  '/api/v2/tasks/{task_id}/claim',
  '/api/v2/tickets/attendance/{match_id}/react',
  '/api/v2/tickets/buy',
  '/api/v2/tickets/event/{match_id}',
  '/api/v2/tickets/resell',
  '/api/v2/tickets/waitlist',
  '/api/v2/tournaments',
  '/api/v2/tournaments/{tournament_id}',
  '/api/v2/tournaments/{tournament_id}/advance',
  '/api/v2/tournaments/{tournament_id}/join',
  '/api/v2/tournaments/{tournament_id}/matches/{match_id}/result',
  '/api/v2/tournaments/{tournament_id}/rent',
  '/api/v2/tournaments/{tournament_id}/squad',
  '/api/v2/trader/markets',
  '/api/v2/trader/orders',
  '/api/v2/trader/overview',
  '/api/v2/trader/p2p',
  '/api/v2/trader/security/totp/setup',
  '/api/v2/trader/watchlist',
  '/api/v2/transfer-market/clubs/{club_id}/team-dynamics',
  '/api/v2/transfer-market/coaches/{club_id}/demands',
  '/api/v2/transfer-market/coaches/{club_id}/profile',
  '/api/v2/transfer-market/jobs/run',
  '/api/v2/transfer-market/listings',
  '/api/v2/transfer-market/listings/{listing_id}',
  '/api/v2/transfer-market/listings/{listing_id}/bids',
  '/api/v2/transfer-market/listings/{listing_id}/close',
  '/api/v2/transfer-market/listings/{listing_id}/contract-offer',
  '/api/v2/transfer-market/listings/{listing_id}/negotiation',
  '/api/v2/transfer-market/listings/{listing_id}/stream',
  '/api/v2/transfer-market/players/{player_id}/decision-profile',
  '/api/v2/transfer-market/watchlist',
  '/api/v2/transfers/windows',
  '/api/v2/transfers/windows/{window_id}',
  '/api/v2/transfers/windows/{window_id}/bids',
  '/api/v2/transfers/windows/{window_id}/bids/{bid_id}/accept',
  '/api/v2/transfers/windows/{window_id}/bids/{bid_id}/reject',
  '/api/v2/transfers/windows/{window_id}/players/{player_id}/regen-bid-evaluations',
  '/api/v2/transfers/windows/{window_id}/players/{player_id}/resolve-regen-bid',
  '/api/v2/trust/me',
  '/api/v2/trust/{user_id}',
  '/api/v2/ultimate-league/competitors/{competitor_id}',
  '/api/v2/ultimate-league/matches/result',
  '/api/v2/ultimate-league/matchmaking/batch',
  '/api/v2/ultimate-league/standings/{tier}',
  '/api/v2/ultimate-league/tactical-presets',
  '/api/v2/ultimate-league/tactical-presets/{preset_id}/purchase',
  '/api/v2/ultimate-league/tiers',
  '/api/v2/ultimate-league/tournaments',
  '/api/v2/ultimate-league/tournaments/{tournament_id}',
  '/api/v2/ultimate-league/tournaments/{tournament_id}/payouts/preview',
  '/api/v2/users/me',
  '/api/v2/users/me/profile',
  '/api/v2/users/suggestions',
  '/api/v2/users/{user_id}',
  '/api/v2/users/{user_id}/follow',
  '/api/v2/users/{user_id}/followers',
  '/api/v2/users/{user_id}/following',
  '/api/v2/value-engine/snapshots/rebuild',
  '/api/v2/value-engine/snapshots/{player_id}/daily-closes',
  '/api/v2/value-engine/snapshots/{player_id}/history',
  '/api/v2/value-engine/snapshots/{player_id}/latest',
  '/api/v2/value-engine/snapshots/{player_id}/trend-summary',
  '/api/v2/viral/accounts',
  '/api/v2/viral/cascades',
  '/api/v2/viral/clips/trending',
  '/api/v2/viral/clips/{clip_id}/variants',
  '/api/v2/viral/clips/{clip_id}/winner',
  '/api/v2/viral/feed',
  '/api/v2/viral/feed/for-you',
  '/api/v2/viral/matches/{match_key}/clips',
  '/api/v2/viral/sessions/{session_id}',
  '/api/v2/wallet',
  '/api/v2/wallet/top-up/initiate',
  '/api/v2/wallet/top-up/verify',
  '/api/v2/wallet/transactions',
  '/api/v2/wallets',
  '/api/v2/wallets/accounts',
  '/api/v2/wallets/adaptive-overview',
  '/api/v2/wallets/conversions',
  '/api/v2/wallets/conversions/quote',
  '/api/v2/wallets/deposits',
  '/api/v2/wallets/deposits/{deposit_id}/submit',
  '/api/v2/wallets/ledger',
  '/api/v2/wallets/market-topups',
  '/api/v2/wallets/overview',
  '/api/v2/wallets/payment-events',
  '/api/v2/wallets/providers/{provider_key}/webhook',
  '/api/v2/wallets/purchase-orders',
  '/api/v2/wallets/purchase-orders/quote',
  '/api/v2/wallets/purchase-orders/{order_id}',
  '/api/v2/wallets/summary',
  '/api/v2/wallets/top-up/initiate',
  '/api/v2/wallets/top-up/verify',
  '/api/v2/wallets/transactions',
  '/api/v2/wallets/withdrawals',
  '/api/v2/wallets/withdrawals/eligibility',
  '/api/v2/wallets/withdrawals/quote',
  '/api/v2/wallets/withdrawals/{withdrawal_id}/receipt',
  '/api/v2/world-super-cup/countdown',
  '/api/v2/world-super-cup/groups/table',
  '/api/v2/world-super-cup/knockout/bracket',
  '/api/v2/world-super-cup/playoff/draw',
  '/api/v2/world-super-cup/qualification/explanation',
  '/api/v2/world/clubs/{club_id}/context',
  '/api/v2/world/competitions/{competition_id}/context',
  '/api/v2/world/cultures',
  '/api/v2/world/narratives',
  '/api/v2/ws/market/{listing_id}',
  '/api/v2/ws/match/{match_id}',
  '/api/v2/ws/notifications',
  '/api/v2/ws/spectate/{match_id}',
  '/api/v2/ws/tournament/{tournament_id}',
  '/health',
  '/ready',
  '/version',
};

const Map<String, String> gteApiCanonicalPathByAlias = <String, String>{
  '/academy': '/api/v2/academy',
  '/academy/awards': '/api/v2/academy/awards',
  '/academy/fixtures': '/api/v2/academy/fixtures',
  '/academy/generate': '/api/v2/academy/generate',
  '/academy/promote/{player_id}': '/api/v2/academy/promote/{player_id}',
  '/academy/qualification': '/api/v2/academy/qualification',
  '/academy/registration': '/api/v2/academy/registration',
  '/academy/season-summary': '/api/v2/academy/season-summary',
  '/academy/standings': '/api/v2/academy/standings',
  '/admin-engine/bootstrap': '/api/v2/admin-engine/bootstrap',
  '/admin/admin-engine/calendar-rules':
      '/api/v2/admin/admin-engine/calendar-rules',
  '/admin/admin-engine/feature-flags':
      '/api/v2/admin/admin-engine/feature-flags',
  '/admin/admin-engine/reward-rules': '/api/v2/admin/admin-engine/reward-rules',
  '/admin/admin-engine/schedule-preview':
      '/api/v2/admin/admin-engine/schedule-preview',
  '/admin/ban-user': '/api/v2/admin/ban-user',
  '/admin/broadcast-rights/jobs/run': '/api/v2/admin/broadcast-rights/jobs/run',
  '/admin/calendar-engine/events': '/api/v2/admin/calendar-engine/events',
  '/admin/calendar-engine/hosted-competitions/{competition_id}/launch':
      '/api/v2/admin/calendar-engine/hosted-competitions/{competition_id}/launch',
  '/admin/calendar-engine/national-competitions/{competition_id}/launch':
      '/api/v2/admin/calendar-engine/national-competitions/{competition_id}/launch',
  '/admin/calendar-engine/seasons': '/api/v2/admin/calendar-engine/seasons',
  '/admin/club-infra/seed': '/api/v2/admin/club-infra/seed',
  '/admin/config/liquidity-bands': '/api/v2/admin/config/liquidity-bands',
  '/admin/config/player-card-market-integrity':
      '/api/v2/admin/config/player-card-market-integrity',
  '/admin/config/supply-tiers': '/api/v2/admin/config/supply-tiers',
  '/admin/config/suspicion-thresholds':
      '/api/v2/admin/config/suspicion-thresholds',
  '/admin/config/value-controls': '/api/v2/admin/config/value-controls',
  '/admin/config/value-controls/audits':
      '/api/v2/admin/config/value-controls/audits',
  '/admin/config/value-controls/integrity/candidates':
      '/api/v2/admin/config/value-controls/integrity/candidates',
  '/admin/config/value-controls/players/{player_id}':
      '/api/v2/admin/config/value-controls/players/{player_id}',
  '/admin/config/value-controls/preview/{player_id}':
      '/api/v2/admin/config/value-controls/preview/{player_id}',
  '/admin/config/value-controls/recompute':
      '/api/v2/admin/config/value-controls/recompute',
  '/admin/config/value-controls/run-history':
      '/api/v2/admin/config/value-controls/run-history',
  '/admin/creator-campaigns/{campaign_id}/metrics':
      '/api/v2/admin/creator-campaigns/{campaign_id}/metrics',
  '/admin/creator/applications': '/api/v2/admin/creator/applications',
  '/admin/creator/applications/{application_id}/approve':
      '/api/v2/admin/creator/applications/{application_id}/approve',
  '/admin/creator/applications/{application_id}/reject':
      '/api/v2/admin/creator/applications/{application_id}/reject',
  '/admin/creator/applications/{application_id}/request-verification':
      '/api/v2/admin/creator/applications/{application_id}/request-verification',
  '/admin/creator/cards/assign': '/api/v2/admin/creator/cards/assign',
  '/admin/creator/dashboard': '/api/v2/admin/creator/dashboard',
  '/admin/creator/fan-share-market/control':
      '/api/v2/admin/creator/fan-share-market/control',
  '/admin/discovery/featured-rails': '/api/v2/admin/discovery/featured-rails',
  '/admin/disputes': '/api/v2/admin/disputes',
  '/admin/disputes/{dispute_id}/assign':
      '/api/v2/admin/disputes/{dispute_id}/assign',
  '/admin/disputes/{dispute_id}/status':
      '/api/v2/admin/disputes/{dispute_id}/status',
  '/admin/economy/burn-events': '/api/v2/admin/economy/burn-events',
  '/admin/economy/fx-rates': '/api/v2/admin/economy/fx-rates',
  '/admin/economy/gift-catalog': '/api/v2/admin/economy/gift-catalog',
  '/admin/economy/gift-combo-rules': '/api/v2/admin/economy/gift-combo-rules',
  '/admin/economy/governor': '/api/v2/admin/economy/governor',
  '/admin/economy/governor/apply': '/api/v2/admin/economy/governor/apply',
  '/admin/economy/governor/evaluate': '/api/v2/admin/economy/governor/evaluate',
  '/admin/economy/governor/policy': '/api/v2/admin/economy/governor/policy',
  '/admin/economy/regional-pricing': '/api/v2/admin/economy/regional-pricing',
  '/admin/economy/revenue-share-rules':
      '/api/v2/admin/economy/revenue-share-rules',
  '/admin/economy/service-pricing': '/api/v2/admin/economy/service-pricing',
  '/admin/fan-predictions/matches/{match_id}/fixture':
      '/api/v2/admin/fan-predictions/matches/{match_id}/fixture',
  '/admin/fan-predictions/matches/{match_id}/settlement':
      '/api/v2/admin/fan-predictions/matches/{match_id}/settlement',
  '/admin/fan-wars/creator-country-assignments':
      '/api/v2/admin/fan-wars/creator-country-assignments',
  '/admin/fan-wars/nations-cup': '/api/v2/admin/fan-wars/nations-cup',
  '/admin/fan-wars/nations-cup/{competition_id}/advance':
      '/api/v2/admin/fan-wars/nations-cup/{competition_id}/advance',
  '/admin/fan-wars/points': '/api/v2/admin/fan-wars/points',
  '/admin/fan-wars/profiles': '/api/v2/admin/fan-wars/profiles',
  '/admin/fan-wars/profiles/{profile_id}/rivals/{rival_profile_id}':
      '/api/v2/admin/fan-wars/profiles/{profile_id}/rivals/{rival_profile_id}',
  '/admin/federations/run-jobs': '/api/v2/admin/federations/run-jobs',
  '/admin/flags': '/api/v2/admin/flags',
  '/admin/football-events/categories':
      '/api/v2/admin/football-events/categories',
  '/admin/football-events/effects/expire':
      '/api/v2/admin/football-events/effects/expire',
  '/admin/football-events/events': '/api/v2/admin/football-events/events',
  '/admin/football-events/events/import':
      '/api/v2/admin/football-events/events/import',
  '/admin/football-events/events/{event_id}/review':
      '/api/v2/admin/football-events/events/{event_id}/review',
  '/admin/football-events/events/{event_id}/severity':
      '/api/v2/admin/football-events/events/{event_id}/severity',
  '/admin/football-events/rules': '/api/v2/admin/football-events/rules',
  '/admin/governance/proposals/{proposal_id}/status':
      '/api/v2/admin/governance/proposals/{proposal_id}/status',
  '/admin/history-engagement/run-workers':
      '/api/v2/admin/history-engagement/run-workers',
  '/admin/hosted-competitions': '/api/v2/admin/hosted-competitions',
  '/admin/hosted-competitions/seed': '/api/v2/admin/hosted-competitions/seed',
  '/admin/hosted-competitions/{competition_id}/finalize':
      '/api/v2/admin/hosted-competitions/{competition_id}/finalize',
  '/admin/hosted-competitions/{competition_id}/launch':
      '/api/v2/admin/hosted-competitions/{competition_id}/launch',
  '/admin/integrity-engine/incidents/{incident_id}/resolve':
      '/api/v2/admin/integrity-engine/incidents/{incident_id}/resolve',
  '/admin/integrity-engine/scan': '/api/v2/admin/integrity-engine/scan',
  '/admin/jackpot/balance': '/api/v2/admin/jackpot/balance',
  '/admin/jackpot/runtime': '/api/v2/admin/jackpot/runtime',
  '/admin/jackpot/trigger': '/api/v2/admin/jackpot/trigger',
  '/admin/leaderboard/season/archive':
      '/api/v2/admin/leaderboard/season/archive',
  '/admin/leaderboard/season/reset': '/api/v2/admin/leaderboard/season/reset',
  '/admin/media-engine/creator-league/clubs/{club_id}/stadium-level':
      '/api/v2/admin/media-engine/creator-league/clubs/{club_id}/stadium-level',
  '/admin/media-engine/creator-league/matches/{match_id}/analytics':
      '/api/v2/admin/media-engine/creator-league/matches/{match_id}/analytics',
  '/admin/media-engine/creator-league/matches/{match_id}/settlement':
      '/api/v2/admin/media-engine/creator-league/matches/{match_id}/settlement',
  '/admin/media-engine/creator-league/stadium-controls':
      '/api/v2/admin/media-engine/creator-league/stadium-controls',
  '/admin/media-engine/exports': '/api/v2/admin/media-engine/exports',
  '/admin/media-engine/highlights': '/api/v2/admin/media-engine/highlights',
  '/admin/media-engine/highlights/{storage_key:path}/archive':
      '/api/v2/admin/media-engine/highlights/{storage_key:path}/archive',
  '/admin/media-engine/share-exports/{export_id}/revenue-attributions':
      '/api/v2/admin/media-engine/share-exports/{export_id}/revenue-attributions',
  '/admin/media-engine/snapshots': '/api/v2/admin/media-engine/snapshots',
  '/admin/moderation/reports': '/api/v2/admin/moderation/reports',
  '/admin/moderation/reports/summary':
      '/api/v2/admin/moderation/reports/summary',
  '/admin/moderation/reports/{report_id}/assign':
      '/api/v2/admin/moderation/reports/{report_id}/assign',
  '/admin/moderation/reports/{report_id}/resolve':
      '/api/v2/admin/moderation/reports/{report_id}/resolve',
  '/admin/national-team-engine/competitions':
      '/api/v2/admin/national-team-engine/competitions',
  '/admin/national-team-engine/competitions/seed-defaults':
      '/api/v2/admin/national-team-engine/competitions/seed-defaults',
  '/admin/national-team-engine/competitions/{competition_id}/ads':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads',
  '/admin/national-team-engine/competitions/{competition_id}/ads/rotate':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads/rotate',
  '/admin/national-team-engine/competitions/{competition_id}/ads/{ad_id}':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads/{ad_id}',
  '/admin/national-team-engine/competitions/{competition_id}/entries':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/entries',
  '/admin/national-team-engine/competitions/{competition_id}/entries/lock':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/entries/lock',
  '/admin/national-team-engine/competitions/{competition_id}/lifecycle/advance':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/lifecycle/advance',
  '/admin/national-team-engine/competitions/{competition_id}/rentals/cleanup':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/rentals/cleanup',
  '/admin/national-team-engine/competitions/{competition_id}/story-events/generate':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/story-events/generate',
  '/admin/national-team-engine/competitions/{competition_id}/theme':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/theme',
  '/admin/national-team-engine/entries/{entry_id}/squad':
      '/api/v2/admin/national-team-engine/entries/{entry_id}/squad',
  '/admin/notifications/announcements':
      '/api/v2/admin/notifications/announcements',
  '/admin/ops/alerts': '/api/v2/admin/ops/alerts',
  '/admin/ops/audit': '/api/v2/admin/ops/audit',
  '/admin/ops/broadcast-expiration': '/api/v2/admin/ops/broadcast-expiration',
  '/admin/ops/broadcast-revenue': '/api/v2/admin/ops/broadcast-revenue',
  '/admin/ops/club-market-valuations':
      '/api/v2/admin/ops/club-market-valuations',
  '/admin/ops/dashboard': '/api/v2/admin/ops/dashboard',
  '/admin/ops/fan-updates': '/api/v2/admin/ops/fan-updates',
  '/admin/ops/identity-evolution': '/api/v2/admin/ops/identity-evolution',
  '/admin/ops/integrity-scan': '/api/v2/admin/ops/integrity-scan',
  '/admin/ops/media-generation': '/api/v2/admin/ops/media-generation',
  '/admin/ops/media-retention': '/api/v2/admin/ops/media-retention',
  '/admin/ops/national-team-rental-cleanup':
      '/api/v2/admin/ops/national-team-rental-cleanup',
  '/admin/ops/ownership-groups/reputation':
      '/api/v2/admin/ops/ownership-groups/reputation',
  '/admin/ops/platform-infra': '/api/v2/admin/ops/platform-infra',
  '/admin/ops/stadium-ad-rotation': '/api/v2/admin/ops/stadium-ad-rotation',
  '/admin/ops/tournament-storylines': '/api/v2/admin/ops/tournament-storylines',
  '/admin/ownership-groups/reputation-cycle':
      '/api/v2/admin/ownership-groups/reputation-cycle',
  '/admin/player-import/card-supply': '/api/v2/admin/player-import/card-supply',
  '/admin/player-import/card-supply/csv':
      '/api/v2/admin/player-import/card-supply/csv',
  '/admin/player-import/jobs': '/api/v2/admin/player-import/jobs',
  '/admin/player-import/jobs/{job_id}':
      '/api/v2/admin/player-import/jobs/{job_id}',
  '/admin/player-import/youth/generate':
      '/api/v2/admin/player-import/youth/generate',
  '/admin/policies/country-policies': '/api/v2/admin/policies/country-policies',
  '/admin/policies/documents': '/api/v2/admin/policies/documents',
  '/admin/policies/documents/versions':
      '/api/v2/admin/policies/documents/versions',
  '/admin/policies/regions/override': '/api/v2/admin/policies/regions/override',
  '/admin/real-world/providers': '/api/v2/admin/real-world/providers',
  '/admin/real-world/providers/{provider_id}/sync':
      '/api/v2/admin/real-world/providers/{provider_id}/sync',
  '/admin/regen-universe/jobs/dna-evolution':
      '/api/v2/admin/regen-universe/jobs/dna-evolution',
  '/admin/regen-universe/jobs/rivalry-detection':
      '/api/v2/admin/regen-universe/jobs/rivalry-detection',
  '/admin/regen-universe/jobs/story-regeneration':
      '/api/v2/admin/regen-universe/jobs/story-regeneration',
  '/admin/regen-universe/jobs/tournament-scheduling':
      '/api/v2/admin/regen-universe/jobs/tournament-scheduling',
  '/admin/regen-universe/national-regens/preseed':
      '/api/v2/admin/regen-universe/national-regens/preseed',
  '/admin/regen-universe/players/{player_id}/portrait/ban':
      '/api/v2/admin/regen-universe/players/{player_id}/portrait/ban',
  '/admin/regen-universe/players/{player_id}/portrait/override':
      '/api/v2/admin/regen-universe/players/{player_id}/portrait/override',
  '/admin/regen-universe/players/{player_id}/portrait/regenerate':
      '/api/v2/admin/regen-universe/players/{player_id}/portrait/regenerate',
  '/admin/regen-universe/seasons': '/api/v2/admin/regen-universe/seasons',
  '/admin/regen-universe/seasons/{season_id}/close':
      '/api/v2/admin/regen-universe/seasons/{season_id}/close',
  '/admin/regen-universe/seasons/{season_id}/evolution':
      '/api/v2/admin/regen-universe/seasons/{season_id}/evolution',
  '/admin/regen-universe/youth-tournaments':
      '/api/v2/admin/regen-universe/youth-tournaments',
  '/admin/reward-engine/promo-pool/credits':
      '/api/v2/admin/reward-engine/promo-pool/credits',
  '/admin/reward-engine/settlements': '/api/v2/admin/reward-engine/settlements',
  '/admin/risk-ops/actions': '/api/v2/admin/risk-ops/actions',
  '/admin/risk-ops/actions/{action_id}/release':
      '/api/v2/admin/risk-ops/actions/{action_id}/release',
  '/admin/risk-ops/aml-cases': '/api/v2/admin/risk-ops/aml-cases',
  '/admin/risk-ops/audit-logs': '/api/v2/admin/risk-ops/audit-logs',
  '/admin/risk-ops/cases/{case_type}/{case_id}/resolve':
      '/api/v2/admin/risk-ops/cases/{case_type}/{case_id}/resolve',
  '/admin/risk-ops/evaluate': '/api/v2/admin/risk-ops/evaluate',
  '/admin/risk-ops/fraud-cases': '/api/v2/admin/risk-ops/fraud-cases',
  '/admin/risk-ops/overview': '/api/v2/admin/risk-ops/overview',
  '/admin/risk-ops/scan': '/api/v2/admin/risk-ops/scan',
  '/admin/risk-ops/signals': '/api/v2/admin/risk-ops/signals',
  '/admin/risk-ops/system-events': '/api/v2/admin/risk-ops/system-events',
  '/admin/sponsorship/analytics': '/api/v2/admin/sponsorship/analytics',
  '/admin/sponsorship/categories/{category}':
      '/api/v2/admin/sponsorship/categories/{category}',
  '/admin/sponsorship/contracts/{contract_id}/review':
      '/api/v2/admin/sponsorship/contracts/{contract_id}/review',
  '/admin/sponsorship/contracts/{contract_id}/settle-next':
      '/api/v2/admin/sponsorship/contracts/{contract_id}/settle-next',
  '/admin/sponsorship/offers': '/api/v2/admin/sponsorship/offers',
  '/admin/sponsorship/offers/{offer_id}/assign':
      '/api/v2/admin/sponsorship/offers/{offer_id}/assign',
  '/admin/sponsorship/offers/{offer_id}/rule':
      '/api/v2/admin/sponsorship/offers/{offer_id}/rule',
  '/admin/sponsorship/packages': '/api/v2/admin/sponsorship/packages',
  '/admin/story-feed': '/api/v2/admin/story-feed',
  '/admin/streamer-tournaments/policy':
      '/api/v2/admin/streamer-tournaments/policy',
  '/admin/streamer-tournaments/risk-signals':
      '/api/v2/admin/streamer-tournaments/risk-signals',
  '/admin/streamer-tournaments/risk-signals/{signal_id}/review':
      '/api/v2/admin/streamer-tournaments/risk-signals/{signal_id}/review',
  '/admin/streamer-tournaments/{tournament_id}/review':
      '/api/v2/admin/streamer-tournaments/{tournament_id}/review',
  '/admin/streamer-tournaments/{tournament_id}/settle':
      '/api/v2/admin/streamer-tournaments/{tournament_id}/settle',
  '/admin/world/clubs/{club_id}/context':
      '/api/v2/admin/world/clubs/{club_id}/context',
  '/admin/world/cultures/{culture_key}':
      '/api/v2/admin/world/cultures/{culture_key}',
  '/admin/world/narratives/{narrative_slug}':
      '/api/v2/admin/world/narratives/{narrative_slug}',
  '/ads/create': '/api/v2/ads/create',
  '/ads/performance': '/api/v2/ads/performance',
  '/agents': '/api/v2/agents',
  '/agents/config': '/api/v2/agents/config',
  '/agents/performance': '/api/v2/agents/performance',
  '/agents/run': '/api/v2/agents/run',
  '/agents/summary': '/api/v2/agents/summary',
  '/ai-reporter/feed': '/api/v2/ai-reporter/feed',
  '/ai-reporter/run': '/api/v2/ai-reporter/run',
  '/ai/leagues': '/api/v2/ai/leagues',
  '/ai/match/{match_id}': '/api/v2/ai/match/{match_id}',
  '/analytics/clip/{clip_id}': '/api/v2/analytics/clip/{clip_id}',
  '/analytics/dashboard/drop-off': '/api/v2/analytics/dashboard/drop-off',
  '/analytics/dashboard/top-clips': '/api/v2/analytics/dashboard/top-clips',
  '/analytics/frontend': '/api/v2/analytics/frontend',
  '/api/academy': '/api/v2/academy',
  '/api/academy/awards': '/api/v2/academy/awards',
  '/api/academy/fixtures': '/api/v2/academy/fixtures',
  '/api/academy/generate': '/api/v2/academy/generate',
  '/api/academy/promote/{player_id}': '/api/v2/academy/promote/{player_id}',
  '/api/academy/qualification': '/api/v2/academy/qualification',
  '/api/academy/registration': '/api/v2/academy/registration',
  '/api/academy/season-summary': '/api/v2/academy/season-summary',
  '/api/academy/standings': '/api/v2/academy/standings',
  '/api/admin-engine/bootstrap': '/api/v2/admin-engine/bootstrap',
  '/api/admin/access': '/api/v2/admin/access',
  '/api/admin/access/permissions': '/api/v2/admin/access/permissions',
  '/api/admin/access/{user_id}/permissions':
      '/api/v2/admin/access/{user_id}/permissions',
  '/api/admin/admin-engine/calendar-rules':
      '/api/v2/admin/admin-engine/calendar-rules',
  '/api/admin/admin-engine/feature-flags':
      '/api/v2/admin/admin-engine/feature-flags',
  '/api/admin/admin-engine/reward-rules':
      '/api/v2/admin/admin-engine/reward-rules',
  '/api/admin/admin-engine/schedule-preview':
      '/api/v2/admin/admin-engine/schedule-preview',
  '/api/admin/analytics/agent-learning':
      '/api/v2/admin/analytics/agent-learning',
  '/api/admin/analytics/anomalies': '/api/v2/admin/analytics/anomalies',
  '/api/admin/analytics/funnels': '/api/v2/admin/analytics/funnels',
  '/api/admin/analytics/match-outcomes':
      '/api/v2/admin/analytics/match-outcomes',
  '/api/admin/analytics/player-matching':
      '/api/v2/admin/analytics/player-matching',
  '/api/admin/analytics/player-matching/recompute-weights':
      '/api/v2/admin/analytics/player-matching/recompute-weights',
  '/api/admin/analytics/price-predictions':
      '/api/v2/admin/analytics/price-predictions',
  '/api/admin/analytics/summary': '/api/v2/admin/analytics/summary',
  '/api/admin/analytics/user-segments': '/api/v2/admin/analytics/user-segments',
  '/api/admin/ban-user': '/api/v2/admin/ban-user',
  '/api/admin/broadcast-rights/jobs/run':
      '/api/v2/admin/broadcast-rights/jobs/run',
  '/api/admin/calendar-engine/events': '/api/v2/admin/calendar-engine/events',
  '/api/admin/calendar-engine/hosted-competitions/{competition_id}/launch':
      '/api/v2/admin/calendar-engine/hosted-competitions/{competition_id}/launch',
  '/api/admin/calendar-engine/national-competitions/{competition_id}/launch':
      '/api/v2/admin/calendar-engine/national-competitions/{competition_id}/launch',
  '/api/admin/calendar-engine/seasons': '/api/v2/admin/calendar-engine/seasons',
  '/api/admin/club-infra/seed': '/api/v2/admin/club-infra/seed',
  '/api/admin/clubs/academy-analytics': '/api/v2/admin/clubs/academy-analytics',
  '/api/admin/clubs/analytics': '/api/v2/admin/clubs/analytics',
  '/api/admin/clubs/finance-analytics': '/api/v2/admin/clubs/finance-analytics',
  '/api/admin/clubs/ops-summary': '/api/v2/admin/clubs/ops-summary',
  '/api/admin/clubs/scouting-analytics':
      '/api/v2/admin/clubs/scouting-analytics',
  '/api/admin/clubs/sponsorship-analytics':
      '/api/v2/admin/clubs/sponsorship-analytics',
  '/api/admin/clubs/summary': '/api/v2/admin/clubs/summary',
  '/api/admin/clubs/{club_id}': '/api/v2/admin/clubs/{club_id}',
  '/api/admin/clubs/{club_id}/moderate-branding':
      '/api/v2/admin/clubs/{club_id}/moderate-branding',
  '/api/admin/competitions': '/api/v2/admin/competitions',
  '/api/admin/competitions/reminders/dispatch':
      '/api/v2/admin/competitions/reminders/dispatch',
  '/api/admin/competitive-integrity/matches/{match_id}/validation':
      '/api/v2/admin/competitive-integrity/matches/{match_id}/validation',
  '/api/admin/competitive-integrity/workers/run-once':
      '/api/v2/admin/competitive-integrity/workers/run-once',
  '/api/admin/config/liquidity-bands': '/api/v2/admin/config/liquidity-bands',
  '/api/admin/config/player-card-market-integrity':
      '/api/v2/admin/config/player-card-market-integrity',
  '/api/admin/config/supply-tiers': '/api/v2/admin/config/supply-tiers',
  '/api/admin/config/suspicion-thresholds':
      '/api/v2/admin/config/suspicion-thresholds',
  '/api/admin/config/value-controls': '/api/v2/admin/config/value-controls',
  '/api/admin/config/value-controls/audits':
      '/api/v2/admin/config/value-controls/audits',
  '/api/admin/config/value-controls/integrity/candidates':
      '/api/v2/admin/config/value-controls/integrity/candidates',
  '/api/admin/config/value-controls/players/{player_id}':
      '/api/v2/admin/config/value-controls/players/{player_id}',
  '/api/admin/config/value-controls/preview/{player_id}':
      '/api/v2/admin/config/value-controls/preview/{player_id}',
  '/api/admin/config/value-controls/recompute':
      '/api/v2/admin/config/value-controls/recompute',
  '/api/admin/config/value-controls/run-history':
      '/api/v2/admin/config/value-controls/run-history',
  '/api/admin/creator-campaigns/{campaign_id}/metrics':
      '/api/v2/admin/creator-campaigns/{campaign_id}/metrics',
  '/api/admin/creator/applications': '/api/v2/admin/creator/applications',
  '/api/admin/creator/applications/{application_id}/approve':
      '/api/v2/admin/creator/applications/{application_id}/approve',
  '/api/admin/creator/applications/{application_id}/reject':
      '/api/v2/admin/creator/applications/{application_id}/reject',
  '/api/admin/creator/applications/{application_id}/request-verification':
      '/api/v2/admin/creator/applications/{application_id}/request-verification',
  '/api/admin/creator/cards/assign': '/api/v2/admin/creator/cards/assign',
  '/api/admin/creator/dashboard': '/api/v2/admin/creator/dashboard',
  '/api/admin/creator/fan-share-market/control':
      '/api/v2/admin/creator/fan-share-market/control',
  '/api/admin/discovery/featured-rails':
      '/api/v2/admin/discovery/featured-rails',
  '/api/admin/disputes': '/api/v2/admin/disputes',
  '/api/admin/disputes/{dispute_id}/assign':
      '/api/v2/admin/disputes/{dispute_id}/assign',
  '/api/admin/disputes/{dispute_id}/status':
      '/api/v2/admin/disputes/{dispute_id}/status',
  '/api/admin/economy/burn-events': '/api/v2/admin/economy/burn-events',
  '/api/admin/economy/fx-rates': '/api/v2/admin/economy/fx-rates',
  '/api/admin/economy/gift-catalog': '/api/v2/admin/economy/gift-catalog',
  '/api/admin/economy/gift-combo-rules':
      '/api/v2/admin/economy/gift-combo-rules',
  '/api/admin/economy/governor': '/api/v2/admin/economy/governor',
  '/api/admin/economy/governor/apply': '/api/v2/admin/economy/governor/apply',
  '/api/admin/economy/governor/evaluate':
      '/api/v2/admin/economy/governor/evaluate',
  '/api/admin/economy/governor/policy': '/api/v2/admin/economy/governor/policy',
  '/api/admin/economy/regional-pricing':
      '/api/v2/admin/economy/regional-pricing',
  '/api/admin/economy/revenue-share-rules':
      '/api/v2/admin/economy/revenue-share-rules',
  '/api/admin/economy/service-pricing': '/api/v2/admin/economy/service-pricing',
  '/api/admin/fan-predictions/matches/{match_id}/fixture':
      '/api/v2/admin/fan-predictions/matches/{match_id}/fixture',
  '/api/admin/fan-predictions/matches/{match_id}/settlement':
      '/api/v2/admin/fan-predictions/matches/{match_id}/settlement',
  '/api/admin/fan-wars/creator-country-assignments':
      '/api/v2/admin/fan-wars/creator-country-assignments',
  '/api/admin/fan-wars/nations-cup': '/api/v2/admin/fan-wars/nations-cup',
  '/api/admin/fan-wars/nations-cup/{competition_id}/advance':
      '/api/v2/admin/fan-wars/nations-cup/{competition_id}/advance',
  '/api/admin/fan-wars/points': '/api/v2/admin/fan-wars/points',
  '/api/admin/fan-wars/profiles': '/api/v2/admin/fan-wars/profiles',
  '/api/admin/fan-wars/profiles/{profile_id}/rivals/{rival_profile_id}':
      '/api/v2/admin/fan-wars/profiles/{profile_id}/rivals/{rival_profile_id}',
  '/api/admin/federations/run-jobs': '/api/v2/admin/federations/run-jobs',
  '/api/admin/finance/account-controls':
      '/api/v2/admin/finance/account-controls',
  '/api/admin/finance/account-controls/{user_id}':
      '/api/v2/admin/finance/account-controls/{user_id}',
  '/api/admin/finance/control-tower': '/api/v2/admin/finance/control-tower',
  '/api/admin/finance/manual-price-overrides':
      '/api/v2/admin/finance/manual-price-overrides',
  '/api/admin/finance/manual-price-overrides/{asset_type}/{asset_id}':
      '/api/v2/admin/finance/manual-price-overrides/{asset_type}/{asset_id}',
  '/api/admin/finance/match-kill-switches':
      '/api/v2/admin/finance/match-kill-switches',
  '/api/admin/finance/match-kill-switches/{match_id}':
      '/api/v2/admin/finance/match-kill-switches/{match_id}',
  '/api/admin/finance/reconciliation': '/api/v2/admin/finance/reconciliation',
  '/api/admin/finance/simulate': '/api/v2/admin/finance/simulate',
  '/api/admin/finance/wallet-protection':
      '/api/v2/admin/finance/wallet-protection',
  '/api/admin/flags': '/api/v2/admin/flags',
  '/api/admin/football-events/categories':
      '/api/v2/admin/football-events/categories',
  '/api/admin/football-events/effects/expire':
      '/api/v2/admin/football-events/effects/expire',
  '/api/admin/football-events/events': '/api/v2/admin/football-events/events',
  '/api/admin/football-events/events/import':
      '/api/v2/admin/football-events/events/import',
  '/api/admin/football-events/events/{event_id}/review':
      '/api/v2/admin/football-events/events/{event_id}/review',
  '/api/admin/football-events/events/{event_id}/severity':
      '/api/v2/admin/football-events/events/{event_id}/severity',
  '/api/admin/football-events/rules': '/api/v2/admin/football-events/rules',
  '/api/admin/god-mode/audit-events': '/api/v2/admin/god-mode/audit-events',
  '/api/admin/god-mode/bootstrap': '/api/v2/admin/god-mode/bootstrap',
  '/api/admin/god-mode/commissions': '/api/v2/admin/god-mode/commissions',
  '/api/admin/god-mode/competition-controls':
      '/api/v2/admin/god-mode/competition-controls',
  '/api/admin/god-mode/high-risk-actions':
      '/api/v2/admin/god-mode/high-risk-actions',
  '/api/admin/god-mode/liquidity/interventions':
      '/api/v2/admin/god-mode/liquidity/interventions',
  '/api/admin/god-mode/payment-rails': '/api/v2/admin/god-mode/payment-rails',
  '/api/admin/god-mode/payment-rails/health':
      '/api/v2/admin/god-mode/payment-rails/health',
  '/api/admin/god-mode/roles': '/api/v2/admin/god-mode/roles',
  '/api/admin/god-mode/treasury': '/api/v2/admin/god-mode/treasury',
  '/api/admin/god-mode/treasury/dashboard':
      '/api/v2/admin/god-mode/treasury/dashboard',
  '/api/admin/god-mode/treasury/withdrawals':
      '/api/v2/admin/god-mode/treasury/withdrawals',
  '/api/admin/god-mode/withdrawal-controls':
      '/api/v2/admin/god-mode/withdrawal-controls',
  '/api/admin/god-mode/withdrawals': '/api/v2/admin/god-mode/withdrawals',
  '/api/admin/god-mode/withdrawals/summary':
      '/api/v2/admin/god-mode/withdrawals/summary',
  '/api/admin/god-mode/withdrawals/{payout_request_id}':
      '/api/v2/admin/god-mode/withdrawals/{payout_request_id}',
  '/api/admin/governance/proposals/{proposal_id}/status':
      '/api/v2/admin/governance/proposals/{proposal_id}/status',
  '/api/admin/history-engagement/run-workers':
      '/api/v2/admin/history-engagement/run-workers',
  '/api/admin/hosted-competitions': '/api/v2/admin/hosted-competitions',
  '/api/admin/hosted-competitions/seed':
      '/api/v2/admin/hosted-competitions/seed',
  '/api/admin/hosted-competitions/{competition_id}/finalize':
      '/api/v2/admin/hosted-competitions/{competition_id}/finalize',
  '/api/admin/hosted-competitions/{competition_id}/launch':
      '/api/v2/admin/hosted-competitions/{competition_id}/launch',
  '/api/admin/integrity-engine/incidents/{incident_id}/resolve':
      '/api/v2/admin/integrity-engine/incidents/{incident_id}/resolve',
  '/api/admin/integrity-engine/scan': '/api/v2/admin/integrity-engine/scan',
  '/api/admin/jackpot/balance': '/api/v2/admin/jackpot/balance',
  '/api/admin/jackpot/runtime': '/api/v2/admin/jackpot/runtime',
  '/api/admin/jackpot/trigger': '/api/v2/admin/jackpot/trigger',
  '/api/admin/leaderboard/season/archive':
      '/api/v2/admin/leaderboard/season/archive',
  '/api/admin/leaderboard/season/reset':
      '/api/v2/admin/leaderboard/season/reset',
  '/api/admin/managers/audit-log': '/api/v2/admin/managers/audit-log',
  '/api/admin/managers/catalog/{manager_id}/supply':
      '/api/v2/admin/managers/catalog/{manager_id}/supply',
  '/api/admin/managers/competitions': '/api/v2/admin/managers/competitions',
  '/api/admin/managers/competitions/{code}':
      '/api/v2/admin/managers/competitions/{code}',
  '/api/admin/managers/competitions/{code}/orchestrate':
      '/api/v2/admin/managers/competitions/{code}/orchestrate',
  '/api/admin/media-engine/creator-league/clubs/{club_id}/stadium-level':
      '/api/v2/admin/media-engine/creator-league/clubs/{club_id}/stadium-level',
  '/api/admin/media-engine/creator-league/matches/{match_id}/analytics':
      '/api/v2/admin/media-engine/creator-league/matches/{match_id}/analytics',
  '/api/admin/media-engine/creator-league/matches/{match_id}/settlement':
      '/api/v2/admin/media-engine/creator-league/matches/{match_id}/settlement',
  '/api/admin/media-engine/creator-league/stadium-controls':
      '/api/v2/admin/media-engine/creator-league/stadium-controls',
  '/api/admin/media-engine/exports': '/api/v2/admin/media-engine/exports',
  '/api/admin/media-engine/highlights': '/api/v2/admin/media-engine/highlights',
  '/api/admin/media-engine/highlights/{storage_key:path}/archive':
      '/api/v2/admin/media-engine/highlights/{storage_key:path}/archive',
  '/api/admin/media-engine/share-exports/{export_id}/revenue-attributions':
      '/api/v2/admin/media-engine/share-exports/{export_id}/revenue-attributions',
  '/api/admin/media-engine/snapshots': '/api/v2/admin/media-engine/snapshots',
  '/api/admin/moderation/reports': '/api/v2/admin/moderation/reports',
  '/api/admin/moderation/reports/summary':
      '/api/v2/admin/moderation/reports/summary',
  '/api/admin/moderation/reports/{report_id}/assign':
      '/api/v2/admin/moderation/reports/{report_id}/assign',
  '/api/admin/moderation/reports/{report_id}/resolve':
      '/api/v2/admin/moderation/reports/{report_id}/resolve',
  '/api/admin/national-team-engine/competitions':
      '/api/v2/admin/national-team-engine/competitions',
  '/api/admin/national-team-engine/competitions/seed-defaults':
      '/api/v2/admin/national-team-engine/competitions/seed-defaults',
  '/api/admin/national-team-engine/competitions/{competition_id}/ads':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads',
  '/api/admin/national-team-engine/competitions/{competition_id}/ads/rotate':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads/rotate',
  '/api/admin/national-team-engine/competitions/{competition_id}/ads/{ad_id}':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads/{ad_id}',
  '/api/admin/national-team-engine/competitions/{competition_id}/entries':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/entries',
  '/api/admin/national-team-engine/competitions/{competition_id}/entries/lock':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/entries/lock',
  '/api/admin/national-team-engine/competitions/{competition_id}/lifecycle/advance':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/lifecycle/advance',
  '/api/admin/national-team-engine/competitions/{competition_id}/rentals/cleanup':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/rentals/cleanup',
  '/api/admin/national-team-engine/competitions/{competition_id}/story-events/generate':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/story-events/generate',
  '/api/admin/national-team-engine/competitions/{competition_id}/theme':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/theme',
  '/api/admin/national-team-engine/entries/{entry_id}/squad':
      '/api/v2/admin/national-team-engine/entries/{entry_id}/squad',
  '/api/admin/notifications/announcements':
      '/api/v2/admin/notifications/announcements',
  '/api/admin/ops/alerts': '/api/v2/admin/ops/alerts',
  '/api/admin/ops/audit': '/api/v2/admin/ops/audit',
  '/api/admin/ops/broadcast-expiration':
      '/api/v2/admin/ops/broadcast-expiration',
  '/api/admin/ops/broadcast-revenue': '/api/v2/admin/ops/broadcast-revenue',
  '/api/admin/ops/club-market-valuations':
      '/api/v2/admin/ops/club-market-valuations',
  '/api/admin/ops/dashboard': '/api/v2/admin/ops/dashboard',
  '/api/admin/ops/fan-updates': '/api/v2/admin/ops/fan-updates',
  '/api/admin/ops/identity-evolution': '/api/v2/admin/ops/identity-evolution',
  '/api/admin/ops/integrity-scan': '/api/v2/admin/ops/integrity-scan',
  '/api/admin/ops/media-generation': '/api/v2/admin/ops/media-generation',
  '/api/admin/ops/media-retention': '/api/v2/admin/ops/media-retention',
  '/api/admin/ops/national-team-rental-cleanup':
      '/api/v2/admin/ops/national-team-rental-cleanup',
  '/api/admin/ops/ownership-groups/reputation':
      '/api/v2/admin/ops/ownership-groups/reputation',
  '/api/admin/ops/platform-infra': '/api/v2/admin/ops/platform-infra',
  '/api/admin/ops/stadium-ad-rotation': '/api/v2/admin/ops/stadium-ad-rotation',
  '/api/admin/ops/tournament-storylines':
      '/api/v2/admin/ops/tournament-storylines',
  '/api/admin/ownership-groups/reputation-cycle':
      '/api/v2/admin/ownership-groups/reputation-cycle',
  '/api/admin/player-import/card-supply':
      '/api/v2/admin/player-import/card-supply',
  '/api/admin/player-import/card-supply/csv':
      '/api/v2/admin/player-import/card-supply/csv',
  '/api/admin/player-import/jobs': '/api/v2/admin/player-import/jobs',
  '/api/admin/player-import/jobs/{job_id}':
      '/api/v2/admin/player-import/jobs/{job_id}',
  '/api/admin/player-import/youth/generate':
      '/api/v2/admin/player-import/youth/generate',
  '/api/admin/policies/country-policies':
      '/api/v2/admin/policies/country-policies',
  '/api/admin/policies/documents': '/api/v2/admin/policies/documents',
  '/api/admin/policies/documents/versions':
      '/api/v2/admin/policies/documents/versions',
  '/api/admin/policies/regions/override':
      '/api/v2/admin/policies/regions/override',
  '/api/admin/real-world/providers': '/api/v2/admin/real-world/providers',
  '/api/admin/real-world/providers/{provider_id}/sync':
      '/api/v2/admin/real-world/providers/{provider_id}/sync',
  '/api/admin/referrals/analytics/summary':
      '/api/v2/admin/referrals/analytics/summary',
  '/api/admin/referrals/attributions': '/api/v2/admin/referrals/attributions',
  '/api/admin/referrals/creators': '/api/v2/admin/referrals/creators',
  '/api/admin/referrals/creators/{creator_id}':
      '/api/v2/admin/referrals/creators/{creator_id}',
  '/api/admin/referrals/creators/{creator_id}/reward-freeze':
      '/api/v2/admin/referrals/creators/{creator_id}/reward-freeze',
  '/api/admin/referrals/dashboard': '/api/v2/admin/referrals/dashboard',
  '/api/admin/referrals/flags': '/api/v2/admin/referrals/flags',
  '/api/admin/referrals/leaderboard': '/api/v2/admin/referrals/leaderboard',
  '/api/admin/referrals/rewards/pending':
      '/api/v2/admin/referrals/rewards/pending',
  '/api/admin/referrals/rewards/{reward_id}/review':
      '/api/v2/admin/referrals/rewards/{reward_id}/review',
  '/api/admin/referrals/share-codes': '/api/v2/admin/referrals/share-codes',
  '/api/admin/referrals/share-codes/{share_code_id}':
      '/api/v2/admin/referrals/share-codes/{share_code_id}',
  '/api/admin/referrals/share-codes/{share_code_id}/block':
      '/api/v2/admin/referrals/share-codes/{share_code_id}/block',
  '/api/admin/regen-universe/jobs/dna-evolution':
      '/api/v2/admin/regen-universe/jobs/dna-evolution',
  '/api/admin/regen-universe/jobs/rivalry-detection':
      '/api/v2/admin/regen-universe/jobs/rivalry-detection',
  '/api/admin/regen-universe/jobs/story-regeneration':
      '/api/v2/admin/regen-universe/jobs/story-regeneration',
  '/api/admin/regen-universe/jobs/tournament-scheduling':
      '/api/v2/admin/regen-universe/jobs/tournament-scheduling',
  '/api/admin/regen-universe/national-regens/preseed':
      '/api/v2/admin/regen-universe/national-regens/preseed',
  '/api/admin/regen-universe/players/{player_id}/portrait/ban':
      '/api/v2/admin/regen-universe/players/{player_id}/portrait/ban',
  '/api/admin/regen-universe/players/{player_id}/portrait/override':
      '/api/v2/admin/regen-universe/players/{player_id}/portrait/override',
  '/api/admin/regen-universe/players/{player_id}/portrait/regenerate':
      '/api/v2/admin/regen-universe/players/{player_id}/portrait/regenerate',
  '/api/admin/regen-universe/seasons': '/api/v2/admin/regen-universe/seasons',
  '/api/admin/regen-universe/seasons/{season_id}/close':
      '/api/v2/admin/regen-universe/seasons/{season_id}/close',
  '/api/admin/regen-universe/seasons/{season_id}/evolution':
      '/api/v2/admin/regen-universe/seasons/{season_id}/evolution',
  '/api/admin/regen-universe/youth-tournaments':
      '/api/v2/admin/regen-universe/youth-tournaments',
  '/api/admin/reward-engine/promo-pool/credits':
      '/api/v2/admin/reward-engine/promo-pool/credits',
  '/api/admin/reward-engine/settlements':
      '/api/v2/admin/reward-engine/settlements',
  '/api/admin/risk-ops/actions': '/api/v2/admin/risk-ops/actions',
  '/api/admin/risk-ops/actions/{action_id}/release':
      '/api/v2/admin/risk-ops/actions/{action_id}/release',
  '/api/admin/risk-ops/aml-cases': '/api/v2/admin/risk-ops/aml-cases',
  '/api/admin/risk-ops/audit-logs': '/api/v2/admin/risk-ops/audit-logs',
  '/api/admin/risk-ops/cases/{case_type}/{case_id}/resolve':
      '/api/v2/admin/risk-ops/cases/{case_type}/{case_id}/resolve',
  '/api/admin/risk-ops/evaluate': '/api/v2/admin/risk-ops/evaluate',
  '/api/admin/risk-ops/fraud-cases': '/api/v2/admin/risk-ops/fraud-cases',
  '/api/admin/risk-ops/overview': '/api/v2/admin/risk-ops/overview',
  '/api/admin/risk-ops/scan': '/api/v2/admin/risk-ops/scan',
  '/api/admin/risk-ops/signals': '/api/v2/admin/risk-ops/signals',
  '/api/admin/risk-ops/system-events': '/api/v2/admin/risk-ops/system-events',
  '/api/admin/sponsorship/analytics': '/api/v2/admin/sponsorship/analytics',
  '/api/admin/sponsorship/categories/{category}':
      '/api/v2/admin/sponsorship/categories/{category}',
  '/api/admin/sponsorship/contracts/{contract_id}/review':
      '/api/v2/admin/sponsorship/contracts/{contract_id}/review',
  '/api/admin/sponsorship/contracts/{contract_id}/settle-next':
      '/api/v2/admin/sponsorship/contracts/{contract_id}/settle-next',
  '/api/admin/sponsorship/offers': '/api/v2/admin/sponsorship/offers',
  '/api/admin/sponsorship/offers/{offer_id}/assign':
      '/api/v2/admin/sponsorship/offers/{offer_id}/assign',
  '/api/admin/sponsorship/offers/{offer_id}/rule':
      '/api/v2/admin/sponsorship/offers/{offer_id}/rule',
  '/api/admin/sponsorship/packages': '/api/v2/admin/sponsorship/packages',
  '/api/admin/story-feed': '/api/v2/admin/story-feed',
  '/api/admin/streamer-tournaments/policy':
      '/api/v2/admin/streamer-tournaments/policy',
  '/api/admin/streamer-tournaments/risk-signals':
      '/api/v2/admin/streamer-tournaments/risk-signals',
  '/api/admin/streamer-tournaments/risk-signals/{signal_id}/review':
      '/api/v2/admin/streamer-tournaments/risk-signals/{signal_id}/review',
  '/api/admin/streamer-tournaments/{tournament_id}/review':
      '/api/v2/admin/streamer-tournaments/{tournament_id}/review',
  '/api/admin/streamer-tournaments/{tournament_id}/settle':
      '/api/v2/admin/streamer-tournaments/{tournament_id}/settle',
  '/api/admin/treasury/bank-accounts': '/api/v2/admin/treasury/bank-accounts',
  '/api/admin/treasury/bank-accounts/{account_id}':
      '/api/v2/admin/treasury/bank-accounts/{account_id}',
  '/api/admin/treasury/dashboard': '/api/v2/admin/treasury/dashboard',
  '/api/admin/treasury/deposits': '/api/v2/admin/treasury/deposits',
  '/api/admin/treasury/deposits/{deposit_id}/confirm':
      '/api/v2/admin/treasury/deposits/{deposit_id}/confirm',
  '/api/admin/treasury/deposits/{deposit_id}/reject':
      '/api/v2/admin/treasury/deposits/{deposit_id}/reject',
  '/api/admin/treasury/deposits/{deposit_id}/review':
      '/api/v2/admin/treasury/deposits/{deposit_id}/review',
  '/api/admin/treasury/disputes': '/api/v2/admin/treasury/disputes',
  '/api/admin/treasury/disputes/{dispute_id}':
      '/api/v2/admin/treasury/disputes/{dispute_id}',
  '/api/admin/treasury/disputes/{dispute_id}/messages':
      '/api/v2/admin/treasury/disputes/{dispute_id}/messages',
  '/api/admin/treasury/kyc': '/api/v2/admin/treasury/kyc',
  '/api/admin/treasury/kyc/{profile_id}/review':
      '/api/v2/admin/treasury/kyc/{profile_id}/review',
  '/api/admin/treasury/settings': '/api/v2/admin/treasury/settings',
  '/api/admin/treasury/withdrawal-batches':
      '/api/v2/admin/treasury/withdrawal-batches',
  '/api/admin/treasury/withdrawals': '/api/v2/admin/treasury/withdrawals',
  '/api/admin/treasury/withdrawals/{withdrawal_id}/reviews':
      '/api/v2/admin/treasury/withdrawals/{withdrawal_id}/reviews',
  '/api/admin/treasury/withdrawals/{withdrawal_id}/status':
      '/api/v2/admin/treasury/withdrawals/{withdrawal_id}/status',
  '/api/admin/wallets/market-topups': '/api/v2/admin/wallets/market-topups',
  '/api/admin/wallets/market-topups/quote':
      '/api/v2/admin/wallets/market-topups/quote',
  '/api/admin/wallets/market-topups/{topup_id}/status':
      '/api/v2/admin/wallets/market-topups/{topup_id}/status',
  '/api/admin/wallets/purchase-orders': '/api/v2/admin/wallets/purchase-orders',
  '/api/admin/wallets/purchase-orders/{order_id}/status':
      '/api/v2/admin/wallets/purchase-orders/{order_id}/status',
  '/api/admin/world/clubs/{club_id}/context':
      '/api/v2/admin/world/clubs/{club_id}/context',
  '/api/admin/world/cultures/{culture_key}':
      '/api/v2/admin/world/cultures/{culture_key}',
  '/api/admin/world/narratives/{narrative_slug}':
      '/api/v2/admin/world/narratives/{narrative_slug}',
  '/api/ads/create': '/api/v2/ads/create',
  '/api/ads/performance': '/api/v2/ads/performance',
  '/api/agents': '/api/v2/agents',
  '/api/agents/config': '/api/v2/agents/config',
  '/api/agents/performance': '/api/v2/agents/performance',
  '/api/agents/run': '/api/v2/agents/run',
  '/api/agents/summary': '/api/v2/agents/summary',
  '/api/ai-manager/autopilot/live-decision':
      '/api/v2/ai-manager/autopilot/live-decision',
  '/api/ai-manager/autopilot/run': '/api/v2/ai-manager/autopilot/run',
  '/api/ai-manager/economy/reward-preview':
      '/api/v2/ai-manager/economy/reward-preview',
  '/api/ai-manager/profiles/{club_id}': '/api/v2/ai-manager/profiles/{club_id}',
  '/api/ai-reporter/feed': '/api/v2/ai-reporter/feed',
  '/api/ai-reporter/run': '/api/v2/ai-reporter/run',
  '/api/ai/leagues': '/api/v2/ai/leagues',
  '/api/ai/match/{match_id}': '/api/v2/ai/match/{match_id}',
  '/api/analytics/clip/{clip_id}': '/api/v2/analytics/clip/{clip_id}',
  '/api/analytics/dashboard/drop-off': '/api/v2/analytics/dashboard/drop-off',
  '/api/analytics/dashboard/top-clips': '/api/v2/analytics/dashboard/top-clips',
  '/api/analytics/device-fingerprint': '/api/v2/analytics/device-fingerprint',
  '/api/analytics/events': '/api/v2/analytics/events',
  '/api/analytics/frontend': '/api/v2/analytics/frontend',
  '/api/analytics/influencer-leaderboard':
      '/api/v2/analytics/influencer-leaderboard',
  '/api/attachments': '/api/v2/attachments',
  '/api/attachments/{attachment_id}': '/api/v2/attachments/{attachment_id}',
  '/api/auth/change-password': '/api/v2/auth/change-password',
  '/api/auth/confirm-email': '/api/v2/auth/confirm-email',
  '/api/auth/login': '/api/v2/auth/login',
  '/api/auth/logout': '/api/v2/auth/logout',
  '/api/auth/me': '/api/v2/auth/me',
  '/api/auth/recovery/request': '/api/v2/auth/recovery/request',
  '/api/auth/recovery/reset': '/api/v2/auth/recovery/reset',
  '/api/auth/refresh': '/api/v2/auth/refresh',
  '/api/auth/signup/creator': '/api/v2/auth/signup/creator',
  '/api/auth/signup/trader': '/api/v2/auth/signup/trader',
  '/api/auth/signup/user': '/api/v2/auth/signup/user',
  '/api/awards/categories': '/api/v2/awards/categories',
  '/api/awards/ceremony': '/api/v2/awards/ceremony',
  '/api/awards/ceremony/tickets': '/api/v2/awards/ceremony/tickets',
  '/api/awards/ceremony/vote': '/api/v2/awards/ceremony/vote',
  '/api/awards/nominees': '/api/v2/awards/nominees',
  '/api/awards/winners': '/api/v2/awards/winners',
  '/api/bank-accounts': '/api/v2/bank-accounts',
  '/api/bank-accounts/{bank_account_id}':
      '/api/v2/bank-accounts/{bank_account_id}',
  '/api/bets/history': '/api/v2/bets/history',
  '/api/bets/odds/{match_id}': '/api/v2/bets/odds/{match_id}',
  '/api/bets/place': '/api/v2/bets/place',
  '/api/bets/preferences': '/api/v2/bets/preferences',
  '/api/broadcast-rights/auctions/{auction_id}/bids':
      '/api/v2/broadcast-rights/auctions/{auction_id}/bids',
  '/api/broadcast-rights/competitions/{competition_id}':
      '/api/v2/broadcast-rights/competitions/{competition_id}',
  '/api/broadcast-rights/competitions/{competition_id}/acquire':
      '/api/v2/broadcast-rights/competitions/{competition_id}/acquire',
  '/api/broadcast-rights/competitions/{competition_id}/auctions':
      '/api/v2/broadcast-rights/competitions/{competition_id}/auctions',
  '/api/broadcast-rights/matches/{match_id}/access':
      '/api/v2/broadcast-rights/matches/{match_id}/access',
  '/api/broadcast-rights/matches/{match_id}/distribute':
      '/api/v2/broadcast-rights/matches/{match_id}/distribute',
  '/api/broadcast-rights/{right_id}/grants':
      '/api/v2/broadcast-rights/{right_id}/grants',
  '/api/broadcast/channels': '/api/v2/broadcast/channels',
  '/api/broadcast/channels/{channel_id}/audio/stems/stream':
      '/api/v2/broadcast/channels/{channel_id}/audio/stems/stream',
  '/api/broadcast/channels/{channel_id}/join':
      '/api/v2/broadcast/channels/{channel_id}/join',
  '/api/broadcast/channels/{channel_id}/stream':
      '/api/v2/broadcast/channels/{channel_id}/stream',
  '/api/broadcast/home': '/api/v2/broadcast/home',
  '/api/broadcast/{match_id}': '/api/v2/broadcast/{match_id}',
  '/api/calendar-engine/dashboard': '/api/v2/calendar-engine/dashboard',
  '/api/calendar-engine/events': '/api/v2/calendar-engine/events',
  '/api/calendar-engine/lifecycle-runs':
      '/api/v2/calendar-engine/lifecycle-runs',
  '/api/calendar-engine/pause-status': '/api/v2/calendar-engine/pause-status',
  '/api/calendar-engine/seasons': '/api/v2/calendar-engine/seasons',
  '/api/campaigns': '/api/v2/campaigns',
  '/api/campaigns/create': '/api/v2/campaigns/create',
  '/api/campaigns/{id}/accept': '/api/v2/campaigns/{id}/accept',
  '/api/campaigns/{id}/apply': '/api/v2/campaigns/{id}/apply',
  '/api/campaigns/{id}/performance': '/api/v2/campaigns/{id}/performance',
  '/api/career/create': '/api/v2/career/create',
  '/api/career/retire': '/api/v2/career/retire',
  '/api/career/train': '/api/v2/career/train',
  '/api/career/transfer': '/api/v2/career/transfer',
  '/api/career/{user_id}': '/api/v2/career/{user_id}',
  '/api/challenges/links/{link_code}': '/api/v2/challenges/links/{link_code}',
  '/api/challenges/{challenge_id}': '/api/v2/challenges/{challenge_id}',
  '/api/challenges/{challenge_id}/accept':
      '/api/v2/challenges/{challenge_id}/accept',
  '/api/challenges/{challenge_id}/links':
      '/api/v2/challenges/{challenge_id}/links',
  '/api/challenges/{challenge_id}/publish':
      '/api/v2/challenges/{challenge_id}/publish',
  '/api/challenges/{challenge_id}/share-events':
      '/api/v2/challenges/{challenge_id}/share-events',
  '/api/champions-league/knockout-bracket':
      '/api/v2/champions-league/knockout-bracket',
  '/api/champions-league/league-phase/table':
      '/api/v2/champions-league/league-phase/table',
  '/api/champions-league/playoff-bracket':
      '/api/v2/champions-league/playoff-bracket',
  '/api/champions-league/prize-pool/preview':
      '/api/v2/champions-league/prize-pool/preview',
  '/api/champions-league/qualification-map':
      '/api/v2/champions-league/qualification-map',
  '/api/club-infra/clubs/{club_id}': '/api/v2/club-infra/clubs/{club_id}',
  '/api/club-infra/clubs/{club_id}/support':
      '/api/v2/club-infra/clubs/{club_id}/support',
  '/api/club-infra/my': '/api/v2/club-infra/my',
  '/api/club-infra/my/facilities/upgrade':
      '/api/v2/club-infra/my/facilities/upgrade',
  '/api/club-infra/my/stadium/upgrade': '/api/v2/club-infra/my/stadium/upgrade',
  '/api/club/identity': '/api/v2/club/identity',
  '/api/clubs': '/api/v2/clubs',
  '/api/clubs/catalog': '/api/v2/clubs/catalog',
  '/api/clubs/catalog/purchase': '/api/v2/clubs/catalog/purchase',
  '/api/clubs/marketplace': '/api/v2/clubs/marketplace',
  '/api/clubs/sale-market/listings': '/api/v2/clubs/sale-market/listings',
  '/api/clubs/{club_id}': '/api/v2/clubs/{club_id}',
  '/api/clubs/{club_id}/academy': '/api/v2/clubs/{club_id}/academy',
  '/api/clubs/{club_id}/academy/players':
      '/api/v2/clubs/{club_id}/academy/players',
  '/api/clubs/{club_id}/academy/players/{player_id}':
      '/api/v2/clubs/{club_id}/academy/players/{player_id}',
  '/api/clubs/{club_id}/academy/programs':
      '/api/v2/clubs/{club_id}/academy/programs',
  '/api/clubs/{club_id}/academy/training-cycles':
      '/api/v2/clubs/{club_id}/academy/training-cycles',
  '/api/clubs/{club_id}/badge': '/api/v2/clubs/{club_id}/badge',
  '/api/clubs/{club_id}/branding': '/api/v2/clubs/{club_id}/branding',
  '/api/clubs/{club_id}/buy-tokens': '/api/v2/clubs/{club_id}/buy-tokens',
  '/api/clubs/{club_id}/challenges': '/api/v2/clubs/{club_id}/challenges',
  '/api/clubs/{club_id}/contracts': '/api/v2/clubs/{club_id}/contracts',
  '/api/clubs/{club_id}/dynasty': '/api/v2/clubs/{club_id}/dynasty',
  '/api/clubs/{club_id}/dynasty/history':
      '/api/v2/clubs/{club_id}/dynasty/history',
  '/api/clubs/{club_id}/eras': '/api/v2/clubs/{club_id}/eras',
  '/api/clubs/{club_id}/finances': '/api/v2/clubs/{club_id}/finances',
  '/api/clubs/{club_id}/finances/budget':
      '/api/v2/clubs/{club_id}/finances/budget',
  '/api/clubs/{club_id}/finances/cashflow':
      '/api/v2/clubs/{club_id}/finances/cashflow',
  '/api/clubs/{club_id}/finances/ledger':
      '/api/v2/clubs/{club_id}/finances/ledger',
  '/api/clubs/{club_id}/honors-timeline':
      '/api/v2/clubs/{club_id}/honors-timeline',
  '/api/clubs/{club_id}/identity': '/api/v2/clubs/{club_id}/identity',
  '/api/clubs/{club_id}/identity/metrics':
      '/api/v2/clubs/{club_id}/identity/metrics',
  '/api/clubs/{club_id}/identity/metrics/refresh':
      '/api/v2/clubs/{club_id}/identity/metrics/refresh',
  '/api/clubs/{club_id}/jerseys': '/api/v2/clubs/{club_id}/jerseys',
  '/api/clubs/{club_id}/jerseys/{jersey_id}':
      '/api/v2/clubs/{club_id}/jerseys/{jersey_id}',
  '/api/clubs/{club_id}/ownership': '/api/v2/clubs/{club_id}/ownership',
  '/api/clubs/{club_id}/prestige': '/api/v2/clubs/{club_id}/prestige',
  '/api/clubs/{club_id}/proposals': '/api/v2/clubs/{club_id}/proposals',
  '/api/clubs/{club_id}/purchases': '/api/v2/clubs/{club_id}/purchases',
  '/api/clubs/{club_id}/reputation': '/api/v2/clubs/{club_id}/reputation',
  '/api/clubs/{club_id}/reputation/history':
      '/api/v2/clubs/{club_id}/reputation/history',
  '/api/clubs/{club_id}/rivalries': '/api/v2/clubs/{club_id}/rivalries',
  '/api/clubs/{club_id}/rivalries/{opponent_club_id}':
      '/api/v2/clubs/{club_id}/rivalries/{opponent_club_id}',
  '/api/clubs/{club_id}/sale-market': '/api/v2/clubs/{club_id}/sale-market',
  '/api/clubs/{club_id}/sale-market/assistant':
      '/api/v2/clubs/{club_id}/sale-market/assistant',
  '/api/clubs/{club_id}/sale-market/history':
      '/api/v2/clubs/{club_id}/sale-market/history',
  '/api/clubs/{club_id}/sale-market/inquiries':
      '/api/v2/clubs/{club_id}/sale-market/inquiries',
  '/api/clubs/{club_id}/sale-market/inquiries/{inquiry_id}/respond':
      '/api/v2/clubs/{club_id}/sale-market/inquiries/{inquiry_id}/respond',
  '/api/clubs/{club_id}/sale-market/listing':
      '/api/v2/clubs/{club_id}/sale-market/listing',
  '/api/clubs/{club_id}/sale-market/listing/cancel':
      '/api/v2/clubs/{club_id}/sale-market/listing/cancel',
  '/api/clubs/{club_id}/sale-market/listing/instant-sell':
      '/api/v2/clubs/{club_id}/sale-market/listing/instant-sell',
  '/api/clubs/{club_id}/sale-market/offers':
      '/api/v2/clubs/{club_id}/sale-market/offers',
  '/api/clubs/{club_id}/sale-market/offers/{offer_id}/accept':
      '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/accept',
  '/api/clubs/{club_id}/sale-market/offers/{offer_id}/counter':
      '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/counter',
  '/api/clubs/{club_id}/sale-market/offers/{offer_id}/reject':
      '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/reject',
  '/api/clubs/{club_id}/sale-market/transfer':
      '/api/v2/clubs/{club_id}/sale-market/transfer',
  '/api/clubs/{club_id}/scouting': '/api/v2/clubs/{club_id}/scouting',
  '/api/clubs/{club_id}/scouting-intelligence/academy-supply-signals':
      '/api/v2/clubs/{club_id}/scouting-intelligence/academy-supply-signals',
  '/api/clubs/{club_id}/scouting-intelligence/assignments':
      '/api/v2/clubs/{club_id}/scouting-intelligence/assignments',
  '/api/clubs/{club_id}/scouting-intelligence/badges':
      '/api/v2/clubs/{club_id}/scouting-intelligence/badges',
  '/api/clubs/{club_id}/scouting-intelligence/lifecycle':
      '/api/v2/clubs/{club_id}/scouting-intelligence/lifecycle',
  '/api/clubs/{club_id}/scouting-intelligence/manager-profiles':
      '/api/v2/clubs/{club_id}/scouting-intelligence/manager-profiles',
  '/api/clubs/{club_id}/scouting-intelligence/missions':
      '/api/v2/clubs/{club_id}/scouting-intelligence/missions',
  '/api/clubs/{club_id}/scouting-intelligence/missions/{mission_id}':
      '/api/v2/clubs/{club_id}/scouting-intelligence/missions/{mission_id}',
  '/api/clubs/{club_id}/scouting-intelligence/missions/{mission_id}/complete':
      '/api/v2/clubs/{club_id}/scouting-intelligence/missions/{mission_id}/complete',
  '/api/clubs/{club_id}/scouting-intelligence/networks':
      '/api/v2/clubs/{club_id}/scouting-intelligence/networks',
  '/api/clubs/{club_id}/scouting-intelligence/planning':
      '/api/v2/clubs/{club_id}/scouting-intelligence/planning',
  '/api/clubs/{club_id}/scouting/assignments':
      '/api/v2/clubs/{club_id}/scouting/assignments',
  '/api/clubs/{club_id}/scouting/prospects':
      '/api/v2/clubs/{club_id}/scouting/prospects',
  '/api/clubs/{club_id}/scouting/prospects/{prospect_id}':
      '/api/v2/clubs/{club_id}/scouting/prospects/{prospect_id}',
  '/api/clubs/{club_id}/season-honors': '/api/v2/clubs/{club_id}/season-honors',
  '/api/clubs/{club_id}/sell-tokens': '/api/v2/clubs/{club_id}/sell-tokens',
  '/api/clubs/{club_id}/showcase': '/api/v2/clubs/{club_id}/showcase',
  '/api/clubs/{club_id}/sponsorships': '/api/v2/clubs/{club_id}/sponsorships',
  '/api/clubs/{club_id}/sponsorships/assets':
      '/api/v2/clubs/{club_id}/sponsorships/assets',
  '/api/clubs/{club_id}/sponsorships/catalog':
      '/api/v2/clubs/{club_id}/sponsorships/catalog',
  '/api/clubs/{club_id}/sponsorships/contracts':
      '/api/v2/clubs/{club_id}/sponsorships/contracts',
  '/api/clubs/{club_id}/sponsorships/contracts/{contract_id}':
      '/api/v2/clubs/{club_id}/sponsorships/contracts/{contract_id}',
  '/api/clubs/{club_id}/treasury': '/api/v2/clubs/{club_id}/treasury',
  '/api/clubs/{club_id}/trophies': '/api/v2/clubs/{club_id}/trophies',
  '/api/clubs/{club_id}/trophy-cabinet':
      '/api/v2/clubs/{club_id}/trophy-cabinet',
  '/api/clubs/{club_id}/valuation': '/api/v2/clubs/{club_id}/valuation',
  '/api/clubs/{club_id}/vote': '/api/v2/clubs/{club_id}/vote',
  '/api/clubs/{club_id}/youth-pipeline':
      '/api/v2/clubs/{club_id}/youth-pipeline',
  '/api/commentary/profiles': '/api/v2/commentary/profiles',
  '/api/commentary/select': '/api/v2/commentary/select',
  '/api/community/creator-clubs/{club_id}/fan-competitions':
      '/api/v2/community/creator-clubs/{club_id}/fan-competitions',
  '/api/community/creator-clubs/{club_id}/fan-groups':
      '/api/v2/community/creator-clubs/{club_id}/fan-groups',
  '/api/community/creator-clubs/{club_id}/fan-state':
      '/api/v2/community/creator-clubs/{club_id}/fan-state',
  '/api/community/creator-clubs/{club_id}/follow':
      '/api/v2/community/creator-clubs/{club_id}/follow',
  '/api/community/creator-matches/{match_id}/chat-room':
      '/api/v2/community/creator-matches/{match_id}/chat-room',
  '/api/community/creator-matches/{match_id}/chat-room/messages':
      '/api/v2/community/creator-matches/{match_id}/chat-room/messages',
  '/api/community/creator-matches/{match_id}/fan-wall':
      '/api/v2/community/creator-matches/{match_id}/fan-wall',
  '/api/community/creator-matches/{match_id}/rivalry-signals':
      '/api/v2/community/creator-matches/{match_id}/rivalry-signals',
  '/api/community/creator-matches/{match_id}/tactical-advice':
      '/api/v2/community/creator-matches/{match_id}/tactical-advice',
  '/api/community/digest': '/api/v2/community/digest',
  '/api/community/fan-competitions/{fan_competition_id}/join':
      '/api/v2/community/fan-competitions/{fan_competition_id}/join',
  '/api/community/fan-groups/{group_id}/join':
      '/api/v2/community/fan-groups/{group_id}/join',
  '/api/community/live-threads': '/api/v2/community/live-threads',
  '/api/community/live-threads/{thread_id}':
      '/api/v2/community/live-threads/{thread_id}',
  '/api/community/live-threads/{thread_id}/messages':
      '/api/v2/community/live-threads/{thread_id}/messages',
  '/api/community/private-messages/threads':
      '/api/v2/community/private-messages/threads',
  '/api/community/private-messages/threads/{thread_id}':
      '/api/v2/community/private-messages/threads/{thread_id}',
  '/api/community/private-messages/threads/{thread_id}/messages':
      '/api/v2/community/private-messages/threads/{thread_id}/messages',
  '/api/community/watchlist': '/api/v2/community/watchlist',
  '/api/community/watchlist/{competition_key}':
      '/api/v2/community/watchlist/{competition_key}',
  '/api/competitions': '/api/v2/competitions',
  '/api/competitions/admin': '/api/v2/competitions/admin',
  '/api/competitions/admin/{code}': '/api/v2/competitions/admin/{code}',
  '/api/competitions/admin/{code}/orchestrate':
      '/api/v2/competitions/admin/{code}/orchestrate',
  '/api/competitions/create': '/api/v2/competitions/create',
  '/api/competitions/join': '/api/v2/competitions/join',
  '/api/competitions/players/{subject_id}/progression':
      '/api/v2/competitions/players/{subject_id}/progression',
  '/api/competitions/records/{competition_id}':
      '/api/v2/competitions/records/{competition_id}',
  '/api/competitions/runtime/{code}': '/api/v2/competitions/runtime/{code}',
  '/api/competitions/{competition_id}': '/api/v2/competitions/{competition_id}',
  '/api/competitions/{competition_id}/advance':
      '/api/v2/competitions/{competition_id}/advance',
  '/api/competitions/{competition_id}/finalize':
      '/api/v2/competitions/{competition_id}/finalize',
  '/api/competitions/{competition_id}/financials':
      '/api/v2/competitions/{competition_id}/financials',
  '/api/competitions/{competition_id}/fixtures':
      '/api/v2/competitions/{competition_id}/fixtures',
  '/api/competitions/{competition_id}/invites':
      '/api/v2/competitions/{competition_id}/invites',
  '/api/competitions/{competition_id}/invites/accept':
      '/api/v2/competitions/{competition_id}/invites/accept',
  '/api/competitions/{competition_id}/join':
      '/api/v2/competitions/{competition_id}/join',
  '/api/competitions/{competition_id}/launch':
      '/api/v2/competitions/{competition_id}/launch',
  '/api/competitions/{competition_id}/leave':
      '/api/v2/competitions/{competition_id}/leave',
  '/api/competitions/{competition_id}/matches/{match_id}/events':
      '/api/v2/competitions/{competition_id}/matches/{match_id}/events',
  '/api/competitions/{competition_id}/matches/{match_id}/result':
      '/api/v2/competitions/{competition_id}/matches/{match_id}/result',
  '/api/competitions/{competition_id}/publish':
      '/api/v2/competitions/{competition_id}/publish',
  '/api/competitions/{competition_id}/rewards':
      '/api/v2/competitions/{competition_id}/rewards',
  '/api/competitions/{competition_id}/rounds':
      '/api/v2/competitions/{competition_id}/rounds',
  '/api/competitions/{competition_id}/schedule/jobs':
      '/api/v2/competitions/{competition_id}/schedule/jobs',
  '/api/competitions/{competition_id}/schedule/jobs/{job_id}':
      '/api/v2/competitions/{competition_id}/schedule/jobs/{job_id}',
  '/api/competitions/{competition_id}/schedule/preview':
      '/api/v2/competitions/{competition_id}/schedule/preview',
  '/api/competitions/{competition_id}/seed':
      '/api/v2/competitions/{competition_id}/seed',
  '/api/competitions/{competition_id}/standings':
      '/api/v2/competitions/{competition_id}/standings',
  '/api/competitions/{competition_id}/summary':
      '/api/v2/competitions/{competition_id}/summary',
  '/api/competitive-integrity/fast-game/runs':
      '/api/v2/competitive-integrity/fast-game/runs',
  '/api/competitive-integrity/fast-game/runs/{run_id}':
      '/api/v2/competitive-integrity/fast-game/runs/{run_id}',
  '/api/competitive-integrity/fast-game/runs/{run_id}/play':
      '/api/v2/competitive-integrity/fast-game/runs/{run_id}/play',
  '/api/competitive-integrity/managers':
      '/api/v2/competitive-integrity/managers',
  '/api/competitive-integrity/managers/candidates':
      '/api/v2/competitive-integrity/managers/candidates',
  '/api/competitive-integrity/managers/{manager_id}/instructions':
      '/api/v2/competitive-integrity/managers/{manager_id}/instructions',
  '/api/competitive-integrity/matches': '/api/v2/competitive-integrity/matches',
  '/api/competitive-integrity/matches/{match_id}':
      '/api/v2/competitive-integrity/matches/{match_id}',
  '/api/competitive-integrity/matches/{match_id}/execute':
      '/api/v2/competitive-integrity/matches/{match_id}/execute',
  '/api/competitive-integrity/notifications/events':
      '/api/v2/competitive-integrity/notifications/events',
  '/api/config/current': '/api/v2/config/current',
  '/api/config/update': '/api/v2/config/update',
  '/api/conversations': '/api/v2/conversations',
  '/api/conversations/start': '/api/v2/conversations/start',
  '/api/conversations/{conversation_id}/message':
      '/api/v2/conversations/{conversation_id}/message',
  '/api/conversations/{conversation_id}/messages':
      '/api/v2/conversations/{conversation_id}/messages',
  '/api/conversations/{conversation_id}/status':
      '/api/v2/conversations/{conversation_id}/status',
  '/api/competitions/creator-league/financial-report':
      '/api/v2/competitions/creator-league/financial-report',
  '/api/competitions/creator-league/financial-settlements':
      '/api/v2/competitions/creator-league/financial-settlements',
  '/api/competitions/creator-league/financial-settlements/{settlement_id}/approve':
      '/api/v2/competitions/creator-league/financial-settlements/{settlement_id}/approve',
  '/api/creator-campaigns': '/api/v2/creator-campaigns',
  '/api/creator-campaigns/me': '/api/v2/creator-campaigns/me',
  '/api/creator-campaigns/{campaign_id}':
      '/api/v2/creator-campaigns/{campaign_id}',
  '/api/creator-campaigns/{campaign_id}/metrics':
      '/api/v2/creator-campaigns/{campaign_id}/metrics',
  '/api/creator-campaigns/{campaign_id}/snapshot':
      '/api/v2/creator-campaigns/{campaign_id}/snapshot',
  '/api/creator-campaigns/{campaign_id}/snapshots':
      '/api/v2/creator-campaigns/{campaign_id}/snapshots',
  '/api/creator-league': '/api/v2/creator-league',
  '/api/creator-league/config': '/api/v2/creator-league/config',
  '/api/creator-league/financial-report':
      '/api/v2/creator-league/financial-report',
  '/api/creator-league/financial-settlements':
      '/api/v2/creator-league/financial-settlements',
  '/api/creator-league/financial-settlements/{settlement_id}/approve':
      '/api/v2/creator-league/financial-settlements/{settlement_id}/approve',
  '/api/creator-league/live-priority': '/api/v2/creator-league/live-priority',
  '/api/creator-league/reset': '/api/v2/creator-league/reset',
  '/api/creator-league/season-tiers/{season_tier_id}/standings':
      '/api/v2/creator-league/season-tiers/{season_tier_id}/standings',
  '/api/creator-league/seasons': '/api/v2/creator-league/seasons',
  '/api/creator-league/seasons/{season_id}':
      '/api/v2/creator-league/seasons/{season_id}',
  '/api/creator-league/seasons/{season_id}/pause':
      '/api/v2/creator-league/seasons/{season_id}/pause',
  '/api/creator-league/tiers': '/api/v2/creator-league/tiers',
  '/api/creator-league/tiers/{tier_id}':
      '/api/v2/creator-league/tiers/{tier_id}',
  '/api/creator/application': '/api/v2/creator/application',
  '/api/creator/apply': '/api/v2/creator/apply',
  '/api/creator/cards': '/api/v2/creator/cards',
  '/api/creator/cards/listings': '/api/v2/creator/cards/listings',
  '/api/creator/cards/listings/{listing_id}/buy':
      '/api/v2/creator/cards/listings/{listing_id}/buy',
  '/api/creator/cards/loans/{loan_id}/return':
      '/api/v2/creator/cards/loans/{loan_id}/return',
  '/api/creator/cards/swap': '/api/v2/creator/cards/swap',
  '/api/creator/cards/{creator_card_id}/list':
      '/api/v2/creator/cards/{creator_card_id}/list',
  '/api/creator/cards/{creator_card_id}/loan':
      '/api/v2/creator/cards/{creator_card_id}/loan',
  '/api/creator/clubs/{club_id}/fan-share-market':
      '/api/v2/creator/clubs/{club_id}/fan-share-market',
  '/api/creator/clubs/{club_id}/fan-share-market/distributions':
      '/api/v2/creator/clubs/{club_id}/fan-share-market/distributions',
  '/api/creator/clubs/{club_id}/fan-share-market/holding':
      '/api/v2/creator/clubs/{club_id}/fan-share-market/holding',
  '/api/creator/clubs/{club_id}/fan-share-market/purchase':
      '/api/v2/creator/clubs/{club_id}/fan-share-market/purchase',
  '/api/creator/verify-email': '/api/v2/creator/verify-email',
  '/api/creator/verify-phone': '/api/v2/creator/verify-phone',
  '/api/creators/marketplace': '/api/v2/creators/marketplace',
  '/api/creators/me/competitions': '/api/v2/creators/me/competitions',
  '/api/creators/me/copilot/analyze': '/api/v2/creators/me/copilot/analyze',
  '/api/creators/me/finance': '/api/v2/creators/me/finance',
  '/api/creators/me/insights': '/api/v2/creators/me/insights',
  '/api/creators/me/reputation': '/api/v2/creators/me/reputation',
  '/api/creators/me/summary': '/api/v2/creators/me/summary',
  '/api/creators/profile': '/api/v2/creators/profile',
  '/api/creators/profile/me': '/api/v2/creators/profile/me',
  '/api/creators/{handle}': '/api/v2/creators/{handle}',
  '/api/daily-challenges': '/api/v2/daily-challenges',
  '/api/daily-challenges/me': '/api/v2/daily-challenges/me',
  '/api/daily-challenges/{challenge_key}/claim':
      '/api/v2/daily-challenges/{challenge_key}/claim',
  '/api/diagnostics': '/api/v2/diagnostics',
  '/api/discovery/home': '/api/v2/discovery/home',
  '/api/discovery/saved-searches': '/api/v2/discovery/saved-searches',
  '/api/discovery/saved-searches/{search_id}':
      '/api/v2/discovery/saved-searches/{search_id}',
  '/api/discovery/search': '/api/v2/discovery/search',
  '/api/disputes': '/api/v2/disputes',
  '/api/disputes/me': '/api/v2/disputes/me',
  '/api/disputes/{dispute_id}': '/api/v2/disputes/{dispute_id}',
  '/api/disputes/{dispute_id}/messages':
      '/api/v2/disputes/{dispute_id}/messages',
  '/api/dynasty': '/api/v2/dynasty',
  '/api/dynasty/leaderboard': '/api/v2/dynasty/leaderboard',
  '/api/economy/fx/quote': '/api/v2/economy/fx/quote',
  '/api/economy/gift-catalog': '/api/v2/economy/gift-catalog',
  '/api/economy/service-pricing': '/api/v2/economy/service-pricing',
  '/api/engagement/achievements': '/api/v2/engagement/achievements',
  '/api/engagement/achievements/me': '/api/v2/engagement/achievements/me',
  '/api/engagement/milestones/me': '/api/v2/engagement/milestones/me',
  '/api/engagement/sync': '/api/v2/engagement/sync',
  '/api/enter': '/api/v2/enter',
  '/api/events/clip': '/api/v2/events/clip',
  '/api/events/today': '/api/v2/events/today',
  '/api/events/upcoming': '/api/v2/events/upcoming',
  '/api/experience/full-simulation': '/api/v2/experience/full-simulation',
  '/api/fan-predictions/creator-clubs/{club_id}/leaderboards/weekly':
      '/api/v2/fan-predictions/creator-clubs/{club_id}/leaderboards/weekly',
  '/api/fan-predictions/leaderboards/weekly':
      '/api/v2/fan-predictions/leaderboards/weekly',
  '/api/fan-predictions/matches/{match_id}':
      '/api/v2/fan-predictions/matches/{match_id}',
  '/api/fan-predictions/matches/{match_id}/leaderboard':
      '/api/v2/fan-predictions/matches/{match_id}/leaderboard',
  '/api/fan-predictions/matches/{match_id}/submissions':
      '/api/v2/fan-predictions/matches/{match_id}/submissions',
  '/api/fan-predictions/me/submissions':
      '/api/v2/fan-predictions/me/submissions',
  '/api/fan-predictions/me/tokens': '/api/v2/fan-predictions/me/tokens',
  '/api/fan-wars/leaderboards/{board_type}':
      '/api/v2/fan-wars/leaderboards/{board_type}',
  '/api/fan-wars/nations-cup/{competition_id}':
      '/api/v2/fan-wars/nations-cup/{competition_id}',
  '/api/fan-wars/profiles/{profile_id}/dashboard':
      '/api/v2/fan-wars/profiles/{profile_id}/dashboard',
  '/api/fan-wars/rivalries/{board_type}':
      '/api/v2/fan-wars/rivalries/{board_type}',
  '/api/fans/profile': '/api/v2/fans/profile',
  '/api/fans/tribe/join': '/api/v2/fans/tribe/join',
  '/api/fans/{club_id}': '/api/v2/fans/{club_id}',
  '/api/fast-cups/upcoming': '/api/v2/fast-cups/upcoming',
  '/api/fast-cups/{cup_id}/bracket': '/api/v2/fast-cups/{cup_id}/bracket',
  '/api/fast-cups/{cup_id}/countdown': '/api/v2/fast-cups/{cup_id}/countdown',
  '/api/fast-cups/{cup_id}/join': '/api/v2/fast-cups/{cup_id}/join',
  '/api/fast-cups/{cup_id}/result-summary':
      '/api/v2/fast-cups/{cup_id}/result-summary',
  '/api/federations': '/api/v2/federations',
  '/api/federations/proposals/{proposal_id}/votes':
      '/api/v2/federations/proposals/{proposal_id}/votes',
  '/api/federations/rankings': '/api/v2/federations/rankings',
  '/api/federations/regional-tournaments':
      '/api/v2/federations/regional-tournaments',
  '/api/federations/{federation_id}': '/api/v2/federations/{federation_id}',
  '/api/federations/{federation_id}/governance':
      '/api/v2/federations/{federation_id}/governance',
  '/api/federations/{federation_id}/leagues':
      '/api/v2/federations/{federation_id}/leagues',
  '/api/federations/{federation_id}/memberships':
      '/api/v2/federations/{federation_id}/memberships',
  '/api/federations/{federation_id}/narratives':
      '/api/v2/federations/{federation_id}/narratives',
  '/api/federations/{federation_id}/proposals':
      '/api/v2/federations/{federation_id}/proposals',
  '/api/federations/{federation_id}/sanctions':
      '/api/v2/federations/{federation_id}/sanctions',
  '/api/federations/{federation_id}/treasury/distribute':
      '/api/v2/federations/{federation_id}/treasury/distribute',
  '/api/federations/{federation_id}/validate-action':
      '/api/v2/federations/{federation_id}/validate-action',
  '/api/feed/following': '/api/v2/feed/following',
  '/api/feed/for-you': '/api/v2/feed/for-you',
  '/api/feed/for-you/refresh': '/api/v2/feed/for-you/refresh',
  '/api/feed/sponsored': '/api/v2/feed/sponsored',
  '/api/finance': '/api/v2/finance',
  '/api/follow/{user_id}': '/api/v2/follow/{user_id}',
  '/api/football-events/players/{player_id}/events':
      '/api/v2/football-events/players/{player_id}/events',
  '/api/football-events/players/{player_id}/impact':
      '/api/v2/football-events/players/{player_id}/impact',
  '/api/gift-engine/me/combos': '/api/v2/gift-engine/me/combos',
  '/api/gift-engine/me/summary': '/api/v2/gift-engine/me/summary',
  '/api/gift-engine/me/transactions': '/api/v2/gift-engine/me/transactions',
  '/api/gift-engine/send': '/api/v2/gift-engine/send',
  '/api/governance/clubs/{club_id}/panel':
      '/api/v2/governance/clubs/{club_id}/panel',
  '/api/governance/me/overview': '/api/v2/governance/me/overview',
  '/api/governance/proposals': '/api/v2/governance/proposals',
  '/api/governance/proposals/{proposal_id}':
      '/api/v2/governance/proposals/{proposal_id}',
  '/api/governance/proposals/{proposal_id}/vote':
      '/api/v2/governance/proposals/{proposal_id}/vote',
  '/api/gtex/market/buy': '/api/v2/gtex/market/buy',
  '/api/gtex/market/sell': '/api/v2/gtex/market/sell',
  '/api/hall-of-fame': '/api/v2/hall-of-fame',
  '/api/health': '/health',
  '/api/history/goat-rankings': '/api/v2/history/goat-rankings',
  '/api/history/leaderboards': '/api/v2/history/leaderboards',
  '/api/history/records': '/api/v2/history/records',
  '/api/history/timeline/{subject_type}/{subject_id}':
      '/api/v2/history/timeline/{subject_type}/{subject_id}',
  '/api/hosted-competitions': '/api/v2/hosted-competitions',
  '/api/hosted-competitions/mine': '/api/v2/hosted-competitions/mine',
  '/api/hosted-competitions/mine/invites':
      '/api/v2/hosted-competitions/mine/invites',
  '/api/hosted-competitions/templates': '/api/v2/hosted-competitions/templates',
  '/api/hosted-competitions/{competition_id}':
      '/api/v2/hosted-competitions/{competition_id}',
  '/api/hosted-competitions/{competition_id}/finance':
      '/api/v2/hosted-competitions/{competition_id}/finance',
  '/api/hosted-competitions/{competition_id}/invites':
      '/api/v2/hosted-competitions/{competition_id}/invites',
  '/api/hosted-competitions/{competition_id}/invites/accept':
      '/api/v2/hosted-competitions/{competition_id}/invites/accept',
  '/api/hosted-competitions/{competition_id}/join':
      '/api/v2/hosted-competitions/{competition_id}/join',
  '/api/hosted-competitions/{competition_id}/launch':
      '/api/v2/hosted-competitions/{competition_id}/launch',
  '/api/hosted-competitions/{competition_id}/standings':
      '/api/v2/hosted-competitions/{competition_id}/standings',
  '/api/infinite-league/economy': '/api/v2/infinite-league/economy',
  '/api/infinite-league/livestream': '/api/v2/infinite-league/livestream',
  '/api/infinite-league/matches': '/api/v2/infinite-league/matches',
  '/api/infinite-league/matches/{match_id}':
      '/api/v2/infinite-league/matches/{match_id}',
  '/api/infinite-league/pundits/{match_id}':
      '/api/v2/infinite-league/pundits/{match_id}',
  '/api/infinite-league/status': '/api/v2/infinite-league/status',
  '/api/infinite-league/tick': '/api/v2/infinite-league/tick',
  '/api/infinite-league/viral-feed': '/api/v2/infinite-league/viral-feed',
  '/api/integrations/payments/korapay/webhook':
      '/api/v2/integrations/payments/korapay/webhook',
  '/api/integrations/payments/methods': '/api/v2/integrations/payments/methods',
  '/api/integrations/payments/orders': '/api/v2/integrations/payments/orders',
  '/api/integrations/payments/paystack/webhook':
      '/api/v2/integrations/payments/paystack/webhook',
  '/api/integrations/payments/quote': '/api/v2/integrations/payments/quote',
  '/api/integrity-engine/me/incidents': '/api/v2/integrity-engine/me/incidents',
  '/api/integrity-engine/me/score': '/api/v2/integrity-engine/me/score',
  '/api/internal/ingestion/bootstrap-sync':
      '/api/v2/internal/ingestion/bootstrap-sync',
  '/api/internal/ingestion/clubs/{club_external_id}/refresh':
      '/api/v2/internal/ingestion/clubs/{club_external_id}/refresh',
  '/api/internal/ingestion/competitions/{competition_external_id}/refresh':
      '/api/v2/internal/ingestion/competitions/{competition_external_id}/refresh',
  '/api/internal/ingestion/cursors/{provider_name}':
      '/api/v2/internal/ingestion/cursors/{provider_name}',
  '/api/internal/ingestion/incremental-sync':
      '/api/v2/internal/ingestion/incremental-sync',
  '/api/internal/ingestion/players/{player_external_id}/refresh':
      '/api/v2/internal/ingestion/players/{player_external_id}/refresh',
  '/api/internal/ingestion/providers/{provider_name}/health':
      '/api/v2/internal/ingestion/providers/{provider_name}/health',
  '/api/internal/ingestion/real-players/batches':
      '/api/v2/internal/ingestion/real-players/batches',
  '/api/internal/ingestion/real-players/batches/{batch_id}':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}',
  '/api/internal/ingestion/real-players/batches/{batch_id}/issues':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}/issues',
  '/api/internal/ingestion/real-players/batches/{batch_id}/resume':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}/resume',
  '/api/internal/ingestion/real-players/batches/{batch_id}/valuation-status':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}/valuation-status',
  '/api/internal/ingestion/real-players/import':
      '/api/v2/internal/ingestion/real-players/import',
  '/api/internal/ingestion/real-players/publish-jobs':
      '/api/v2/internal/ingestion/real-players/publish-jobs',
  '/api/internal/ingestion/real-players/publish-jobs/{job_id}':
      '/api/v2/internal/ingestion/real-players/publish-jobs/{job_id}',
  '/api/internal/ingestion/real-players/status':
      '/api/v2/internal/ingestion/real-players/status',
  '/api/internal/ingestion/runs': '/api/v2/internal/ingestion/runs',
  '/api/internal/ingestion/status': '/api/v2/internal/ingestion/status',
  '/api/jackpot/contribute': '/api/v2/jackpot/contribute',
  '/api/jackpot/history': '/api/v2/jackpot/history',
  '/api/jackpot/state': '/api/v2/jackpot/state',
  '/api/jobs/{job_id}': '/api/v2/jobs/{job_id}',
  '/api/kyc': '/api/v2/kyc',
  '/api/leaderboard/division/{division}':
      '/api/v2/leaderboard/division/{division}',
  '/api/leaderboard/global': '/api/v2/leaderboard/global',
  '/api/leaderboard/player/{player_id}':
      '/api/v2/leaderboard/player/{player_id}',
  '/api/leaderboard/region/{region}': '/api/v2/leaderboard/region/{region}',
  '/api/leaderboards/dynasties': '/api/v2/leaderboards/dynasties',
  '/api/leaderboards/prestige': '/api/v2/leaderboards/prestige',
  '/api/leaderboards/trophies': '/api/v2/leaderboards/trophies',
  '/api/leagues/register': '/api/v2/leagues/register',
  '/api/leagues/{season_id}/fixtures': '/api/v2/leagues/{season_id}/fixtures',
  '/api/leagues/{season_id}/qualification-markers':
      '/api/v2/leagues/{season_id}/qualification-markers',
  '/api/leagues/{season_id}/standings': '/api/v2/leagues/{season_id}/standings',
  '/api/leagues/{season_id}/summary': '/api/v2/leagues/{season_id}/summary',
  '/api/legacy/board': '/api/v2/legacy/board',
  '/api/live-events': '/api/v2/live-events',
  '/api/manager-duels': '/api/v2/manager-duels',
  '/api/manager-duels/leaderboard': '/api/v2/manager-duels/leaderboard',
  '/api/manager-duels/{duel_id}': '/api/v2/manager-duels/{duel_id}',
  '/api/managers': '/api/v2/managers',
  '/api/managers/assign': '/api/v2/managers/assign',
  '/api/managers/catalog': '/api/v2/managers/catalog',
  '/api/managers/compare': '/api/v2/managers/compare',
  '/api/managers/competition-runtime/{code}':
      '/api/v2/managers/competition-runtime/{code}',
  '/api/managers/create': '/api/v2/managers/create',
  '/api/managers/filters': '/api/v2/managers/filters',
  '/api/managers/history': '/api/v2/managers/history',
  '/api/managers/leaderboard': '/api/v2/managers/leaderboard',
  '/api/managers/my-trade-listings': '/api/v2/managers/my-trade-listings',
  '/api/managers/recommendation': '/api/v2/managers/recommendation',
  '/api/managers/recruit': '/api/v2/managers/recruit',
  '/api/managers/swap': '/api/v2/managers/swap',
  '/api/managers/team': '/api/v2/managers/team',
  '/api/managers/trade-listings': '/api/v2/managers/trade-listings',
  '/api/managers/trade-listings/{listing_id}/buy':
      '/api/v2/managers/trade-listings/{listing_id}/buy',
  '/api/managers/trade-listings/{listing_id}/cancel':
      '/api/v2/managers/trade-listings/{listing_id}/cancel',
  '/api/managers/{asset_id}/release': '/api/v2/managers/{asset_id}/release',
  '/api/managers/{manager_id}': '/api/v2/managers/{manager_id}',
  '/api/managers/{manager_id}/hire': '/api/v2/managers/{manager_id}/hire',
  '/api/managers/{manager_id}/history': '/api/v2/managers/{manager_id}/history',
  '/api/managers/{manager_id}/release': '/api/v2/managers/{manager_id}/release',
  '/api/market/buy': '/api/v2/market/buy',
  '/api/market/listings': '/api/v2/market/listings',
  '/api/market/listings/{listing_id}/cancel':
      '/api/v2/market/listings/{listing_id}/cancel',
  '/api/market/listings/{listing_id}/matches':
      '/api/v2/market/listings/{listing_id}/matches',
  '/api/market/listings/{listing_id}/offers':
      '/api/v2/market/listings/{listing_id}/offers',
  '/api/market/movers': '/api/v2/market/movers',
  '/api/market/offers': '/api/v2/market/offers',
  '/api/market/offers/{offer_id}/accept':
      '/api/v2/market/offers/{offer_id}/accept',
  '/api/market/offers/{offer_id}/counter':
      '/api/v2/market/offers/{offer_id}/counter',
  '/api/market/offers/{offer_id}/reject':
      '/api/v2/market/offers/{offer_id}/reject',
  '/api/market/players': '/api/v2/market/players',
  '/api/market/players/{player_id}': '/api/v2/market/players/{player_id}',
  '/api/market/players/{player_id}/candles':
      '/api/v2/market/players/{player_id}/candles',
  '/api/market/players/{player_id}/history':
      '/api/v2/market/players/{player_id}/history',
  '/api/market/sell': '/api/v2/market/sell',
  '/api/market/summary/{asset_id}': '/api/v2/market/summary/{asset_id}',
  '/api/market/ticker/{player_id}': '/api/v2/market/ticker/{player_id}',
  '/api/market/trade-intents': '/api/v2/market/trade-intents',
  '/api/market/trade-intents/{intent_id}/withdraw':
      '/api/v2/market/trade-intents/{intent_id}/withdraw',
  '/api/market/trending': '/api/v2/market/trending',
  '/api/marketplace/my-players': '/api/v2/marketplace/my-players',
  '/api/marketplace/players': '/api/v2/marketplace/players',
  '/api/marketplace/players/{player_id}':
      '/api/v2/marketplace/players/{player_id}',
  '/api/match-engine/analytics': '/api/v2/match-engine/analytics',
  '/api/match-engine/analytics/{match_key}':
      '/api/v2/match-engine/analytics/{match_key}',
  '/api/match-engine/highlights/{match_key}':
      '/api/v2/match-engine/highlights/{match_key}',
  '/api/match-engine/live-feed/{match_key}':
      '/api/v2/match-engine/live-feed/{match_key}',
  '/api/match-engine/render-sync': '/api/v2/match-engine/render-sync',
  '/api/match-engine/render-sync/{match_key}':
      '/api/v2/match-engine/render-sync/{match_key}',
  '/api/match-engine/replay': '/api/v2/match-engine/replay',
  '/api/match-engine/simulate': '/api/v2/match-engine/simulate',
  '/api/match-engine/summary': '/api/v2/match-engine/summary',
  '/api/match-engine/timeline': '/api/v2/match-engine/timeline',
  '/api/match-share-links/{share_code}':
      '/api/v2/match-share-links/{share_code}',
  '/api/match-share-links/{share_code}/events':
      '/api/v2/match-share-links/{share_code}/events',
  '/api/match-viewer/{match_key}': '/api/v2/match-viewer/{match_key}',
  '/api/match-viewer/{match_key}/illusion':
      '/api/v2/match-viewer/{match_key}/illusion',
  '/api/match-viewer/{match_key}/session':
      '/api/v2/match-viewer/{match_key}/session',
  '/api/match/find': '/api/v2/match/find',
  '/api/match/live/active': '/api/v2/match/live/active',
  '/api/match/{match_id}/commentary/stream':
      '/api/v2/match/{match_id}/commentary/stream',
  '/api/match/{match_id}/live': '/api/v2/match/{match_id}/live',
  '/api/match/{match_id}/unity-access': '/api/v2/match/{match_id}/unity-access',
  '/api/match/{match_id}/unity-access/refresh':
      '/api/v2/match/{match_id}/unity-access/refresh',
  '/api/matches/complete': '/api/v2/matches/complete',
  '/api/matches/live/active': '/api/v2/matches/live/active',
  '/api/matches/start': '/api/v2/matches/start',
  '/api/matches/{match_id}/analysis': '/api/v2/matches/{match_id}/analysis',
  '/api/matches/{match_id}/audio/stems/stream':
      '/api/v2/matches/{match_id}/audio/stems/stream',
  '/api/matches/{match_id}/chat': '/api/v2/matches/{match_id}/chat',
  '/api/matches/{match_id}/chat/messages':
      '/api/v2/matches/{match_id}/chat/messages',
  '/api/matches/{match_id}/commentary': '/api/v2/matches/{match_id}/commentary',
  '/api/matches/{match_id}/commentary/stream':
      '/api/v2/matches/{match_id}/commentary/stream',
  '/api/matches/{match_id}/fan-experience':
      '/api/v2/matches/{match_id}/fan-experience',
  '/api/matches/{match_id}/highlights': '/api/v2/matches/{match_id}/highlights',
  '/api/matches/{match_id}/highlights/share-package':
      '/api/v2/matches/{match_id}/highlights/share-package',
  '/api/matches/{match_id}/live': '/api/v2/matches/{match_id}/live',
  '/api/matches/{match_id}/live-reactions':
      '/api/v2/matches/{match_id}/live-reactions',
  '/api/matches/{match_id}/reactions': '/api/v2/matches/{match_id}/reactions',
  '/api/matches/{match_id}/replay': '/api/v2/matches/{match_id}/replay',
  '/api/matches/{match_id}/share-links':
      '/api/v2/matches/{match_id}/share-links',
  '/api/matches/{match_id}/social-warfare':
      '/api/v2/matches/{match_id}/social-warfare',
  '/api/matches/{match_id}/spectate': '/api/v2/matches/{match_id}/spectate',
  '/api/matches/{match_id}/spectators': '/api/v2/matches/{match_id}/spectators',
  '/api/matches/{match_id}/stream': '/api/v2/matches/{match_id}/stream',
  '/api/matches/{match_id}/tickets': '/api/v2/matches/{match_id}/tickets',
  '/api/matches/{match_id}/unity-access':
      '/api/v2/matches/{match_id}/unity-access',
  '/api/matches/{match_id}/unity-access/refresh':
      '/api/v2/matches/{match_id}/unity-access/refresh',
  '/api/me/clubs/sale-market/listings': '/api/v2/me/clubs/sale-market/listings',
  '/api/me/clubs/sale-market/offers': '/api/v2/me/clubs/sale-market/offers',
  '/api/media': '/api/v2/media',
  '/api/media-engine/creator-league/broadcast-modes':
      '/api/v2/media-engine/creator-league/broadcast-modes',
  '/api/media-engine/creator-league/clubs/{club_id}/stadium':
      '/api/v2/media-engine/creator-league/clubs/{club_id}/stadium',
  '/api/media-engine/creator-league/matches/{match_id}/access':
      '/api/v2/media-engine/creator-league/matches/{match_id}/access',
  '/api/media-engine/creator-league/matches/{match_id}/analytics':
      '/api/v2/media-engine/creator-league/matches/{match_id}/analytics',
  '/api/media-engine/creator-league/matches/{match_id}/gifts':
      '/api/v2/media-engine/creator-league/matches/{match_id}/gifts',
  '/api/media-engine/creator-league/matches/{match_id}/purchase':
      '/api/v2/media-engine/creator-league/matches/{match_id}/purchase',
  '/api/media-engine/creator-league/matches/{match_id}/stadium':
      '/api/v2/media-engine/creator-league/matches/{match_id}/stadium',
  '/api/media-engine/creator-league/matches/{match_id}/stadium/placements':
      '/api/v2/media-engine/creator-league/matches/{match_id}/stadium/placements',
  '/api/media-engine/creator-league/matches/{match_id}/tickets':
      '/api/v2/media-engine/creator-league/matches/{match_id}/tickets',
  '/api/media-engine/creator-league/season-passes':
      '/api/v2/media-engine/creator-league/season-passes',
  '/api/media-engine/creator-league/season-passes/me':
      '/api/v2/media-engine/creator-league/season-passes/me',
  '/api/media-engine/downloads': '/api/v2/media-engine/downloads',
  '/api/media-engine/downloads/{token}':
      '/api/v2/media-engine/downloads/{token}',
  '/api/media-engine/matches/{match_key}/snapshot':
      '/api/v2/media-engine/matches/{match_key}/snapshot',
  '/api/media-engine/me/clip-earnings': '/api/v2/media-engine/me/clip-earnings',
  '/api/media-engine/me/purchases': '/api/v2/media-engine/me/purchases',
  '/api/media-engine/me/share-exports': '/api/v2/media-engine/me/share-exports',
  '/api/media-engine/purchases': '/api/v2/media-engine/purchases',
  '/api/media-engine/share-exports': '/api/v2/media-engine/share-exports',
  '/api/media-engine/share-exports/{export_id}/amplifications':
      '/api/v2/media-engine/share-exports/{export_id}/amplifications',
  '/api/media-engine/share-templates': '/api/v2/media-engine/share-templates',
  '/api/media-engine/views': '/api/v2/media-engine/views',
  '/api/metrics': '/api/v2/metrics',
  '/api/moderation/me/reports': '/api/v2/moderation/me/reports',
  '/api/moderation/reports': '/api/v2/moderation/reports',
  '/api/moments/live': '/api/v2/moments/live',
  '/api/national-pool': '/api/v2/national-pool',
  '/api/national-team-engine/competitions':
      '/api/v2/national-team-engine/competitions',
  '/api/national-team-engine/competitions/{competition_id}':
      '/api/v2/national-team-engine/competitions/{competition_id}',
  '/api/national-team-engine/competitions/{competition_id}/ads/active':
      '/api/v2/national-team-engine/competitions/{competition_id}/ads/active',
  '/api/national-team-engine/competitions/{competition_id}/auto-build-squad':
      '/api/v2/national-team-engine/competitions/{competition_id}/auto-build-squad',
  '/api/national-team-engine/competitions/{competition_id}/entries':
      '/api/v2/national-team-engine/competitions/{competition_id}/entries',
  '/api/national-team-engine/competitions/{competition_id}/gifts':
      '/api/v2/national-team-engine/competitions/{competition_id}/gifts',
  '/api/national-team-engine/competitions/{competition_id}/lifecycle':
      '/api/v2/national-team-engine/competitions/{competition_id}/lifecycle',
  '/api/national-team-engine/competitions/{competition_id}/presentation':
      '/api/v2/national-team-engine/competitions/{competition_id}/presentation',
  '/api/national-team-engine/competitions/{competition_id}/rental-entry':
      '/api/v2/national-team-engine/competitions/{competition_id}/rental-entry',
  '/api/national-team-engine/competitions/{competition_id}/rental-pool':
      '/api/v2/national-team-engine/competitions/{competition_id}/rental-pool',
  '/api/national-team-engine/competitions/{competition_id}/story-events':
      '/api/v2/national-team-engine/competitions/{competition_id}/story-events',
  '/api/national-team-engine/competitions/{competition_id}/theme':
      '/api/v2/national-team-engine/competitions/{competition_id}/theme',
  '/api/national-team-engine/entries/{entry_id}':
      '/api/v2/national-team-engine/entries/{entry_id}',
  '/api/national-team-engine/entries/{entry_id}/free-players/claim':
      '/api/v2/national-team-engine/entries/{entry_id}/free-players/claim',
  '/api/national-team-engine/entries/{entry_id}/rental-status':
      '/api/v2/national-team-engine/entries/{entry_id}/rental-status',
  '/api/national-team-engine/entries/{entry_id}/rentals':
      '/api/v2/national-team-engine/entries/{entry_id}/rentals',
  '/api/national-team-engine/me/history':
      '/api/v2/national-team-engine/me/history',
  '/api/national-team-engine/me/previous-roster':
      '/api/v2/national-team-engine/me/previous-roster',
  '/api/national-team-engine/rankings': '/api/v2/national-team-engine/rankings',
  '/api/news/breaking': '/api/v2/news/breaking',
  '/api/news/daily': '/api/v2/news/daily',
  '/api/news/feed': '/api/v2/news/feed',
  '/api/news/personalized': '/api/v2/news/personalized',
  '/api/news/{article_id}': '/api/v2/news/{article_id}',
  '/api/notifications': '/api/v2/notifications',
  '/api/notifications/announcements': '/api/v2/notifications/announcements',
  '/api/notifications/me': '/api/v2/notifications/me',
  '/api/notifications/preferences': '/api/v2/notifications/preferences',
  '/api/notifications/read-all': '/api/v2/notifications/read-all',
  '/api/notifications/subscriptions': '/api/v2/notifications/subscriptions',
  '/api/notifications/subscriptions/{subscription_id}':
      '/api/v2/notifications/subscriptions/{subscription_id}',
  '/api/notifications/{notification_id}/read':
      '/api/v2/notifications/{notification_id}/read',
  '/api/objectives/me': '/api/v2/objectives/me',
  '/api/observability/config': '/api/v2/observability/config',
  '/api/orchestrator/config': '/api/v2/orchestrator/config',
  '/api/orchestrator/metrics': '/api/v2/orchestrator/metrics',
  '/api/orders': '/api/v2/orders',
  '/api/orders/book/{player_id}': '/api/v2/orders/book/{player_id}',
  '/api/orders/{order_id}': '/api/v2/orders/{order_id}',
  '/api/orders/{order_id}/admin-buyback':
      '/api/v2/orders/{order_id}/admin-buyback',
  '/api/orders/{order_id}/admin-buyback-preview':
      '/api/v2/orders/{order_id}/admin-buyback-preview',
  '/api/orders/{order_id}/cancel': '/api/v2/orders/{order_id}/cancel',
  '/api/organizations': '/api/v2/organizations',
  '/api/organizations/invites/accept': '/api/v2/organizations/invites/accept',
  '/api/organizations/me': '/api/v2/organizations/me',
  '/api/organizations/{organization_id}/audit-log':
      '/api/v2/organizations/{organization_id}/audit-log',
  '/api/organizations/{organization_id}/invite':
      '/api/v2/organizations/{organization_id}/invite',
  '/api/ownership-groups': '/api/v2/ownership-groups',
  '/api/ownership-groups/transfers/validate':
      '/api/v2/ownership-groups/transfers/validate',
  '/api/ownership-groups/{group_id}': '/api/v2/ownership-groups/{group_id}',
  '/api/ownership-groups/{group_id}/budget/allocate':
      '/api/v2/ownership-groups/{group_id}/budget/allocate',
  '/api/ownership-groups/{group_id}/budget/transfer':
      '/api/v2/ownership-groups/{group_id}/budget/transfer',
  '/api/ownership-groups/{group_id}/clubs':
      '/api/v2/ownership-groups/{group_id}/clubs',
  '/api/platform/mode': '/api/v2/platform/mode',
  '/api/platform/switch': '/api/v2/platform/switch',
  '/api/player-cards/admin/preseeded-regens':
      '/api/v2/player-cards/admin/preseeded-regens',
  '/api/player-cards/admin/preseeded-regens/mint':
      '/api/v2/player-cards/admin/preseeded-regens/mint',
  '/api/player-cards/inventory': '/api/v2/player-cards/inventory',
  '/api/player-cards/listings': '/api/v2/player-cards/listings',
  '/api/player-cards/listings/mine': '/api/v2/player-cards/listings/mine',
  '/api/player-cards/listings/{listing_id}/buy':
      '/api/v2/player-cards/listings/{listing_id}/buy',
  '/api/player-cards/listings/{listing_id}/cancel':
      '/api/v2/player-cards/listings/{listing_id}/cancel',
  '/api/player-cards/loans': '/api/v2/player-cards/loans',
  '/api/player-cards/loans/contracts/{loan_contract_id}/return':
      '/api/v2/player-cards/loans/contracts/{loan_contract_id}/return',
  '/api/player-cards/loans/{loan_listing_id}/borrow':
      '/api/v2/player-cards/loans/{loan_listing_id}/borrow',
  '/api/player-cards/marketplace/listings':
      '/api/v2/player-cards/marketplace/listings',
  '/api/player-cards/marketplace/loans':
      '/api/v2/player-cards/marketplace/loans',
  '/api/player-cards/marketplace/loans/contracts':
      '/api/v2/player-cards/marketplace/loans/contracts',
  '/api/player-cards/marketplace/loans/contracts/{contract_id}/return':
      '/api/v2/player-cards/marketplace/loans/contracts/{contract_id}/return',
  '/api/player-cards/marketplace/loans/contracts/{contract_id}/settle':
      '/api/v2/player-cards/marketplace/loans/contracts/{contract_id}/settle',
  '/api/player-cards/marketplace/loans/negotiations/{negotiation_id}/accept':
      '/api/v2/player-cards/marketplace/loans/negotiations/{negotiation_id}/accept',
  '/api/player-cards/marketplace/loans/negotiations/{negotiation_id}/counter':
      '/api/v2/player-cards/marketplace/loans/negotiations/{negotiation_id}/counter',
  '/api/player-cards/marketplace/loans/{listing_id}/cancel':
      '/api/v2/player-cards/marketplace/loans/{listing_id}/cancel',
  '/api/player-cards/marketplace/loans/{listing_id}/negotiations':
      '/api/v2/player-cards/marketplace/loans/{listing_id}/negotiations',
  '/api/player-cards/marketplace/sales':
      '/api/v2/player-cards/marketplace/sales',
  '/api/player-cards/marketplace/sales/{listing_id}/buy':
      '/api/v2/player-cards/marketplace/sales/{listing_id}/buy',
  '/api/player-cards/marketplace/sales/{listing_id}/cancel':
      '/api/v2/player-cards/marketplace/sales/{listing_id}/cancel',
  '/api/player-cards/marketplace/swaps':
      '/api/v2/player-cards/marketplace/swaps',
  '/api/player-cards/marketplace/swaps/{listing_id}/cancel':
      '/api/v2/player-cards/marketplace/swaps/{listing_id}/cancel',
  '/api/player-cards/marketplace/swaps/{listing_id}/execute':
      '/api/v2/player-cards/marketplace/swaps/{listing_id}/execute',
  '/api/player-cards/players': '/api/v2/player-cards/players',
  '/api/player-cards/players/{player_id}':
      '/api/v2/player-cards/players/{player_id}',
  '/api/player-cards/starter-rental': '/api/v2/player-cards/starter-rental',
  '/api/player-cards/watchlist': '/api/v2/player-cards/watchlist',
  '/api/player-cards/watchlist/{watchlist_id}':
      '/api/v2/player-cards/watchlist/{watchlist_id}',
  '/api/player-history': '/api/v2/player-history',
  '/api/player-history/{player_id}': '/api/v2/player-history/{player_id}',
  '/api/player-import/youth-prospects/me':
      '/api/v2/player-import/youth-prospects/me',
  '/api/player-import/youth-prospects/{club_id}':
      '/api/v2/player-import/youth-prospects/{club_id}',
  '/api/players': '/api/v2/players',
  '/api/players/events': '/api/v2/players/events',
  '/api/players/markets': '/api/v2/players/markets',
  '/api/players/match': '/api/v2/players/match',
  '/api/players/me/match-profile': '/api/v2/players/me/match-profile',
  '/api/players/me/shares/holdings': '/api/v2/players/me/shares/holdings',
  '/api/players/real-universe': '/api/v2/players/real-universe',
  '/api/players/real-universe/search': '/api/v2/players/real-universe/search',
  '/api/players/real-universe/{player_id}':
      '/api/v2/players/real-universe/{player_id}',
  '/api/players/summaries/recent': '/api/v2/players/summaries/recent',
  '/api/players/{player_id}': '/api/v2/players/{player_id}',
  '/api/players/{player_id}/agency': '/api/v2/players/{player_id}/agency',
  '/api/players/{player_id}/agency/contract-decision':
      '/api/v2/players/{player_id}/agency/contract-decision',
  '/api/players/{player_id}/agency/transfer-decision':
      '/api/v2/players/{player_id}/agency/transfer-decision',
  '/api/players/{player_id}/availability':
      '/api/v2/players/{player_id}/availability',
  '/api/players/{player_id}/avatar': '/api/v2/players/{player_id}/avatar',
  '/api/players/{player_id}/career': '/api/v2/players/{player_id}/career',
  '/api/players/{player_id}/career-events':
      '/api/v2/players/{player_id}/career-events',
  '/api/players/{player_id}/career/summary':
      '/api/v2/players/{player_id}/career/summary',
  '/api/players/{player_id}/contracts': '/api/v2/players/{player_id}/contracts',
  '/api/players/{player_id}/contracts/summary':
      '/api/v2/players/{player_id}/contracts/summary',
  '/api/players/{player_id}/contracts/{contract_id}/renew':
      '/api/v2/players/{player_id}/contracts/{contract_id}/renew',
  '/api/players/{player_id}/dna': '/api/v2/players/{player_id}/dna',
  '/api/players/{player_id}/events': '/api/v2/players/{player_id}/events',
  '/api/players/{player_id}/injuries': '/api/v2/players/{player_id}/injuries',
  '/api/players/{player_id}/injuries/{injury_id}/recover':
      '/api/v2/players/{player_id}/injuries/{injury_id}/recover',
  '/api/players/{player_id}/interviews':
      '/api/v2/players/{player_id}/interviews',
  '/api/players/{player_id}/lifecycle-snapshot':
      '/api/v2/players/{player_id}/lifecycle-snapshot',
  '/api/players/{player_id}/overview': '/api/v2/players/{player_id}/overview',
  '/api/players/{player_id}/personality':
      '/api/v2/players/{player_id}/personality',
  '/api/players/{player_id}/regen': '/api/v2/players/{player_id}/regen',
  '/api/players/{player_id}/regen/big-club-approaches':
      '/api/v2/players/{player_id}/regen/big-club-approaches',
  '/api/players/{player_id}/regen/contract-offers/quote':
      '/api/v2/players/{player_id}/regen/contract-offers/quote',
  '/api/players/{player_id}/regen/offer-market':
      '/api/v2/players/{player_id}/regen/offer-market',
  '/api/players/{player_id}/regen/pressure-resolution':
      '/api/v2/players/{player_id}/regen/pressure-resolution',
  '/api/players/{player_id}/regen/special-training':
      '/api/v2/players/{player_id}/regen/special-training',
  '/api/players/{player_id}/regen/transfer-listing':
      '/api/v2/players/{player_id}/regen/transfer-listing',
  '/api/players/{player_id}/rivalries': '/api/v2/players/{player_id}/rivalries',
  '/api/players/{player_id}/shares/buy':
      '/api/v2/players/{player_id}/shares/buy',
  '/api/players/{player_id}/shares/dividends':
      '/api/v2/players/{player_id}/shares/dividends',
  '/api/players/{player_id}/shares/events':
      '/api/v2/players/{player_id}/shares/events',
  '/api/players/{player_id}/shares/issue':
      '/api/v2/players/{player_id}/shares/issue',
  '/api/players/{player_id}/shares/market':
      '/api/v2/players/{player_id}/shares/market',
  '/api/players/{player_id}/shares/performance':
      '/api/v2/players/{player_id}/shares/performance',
  '/api/players/{player_id}/shares/sell':
      '/api/v2/players/{player_id}/shares/sell',
  '/api/players/{player_id}/story': '/api/v2/players/{player_id}/story',
  '/api/players/{player_id}/summary': '/api/v2/players/{player_id}/summary',
  '/api/policies/acceptances': '/api/v2/policies/acceptances',
  '/api/policies/country/{country_code}':
      '/api/v2/policies/country/{country_code}',
  '/api/policies/documents': '/api/v2/policies/documents',
  '/api/policies/documents/{document_key}':
      '/api/v2/policies/documents/{document_key}',
  '/api/policies/me/acceptances': '/api/v2/policies/me/acceptances',
  '/api/policies/me/compliance': '/api/v2/policies/me/compliance',
  '/api/policies/me/region': '/api/v2/policies/me/region',
  '/api/policies/me/requirements': '/api/v2/policies/me/requirements',
  '/api/portfolio': '/api/v2/portfolio',
  '/api/portfolio/snapshot': '/api/v2/portfolio/snapshot',
  '/api/portfolio/summary': '/api/v2/portfolio/summary',
  '/api/portfolios/me': '/api/v2/portfolios/me',
  '/api/predictions': '/api/v2/predictions',
  '/api/predictions/leaderboard': '/api/v2/predictions/leaderboard',
  '/api/pundits/matches/{match_key}': '/api/v2/pundits/matches/{match_key}',
  '/api/rankings/clubs': '/api/v2/rankings/clubs',
  '/api/rankings/global': '/api/v2/rankings/global',
  '/api/rankings/players': '/api/v2/rankings/players',
  '/api/ready': '/ready',
  '/api/real-world/events': '/api/v2/real-world/events',
  '/api/real-world/hybrid-players': '/api/v2/real-world/hybrid-players',
  '/api/real-world/normalize': '/api/v2/real-world/normalize',
  '/api/real-world/players': '/api/v2/real-world/players',
  '/api/real-world/players/{real_player_id}':
      '/api/v2/real-world/players/{real_player_id}',
  '/api/real-world/providers': '/api/v2/real-world/providers',
  '/api/real-world/settings/me': '/api/v2/real-world/settings/me',
  '/api/realtime/matches/{match_id}/gateway':
      '/api/v2/realtime/matches/{match_id}/gateway',
  '/api/realtime/matches/{match_id}/stream':
      '/api/v2/realtime/matches/{match_id}/stream',
  '/api/realtime/status': '/api/v2/realtime/status',
  '/api/realtime/stream': '/api/v2/realtime/stream',
  '/api/realtime/wallet/gateway': '/api/v2/realtime/wallet/gateway',
  '/api/realtime/wallet/stream': '/api/v2/realtime/wallet/stream',
  '/api/referrals/attribution': '/api/v2/referrals/attribution',
  '/api/referrals/me/invites': '/api/v2/referrals/me/invites',
  '/api/referrals/me/rewards': '/api/v2/referrals/me/rewards',
  '/api/referrals/me/summary': '/api/v2/referrals/me/summary',
  '/api/referrals/share-codes': '/api/v2/referrals/share-codes',
  '/api/referrals/share-codes/me': '/api/v2/referrals/share-codes/me',
  '/api/referrals/share-codes/{code}/redeem':
      '/api/v2/referrals/share-codes/{code}/redeem',
  '/api/referrals/share-codes/{share_code_id}':
      '/api/v2/referrals/share-codes/{share_code_id}',
  '/api/regen-hype': '/api/v2/regen-hype',
  '/api/regen-universe/achievements': '/api/v2/regen-universe/achievements',
  '/api/regen-universe/awards': '/api/v2/regen-universe/awards',
  '/api/regen-universe/bloodlines': '/api/v2/regen-universe/bloodlines',
  '/api/regen-universe/hall-of-fame': '/api/v2/regen-universe/hall-of-fame',
  '/api/regen-universe/national-regens':
      '/api/v2/regen-universe/national-regens',
  '/api/regen-universe/player/{player_id}':
      '/api/v2/regen-universe/player/{player_id}',
  '/api/regen-universe/players/{player_id}':
      '/api/v2/regen-universe/players/{player_id}',
  '/api/regen-universe/players/{player_id}/timeline':
      '/api/v2/regen-universe/players/{player_id}/timeline',
  '/api/regen-universe/rankings': '/api/v2/regen-universe/rankings',
  '/api/regen-universe/rising-stars': '/api/v2/regen-universe/rising-stars',
  '/api/regen-universe/scouting-feed': '/api/v2/regen-universe/scouting-feed',
  '/api/regen-universe/seasons': '/api/v2/regen-universe/seasons',
  '/api/regen-universe/tracking': '/api/v2/regen-universe/tracking',
  '/api/regen-universe/youth-tournaments':
      '/api/v2/regen-universe/youth-tournaments',
  '/api/regen-universe/youth-tournaments/{tournament_id}':
      '/api/v2/regen-universe/youth-tournaments/{tournament_id}',
  '/api/regens/awards': '/api/v2/regens/awards',
  '/api/regens/awards/{award_id}/vote': '/api/v2/regens/awards/{award_id}/vote',
  '/api/regens/creation-orders': '/api/v2/regens/creation-orders',
  '/api/regens/creation-orders/{order_id}':
      '/api/v2/regens/creation-orders/{order_id}',
  '/api/regens/creation-orders/{order_id}/generate-after-payment':
      '/api/v2/regens/creation-orders/{order_id}/generate-after-payment',
  '/api/regens/creation-orders/{order_id}/pay-with-wallet':
      '/api/v2/regens/creation-orders/{order_id}/pay-with-wallet',
  '/api/regens/feed': '/api/v2/regens/feed',
  '/api/regens/jobs/{job_name}': '/api/v2/regens/jobs/{job_name}',
  '/api/regens/request-son': '/api/v2/regens/request-son',
  '/api/regens/request-son/options': '/api/v2/regens/request-son/options',
  '/api/regens/rising': '/api/v2/regens/rising',
  '/api/regens/top': '/api/v2/regens/top',
  '/api/regens/{regen_id}/lineage': '/api/v2/regens/{regen_id}/lineage',
  '/api/rent': '/api/v2/rent',
  '/api/replays/countdown/{fixture_id}':
      '/api/v2/replays/countdown/{fixture_id}',
  '/api/replays/me': '/api/v2/replays/me',
  '/api/replays/public/featured': '/api/v2/replays/public/featured',
  '/api/replays/{replay_id}': '/api/v2/replays/{replay_id}',
  '/api/reward-engine/me/settlements': '/api/v2/reward-engine/me/settlements',
  '/api/reward-engine/me/summary': '/api/v2/reward-engine/me/summary',
  '/api/risk-ops/me/aml-cases': '/api/v2/risk-ops/me/aml-cases',
  '/api/risk-ops/me/fraud-cases': '/api/v2/risk-ops/me/fraud-cases',
  '/api/risk-ops/me/overview': '/api/v2/risk-ops/me/overview',
  '/api/risk-ops/me/restrictions': '/api/v2/risk-ops/me/restrictions',
  '/api/risk-ops/me/signals': '/api/v2/risk-ops/me/signals',
  '/api/rivalries/matches': '/api/v2/rivalries/matches',
  '/api/scout/report/{player_id}': '/api/v2/scout/report/{player_id}',
  '/api/scouts': '/api/v2/scouts',
  '/api/scouts/{scout_id}/discover': '/api/v2/scouts/{scout_id}/discover',
  '/api/season-pass': '/api/v2/season-pass',
  '/api/season-pass/claim': '/api/v2/season-pass/claim',
  '/api/season-pass/me': '/api/v2/season-pass/me',
  '/api/season-pass/rewards/{reward_id}/claim':
      '/api/v2/season-pass/rewards/{reward_id}/claim',
  '/api/season/current': '/api/v2/season/current',
  '/api/season/history': '/api/v2/season/history',
  '/api/session/bootstrap': '/api/v2/session/bootstrap',
  '/api/shows/debate': '/api/v2/shows/debate',
  '/api/shows/post-match/{match_id}': '/api/v2/shows/post-match/{match_id}',
  '/api/shows/pre-match/{match_id}': '/api/v2/shows/pre-match/{match_id}',
  '/api/simulation-matchmaking/hosted-competitions/preview':
      '/api/v2/simulation-matchmaking/hosted-competitions/preview',
  '/api/simulation-matchmaking/profiles/{user_id}':
      '/api/v2/simulation-matchmaking/profiles/{user_id}',
  '/api/simulation-matchmaking/quick-game':
      '/api/v2/simulation-matchmaking/quick-game',
  '/api/simulation-matchmaking/quick-tournament':
      '/api/v2/simulation-matchmaking/quick-tournament',
  '/api/social/clubs/{club_id}/community':
      '/api/v2/social/clubs/{club_id}/community',
  '/api/social/clubs/{club_id}/community/messages':
      '/api/v2/social/clubs/{club_id}/community/messages',
  '/api/social/feed': '/api/v2/social/feed',
  '/api/social/follows': '/api/v2/social/follows',
  '/api/social/follows/me': '/api/v2/social/follows/me',
  '/api/social/profile/me': '/api/v2/social/profile/me',
  '/api/social/rivalries/{club_a_id}/{club_b_id}':
      '/api/v2/social/rivalries/{club_a_id}/{club_b_id}',
  '/api/social/rivalries/{club_a_id}/{club_b_id}/banter':
      '/api/v2/social/rivalries/{club_a_id}/{club_b_id}/banter',
  '/api/sponsors': '/api/v2/sponsors',
  '/api/sponsorship/clubs/{club_id}/contracts':
      '/api/v2/sponsorship/clubs/{club_id}/contracts',
  '/api/sponsorship/clubs/{club_id}/dashboard':
      '/api/v2/sponsorship/clubs/{club_id}/dashboard',
  '/api/sponsorship/clubs/{club_id}/offers':
      '/api/v2/sponsorship/clubs/{club_id}/offers',
  '/api/sponsorship/clubs/{club_id}/sponsors':
      '/api/v2/sponsorship/clubs/{club_id}/sponsors',
  '/api/sponsorship/contracts/request': '/api/v2/sponsorship/contracts/request',
  '/api/sponsorship/me/leads': '/api/v2/sponsorship/me/leads',
  '/api/sponsorship/packages': '/api/v2/sponsorship/packages',
  '/api/sponsorship/placements': '/api/v2/sponsorship/placements',
  '/api/story-feed': '/api/v2/story-feed',
  '/api/story-feed/digest': '/api/v2/story-feed/digest',
  '/api/streamer-tournaments': '/api/v2/streamer-tournaments',
  '/api/streamer-tournaments/mine': '/api/v2/streamer-tournaments/mine',
  '/api/streamer-tournaments/{tournament_id}':
      '/api/v2/streamer-tournaments/{tournament_id}',
  '/api/streamer-tournaments/{tournament_id}/invites':
      '/api/v2/streamer-tournaments/{tournament_id}/invites',
  '/api/streamer-tournaments/{tournament_id}/join':
      '/api/v2/streamer-tournaments/{tournament_id}/join',
  '/api/streamer-tournaments/{tournament_id}/publish':
      '/api/v2/streamer-tournaments/{tournament_id}/publish',
  '/api/streamer-tournaments/{tournament_id}/rewards':
      '/api/v2/streamer-tournaments/{tournament_id}/rewards',
  '/api/surveillance/circular-trade-alerts':
      '/api/v2/surveillance/circular-trade-alerts',
  '/api/surveillance/holder-concentration-alerts':
      '/api/v2/surveillance/holder-concentration-alerts',
  '/api/surveillance/suspicious-clusters':
      '/api/v2/surveillance/suspicious-clusters',
  '/api/surveillance/suspicious-players':
      '/api/v2/surveillance/suspicious-players',
  '/api/surveillance/thin-market-alerts':
      '/api/v2/surveillance/thin-market-alerts',
  '/api/sync/update': '/api/v2/sync/update',
  '/api/tickets/attendance/{match_id}/react':
      '/api/v2/tickets/attendance/{match_id}/react',
  '/api/tickets/buy': '/api/v2/tickets/buy',
  '/api/tickets/event/{match_id}': '/api/v2/tickets/event/{match_id}',
  '/api/tickets/resell': '/api/v2/tickets/resell',
  '/api/tickets/waitlist': '/api/v2/tickets/waitlist',
  '/api/tournaments': '/api/v2/tournaments',
  '/api/tournaments/{tournament_id}': '/api/v2/tournaments/{tournament_id}',
  '/api/tournaments/{tournament_id}/advance':
      '/api/v2/tournaments/{tournament_id}/advance',
  '/api/tournaments/{tournament_id}/join':
      '/api/v2/tournaments/{tournament_id}/join',
  '/api/tournaments/{tournament_id}/matches/{match_id}/result':
      '/api/v2/tournaments/{tournament_id}/matches/{match_id}/result',
  '/api/trader/markets': '/api/v2/trader/markets',
  '/api/trader/orders': '/api/v2/trader/orders',
  '/api/trader/overview': '/api/v2/trader/overview',
  '/api/trader/p2p': '/api/v2/trader/p2p',
  '/api/trader/security/totp/setup': '/api/v2/trader/security/totp/setup',
  '/api/trader/watchlist': '/api/v2/trader/watchlist',
  '/api/transfer-market/clubs/{club_id}/team-dynamics':
      '/api/v2/transfer-market/clubs/{club_id}/team-dynamics',
  '/api/transfer-market/coaches/{club_id}/demands':
      '/api/v2/transfer-market/coaches/{club_id}/demands',
  '/api/transfer-market/coaches/{club_id}/profile':
      '/api/v2/transfer-market/coaches/{club_id}/profile',
  '/api/transfer-market/jobs/run': '/api/v2/transfer-market/jobs/run',
  '/api/transfer-market/listings': '/api/v2/transfer-market/listings',
  '/api/transfer-market/listings/{listing_id}':
      '/api/v2/transfer-market/listings/{listing_id}',
  '/api/transfer-market/listings/{listing_id}/bids':
      '/api/v2/transfer-market/listings/{listing_id}/bids',
  '/api/transfer-market/listings/{listing_id}/close':
      '/api/v2/transfer-market/listings/{listing_id}/close',
  '/api/transfer-market/listings/{listing_id}/contract-offer':
      '/api/v2/transfer-market/listings/{listing_id}/contract-offer',
  '/api/transfer-market/listings/{listing_id}/negotiation':
      '/api/v2/transfer-market/listings/{listing_id}/negotiation',
  '/api/transfer-market/listings/{listing_id}/stream':
      '/api/v2/transfer-market/listings/{listing_id}/stream',
  '/api/transfer-market/players/{player_id}/decision-profile':
      '/api/v2/transfer-market/players/{player_id}/decision-profile',
  '/api/transfer-market/watchlist': '/api/v2/transfer-market/watchlist',
  '/api/transfers/windows': '/api/v2/transfers/windows',
  '/api/transfers/windows/{window_id}': '/api/v2/transfers/windows/{window_id}',
  '/api/transfers/windows/{window_id}/bids':
      '/api/v2/transfers/windows/{window_id}/bids',
  '/api/transfers/windows/{window_id}/bids/{bid_id}/accept':
      '/api/v2/transfers/windows/{window_id}/bids/{bid_id}/accept',
  '/api/transfers/windows/{window_id}/bids/{bid_id}/reject':
      '/api/v2/transfers/windows/{window_id}/bids/{bid_id}/reject',
  '/api/transfers/windows/{window_id}/players/{player_id}/regen-bid-evaluations':
      '/api/v2/transfers/windows/{window_id}/players/{player_id}/regen-bid-evaluations',
  '/api/transfers/windows/{window_id}/players/{player_id}/resolve-regen-bid':
      '/api/v2/transfers/windows/{window_id}/players/{player_id}/resolve-regen-bid',
  '/api/trust/me': '/api/v2/trust/me',
  '/api/trust/{user_id}': '/api/v2/trust/{user_id}',
  '/api/ultimate-league/competitors/{competitor_id}':
      '/api/v2/ultimate-league/competitors/{competitor_id}',
  '/api/ultimate-league/matches/result':
      '/api/v2/ultimate-league/matches/result',
  '/api/ultimate-league/matchmaking/batch':
      '/api/v2/ultimate-league/matchmaking/batch',
  '/api/ultimate-league/standings/{tier}':
      '/api/v2/ultimate-league/standings/{tier}',
  '/api/ultimate-league/tactical-presets':
      '/api/v2/ultimate-league/tactical-presets',
  '/api/ultimate-league/tactical-presets/{preset_id}/purchase':
      '/api/v2/ultimate-league/tactical-presets/{preset_id}/purchase',
  '/api/ultimate-league/tiers': '/api/v2/ultimate-league/tiers',
  '/api/ultimate-league/tournaments': '/api/v2/ultimate-league/tournaments',
  '/api/ultimate-league/tournaments/{tournament_id}':
      '/api/v2/ultimate-league/tournaments/{tournament_id}',
  '/api/ultimate-league/tournaments/{tournament_id}/payouts/preview':
      '/api/v2/ultimate-league/tournaments/{tournament_id}/payouts/preview',
  '/api/users/me': '/api/v2/users/me',
  '/api/users/me/profile': '/api/v2/users/me/profile',
  '/api/users/suggestions': '/api/v2/users/suggestions',
  '/api/users/{user_id}/followers': '/api/v2/users/{user_id}/followers',
  '/api/users/{user_id}/following': '/api/v2/users/{user_id}/following',
  '/api/v1/academy': '/api/v2/academy',
  '/api/v1/academy/awards': '/api/v2/academy/awards',
  '/api/v1/academy/fixtures': '/api/v2/academy/fixtures',
  '/api/v1/academy/generate': '/api/v2/academy/generate',
  '/api/v1/academy/promote/{player_id}': '/api/v2/academy/promote/{player_id}',
  '/api/v1/academy/qualification': '/api/v2/academy/qualification',
  '/api/v1/academy/registration': '/api/v2/academy/registration',
  '/api/v1/academy/season-summary': '/api/v2/academy/season-summary',
  '/api/v1/academy/standings': '/api/v2/academy/standings',
  '/api/v1/admin-engine/bootstrap': '/api/v2/admin-engine/bootstrap',
  '/api/v1/admin/access': '/api/v2/admin/access',
  '/api/v1/admin/access/permissions': '/api/v2/admin/access/permissions',
  '/api/v1/admin/access/{user_id}/permissions':
      '/api/v2/admin/access/{user_id}/permissions',
  '/api/v1/admin/admin-engine/calendar-rules':
      '/api/v2/admin/admin-engine/calendar-rules',
  '/api/v1/admin/admin-engine/feature-flags':
      '/api/v2/admin/admin-engine/feature-flags',
  '/api/v1/admin/admin-engine/reward-rules':
      '/api/v2/admin/admin-engine/reward-rules',
  '/api/v1/admin/admin-engine/schedule-preview':
      '/api/v2/admin/admin-engine/schedule-preview',
  '/api/v1/admin/analytics/agent-learning':
      '/api/v2/admin/analytics/agent-learning',
  '/api/v1/admin/analytics/anomalies': '/api/v2/admin/analytics/anomalies',
  '/api/v1/admin/analytics/funnels': '/api/v2/admin/analytics/funnels',
  '/api/v1/admin/analytics/match-outcomes':
      '/api/v2/admin/analytics/match-outcomes',
  '/api/v1/admin/analytics/player-matching':
      '/api/v2/admin/analytics/player-matching',
  '/api/v1/admin/analytics/player-matching/recompute-weights':
      '/api/v2/admin/analytics/player-matching/recompute-weights',
  '/api/v1/admin/analytics/price-predictions':
      '/api/v2/admin/analytics/price-predictions',
  '/api/v1/admin/analytics/summary': '/api/v2/admin/analytics/summary',
  '/api/v1/admin/analytics/user-segments':
      '/api/v2/admin/analytics/user-segments',
  '/api/v1/admin/ban-user': '/api/v2/admin/ban-user',
  '/api/v1/admin/broadcast-rights/jobs/run':
      '/api/v2/admin/broadcast-rights/jobs/run',
  '/api/v1/admin/calendar-engine/events':
      '/api/v2/admin/calendar-engine/events',
  '/api/v1/admin/calendar-engine/hosted-competitions/{competition_id}/launch':
      '/api/v2/admin/calendar-engine/hosted-competitions/{competition_id}/launch',
  '/api/v1/admin/calendar-engine/national-competitions/{competition_id}/launch':
      '/api/v2/admin/calendar-engine/national-competitions/{competition_id}/launch',
  '/api/v1/admin/calendar-engine/seasons':
      '/api/v2/admin/calendar-engine/seasons',
  '/api/v1/admin/club-infra/seed': '/api/v2/admin/club-infra/seed',
  '/api/v1/admin/clubs/academy-analytics':
      '/api/v2/admin/clubs/academy-analytics',
  '/api/v1/admin/clubs/analytics': '/api/v2/admin/clubs/analytics',
  '/api/v1/admin/clubs/finance-analytics':
      '/api/v2/admin/clubs/finance-analytics',
  '/api/v1/admin/clubs/ops-summary': '/api/v2/admin/clubs/ops-summary',
  '/api/v1/admin/clubs/scouting-analytics':
      '/api/v2/admin/clubs/scouting-analytics',
  '/api/v1/admin/clubs/sponsorship-analytics':
      '/api/v2/admin/clubs/sponsorship-analytics',
  '/api/v1/admin/clubs/summary': '/api/v2/admin/clubs/summary',
  '/api/v1/admin/clubs/{club_id}': '/api/v2/admin/clubs/{club_id}',
  '/api/v1/admin/clubs/{club_id}/moderate-branding':
      '/api/v2/admin/clubs/{club_id}/moderate-branding',
  '/api/v1/admin/competitions': '/api/v2/admin/competitions',
  '/api/v1/admin/competitions/reminders/dispatch':
      '/api/v2/admin/competitions/reminders/dispatch',
  '/api/v1/admin/competitive-integrity/matches/{match_id}/validation':
      '/api/v2/admin/competitive-integrity/matches/{match_id}/validation',
  '/api/v1/admin/competitive-integrity/workers/run-once':
      '/api/v2/admin/competitive-integrity/workers/run-once',
  '/api/v1/admin/config/liquidity-bands':
      '/api/v2/admin/config/liquidity-bands',
  '/api/v1/admin/config/player-card-market-integrity':
      '/api/v2/admin/config/player-card-market-integrity',
  '/api/v1/admin/config/supply-tiers': '/api/v2/admin/config/supply-tiers',
  '/api/v1/admin/config/suspicion-thresholds':
      '/api/v2/admin/config/suspicion-thresholds',
  '/api/v1/admin/config/value-controls': '/api/v2/admin/config/value-controls',
  '/api/v1/admin/config/value-controls/audits':
      '/api/v2/admin/config/value-controls/audits',
  '/api/v1/admin/config/value-controls/integrity/candidates':
      '/api/v2/admin/config/value-controls/integrity/candidates',
  '/api/v1/admin/config/value-controls/players/{player_id}':
      '/api/v2/admin/config/value-controls/players/{player_id}',
  '/api/v1/admin/config/value-controls/preview/{player_id}':
      '/api/v2/admin/config/value-controls/preview/{player_id}',
  '/api/v1/admin/config/value-controls/recompute':
      '/api/v2/admin/config/value-controls/recompute',
  '/api/v1/admin/config/value-controls/run-history':
      '/api/v2/admin/config/value-controls/run-history',
  '/api/v1/admin/creator-campaigns/{campaign_id}/metrics':
      '/api/v2/admin/creator-campaigns/{campaign_id}/metrics',
  '/api/v1/admin/creator/applications': '/api/v2/admin/creator/applications',
  '/api/v1/admin/creator/applications/{application_id}/approve':
      '/api/v2/admin/creator/applications/{application_id}/approve',
  '/api/v1/admin/creator/applications/{application_id}/reject':
      '/api/v2/admin/creator/applications/{application_id}/reject',
  '/api/v1/admin/creator/applications/{application_id}/request-verification':
      '/api/v2/admin/creator/applications/{application_id}/request-verification',
  '/api/v1/admin/creator/cards/assign': '/api/v2/admin/creator/cards/assign',
  '/api/v1/admin/creator/dashboard': '/api/v2/admin/creator/dashboard',
  '/api/v1/admin/creator/fan-share-market/control':
      '/api/v2/admin/creator/fan-share-market/control',
  '/api/v1/admin/discovery/featured-rails':
      '/api/v2/admin/discovery/featured-rails',
  '/api/v1/admin/disputes': '/api/v2/admin/disputes',
  '/api/v1/admin/disputes/{dispute_id}/assign':
      '/api/v2/admin/disputes/{dispute_id}/assign',
  '/api/v1/admin/disputes/{dispute_id}/status':
      '/api/v2/admin/disputes/{dispute_id}/status',
  '/api/v1/admin/economy/burn-events': '/api/v2/admin/economy/burn-events',
  '/api/v1/admin/economy/fx-rates': '/api/v2/admin/economy/fx-rates',
  '/api/v1/admin/economy/gift-catalog': '/api/v2/admin/economy/gift-catalog',
  '/api/v1/admin/economy/gift-combo-rules':
      '/api/v2/admin/economy/gift-combo-rules',
  '/api/v1/admin/economy/governor': '/api/v2/admin/economy/governor',
  '/api/v1/admin/economy/governor/apply':
      '/api/v2/admin/economy/governor/apply',
  '/api/v1/admin/economy/governor/evaluate':
      '/api/v2/admin/economy/governor/evaluate',
  '/api/v1/admin/economy/governor/policy':
      '/api/v2/admin/economy/governor/policy',
  '/api/v1/admin/economy/regional-pricing':
      '/api/v2/admin/economy/regional-pricing',
  '/api/v1/admin/economy/revenue-share-rules':
      '/api/v2/admin/economy/revenue-share-rules',
  '/api/v1/admin/economy/service-pricing':
      '/api/v2/admin/economy/service-pricing',
  '/api/v1/admin/fan-predictions/matches/{match_id}/fixture':
      '/api/v2/admin/fan-predictions/matches/{match_id}/fixture',
  '/api/v1/admin/fan-predictions/matches/{match_id}/settlement':
      '/api/v2/admin/fan-predictions/matches/{match_id}/settlement',
  '/api/v1/admin/fan-wars/creator-country-assignments':
      '/api/v2/admin/fan-wars/creator-country-assignments',
  '/api/v1/admin/fan-wars/nations-cup': '/api/v2/admin/fan-wars/nations-cup',
  '/api/v1/admin/fan-wars/nations-cup/{competition_id}/advance':
      '/api/v2/admin/fan-wars/nations-cup/{competition_id}/advance',
  '/api/v1/admin/fan-wars/points': '/api/v2/admin/fan-wars/points',
  '/api/v1/admin/fan-wars/profiles': '/api/v2/admin/fan-wars/profiles',
  '/api/v1/admin/fan-wars/profiles/{profile_id}/rivals/{rival_profile_id}':
      '/api/v2/admin/fan-wars/profiles/{profile_id}/rivals/{rival_profile_id}',
  '/api/v1/admin/federations/run-jobs': '/api/v2/admin/federations/run-jobs',
  '/api/v1/admin/finance/account-controls':
      '/api/v2/admin/finance/account-controls',
  '/api/v1/admin/finance/account-controls/{user_id}':
      '/api/v2/admin/finance/account-controls/{user_id}',
  '/api/v1/admin/finance/control-tower': '/api/v2/admin/finance/control-tower',
  '/api/v1/admin/finance/manual-price-overrides':
      '/api/v2/admin/finance/manual-price-overrides',
  '/api/v1/admin/finance/manual-price-overrides/{asset_type}/{asset_id}':
      '/api/v2/admin/finance/manual-price-overrides/{asset_type}/{asset_id}',
  '/api/v1/admin/finance/match-kill-switches':
      '/api/v2/admin/finance/match-kill-switches',
  '/api/v1/admin/finance/match-kill-switches/{match_id}':
      '/api/v2/admin/finance/match-kill-switches/{match_id}',
  '/api/v1/admin/finance/reconciliation':
      '/api/v2/admin/finance/reconciliation',
  '/api/v1/admin/finance/simulate': '/api/v2/admin/finance/simulate',
  '/api/v1/admin/finance/wallet-protection':
      '/api/v2/admin/finance/wallet-protection',
  '/api/v1/admin/flags': '/api/v2/admin/flags',
  '/api/v1/admin/football-events/categories':
      '/api/v2/admin/football-events/categories',
  '/api/v1/admin/football-events/effects/expire':
      '/api/v2/admin/football-events/effects/expire',
  '/api/v1/admin/football-events/events':
      '/api/v2/admin/football-events/events',
  '/api/v1/admin/football-events/events/import':
      '/api/v2/admin/football-events/events/import',
  '/api/v1/admin/football-events/events/{event_id}/review':
      '/api/v2/admin/football-events/events/{event_id}/review',
  '/api/v1/admin/football-events/events/{event_id}/severity':
      '/api/v2/admin/football-events/events/{event_id}/severity',
  '/api/v1/admin/football-events/rules': '/api/v2/admin/football-events/rules',
  '/api/v1/admin/god-mode/audit-events': '/api/v2/admin/god-mode/audit-events',
  '/api/v1/admin/god-mode/bootstrap': '/api/v2/admin/god-mode/bootstrap',
  '/api/v1/admin/god-mode/commissions': '/api/v2/admin/god-mode/commissions',
  '/api/v1/admin/god-mode/competition-controls':
      '/api/v2/admin/god-mode/competition-controls',
  '/api/v1/admin/god-mode/high-risk-actions':
      '/api/v2/admin/god-mode/high-risk-actions',
  '/api/v1/admin/god-mode/liquidity/interventions':
      '/api/v2/admin/god-mode/liquidity/interventions',
  '/api/v1/admin/god-mode/payment-rails':
      '/api/v2/admin/god-mode/payment-rails',
  '/api/v1/admin/god-mode/payment-rails/health':
      '/api/v2/admin/god-mode/payment-rails/health',
  '/api/v1/admin/god-mode/roles': '/api/v2/admin/god-mode/roles',
  '/api/v1/admin/god-mode/treasury': '/api/v2/admin/god-mode/treasury',
  '/api/v1/admin/god-mode/treasury/dashboard':
      '/api/v2/admin/god-mode/treasury/dashboard',
  '/api/v1/admin/god-mode/treasury/withdrawals':
      '/api/v2/admin/god-mode/treasury/withdrawals',
  '/api/v1/admin/god-mode/withdrawal-controls':
      '/api/v2/admin/god-mode/withdrawal-controls',
  '/api/v1/admin/god-mode/withdrawals': '/api/v2/admin/god-mode/withdrawals',
  '/api/v1/admin/god-mode/withdrawals/summary':
      '/api/v2/admin/god-mode/withdrawals/summary',
  '/api/v1/admin/god-mode/withdrawals/{payout_request_id}':
      '/api/v2/admin/god-mode/withdrawals/{payout_request_id}',
  '/api/v1/admin/governance/proposals/{proposal_id}/status':
      '/api/v2/admin/governance/proposals/{proposal_id}/status',
  '/api/v1/admin/history-engagement/run-workers':
      '/api/v2/admin/history-engagement/run-workers',
  '/api/v1/admin/hosted-competitions': '/api/v2/admin/hosted-competitions',
  '/api/v1/admin/hosted-competitions/seed':
      '/api/v2/admin/hosted-competitions/seed',
  '/api/v1/admin/hosted-competitions/{competition_id}/finalize':
      '/api/v2/admin/hosted-competitions/{competition_id}/finalize',
  '/api/v1/admin/hosted-competitions/{competition_id}/launch':
      '/api/v2/admin/hosted-competitions/{competition_id}/launch',
  '/api/v1/admin/integrity-engine/incidents/{incident_id}/resolve':
      '/api/v2/admin/integrity-engine/incidents/{incident_id}/resolve',
  '/api/v1/admin/integrity-engine/scan': '/api/v2/admin/integrity-engine/scan',
  '/api/v1/admin/jackpot/balance': '/api/v2/admin/jackpot/balance',
  '/api/v1/admin/jackpot/runtime': '/api/v2/admin/jackpot/runtime',
  '/api/v1/admin/jackpot/trigger': '/api/v2/admin/jackpot/trigger',
  '/api/v1/admin/leaderboard/season/archive':
      '/api/v2/admin/leaderboard/season/archive',
  '/api/v1/admin/leaderboard/season/reset':
      '/api/v2/admin/leaderboard/season/reset',
  '/api/v1/admin/managers/audit-log': '/api/v2/admin/managers/audit-log',
  '/api/v1/admin/managers/catalog/{manager_id}/supply':
      '/api/v2/admin/managers/catalog/{manager_id}/supply',
  '/api/v1/admin/managers/competitions': '/api/v2/admin/managers/competitions',
  '/api/v1/admin/managers/competitions/{code}':
      '/api/v2/admin/managers/competitions/{code}',
  '/api/v1/admin/managers/competitions/{code}/orchestrate':
      '/api/v2/admin/managers/competitions/{code}/orchestrate',
  '/api/v1/admin/media-engine/creator-league/clubs/{club_id}/stadium-level':
      '/api/v2/admin/media-engine/creator-league/clubs/{club_id}/stadium-level',
  '/api/v1/admin/media-engine/creator-league/matches/{match_id}/analytics':
      '/api/v2/admin/media-engine/creator-league/matches/{match_id}/analytics',
  '/api/v1/admin/media-engine/creator-league/matches/{match_id}/settlement':
      '/api/v2/admin/media-engine/creator-league/matches/{match_id}/settlement',
  '/api/v1/admin/media-engine/creator-league/stadium-controls':
      '/api/v2/admin/media-engine/creator-league/stadium-controls',
  '/api/v1/admin/media-engine/exports': '/api/v2/admin/media-engine/exports',
  '/api/v1/admin/media-engine/highlights':
      '/api/v2/admin/media-engine/highlights',
  '/api/v1/admin/media-engine/highlights/{storage_key:path}/archive':
      '/api/v2/admin/media-engine/highlights/{storage_key:path}/archive',
  '/api/v1/admin/media-engine/share-exports/{export_id}/revenue-attributions':
      '/api/v2/admin/media-engine/share-exports/{export_id}/revenue-attributions',
  '/api/v1/admin/media-engine/snapshots':
      '/api/v2/admin/media-engine/snapshots',
  '/api/v1/admin/moderation/reports': '/api/v2/admin/moderation/reports',
  '/api/v1/admin/moderation/reports/summary':
      '/api/v2/admin/moderation/reports/summary',
  '/api/v1/admin/moderation/reports/{report_id}/assign':
      '/api/v2/admin/moderation/reports/{report_id}/assign',
  '/api/v1/admin/moderation/reports/{report_id}/resolve':
      '/api/v2/admin/moderation/reports/{report_id}/resolve',
  '/api/v1/admin/national-team-engine/competitions':
      '/api/v2/admin/national-team-engine/competitions',
  '/api/v1/admin/national-team-engine/competitions/seed-defaults':
      '/api/v2/admin/national-team-engine/competitions/seed-defaults',
  '/api/v1/admin/national-team-engine/competitions/{competition_id}/ads':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads',
  '/api/v1/admin/national-team-engine/competitions/{competition_id}/ads/rotate':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads/rotate',
  '/api/v1/admin/national-team-engine/competitions/{competition_id}/ads/{ad_id}':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads/{ad_id}',
  '/api/v1/admin/national-team-engine/competitions/{competition_id}/entries':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/entries',
  '/api/v1/admin/national-team-engine/competitions/{competition_id}/entries/lock':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/entries/lock',
  '/api/v1/admin/national-team-engine/competitions/{competition_id}/lifecycle/advance':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/lifecycle/advance',
  '/api/v1/admin/national-team-engine/competitions/{competition_id}/rentals/cleanup':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/rentals/cleanup',
  '/api/v1/admin/national-team-engine/competitions/{competition_id}/story-events/generate':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/story-events/generate',
  '/api/v1/admin/national-team-engine/competitions/{competition_id}/theme':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/theme',
  '/api/v1/admin/national-team-engine/entries/{entry_id}/squad':
      '/api/v2/admin/national-team-engine/entries/{entry_id}/squad',
  '/api/v1/admin/notifications/announcements':
      '/api/v2/admin/notifications/announcements',
  '/api/v1/admin/ops/alerts': '/api/v2/admin/ops/alerts',
  '/api/v1/admin/ops/audit': '/api/v2/admin/ops/audit',
  '/api/v1/admin/ops/broadcast-expiration':
      '/api/v2/admin/ops/broadcast-expiration',
  '/api/v1/admin/ops/broadcast-revenue': '/api/v2/admin/ops/broadcast-revenue',
  '/api/v1/admin/ops/club-market-valuations':
      '/api/v2/admin/ops/club-market-valuations',
  '/api/v1/admin/ops/dashboard': '/api/v2/admin/ops/dashboard',
  '/api/v1/admin/ops/fan-updates': '/api/v2/admin/ops/fan-updates',
  '/api/v1/admin/ops/identity-evolution':
      '/api/v2/admin/ops/identity-evolution',
  '/api/v1/admin/ops/integrity-scan': '/api/v2/admin/ops/integrity-scan',
  '/api/v1/admin/ops/media-generation': '/api/v2/admin/ops/media-generation',
  '/api/v1/admin/ops/media-retention': '/api/v2/admin/ops/media-retention',
  '/api/v1/admin/ops/national-team-rental-cleanup':
      '/api/v2/admin/ops/national-team-rental-cleanup',
  '/api/v1/admin/ops/ownership-groups/reputation':
      '/api/v2/admin/ops/ownership-groups/reputation',
  '/api/v1/admin/ops/platform-infra': '/api/v2/admin/ops/platform-infra',
  '/api/v1/admin/ops/stadium-ad-rotation':
      '/api/v2/admin/ops/stadium-ad-rotation',
  '/api/v1/admin/ops/tournament-storylines':
      '/api/v2/admin/ops/tournament-storylines',
  '/api/v1/admin/ownership-groups/reputation-cycle':
      '/api/v2/admin/ownership-groups/reputation-cycle',
  '/api/v1/admin/player-import/card-supply':
      '/api/v2/admin/player-import/card-supply',
  '/api/v1/admin/player-import/card-supply/csv':
      '/api/v2/admin/player-import/card-supply/csv',
  '/api/v1/admin/player-import/jobs': '/api/v2/admin/player-import/jobs',
  '/api/v1/admin/player-import/jobs/{job_id}':
      '/api/v2/admin/player-import/jobs/{job_id}',
  '/api/v1/admin/player-import/youth/generate':
      '/api/v2/admin/player-import/youth/generate',
  '/api/v1/admin/policies/country-policies':
      '/api/v2/admin/policies/country-policies',
  '/api/v1/admin/policies/documents': '/api/v2/admin/policies/documents',
  '/api/v1/admin/policies/documents/versions':
      '/api/v2/admin/policies/documents/versions',
  '/api/v1/admin/policies/regions/override':
      '/api/v2/admin/policies/regions/override',
  '/api/v1/admin/real-world/providers': '/api/v2/admin/real-world/providers',
  '/api/v1/admin/real-world/providers/{provider_id}/sync':
      '/api/v2/admin/real-world/providers/{provider_id}/sync',
  '/api/v1/admin/referrals/analytics/summary':
      '/api/v2/admin/referrals/analytics/summary',
  '/api/v1/admin/referrals/attributions':
      '/api/v2/admin/referrals/attributions',
  '/api/v1/admin/referrals/creators': '/api/v2/admin/referrals/creators',
  '/api/v1/admin/referrals/creators/{creator_id}':
      '/api/v2/admin/referrals/creators/{creator_id}',
  '/api/v1/admin/referrals/creators/{creator_id}/reward-freeze':
      '/api/v2/admin/referrals/creators/{creator_id}/reward-freeze',
  '/api/v1/admin/referrals/dashboard': '/api/v2/admin/referrals/dashboard',
  '/api/v1/admin/referrals/flags': '/api/v2/admin/referrals/flags',
  '/api/v1/admin/referrals/leaderboard': '/api/v2/admin/referrals/leaderboard',
  '/api/v1/admin/referrals/rewards/pending':
      '/api/v2/admin/referrals/rewards/pending',
  '/api/v1/admin/referrals/rewards/{reward_id}/review':
      '/api/v2/admin/referrals/rewards/{reward_id}/review',
  '/api/v1/admin/referrals/share-codes': '/api/v2/admin/referrals/share-codes',
  '/api/v1/admin/referrals/share-codes/{share_code_id}':
      '/api/v2/admin/referrals/share-codes/{share_code_id}',
  '/api/v1/admin/referrals/share-codes/{share_code_id}/block':
      '/api/v2/admin/referrals/share-codes/{share_code_id}/block',
  '/api/v1/admin/regen-universe/jobs/dna-evolution':
      '/api/v2/admin/regen-universe/jobs/dna-evolution',
  '/api/v1/admin/regen-universe/jobs/rivalry-detection':
      '/api/v2/admin/regen-universe/jobs/rivalry-detection',
  '/api/v1/admin/regen-universe/jobs/story-regeneration':
      '/api/v2/admin/regen-universe/jobs/story-regeneration',
  '/api/v1/admin/regen-universe/jobs/tournament-scheduling':
      '/api/v2/admin/regen-universe/jobs/tournament-scheduling',
  '/api/v1/admin/regen-universe/national-regens/preseed':
      '/api/v2/admin/regen-universe/national-regens/preseed',
  '/api/v1/admin/regen-universe/players/{player_id}/portrait/ban':
      '/api/v2/admin/regen-universe/players/{player_id}/portrait/ban',
  '/api/v1/admin/regen-universe/players/{player_id}/portrait/override':
      '/api/v2/admin/regen-universe/players/{player_id}/portrait/override',
  '/api/v1/admin/regen-universe/players/{player_id}/portrait/regenerate':
      '/api/v2/admin/regen-universe/players/{player_id}/portrait/regenerate',
  '/api/v1/admin/regen-universe/seasons':
      '/api/v2/admin/regen-universe/seasons',
  '/api/v1/admin/regen-universe/seasons/{season_id}/close':
      '/api/v2/admin/regen-universe/seasons/{season_id}/close',
  '/api/v1/admin/regen-universe/seasons/{season_id}/evolution':
      '/api/v2/admin/regen-universe/seasons/{season_id}/evolution',
  '/api/v1/admin/regen-universe/youth-tournaments':
      '/api/v2/admin/regen-universe/youth-tournaments',
  '/api/v1/admin/reward-engine/promo-pool/credits':
      '/api/v2/admin/reward-engine/promo-pool/credits',
  '/api/v1/admin/reward-engine/settlements':
      '/api/v2/admin/reward-engine/settlements',
  '/api/v1/admin/risk-ops/actions': '/api/v2/admin/risk-ops/actions',
  '/api/v1/admin/risk-ops/actions/{action_id}/release':
      '/api/v2/admin/risk-ops/actions/{action_id}/release',
  '/api/v1/admin/risk-ops/aml-cases': '/api/v2/admin/risk-ops/aml-cases',
  '/api/v1/admin/risk-ops/audit-logs': '/api/v2/admin/risk-ops/audit-logs',
  '/api/v1/admin/risk-ops/cases/{case_type}/{case_id}/resolve':
      '/api/v2/admin/risk-ops/cases/{case_type}/{case_id}/resolve',
  '/api/v1/admin/risk-ops/evaluate': '/api/v2/admin/risk-ops/evaluate',
  '/api/v1/admin/risk-ops/fraud-cases': '/api/v2/admin/risk-ops/fraud-cases',
  '/api/v1/admin/risk-ops/overview': '/api/v2/admin/risk-ops/overview',
  '/api/v1/admin/risk-ops/scan': '/api/v2/admin/risk-ops/scan',
  '/api/v1/admin/risk-ops/signals': '/api/v2/admin/risk-ops/signals',
  '/api/v1/admin/risk-ops/system-events':
      '/api/v2/admin/risk-ops/system-events',
  '/api/v1/admin/sponsorship/analytics': '/api/v2/admin/sponsorship/analytics',
  '/api/v1/admin/sponsorship/categories/{category}':
      '/api/v2/admin/sponsorship/categories/{category}',
  '/api/v1/admin/sponsorship/contracts/{contract_id}/review':
      '/api/v2/admin/sponsorship/contracts/{contract_id}/review',
  '/api/v1/admin/sponsorship/contracts/{contract_id}/settle-next':
      '/api/v2/admin/sponsorship/contracts/{contract_id}/settle-next',
  '/api/v1/admin/sponsorship/offers': '/api/v2/admin/sponsorship/offers',
  '/api/v1/admin/sponsorship/offers/{offer_id}/assign':
      '/api/v2/admin/sponsorship/offers/{offer_id}/assign',
  '/api/v1/admin/sponsorship/offers/{offer_id}/rule':
      '/api/v2/admin/sponsorship/offers/{offer_id}/rule',
  '/api/v1/admin/sponsorship/packages': '/api/v2/admin/sponsorship/packages',
  '/api/v1/admin/story-feed': '/api/v2/admin/story-feed',
  '/api/v1/admin/streamer-tournaments/policy':
      '/api/v2/admin/streamer-tournaments/policy',
  '/api/v1/admin/streamer-tournaments/risk-signals':
      '/api/v2/admin/streamer-tournaments/risk-signals',
  '/api/v1/admin/streamer-tournaments/risk-signals/{signal_id}/review':
      '/api/v2/admin/streamer-tournaments/risk-signals/{signal_id}/review',
  '/api/v1/admin/streamer-tournaments/{tournament_id}/review':
      '/api/v2/admin/streamer-tournaments/{tournament_id}/review',
  '/api/v1/admin/streamer-tournaments/{tournament_id}/settle':
      '/api/v2/admin/streamer-tournaments/{tournament_id}/settle',
  '/api/v1/admin/treasury/bank-accounts':
      '/api/v2/admin/treasury/bank-accounts',
  '/api/v1/admin/treasury/bank-accounts/{account_id}':
      '/api/v2/admin/treasury/bank-accounts/{account_id}',
  '/api/v1/admin/treasury/dashboard': '/api/v2/admin/treasury/dashboard',
  '/api/v1/admin/treasury/deposits': '/api/v2/admin/treasury/deposits',
  '/api/v1/admin/treasury/deposits/{deposit_id}/confirm':
      '/api/v2/admin/treasury/deposits/{deposit_id}/confirm',
  '/api/v1/admin/treasury/deposits/{deposit_id}/reject':
      '/api/v2/admin/treasury/deposits/{deposit_id}/reject',
  '/api/v1/admin/treasury/deposits/{deposit_id}/review':
      '/api/v2/admin/treasury/deposits/{deposit_id}/review',
  '/api/v1/admin/treasury/disputes': '/api/v2/admin/treasury/disputes',
  '/api/v1/admin/treasury/disputes/{dispute_id}':
      '/api/v2/admin/treasury/disputes/{dispute_id}',
  '/api/v1/admin/treasury/disputes/{dispute_id}/messages':
      '/api/v2/admin/treasury/disputes/{dispute_id}/messages',
  '/api/v1/admin/treasury/kyc': '/api/v2/admin/treasury/kyc',
  '/api/v1/admin/treasury/kyc/{profile_id}/review':
      '/api/v2/admin/treasury/kyc/{profile_id}/review',
  '/api/v1/admin/treasury/settings': '/api/v2/admin/treasury/settings',
  '/api/v1/admin/treasury/withdrawal-batches':
      '/api/v2/admin/treasury/withdrawal-batches',
  '/api/v1/admin/treasury/withdrawals': '/api/v2/admin/treasury/withdrawals',
  '/api/v1/admin/treasury/withdrawals/{withdrawal_id}/reviews':
      '/api/v2/admin/treasury/withdrawals/{withdrawal_id}/reviews',
  '/api/v1/admin/treasury/withdrawals/{withdrawal_id}/status':
      '/api/v2/admin/treasury/withdrawals/{withdrawal_id}/status',
  '/api/v1/admin/wallets/market-topups': '/api/v2/admin/wallets/market-topups',
  '/api/v1/admin/wallets/market-topups/quote':
      '/api/v2/admin/wallets/market-topups/quote',
  '/api/v1/admin/wallets/market-topups/{topup_id}/status':
      '/api/v2/admin/wallets/market-topups/{topup_id}/status',
  '/api/v1/admin/wallets/purchase-orders':
      '/api/v2/admin/wallets/purchase-orders',
  '/api/v1/admin/wallets/purchase-orders/{order_id}/status':
      '/api/v2/admin/wallets/purchase-orders/{order_id}/status',
  '/api/v1/admin/world/clubs/{club_id}/context':
      '/api/v2/admin/world/clubs/{club_id}/context',
  '/api/v1/admin/world/cultures/{culture_key}':
      '/api/v2/admin/world/cultures/{culture_key}',
  '/api/v1/admin/world/narratives/{narrative_slug}':
      '/api/v2/admin/world/narratives/{narrative_slug}',
  '/api/v1/ads/create': '/api/v2/ads/create',
  '/api/v1/ads/performance': '/api/v2/ads/performance',
  '/api/v1/agents': '/api/v2/agents',
  '/api/v1/agents/config': '/api/v2/agents/config',
  '/api/v1/agents/performance': '/api/v2/agents/performance',
  '/api/v1/agents/run': '/api/v2/agents/run',
  '/api/v1/agents/summary': '/api/v2/agents/summary',
  '/api/v1/ai-manager/autopilot/live-decision':
      '/api/v2/ai-manager/autopilot/live-decision',
  '/api/v1/ai-manager/autopilot/run': '/api/v2/ai-manager/autopilot/run',
  '/api/v1/ai-manager/economy/reward-preview':
      '/api/v2/ai-manager/economy/reward-preview',
  '/api/v1/ai-manager/profiles/{club_id}':
      '/api/v2/ai-manager/profiles/{club_id}',
  '/api/v1/ai-reporter/feed': '/api/v2/ai-reporter/feed',
  '/api/v1/ai-reporter/run': '/api/v2/ai-reporter/run',
  '/api/v1/ai/leagues': '/api/v2/ai/leagues',
  '/api/v1/ai/match/{match_id}': '/api/v2/ai/match/{match_id}',
  '/api/v1/analytics/clip/{clip_id}': '/api/v2/analytics/clip/{clip_id}',
  '/api/v1/analytics/dashboard/drop-off':
      '/api/v2/analytics/dashboard/drop-off',
  '/api/v1/analytics/dashboard/top-clips':
      '/api/v2/analytics/dashboard/top-clips',
  '/api/v1/analytics/device-fingerprint':
      '/api/v2/analytics/device-fingerprint',
  '/api/v1/analytics/events': '/api/v2/analytics/events',
  '/api/v1/analytics/frontend': '/api/v2/analytics/frontend',
  '/api/v1/analytics/influencer-leaderboard':
      '/api/v2/analytics/influencer-leaderboard',
  '/api/v1/attachments': '/api/v2/attachments',
  '/api/v1/attachments/{attachment_id}': '/api/v2/attachments/{attachment_id}',
  '/api/v1/auth/change-password': '/api/v2/auth/change-password',
  '/api/v1/auth/confirm-email': '/api/v2/auth/confirm-email',
  '/api/v1/auth/login': '/api/v2/auth/login',
  '/api/v1/auth/logout': '/api/v2/auth/logout',
  '/api/v1/auth/me': '/api/v2/auth/me',
  '/api/v1/auth/recovery/request': '/api/v2/auth/recovery/request',
  '/api/v1/auth/recovery/reset': '/api/v2/auth/recovery/reset',
  '/api/v1/auth/refresh': '/api/v2/auth/refresh',
  '/api/v1/auth/signup/creator': '/api/v2/auth/signup/creator',
  '/api/v1/auth/signup/trader': '/api/v2/auth/signup/trader',
  '/api/v1/auth/signup/user': '/api/v2/auth/signup/user',
  '/api/v1/awards/categories': '/api/v2/awards/categories',
  '/api/v1/awards/ceremony': '/api/v2/awards/ceremony',
  '/api/v1/awards/ceremony/tickets': '/api/v2/awards/ceremony/tickets',
  '/api/v1/awards/ceremony/vote': '/api/v2/awards/ceremony/vote',
  '/api/v1/awards/nominees': '/api/v2/awards/nominees',
  '/api/v1/awards/winners': '/api/v2/awards/winners',
  '/api/v1/bank-accounts': '/api/v2/bank-accounts',
  '/api/v1/bank-accounts/{bank_account_id}':
      '/api/v2/bank-accounts/{bank_account_id}',
  '/api/v1/bets/history': '/api/v2/bets/history',
  '/api/v1/bets/odds/{match_id}': '/api/v2/bets/odds/{match_id}',
  '/api/v1/bets/place': '/api/v2/bets/place',
  '/api/v1/bets/preferences': '/api/v2/bets/preferences',
  '/api/v1/broadcast-rights/auctions/{auction_id}/bids':
      '/api/v2/broadcast-rights/auctions/{auction_id}/bids',
  '/api/v1/broadcast-rights/competitions/{competition_id}':
      '/api/v2/broadcast-rights/competitions/{competition_id}',
  '/api/v1/broadcast-rights/competitions/{competition_id}/acquire':
      '/api/v2/broadcast-rights/competitions/{competition_id}/acquire',
  '/api/v1/broadcast-rights/competitions/{competition_id}/auctions':
      '/api/v2/broadcast-rights/competitions/{competition_id}/auctions',
  '/api/v1/broadcast-rights/matches/{match_id}/access':
      '/api/v2/broadcast-rights/matches/{match_id}/access',
  '/api/v1/broadcast-rights/matches/{match_id}/distribute':
      '/api/v2/broadcast-rights/matches/{match_id}/distribute',
  '/api/v1/broadcast-rights/{right_id}/grants':
      '/api/v2/broadcast-rights/{right_id}/grants',
  '/api/v1/broadcast/channels': '/api/v2/broadcast/channels',
  '/api/v1/broadcast/channels/{channel_id}/audio/stems/stream':
      '/api/v2/broadcast/channels/{channel_id}/audio/stems/stream',
  '/api/v1/broadcast/channels/{channel_id}/join':
      '/api/v2/broadcast/channels/{channel_id}/join',
  '/api/v1/broadcast/channels/{channel_id}/stream':
      '/api/v2/broadcast/channels/{channel_id}/stream',
  '/api/v1/broadcast/home': '/api/v2/broadcast/home',
  '/api/v1/broadcast/{match_id}': '/api/v2/broadcast/{match_id}',
  '/api/v1/calendar-engine/dashboard': '/api/v2/calendar-engine/dashboard',
  '/api/v1/calendar-engine/events': '/api/v2/calendar-engine/events',
  '/api/v1/calendar-engine/lifecycle-runs':
      '/api/v2/calendar-engine/lifecycle-runs',
  '/api/v1/calendar-engine/pause-status':
      '/api/v2/calendar-engine/pause-status',
  '/api/v1/calendar-engine/seasons': '/api/v2/calendar-engine/seasons',
  '/api/v1/campaigns': '/api/v2/campaigns',
  '/api/v1/campaigns/create': '/api/v2/campaigns/create',
  '/api/v1/campaigns/{id}/accept': '/api/v2/campaigns/{id}/accept',
  '/api/v1/campaigns/{id}/apply': '/api/v2/campaigns/{id}/apply',
  '/api/v1/campaigns/{id}/performance': '/api/v2/campaigns/{id}/performance',
  '/api/v1/career/create': '/api/v2/career/create',
  '/api/v1/career/retire': '/api/v2/career/retire',
  '/api/v1/career/train': '/api/v2/career/train',
  '/api/v1/career/transfer': '/api/v2/career/transfer',
  '/api/v1/career/{user_id}': '/api/v2/career/{user_id}',
  '/api/v1/challenges/links/{link_code}':
      '/api/v2/challenges/links/{link_code}',
  '/api/v1/challenges/{challenge_id}': '/api/v2/challenges/{challenge_id}',
  '/api/v1/challenges/{challenge_id}/accept':
      '/api/v2/challenges/{challenge_id}/accept',
  '/api/v1/challenges/{challenge_id}/links':
      '/api/v2/challenges/{challenge_id}/links',
  '/api/v1/challenges/{challenge_id}/publish':
      '/api/v2/challenges/{challenge_id}/publish',
  '/api/v1/challenges/{challenge_id}/share-events':
      '/api/v2/challenges/{challenge_id}/share-events',
  '/api/v1/champions-league/knockout-bracket':
      '/api/v2/champions-league/knockout-bracket',
  '/api/v1/champions-league/league-phase/table':
      '/api/v2/champions-league/league-phase/table',
  '/api/v1/champions-league/playoff-bracket':
      '/api/v2/champions-league/playoff-bracket',
  '/api/v1/champions-league/prize-pool/preview':
      '/api/v2/champions-league/prize-pool/preview',
  '/api/v1/champions-league/qualification-map':
      '/api/v2/champions-league/qualification-map',
  '/api/v1/club-infra/clubs/{club_id}': '/api/v2/club-infra/clubs/{club_id}',
  '/api/v1/club-infra/clubs/{club_id}/support':
      '/api/v2/club-infra/clubs/{club_id}/support',
  '/api/v1/club-infra/my': '/api/v2/club-infra/my',
  '/api/v1/club-infra/my/facilities/upgrade':
      '/api/v2/club-infra/my/facilities/upgrade',
  '/api/v1/club-infra/my/stadium/upgrade':
      '/api/v2/club-infra/my/stadium/upgrade',
  '/api/v1/club/identity': '/api/v2/club/identity',
  '/api/v1/clubs': '/api/v2/clubs',
  '/api/v1/clubs/catalog': '/api/v2/clubs/catalog',
  '/api/v1/clubs/catalog/purchase': '/api/v2/clubs/catalog/purchase',
  '/api/v1/clubs/marketplace': '/api/v2/clubs/marketplace',
  '/api/v1/clubs/sale-market/listings': '/api/v2/clubs/sale-market/listings',
  '/api/v1/clubs/{club_id}': '/api/v2/clubs/{club_id}',
  '/api/v1/clubs/{club_id}/academy': '/api/v2/clubs/{club_id}/academy',
  '/api/v1/clubs/{club_id}/academy/players':
      '/api/v2/clubs/{club_id}/academy/players',
  '/api/v1/clubs/{club_id}/academy/players/{player_id}':
      '/api/v2/clubs/{club_id}/academy/players/{player_id}',
  '/api/v1/clubs/{club_id}/academy/programs':
      '/api/v2/clubs/{club_id}/academy/programs',
  '/api/v1/clubs/{club_id}/academy/training-cycles':
      '/api/v2/clubs/{club_id}/academy/training-cycles',
  '/api/v1/clubs/{club_id}/badge': '/api/v2/clubs/{club_id}/badge',
  '/api/v1/clubs/{club_id}/branding': '/api/v2/clubs/{club_id}/branding',
  '/api/v1/clubs/{club_id}/buy-tokens': '/api/v2/clubs/{club_id}/buy-tokens',
  '/api/v1/clubs/{club_id}/challenges': '/api/v2/clubs/{club_id}/challenges',
  '/api/v1/clubs/{club_id}/contracts': '/api/v2/clubs/{club_id}/contracts',
  '/api/v1/clubs/{club_id}/dynasty': '/api/v2/clubs/{club_id}/dynasty',
  '/api/v1/clubs/{club_id}/dynasty/history':
      '/api/v2/clubs/{club_id}/dynasty/history',
  '/api/v1/clubs/{club_id}/eras': '/api/v2/clubs/{club_id}/eras',
  '/api/v1/clubs/{club_id}/finances': '/api/v2/clubs/{club_id}/finances',
  '/api/v1/clubs/{club_id}/finances/budget':
      '/api/v2/clubs/{club_id}/finances/budget',
  '/api/v1/clubs/{club_id}/finances/cashflow':
      '/api/v2/clubs/{club_id}/finances/cashflow',
  '/api/v1/clubs/{club_id}/finances/ledger':
      '/api/v2/clubs/{club_id}/finances/ledger',
  '/api/v1/clubs/{club_id}/honors-timeline':
      '/api/v2/clubs/{club_id}/honors-timeline',
  '/api/v1/clubs/{club_id}/identity': '/api/v2/clubs/{club_id}/identity',
  '/api/v1/clubs/{club_id}/identity/metrics':
      '/api/v2/clubs/{club_id}/identity/metrics',
  '/api/v1/clubs/{club_id}/identity/metrics/refresh':
      '/api/v2/clubs/{club_id}/identity/metrics/refresh',
  '/api/v1/clubs/{club_id}/jerseys': '/api/v2/clubs/{club_id}/jerseys',
  '/api/v1/clubs/{club_id}/jerseys/{jersey_id}':
      '/api/v2/clubs/{club_id}/jerseys/{jersey_id}',
  '/api/v1/clubs/{club_id}/ownership': '/api/v2/clubs/{club_id}/ownership',
  '/api/v1/clubs/{club_id}/prestige': '/api/v2/clubs/{club_id}/prestige',
  '/api/v1/clubs/{club_id}/proposals': '/api/v2/clubs/{club_id}/proposals',
  '/api/v1/clubs/{club_id}/purchases': '/api/v2/clubs/{club_id}/purchases',
  '/api/v1/clubs/{club_id}/reputation': '/api/v2/clubs/{club_id}/reputation',
  '/api/v1/clubs/{club_id}/reputation/history':
      '/api/v2/clubs/{club_id}/reputation/history',
  '/api/v1/clubs/{club_id}/rivalries': '/api/v2/clubs/{club_id}/rivalries',
  '/api/v1/clubs/{club_id}/rivalries/{opponent_club_id}':
      '/api/v2/clubs/{club_id}/rivalries/{opponent_club_id}',
  '/api/v1/clubs/{club_id}/sale-market': '/api/v2/clubs/{club_id}/sale-market',
  '/api/v1/clubs/{club_id}/sale-market/assistant':
      '/api/v2/clubs/{club_id}/sale-market/assistant',
  '/api/v1/clubs/{club_id}/sale-market/history':
      '/api/v2/clubs/{club_id}/sale-market/history',
  '/api/v1/clubs/{club_id}/sale-market/inquiries':
      '/api/v2/clubs/{club_id}/sale-market/inquiries',
  '/api/v1/clubs/{club_id}/sale-market/inquiries/{inquiry_id}/respond':
      '/api/v2/clubs/{club_id}/sale-market/inquiries/{inquiry_id}/respond',
  '/api/v1/clubs/{club_id}/sale-market/listing':
      '/api/v2/clubs/{club_id}/sale-market/listing',
  '/api/v1/clubs/{club_id}/sale-market/listing/cancel':
      '/api/v2/clubs/{club_id}/sale-market/listing/cancel',
  '/api/v1/clubs/{club_id}/sale-market/listing/instant-sell':
      '/api/v2/clubs/{club_id}/sale-market/listing/instant-sell',
  '/api/v1/clubs/{club_id}/sale-market/offers':
      '/api/v2/clubs/{club_id}/sale-market/offers',
  '/api/v1/clubs/{club_id}/sale-market/offers/{offer_id}/accept':
      '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/accept',
  '/api/v1/clubs/{club_id}/sale-market/offers/{offer_id}/counter':
      '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/counter',
  '/api/v1/clubs/{club_id}/sale-market/offers/{offer_id}/reject':
      '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/reject',
  '/api/v1/clubs/{club_id}/sale-market/transfer':
      '/api/v2/clubs/{club_id}/sale-market/transfer',
  '/api/v1/clubs/{club_id}/scouting': '/api/v2/clubs/{club_id}/scouting',
  '/api/v1/clubs/{club_id}/scouting-intelligence/academy-supply-signals':
      '/api/v2/clubs/{club_id}/scouting-intelligence/academy-supply-signals',
  '/api/v1/clubs/{club_id}/scouting-intelligence/assignments':
      '/api/v2/clubs/{club_id}/scouting-intelligence/assignments',
  '/api/v1/clubs/{club_id}/scouting-intelligence/badges':
      '/api/v2/clubs/{club_id}/scouting-intelligence/badges',
  '/api/v1/clubs/{club_id}/scouting-intelligence/lifecycle':
      '/api/v2/clubs/{club_id}/scouting-intelligence/lifecycle',
  '/api/v1/clubs/{club_id}/scouting-intelligence/manager-profiles':
      '/api/v2/clubs/{club_id}/scouting-intelligence/manager-profiles',
  '/api/v1/clubs/{club_id}/scouting-intelligence/missions':
      '/api/v2/clubs/{club_id}/scouting-intelligence/missions',
  '/api/v1/clubs/{club_id}/scouting-intelligence/missions/{mission_id}':
      '/api/v2/clubs/{club_id}/scouting-intelligence/missions/{mission_id}',
  '/api/v1/clubs/{club_id}/scouting-intelligence/missions/{mission_id}/complete':
      '/api/v2/clubs/{club_id}/scouting-intelligence/missions/{mission_id}/complete',
  '/api/v1/clubs/{club_id}/scouting-intelligence/networks':
      '/api/v2/clubs/{club_id}/scouting-intelligence/networks',
  '/api/v1/clubs/{club_id}/scouting-intelligence/planning':
      '/api/v2/clubs/{club_id}/scouting-intelligence/planning',
  '/api/v1/clubs/{club_id}/scouting/assignments':
      '/api/v2/clubs/{club_id}/scouting/assignments',
  '/api/v1/clubs/{club_id}/scouting/prospects':
      '/api/v2/clubs/{club_id}/scouting/prospects',
  '/api/v1/clubs/{club_id}/scouting/prospects/{prospect_id}':
      '/api/v2/clubs/{club_id}/scouting/prospects/{prospect_id}',
  '/api/v1/clubs/{club_id}/season-honors':
      '/api/v2/clubs/{club_id}/season-honors',
  '/api/v1/clubs/{club_id}/sell-tokens': '/api/v2/clubs/{club_id}/sell-tokens',
  '/api/v1/clubs/{club_id}/showcase': '/api/v2/clubs/{club_id}/showcase',
  '/api/v1/clubs/{club_id}/sponsorships':
      '/api/v2/clubs/{club_id}/sponsorships',
  '/api/v1/clubs/{club_id}/sponsorships/assets':
      '/api/v2/clubs/{club_id}/sponsorships/assets',
  '/api/v1/clubs/{club_id}/sponsorships/catalog':
      '/api/v2/clubs/{club_id}/sponsorships/catalog',
  '/api/v1/clubs/{club_id}/sponsorships/contracts':
      '/api/v2/clubs/{club_id}/sponsorships/contracts',
  '/api/v1/clubs/{club_id}/sponsorships/contracts/{contract_id}':
      '/api/v2/clubs/{club_id}/sponsorships/contracts/{contract_id}',
  '/api/v1/clubs/{club_id}/treasury': '/api/v2/clubs/{club_id}/treasury',
  '/api/v1/clubs/{club_id}/trophies': '/api/v2/clubs/{club_id}/trophies',
  '/api/v1/clubs/{club_id}/trophy-cabinet':
      '/api/v2/clubs/{club_id}/trophy-cabinet',
  '/api/v1/clubs/{club_id}/valuation': '/api/v2/clubs/{club_id}/valuation',
  '/api/v1/clubs/{club_id}/vote': '/api/v2/clubs/{club_id}/vote',
  '/api/v1/clubs/{club_id}/youth-pipeline':
      '/api/v2/clubs/{club_id}/youth-pipeline',
  '/api/v1/commentary/profiles': '/api/v2/commentary/profiles',
  '/api/v1/commentary/select': '/api/v2/commentary/select',
  '/api/v1/community/creator-clubs/{club_id}/fan-competitions':
      '/api/v2/community/creator-clubs/{club_id}/fan-competitions',
  '/api/v1/community/creator-clubs/{club_id}/fan-groups':
      '/api/v2/community/creator-clubs/{club_id}/fan-groups',
  '/api/v1/community/creator-clubs/{club_id}/fan-state':
      '/api/v2/community/creator-clubs/{club_id}/fan-state',
  '/api/v1/community/creator-clubs/{club_id}/follow':
      '/api/v2/community/creator-clubs/{club_id}/follow',
  '/api/v1/community/creator-matches/{match_id}/chat-room':
      '/api/v2/community/creator-matches/{match_id}/chat-room',
  '/api/v1/community/creator-matches/{match_id}/chat-room/messages':
      '/api/v2/community/creator-matches/{match_id}/chat-room/messages',
  '/api/v1/community/creator-matches/{match_id}/fan-wall':
      '/api/v2/community/creator-matches/{match_id}/fan-wall',
  '/api/v1/community/creator-matches/{match_id}/rivalry-signals':
      '/api/v2/community/creator-matches/{match_id}/rivalry-signals',
  '/api/v1/community/creator-matches/{match_id}/tactical-advice':
      '/api/v2/community/creator-matches/{match_id}/tactical-advice',
  '/api/v1/community/digest': '/api/v2/community/digest',
  '/api/v1/community/fan-competitions/{fan_competition_id}/join':
      '/api/v2/community/fan-competitions/{fan_competition_id}/join',
  '/api/v1/community/fan-groups/{group_id}/join':
      '/api/v2/community/fan-groups/{group_id}/join',
  '/api/v1/community/live-threads': '/api/v2/community/live-threads',
  '/api/v1/community/live-threads/{thread_id}':
      '/api/v2/community/live-threads/{thread_id}',
  '/api/v1/community/live-threads/{thread_id}/messages':
      '/api/v2/community/live-threads/{thread_id}/messages',
  '/api/v1/community/private-messages/threads':
      '/api/v2/community/private-messages/threads',
  '/api/v1/community/private-messages/threads/{thread_id}':
      '/api/v2/community/private-messages/threads/{thread_id}',
  '/api/v1/community/private-messages/threads/{thread_id}/messages':
      '/api/v2/community/private-messages/threads/{thread_id}/messages',
  '/api/v1/community/watchlist': '/api/v2/community/watchlist',
  '/api/v1/community/watchlist/{competition_key}':
      '/api/v2/community/watchlist/{competition_key}',
  '/api/v1/competitions': '/api/v2/competitions',
  '/api/v1/competitions/admin': '/api/v2/competitions/admin',
  '/api/v1/competitions/admin/{code}': '/api/v2/competitions/admin/{code}',
  '/api/v1/competitions/admin/{code}/orchestrate':
      '/api/v2/competitions/admin/{code}/orchestrate',
  '/api/v1/competitions/create': '/api/v2/competitions/create',
  '/api/v1/competitions/join': '/api/v2/competitions/join',
  '/api/v1/competitions/players/{subject_id}/progression':
      '/api/v2/competitions/players/{subject_id}/progression',
  '/api/v1/competitions/records/{competition_id}':
      '/api/v2/competitions/records/{competition_id}',
  '/api/v1/competitions/runtime/{code}': '/api/v2/competitions/runtime/{code}',
  '/api/v1/competitions/{competition_id}':
      '/api/v2/competitions/{competition_id}',
  '/api/v1/competitions/{competition_id}/advance':
      '/api/v2/competitions/{competition_id}/advance',
  '/api/v1/competitions/{competition_id}/finalize':
      '/api/v2/competitions/{competition_id}/finalize',
  '/api/v1/competitions/{competition_id}/financials':
      '/api/v2/competitions/{competition_id}/financials',
  '/api/v1/competitions/{competition_id}/fixtures':
      '/api/v2/competitions/{competition_id}/fixtures',
  '/api/v1/competitions/{competition_id}/invites':
      '/api/v2/competitions/{competition_id}/invites',
  '/api/v1/competitions/{competition_id}/invites/accept':
      '/api/v2/competitions/{competition_id}/invites/accept',
  '/api/v1/competitions/{competition_id}/join':
      '/api/v2/competitions/{competition_id}/join',
  '/api/v1/competitions/{competition_id}/launch':
      '/api/v2/competitions/{competition_id}/launch',
  '/api/v1/competitions/{competition_id}/leave':
      '/api/v2/competitions/{competition_id}/leave',
  '/api/v1/competitions/{competition_id}/matches/{match_id}/events':
      '/api/v2/competitions/{competition_id}/matches/{match_id}/events',
  '/api/v1/competitions/{competition_id}/matches/{match_id}/result':
      '/api/v2/competitions/{competition_id}/matches/{match_id}/result',
  '/api/v1/competitions/{competition_id}/publish':
      '/api/v2/competitions/{competition_id}/publish',
  '/api/v1/competitions/{competition_id}/rewards':
      '/api/v2/competitions/{competition_id}/rewards',
  '/api/v1/competitions/{competition_id}/rounds':
      '/api/v2/competitions/{competition_id}/rounds',
  '/api/v1/competitions/{competition_id}/schedule/jobs':
      '/api/v2/competitions/{competition_id}/schedule/jobs',
  '/api/v1/competitions/{competition_id}/schedule/jobs/{job_id}':
      '/api/v2/competitions/{competition_id}/schedule/jobs/{job_id}',
  '/api/v1/competitions/{competition_id}/schedule/preview':
      '/api/v2/competitions/{competition_id}/schedule/preview',
  '/api/v1/competitions/{competition_id}/seed':
      '/api/v2/competitions/{competition_id}/seed',
  '/api/v1/competitions/{competition_id}/standings':
      '/api/v2/competitions/{competition_id}/standings',
  '/api/v1/competitions/{competition_id}/summary':
      '/api/v2/competitions/{competition_id}/summary',
  '/api/v1/competitive-integrity/fast-game/runs':
      '/api/v2/competitive-integrity/fast-game/runs',
  '/api/v1/competitive-integrity/fast-game/runs/{run_id}':
      '/api/v2/competitive-integrity/fast-game/runs/{run_id}',
  '/api/v1/competitive-integrity/fast-game/runs/{run_id}/play':
      '/api/v2/competitive-integrity/fast-game/runs/{run_id}/play',
  '/api/v1/competitive-integrity/managers':
      '/api/v2/competitive-integrity/managers',
  '/api/v1/competitive-integrity/managers/candidates':
      '/api/v2/competitive-integrity/managers/candidates',
  '/api/v1/competitive-integrity/managers/{manager_id}/instructions':
      '/api/v2/competitive-integrity/managers/{manager_id}/instructions',
  '/api/v1/competitive-integrity/matches':
      '/api/v2/competitive-integrity/matches',
  '/api/v1/competitive-integrity/matches/{match_id}':
      '/api/v2/competitive-integrity/matches/{match_id}',
  '/api/v1/competitive-integrity/matches/{match_id}/execute':
      '/api/v2/competitive-integrity/matches/{match_id}/execute',
  '/api/v1/competitive-integrity/notifications/events':
      '/api/v2/competitive-integrity/notifications/events',
  '/api/v1/config/current': '/api/v2/config/current',
  '/api/v1/config/update': '/api/v2/config/update',
  '/api/v1/conversations': '/api/v2/conversations',
  '/api/v1/conversations/start': '/api/v2/conversations/start',
  '/api/v1/conversations/{conversation_id}/message':
      '/api/v2/conversations/{conversation_id}/message',
  '/api/v1/conversations/{conversation_id}/messages':
      '/api/v2/conversations/{conversation_id}/messages',
  '/api/v1/conversations/{conversation_id}/status':
      '/api/v2/conversations/{conversation_id}/status',
  '/api/v1/creator-campaigns': '/api/v2/creator-campaigns',
  '/api/v1/creator-campaigns/me': '/api/v2/creator-campaigns/me',
  '/api/v1/creator-campaigns/{campaign_id}':
      '/api/v2/creator-campaigns/{campaign_id}',
  '/api/v1/creator-campaigns/{campaign_id}/metrics':
      '/api/v2/creator-campaigns/{campaign_id}/metrics',
  '/api/v1/creator-campaigns/{campaign_id}/snapshot':
      '/api/v2/creator-campaigns/{campaign_id}/snapshot',
  '/api/v1/creator-campaigns/{campaign_id}/snapshots':
      '/api/v2/creator-campaigns/{campaign_id}/snapshots',
  '/api/v1/creator-league': '/api/v2/creator-league',
  '/api/v1/creator-league/config': '/api/v2/creator-league/config',
  '/api/v1/creator-league/financial-report':
      '/api/v2/creator-league/financial-report',
  '/api/v1/creator-league/financial-settlements':
      '/api/v2/creator-league/financial-settlements',
  '/api/v1/creator-league/financial-settlements/{settlement_id}/approve':
      '/api/v2/creator-league/financial-settlements/{settlement_id}/approve',
  '/api/v1/creator-league/live-priority':
      '/api/v2/creator-league/live-priority',
  '/api/v1/creator-league/reset': '/api/v2/creator-league/reset',
  '/api/v1/creator-league/season-tiers/{season_tier_id}/standings':
      '/api/v2/creator-league/season-tiers/{season_tier_id}/standings',
  '/api/v1/creator-league/seasons': '/api/v2/creator-league/seasons',
  '/api/v1/creator-league/seasons/{season_id}':
      '/api/v2/creator-league/seasons/{season_id}',
  '/api/v1/creator-league/seasons/{season_id}/pause':
      '/api/v2/creator-league/seasons/{season_id}/pause',
  '/api/v1/creator-league/tiers': '/api/v2/creator-league/tiers',
  '/api/v1/creator-league/tiers/{tier_id}':
      '/api/v2/creator-league/tiers/{tier_id}',
  '/api/v1/creator/application': '/api/v2/creator/application',
  '/api/v1/creator/apply': '/api/v2/creator/apply',
  '/api/v1/creator/cards': '/api/v2/creator/cards',
  '/api/v1/creator/cards/listings': '/api/v2/creator/cards/listings',
  '/api/v1/creator/cards/listings/{listing_id}/buy':
      '/api/v2/creator/cards/listings/{listing_id}/buy',
  '/api/v1/creator/cards/loans/{loan_id}/return':
      '/api/v2/creator/cards/loans/{loan_id}/return',
  '/api/v1/creator/cards/swap': '/api/v2/creator/cards/swap',
  '/api/v1/creator/cards/{creator_card_id}/list':
      '/api/v2/creator/cards/{creator_card_id}/list',
  '/api/v1/creator/cards/{creator_card_id}/loan':
      '/api/v2/creator/cards/{creator_card_id}/loan',
  '/api/v1/creator/clubs/{club_id}/fan-share-market':
      '/api/v2/creator/clubs/{club_id}/fan-share-market',
  '/api/v1/creator/clubs/{club_id}/fan-share-market/distributions':
      '/api/v2/creator/clubs/{club_id}/fan-share-market/distributions',
  '/api/v1/creator/clubs/{club_id}/fan-share-market/holding':
      '/api/v2/creator/clubs/{club_id}/fan-share-market/holding',
  '/api/v1/creator/clubs/{club_id}/fan-share-market/purchase':
      '/api/v2/creator/clubs/{club_id}/fan-share-market/purchase',
  '/api/v1/creator/verify-email': '/api/v2/creator/verify-email',
  '/api/v1/creator/verify-phone': '/api/v2/creator/verify-phone',
  '/api/v1/creators/marketplace': '/api/v2/creators/marketplace',
  '/api/v1/creators/me/competitions': '/api/v2/creators/me/competitions',
  '/api/v1/creators/me/copilot/analyze': '/api/v2/creators/me/copilot/analyze',
  '/api/v1/creators/me/finance': '/api/v2/creators/me/finance',
  '/api/v1/creators/me/insights': '/api/v2/creators/me/insights',
  '/api/v1/creators/me/reputation': '/api/v2/creators/me/reputation',
  '/api/v1/creators/me/summary': '/api/v2/creators/me/summary',
  '/api/v1/creators/profile': '/api/v2/creators/profile',
  '/api/v1/creators/profile/me': '/api/v2/creators/profile/me',
  '/api/v1/creators/{handle}': '/api/v2/creators/{handle}',
  '/api/v1/daily-challenges': '/api/v2/daily-challenges',
  '/api/v1/daily-challenges/me': '/api/v2/daily-challenges/me',
  '/api/v1/daily-challenges/{challenge_key}/claim':
      '/api/v2/daily-challenges/{challenge_key}/claim',
  '/api/v1/diagnostics': '/api/v2/diagnostics',
  '/api/v1/discovery/home': '/api/v2/discovery/home',
  '/api/v1/discovery/saved-searches': '/api/v2/discovery/saved-searches',
  '/api/v1/discovery/saved-searches/{search_id}':
      '/api/v2/discovery/saved-searches/{search_id}',
  '/api/v1/discovery/search': '/api/v2/discovery/search',
  '/api/v1/disputes': '/api/v2/disputes',
  '/api/v1/disputes/me': '/api/v2/disputes/me',
  '/api/v1/disputes/{dispute_id}': '/api/v2/disputes/{dispute_id}',
  '/api/v1/disputes/{dispute_id}/messages':
      '/api/v2/disputes/{dispute_id}/messages',
  '/api/v1/dynasty': '/api/v2/dynasty',
  '/api/v1/dynasty/leaderboard': '/api/v2/dynasty/leaderboard',
  '/api/v1/economy/fx/quote': '/api/v2/economy/fx/quote',
  '/api/v1/economy/gift-catalog': '/api/v2/economy/gift-catalog',
  '/api/v1/economy/service-pricing': '/api/v2/economy/service-pricing',
  '/api/v1/engagement/achievements': '/api/v2/engagement/achievements',
  '/api/v1/engagement/achievements/me': '/api/v2/engagement/achievements/me',
  '/api/v1/engagement/milestones/me': '/api/v2/engagement/milestones/me',
  '/api/v1/engagement/sync': '/api/v2/engagement/sync',
  '/api/v1/enter': '/api/v2/enter',
  '/api/v1/events/clip': '/api/v2/events/clip',
  '/api/v1/events/today': '/api/v2/events/today',
  '/api/v1/events/upcoming': '/api/v2/events/upcoming',
  '/api/v1/experience/full-simulation': '/api/v2/experience/full-simulation',
  '/api/v1/fan-predictions/creator-clubs/{club_id}/leaderboards/weekly':
      '/api/v2/fan-predictions/creator-clubs/{club_id}/leaderboards/weekly',
  '/api/v1/fan-predictions/leaderboards/weekly':
      '/api/v2/fan-predictions/leaderboards/weekly',
  '/api/v1/fan-predictions/matches/{match_id}':
      '/api/v2/fan-predictions/matches/{match_id}',
  '/api/v1/fan-predictions/matches/{match_id}/leaderboard':
      '/api/v2/fan-predictions/matches/{match_id}/leaderboard',
  '/api/v1/fan-predictions/matches/{match_id}/submissions':
      '/api/v2/fan-predictions/matches/{match_id}/submissions',
  '/api/v1/fan-predictions/me/submissions':
      '/api/v2/fan-predictions/me/submissions',
  '/api/v1/fan-predictions/me/tokens': '/api/v2/fan-predictions/me/tokens',
  '/api/v1/fan-wars/leaderboards/{board_type}':
      '/api/v2/fan-wars/leaderboards/{board_type}',
  '/api/v1/fan-wars/nations-cup/{competition_id}':
      '/api/v2/fan-wars/nations-cup/{competition_id}',
  '/api/v1/fan-wars/profiles/{profile_id}/dashboard':
      '/api/v2/fan-wars/profiles/{profile_id}/dashboard',
  '/api/v1/fan-wars/rivalries/{board_type}':
      '/api/v2/fan-wars/rivalries/{board_type}',
  '/api/v1/fans/profile': '/api/v2/fans/profile',
  '/api/v1/fans/tribe/join': '/api/v2/fans/tribe/join',
  '/api/v1/fans/{club_id}': '/api/v2/fans/{club_id}',
  '/api/v1/fast-cups/upcoming': '/api/v2/fast-cups/upcoming',
  '/api/v1/fast-cups/{cup_id}/bracket': '/api/v2/fast-cups/{cup_id}/bracket',
  '/api/v1/fast-cups/{cup_id}/countdown':
      '/api/v2/fast-cups/{cup_id}/countdown',
  '/api/v1/fast-cups/{cup_id}/join': '/api/v2/fast-cups/{cup_id}/join',
  '/api/v1/fast-cups/{cup_id}/result-summary':
      '/api/v2/fast-cups/{cup_id}/result-summary',
  '/api/v1/federations': '/api/v2/federations',
  '/api/v1/federations/proposals/{proposal_id}/votes':
      '/api/v2/federations/proposals/{proposal_id}/votes',
  '/api/v1/federations/rankings': '/api/v2/federations/rankings',
  '/api/v1/federations/regional-tournaments':
      '/api/v2/federations/regional-tournaments',
  '/api/v1/federations/{federation_id}': '/api/v2/federations/{federation_id}',
  '/api/v1/federations/{federation_id}/governance':
      '/api/v2/federations/{federation_id}/governance',
  '/api/v1/federations/{federation_id}/leagues':
      '/api/v2/federations/{federation_id}/leagues',
  '/api/v1/federations/{federation_id}/memberships':
      '/api/v2/federations/{federation_id}/memberships',
  '/api/v1/federations/{federation_id}/narratives':
      '/api/v2/federations/{federation_id}/narratives',
  '/api/v1/federations/{federation_id}/proposals':
      '/api/v2/federations/{federation_id}/proposals',
  '/api/v1/federations/{federation_id}/sanctions':
      '/api/v2/federations/{federation_id}/sanctions',
  '/api/v1/federations/{federation_id}/treasury/distribute':
      '/api/v2/federations/{federation_id}/treasury/distribute',
  '/api/v1/federations/{federation_id}/validate-action':
      '/api/v2/federations/{federation_id}/validate-action',
  '/api/v1/feed/following': '/api/v2/feed/following',
  '/api/v1/feed/for-you': '/api/v2/feed/for-you',
  '/api/v1/feed/for-you/refresh': '/api/v2/feed/for-you/refresh',
  '/api/v1/feed/sponsored': '/api/v2/feed/sponsored',
  '/api/v1/finance': '/api/v2/finance',
  '/api/v1/follow/{user_id}': '/api/v2/follow/{user_id}',
  '/api/v1/football-events/players/{player_id}/events':
      '/api/v2/football-events/players/{player_id}/events',
  '/api/v1/football-events/players/{player_id}/impact':
      '/api/v2/football-events/players/{player_id}/impact',
  '/api/v1/gift-engine/me/combos': '/api/v2/gift-engine/me/combos',
  '/api/v1/gift-engine/me/summary': '/api/v2/gift-engine/me/summary',
  '/api/v1/gift-engine/me/transactions': '/api/v2/gift-engine/me/transactions',
  '/api/v1/gift-engine/send': '/api/v2/gift-engine/send',
  '/api/v1/governance/clubs/{club_id}/panel':
      '/api/v2/governance/clubs/{club_id}/panel',
  '/api/v1/governance/me/overview': '/api/v2/governance/me/overview',
  '/api/v1/governance/proposals': '/api/v2/governance/proposals',
  '/api/v1/governance/proposals/{proposal_id}':
      '/api/v2/governance/proposals/{proposal_id}',
  '/api/v1/governance/proposals/{proposal_id}/vote':
      '/api/v2/governance/proposals/{proposal_id}/vote',
  '/api/v1/gtex/market/buy': '/api/v2/gtex/market/buy',
  '/api/v1/gtex/market/sell': '/api/v2/gtex/market/sell',
  '/api/v1/hall-of-fame': '/api/v2/hall-of-fame',
  '/api/v1/health': '/health',
  '/api/v1/history/goat-rankings': '/api/v2/history/goat-rankings',
  '/api/v1/history/leaderboards': '/api/v2/history/leaderboards',
  '/api/v1/history/records': '/api/v2/history/records',
  '/api/v1/history/timeline/{subject_type}/{subject_id}':
      '/api/v2/history/timeline/{subject_type}/{subject_id}',
  '/api/v1/hosted-competitions': '/api/v2/hosted-competitions',
  '/api/v1/hosted-competitions/mine': '/api/v2/hosted-competitions/mine',
  '/api/v1/hosted-competitions/mine/invites':
      '/api/v2/hosted-competitions/mine/invites',
  '/api/v1/hosted-competitions/templates':
      '/api/v2/hosted-competitions/templates',
  '/api/v1/hosted-competitions/{competition_id}':
      '/api/v2/hosted-competitions/{competition_id}',
  '/api/v1/hosted-competitions/{competition_id}/finance':
      '/api/v2/hosted-competitions/{competition_id}/finance',
  '/api/v1/hosted-competitions/{competition_id}/invites':
      '/api/v2/hosted-competitions/{competition_id}/invites',
  '/api/v1/hosted-competitions/{competition_id}/invites/accept':
      '/api/v2/hosted-competitions/{competition_id}/invites/accept',
  '/api/v1/hosted-competitions/{competition_id}/join':
      '/api/v2/hosted-competitions/{competition_id}/join',
  '/api/v1/hosted-competitions/{competition_id}/launch':
      '/api/v2/hosted-competitions/{competition_id}/launch',
  '/api/v1/hosted-competitions/{competition_id}/standings':
      '/api/v2/hosted-competitions/{competition_id}/standings',
  '/api/v1/infinite-league/economy': '/api/v2/infinite-league/economy',
  '/api/v1/infinite-league/livestream': '/api/v2/infinite-league/livestream',
  '/api/v1/infinite-league/matches': '/api/v2/infinite-league/matches',
  '/api/v1/infinite-league/matches/{match_id}':
      '/api/v2/infinite-league/matches/{match_id}',
  '/api/v1/infinite-league/pundits/{match_id}':
      '/api/v2/infinite-league/pundits/{match_id}',
  '/api/v1/infinite-league/status': '/api/v2/infinite-league/status',
  '/api/v1/infinite-league/tick': '/api/v2/infinite-league/tick',
  '/api/v1/infinite-league/viral-feed': '/api/v2/infinite-league/viral-feed',
  '/api/v1/integrations/payments/korapay/webhook':
      '/api/v2/integrations/payments/korapay/webhook',
  '/api/v1/integrations/payments/methods':
      '/api/v2/integrations/payments/methods',
  '/api/v1/integrations/payments/orders':
      '/api/v2/integrations/payments/orders',
  '/api/v1/integrations/payments/paystack/webhook':
      '/api/v2/integrations/payments/paystack/webhook',
  '/api/v1/integrations/payments/quote': '/api/v2/integrations/payments/quote',
  '/api/v1/integrity-engine/me/incidents':
      '/api/v2/integrity-engine/me/incidents',
  '/api/v1/integrity-engine/me/score': '/api/v2/integrity-engine/me/score',
  '/api/v1/internal/ingestion/bootstrap-sync':
      '/api/v2/internal/ingestion/bootstrap-sync',
  '/api/v1/internal/ingestion/clubs/{club_external_id}/refresh':
      '/api/v2/internal/ingestion/clubs/{club_external_id}/refresh',
  '/api/v1/internal/ingestion/competitions/{competition_external_id}/refresh':
      '/api/v2/internal/ingestion/competitions/{competition_external_id}/refresh',
  '/api/v1/internal/ingestion/cursors/{provider_name}':
      '/api/v2/internal/ingestion/cursors/{provider_name}',
  '/api/v1/internal/ingestion/incremental-sync':
      '/api/v2/internal/ingestion/incremental-sync',
  '/api/v1/internal/ingestion/players/{player_external_id}/refresh':
      '/api/v2/internal/ingestion/players/{player_external_id}/refresh',
  '/api/v1/internal/ingestion/providers/{provider_name}/health':
      '/api/v2/internal/ingestion/providers/{provider_name}/health',
  '/api/v1/internal/ingestion/real-players/batches':
      '/api/v2/internal/ingestion/real-players/batches',
  '/api/v1/internal/ingestion/real-players/batches/{batch_id}':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}',
  '/api/v1/internal/ingestion/real-players/batches/{batch_id}/issues':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}/issues',
  '/api/v1/internal/ingestion/real-players/batches/{batch_id}/resume':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}/resume',
  '/api/v1/internal/ingestion/real-players/batches/{batch_id}/valuation-status':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}/valuation-status',
  '/api/v1/internal/ingestion/real-players/import':
      '/api/v2/internal/ingestion/real-players/import',
  '/api/v1/internal/ingestion/real-players/publish-jobs':
      '/api/v2/internal/ingestion/real-players/publish-jobs',
  '/api/v1/internal/ingestion/real-players/publish-jobs/{job_id}':
      '/api/v2/internal/ingestion/real-players/publish-jobs/{job_id}',
  '/api/v1/internal/ingestion/real-players/status':
      '/api/v2/internal/ingestion/real-players/status',
  '/api/v1/internal/ingestion/runs': '/api/v2/internal/ingestion/runs',
  '/api/v1/internal/ingestion/status': '/api/v2/internal/ingestion/status',
  '/api/v1/jackpot/contribute': '/api/v2/jackpot/contribute',
  '/api/v1/jackpot/history': '/api/v2/jackpot/history',
  '/api/v1/jackpot/state': '/api/v2/jackpot/state',
  '/api/v1/jobs/{job_id}': '/api/v2/jobs/{job_id}',
  '/api/v1/kyc': '/api/v2/kyc',
  '/api/v1/leaderboard/division/{division}':
      '/api/v2/leaderboard/division/{division}',
  '/api/v1/leaderboard/global': '/api/v2/leaderboard/global',
  '/api/v1/leaderboard/player/{player_id}':
      '/api/v2/leaderboard/player/{player_id}',
  '/api/v1/leaderboard/region/{region}': '/api/v2/leaderboard/region/{region}',
  '/api/v1/leaderboards/dynasties': '/api/v2/leaderboards/dynasties',
  '/api/v1/leaderboards/prestige': '/api/v2/leaderboards/prestige',
  '/api/v1/leaderboards/trophies': '/api/v2/leaderboards/trophies',
  '/api/v1/leagues/register': '/api/v2/leagues/register',
  '/api/v1/leagues/{season_id}/fixtures':
      '/api/v2/leagues/{season_id}/fixtures',
  '/api/v1/leagues/{season_id}/qualification-markers':
      '/api/v2/leagues/{season_id}/qualification-markers',
  '/api/v1/leagues/{season_id}/standings':
      '/api/v2/leagues/{season_id}/standings',
  '/api/v1/leagues/{season_id}/summary': '/api/v2/leagues/{season_id}/summary',
  '/api/v1/legacy/board': '/api/v2/legacy/board',
  '/api/v1/live-events': '/api/v2/live-events',
  '/api/v1/manager-duels': '/api/v2/manager-duels',
  '/api/v1/manager-duels/leaderboard': '/api/v2/manager-duels/leaderboard',
  '/api/v1/manager-duels/{duel_id}': '/api/v2/manager-duels/{duel_id}',
  '/api/v1/managers': '/api/v2/managers',
  '/api/v1/managers/assign': '/api/v2/managers/assign',
  '/api/v1/managers/catalog': '/api/v2/managers/catalog',
  '/api/v1/managers/compare': '/api/v2/managers/compare',
  '/api/v1/managers/competition-runtime/{code}':
      '/api/v2/managers/competition-runtime/{code}',
  '/api/v1/managers/create': '/api/v2/managers/create',
  '/api/v1/managers/filters': '/api/v2/managers/filters',
  '/api/v1/managers/history': '/api/v2/managers/history',
  '/api/v1/managers/leaderboard': '/api/v2/managers/leaderboard',
  '/api/v1/managers/my-trade-listings': '/api/v2/managers/my-trade-listings',
  '/api/v1/managers/recommendation': '/api/v2/managers/recommendation',
  '/api/v1/managers/recruit': '/api/v2/managers/recruit',
  '/api/v1/managers/swap': '/api/v2/managers/swap',
  '/api/v1/managers/team': '/api/v2/managers/team',
  '/api/v1/managers/trade-listings': '/api/v2/managers/trade-listings',
  '/api/v1/managers/trade-listings/{listing_id}/buy':
      '/api/v2/managers/trade-listings/{listing_id}/buy',
  '/api/v1/managers/trade-listings/{listing_id}/cancel':
      '/api/v2/managers/trade-listings/{listing_id}/cancel',
  '/api/v1/managers/{asset_id}/release': '/api/v2/managers/{asset_id}/release',
  '/api/v1/managers/{manager_id}': '/api/v2/managers/{manager_id}',
  '/api/v1/managers/{manager_id}/hire': '/api/v2/managers/{manager_id}/hire',
  '/api/v1/managers/{manager_id}/history':
      '/api/v2/managers/{manager_id}/history',
  '/api/v1/managers/{manager_id}/release':
      '/api/v2/managers/{manager_id}/release',
  '/api/v1/market/buy': '/api/v2/market/buy',
  '/api/v1/market/listings': '/api/v2/market/listings',
  '/api/v1/market/listings/{listing_id}/cancel':
      '/api/v2/market/listings/{listing_id}/cancel',
  '/api/v1/market/listings/{listing_id}/matches':
      '/api/v2/market/listings/{listing_id}/matches',
  '/api/v1/market/listings/{listing_id}/offers':
      '/api/v2/market/listings/{listing_id}/offers',
  '/api/v1/market/movers': '/api/v2/market/movers',
  '/api/v1/market/offers': '/api/v2/market/offers',
  '/api/v1/market/offers/{offer_id}/accept':
      '/api/v2/market/offers/{offer_id}/accept',
  '/api/v1/market/offers/{offer_id}/counter':
      '/api/v2/market/offers/{offer_id}/counter',
  '/api/v1/market/offers/{offer_id}/reject':
      '/api/v2/market/offers/{offer_id}/reject',
  '/api/v1/market/players': '/api/v2/market/players',
  '/api/v1/market/players/{player_id}': '/api/v2/market/players/{player_id}',
  '/api/v1/market/players/{player_id}/candles':
      '/api/v2/market/players/{player_id}/candles',
  '/api/v1/market/players/{player_id}/history':
      '/api/v2/market/players/{player_id}/history',
  '/api/v1/market/sell': '/api/v2/market/sell',
  '/api/v1/market/summary/{asset_id}': '/api/v2/market/summary/{asset_id}',
  '/api/v1/market/ticker/{player_id}': '/api/v2/market/ticker/{player_id}',
  '/api/v1/market/trade-intents': '/api/v2/market/trade-intents',
  '/api/v1/market/trade-intents/{intent_id}/withdraw':
      '/api/v2/market/trade-intents/{intent_id}/withdraw',
  '/api/v1/market/trending': '/api/v2/market/trending',
  '/api/v1/marketplace/my-players': '/api/v2/marketplace/my-players',
  '/api/v1/marketplace/players': '/api/v2/marketplace/players',
  '/api/v1/marketplace/players/{player_id}':
      '/api/v2/marketplace/players/{player_id}',
  '/api/v1/match-engine/analytics': '/api/v2/match-engine/analytics',
  '/api/v1/match-engine/analytics/{match_key}':
      '/api/v2/match-engine/analytics/{match_key}',
  '/api/v1/match-engine/highlights/{match_key}':
      '/api/v2/match-engine/highlights/{match_key}',
  '/api/v1/match-engine/live-feed/{match_key}':
      '/api/v2/match-engine/live-feed/{match_key}',
  '/api/v1/match-engine/render-sync': '/api/v2/match-engine/render-sync',
  '/api/v1/match-engine/render-sync/{match_key}':
      '/api/v2/match-engine/render-sync/{match_key}',
  '/api/v1/match-engine/replay': '/api/v2/match-engine/replay',
  '/api/v1/match-engine/simulate': '/api/v2/match-engine/simulate',
  '/api/v1/match-engine/summary': '/api/v2/match-engine/summary',
  '/api/v1/match-engine/timeline': '/api/v2/match-engine/timeline',
  '/api/v1/match-share-links/{share_code}':
      '/api/v2/match-share-links/{share_code}',
  '/api/v1/match-share-links/{share_code}/events':
      '/api/v2/match-share-links/{share_code}/events',
  '/api/v1/match-viewer/{match_key}': '/api/v2/match-viewer/{match_key}',
  '/api/v1/match-viewer/{match_key}/illusion':
      '/api/v2/match-viewer/{match_key}/illusion',
  '/api/v1/match-viewer/{match_key}/session':
      '/api/v2/match-viewer/{match_key}/session',
  '/api/v1/match/find': '/api/v2/match/find',
  '/api/v1/match/live/active': '/api/v2/match/live/active',
  '/api/v1/match/{match_id}/commentary/stream':
      '/api/v2/match/{match_id}/commentary/stream',
  '/api/v1/match/{match_id}/live': '/api/v2/match/{match_id}/live',
  '/api/v1/match/{match_id}/unity-access':
      '/api/v2/match/{match_id}/unity-access',
  '/api/v1/match/{match_id}/unity-access/refresh':
      '/api/v2/match/{match_id}/unity-access/refresh',
  '/api/v1/matches/complete': '/api/v2/matches/complete',
  '/api/v1/matches/live/active': '/api/v2/matches/live/active',
  '/api/v1/matches/start': '/api/v2/matches/start',
  '/api/v1/matches/{match_id}/analysis': '/api/v2/matches/{match_id}/analysis',
  '/api/v1/matches/{match_id}/audio/stems/stream':
      '/api/v2/matches/{match_id}/audio/stems/stream',
  '/api/v1/matches/{match_id}/chat': '/api/v2/matches/{match_id}/chat',
  '/api/v1/matches/{match_id}/chat/messages':
      '/api/v2/matches/{match_id}/chat/messages',
  '/api/v1/matches/{match_id}/commentary':
      '/api/v2/matches/{match_id}/commentary',
  '/api/v1/matches/{match_id}/commentary/stream':
      '/api/v2/matches/{match_id}/commentary/stream',
  '/api/v1/matches/{match_id}/fan-experience':
      '/api/v2/matches/{match_id}/fan-experience',
  '/api/v1/matches/{match_id}/highlights':
      '/api/v2/matches/{match_id}/highlights',
  '/api/v1/matches/{match_id}/highlights/share-package':
      '/api/v2/matches/{match_id}/highlights/share-package',
  '/api/v1/matches/{match_id}/live': '/api/v2/matches/{match_id}/live',
  '/api/v1/matches/{match_id}/live-reactions':
      '/api/v2/matches/{match_id}/live-reactions',
  '/api/v1/matches/{match_id}/reactions':
      '/api/v2/matches/{match_id}/reactions',
  '/api/v1/matches/{match_id}/replay': '/api/v2/matches/{match_id}/replay',
  '/api/v1/matches/{match_id}/share-links':
      '/api/v2/matches/{match_id}/share-links',
  '/api/v1/matches/{match_id}/social-warfare':
      '/api/v2/matches/{match_id}/social-warfare',
  '/api/v1/matches/{match_id}/spectate': '/api/v2/matches/{match_id}/spectate',
  '/api/v1/matches/{match_id}/spectators':
      '/api/v2/matches/{match_id}/spectators',
  '/api/v1/matches/{match_id}/stream': '/api/v2/matches/{match_id}/stream',
  '/api/v1/matches/{match_id}/tickets': '/api/v2/matches/{match_id}/tickets',
  '/api/v1/matches/{match_id}/unity-access':
      '/api/v2/matches/{match_id}/unity-access',
  '/api/v1/matches/{match_id}/unity-access/refresh':
      '/api/v2/matches/{match_id}/unity-access/refresh',
  '/api/v1/me/clubs/sale-market/listings':
      '/api/v2/me/clubs/sale-market/listings',
  '/api/v1/me/clubs/sale-market/offers': '/api/v2/me/clubs/sale-market/offers',
  '/api/v1/media': '/api/v2/media',
  '/api/v1/media-engine/creator-league/broadcast-modes':
      '/api/v2/media-engine/creator-league/broadcast-modes',
  '/api/v1/media-engine/creator-league/clubs/{club_id}/stadium':
      '/api/v2/media-engine/creator-league/clubs/{club_id}/stadium',
  '/api/v1/media-engine/creator-league/matches/{match_id}/access':
      '/api/v2/media-engine/creator-league/matches/{match_id}/access',
  '/api/v1/media-engine/creator-league/matches/{match_id}/analytics':
      '/api/v2/media-engine/creator-league/matches/{match_id}/analytics',
  '/api/v1/media-engine/creator-league/matches/{match_id}/gifts':
      '/api/v2/media-engine/creator-league/matches/{match_id}/gifts',
  '/api/v1/media-engine/creator-league/matches/{match_id}/purchase':
      '/api/v2/media-engine/creator-league/matches/{match_id}/purchase',
  '/api/v1/media-engine/creator-league/matches/{match_id}/stadium':
      '/api/v2/media-engine/creator-league/matches/{match_id}/stadium',
  '/api/v1/media-engine/creator-league/matches/{match_id}/stadium/placements':
      '/api/v2/media-engine/creator-league/matches/{match_id}/stadium/placements',
  '/api/v1/media-engine/creator-league/matches/{match_id}/tickets':
      '/api/v2/media-engine/creator-league/matches/{match_id}/tickets',
  '/api/v1/media-engine/creator-league/season-passes':
      '/api/v2/media-engine/creator-league/season-passes',
  '/api/v1/media-engine/creator-league/season-passes/me':
      '/api/v2/media-engine/creator-league/season-passes/me',
  '/api/v1/media-engine/downloads': '/api/v2/media-engine/downloads',
  '/api/v1/media-engine/downloads/{token}':
      '/api/v2/media-engine/downloads/{token}',
  '/api/v1/media-engine/matches/{match_key}/snapshot':
      '/api/v2/media-engine/matches/{match_key}/snapshot',
  '/api/v1/media-engine/me/clip-earnings':
      '/api/v2/media-engine/me/clip-earnings',
  '/api/v1/media-engine/me/purchases': '/api/v2/media-engine/me/purchases',
  '/api/v1/media-engine/me/share-exports':
      '/api/v2/media-engine/me/share-exports',
  '/api/v1/media-engine/purchases': '/api/v2/media-engine/purchases',
  '/api/v1/media-engine/share-exports': '/api/v2/media-engine/share-exports',
  '/api/v1/media-engine/share-exports/{export_id}/amplifications':
      '/api/v2/media-engine/share-exports/{export_id}/amplifications',
  '/api/v1/media-engine/share-templates':
      '/api/v2/media-engine/share-templates',
  '/api/v1/media-engine/views': '/api/v2/media-engine/views',
  '/api/v1/metrics': '/api/v2/metrics',
  '/api/v1/moderation/me/reports': '/api/v2/moderation/me/reports',
  '/api/v1/moderation/reports': '/api/v2/moderation/reports',
  '/api/v1/moments/live': '/api/v2/moments/live',
  '/api/v1/national-pool': '/api/v2/national-pool',
  '/api/v1/national-team-engine/competitions':
      '/api/v2/national-team-engine/competitions',
  '/api/v1/national-team-engine/competitions/{competition_id}':
      '/api/v2/national-team-engine/competitions/{competition_id}',
  '/api/v1/national-team-engine/competitions/{competition_id}/ads/active':
      '/api/v2/national-team-engine/competitions/{competition_id}/ads/active',
  '/api/v1/national-team-engine/competitions/{competition_id}/auto-build-squad':
      '/api/v2/national-team-engine/competitions/{competition_id}/auto-build-squad',
  '/api/v1/national-team-engine/competitions/{competition_id}/entries':
      '/api/v2/national-team-engine/competitions/{competition_id}/entries',
  '/api/v1/national-team-engine/competitions/{competition_id}/gifts':
      '/api/v2/national-team-engine/competitions/{competition_id}/gifts',
  '/api/v1/national-team-engine/competitions/{competition_id}/lifecycle':
      '/api/v2/national-team-engine/competitions/{competition_id}/lifecycle',
  '/api/v1/national-team-engine/competitions/{competition_id}/presentation':
      '/api/v2/national-team-engine/competitions/{competition_id}/presentation',
  '/api/v1/national-team-engine/competitions/{competition_id}/rental-entry':
      '/api/v2/national-team-engine/competitions/{competition_id}/rental-entry',
  '/api/v1/national-team-engine/competitions/{competition_id}/rental-pool':
      '/api/v2/national-team-engine/competitions/{competition_id}/rental-pool',
  '/api/v1/national-team-engine/competitions/{competition_id}/story-events':
      '/api/v2/national-team-engine/competitions/{competition_id}/story-events',
  '/api/v1/national-team-engine/competitions/{competition_id}/theme':
      '/api/v2/national-team-engine/competitions/{competition_id}/theme',
  '/api/v1/national-team-engine/entries/{entry_id}':
      '/api/v2/national-team-engine/entries/{entry_id}',
  '/api/v1/national-team-engine/entries/{entry_id}/free-players/claim':
      '/api/v2/national-team-engine/entries/{entry_id}/free-players/claim',
  '/api/v1/national-team-engine/entries/{entry_id}/rental-status':
      '/api/v2/national-team-engine/entries/{entry_id}/rental-status',
  '/api/v1/national-team-engine/entries/{entry_id}/rentals':
      '/api/v2/national-team-engine/entries/{entry_id}/rentals',
  '/api/v1/national-team-engine/me/history':
      '/api/v2/national-team-engine/me/history',
  '/api/v1/national-team-engine/me/previous-roster':
      '/api/v2/national-team-engine/me/previous-roster',
  '/api/v1/national-team-engine/rankings':
      '/api/v2/national-team-engine/rankings',
  '/api/v1/news/breaking': '/api/v2/news/breaking',
  '/api/v1/news/daily': '/api/v2/news/daily',
  '/api/v1/news/feed': '/api/v2/news/feed',
  '/api/v1/news/personalized': '/api/v2/news/personalized',
  '/api/v1/news/{article_id}': '/api/v2/news/{article_id}',
  '/api/v1/notifications': '/api/v2/notifications',
  '/api/v1/notifications/announcements': '/api/v2/notifications/announcements',
  '/api/v1/notifications/me': '/api/v2/notifications/me',
  '/api/v1/notifications/preferences': '/api/v2/notifications/preferences',
  '/api/v1/notifications/read-all': '/api/v2/notifications/read-all',
  '/api/v1/notifications/subscriptions': '/api/v2/notifications/subscriptions',
  '/api/v1/notifications/subscriptions/{subscription_id}':
      '/api/v2/notifications/subscriptions/{subscription_id}',
  '/api/v1/notifications/{notification_id}/read':
      '/api/v2/notifications/{notification_id}/read',
  '/api/v1/objectives/me': '/api/v2/objectives/me',
  '/api/v1/observability/config': '/api/v2/observability/config',
  '/api/v1/orchestrator/config': '/api/v2/orchestrator/config',
  '/api/v1/orchestrator/metrics': '/api/v2/orchestrator/metrics',
  '/api/v1/orders': '/api/v2/orders',
  '/api/v1/orders/book/{player_id}': '/api/v2/orders/book/{player_id}',
  '/api/v1/orders/{order_id}': '/api/v2/orders/{order_id}',
  '/api/v1/orders/{order_id}/admin-buyback':
      '/api/v2/orders/{order_id}/admin-buyback',
  '/api/v1/orders/{order_id}/admin-buyback-preview':
      '/api/v2/orders/{order_id}/admin-buyback-preview',
  '/api/v1/orders/{order_id}/cancel': '/api/v2/orders/{order_id}/cancel',
  '/api/v1/organizations': '/api/v2/organizations',
  '/api/v1/organizations/invites/accept':
      '/api/v2/organizations/invites/accept',
  '/api/v1/organizations/me': '/api/v2/organizations/me',
  '/api/v1/organizations/{organization_id}/audit-log':
      '/api/v2/organizations/{organization_id}/audit-log',
  '/api/v1/organizations/{organization_id}/invite':
      '/api/v2/organizations/{organization_id}/invite',
  '/api/v1/ownership-groups': '/api/v2/ownership-groups',
  '/api/v1/ownership-groups/transfers/validate':
      '/api/v2/ownership-groups/transfers/validate',
  '/api/v1/ownership-groups/{group_id}': '/api/v2/ownership-groups/{group_id}',
  '/api/v1/ownership-groups/{group_id}/budget/allocate':
      '/api/v2/ownership-groups/{group_id}/budget/allocate',
  '/api/v1/ownership-groups/{group_id}/budget/transfer':
      '/api/v2/ownership-groups/{group_id}/budget/transfer',
  '/api/v1/ownership-groups/{group_id}/clubs':
      '/api/v2/ownership-groups/{group_id}/clubs',
  '/api/v1/platform/mode': '/api/v2/platform/mode',
  '/api/v1/platform/switch': '/api/v2/platform/switch',
  '/api/v1/player-cards/admin/preseeded-regens':
      '/api/v2/player-cards/admin/preseeded-regens',
  '/api/v1/player-cards/admin/preseeded-regens/mint':
      '/api/v2/player-cards/admin/preseeded-regens/mint',
  '/api/v1/player-cards/inventory': '/api/v2/player-cards/inventory',
  '/api/v1/player-cards/listings': '/api/v2/player-cards/listings',
  '/api/v1/player-cards/listings/mine': '/api/v2/player-cards/listings/mine',
  '/api/v1/player-cards/listings/{listing_id}/buy':
      '/api/v2/player-cards/listings/{listing_id}/buy',
  '/api/v1/player-cards/listings/{listing_id}/cancel':
      '/api/v2/player-cards/listings/{listing_id}/cancel',
  '/api/v1/player-cards/loans': '/api/v2/player-cards/loans',
  '/api/v1/player-cards/loans/contracts/{loan_contract_id}/return':
      '/api/v2/player-cards/loans/contracts/{loan_contract_id}/return',
  '/api/v1/player-cards/loans/{loan_listing_id}/borrow':
      '/api/v2/player-cards/loans/{loan_listing_id}/borrow',
  '/api/v1/player-cards/marketplace/listings':
      '/api/v2/player-cards/marketplace/listings',
  '/api/v1/player-cards/marketplace/loans':
      '/api/v2/player-cards/marketplace/loans',
  '/api/v1/player-cards/marketplace/loans/contracts':
      '/api/v2/player-cards/marketplace/loans/contracts',
  '/api/v1/player-cards/marketplace/loans/contracts/{contract_id}/return':
      '/api/v2/player-cards/marketplace/loans/contracts/{contract_id}/return',
  '/api/v1/player-cards/marketplace/loans/contracts/{contract_id}/settle':
      '/api/v2/player-cards/marketplace/loans/contracts/{contract_id}/settle',
  '/api/v1/player-cards/marketplace/loans/negotiations/{negotiation_id}/accept':
      '/api/v2/player-cards/marketplace/loans/negotiations/{negotiation_id}/accept',
  '/api/v1/player-cards/marketplace/loans/negotiations/{negotiation_id}/counter':
      '/api/v2/player-cards/marketplace/loans/negotiations/{negotiation_id}/counter',
  '/api/v1/player-cards/marketplace/loans/{listing_id}/cancel':
      '/api/v2/player-cards/marketplace/loans/{listing_id}/cancel',
  '/api/v1/player-cards/marketplace/loans/{listing_id}/negotiations':
      '/api/v2/player-cards/marketplace/loans/{listing_id}/negotiations',
  '/api/v1/player-cards/marketplace/sales':
      '/api/v2/player-cards/marketplace/sales',
  '/api/v1/player-cards/marketplace/sales/{listing_id}/buy':
      '/api/v2/player-cards/marketplace/sales/{listing_id}/buy',
  '/api/v1/player-cards/marketplace/sales/{listing_id}/cancel':
      '/api/v2/player-cards/marketplace/sales/{listing_id}/cancel',
  '/api/v1/player-cards/marketplace/swaps':
      '/api/v2/player-cards/marketplace/swaps',
  '/api/v1/player-cards/marketplace/swaps/{listing_id}/cancel':
      '/api/v2/player-cards/marketplace/swaps/{listing_id}/cancel',
  '/api/v1/player-cards/marketplace/swaps/{listing_id}/execute':
      '/api/v2/player-cards/marketplace/swaps/{listing_id}/execute',
  '/api/v1/player-cards/players': '/api/v2/player-cards/players',
  '/api/v1/player-cards/players/{player_id}':
      '/api/v2/player-cards/players/{player_id}',
  '/api/v1/player-cards/starter-rental': '/api/v2/player-cards/starter-rental',
  '/api/v1/player-cards/watchlist': '/api/v2/player-cards/watchlist',
  '/api/v1/player-cards/watchlist/{watchlist_id}':
      '/api/v2/player-cards/watchlist/{watchlist_id}',
  '/api/v1/player-history': '/api/v2/player-history',
  '/api/v1/player-history/{player_id}': '/api/v2/player-history/{player_id}',
  '/api/v1/player-import/youth-prospects/me':
      '/api/v2/player-import/youth-prospects/me',
  '/api/v1/player-import/youth-prospects/{club_id}':
      '/api/v2/player-import/youth-prospects/{club_id}',
  '/api/v1/players': '/api/v2/players',
  '/api/v1/players/events': '/api/v2/players/events',
  '/api/v1/players/markets': '/api/v2/players/markets',
  '/api/v1/players/match': '/api/v2/players/match',
  '/api/v1/players/me/match-profile': '/api/v2/players/me/match-profile',
  '/api/v1/players/me/shares/holdings': '/api/v2/players/me/shares/holdings',
  '/api/v1/players/real-universe': '/api/v2/players/real-universe',
  '/api/v1/players/real-universe/search':
      '/api/v2/players/real-universe/search',
  '/api/v1/players/real-universe/{player_id}':
      '/api/v2/players/real-universe/{player_id}',
  '/api/v1/players/summaries/recent': '/api/v2/players/summaries/recent',
  '/api/v1/players/{player_id}': '/api/v2/players/{player_id}',
  '/api/v1/players/{player_id}/agency': '/api/v2/players/{player_id}/agency',
  '/api/v1/players/{player_id}/agency/contract-decision':
      '/api/v2/players/{player_id}/agency/contract-decision',
  '/api/v1/players/{player_id}/agency/transfer-decision':
      '/api/v2/players/{player_id}/agency/transfer-decision',
  '/api/v1/players/{player_id}/availability':
      '/api/v2/players/{player_id}/availability',
  '/api/v1/players/{player_id}/avatar': '/api/v2/players/{player_id}/avatar',
  '/api/v1/players/{player_id}/career': '/api/v2/players/{player_id}/career',
  '/api/v1/players/{player_id}/career-events':
      '/api/v2/players/{player_id}/career-events',
  '/api/v1/players/{player_id}/career/summary':
      '/api/v2/players/{player_id}/career/summary',
  '/api/v1/players/{player_id}/contracts':
      '/api/v2/players/{player_id}/contracts',
  '/api/v1/players/{player_id}/contracts/summary':
      '/api/v2/players/{player_id}/contracts/summary',
  '/api/v1/players/{player_id}/contracts/{contract_id}/renew':
      '/api/v2/players/{player_id}/contracts/{contract_id}/renew',
  '/api/v1/players/{player_id}/dna': '/api/v2/players/{player_id}/dna',
  '/api/v1/players/{player_id}/events': '/api/v2/players/{player_id}/events',
  '/api/v1/players/{player_id}/injuries':
      '/api/v2/players/{player_id}/injuries',
  '/api/v1/players/{player_id}/injuries/{injury_id}/recover':
      '/api/v2/players/{player_id}/injuries/{injury_id}/recover',
  '/api/v1/players/{player_id}/interviews':
      '/api/v2/players/{player_id}/interviews',
  '/api/v1/players/{player_id}/lifecycle-snapshot':
      '/api/v2/players/{player_id}/lifecycle-snapshot',
  '/api/v1/players/{player_id}/overview':
      '/api/v2/players/{player_id}/overview',
  '/api/v1/players/{player_id}/personality':
      '/api/v2/players/{player_id}/personality',
  '/api/v1/players/{player_id}/regen': '/api/v2/players/{player_id}/regen',
  '/api/v1/players/{player_id}/regen/big-club-approaches':
      '/api/v2/players/{player_id}/regen/big-club-approaches',
  '/api/v1/players/{player_id}/regen/contract-offers/quote':
      '/api/v2/players/{player_id}/regen/contract-offers/quote',
  '/api/v1/players/{player_id}/regen/offer-market':
      '/api/v2/players/{player_id}/regen/offer-market',
  '/api/v1/players/{player_id}/regen/pressure-resolution':
      '/api/v2/players/{player_id}/regen/pressure-resolution',
  '/api/v1/players/{player_id}/regen/special-training':
      '/api/v2/players/{player_id}/regen/special-training',
  '/api/v1/players/{player_id}/regen/transfer-listing':
      '/api/v2/players/{player_id}/regen/transfer-listing',
  '/api/v1/players/{player_id}/rivalries':
      '/api/v2/players/{player_id}/rivalries',
  '/api/v1/players/{player_id}/shares/buy':
      '/api/v2/players/{player_id}/shares/buy',
  '/api/v1/players/{player_id}/shares/dividends':
      '/api/v2/players/{player_id}/shares/dividends',
  '/api/v1/players/{player_id}/shares/events':
      '/api/v2/players/{player_id}/shares/events',
  '/api/v1/players/{player_id}/shares/issue':
      '/api/v2/players/{player_id}/shares/issue',
  '/api/v1/players/{player_id}/shares/market':
      '/api/v2/players/{player_id}/shares/market',
  '/api/v1/players/{player_id}/shares/performance':
      '/api/v2/players/{player_id}/shares/performance',
  '/api/v1/players/{player_id}/shares/sell':
      '/api/v2/players/{player_id}/shares/sell',
  '/api/v1/players/{player_id}/story': '/api/v2/players/{player_id}/story',
  '/api/v1/players/{player_id}/summary': '/api/v2/players/{player_id}/summary',
  '/api/v1/policies/acceptances': '/api/v2/policies/acceptances',
  '/api/v1/policies/country/{country_code}':
      '/api/v2/policies/country/{country_code}',
  '/api/v1/policies/documents': '/api/v2/policies/documents',
  '/api/v1/policies/documents/{document_key}':
      '/api/v2/policies/documents/{document_key}',
  '/api/v1/policies/me/acceptances': '/api/v2/policies/me/acceptances',
  '/api/v1/policies/me/compliance': '/api/v2/policies/me/compliance',
  '/api/v1/policies/me/region': '/api/v2/policies/me/region',
  '/api/v1/policies/me/requirements': '/api/v2/policies/me/requirements',
  '/api/v1/portfolio': '/api/v2/portfolio',
  '/api/v1/portfolio/snapshot': '/api/v2/portfolio/snapshot',
  '/api/v1/portfolio/summary': '/api/v2/portfolio/summary',
  '/api/v1/portfolios/me': '/api/v2/portfolios/me',
  '/api/v1/predictions': '/api/v2/predictions',
  '/api/v1/predictions/leaderboard': '/api/v2/predictions/leaderboard',
  '/api/v1/pundits/matches/{match_key}': '/api/v2/pundits/matches/{match_key}',
  '/api/v1/rankings/clubs': '/api/v2/rankings/clubs',
  '/api/v1/rankings/global': '/api/v2/rankings/global',
  '/api/v1/rankings/players': '/api/v2/rankings/players',
  '/api/v1/ready': '/ready',
  '/api/v1/real-world/events': '/api/v2/real-world/events',
  '/api/v1/real-world/hybrid-players': '/api/v2/real-world/hybrid-players',
  '/api/v1/real-world/normalize': '/api/v2/real-world/normalize',
  '/api/v1/real-world/players': '/api/v2/real-world/players',
  '/api/v1/real-world/players/{real_player_id}':
      '/api/v2/real-world/players/{real_player_id}',
  '/api/v1/real-world/providers': '/api/v2/real-world/providers',
  '/api/v1/real-world/settings/me': '/api/v2/real-world/settings/me',
  '/api/v1/realtime/matches/{match_id}/gateway':
      '/api/v2/realtime/matches/{match_id}/gateway',
  '/api/v1/realtime/matches/{match_id}/stream':
      '/api/v2/realtime/matches/{match_id}/stream',
  '/api/v1/realtime/status': '/api/v2/realtime/status',
  '/api/v1/realtime/stream': '/api/v2/realtime/stream',
  '/api/v1/realtime/wallet/gateway': '/api/v2/realtime/wallet/gateway',
  '/api/v1/realtime/wallet/stream': '/api/v2/realtime/wallet/stream',
  '/api/v1/referrals/attribution': '/api/v2/referrals/attribution',
  '/api/v1/referrals/me/invites': '/api/v2/referrals/me/invites',
  '/api/v1/referrals/me/rewards': '/api/v2/referrals/me/rewards',
  '/api/v1/referrals/me/summary': '/api/v2/referrals/me/summary',
  '/api/v1/referrals/share-codes': '/api/v2/referrals/share-codes',
  '/api/v1/referrals/share-codes/me': '/api/v2/referrals/share-codes/me',
  '/api/v1/referrals/share-codes/{code}/redeem':
      '/api/v2/referrals/share-codes/{code}/redeem',
  '/api/v1/referrals/share-codes/{share_code_id}':
      '/api/v2/referrals/share-codes/{share_code_id}',
  '/api/v1/regen-hype': '/api/v2/regen-hype',
  '/api/v1/regen-universe/achievements': '/api/v2/regen-universe/achievements',
  '/api/v1/regen-universe/awards': '/api/v2/regen-universe/awards',
  '/api/v1/regen-universe/bloodlines': '/api/v2/regen-universe/bloodlines',
  '/api/v1/regen-universe/hall-of-fame': '/api/v2/regen-universe/hall-of-fame',
  '/api/v1/regen-universe/national-regens':
      '/api/v2/regen-universe/national-regens',
  '/api/v1/regen-universe/player/{player_id}':
      '/api/v2/regen-universe/player/{player_id}',
  '/api/v1/regen-universe/players/{player_id}':
      '/api/v2/regen-universe/players/{player_id}',
  '/api/v1/regen-universe/players/{player_id}/timeline':
      '/api/v2/regen-universe/players/{player_id}/timeline',
  '/api/v1/regen-universe/rankings': '/api/v2/regen-universe/rankings',
  '/api/v1/regen-universe/rising-stars': '/api/v2/regen-universe/rising-stars',
  '/api/v1/regen-universe/scouting-feed':
      '/api/v2/regen-universe/scouting-feed',
  '/api/v1/regen-universe/seasons': '/api/v2/regen-universe/seasons',
  '/api/v1/regen-universe/tracking': '/api/v2/regen-universe/tracking',
  '/api/v1/regen-universe/youth-tournaments':
      '/api/v2/regen-universe/youth-tournaments',
  '/api/v1/regen-universe/youth-tournaments/{tournament_id}':
      '/api/v2/regen-universe/youth-tournaments/{tournament_id}',
  '/api/v1/regens/awards': '/api/v2/regens/awards',
  '/api/v1/regens/awards/{award_id}/vote':
      '/api/v2/regens/awards/{award_id}/vote',
  '/api/v1/regens/creation-orders': '/api/v2/regens/creation-orders',
  '/api/v1/regens/creation-orders/{order_id}':
      '/api/v2/regens/creation-orders/{order_id}',
  '/api/v1/regens/creation-orders/{order_id}/generate-after-payment':
      '/api/v2/regens/creation-orders/{order_id}/generate-after-payment',
  '/api/v1/regens/creation-orders/{order_id}/pay-with-wallet':
      '/api/v2/regens/creation-orders/{order_id}/pay-with-wallet',
  '/api/v1/regens/feed': '/api/v2/regens/feed',
  '/api/v1/regens/jobs/{job_name}': '/api/v2/regens/jobs/{job_name}',
  '/api/v1/regens/request-son': '/api/v2/regens/request-son',
  '/api/v1/regens/request-son/options': '/api/v2/regens/request-son/options',
  '/api/v1/regens/rising': '/api/v2/regens/rising',
  '/api/v1/regens/top': '/api/v2/regens/top',
  '/api/v1/regens/{regen_id}/lineage': '/api/v2/regens/{regen_id}/lineage',
  '/api/v1/rent': '/api/v2/rent',
  '/api/v1/replays/countdown/{fixture_id}':
      '/api/v2/replays/countdown/{fixture_id}',
  '/api/v1/replays/me': '/api/v2/replays/me',
  '/api/v1/replays/public/featured': '/api/v2/replays/public/featured',
  '/api/v1/replays/{replay_id}': '/api/v2/replays/{replay_id}',
  '/api/v1/reward-engine/me/settlements':
      '/api/v2/reward-engine/me/settlements',
  '/api/v1/reward-engine/me/summary': '/api/v2/reward-engine/me/summary',
  '/api/v1/risk-ops/me/aml-cases': '/api/v2/risk-ops/me/aml-cases',
  '/api/v1/risk-ops/me/fraud-cases': '/api/v2/risk-ops/me/fraud-cases',
  '/api/v1/risk-ops/me/overview': '/api/v2/risk-ops/me/overview',
  '/api/v1/risk-ops/me/restrictions': '/api/v2/risk-ops/me/restrictions',
  '/api/v1/risk-ops/me/signals': '/api/v2/risk-ops/me/signals',
  '/api/v1/rivalries/matches': '/api/v2/rivalries/matches',
  '/api/v1/scout/report/{player_id}': '/api/v2/scout/report/{player_id}',
  '/api/v1/scouts': '/api/v2/scouts',
  '/api/v1/scouts/{scout_id}/discover': '/api/v2/scouts/{scout_id}/discover',
  '/api/v1/season-pass': '/api/v2/season-pass',
  '/api/v1/season-pass/claim': '/api/v2/season-pass/claim',
  '/api/v1/season-pass/me': '/api/v2/season-pass/me',
  '/api/v1/season-pass/rewards/{reward_id}/claim':
      '/api/v2/season-pass/rewards/{reward_id}/claim',
  '/api/v1/season/current': '/api/v2/season/current',
  '/api/v1/season/history': '/api/v2/season/history',
  '/api/v1/session/bootstrap': '/api/v2/session/bootstrap',
  '/api/v1/shows/debate': '/api/v2/shows/debate',
  '/api/v1/shows/post-match/{match_id}': '/api/v2/shows/post-match/{match_id}',
  '/api/v1/shows/pre-match/{match_id}': '/api/v2/shows/pre-match/{match_id}',
  '/api/v1/simulation-matchmaking/hosted-competitions/preview':
      '/api/v2/simulation-matchmaking/hosted-competitions/preview',
  '/api/v1/simulation-matchmaking/profiles/{user_id}':
      '/api/v2/simulation-matchmaking/profiles/{user_id}',
  '/api/v1/simulation-matchmaking/quick-game':
      '/api/v2/simulation-matchmaking/quick-game',
  '/api/v1/simulation-matchmaking/quick-tournament':
      '/api/v2/simulation-matchmaking/quick-tournament',
  '/api/v1/social/clubs/{club_id}/community':
      '/api/v2/social/clubs/{club_id}/community',
  '/api/v1/social/clubs/{club_id}/community/messages':
      '/api/v2/social/clubs/{club_id}/community/messages',
  '/api/v1/social/feed': '/api/v2/social/feed',
  '/api/v1/social/follows': '/api/v2/social/follows',
  '/api/v1/social/follows/me': '/api/v2/social/follows/me',
  '/api/v1/social/profile/me': '/api/v2/social/profile/me',
  '/api/v1/social/rivalries/{club_a_id}/{club_b_id}':
      '/api/v2/social/rivalries/{club_a_id}/{club_b_id}',
  '/api/v1/social/rivalries/{club_a_id}/{club_b_id}/banter':
      '/api/v2/social/rivalries/{club_a_id}/{club_b_id}/banter',
  '/api/v1/sponsors': '/api/v2/sponsors',
  '/api/v1/sponsorship/clubs/{club_id}/contracts':
      '/api/v2/sponsorship/clubs/{club_id}/contracts',
  '/api/v1/sponsorship/clubs/{club_id}/dashboard':
      '/api/v2/sponsorship/clubs/{club_id}/dashboard',
  '/api/v1/sponsorship/clubs/{club_id}/offers':
      '/api/v2/sponsorship/clubs/{club_id}/offers',
  '/api/v1/sponsorship/clubs/{club_id}/sponsors':
      '/api/v2/sponsorship/clubs/{club_id}/sponsors',
  '/api/v1/sponsorship/contracts/request':
      '/api/v2/sponsorship/contracts/request',
  '/api/v1/sponsorship/me/leads': '/api/v2/sponsorship/me/leads',
  '/api/v1/sponsorship/packages': '/api/v2/sponsorship/packages',
  '/api/v1/sponsorship/placements': '/api/v2/sponsorship/placements',
  '/api/v1/story-feed': '/api/v2/story-feed',
  '/api/v1/story-feed/digest': '/api/v2/story-feed/digest',
  '/api/v1/streamer-tournaments': '/api/v2/streamer-tournaments',
  '/api/v1/streamer-tournaments/mine': '/api/v2/streamer-tournaments/mine',
  '/api/v1/streamer-tournaments/{tournament_id}':
      '/api/v2/streamer-tournaments/{tournament_id}',
  '/api/v1/streamer-tournaments/{tournament_id}/invites':
      '/api/v2/streamer-tournaments/{tournament_id}/invites',
  '/api/v1/streamer-tournaments/{tournament_id}/join':
      '/api/v2/streamer-tournaments/{tournament_id}/join',
  '/api/v1/streamer-tournaments/{tournament_id}/publish':
      '/api/v2/streamer-tournaments/{tournament_id}/publish',
  '/api/v1/streamer-tournaments/{tournament_id}/rewards':
      '/api/v2/streamer-tournaments/{tournament_id}/rewards',
  '/api/v1/surveillance/circular-trade-alerts':
      '/api/v2/surveillance/circular-trade-alerts',
  '/api/v1/surveillance/holder-concentration-alerts':
      '/api/v2/surveillance/holder-concentration-alerts',
  '/api/v1/surveillance/suspicious-clusters':
      '/api/v2/surveillance/suspicious-clusters',
  '/api/v1/surveillance/suspicious-players':
      '/api/v2/surveillance/suspicious-players',
  '/api/v1/surveillance/thin-market-alerts':
      '/api/v2/surveillance/thin-market-alerts',
  '/api/v1/sync/update': '/api/v2/sync/update',
  '/api/v1/tickets/attendance/{match_id}/react':
      '/api/v2/tickets/attendance/{match_id}/react',
  '/api/v1/tickets/buy': '/api/v2/tickets/buy',
  '/api/v1/tickets/event/{match_id}': '/api/v2/tickets/event/{match_id}',
  '/api/v1/tickets/resell': '/api/v2/tickets/resell',
  '/api/v1/tickets/waitlist': '/api/v2/tickets/waitlist',
  '/api/v1/tournaments': '/api/v2/tournaments',
  '/api/v1/tournaments/{tournament_id}': '/api/v2/tournaments/{tournament_id}',
  '/api/v1/tournaments/{tournament_id}/advance':
      '/api/v2/tournaments/{tournament_id}/advance',
  '/api/v1/tournaments/{tournament_id}/join':
      '/api/v2/tournaments/{tournament_id}/join',
  '/api/v1/tournaments/{tournament_id}/matches/{match_id}/result':
      '/api/v2/tournaments/{tournament_id}/matches/{match_id}/result',
  '/api/v1/trader/markets': '/api/v2/trader/markets',
  '/api/v1/trader/orders': '/api/v2/trader/orders',
  '/api/v1/trader/overview': '/api/v2/trader/overview',
  '/api/v1/trader/p2p': '/api/v2/trader/p2p',
  '/api/v1/trader/security/totp/setup': '/api/v2/trader/security/totp/setup',
  '/api/v1/trader/watchlist': '/api/v2/trader/watchlist',
  '/api/v1/transfer-market/clubs/{club_id}/team-dynamics':
      '/api/v2/transfer-market/clubs/{club_id}/team-dynamics',
  '/api/v1/transfer-market/coaches/{club_id}/demands':
      '/api/v2/transfer-market/coaches/{club_id}/demands',
  '/api/v1/transfer-market/coaches/{club_id}/profile':
      '/api/v2/transfer-market/coaches/{club_id}/profile',
  '/api/v1/transfer-market/jobs/run': '/api/v2/transfer-market/jobs/run',
  '/api/v1/transfer-market/listings': '/api/v2/transfer-market/listings',
  '/api/v1/transfer-market/listings/{listing_id}':
      '/api/v2/transfer-market/listings/{listing_id}',
  '/api/v1/transfer-market/listings/{listing_id}/bids':
      '/api/v2/transfer-market/listings/{listing_id}/bids',
  '/api/v1/transfer-market/listings/{listing_id}/close':
      '/api/v2/transfer-market/listings/{listing_id}/close',
  '/api/v1/transfer-market/listings/{listing_id}/contract-offer':
      '/api/v2/transfer-market/listings/{listing_id}/contract-offer',
  '/api/v1/transfer-market/listings/{listing_id}/negotiation':
      '/api/v2/transfer-market/listings/{listing_id}/negotiation',
  '/api/v1/transfer-market/listings/{listing_id}/stream':
      '/api/v2/transfer-market/listings/{listing_id}/stream',
  '/api/v1/transfer-market/players/{player_id}/decision-profile':
      '/api/v2/transfer-market/players/{player_id}/decision-profile',
  '/api/v1/transfer-market/watchlist': '/api/v2/transfer-market/watchlist',
  '/api/v1/transfers/windows': '/api/v2/transfers/windows',
  '/api/v1/transfers/windows/{window_id}':
      '/api/v2/transfers/windows/{window_id}',
  '/api/v1/transfers/windows/{window_id}/bids':
      '/api/v2/transfers/windows/{window_id}/bids',
  '/api/v1/transfers/windows/{window_id}/bids/{bid_id}/accept':
      '/api/v2/transfers/windows/{window_id}/bids/{bid_id}/accept',
  '/api/v1/transfers/windows/{window_id}/bids/{bid_id}/reject':
      '/api/v2/transfers/windows/{window_id}/bids/{bid_id}/reject',
  '/api/v1/transfers/windows/{window_id}/players/{player_id}/regen-bid-evaluations':
      '/api/v2/transfers/windows/{window_id}/players/{player_id}/regen-bid-evaluations',
  '/api/v1/transfers/windows/{window_id}/players/{player_id}/resolve-regen-bid':
      '/api/v2/transfers/windows/{window_id}/players/{player_id}/resolve-regen-bid',
  '/api/v1/trust/me': '/api/v2/trust/me',
  '/api/v1/trust/{user_id}': '/api/v2/trust/{user_id}',
  '/api/v1/ultimate-league/competitors/{competitor_id}':
      '/api/v2/ultimate-league/competitors/{competitor_id}',
  '/api/v1/ultimate-league/matches/result':
      '/api/v2/ultimate-league/matches/result',
  '/api/v1/ultimate-league/matchmaking/batch':
      '/api/v2/ultimate-league/matchmaking/batch',
  '/api/v1/ultimate-league/standings/{tier}':
      '/api/v2/ultimate-league/standings/{tier}',
  '/api/v1/ultimate-league/tactical-presets':
      '/api/v2/ultimate-league/tactical-presets',
  '/api/v1/ultimate-league/tactical-presets/{preset_id}/purchase':
      '/api/v2/ultimate-league/tactical-presets/{preset_id}/purchase',
  '/api/v1/ultimate-league/tiers': '/api/v2/ultimate-league/tiers',
  '/api/v1/ultimate-league/tournaments': '/api/v2/ultimate-league/tournaments',
  '/api/v1/ultimate-league/tournaments/{tournament_id}':
      '/api/v2/ultimate-league/tournaments/{tournament_id}',
  '/api/v1/ultimate-league/tournaments/{tournament_id}/payouts/preview':
      '/api/v2/ultimate-league/tournaments/{tournament_id}/payouts/preview',
  '/api/v1/users/me': '/api/v2/users/me',
  '/api/v1/users/me/profile': '/api/v2/users/me/profile',
  '/api/v1/users/suggestions': '/api/v2/users/suggestions',
  '/api/v1/users/{user_id}/followers': '/api/v2/users/{user_id}/followers',
  '/api/v1/users/{user_id}/following': '/api/v2/users/{user_id}/following',
  '/api/v1/v2/broadcast/pay': '/api/v2/broadcast/pay',
  '/api/v1/v2/broadcast/{match_id}': '/api/v2/broadcast/{match_id}',
  '/api/v1/v2/clubs/list': '/api/v2/clubs/list',
  '/api/v1/v2/clubs/marketplace': '/api/v2/clubs/marketplace',
  '/api/v1/v2/clubs/offer': '/api/v2/clubs/offer',
  '/api/v1/v2/clubs/{club_id}/fans': '/api/v2/clubs/{club_id}/fans',
  '/api/v1/v2/clubs/{club_id}/finances': '/api/v2/clubs/{club_id}/finances',
  '/api/v1/v2/clubs/{club_id}/squad': '/api/v2/clubs/{club_id}/squad',
  '/api/v1/v2/competitions': '/api/v2/competitions',
  '/api/v1/v2/federations': '/api/v2/federations',
  '/api/v1/v2/federations/vote': '/api/v2/federations/vote',
  '/api/v1/v2/federations/{federation_id}/join':
      '/api/v2/federations/{federation_id}/join',
  '/api/v1/v2/feed': '/api/v2/feed',
  '/api/v1/v2/history/records': '/api/v2/history/records',
  '/api/v1/v2/home/dashboard': '/api/v2/home/dashboard',
  '/api/v1/v2/market/bid': '/api/v2/market/bid',
  '/api/v1/v2/market/listings': '/api/v2/market/listings',
  '/api/v1/v2/matches/{match_id}': '/api/v2/matches/{match_id}',
  '/api/v1/v2/players/{player_id}': '/api/v2/players/{player_id}',
  '/api/v1/v2/regens': '/api/v2/regens',
  '/api/v1/v2/stories': '/api/v2/stories',
  '/api/v1/v2/stories/generate': '/api/v2/stories/generate',
  '/api/v1/v2/tasks': '/api/v2/tasks',
  '/api/v1/v2/tasks/{task_id}/claim': '/api/v2/tasks/{task_id}/claim',
  '/api/v1/v2/tournaments/{tournament_id}':
      '/api/v2/tournaments/{tournament_id}',
  '/api/v1/v2/tournaments/{tournament_id}/join':
      '/api/v2/tournaments/{tournament_id}/join',
  '/api/v1/v2/tournaments/{tournament_id}/rent':
      '/api/v2/tournaments/{tournament_id}/rent',
  '/api/v1/v2/tournaments/{tournament_id}/squad':
      '/api/v2/tournaments/{tournament_id}/squad',
  '/api/v1/v2/users/{user_id}': '/api/v2/users/{user_id}',
  '/api/v1/v2/users/{user_id}/follow': '/api/v2/users/{user_id}/follow',
  '/api/v1/v2/ws/market/{listing_id}': '/api/v2/ws/market/{listing_id}',
  '/api/v1/v2/ws/notifications': '/api/v2/ws/notifications',
  '/api/v1/value-engine/snapshots/rebuild':
      '/api/v2/value-engine/snapshots/rebuild',
  '/api/v1/value-engine/snapshots/{player_id}/daily-closes':
      '/api/v2/value-engine/snapshots/{player_id}/daily-closes',
  '/api/v1/value-engine/snapshots/{player_id}/history':
      '/api/v2/value-engine/snapshots/{player_id}/history',
  '/api/v1/value-engine/snapshots/{player_id}/latest':
      '/api/v2/value-engine/snapshots/{player_id}/latest',
  '/api/v1/value-engine/snapshots/{player_id}/trend-summary':
      '/api/v2/value-engine/snapshots/{player_id}/trend-summary',
  '/api/v1/version': '/version',
  '/api/v1/viral/accounts': '/api/v2/viral/accounts',
  '/api/v1/viral/cascades': '/api/v2/viral/cascades',
  '/api/v1/viral/clips/trending': '/api/v2/viral/clips/trending',
  '/api/v1/viral/clips/{clip_id}/variants':
      '/api/v2/viral/clips/{clip_id}/variants',
  '/api/v1/viral/clips/{clip_id}/winner':
      '/api/v2/viral/clips/{clip_id}/winner',
  '/api/v1/viral/feed': '/api/v2/viral/feed',
  '/api/v1/viral/feed/for-you': '/api/v2/viral/feed/for-you',
  '/api/v1/viral/matches/{match_key}/clips':
      '/api/v2/viral/matches/{match_key}/clips',
  '/api/v1/viral/sessions/{session_id}': '/api/v2/viral/sessions/{session_id}',
  '/api/v1/wallet': '/api/v2/wallet',
  '/api/v1/wallet/top-up/initiate': '/api/v2/wallet/top-up/initiate',
  '/api/v1/wallet/top-up/verify': '/api/v2/wallet/top-up/verify',
  '/api/v1/wallet/transactions': '/api/v2/wallet/transactions',
  '/api/v1/wallets': '/api/v2/wallets',
  '/api/v1/wallets/accounts': '/api/v2/wallets/accounts',
  '/api/v1/wallets/adaptive-overview': '/api/v2/wallets/adaptive-overview',
  '/api/v1/wallets/conversions': '/api/v2/wallets/conversions',
  '/api/v1/wallets/conversions/quote': '/api/v2/wallets/conversions/quote',
  '/api/v1/wallets/deposits': '/api/v2/wallets/deposits',
  '/api/v1/wallets/deposits/{deposit_id}/submit':
      '/api/v2/wallets/deposits/{deposit_id}/submit',
  '/api/v1/wallets/ledger': '/api/v2/wallets/ledger',
  '/api/v1/wallets/market-topups': '/api/v2/wallets/market-topups',
  '/api/v1/wallets/overview': '/api/v2/wallets/overview',
  '/api/v1/wallets/payment-events': '/api/v2/wallets/payment-events',
  '/api/v1/wallets/providers/{provider_key}/webhook':
      '/api/v2/wallets/providers/{provider_key}/webhook',
  '/api/v1/wallets/purchase-orders': '/api/v2/wallets/purchase-orders',
  '/api/v1/wallets/purchase-orders/quote':
      '/api/v2/wallets/purchase-orders/quote',
  '/api/v1/wallets/purchase-orders/{order_id}':
      '/api/v2/wallets/purchase-orders/{order_id}',
  '/api/v1/wallets/summary': '/api/v2/wallets/summary',
  '/api/v1/wallets/top-up/initiate': '/api/v2/wallets/top-up/initiate',
  '/api/v1/wallets/top-up/verify': '/api/v2/wallets/top-up/verify',
  '/api/v1/wallets/transactions': '/api/v2/wallets/transactions',
  '/api/v1/wallets/withdrawals': '/api/v2/wallets/withdrawals',
  '/api/v1/wallets/withdrawals/eligibility':
      '/api/v2/wallets/withdrawals/eligibility',
  '/api/v1/wallets/withdrawals/quote': '/api/v2/wallets/withdrawals/quote',
  '/api/v1/wallets/withdrawals/{withdrawal_id}/receipt':
      '/api/v2/wallets/withdrawals/{withdrawal_id}/receipt',
  '/api/v1/world-super-cup/countdown': '/api/v2/world-super-cup/countdown',
  '/api/v1/world-super-cup/groups/table':
      '/api/v2/world-super-cup/groups/table',
  '/api/v1/world-super-cup/knockout/bracket':
      '/api/v2/world-super-cup/knockout/bracket',
  '/api/v1/world-super-cup/playoff/draw':
      '/api/v2/world-super-cup/playoff/draw',
  '/api/v1/world-super-cup/qualification/explanation':
      '/api/v2/world-super-cup/qualification/explanation',
  '/api/v1/world/clubs/{club_id}/context':
      '/api/v2/world/clubs/{club_id}/context',
  '/api/v1/world/competitions/{competition_id}/context':
      '/api/v2/world/competitions/{competition_id}/context',
  '/api/v1/world/cultures': '/api/v2/world/cultures',
  '/api/v1/world/narratives': '/api/v2/world/narratives',
  '/api/v1/ws/match/{match_id}': '/api/v2/ws/match/{match_id}',
  '/api/v1/ws/spectate/{match_id}': '/api/v2/ws/spectate/{match_id}',
  '/api/v1/ws/tournament/{tournament_id}':
      '/api/v2/ws/tournament/{tournament_id}',
  '/api/v2/academy': '/api/v2/academy',
  '/api/v2/academy/awards': '/api/v2/academy/awards',
  '/api/v2/academy/fixtures': '/api/v2/academy/fixtures',
  '/api/v2/academy/generate': '/api/v2/academy/generate',
  '/api/v2/academy/promote/{player_id}': '/api/v2/academy/promote/{player_id}',
  '/api/v2/academy/qualification': '/api/v2/academy/qualification',
  '/api/v2/academy/registration': '/api/v2/academy/registration',
  '/api/v2/academy/season-summary': '/api/v2/academy/season-summary',
  '/api/v2/academy/standings': '/api/v2/academy/standings',
  '/api/v2/admin-engine/bootstrap': '/api/v2/admin-engine/bootstrap',
  '/api/v2/admin/access': '/api/v2/admin/access',
  '/api/v2/admin/access/permissions': '/api/v2/admin/access/permissions',
  '/api/v2/admin/access/{user_id}/permissions':
      '/api/v2/admin/access/{user_id}/permissions',
  '/api/v2/admin/admin-engine/calendar-rules':
      '/api/v2/admin/admin-engine/calendar-rules',
  '/api/v2/admin/admin-engine/feature-flags':
      '/api/v2/admin/admin-engine/feature-flags',
  '/api/v2/admin/admin-engine/reward-rules':
      '/api/v2/admin/admin-engine/reward-rules',
  '/api/v2/admin/admin-engine/schedule-preview':
      '/api/v2/admin/admin-engine/schedule-preview',
  '/api/v2/admin/analytics/agent-learning':
      '/api/v2/admin/analytics/agent-learning',
  '/api/v2/admin/analytics/anomalies': '/api/v2/admin/analytics/anomalies',
  '/api/v2/admin/analytics/funnels': '/api/v2/admin/analytics/funnels',
  '/api/v2/admin/analytics/match-outcomes':
      '/api/v2/admin/analytics/match-outcomes',
  '/api/v2/admin/analytics/player-matching':
      '/api/v2/admin/analytics/player-matching',
  '/api/v2/admin/analytics/player-matching/recompute-weights':
      '/api/v2/admin/analytics/player-matching/recompute-weights',
  '/api/v2/admin/analytics/price-predictions':
      '/api/v2/admin/analytics/price-predictions',
  '/api/v2/admin/analytics/summary': '/api/v2/admin/analytics/summary',
  '/api/v2/admin/analytics/user-segments':
      '/api/v2/admin/analytics/user-segments',
  '/api/v2/admin/ban-user': '/api/v2/admin/ban-user',
  '/api/v2/admin/broadcast-rights/jobs/run':
      '/api/v2/admin/broadcast-rights/jobs/run',
  '/api/v2/admin/calendar-engine/events':
      '/api/v2/admin/calendar-engine/events',
  '/api/v2/admin/calendar-engine/hosted-competitions/{competition_id}/launch':
      '/api/v2/admin/calendar-engine/hosted-competitions/{competition_id}/launch',
  '/api/v2/admin/calendar-engine/national-competitions/{competition_id}/launch':
      '/api/v2/admin/calendar-engine/national-competitions/{competition_id}/launch',
  '/api/v2/admin/calendar-engine/seasons':
      '/api/v2/admin/calendar-engine/seasons',
  '/api/v2/admin/club-infra/seed': '/api/v2/admin/club-infra/seed',
  '/api/v2/admin/clubs/academy-analytics':
      '/api/v2/admin/clubs/academy-analytics',
  '/api/v2/admin/clubs/analytics': '/api/v2/admin/clubs/analytics',
  '/api/v2/admin/clubs/finance-analytics':
      '/api/v2/admin/clubs/finance-analytics',
  '/api/v2/admin/clubs/ops-summary': '/api/v2/admin/clubs/ops-summary',
  '/api/v2/admin/clubs/scouting-analytics':
      '/api/v2/admin/clubs/scouting-analytics',
  '/api/v2/admin/clubs/sponsorship-analytics':
      '/api/v2/admin/clubs/sponsorship-analytics',
  '/api/v2/admin/clubs/summary': '/api/v2/admin/clubs/summary',
  '/api/v2/admin/clubs/{club_id}': '/api/v2/admin/clubs/{club_id}',
  '/api/v2/admin/clubs/{club_id}/moderate-branding':
      '/api/v2/admin/clubs/{club_id}/moderate-branding',
  '/api/v2/admin/competitions': '/api/v2/admin/competitions',
  '/api/v2/admin/competitions/reminders/dispatch':
      '/api/v2/admin/competitions/reminders/dispatch',
  '/api/v2/admin/competitive-integrity/matches/{match_id}/validation':
      '/api/v2/admin/competitive-integrity/matches/{match_id}/validation',
  '/api/v2/admin/competitive-integrity/workers/run-once':
      '/api/v2/admin/competitive-integrity/workers/run-once',
  '/api/v2/admin/config/liquidity-bands':
      '/api/v2/admin/config/liquidity-bands',
  '/api/v2/admin/config/player-card-market-integrity':
      '/api/v2/admin/config/player-card-market-integrity',
  '/api/v2/admin/config/supply-tiers': '/api/v2/admin/config/supply-tiers',
  '/api/v2/admin/config/suspicion-thresholds':
      '/api/v2/admin/config/suspicion-thresholds',
  '/api/v2/admin/config/value-controls': '/api/v2/admin/config/value-controls',
  '/api/v2/admin/config/value-controls/audits':
      '/api/v2/admin/config/value-controls/audits',
  '/api/v2/admin/config/value-controls/integrity/candidates':
      '/api/v2/admin/config/value-controls/integrity/candidates',
  '/api/v2/admin/config/value-controls/players/{player_id}':
      '/api/v2/admin/config/value-controls/players/{player_id}',
  '/api/v2/admin/config/value-controls/preview/{player_id}':
      '/api/v2/admin/config/value-controls/preview/{player_id}',
  '/api/v2/admin/config/value-controls/recompute':
      '/api/v2/admin/config/value-controls/recompute',
  '/api/v2/admin/config/value-controls/run-history':
      '/api/v2/admin/config/value-controls/run-history',
  '/api/v2/admin/creator-campaigns/{campaign_id}/metrics':
      '/api/v2/admin/creator-campaigns/{campaign_id}/metrics',
  '/api/v2/admin/creator/applications': '/api/v2/admin/creator/applications',
  '/api/v2/admin/creator/applications/{application_id}/approve':
      '/api/v2/admin/creator/applications/{application_id}/approve',
  '/api/v2/admin/creator/applications/{application_id}/reject':
      '/api/v2/admin/creator/applications/{application_id}/reject',
  '/api/v2/admin/creator/applications/{application_id}/request-verification':
      '/api/v2/admin/creator/applications/{application_id}/request-verification',
  '/api/v2/admin/creator/cards/assign': '/api/v2/admin/creator/cards/assign',
  '/api/v2/admin/creator/dashboard': '/api/v2/admin/creator/dashboard',
  '/api/v2/admin/creator/fan-share-market/control':
      '/api/v2/admin/creator/fan-share-market/control',
  '/api/v2/admin/discovery/featured-rails':
      '/api/v2/admin/discovery/featured-rails',
  '/api/v2/admin/disputes': '/api/v2/admin/disputes',
  '/api/v2/admin/disputes/{dispute_id}/assign':
      '/api/v2/admin/disputes/{dispute_id}/assign',
  '/api/v2/admin/disputes/{dispute_id}/status':
      '/api/v2/admin/disputes/{dispute_id}/status',
  '/api/v2/admin/economy/burn-events': '/api/v2/admin/economy/burn-events',
  '/api/v2/admin/economy/fx-rates': '/api/v2/admin/economy/fx-rates',
  '/api/v2/admin/economy/gift-catalog': '/api/v2/admin/economy/gift-catalog',
  '/api/v2/admin/economy/gift-combo-rules':
      '/api/v2/admin/economy/gift-combo-rules',
  '/api/v2/admin/economy/governor': '/api/v2/admin/economy/governor',
  '/api/v2/admin/economy/governor/apply':
      '/api/v2/admin/economy/governor/apply',
  '/api/v2/admin/economy/governor/evaluate':
      '/api/v2/admin/economy/governor/evaluate',
  '/api/v2/admin/economy/governor/policy':
      '/api/v2/admin/economy/governor/policy',
  '/api/v2/admin/economy/regional-pricing':
      '/api/v2/admin/economy/regional-pricing',
  '/api/v2/admin/economy/revenue-share-rules':
      '/api/v2/admin/economy/revenue-share-rules',
  '/api/v2/admin/economy/service-pricing':
      '/api/v2/admin/economy/service-pricing',
  '/api/v2/admin/fan-predictions/matches/{match_id}/fixture':
      '/api/v2/admin/fan-predictions/matches/{match_id}/fixture',
  '/api/v2/admin/fan-predictions/matches/{match_id}/settlement':
      '/api/v2/admin/fan-predictions/matches/{match_id}/settlement',
  '/api/v2/admin/fan-wars/creator-country-assignments':
      '/api/v2/admin/fan-wars/creator-country-assignments',
  '/api/v2/admin/fan-wars/nations-cup': '/api/v2/admin/fan-wars/nations-cup',
  '/api/v2/admin/fan-wars/nations-cup/{competition_id}/advance':
      '/api/v2/admin/fan-wars/nations-cup/{competition_id}/advance',
  '/api/v2/admin/fan-wars/points': '/api/v2/admin/fan-wars/points',
  '/api/v2/admin/fan-wars/profiles': '/api/v2/admin/fan-wars/profiles',
  '/api/v2/admin/fan-wars/profiles/{profile_id}/rivals/{rival_profile_id}':
      '/api/v2/admin/fan-wars/profiles/{profile_id}/rivals/{rival_profile_id}',
  '/api/v2/admin/federations/run-jobs': '/api/v2/admin/federations/run-jobs',
  '/api/v2/admin/finance/account-controls':
      '/api/v2/admin/finance/account-controls',
  '/api/v2/admin/finance/account-controls/{user_id}':
      '/api/v2/admin/finance/account-controls/{user_id}',
  '/api/v2/admin/finance/control-tower': '/api/v2/admin/finance/control-tower',
  '/api/v2/admin/finance/manual-price-overrides':
      '/api/v2/admin/finance/manual-price-overrides',
  '/api/v2/admin/finance/manual-price-overrides/{asset_type}/{asset_id}':
      '/api/v2/admin/finance/manual-price-overrides/{asset_type}/{asset_id}',
  '/api/v2/admin/finance/match-kill-switches':
      '/api/v2/admin/finance/match-kill-switches',
  '/api/v2/admin/finance/match-kill-switches/{match_id}':
      '/api/v2/admin/finance/match-kill-switches/{match_id}',
  '/api/v2/admin/finance/reconciliation':
      '/api/v2/admin/finance/reconciliation',
  '/api/v2/admin/finance/simulate': '/api/v2/admin/finance/simulate',
  '/api/v2/admin/finance/wallet-protection':
      '/api/v2/admin/finance/wallet-protection',
  '/api/v2/admin/flags': '/api/v2/admin/flags',
  '/api/v2/admin/football-events/categories':
      '/api/v2/admin/football-events/categories',
  '/api/v2/admin/football-events/effects/expire':
      '/api/v2/admin/football-events/effects/expire',
  '/api/v2/admin/football-events/events':
      '/api/v2/admin/football-events/events',
  '/api/v2/admin/football-events/events/import':
      '/api/v2/admin/football-events/events/import',
  '/api/v2/admin/football-events/events/{event_id}/review':
      '/api/v2/admin/football-events/events/{event_id}/review',
  '/api/v2/admin/football-events/events/{event_id}/severity':
      '/api/v2/admin/football-events/events/{event_id}/severity',
  '/api/v2/admin/football-events/rules': '/api/v2/admin/football-events/rules',
  '/api/v2/admin/god-mode/audit-events': '/api/v2/admin/god-mode/audit-events',
  '/api/v2/admin/god-mode/bootstrap': '/api/v2/admin/god-mode/bootstrap',
  '/api/v2/admin/god-mode/commissions': '/api/v2/admin/god-mode/commissions',
  '/api/v2/admin/god-mode/competition-controls':
      '/api/v2/admin/god-mode/competition-controls',
  '/api/v2/admin/god-mode/high-risk-actions':
      '/api/v2/admin/god-mode/high-risk-actions',
  '/api/v2/admin/god-mode/liquidity/interventions':
      '/api/v2/admin/god-mode/liquidity/interventions',
  '/api/v2/admin/god-mode/payment-rails':
      '/api/v2/admin/god-mode/payment-rails',
  '/api/v2/admin/god-mode/payment-rails/health':
      '/api/v2/admin/god-mode/payment-rails/health',
  '/api/v2/admin/god-mode/roles': '/api/v2/admin/god-mode/roles',
  '/api/v2/admin/god-mode/treasury': '/api/v2/admin/god-mode/treasury',
  '/api/v2/admin/god-mode/treasury/dashboard':
      '/api/v2/admin/god-mode/treasury/dashboard',
  '/api/v2/admin/god-mode/treasury/withdrawals':
      '/api/v2/admin/god-mode/treasury/withdrawals',
  '/api/v2/admin/god-mode/withdrawal-controls':
      '/api/v2/admin/god-mode/withdrawal-controls',
  '/api/v2/admin/god-mode/withdrawals': '/api/v2/admin/god-mode/withdrawals',
  '/api/v2/admin/god-mode/withdrawals/summary':
      '/api/v2/admin/god-mode/withdrawals/summary',
  '/api/v2/admin/god-mode/withdrawals/{payout_request_id}':
      '/api/v2/admin/god-mode/withdrawals/{payout_request_id}',
  '/api/v2/admin/governance/proposals/{proposal_id}/status':
      '/api/v2/admin/governance/proposals/{proposal_id}/status',
  '/api/v2/admin/history-engagement/run-workers':
      '/api/v2/admin/history-engagement/run-workers',
  '/api/v2/admin/hosted-competitions': '/api/v2/admin/hosted-competitions',
  '/api/v2/admin/hosted-competitions/seed':
      '/api/v2/admin/hosted-competitions/seed',
  '/api/v2/admin/hosted-competitions/{competition_id}/finalize':
      '/api/v2/admin/hosted-competitions/{competition_id}/finalize',
  '/api/v2/admin/hosted-competitions/{competition_id}/launch':
      '/api/v2/admin/hosted-competitions/{competition_id}/launch',
  '/api/v2/admin/integrity-engine/incidents/{incident_id}/resolve':
      '/api/v2/admin/integrity-engine/incidents/{incident_id}/resolve',
  '/api/v2/admin/integrity-engine/scan': '/api/v2/admin/integrity-engine/scan',
  '/api/v2/admin/jackpot/balance': '/api/v2/admin/jackpot/balance',
  '/api/v2/admin/jackpot/runtime': '/api/v2/admin/jackpot/runtime',
  '/api/v2/admin/jackpot/trigger': '/api/v2/admin/jackpot/trigger',
  '/api/v2/admin/leaderboard/season/archive':
      '/api/v2/admin/leaderboard/season/archive',
  '/api/v2/admin/leaderboard/season/reset':
      '/api/v2/admin/leaderboard/season/reset',
  '/api/v2/admin/managers/audit-log': '/api/v2/admin/managers/audit-log',
  '/api/v2/admin/managers/catalog/{manager_id}/supply':
      '/api/v2/admin/managers/catalog/{manager_id}/supply',
  '/api/v2/admin/managers/competitions': '/api/v2/admin/managers/competitions',
  '/api/v2/admin/managers/competitions/{code}':
      '/api/v2/admin/managers/competitions/{code}',
  '/api/v2/admin/managers/competitions/{code}/orchestrate':
      '/api/v2/admin/managers/competitions/{code}/orchestrate',
  '/api/v2/admin/media-engine/creator-league/clubs/{club_id}/stadium-level':
      '/api/v2/admin/media-engine/creator-league/clubs/{club_id}/stadium-level',
  '/api/v2/admin/media-engine/creator-league/matches/{match_id}/analytics':
      '/api/v2/admin/media-engine/creator-league/matches/{match_id}/analytics',
  '/api/v2/admin/media-engine/creator-league/matches/{match_id}/settlement':
      '/api/v2/admin/media-engine/creator-league/matches/{match_id}/settlement',
  '/api/v2/admin/media-engine/creator-league/stadium-controls':
      '/api/v2/admin/media-engine/creator-league/stadium-controls',
  '/api/v2/admin/media-engine/exports': '/api/v2/admin/media-engine/exports',
  '/api/v2/admin/media-engine/highlights':
      '/api/v2/admin/media-engine/highlights',
  '/api/v2/admin/media-engine/highlights/{storage_key:path}/archive':
      '/api/v2/admin/media-engine/highlights/{storage_key:path}/archive',
  '/api/v2/admin/media-engine/share-exports/{export_id}/revenue-attributions':
      '/api/v2/admin/media-engine/share-exports/{export_id}/revenue-attributions',
  '/api/v2/admin/media-engine/snapshots':
      '/api/v2/admin/media-engine/snapshots',
  '/api/v2/admin/moderation/reports': '/api/v2/admin/moderation/reports',
  '/api/v2/admin/moderation/reports/summary':
      '/api/v2/admin/moderation/reports/summary',
  '/api/v2/admin/moderation/reports/{report_id}/assign':
      '/api/v2/admin/moderation/reports/{report_id}/assign',
  '/api/v2/admin/moderation/reports/{report_id}/resolve':
      '/api/v2/admin/moderation/reports/{report_id}/resolve',
  '/api/v2/admin/national-team-engine/competitions':
      '/api/v2/admin/national-team-engine/competitions',
  '/api/v2/admin/national-team-engine/competitions/seed-defaults':
      '/api/v2/admin/national-team-engine/competitions/seed-defaults',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads/rotate':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads/rotate',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads/{ad_id}':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads/{ad_id}',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/entries':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/entries',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/entries/lock':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/entries/lock',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/lifecycle/advance':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/lifecycle/advance',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/rentals/cleanup':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/rentals/cleanup',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/story-events/generate':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/story-events/generate',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/theme':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/theme',
  '/api/v2/admin/national-team-engine/entries/{entry_id}/squad':
      '/api/v2/admin/national-team-engine/entries/{entry_id}/squad',
  '/api/v2/admin/notifications/announcements':
      '/api/v2/admin/notifications/announcements',
  '/api/v2/admin/ops/alerts': '/api/v2/admin/ops/alerts',
  '/api/v2/admin/ops/audit': '/api/v2/admin/ops/audit',
  '/api/v2/admin/ops/broadcast-expiration':
      '/api/v2/admin/ops/broadcast-expiration',
  '/api/v2/admin/ops/broadcast-revenue': '/api/v2/admin/ops/broadcast-revenue',
  '/api/v2/admin/ops/club-market-valuations':
      '/api/v2/admin/ops/club-market-valuations',
  '/api/v2/admin/ops/dashboard': '/api/v2/admin/ops/dashboard',
  '/api/v2/admin/ops/fan-updates': '/api/v2/admin/ops/fan-updates',
  '/api/v2/admin/ops/identity-evolution':
      '/api/v2/admin/ops/identity-evolution',
  '/api/v2/admin/ops/integrity-scan': '/api/v2/admin/ops/integrity-scan',
  '/api/v2/admin/ops/media-generation': '/api/v2/admin/ops/media-generation',
  '/api/v2/admin/ops/media-retention': '/api/v2/admin/ops/media-retention',
  '/api/v2/admin/ops/national-team-rental-cleanup':
      '/api/v2/admin/ops/national-team-rental-cleanup',
  '/api/v2/admin/ops/ownership-groups/reputation':
      '/api/v2/admin/ops/ownership-groups/reputation',
  '/api/v2/admin/ops/platform-infra': '/api/v2/admin/ops/platform-infra',
  '/api/v2/admin/ops/stadium-ad-rotation':
      '/api/v2/admin/ops/stadium-ad-rotation',
  '/api/v2/admin/ops/tournament-storylines':
      '/api/v2/admin/ops/tournament-storylines',
  '/api/v2/admin/ownership-groups/reputation-cycle':
      '/api/v2/admin/ownership-groups/reputation-cycle',
  '/api/v2/admin/player-import/card-supply':
      '/api/v2/admin/player-import/card-supply',
  '/api/v2/admin/player-import/card-supply/csv':
      '/api/v2/admin/player-import/card-supply/csv',
  '/api/v2/admin/player-import/jobs': '/api/v2/admin/player-import/jobs',
  '/api/v2/admin/player-import/jobs/{job_id}':
      '/api/v2/admin/player-import/jobs/{job_id}',
  '/api/v2/admin/player-import/youth/generate':
      '/api/v2/admin/player-import/youth/generate',
  '/api/v2/admin/policies/country-policies':
      '/api/v2/admin/policies/country-policies',
  '/api/v2/admin/policies/documents': '/api/v2/admin/policies/documents',
  '/api/v2/admin/policies/documents/versions':
      '/api/v2/admin/policies/documents/versions',
  '/api/v2/admin/policies/regions/override':
      '/api/v2/admin/policies/regions/override',
  '/api/v2/admin/real-world/providers': '/api/v2/admin/real-world/providers',
  '/api/v2/admin/real-world/providers/{provider_id}/sync':
      '/api/v2/admin/real-world/providers/{provider_id}/sync',
  '/api/v2/admin/referrals/analytics/summary':
      '/api/v2/admin/referrals/analytics/summary',
  '/api/v2/admin/referrals/attributions':
      '/api/v2/admin/referrals/attributions',
  '/api/v2/admin/referrals/creators': '/api/v2/admin/referrals/creators',
  '/api/v2/admin/referrals/creators/{creator_id}':
      '/api/v2/admin/referrals/creators/{creator_id}',
  '/api/v2/admin/referrals/creators/{creator_id}/reward-freeze':
      '/api/v2/admin/referrals/creators/{creator_id}/reward-freeze',
  '/api/v2/admin/referrals/dashboard': '/api/v2/admin/referrals/dashboard',
  '/api/v2/admin/referrals/flags': '/api/v2/admin/referrals/flags',
  '/api/v2/admin/referrals/leaderboard': '/api/v2/admin/referrals/leaderboard',
  '/api/v2/admin/referrals/rewards/pending':
      '/api/v2/admin/referrals/rewards/pending',
  '/api/v2/admin/referrals/rewards/{reward_id}/review':
      '/api/v2/admin/referrals/rewards/{reward_id}/review',
  '/api/v2/admin/referrals/share-codes': '/api/v2/admin/referrals/share-codes',
  '/api/v2/admin/referrals/share-codes/{share_code_id}':
      '/api/v2/admin/referrals/share-codes/{share_code_id}',
  '/api/v2/admin/referrals/share-codes/{share_code_id}/block':
      '/api/v2/admin/referrals/share-codes/{share_code_id}/block',
  '/api/v2/admin/regen-universe/jobs/dna-evolution':
      '/api/v2/admin/regen-universe/jobs/dna-evolution',
  '/api/v2/admin/regen-universe/jobs/rivalry-detection':
      '/api/v2/admin/regen-universe/jobs/rivalry-detection',
  '/api/v2/admin/regen-universe/jobs/story-regeneration':
      '/api/v2/admin/regen-universe/jobs/story-regeneration',
  '/api/v2/admin/regen-universe/jobs/tournament-scheduling':
      '/api/v2/admin/regen-universe/jobs/tournament-scheduling',
  '/api/v2/admin/regen-universe/national-regens/preseed':
      '/api/v2/admin/regen-universe/national-regens/preseed',
  '/api/v2/admin/regen-universe/players/{player_id}/portrait/ban':
      '/api/v2/admin/regen-universe/players/{player_id}/portrait/ban',
  '/api/v2/admin/regen-universe/players/{player_id}/portrait/override':
      '/api/v2/admin/regen-universe/players/{player_id}/portrait/override',
  '/api/v2/admin/regen-universe/players/{player_id}/portrait/regenerate':
      '/api/v2/admin/regen-universe/players/{player_id}/portrait/regenerate',
  '/api/v2/admin/regen-universe/seasons':
      '/api/v2/admin/regen-universe/seasons',
  '/api/v2/admin/regen-universe/seasons/{season_id}/close':
      '/api/v2/admin/regen-universe/seasons/{season_id}/close',
  '/api/v2/admin/regen-universe/seasons/{season_id}/evolution':
      '/api/v2/admin/regen-universe/seasons/{season_id}/evolution',
  '/api/v2/admin/regen-universe/youth-tournaments':
      '/api/v2/admin/regen-universe/youth-tournaments',
  '/api/v2/admin/reward-engine/promo-pool/credits':
      '/api/v2/admin/reward-engine/promo-pool/credits',
  '/api/v2/admin/reward-engine/settlements':
      '/api/v2/admin/reward-engine/settlements',
  '/api/v2/admin/risk-ops/actions': '/api/v2/admin/risk-ops/actions',
  '/api/v2/admin/risk-ops/actions/{action_id}/release':
      '/api/v2/admin/risk-ops/actions/{action_id}/release',
  '/api/v2/admin/risk-ops/aml-cases': '/api/v2/admin/risk-ops/aml-cases',
  '/api/v2/admin/risk-ops/audit-logs': '/api/v2/admin/risk-ops/audit-logs',
  '/api/v2/admin/risk-ops/cases/{case_type}/{case_id}/resolve':
      '/api/v2/admin/risk-ops/cases/{case_type}/{case_id}/resolve',
  '/api/v2/admin/risk-ops/evaluate': '/api/v2/admin/risk-ops/evaluate',
  '/api/v2/admin/risk-ops/fraud-cases': '/api/v2/admin/risk-ops/fraud-cases',
  '/api/v2/admin/risk-ops/overview': '/api/v2/admin/risk-ops/overview',
  '/api/v2/admin/risk-ops/scan': '/api/v2/admin/risk-ops/scan',
  '/api/v2/admin/risk-ops/signals': '/api/v2/admin/risk-ops/signals',
  '/api/v2/admin/risk-ops/system-events':
      '/api/v2/admin/risk-ops/system-events',
  '/api/v2/admin/sponsorship/analytics': '/api/v2/admin/sponsorship/analytics',
  '/api/v2/admin/sponsorship/categories/{category}':
      '/api/v2/admin/sponsorship/categories/{category}',
  '/api/v2/admin/sponsorship/contracts/{contract_id}/review':
      '/api/v2/admin/sponsorship/contracts/{contract_id}/review',
  '/api/v2/admin/sponsorship/contracts/{contract_id}/settle-next':
      '/api/v2/admin/sponsorship/contracts/{contract_id}/settle-next',
  '/api/v2/admin/sponsorship/offers': '/api/v2/admin/sponsorship/offers',
  '/api/v2/admin/sponsorship/offers/{offer_id}/assign':
      '/api/v2/admin/sponsorship/offers/{offer_id}/assign',
  '/api/v2/admin/sponsorship/offers/{offer_id}/rule':
      '/api/v2/admin/sponsorship/offers/{offer_id}/rule',
  '/api/v2/admin/sponsorship/packages': '/api/v2/admin/sponsorship/packages',
  '/api/v2/admin/story-feed': '/api/v2/admin/story-feed',
  '/api/v2/admin/streamer-tournaments/policy':
      '/api/v2/admin/streamer-tournaments/policy',
  '/api/v2/admin/streamer-tournaments/risk-signals':
      '/api/v2/admin/streamer-tournaments/risk-signals',
  '/api/v2/admin/streamer-tournaments/risk-signals/{signal_id}/review':
      '/api/v2/admin/streamer-tournaments/risk-signals/{signal_id}/review',
  '/api/v2/admin/streamer-tournaments/{tournament_id}/review':
      '/api/v2/admin/streamer-tournaments/{tournament_id}/review',
  '/api/v2/admin/streamer-tournaments/{tournament_id}/settle':
      '/api/v2/admin/streamer-tournaments/{tournament_id}/settle',
  '/api/v2/admin/treasury/bank-accounts':
      '/api/v2/admin/treasury/bank-accounts',
  '/api/v2/admin/treasury/bank-accounts/{account_id}':
      '/api/v2/admin/treasury/bank-accounts/{account_id}',
  '/api/v2/admin/treasury/dashboard': '/api/v2/admin/treasury/dashboard',
  '/api/v2/admin/treasury/deposits': '/api/v2/admin/treasury/deposits',
  '/api/v2/admin/treasury/deposits/{deposit_id}/confirm':
      '/api/v2/admin/treasury/deposits/{deposit_id}/confirm',
  '/api/v2/admin/treasury/deposits/{deposit_id}/reject':
      '/api/v2/admin/treasury/deposits/{deposit_id}/reject',
  '/api/v2/admin/treasury/deposits/{deposit_id}/review':
      '/api/v2/admin/treasury/deposits/{deposit_id}/review',
  '/api/v2/admin/treasury/disputes': '/api/v2/admin/treasury/disputes',
  '/api/v2/admin/treasury/disputes/{dispute_id}':
      '/api/v2/admin/treasury/disputes/{dispute_id}',
  '/api/v2/admin/treasury/disputes/{dispute_id}/messages':
      '/api/v2/admin/treasury/disputes/{dispute_id}/messages',
  '/api/v2/admin/treasury/kyc': '/api/v2/admin/treasury/kyc',
  '/api/v2/admin/treasury/kyc/{profile_id}/review':
      '/api/v2/admin/treasury/kyc/{profile_id}/review',
  '/api/v2/admin/treasury/settings': '/api/v2/admin/treasury/settings',
  '/api/v2/admin/treasury/withdrawal-batches':
      '/api/v2/admin/treasury/withdrawal-batches',
  '/api/v2/admin/treasury/withdrawals': '/api/v2/admin/treasury/withdrawals',
  '/api/v2/admin/treasury/withdrawals/{withdrawal_id}/reviews':
      '/api/v2/admin/treasury/withdrawals/{withdrawal_id}/reviews',
  '/api/v2/admin/treasury/withdrawals/{withdrawal_id}/status':
      '/api/v2/admin/treasury/withdrawals/{withdrawal_id}/status',
  '/api/v2/admin/wallets/market-topups': '/api/v2/admin/wallets/market-topups',
  '/api/v2/admin/wallets/market-topups/quote':
      '/api/v2/admin/wallets/market-topups/quote',
  '/api/v2/admin/wallets/market-topups/{topup_id}/status':
      '/api/v2/admin/wallets/market-topups/{topup_id}/status',
  '/api/v2/admin/wallets/purchase-orders':
      '/api/v2/admin/wallets/purchase-orders',
  '/api/v2/admin/wallets/purchase-orders/{order_id}/status':
      '/api/v2/admin/wallets/purchase-orders/{order_id}/status',
  '/api/v2/admin/world/clubs/{club_id}/context':
      '/api/v2/admin/world/clubs/{club_id}/context',
  '/api/v2/admin/world/cultures/{culture_key}':
      '/api/v2/admin/world/cultures/{culture_key}',
  '/api/v2/admin/world/narratives/{narrative_slug}':
      '/api/v2/admin/world/narratives/{narrative_slug}',
  '/api/v2/ads/create': '/api/v2/ads/create',
  '/api/v2/ads/performance': '/api/v2/ads/performance',
  '/api/v2/agents': '/api/v2/agents',
  '/api/v2/agents/config': '/api/v2/agents/config',
  '/api/v2/agents/performance': '/api/v2/agents/performance',
  '/api/v2/agents/run': '/api/v2/agents/run',
  '/api/v2/agents/summary': '/api/v2/agents/summary',
  '/api/v2/ai-manager/autopilot/live-decision':
      '/api/v2/ai-manager/autopilot/live-decision',
  '/api/v2/ai-manager/autopilot/run': '/api/v2/ai-manager/autopilot/run',
  '/api/v2/ai-manager/economy/reward-preview':
      '/api/v2/ai-manager/economy/reward-preview',
  '/api/v2/ai-manager/profiles/{club_id}':
      '/api/v2/ai-manager/profiles/{club_id}',
  '/api/v2/ai-reporter/feed': '/api/v2/ai-reporter/feed',
  '/api/v2/ai-reporter/run': '/api/v2/ai-reporter/run',
  '/api/v2/ai/leagues': '/api/v2/ai/leagues',
  '/api/v2/ai/match/{match_id}': '/api/v2/ai/match/{match_id}',
  '/api/v2/analytics/clip/{clip_id}': '/api/v2/analytics/clip/{clip_id}',
  '/api/v2/analytics/dashboard/drop-off':
      '/api/v2/analytics/dashboard/drop-off',
  '/api/v2/analytics/dashboard/top-clips':
      '/api/v2/analytics/dashboard/top-clips',
  '/api/v2/analytics/device-fingerprint':
      '/api/v2/analytics/device-fingerprint',
  '/api/v2/analytics/events': '/api/v2/analytics/events',
  '/api/v2/analytics/frontend': '/api/v2/analytics/frontend',
  '/api/v2/analytics/influencer-leaderboard':
      '/api/v2/analytics/influencer-leaderboard',
  '/api/v2/attachments': '/api/v2/attachments',
  '/api/v2/attachments/{attachment_id}': '/api/v2/attachments/{attachment_id}',
  '/api/v2/auth/change-password': '/api/v2/auth/change-password',
  '/api/v2/auth/confirm-email': '/api/v2/auth/confirm-email',
  '/api/v2/auth/login': '/api/v2/auth/login',
  '/api/v2/auth/logout': '/api/v2/auth/logout',
  '/api/v2/auth/me': '/api/v2/auth/me',
  '/api/v2/auth/recovery/request': '/api/v2/auth/recovery/request',
  '/api/v2/auth/recovery/reset': '/api/v2/auth/recovery/reset',
  '/api/v2/auth/refresh': '/api/v2/auth/refresh',
  '/api/v2/auth/signup/creator': '/api/v2/auth/signup/creator',
  '/api/v2/auth/signup/trader': '/api/v2/auth/signup/trader',
  '/api/v2/auth/signup/user': '/api/v2/auth/signup/user',
  '/api/v2/awards/categories': '/api/v2/awards/categories',
  '/api/v2/awards/ceremony': '/api/v2/awards/ceremony',
  '/api/v2/awards/ceremony/tickets': '/api/v2/awards/ceremony/tickets',
  '/api/v2/awards/ceremony/vote': '/api/v2/awards/ceremony/vote',
  '/api/v2/awards/nominees': '/api/v2/awards/nominees',
  '/api/v2/awards/winners': '/api/v2/awards/winners',
  '/api/v2/bank-accounts': '/api/v2/bank-accounts',
  '/api/v2/bank-accounts/{bank_account_id}':
      '/api/v2/bank-accounts/{bank_account_id}',
  '/api/v2/bets/history': '/api/v2/bets/history',
  '/api/v2/bets/odds/{match_id}': '/api/v2/bets/odds/{match_id}',
  '/api/v2/bets/place': '/api/v2/bets/place',
  '/api/v2/bets/preferences': '/api/v2/bets/preferences',
  '/api/v2/broadcast-rights/auctions/{auction_id}/bids':
      '/api/v2/broadcast-rights/auctions/{auction_id}/bids',
  '/api/v2/broadcast-rights/competitions/{competition_id}':
      '/api/v2/broadcast-rights/competitions/{competition_id}',
  '/api/v2/broadcast-rights/competitions/{competition_id}/acquire':
      '/api/v2/broadcast-rights/competitions/{competition_id}/acquire',
  '/api/v2/broadcast-rights/competitions/{competition_id}/auctions':
      '/api/v2/broadcast-rights/competitions/{competition_id}/auctions',
  '/api/v2/broadcast-rights/matches/{match_id}/access':
      '/api/v2/broadcast-rights/matches/{match_id}/access',
  '/api/v2/broadcast-rights/matches/{match_id}/distribute':
      '/api/v2/broadcast-rights/matches/{match_id}/distribute',
  '/api/v2/broadcast-rights/{right_id}/grants':
      '/api/v2/broadcast-rights/{right_id}/grants',
  '/api/v2/broadcast/channels': '/api/v2/broadcast/channels',
  '/api/v2/broadcast/channels/{channel_id}/audio/stems/stream':
      '/api/v2/broadcast/channels/{channel_id}/audio/stems/stream',
  '/api/v2/broadcast/channels/{channel_id}/join':
      '/api/v2/broadcast/channels/{channel_id}/join',
  '/api/v2/broadcast/channels/{channel_id}/stream':
      '/api/v2/broadcast/channels/{channel_id}/stream',
  '/api/v2/broadcast/home': '/api/v2/broadcast/home',
  '/api/v2/broadcast/pay': '/api/v2/broadcast/pay',
  '/api/v2/broadcast/{match_id}': '/api/v2/broadcast/{match_id}',
  '/api/v2/calendar-engine/dashboard': '/api/v2/calendar-engine/dashboard',
  '/api/v2/calendar-engine/events': '/api/v2/calendar-engine/events',
  '/api/v2/calendar-engine/lifecycle-runs':
      '/api/v2/calendar-engine/lifecycle-runs',
  '/api/v2/calendar-engine/pause-status':
      '/api/v2/calendar-engine/pause-status',
  '/api/v2/calendar-engine/seasons': '/api/v2/calendar-engine/seasons',
  '/api/v2/campaigns': '/api/v2/campaigns',
  '/api/v2/campaigns/create': '/api/v2/campaigns/create',
  '/api/v2/campaigns/{id}/accept': '/api/v2/campaigns/{id}/accept',
  '/api/v2/campaigns/{id}/apply': '/api/v2/campaigns/{id}/apply',
  '/api/v2/campaigns/{id}/performance': '/api/v2/campaigns/{id}/performance',
  '/api/v2/career/create': '/api/v2/career/create',
  '/api/v2/career/retire': '/api/v2/career/retire',
  '/api/v2/career/train': '/api/v2/career/train',
  '/api/v2/career/transfer': '/api/v2/career/transfer',
  '/api/v2/career/{user_id}': '/api/v2/career/{user_id}',
  '/api/v2/challenges/links/{link_code}':
      '/api/v2/challenges/links/{link_code}',
  '/api/v2/challenges/{challenge_id}': '/api/v2/challenges/{challenge_id}',
  '/api/v2/challenges/{challenge_id}/accept':
      '/api/v2/challenges/{challenge_id}/accept',
  '/api/v2/challenges/{challenge_id}/links':
      '/api/v2/challenges/{challenge_id}/links',
  '/api/v2/challenges/{challenge_id}/publish':
      '/api/v2/challenges/{challenge_id}/publish',
  '/api/v2/challenges/{challenge_id}/share-events':
      '/api/v2/challenges/{challenge_id}/share-events',
  '/api/v2/champions-league/knockout-bracket':
      '/api/v2/champions-league/knockout-bracket',
  '/api/v2/champions-league/league-phase/table':
      '/api/v2/champions-league/league-phase/table',
  '/api/v2/champions-league/playoff-bracket':
      '/api/v2/champions-league/playoff-bracket',
  '/api/v2/champions-league/prize-pool/preview':
      '/api/v2/champions-league/prize-pool/preview',
  '/api/v2/champions-league/qualification-map':
      '/api/v2/champions-league/qualification-map',
  '/api/v2/club-infra/clubs/{club_id}': '/api/v2/club-infra/clubs/{club_id}',
  '/api/v2/club-infra/clubs/{club_id}/support':
      '/api/v2/club-infra/clubs/{club_id}/support',
  '/api/v2/club-infra/my': '/api/v2/club-infra/my',
  '/api/v2/club-infra/my/facilities/upgrade':
      '/api/v2/club-infra/my/facilities/upgrade',
  '/api/v2/club-infra/my/stadium/upgrade':
      '/api/v2/club-infra/my/stadium/upgrade',
  '/api/v2/club/identity': '/api/v2/club/identity',
  '/api/v2/clubs': '/api/v2/clubs',
  '/api/v2/clubs/catalog': '/api/v2/clubs/catalog',
  '/api/v2/clubs/catalog/purchase': '/api/v2/clubs/catalog/purchase',
  '/api/v2/clubs/list': '/api/v2/clubs/list',
  '/api/v2/clubs/marketplace': '/api/v2/clubs/marketplace',
  '/api/v2/clubs/offer': '/api/v2/clubs/offer',
  '/api/v2/clubs/sale-market/listings': '/api/v2/clubs/sale-market/listings',
  '/api/v2/clubs/{club_id}': '/api/v2/clubs/{club_id}',
  '/api/v2/clubs/{club_id}/academy': '/api/v2/clubs/{club_id}/academy',
  '/api/v2/clubs/{club_id}/academy/players':
      '/api/v2/clubs/{club_id}/academy/players',
  '/api/v2/clubs/{club_id}/academy/players/{player_id}':
      '/api/v2/clubs/{club_id}/academy/players/{player_id}',
  '/api/v2/clubs/{club_id}/academy/programs':
      '/api/v2/clubs/{club_id}/academy/programs',
  '/api/v2/clubs/{club_id}/academy/training-cycles':
      '/api/v2/clubs/{club_id}/academy/training-cycles',
  '/api/v2/clubs/{club_id}/badge': '/api/v2/clubs/{club_id}/badge',
  '/api/v2/clubs/{club_id}/branding': '/api/v2/clubs/{club_id}/branding',
  '/api/v2/clubs/{club_id}/buy-tokens': '/api/v2/clubs/{club_id}/buy-tokens',
  '/api/v2/clubs/{club_id}/challenges': '/api/v2/clubs/{club_id}/challenges',
  '/api/v2/clubs/{club_id}/contracts': '/api/v2/clubs/{club_id}/contracts',
  '/api/v2/clubs/{club_id}/dynasty': '/api/v2/clubs/{club_id}/dynasty',
  '/api/v2/clubs/{club_id}/dynasty/history':
      '/api/v2/clubs/{club_id}/dynasty/history',
  '/api/v2/clubs/{club_id}/eras': '/api/v2/clubs/{club_id}/eras',
  '/api/v2/clubs/{club_id}/fans': '/api/v2/clubs/{club_id}/fans',
  '/api/v2/clubs/{club_id}/finances': '/api/v2/clubs/{club_id}/finances',
  '/api/v2/clubs/{club_id}/finances/budget':
      '/api/v2/clubs/{club_id}/finances/budget',
  '/api/v2/clubs/{club_id}/finances/cashflow':
      '/api/v2/clubs/{club_id}/finances/cashflow',
  '/api/v2/clubs/{club_id}/finances/ledger':
      '/api/v2/clubs/{club_id}/finances/ledger',
  '/api/v2/clubs/{club_id}/honors-timeline':
      '/api/v2/clubs/{club_id}/honors-timeline',
  '/api/v2/clubs/{club_id}/identity': '/api/v2/clubs/{club_id}/identity',
  '/api/v2/clubs/{club_id}/identity/metrics':
      '/api/v2/clubs/{club_id}/identity/metrics',
  '/api/v2/clubs/{club_id}/identity/metrics/refresh':
      '/api/v2/clubs/{club_id}/identity/metrics/refresh',
  '/api/v2/clubs/{club_id}/jerseys': '/api/v2/clubs/{club_id}/jerseys',
  '/api/v2/clubs/{club_id}/jerseys/{jersey_id}':
      '/api/v2/clubs/{club_id}/jerseys/{jersey_id}',
  '/api/v2/clubs/{club_id}/ownership': '/api/v2/clubs/{club_id}/ownership',
  '/api/v2/clubs/{club_id}/prestige': '/api/v2/clubs/{club_id}/prestige',
  '/api/v2/clubs/{club_id}/proposals': '/api/v2/clubs/{club_id}/proposals',
  '/api/v2/clubs/{club_id}/purchases': '/api/v2/clubs/{club_id}/purchases',
  '/api/v2/clubs/{club_id}/reputation': '/api/v2/clubs/{club_id}/reputation',
  '/api/v2/clubs/{club_id}/reputation/history':
      '/api/v2/clubs/{club_id}/reputation/history',
  '/api/v2/clubs/{club_id}/rivalries': '/api/v2/clubs/{club_id}/rivalries',
  '/api/v2/clubs/{club_id}/rivalries/{opponent_club_id}':
      '/api/v2/clubs/{club_id}/rivalries/{opponent_club_id}',
  '/api/v2/clubs/{club_id}/sale-market': '/api/v2/clubs/{club_id}/sale-market',
  '/api/v2/clubs/{club_id}/sale-market/assistant':
      '/api/v2/clubs/{club_id}/sale-market/assistant',
  '/api/v2/clubs/{club_id}/sale-market/history':
      '/api/v2/clubs/{club_id}/sale-market/history',
  '/api/v2/clubs/{club_id}/sale-market/inquiries':
      '/api/v2/clubs/{club_id}/sale-market/inquiries',
  '/api/v2/clubs/{club_id}/sale-market/inquiries/{inquiry_id}/respond':
      '/api/v2/clubs/{club_id}/sale-market/inquiries/{inquiry_id}/respond',
  '/api/v2/clubs/{club_id}/sale-market/listing':
      '/api/v2/clubs/{club_id}/sale-market/listing',
  '/api/v2/clubs/{club_id}/sale-market/listing/cancel':
      '/api/v2/clubs/{club_id}/sale-market/listing/cancel',
  '/api/v2/clubs/{club_id}/sale-market/listing/instant-sell':
      '/api/v2/clubs/{club_id}/sale-market/listing/instant-sell',
  '/api/v2/clubs/{club_id}/sale-market/offers':
      '/api/v2/clubs/{club_id}/sale-market/offers',
  '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/accept':
      '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/accept',
  '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/counter':
      '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/counter',
  '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/reject':
      '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/reject',
  '/api/v2/clubs/{club_id}/sale-market/transfer':
      '/api/v2/clubs/{club_id}/sale-market/transfer',
  '/api/v2/clubs/{club_id}/scouting': '/api/v2/clubs/{club_id}/scouting',
  '/api/v2/clubs/{club_id}/scouting-intelligence/academy-supply-signals':
      '/api/v2/clubs/{club_id}/scouting-intelligence/academy-supply-signals',
  '/api/v2/clubs/{club_id}/scouting-intelligence/assignments':
      '/api/v2/clubs/{club_id}/scouting-intelligence/assignments',
  '/api/v2/clubs/{club_id}/scouting-intelligence/badges':
      '/api/v2/clubs/{club_id}/scouting-intelligence/badges',
  '/api/v2/clubs/{club_id}/scouting-intelligence/lifecycle':
      '/api/v2/clubs/{club_id}/scouting-intelligence/lifecycle',
  '/api/v2/clubs/{club_id}/scouting-intelligence/manager-profiles':
      '/api/v2/clubs/{club_id}/scouting-intelligence/manager-profiles',
  '/api/v2/clubs/{club_id}/scouting-intelligence/missions':
      '/api/v2/clubs/{club_id}/scouting-intelligence/missions',
  '/api/v2/clubs/{club_id}/scouting-intelligence/missions/{mission_id}':
      '/api/v2/clubs/{club_id}/scouting-intelligence/missions/{mission_id}',
  '/api/v2/clubs/{club_id}/scouting-intelligence/missions/{mission_id}/complete':
      '/api/v2/clubs/{club_id}/scouting-intelligence/missions/{mission_id}/complete',
  '/api/v2/clubs/{club_id}/scouting-intelligence/networks':
      '/api/v2/clubs/{club_id}/scouting-intelligence/networks',
  '/api/v2/clubs/{club_id}/scouting-intelligence/planning':
      '/api/v2/clubs/{club_id}/scouting-intelligence/planning',
  '/api/v2/clubs/{club_id}/scouting/assignments':
      '/api/v2/clubs/{club_id}/scouting/assignments',
  '/api/v2/clubs/{club_id}/scouting/prospects':
      '/api/v2/clubs/{club_id}/scouting/prospects',
  '/api/v2/clubs/{club_id}/scouting/prospects/{prospect_id}':
      '/api/v2/clubs/{club_id}/scouting/prospects/{prospect_id}',
  '/api/v2/clubs/{club_id}/season-honors':
      '/api/v2/clubs/{club_id}/season-honors',
  '/api/v2/clubs/{club_id}/sell-tokens': '/api/v2/clubs/{club_id}/sell-tokens',
  '/api/v2/clubs/{club_id}/showcase': '/api/v2/clubs/{club_id}/showcase',
  '/api/v2/clubs/{club_id}/sponsorships':
      '/api/v2/clubs/{club_id}/sponsorships',
  '/api/v2/clubs/{club_id}/sponsorships/assets':
      '/api/v2/clubs/{club_id}/sponsorships/assets',
  '/api/v2/clubs/{club_id}/sponsorships/catalog':
      '/api/v2/clubs/{club_id}/sponsorships/catalog',
  '/api/v2/clubs/{club_id}/sponsorships/contracts':
      '/api/v2/clubs/{club_id}/sponsorships/contracts',
  '/api/v2/clubs/{club_id}/sponsorships/contracts/{contract_id}':
      '/api/v2/clubs/{club_id}/sponsorships/contracts/{contract_id}',
  '/api/v2/clubs/{club_id}/squad': '/api/v2/clubs/{club_id}/squad',
  '/api/v2/clubs/{club_id}/treasury': '/api/v2/clubs/{club_id}/treasury',
  '/api/v2/clubs/{club_id}/trophies': '/api/v2/clubs/{club_id}/trophies',
  '/api/v2/clubs/{club_id}/trophy-cabinet':
      '/api/v2/clubs/{club_id}/trophy-cabinet',
  '/api/v2/clubs/{club_id}/valuation': '/api/v2/clubs/{club_id}/valuation',
  '/api/v2/clubs/{club_id}/vote': '/api/v2/clubs/{club_id}/vote',
  '/api/v2/clubs/{club_id}/youth-pipeline':
      '/api/v2/clubs/{club_id}/youth-pipeline',
  '/api/v2/commentary/profiles': '/api/v2/commentary/profiles',
  '/api/v2/commentary/select': '/api/v2/commentary/select',
  '/api/v2/community/creator-clubs/{club_id}/fan-competitions':
      '/api/v2/community/creator-clubs/{club_id}/fan-competitions',
  '/api/v2/community/creator-clubs/{club_id}/fan-groups':
      '/api/v2/community/creator-clubs/{club_id}/fan-groups',
  '/api/v2/community/creator-clubs/{club_id}/fan-state':
      '/api/v2/community/creator-clubs/{club_id}/fan-state',
  '/api/v2/community/creator-clubs/{club_id}/follow':
      '/api/v2/community/creator-clubs/{club_id}/follow',
  '/api/v2/community/creator-matches/{match_id}/chat-room':
      '/api/v2/community/creator-matches/{match_id}/chat-room',
  '/api/v2/community/creator-matches/{match_id}/chat-room/messages':
      '/api/v2/community/creator-matches/{match_id}/chat-room/messages',
  '/api/v2/community/creator-matches/{match_id}/fan-wall':
      '/api/v2/community/creator-matches/{match_id}/fan-wall',
  '/api/v2/community/creator-matches/{match_id}/rivalry-signals':
      '/api/v2/community/creator-matches/{match_id}/rivalry-signals',
  '/api/v2/community/creator-matches/{match_id}/tactical-advice':
      '/api/v2/community/creator-matches/{match_id}/tactical-advice',
  '/api/v2/community/digest': '/api/v2/community/digest',
  '/api/v2/community/fan-competitions/{fan_competition_id}/join':
      '/api/v2/community/fan-competitions/{fan_competition_id}/join',
  '/api/v2/community/fan-groups/{group_id}/join':
      '/api/v2/community/fan-groups/{group_id}/join',
  '/api/v2/community/live-threads': '/api/v2/community/live-threads',
  '/api/v2/community/live-threads/{thread_id}':
      '/api/v2/community/live-threads/{thread_id}',
  '/api/v2/community/live-threads/{thread_id}/messages':
      '/api/v2/community/live-threads/{thread_id}/messages',
  '/api/v2/community/private-messages/threads':
      '/api/v2/community/private-messages/threads',
  '/api/v2/community/private-messages/threads/{thread_id}':
      '/api/v2/community/private-messages/threads/{thread_id}',
  '/api/v2/community/private-messages/threads/{thread_id}/messages':
      '/api/v2/community/private-messages/threads/{thread_id}/messages',
  '/api/v2/community/watchlist': '/api/v2/community/watchlist',
  '/api/v2/community/watchlist/{competition_key}':
      '/api/v2/community/watchlist/{competition_key}',
  '/api/v2/competitions': '/api/v2/competitions',
  '/api/v2/competitions/admin': '/api/v2/competitions/admin',
  '/api/v2/competitions/admin/{code}': '/api/v2/competitions/admin/{code}',
  '/api/v2/competitions/admin/{code}/orchestrate':
      '/api/v2/competitions/admin/{code}/orchestrate',
  '/api/v2/competitions/create': '/api/v2/competitions/create',
  '/api/v2/competitions/join': '/api/v2/competitions/join',
  '/api/v2/competitions/players/{subject_id}/progression':
      '/api/v2/competitions/players/{subject_id}/progression',
  '/api/v2/competitions/records/{competition_id}':
      '/api/v2/competitions/records/{competition_id}',
  '/api/v2/competitions/runtime/{code}': '/api/v2/competitions/runtime/{code}',
  '/api/v2/competitions/{competition_id}':
      '/api/v2/competitions/{competition_id}',
  '/api/v2/competitions/{competition_id}/advance':
      '/api/v2/competitions/{competition_id}/advance',
  '/api/v2/competitions/{competition_id}/finalize':
      '/api/v2/competitions/{competition_id}/finalize',
  '/api/v2/competitions/{competition_id}/financials':
      '/api/v2/competitions/{competition_id}/financials',
  '/api/v2/competitions/{competition_id}/fixtures':
      '/api/v2/competitions/{competition_id}/fixtures',
  '/api/v2/competitions/{competition_id}/invites':
      '/api/v2/competitions/{competition_id}/invites',
  '/api/v2/competitions/{competition_id}/invites/accept':
      '/api/v2/competitions/{competition_id}/invites/accept',
  '/api/v2/competitions/{competition_id}/join':
      '/api/v2/competitions/{competition_id}/join',
  '/api/v2/competitions/{competition_id}/launch':
      '/api/v2/competitions/{competition_id}/launch',
  '/api/v2/competitions/{competition_id}/leave':
      '/api/v2/competitions/{competition_id}/leave',
  '/api/v2/competitions/{competition_id}/matches/{match_id}/events':
      '/api/v2/competitions/{competition_id}/matches/{match_id}/events',
  '/api/v2/competitions/{competition_id}/matches/{match_id}/result':
      '/api/v2/competitions/{competition_id}/matches/{match_id}/result',
  '/api/v2/competitions/{competition_id}/publish':
      '/api/v2/competitions/{competition_id}/publish',
  '/api/v2/competitions/{competition_id}/rewards':
      '/api/v2/competitions/{competition_id}/rewards',
  '/api/v2/competitions/{competition_id}/rounds':
      '/api/v2/competitions/{competition_id}/rounds',
  '/api/v2/competitions/{competition_id}/schedule/jobs':
      '/api/v2/competitions/{competition_id}/schedule/jobs',
  '/api/v2/competitions/{competition_id}/schedule/jobs/{job_id}':
      '/api/v2/competitions/{competition_id}/schedule/jobs/{job_id}',
  '/api/v2/competitions/{competition_id}/schedule/preview':
      '/api/v2/competitions/{competition_id}/schedule/preview',
  '/api/v2/competitions/{competition_id}/seed':
      '/api/v2/competitions/{competition_id}/seed',
  '/api/v2/competitions/{competition_id}/standings':
      '/api/v2/competitions/{competition_id}/standings',
  '/api/v2/competitions/{competition_id}/summary':
      '/api/v2/competitions/{competition_id}/summary',
  '/api/v2/competitive-integrity/fast-game/runs':
      '/api/v2/competitive-integrity/fast-game/runs',
  '/api/v2/competitive-integrity/fast-game/runs/{run_id}':
      '/api/v2/competitive-integrity/fast-game/runs/{run_id}',
  '/api/v2/competitive-integrity/fast-game/runs/{run_id}/play':
      '/api/v2/competitive-integrity/fast-game/runs/{run_id}/play',
  '/api/v2/competitive-integrity/managers':
      '/api/v2/competitive-integrity/managers',
  '/api/v2/competitive-integrity/managers/candidates':
      '/api/v2/competitive-integrity/managers/candidates',
  '/api/v2/competitive-integrity/managers/{manager_id}/instructions':
      '/api/v2/competitive-integrity/managers/{manager_id}/instructions',
  '/api/v2/competitive-integrity/matches':
      '/api/v2/competitive-integrity/matches',
  '/api/v2/competitive-integrity/matches/{match_id}':
      '/api/v2/competitive-integrity/matches/{match_id}',
  '/api/v2/competitive-integrity/matches/{match_id}/execute':
      '/api/v2/competitive-integrity/matches/{match_id}/execute',
  '/api/v2/competitive-integrity/notifications/events':
      '/api/v2/competitive-integrity/notifications/events',
  '/api/v2/config/current': '/api/v2/config/current',
  '/api/v2/config/update': '/api/v2/config/update',
  '/api/v2/conversations': '/api/v2/conversations',
  '/api/v2/conversations/start': '/api/v2/conversations/start',
  '/api/v2/conversations/{conversation_id}/message':
      '/api/v2/conversations/{conversation_id}/message',
  '/api/v2/conversations/{conversation_id}/messages':
      '/api/v2/conversations/{conversation_id}/messages',
  '/api/v2/conversations/{conversation_id}/status':
      '/api/v2/conversations/{conversation_id}/status',
  '/api/v2/competitions/creator-league/financial-report':
      '/api/v2/competitions/creator-league/financial-report',
  '/api/v2/competitions/creator-league/financial-settlements':
      '/api/v2/competitions/creator-league/financial-settlements',
  '/api/v2/competitions/creator-league/financial-settlements/{settlement_id}/approve':
      '/api/v2/competitions/creator-league/financial-settlements/{settlement_id}/approve',
  '/api/v2/creator-campaigns': '/api/v2/creator-campaigns',
  '/api/v2/creator-campaigns/me': '/api/v2/creator-campaigns/me',
  '/api/v2/creator-campaigns/{campaign_id}':
      '/api/v2/creator-campaigns/{campaign_id}',
  '/api/v2/creator-campaigns/{campaign_id}/metrics':
      '/api/v2/creator-campaigns/{campaign_id}/metrics',
  '/api/v2/creator-campaigns/{campaign_id}/snapshot':
      '/api/v2/creator-campaigns/{campaign_id}/snapshot',
  '/api/v2/creator-campaigns/{campaign_id}/snapshots':
      '/api/v2/creator-campaigns/{campaign_id}/snapshots',
  '/api/v2/creator-league': '/api/v2/creator-league',
  '/api/v2/creator-league/config': '/api/v2/creator-league/config',
  '/api/v2/creator-league/financial-report':
      '/api/v2/creator-league/financial-report',
  '/api/v2/creator-league/financial-settlements':
      '/api/v2/creator-league/financial-settlements',
  '/api/v2/creator-league/financial-settlements/{settlement_id}/approve':
      '/api/v2/creator-league/financial-settlements/{settlement_id}/approve',
  '/api/v2/creator-league/live-priority':
      '/api/v2/creator-league/live-priority',
  '/api/v2/creator-league/reset': '/api/v2/creator-league/reset',
  '/api/v2/creator-league/season-tiers/{season_tier_id}/standings':
      '/api/v2/creator-league/season-tiers/{season_tier_id}/standings',
  '/api/v2/creator-league/seasons': '/api/v2/creator-league/seasons',
  '/api/v2/creator-league/seasons/{season_id}':
      '/api/v2/creator-league/seasons/{season_id}',
  '/api/v2/creator-league/seasons/{season_id}/pause':
      '/api/v2/creator-league/seasons/{season_id}/pause',
  '/api/v2/creator-league/tiers': '/api/v2/creator-league/tiers',
  '/api/v2/creator-league/tiers/{tier_id}':
      '/api/v2/creator-league/tiers/{tier_id}',
  '/api/v2/creator/application': '/api/v2/creator/application',
  '/api/v2/creator/apply': '/api/v2/creator/apply',
  '/api/v2/creator/cards': '/api/v2/creator/cards',
  '/api/v2/creator/cards/listings': '/api/v2/creator/cards/listings',
  '/api/v2/creator/cards/listings/{listing_id}/buy':
      '/api/v2/creator/cards/listings/{listing_id}/buy',
  '/api/v2/creator/cards/loans/{loan_id}/return':
      '/api/v2/creator/cards/loans/{loan_id}/return',
  '/api/v2/creator/cards/swap': '/api/v2/creator/cards/swap',
  '/api/v2/creator/cards/{creator_card_id}/list':
      '/api/v2/creator/cards/{creator_card_id}/list',
  '/api/v2/creator/cards/{creator_card_id}/loan':
      '/api/v2/creator/cards/{creator_card_id}/loan',
  '/api/v2/creator/clubs/{club_id}/fan-share-market':
      '/api/v2/creator/clubs/{club_id}/fan-share-market',
  '/api/v2/creator/clubs/{club_id}/fan-share-market/distributions':
      '/api/v2/creator/clubs/{club_id}/fan-share-market/distributions',
  '/api/v2/creator/clubs/{club_id}/fan-share-market/holding':
      '/api/v2/creator/clubs/{club_id}/fan-share-market/holding',
  '/api/v2/creator/clubs/{club_id}/fan-share-market/purchase':
      '/api/v2/creator/clubs/{club_id}/fan-share-market/purchase',
  '/api/v2/creator/verify-email': '/api/v2/creator/verify-email',
  '/api/v2/creator/verify-phone': '/api/v2/creator/verify-phone',
  '/api/v2/creators/marketplace': '/api/v2/creators/marketplace',
  '/api/v2/creators/me/competitions': '/api/v2/creators/me/competitions',
  '/api/v2/creators/me/copilot/analyze': '/api/v2/creators/me/copilot/analyze',
  '/api/v2/creators/me/finance': '/api/v2/creators/me/finance',
  '/api/v2/creators/me/insights': '/api/v2/creators/me/insights',
  '/api/v2/creators/me/reputation': '/api/v2/creators/me/reputation',
  '/api/v2/creators/me/summary': '/api/v2/creators/me/summary',
  '/api/v2/creators/profile': '/api/v2/creators/profile',
  '/api/v2/creators/profile/me': '/api/v2/creators/profile/me',
  '/api/v2/creators/{handle}': '/api/v2/creators/{handle}',
  '/api/v2/daily-challenges': '/api/v2/daily-challenges',
  '/api/v2/daily-challenges/me': '/api/v2/daily-challenges/me',
  '/api/v2/daily-challenges/{challenge_key}/claim':
      '/api/v2/daily-challenges/{challenge_key}/claim',
  '/api/v2/diagnostics': '/api/v2/diagnostics',
  '/api/v2/discovery/home': '/api/v2/discovery/home',
  '/api/v2/discovery/saved-searches': '/api/v2/discovery/saved-searches',
  '/api/v2/discovery/saved-searches/{search_id}':
      '/api/v2/discovery/saved-searches/{search_id}',
  '/api/v2/discovery/search': '/api/v2/discovery/search',
  '/api/v2/disputes': '/api/v2/disputes',
  '/api/v2/disputes/me': '/api/v2/disputes/me',
  '/api/v2/disputes/{dispute_id}': '/api/v2/disputes/{dispute_id}',
  '/api/v2/disputes/{dispute_id}/messages':
      '/api/v2/disputes/{dispute_id}/messages',
  '/api/v2/dynasty': '/api/v2/dynasty',
  '/api/v2/dynasty/leaderboard': '/api/v2/dynasty/leaderboard',
  '/api/v2/economy/fx/quote': '/api/v2/economy/fx/quote',
  '/api/v2/economy/gift-catalog': '/api/v2/economy/gift-catalog',
  '/api/v2/economy/service-pricing': '/api/v2/economy/service-pricing',
  '/api/v2/engagement/achievements': '/api/v2/engagement/achievements',
  '/api/v2/engagement/achievements/me': '/api/v2/engagement/achievements/me',
  '/api/v2/engagement/milestones/me': '/api/v2/engagement/milestones/me',
  '/api/v2/engagement/sync': '/api/v2/engagement/sync',
  '/api/v2/enter': '/api/v2/enter',
  '/api/v2/events/clip': '/api/v2/events/clip',
  '/api/v2/events/today': '/api/v2/events/today',
  '/api/v2/events/upcoming': '/api/v2/events/upcoming',
  '/api/v2/experience/full-simulation': '/api/v2/experience/full-simulation',
  '/api/v2/fan-predictions/creator-clubs/{club_id}/leaderboards/weekly':
      '/api/v2/fan-predictions/creator-clubs/{club_id}/leaderboards/weekly',
  '/api/v2/fan-predictions/leaderboards/weekly':
      '/api/v2/fan-predictions/leaderboards/weekly',
  '/api/v2/fan-predictions/matches/{match_id}':
      '/api/v2/fan-predictions/matches/{match_id}',
  '/api/v2/fan-predictions/matches/{match_id}/leaderboard':
      '/api/v2/fan-predictions/matches/{match_id}/leaderboard',
  '/api/v2/fan-predictions/matches/{match_id}/submissions':
      '/api/v2/fan-predictions/matches/{match_id}/submissions',
  '/api/v2/fan-predictions/me/submissions':
      '/api/v2/fan-predictions/me/submissions',
  '/api/v2/fan-predictions/me/tokens': '/api/v2/fan-predictions/me/tokens',
  '/api/v2/fan-wars/leaderboards/{board_type}':
      '/api/v2/fan-wars/leaderboards/{board_type}',
  '/api/v2/fan-wars/nations-cup/{competition_id}':
      '/api/v2/fan-wars/nations-cup/{competition_id}',
  '/api/v2/fan-wars/profiles/{profile_id}/dashboard':
      '/api/v2/fan-wars/profiles/{profile_id}/dashboard',
  '/api/v2/fan-wars/rivalries/{board_type}':
      '/api/v2/fan-wars/rivalries/{board_type}',
  '/api/v2/fans/profile': '/api/v2/fans/profile',
  '/api/v2/fans/tribe/join': '/api/v2/fans/tribe/join',
  '/api/v2/fans/{club_id}': '/api/v2/fans/{club_id}',
  '/api/v2/fast-cups/upcoming': '/api/v2/fast-cups/upcoming',
  '/api/v2/fast-cups/{cup_id}/bracket': '/api/v2/fast-cups/{cup_id}/bracket',
  '/api/v2/fast-cups/{cup_id}/countdown':
      '/api/v2/fast-cups/{cup_id}/countdown',
  '/api/v2/fast-cups/{cup_id}/join': '/api/v2/fast-cups/{cup_id}/join',
  '/api/v2/fast-cups/{cup_id}/result-summary':
      '/api/v2/fast-cups/{cup_id}/result-summary',
  '/api/v2/federations': '/api/v2/federations',
  '/api/v2/federations/proposals/{proposal_id}/votes':
      '/api/v2/federations/proposals/{proposal_id}/votes',
  '/api/v2/federations/rankings': '/api/v2/federations/rankings',
  '/api/v2/federations/regional-tournaments':
      '/api/v2/federations/regional-tournaments',
  '/api/v2/federations/vote': '/api/v2/federations/vote',
  '/api/v2/federations/{federation_id}': '/api/v2/federations/{federation_id}',
  '/api/v2/federations/{federation_id}/governance':
      '/api/v2/federations/{federation_id}/governance',
  '/api/v2/federations/{federation_id}/join':
      '/api/v2/federations/{federation_id}/join',
  '/api/v2/federations/{federation_id}/leagues':
      '/api/v2/federations/{federation_id}/leagues',
  '/api/v2/federations/{federation_id}/memberships':
      '/api/v2/federations/{federation_id}/memberships',
  '/api/v2/federations/{federation_id}/narratives':
      '/api/v2/federations/{federation_id}/narratives',
  '/api/v2/federations/{federation_id}/proposals':
      '/api/v2/federations/{federation_id}/proposals',
  '/api/v2/federations/{federation_id}/sanctions':
      '/api/v2/federations/{federation_id}/sanctions',
  '/api/v2/federations/{federation_id}/treasury/distribute':
      '/api/v2/federations/{federation_id}/treasury/distribute',
  '/api/v2/federations/{federation_id}/validate-action':
      '/api/v2/federations/{federation_id}/validate-action',
  '/api/v2/feed': '/api/v2/feed',
  '/api/v2/feed/following': '/api/v2/feed/following',
  '/api/v2/feed/for-you': '/api/v2/feed/for-you',
  '/api/v2/feed/for-you/refresh': '/api/v2/feed/for-you/refresh',
  '/api/v2/feed/sponsored': '/api/v2/feed/sponsored',
  '/api/v2/finance': '/api/v2/finance',
  '/api/v2/follow/{user_id}': '/api/v2/follow/{user_id}',
  '/api/v2/football-events/players/{player_id}/events':
      '/api/v2/football-events/players/{player_id}/events',
  '/api/v2/football-events/players/{player_id}/impact':
      '/api/v2/football-events/players/{player_id}/impact',
  '/api/v2/gift-engine/me/combos': '/api/v2/gift-engine/me/combos',
  '/api/v2/gift-engine/me/summary': '/api/v2/gift-engine/me/summary',
  '/api/v2/gift-engine/me/transactions': '/api/v2/gift-engine/me/transactions',
  '/api/v2/gift-engine/send': '/api/v2/gift-engine/send',
  '/api/v2/governance/clubs/{club_id}/panel':
      '/api/v2/governance/clubs/{club_id}/panel',
  '/api/v2/governance/me/overview': '/api/v2/governance/me/overview',
  '/api/v2/governance/proposals': '/api/v2/governance/proposals',
  '/api/v2/governance/proposals/{proposal_id}':
      '/api/v2/governance/proposals/{proposal_id}',
  '/api/v2/governance/proposals/{proposal_id}/vote':
      '/api/v2/governance/proposals/{proposal_id}/vote',
  '/api/v2/gtex/market/buy': '/api/v2/gtex/market/buy',
  '/api/v2/gtex/market/sell': '/api/v2/gtex/market/sell',
  '/api/v2/hall-of-fame': '/api/v2/hall-of-fame',
  '/api/v2/history/goat-rankings': '/api/v2/history/goat-rankings',
  '/api/v2/history/leaderboards': '/api/v2/history/leaderboards',
  '/api/v2/history/records': '/api/v2/history/records',
  '/api/v2/history/timeline/{subject_type}/{subject_id}':
      '/api/v2/history/timeline/{subject_type}/{subject_id}',
  '/api/v2/home/dashboard': '/api/v2/home/dashboard',
  '/api/v2/hosted-competitions': '/api/v2/hosted-competitions',
  '/api/v2/hosted-competitions/mine': '/api/v2/hosted-competitions/mine',
  '/api/v2/hosted-competitions/mine/invites':
      '/api/v2/hosted-competitions/mine/invites',
  '/api/v2/hosted-competitions/templates':
      '/api/v2/hosted-competitions/templates',
  '/api/v2/hosted-competitions/{competition_id}':
      '/api/v2/hosted-competitions/{competition_id}',
  '/api/v2/hosted-competitions/{competition_id}/finance':
      '/api/v2/hosted-competitions/{competition_id}/finance',
  '/api/v2/hosted-competitions/{competition_id}/invites':
      '/api/v2/hosted-competitions/{competition_id}/invites',
  '/api/v2/hosted-competitions/{competition_id}/invites/accept':
      '/api/v2/hosted-competitions/{competition_id}/invites/accept',
  '/api/v2/hosted-competitions/{competition_id}/join':
      '/api/v2/hosted-competitions/{competition_id}/join',
  '/api/v2/hosted-competitions/{competition_id}/launch':
      '/api/v2/hosted-competitions/{competition_id}/launch',
  '/api/v2/hosted-competitions/{competition_id}/standings':
      '/api/v2/hosted-competitions/{competition_id}/standings',
  '/api/v2/infinite-league/economy': '/api/v2/infinite-league/economy',
  '/api/v2/infinite-league/livestream': '/api/v2/infinite-league/livestream',
  '/api/v2/infinite-league/matches': '/api/v2/infinite-league/matches',
  '/api/v2/infinite-league/matches/{match_id}':
      '/api/v2/infinite-league/matches/{match_id}',
  '/api/v2/infinite-league/pundits/{match_id}':
      '/api/v2/infinite-league/pundits/{match_id}',
  '/api/v2/infinite-league/status': '/api/v2/infinite-league/status',
  '/api/v2/infinite-league/tick': '/api/v2/infinite-league/tick',
  '/api/v2/infinite-league/viral-feed': '/api/v2/infinite-league/viral-feed',
  '/api/v2/integrations/payments/korapay/webhook':
      '/api/v2/integrations/payments/korapay/webhook',
  '/api/v2/integrations/payments/methods':
      '/api/v2/integrations/payments/methods',
  '/api/v2/integrations/payments/orders':
      '/api/v2/integrations/payments/orders',
  '/api/v2/integrations/payments/paystack/webhook':
      '/api/v2/integrations/payments/paystack/webhook',
  '/api/v2/integrations/payments/quote': '/api/v2/integrations/payments/quote',
  '/api/v2/integrity-engine/me/incidents':
      '/api/v2/integrity-engine/me/incidents',
  '/api/v2/integrity-engine/me/score': '/api/v2/integrity-engine/me/score',
  '/api/v2/internal/ingestion/bootstrap-sync':
      '/api/v2/internal/ingestion/bootstrap-sync',
  '/api/v2/internal/ingestion/clubs/{club_external_id}/refresh':
      '/api/v2/internal/ingestion/clubs/{club_external_id}/refresh',
  '/api/v2/internal/ingestion/competitions/{competition_external_id}/refresh':
      '/api/v2/internal/ingestion/competitions/{competition_external_id}/refresh',
  '/api/v2/internal/ingestion/cursors/{provider_name}':
      '/api/v2/internal/ingestion/cursors/{provider_name}',
  '/api/v2/internal/ingestion/incremental-sync':
      '/api/v2/internal/ingestion/incremental-sync',
  '/api/v2/internal/ingestion/players/{player_external_id}/refresh':
      '/api/v2/internal/ingestion/players/{player_external_id}/refresh',
  '/api/v2/internal/ingestion/providers/{provider_name}/health':
      '/api/v2/internal/ingestion/providers/{provider_name}/health',
  '/api/v2/internal/ingestion/real-players/batches':
      '/api/v2/internal/ingestion/real-players/batches',
  '/api/v2/internal/ingestion/real-players/batches/{batch_id}':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}',
  '/api/v2/internal/ingestion/real-players/batches/{batch_id}/issues':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}/issues',
  '/api/v2/internal/ingestion/real-players/batches/{batch_id}/resume':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}/resume',
  '/api/v2/internal/ingestion/real-players/batches/{batch_id}/valuation-status':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}/valuation-status',
  '/api/v2/internal/ingestion/real-players/import':
      '/api/v2/internal/ingestion/real-players/import',
  '/api/v2/internal/ingestion/real-players/publish-jobs':
      '/api/v2/internal/ingestion/real-players/publish-jobs',
  '/api/v2/internal/ingestion/real-players/publish-jobs/{job_id}':
      '/api/v2/internal/ingestion/real-players/publish-jobs/{job_id}',
  '/api/v2/internal/ingestion/real-players/status':
      '/api/v2/internal/ingestion/real-players/status',
  '/api/v2/internal/ingestion/runs': '/api/v2/internal/ingestion/runs',
  '/api/v2/internal/ingestion/status': '/api/v2/internal/ingestion/status',
  '/api/v2/jackpot/contribute': '/api/v2/jackpot/contribute',
  '/api/v2/jackpot/history': '/api/v2/jackpot/history',
  '/api/v2/jackpot/state': '/api/v2/jackpot/state',
  '/api/v2/jobs/{job_id}': '/api/v2/jobs/{job_id}',
  '/api/v2/kyc': '/api/v2/kyc',
  '/api/v2/leaderboard/division/{division}':
      '/api/v2/leaderboard/division/{division}',
  '/api/v2/leaderboard/global': '/api/v2/leaderboard/global',
  '/api/v2/leaderboard/player/{player_id}':
      '/api/v2/leaderboard/player/{player_id}',
  '/api/v2/leaderboard/region/{region}': '/api/v2/leaderboard/region/{region}',
  '/api/v2/leaderboards/dynasties': '/api/v2/leaderboards/dynasties',
  '/api/v2/leaderboards/prestige': '/api/v2/leaderboards/prestige',
  '/api/v2/leaderboards/trophies': '/api/v2/leaderboards/trophies',
  '/api/v2/leagues/register': '/api/v2/leagues/register',
  '/api/v2/leagues/{season_id}/fixtures':
      '/api/v2/leagues/{season_id}/fixtures',
  '/api/v2/leagues/{season_id}/qualification-markers':
      '/api/v2/leagues/{season_id}/qualification-markers',
  '/api/v2/leagues/{season_id}/standings':
      '/api/v2/leagues/{season_id}/standings',
  '/api/v2/leagues/{season_id}/summary': '/api/v2/leagues/{season_id}/summary',
  '/api/v2/legacy/board': '/api/v2/legacy/board',
  '/api/v2/live-events': '/api/v2/live-events',
  '/api/v2/manager-duels': '/api/v2/manager-duels',
  '/api/v2/manager-duels/leaderboard': '/api/v2/manager-duels/leaderboard',
  '/api/v2/manager-duels/{duel_id}': '/api/v2/manager-duels/{duel_id}',
  '/api/v2/managers': '/api/v2/managers',
  '/api/v2/managers/assign': '/api/v2/managers/assign',
  '/api/v2/managers/catalog': '/api/v2/managers/catalog',
  '/api/v2/managers/compare': '/api/v2/managers/compare',
  '/api/v2/managers/competition-runtime/{code}':
      '/api/v2/managers/competition-runtime/{code}',
  '/api/v2/managers/create': '/api/v2/managers/create',
  '/api/v2/managers/filters': '/api/v2/managers/filters',
  '/api/v2/managers/history': '/api/v2/managers/history',
  '/api/v2/managers/leaderboard': '/api/v2/managers/leaderboard',
  '/api/v2/managers/my-trade-listings': '/api/v2/managers/my-trade-listings',
  '/api/v2/managers/recommendation': '/api/v2/managers/recommendation',
  '/api/v2/managers/recruit': '/api/v2/managers/recruit',
  '/api/v2/managers/swap': '/api/v2/managers/swap',
  '/api/v2/managers/team': '/api/v2/managers/team',
  '/api/v2/managers/trade-listings': '/api/v2/managers/trade-listings',
  '/api/v2/managers/trade-listings/{listing_id}/buy':
      '/api/v2/managers/trade-listings/{listing_id}/buy',
  '/api/v2/managers/trade-listings/{listing_id}/cancel':
      '/api/v2/managers/trade-listings/{listing_id}/cancel',
  '/api/v2/managers/{asset_id}/release': '/api/v2/managers/{asset_id}/release',
  '/api/v2/managers/{manager_id}': '/api/v2/managers/{manager_id}',
  '/api/v2/managers/{manager_id}/hire': '/api/v2/managers/{manager_id}/hire',
  '/api/v2/managers/{manager_id}/history':
      '/api/v2/managers/{manager_id}/history',
  '/api/v2/managers/{manager_id}/release':
      '/api/v2/managers/{manager_id}/release',
  '/api/v2/market/bid': '/api/v2/market/bid',
  '/api/v2/market/buy': '/api/v2/market/buy',
  '/api/v2/market/listings': '/api/v2/market/listings',
  '/api/v2/market/listings/{listing_id}/cancel':
      '/api/v2/market/listings/{listing_id}/cancel',
  '/api/v2/market/listings/{listing_id}/matches':
      '/api/v2/market/listings/{listing_id}/matches',
  '/api/v2/market/listings/{listing_id}/offers':
      '/api/v2/market/listings/{listing_id}/offers',
  '/api/v2/market/movers': '/api/v2/market/movers',
  '/api/v2/market/offers': '/api/v2/market/offers',
  '/api/v2/market/offers/{offer_id}/accept':
      '/api/v2/market/offers/{offer_id}/accept',
  '/api/v2/market/offers/{offer_id}/counter':
      '/api/v2/market/offers/{offer_id}/counter',
  '/api/v2/market/offers/{offer_id}/reject':
      '/api/v2/market/offers/{offer_id}/reject',
  '/api/v2/market/players': '/api/v2/market/players',
  '/api/v2/market/players/{player_id}': '/api/v2/market/players/{player_id}',
  '/api/v2/market/players/{player_id}/candles':
      '/api/v2/market/players/{player_id}/candles',
  '/api/v2/market/players/{player_id}/history':
      '/api/v2/market/players/{player_id}/history',
  '/api/v2/market/sell': '/api/v2/market/sell',
  '/api/v2/market/summary/{asset_id}': '/api/v2/market/summary/{asset_id}',
  '/api/v2/market/ticker/{player_id}': '/api/v2/market/ticker/{player_id}',
  '/api/v2/market/trade-intents': '/api/v2/market/trade-intents',
  '/api/v2/market/trade-intents/{intent_id}/withdraw':
      '/api/v2/market/trade-intents/{intent_id}/withdraw',
  '/api/v2/market/trending': '/api/v2/market/trending',
  '/api/v2/marketplace/my-players': '/api/v2/marketplace/my-players',
  '/api/v2/marketplace/players': '/api/v2/marketplace/players',
  '/api/v2/marketplace/players/{player_id}':
      '/api/v2/marketplace/players/{player_id}',
  '/api/v2/match-engine/analytics': '/api/v2/match-engine/analytics',
  '/api/v2/match-engine/analytics/{match_key}':
      '/api/v2/match-engine/analytics/{match_key}',
  '/api/v2/match-engine/highlights/{match_key}':
      '/api/v2/match-engine/highlights/{match_key}',
  '/api/v2/match-engine/live-feed/{match_key}':
      '/api/v2/match-engine/live-feed/{match_key}',
  '/api/v2/match-engine/render-sync': '/api/v2/match-engine/render-sync',
  '/api/v2/match-engine/render-sync/{match_key}':
      '/api/v2/match-engine/render-sync/{match_key}',
  '/api/v2/match-engine/replay': '/api/v2/match-engine/replay',
  '/api/v2/match-engine/simulate': '/api/v2/match-engine/simulate',
  '/api/v2/match-engine/summary': '/api/v2/match-engine/summary',
  '/api/v2/match-engine/timeline': '/api/v2/match-engine/timeline',
  '/api/v2/match-share-links/{share_code}':
      '/api/v2/match-share-links/{share_code}',
  '/api/v2/match-share-links/{share_code}/events':
      '/api/v2/match-share-links/{share_code}/events',
  '/api/v2/match-viewer/{match_key}': '/api/v2/match-viewer/{match_key}',
  '/api/v2/match-viewer/{match_key}/illusion':
      '/api/v2/match-viewer/{match_key}/illusion',
  '/api/v2/match-viewer/{match_key}/session':
      '/api/v2/match-viewer/{match_key}/session',
  '/api/v2/match/find': '/api/v2/match/find',
  '/api/v2/match/live/active': '/api/v2/match/live/active',
  '/api/v2/match/{match_id}/commentary/stream':
      '/api/v2/match/{match_id}/commentary/stream',
  '/api/v2/match/{match_id}/live': '/api/v2/match/{match_id}/live',
  '/api/v2/match/{match_id}/unity-access':
      '/api/v2/match/{match_id}/unity-access',
  '/api/v2/match/{match_id}/unity-access/refresh':
      '/api/v2/match/{match_id}/unity-access/refresh',
  '/api/v2/matches/complete': '/api/v2/matches/complete',
  '/api/v2/matches/live/active': '/api/v2/matches/live/active',
  '/api/v2/matches/start': '/api/v2/matches/start',
  '/api/v2/matches/{match_id}': '/api/v2/matches/{match_id}',
  '/api/v2/matches/{match_id}/analysis': '/api/v2/matches/{match_id}/analysis',
  '/api/v2/matches/{match_id}/audio/stems/stream':
      '/api/v2/matches/{match_id}/audio/stems/stream',
  '/api/v2/matches/{match_id}/chat': '/api/v2/matches/{match_id}/chat',
  '/api/v2/matches/{match_id}/chat/messages':
      '/api/v2/matches/{match_id}/chat/messages',
  '/api/v2/matches/{match_id}/commentary':
      '/api/v2/matches/{match_id}/commentary',
  '/api/v2/matches/{match_id}/commentary/stream':
      '/api/v2/matches/{match_id}/commentary/stream',
  '/api/v2/matches/{match_id}/fan-experience':
      '/api/v2/matches/{match_id}/fan-experience',
  '/api/v2/matches/{match_id}/highlights':
      '/api/v2/matches/{match_id}/highlights',
  '/api/v2/matches/{match_id}/highlights/share-package':
      '/api/v2/matches/{match_id}/highlights/share-package',
  '/api/v2/matches/{match_id}/live': '/api/v2/matches/{match_id}/live',
  '/api/v2/matches/{match_id}/live-reactions':
      '/api/v2/matches/{match_id}/live-reactions',
  '/api/v2/matches/{match_id}/reactions':
      '/api/v2/matches/{match_id}/reactions',
  '/api/v2/matches/{match_id}/replay': '/api/v2/matches/{match_id}/replay',
  '/api/v2/matches/{match_id}/share-links':
      '/api/v2/matches/{match_id}/share-links',
  '/api/v2/matches/{match_id}/social-warfare':
      '/api/v2/matches/{match_id}/social-warfare',
  '/api/v2/matches/{match_id}/spectate': '/api/v2/matches/{match_id}/spectate',
  '/api/v2/matches/{match_id}/spectators':
      '/api/v2/matches/{match_id}/spectators',
  '/api/v2/matches/{match_id}/stream': '/api/v2/matches/{match_id}/stream',
  '/api/v2/matches/{match_id}/tickets': '/api/v2/matches/{match_id}/tickets',
  '/api/v2/matches/{match_id}/unity-access':
      '/api/v2/matches/{match_id}/unity-access',
  '/api/v2/matches/{match_id}/unity-access/refresh':
      '/api/v2/matches/{match_id}/unity-access/refresh',
  '/api/v2/me/clubs/sale-market/listings':
      '/api/v2/me/clubs/sale-market/listings',
  '/api/v2/me/clubs/sale-market/offers': '/api/v2/me/clubs/sale-market/offers',
  '/api/v2/media': '/api/v2/media',
  '/api/v2/media-engine/creator-league/broadcast-modes':
      '/api/v2/media-engine/creator-league/broadcast-modes',
  '/api/v2/media-engine/creator-league/clubs/{club_id}/stadium':
      '/api/v2/media-engine/creator-league/clubs/{club_id}/stadium',
  '/api/v2/media-engine/creator-league/matches/{match_id}/access':
      '/api/v2/media-engine/creator-league/matches/{match_id}/access',
  '/api/v2/media-engine/creator-league/matches/{match_id}/analytics':
      '/api/v2/media-engine/creator-league/matches/{match_id}/analytics',
  '/api/v2/media-engine/creator-league/matches/{match_id}/gifts':
      '/api/v2/media-engine/creator-league/matches/{match_id}/gifts',
  '/api/v2/media-engine/creator-league/matches/{match_id}/purchase':
      '/api/v2/media-engine/creator-league/matches/{match_id}/purchase',
  '/api/v2/media-engine/creator-league/matches/{match_id}/stadium':
      '/api/v2/media-engine/creator-league/matches/{match_id}/stadium',
  '/api/v2/media-engine/creator-league/matches/{match_id}/stadium/placements':
      '/api/v2/media-engine/creator-league/matches/{match_id}/stadium/placements',
  '/api/v2/media-engine/creator-league/matches/{match_id}/tickets':
      '/api/v2/media-engine/creator-league/matches/{match_id}/tickets',
  '/api/v2/media-engine/creator-league/season-passes':
      '/api/v2/media-engine/creator-league/season-passes',
  '/api/v2/media-engine/creator-league/season-passes/me':
      '/api/v2/media-engine/creator-league/season-passes/me',
  '/api/v2/media-engine/downloads': '/api/v2/media-engine/downloads',
  '/api/v2/media-engine/downloads/{token}':
      '/api/v2/media-engine/downloads/{token}',
  '/api/v2/media-engine/matches/{match_key}/snapshot':
      '/api/v2/media-engine/matches/{match_key}/snapshot',
  '/api/v2/media-engine/me/clip-earnings':
      '/api/v2/media-engine/me/clip-earnings',
  '/api/v2/media-engine/me/purchases': '/api/v2/media-engine/me/purchases',
  '/api/v2/media-engine/me/share-exports':
      '/api/v2/media-engine/me/share-exports',
  '/api/v2/media-engine/purchases': '/api/v2/media-engine/purchases',
  '/api/v2/media-engine/share-exports': '/api/v2/media-engine/share-exports',
  '/api/v2/media-engine/share-exports/{export_id}/amplifications':
      '/api/v2/media-engine/share-exports/{export_id}/amplifications',
  '/api/v2/media-engine/share-templates':
      '/api/v2/media-engine/share-templates',
  '/api/v2/media-engine/views': '/api/v2/media-engine/views',
  '/api/v2/metrics': '/api/v2/metrics',
  '/api/v2/moderation/me/reports': '/api/v2/moderation/me/reports',
  '/api/v2/moderation/reports': '/api/v2/moderation/reports',
  '/api/v2/moments/live': '/api/v2/moments/live',
  '/api/v2/national-pool': '/api/v2/national-pool',
  '/api/v2/national-team-engine/competitions':
      '/api/v2/national-team-engine/competitions',
  '/api/v2/national-team-engine/competitions/{competition_id}':
      '/api/v2/national-team-engine/competitions/{competition_id}',
  '/api/v2/national-team-engine/competitions/{competition_id}/ads/active':
      '/api/v2/national-team-engine/competitions/{competition_id}/ads/active',
  '/api/v2/national-team-engine/competitions/{competition_id}/auto-build-squad':
      '/api/v2/national-team-engine/competitions/{competition_id}/auto-build-squad',
  '/api/v2/national-team-engine/competitions/{competition_id}/entries':
      '/api/v2/national-team-engine/competitions/{competition_id}/entries',
  '/api/v2/national-team-engine/competitions/{competition_id}/gifts':
      '/api/v2/national-team-engine/competitions/{competition_id}/gifts',
  '/api/v2/national-team-engine/competitions/{competition_id}/lifecycle':
      '/api/v2/national-team-engine/competitions/{competition_id}/lifecycle',
  '/api/v2/national-team-engine/competitions/{competition_id}/presentation':
      '/api/v2/national-team-engine/competitions/{competition_id}/presentation',
  '/api/v2/national-team-engine/competitions/{competition_id}/rental-entry':
      '/api/v2/national-team-engine/competitions/{competition_id}/rental-entry',
  '/api/v2/national-team-engine/competitions/{competition_id}/rental-pool':
      '/api/v2/national-team-engine/competitions/{competition_id}/rental-pool',
  '/api/v2/national-team-engine/competitions/{competition_id}/story-events':
      '/api/v2/national-team-engine/competitions/{competition_id}/story-events',
  '/api/v2/national-team-engine/competitions/{competition_id}/theme':
      '/api/v2/national-team-engine/competitions/{competition_id}/theme',
  '/api/v2/national-team-engine/entries/{entry_id}':
      '/api/v2/national-team-engine/entries/{entry_id}',
  '/api/v2/national-team-engine/entries/{entry_id}/free-players/claim':
      '/api/v2/national-team-engine/entries/{entry_id}/free-players/claim',
  '/api/v2/national-team-engine/entries/{entry_id}/rental-status':
      '/api/v2/national-team-engine/entries/{entry_id}/rental-status',
  '/api/v2/national-team-engine/entries/{entry_id}/rentals':
      '/api/v2/national-team-engine/entries/{entry_id}/rentals',
  '/api/v2/national-team-engine/me/history':
      '/api/v2/national-team-engine/me/history',
  '/api/v2/national-team-engine/me/previous-roster':
      '/api/v2/national-team-engine/me/previous-roster',
  '/api/v2/national-team-engine/rankings':
      '/api/v2/national-team-engine/rankings',
  '/api/v2/news/breaking': '/api/v2/news/breaking',
  '/api/v2/news/daily': '/api/v2/news/daily',
  '/api/v2/news/feed': '/api/v2/news/feed',
  '/api/v2/news/personalized': '/api/v2/news/personalized',
  '/api/v2/news/{article_id}': '/api/v2/news/{article_id}',
  '/api/v2/notifications': '/api/v2/notifications',
  '/api/v2/notifications/announcements': '/api/v2/notifications/announcements',
  '/api/v2/notifications/me': '/api/v2/notifications/me',
  '/api/v2/notifications/preferences': '/api/v2/notifications/preferences',
  '/api/v2/notifications/read-all': '/api/v2/notifications/read-all',
  '/api/v2/notifications/subscriptions': '/api/v2/notifications/subscriptions',
  '/api/v2/notifications/subscriptions/{subscription_id}':
      '/api/v2/notifications/subscriptions/{subscription_id}',
  '/api/v2/notifications/{notification_id}/read':
      '/api/v2/notifications/{notification_id}/read',
  '/api/v2/objectives/me': '/api/v2/objectives/me',
  '/api/v2/observability/config': '/api/v2/observability/config',
  '/api/v2/orchestrator/config': '/api/v2/orchestrator/config',
  '/api/v2/orchestrator/metrics': '/api/v2/orchestrator/metrics',
  '/api/v2/orders': '/api/v2/orders',
  '/api/v2/orders/book/{player_id}': '/api/v2/orders/book/{player_id}',
  '/api/v2/orders/{order_id}': '/api/v2/orders/{order_id}',
  '/api/v2/orders/{order_id}/admin-buyback':
      '/api/v2/orders/{order_id}/admin-buyback',
  '/api/v2/orders/{order_id}/admin-buyback-preview':
      '/api/v2/orders/{order_id}/admin-buyback-preview',
  '/api/v2/orders/{order_id}/cancel': '/api/v2/orders/{order_id}/cancel',
  '/api/v2/organizations': '/api/v2/organizations',
  '/api/v2/organizations/invites/accept':
      '/api/v2/organizations/invites/accept',
  '/api/v2/organizations/me': '/api/v2/organizations/me',
  '/api/v2/organizations/{organization_id}/audit-log':
      '/api/v2/organizations/{organization_id}/audit-log',
  '/api/v2/organizations/{organization_id}/invite':
      '/api/v2/organizations/{organization_id}/invite',
  '/api/v2/ownership-groups': '/api/v2/ownership-groups',
  '/api/v2/ownership-groups/transfers/validate':
      '/api/v2/ownership-groups/transfers/validate',
  '/api/v2/ownership-groups/{group_id}': '/api/v2/ownership-groups/{group_id}',
  '/api/v2/ownership-groups/{group_id}/budget/allocate':
      '/api/v2/ownership-groups/{group_id}/budget/allocate',
  '/api/v2/ownership-groups/{group_id}/budget/transfer':
      '/api/v2/ownership-groups/{group_id}/budget/transfer',
  '/api/v2/ownership-groups/{group_id}/clubs':
      '/api/v2/ownership-groups/{group_id}/clubs',
  '/api/v2/platform/mode': '/api/v2/platform/mode',
  '/api/v2/platform/switch': '/api/v2/platform/switch',
  '/api/v2/player-cards/admin/preseeded-regens':
      '/api/v2/player-cards/admin/preseeded-regens',
  '/api/v2/player-cards/admin/preseeded-regens/mint':
      '/api/v2/player-cards/admin/preseeded-regens/mint',
  '/api/v2/player-cards/inventory': '/api/v2/player-cards/inventory',
  '/api/v2/player-cards/listings': '/api/v2/player-cards/listings',
  '/api/v2/player-cards/listings/mine': '/api/v2/player-cards/listings/mine',
  '/api/v2/player-cards/listings/{listing_id}/buy':
      '/api/v2/player-cards/listings/{listing_id}/buy',
  '/api/v2/player-cards/listings/{listing_id}/cancel':
      '/api/v2/player-cards/listings/{listing_id}/cancel',
  '/api/v2/player-cards/loans': '/api/v2/player-cards/loans',
  '/api/v2/player-cards/loans/contracts/{loan_contract_id}/return':
      '/api/v2/player-cards/loans/contracts/{loan_contract_id}/return',
  '/api/v2/player-cards/loans/{loan_listing_id}/borrow':
      '/api/v2/player-cards/loans/{loan_listing_id}/borrow',
  '/api/v2/player-cards/marketplace/listings':
      '/api/v2/player-cards/marketplace/listings',
  '/api/v2/player-cards/marketplace/loans':
      '/api/v2/player-cards/marketplace/loans',
  '/api/v2/player-cards/marketplace/loans/contracts':
      '/api/v2/player-cards/marketplace/loans/contracts',
  '/api/v2/player-cards/marketplace/loans/contracts/{contract_id}/return':
      '/api/v2/player-cards/marketplace/loans/contracts/{contract_id}/return',
  '/api/v2/player-cards/marketplace/loans/contracts/{contract_id}/settle':
      '/api/v2/player-cards/marketplace/loans/contracts/{contract_id}/settle',
  '/api/v2/player-cards/marketplace/loans/negotiations/{negotiation_id}/accept':
      '/api/v2/player-cards/marketplace/loans/negotiations/{negotiation_id}/accept',
  '/api/v2/player-cards/marketplace/loans/negotiations/{negotiation_id}/counter':
      '/api/v2/player-cards/marketplace/loans/negotiations/{negotiation_id}/counter',
  '/api/v2/player-cards/marketplace/loans/{listing_id}/cancel':
      '/api/v2/player-cards/marketplace/loans/{listing_id}/cancel',
  '/api/v2/player-cards/marketplace/loans/{listing_id}/negotiations':
      '/api/v2/player-cards/marketplace/loans/{listing_id}/negotiations',
  '/api/v2/player-cards/marketplace/sales':
      '/api/v2/player-cards/marketplace/sales',
  '/api/v2/player-cards/marketplace/sales/{listing_id}/buy':
      '/api/v2/player-cards/marketplace/sales/{listing_id}/buy',
  '/api/v2/player-cards/marketplace/sales/{listing_id}/cancel':
      '/api/v2/player-cards/marketplace/sales/{listing_id}/cancel',
  '/api/v2/player-cards/marketplace/swaps':
      '/api/v2/player-cards/marketplace/swaps',
  '/api/v2/player-cards/marketplace/swaps/{listing_id}/cancel':
      '/api/v2/player-cards/marketplace/swaps/{listing_id}/cancel',
  '/api/v2/player-cards/marketplace/swaps/{listing_id}/execute':
      '/api/v2/player-cards/marketplace/swaps/{listing_id}/execute',
  '/api/v2/player-cards/players': '/api/v2/player-cards/players',
  '/api/v2/player-cards/players/{player_id}':
      '/api/v2/player-cards/players/{player_id}',
  '/api/v2/player-cards/starter-rental': '/api/v2/player-cards/starter-rental',
  '/api/v2/player-cards/watchlist': '/api/v2/player-cards/watchlist',
  '/api/v2/player-cards/watchlist/{watchlist_id}':
      '/api/v2/player-cards/watchlist/{watchlist_id}',
  '/api/v2/player-history': '/api/v2/player-history',
  '/api/v2/player-history/{player_id}': '/api/v2/player-history/{player_id}',
  '/api/v2/player-import/youth-prospects/me':
      '/api/v2/player-import/youth-prospects/me',
  '/api/v2/player-import/youth-prospects/{club_id}':
      '/api/v2/player-import/youth-prospects/{club_id}',
  '/api/v2/players': '/api/v2/players',
  '/api/v2/players/events': '/api/v2/players/events',
  '/api/v2/players/markets': '/api/v2/players/markets',
  '/api/v2/players/match': '/api/v2/players/match',
  '/api/v2/players/me/match-profile': '/api/v2/players/me/match-profile',
  '/api/v2/players/me/shares/holdings': '/api/v2/players/me/shares/holdings',
  '/api/v2/players/real-universe': '/api/v2/players/real-universe',
  '/api/v2/players/real-universe/search':
      '/api/v2/players/real-universe/search',
  '/api/v2/players/real-universe/{player_id}':
      '/api/v2/players/real-universe/{player_id}',
  '/api/v2/players/summaries/recent': '/api/v2/players/summaries/recent',
  '/api/v2/players/{player_id}': '/api/v2/players/{player_id}',
  '/api/v2/players/{player_id}/agency': '/api/v2/players/{player_id}/agency',
  '/api/v2/players/{player_id}/agency/contract-decision':
      '/api/v2/players/{player_id}/agency/contract-decision',
  '/api/v2/players/{player_id}/agency/transfer-decision':
      '/api/v2/players/{player_id}/agency/transfer-decision',
  '/api/v2/players/{player_id}/availability':
      '/api/v2/players/{player_id}/availability',
  '/api/v2/players/{player_id}/avatar': '/api/v2/players/{player_id}/avatar',
  '/api/v2/players/{player_id}/career': '/api/v2/players/{player_id}/career',
  '/api/v2/players/{player_id}/career-events':
      '/api/v2/players/{player_id}/career-events',
  '/api/v2/players/{player_id}/career/summary':
      '/api/v2/players/{player_id}/career/summary',
  '/api/v2/players/{player_id}/contracts':
      '/api/v2/players/{player_id}/contracts',
  '/api/v2/players/{player_id}/contracts/summary':
      '/api/v2/players/{player_id}/contracts/summary',
  '/api/v2/players/{player_id}/contracts/{contract_id}/renew':
      '/api/v2/players/{player_id}/contracts/{contract_id}/renew',
  '/api/v2/players/{player_id}/dna': '/api/v2/players/{player_id}/dna',
  '/api/v2/players/{player_id}/events': '/api/v2/players/{player_id}/events',
  '/api/v2/players/{player_id}/injuries':
      '/api/v2/players/{player_id}/injuries',
  '/api/v2/players/{player_id}/injuries/{injury_id}/recover':
      '/api/v2/players/{player_id}/injuries/{injury_id}/recover',
  '/api/v2/players/{player_id}/interviews':
      '/api/v2/players/{player_id}/interviews',
  '/api/v2/players/{player_id}/lifecycle-snapshot':
      '/api/v2/players/{player_id}/lifecycle-snapshot',
  '/api/v2/players/{player_id}/overview':
      '/api/v2/players/{player_id}/overview',
  '/api/v2/players/{player_id}/personality':
      '/api/v2/players/{player_id}/personality',
  '/api/v2/players/{player_id}/regen': '/api/v2/players/{player_id}/regen',
  '/api/v2/players/{player_id}/regen/big-club-approaches':
      '/api/v2/players/{player_id}/regen/big-club-approaches',
  '/api/v2/players/{player_id}/regen/contract-offers/quote':
      '/api/v2/players/{player_id}/regen/contract-offers/quote',
  '/api/v2/players/{player_id}/regen/offer-market':
      '/api/v2/players/{player_id}/regen/offer-market',
  '/api/v2/players/{player_id}/regen/pressure-resolution':
      '/api/v2/players/{player_id}/regen/pressure-resolution',
  '/api/v2/players/{player_id}/regen/special-training':
      '/api/v2/players/{player_id}/regen/special-training',
  '/api/v2/players/{player_id}/regen/transfer-listing':
      '/api/v2/players/{player_id}/regen/transfer-listing',
  '/api/v2/players/{player_id}/rivalries':
      '/api/v2/players/{player_id}/rivalries',
  '/api/v2/players/{player_id}/shares/buy':
      '/api/v2/players/{player_id}/shares/buy',
  '/api/v2/players/{player_id}/shares/dividends':
      '/api/v2/players/{player_id}/shares/dividends',
  '/api/v2/players/{player_id}/shares/events':
      '/api/v2/players/{player_id}/shares/events',
  '/api/v2/players/{player_id}/shares/issue':
      '/api/v2/players/{player_id}/shares/issue',
  '/api/v2/players/{player_id}/shares/market':
      '/api/v2/players/{player_id}/shares/market',
  '/api/v2/players/{player_id}/shares/performance':
      '/api/v2/players/{player_id}/shares/performance',
  '/api/v2/players/{player_id}/shares/sell':
      '/api/v2/players/{player_id}/shares/sell',
  '/api/v2/players/{player_id}/story': '/api/v2/players/{player_id}/story',
  '/api/v2/players/{player_id}/summary': '/api/v2/players/{player_id}/summary',
  '/api/v2/policies/acceptances': '/api/v2/policies/acceptances',
  '/api/v2/policies/country/{country_code}':
      '/api/v2/policies/country/{country_code}',
  '/api/v2/policies/documents': '/api/v2/policies/documents',
  '/api/v2/policies/documents/{document_key}':
      '/api/v2/policies/documents/{document_key}',
  '/api/v2/policies/me/acceptances': '/api/v2/policies/me/acceptances',
  '/api/v2/policies/me/compliance': '/api/v2/policies/me/compliance',
  '/api/v2/policies/me/region': '/api/v2/policies/me/region',
  '/api/v2/policies/me/requirements': '/api/v2/policies/me/requirements',
  '/api/v2/portfolio': '/api/v2/portfolio',
  '/api/v2/portfolio/snapshot': '/api/v2/portfolio/snapshot',
  '/api/v2/portfolio/summary': '/api/v2/portfolio/summary',
  '/api/v2/portfolios/me': '/api/v2/portfolios/me',
  '/api/v2/predictions': '/api/v2/predictions',
  '/api/v2/predictions/leaderboard': '/api/v2/predictions/leaderboard',
  '/api/v2/pundits/matches/{match_key}': '/api/v2/pundits/matches/{match_key}',
  '/api/v2/rankings/clubs': '/api/v2/rankings/clubs',
  '/api/v2/rankings/global': '/api/v2/rankings/global',
  '/api/v2/rankings/players': '/api/v2/rankings/players',
  '/api/v2/real-world/events': '/api/v2/real-world/events',
  '/api/v2/real-world/hybrid-players': '/api/v2/real-world/hybrid-players',
  '/api/v2/real-world/normalize': '/api/v2/real-world/normalize',
  '/api/v2/real-world/players': '/api/v2/real-world/players',
  '/api/v2/real-world/players/{real_player_id}':
      '/api/v2/real-world/players/{real_player_id}',
  '/api/v2/real-world/providers': '/api/v2/real-world/providers',
  '/api/v2/real-world/settings/me': '/api/v2/real-world/settings/me',
  '/api/v2/realtime/matches/{match_id}/gateway':
      '/api/v2/realtime/matches/{match_id}/gateway',
  '/api/v2/realtime/matches/{match_id}/stream':
      '/api/v2/realtime/matches/{match_id}/stream',
  '/api/v2/realtime/status': '/api/v2/realtime/status',
  '/api/v2/realtime/stream': '/api/v2/realtime/stream',
  '/api/v2/realtime/wallet/gateway': '/api/v2/realtime/wallet/gateway',
  '/api/v2/realtime/wallet/stream': '/api/v2/realtime/wallet/stream',
  '/api/v2/referrals/attribution': '/api/v2/referrals/attribution',
  '/api/v2/referrals/me/invites': '/api/v2/referrals/me/invites',
  '/api/v2/referrals/me/rewards': '/api/v2/referrals/me/rewards',
  '/api/v2/referrals/me/summary': '/api/v2/referrals/me/summary',
  '/api/v2/referrals/share-codes': '/api/v2/referrals/share-codes',
  '/api/v2/referrals/share-codes/me': '/api/v2/referrals/share-codes/me',
  '/api/v2/referrals/share-codes/{code}/redeem':
      '/api/v2/referrals/share-codes/{code}/redeem',
  '/api/v2/referrals/share-codes/{share_code_id}':
      '/api/v2/referrals/share-codes/{share_code_id}',
  '/api/v2/regen-hype': '/api/v2/regen-hype',
  '/api/v2/regen-universe/achievements': '/api/v2/regen-universe/achievements',
  '/api/v2/regen-universe/awards': '/api/v2/regen-universe/awards',
  '/api/v2/regen-universe/bloodlines': '/api/v2/regen-universe/bloodlines',
  '/api/v2/regen-universe/hall-of-fame': '/api/v2/regen-universe/hall-of-fame',
  '/api/v2/regen-universe/national-regens':
      '/api/v2/regen-universe/national-regens',
  '/api/v2/regen-universe/player/{player_id}':
      '/api/v2/regen-universe/player/{player_id}',
  '/api/v2/regen-universe/players/{player_id}':
      '/api/v2/regen-universe/players/{player_id}',
  '/api/v2/regen-universe/players/{player_id}/timeline':
      '/api/v2/regen-universe/players/{player_id}/timeline',
  '/api/v2/regen-universe/rankings': '/api/v2/regen-universe/rankings',
  '/api/v2/regen-universe/rising-stars': '/api/v2/regen-universe/rising-stars',
  '/api/v2/regen-universe/scouting-feed':
      '/api/v2/regen-universe/scouting-feed',
  '/api/v2/regen-universe/seasons': '/api/v2/regen-universe/seasons',
  '/api/v2/regen-universe/tracking': '/api/v2/regen-universe/tracking',
  '/api/v2/regen-universe/youth-tournaments':
      '/api/v2/regen-universe/youth-tournaments',
  '/api/v2/regen-universe/youth-tournaments/{tournament_id}':
      '/api/v2/regen-universe/youth-tournaments/{tournament_id}',
  '/api/v2/regens': '/api/v2/regens',
  '/api/v2/regens/awards': '/api/v2/regens/awards',
  '/api/v2/regens/awards/{award_id}/vote':
      '/api/v2/regens/awards/{award_id}/vote',
  '/api/v2/regens/creation-orders': '/api/v2/regens/creation-orders',
  '/api/v2/regens/creation-orders/{order_id}':
      '/api/v2/regens/creation-orders/{order_id}',
  '/api/v2/regens/creation-orders/{order_id}/generate-after-payment':
      '/api/v2/regens/creation-orders/{order_id}/generate-after-payment',
  '/api/v2/regens/creation-orders/{order_id}/pay-with-wallet':
      '/api/v2/regens/creation-orders/{order_id}/pay-with-wallet',
  '/api/v2/regens/feed': '/api/v2/regens/feed',
  '/api/v2/regens/jobs/{job_name}': '/api/v2/regens/jobs/{job_name}',
  '/api/v2/regens/request-son': '/api/v2/regens/request-son',
  '/api/v2/regens/request-son/options': '/api/v2/regens/request-son/options',
  '/api/v2/regens/rising': '/api/v2/regens/rising',
  '/api/v2/regens/top': '/api/v2/regens/top',
  '/api/v2/regens/{regen_id}/lineage': '/api/v2/regens/{regen_id}/lineage',
  '/api/v2/rent': '/api/v2/rent',
  '/api/v2/replays/countdown/{fixture_id}':
      '/api/v2/replays/countdown/{fixture_id}',
  '/api/v2/replays/me': '/api/v2/replays/me',
  '/api/v2/replays/public/featured': '/api/v2/replays/public/featured',
  '/api/v2/replays/{replay_id}': '/api/v2/replays/{replay_id}',
  '/api/v2/reward-engine/me/settlements':
      '/api/v2/reward-engine/me/settlements',
  '/api/v2/reward-engine/me/summary': '/api/v2/reward-engine/me/summary',
  '/api/v2/risk-ops/me/aml-cases': '/api/v2/risk-ops/me/aml-cases',
  '/api/v2/risk-ops/me/fraud-cases': '/api/v2/risk-ops/me/fraud-cases',
  '/api/v2/risk-ops/me/overview': '/api/v2/risk-ops/me/overview',
  '/api/v2/risk-ops/me/restrictions': '/api/v2/risk-ops/me/restrictions',
  '/api/v2/risk-ops/me/signals': '/api/v2/risk-ops/me/signals',
  '/api/v2/rivalries/matches': '/api/v2/rivalries/matches',
  '/api/v2/scout/report/{player_id}': '/api/v2/scout/report/{player_id}',
  '/api/v2/scouts': '/api/v2/scouts',
  '/api/v2/scouts/{scout_id}/discover': '/api/v2/scouts/{scout_id}/discover',
  '/api/v2/season-pass': '/api/v2/season-pass',
  '/api/v2/season-pass/claim': '/api/v2/season-pass/claim',
  '/api/v2/season-pass/me': '/api/v2/season-pass/me',
  '/api/v2/season-pass/rewards/{reward_id}/claim':
      '/api/v2/season-pass/rewards/{reward_id}/claim',
  '/api/v2/season/current': '/api/v2/season/current',
  '/api/v2/season/history': '/api/v2/season/history',
  '/api/v2/session/bootstrap': '/api/v2/session/bootstrap',
  '/api/v2/shows/debate': '/api/v2/shows/debate',
  '/api/v2/shows/post-match/{match_id}': '/api/v2/shows/post-match/{match_id}',
  '/api/v2/shows/pre-match/{match_id}': '/api/v2/shows/pre-match/{match_id}',
  '/api/v2/simulation-matchmaking/hosted-competitions/preview':
      '/api/v2/simulation-matchmaking/hosted-competitions/preview',
  '/api/v2/simulation-matchmaking/profiles/{user_id}':
      '/api/v2/simulation-matchmaking/profiles/{user_id}',
  '/api/v2/simulation-matchmaking/quick-game':
      '/api/v2/simulation-matchmaking/quick-game',
  '/api/v2/simulation-matchmaking/quick-tournament':
      '/api/v2/simulation-matchmaking/quick-tournament',
  '/api/v2/social/clubs/{club_id}/community':
      '/api/v2/social/clubs/{club_id}/community',
  '/api/v2/social/clubs/{club_id}/community/messages':
      '/api/v2/social/clubs/{club_id}/community/messages',
  '/api/v2/social/feed': '/api/v2/social/feed',
  '/api/v2/social/follows': '/api/v2/social/follows',
  '/api/v2/social/follows/me': '/api/v2/social/follows/me',
  '/api/v2/social/profile/me': '/api/v2/social/profile/me',
  '/api/v2/social/rivalries/{club_a_id}/{club_b_id}':
      '/api/v2/social/rivalries/{club_a_id}/{club_b_id}',
  '/api/v2/social/rivalries/{club_a_id}/{club_b_id}/banter':
      '/api/v2/social/rivalries/{club_a_id}/{club_b_id}/banter',
  '/api/v2/sponsors': '/api/v2/sponsors',
  '/api/v2/sponsorship/clubs/{club_id}/contracts':
      '/api/v2/sponsorship/clubs/{club_id}/contracts',
  '/api/v2/sponsorship/clubs/{club_id}/dashboard':
      '/api/v2/sponsorship/clubs/{club_id}/dashboard',
  '/api/v2/sponsorship/clubs/{club_id}/offers':
      '/api/v2/sponsorship/clubs/{club_id}/offers',
  '/api/v2/sponsorship/clubs/{club_id}/sponsors':
      '/api/v2/sponsorship/clubs/{club_id}/sponsors',
  '/api/v2/sponsorship/contracts/request':
      '/api/v2/sponsorship/contracts/request',
  '/api/v2/sponsorship/me/leads': '/api/v2/sponsorship/me/leads',
  '/api/v2/sponsorship/packages': '/api/v2/sponsorship/packages',
  '/api/v2/sponsorship/placements': '/api/v2/sponsorship/placements',
  '/api/v2/stories': '/api/v2/stories',
  '/api/v2/stories/generate': '/api/v2/stories/generate',
  '/api/v2/story-feed': '/api/v2/story-feed',
  '/api/v2/story-feed/digest': '/api/v2/story-feed/digest',
  '/api/v2/streamer-tournaments': '/api/v2/streamer-tournaments',
  '/api/v2/streamer-tournaments/mine': '/api/v2/streamer-tournaments/mine',
  '/api/v2/streamer-tournaments/{tournament_id}':
      '/api/v2/streamer-tournaments/{tournament_id}',
  '/api/v2/streamer-tournaments/{tournament_id}/invites':
      '/api/v2/streamer-tournaments/{tournament_id}/invites',
  '/api/v2/streamer-tournaments/{tournament_id}/join':
      '/api/v2/streamer-tournaments/{tournament_id}/join',
  '/api/v2/streamer-tournaments/{tournament_id}/publish':
      '/api/v2/streamer-tournaments/{tournament_id}/publish',
  '/api/v2/streamer-tournaments/{tournament_id}/rewards':
      '/api/v2/streamer-tournaments/{tournament_id}/rewards',
  '/api/v2/surveillance/circular-trade-alerts':
      '/api/v2/surveillance/circular-trade-alerts',
  '/api/v2/surveillance/holder-concentration-alerts':
      '/api/v2/surveillance/holder-concentration-alerts',
  '/api/v2/surveillance/suspicious-clusters':
      '/api/v2/surveillance/suspicious-clusters',
  '/api/v2/surveillance/suspicious-players':
      '/api/v2/surveillance/suspicious-players',
  '/api/v2/surveillance/thin-market-alerts':
      '/api/v2/surveillance/thin-market-alerts',
  '/api/v2/sync/update': '/api/v2/sync/update',
  '/api/v2/tasks': '/api/v2/tasks',
  '/api/v2/tasks/{task_id}/claim': '/api/v2/tasks/{task_id}/claim',
  '/api/v2/tickets/attendance/{match_id}/react':
      '/api/v2/tickets/attendance/{match_id}/react',
  '/api/v2/tickets/buy': '/api/v2/tickets/buy',
  '/api/v2/tickets/event/{match_id}': '/api/v2/tickets/event/{match_id}',
  '/api/v2/tickets/resell': '/api/v2/tickets/resell',
  '/api/v2/tickets/waitlist': '/api/v2/tickets/waitlist',
  '/api/v2/tournaments': '/api/v2/tournaments',
  '/api/v2/tournaments/{tournament_id}': '/api/v2/tournaments/{tournament_id}',
  '/api/v2/tournaments/{tournament_id}/advance':
      '/api/v2/tournaments/{tournament_id}/advance',
  '/api/v2/tournaments/{tournament_id}/join':
      '/api/v2/tournaments/{tournament_id}/join',
  '/api/v2/tournaments/{tournament_id}/matches/{match_id}/result':
      '/api/v2/tournaments/{tournament_id}/matches/{match_id}/result',
  '/api/v2/tournaments/{tournament_id}/rent':
      '/api/v2/tournaments/{tournament_id}/rent',
  '/api/v2/tournaments/{tournament_id}/squad':
      '/api/v2/tournaments/{tournament_id}/squad',
  '/api/v2/trader/markets': '/api/v2/trader/markets',
  '/api/v2/trader/orders': '/api/v2/trader/orders',
  '/api/v2/trader/overview': '/api/v2/trader/overview',
  '/api/v2/trader/p2p': '/api/v2/trader/p2p',
  '/api/v2/trader/security/totp/setup': '/api/v2/trader/security/totp/setup',
  '/api/v2/trader/watchlist': '/api/v2/trader/watchlist',
  '/api/v2/transfer-market/clubs/{club_id}/team-dynamics':
      '/api/v2/transfer-market/clubs/{club_id}/team-dynamics',
  '/api/v2/transfer-market/coaches/{club_id}/demands':
      '/api/v2/transfer-market/coaches/{club_id}/demands',
  '/api/v2/transfer-market/coaches/{club_id}/profile':
      '/api/v2/transfer-market/coaches/{club_id}/profile',
  '/api/v2/transfer-market/jobs/run': '/api/v2/transfer-market/jobs/run',
  '/api/v2/transfer-market/listings': '/api/v2/transfer-market/listings',
  '/api/v2/transfer-market/listings/{listing_id}':
      '/api/v2/transfer-market/listings/{listing_id}',
  '/api/v2/transfer-market/listings/{listing_id}/bids':
      '/api/v2/transfer-market/listings/{listing_id}/bids',
  '/api/v2/transfer-market/listings/{listing_id}/close':
      '/api/v2/transfer-market/listings/{listing_id}/close',
  '/api/v2/transfer-market/listings/{listing_id}/contract-offer':
      '/api/v2/transfer-market/listings/{listing_id}/contract-offer',
  '/api/v2/transfer-market/listings/{listing_id}/negotiation':
      '/api/v2/transfer-market/listings/{listing_id}/negotiation',
  '/api/v2/transfer-market/listings/{listing_id}/stream':
      '/api/v2/transfer-market/listings/{listing_id}/stream',
  '/api/v2/transfer-market/players/{player_id}/decision-profile':
      '/api/v2/transfer-market/players/{player_id}/decision-profile',
  '/api/v2/transfer-market/watchlist': '/api/v2/transfer-market/watchlist',
  '/api/v2/transfers/windows': '/api/v2/transfers/windows',
  '/api/v2/transfers/windows/{window_id}':
      '/api/v2/transfers/windows/{window_id}',
  '/api/v2/transfers/windows/{window_id}/bids':
      '/api/v2/transfers/windows/{window_id}/bids',
  '/api/v2/transfers/windows/{window_id}/bids/{bid_id}/accept':
      '/api/v2/transfers/windows/{window_id}/bids/{bid_id}/accept',
  '/api/v2/transfers/windows/{window_id}/bids/{bid_id}/reject':
      '/api/v2/transfers/windows/{window_id}/bids/{bid_id}/reject',
  '/api/v2/transfers/windows/{window_id}/players/{player_id}/regen-bid-evaluations':
      '/api/v2/transfers/windows/{window_id}/players/{player_id}/regen-bid-evaluations',
  '/api/v2/transfers/windows/{window_id}/players/{player_id}/resolve-regen-bid':
      '/api/v2/transfers/windows/{window_id}/players/{player_id}/resolve-regen-bid',
  '/api/v2/trust/me': '/api/v2/trust/me',
  '/api/v2/trust/{user_id}': '/api/v2/trust/{user_id}',
  '/api/v2/ultimate-league/competitors/{competitor_id}':
      '/api/v2/ultimate-league/competitors/{competitor_id}',
  '/api/v2/ultimate-league/matches/result':
      '/api/v2/ultimate-league/matches/result',
  '/api/v2/ultimate-league/matchmaking/batch':
      '/api/v2/ultimate-league/matchmaking/batch',
  '/api/v2/ultimate-league/standings/{tier}':
      '/api/v2/ultimate-league/standings/{tier}',
  '/api/v2/ultimate-league/tactical-presets':
      '/api/v2/ultimate-league/tactical-presets',
  '/api/v2/ultimate-league/tactical-presets/{preset_id}/purchase':
      '/api/v2/ultimate-league/tactical-presets/{preset_id}/purchase',
  '/api/v2/ultimate-league/tiers': '/api/v2/ultimate-league/tiers',
  '/api/v2/ultimate-league/tournaments': '/api/v2/ultimate-league/tournaments',
  '/api/v2/ultimate-league/tournaments/{tournament_id}':
      '/api/v2/ultimate-league/tournaments/{tournament_id}',
  '/api/v2/ultimate-league/tournaments/{tournament_id}/payouts/preview':
      '/api/v2/ultimate-league/tournaments/{tournament_id}/payouts/preview',
  '/api/v2/users/me': '/api/v2/users/me',
  '/api/v2/users/me/profile': '/api/v2/users/me/profile',
  '/api/v2/users/suggestions': '/api/v2/users/suggestions',
  '/api/v2/users/{user_id}': '/api/v2/users/{user_id}',
  '/api/v2/users/{user_id}/follow': '/api/v2/users/{user_id}/follow',
  '/api/v2/users/{user_id}/followers': '/api/v2/users/{user_id}/followers',
  '/api/v2/users/{user_id}/following': '/api/v2/users/{user_id}/following',
  '/api/v2/value-engine/snapshots/rebuild':
      '/api/v2/value-engine/snapshots/rebuild',
  '/api/v2/value-engine/snapshots/{player_id}/daily-closes':
      '/api/v2/value-engine/snapshots/{player_id}/daily-closes',
  '/api/v2/value-engine/snapshots/{player_id}/history':
      '/api/v2/value-engine/snapshots/{player_id}/history',
  '/api/v2/value-engine/snapshots/{player_id}/latest':
      '/api/v2/value-engine/snapshots/{player_id}/latest',
  '/api/v2/value-engine/snapshots/{player_id}/trend-summary':
      '/api/v2/value-engine/snapshots/{player_id}/trend-summary',
  '/api/v2/viral/accounts': '/api/v2/viral/accounts',
  '/api/v2/viral/cascades': '/api/v2/viral/cascades',
  '/api/v2/viral/clips/trending': '/api/v2/viral/clips/trending',
  '/api/v2/viral/clips/{clip_id}/variants':
      '/api/v2/viral/clips/{clip_id}/variants',
  '/api/v2/viral/clips/{clip_id}/winner':
      '/api/v2/viral/clips/{clip_id}/winner',
  '/api/v2/viral/feed': '/api/v2/viral/feed',
  '/api/v2/viral/feed/for-you': '/api/v2/viral/feed/for-you',
  '/api/v2/viral/matches/{match_key}/clips':
      '/api/v2/viral/matches/{match_key}/clips',
  '/api/v2/viral/sessions/{session_id}': '/api/v2/viral/sessions/{session_id}',
  '/api/v2/wallet': '/api/v2/wallet',
  '/api/v2/wallet/top-up/initiate': '/api/v2/wallet/top-up/initiate',
  '/api/v2/wallet/top-up/verify': '/api/v2/wallet/top-up/verify',
  '/api/v2/wallet/transactions': '/api/v2/wallet/transactions',
  '/api/v2/wallets': '/api/v2/wallets',
  '/api/v2/wallets/accounts': '/api/v2/wallets/accounts',
  '/api/v2/wallets/adaptive-overview': '/api/v2/wallets/adaptive-overview',
  '/api/v2/wallets/conversions': '/api/v2/wallets/conversions',
  '/api/v2/wallets/conversions/quote': '/api/v2/wallets/conversions/quote',
  '/api/v2/wallets/deposits': '/api/v2/wallets/deposits',
  '/api/v2/wallets/deposits/{deposit_id}/submit':
      '/api/v2/wallets/deposits/{deposit_id}/submit',
  '/api/v2/wallets/ledger': '/api/v2/wallets/ledger',
  '/api/v2/wallets/market-topups': '/api/v2/wallets/market-topups',
  '/api/v2/wallets/overview': '/api/v2/wallets/overview',
  '/api/v2/wallets/payment-events': '/api/v2/wallets/payment-events',
  '/api/v2/wallets/providers/{provider_key}/webhook':
      '/api/v2/wallets/providers/{provider_key}/webhook',
  '/api/v2/wallets/purchase-orders': '/api/v2/wallets/purchase-orders',
  '/api/v2/wallets/purchase-orders/quote':
      '/api/v2/wallets/purchase-orders/quote',
  '/api/v2/wallets/purchase-orders/{order_id}':
      '/api/v2/wallets/purchase-orders/{order_id}',
  '/api/v2/wallets/summary': '/api/v2/wallets/summary',
  '/api/v2/wallets/top-up/initiate': '/api/v2/wallets/top-up/initiate',
  '/api/v2/wallets/top-up/verify': '/api/v2/wallets/top-up/verify',
  '/api/v2/wallets/transactions': '/api/v2/wallets/transactions',
  '/api/v2/wallets/withdrawals': '/api/v2/wallets/withdrawals',
  '/api/v2/wallets/withdrawals/eligibility':
      '/api/v2/wallets/withdrawals/eligibility',
  '/api/v2/wallets/withdrawals/quote': '/api/v2/wallets/withdrawals/quote',
  '/api/v2/wallets/withdrawals/{withdrawal_id}/receipt':
      '/api/v2/wallets/withdrawals/{withdrawal_id}/receipt',
  '/api/v2/world-super-cup/countdown': '/api/v2/world-super-cup/countdown',
  '/api/v2/world-super-cup/groups/table':
      '/api/v2/world-super-cup/groups/table',
  '/api/v2/world-super-cup/knockout/bracket':
      '/api/v2/world-super-cup/knockout/bracket',
  '/api/v2/world-super-cup/playoff/draw':
      '/api/v2/world-super-cup/playoff/draw',
  '/api/v2/world-super-cup/qualification/explanation':
      '/api/v2/world-super-cup/qualification/explanation',
  '/api/v2/world/clubs/{club_id}/context':
      '/api/v2/world/clubs/{club_id}/context',
  '/api/v2/world/competitions/{competition_id}/context':
      '/api/v2/world/competitions/{competition_id}/context',
  '/api/v2/world/cultures': '/api/v2/world/cultures',
  '/api/v2/world/narratives': '/api/v2/world/narratives',
  '/api/v2/ws/market/{listing_id}': '/api/v2/ws/market/{listing_id}',
  '/api/v2/ws/match/{match_id}': '/api/v2/ws/match/{match_id}',
  '/api/v2/ws/notifications': '/api/v2/ws/notifications',
  '/api/v2/ws/spectate/{match_id}': '/api/v2/ws/spectate/{match_id}',
  '/api/v2/ws/tournament/{tournament_id}':
      '/api/v2/ws/tournament/{tournament_id}',
  '/api/value-engine/snapshots/rebuild':
      '/api/v2/value-engine/snapshots/rebuild',
  '/api/value-engine/snapshots/{player_id}/daily-closes':
      '/api/v2/value-engine/snapshots/{player_id}/daily-closes',
  '/api/value-engine/snapshots/{player_id}/history':
      '/api/v2/value-engine/snapshots/{player_id}/history',
  '/api/value-engine/snapshots/{player_id}/latest':
      '/api/v2/value-engine/snapshots/{player_id}/latest',
  '/api/value-engine/snapshots/{player_id}/trend-summary':
      '/api/v2/value-engine/snapshots/{player_id}/trend-summary',
  '/api/version': '/version',
  '/api/viral/accounts': '/api/v2/viral/accounts',
  '/api/viral/cascades': '/api/v2/viral/cascades',
  '/api/viral/clips/trending': '/api/v2/viral/clips/trending',
  '/api/viral/clips/{clip_id}/variants':
      '/api/v2/viral/clips/{clip_id}/variants',
  '/api/viral/clips/{clip_id}/winner': '/api/v2/viral/clips/{clip_id}/winner',
  '/api/viral/feed': '/api/v2/viral/feed',
  '/api/viral/feed/for-you': '/api/v2/viral/feed/for-you',
  '/api/viral/matches/{match_key}/clips':
      '/api/v2/viral/matches/{match_key}/clips',
  '/api/viral/sessions/{session_id}': '/api/v2/viral/sessions/{session_id}',
  '/api/wallet': '/api/v2/wallet',
  '/api/wallet/top-up/initiate': '/api/v2/wallet/top-up/initiate',
  '/api/wallet/top-up/verify': '/api/v2/wallet/top-up/verify',
  '/api/wallet/transactions': '/api/v2/wallet/transactions',
  '/api/wallets': '/api/v2/wallets',
  '/api/wallets/accounts': '/api/v2/wallets/accounts',
  '/api/wallets/adaptive-overview': '/api/v2/wallets/adaptive-overview',
  '/api/wallets/conversions': '/api/v2/wallets/conversions',
  '/api/wallets/conversions/quote': '/api/v2/wallets/conversions/quote',
  '/api/wallets/deposits': '/api/v2/wallets/deposits',
  '/api/wallets/deposits/{deposit_id}/submit':
      '/api/v2/wallets/deposits/{deposit_id}/submit',
  '/api/wallets/ledger': '/api/v2/wallets/ledger',
  '/api/wallets/market-topups': '/api/v2/wallets/market-topups',
  '/api/wallets/overview': '/api/v2/wallets/overview',
  '/api/wallets/payment-events': '/api/v2/wallets/payment-events',
  '/api/wallets/providers/{provider_key}/webhook':
      '/api/v2/wallets/providers/{provider_key}/webhook',
  '/api/wallets/purchase-orders': '/api/v2/wallets/purchase-orders',
  '/api/wallets/purchase-orders/quote': '/api/v2/wallets/purchase-orders/quote',
  '/api/wallets/purchase-orders/{order_id}':
      '/api/v2/wallets/purchase-orders/{order_id}',
  '/api/wallets/summary': '/api/v2/wallets/summary',
  '/api/wallets/top-up/initiate': '/api/v2/wallets/top-up/initiate',
  '/api/wallets/top-up/verify': '/api/v2/wallets/top-up/verify',
  '/api/wallets/transactions': '/api/v2/wallets/transactions',
  '/api/wallets/withdrawals': '/api/v2/wallets/withdrawals',
  '/api/wallets/withdrawals/eligibility':
      '/api/v2/wallets/withdrawals/eligibility',
  '/api/wallets/withdrawals/quote': '/api/v2/wallets/withdrawals/quote',
  '/api/wallets/withdrawals/{withdrawal_id}/receipt':
      '/api/v2/wallets/withdrawals/{withdrawal_id}/receipt',
  '/api/world-super-cup/countdown': '/api/v2/world-super-cup/countdown',
  '/api/world-super-cup/groups/table': '/api/v2/world-super-cup/groups/table',
  '/api/world-super-cup/knockout/bracket':
      '/api/v2/world-super-cup/knockout/bracket',
  '/api/world-super-cup/playoff/draw': '/api/v2/world-super-cup/playoff/draw',
  '/api/world-super-cup/qualification/explanation':
      '/api/v2/world-super-cup/qualification/explanation',
  '/api/world/clubs/{club_id}/context': '/api/v2/world/clubs/{club_id}/context',
  '/api/world/competitions/{competition_id}/context':
      '/api/v2/world/competitions/{competition_id}/context',
  '/api/world/cultures': '/api/v2/world/cultures',
  '/api/world/narratives': '/api/v2/world/narratives',
  '/auth/confirm-email': '/api/v2/auth/confirm-email',
  '/auth/login': '/api/v2/auth/login',
  '/auth/logout': '/api/v2/auth/logout',
  '/auth/recovery/request': '/api/v2/auth/recovery/request',
  '/auth/recovery/reset': '/api/v2/auth/recovery/reset',
  '/auth/refresh': '/api/v2/auth/refresh',
  '/auth/signup/creator': '/api/v2/auth/signup/creator',
  '/auth/signup/trader': '/api/v2/auth/signup/trader',
  '/auth/signup/user': '/api/v2/auth/signup/user',
  '/awards/categories': '/api/v2/awards/categories',
  '/awards/ceremony': '/api/v2/awards/ceremony',
  '/awards/ceremony/tickets': '/api/v2/awards/ceremony/tickets',
  '/awards/ceremony/vote': '/api/v2/awards/ceremony/vote',
  '/awards/nominees': '/api/v2/awards/nominees',
  '/awards/winners': '/api/v2/awards/winners',
  '/bets/history': '/api/v2/bets/history',
  '/bets/odds/{match_id}': '/api/v2/bets/odds/{match_id}',
  '/bets/place': '/api/v2/bets/place',
  '/bets/preferences': '/api/v2/bets/preferences',
  '/broadcast-rights/auctions/{auction_id}/bids':
      '/api/v2/broadcast-rights/auctions/{auction_id}/bids',
  '/broadcast-rights/competitions/{competition_id}':
      '/api/v2/broadcast-rights/competitions/{competition_id}',
  '/broadcast-rights/competitions/{competition_id}/acquire':
      '/api/v2/broadcast-rights/competitions/{competition_id}/acquire',
  '/broadcast-rights/competitions/{competition_id}/auctions':
      '/api/v2/broadcast-rights/competitions/{competition_id}/auctions',
  '/broadcast-rights/matches/{match_id}/access':
      '/api/v2/broadcast-rights/matches/{match_id}/access',
  '/broadcast-rights/matches/{match_id}/distribute':
      '/api/v2/broadcast-rights/matches/{match_id}/distribute',
  '/broadcast-rights/{right_id}/grants':
      '/api/v2/broadcast-rights/{right_id}/grants',
  '/broadcast/channels': '/api/v2/broadcast/channels',
  '/broadcast/{match_id}': '/api/v2/broadcast/{match_id}',
  '/calendar-engine/dashboard': '/api/v2/calendar-engine/dashboard',
  '/calendar-engine/events': '/api/v2/calendar-engine/events',
  '/calendar-engine/lifecycle-runs': '/api/v2/calendar-engine/lifecycle-runs',
  '/calendar-engine/pause-status': '/api/v2/calendar-engine/pause-status',
  '/calendar-engine/seasons': '/api/v2/calendar-engine/seasons',
  '/campaigns': '/api/v2/campaigns',
  '/campaigns/create': '/api/v2/campaigns/create',
  '/campaigns/{id}/accept': '/api/v2/campaigns/{id}/accept',
  '/campaigns/{id}/apply': '/api/v2/campaigns/{id}/apply',
  '/campaigns/{id}/performance': '/api/v2/campaigns/{id}/performance',
  '/career/create': '/api/v2/career/create',
  '/career/retire': '/api/v2/career/retire',
  '/career/train': '/api/v2/career/train',
  '/career/transfer': '/api/v2/career/transfer',
  '/career/{user_id}': '/api/v2/career/{user_id}',
  '/champions-league/knockout-bracket':
      '/api/v2/champions-league/knockout-bracket',
  '/champions-league/league-phase/table':
      '/api/v2/champions-league/league-phase/table',
  '/champions-league/playoff-bracket':
      '/api/v2/champions-league/playoff-bracket',
  '/champions-league/prize-pool/preview':
      '/api/v2/champions-league/prize-pool/preview',
  '/champions-league/qualification-map':
      '/api/v2/champions-league/qualification-map',
  '/club-infra/clubs/{club_id}': '/api/v2/club-infra/clubs/{club_id}',
  '/club-infra/clubs/{club_id}/support':
      '/api/v2/club-infra/clubs/{club_id}/support',
  '/club-infra/my': '/api/v2/club-infra/my',
  '/club-infra/my/facilities/upgrade':
      '/api/v2/club-infra/my/facilities/upgrade',
  '/club-infra/my/stadium/upgrade': '/api/v2/club-infra/my/stadium/upgrade',
  '/club/identity': '/api/v2/club/identity',
  '/clubs/marketplace': '/api/v2/clubs/marketplace',
  '/clubs/{club_id}': '/api/v2/clubs/{club_id}',
  '/clubs/{club_id}/buy-tokens': '/api/v2/clubs/{club_id}/buy-tokens',
  '/clubs/{club_id}/ownership': '/api/v2/clubs/{club_id}/ownership',
  '/clubs/{club_id}/proposals': '/api/v2/clubs/{club_id}/proposals',
  '/clubs/{club_id}/sell-tokens': '/api/v2/clubs/{club_id}/sell-tokens',
  '/clubs/{club_id}/treasury': '/api/v2/clubs/{club_id}/treasury',
  '/clubs/{club_id}/vote': '/api/v2/clubs/{club_id}/vote',
  '/commentary/profiles': '/api/v2/commentary/profiles',
  '/commentary/select': '/api/v2/commentary/select',
  '/community/creator-clubs/{club_id}/fan-competitions':
      '/api/v2/community/creator-clubs/{club_id}/fan-competitions',
  '/community/creator-clubs/{club_id}/fan-groups':
      '/api/v2/community/creator-clubs/{club_id}/fan-groups',
  '/community/creator-clubs/{club_id}/fan-state':
      '/api/v2/community/creator-clubs/{club_id}/fan-state',
  '/community/creator-clubs/{club_id}/follow':
      '/api/v2/community/creator-clubs/{club_id}/follow',
  '/community/creator-matches/{match_id}/chat-room':
      '/api/v2/community/creator-matches/{match_id}/chat-room',
  '/community/creator-matches/{match_id}/chat-room/messages':
      '/api/v2/community/creator-matches/{match_id}/chat-room/messages',
  '/community/creator-matches/{match_id}/fan-wall':
      '/api/v2/community/creator-matches/{match_id}/fan-wall',
  '/community/creator-matches/{match_id}/rivalry-signals':
      '/api/v2/community/creator-matches/{match_id}/rivalry-signals',
  '/community/creator-matches/{match_id}/tactical-advice':
      '/api/v2/community/creator-matches/{match_id}/tactical-advice',
  '/community/digest': '/api/v2/community/digest',
  '/community/fan-competitions/{fan_competition_id}/join':
      '/api/v2/community/fan-competitions/{fan_competition_id}/join',
  '/community/fan-groups/{group_id}/join':
      '/api/v2/community/fan-groups/{group_id}/join',
  '/community/live-threads': '/api/v2/community/live-threads',
  '/community/live-threads/{thread_id}':
      '/api/v2/community/live-threads/{thread_id}',
  '/community/live-threads/{thread_id}/messages':
      '/api/v2/community/live-threads/{thread_id}/messages',
  '/community/private-messages/threads':
      '/api/v2/community/private-messages/threads',
  '/community/private-messages/threads/{thread_id}':
      '/api/v2/community/private-messages/threads/{thread_id}',
  '/community/private-messages/threads/{thread_id}/messages':
      '/api/v2/community/private-messages/threads/{thread_id}/messages',
  '/community/watchlist': '/api/v2/community/watchlist',
  '/community/watchlist/{competition_key}':
      '/api/v2/community/watchlist/{competition_key}',
  '/competitions': '/api/v2/competitions',
  '/competitive-integrity/fast-game/runs':
      '/api/v2/competitive-integrity/fast-game/runs',
  '/competitive-integrity/fast-game/runs/{run_id}':
      '/api/v2/competitive-integrity/fast-game/runs/{run_id}',
  '/competitive-integrity/fast-game/runs/{run_id}/play':
      '/api/v2/competitive-integrity/fast-game/runs/{run_id}/play',
  '/competitive-integrity/managers': '/api/v2/competitive-integrity/managers',
  '/competitive-integrity/managers/candidates':
      '/api/v2/competitive-integrity/managers/candidates',
  '/competitive-integrity/managers/{manager_id}/instructions':
      '/api/v2/competitive-integrity/managers/{manager_id}/instructions',
  '/competitive-integrity/matches': '/api/v2/competitive-integrity/matches',
  '/competitive-integrity/matches/{match_id}':
      '/api/v2/competitive-integrity/matches/{match_id}',
  '/competitive-integrity/matches/{match_id}/execute':
      '/api/v2/competitive-integrity/matches/{match_id}/execute',
  '/competitive-integrity/notifications/events':
      '/api/v2/competitive-integrity/notifications/events',
  '/config/current': '/api/v2/config/current',
  '/config/update': '/api/v2/config/update',
  '/conversations': '/api/v2/conversations',
  '/conversations/start': '/api/v2/conversations/start',
  '/conversations/{conversation_id}/message':
      '/api/v2/conversations/{conversation_id}/message',
  '/conversations/{conversation_id}/messages':
      '/api/v2/conversations/{conversation_id}/messages',
  '/conversations/{conversation_id}/status':
      '/api/v2/conversations/{conversation_id}/status',
  '/creator-campaigns': '/api/v2/creator-campaigns',
  '/creator-campaigns/me': '/api/v2/creator-campaigns/me',
  '/creator-campaigns/{campaign_id}': '/api/v2/creator-campaigns/{campaign_id}',
  '/creator-campaigns/{campaign_id}/metrics':
      '/api/v2/creator-campaigns/{campaign_id}/metrics',
  '/creator-campaigns/{campaign_id}/snapshot':
      '/api/v2/creator-campaigns/{campaign_id}/snapshot',
  '/creator-campaigns/{campaign_id}/snapshots':
      '/api/v2/creator-campaigns/{campaign_id}/snapshots',
  '/creator-league': '/api/v2/creator-league',
  '/creator-league/config': '/api/v2/creator-league/config',
  '/creator-league/financial-report': '/api/v2/creator-league/financial-report',
  '/creator-league/financial-settlements':
      '/api/v2/creator-league/financial-settlements',
  '/creator-league/financial-settlements/{settlement_id}/approve':
      '/api/v2/creator-league/financial-settlements/{settlement_id}/approve',
  '/creator-league/live-priority': '/api/v2/creator-league/live-priority',
  '/creator-league/reset': '/api/v2/creator-league/reset',
  '/creator-league/season-tiers/{season_tier_id}/standings':
      '/api/v2/creator-league/season-tiers/{season_tier_id}/standings',
  '/creator-league/seasons': '/api/v2/creator-league/seasons',
  '/creator-league/seasons/{season_id}':
      '/api/v2/creator-league/seasons/{season_id}',
  '/creator-league/seasons/{season_id}/pause':
      '/api/v2/creator-league/seasons/{season_id}/pause',
  '/creator-league/tiers': '/api/v2/creator-league/tiers',
  '/creator-league/tiers/{tier_id}': '/api/v2/creator-league/tiers/{tier_id}',
  '/creator/application': '/api/v2/creator/application',
  '/creator/apply': '/api/v2/creator/apply',
  '/creator/cards': '/api/v2/creator/cards',
  '/creator/cards/listings': '/api/v2/creator/cards/listings',
  '/creator/cards/listings/{listing_id}/buy':
      '/api/v2/creator/cards/listings/{listing_id}/buy',
  '/creator/cards/loans/{loan_id}/return':
      '/api/v2/creator/cards/loans/{loan_id}/return',
  '/creator/cards/swap': '/api/v2/creator/cards/swap',
  '/creator/cards/{creator_card_id}/list':
      '/api/v2/creator/cards/{creator_card_id}/list',
  '/creator/cards/{creator_card_id}/loan':
      '/api/v2/creator/cards/{creator_card_id}/loan',
  '/creator/clubs/{club_id}/fan-share-market':
      '/api/v2/creator/clubs/{club_id}/fan-share-market',
  '/creator/clubs/{club_id}/fan-share-market/distributions':
      '/api/v2/creator/clubs/{club_id}/fan-share-market/distributions',
  '/creator/clubs/{club_id}/fan-share-market/holding':
      '/api/v2/creator/clubs/{club_id}/fan-share-market/holding',
  '/creator/clubs/{club_id}/fan-share-market/purchase':
      '/api/v2/creator/clubs/{club_id}/fan-share-market/purchase',
  '/creator/verify-email': '/api/v2/creator/verify-email',
  '/creator/verify-phone': '/api/v2/creator/verify-phone',
  '/creators/marketplace': '/api/v2/creators/marketplace',
  '/creators/me/copilot/analyze': '/api/v2/creators/me/copilot/analyze',
  '/creators/me/insights': '/api/v2/creators/me/insights',
  '/creators/me/reputation': '/api/v2/creators/me/reputation',
  '/daily-challenges': '/api/v2/daily-challenges',
  '/daily-challenges/me': '/api/v2/daily-challenges/me',
  '/daily-challenges/{challenge_key}/claim':
      '/api/v2/daily-challenges/{challenge_key}/claim',
  '/diagnostics': '/api/v2/diagnostics',
  '/discovery/home': '/api/v2/discovery/home',
  '/discovery/saved-searches': '/api/v2/discovery/saved-searches',
  '/discovery/saved-searches/{search_id}':
      '/api/v2/discovery/saved-searches/{search_id}',
  '/discovery/search': '/api/v2/discovery/search',
  '/disputes': '/api/v2/disputes',
  '/disputes/me': '/api/v2/disputes/me',
  '/disputes/{dispute_id}': '/api/v2/disputes/{dispute_id}',
  '/disputes/{dispute_id}/messages': '/api/v2/disputes/{dispute_id}/messages',
  '/dynasty': '/api/v2/dynasty',
  '/dynasty/leaderboard': '/api/v2/dynasty/leaderboard',
  '/economy/fx/quote': '/api/v2/economy/fx/quote',
  '/economy/gift-catalog': '/api/v2/economy/gift-catalog',
  '/economy/service-pricing': '/api/v2/economy/service-pricing',
  '/engagement/achievements': '/api/v2/engagement/achievements',
  '/engagement/achievements/me': '/api/v2/engagement/achievements/me',
  '/engagement/milestones/me': '/api/v2/engagement/milestones/me',
  '/engagement/sync': '/api/v2/engagement/sync',
  '/enter': '/api/v2/enter',
  '/events/clip': '/api/v2/events/clip',
  '/events/today': '/api/v2/events/today',
  '/events/upcoming': '/api/v2/events/upcoming',
  '/experience/full-simulation': '/api/v2/experience/full-simulation',
  '/fan-predictions/creator-clubs/{club_id}/leaderboards/weekly':
      '/api/v2/fan-predictions/creator-clubs/{club_id}/leaderboards/weekly',
  '/fan-predictions/leaderboards/weekly':
      '/api/v2/fan-predictions/leaderboards/weekly',
  '/fan-predictions/matches/{match_id}':
      '/api/v2/fan-predictions/matches/{match_id}',
  '/fan-predictions/matches/{match_id}/leaderboard':
      '/api/v2/fan-predictions/matches/{match_id}/leaderboard',
  '/fan-predictions/matches/{match_id}/submissions':
      '/api/v2/fan-predictions/matches/{match_id}/submissions',
  '/fan-predictions/me/submissions': '/api/v2/fan-predictions/me/submissions',
  '/fan-predictions/me/tokens': '/api/v2/fan-predictions/me/tokens',
  '/fan-wars/leaderboards/{board_type}':
      '/api/v2/fan-wars/leaderboards/{board_type}',
  '/fan-wars/nations-cup/{competition_id}':
      '/api/v2/fan-wars/nations-cup/{competition_id}',
  '/fan-wars/profiles/{profile_id}/dashboard':
      '/api/v2/fan-wars/profiles/{profile_id}/dashboard',
  '/fan-wars/rivalries/{board_type}': '/api/v2/fan-wars/rivalries/{board_type}',
  '/fans/profile': '/api/v2/fans/profile',
  '/fans/tribe/join': '/api/v2/fans/tribe/join',
  '/fans/{club_id}': '/api/v2/fans/{club_id}',
  '/fast-cups/upcoming': '/api/v2/fast-cups/upcoming',
  '/fast-cups/{cup_id}/bracket': '/api/v2/fast-cups/{cup_id}/bracket',
  '/fast-cups/{cup_id}/countdown': '/api/v2/fast-cups/{cup_id}/countdown',
  '/fast-cups/{cup_id}/join': '/api/v2/fast-cups/{cup_id}/join',
  '/fast-cups/{cup_id}/result-summary':
      '/api/v2/fast-cups/{cup_id}/result-summary',
  '/federations': '/api/v2/federations',
  '/federations/proposals/{proposal_id}/votes':
      '/api/v2/federations/proposals/{proposal_id}/votes',
  '/federations/rankings': '/api/v2/federations/rankings',
  '/federations/regional-tournaments':
      '/api/v2/federations/regional-tournaments',
  '/federations/{federation_id}': '/api/v2/federations/{federation_id}',
  '/federations/{federation_id}/governance':
      '/api/v2/federations/{federation_id}/governance',
  '/federations/{federation_id}/leagues':
      '/api/v2/federations/{federation_id}/leagues',
  '/federations/{federation_id}/memberships':
      '/api/v2/federations/{federation_id}/memberships',
  '/federations/{federation_id}/narratives':
      '/api/v2/federations/{federation_id}/narratives',
  '/federations/{federation_id}/proposals':
      '/api/v2/federations/{federation_id}/proposals',
  '/federations/{federation_id}/sanctions':
      '/api/v2/federations/{federation_id}/sanctions',
  '/federations/{federation_id}/treasury/distribute':
      '/api/v2/federations/{federation_id}/treasury/distribute',
  '/federations/{federation_id}/validate-action':
      '/api/v2/federations/{federation_id}/validate-action',
  '/feed/following': '/api/v2/feed/following',
  '/feed/for-you': '/api/v2/feed/for-you',
  '/feed/for-you/refresh': '/api/v2/feed/for-you/refresh',
  '/feed/sponsored': '/api/v2/feed/sponsored',
  '/finance': '/api/v2/finance',
  '/follow/{user_id}': '/api/v2/follow/{user_id}',
  '/football-events/players/{player_id}/events':
      '/api/v2/football-events/players/{player_id}/events',
  '/football-events/players/{player_id}/impact':
      '/api/v2/football-events/players/{player_id}/impact',
  '/gift-engine/me/combos': '/api/v2/gift-engine/me/combos',
  '/gift-engine/me/summary': '/api/v2/gift-engine/me/summary',
  '/gift-engine/me/transactions': '/api/v2/gift-engine/me/transactions',
  '/gift-engine/send': '/api/v2/gift-engine/send',
  '/governance/clubs/{club_id}/panel':
      '/api/v2/governance/clubs/{club_id}/panel',
  '/governance/me/overview': '/api/v2/governance/me/overview',
  '/governance/proposals': '/api/v2/governance/proposals',
  '/governance/proposals/{proposal_id}':
      '/api/v2/governance/proposals/{proposal_id}',
  '/governance/proposals/{proposal_id}/vote':
      '/api/v2/governance/proposals/{proposal_id}/vote',
  '/gtex/market/buy': '/api/v2/gtex/market/buy',
  '/gtex/market/sell': '/api/v2/gtex/market/sell',
  '/hall-of-fame': '/api/v2/hall-of-fame',
  '/health': '/health',
  '/history/goat-rankings': '/api/v2/history/goat-rankings',
  '/history/leaderboards': '/api/v2/history/leaderboards',
  '/history/records': '/api/v2/history/records',
  '/history/timeline/{subject_type}/{subject_id}':
      '/api/v2/history/timeline/{subject_type}/{subject_id}',
  '/hosted-competitions': '/api/v2/hosted-competitions',
  '/hosted-competitions/mine': '/api/v2/hosted-competitions/mine',
  '/hosted-competitions/mine/invites':
      '/api/v2/hosted-competitions/mine/invites',
  '/hosted-competitions/templates': '/api/v2/hosted-competitions/templates',
  '/hosted-competitions/{competition_id}':
      '/api/v2/hosted-competitions/{competition_id}',
  '/hosted-competitions/{competition_id}/finance':
      '/api/v2/hosted-competitions/{competition_id}/finance',
  '/hosted-competitions/{competition_id}/invites':
      '/api/v2/hosted-competitions/{competition_id}/invites',
  '/hosted-competitions/{competition_id}/invites/accept':
      '/api/v2/hosted-competitions/{competition_id}/invites/accept',
  '/hosted-competitions/{competition_id}/join':
      '/api/v2/hosted-competitions/{competition_id}/join',
  '/hosted-competitions/{competition_id}/launch':
      '/api/v2/hosted-competitions/{competition_id}/launch',
  '/hosted-competitions/{competition_id}/standings':
      '/api/v2/hosted-competitions/{competition_id}/standings',
  '/infinite-league/economy': '/api/v2/infinite-league/economy',
  '/infinite-league/livestream': '/api/v2/infinite-league/livestream',
  '/infinite-league/matches': '/api/v2/infinite-league/matches',
  '/infinite-league/matches/{match_id}':
      '/api/v2/infinite-league/matches/{match_id}',
  '/infinite-league/pundits/{match_id}':
      '/api/v2/infinite-league/pundits/{match_id}',
  '/infinite-league/status': '/api/v2/infinite-league/status',
  '/infinite-league/tick': '/api/v2/infinite-league/tick',
  '/infinite-league/viral-feed': '/api/v2/infinite-league/viral-feed',
  '/integrations/payments/korapay/webhook':
      '/api/v2/integrations/payments/korapay/webhook',
  '/integrations/payments/methods': '/api/v2/integrations/payments/methods',
  '/integrations/payments/orders': '/api/v2/integrations/payments/orders',
  '/integrations/payments/paystack/webhook':
      '/api/v2/integrations/payments/paystack/webhook',
  '/integrations/payments/quote': '/api/v2/integrations/payments/quote',
  '/integrity-engine/me/incidents': '/api/v2/integrity-engine/me/incidents',
  '/integrity-engine/me/score': '/api/v2/integrity-engine/me/score',
  '/internal/ingestion/bootstrap-sync':
      '/api/v2/internal/ingestion/bootstrap-sync',
  '/internal/ingestion/clubs/{club_external_id}/refresh':
      '/api/v2/internal/ingestion/clubs/{club_external_id}/refresh',
  '/internal/ingestion/competitions/{competition_external_id}/refresh':
      '/api/v2/internal/ingestion/competitions/{competition_external_id}/refresh',
  '/internal/ingestion/cursors/{provider_name}':
      '/api/v2/internal/ingestion/cursors/{provider_name}',
  '/internal/ingestion/incremental-sync':
      '/api/v2/internal/ingestion/incremental-sync',
  '/internal/ingestion/players/{player_external_id}/refresh':
      '/api/v2/internal/ingestion/players/{player_external_id}/refresh',
  '/internal/ingestion/providers/{provider_name}/health':
      '/api/v2/internal/ingestion/providers/{provider_name}/health',
  '/internal/ingestion/real-players/batches':
      '/api/v2/internal/ingestion/real-players/batches',
  '/internal/ingestion/real-players/batches/{batch_id}':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}',
  '/internal/ingestion/real-players/batches/{batch_id}/issues':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}/issues',
  '/internal/ingestion/real-players/batches/{batch_id}/resume':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}/resume',
  '/internal/ingestion/real-players/batches/{batch_id}/valuation-status':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}/valuation-status',
  '/internal/ingestion/real-players/import':
      '/api/v2/internal/ingestion/real-players/import',
  '/internal/ingestion/real-players/publish-jobs':
      '/api/v2/internal/ingestion/real-players/publish-jobs',
  '/internal/ingestion/real-players/publish-jobs/{job_id}':
      '/api/v2/internal/ingestion/real-players/publish-jobs/{job_id}',
  '/internal/ingestion/real-players/status':
      '/api/v2/internal/ingestion/real-players/status',
  '/internal/ingestion/runs': '/api/v2/internal/ingestion/runs',
  '/internal/ingestion/status': '/api/v2/internal/ingestion/status',
  '/jackpot/contribute': '/api/v2/jackpot/contribute',
  '/jackpot/history': '/api/v2/jackpot/history',
  '/jackpot/state': '/api/v2/jackpot/state',
  '/jobs/{job_id}': '/api/v2/jobs/{job_id}',
  '/leaderboard/division/{division}': '/api/v2/leaderboard/division/{division}',
  '/leaderboard/global': '/api/v2/leaderboard/global',
  '/leaderboard/player/{player_id}': '/api/v2/leaderboard/player/{player_id}',
  '/leaderboard/region/{region}': '/api/v2/leaderboard/region/{region}',
  '/leagues/register': '/api/v2/leagues/register',
  '/leagues/{season_id}/fixtures': '/api/v2/leagues/{season_id}/fixtures',
  '/leagues/{season_id}/qualification-markers':
      '/api/v2/leagues/{season_id}/qualification-markers',
  '/leagues/{season_id}/standings': '/api/v2/leagues/{season_id}/standings',
  '/leagues/{season_id}/summary': '/api/v2/leagues/{season_id}/summary',
  '/legacy/board': '/api/v2/legacy/board',
  '/live-events': '/api/v2/live-events',
  '/manager-duels': '/api/v2/manager-duels',
  '/manager-duels/leaderboard': '/api/v2/manager-duels/leaderboard',
  '/manager-duels/{duel_id}': '/api/v2/manager-duels/{duel_id}',
  '/managers': '/api/v2/managers',
  '/managers/leaderboard': '/api/v2/managers/leaderboard',
  '/managers/{manager_id}': '/api/v2/managers/{manager_id}',
  '/managers/{manager_id}/hire': '/api/v2/managers/{manager_id}/hire',
  '/managers/{manager_id}/history': '/api/v2/managers/{manager_id}/history',
  '/managers/{manager_id}/release': '/api/v2/managers/{manager_id}/release',
  '/market/buy': '/api/v2/market/buy',
  '/market/listings': '/api/v2/market/listings',
  '/market/listings/{listing_id}/cancel':
      '/api/v2/market/listings/{listing_id}/cancel',
  '/market/listings/{listing_id}/matches':
      '/api/v2/market/listings/{listing_id}/matches',
  '/market/listings/{listing_id}/offers':
      '/api/v2/market/listings/{listing_id}/offers',
  '/market/movers': '/api/v2/market/movers',
  '/market/offers': '/api/v2/market/offers',
  '/market/offers/{offer_id}/accept': '/api/v2/market/offers/{offer_id}/accept',
  '/market/offers/{offer_id}/counter':
      '/api/v2/market/offers/{offer_id}/counter',
  '/market/offers/{offer_id}/reject': '/api/v2/market/offers/{offer_id}/reject',
  '/market/players': '/api/v2/market/players',
  '/market/players/{player_id}': '/api/v2/market/players/{player_id}',
  '/market/players/{player_id}/candles':
      '/api/v2/market/players/{player_id}/candles',
  '/market/players/{player_id}/history':
      '/api/v2/market/players/{player_id}/history',
  '/market/sell': '/api/v2/market/sell',
  '/market/summary/{asset_id}': '/api/v2/market/summary/{asset_id}',
  '/market/ticker/{player_id}': '/api/v2/market/ticker/{player_id}',
  '/market/trade-intents': '/api/v2/market/trade-intents',
  '/market/trade-intents/{intent_id}/withdraw':
      '/api/v2/market/trade-intents/{intent_id}/withdraw',
  '/market/trending': '/api/v2/market/trending',
  '/marketplace/my-players': '/api/v2/marketplace/my-players',
  '/marketplace/players': '/api/v2/marketplace/players',
  '/marketplace/players/{player_id}': '/api/v2/marketplace/players/{player_id}',
  '/match-engine/analytics': '/api/v2/match-engine/analytics',
  '/match-engine/analytics/{match_key}':
      '/api/v2/match-engine/analytics/{match_key}',
  '/match-engine/highlights/{match_key}':
      '/api/v2/match-engine/highlights/{match_key}',
  '/match-engine/live-feed/{match_key}':
      '/api/v2/match-engine/live-feed/{match_key}',
  '/match-engine/render-sync': '/api/v2/match-engine/render-sync',
  '/match-engine/render-sync/{match_key}':
      '/api/v2/match-engine/render-sync/{match_key}',
  '/match-engine/replay': '/api/v2/match-engine/replay',
  '/match-engine/simulate': '/api/v2/match-engine/simulate',
  '/match-engine/summary': '/api/v2/match-engine/summary',
  '/match-engine/timeline': '/api/v2/match-engine/timeline',
  '/match-viewer/{match_key}': '/api/v2/match-viewer/{match_key}',
  '/match-viewer/{match_key}/illusion':
      '/api/v2/match-viewer/{match_key}/illusion',
  '/match-viewer/{match_key}/session':
      '/api/v2/match-viewer/{match_key}/session',
  '/match/find': '/api/v2/match/find',
  '/match/live/active': '/api/v2/match/live/active',
  '/match/{match_id}/commentary/stream':
      '/api/v2/match/{match_id}/commentary/stream',
  '/match/{match_id}/live': '/api/v2/match/{match_id}/live',
  '/match/{match_id}/unity-access': '/api/v2/match/{match_id}/unity-access',
  '/match/{match_id}/unity-access/refresh':
      '/api/v2/match/{match_id}/unity-access/refresh',
  '/matches/complete': '/api/v2/matches/complete',
  '/matches/live/active': '/api/v2/matches/live/active',
  '/matches/start': '/api/v2/matches/start',
  '/matches/{match_id}/analysis': '/api/v2/matches/{match_id}/analysis',
  '/matches/{match_id}/audio/stems/stream':
      '/api/v2/matches/{match_id}/audio/stems/stream',
  '/matches/{match_id}/chat/messages':
      '/api/v2/matches/{match_id}/chat/messages',
  '/matches/{match_id}/commentary': '/api/v2/matches/{match_id}/commentary',
  '/matches/{match_id}/commentary/stream':
      '/api/v2/matches/{match_id}/commentary/stream',
  '/matches/{match_id}/fan-experience':
      '/api/v2/matches/{match_id}/fan-experience',
  '/matches/{match_id}/highlights': '/api/v2/matches/{match_id}/highlights',
  '/matches/{match_id}/live': '/api/v2/matches/{match_id}/live',
  '/matches/{match_id}/reactions': '/api/v2/matches/{match_id}/reactions',
  '/matches/{match_id}/replay': '/api/v2/matches/{match_id}/replay',
  '/matches/{match_id}/social-warfare':
      '/api/v2/matches/{match_id}/social-warfare',
  '/matches/{match_id}/spectate': '/api/v2/matches/{match_id}/spectate',
  '/matches/{match_id}/spectators': '/api/v2/matches/{match_id}/spectators',
  '/matches/{match_id}/stream': '/api/v2/matches/{match_id}/stream',
  '/matches/{match_id}/tickets': '/api/v2/matches/{match_id}/tickets',
  '/matches/{match_id}/unity-access': '/api/v2/matches/{match_id}/unity-access',
  '/matches/{match_id}/unity-access/refresh':
      '/api/v2/matches/{match_id}/unity-access/refresh',
  '/media': '/api/v2/media',
  '/media-engine/creator-league/broadcast-modes':
      '/api/v2/media-engine/creator-league/broadcast-modes',
  '/media-engine/creator-league/clubs/{club_id}/stadium':
      '/api/v2/media-engine/creator-league/clubs/{club_id}/stadium',
  '/media-engine/creator-league/matches/{match_id}/access':
      '/api/v2/media-engine/creator-league/matches/{match_id}/access',
  '/media-engine/creator-league/matches/{match_id}/analytics':
      '/api/v2/media-engine/creator-league/matches/{match_id}/analytics',
  '/media-engine/creator-league/matches/{match_id}/gifts':
      '/api/v2/media-engine/creator-league/matches/{match_id}/gifts',
  '/media-engine/creator-league/matches/{match_id}/purchase':
      '/api/v2/media-engine/creator-league/matches/{match_id}/purchase',
  '/media-engine/creator-league/matches/{match_id}/stadium':
      '/api/v2/media-engine/creator-league/matches/{match_id}/stadium',
  '/media-engine/creator-league/matches/{match_id}/stadium/placements':
      '/api/v2/media-engine/creator-league/matches/{match_id}/stadium/placements',
  '/media-engine/creator-league/matches/{match_id}/tickets':
      '/api/v2/media-engine/creator-league/matches/{match_id}/tickets',
  '/media-engine/creator-league/season-passes':
      '/api/v2/media-engine/creator-league/season-passes',
  '/media-engine/creator-league/season-passes/me':
      '/api/v2/media-engine/creator-league/season-passes/me',
  '/media-engine/downloads': '/api/v2/media-engine/downloads',
  '/media-engine/downloads/{token}': '/api/v2/media-engine/downloads/{token}',
  '/media-engine/matches/{match_key}/snapshot':
      '/api/v2/media-engine/matches/{match_key}/snapshot',
  '/media-engine/me/clip-earnings': '/api/v2/media-engine/me/clip-earnings',
  '/media-engine/me/purchases': '/api/v2/media-engine/me/purchases',
  '/media-engine/me/share-exports': '/api/v2/media-engine/me/share-exports',
  '/media-engine/purchases': '/api/v2/media-engine/purchases',
  '/media-engine/share-exports': '/api/v2/media-engine/share-exports',
  '/media-engine/share-exports/{export_id}/amplifications':
      '/api/v2/media-engine/share-exports/{export_id}/amplifications',
  '/media-engine/share-templates': '/api/v2/media-engine/share-templates',
  '/media-engine/views': '/api/v2/media-engine/views',
  '/metrics': '/api/v2/metrics',
  '/moderation/me/reports': '/api/v2/moderation/me/reports',
  '/moderation/reports': '/api/v2/moderation/reports',
  '/moments/live': '/api/v2/moments/live',
  '/national-pool': '/api/v2/national-pool',
  '/national-team-engine/competitions':
      '/api/v2/national-team-engine/competitions',
  '/national-team-engine/competitions/{competition_id}':
      '/api/v2/national-team-engine/competitions/{competition_id}',
  '/national-team-engine/competitions/{competition_id}/ads/active':
      '/api/v2/national-team-engine/competitions/{competition_id}/ads/active',
  '/national-team-engine/competitions/{competition_id}/auto-build-squad':
      '/api/v2/national-team-engine/competitions/{competition_id}/auto-build-squad',
  '/national-team-engine/competitions/{competition_id}/entries':
      '/api/v2/national-team-engine/competitions/{competition_id}/entries',
  '/national-team-engine/competitions/{competition_id}/gifts':
      '/api/v2/national-team-engine/competitions/{competition_id}/gifts',
  '/national-team-engine/competitions/{competition_id}/lifecycle':
      '/api/v2/national-team-engine/competitions/{competition_id}/lifecycle',
  '/national-team-engine/competitions/{competition_id}/presentation':
      '/api/v2/national-team-engine/competitions/{competition_id}/presentation',
  '/national-team-engine/competitions/{competition_id}/rental-entry':
      '/api/v2/national-team-engine/competitions/{competition_id}/rental-entry',
  '/national-team-engine/competitions/{competition_id}/rental-pool':
      '/api/v2/national-team-engine/competitions/{competition_id}/rental-pool',
  '/national-team-engine/competitions/{competition_id}/story-events':
      '/api/v2/national-team-engine/competitions/{competition_id}/story-events',
  '/national-team-engine/competitions/{competition_id}/theme':
      '/api/v2/national-team-engine/competitions/{competition_id}/theme',
  '/national-team-engine/entries/{entry_id}':
      '/api/v2/national-team-engine/entries/{entry_id}',
  '/national-team-engine/entries/{entry_id}/free-players/claim':
      '/api/v2/national-team-engine/entries/{entry_id}/free-players/claim',
  '/national-team-engine/entries/{entry_id}/rental-status':
      '/api/v2/national-team-engine/entries/{entry_id}/rental-status',
  '/national-team-engine/entries/{entry_id}/rentals':
      '/api/v2/national-team-engine/entries/{entry_id}/rentals',
  '/national-team-engine/me/history': '/api/v2/national-team-engine/me/history',
  '/national-team-engine/me/previous-roster':
      '/api/v2/national-team-engine/me/previous-roster',
  '/national-team-engine/rankings': '/api/v2/national-team-engine/rankings',
  '/news/breaking': '/api/v2/news/breaking',
  '/news/daily': '/api/v2/news/daily',
  '/news/feed': '/api/v2/news/feed',
  '/news/personalized': '/api/v2/news/personalized',
  '/news/{article_id}': '/api/v2/news/{article_id}',
  '/notifications': '/api/v2/notifications',
  '/notifications/announcements': '/api/v2/notifications/announcements',
  '/notifications/me': '/api/v2/notifications/me',
  '/notifications/preferences': '/api/v2/notifications/preferences',
  '/notifications/read-all': '/api/v2/notifications/read-all',
  '/notifications/subscriptions': '/api/v2/notifications/subscriptions',
  '/notifications/subscriptions/{subscription_id}':
      '/api/v2/notifications/subscriptions/{subscription_id}',
  '/notifications/{notification_id}/read':
      '/api/v2/notifications/{notification_id}/read',
  '/objectives/me': '/api/v2/objectives/me',
  '/observability/config': '/api/v2/observability/config',
  '/orchestrator/config': '/api/v2/orchestrator/config',
  '/orchestrator/metrics': '/api/v2/orchestrator/metrics',
  '/orders': '/api/v2/orders',
  '/orders/book/{player_id}': '/api/v2/orders/book/{player_id}',
  '/orders/{order_id}': '/api/v2/orders/{order_id}',
  '/orders/{order_id}/admin-buyback': '/api/v2/orders/{order_id}/admin-buyback',
  '/orders/{order_id}/admin-buyback-preview':
      '/api/v2/orders/{order_id}/admin-buyback-preview',
  '/orders/{order_id}/cancel': '/api/v2/orders/{order_id}/cancel',
  '/ownership-groups': '/api/v2/ownership-groups',
  '/ownership-groups/transfers/validate':
      '/api/v2/ownership-groups/transfers/validate',
  '/ownership-groups/{group_id}': '/api/v2/ownership-groups/{group_id}',
  '/ownership-groups/{group_id}/budget/allocate':
      '/api/v2/ownership-groups/{group_id}/budget/allocate',
  '/ownership-groups/{group_id}/budget/transfer':
      '/api/v2/ownership-groups/{group_id}/budget/transfer',
  '/ownership-groups/{group_id}/clubs':
      '/api/v2/ownership-groups/{group_id}/clubs',
  '/platform/mode': '/api/v2/platform/mode',
  '/platform/switch': '/api/v2/platform/switch',
  '/player-cards/admin/preseeded-regens':
      '/api/v2/player-cards/admin/preseeded-regens',
  '/player-cards/admin/preseeded-regens/mint':
      '/api/v2/player-cards/admin/preseeded-regens/mint',
  '/player-cards/inventory': '/api/v2/player-cards/inventory',
  '/player-cards/listings': '/api/v2/player-cards/listings',
  '/player-cards/listings/mine': '/api/v2/player-cards/listings/mine',
  '/player-cards/listings/{listing_id}/buy':
      '/api/v2/player-cards/listings/{listing_id}/buy',
  '/player-cards/listings/{listing_id}/cancel':
      '/api/v2/player-cards/listings/{listing_id}/cancel',
  '/player-cards/loans': '/api/v2/player-cards/loans',
  '/player-cards/loans/contracts/{loan_contract_id}/return':
      '/api/v2/player-cards/loans/contracts/{loan_contract_id}/return',
  '/player-cards/loans/{loan_listing_id}/borrow':
      '/api/v2/player-cards/loans/{loan_listing_id}/borrow',
  '/player-cards/marketplace/listings':
      '/api/v2/player-cards/marketplace/listings',
  '/player-cards/marketplace/loans': '/api/v2/player-cards/marketplace/loans',
  '/player-cards/marketplace/loans/contracts':
      '/api/v2/player-cards/marketplace/loans/contracts',
  '/player-cards/marketplace/loans/contracts/{contract_id}/return':
      '/api/v2/player-cards/marketplace/loans/contracts/{contract_id}/return',
  '/player-cards/marketplace/loans/contracts/{contract_id}/settle':
      '/api/v2/player-cards/marketplace/loans/contracts/{contract_id}/settle',
  '/player-cards/marketplace/loans/negotiations/{negotiation_id}/accept':
      '/api/v2/player-cards/marketplace/loans/negotiations/{negotiation_id}/accept',
  '/player-cards/marketplace/loans/negotiations/{negotiation_id}/counter':
      '/api/v2/player-cards/marketplace/loans/negotiations/{negotiation_id}/counter',
  '/player-cards/marketplace/loans/{listing_id}/cancel':
      '/api/v2/player-cards/marketplace/loans/{listing_id}/cancel',
  '/player-cards/marketplace/loans/{listing_id}/negotiations':
      '/api/v2/player-cards/marketplace/loans/{listing_id}/negotiations',
  '/player-cards/marketplace/sales': '/api/v2/player-cards/marketplace/sales',
  '/player-cards/marketplace/sales/{listing_id}/buy':
      '/api/v2/player-cards/marketplace/sales/{listing_id}/buy',
  '/player-cards/marketplace/sales/{listing_id}/cancel':
      '/api/v2/player-cards/marketplace/sales/{listing_id}/cancel',
  '/player-cards/marketplace/swaps': '/api/v2/player-cards/marketplace/swaps',
  '/player-cards/marketplace/swaps/{listing_id}/cancel':
      '/api/v2/player-cards/marketplace/swaps/{listing_id}/cancel',
  '/player-cards/marketplace/swaps/{listing_id}/execute':
      '/api/v2/player-cards/marketplace/swaps/{listing_id}/execute',
  '/player-cards/players': '/api/v2/player-cards/players',
  '/player-cards/players/{player_id}':
      '/api/v2/player-cards/players/{player_id}',
  '/player-cards/starter-rental': '/api/v2/player-cards/starter-rental',
  '/player-cards/watchlist': '/api/v2/player-cards/watchlist',
  '/player-cards/watchlist/{watchlist_id}':
      '/api/v2/player-cards/watchlist/{watchlist_id}',
  '/player-history': '/api/v2/player-history',
  '/player-history/{player_id}': '/api/v2/player-history/{player_id}',
  '/player-import/youth-prospects/me':
      '/api/v2/player-import/youth-prospects/me',
  '/player-import/youth-prospects/{club_id}':
      '/api/v2/player-import/youth-prospects/{club_id}',
  '/players': '/api/v2/players',
  '/players/events': '/api/v2/players/events',
  '/players/markets': '/api/v2/players/markets',
  '/players/match': '/api/v2/players/match',
  '/players/me/match-profile': '/api/v2/players/me/match-profile',
  '/players/me/shares/holdings': '/api/v2/players/me/shares/holdings',
  '/players/real-universe': '/api/v2/players/real-universe',
  '/players/real-universe/search': '/api/v2/players/real-universe/search',
  '/players/real-universe/{player_id}':
      '/api/v2/players/real-universe/{player_id}',
  '/players/summaries/recent': '/api/v2/players/summaries/recent',
  '/players/{player_id}': '/api/v2/players/{player_id}',
  '/players/{player_id}/avatar': '/api/v2/players/{player_id}/avatar',
  '/players/{player_id}/career-events':
      '/api/v2/players/{player_id}/career-events',
  '/players/{player_id}/dna': '/api/v2/players/{player_id}/dna',
  '/players/{player_id}/interviews': '/api/v2/players/{player_id}/interviews',
  '/players/{player_id}/personality': '/api/v2/players/{player_id}/personality',
  '/players/{player_id}/rivalries': '/api/v2/players/{player_id}/rivalries',
  '/players/{player_id}/shares/buy': '/api/v2/players/{player_id}/shares/buy',
  '/players/{player_id}/shares/dividends':
      '/api/v2/players/{player_id}/shares/dividends',
  '/players/{player_id}/shares/events':
      '/api/v2/players/{player_id}/shares/events',
  '/players/{player_id}/shares/issue':
      '/api/v2/players/{player_id}/shares/issue',
  '/players/{player_id}/shares/market':
      '/api/v2/players/{player_id}/shares/market',
  '/players/{player_id}/shares/performance':
      '/api/v2/players/{player_id}/shares/performance',
  '/players/{player_id}/shares/sell': '/api/v2/players/{player_id}/shares/sell',
  '/players/{player_id}/story': '/api/v2/players/{player_id}/story',
  '/players/{player_id}/summary': '/api/v2/players/{player_id}/summary',
  '/policies/acceptances': '/api/v2/policies/acceptances',
  '/policies/country/{country_code}': '/api/v2/policies/country/{country_code}',
  '/policies/documents': '/api/v2/policies/documents',
  '/policies/documents/{document_key}':
      '/api/v2/policies/documents/{document_key}',
  '/policies/me/acceptances': '/api/v2/policies/me/acceptances',
  '/policies/me/compliance': '/api/v2/policies/me/compliance',
  '/policies/me/region': '/api/v2/policies/me/region',
  '/policies/me/requirements': '/api/v2/policies/me/requirements',
  '/portfolio': '/api/v2/portfolio',
  '/portfolio/snapshot': '/api/v2/portfolio/snapshot',
  '/portfolio/summary': '/api/v2/portfolio/summary',
  '/portfolios/me': '/api/v2/portfolios/me',
  '/predictions': '/api/v2/predictions',
  '/predictions/leaderboard': '/api/v2/predictions/leaderboard',
  '/rankings/clubs': '/api/v2/rankings/clubs',
  '/rankings/global': '/api/v2/rankings/global',
  '/rankings/players': '/api/v2/rankings/players',
  '/ready': '/ready',
  '/real-world/events': '/api/v2/real-world/events',
  '/real-world/hybrid-players': '/api/v2/real-world/hybrid-players',
  '/real-world/normalize': '/api/v2/real-world/normalize',
  '/real-world/players': '/api/v2/real-world/players',
  '/real-world/players/{real_player_id}':
      '/api/v2/real-world/players/{real_player_id}',
  '/real-world/providers': '/api/v2/real-world/providers',
  '/real-world/settings/me': '/api/v2/real-world/settings/me',
  '/realtime/matches/{match_id}/gateway':
      '/api/v2/realtime/matches/{match_id}/gateway',
  '/realtime/matches/{match_id}/stream':
      '/api/v2/realtime/matches/{match_id}/stream',
  '/realtime/status': '/api/v2/realtime/status',
  '/realtime/stream': '/api/v2/realtime/stream',
  '/realtime/wallet/gateway': '/api/v2/realtime/wallet/gateway',
  '/realtime/wallet/stream': '/api/v2/realtime/wallet/stream',
  '/regen-hype': '/api/v2/regen-hype',
  '/regen-universe/achievements': '/api/v2/regen-universe/achievements',
  '/regen-universe/awards': '/api/v2/regen-universe/awards',
  '/regen-universe/bloodlines': '/api/v2/regen-universe/bloodlines',
  '/regen-universe/hall-of-fame': '/api/v2/regen-universe/hall-of-fame',
  '/regen-universe/national-regens': '/api/v2/regen-universe/national-regens',
  '/regen-universe/player/{player_id}':
      '/api/v2/regen-universe/player/{player_id}',
  '/regen-universe/players/{player_id}':
      '/api/v2/regen-universe/players/{player_id}',
  '/regen-universe/players/{player_id}/timeline':
      '/api/v2/regen-universe/players/{player_id}/timeline',
  '/regen-universe/rankings': '/api/v2/regen-universe/rankings',
  '/regen-universe/rising-stars': '/api/v2/regen-universe/rising-stars',
  '/regen-universe/scouting-feed': '/api/v2/regen-universe/scouting-feed',
  '/regen-universe/seasons': '/api/v2/regen-universe/seasons',
  '/regen-universe/tracking': '/api/v2/regen-universe/tracking',
  '/regen-universe/youth-tournaments':
      '/api/v2/regen-universe/youth-tournaments',
  '/regen-universe/youth-tournaments/{tournament_id}':
      '/api/v2/regen-universe/youth-tournaments/{tournament_id}',
  '/regens/awards': '/api/v2/regens/awards',
  '/regens/awards/{award_id}/vote': '/api/v2/regens/awards/{award_id}/vote',
  '/regens/creation-orders': '/api/v2/regens/creation-orders',
  '/regens/creation-orders/{order_id}':
      '/api/v2/regens/creation-orders/{order_id}',
  '/regens/creation-orders/{order_id}/generate-after-payment':
      '/api/v2/regens/creation-orders/{order_id}/generate-after-payment',
  '/regens/creation-orders/{order_id}/pay-with-wallet':
      '/api/v2/regens/creation-orders/{order_id}/pay-with-wallet',
  '/regens/feed': '/api/v2/regens/feed',
  '/regens/jobs/{job_name}': '/api/v2/regens/jobs/{job_name}',
  '/regens/request-son': '/api/v2/regens/request-son',
  '/regens/request-son/options': '/api/v2/regens/request-son/options',
  '/regens/rising': '/api/v2/regens/rising',
  '/regens/top': '/api/v2/regens/top',
  '/regens/{regen_id}/lineage': '/api/v2/regens/{regen_id}/lineage',
  '/rent': '/api/v2/rent',
  '/replays/countdown/{fixture_id}': '/api/v2/replays/countdown/{fixture_id}',
  '/replays/me': '/api/v2/replays/me',
  '/replays/public/featured': '/api/v2/replays/public/featured',
  '/replays/{replay_id}': '/api/v2/replays/{replay_id}',
  '/reward-engine/me/settlements': '/api/v2/reward-engine/me/settlements',
  '/reward-engine/me/summary': '/api/v2/reward-engine/me/summary',
  '/risk-ops/me/aml-cases': '/api/v2/risk-ops/me/aml-cases',
  '/risk-ops/me/fraud-cases': '/api/v2/risk-ops/me/fraud-cases',
  '/risk-ops/me/overview': '/api/v2/risk-ops/me/overview',
  '/risk-ops/me/restrictions': '/api/v2/risk-ops/me/restrictions',
  '/risk-ops/me/signals': '/api/v2/risk-ops/me/signals',
  '/scout/report/{player_id}': '/api/v2/scout/report/{player_id}',
  '/scouts': '/api/v2/scouts',
  '/scouts/{scout_id}/discover': '/api/v2/scouts/{scout_id}/discover',
  '/season-pass': '/api/v2/season-pass',
  '/season-pass/claim': '/api/v2/season-pass/claim',
  '/season-pass/me': '/api/v2/season-pass/me',
  '/season-pass/rewards/{reward_id}/claim':
      '/api/v2/season-pass/rewards/{reward_id}/claim',
  '/season/current': '/api/v2/season/current',
  '/season/history': '/api/v2/season/history',
  '/shows/debate': '/api/v2/shows/debate',
  '/shows/post-match/{match_id}': '/api/v2/shows/post-match/{match_id}',
  '/shows/pre-match/{match_id}': '/api/v2/shows/pre-match/{match_id}',
  '/simulation-matchmaking/hosted-competitions/preview':
      '/api/v2/simulation-matchmaking/hosted-competitions/preview',
  '/simulation-matchmaking/profiles/{user_id}':
      '/api/v2/simulation-matchmaking/profiles/{user_id}',
  '/simulation-matchmaking/quick-game':
      '/api/v2/simulation-matchmaking/quick-game',
  '/simulation-matchmaking/quick-tournament':
      '/api/v2/simulation-matchmaking/quick-tournament',
  '/social/clubs/{club_id}/community':
      '/api/v2/social/clubs/{club_id}/community',
  '/social/clubs/{club_id}/community/messages':
      '/api/v2/social/clubs/{club_id}/community/messages',
  '/social/feed': '/api/v2/social/feed',
  '/social/follows': '/api/v2/social/follows',
  '/social/profile/me': '/api/v2/social/profile/me',
  '/social/rivalries/{club_a_id}/{club_b_id}':
      '/api/v2/social/rivalries/{club_a_id}/{club_b_id}',
  '/social/rivalries/{club_a_id}/{club_b_id}/banter':
      '/api/v2/social/rivalries/{club_a_id}/{club_b_id}/banter',
  '/sponsors': '/api/v2/sponsors',
  '/sponsorship/clubs/{club_id}/contracts':
      '/api/v2/sponsorship/clubs/{club_id}/contracts',
  '/sponsorship/clubs/{club_id}/dashboard':
      '/api/v2/sponsorship/clubs/{club_id}/dashboard',
  '/sponsorship/clubs/{club_id}/offers':
      '/api/v2/sponsorship/clubs/{club_id}/offers',
  '/sponsorship/clubs/{club_id}/sponsors':
      '/api/v2/sponsorship/clubs/{club_id}/sponsors',
  '/sponsorship/contracts/request': '/api/v2/sponsorship/contracts/request',
  '/sponsorship/me/leads': '/api/v2/sponsorship/me/leads',
  '/sponsorship/packages': '/api/v2/sponsorship/packages',
  '/sponsorship/placements': '/api/v2/sponsorship/placements',
  '/story-feed': '/api/v2/story-feed',
  '/story-feed/digest': '/api/v2/story-feed/digest',
  '/streamer-tournaments': '/api/v2/streamer-tournaments',
  '/streamer-tournaments/mine': '/api/v2/streamer-tournaments/mine',
  '/streamer-tournaments/{tournament_id}':
      '/api/v2/streamer-tournaments/{tournament_id}',
  '/streamer-tournaments/{tournament_id}/invites':
      '/api/v2/streamer-tournaments/{tournament_id}/invites',
  '/streamer-tournaments/{tournament_id}/join':
      '/api/v2/streamer-tournaments/{tournament_id}/join',
  '/streamer-tournaments/{tournament_id}/publish':
      '/api/v2/streamer-tournaments/{tournament_id}/publish',
  '/streamer-tournaments/{tournament_id}/rewards':
      '/api/v2/streamer-tournaments/{tournament_id}/rewards',
  '/surveillance/circular-trade-alerts':
      '/api/v2/surveillance/circular-trade-alerts',
  '/surveillance/holder-concentration-alerts':
      '/api/v2/surveillance/holder-concentration-alerts',
  '/surveillance/suspicious-clusters':
      '/api/v2/surveillance/suspicious-clusters',
  '/surveillance/suspicious-players': '/api/v2/surveillance/suspicious-players',
  '/surveillance/thin-market-alerts': '/api/v2/surveillance/thin-market-alerts',
  '/sync/update': '/api/v2/sync/update',
  '/tickets/attendance/{match_id}/react':
      '/api/v2/tickets/attendance/{match_id}/react',
  '/tickets/buy': '/api/v2/tickets/buy',
  '/tickets/event/{match_id}': '/api/v2/tickets/event/{match_id}',
  '/tickets/resell': '/api/v2/tickets/resell',
  '/tickets/waitlist': '/api/v2/tickets/waitlist',
  '/trust/me': '/api/v2/trust/me',
  '/trust/{user_id}': '/api/v2/trust/{user_id}',
  '/ultimate-league/competitors/{competitor_id}':
      '/api/v2/ultimate-league/competitors/{competitor_id}',
  '/ultimate-league/matches/result': '/api/v2/ultimate-league/matches/result',
  '/ultimate-league/matchmaking/batch':
      '/api/v2/ultimate-league/matchmaking/batch',
  '/ultimate-league/standings/{tier}':
      '/api/v2/ultimate-league/standings/{tier}',
  '/ultimate-league/tactical-presets':
      '/api/v2/ultimate-league/tactical-presets',
  '/ultimate-league/tactical-presets/{preset_id}/purchase':
      '/api/v2/ultimate-league/tactical-presets/{preset_id}/purchase',
  '/ultimate-league/tiers': '/api/v2/ultimate-league/tiers',
  '/ultimate-league/tournaments': '/api/v2/ultimate-league/tournaments',
  '/ultimate-league/tournaments/{tournament_id}':
      '/api/v2/ultimate-league/tournaments/{tournament_id}',
  '/ultimate-league/tournaments/{tournament_id}/payouts/preview':
      '/api/v2/ultimate-league/tournaments/{tournament_id}/payouts/preview',
  '/users/me': '/api/v2/users/me',
  '/users/me/profile': '/api/v2/users/me/profile',
  '/users/suggestions': '/api/v2/users/suggestions',
  '/users/{user_id}/followers': '/api/v2/users/{user_id}/followers',
  '/users/{user_id}/following': '/api/v2/users/{user_id}/following',
  '/value-engine/snapshots/rebuild': '/api/v2/value-engine/snapshots/rebuild',
  '/value-engine/snapshots/{player_id}/daily-closes':
      '/api/v2/value-engine/snapshots/{player_id}/daily-closes',
  '/value-engine/snapshots/{player_id}/history':
      '/api/v2/value-engine/snapshots/{player_id}/history',
  '/value-engine/snapshots/{player_id}/latest':
      '/api/v2/value-engine/snapshots/{player_id}/latest',
  '/value-engine/snapshots/{player_id}/trend-summary':
      '/api/v2/value-engine/snapshots/{player_id}/trend-summary',
  '/version': '/version',
  '/viral/cascades': '/api/v2/viral/cascades',
  '/viral/clips/trending': '/api/v2/viral/clips/trending',
  '/wallet': '/api/v2/wallet',
  '/wallet/top-up/initiate': '/api/v2/wallet/top-up/initiate',
  '/wallet/top-up/verify': '/api/v2/wallet/top-up/verify',
  '/wallet/transactions': '/api/v2/wallet/transactions',
  '/wallets': '/api/v2/wallets',
  '/wallets/accounts': '/api/v2/wallets/accounts',
  '/wallets/adaptive-overview': '/api/v2/wallets/adaptive-overview',
  '/wallets/conversions': '/api/v2/wallets/conversions',
  '/wallets/conversions/quote': '/api/v2/wallets/conversions/quote',
  '/wallets/deposits': '/api/v2/wallets/deposits',
  '/wallets/deposits/{deposit_id}/submit':
      '/api/v2/wallets/deposits/{deposit_id}/submit',
  '/wallets/ledger': '/api/v2/wallets/ledger',
  '/wallets/market-topups': '/api/v2/wallets/market-topups',
  '/wallets/overview': '/api/v2/wallets/overview',
  '/wallets/payment-events': '/api/v2/wallets/payment-events',
  '/wallets/providers/{provider_key}/webhook':
      '/api/v2/wallets/providers/{provider_key}/webhook',
  '/wallets/purchase-orders': '/api/v2/wallets/purchase-orders',
  '/wallets/purchase-orders/quote': '/api/v2/wallets/purchase-orders/quote',
  '/wallets/purchase-orders/{order_id}':
      '/api/v2/wallets/purchase-orders/{order_id}',
  '/wallets/summary': '/api/v2/wallets/summary',
  '/wallets/top-up/initiate': '/api/v2/wallets/top-up/initiate',
  '/wallets/top-up/verify': '/api/v2/wallets/top-up/verify',
  '/wallets/transactions': '/api/v2/wallets/transactions',
  '/wallets/withdrawals': '/api/v2/wallets/withdrawals',
  '/wallets/withdrawals/eligibility': '/api/v2/wallets/withdrawals/eligibility',
  '/wallets/withdrawals/quote': '/api/v2/wallets/withdrawals/quote',
  '/wallets/withdrawals/{withdrawal_id}/receipt':
      '/api/v2/wallets/withdrawals/{withdrawal_id}/receipt',
  '/world-super-cup/countdown': '/api/v2/world-super-cup/countdown',
  '/world-super-cup/groups/table': '/api/v2/world-super-cup/groups/table',
  '/world-super-cup/knockout/bracket':
      '/api/v2/world-super-cup/knockout/bracket',
  '/world-super-cup/playoff/draw': '/api/v2/world-super-cup/playoff/draw',
  '/world-super-cup/qualification/explanation':
      '/api/v2/world-super-cup/qualification/explanation',
  '/ws/match/{match_id}': '/api/v2/ws/match/{match_id}',
  '/ws/spectate/{match_id}': '/api/v2/ws/spectate/{match_id}',
  '/ws/tournament/{tournament_id}': '/api/v2/ws/tournament/{tournament_id}',
};

const Map<String, String> gteApiDeprecatedAliases = <String, String>{
  '/academy': '/api/v2/academy',
  '/academy/awards': '/api/v2/academy/awards',
  '/academy/fixtures': '/api/v2/academy/fixtures',
  '/academy/generate': '/api/v2/academy/generate',
  '/academy/promote/{player_id}': '/api/v2/academy/promote/{player_id}',
  '/academy/qualification': '/api/v2/academy/qualification',
  '/academy/registration': '/api/v2/academy/registration',
  '/academy/season-summary': '/api/v2/academy/season-summary',
  '/academy/standings': '/api/v2/academy/standings',
  '/admin-engine/bootstrap': '/api/v2/admin-engine/bootstrap',
  '/admin/admin-engine/calendar-rules':
      '/api/v2/admin/admin-engine/calendar-rules',
  '/admin/admin-engine/feature-flags':
      '/api/v2/admin/admin-engine/feature-flags',
  '/admin/admin-engine/reward-rules': '/api/v2/admin/admin-engine/reward-rules',
  '/admin/admin-engine/schedule-preview':
      '/api/v2/admin/admin-engine/schedule-preview',
  '/admin/ban-user': '/api/v2/admin/ban-user',
  '/admin/broadcast-rights/jobs/run': '/api/v2/admin/broadcast-rights/jobs/run',
  '/admin/calendar-engine/events': '/api/v2/admin/calendar-engine/events',
  '/admin/calendar-engine/hosted-competitions/{competition_id}/launch':
      '/api/v2/admin/calendar-engine/hosted-competitions/{competition_id}/launch',
  '/admin/calendar-engine/national-competitions/{competition_id}/launch':
      '/api/v2/admin/calendar-engine/national-competitions/{competition_id}/launch',
  '/admin/calendar-engine/seasons': '/api/v2/admin/calendar-engine/seasons',
  '/admin/club-infra/seed': '/api/v2/admin/club-infra/seed',
  '/admin/config/liquidity-bands': '/api/v2/admin/config/liquidity-bands',
  '/admin/config/player-card-market-integrity':
      '/api/v2/admin/config/player-card-market-integrity',
  '/admin/config/supply-tiers': '/api/v2/admin/config/supply-tiers',
  '/admin/config/suspicion-thresholds':
      '/api/v2/admin/config/suspicion-thresholds',
  '/admin/config/value-controls': '/api/v2/admin/config/value-controls',
  '/admin/config/value-controls/audits':
      '/api/v2/admin/config/value-controls/audits',
  '/admin/config/value-controls/integrity/candidates':
      '/api/v2/admin/config/value-controls/integrity/candidates',
  '/admin/config/value-controls/players/{player_id}':
      '/api/v2/admin/config/value-controls/players/{player_id}',
  '/admin/config/value-controls/preview/{player_id}':
      '/api/v2/admin/config/value-controls/preview/{player_id}',
  '/admin/config/value-controls/recompute':
      '/api/v2/admin/config/value-controls/recompute',
  '/admin/config/value-controls/run-history':
      '/api/v2/admin/config/value-controls/run-history',
  '/admin/creator-campaigns/{campaign_id}/metrics':
      '/api/v2/admin/creator-campaigns/{campaign_id}/metrics',
  '/admin/creator/applications': '/api/v2/admin/creator/applications',
  '/admin/creator/applications/{application_id}/approve':
      '/api/v2/admin/creator/applications/{application_id}/approve',
  '/admin/creator/applications/{application_id}/reject':
      '/api/v2/admin/creator/applications/{application_id}/reject',
  '/admin/creator/applications/{application_id}/request-verification':
      '/api/v2/admin/creator/applications/{application_id}/request-verification',
  '/admin/creator/cards/assign': '/api/v2/admin/creator/cards/assign',
  '/admin/creator/dashboard': '/api/v2/admin/creator/dashboard',
  '/admin/creator/fan-share-market/control':
      '/api/v2/admin/creator/fan-share-market/control',
  '/admin/discovery/featured-rails': '/api/v2/admin/discovery/featured-rails',
  '/admin/disputes': '/api/v2/admin/disputes',
  '/admin/disputes/{dispute_id}/assign':
      '/api/v2/admin/disputes/{dispute_id}/assign',
  '/admin/disputes/{dispute_id}/status':
      '/api/v2/admin/disputes/{dispute_id}/status',
  '/admin/economy/burn-events': '/api/v2/admin/economy/burn-events',
  '/admin/economy/fx-rates': '/api/v2/admin/economy/fx-rates',
  '/admin/economy/gift-catalog': '/api/v2/admin/economy/gift-catalog',
  '/admin/economy/gift-combo-rules': '/api/v2/admin/economy/gift-combo-rules',
  '/admin/economy/governor': '/api/v2/admin/economy/governor',
  '/admin/economy/governor/apply': '/api/v2/admin/economy/governor/apply',
  '/admin/economy/governor/evaluate': '/api/v2/admin/economy/governor/evaluate',
  '/admin/economy/governor/policy': '/api/v2/admin/economy/governor/policy',
  '/admin/economy/regional-pricing': '/api/v2/admin/economy/regional-pricing',
  '/admin/economy/revenue-share-rules':
      '/api/v2/admin/economy/revenue-share-rules',
  '/admin/economy/service-pricing': '/api/v2/admin/economy/service-pricing',
  '/admin/fan-predictions/matches/{match_id}/fixture':
      '/api/v2/admin/fan-predictions/matches/{match_id}/fixture',
  '/admin/fan-predictions/matches/{match_id}/settlement':
      '/api/v2/admin/fan-predictions/matches/{match_id}/settlement',
  '/admin/fan-wars/creator-country-assignments':
      '/api/v2/admin/fan-wars/creator-country-assignments',
  '/admin/fan-wars/nations-cup': '/api/v2/admin/fan-wars/nations-cup',
  '/admin/fan-wars/nations-cup/{competition_id}/advance':
      '/api/v2/admin/fan-wars/nations-cup/{competition_id}/advance',
  '/admin/fan-wars/points': '/api/v2/admin/fan-wars/points',
  '/admin/fan-wars/profiles': '/api/v2/admin/fan-wars/profiles',
  '/admin/fan-wars/profiles/{profile_id}/rivals/{rival_profile_id}':
      '/api/v2/admin/fan-wars/profiles/{profile_id}/rivals/{rival_profile_id}',
  '/admin/federations/run-jobs': '/api/v2/admin/federations/run-jobs',
  '/admin/flags': '/api/v2/admin/flags',
  '/admin/football-events/categories':
      '/api/v2/admin/football-events/categories',
  '/admin/football-events/effects/expire':
      '/api/v2/admin/football-events/effects/expire',
  '/admin/football-events/events': '/api/v2/admin/football-events/events',
  '/admin/football-events/events/import':
      '/api/v2/admin/football-events/events/import',
  '/admin/football-events/events/{event_id}/review':
      '/api/v2/admin/football-events/events/{event_id}/review',
  '/admin/football-events/events/{event_id}/severity':
      '/api/v2/admin/football-events/events/{event_id}/severity',
  '/admin/football-events/rules': '/api/v2/admin/football-events/rules',
  '/admin/governance/proposals/{proposal_id}/status':
      '/api/v2/admin/governance/proposals/{proposal_id}/status',
  '/admin/history-engagement/run-workers':
      '/api/v2/admin/history-engagement/run-workers',
  '/admin/hosted-competitions': '/api/v2/admin/hosted-competitions',
  '/admin/hosted-competitions/seed': '/api/v2/admin/hosted-competitions/seed',
  '/admin/hosted-competitions/{competition_id}/finalize':
      '/api/v2/admin/hosted-competitions/{competition_id}/finalize',
  '/admin/hosted-competitions/{competition_id}/launch':
      '/api/v2/admin/hosted-competitions/{competition_id}/launch',
  '/admin/integrity-engine/incidents/{incident_id}/resolve':
      '/api/v2/admin/integrity-engine/incidents/{incident_id}/resolve',
  '/admin/integrity-engine/scan': '/api/v2/admin/integrity-engine/scan',
  '/admin/jackpot/balance': '/api/v2/admin/jackpot/balance',
  '/admin/jackpot/runtime': '/api/v2/admin/jackpot/runtime',
  '/admin/jackpot/trigger': '/api/v2/admin/jackpot/trigger',
  '/admin/leaderboard/season/archive':
      '/api/v2/admin/leaderboard/season/archive',
  '/admin/leaderboard/season/reset': '/api/v2/admin/leaderboard/season/reset',
  '/admin/media-engine/creator-league/clubs/{club_id}/stadium-level':
      '/api/v2/admin/media-engine/creator-league/clubs/{club_id}/stadium-level',
  '/admin/media-engine/creator-league/matches/{match_id}/analytics':
      '/api/v2/admin/media-engine/creator-league/matches/{match_id}/analytics',
  '/admin/media-engine/creator-league/matches/{match_id}/settlement':
      '/api/v2/admin/media-engine/creator-league/matches/{match_id}/settlement',
  '/admin/media-engine/creator-league/stadium-controls':
      '/api/v2/admin/media-engine/creator-league/stadium-controls',
  '/admin/media-engine/exports': '/api/v2/admin/media-engine/exports',
  '/admin/media-engine/highlights': '/api/v2/admin/media-engine/highlights',
  '/admin/media-engine/highlights/{storage_key:path}/archive':
      '/api/v2/admin/media-engine/highlights/{storage_key:path}/archive',
  '/admin/media-engine/share-exports/{export_id}/revenue-attributions':
      '/api/v2/admin/media-engine/share-exports/{export_id}/revenue-attributions',
  '/admin/media-engine/snapshots': '/api/v2/admin/media-engine/snapshots',
  '/admin/moderation/reports': '/api/v2/admin/moderation/reports',
  '/admin/moderation/reports/summary':
      '/api/v2/admin/moderation/reports/summary',
  '/admin/moderation/reports/{report_id}/assign':
      '/api/v2/admin/moderation/reports/{report_id}/assign',
  '/admin/moderation/reports/{report_id}/resolve':
      '/api/v2/admin/moderation/reports/{report_id}/resolve',
  '/admin/national-team-engine/competitions':
      '/api/v2/admin/national-team-engine/competitions',
  '/admin/national-team-engine/competitions/seed-defaults':
      '/api/v2/admin/national-team-engine/competitions/seed-defaults',
  '/admin/national-team-engine/competitions/{competition_id}/ads':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads',
  '/admin/national-team-engine/competitions/{competition_id}/ads/rotate':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads/rotate',
  '/admin/national-team-engine/competitions/{competition_id}/ads/{ad_id}':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads/{ad_id}',
  '/admin/national-team-engine/competitions/{competition_id}/entries':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/entries',
  '/admin/national-team-engine/competitions/{competition_id}/entries/lock':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/entries/lock',
  '/admin/national-team-engine/competitions/{competition_id}/lifecycle/advance':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/lifecycle/advance',
  '/admin/national-team-engine/competitions/{competition_id}/rentals/cleanup':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/rentals/cleanup',
  '/admin/national-team-engine/competitions/{competition_id}/story-events/generate':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/story-events/generate',
  '/admin/national-team-engine/competitions/{competition_id}/theme':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/theme',
  '/admin/national-team-engine/entries/{entry_id}/squad':
      '/api/v2/admin/national-team-engine/entries/{entry_id}/squad',
  '/admin/notifications/announcements':
      '/api/v2/admin/notifications/announcements',
  '/admin/ops/alerts': '/api/v2/admin/ops/alerts',
  '/admin/ops/audit': '/api/v2/admin/ops/audit',
  '/admin/ops/broadcast-expiration': '/api/v2/admin/ops/broadcast-expiration',
  '/admin/ops/broadcast-revenue': '/api/v2/admin/ops/broadcast-revenue',
  '/admin/ops/club-market-valuations':
      '/api/v2/admin/ops/club-market-valuations',
  '/admin/ops/dashboard': '/api/v2/admin/ops/dashboard',
  '/admin/ops/fan-updates': '/api/v2/admin/ops/fan-updates',
  '/admin/ops/identity-evolution': '/api/v2/admin/ops/identity-evolution',
  '/admin/ops/integrity-scan': '/api/v2/admin/ops/integrity-scan',
  '/admin/ops/media-generation': '/api/v2/admin/ops/media-generation',
  '/admin/ops/media-retention': '/api/v2/admin/ops/media-retention',
  '/admin/ops/national-team-rental-cleanup':
      '/api/v2/admin/ops/national-team-rental-cleanup',
  '/admin/ops/ownership-groups/reputation':
      '/api/v2/admin/ops/ownership-groups/reputation',
  '/admin/ops/platform-infra': '/api/v2/admin/ops/platform-infra',
  '/admin/ops/stadium-ad-rotation': '/api/v2/admin/ops/stadium-ad-rotation',
  '/admin/ops/tournament-storylines': '/api/v2/admin/ops/tournament-storylines',
  '/admin/ownership-groups/reputation-cycle':
      '/api/v2/admin/ownership-groups/reputation-cycle',
  '/admin/player-import/card-supply': '/api/v2/admin/player-import/card-supply',
  '/admin/player-import/card-supply/csv':
      '/api/v2/admin/player-import/card-supply/csv',
  '/admin/player-import/jobs': '/api/v2/admin/player-import/jobs',
  '/admin/player-import/jobs/{job_id}':
      '/api/v2/admin/player-import/jobs/{job_id}',
  '/admin/player-import/youth/generate':
      '/api/v2/admin/player-import/youth/generate',
  '/admin/policies/country-policies': '/api/v2/admin/policies/country-policies',
  '/admin/policies/documents': '/api/v2/admin/policies/documents',
  '/admin/policies/documents/versions':
      '/api/v2/admin/policies/documents/versions',
  '/admin/policies/regions/override': '/api/v2/admin/policies/regions/override',
  '/admin/real-world/providers': '/api/v2/admin/real-world/providers',
  '/admin/real-world/providers/{provider_id}/sync':
      '/api/v2/admin/real-world/providers/{provider_id}/sync',
  '/admin/regen-universe/jobs/dna-evolution':
      '/api/v2/admin/regen-universe/jobs/dna-evolution',
  '/admin/regen-universe/jobs/rivalry-detection':
      '/api/v2/admin/regen-universe/jobs/rivalry-detection',
  '/admin/regen-universe/jobs/story-regeneration':
      '/api/v2/admin/regen-universe/jobs/story-regeneration',
  '/admin/regen-universe/jobs/tournament-scheduling':
      '/api/v2/admin/regen-universe/jobs/tournament-scheduling',
  '/admin/regen-universe/national-regens/preseed':
      '/api/v2/admin/regen-universe/national-regens/preseed',
  '/admin/regen-universe/players/{player_id}/portrait/ban':
      '/api/v2/admin/regen-universe/players/{player_id}/portrait/ban',
  '/admin/regen-universe/players/{player_id}/portrait/override':
      '/api/v2/admin/regen-universe/players/{player_id}/portrait/override',
  '/admin/regen-universe/players/{player_id}/portrait/regenerate':
      '/api/v2/admin/regen-universe/players/{player_id}/portrait/regenerate',
  '/admin/regen-universe/seasons': '/api/v2/admin/regen-universe/seasons',
  '/admin/regen-universe/seasons/{season_id}/close':
      '/api/v2/admin/regen-universe/seasons/{season_id}/close',
  '/admin/regen-universe/seasons/{season_id}/evolution':
      '/api/v2/admin/regen-universe/seasons/{season_id}/evolution',
  '/admin/regen-universe/youth-tournaments':
      '/api/v2/admin/regen-universe/youth-tournaments',
  '/admin/reward-engine/promo-pool/credits':
      '/api/v2/admin/reward-engine/promo-pool/credits',
  '/admin/reward-engine/settlements': '/api/v2/admin/reward-engine/settlements',
  '/admin/risk-ops/actions': '/api/v2/admin/risk-ops/actions',
  '/admin/risk-ops/actions/{action_id}/release':
      '/api/v2/admin/risk-ops/actions/{action_id}/release',
  '/admin/risk-ops/aml-cases': '/api/v2/admin/risk-ops/aml-cases',
  '/admin/risk-ops/audit-logs': '/api/v2/admin/risk-ops/audit-logs',
  '/admin/risk-ops/cases/{case_type}/{case_id}/resolve':
      '/api/v2/admin/risk-ops/cases/{case_type}/{case_id}/resolve',
  '/admin/risk-ops/evaluate': '/api/v2/admin/risk-ops/evaluate',
  '/admin/risk-ops/fraud-cases': '/api/v2/admin/risk-ops/fraud-cases',
  '/admin/risk-ops/overview': '/api/v2/admin/risk-ops/overview',
  '/admin/risk-ops/scan': '/api/v2/admin/risk-ops/scan',
  '/admin/risk-ops/signals': '/api/v2/admin/risk-ops/signals',
  '/admin/risk-ops/system-events': '/api/v2/admin/risk-ops/system-events',
  '/admin/sponsorship/analytics': '/api/v2/admin/sponsorship/analytics',
  '/admin/sponsorship/categories/{category}':
      '/api/v2/admin/sponsorship/categories/{category}',
  '/admin/sponsorship/contracts/{contract_id}/review':
      '/api/v2/admin/sponsorship/contracts/{contract_id}/review',
  '/admin/sponsorship/contracts/{contract_id}/settle-next':
      '/api/v2/admin/sponsorship/contracts/{contract_id}/settle-next',
  '/admin/sponsorship/offers': '/api/v2/admin/sponsorship/offers',
  '/admin/sponsorship/offers/{offer_id}/assign':
      '/api/v2/admin/sponsorship/offers/{offer_id}/assign',
  '/admin/sponsorship/offers/{offer_id}/rule':
      '/api/v2/admin/sponsorship/offers/{offer_id}/rule',
  '/admin/sponsorship/packages': '/api/v2/admin/sponsorship/packages',
  '/admin/story-feed': '/api/v2/admin/story-feed',
  '/admin/streamer-tournaments/policy':
      '/api/v2/admin/streamer-tournaments/policy',
  '/admin/streamer-tournaments/risk-signals':
      '/api/v2/admin/streamer-tournaments/risk-signals',
  '/admin/streamer-tournaments/risk-signals/{signal_id}/review':
      '/api/v2/admin/streamer-tournaments/risk-signals/{signal_id}/review',
  '/admin/streamer-tournaments/{tournament_id}/review':
      '/api/v2/admin/streamer-tournaments/{tournament_id}/review',
  '/admin/streamer-tournaments/{tournament_id}/settle':
      '/api/v2/admin/streamer-tournaments/{tournament_id}/settle',
  '/admin/world/clubs/{club_id}/context':
      '/api/v2/admin/world/clubs/{club_id}/context',
  '/admin/world/cultures/{culture_key}':
      '/api/v2/admin/world/cultures/{culture_key}',
  '/admin/world/narratives/{narrative_slug}':
      '/api/v2/admin/world/narratives/{narrative_slug}',
  '/ads/create': '/api/v2/ads/create',
  '/ads/performance': '/api/v2/ads/performance',
  '/agents': '/api/v2/agents',
  '/agents/config': '/api/v2/agents/config',
  '/agents/performance': '/api/v2/agents/performance',
  '/agents/run': '/api/v2/agents/run',
  '/agents/summary': '/api/v2/agents/summary',
  '/ai-manager/autopilot/live-decision':
      '/api/v2/ai-manager/autopilot/live-decision',
  '/ai-manager/autopilot/run': '/api/v2/ai-manager/autopilot/run',
  '/ai-manager/economy/reward-preview':
      '/api/v2/ai-manager/economy/reward-preview',
  '/ai-manager/profiles/{club_id}': '/api/v2/ai-manager/profiles/{club_id}',
  '/ai-reporter/feed': '/api/v2/ai-reporter/feed',
  '/ai-reporter/run': '/api/v2/ai-reporter/run',
  '/ai/leagues': '/api/v2/ai/leagues',
  '/ai/match/{match_id}': '/api/v2/ai/match/{match_id}',
  '/analytics/clip/{clip_id}': '/api/v2/analytics/clip/{clip_id}',
  '/analytics/dashboard/drop-off': '/api/v2/analytics/dashboard/drop-off',
  '/analytics/dashboard/top-clips': '/api/v2/analytics/dashboard/top-clips',
  '/analytics/frontend': '/api/v2/analytics/frontend',
  '/api/academy': '/api/v2/academy',
  '/api/academy/awards': '/api/v2/academy/awards',
  '/api/academy/fixtures': '/api/v2/academy/fixtures',
  '/api/academy/generate': '/api/v2/academy/generate',
  '/api/academy/promote/{player_id}': '/api/v2/academy/promote/{player_id}',
  '/api/academy/qualification': '/api/v2/academy/qualification',
  '/api/academy/registration': '/api/v2/academy/registration',
  '/api/academy/season-summary': '/api/v2/academy/season-summary',
  '/api/academy/standings': '/api/v2/academy/standings',
  '/api/admin-engine/bootstrap': '/api/v2/admin-engine/bootstrap',
  '/api/admin/access': '/api/v2/admin/access',
  '/api/admin/access/permissions': '/api/v2/admin/access/permissions',
  '/api/admin/access/{user_id}/permissions':
      '/api/v2/admin/access/{user_id}/permissions',
  '/api/admin/admin-engine/calendar-rules':
      '/api/v2/admin/admin-engine/calendar-rules',
  '/api/admin/admin-engine/feature-flags':
      '/api/v2/admin/admin-engine/feature-flags',
  '/api/admin/admin-engine/reward-rules':
      '/api/v2/admin/admin-engine/reward-rules',
  '/api/admin/admin-engine/schedule-preview':
      '/api/v2/admin/admin-engine/schedule-preview',
  '/api/admin/analytics/agent-learning':
      '/api/v2/admin/analytics/agent-learning',
  '/api/admin/analytics/anomalies': '/api/v2/admin/analytics/anomalies',
  '/api/admin/analytics/funnels': '/api/v2/admin/analytics/funnels',
  '/api/admin/analytics/match-outcomes':
      '/api/v2/admin/analytics/match-outcomes',
  '/api/admin/analytics/player-matching':
      '/api/v2/admin/analytics/player-matching',
  '/api/admin/analytics/player-matching/recompute-weights':
      '/api/v2/admin/analytics/player-matching/recompute-weights',
  '/api/admin/analytics/price-predictions':
      '/api/v2/admin/analytics/price-predictions',
  '/api/admin/analytics/summary': '/api/v2/admin/analytics/summary',
  '/api/admin/analytics/user-segments': '/api/v2/admin/analytics/user-segments',
  '/api/admin/ban-user': '/api/v2/admin/ban-user',
  '/api/admin/broadcast-rights/jobs/run':
      '/api/v2/admin/broadcast-rights/jobs/run',
  '/api/admin/calendar-engine/events': '/api/v2/admin/calendar-engine/events',
  '/api/admin/calendar-engine/hosted-competitions/{competition_id}/launch':
      '/api/v2/admin/calendar-engine/hosted-competitions/{competition_id}/launch',
  '/api/admin/calendar-engine/national-competitions/{competition_id}/launch':
      '/api/v2/admin/calendar-engine/national-competitions/{competition_id}/launch',
  '/api/admin/calendar-engine/seasons': '/api/v2/admin/calendar-engine/seasons',
  '/api/admin/club-infra/seed': '/api/v2/admin/club-infra/seed',
  '/api/admin/clubs/academy-analytics': '/api/v2/admin/clubs/academy-analytics',
  '/api/admin/clubs/analytics': '/api/v2/admin/clubs/analytics',
  '/api/admin/clubs/finance-analytics': '/api/v2/admin/clubs/finance-analytics',
  '/api/admin/clubs/ops-summary': '/api/v2/admin/clubs/ops-summary',
  '/api/admin/clubs/scouting-analytics':
      '/api/v2/admin/clubs/scouting-analytics',
  '/api/admin/clubs/sponsorship-analytics':
      '/api/v2/admin/clubs/sponsorship-analytics',
  '/api/admin/clubs/summary': '/api/v2/admin/clubs/summary',
  '/api/admin/clubs/{club_id}': '/api/v2/admin/clubs/{club_id}',
  '/api/admin/clubs/{club_id}/moderate-branding':
      '/api/v2/admin/clubs/{club_id}/moderate-branding',
  '/api/admin/competitions': '/api/v2/admin/competitions',
  '/api/admin/competitions/reminders/dispatch':
      '/api/v2/admin/competitions/reminders/dispatch',
  '/api/admin/competitive-integrity/matches/{match_id}/validation':
      '/api/v2/admin/competitive-integrity/matches/{match_id}/validation',
  '/api/admin/competitive-integrity/workers/run-once':
      '/api/v2/admin/competitive-integrity/workers/run-once',
  '/api/admin/config/liquidity-bands': '/api/v2/admin/config/liquidity-bands',
  '/api/admin/config/player-card-market-integrity':
      '/api/v2/admin/config/player-card-market-integrity',
  '/api/admin/config/supply-tiers': '/api/v2/admin/config/supply-tiers',
  '/api/admin/config/suspicion-thresholds':
      '/api/v2/admin/config/suspicion-thresholds',
  '/api/admin/config/value-controls': '/api/v2/admin/config/value-controls',
  '/api/admin/config/value-controls/audits':
      '/api/v2/admin/config/value-controls/audits',
  '/api/admin/config/value-controls/integrity/candidates':
      '/api/v2/admin/config/value-controls/integrity/candidates',
  '/api/admin/config/value-controls/players/{player_id}':
      '/api/v2/admin/config/value-controls/players/{player_id}',
  '/api/admin/config/value-controls/preview/{player_id}':
      '/api/v2/admin/config/value-controls/preview/{player_id}',
  '/api/admin/config/value-controls/recompute':
      '/api/v2/admin/config/value-controls/recompute',
  '/api/admin/config/value-controls/run-history':
      '/api/v2/admin/config/value-controls/run-history',
  '/api/admin/creator-campaigns/{campaign_id}/metrics':
      '/api/v2/admin/creator-campaigns/{campaign_id}/metrics',
  '/api/admin/creator/applications': '/api/v2/admin/creator/applications',
  '/api/admin/creator/applications/{application_id}/approve':
      '/api/v2/admin/creator/applications/{application_id}/approve',
  '/api/admin/creator/applications/{application_id}/reject':
      '/api/v2/admin/creator/applications/{application_id}/reject',
  '/api/admin/creator/applications/{application_id}/request-verification':
      '/api/v2/admin/creator/applications/{application_id}/request-verification',
  '/api/admin/creator/cards/assign': '/api/v2/admin/creator/cards/assign',
  '/api/admin/creator/dashboard': '/api/v2/admin/creator/dashboard',
  '/api/admin/creator/fan-share-market/control':
      '/api/v2/admin/creator/fan-share-market/control',
  '/api/admin/discovery/featured-rails':
      '/api/v2/admin/discovery/featured-rails',
  '/api/admin/disputes': '/api/v2/admin/disputes',
  '/api/admin/disputes/{dispute_id}/assign':
      '/api/v2/admin/disputes/{dispute_id}/assign',
  '/api/admin/disputes/{dispute_id}/status':
      '/api/v2/admin/disputes/{dispute_id}/status',
  '/api/admin/economy/burn-events': '/api/v2/admin/economy/burn-events',
  '/api/admin/economy/fx-rates': '/api/v2/admin/economy/fx-rates',
  '/api/admin/economy/gift-catalog': '/api/v2/admin/economy/gift-catalog',
  '/api/admin/economy/gift-combo-rules':
      '/api/v2/admin/economy/gift-combo-rules',
  '/api/admin/economy/governor': '/api/v2/admin/economy/governor',
  '/api/admin/economy/governor/apply': '/api/v2/admin/economy/governor/apply',
  '/api/admin/economy/governor/evaluate':
      '/api/v2/admin/economy/governor/evaluate',
  '/api/admin/economy/governor/policy': '/api/v2/admin/economy/governor/policy',
  '/api/admin/economy/regional-pricing':
      '/api/v2/admin/economy/regional-pricing',
  '/api/admin/economy/revenue-share-rules':
      '/api/v2/admin/economy/revenue-share-rules',
  '/api/admin/economy/service-pricing': '/api/v2/admin/economy/service-pricing',
  '/api/admin/fan-predictions/matches/{match_id}/fixture':
      '/api/v2/admin/fan-predictions/matches/{match_id}/fixture',
  '/api/admin/fan-predictions/matches/{match_id}/settlement':
      '/api/v2/admin/fan-predictions/matches/{match_id}/settlement',
  '/api/admin/fan-wars/creator-country-assignments':
      '/api/v2/admin/fan-wars/creator-country-assignments',
  '/api/admin/fan-wars/nations-cup': '/api/v2/admin/fan-wars/nations-cup',
  '/api/admin/fan-wars/nations-cup/{competition_id}/advance':
      '/api/v2/admin/fan-wars/nations-cup/{competition_id}/advance',
  '/api/admin/fan-wars/points': '/api/v2/admin/fan-wars/points',
  '/api/admin/fan-wars/profiles': '/api/v2/admin/fan-wars/profiles',
  '/api/admin/fan-wars/profiles/{profile_id}/rivals/{rival_profile_id}':
      '/api/v2/admin/fan-wars/profiles/{profile_id}/rivals/{rival_profile_id}',
  '/api/admin/federations/run-jobs': '/api/v2/admin/federations/run-jobs',
  '/api/admin/finance/account-controls':
      '/api/v2/admin/finance/account-controls',
  '/api/admin/finance/account-controls/{user_id}':
      '/api/v2/admin/finance/account-controls/{user_id}',
  '/api/admin/finance/control-tower': '/api/v2/admin/finance/control-tower',
  '/api/admin/finance/manual-price-overrides':
      '/api/v2/admin/finance/manual-price-overrides',
  '/api/admin/finance/manual-price-overrides/{asset_type}/{asset_id}':
      '/api/v2/admin/finance/manual-price-overrides/{asset_type}/{asset_id}',
  '/api/admin/finance/match-kill-switches':
      '/api/v2/admin/finance/match-kill-switches',
  '/api/admin/finance/match-kill-switches/{match_id}':
      '/api/v2/admin/finance/match-kill-switches/{match_id}',
  '/api/admin/finance/reconciliation': '/api/v2/admin/finance/reconciliation',
  '/api/admin/finance/simulate': '/api/v2/admin/finance/simulate',
  '/api/admin/finance/wallet-protection':
      '/api/v2/admin/finance/wallet-protection',
  '/api/admin/flags': '/api/v2/admin/flags',
  '/api/admin/football-events/categories':
      '/api/v2/admin/football-events/categories',
  '/api/admin/football-events/effects/expire':
      '/api/v2/admin/football-events/effects/expire',
  '/api/admin/football-events/events': '/api/v2/admin/football-events/events',
  '/api/admin/football-events/events/import':
      '/api/v2/admin/football-events/events/import',
  '/api/admin/football-events/events/{event_id}/review':
      '/api/v2/admin/football-events/events/{event_id}/review',
  '/api/admin/football-events/events/{event_id}/severity':
      '/api/v2/admin/football-events/events/{event_id}/severity',
  '/api/admin/football-events/rules': '/api/v2/admin/football-events/rules',
  '/api/admin/god-mode/audit-events': '/api/v2/admin/god-mode/audit-events',
  '/api/admin/god-mode/bootstrap': '/api/v2/admin/god-mode/bootstrap',
  '/api/admin/god-mode/commissions': '/api/v2/admin/god-mode/commissions',
  '/api/admin/god-mode/competition-controls':
      '/api/v2/admin/god-mode/competition-controls',
  '/api/admin/god-mode/high-risk-actions':
      '/api/v2/admin/god-mode/high-risk-actions',
  '/api/admin/god-mode/liquidity/interventions':
      '/api/v2/admin/god-mode/liquidity/interventions',
  '/api/admin/god-mode/payment-rails': '/api/v2/admin/god-mode/payment-rails',
  '/api/admin/god-mode/payment-rails/health':
      '/api/v2/admin/god-mode/payment-rails/health',
  '/api/admin/god-mode/roles': '/api/v2/admin/god-mode/roles',
  '/api/admin/god-mode/treasury': '/api/v2/admin/god-mode/treasury',
  '/api/admin/god-mode/treasury/dashboard':
      '/api/v2/admin/god-mode/treasury/dashboard',
  '/api/admin/god-mode/treasury/withdrawals':
      '/api/v2/admin/god-mode/treasury/withdrawals',
  '/api/admin/god-mode/withdrawal-controls':
      '/api/v2/admin/god-mode/withdrawal-controls',
  '/api/admin/god-mode/withdrawals': '/api/v2/admin/god-mode/withdrawals',
  '/api/admin/god-mode/withdrawals/summary':
      '/api/v2/admin/god-mode/withdrawals/summary',
  '/api/admin/god-mode/withdrawals/{payout_request_id}':
      '/api/v2/admin/god-mode/withdrawals/{payout_request_id}',
  '/api/admin/governance/proposals/{proposal_id}/status':
      '/api/v2/admin/governance/proposals/{proposal_id}/status',
  '/api/admin/history-engagement/run-workers':
      '/api/v2/admin/history-engagement/run-workers',
  '/api/admin/hosted-competitions': '/api/v2/admin/hosted-competitions',
  '/api/admin/hosted-competitions/seed':
      '/api/v2/admin/hosted-competitions/seed',
  '/api/admin/hosted-competitions/{competition_id}/finalize':
      '/api/v2/admin/hosted-competitions/{competition_id}/finalize',
  '/api/admin/hosted-competitions/{competition_id}/launch':
      '/api/v2/admin/hosted-competitions/{competition_id}/launch',
  '/api/admin/integrity-engine/incidents/{incident_id}/resolve':
      '/api/v2/admin/integrity-engine/incidents/{incident_id}/resolve',
  '/api/admin/integrity-engine/scan': '/api/v2/admin/integrity-engine/scan',
  '/api/admin/jackpot/balance': '/api/v2/admin/jackpot/balance',
  '/api/admin/jackpot/runtime': '/api/v2/admin/jackpot/runtime',
  '/api/admin/jackpot/trigger': '/api/v2/admin/jackpot/trigger',
  '/api/admin/leaderboard/season/archive':
      '/api/v2/admin/leaderboard/season/archive',
  '/api/admin/leaderboard/season/reset':
      '/api/v2/admin/leaderboard/season/reset',
  '/api/admin/managers/audit-log': '/api/v2/admin/managers/audit-log',
  '/api/admin/managers/catalog/{manager_id}/supply':
      '/api/v2/admin/managers/catalog/{manager_id}/supply',
  '/api/admin/managers/competitions': '/api/v2/admin/managers/competitions',
  '/api/admin/managers/competitions/{code}':
      '/api/v2/admin/managers/competitions/{code}',
  '/api/admin/managers/competitions/{code}/orchestrate':
      '/api/v2/admin/managers/competitions/{code}/orchestrate',
  '/api/admin/media-engine/creator-league/clubs/{club_id}/stadium-level':
      '/api/v2/admin/media-engine/creator-league/clubs/{club_id}/stadium-level',
  '/api/admin/media-engine/creator-league/matches/{match_id}/analytics':
      '/api/v2/admin/media-engine/creator-league/matches/{match_id}/analytics',
  '/api/admin/media-engine/creator-league/matches/{match_id}/settlement':
      '/api/v2/admin/media-engine/creator-league/matches/{match_id}/settlement',
  '/api/admin/media-engine/creator-league/stadium-controls':
      '/api/v2/admin/media-engine/creator-league/stadium-controls',
  '/api/admin/media-engine/exports': '/api/v2/admin/media-engine/exports',
  '/api/admin/media-engine/highlights': '/api/v2/admin/media-engine/highlights',
  '/api/admin/media-engine/highlights/{storage_key:path}/archive':
      '/api/v2/admin/media-engine/highlights/{storage_key:path}/archive',
  '/api/admin/media-engine/share-exports/{export_id}/revenue-attributions':
      '/api/v2/admin/media-engine/share-exports/{export_id}/revenue-attributions',
  '/api/admin/media-engine/snapshots': '/api/v2/admin/media-engine/snapshots',
  '/api/admin/moderation/reports': '/api/v2/admin/moderation/reports',
  '/api/admin/moderation/reports/summary':
      '/api/v2/admin/moderation/reports/summary',
  '/api/admin/moderation/reports/{report_id}/assign':
      '/api/v2/admin/moderation/reports/{report_id}/assign',
  '/api/admin/moderation/reports/{report_id}/resolve':
      '/api/v2/admin/moderation/reports/{report_id}/resolve',
  '/api/admin/national-team-engine/competitions':
      '/api/v2/admin/national-team-engine/competitions',
  '/api/admin/national-team-engine/competitions/seed-defaults':
      '/api/v2/admin/national-team-engine/competitions/seed-defaults',
  '/api/admin/national-team-engine/competitions/{competition_id}/ads':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads',
  '/api/admin/national-team-engine/competitions/{competition_id}/ads/rotate':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads/rotate',
  '/api/admin/national-team-engine/competitions/{competition_id}/ads/{ad_id}':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads/{ad_id}',
  '/api/admin/national-team-engine/competitions/{competition_id}/entries':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/entries',
  '/api/admin/national-team-engine/competitions/{competition_id}/entries/lock':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/entries/lock',
  '/api/admin/national-team-engine/competitions/{competition_id}/lifecycle/advance':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/lifecycle/advance',
  '/api/admin/national-team-engine/competitions/{competition_id}/rentals/cleanup':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/rentals/cleanup',
  '/api/admin/national-team-engine/competitions/{competition_id}/story-events/generate':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/story-events/generate',
  '/api/admin/national-team-engine/competitions/{competition_id}/theme':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/theme',
  '/api/admin/national-team-engine/entries/{entry_id}/squad':
      '/api/v2/admin/national-team-engine/entries/{entry_id}/squad',
  '/api/admin/notifications/announcements':
      '/api/v2/admin/notifications/announcements',
  '/api/admin/ops/alerts': '/api/v2/admin/ops/alerts',
  '/api/admin/ops/audit': '/api/v2/admin/ops/audit',
  '/api/admin/ops/broadcast-expiration':
      '/api/v2/admin/ops/broadcast-expiration',
  '/api/admin/ops/broadcast-revenue': '/api/v2/admin/ops/broadcast-revenue',
  '/api/admin/ops/club-market-valuations':
      '/api/v2/admin/ops/club-market-valuations',
  '/api/admin/ops/dashboard': '/api/v2/admin/ops/dashboard',
  '/api/admin/ops/fan-updates': '/api/v2/admin/ops/fan-updates',
  '/api/admin/ops/identity-evolution': '/api/v2/admin/ops/identity-evolution',
  '/api/admin/ops/integrity-scan': '/api/v2/admin/ops/integrity-scan',
  '/api/admin/ops/media-generation': '/api/v2/admin/ops/media-generation',
  '/api/admin/ops/media-retention': '/api/v2/admin/ops/media-retention',
  '/api/admin/ops/national-team-rental-cleanup':
      '/api/v2/admin/ops/national-team-rental-cleanup',
  '/api/admin/ops/ownership-groups/reputation':
      '/api/v2/admin/ops/ownership-groups/reputation',
  '/api/admin/ops/platform-infra': '/api/v2/admin/ops/platform-infra',
  '/api/admin/ops/stadium-ad-rotation': '/api/v2/admin/ops/stadium-ad-rotation',
  '/api/admin/ops/tournament-storylines':
      '/api/v2/admin/ops/tournament-storylines',
  '/api/admin/ownership-groups/reputation-cycle':
      '/api/v2/admin/ownership-groups/reputation-cycle',
  '/api/admin/player-import/card-supply':
      '/api/v2/admin/player-import/card-supply',
  '/api/admin/player-import/card-supply/csv':
      '/api/v2/admin/player-import/card-supply/csv',
  '/api/admin/player-import/jobs': '/api/v2/admin/player-import/jobs',
  '/api/admin/player-import/jobs/{job_id}':
      '/api/v2/admin/player-import/jobs/{job_id}',
  '/api/admin/player-import/youth/generate':
      '/api/v2/admin/player-import/youth/generate',
  '/api/admin/policies/country-policies':
      '/api/v2/admin/policies/country-policies',
  '/api/admin/policies/documents': '/api/v2/admin/policies/documents',
  '/api/admin/policies/documents/versions':
      '/api/v2/admin/policies/documents/versions',
  '/api/admin/policies/regions/override':
      '/api/v2/admin/policies/regions/override',
  '/api/admin/real-world/providers': '/api/v2/admin/real-world/providers',
  '/api/admin/real-world/providers/{provider_id}/sync':
      '/api/v2/admin/real-world/providers/{provider_id}/sync',
  '/api/admin/referrals/analytics/summary':
      '/api/v2/admin/referrals/analytics/summary',
  '/api/admin/referrals/attributions': '/api/v2/admin/referrals/attributions',
  '/api/admin/referrals/creators': '/api/v2/admin/referrals/creators',
  '/api/admin/referrals/creators/{creator_id}':
      '/api/v2/admin/referrals/creators/{creator_id}',
  '/api/admin/referrals/creators/{creator_id}/reward-freeze':
      '/api/v2/admin/referrals/creators/{creator_id}/reward-freeze',
  '/api/admin/referrals/dashboard': '/api/v2/admin/referrals/dashboard',
  '/api/admin/referrals/flags': '/api/v2/admin/referrals/flags',
  '/api/admin/referrals/leaderboard': '/api/v2/admin/referrals/leaderboard',
  '/api/admin/referrals/rewards/pending':
      '/api/v2/admin/referrals/rewards/pending',
  '/api/admin/referrals/rewards/{reward_id}/review':
      '/api/v2/admin/referrals/rewards/{reward_id}/review',
  '/api/admin/referrals/share-codes': '/api/v2/admin/referrals/share-codes',
  '/api/admin/referrals/share-codes/{share_code_id}':
      '/api/v2/admin/referrals/share-codes/{share_code_id}',
  '/api/admin/referrals/share-codes/{share_code_id}/block':
      '/api/v2/admin/referrals/share-codes/{share_code_id}/block',
  '/api/admin/regen-universe/jobs/dna-evolution':
      '/api/v2/admin/regen-universe/jobs/dna-evolution',
  '/api/admin/regen-universe/jobs/rivalry-detection':
      '/api/v2/admin/regen-universe/jobs/rivalry-detection',
  '/api/admin/regen-universe/jobs/story-regeneration':
      '/api/v2/admin/regen-universe/jobs/story-regeneration',
  '/api/admin/regen-universe/jobs/tournament-scheduling':
      '/api/v2/admin/regen-universe/jobs/tournament-scheduling',
  '/api/admin/regen-universe/national-regens/preseed':
      '/api/v2/admin/regen-universe/national-regens/preseed',
  '/api/admin/regen-universe/players/{player_id}/portrait/ban':
      '/api/v2/admin/regen-universe/players/{player_id}/portrait/ban',
  '/api/admin/regen-universe/players/{player_id}/portrait/override':
      '/api/v2/admin/regen-universe/players/{player_id}/portrait/override',
  '/api/admin/regen-universe/players/{player_id}/portrait/regenerate':
      '/api/v2/admin/regen-universe/players/{player_id}/portrait/regenerate',
  '/api/admin/regen-universe/seasons': '/api/v2/admin/regen-universe/seasons',
  '/api/admin/regen-universe/seasons/{season_id}/close':
      '/api/v2/admin/regen-universe/seasons/{season_id}/close',
  '/api/admin/regen-universe/seasons/{season_id}/evolution':
      '/api/v2/admin/regen-universe/seasons/{season_id}/evolution',
  '/api/admin/regen-universe/youth-tournaments':
      '/api/v2/admin/regen-universe/youth-tournaments',
  '/api/admin/reward-engine/promo-pool/credits':
      '/api/v2/admin/reward-engine/promo-pool/credits',
  '/api/admin/reward-engine/settlements':
      '/api/v2/admin/reward-engine/settlements',
  '/api/admin/risk-ops/actions': '/api/v2/admin/risk-ops/actions',
  '/api/admin/risk-ops/actions/{action_id}/release':
      '/api/v2/admin/risk-ops/actions/{action_id}/release',
  '/api/admin/risk-ops/aml-cases': '/api/v2/admin/risk-ops/aml-cases',
  '/api/admin/risk-ops/audit-logs': '/api/v2/admin/risk-ops/audit-logs',
  '/api/admin/risk-ops/cases/{case_type}/{case_id}/resolve':
      '/api/v2/admin/risk-ops/cases/{case_type}/{case_id}/resolve',
  '/api/admin/risk-ops/evaluate': '/api/v2/admin/risk-ops/evaluate',
  '/api/admin/risk-ops/fraud-cases': '/api/v2/admin/risk-ops/fraud-cases',
  '/api/admin/risk-ops/overview': '/api/v2/admin/risk-ops/overview',
  '/api/admin/risk-ops/scan': '/api/v2/admin/risk-ops/scan',
  '/api/admin/risk-ops/signals': '/api/v2/admin/risk-ops/signals',
  '/api/admin/risk-ops/system-events': '/api/v2/admin/risk-ops/system-events',
  '/api/admin/sponsorship/analytics': '/api/v2/admin/sponsorship/analytics',
  '/api/admin/sponsorship/categories/{category}':
      '/api/v2/admin/sponsorship/categories/{category}',
  '/api/admin/sponsorship/contracts/{contract_id}/review':
      '/api/v2/admin/sponsorship/contracts/{contract_id}/review',
  '/api/admin/sponsorship/contracts/{contract_id}/settle-next':
      '/api/v2/admin/sponsorship/contracts/{contract_id}/settle-next',
  '/api/admin/sponsorship/offers': '/api/v2/admin/sponsorship/offers',
  '/api/admin/sponsorship/offers/{offer_id}/assign':
      '/api/v2/admin/sponsorship/offers/{offer_id}/assign',
  '/api/admin/sponsorship/offers/{offer_id}/rule':
      '/api/v2/admin/sponsorship/offers/{offer_id}/rule',
  '/api/admin/sponsorship/packages': '/api/v2/admin/sponsorship/packages',
  '/api/admin/story-feed': '/api/v2/admin/story-feed',
  '/api/admin/streamer-tournaments/policy':
      '/api/v2/admin/streamer-tournaments/policy',
  '/api/admin/streamer-tournaments/risk-signals':
      '/api/v2/admin/streamer-tournaments/risk-signals',
  '/api/admin/streamer-tournaments/risk-signals/{signal_id}/review':
      '/api/v2/admin/streamer-tournaments/risk-signals/{signal_id}/review',
  '/api/admin/streamer-tournaments/{tournament_id}/review':
      '/api/v2/admin/streamer-tournaments/{tournament_id}/review',
  '/api/admin/streamer-tournaments/{tournament_id}/settle':
      '/api/v2/admin/streamer-tournaments/{tournament_id}/settle',
  '/api/admin/treasury/bank-accounts': '/api/v2/admin/treasury/bank-accounts',
  '/api/admin/treasury/bank-accounts/{account_id}':
      '/api/v2/admin/treasury/bank-accounts/{account_id}',
  '/api/admin/treasury/dashboard': '/api/v2/admin/treasury/dashboard',
  '/api/admin/treasury/deposits': '/api/v2/admin/treasury/deposits',
  '/api/admin/treasury/deposits/{deposit_id}/confirm':
      '/api/v2/admin/treasury/deposits/{deposit_id}/confirm',
  '/api/admin/treasury/deposits/{deposit_id}/reject':
      '/api/v2/admin/treasury/deposits/{deposit_id}/reject',
  '/api/admin/treasury/deposits/{deposit_id}/review':
      '/api/v2/admin/treasury/deposits/{deposit_id}/review',
  '/api/admin/treasury/disputes': '/api/v2/admin/treasury/disputes',
  '/api/admin/treasury/disputes/{dispute_id}':
      '/api/v2/admin/treasury/disputes/{dispute_id}',
  '/api/admin/treasury/disputes/{dispute_id}/messages':
      '/api/v2/admin/treasury/disputes/{dispute_id}/messages',
  '/api/admin/treasury/kyc': '/api/v2/admin/treasury/kyc',
  '/api/admin/treasury/kyc/{profile_id}/review':
      '/api/v2/admin/treasury/kyc/{profile_id}/review',
  '/api/admin/treasury/settings': '/api/v2/admin/treasury/settings',
  '/api/admin/treasury/withdrawal-batches':
      '/api/v2/admin/treasury/withdrawal-batches',
  '/api/admin/treasury/withdrawals': '/api/v2/admin/treasury/withdrawals',
  '/api/admin/treasury/withdrawals/{withdrawal_id}/reviews':
      '/api/v2/admin/treasury/withdrawals/{withdrawal_id}/reviews',
  '/api/admin/treasury/withdrawals/{withdrawal_id}/status':
      '/api/v2/admin/treasury/withdrawals/{withdrawal_id}/status',
  '/api/admin/wallets/market-topups': '/api/v2/admin/wallets/market-topups',
  '/api/admin/wallets/market-topups/quote':
      '/api/v2/admin/wallets/market-topups/quote',
  '/api/admin/wallets/market-topups/{topup_id}/status':
      '/api/v2/admin/wallets/market-topups/{topup_id}/status',
  '/api/admin/wallets/purchase-orders': '/api/v2/admin/wallets/purchase-orders',
  '/api/admin/wallets/purchase-orders/{order_id}/status':
      '/api/v2/admin/wallets/purchase-orders/{order_id}/status',
  '/api/admin/world/clubs/{club_id}/context':
      '/api/v2/admin/world/clubs/{club_id}/context',
  '/api/admin/world/cultures/{culture_key}':
      '/api/v2/admin/world/cultures/{culture_key}',
  '/api/admin/world/narratives/{narrative_slug}':
      '/api/v2/admin/world/narratives/{narrative_slug}',
  '/api/ads/create': '/api/v2/ads/create',
  '/api/ads/performance': '/api/v2/ads/performance',
  '/api/agents': '/api/v2/agents',
  '/api/agents/config': '/api/v2/agents/config',
  '/api/agents/performance': '/api/v2/agents/performance',
  '/api/agents/run': '/api/v2/agents/run',
  '/api/agents/summary': '/api/v2/agents/summary',
  '/api/ai-manager/autopilot/live-decision':
      '/api/v2/ai-manager/autopilot/live-decision',
  '/api/ai-manager/autopilot/run': '/api/v2/ai-manager/autopilot/run',
  '/api/ai-manager/economy/reward-preview':
      '/api/v2/ai-manager/economy/reward-preview',
  '/api/ai-manager/profiles/{club_id}': '/api/v2/ai-manager/profiles/{club_id}',
  '/api/ai-reporter/feed': '/api/v2/ai-reporter/feed',
  '/api/ai-reporter/run': '/api/v2/ai-reporter/run',
  '/api/ai/leagues': '/api/v2/ai/leagues',
  '/api/ai/match/{match_id}': '/api/v2/ai/match/{match_id}',
  '/api/analytics/clip/{clip_id}': '/api/v2/analytics/clip/{clip_id}',
  '/api/analytics/dashboard/drop-off': '/api/v2/analytics/dashboard/drop-off',
  '/api/analytics/dashboard/top-clips': '/api/v2/analytics/dashboard/top-clips',
  '/api/analytics/device-fingerprint': '/api/v2/analytics/device-fingerprint',
  '/api/analytics/events': '/api/v2/analytics/events',
  '/api/analytics/frontend': '/api/v2/analytics/frontend',
  '/api/analytics/influencer-leaderboard':
      '/api/v2/analytics/influencer-leaderboard',
  '/api/attachments': '/api/v2/attachments',
  '/api/attachments/{attachment_id}': '/api/v2/attachments/{attachment_id}',
  '/api/auth/change-password': '/api/v2/auth/change-password',
  '/api/auth/confirm-email': '/api/v2/auth/confirm-email',
  '/api/auth/login': '/api/v2/auth/login',
  '/api/auth/logout': '/api/v2/auth/logout',
  '/api/auth/me': '/api/v2/auth/me',
  '/api/auth/recovery/request': '/api/v2/auth/recovery/request',
  '/api/auth/recovery/reset': '/api/v2/auth/recovery/reset',
  '/api/auth/refresh': '/api/v2/auth/refresh',
  '/api/auth/signup/creator': '/api/v2/auth/signup/creator',
  '/api/auth/signup/trader': '/api/v2/auth/signup/trader',
  '/api/auth/signup/user': '/api/v2/auth/signup/user',
  '/api/awards/categories': '/api/v2/awards/categories',
  '/api/awards/ceremony': '/api/v2/awards/ceremony',
  '/api/awards/ceremony/tickets': '/api/v2/awards/ceremony/tickets',
  '/api/awards/ceremony/vote': '/api/v2/awards/ceremony/vote',
  '/api/awards/nominees': '/api/v2/awards/nominees',
  '/api/awards/winners': '/api/v2/awards/winners',
  '/api/bank-accounts': '/api/v2/bank-accounts',
  '/api/bank-accounts/{bank_account_id}':
      '/api/v2/bank-accounts/{bank_account_id}',
  '/api/bets/history': '/api/v2/bets/history',
  '/api/bets/odds/{match_id}': '/api/v2/bets/odds/{match_id}',
  '/api/bets/place': '/api/v2/bets/place',
  '/api/bets/preferences': '/api/v2/bets/preferences',
  '/api/broadcast-rights/auctions/{auction_id}/bids':
      '/api/v2/broadcast-rights/auctions/{auction_id}/bids',
  '/api/broadcast-rights/competitions/{competition_id}':
      '/api/v2/broadcast-rights/competitions/{competition_id}',
  '/api/broadcast-rights/competitions/{competition_id}/acquire':
      '/api/v2/broadcast-rights/competitions/{competition_id}/acquire',
  '/api/broadcast-rights/competitions/{competition_id}/auctions':
      '/api/v2/broadcast-rights/competitions/{competition_id}/auctions',
  '/api/broadcast-rights/matches/{match_id}/access':
      '/api/v2/broadcast-rights/matches/{match_id}/access',
  '/api/broadcast-rights/matches/{match_id}/distribute':
      '/api/v2/broadcast-rights/matches/{match_id}/distribute',
  '/api/broadcast-rights/{right_id}/grants':
      '/api/v2/broadcast-rights/{right_id}/grants',
  '/api/broadcast/channels': '/api/v2/broadcast/channels',
  '/api/broadcast/channels/{channel_id}/audio/stems/stream':
      '/api/v2/broadcast/channels/{channel_id}/audio/stems/stream',
  '/api/broadcast/channels/{channel_id}/join':
      '/api/v2/broadcast/channels/{channel_id}/join',
  '/api/broadcast/channels/{channel_id}/stream':
      '/api/v2/broadcast/channels/{channel_id}/stream',
  '/api/broadcast/home': '/api/v2/broadcast/home',
  '/api/broadcast/{match_id}': '/api/v2/broadcast/{match_id}',
  '/api/calendar-engine/dashboard': '/api/v2/calendar-engine/dashboard',
  '/api/calendar-engine/events': '/api/v2/calendar-engine/events',
  '/api/calendar-engine/lifecycle-runs':
      '/api/v2/calendar-engine/lifecycle-runs',
  '/api/calendar-engine/pause-status': '/api/v2/calendar-engine/pause-status',
  '/api/calendar-engine/seasons': '/api/v2/calendar-engine/seasons',
  '/api/campaigns': '/api/v2/campaigns',
  '/api/campaigns/create': '/api/v2/campaigns/create',
  '/api/campaigns/{id}/accept': '/api/v2/campaigns/{id}/accept',
  '/api/campaigns/{id}/apply': '/api/v2/campaigns/{id}/apply',
  '/api/campaigns/{id}/performance': '/api/v2/campaigns/{id}/performance',
  '/api/career/create': '/api/v2/career/create',
  '/api/career/retire': '/api/v2/career/retire',
  '/api/career/train': '/api/v2/career/train',
  '/api/career/transfer': '/api/v2/career/transfer',
  '/api/career/{user_id}': '/api/v2/career/{user_id}',
  '/api/challenges/links/{link_code}': '/api/v2/challenges/links/{link_code}',
  '/api/challenges/{challenge_id}': '/api/v2/challenges/{challenge_id}',
  '/api/challenges/{challenge_id}/accept':
      '/api/v2/challenges/{challenge_id}/accept',
  '/api/challenges/{challenge_id}/links':
      '/api/v2/challenges/{challenge_id}/links',
  '/api/challenges/{challenge_id}/publish':
      '/api/v2/challenges/{challenge_id}/publish',
  '/api/challenges/{challenge_id}/share-events':
      '/api/v2/challenges/{challenge_id}/share-events',
  '/api/champions-league/knockout-bracket':
      '/api/v2/champions-league/knockout-bracket',
  '/api/champions-league/league-phase/table':
      '/api/v2/champions-league/league-phase/table',
  '/api/champions-league/playoff-bracket':
      '/api/v2/champions-league/playoff-bracket',
  '/api/champions-league/prize-pool/preview':
      '/api/v2/champions-league/prize-pool/preview',
  '/api/champions-league/qualification-map':
      '/api/v2/champions-league/qualification-map',
  '/api/club-infra/clubs/{club_id}': '/api/v2/club-infra/clubs/{club_id}',
  '/api/club-infra/clubs/{club_id}/support':
      '/api/v2/club-infra/clubs/{club_id}/support',
  '/api/club-infra/my': '/api/v2/club-infra/my',
  '/api/club-infra/my/facilities/upgrade':
      '/api/v2/club-infra/my/facilities/upgrade',
  '/api/club-infra/my/stadium/upgrade': '/api/v2/club-infra/my/stadium/upgrade',
  '/api/club/identity': '/api/v2/club/identity',
  '/api/clubs': '/api/v2/clubs',
  '/api/clubs/catalog': '/api/v2/clubs/catalog',
  '/api/clubs/catalog/purchase': '/api/v2/clubs/catalog/purchase',
  '/api/clubs/marketplace': '/api/v2/clubs/marketplace',
  '/api/clubs/sale-market/listings': '/api/v2/clubs/sale-market/listings',
  '/api/clubs/{club_id}': '/api/v2/clubs/{club_id}',
  '/api/clubs/{club_id}/academy': '/api/v2/clubs/{club_id}/academy',
  '/api/clubs/{club_id}/academy/players':
      '/api/v2/clubs/{club_id}/academy/players',
  '/api/clubs/{club_id}/academy/players/{player_id}':
      '/api/v2/clubs/{club_id}/academy/players/{player_id}',
  '/api/clubs/{club_id}/academy/programs':
      '/api/v2/clubs/{club_id}/academy/programs',
  '/api/clubs/{club_id}/academy/training-cycles':
      '/api/v2/clubs/{club_id}/academy/training-cycles',
  '/api/clubs/{club_id}/badge': '/api/v2/clubs/{club_id}/badge',
  '/api/clubs/{club_id}/branding': '/api/v2/clubs/{club_id}/branding',
  '/api/clubs/{club_id}/buy-tokens': '/api/v2/clubs/{club_id}/buy-tokens',
  '/api/clubs/{club_id}/challenges': '/api/v2/clubs/{club_id}/challenges',
  '/api/clubs/{club_id}/contracts': '/api/v2/clubs/{club_id}/contracts',
  '/api/clubs/{club_id}/dynasty': '/api/v2/clubs/{club_id}/dynasty',
  '/api/clubs/{club_id}/dynasty/history':
      '/api/v2/clubs/{club_id}/dynasty/history',
  '/api/clubs/{club_id}/eras': '/api/v2/clubs/{club_id}/eras',
  '/api/clubs/{club_id}/finances': '/api/v2/clubs/{club_id}/finances',
  '/api/clubs/{club_id}/finances/budget':
      '/api/v2/clubs/{club_id}/finances/budget',
  '/api/clubs/{club_id}/finances/cashflow':
      '/api/v2/clubs/{club_id}/finances/cashflow',
  '/api/clubs/{club_id}/finances/ledger':
      '/api/v2/clubs/{club_id}/finances/ledger',
  '/api/clubs/{club_id}/honors-timeline':
      '/api/v2/clubs/{club_id}/honors-timeline',
  '/api/clubs/{club_id}/identity': '/api/v2/clubs/{club_id}/identity',
  '/api/clubs/{club_id}/identity/metrics':
      '/api/v2/clubs/{club_id}/identity/metrics',
  '/api/clubs/{club_id}/identity/metrics/refresh':
      '/api/v2/clubs/{club_id}/identity/metrics/refresh',
  '/api/clubs/{club_id}/jerseys': '/api/v2/clubs/{club_id}/jerseys',
  '/api/clubs/{club_id}/jerseys/{jersey_id}':
      '/api/v2/clubs/{club_id}/jerseys/{jersey_id}',
  '/api/clubs/{club_id}/ownership': '/api/v2/clubs/{club_id}/ownership',
  '/api/clubs/{club_id}/prestige': '/api/v2/clubs/{club_id}/prestige',
  '/api/clubs/{club_id}/proposals': '/api/v2/clubs/{club_id}/proposals',
  '/api/clubs/{club_id}/purchases': '/api/v2/clubs/{club_id}/purchases',
  '/api/clubs/{club_id}/reputation': '/api/v2/clubs/{club_id}/reputation',
  '/api/clubs/{club_id}/reputation/history':
      '/api/v2/clubs/{club_id}/reputation/history',
  '/api/clubs/{club_id}/rivalries': '/api/v2/clubs/{club_id}/rivalries',
  '/api/clubs/{club_id}/rivalries/{opponent_club_id}':
      '/api/v2/clubs/{club_id}/rivalries/{opponent_club_id}',
  '/api/clubs/{club_id}/sale-market': '/api/v2/clubs/{club_id}/sale-market',
  '/api/clubs/{club_id}/sale-market/assistant':
      '/api/v2/clubs/{club_id}/sale-market/assistant',
  '/api/clubs/{club_id}/sale-market/history':
      '/api/v2/clubs/{club_id}/sale-market/history',
  '/api/clubs/{club_id}/sale-market/inquiries':
      '/api/v2/clubs/{club_id}/sale-market/inquiries',
  '/api/clubs/{club_id}/sale-market/inquiries/{inquiry_id}/respond':
      '/api/v2/clubs/{club_id}/sale-market/inquiries/{inquiry_id}/respond',
  '/api/clubs/{club_id}/sale-market/listing':
      '/api/v2/clubs/{club_id}/sale-market/listing',
  '/api/clubs/{club_id}/sale-market/listing/cancel':
      '/api/v2/clubs/{club_id}/sale-market/listing/cancel',
  '/api/clubs/{club_id}/sale-market/listing/instant-sell':
      '/api/v2/clubs/{club_id}/sale-market/listing/instant-sell',
  '/api/clubs/{club_id}/sale-market/offers':
      '/api/v2/clubs/{club_id}/sale-market/offers',
  '/api/clubs/{club_id}/sale-market/offers/{offer_id}/accept':
      '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/accept',
  '/api/clubs/{club_id}/sale-market/offers/{offer_id}/counter':
      '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/counter',
  '/api/clubs/{club_id}/sale-market/offers/{offer_id}/reject':
      '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/reject',
  '/api/clubs/{club_id}/sale-market/transfer':
      '/api/v2/clubs/{club_id}/sale-market/transfer',
  '/api/clubs/{club_id}/scouting': '/api/v2/clubs/{club_id}/scouting',
  '/api/clubs/{club_id}/scouting-intelligence/academy-supply-signals':
      '/api/v2/clubs/{club_id}/scouting-intelligence/academy-supply-signals',
  '/api/clubs/{club_id}/scouting-intelligence/assignments':
      '/api/v2/clubs/{club_id}/scouting-intelligence/assignments',
  '/api/clubs/{club_id}/scouting-intelligence/badges':
      '/api/v2/clubs/{club_id}/scouting-intelligence/badges',
  '/api/clubs/{club_id}/scouting-intelligence/lifecycle':
      '/api/v2/clubs/{club_id}/scouting-intelligence/lifecycle',
  '/api/clubs/{club_id}/scouting-intelligence/manager-profiles':
      '/api/v2/clubs/{club_id}/scouting-intelligence/manager-profiles',
  '/api/clubs/{club_id}/scouting-intelligence/missions':
      '/api/v2/clubs/{club_id}/scouting-intelligence/missions',
  '/api/clubs/{club_id}/scouting-intelligence/missions/{mission_id}':
      '/api/v2/clubs/{club_id}/scouting-intelligence/missions/{mission_id}',
  '/api/clubs/{club_id}/scouting-intelligence/missions/{mission_id}/complete':
      '/api/v2/clubs/{club_id}/scouting-intelligence/missions/{mission_id}/complete',
  '/api/clubs/{club_id}/scouting-intelligence/networks':
      '/api/v2/clubs/{club_id}/scouting-intelligence/networks',
  '/api/clubs/{club_id}/scouting-intelligence/planning':
      '/api/v2/clubs/{club_id}/scouting-intelligence/planning',
  '/api/clubs/{club_id}/scouting/assignments':
      '/api/v2/clubs/{club_id}/scouting/assignments',
  '/api/clubs/{club_id}/scouting/prospects':
      '/api/v2/clubs/{club_id}/scouting/prospects',
  '/api/clubs/{club_id}/scouting/prospects/{prospect_id}':
      '/api/v2/clubs/{club_id}/scouting/prospects/{prospect_id}',
  '/api/clubs/{club_id}/season-honors': '/api/v2/clubs/{club_id}/season-honors',
  '/api/clubs/{club_id}/sell-tokens': '/api/v2/clubs/{club_id}/sell-tokens',
  '/api/clubs/{club_id}/showcase': '/api/v2/clubs/{club_id}/showcase',
  '/api/clubs/{club_id}/sponsorships': '/api/v2/clubs/{club_id}/sponsorships',
  '/api/clubs/{club_id}/sponsorships/assets':
      '/api/v2/clubs/{club_id}/sponsorships/assets',
  '/api/clubs/{club_id}/sponsorships/catalog':
      '/api/v2/clubs/{club_id}/sponsorships/catalog',
  '/api/clubs/{club_id}/sponsorships/contracts':
      '/api/v2/clubs/{club_id}/sponsorships/contracts',
  '/api/clubs/{club_id}/sponsorships/contracts/{contract_id}':
      '/api/v2/clubs/{club_id}/sponsorships/contracts/{contract_id}',
  '/api/clubs/{club_id}/treasury': '/api/v2/clubs/{club_id}/treasury',
  '/api/clubs/{club_id}/trophies': '/api/v2/clubs/{club_id}/trophies',
  '/api/clubs/{club_id}/trophy-cabinet':
      '/api/v2/clubs/{club_id}/trophy-cabinet',
  '/api/clubs/{club_id}/valuation': '/api/v2/clubs/{club_id}/valuation',
  '/api/clubs/{club_id}/vote': '/api/v2/clubs/{club_id}/vote',
  '/api/clubs/{club_id}/youth-pipeline':
      '/api/v2/clubs/{club_id}/youth-pipeline',
  '/api/commentary/profiles': '/api/v2/commentary/profiles',
  '/api/commentary/select': '/api/v2/commentary/select',
  '/api/community/creator-clubs/{club_id}/fan-competitions':
      '/api/v2/community/creator-clubs/{club_id}/fan-competitions',
  '/api/community/creator-clubs/{club_id}/fan-groups':
      '/api/v2/community/creator-clubs/{club_id}/fan-groups',
  '/api/community/creator-clubs/{club_id}/fan-state':
      '/api/v2/community/creator-clubs/{club_id}/fan-state',
  '/api/community/creator-clubs/{club_id}/follow':
      '/api/v2/community/creator-clubs/{club_id}/follow',
  '/api/community/creator-matches/{match_id}/chat-room':
      '/api/v2/community/creator-matches/{match_id}/chat-room',
  '/api/community/creator-matches/{match_id}/chat-room/messages':
      '/api/v2/community/creator-matches/{match_id}/chat-room/messages',
  '/api/community/creator-matches/{match_id}/fan-wall':
      '/api/v2/community/creator-matches/{match_id}/fan-wall',
  '/api/community/creator-matches/{match_id}/rivalry-signals':
      '/api/v2/community/creator-matches/{match_id}/rivalry-signals',
  '/api/community/creator-matches/{match_id}/tactical-advice':
      '/api/v2/community/creator-matches/{match_id}/tactical-advice',
  '/api/community/digest': '/api/v2/community/digest',
  '/api/community/fan-competitions/{fan_competition_id}/join':
      '/api/v2/community/fan-competitions/{fan_competition_id}/join',
  '/api/community/fan-groups/{group_id}/join':
      '/api/v2/community/fan-groups/{group_id}/join',
  '/api/community/live-threads': '/api/v2/community/live-threads',
  '/api/community/live-threads/{thread_id}':
      '/api/v2/community/live-threads/{thread_id}',
  '/api/community/live-threads/{thread_id}/messages':
      '/api/v2/community/live-threads/{thread_id}/messages',
  '/api/community/private-messages/threads':
      '/api/v2/community/private-messages/threads',
  '/api/community/private-messages/threads/{thread_id}':
      '/api/v2/community/private-messages/threads/{thread_id}',
  '/api/community/private-messages/threads/{thread_id}/messages':
      '/api/v2/community/private-messages/threads/{thread_id}/messages',
  '/api/community/watchlist': '/api/v2/community/watchlist',
  '/api/community/watchlist/{competition_key}':
      '/api/v2/community/watchlist/{competition_key}',
  '/api/competitions': '/api/v2/competitions',
  '/api/competitions/admin': '/api/v2/competitions/admin',
  '/api/competitions/admin/{code}': '/api/v2/competitions/admin/{code}',
  '/api/competitions/admin/{code}/orchestrate':
      '/api/v2/competitions/admin/{code}/orchestrate',
  '/api/competitions/create': '/api/v2/competitions/create',
  '/api/competitions/join': '/api/v2/competitions/join',
  '/api/competitions/players/{subject_id}/progression':
      '/api/v2/competitions/players/{subject_id}/progression',
  '/api/competitions/records/{competition_id}':
      '/api/v2/competitions/records/{competition_id}',
  '/api/competitions/runtime/{code}': '/api/v2/competitions/runtime/{code}',
  '/api/competitions/{competition_id}': '/api/v2/competitions/{competition_id}',
  '/api/competitions/{competition_id}/advance':
      '/api/v2/competitions/{competition_id}/advance',
  '/api/competitions/{competition_id}/finalize':
      '/api/v2/competitions/{competition_id}/finalize',
  '/api/competitions/{competition_id}/financials':
      '/api/v2/competitions/{competition_id}/financials',
  '/api/competitions/{competition_id}/fixtures':
      '/api/v2/competitions/{competition_id}/fixtures',
  '/api/competitions/{competition_id}/invites':
      '/api/v2/competitions/{competition_id}/invites',
  '/api/competitions/{competition_id}/invites/accept':
      '/api/v2/competitions/{competition_id}/invites/accept',
  '/api/competitions/{competition_id}/join':
      '/api/v2/competitions/{competition_id}/join',
  '/api/competitions/{competition_id}/launch':
      '/api/v2/competitions/{competition_id}/launch',
  '/api/competitions/{competition_id}/leave':
      '/api/v2/competitions/{competition_id}/leave',
  '/api/competitions/{competition_id}/matches/{match_id}/events':
      '/api/v2/competitions/{competition_id}/matches/{match_id}/events',
  '/api/competitions/{competition_id}/matches/{match_id}/result':
      '/api/v2/competitions/{competition_id}/matches/{match_id}/result',
  '/api/competitions/{competition_id}/publish':
      '/api/v2/competitions/{competition_id}/publish',
  '/api/competitions/{competition_id}/rewards':
      '/api/v2/competitions/{competition_id}/rewards',
  '/api/competitions/{competition_id}/rounds':
      '/api/v2/competitions/{competition_id}/rounds',
  '/api/competitions/{competition_id}/schedule/jobs':
      '/api/v2/competitions/{competition_id}/schedule/jobs',
  '/api/competitions/{competition_id}/schedule/jobs/{job_id}':
      '/api/v2/competitions/{competition_id}/schedule/jobs/{job_id}',
  '/api/competitions/{competition_id}/schedule/preview':
      '/api/v2/competitions/{competition_id}/schedule/preview',
  '/api/competitions/{competition_id}/seed':
      '/api/v2/competitions/{competition_id}/seed',
  '/api/competitions/{competition_id}/standings':
      '/api/v2/competitions/{competition_id}/standings',
  '/api/competitions/{competition_id}/summary':
      '/api/v2/competitions/{competition_id}/summary',
  '/api/competitive-integrity/fast-game/runs':
      '/api/v2/competitive-integrity/fast-game/runs',
  '/api/competitive-integrity/fast-game/runs/{run_id}':
      '/api/v2/competitive-integrity/fast-game/runs/{run_id}',
  '/api/competitive-integrity/fast-game/runs/{run_id}/play':
      '/api/v2/competitive-integrity/fast-game/runs/{run_id}/play',
  '/api/competitive-integrity/managers':
      '/api/v2/competitive-integrity/managers',
  '/api/competitive-integrity/managers/candidates':
      '/api/v2/competitive-integrity/managers/candidates',
  '/api/competitive-integrity/managers/{manager_id}/instructions':
      '/api/v2/competitive-integrity/managers/{manager_id}/instructions',
  '/api/competitive-integrity/matches': '/api/v2/competitive-integrity/matches',
  '/api/competitive-integrity/matches/{match_id}':
      '/api/v2/competitive-integrity/matches/{match_id}',
  '/api/competitive-integrity/matches/{match_id}/execute':
      '/api/v2/competitive-integrity/matches/{match_id}/execute',
  '/api/competitive-integrity/notifications/events':
      '/api/v2/competitive-integrity/notifications/events',
  '/api/config/current': '/api/v2/config/current',
  '/api/config/update': '/api/v2/config/update',
  '/api/conversations': '/api/v2/conversations',
  '/api/conversations/start': '/api/v2/conversations/start',
  '/api/conversations/{conversation_id}/message':
      '/api/v2/conversations/{conversation_id}/message',
  '/api/conversations/{conversation_id}/messages':
      '/api/v2/conversations/{conversation_id}/messages',
  '/api/conversations/{conversation_id}/status':
      '/api/v2/conversations/{conversation_id}/status',
  '/api/creator-campaigns': '/api/v2/creator-campaigns',
  '/api/creator-campaigns/me': '/api/v2/creator-campaigns/me',
  '/api/creator-campaigns/{campaign_id}':
      '/api/v2/creator-campaigns/{campaign_id}',
  '/api/creator-campaigns/{campaign_id}/metrics':
      '/api/v2/creator-campaigns/{campaign_id}/metrics',
  '/api/creator-campaigns/{campaign_id}/snapshot':
      '/api/v2/creator-campaigns/{campaign_id}/snapshot',
  '/api/creator-campaigns/{campaign_id}/snapshots':
      '/api/v2/creator-campaigns/{campaign_id}/snapshots',
  '/api/creator-league': '/api/v2/creator-league',
  '/api/creator-league/config': '/api/v2/creator-league/config',
  '/api/creator-league/financial-report':
      '/api/v2/creator-league/financial-report',
  '/api/creator-league/financial-settlements':
      '/api/v2/creator-league/financial-settlements',
  '/api/creator-league/financial-settlements/{settlement_id}/approve':
      '/api/v2/creator-league/financial-settlements/{settlement_id}/approve',
  '/api/creator-league/live-priority': '/api/v2/creator-league/live-priority',
  '/api/creator-league/reset': '/api/v2/creator-league/reset',
  '/api/creator-league/season-tiers/{season_tier_id}/standings':
      '/api/v2/creator-league/season-tiers/{season_tier_id}/standings',
  '/api/creator-league/seasons': '/api/v2/creator-league/seasons',
  '/api/creator-league/seasons/{season_id}':
      '/api/v2/creator-league/seasons/{season_id}',
  '/api/creator-league/seasons/{season_id}/pause':
      '/api/v2/creator-league/seasons/{season_id}/pause',
  '/api/creator-league/tiers': '/api/v2/creator-league/tiers',
  '/api/creator-league/tiers/{tier_id}':
      '/api/v2/creator-league/tiers/{tier_id}',
  '/api/creator/application': '/api/v2/creator/application',
  '/api/creator/apply': '/api/v2/creator/apply',
  '/api/creator/cards': '/api/v2/creator/cards',
  '/api/creator/cards/listings': '/api/v2/creator/cards/listings',
  '/api/creator/cards/listings/{listing_id}/buy':
      '/api/v2/creator/cards/listings/{listing_id}/buy',
  '/api/creator/cards/loans/{loan_id}/return':
      '/api/v2/creator/cards/loans/{loan_id}/return',
  '/api/creator/cards/swap': '/api/v2/creator/cards/swap',
  '/api/creator/cards/{creator_card_id}/list':
      '/api/v2/creator/cards/{creator_card_id}/list',
  '/api/creator/cards/{creator_card_id}/loan':
      '/api/v2/creator/cards/{creator_card_id}/loan',
  '/api/creator/clubs/{club_id}/fan-share-market':
      '/api/v2/creator/clubs/{club_id}/fan-share-market',
  '/api/creator/clubs/{club_id}/fan-share-market/distributions':
      '/api/v2/creator/clubs/{club_id}/fan-share-market/distributions',
  '/api/creator/clubs/{club_id}/fan-share-market/holding':
      '/api/v2/creator/clubs/{club_id}/fan-share-market/holding',
  '/api/creator/clubs/{club_id}/fan-share-market/purchase':
      '/api/v2/creator/clubs/{club_id}/fan-share-market/purchase',
  '/api/creator/verify-email': '/api/v2/creator/verify-email',
  '/api/creator/verify-phone': '/api/v2/creator/verify-phone',
  '/api/creators/marketplace': '/api/v2/creators/marketplace',
  '/api/creators/me/competitions': '/api/v2/creators/me/competitions',
  '/api/creators/me/copilot/analyze': '/api/v2/creators/me/copilot/analyze',
  '/api/creators/me/finance': '/api/v2/creators/me/finance',
  '/api/creators/me/insights': '/api/v2/creators/me/insights',
  '/api/creators/me/reputation': '/api/v2/creators/me/reputation',
  '/api/creators/me/summary': '/api/v2/creators/me/summary',
  '/api/creators/profile': '/api/v2/creators/profile',
  '/api/creators/profile/me': '/api/v2/creators/profile/me',
  '/api/creators/{handle}': '/api/v2/creators/{handle}',
  '/api/daily-challenges': '/api/v2/daily-challenges',
  '/api/daily-challenges/me': '/api/v2/daily-challenges/me',
  '/api/daily-challenges/{challenge_key}/claim':
      '/api/v2/daily-challenges/{challenge_key}/claim',
  '/api/diagnostics': '/api/v2/diagnostics',
  '/api/discovery/home': '/api/v2/discovery/home',
  '/api/discovery/saved-searches': '/api/v2/discovery/saved-searches',
  '/api/discovery/saved-searches/{search_id}':
      '/api/v2/discovery/saved-searches/{search_id}',
  '/api/discovery/search': '/api/v2/discovery/search',
  '/api/disputes': '/api/v2/disputes',
  '/api/disputes/me': '/api/v2/disputes/me',
  '/api/disputes/{dispute_id}': '/api/v2/disputes/{dispute_id}',
  '/api/disputes/{dispute_id}/messages':
      '/api/v2/disputes/{dispute_id}/messages',
  '/api/dynasty': '/api/v2/dynasty',
  '/api/dynasty/leaderboard': '/api/v2/dynasty/leaderboard',
  '/api/economy/fx/quote': '/api/v2/economy/fx/quote',
  '/api/economy/gift-catalog': '/api/v2/economy/gift-catalog',
  '/api/economy/service-pricing': '/api/v2/economy/service-pricing',
  '/api/engagement/achievements': '/api/v2/engagement/achievements',
  '/api/engagement/achievements/me': '/api/v2/engagement/achievements/me',
  '/api/engagement/milestones/me': '/api/v2/engagement/milestones/me',
  '/api/engagement/sync': '/api/v2/engagement/sync',
  '/api/enter': '/api/v2/enter',
  '/api/events/clip': '/api/v2/events/clip',
  '/api/events/today': '/api/v2/events/today',
  '/api/events/upcoming': '/api/v2/events/upcoming',
  '/api/experience/full-simulation': '/api/v2/experience/full-simulation',
  '/api/fan-predictions/creator-clubs/{club_id}/leaderboards/weekly':
      '/api/v2/fan-predictions/creator-clubs/{club_id}/leaderboards/weekly',
  '/api/fan-predictions/leaderboards/weekly':
      '/api/v2/fan-predictions/leaderboards/weekly',
  '/api/fan-predictions/matches/{match_id}':
      '/api/v2/fan-predictions/matches/{match_id}',
  '/api/fan-predictions/matches/{match_id}/leaderboard':
      '/api/v2/fan-predictions/matches/{match_id}/leaderboard',
  '/api/fan-predictions/matches/{match_id}/submissions':
      '/api/v2/fan-predictions/matches/{match_id}/submissions',
  '/api/fan-predictions/me/submissions':
      '/api/v2/fan-predictions/me/submissions',
  '/api/fan-predictions/me/tokens': '/api/v2/fan-predictions/me/tokens',
  '/api/fan-wars/leaderboards/{board_type}':
      '/api/v2/fan-wars/leaderboards/{board_type}',
  '/api/fan-wars/nations-cup/{competition_id}':
      '/api/v2/fan-wars/nations-cup/{competition_id}',
  '/api/fan-wars/profiles/{profile_id}/dashboard':
      '/api/v2/fan-wars/profiles/{profile_id}/dashboard',
  '/api/fan-wars/rivalries/{board_type}':
      '/api/v2/fan-wars/rivalries/{board_type}',
  '/api/fans/profile': '/api/v2/fans/profile',
  '/api/fans/tribe/join': '/api/v2/fans/tribe/join',
  '/api/fans/{club_id}': '/api/v2/fans/{club_id}',
  '/api/fast-cups/upcoming': '/api/v2/fast-cups/upcoming',
  '/api/fast-cups/{cup_id}/bracket': '/api/v2/fast-cups/{cup_id}/bracket',
  '/api/fast-cups/{cup_id}/countdown': '/api/v2/fast-cups/{cup_id}/countdown',
  '/api/fast-cups/{cup_id}/join': '/api/v2/fast-cups/{cup_id}/join',
  '/api/fast-cups/{cup_id}/result-summary':
      '/api/v2/fast-cups/{cup_id}/result-summary',
  '/api/federations': '/api/v2/federations',
  '/api/federations/proposals/{proposal_id}/votes':
      '/api/v2/federations/proposals/{proposal_id}/votes',
  '/api/federations/rankings': '/api/v2/federations/rankings',
  '/api/federations/regional-tournaments':
      '/api/v2/federations/regional-tournaments',
  '/api/federations/{federation_id}': '/api/v2/federations/{federation_id}',
  '/api/federations/{federation_id}/governance':
      '/api/v2/federations/{federation_id}/governance',
  '/api/federations/{federation_id}/leagues':
      '/api/v2/federations/{federation_id}/leagues',
  '/api/federations/{federation_id}/memberships':
      '/api/v2/federations/{federation_id}/memberships',
  '/api/federations/{federation_id}/narratives':
      '/api/v2/federations/{federation_id}/narratives',
  '/api/federations/{federation_id}/proposals':
      '/api/v2/federations/{federation_id}/proposals',
  '/api/federations/{federation_id}/sanctions':
      '/api/v2/federations/{federation_id}/sanctions',
  '/api/federations/{federation_id}/treasury/distribute':
      '/api/v2/federations/{federation_id}/treasury/distribute',
  '/api/federations/{federation_id}/validate-action':
      '/api/v2/federations/{federation_id}/validate-action',
  '/api/feed/following': '/api/v2/feed/following',
  '/api/feed/for-you': '/api/v2/feed/for-you',
  '/api/feed/for-you/refresh': '/api/v2/feed/for-you/refresh',
  '/api/feed/sponsored': '/api/v2/feed/sponsored',
  '/api/finance': '/api/v2/finance',
  '/api/follow/{user_id}': '/api/v2/follow/{user_id}',
  '/api/football-events/players/{player_id}/events':
      '/api/v2/football-events/players/{player_id}/events',
  '/api/football-events/players/{player_id}/impact':
      '/api/v2/football-events/players/{player_id}/impact',
  '/api/gift-engine/me/combos': '/api/v2/gift-engine/me/combos',
  '/api/gift-engine/me/summary': '/api/v2/gift-engine/me/summary',
  '/api/gift-engine/me/transactions': '/api/v2/gift-engine/me/transactions',
  '/api/gift-engine/send': '/api/v2/gift-engine/send',
  '/api/governance/clubs/{club_id}/panel':
      '/api/v2/governance/clubs/{club_id}/panel',
  '/api/governance/me/overview': '/api/v2/governance/me/overview',
  '/api/governance/proposals': '/api/v2/governance/proposals',
  '/api/governance/proposals/{proposal_id}':
      '/api/v2/governance/proposals/{proposal_id}',
  '/api/governance/proposals/{proposal_id}/vote':
      '/api/v2/governance/proposals/{proposal_id}/vote',
  '/api/gtex/market/buy': '/api/v2/gtex/market/buy',
  '/api/gtex/market/sell': '/api/v2/gtex/market/sell',
  '/api/hall-of-fame': '/api/v2/hall-of-fame',
  '/api/health': '/health',
  '/api/history/goat-rankings': '/api/v2/history/goat-rankings',
  '/api/history/leaderboards': '/api/v2/history/leaderboards',
  '/api/history/records': '/api/v2/history/records',
  '/api/history/timeline/{subject_type}/{subject_id}':
      '/api/v2/history/timeline/{subject_type}/{subject_id}',
  '/api/hosted-competitions': '/api/v2/hosted-competitions',
  '/api/hosted-competitions/mine': '/api/v2/hosted-competitions/mine',
  '/api/hosted-competitions/mine/invites':
      '/api/v2/hosted-competitions/mine/invites',
  '/api/hosted-competitions/templates': '/api/v2/hosted-competitions/templates',
  '/api/hosted-competitions/{competition_id}':
      '/api/v2/hosted-competitions/{competition_id}',
  '/api/hosted-competitions/{competition_id}/finance':
      '/api/v2/hosted-competitions/{competition_id}/finance',
  '/api/hosted-competitions/{competition_id}/invites':
      '/api/v2/hosted-competitions/{competition_id}/invites',
  '/api/hosted-competitions/{competition_id}/invites/accept':
      '/api/v2/hosted-competitions/{competition_id}/invites/accept',
  '/api/hosted-competitions/{competition_id}/join':
      '/api/v2/hosted-competitions/{competition_id}/join',
  '/api/hosted-competitions/{competition_id}/launch':
      '/api/v2/hosted-competitions/{competition_id}/launch',
  '/api/hosted-competitions/{competition_id}/standings':
      '/api/v2/hosted-competitions/{competition_id}/standings',
  '/api/infinite-league/economy': '/api/v2/infinite-league/economy',
  '/api/infinite-league/livestream': '/api/v2/infinite-league/livestream',
  '/api/infinite-league/matches': '/api/v2/infinite-league/matches',
  '/api/infinite-league/matches/{match_id}':
      '/api/v2/infinite-league/matches/{match_id}',
  '/api/infinite-league/pundits/{match_id}':
      '/api/v2/infinite-league/pundits/{match_id}',
  '/api/infinite-league/status': '/api/v2/infinite-league/status',
  '/api/infinite-league/tick': '/api/v2/infinite-league/tick',
  '/api/infinite-league/viral-feed': '/api/v2/infinite-league/viral-feed',
  '/api/integrations/payments/korapay/webhook':
      '/api/v2/integrations/payments/korapay/webhook',
  '/api/integrations/payments/methods': '/api/v2/integrations/payments/methods',
  '/api/integrations/payments/orders': '/api/v2/integrations/payments/orders',
  '/api/integrations/payments/paystack/webhook':
      '/api/v2/integrations/payments/paystack/webhook',
  '/api/integrations/payments/quote': '/api/v2/integrations/payments/quote',
  '/api/integrity-engine/me/incidents': '/api/v2/integrity-engine/me/incidents',
  '/api/integrity-engine/me/score': '/api/v2/integrity-engine/me/score',
  '/api/internal/ingestion/bootstrap-sync':
      '/api/v2/internal/ingestion/bootstrap-sync',
  '/api/internal/ingestion/clubs/{club_external_id}/refresh':
      '/api/v2/internal/ingestion/clubs/{club_external_id}/refresh',
  '/api/internal/ingestion/competitions/{competition_external_id}/refresh':
      '/api/v2/internal/ingestion/competitions/{competition_external_id}/refresh',
  '/api/internal/ingestion/cursors/{provider_name}':
      '/api/v2/internal/ingestion/cursors/{provider_name}',
  '/api/internal/ingestion/incremental-sync':
      '/api/v2/internal/ingestion/incremental-sync',
  '/api/internal/ingestion/players/{player_external_id}/refresh':
      '/api/v2/internal/ingestion/players/{player_external_id}/refresh',
  '/api/internal/ingestion/providers/{provider_name}/health':
      '/api/v2/internal/ingestion/providers/{provider_name}/health',
  '/api/internal/ingestion/real-players/batches':
      '/api/v2/internal/ingestion/real-players/batches',
  '/api/internal/ingestion/real-players/batches/{batch_id}':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}',
  '/api/internal/ingestion/real-players/batches/{batch_id}/issues':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}/issues',
  '/api/internal/ingestion/real-players/batches/{batch_id}/resume':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}/resume',
  '/api/internal/ingestion/real-players/batches/{batch_id}/valuation-status':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}/valuation-status',
  '/api/internal/ingestion/real-players/import':
      '/api/v2/internal/ingestion/real-players/import',
  '/api/internal/ingestion/real-players/publish-jobs':
      '/api/v2/internal/ingestion/real-players/publish-jobs',
  '/api/internal/ingestion/real-players/publish-jobs/{job_id}':
      '/api/v2/internal/ingestion/real-players/publish-jobs/{job_id}',
  '/api/internal/ingestion/real-players/status':
      '/api/v2/internal/ingestion/real-players/status',
  '/api/internal/ingestion/runs': '/api/v2/internal/ingestion/runs',
  '/api/internal/ingestion/status': '/api/v2/internal/ingestion/status',
  '/api/jackpot/contribute': '/api/v2/jackpot/contribute',
  '/api/jackpot/history': '/api/v2/jackpot/history',
  '/api/jackpot/state': '/api/v2/jackpot/state',
  '/api/jobs/{job_id}': '/api/v2/jobs/{job_id}',
  '/api/kyc': '/api/v2/kyc',
  '/api/leaderboard/division/{division}':
      '/api/v2/leaderboard/division/{division}',
  '/api/leaderboard/global': '/api/v2/leaderboard/global',
  '/api/leaderboard/player/{player_id}':
      '/api/v2/leaderboard/player/{player_id}',
  '/api/leaderboard/region/{region}': '/api/v2/leaderboard/region/{region}',
  '/api/leaderboards/dynasties': '/api/v2/leaderboards/dynasties',
  '/api/leaderboards/prestige': '/api/v2/leaderboards/prestige',
  '/api/leaderboards/trophies': '/api/v2/leaderboards/trophies',
  '/api/leagues/register': '/api/v2/leagues/register',
  '/api/leagues/{season_id}/fixtures': '/api/v2/leagues/{season_id}/fixtures',
  '/api/leagues/{season_id}/qualification-markers':
      '/api/v2/leagues/{season_id}/qualification-markers',
  '/api/leagues/{season_id}/standings': '/api/v2/leagues/{season_id}/standings',
  '/api/leagues/{season_id}/summary': '/api/v2/leagues/{season_id}/summary',
  '/api/legacy/board': '/api/v2/legacy/board',
  '/api/live-events': '/api/v2/live-events',
  '/api/manager-duels': '/api/v2/manager-duels',
  '/api/manager-duels/leaderboard': '/api/v2/manager-duels/leaderboard',
  '/api/manager-duels/{duel_id}': '/api/v2/manager-duels/{duel_id}',
  '/api/managers': '/api/v2/managers',
  '/api/managers/assign': '/api/v2/managers/assign',
  '/api/managers/catalog': '/api/v2/managers/catalog',
  '/api/managers/compare': '/api/v2/managers/compare',
  '/api/managers/competition-runtime/{code}':
      '/api/v2/managers/competition-runtime/{code}',
  '/api/managers/create': '/api/v2/managers/create',
  '/api/managers/filters': '/api/v2/managers/filters',
  '/api/managers/history': '/api/v2/managers/history',
  '/api/managers/leaderboard': '/api/v2/managers/leaderboard',
  '/api/managers/my-trade-listings': '/api/v2/managers/my-trade-listings',
  '/api/managers/recommendation': '/api/v2/managers/recommendation',
  '/api/managers/recruit': '/api/v2/managers/recruit',
  '/api/managers/swap': '/api/v2/managers/swap',
  '/api/managers/team': '/api/v2/managers/team',
  '/api/managers/trade-listings': '/api/v2/managers/trade-listings',
  '/api/managers/trade-listings/{listing_id}/buy':
      '/api/v2/managers/trade-listings/{listing_id}/buy',
  '/api/managers/trade-listings/{listing_id}/cancel':
      '/api/v2/managers/trade-listings/{listing_id}/cancel',
  '/api/managers/{asset_id}/release': '/api/v2/managers/{asset_id}/release',
  '/api/managers/{manager_id}': '/api/v2/managers/{manager_id}',
  '/api/managers/{manager_id}/hire': '/api/v2/managers/{manager_id}/hire',
  '/api/managers/{manager_id}/history': '/api/v2/managers/{manager_id}/history',
  '/api/managers/{manager_id}/release': '/api/v2/managers/{manager_id}/release',
  '/api/market/buy': '/api/v2/market/buy',
  '/api/market/listings': '/api/v2/market/listings',
  '/api/market/listings/{listing_id}/cancel':
      '/api/v2/market/listings/{listing_id}/cancel',
  '/api/market/listings/{listing_id}/matches':
      '/api/v2/market/listings/{listing_id}/matches',
  '/api/market/listings/{listing_id}/offers':
      '/api/v2/market/listings/{listing_id}/offers',
  '/api/market/movers': '/api/v2/market/movers',
  '/api/market/offers': '/api/v2/market/offers',
  '/api/market/offers/{offer_id}/accept':
      '/api/v2/market/offers/{offer_id}/accept',
  '/api/market/offers/{offer_id}/counter':
      '/api/v2/market/offers/{offer_id}/counter',
  '/api/market/offers/{offer_id}/reject':
      '/api/v2/market/offers/{offer_id}/reject',
  '/api/market/players': '/api/v2/market/players',
  '/api/market/players/{player_id}': '/api/v2/market/players/{player_id}',
  '/api/market/players/{player_id}/candles':
      '/api/v2/market/players/{player_id}/candles',
  '/api/market/players/{player_id}/history':
      '/api/v2/market/players/{player_id}/history',
  '/api/market/sell': '/api/v2/market/sell',
  '/api/market/summary/{asset_id}': '/api/v2/market/summary/{asset_id}',
  '/api/market/ticker/{player_id}': '/api/v2/market/ticker/{player_id}',
  '/api/market/trade-intents': '/api/v2/market/trade-intents',
  '/api/market/trade-intents/{intent_id}/withdraw':
      '/api/v2/market/trade-intents/{intent_id}/withdraw',
  '/api/market/trending': '/api/v2/market/trending',
  '/api/marketplace/my-players': '/api/v2/marketplace/my-players',
  '/api/marketplace/players': '/api/v2/marketplace/players',
  '/api/marketplace/players/{player_id}':
      '/api/v2/marketplace/players/{player_id}',
  '/api/match-engine/analytics': '/api/v2/match-engine/analytics',
  '/api/match-engine/analytics/{match_key}':
      '/api/v2/match-engine/analytics/{match_key}',
  '/api/match-engine/highlights/{match_key}':
      '/api/v2/match-engine/highlights/{match_key}',
  '/api/match-engine/live-feed/{match_key}':
      '/api/v2/match-engine/live-feed/{match_key}',
  '/api/match-engine/render-sync': '/api/v2/match-engine/render-sync',
  '/api/match-engine/render-sync/{match_key}':
      '/api/v2/match-engine/render-sync/{match_key}',
  '/api/match-engine/replay': '/api/v2/match-engine/replay',
  '/api/match-engine/simulate': '/api/v2/match-engine/simulate',
  '/api/match-engine/summary': '/api/v2/match-engine/summary',
  '/api/match-engine/timeline': '/api/v2/match-engine/timeline',
  '/api/match-share-links/{share_code}':
      '/api/v2/match-share-links/{share_code}',
  '/api/match-share-links/{share_code}/events':
      '/api/v2/match-share-links/{share_code}/events',
  '/api/match-viewer/{match_key}': '/api/v2/match-viewer/{match_key}',
  '/api/match-viewer/{match_key}/illusion':
      '/api/v2/match-viewer/{match_key}/illusion',
  '/api/match-viewer/{match_key}/session':
      '/api/v2/match-viewer/{match_key}/session',
  '/api/match/find': '/api/v2/match/find',
  '/api/match/live/active': '/api/v2/match/live/active',
  '/api/match/{match_id}/commentary/stream':
      '/api/v2/match/{match_id}/commentary/stream',
  '/api/match/{match_id}/live': '/api/v2/match/{match_id}/live',
  '/api/match/{match_id}/unity-access': '/api/v2/match/{match_id}/unity-access',
  '/api/match/{match_id}/unity-access/refresh':
      '/api/v2/match/{match_id}/unity-access/refresh',
  '/api/matches/complete': '/api/v2/matches/complete',
  '/api/matches/live/active': '/api/v2/matches/live/active',
  '/api/matches/start': '/api/v2/matches/start',
  '/api/matches/{match_id}/analysis': '/api/v2/matches/{match_id}/analysis',
  '/api/matches/{match_id}/audio/stems/stream':
      '/api/v2/matches/{match_id}/audio/stems/stream',
  '/api/matches/{match_id}/chat': '/api/v2/matches/{match_id}/chat',
  '/api/matches/{match_id}/chat/messages':
      '/api/v2/matches/{match_id}/chat/messages',
  '/api/matches/{match_id}/commentary': '/api/v2/matches/{match_id}/commentary',
  '/api/matches/{match_id}/commentary/stream':
      '/api/v2/matches/{match_id}/commentary/stream',
  '/api/matches/{match_id}/fan-experience':
      '/api/v2/matches/{match_id}/fan-experience',
  '/api/matches/{match_id}/highlights': '/api/v2/matches/{match_id}/highlights',
  '/api/matches/{match_id}/highlights/share-package':
      '/api/v2/matches/{match_id}/highlights/share-package',
  '/api/matches/{match_id}/live': '/api/v2/matches/{match_id}/live',
  '/api/matches/{match_id}/live-reactions':
      '/api/v2/matches/{match_id}/live-reactions',
  '/api/matches/{match_id}/reactions': '/api/v2/matches/{match_id}/reactions',
  '/api/matches/{match_id}/replay': '/api/v2/matches/{match_id}/replay',
  '/api/matches/{match_id}/share-links':
      '/api/v2/matches/{match_id}/share-links',
  '/api/matches/{match_id}/social-warfare':
      '/api/v2/matches/{match_id}/social-warfare',
  '/api/matches/{match_id}/spectate': '/api/v2/matches/{match_id}/spectate',
  '/api/matches/{match_id}/spectators': '/api/v2/matches/{match_id}/spectators',
  '/api/matches/{match_id}/stream': '/api/v2/matches/{match_id}/stream',
  '/api/matches/{match_id}/tickets': '/api/v2/matches/{match_id}/tickets',
  '/api/matches/{match_id}/unity-access':
      '/api/v2/matches/{match_id}/unity-access',
  '/api/matches/{match_id}/unity-access/refresh':
      '/api/v2/matches/{match_id}/unity-access/refresh',
  '/api/me/clubs/sale-market/listings': '/api/v2/me/clubs/sale-market/listings',
  '/api/me/clubs/sale-market/offers': '/api/v2/me/clubs/sale-market/offers',
  '/api/media': '/api/v2/media',
  '/api/media-engine/creator-league/broadcast-modes':
      '/api/v2/media-engine/creator-league/broadcast-modes',
  '/api/media-engine/creator-league/clubs/{club_id}/stadium':
      '/api/v2/media-engine/creator-league/clubs/{club_id}/stadium',
  '/api/media-engine/creator-league/matches/{match_id}/access':
      '/api/v2/media-engine/creator-league/matches/{match_id}/access',
  '/api/media-engine/creator-league/matches/{match_id}/analytics':
      '/api/v2/media-engine/creator-league/matches/{match_id}/analytics',
  '/api/media-engine/creator-league/matches/{match_id}/gifts':
      '/api/v2/media-engine/creator-league/matches/{match_id}/gifts',
  '/api/media-engine/creator-league/matches/{match_id}/purchase':
      '/api/v2/media-engine/creator-league/matches/{match_id}/purchase',
  '/api/media-engine/creator-league/matches/{match_id}/stadium':
      '/api/v2/media-engine/creator-league/matches/{match_id}/stadium',
  '/api/media-engine/creator-league/matches/{match_id}/stadium/placements':
      '/api/v2/media-engine/creator-league/matches/{match_id}/stadium/placements',
  '/api/media-engine/creator-league/matches/{match_id}/tickets':
      '/api/v2/media-engine/creator-league/matches/{match_id}/tickets',
  '/api/media-engine/creator-league/season-passes':
      '/api/v2/media-engine/creator-league/season-passes',
  '/api/media-engine/creator-league/season-passes/me':
      '/api/v2/media-engine/creator-league/season-passes/me',
  '/api/media-engine/downloads': '/api/v2/media-engine/downloads',
  '/api/media-engine/downloads/{token}':
      '/api/v2/media-engine/downloads/{token}',
  '/api/media-engine/matches/{match_key}/snapshot':
      '/api/v2/media-engine/matches/{match_key}/snapshot',
  '/api/media-engine/me/clip-earnings': '/api/v2/media-engine/me/clip-earnings',
  '/api/media-engine/me/purchases': '/api/v2/media-engine/me/purchases',
  '/api/media-engine/me/share-exports': '/api/v2/media-engine/me/share-exports',
  '/api/media-engine/purchases': '/api/v2/media-engine/purchases',
  '/api/media-engine/share-exports': '/api/v2/media-engine/share-exports',
  '/api/media-engine/share-exports/{export_id}/amplifications':
      '/api/v2/media-engine/share-exports/{export_id}/amplifications',
  '/api/media-engine/share-templates': '/api/v2/media-engine/share-templates',
  '/api/media-engine/views': '/api/v2/media-engine/views',
  '/api/metrics': '/api/v2/metrics',
  '/api/moderation/me/reports': '/api/v2/moderation/me/reports',
  '/api/moderation/reports': '/api/v2/moderation/reports',
  '/api/moments/live': '/api/v2/moments/live',
  '/api/national-pool': '/api/v2/national-pool',
  '/api/national-team-engine/competitions':
      '/api/v2/national-team-engine/competitions',
  '/api/national-team-engine/competitions/{competition_id}':
      '/api/v2/national-team-engine/competitions/{competition_id}',
  '/api/national-team-engine/competitions/{competition_id}/ads/active':
      '/api/v2/national-team-engine/competitions/{competition_id}/ads/active',
  '/api/national-team-engine/competitions/{competition_id}/auto-build-squad':
      '/api/v2/national-team-engine/competitions/{competition_id}/auto-build-squad',
  '/api/national-team-engine/competitions/{competition_id}/entries':
      '/api/v2/national-team-engine/competitions/{competition_id}/entries',
  '/api/national-team-engine/competitions/{competition_id}/gifts':
      '/api/v2/national-team-engine/competitions/{competition_id}/gifts',
  '/api/national-team-engine/competitions/{competition_id}/lifecycle':
      '/api/v2/national-team-engine/competitions/{competition_id}/lifecycle',
  '/api/national-team-engine/competitions/{competition_id}/presentation':
      '/api/v2/national-team-engine/competitions/{competition_id}/presentation',
  '/api/national-team-engine/competitions/{competition_id}/rental-entry':
      '/api/v2/national-team-engine/competitions/{competition_id}/rental-entry',
  '/api/national-team-engine/competitions/{competition_id}/rental-pool':
      '/api/v2/national-team-engine/competitions/{competition_id}/rental-pool',
  '/api/national-team-engine/competitions/{competition_id}/story-events':
      '/api/v2/national-team-engine/competitions/{competition_id}/story-events',
  '/api/national-team-engine/competitions/{competition_id}/theme':
      '/api/v2/national-team-engine/competitions/{competition_id}/theme',
  '/api/national-team-engine/entries/{entry_id}':
      '/api/v2/national-team-engine/entries/{entry_id}',
  '/api/national-team-engine/entries/{entry_id}/free-players/claim':
      '/api/v2/national-team-engine/entries/{entry_id}/free-players/claim',
  '/api/national-team-engine/entries/{entry_id}/rental-status':
      '/api/v2/national-team-engine/entries/{entry_id}/rental-status',
  '/api/national-team-engine/entries/{entry_id}/rentals':
      '/api/v2/national-team-engine/entries/{entry_id}/rentals',
  '/api/national-team-engine/me/history':
      '/api/v2/national-team-engine/me/history',
  '/api/national-team-engine/me/previous-roster':
      '/api/v2/national-team-engine/me/previous-roster',
  '/api/national-team-engine/rankings': '/api/v2/national-team-engine/rankings',
  '/api/news/breaking': '/api/v2/news/breaking',
  '/api/news/daily': '/api/v2/news/daily',
  '/api/news/feed': '/api/v2/news/feed',
  '/api/news/personalized': '/api/v2/news/personalized',
  '/api/news/{article_id}': '/api/v2/news/{article_id}',
  '/api/notifications': '/api/v2/notifications',
  '/api/notifications/announcements': '/api/v2/notifications/announcements',
  '/api/notifications/me': '/api/v2/notifications/me',
  '/api/notifications/preferences': '/api/v2/notifications/preferences',
  '/api/notifications/read-all': '/api/v2/notifications/read-all',
  '/api/notifications/subscriptions': '/api/v2/notifications/subscriptions',
  '/api/notifications/subscriptions/{subscription_id}':
      '/api/v2/notifications/subscriptions/{subscription_id}',
  '/api/notifications/{notification_id}/read':
      '/api/v2/notifications/{notification_id}/read',
  '/api/objectives/me': '/api/v2/objectives/me',
  '/api/observability/config': '/api/v2/observability/config',
  '/api/orchestrator/config': '/api/v2/orchestrator/config',
  '/api/orchestrator/metrics': '/api/v2/orchestrator/metrics',
  '/api/orders': '/api/v2/orders',
  '/api/orders/book/{player_id}': '/api/v2/orders/book/{player_id}',
  '/api/orders/{order_id}': '/api/v2/orders/{order_id}',
  '/api/orders/{order_id}/admin-buyback':
      '/api/v2/orders/{order_id}/admin-buyback',
  '/api/orders/{order_id}/admin-buyback-preview':
      '/api/v2/orders/{order_id}/admin-buyback-preview',
  '/api/orders/{order_id}/cancel': '/api/v2/orders/{order_id}/cancel',
  '/api/organizations': '/api/v2/organizations',
  '/api/organizations/invites/accept': '/api/v2/organizations/invites/accept',
  '/api/organizations/me': '/api/v2/organizations/me',
  '/api/organizations/{organization_id}/audit-log':
      '/api/v2/organizations/{organization_id}/audit-log',
  '/api/organizations/{organization_id}/invite':
      '/api/v2/organizations/{organization_id}/invite',
  '/api/ownership-groups': '/api/v2/ownership-groups',
  '/api/ownership-groups/transfers/validate':
      '/api/v2/ownership-groups/transfers/validate',
  '/api/ownership-groups/{group_id}': '/api/v2/ownership-groups/{group_id}',
  '/api/ownership-groups/{group_id}/budget/allocate':
      '/api/v2/ownership-groups/{group_id}/budget/allocate',
  '/api/ownership-groups/{group_id}/budget/transfer':
      '/api/v2/ownership-groups/{group_id}/budget/transfer',
  '/api/ownership-groups/{group_id}/clubs':
      '/api/v2/ownership-groups/{group_id}/clubs',
  '/api/platform/mode': '/api/v2/platform/mode',
  '/api/platform/switch': '/api/v2/platform/switch',
  '/api/player-cards/admin/preseeded-regens':
      '/api/v2/player-cards/admin/preseeded-regens',
  '/api/player-cards/admin/preseeded-regens/mint':
      '/api/v2/player-cards/admin/preseeded-regens/mint',
  '/api/player-cards/inventory': '/api/v2/player-cards/inventory',
  '/api/player-cards/listings': '/api/v2/player-cards/listings',
  '/api/player-cards/listings/mine': '/api/v2/player-cards/listings/mine',
  '/api/player-cards/listings/{listing_id}/buy':
      '/api/v2/player-cards/listings/{listing_id}/buy',
  '/api/player-cards/listings/{listing_id}/cancel':
      '/api/v2/player-cards/listings/{listing_id}/cancel',
  '/api/player-cards/loans': '/api/v2/player-cards/loans',
  '/api/player-cards/loans/contracts/{loan_contract_id}/return':
      '/api/v2/player-cards/loans/contracts/{loan_contract_id}/return',
  '/api/player-cards/loans/{loan_listing_id}/borrow':
      '/api/v2/player-cards/loans/{loan_listing_id}/borrow',
  '/api/player-cards/marketplace/listings':
      '/api/v2/player-cards/marketplace/listings',
  '/api/player-cards/marketplace/loans':
      '/api/v2/player-cards/marketplace/loans',
  '/api/player-cards/marketplace/loans/contracts':
      '/api/v2/player-cards/marketplace/loans/contracts',
  '/api/player-cards/marketplace/loans/contracts/{contract_id}/return':
      '/api/v2/player-cards/marketplace/loans/contracts/{contract_id}/return',
  '/api/player-cards/marketplace/loans/contracts/{contract_id}/settle':
      '/api/v2/player-cards/marketplace/loans/contracts/{contract_id}/settle',
  '/api/player-cards/marketplace/loans/negotiations/{negotiation_id}/accept':
      '/api/v2/player-cards/marketplace/loans/negotiations/{negotiation_id}/accept',
  '/api/player-cards/marketplace/loans/negotiations/{negotiation_id}/counter':
      '/api/v2/player-cards/marketplace/loans/negotiations/{negotiation_id}/counter',
  '/api/player-cards/marketplace/loans/{listing_id}/cancel':
      '/api/v2/player-cards/marketplace/loans/{listing_id}/cancel',
  '/api/player-cards/marketplace/loans/{listing_id}/negotiations':
      '/api/v2/player-cards/marketplace/loans/{listing_id}/negotiations',
  '/api/player-cards/marketplace/sales':
      '/api/v2/player-cards/marketplace/sales',
  '/api/player-cards/marketplace/sales/{listing_id}/buy':
      '/api/v2/player-cards/marketplace/sales/{listing_id}/buy',
  '/api/player-cards/marketplace/sales/{listing_id}/cancel':
      '/api/v2/player-cards/marketplace/sales/{listing_id}/cancel',
  '/api/player-cards/marketplace/swaps':
      '/api/v2/player-cards/marketplace/swaps',
  '/api/player-cards/marketplace/swaps/{listing_id}/cancel':
      '/api/v2/player-cards/marketplace/swaps/{listing_id}/cancel',
  '/api/player-cards/marketplace/swaps/{listing_id}/execute':
      '/api/v2/player-cards/marketplace/swaps/{listing_id}/execute',
  '/api/player-cards/players': '/api/v2/player-cards/players',
  '/api/player-cards/players/{player_id}':
      '/api/v2/player-cards/players/{player_id}',
  '/api/player-cards/starter-rental': '/api/v2/player-cards/starter-rental',
  '/api/player-cards/watchlist': '/api/v2/player-cards/watchlist',
  '/api/player-cards/watchlist/{watchlist_id}':
      '/api/v2/player-cards/watchlist/{watchlist_id}',
  '/api/player-history': '/api/v2/player-history',
  '/api/player-history/{player_id}': '/api/v2/player-history/{player_id}',
  '/api/player-import/youth-prospects/me':
      '/api/v2/player-import/youth-prospects/me',
  '/api/player-import/youth-prospects/{club_id}':
      '/api/v2/player-import/youth-prospects/{club_id}',
  '/api/players': '/api/v2/players',
  '/api/players/events': '/api/v2/players/events',
  '/api/players/markets': '/api/v2/players/markets',
  '/api/players/match': '/api/v2/players/match',
  '/api/players/me/match-profile': '/api/v2/players/me/match-profile',
  '/api/players/me/shares/holdings': '/api/v2/players/me/shares/holdings',
  '/api/players/real-universe': '/api/v2/players/real-universe',
  '/api/players/real-universe/search': '/api/v2/players/real-universe/search',
  '/api/players/real-universe/{player_id}':
      '/api/v2/players/real-universe/{player_id}',
  '/api/players/summaries/recent': '/api/v2/players/summaries/recent',
  '/api/players/{player_id}': '/api/v2/players/{player_id}',
  '/api/players/{player_id}/agency': '/api/v2/players/{player_id}/agency',
  '/api/players/{player_id}/agency/contract-decision':
      '/api/v2/players/{player_id}/agency/contract-decision',
  '/api/players/{player_id}/agency/transfer-decision':
      '/api/v2/players/{player_id}/agency/transfer-decision',
  '/api/players/{player_id}/availability':
      '/api/v2/players/{player_id}/availability',
  '/api/players/{player_id}/avatar': '/api/v2/players/{player_id}/avatar',
  '/api/players/{player_id}/career': '/api/v2/players/{player_id}/career',
  '/api/players/{player_id}/career-events':
      '/api/v2/players/{player_id}/career-events',
  '/api/players/{player_id}/career/summary':
      '/api/v2/players/{player_id}/career/summary',
  '/api/players/{player_id}/contracts': '/api/v2/players/{player_id}/contracts',
  '/api/players/{player_id}/contracts/summary':
      '/api/v2/players/{player_id}/contracts/summary',
  '/api/players/{player_id}/contracts/{contract_id}/renew':
      '/api/v2/players/{player_id}/contracts/{contract_id}/renew',
  '/api/players/{player_id}/dna': '/api/v2/players/{player_id}/dna',
  '/api/players/{player_id}/events': '/api/v2/players/{player_id}/events',
  '/api/players/{player_id}/injuries': '/api/v2/players/{player_id}/injuries',
  '/api/players/{player_id}/injuries/{injury_id}/recover':
      '/api/v2/players/{player_id}/injuries/{injury_id}/recover',
  '/api/players/{player_id}/interviews':
      '/api/v2/players/{player_id}/interviews',
  '/api/players/{player_id}/lifecycle-snapshot':
      '/api/v2/players/{player_id}/lifecycle-snapshot',
  '/api/players/{player_id}/overview': '/api/v2/players/{player_id}/overview',
  '/api/players/{player_id}/personality':
      '/api/v2/players/{player_id}/personality',
  '/api/players/{player_id}/regen': '/api/v2/players/{player_id}/regen',
  '/api/players/{player_id}/regen/big-club-approaches':
      '/api/v2/players/{player_id}/regen/big-club-approaches',
  '/api/players/{player_id}/regen/contract-offers/quote':
      '/api/v2/players/{player_id}/regen/contract-offers/quote',
  '/api/players/{player_id}/regen/offer-market':
      '/api/v2/players/{player_id}/regen/offer-market',
  '/api/players/{player_id}/regen/pressure-resolution':
      '/api/v2/players/{player_id}/regen/pressure-resolution',
  '/api/players/{player_id}/regen/special-training':
      '/api/v2/players/{player_id}/regen/special-training',
  '/api/players/{player_id}/regen/transfer-listing':
      '/api/v2/players/{player_id}/regen/transfer-listing',
  '/api/players/{player_id}/rivalries': '/api/v2/players/{player_id}/rivalries',
  '/api/players/{player_id}/shares/buy':
      '/api/v2/players/{player_id}/shares/buy',
  '/api/players/{player_id}/shares/dividends':
      '/api/v2/players/{player_id}/shares/dividends',
  '/api/players/{player_id}/shares/events':
      '/api/v2/players/{player_id}/shares/events',
  '/api/players/{player_id}/shares/issue':
      '/api/v2/players/{player_id}/shares/issue',
  '/api/players/{player_id}/shares/market':
      '/api/v2/players/{player_id}/shares/market',
  '/api/players/{player_id}/shares/performance':
      '/api/v2/players/{player_id}/shares/performance',
  '/api/players/{player_id}/shares/sell':
      '/api/v2/players/{player_id}/shares/sell',
  '/api/players/{player_id}/story': '/api/v2/players/{player_id}/story',
  '/api/players/{player_id}/summary': '/api/v2/players/{player_id}/summary',
  '/api/policies/acceptances': '/api/v2/policies/acceptances',
  '/api/policies/country/{country_code}':
      '/api/v2/policies/country/{country_code}',
  '/api/policies/documents': '/api/v2/policies/documents',
  '/api/policies/documents/{document_key}':
      '/api/v2/policies/documents/{document_key}',
  '/api/policies/me/acceptances': '/api/v2/policies/me/acceptances',
  '/api/policies/me/compliance': '/api/v2/policies/me/compliance',
  '/api/policies/me/region': '/api/v2/policies/me/region',
  '/api/policies/me/requirements': '/api/v2/policies/me/requirements',
  '/api/portfolio': '/api/v2/portfolio',
  '/api/portfolio/snapshot': '/api/v2/portfolio/snapshot',
  '/api/portfolio/summary': '/api/v2/portfolio/summary',
  '/api/portfolios/me': '/api/v2/portfolios/me',
  '/api/predictions': '/api/v2/predictions',
  '/api/predictions/leaderboard': '/api/v2/predictions/leaderboard',
  '/api/pundits/matches/{match_key}': '/api/v2/pundits/matches/{match_key}',
  '/api/rankings/clubs': '/api/v2/rankings/clubs',
  '/api/rankings/global': '/api/v2/rankings/global',
  '/api/rankings/players': '/api/v2/rankings/players',
  '/api/ready': '/ready',
  '/api/real-world/events': '/api/v2/real-world/events',
  '/api/real-world/hybrid-players': '/api/v2/real-world/hybrid-players',
  '/api/real-world/normalize': '/api/v2/real-world/normalize',
  '/api/real-world/players': '/api/v2/real-world/players',
  '/api/real-world/players/{real_player_id}':
      '/api/v2/real-world/players/{real_player_id}',
  '/api/real-world/providers': '/api/v2/real-world/providers',
  '/api/real-world/settings/me': '/api/v2/real-world/settings/me',
  '/api/realtime/matches/{match_id}/gateway':
      '/api/v2/realtime/matches/{match_id}/gateway',
  '/api/realtime/matches/{match_id}/stream':
      '/api/v2/realtime/matches/{match_id}/stream',
  '/api/realtime/status': '/api/v2/realtime/status',
  '/api/realtime/stream': '/api/v2/realtime/stream',
  '/api/realtime/wallet/gateway': '/api/v2/realtime/wallet/gateway',
  '/api/realtime/wallet/stream': '/api/v2/realtime/wallet/stream',
  '/api/referrals/attribution': '/api/v2/referrals/attribution',
  '/api/referrals/me/invites': '/api/v2/referrals/me/invites',
  '/api/referrals/me/rewards': '/api/v2/referrals/me/rewards',
  '/api/referrals/me/summary': '/api/v2/referrals/me/summary',
  '/api/referrals/share-codes': '/api/v2/referrals/share-codes',
  '/api/referrals/share-codes/me': '/api/v2/referrals/share-codes/me',
  '/api/referrals/share-codes/{code}/redeem':
      '/api/v2/referrals/share-codes/{code}/redeem',
  '/api/referrals/share-codes/{share_code_id}':
      '/api/v2/referrals/share-codes/{share_code_id}',
  '/api/regen-hype': '/api/v2/regen-hype',
  '/api/regen-universe/achievements': '/api/v2/regen-universe/achievements',
  '/api/regen-universe/awards': '/api/v2/regen-universe/awards',
  '/api/regen-universe/bloodlines': '/api/v2/regen-universe/bloodlines',
  '/api/regen-universe/hall-of-fame': '/api/v2/regen-universe/hall-of-fame',
  '/api/regen-universe/national-regens':
      '/api/v2/regen-universe/national-regens',
  '/api/regen-universe/player/{player_id}':
      '/api/v2/regen-universe/player/{player_id}',
  '/api/regen-universe/players/{player_id}':
      '/api/v2/regen-universe/players/{player_id}',
  '/api/regen-universe/players/{player_id}/timeline':
      '/api/v2/regen-universe/players/{player_id}/timeline',
  '/api/regen-universe/rankings': '/api/v2/regen-universe/rankings',
  '/api/regen-universe/rising-stars': '/api/v2/regen-universe/rising-stars',
  '/api/regen-universe/scouting-feed': '/api/v2/regen-universe/scouting-feed',
  '/api/regen-universe/seasons': '/api/v2/regen-universe/seasons',
  '/api/regen-universe/tracking': '/api/v2/regen-universe/tracking',
  '/api/regen-universe/youth-tournaments':
      '/api/v2/regen-universe/youth-tournaments',
  '/api/regen-universe/youth-tournaments/{tournament_id}':
      '/api/v2/regen-universe/youth-tournaments/{tournament_id}',
  '/api/regens/awards': '/api/v2/regens/awards',
  '/api/regens/awards/{award_id}/vote': '/api/v2/regens/awards/{award_id}/vote',
  '/api/regens/creation-orders': '/api/v2/regens/creation-orders',
  '/api/regens/creation-orders/{order_id}':
      '/api/v2/regens/creation-orders/{order_id}',
  '/api/regens/creation-orders/{order_id}/generate-after-payment':
      '/api/v2/regens/creation-orders/{order_id}/generate-after-payment',
  '/api/regens/creation-orders/{order_id}/pay-with-wallet':
      '/api/v2/regens/creation-orders/{order_id}/pay-with-wallet',
  '/api/regens/feed': '/api/v2/regens/feed',
  '/api/regens/jobs/{job_name}': '/api/v2/regens/jobs/{job_name}',
  '/api/regens/request-son': '/api/v2/regens/request-son',
  '/api/regens/request-son/options': '/api/v2/regens/request-son/options',
  '/api/regens/rising': '/api/v2/regens/rising',
  '/api/regens/top': '/api/v2/regens/top',
  '/api/regens/{regen_id}/lineage': '/api/v2/regens/{regen_id}/lineage',
  '/api/rent': '/api/v2/rent',
  '/api/replays/countdown/{fixture_id}':
      '/api/v2/replays/countdown/{fixture_id}',
  '/api/replays/me': '/api/v2/replays/me',
  '/api/replays/public/featured': '/api/v2/replays/public/featured',
  '/api/replays/{replay_id}': '/api/v2/replays/{replay_id}',
  '/api/reward-engine/me/settlements': '/api/v2/reward-engine/me/settlements',
  '/api/reward-engine/me/summary': '/api/v2/reward-engine/me/summary',
  '/api/risk-ops/me/aml-cases': '/api/v2/risk-ops/me/aml-cases',
  '/api/risk-ops/me/fraud-cases': '/api/v2/risk-ops/me/fraud-cases',
  '/api/risk-ops/me/overview': '/api/v2/risk-ops/me/overview',
  '/api/risk-ops/me/restrictions': '/api/v2/risk-ops/me/restrictions',
  '/api/risk-ops/me/signals': '/api/v2/risk-ops/me/signals',
  '/api/rivalries/matches': '/api/v2/rivalries/matches',
  '/api/scout/report/{player_id}': '/api/v2/scout/report/{player_id}',
  '/api/scouts': '/api/v2/scouts',
  '/api/scouts/{scout_id}/discover': '/api/v2/scouts/{scout_id}/discover',
  '/api/season-pass': '/api/v2/season-pass',
  '/api/season-pass/claim': '/api/v2/season-pass/claim',
  '/api/season-pass/me': '/api/v2/season-pass/me',
  '/api/season-pass/rewards/{reward_id}/claim':
      '/api/v2/season-pass/rewards/{reward_id}/claim',
  '/api/season/current': '/api/v2/season/current',
  '/api/season/history': '/api/v2/season/history',
  '/api/session/bootstrap': '/api/v2/session/bootstrap',
  '/api/shows/debate': '/api/v2/shows/debate',
  '/api/shows/post-match/{match_id}': '/api/v2/shows/post-match/{match_id}',
  '/api/shows/pre-match/{match_id}': '/api/v2/shows/pre-match/{match_id}',
  '/api/simulation-matchmaking/hosted-competitions/preview':
      '/api/v2/simulation-matchmaking/hosted-competitions/preview',
  '/api/simulation-matchmaking/profiles/{user_id}':
      '/api/v2/simulation-matchmaking/profiles/{user_id}',
  '/api/simulation-matchmaking/quick-game':
      '/api/v2/simulation-matchmaking/quick-game',
  '/api/simulation-matchmaking/quick-tournament':
      '/api/v2/simulation-matchmaking/quick-tournament',
  '/api/social/clubs/{club_id}/community':
      '/api/v2/social/clubs/{club_id}/community',
  '/api/social/clubs/{club_id}/community/messages':
      '/api/v2/social/clubs/{club_id}/community/messages',
  '/api/social/feed': '/api/v2/social/feed',
  '/api/social/follows': '/api/v2/social/follows',
  '/api/social/follows/me': '/api/v2/social/follows/me',
  '/api/social/profile/me': '/api/v2/social/profile/me',
  '/api/social/rivalries/{club_a_id}/{club_b_id}':
      '/api/v2/social/rivalries/{club_a_id}/{club_b_id}',
  '/api/social/rivalries/{club_a_id}/{club_b_id}/banter':
      '/api/v2/social/rivalries/{club_a_id}/{club_b_id}/banter',
  '/api/sponsors': '/api/v2/sponsors',
  '/api/sponsorship/clubs/{club_id}/contracts':
      '/api/v2/sponsorship/clubs/{club_id}/contracts',
  '/api/sponsorship/clubs/{club_id}/dashboard':
      '/api/v2/sponsorship/clubs/{club_id}/dashboard',
  '/api/sponsorship/clubs/{club_id}/offers':
      '/api/v2/sponsorship/clubs/{club_id}/offers',
  '/api/sponsorship/clubs/{club_id}/sponsors':
      '/api/v2/sponsorship/clubs/{club_id}/sponsors',
  '/api/sponsorship/contracts/request': '/api/v2/sponsorship/contracts/request',
  '/api/sponsorship/me/leads': '/api/v2/sponsorship/me/leads',
  '/api/sponsorship/packages': '/api/v2/sponsorship/packages',
  '/api/sponsorship/placements': '/api/v2/sponsorship/placements',
  '/api/story-feed': '/api/v2/story-feed',
  '/api/story-feed/digest': '/api/v2/story-feed/digest',
  '/api/streamer-tournaments': '/api/v2/streamer-tournaments',
  '/api/streamer-tournaments/mine': '/api/v2/streamer-tournaments/mine',
  '/api/streamer-tournaments/{tournament_id}':
      '/api/v2/streamer-tournaments/{tournament_id}',
  '/api/streamer-tournaments/{tournament_id}/invites':
      '/api/v2/streamer-tournaments/{tournament_id}/invites',
  '/api/streamer-tournaments/{tournament_id}/join':
      '/api/v2/streamer-tournaments/{tournament_id}/join',
  '/api/streamer-tournaments/{tournament_id}/publish':
      '/api/v2/streamer-tournaments/{tournament_id}/publish',
  '/api/streamer-tournaments/{tournament_id}/rewards':
      '/api/v2/streamer-tournaments/{tournament_id}/rewards',
  '/api/surveillance/circular-trade-alerts':
      '/api/v2/surveillance/circular-trade-alerts',
  '/api/surveillance/holder-concentration-alerts':
      '/api/v2/surveillance/holder-concentration-alerts',
  '/api/surveillance/suspicious-clusters':
      '/api/v2/surveillance/suspicious-clusters',
  '/api/surveillance/suspicious-players':
      '/api/v2/surveillance/suspicious-players',
  '/api/surveillance/thin-market-alerts':
      '/api/v2/surveillance/thin-market-alerts',
  '/api/sync/update': '/api/v2/sync/update',
  '/api/tickets/attendance/{match_id}/react':
      '/api/v2/tickets/attendance/{match_id}/react',
  '/api/tickets/buy': '/api/v2/tickets/buy',
  '/api/tickets/event/{match_id}': '/api/v2/tickets/event/{match_id}',
  '/api/tickets/resell': '/api/v2/tickets/resell',
  '/api/tickets/waitlist': '/api/v2/tickets/waitlist',
  '/api/tournaments': '/api/v2/tournaments',
  '/api/tournaments/{tournament_id}': '/api/v2/tournaments/{tournament_id}',
  '/api/tournaments/{tournament_id}/advance':
      '/api/v2/tournaments/{tournament_id}/advance',
  '/api/tournaments/{tournament_id}/join':
      '/api/v2/tournaments/{tournament_id}/join',
  '/api/tournaments/{tournament_id}/matches/{match_id}/result':
      '/api/v2/tournaments/{tournament_id}/matches/{match_id}/result',
  '/api/trader/markets': '/api/v2/trader/markets',
  '/api/trader/orders': '/api/v2/trader/orders',
  '/api/trader/overview': '/api/v2/trader/overview',
  '/api/trader/p2p': '/api/v2/trader/p2p',
  '/api/trader/security/totp/setup': '/api/v2/trader/security/totp/setup',
  '/api/trader/watchlist': '/api/v2/trader/watchlist',
  '/api/transfer-market/clubs/{club_id}/team-dynamics':
      '/api/v2/transfer-market/clubs/{club_id}/team-dynamics',
  '/api/transfer-market/coaches/{club_id}/demands':
      '/api/v2/transfer-market/coaches/{club_id}/demands',
  '/api/transfer-market/coaches/{club_id}/profile':
      '/api/v2/transfer-market/coaches/{club_id}/profile',
  '/api/transfer-market/jobs/run': '/api/v2/transfer-market/jobs/run',
  '/api/transfer-market/listings': '/api/v2/transfer-market/listings',
  '/api/transfer-market/listings/{listing_id}':
      '/api/v2/transfer-market/listings/{listing_id}',
  '/api/transfer-market/listings/{listing_id}/bids':
      '/api/v2/transfer-market/listings/{listing_id}/bids',
  '/api/transfer-market/listings/{listing_id}/close':
      '/api/v2/transfer-market/listings/{listing_id}/close',
  '/api/transfer-market/listings/{listing_id}/contract-offer':
      '/api/v2/transfer-market/listings/{listing_id}/contract-offer',
  '/api/transfer-market/listings/{listing_id}/negotiation':
      '/api/v2/transfer-market/listings/{listing_id}/negotiation',
  '/api/transfer-market/listings/{listing_id}/stream':
      '/api/v2/transfer-market/listings/{listing_id}/stream',
  '/api/transfer-market/players/{player_id}/decision-profile':
      '/api/v2/transfer-market/players/{player_id}/decision-profile',
  '/api/transfer-market/watchlist': '/api/v2/transfer-market/watchlist',
  '/api/transfers/windows': '/api/v2/transfers/windows',
  '/api/transfers/windows/{window_id}': '/api/v2/transfers/windows/{window_id}',
  '/api/transfers/windows/{window_id}/bids':
      '/api/v2/transfers/windows/{window_id}/bids',
  '/api/transfers/windows/{window_id}/bids/{bid_id}/accept':
      '/api/v2/transfers/windows/{window_id}/bids/{bid_id}/accept',
  '/api/transfers/windows/{window_id}/bids/{bid_id}/reject':
      '/api/v2/transfers/windows/{window_id}/bids/{bid_id}/reject',
  '/api/transfers/windows/{window_id}/players/{player_id}/regen-bid-evaluations':
      '/api/v2/transfers/windows/{window_id}/players/{player_id}/regen-bid-evaluations',
  '/api/transfers/windows/{window_id}/players/{player_id}/resolve-regen-bid':
      '/api/v2/transfers/windows/{window_id}/players/{player_id}/resolve-regen-bid',
  '/api/trust/me': '/api/v2/trust/me',
  '/api/trust/{user_id}': '/api/v2/trust/{user_id}',
  '/api/ultimate-league/competitors/{competitor_id}':
      '/api/v2/ultimate-league/competitors/{competitor_id}',
  '/api/ultimate-league/matches/result':
      '/api/v2/ultimate-league/matches/result',
  '/api/ultimate-league/matchmaking/batch':
      '/api/v2/ultimate-league/matchmaking/batch',
  '/api/ultimate-league/standings/{tier}':
      '/api/v2/ultimate-league/standings/{tier}',
  '/api/ultimate-league/tactical-presets':
      '/api/v2/ultimate-league/tactical-presets',
  '/api/ultimate-league/tactical-presets/{preset_id}/purchase':
      '/api/v2/ultimate-league/tactical-presets/{preset_id}/purchase',
  '/api/ultimate-league/tiers': '/api/v2/ultimate-league/tiers',
  '/api/ultimate-league/tournaments': '/api/v2/ultimate-league/tournaments',
  '/api/ultimate-league/tournaments/{tournament_id}':
      '/api/v2/ultimate-league/tournaments/{tournament_id}',
  '/api/ultimate-league/tournaments/{tournament_id}/payouts/preview':
      '/api/v2/ultimate-league/tournaments/{tournament_id}/payouts/preview',
  '/api/users/me': '/api/v2/users/me',
  '/api/users/me/profile': '/api/v2/users/me/profile',
  '/api/users/suggestions': '/api/v2/users/suggestions',
  '/api/users/{user_id}/followers': '/api/v2/users/{user_id}/followers',
  '/api/users/{user_id}/following': '/api/v2/users/{user_id}/following',
  '/api/v1/academy': '/api/v2/academy',
  '/api/v1/academy/awards': '/api/v2/academy/awards',
  '/api/v1/academy/fixtures': '/api/v2/academy/fixtures',
  '/api/v1/academy/generate': '/api/v2/academy/generate',
  '/api/v1/academy/promote/{player_id}': '/api/v2/academy/promote/{player_id}',
  '/api/v1/academy/qualification': '/api/v2/academy/qualification',
  '/api/v1/academy/registration': '/api/v2/academy/registration',
  '/api/v1/academy/season-summary': '/api/v2/academy/season-summary',
  '/api/v1/academy/standings': '/api/v2/academy/standings',
  '/api/v1/admin-engine/bootstrap': '/api/v2/admin-engine/bootstrap',
  '/api/v1/admin/access': '/api/v2/admin/access',
  '/api/v1/admin/access/permissions': '/api/v2/admin/access/permissions',
  '/api/v1/admin/access/{user_id}/permissions':
      '/api/v2/admin/access/{user_id}/permissions',
  '/api/v1/admin/admin-engine/calendar-rules':
      '/api/v2/admin/admin-engine/calendar-rules',
  '/api/v1/admin/admin-engine/feature-flags':
      '/api/v2/admin/admin-engine/feature-flags',
  '/api/v1/admin/admin-engine/reward-rules':
      '/api/v2/admin/admin-engine/reward-rules',
  '/api/v1/admin/admin-engine/schedule-preview':
      '/api/v2/admin/admin-engine/schedule-preview',
  '/api/v1/admin/analytics/agent-learning':
      '/api/v2/admin/analytics/agent-learning',
  '/api/v1/admin/analytics/anomalies': '/api/v2/admin/analytics/anomalies',
  '/api/v1/admin/analytics/funnels': '/api/v2/admin/analytics/funnels',
  '/api/v1/admin/analytics/match-outcomes':
      '/api/v2/admin/analytics/match-outcomes',
  '/api/v1/admin/analytics/player-matching':
      '/api/v2/admin/analytics/player-matching',
  '/api/v1/admin/analytics/player-matching/recompute-weights':
      '/api/v2/admin/analytics/player-matching/recompute-weights',
  '/api/v1/admin/analytics/price-predictions':
      '/api/v2/admin/analytics/price-predictions',
  '/api/v1/admin/analytics/summary': '/api/v2/admin/analytics/summary',
  '/api/v1/admin/analytics/user-segments':
      '/api/v2/admin/analytics/user-segments',
  '/api/v1/admin/ban-user': '/api/v2/admin/ban-user',
  '/api/v1/admin/broadcast-rights/jobs/run':
      '/api/v2/admin/broadcast-rights/jobs/run',
  '/api/v1/admin/calendar-engine/events':
      '/api/v2/admin/calendar-engine/events',
  '/api/v1/admin/calendar-engine/hosted-competitions/{competition_id}/launch':
      '/api/v2/admin/calendar-engine/hosted-competitions/{competition_id}/launch',
  '/api/v1/admin/calendar-engine/national-competitions/{competition_id}/launch':
      '/api/v2/admin/calendar-engine/national-competitions/{competition_id}/launch',
  '/api/v1/admin/calendar-engine/seasons':
      '/api/v2/admin/calendar-engine/seasons',
  '/api/v1/admin/club-infra/seed': '/api/v2/admin/club-infra/seed',
  '/api/v1/admin/clubs/academy-analytics':
      '/api/v2/admin/clubs/academy-analytics',
  '/api/v1/admin/clubs/analytics': '/api/v2/admin/clubs/analytics',
  '/api/v1/admin/clubs/finance-analytics':
      '/api/v2/admin/clubs/finance-analytics',
  '/api/v1/admin/clubs/ops-summary': '/api/v2/admin/clubs/ops-summary',
  '/api/v1/admin/clubs/scouting-analytics':
      '/api/v2/admin/clubs/scouting-analytics',
  '/api/v1/admin/clubs/sponsorship-analytics':
      '/api/v2/admin/clubs/sponsorship-analytics',
  '/api/v1/admin/clubs/summary': '/api/v2/admin/clubs/summary',
  '/api/v1/admin/clubs/{club_id}': '/api/v2/admin/clubs/{club_id}',
  '/api/v1/admin/clubs/{club_id}/moderate-branding':
      '/api/v2/admin/clubs/{club_id}/moderate-branding',
  '/api/v1/admin/competitions': '/api/v2/admin/competitions',
  '/api/v1/admin/competitions/reminders/dispatch':
      '/api/v2/admin/competitions/reminders/dispatch',
  '/api/v1/admin/competitive-integrity/matches/{match_id}/validation':
      '/api/v2/admin/competitive-integrity/matches/{match_id}/validation',
  '/api/v1/admin/competitive-integrity/workers/run-once':
      '/api/v2/admin/competitive-integrity/workers/run-once',
  '/api/v1/admin/config/liquidity-bands':
      '/api/v2/admin/config/liquidity-bands',
  '/api/v1/admin/config/player-card-market-integrity':
      '/api/v2/admin/config/player-card-market-integrity',
  '/api/v1/admin/config/supply-tiers': '/api/v2/admin/config/supply-tiers',
  '/api/v1/admin/config/suspicion-thresholds':
      '/api/v2/admin/config/suspicion-thresholds',
  '/api/v1/admin/config/value-controls': '/api/v2/admin/config/value-controls',
  '/api/v1/admin/config/value-controls/audits':
      '/api/v2/admin/config/value-controls/audits',
  '/api/v1/admin/config/value-controls/integrity/candidates':
      '/api/v2/admin/config/value-controls/integrity/candidates',
  '/api/v1/admin/config/value-controls/players/{player_id}':
      '/api/v2/admin/config/value-controls/players/{player_id}',
  '/api/v1/admin/config/value-controls/preview/{player_id}':
      '/api/v2/admin/config/value-controls/preview/{player_id}',
  '/api/v1/admin/config/value-controls/recompute':
      '/api/v2/admin/config/value-controls/recompute',
  '/api/v1/admin/config/value-controls/run-history':
      '/api/v2/admin/config/value-controls/run-history',
  '/api/v1/admin/creator-campaigns/{campaign_id}/metrics':
      '/api/v2/admin/creator-campaigns/{campaign_id}/metrics',
  '/api/v1/admin/creator/applications': '/api/v2/admin/creator/applications',
  '/api/v1/admin/creator/applications/{application_id}/approve':
      '/api/v2/admin/creator/applications/{application_id}/approve',
  '/api/v1/admin/creator/applications/{application_id}/reject':
      '/api/v2/admin/creator/applications/{application_id}/reject',
  '/api/v1/admin/creator/applications/{application_id}/request-verification':
      '/api/v2/admin/creator/applications/{application_id}/request-verification',
  '/api/v1/admin/creator/cards/assign': '/api/v2/admin/creator/cards/assign',
  '/api/v1/admin/creator/dashboard': '/api/v2/admin/creator/dashboard',
  '/api/v1/admin/creator/fan-share-market/control':
      '/api/v2/admin/creator/fan-share-market/control',
  '/api/v1/admin/discovery/featured-rails':
      '/api/v2/admin/discovery/featured-rails',
  '/api/v1/admin/disputes': '/api/v2/admin/disputes',
  '/api/v1/admin/disputes/{dispute_id}/assign':
      '/api/v2/admin/disputes/{dispute_id}/assign',
  '/api/v1/admin/disputes/{dispute_id}/status':
      '/api/v2/admin/disputes/{dispute_id}/status',
  '/api/v1/admin/economy/burn-events': '/api/v2/admin/economy/burn-events',
  '/api/v1/admin/economy/fx-rates': '/api/v2/admin/economy/fx-rates',
  '/api/v1/admin/economy/gift-catalog': '/api/v2/admin/economy/gift-catalog',
  '/api/v1/admin/economy/gift-combo-rules':
      '/api/v2/admin/economy/gift-combo-rules',
  '/api/v1/admin/economy/governor': '/api/v2/admin/economy/governor',
  '/api/v1/admin/economy/governor/apply':
      '/api/v2/admin/economy/governor/apply',
  '/api/v1/admin/economy/governor/evaluate':
      '/api/v2/admin/economy/governor/evaluate',
  '/api/v1/admin/economy/governor/policy':
      '/api/v2/admin/economy/governor/policy',
  '/api/v1/admin/economy/regional-pricing':
      '/api/v2/admin/economy/regional-pricing',
  '/api/v1/admin/economy/revenue-share-rules':
      '/api/v2/admin/economy/revenue-share-rules',
  '/api/v1/admin/economy/service-pricing':
      '/api/v2/admin/economy/service-pricing',
  '/api/v1/admin/fan-predictions/matches/{match_id}/fixture':
      '/api/v2/admin/fan-predictions/matches/{match_id}/fixture',
  '/api/v1/admin/fan-predictions/matches/{match_id}/settlement':
      '/api/v2/admin/fan-predictions/matches/{match_id}/settlement',
  '/api/v1/admin/fan-wars/creator-country-assignments':
      '/api/v2/admin/fan-wars/creator-country-assignments',
  '/api/v1/admin/fan-wars/nations-cup': '/api/v2/admin/fan-wars/nations-cup',
  '/api/v1/admin/fan-wars/nations-cup/{competition_id}/advance':
      '/api/v2/admin/fan-wars/nations-cup/{competition_id}/advance',
  '/api/v1/admin/fan-wars/points': '/api/v2/admin/fan-wars/points',
  '/api/v1/admin/fan-wars/profiles': '/api/v2/admin/fan-wars/profiles',
  '/api/v1/admin/fan-wars/profiles/{profile_id}/rivals/{rival_profile_id}':
      '/api/v2/admin/fan-wars/profiles/{profile_id}/rivals/{rival_profile_id}',
  '/api/v1/admin/federations/run-jobs': '/api/v2/admin/federations/run-jobs',
  '/api/v1/admin/finance/account-controls':
      '/api/v2/admin/finance/account-controls',
  '/api/v1/admin/finance/account-controls/{user_id}':
      '/api/v2/admin/finance/account-controls/{user_id}',
  '/api/v1/admin/finance/control-tower': '/api/v2/admin/finance/control-tower',
  '/api/v1/admin/finance/manual-price-overrides':
      '/api/v2/admin/finance/manual-price-overrides',
  '/api/v1/admin/finance/manual-price-overrides/{asset_type}/{asset_id}':
      '/api/v2/admin/finance/manual-price-overrides/{asset_type}/{asset_id}',
  '/api/v1/admin/finance/match-kill-switches':
      '/api/v2/admin/finance/match-kill-switches',
  '/api/v1/admin/finance/match-kill-switches/{match_id}':
      '/api/v2/admin/finance/match-kill-switches/{match_id}',
  '/api/v1/admin/finance/reconciliation':
      '/api/v2/admin/finance/reconciliation',
  '/api/v1/admin/finance/simulate': '/api/v2/admin/finance/simulate',
  '/api/v1/admin/finance/wallet-protection':
      '/api/v2/admin/finance/wallet-protection',
  '/api/v1/admin/flags': '/api/v2/admin/flags',
  '/api/v1/admin/football-events/categories':
      '/api/v2/admin/football-events/categories',
  '/api/v1/admin/football-events/effects/expire':
      '/api/v2/admin/football-events/effects/expire',
  '/api/v1/admin/football-events/events':
      '/api/v2/admin/football-events/events',
  '/api/v1/admin/football-events/events/import':
      '/api/v2/admin/football-events/events/import',
  '/api/v1/admin/football-events/events/{event_id}/review':
      '/api/v2/admin/football-events/events/{event_id}/review',
  '/api/v1/admin/football-events/events/{event_id}/severity':
      '/api/v2/admin/football-events/events/{event_id}/severity',
  '/api/v1/admin/football-events/rules': '/api/v2/admin/football-events/rules',
  '/api/v1/admin/god-mode/audit-events': '/api/v2/admin/god-mode/audit-events',
  '/api/v1/admin/god-mode/bootstrap': '/api/v2/admin/god-mode/bootstrap',
  '/api/v1/admin/god-mode/commissions': '/api/v2/admin/god-mode/commissions',
  '/api/v1/admin/god-mode/competition-controls':
      '/api/v2/admin/god-mode/competition-controls',
  '/api/v1/admin/god-mode/high-risk-actions':
      '/api/v2/admin/god-mode/high-risk-actions',
  '/api/v1/admin/god-mode/liquidity/interventions':
      '/api/v2/admin/god-mode/liquidity/interventions',
  '/api/v1/admin/god-mode/payment-rails':
      '/api/v2/admin/god-mode/payment-rails',
  '/api/v1/admin/god-mode/payment-rails/health':
      '/api/v2/admin/god-mode/payment-rails/health',
  '/api/v1/admin/god-mode/roles': '/api/v2/admin/god-mode/roles',
  '/api/v1/admin/god-mode/treasury': '/api/v2/admin/god-mode/treasury',
  '/api/v1/admin/god-mode/treasury/dashboard':
      '/api/v2/admin/god-mode/treasury/dashboard',
  '/api/v1/admin/god-mode/treasury/withdrawals':
      '/api/v2/admin/god-mode/treasury/withdrawals',
  '/api/v1/admin/god-mode/withdrawal-controls':
      '/api/v2/admin/god-mode/withdrawal-controls',
  '/api/v1/admin/god-mode/withdrawals': '/api/v2/admin/god-mode/withdrawals',
  '/api/v1/admin/god-mode/withdrawals/summary':
      '/api/v2/admin/god-mode/withdrawals/summary',
  '/api/v1/admin/god-mode/withdrawals/{payout_request_id}':
      '/api/v2/admin/god-mode/withdrawals/{payout_request_id}',
  '/api/v1/admin/governance/proposals/{proposal_id}/status':
      '/api/v2/admin/governance/proposals/{proposal_id}/status',
  '/api/v1/admin/history-engagement/run-workers':
      '/api/v2/admin/history-engagement/run-workers',
  '/api/v1/admin/hosted-competitions': '/api/v2/admin/hosted-competitions',
  '/api/v1/admin/hosted-competitions/seed':
      '/api/v2/admin/hosted-competitions/seed',
  '/api/v1/admin/hosted-competitions/{competition_id}/finalize':
      '/api/v2/admin/hosted-competitions/{competition_id}/finalize',
  '/api/v1/admin/hosted-competitions/{competition_id}/launch':
      '/api/v2/admin/hosted-competitions/{competition_id}/launch',
  '/api/v1/admin/integrity-engine/incidents/{incident_id}/resolve':
      '/api/v2/admin/integrity-engine/incidents/{incident_id}/resolve',
  '/api/v1/admin/integrity-engine/scan': '/api/v2/admin/integrity-engine/scan',
  '/api/v1/admin/jackpot/balance': '/api/v2/admin/jackpot/balance',
  '/api/v1/admin/jackpot/runtime': '/api/v2/admin/jackpot/runtime',
  '/api/v1/admin/jackpot/trigger': '/api/v2/admin/jackpot/trigger',
  '/api/v1/admin/leaderboard/season/archive':
      '/api/v2/admin/leaderboard/season/archive',
  '/api/v1/admin/leaderboard/season/reset':
      '/api/v2/admin/leaderboard/season/reset',
  '/api/v1/admin/managers/audit-log': '/api/v2/admin/managers/audit-log',
  '/api/v1/admin/managers/catalog/{manager_id}/supply':
      '/api/v2/admin/managers/catalog/{manager_id}/supply',
  '/api/v1/admin/managers/competitions': '/api/v2/admin/managers/competitions',
  '/api/v1/admin/managers/competitions/{code}':
      '/api/v2/admin/managers/competitions/{code}',
  '/api/v1/admin/managers/competitions/{code}/orchestrate':
      '/api/v2/admin/managers/competitions/{code}/orchestrate',
  '/api/v1/admin/media-engine/creator-league/clubs/{club_id}/stadium-level':
      '/api/v2/admin/media-engine/creator-league/clubs/{club_id}/stadium-level',
  '/api/v1/admin/media-engine/creator-league/matches/{match_id}/analytics':
      '/api/v2/admin/media-engine/creator-league/matches/{match_id}/analytics',
  '/api/v1/admin/media-engine/creator-league/matches/{match_id}/settlement':
      '/api/v2/admin/media-engine/creator-league/matches/{match_id}/settlement',
  '/api/v1/admin/media-engine/creator-league/stadium-controls':
      '/api/v2/admin/media-engine/creator-league/stadium-controls',
  '/api/v1/admin/media-engine/exports': '/api/v2/admin/media-engine/exports',
  '/api/v1/admin/media-engine/highlights':
      '/api/v2/admin/media-engine/highlights',
  '/api/v1/admin/media-engine/highlights/{storage_key:path}/archive':
      '/api/v2/admin/media-engine/highlights/{storage_key:path}/archive',
  '/api/v1/admin/media-engine/share-exports/{export_id}/revenue-attributions':
      '/api/v2/admin/media-engine/share-exports/{export_id}/revenue-attributions',
  '/api/v1/admin/media-engine/snapshots':
      '/api/v2/admin/media-engine/snapshots',
  '/api/v1/admin/moderation/reports': '/api/v2/admin/moderation/reports',
  '/api/v1/admin/moderation/reports/summary':
      '/api/v2/admin/moderation/reports/summary',
  '/api/v1/admin/moderation/reports/{report_id}/assign':
      '/api/v2/admin/moderation/reports/{report_id}/assign',
  '/api/v1/admin/moderation/reports/{report_id}/resolve':
      '/api/v2/admin/moderation/reports/{report_id}/resolve',
  '/api/v1/admin/national-team-engine/competitions':
      '/api/v2/admin/national-team-engine/competitions',
  '/api/v1/admin/national-team-engine/competitions/seed-defaults':
      '/api/v2/admin/national-team-engine/competitions/seed-defaults',
  '/api/v1/admin/national-team-engine/competitions/{competition_id}/ads':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads',
  '/api/v1/admin/national-team-engine/competitions/{competition_id}/ads/rotate':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads/rotate',
  '/api/v1/admin/national-team-engine/competitions/{competition_id}/ads/{ad_id}':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads/{ad_id}',
  '/api/v1/admin/national-team-engine/competitions/{competition_id}/entries':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/entries',
  '/api/v1/admin/national-team-engine/competitions/{competition_id}/entries/lock':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/entries/lock',
  '/api/v1/admin/national-team-engine/competitions/{competition_id}/lifecycle/advance':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/lifecycle/advance',
  '/api/v1/admin/national-team-engine/competitions/{competition_id}/rentals/cleanup':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/rentals/cleanup',
  '/api/v1/admin/national-team-engine/competitions/{competition_id}/story-events/generate':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/story-events/generate',
  '/api/v1/admin/national-team-engine/competitions/{competition_id}/theme':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/theme',
  '/api/v1/admin/national-team-engine/entries/{entry_id}/squad':
      '/api/v2/admin/national-team-engine/entries/{entry_id}/squad',
  '/api/v1/admin/notifications/announcements':
      '/api/v2/admin/notifications/announcements',
  '/api/v1/admin/ops/alerts': '/api/v2/admin/ops/alerts',
  '/api/v1/admin/ops/audit': '/api/v2/admin/ops/audit',
  '/api/v1/admin/ops/broadcast-expiration':
      '/api/v2/admin/ops/broadcast-expiration',
  '/api/v1/admin/ops/broadcast-revenue': '/api/v2/admin/ops/broadcast-revenue',
  '/api/v1/admin/ops/club-market-valuations':
      '/api/v2/admin/ops/club-market-valuations',
  '/api/v1/admin/ops/dashboard': '/api/v2/admin/ops/dashboard',
  '/api/v1/admin/ops/fan-updates': '/api/v2/admin/ops/fan-updates',
  '/api/v1/admin/ops/identity-evolution':
      '/api/v2/admin/ops/identity-evolution',
  '/api/v1/admin/ops/integrity-scan': '/api/v2/admin/ops/integrity-scan',
  '/api/v1/admin/ops/media-generation': '/api/v2/admin/ops/media-generation',
  '/api/v1/admin/ops/media-retention': '/api/v2/admin/ops/media-retention',
  '/api/v1/admin/ops/national-team-rental-cleanup':
      '/api/v2/admin/ops/national-team-rental-cleanup',
  '/api/v1/admin/ops/ownership-groups/reputation':
      '/api/v2/admin/ops/ownership-groups/reputation',
  '/api/v1/admin/ops/platform-infra': '/api/v2/admin/ops/platform-infra',
  '/api/v1/admin/ops/stadium-ad-rotation':
      '/api/v2/admin/ops/stadium-ad-rotation',
  '/api/v1/admin/ops/tournament-storylines':
      '/api/v2/admin/ops/tournament-storylines',
  '/api/v1/admin/ownership-groups/reputation-cycle':
      '/api/v2/admin/ownership-groups/reputation-cycle',
  '/api/v1/admin/player-import/card-supply':
      '/api/v2/admin/player-import/card-supply',
  '/api/v1/admin/player-import/card-supply/csv':
      '/api/v2/admin/player-import/card-supply/csv',
  '/api/v1/admin/player-import/jobs': '/api/v2/admin/player-import/jobs',
  '/api/v1/admin/player-import/jobs/{job_id}':
      '/api/v2/admin/player-import/jobs/{job_id}',
  '/api/v1/admin/player-import/youth/generate':
      '/api/v2/admin/player-import/youth/generate',
  '/api/v1/admin/policies/country-policies':
      '/api/v2/admin/policies/country-policies',
  '/api/v1/admin/policies/documents': '/api/v2/admin/policies/documents',
  '/api/v1/admin/policies/documents/versions':
      '/api/v2/admin/policies/documents/versions',
  '/api/v1/admin/policies/regions/override':
      '/api/v2/admin/policies/regions/override',
  '/api/v1/admin/real-world/providers': '/api/v2/admin/real-world/providers',
  '/api/v1/admin/real-world/providers/{provider_id}/sync':
      '/api/v2/admin/real-world/providers/{provider_id}/sync',
  '/api/v1/admin/referrals/analytics/summary':
      '/api/v2/admin/referrals/analytics/summary',
  '/api/v1/admin/referrals/attributions':
      '/api/v2/admin/referrals/attributions',
  '/api/v1/admin/referrals/creators': '/api/v2/admin/referrals/creators',
  '/api/v1/admin/referrals/creators/{creator_id}':
      '/api/v2/admin/referrals/creators/{creator_id}',
  '/api/v1/admin/referrals/creators/{creator_id}/reward-freeze':
      '/api/v2/admin/referrals/creators/{creator_id}/reward-freeze',
  '/api/v1/admin/referrals/dashboard': '/api/v2/admin/referrals/dashboard',
  '/api/v1/admin/referrals/flags': '/api/v2/admin/referrals/flags',
  '/api/v1/admin/referrals/leaderboard': '/api/v2/admin/referrals/leaderboard',
  '/api/v1/admin/referrals/rewards/pending':
      '/api/v2/admin/referrals/rewards/pending',
  '/api/v1/admin/referrals/rewards/{reward_id}/review':
      '/api/v2/admin/referrals/rewards/{reward_id}/review',
  '/api/v1/admin/referrals/share-codes': '/api/v2/admin/referrals/share-codes',
  '/api/v1/admin/referrals/share-codes/{share_code_id}':
      '/api/v2/admin/referrals/share-codes/{share_code_id}',
  '/api/v1/admin/referrals/share-codes/{share_code_id}/block':
      '/api/v2/admin/referrals/share-codes/{share_code_id}/block',
  '/api/v1/admin/regen-universe/jobs/dna-evolution':
      '/api/v2/admin/regen-universe/jobs/dna-evolution',
  '/api/v1/admin/regen-universe/jobs/rivalry-detection':
      '/api/v2/admin/regen-universe/jobs/rivalry-detection',
  '/api/v1/admin/regen-universe/jobs/story-regeneration':
      '/api/v2/admin/regen-universe/jobs/story-regeneration',
  '/api/v1/admin/regen-universe/jobs/tournament-scheduling':
      '/api/v2/admin/regen-universe/jobs/tournament-scheduling',
  '/api/v1/admin/regen-universe/national-regens/preseed':
      '/api/v2/admin/regen-universe/national-regens/preseed',
  '/api/v1/admin/regen-universe/players/{player_id}/portrait/ban':
      '/api/v2/admin/regen-universe/players/{player_id}/portrait/ban',
  '/api/v1/admin/regen-universe/players/{player_id}/portrait/override':
      '/api/v2/admin/regen-universe/players/{player_id}/portrait/override',
  '/api/v1/admin/regen-universe/players/{player_id}/portrait/regenerate':
      '/api/v2/admin/regen-universe/players/{player_id}/portrait/regenerate',
  '/api/v1/admin/regen-universe/seasons':
      '/api/v2/admin/regen-universe/seasons',
  '/api/v1/admin/regen-universe/seasons/{season_id}/close':
      '/api/v2/admin/regen-universe/seasons/{season_id}/close',
  '/api/v1/admin/regen-universe/seasons/{season_id}/evolution':
      '/api/v2/admin/regen-universe/seasons/{season_id}/evolution',
  '/api/v1/admin/regen-universe/youth-tournaments':
      '/api/v2/admin/regen-universe/youth-tournaments',
  '/api/v1/admin/reward-engine/promo-pool/credits':
      '/api/v2/admin/reward-engine/promo-pool/credits',
  '/api/v1/admin/reward-engine/settlements':
      '/api/v2/admin/reward-engine/settlements',
  '/api/v1/admin/risk-ops/actions': '/api/v2/admin/risk-ops/actions',
  '/api/v1/admin/risk-ops/actions/{action_id}/release':
      '/api/v2/admin/risk-ops/actions/{action_id}/release',
  '/api/v1/admin/risk-ops/aml-cases': '/api/v2/admin/risk-ops/aml-cases',
  '/api/v1/admin/risk-ops/audit-logs': '/api/v2/admin/risk-ops/audit-logs',
  '/api/v1/admin/risk-ops/cases/{case_type}/{case_id}/resolve':
      '/api/v2/admin/risk-ops/cases/{case_type}/{case_id}/resolve',
  '/api/v1/admin/risk-ops/evaluate': '/api/v2/admin/risk-ops/evaluate',
  '/api/v1/admin/risk-ops/fraud-cases': '/api/v2/admin/risk-ops/fraud-cases',
  '/api/v1/admin/risk-ops/overview': '/api/v2/admin/risk-ops/overview',
  '/api/v1/admin/risk-ops/scan': '/api/v2/admin/risk-ops/scan',
  '/api/v1/admin/risk-ops/signals': '/api/v2/admin/risk-ops/signals',
  '/api/v1/admin/risk-ops/system-events':
      '/api/v2/admin/risk-ops/system-events',
  '/api/v1/admin/sponsorship/analytics': '/api/v2/admin/sponsorship/analytics',
  '/api/v1/admin/sponsorship/categories/{category}':
      '/api/v2/admin/sponsorship/categories/{category}',
  '/api/v1/admin/sponsorship/contracts/{contract_id}/review':
      '/api/v2/admin/sponsorship/contracts/{contract_id}/review',
  '/api/v1/admin/sponsorship/contracts/{contract_id}/settle-next':
      '/api/v2/admin/sponsorship/contracts/{contract_id}/settle-next',
  '/api/v1/admin/sponsorship/offers': '/api/v2/admin/sponsorship/offers',
  '/api/v1/admin/sponsorship/offers/{offer_id}/assign':
      '/api/v2/admin/sponsorship/offers/{offer_id}/assign',
  '/api/v1/admin/sponsorship/offers/{offer_id}/rule':
      '/api/v2/admin/sponsorship/offers/{offer_id}/rule',
  '/api/v1/admin/sponsorship/packages': '/api/v2/admin/sponsorship/packages',
  '/api/v1/admin/story-feed': '/api/v2/admin/story-feed',
  '/api/v1/admin/streamer-tournaments/policy':
      '/api/v2/admin/streamer-tournaments/policy',
  '/api/v1/admin/streamer-tournaments/risk-signals':
      '/api/v2/admin/streamer-tournaments/risk-signals',
  '/api/v1/admin/streamer-tournaments/risk-signals/{signal_id}/review':
      '/api/v2/admin/streamer-tournaments/risk-signals/{signal_id}/review',
  '/api/v1/admin/streamer-tournaments/{tournament_id}/review':
      '/api/v2/admin/streamer-tournaments/{tournament_id}/review',
  '/api/v1/admin/streamer-tournaments/{tournament_id}/settle':
      '/api/v2/admin/streamer-tournaments/{tournament_id}/settle',
  '/api/v1/admin/treasury/bank-accounts':
      '/api/v2/admin/treasury/bank-accounts',
  '/api/v1/admin/treasury/bank-accounts/{account_id}':
      '/api/v2/admin/treasury/bank-accounts/{account_id}',
  '/api/v1/admin/treasury/dashboard': '/api/v2/admin/treasury/dashboard',
  '/api/v1/admin/treasury/deposits': '/api/v2/admin/treasury/deposits',
  '/api/v1/admin/treasury/deposits/{deposit_id}/confirm':
      '/api/v2/admin/treasury/deposits/{deposit_id}/confirm',
  '/api/v1/admin/treasury/deposits/{deposit_id}/reject':
      '/api/v2/admin/treasury/deposits/{deposit_id}/reject',
  '/api/v1/admin/treasury/deposits/{deposit_id}/review':
      '/api/v2/admin/treasury/deposits/{deposit_id}/review',
  '/api/v1/admin/treasury/disputes': '/api/v2/admin/treasury/disputes',
  '/api/v1/admin/treasury/disputes/{dispute_id}':
      '/api/v2/admin/treasury/disputes/{dispute_id}',
  '/api/v1/admin/treasury/disputes/{dispute_id}/messages':
      '/api/v2/admin/treasury/disputes/{dispute_id}/messages',
  '/api/v1/admin/treasury/kyc': '/api/v2/admin/treasury/kyc',
  '/api/v1/admin/treasury/kyc/{profile_id}/review':
      '/api/v2/admin/treasury/kyc/{profile_id}/review',
  '/api/v1/admin/treasury/settings': '/api/v2/admin/treasury/settings',
  '/api/v1/admin/treasury/withdrawal-batches':
      '/api/v2/admin/treasury/withdrawal-batches',
  '/api/v1/admin/treasury/withdrawals': '/api/v2/admin/treasury/withdrawals',
  '/api/v1/admin/treasury/withdrawals/{withdrawal_id}/reviews':
      '/api/v2/admin/treasury/withdrawals/{withdrawal_id}/reviews',
  '/api/v1/admin/treasury/withdrawals/{withdrawal_id}/status':
      '/api/v2/admin/treasury/withdrawals/{withdrawal_id}/status',
  '/api/v1/admin/wallets/market-topups': '/api/v2/admin/wallets/market-topups',
  '/api/v1/admin/wallets/market-topups/quote':
      '/api/v2/admin/wallets/market-topups/quote',
  '/api/v1/admin/wallets/market-topups/{topup_id}/status':
      '/api/v2/admin/wallets/market-topups/{topup_id}/status',
  '/api/v1/admin/wallets/purchase-orders':
      '/api/v2/admin/wallets/purchase-orders',
  '/api/v1/admin/wallets/purchase-orders/{order_id}/status':
      '/api/v2/admin/wallets/purchase-orders/{order_id}/status',
  '/api/v1/admin/world/clubs/{club_id}/context':
      '/api/v2/admin/world/clubs/{club_id}/context',
  '/api/v1/admin/world/cultures/{culture_key}':
      '/api/v2/admin/world/cultures/{culture_key}',
  '/api/v1/admin/world/narratives/{narrative_slug}':
      '/api/v2/admin/world/narratives/{narrative_slug}',
  '/api/v1/ads/create': '/api/v2/ads/create',
  '/api/v1/ads/performance': '/api/v2/ads/performance',
  '/api/v1/agents': '/api/v2/agents',
  '/api/v1/agents/config': '/api/v2/agents/config',
  '/api/v1/agents/performance': '/api/v2/agents/performance',
  '/api/v1/agents/run': '/api/v2/agents/run',
  '/api/v1/agents/summary': '/api/v2/agents/summary',
  '/api/v1/ai-manager/autopilot/live-decision':
      '/api/v2/ai-manager/autopilot/live-decision',
  '/api/v1/ai-manager/autopilot/run': '/api/v2/ai-manager/autopilot/run',
  '/api/v1/ai-manager/economy/reward-preview':
      '/api/v2/ai-manager/economy/reward-preview',
  '/api/v1/ai-manager/profiles/{club_id}':
      '/api/v2/ai-manager/profiles/{club_id}',
  '/api/v1/ai-reporter/feed': '/api/v2/ai-reporter/feed',
  '/api/v1/ai-reporter/run': '/api/v2/ai-reporter/run',
  '/api/v1/ai/leagues': '/api/v2/ai/leagues',
  '/api/v1/ai/match/{match_id}': '/api/v2/ai/match/{match_id}',
  '/api/v1/analytics/clip/{clip_id}': '/api/v2/analytics/clip/{clip_id}',
  '/api/v1/analytics/dashboard/drop-off':
      '/api/v2/analytics/dashboard/drop-off',
  '/api/v1/analytics/dashboard/top-clips':
      '/api/v2/analytics/dashboard/top-clips',
  '/api/v1/analytics/device-fingerprint':
      '/api/v2/analytics/device-fingerprint',
  '/api/v1/analytics/events': '/api/v2/analytics/events',
  '/api/v1/analytics/frontend': '/api/v2/analytics/frontend',
  '/api/v1/analytics/influencer-leaderboard':
      '/api/v2/analytics/influencer-leaderboard',
  '/api/v1/attachments': '/api/v2/attachments',
  '/api/v1/attachments/{attachment_id}': '/api/v2/attachments/{attachment_id}',
  '/api/v1/auth/change-password': '/api/v2/auth/change-password',
  '/api/v1/auth/confirm-email': '/api/v2/auth/confirm-email',
  '/api/v1/auth/login': '/api/v2/auth/login',
  '/api/v1/auth/logout': '/api/v2/auth/logout',
  '/api/v1/auth/me': '/api/v2/auth/me',
  '/api/v1/auth/recovery/request': '/api/v2/auth/recovery/request',
  '/api/v1/auth/recovery/reset': '/api/v2/auth/recovery/reset',
  '/api/v1/auth/refresh': '/api/v2/auth/refresh',
  '/api/v1/auth/signup/creator': '/api/v2/auth/signup/creator',
  '/api/v1/auth/signup/trader': '/api/v2/auth/signup/trader',
  '/api/v1/auth/signup/user': '/api/v2/auth/signup/user',
  '/api/v1/awards/categories': '/api/v2/awards/categories',
  '/api/v1/awards/ceremony': '/api/v2/awards/ceremony',
  '/api/v1/awards/ceremony/tickets': '/api/v2/awards/ceremony/tickets',
  '/api/v1/awards/ceremony/vote': '/api/v2/awards/ceremony/vote',
  '/api/v1/awards/nominees': '/api/v2/awards/nominees',
  '/api/v1/awards/winners': '/api/v2/awards/winners',
  '/api/v1/bank-accounts': '/api/v2/bank-accounts',
  '/api/v1/bank-accounts/{bank_account_id}':
      '/api/v2/bank-accounts/{bank_account_id}',
  '/api/v1/bets/history': '/api/v2/bets/history',
  '/api/v1/bets/odds/{match_id}': '/api/v2/bets/odds/{match_id}',
  '/api/v1/bets/place': '/api/v2/bets/place',
  '/api/v1/bets/preferences': '/api/v2/bets/preferences',
  '/api/v1/broadcast-rights/auctions/{auction_id}/bids':
      '/api/v2/broadcast-rights/auctions/{auction_id}/bids',
  '/api/v1/broadcast-rights/competitions/{competition_id}':
      '/api/v2/broadcast-rights/competitions/{competition_id}',
  '/api/v1/broadcast-rights/competitions/{competition_id}/acquire':
      '/api/v2/broadcast-rights/competitions/{competition_id}/acquire',
  '/api/v1/broadcast-rights/competitions/{competition_id}/auctions':
      '/api/v2/broadcast-rights/competitions/{competition_id}/auctions',
  '/api/v1/broadcast-rights/matches/{match_id}/access':
      '/api/v2/broadcast-rights/matches/{match_id}/access',
  '/api/v1/broadcast-rights/matches/{match_id}/distribute':
      '/api/v2/broadcast-rights/matches/{match_id}/distribute',
  '/api/v1/broadcast-rights/{right_id}/grants':
      '/api/v2/broadcast-rights/{right_id}/grants',
  '/api/v1/broadcast/channels': '/api/v2/broadcast/channels',
  '/api/v1/broadcast/channels/{channel_id}/audio/stems/stream':
      '/api/v2/broadcast/channels/{channel_id}/audio/stems/stream',
  '/api/v1/broadcast/channels/{channel_id}/join':
      '/api/v2/broadcast/channels/{channel_id}/join',
  '/api/v1/broadcast/channels/{channel_id}/stream':
      '/api/v2/broadcast/channels/{channel_id}/stream',
  '/api/v1/broadcast/home': '/api/v2/broadcast/home',
  '/api/v1/broadcast/{match_id}': '/api/v2/broadcast/{match_id}',
  '/api/v1/calendar-engine/dashboard': '/api/v2/calendar-engine/dashboard',
  '/api/v1/calendar-engine/events': '/api/v2/calendar-engine/events',
  '/api/v1/calendar-engine/lifecycle-runs':
      '/api/v2/calendar-engine/lifecycle-runs',
  '/api/v1/calendar-engine/pause-status':
      '/api/v2/calendar-engine/pause-status',
  '/api/v1/calendar-engine/seasons': '/api/v2/calendar-engine/seasons',
  '/api/v1/campaigns': '/api/v2/campaigns',
  '/api/v1/campaigns/create': '/api/v2/campaigns/create',
  '/api/v1/campaigns/{id}/accept': '/api/v2/campaigns/{id}/accept',
  '/api/v1/campaigns/{id}/apply': '/api/v2/campaigns/{id}/apply',
  '/api/v1/campaigns/{id}/performance': '/api/v2/campaigns/{id}/performance',
  '/api/v1/career/create': '/api/v2/career/create',
  '/api/v1/career/retire': '/api/v2/career/retire',
  '/api/v1/career/train': '/api/v2/career/train',
  '/api/v1/career/transfer': '/api/v2/career/transfer',
  '/api/v1/career/{user_id}': '/api/v2/career/{user_id}',
  '/api/v1/challenges/links/{link_code}':
      '/api/v2/challenges/links/{link_code}',
  '/api/v1/challenges/{challenge_id}': '/api/v2/challenges/{challenge_id}',
  '/api/v1/challenges/{challenge_id}/accept':
      '/api/v2/challenges/{challenge_id}/accept',
  '/api/v1/challenges/{challenge_id}/links':
      '/api/v2/challenges/{challenge_id}/links',
  '/api/v1/challenges/{challenge_id}/publish':
      '/api/v2/challenges/{challenge_id}/publish',
  '/api/v1/challenges/{challenge_id}/share-events':
      '/api/v2/challenges/{challenge_id}/share-events',
  '/api/v1/champions-league/knockout-bracket':
      '/api/v2/champions-league/knockout-bracket',
  '/api/v1/champions-league/league-phase/table':
      '/api/v2/champions-league/league-phase/table',
  '/api/v1/champions-league/playoff-bracket':
      '/api/v2/champions-league/playoff-bracket',
  '/api/v1/champions-league/prize-pool/preview':
      '/api/v2/champions-league/prize-pool/preview',
  '/api/v1/champions-league/qualification-map':
      '/api/v2/champions-league/qualification-map',
  '/api/v1/club-infra/clubs/{club_id}': '/api/v2/club-infra/clubs/{club_id}',
  '/api/v1/club-infra/clubs/{club_id}/support':
      '/api/v2/club-infra/clubs/{club_id}/support',
  '/api/v1/club-infra/my': '/api/v2/club-infra/my',
  '/api/v1/club-infra/my/facilities/upgrade':
      '/api/v2/club-infra/my/facilities/upgrade',
  '/api/v1/club-infra/my/stadium/upgrade':
      '/api/v2/club-infra/my/stadium/upgrade',
  '/api/v1/club/identity': '/api/v2/club/identity',
  '/api/v1/clubs': '/api/v2/clubs',
  '/api/v1/clubs/catalog': '/api/v2/clubs/catalog',
  '/api/v1/clubs/catalog/purchase': '/api/v2/clubs/catalog/purchase',
  '/api/v1/clubs/marketplace': '/api/v2/clubs/marketplace',
  '/api/v1/clubs/sale-market/listings': '/api/v2/clubs/sale-market/listings',
  '/api/v1/clubs/{club_id}': '/api/v2/clubs/{club_id}',
  '/api/v1/clubs/{club_id}/academy': '/api/v2/clubs/{club_id}/academy',
  '/api/v1/clubs/{club_id}/academy/players':
      '/api/v2/clubs/{club_id}/academy/players',
  '/api/v1/clubs/{club_id}/academy/players/{player_id}':
      '/api/v2/clubs/{club_id}/academy/players/{player_id}',
  '/api/v1/clubs/{club_id}/academy/programs':
      '/api/v2/clubs/{club_id}/academy/programs',
  '/api/v1/clubs/{club_id}/academy/training-cycles':
      '/api/v2/clubs/{club_id}/academy/training-cycles',
  '/api/v1/clubs/{club_id}/badge': '/api/v2/clubs/{club_id}/badge',
  '/api/v1/clubs/{club_id}/branding': '/api/v2/clubs/{club_id}/branding',
  '/api/v1/clubs/{club_id}/buy-tokens': '/api/v2/clubs/{club_id}/buy-tokens',
  '/api/v1/clubs/{club_id}/challenges': '/api/v2/clubs/{club_id}/challenges',
  '/api/v1/clubs/{club_id}/contracts': '/api/v2/clubs/{club_id}/contracts',
  '/api/v1/clubs/{club_id}/dynasty': '/api/v2/clubs/{club_id}/dynasty',
  '/api/v1/clubs/{club_id}/dynasty/history':
      '/api/v2/clubs/{club_id}/dynasty/history',
  '/api/v1/clubs/{club_id}/eras': '/api/v2/clubs/{club_id}/eras',
  '/api/v1/clubs/{club_id}/finances': '/api/v2/clubs/{club_id}/finances',
  '/api/v1/clubs/{club_id}/finances/budget':
      '/api/v2/clubs/{club_id}/finances/budget',
  '/api/v1/clubs/{club_id}/finances/cashflow':
      '/api/v2/clubs/{club_id}/finances/cashflow',
  '/api/v1/clubs/{club_id}/finances/ledger':
      '/api/v2/clubs/{club_id}/finances/ledger',
  '/api/v1/clubs/{club_id}/honors-timeline':
      '/api/v2/clubs/{club_id}/honors-timeline',
  '/api/v1/clubs/{club_id}/identity': '/api/v2/clubs/{club_id}/identity',
  '/api/v1/clubs/{club_id}/identity/metrics':
      '/api/v2/clubs/{club_id}/identity/metrics',
  '/api/v1/clubs/{club_id}/identity/metrics/refresh':
      '/api/v2/clubs/{club_id}/identity/metrics/refresh',
  '/api/v1/clubs/{club_id}/jerseys': '/api/v2/clubs/{club_id}/jerseys',
  '/api/v1/clubs/{club_id}/jerseys/{jersey_id}':
      '/api/v2/clubs/{club_id}/jerseys/{jersey_id}',
  '/api/v1/clubs/{club_id}/ownership': '/api/v2/clubs/{club_id}/ownership',
  '/api/v1/clubs/{club_id}/prestige': '/api/v2/clubs/{club_id}/prestige',
  '/api/v1/clubs/{club_id}/proposals': '/api/v2/clubs/{club_id}/proposals',
  '/api/v1/clubs/{club_id}/purchases': '/api/v2/clubs/{club_id}/purchases',
  '/api/v1/clubs/{club_id}/reputation': '/api/v2/clubs/{club_id}/reputation',
  '/api/v1/clubs/{club_id}/reputation/history':
      '/api/v2/clubs/{club_id}/reputation/history',
  '/api/v1/clubs/{club_id}/rivalries': '/api/v2/clubs/{club_id}/rivalries',
  '/api/v1/clubs/{club_id}/rivalries/{opponent_club_id}':
      '/api/v2/clubs/{club_id}/rivalries/{opponent_club_id}',
  '/api/v1/clubs/{club_id}/sale-market': '/api/v2/clubs/{club_id}/sale-market',
  '/api/v1/clubs/{club_id}/sale-market/assistant':
      '/api/v2/clubs/{club_id}/sale-market/assistant',
  '/api/v1/clubs/{club_id}/sale-market/history':
      '/api/v2/clubs/{club_id}/sale-market/history',
  '/api/v1/clubs/{club_id}/sale-market/inquiries':
      '/api/v2/clubs/{club_id}/sale-market/inquiries',
  '/api/v1/clubs/{club_id}/sale-market/inquiries/{inquiry_id}/respond':
      '/api/v2/clubs/{club_id}/sale-market/inquiries/{inquiry_id}/respond',
  '/api/v1/clubs/{club_id}/sale-market/listing':
      '/api/v2/clubs/{club_id}/sale-market/listing',
  '/api/v1/clubs/{club_id}/sale-market/listing/cancel':
      '/api/v2/clubs/{club_id}/sale-market/listing/cancel',
  '/api/v1/clubs/{club_id}/sale-market/listing/instant-sell':
      '/api/v2/clubs/{club_id}/sale-market/listing/instant-sell',
  '/api/v1/clubs/{club_id}/sale-market/offers':
      '/api/v2/clubs/{club_id}/sale-market/offers',
  '/api/v1/clubs/{club_id}/sale-market/offers/{offer_id}/accept':
      '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/accept',
  '/api/v1/clubs/{club_id}/sale-market/offers/{offer_id}/counter':
      '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/counter',
  '/api/v1/clubs/{club_id}/sale-market/offers/{offer_id}/reject':
      '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/reject',
  '/api/v1/clubs/{club_id}/sale-market/transfer':
      '/api/v2/clubs/{club_id}/sale-market/transfer',
  '/api/v1/clubs/{club_id}/scouting': '/api/v2/clubs/{club_id}/scouting',
  '/api/v1/clubs/{club_id}/scouting-intelligence/academy-supply-signals':
      '/api/v2/clubs/{club_id}/scouting-intelligence/academy-supply-signals',
  '/api/v1/clubs/{club_id}/scouting-intelligence/assignments':
      '/api/v2/clubs/{club_id}/scouting-intelligence/assignments',
  '/api/v1/clubs/{club_id}/scouting-intelligence/badges':
      '/api/v2/clubs/{club_id}/scouting-intelligence/badges',
  '/api/v1/clubs/{club_id}/scouting-intelligence/lifecycle':
      '/api/v2/clubs/{club_id}/scouting-intelligence/lifecycle',
  '/api/v1/clubs/{club_id}/scouting-intelligence/manager-profiles':
      '/api/v2/clubs/{club_id}/scouting-intelligence/manager-profiles',
  '/api/v1/clubs/{club_id}/scouting-intelligence/missions':
      '/api/v2/clubs/{club_id}/scouting-intelligence/missions',
  '/api/v1/clubs/{club_id}/scouting-intelligence/missions/{mission_id}':
      '/api/v2/clubs/{club_id}/scouting-intelligence/missions/{mission_id}',
  '/api/v1/clubs/{club_id}/scouting-intelligence/missions/{mission_id}/complete':
      '/api/v2/clubs/{club_id}/scouting-intelligence/missions/{mission_id}/complete',
  '/api/v1/clubs/{club_id}/scouting-intelligence/networks':
      '/api/v2/clubs/{club_id}/scouting-intelligence/networks',
  '/api/v1/clubs/{club_id}/scouting-intelligence/planning':
      '/api/v2/clubs/{club_id}/scouting-intelligence/planning',
  '/api/v1/clubs/{club_id}/scouting/assignments':
      '/api/v2/clubs/{club_id}/scouting/assignments',
  '/api/v1/clubs/{club_id}/scouting/prospects':
      '/api/v2/clubs/{club_id}/scouting/prospects',
  '/api/v1/clubs/{club_id}/scouting/prospects/{prospect_id}':
      '/api/v2/clubs/{club_id}/scouting/prospects/{prospect_id}',
  '/api/v1/clubs/{club_id}/season-honors':
      '/api/v2/clubs/{club_id}/season-honors',
  '/api/v1/clubs/{club_id}/sell-tokens': '/api/v2/clubs/{club_id}/sell-tokens',
  '/api/v1/clubs/{club_id}/showcase': '/api/v2/clubs/{club_id}/showcase',
  '/api/v1/clubs/{club_id}/sponsorships':
      '/api/v2/clubs/{club_id}/sponsorships',
  '/api/v1/clubs/{club_id}/sponsorships/assets':
      '/api/v2/clubs/{club_id}/sponsorships/assets',
  '/api/v1/clubs/{club_id}/sponsorships/catalog':
      '/api/v2/clubs/{club_id}/sponsorships/catalog',
  '/api/v1/clubs/{club_id}/sponsorships/contracts':
      '/api/v2/clubs/{club_id}/sponsorships/contracts',
  '/api/v1/clubs/{club_id}/sponsorships/contracts/{contract_id}':
      '/api/v2/clubs/{club_id}/sponsorships/contracts/{contract_id}',
  '/api/v1/clubs/{club_id}/treasury': '/api/v2/clubs/{club_id}/treasury',
  '/api/v1/clubs/{club_id}/trophies': '/api/v2/clubs/{club_id}/trophies',
  '/api/v1/clubs/{club_id}/trophy-cabinet':
      '/api/v2/clubs/{club_id}/trophy-cabinet',
  '/api/v1/clubs/{club_id}/valuation': '/api/v2/clubs/{club_id}/valuation',
  '/api/v1/clubs/{club_id}/vote': '/api/v2/clubs/{club_id}/vote',
  '/api/v1/clubs/{club_id}/youth-pipeline':
      '/api/v2/clubs/{club_id}/youth-pipeline',
  '/api/v1/commentary/profiles': '/api/v2/commentary/profiles',
  '/api/v1/commentary/select': '/api/v2/commentary/select',
  '/api/v1/community/creator-clubs/{club_id}/fan-competitions':
      '/api/v2/community/creator-clubs/{club_id}/fan-competitions',
  '/api/v1/community/creator-clubs/{club_id}/fan-groups':
      '/api/v2/community/creator-clubs/{club_id}/fan-groups',
  '/api/v1/community/creator-clubs/{club_id}/fan-state':
      '/api/v2/community/creator-clubs/{club_id}/fan-state',
  '/api/v1/community/creator-clubs/{club_id}/follow':
      '/api/v2/community/creator-clubs/{club_id}/follow',
  '/api/v1/community/creator-matches/{match_id}/chat-room':
      '/api/v2/community/creator-matches/{match_id}/chat-room',
  '/api/v1/community/creator-matches/{match_id}/chat-room/messages':
      '/api/v2/community/creator-matches/{match_id}/chat-room/messages',
  '/api/v1/community/creator-matches/{match_id}/fan-wall':
      '/api/v2/community/creator-matches/{match_id}/fan-wall',
  '/api/v1/community/creator-matches/{match_id}/rivalry-signals':
      '/api/v2/community/creator-matches/{match_id}/rivalry-signals',
  '/api/v1/community/creator-matches/{match_id}/tactical-advice':
      '/api/v2/community/creator-matches/{match_id}/tactical-advice',
  '/api/v1/community/digest': '/api/v2/community/digest',
  '/api/v1/community/fan-competitions/{fan_competition_id}/join':
      '/api/v2/community/fan-competitions/{fan_competition_id}/join',
  '/api/v1/community/fan-groups/{group_id}/join':
      '/api/v2/community/fan-groups/{group_id}/join',
  '/api/v1/community/live-threads': '/api/v2/community/live-threads',
  '/api/v1/community/live-threads/{thread_id}':
      '/api/v2/community/live-threads/{thread_id}',
  '/api/v1/community/live-threads/{thread_id}/messages':
      '/api/v2/community/live-threads/{thread_id}/messages',
  '/api/v1/community/private-messages/threads':
      '/api/v2/community/private-messages/threads',
  '/api/v1/community/private-messages/threads/{thread_id}':
      '/api/v2/community/private-messages/threads/{thread_id}',
  '/api/v1/community/private-messages/threads/{thread_id}/messages':
      '/api/v2/community/private-messages/threads/{thread_id}/messages',
  '/api/v1/community/watchlist': '/api/v2/community/watchlist',
  '/api/v1/community/watchlist/{competition_key}':
      '/api/v2/community/watchlist/{competition_key}',
  '/api/v1/competitions': '/api/v2/competitions',
  '/api/v1/competitions/admin': '/api/v2/competitions/admin',
  '/api/v1/competitions/admin/{code}': '/api/v2/competitions/admin/{code}',
  '/api/v1/competitions/admin/{code}/orchestrate':
      '/api/v2/competitions/admin/{code}/orchestrate',
  '/api/v1/competitions/create': '/api/v2/competitions/create',
  '/api/v1/competitions/join': '/api/v2/competitions/join',
  '/api/v1/competitions/players/{subject_id}/progression':
      '/api/v2/competitions/players/{subject_id}/progression',
  '/api/v1/competitions/records/{competition_id}':
      '/api/v2/competitions/records/{competition_id}',
  '/api/v1/competitions/runtime/{code}': '/api/v2/competitions/runtime/{code}',
  '/api/v1/competitions/{competition_id}':
      '/api/v2/competitions/{competition_id}',
  '/api/v1/competitions/{competition_id}/advance':
      '/api/v2/competitions/{competition_id}/advance',
  '/api/v1/competitions/{competition_id}/finalize':
      '/api/v2/competitions/{competition_id}/finalize',
  '/api/v1/competitions/{competition_id}/financials':
      '/api/v2/competitions/{competition_id}/financials',
  '/api/v1/competitions/{competition_id}/fixtures':
      '/api/v2/competitions/{competition_id}/fixtures',
  '/api/v1/competitions/{competition_id}/invites':
      '/api/v2/competitions/{competition_id}/invites',
  '/api/v1/competitions/{competition_id}/invites/accept':
      '/api/v2/competitions/{competition_id}/invites/accept',
  '/api/v1/competitions/{competition_id}/join':
      '/api/v2/competitions/{competition_id}/join',
  '/api/v1/competitions/{competition_id}/launch':
      '/api/v2/competitions/{competition_id}/launch',
  '/api/v1/competitions/{competition_id}/leave':
      '/api/v2/competitions/{competition_id}/leave',
  '/api/v1/competitions/{competition_id}/matches/{match_id}/events':
      '/api/v2/competitions/{competition_id}/matches/{match_id}/events',
  '/api/v1/competitions/{competition_id}/matches/{match_id}/result':
      '/api/v2/competitions/{competition_id}/matches/{match_id}/result',
  '/api/v1/competitions/{competition_id}/publish':
      '/api/v2/competitions/{competition_id}/publish',
  '/api/v1/competitions/{competition_id}/rewards':
      '/api/v2/competitions/{competition_id}/rewards',
  '/api/v1/competitions/{competition_id}/rounds':
      '/api/v2/competitions/{competition_id}/rounds',
  '/api/v1/competitions/{competition_id}/schedule/jobs':
      '/api/v2/competitions/{competition_id}/schedule/jobs',
  '/api/v1/competitions/{competition_id}/schedule/jobs/{job_id}':
      '/api/v2/competitions/{competition_id}/schedule/jobs/{job_id}',
  '/api/v1/competitions/{competition_id}/schedule/preview':
      '/api/v2/competitions/{competition_id}/schedule/preview',
  '/api/v1/competitions/{competition_id}/seed':
      '/api/v2/competitions/{competition_id}/seed',
  '/api/v1/competitions/{competition_id}/standings':
      '/api/v2/competitions/{competition_id}/standings',
  '/api/v1/competitions/{competition_id}/summary':
      '/api/v2/competitions/{competition_id}/summary',
  '/api/v1/competitive-integrity/fast-game/runs':
      '/api/v2/competitive-integrity/fast-game/runs',
  '/api/v1/competitive-integrity/fast-game/runs/{run_id}':
      '/api/v2/competitive-integrity/fast-game/runs/{run_id}',
  '/api/v1/competitive-integrity/fast-game/runs/{run_id}/play':
      '/api/v2/competitive-integrity/fast-game/runs/{run_id}/play',
  '/api/v1/competitive-integrity/managers':
      '/api/v2/competitive-integrity/managers',
  '/api/v1/competitive-integrity/managers/candidates':
      '/api/v2/competitive-integrity/managers/candidates',
  '/api/v1/competitive-integrity/managers/{manager_id}/instructions':
      '/api/v2/competitive-integrity/managers/{manager_id}/instructions',
  '/api/v1/competitive-integrity/matches':
      '/api/v2/competitive-integrity/matches',
  '/api/v1/competitive-integrity/matches/{match_id}':
      '/api/v2/competitive-integrity/matches/{match_id}',
  '/api/v1/competitive-integrity/matches/{match_id}/execute':
      '/api/v2/competitive-integrity/matches/{match_id}/execute',
  '/api/v1/competitive-integrity/notifications/events':
      '/api/v2/competitive-integrity/notifications/events',
  '/api/v1/config/current': '/api/v2/config/current',
  '/api/v1/config/update': '/api/v2/config/update',
  '/api/v1/conversations': '/api/v2/conversations',
  '/api/v1/conversations/start': '/api/v2/conversations/start',
  '/api/v1/conversations/{conversation_id}/message':
      '/api/v2/conversations/{conversation_id}/message',
  '/api/v1/conversations/{conversation_id}/messages':
      '/api/v2/conversations/{conversation_id}/messages',
  '/api/v1/conversations/{conversation_id}/status':
      '/api/v2/conversations/{conversation_id}/status',
  '/api/v1/creator-campaigns': '/api/v2/creator-campaigns',
  '/api/v1/creator-campaigns/me': '/api/v2/creator-campaigns/me',
  '/api/v1/creator-campaigns/{campaign_id}':
      '/api/v2/creator-campaigns/{campaign_id}',
  '/api/v1/creator-campaigns/{campaign_id}/metrics':
      '/api/v2/creator-campaigns/{campaign_id}/metrics',
  '/api/v1/creator-campaigns/{campaign_id}/snapshot':
      '/api/v2/creator-campaigns/{campaign_id}/snapshot',
  '/api/v1/creator-campaigns/{campaign_id}/snapshots':
      '/api/v2/creator-campaigns/{campaign_id}/snapshots',
  '/api/v1/creator-league': '/api/v2/creator-league',
  '/api/v1/creator-league/config': '/api/v2/creator-league/config',
  '/api/v1/creator-league/financial-report':
      '/api/v2/creator-league/financial-report',
  '/api/v1/creator-league/financial-settlements':
      '/api/v2/creator-league/financial-settlements',
  '/api/v1/creator-league/financial-settlements/{settlement_id}/approve':
      '/api/v2/creator-league/financial-settlements/{settlement_id}/approve',
  '/api/v1/creator-league/live-priority':
      '/api/v2/creator-league/live-priority',
  '/api/v1/creator-league/reset': '/api/v2/creator-league/reset',
  '/api/v1/creator-league/season-tiers/{season_tier_id}/standings':
      '/api/v2/creator-league/season-tiers/{season_tier_id}/standings',
  '/api/v1/creator-league/seasons': '/api/v2/creator-league/seasons',
  '/api/v1/creator-league/seasons/{season_id}':
      '/api/v2/creator-league/seasons/{season_id}',
  '/api/v1/creator-league/seasons/{season_id}/pause':
      '/api/v2/creator-league/seasons/{season_id}/pause',
  '/api/v1/creator-league/tiers': '/api/v2/creator-league/tiers',
  '/api/v1/creator-league/tiers/{tier_id}':
      '/api/v2/creator-league/tiers/{tier_id}',
  '/api/v1/creator/application': '/api/v2/creator/application',
  '/api/v1/creator/apply': '/api/v2/creator/apply',
  '/api/v1/creator/cards': '/api/v2/creator/cards',
  '/api/v1/creator/cards/listings': '/api/v2/creator/cards/listings',
  '/api/v1/creator/cards/listings/{listing_id}/buy':
      '/api/v2/creator/cards/listings/{listing_id}/buy',
  '/api/v1/creator/cards/loans/{loan_id}/return':
      '/api/v2/creator/cards/loans/{loan_id}/return',
  '/api/v1/creator/cards/swap': '/api/v2/creator/cards/swap',
  '/api/v1/creator/cards/{creator_card_id}/list':
      '/api/v2/creator/cards/{creator_card_id}/list',
  '/api/v1/creator/cards/{creator_card_id}/loan':
      '/api/v2/creator/cards/{creator_card_id}/loan',
  '/api/v1/creator/clubs/{club_id}/fan-share-market':
      '/api/v2/creator/clubs/{club_id}/fan-share-market',
  '/api/v1/creator/clubs/{club_id}/fan-share-market/distributions':
      '/api/v2/creator/clubs/{club_id}/fan-share-market/distributions',
  '/api/v1/creator/clubs/{club_id}/fan-share-market/holding':
      '/api/v2/creator/clubs/{club_id}/fan-share-market/holding',
  '/api/v1/creator/clubs/{club_id}/fan-share-market/purchase':
      '/api/v2/creator/clubs/{club_id}/fan-share-market/purchase',
  '/api/v1/creator/verify-email': '/api/v2/creator/verify-email',
  '/api/v1/creator/verify-phone': '/api/v2/creator/verify-phone',
  '/api/v1/creators/marketplace': '/api/v2/creators/marketplace',
  '/api/v1/creators/me/competitions': '/api/v2/creators/me/competitions',
  '/api/v1/creators/me/copilot/analyze': '/api/v2/creators/me/copilot/analyze',
  '/api/v1/creators/me/finance': '/api/v2/creators/me/finance',
  '/api/v1/creators/me/insights': '/api/v2/creators/me/insights',
  '/api/v1/creators/me/reputation': '/api/v2/creators/me/reputation',
  '/api/v1/creators/me/summary': '/api/v2/creators/me/summary',
  '/api/v1/creators/profile': '/api/v2/creators/profile',
  '/api/v1/creators/profile/me': '/api/v2/creators/profile/me',
  '/api/v1/creators/{handle}': '/api/v2/creators/{handle}',
  '/api/v1/daily-challenges': '/api/v2/daily-challenges',
  '/api/v1/daily-challenges/me': '/api/v2/daily-challenges/me',
  '/api/v1/daily-challenges/{challenge_key}/claim':
      '/api/v2/daily-challenges/{challenge_key}/claim',
  '/api/v1/diagnostics': '/api/v2/diagnostics',
  '/api/v1/discovery/home': '/api/v2/discovery/home',
  '/api/v1/discovery/saved-searches': '/api/v2/discovery/saved-searches',
  '/api/v1/discovery/saved-searches/{search_id}':
      '/api/v2/discovery/saved-searches/{search_id}',
  '/api/v1/discovery/search': '/api/v2/discovery/search',
  '/api/v1/disputes': '/api/v2/disputes',
  '/api/v1/disputes/me': '/api/v2/disputes/me',
  '/api/v1/disputes/{dispute_id}': '/api/v2/disputes/{dispute_id}',
  '/api/v1/disputes/{dispute_id}/messages':
      '/api/v2/disputes/{dispute_id}/messages',
  '/api/v1/dynasty': '/api/v2/dynasty',
  '/api/v1/dynasty/leaderboard': '/api/v2/dynasty/leaderboard',
  '/api/v1/economy/fx/quote': '/api/v2/economy/fx/quote',
  '/api/v1/economy/gift-catalog': '/api/v2/economy/gift-catalog',
  '/api/v1/economy/service-pricing': '/api/v2/economy/service-pricing',
  '/api/v1/engagement/achievements': '/api/v2/engagement/achievements',
  '/api/v1/engagement/achievements/me': '/api/v2/engagement/achievements/me',
  '/api/v1/engagement/milestones/me': '/api/v2/engagement/milestones/me',
  '/api/v1/engagement/sync': '/api/v2/engagement/sync',
  '/api/v1/enter': '/api/v2/enter',
  '/api/v1/events/clip': '/api/v2/events/clip',
  '/api/v1/events/today': '/api/v2/events/today',
  '/api/v1/events/upcoming': '/api/v2/events/upcoming',
  '/api/v1/experience/full-simulation': '/api/v2/experience/full-simulation',
  '/api/v1/fan-predictions/creator-clubs/{club_id}/leaderboards/weekly':
      '/api/v2/fan-predictions/creator-clubs/{club_id}/leaderboards/weekly',
  '/api/v1/fan-predictions/leaderboards/weekly':
      '/api/v2/fan-predictions/leaderboards/weekly',
  '/api/v1/fan-predictions/matches/{match_id}':
      '/api/v2/fan-predictions/matches/{match_id}',
  '/api/v1/fan-predictions/matches/{match_id}/leaderboard':
      '/api/v2/fan-predictions/matches/{match_id}/leaderboard',
  '/api/v1/fan-predictions/matches/{match_id}/submissions':
      '/api/v2/fan-predictions/matches/{match_id}/submissions',
  '/api/v1/fan-predictions/me/submissions':
      '/api/v2/fan-predictions/me/submissions',
  '/api/v1/fan-predictions/me/tokens': '/api/v2/fan-predictions/me/tokens',
  '/api/v1/fan-wars/leaderboards/{board_type}':
      '/api/v2/fan-wars/leaderboards/{board_type}',
  '/api/v1/fan-wars/nations-cup/{competition_id}':
      '/api/v2/fan-wars/nations-cup/{competition_id}',
  '/api/v1/fan-wars/profiles/{profile_id}/dashboard':
      '/api/v2/fan-wars/profiles/{profile_id}/dashboard',
  '/api/v1/fan-wars/rivalries/{board_type}':
      '/api/v2/fan-wars/rivalries/{board_type}',
  '/api/v1/fans/profile': '/api/v2/fans/profile',
  '/api/v1/fans/tribe/join': '/api/v2/fans/tribe/join',
  '/api/v1/fans/{club_id}': '/api/v2/fans/{club_id}',
  '/api/v1/fast-cups/upcoming': '/api/v2/fast-cups/upcoming',
  '/api/v1/fast-cups/{cup_id}/bracket': '/api/v2/fast-cups/{cup_id}/bracket',
  '/api/v1/fast-cups/{cup_id}/countdown':
      '/api/v2/fast-cups/{cup_id}/countdown',
  '/api/v1/fast-cups/{cup_id}/join': '/api/v2/fast-cups/{cup_id}/join',
  '/api/v1/fast-cups/{cup_id}/result-summary':
      '/api/v2/fast-cups/{cup_id}/result-summary',
  '/api/v1/federations': '/api/v2/federations',
  '/api/v1/federations/proposals/{proposal_id}/votes':
      '/api/v2/federations/proposals/{proposal_id}/votes',
  '/api/v1/federations/rankings': '/api/v2/federations/rankings',
  '/api/v1/federations/regional-tournaments':
      '/api/v2/federations/regional-tournaments',
  '/api/v1/federations/{federation_id}': '/api/v2/federations/{federation_id}',
  '/api/v1/federations/{federation_id}/governance':
      '/api/v2/federations/{federation_id}/governance',
  '/api/v1/federations/{federation_id}/leagues':
      '/api/v2/federations/{federation_id}/leagues',
  '/api/v1/federations/{federation_id}/memberships':
      '/api/v2/federations/{federation_id}/memberships',
  '/api/v1/federations/{federation_id}/narratives':
      '/api/v2/federations/{federation_id}/narratives',
  '/api/v1/federations/{federation_id}/proposals':
      '/api/v2/federations/{federation_id}/proposals',
  '/api/v1/federations/{federation_id}/sanctions':
      '/api/v2/federations/{federation_id}/sanctions',
  '/api/v1/federations/{federation_id}/treasury/distribute':
      '/api/v2/federations/{federation_id}/treasury/distribute',
  '/api/v1/federations/{federation_id}/validate-action':
      '/api/v2/federations/{federation_id}/validate-action',
  '/api/v1/feed/following': '/api/v2/feed/following',
  '/api/v1/feed/for-you': '/api/v2/feed/for-you',
  '/api/v1/feed/for-you/refresh': '/api/v2/feed/for-you/refresh',
  '/api/v1/feed/sponsored': '/api/v2/feed/sponsored',
  '/api/v1/finance': '/api/v2/finance',
  '/api/v1/follow/{user_id}': '/api/v2/follow/{user_id}',
  '/api/v1/football-events/players/{player_id}/events':
      '/api/v2/football-events/players/{player_id}/events',
  '/api/v1/football-events/players/{player_id}/impact':
      '/api/v2/football-events/players/{player_id}/impact',
  '/api/v1/gift-engine/me/combos': '/api/v2/gift-engine/me/combos',
  '/api/v1/gift-engine/me/summary': '/api/v2/gift-engine/me/summary',
  '/api/v1/gift-engine/me/transactions': '/api/v2/gift-engine/me/transactions',
  '/api/v1/gift-engine/send': '/api/v2/gift-engine/send',
  '/api/v1/governance/clubs/{club_id}/panel':
      '/api/v2/governance/clubs/{club_id}/panel',
  '/api/v1/governance/me/overview': '/api/v2/governance/me/overview',
  '/api/v1/governance/proposals': '/api/v2/governance/proposals',
  '/api/v1/governance/proposals/{proposal_id}':
      '/api/v2/governance/proposals/{proposal_id}',
  '/api/v1/governance/proposals/{proposal_id}/vote':
      '/api/v2/governance/proposals/{proposal_id}/vote',
  '/api/v1/gtex/market/buy': '/api/v2/gtex/market/buy',
  '/api/v1/gtex/market/sell': '/api/v2/gtex/market/sell',
  '/api/v1/hall-of-fame': '/api/v2/hall-of-fame',
  '/api/v1/health': '/health',
  '/api/v1/history/goat-rankings': '/api/v2/history/goat-rankings',
  '/api/v1/history/leaderboards': '/api/v2/history/leaderboards',
  '/api/v1/history/records': '/api/v2/history/records',
  '/api/v1/history/timeline/{subject_type}/{subject_id}':
      '/api/v2/history/timeline/{subject_type}/{subject_id}',
  '/api/v1/hosted-competitions': '/api/v2/hosted-competitions',
  '/api/v1/hosted-competitions/mine': '/api/v2/hosted-competitions/mine',
  '/api/v1/hosted-competitions/mine/invites':
      '/api/v2/hosted-competitions/mine/invites',
  '/api/v1/hosted-competitions/templates':
      '/api/v2/hosted-competitions/templates',
  '/api/v1/hosted-competitions/{competition_id}':
      '/api/v2/hosted-competitions/{competition_id}',
  '/api/v1/hosted-competitions/{competition_id}/finance':
      '/api/v2/hosted-competitions/{competition_id}/finance',
  '/api/v1/hosted-competitions/{competition_id}/invites':
      '/api/v2/hosted-competitions/{competition_id}/invites',
  '/api/v1/hosted-competitions/{competition_id}/invites/accept':
      '/api/v2/hosted-competitions/{competition_id}/invites/accept',
  '/api/v1/hosted-competitions/{competition_id}/join':
      '/api/v2/hosted-competitions/{competition_id}/join',
  '/api/v1/hosted-competitions/{competition_id}/launch':
      '/api/v2/hosted-competitions/{competition_id}/launch',
  '/api/v1/hosted-competitions/{competition_id}/standings':
      '/api/v2/hosted-competitions/{competition_id}/standings',
  '/api/v1/infinite-league/economy': '/api/v2/infinite-league/economy',
  '/api/v1/infinite-league/livestream': '/api/v2/infinite-league/livestream',
  '/api/v1/infinite-league/matches': '/api/v2/infinite-league/matches',
  '/api/v1/infinite-league/matches/{match_id}':
      '/api/v2/infinite-league/matches/{match_id}',
  '/api/v1/infinite-league/pundits/{match_id}':
      '/api/v2/infinite-league/pundits/{match_id}',
  '/api/v1/infinite-league/status': '/api/v2/infinite-league/status',
  '/api/v1/infinite-league/tick': '/api/v2/infinite-league/tick',
  '/api/v1/infinite-league/viral-feed': '/api/v2/infinite-league/viral-feed',
  '/api/v1/integrations/payments/korapay/webhook':
      '/api/v2/integrations/payments/korapay/webhook',
  '/api/v1/integrations/payments/methods':
      '/api/v2/integrations/payments/methods',
  '/api/v1/integrations/payments/orders':
      '/api/v2/integrations/payments/orders',
  '/api/v1/integrations/payments/paystack/webhook':
      '/api/v2/integrations/payments/paystack/webhook',
  '/api/v1/integrations/payments/quote': '/api/v2/integrations/payments/quote',
  '/api/v1/integrity-engine/me/incidents':
      '/api/v2/integrity-engine/me/incidents',
  '/api/v1/integrity-engine/me/score': '/api/v2/integrity-engine/me/score',
  '/api/v1/internal/ingestion/bootstrap-sync':
      '/api/v2/internal/ingestion/bootstrap-sync',
  '/api/v1/internal/ingestion/clubs/{club_external_id}/refresh':
      '/api/v2/internal/ingestion/clubs/{club_external_id}/refresh',
  '/api/v1/internal/ingestion/competitions/{competition_external_id}/refresh':
      '/api/v2/internal/ingestion/competitions/{competition_external_id}/refresh',
  '/api/v1/internal/ingestion/cursors/{provider_name}':
      '/api/v2/internal/ingestion/cursors/{provider_name}',
  '/api/v1/internal/ingestion/incremental-sync':
      '/api/v2/internal/ingestion/incremental-sync',
  '/api/v1/internal/ingestion/players/{player_external_id}/refresh':
      '/api/v2/internal/ingestion/players/{player_external_id}/refresh',
  '/api/v1/internal/ingestion/providers/{provider_name}/health':
      '/api/v2/internal/ingestion/providers/{provider_name}/health',
  '/api/v1/internal/ingestion/real-players/batches':
      '/api/v2/internal/ingestion/real-players/batches',
  '/api/v1/internal/ingestion/real-players/batches/{batch_id}':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}',
  '/api/v1/internal/ingestion/real-players/batches/{batch_id}/issues':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}/issues',
  '/api/v1/internal/ingestion/real-players/batches/{batch_id}/resume':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}/resume',
  '/api/v1/internal/ingestion/real-players/batches/{batch_id}/valuation-status':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}/valuation-status',
  '/api/v1/internal/ingestion/real-players/import':
      '/api/v2/internal/ingestion/real-players/import',
  '/api/v1/internal/ingestion/real-players/publish-jobs':
      '/api/v2/internal/ingestion/real-players/publish-jobs',
  '/api/v1/internal/ingestion/real-players/publish-jobs/{job_id}':
      '/api/v2/internal/ingestion/real-players/publish-jobs/{job_id}',
  '/api/v1/internal/ingestion/real-players/status':
      '/api/v2/internal/ingestion/real-players/status',
  '/api/v1/internal/ingestion/runs': '/api/v2/internal/ingestion/runs',
  '/api/v1/internal/ingestion/status': '/api/v2/internal/ingestion/status',
  '/api/v1/jackpot/contribute': '/api/v2/jackpot/contribute',
  '/api/v1/jackpot/history': '/api/v2/jackpot/history',
  '/api/v1/jackpot/state': '/api/v2/jackpot/state',
  '/api/v1/jobs/{job_id}': '/api/v2/jobs/{job_id}',
  '/api/v1/kyc': '/api/v2/kyc',
  '/api/v1/leaderboard/division/{division}':
      '/api/v2/leaderboard/division/{division}',
  '/api/v1/leaderboard/global': '/api/v2/leaderboard/global',
  '/api/v1/leaderboard/player/{player_id}':
      '/api/v2/leaderboard/player/{player_id}',
  '/api/v1/leaderboard/region/{region}': '/api/v2/leaderboard/region/{region}',
  '/api/v1/leaderboards/dynasties': '/api/v2/leaderboards/dynasties',
  '/api/v1/leaderboards/prestige': '/api/v2/leaderboards/prestige',
  '/api/v1/leaderboards/trophies': '/api/v2/leaderboards/trophies',
  '/api/v1/leagues/register': '/api/v2/leagues/register',
  '/api/v1/leagues/{season_id}/fixtures':
      '/api/v2/leagues/{season_id}/fixtures',
  '/api/v1/leagues/{season_id}/qualification-markers':
      '/api/v2/leagues/{season_id}/qualification-markers',
  '/api/v1/leagues/{season_id}/standings':
      '/api/v2/leagues/{season_id}/standings',
  '/api/v1/leagues/{season_id}/summary': '/api/v2/leagues/{season_id}/summary',
  '/api/v1/legacy/board': '/api/v2/legacy/board',
  '/api/v1/live-events': '/api/v2/live-events',
  '/api/v1/manager-duels': '/api/v2/manager-duels',
  '/api/v1/manager-duels/leaderboard': '/api/v2/manager-duels/leaderboard',
  '/api/v1/manager-duels/{duel_id}': '/api/v2/manager-duels/{duel_id}',
  '/api/v1/managers': '/api/v2/managers',
  '/api/v1/managers/assign': '/api/v2/managers/assign',
  '/api/v1/managers/catalog': '/api/v2/managers/catalog',
  '/api/v1/managers/compare': '/api/v2/managers/compare',
  '/api/v1/managers/competition-runtime/{code}':
      '/api/v2/managers/competition-runtime/{code}',
  '/api/v1/managers/create': '/api/v2/managers/create',
  '/api/v1/managers/filters': '/api/v2/managers/filters',
  '/api/v1/managers/history': '/api/v2/managers/history',
  '/api/v1/managers/leaderboard': '/api/v2/managers/leaderboard',
  '/api/v1/managers/my-trade-listings': '/api/v2/managers/my-trade-listings',
  '/api/v1/managers/recommendation': '/api/v2/managers/recommendation',
  '/api/v1/managers/recruit': '/api/v2/managers/recruit',
  '/api/v1/managers/swap': '/api/v2/managers/swap',
  '/api/v1/managers/team': '/api/v2/managers/team',
  '/api/v1/managers/trade-listings': '/api/v2/managers/trade-listings',
  '/api/v1/managers/trade-listings/{listing_id}/buy':
      '/api/v2/managers/trade-listings/{listing_id}/buy',
  '/api/v1/managers/trade-listings/{listing_id}/cancel':
      '/api/v2/managers/trade-listings/{listing_id}/cancel',
  '/api/v1/managers/{asset_id}/release': '/api/v2/managers/{asset_id}/release',
  '/api/v1/managers/{manager_id}': '/api/v2/managers/{manager_id}',
  '/api/v1/managers/{manager_id}/hire': '/api/v2/managers/{manager_id}/hire',
  '/api/v1/managers/{manager_id}/history':
      '/api/v2/managers/{manager_id}/history',
  '/api/v1/managers/{manager_id}/release':
      '/api/v2/managers/{manager_id}/release',
  '/api/v1/market/buy': '/api/v2/market/buy',
  '/api/v1/market/listings': '/api/v2/market/listings',
  '/api/v1/market/listings/{listing_id}/cancel':
      '/api/v2/market/listings/{listing_id}/cancel',
  '/api/v1/market/listings/{listing_id}/matches':
      '/api/v2/market/listings/{listing_id}/matches',
  '/api/v1/market/listings/{listing_id}/offers':
      '/api/v2/market/listings/{listing_id}/offers',
  '/api/v1/market/movers': '/api/v2/market/movers',
  '/api/v1/market/offers': '/api/v2/market/offers',
  '/api/v1/market/offers/{offer_id}/accept':
      '/api/v2/market/offers/{offer_id}/accept',
  '/api/v1/market/offers/{offer_id}/counter':
      '/api/v2/market/offers/{offer_id}/counter',
  '/api/v1/market/offers/{offer_id}/reject':
      '/api/v2/market/offers/{offer_id}/reject',
  '/api/v1/market/players': '/api/v2/market/players',
  '/api/v1/market/players/{player_id}': '/api/v2/market/players/{player_id}',
  '/api/v1/market/players/{player_id}/candles':
      '/api/v2/market/players/{player_id}/candles',
  '/api/v1/market/players/{player_id}/history':
      '/api/v2/market/players/{player_id}/history',
  '/api/v1/market/sell': '/api/v2/market/sell',
  '/api/v1/market/summary/{asset_id}': '/api/v2/market/summary/{asset_id}',
  '/api/v1/market/ticker/{player_id}': '/api/v2/market/ticker/{player_id}',
  '/api/v1/market/trade-intents': '/api/v2/market/trade-intents',
  '/api/v1/market/trade-intents/{intent_id}/withdraw':
      '/api/v2/market/trade-intents/{intent_id}/withdraw',
  '/api/v1/market/trending': '/api/v2/market/trending',
  '/api/v1/marketplace/my-players': '/api/v2/marketplace/my-players',
  '/api/v1/marketplace/players': '/api/v2/marketplace/players',
  '/api/v1/marketplace/players/{player_id}':
      '/api/v2/marketplace/players/{player_id}',
  '/api/v1/match-engine/analytics': '/api/v2/match-engine/analytics',
  '/api/v1/match-engine/analytics/{match_key}':
      '/api/v2/match-engine/analytics/{match_key}',
  '/api/v1/match-engine/highlights/{match_key}':
      '/api/v2/match-engine/highlights/{match_key}',
  '/api/v1/match-engine/live-feed/{match_key}':
      '/api/v2/match-engine/live-feed/{match_key}',
  '/api/v1/match-engine/render-sync': '/api/v2/match-engine/render-sync',
  '/api/v1/match-engine/render-sync/{match_key}':
      '/api/v2/match-engine/render-sync/{match_key}',
  '/api/v1/match-engine/replay': '/api/v2/match-engine/replay',
  '/api/v1/match-engine/simulate': '/api/v2/match-engine/simulate',
  '/api/v1/match-engine/summary': '/api/v2/match-engine/summary',
  '/api/v1/match-engine/timeline': '/api/v2/match-engine/timeline',
  '/api/v1/match-share-links/{share_code}':
      '/api/v2/match-share-links/{share_code}',
  '/api/v1/match-share-links/{share_code}/events':
      '/api/v2/match-share-links/{share_code}/events',
  '/api/v1/match-viewer/{match_key}': '/api/v2/match-viewer/{match_key}',
  '/api/v1/match-viewer/{match_key}/illusion':
      '/api/v2/match-viewer/{match_key}/illusion',
  '/api/v1/match-viewer/{match_key}/session':
      '/api/v2/match-viewer/{match_key}/session',
  '/api/v1/match/find': '/api/v2/match/find',
  '/api/v1/match/live/active': '/api/v2/match/live/active',
  '/api/v1/match/{match_id}/commentary/stream':
      '/api/v2/match/{match_id}/commentary/stream',
  '/api/v1/match/{match_id}/live': '/api/v2/match/{match_id}/live',
  '/api/v1/match/{match_id}/unity-access':
      '/api/v2/match/{match_id}/unity-access',
  '/api/v1/match/{match_id}/unity-access/refresh':
      '/api/v2/match/{match_id}/unity-access/refresh',
  '/api/v1/matches/complete': '/api/v2/matches/complete',
  '/api/v1/matches/live/active': '/api/v2/matches/live/active',
  '/api/v1/matches/start': '/api/v2/matches/start',
  '/api/v1/matches/{match_id}/analysis': '/api/v2/matches/{match_id}/analysis',
  '/api/v1/matches/{match_id}/audio/stems/stream':
      '/api/v2/matches/{match_id}/audio/stems/stream',
  '/api/v1/matches/{match_id}/chat': '/api/v2/matches/{match_id}/chat',
  '/api/v1/matches/{match_id}/chat/messages':
      '/api/v2/matches/{match_id}/chat/messages',
  '/api/v1/matches/{match_id}/commentary':
      '/api/v2/matches/{match_id}/commentary',
  '/api/v1/matches/{match_id}/commentary/stream':
      '/api/v2/matches/{match_id}/commentary/stream',
  '/api/v1/matches/{match_id}/fan-experience':
      '/api/v2/matches/{match_id}/fan-experience',
  '/api/v1/matches/{match_id}/highlights':
      '/api/v2/matches/{match_id}/highlights',
  '/api/v1/matches/{match_id}/highlights/share-package':
      '/api/v2/matches/{match_id}/highlights/share-package',
  '/api/v1/matches/{match_id}/live': '/api/v2/matches/{match_id}/live',
  '/api/v1/matches/{match_id}/live-reactions':
      '/api/v2/matches/{match_id}/live-reactions',
  '/api/v1/matches/{match_id}/reactions':
      '/api/v2/matches/{match_id}/reactions',
  '/api/v1/matches/{match_id}/replay': '/api/v2/matches/{match_id}/replay',
  '/api/v1/matches/{match_id}/share-links':
      '/api/v2/matches/{match_id}/share-links',
  '/api/v1/matches/{match_id}/social-warfare':
      '/api/v2/matches/{match_id}/social-warfare',
  '/api/v1/matches/{match_id}/spectate': '/api/v2/matches/{match_id}/spectate',
  '/api/v1/matches/{match_id}/spectators':
      '/api/v2/matches/{match_id}/spectators',
  '/api/v1/matches/{match_id}/stream': '/api/v2/matches/{match_id}/stream',
  '/api/v1/matches/{match_id}/tickets': '/api/v2/matches/{match_id}/tickets',
  '/api/v1/matches/{match_id}/unity-access':
      '/api/v2/matches/{match_id}/unity-access',
  '/api/v1/matches/{match_id}/unity-access/refresh':
      '/api/v2/matches/{match_id}/unity-access/refresh',
  '/api/v1/me/clubs/sale-market/listings':
      '/api/v2/me/clubs/sale-market/listings',
  '/api/v1/me/clubs/sale-market/offers': '/api/v2/me/clubs/sale-market/offers',
  '/api/v1/media': '/api/v2/media',
  '/api/v1/media-engine/creator-league/broadcast-modes':
      '/api/v2/media-engine/creator-league/broadcast-modes',
  '/api/v1/media-engine/creator-league/clubs/{club_id}/stadium':
      '/api/v2/media-engine/creator-league/clubs/{club_id}/stadium',
  '/api/v1/media-engine/creator-league/matches/{match_id}/access':
      '/api/v2/media-engine/creator-league/matches/{match_id}/access',
  '/api/v1/media-engine/creator-league/matches/{match_id}/analytics':
      '/api/v2/media-engine/creator-league/matches/{match_id}/analytics',
  '/api/v1/media-engine/creator-league/matches/{match_id}/gifts':
      '/api/v2/media-engine/creator-league/matches/{match_id}/gifts',
  '/api/v1/media-engine/creator-league/matches/{match_id}/purchase':
      '/api/v2/media-engine/creator-league/matches/{match_id}/purchase',
  '/api/v1/media-engine/creator-league/matches/{match_id}/stadium':
      '/api/v2/media-engine/creator-league/matches/{match_id}/stadium',
  '/api/v1/media-engine/creator-league/matches/{match_id}/stadium/placements':
      '/api/v2/media-engine/creator-league/matches/{match_id}/stadium/placements',
  '/api/v1/media-engine/creator-league/matches/{match_id}/tickets':
      '/api/v2/media-engine/creator-league/matches/{match_id}/tickets',
  '/api/v1/media-engine/creator-league/season-passes':
      '/api/v2/media-engine/creator-league/season-passes',
  '/api/v1/media-engine/creator-league/season-passes/me':
      '/api/v2/media-engine/creator-league/season-passes/me',
  '/api/v1/media-engine/downloads': '/api/v2/media-engine/downloads',
  '/api/v1/media-engine/downloads/{token}':
      '/api/v2/media-engine/downloads/{token}',
  '/api/v1/media-engine/matches/{match_key}/snapshot':
      '/api/v2/media-engine/matches/{match_key}/snapshot',
  '/api/v1/media-engine/me/clip-earnings':
      '/api/v2/media-engine/me/clip-earnings',
  '/api/v1/media-engine/me/purchases': '/api/v2/media-engine/me/purchases',
  '/api/v1/media-engine/me/share-exports':
      '/api/v2/media-engine/me/share-exports',
  '/api/v1/media-engine/purchases': '/api/v2/media-engine/purchases',
  '/api/v1/media-engine/share-exports': '/api/v2/media-engine/share-exports',
  '/api/v1/media-engine/share-exports/{export_id}/amplifications':
      '/api/v2/media-engine/share-exports/{export_id}/amplifications',
  '/api/v1/media-engine/share-templates':
      '/api/v2/media-engine/share-templates',
  '/api/v1/media-engine/views': '/api/v2/media-engine/views',
  '/api/v1/metrics': '/api/v2/metrics',
  '/api/v1/moderation/me/reports': '/api/v2/moderation/me/reports',
  '/api/v1/moderation/reports': '/api/v2/moderation/reports',
  '/api/v1/moments/live': '/api/v2/moments/live',
  '/api/v1/national-pool': '/api/v2/national-pool',
  '/api/v1/national-team-engine/competitions':
      '/api/v2/national-team-engine/competitions',
  '/api/v1/national-team-engine/competitions/{competition_id}':
      '/api/v2/national-team-engine/competitions/{competition_id}',
  '/api/v1/national-team-engine/competitions/{competition_id}/ads/active':
      '/api/v2/national-team-engine/competitions/{competition_id}/ads/active',
  '/api/v1/national-team-engine/competitions/{competition_id}/auto-build-squad':
      '/api/v2/national-team-engine/competitions/{competition_id}/auto-build-squad',
  '/api/v1/national-team-engine/competitions/{competition_id}/entries':
      '/api/v2/national-team-engine/competitions/{competition_id}/entries',
  '/api/v1/national-team-engine/competitions/{competition_id}/gifts':
      '/api/v2/national-team-engine/competitions/{competition_id}/gifts',
  '/api/v1/national-team-engine/competitions/{competition_id}/lifecycle':
      '/api/v2/national-team-engine/competitions/{competition_id}/lifecycle',
  '/api/v1/national-team-engine/competitions/{competition_id}/presentation':
      '/api/v2/national-team-engine/competitions/{competition_id}/presentation',
  '/api/v1/national-team-engine/competitions/{competition_id}/rental-entry':
      '/api/v2/national-team-engine/competitions/{competition_id}/rental-entry',
  '/api/v1/national-team-engine/competitions/{competition_id}/rental-pool':
      '/api/v2/national-team-engine/competitions/{competition_id}/rental-pool',
  '/api/v1/national-team-engine/competitions/{competition_id}/story-events':
      '/api/v2/national-team-engine/competitions/{competition_id}/story-events',
  '/api/v1/national-team-engine/competitions/{competition_id}/theme':
      '/api/v2/national-team-engine/competitions/{competition_id}/theme',
  '/api/v1/national-team-engine/entries/{entry_id}':
      '/api/v2/national-team-engine/entries/{entry_id}',
  '/api/v1/national-team-engine/entries/{entry_id}/free-players/claim':
      '/api/v2/national-team-engine/entries/{entry_id}/free-players/claim',
  '/api/v1/national-team-engine/entries/{entry_id}/rental-status':
      '/api/v2/national-team-engine/entries/{entry_id}/rental-status',
  '/api/v1/national-team-engine/entries/{entry_id}/rentals':
      '/api/v2/national-team-engine/entries/{entry_id}/rentals',
  '/api/v1/national-team-engine/me/history':
      '/api/v2/national-team-engine/me/history',
  '/api/v1/national-team-engine/me/previous-roster':
      '/api/v2/national-team-engine/me/previous-roster',
  '/api/v1/national-team-engine/rankings':
      '/api/v2/national-team-engine/rankings',
  '/api/v1/news/breaking': '/api/v2/news/breaking',
  '/api/v1/news/daily': '/api/v2/news/daily',
  '/api/v1/news/feed': '/api/v2/news/feed',
  '/api/v1/news/personalized': '/api/v2/news/personalized',
  '/api/v1/news/{article_id}': '/api/v2/news/{article_id}',
  '/api/v1/notifications': '/api/v2/notifications',
  '/api/v1/notifications/announcements': '/api/v2/notifications/announcements',
  '/api/v1/notifications/me': '/api/v2/notifications/me',
  '/api/v1/notifications/preferences': '/api/v2/notifications/preferences',
  '/api/v1/notifications/read-all': '/api/v2/notifications/read-all',
  '/api/v1/notifications/subscriptions': '/api/v2/notifications/subscriptions',
  '/api/v1/notifications/subscriptions/{subscription_id}':
      '/api/v2/notifications/subscriptions/{subscription_id}',
  '/api/v1/notifications/{notification_id}/read':
      '/api/v2/notifications/{notification_id}/read',
  '/api/v1/objectives/me': '/api/v2/objectives/me',
  '/api/v1/observability/config': '/api/v2/observability/config',
  '/api/v1/orchestrator/config': '/api/v2/orchestrator/config',
  '/api/v1/orchestrator/metrics': '/api/v2/orchestrator/metrics',
  '/api/v1/orders': '/api/v2/orders',
  '/api/v1/orders/book/{player_id}': '/api/v2/orders/book/{player_id}',
  '/api/v1/orders/{order_id}': '/api/v2/orders/{order_id}',
  '/api/v1/orders/{order_id}/admin-buyback':
      '/api/v2/orders/{order_id}/admin-buyback',
  '/api/v1/orders/{order_id}/admin-buyback-preview':
      '/api/v2/orders/{order_id}/admin-buyback-preview',
  '/api/v1/orders/{order_id}/cancel': '/api/v2/orders/{order_id}/cancel',
  '/api/v1/organizations': '/api/v2/organizations',
  '/api/v1/organizations/invites/accept':
      '/api/v2/organizations/invites/accept',
  '/api/v1/organizations/me': '/api/v2/organizations/me',
  '/api/v1/organizations/{organization_id}/audit-log':
      '/api/v2/organizations/{organization_id}/audit-log',
  '/api/v1/organizations/{organization_id}/invite':
      '/api/v2/organizations/{organization_id}/invite',
  '/api/v1/ownership-groups': '/api/v2/ownership-groups',
  '/api/v1/ownership-groups/transfers/validate':
      '/api/v2/ownership-groups/transfers/validate',
  '/api/v1/ownership-groups/{group_id}': '/api/v2/ownership-groups/{group_id}',
  '/api/v1/ownership-groups/{group_id}/budget/allocate':
      '/api/v2/ownership-groups/{group_id}/budget/allocate',
  '/api/v1/ownership-groups/{group_id}/budget/transfer':
      '/api/v2/ownership-groups/{group_id}/budget/transfer',
  '/api/v1/ownership-groups/{group_id}/clubs':
      '/api/v2/ownership-groups/{group_id}/clubs',
  '/api/v1/platform/mode': '/api/v2/platform/mode',
  '/api/v1/platform/switch': '/api/v2/platform/switch',
  '/api/v1/player-cards/admin/preseeded-regens':
      '/api/v2/player-cards/admin/preseeded-regens',
  '/api/v1/player-cards/admin/preseeded-regens/mint':
      '/api/v2/player-cards/admin/preseeded-regens/mint',
  '/api/v1/player-cards/inventory': '/api/v2/player-cards/inventory',
  '/api/v1/player-cards/listings': '/api/v2/player-cards/listings',
  '/api/v1/player-cards/listings/mine': '/api/v2/player-cards/listings/mine',
  '/api/v1/player-cards/listings/{listing_id}/buy':
      '/api/v2/player-cards/listings/{listing_id}/buy',
  '/api/v1/player-cards/listings/{listing_id}/cancel':
      '/api/v2/player-cards/listings/{listing_id}/cancel',
  '/api/v1/player-cards/loans': '/api/v2/player-cards/loans',
  '/api/v1/player-cards/loans/contracts/{loan_contract_id}/return':
      '/api/v2/player-cards/loans/contracts/{loan_contract_id}/return',
  '/api/v1/player-cards/loans/{loan_listing_id}/borrow':
      '/api/v2/player-cards/loans/{loan_listing_id}/borrow',
  '/api/v1/player-cards/marketplace/listings':
      '/api/v2/player-cards/marketplace/listings',
  '/api/v1/player-cards/marketplace/loans':
      '/api/v2/player-cards/marketplace/loans',
  '/api/v1/player-cards/marketplace/loans/contracts':
      '/api/v2/player-cards/marketplace/loans/contracts',
  '/api/v1/player-cards/marketplace/loans/contracts/{contract_id}/return':
      '/api/v2/player-cards/marketplace/loans/contracts/{contract_id}/return',
  '/api/v1/player-cards/marketplace/loans/contracts/{contract_id}/settle':
      '/api/v2/player-cards/marketplace/loans/contracts/{contract_id}/settle',
  '/api/v1/player-cards/marketplace/loans/negotiations/{negotiation_id}/accept':
      '/api/v2/player-cards/marketplace/loans/negotiations/{negotiation_id}/accept',
  '/api/v1/player-cards/marketplace/loans/negotiations/{negotiation_id}/counter':
      '/api/v2/player-cards/marketplace/loans/negotiations/{negotiation_id}/counter',
  '/api/v1/player-cards/marketplace/loans/{listing_id}/cancel':
      '/api/v2/player-cards/marketplace/loans/{listing_id}/cancel',
  '/api/v1/player-cards/marketplace/loans/{listing_id}/negotiations':
      '/api/v2/player-cards/marketplace/loans/{listing_id}/negotiations',
  '/api/v1/player-cards/marketplace/sales':
      '/api/v2/player-cards/marketplace/sales',
  '/api/v1/player-cards/marketplace/sales/{listing_id}/buy':
      '/api/v2/player-cards/marketplace/sales/{listing_id}/buy',
  '/api/v1/player-cards/marketplace/sales/{listing_id}/cancel':
      '/api/v2/player-cards/marketplace/sales/{listing_id}/cancel',
  '/api/v1/player-cards/marketplace/swaps':
      '/api/v2/player-cards/marketplace/swaps',
  '/api/v1/player-cards/marketplace/swaps/{listing_id}/cancel':
      '/api/v2/player-cards/marketplace/swaps/{listing_id}/cancel',
  '/api/v1/player-cards/marketplace/swaps/{listing_id}/execute':
      '/api/v2/player-cards/marketplace/swaps/{listing_id}/execute',
  '/api/v1/player-cards/players': '/api/v2/player-cards/players',
  '/api/v1/player-cards/players/{player_id}':
      '/api/v2/player-cards/players/{player_id}',
  '/api/v1/player-cards/starter-rental': '/api/v2/player-cards/starter-rental',
  '/api/v1/player-cards/watchlist': '/api/v2/player-cards/watchlist',
  '/api/v1/player-cards/watchlist/{watchlist_id}':
      '/api/v2/player-cards/watchlist/{watchlist_id}',
  '/api/v1/player-history': '/api/v2/player-history',
  '/api/v1/player-history/{player_id}': '/api/v2/player-history/{player_id}',
  '/api/v1/player-import/youth-prospects/me':
      '/api/v2/player-import/youth-prospects/me',
  '/api/v1/player-import/youth-prospects/{club_id}':
      '/api/v2/player-import/youth-prospects/{club_id}',
  '/api/v1/players': '/api/v2/players',
  '/api/v1/players/events': '/api/v2/players/events',
  '/api/v1/players/markets': '/api/v2/players/markets',
  '/api/v1/players/match': '/api/v2/players/match',
  '/api/v1/players/me/match-profile': '/api/v2/players/me/match-profile',
  '/api/v1/players/me/shares/holdings': '/api/v2/players/me/shares/holdings',
  '/api/v1/players/real-universe': '/api/v2/players/real-universe',
  '/api/v1/players/real-universe/search':
      '/api/v2/players/real-universe/search',
  '/api/v1/players/real-universe/{player_id}':
      '/api/v2/players/real-universe/{player_id}',
  '/api/v1/players/summaries/recent': '/api/v2/players/summaries/recent',
  '/api/v1/players/{player_id}': '/api/v2/players/{player_id}',
  '/api/v1/players/{player_id}/agency': '/api/v2/players/{player_id}/agency',
  '/api/v1/players/{player_id}/agency/contract-decision':
      '/api/v2/players/{player_id}/agency/contract-decision',
  '/api/v1/players/{player_id}/agency/transfer-decision':
      '/api/v2/players/{player_id}/agency/transfer-decision',
  '/api/v1/players/{player_id}/availability':
      '/api/v2/players/{player_id}/availability',
  '/api/v1/players/{player_id}/avatar': '/api/v2/players/{player_id}/avatar',
  '/api/v1/players/{player_id}/career': '/api/v2/players/{player_id}/career',
  '/api/v1/players/{player_id}/career-events':
      '/api/v2/players/{player_id}/career-events',
  '/api/v1/players/{player_id}/career/summary':
      '/api/v2/players/{player_id}/career/summary',
  '/api/v1/players/{player_id}/contracts':
      '/api/v2/players/{player_id}/contracts',
  '/api/v1/players/{player_id}/contracts/summary':
      '/api/v2/players/{player_id}/contracts/summary',
  '/api/v1/players/{player_id}/contracts/{contract_id}/renew':
      '/api/v2/players/{player_id}/contracts/{contract_id}/renew',
  '/api/v1/players/{player_id}/dna': '/api/v2/players/{player_id}/dna',
  '/api/v1/players/{player_id}/events': '/api/v2/players/{player_id}/events',
  '/api/v1/players/{player_id}/injuries':
      '/api/v2/players/{player_id}/injuries',
  '/api/v1/players/{player_id}/injuries/{injury_id}/recover':
      '/api/v2/players/{player_id}/injuries/{injury_id}/recover',
  '/api/v1/players/{player_id}/interviews':
      '/api/v2/players/{player_id}/interviews',
  '/api/v1/players/{player_id}/lifecycle-snapshot':
      '/api/v2/players/{player_id}/lifecycle-snapshot',
  '/api/v1/players/{player_id}/overview':
      '/api/v2/players/{player_id}/overview',
  '/api/v1/players/{player_id}/personality':
      '/api/v2/players/{player_id}/personality',
  '/api/v1/players/{player_id}/regen': '/api/v2/players/{player_id}/regen',
  '/api/v1/players/{player_id}/regen/big-club-approaches':
      '/api/v2/players/{player_id}/regen/big-club-approaches',
  '/api/v1/players/{player_id}/regen/contract-offers/quote':
      '/api/v2/players/{player_id}/regen/contract-offers/quote',
  '/api/v1/players/{player_id}/regen/offer-market':
      '/api/v2/players/{player_id}/regen/offer-market',
  '/api/v1/players/{player_id}/regen/pressure-resolution':
      '/api/v2/players/{player_id}/regen/pressure-resolution',
  '/api/v1/players/{player_id}/regen/special-training':
      '/api/v2/players/{player_id}/regen/special-training',
  '/api/v1/players/{player_id}/regen/transfer-listing':
      '/api/v2/players/{player_id}/regen/transfer-listing',
  '/api/v1/players/{player_id}/rivalries':
      '/api/v2/players/{player_id}/rivalries',
  '/api/v1/players/{player_id}/shares/buy':
      '/api/v2/players/{player_id}/shares/buy',
  '/api/v1/players/{player_id}/shares/dividends':
      '/api/v2/players/{player_id}/shares/dividends',
  '/api/v1/players/{player_id}/shares/events':
      '/api/v2/players/{player_id}/shares/events',
  '/api/v1/players/{player_id}/shares/issue':
      '/api/v2/players/{player_id}/shares/issue',
  '/api/v1/players/{player_id}/shares/market':
      '/api/v2/players/{player_id}/shares/market',
  '/api/v1/players/{player_id}/shares/performance':
      '/api/v2/players/{player_id}/shares/performance',
  '/api/v1/players/{player_id}/shares/sell':
      '/api/v2/players/{player_id}/shares/sell',
  '/api/v1/players/{player_id}/story': '/api/v2/players/{player_id}/story',
  '/api/v1/players/{player_id}/summary': '/api/v2/players/{player_id}/summary',
  '/api/v1/policies/acceptances': '/api/v2/policies/acceptances',
  '/api/v1/policies/country/{country_code}':
      '/api/v2/policies/country/{country_code}',
  '/api/v1/policies/documents': '/api/v2/policies/documents',
  '/api/v1/policies/documents/{document_key}':
      '/api/v2/policies/documents/{document_key}',
  '/api/v1/policies/me/acceptances': '/api/v2/policies/me/acceptances',
  '/api/v1/policies/me/compliance': '/api/v2/policies/me/compliance',
  '/api/v1/policies/me/region': '/api/v2/policies/me/region',
  '/api/v1/policies/me/requirements': '/api/v2/policies/me/requirements',
  '/api/v1/portfolio': '/api/v2/portfolio',
  '/api/v1/portfolio/snapshot': '/api/v2/portfolio/snapshot',
  '/api/v1/portfolio/summary': '/api/v2/portfolio/summary',
  '/api/v1/portfolios/me': '/api/v2/portfolios/me',
  '/api/v1/predictions': '/api/v2/predictions',
  '/api/v1/predictions/leaderboard': '/api/v2/predictions/leaderboard',
  '/api/v1/pundits/matches/{match_key}': '/api/v2/pundits/matches/{match_key}',
  '/api/v1/rankings/clubs': '/api/v2/rankings/clubs',
  '/api/v1/rankings/global': '/api/v2/rankings/global',
  '/api/v1/rankings/players': '/api/v2/rankings/players',
  '/api/v1/ready': '/ready',
  '/api/v1/real-world/events': '/api/v2/real-world/events',
  '/api/v1/real-world/hybrid-players': '/api/v2/real-world/hybrid-players',
  '/api/v1/real-world/normalize': '/api/v2/real-world/normalize',
  '/api/v1/real-world/players': '/api/v2/real-world/players',
  '/api/v1/real-world/players/{real_player_id}':
      '/api/v2/real-world/players/{real_player_id}',
  '/api/v1/real-world/providers': '/api/v2/real-world/providers',
  '/api/v1/real-world/settings/me': '/api/v2/real-world/settings/me',
  '/api/v1/realtime/matches/{match_id}/gateway':
      '/api/v2/realtime/matches/{match_id}/gateway',
  '/api/v1/realtime/matches/{match_id}/stream':
      '/api/v2/realtime/matches/{match_id}/stream',
  '/api/v1/realtime/status': '/api/v2/realtime/status',
  '/api/v1/realtime/stream': '/api/v2/realtime/stream',
  '/api/v1/realtime/wallet/gateway': '/api/v2/realtime/wallet/gateway',
  '/api/v1/realtime/wallet/stream': '/api/v2/realtime/wallet/stream',
  '/api/v1/referrals/attribution': '/api/v2/referrals/attribution',
  '/api/v1/referrals/me/invites': '/api/v2/referrals/me/invites',
  '/api/v1/referrals/me/rewards': '/api/v2/referrals/me/rewards',
  '/api/v1/referrals/me/summary': '/api/v2/referrals/me/summary',
  '/api/v1/referrals/share-codes': '/api/v2/referrals/share-codes',
  '/api/v1/referrals/share-codes/me': '/api/v2/referrals/share-codes/me',
  '/api/v1/referrals/share-codes/{code}/redeem':
      '/api/v2/referrals/share-codes/{code}/redeem',
  '/api/v1/referrals/share-codes/{share_code_id}':
      '/api/v2/referrals/share-codes/{share_code_id}',
  '/api/v1/regen-hype': '/api/v2/regen-hype',
  '/api/v1/regen-universe/achievements': '/api/v2/regen-universe/achievements',
  '/api/v1/regen-universe/awards': '/api/v2/regen-universe/awards',
  '/api/v1/regen-universe/bloodlines': '/api/v2/regen-universe/bloodlines',
  '/api/v1/regen-universe/hall-of-fame': '/api/v2/regen-universe/hall-of-fame',
  '/api/v1/regen-universe/national-regens':
      '/api/v2/regen-universe/national-regens',
  '/api/v1/regen-universe/player/{player_id}':
      '/api/v2/regen-universe/player/{player_id}',
  '/api/v1/regen-universe/players/{player_id}':
      '/api/v2/regen-universe/players/{player_id}',
  '/api/v1/regen-universe/players/{player_id}/timeline':
      '/api/v2/regen-universe/players/{player_id}/timeline',
  '/api/v1/regen-universe/rankings': '/api/v2/regen-universe/rankings',
  '/api/v1/regen-universe/rising-stars': '/api/v2/regen-universe/rising-stars',
  '/api/v1/regen-universe/scouting-feed':
      '/api/v2/regen-universe/scouting-feed',
  '/api/v1/regen-universe/seasons': '/api/v2/regen-universe/seasons',
  '/api/v1/regen-universe/tracking': '/api/v2/regen-universe/tracking',
  '/api/v1/regen-universe/youth-tournaments':
      '/api/v2/regen-universe/youth-tournaments',
  '/api/v1/regen-universe/youth-tournaments/{tournament_id}':
      '/api/v2/regen-universe/youth-tournaments/{tournament_id}',
  '/api/v1/regens/awards': '/api/v2/regens/awards',
  '/api/v1/regens/awards/{award_id}/vote':
      '/api/v2/regens/awards/{award_id}/vote',
  '/api/v1/regens/creation-orders': '/api/v2/regens/creation-orders',
  '/api/v1/regens/creation-orders/{order_id}':
      '/api/v2/regens/creation-orders/{order_id}',
  '/api/v1/regens/creation-orders/{order_id}/generate-after-payment':
      '/api/v2/regens/creation-orders/{order_id}/generate-after-payment',
  '/api/v1/regens/creation-orders/{order_id}/pay-with-wallet':
      '/api/v2/regens/creation-orders/{order_id}/pay-with-wallet',
  '/api/v1/regens/feed': '/api/v2/regens/feed',
  '/api/v1/regens/jobs/{job_name}': '/api/v2/regens/jobs/{job_name}',
  '/api/v1/regens/request-son': '/api/v2/regens/request-son',
  '/api/v1/regens/request-son/options': '/api/v2/regens/request-son/options',
  '/api/v1/regens/rising': '/api/v2/regens/rising',
  '/api/v1/regens/top': '/api/v2/regens/top',
  '/api/v1/regens/{regen_id}/lineage': '/api/v2/regens/{regen_id}/lineage',
  '/api/v1/rent': '/api/v2/rent',
  '/api/v1/replays/countdown/{fixture_id}':
      '/api/v2/replays/countdown/{fixture_id}',
  '/api/v1/replays/me': '/api/v2/replays/me',
  '/api/v1/replays/public/featured': '/api/v2/replays/public/featured',
  '/api/v1/replays/{replay_id}': '/api/v2/replays/{replay_id}',
  '/api/v1/reward-engine/me/settlements':
      '/api/v2/reward-engine/me/settlements',
  '/api/v1/reward-engine/me/summary': '/api/v2/reward-engine/me/summary',
  '/api/v1/risk-ops/me/aml-cases': '/api/v2/risk-ops/me/aml-cases',
  '/api/v1/risk-ops/me/fraud-cases': '/api/v2/risk-ops/me/fraud-cases',
  '/api/v1/risk-ops/me/overview': '/api/v2/risk-ops/me/overview',
  '/api/v1/risk-ops/me/restrictions': '/api/v2/risk-ops/me/restrictions',
  '/api/v1/risk-ops/me/signals': '/api/v2/risk-ops/me/signals',
  '/api/v1/rivalries/matches': '/api/v2/rivalries/matches',
  '/api/v1/scout/report/{player_id}': '/api/v2/scout/report/{player_id}',
  '/api/v1/scouts': '/api/v2/scouts',
  '/api/v1/scouts/{scout_id}/discover': '/api/v2/scouts/{scout_id}/discover',
  '/api/v1/season-pass': '/api/v2/season-pass',
  '/api/v1/season-pass/claim': '/api/v2/season-pass/claim',
  '/api/v1/season-pass/me': '/api/v2/season-pass/me',
  '/api/v1/season-pass/rewards/{reward_id}/claim':
      '/api/v2/season-pass/rewards/{reward_id}/claim',
  '/api/v1/season/current': '/api/v2/season/current',
  '/api/v1/season/history': '/api/v2/season/history',
  '/api/v1/session/bootstrap': '/api/v2/session/bootstrap',
  '/api/v1/shows/debate': '/api/v2/shows/debate',
  '/api/v1/shows/post-match/{match_id}': '/api/v2/shows/post-match/{match_id}',
  '/api/v1/shows/pre-match/{match_id}': '/api/v2/shows/pre-match/{match_id}',
  '/api/v1/simulation-matchmaking/hosted-competitions/preview':
      '/api/v2/simulation-matchmaking/hosted-competitions/preview',
  '/api/v1/simulation-matchmaking/profiles/{user_id}':
      '/api/v2/simulation-matchmaking/profiles/{user_id}',
  '/api/v1/simulation-matchmaking/quick-game':
      '/api/v2/simulation-matchmaking/quick-game',
  '/api/v1/simulation-matchmaking/quick-tournament':
      '/api/v2/simulation-matchmaking/quick-tournament',
  '/api/v1/social/clubs/{club_id}/community':
      '/api/v2/social/clubs/{club_id}/community',
  '/api/v1/social/clubs/{club_id}/community/messages':
      '/api/v2/social/clubs/{club_id}/community/messages',
  '/api/v1/social/feed': '/api/v2/social/feed',
  '/api/v1/social/follows': '/api/v2/social/follows',
  '/api/v1/social/follows/me': '/api/v2/social/follows/me',
  '/api/v1/social/profile/me': '/api/v2/social/profile/me',
  '/api/v1/social/rivalries/{club_a_id}/{club_b_id}':
      '/api/v2/social/rivalries/{club_a_id}/{club_b_id}',
  '/api/v1/social/rivalries/{club_a_id}/{club_b_id}/banter':
      '/api/v2/social/rivalries/{club_a_id}/{club_b_id}/banter',
  '/api/v1/sponsors': '/api/v2/sponsors',
  '/api/v1/sponsorship/clubs/{club_id}/contracts':
      '/api/v2/sponsorship/clubs/{club_id}/contracts',
  '/api/v1/sponsorship/clubs/{club_id}/dashboard':
      '/api/v2/sponsorship/clubs/{club_id}/dashboard',
  '/api/v1/sponsorship/clubs/{club_id}/offers':
      '/api/v2/sponsorship/clubs/{club_id}/offers',
  '/api/v1/sponsorship/clubs/{club_id}/sponsors':
      '/api/v2/sponsorship/clubs/{club_id}/sponsors',
  '/api/v1/sponsorship/contracts/request':
      '/api/v2/sponsorship/contracts/request',
  '/api/v1/sponsorship/me/leads': '/api/v2/sponsorship/me/leads',
  '/api/v1/sponsorship/packages': '/api/v2/sponsorship/packages',
  '/api/v1/sponsorship/placements': '/api/v2/sponsorship/placements',
  '/api/v1/story-feed': '/api/v2/story-feed',
  '/api/v1/story-feed/digest': '/api/v2/story-feed/digest',
  '/api/v1/streamer-tournaments': '/api/v2/streamer-tournaments',
  '/api/v1/streamer-tournaments/mine': '/api/v2/streamer-tournaments/mine',
  '/api/v1/streamer-tournaments/{tournament_id}':
      '/api/v2/streamer-tournaments/{tournament_id}',
  '/api/v1/streamer-tournaments/{tournament_id}/invites':
      '/api/v2/streamer-tournaments/{tournament_id}/invites',
  '/api/v1/streamer-tournaments/{tournament_id}/join':
      '/api/v2/streamer-tournaments/{tournament_id}/join',
  '/api/v1/streamer-tournaments/{tournament_id}/publish':
      '/api/v2/streamer-tournaments/{tournament_id}/publish',
  '/api/v1/streamer-tournaments/{tournament_id}/rewards':
      '/api/v2/streamer-tournaments/{tournament_id}/rewards',
  '/api/v1/surveillance/circular-trade-alerts':
      '/api/v2/surveillance/circular-trade-alerts',
  '/api/v1/surveillance/holder-concentration-alerts':
      '/api/v2/surveillance/holder-concentration-alerts',
  '/api/v1/surveillance/suspicious-clusters':
      '/api/v2/surveillance/suspicious-clusters',
  '/api/v1/surveillance/suspicious-players':
      '/api/v2/surveillance/suspicious-players',
  '/api/v1/surveillance/thin-market-alerts':
      '/api/v2/surveillance/thin-market-alerts',
  '/api/v1/sync/update': '/api/v2/sync/update',
  '/api/v1/tickets/attendance/{match_id}/react':
      '/api/v2/tickets/attendance/{match_id}/react',
  '/api/v1/tickets/buy': '/api/v2/tickets/buy',
  '/api/v1/tickets/event/{match_id}': '/api/v2/tickets/event/{match_id}',
  '/api/v1/tickets/resell': '/api/v2/tickets/resell',
  '/api/v1/tickets/waitlist': '/api/v2/tickets/waitlist',
  '/api/v1/tournaments': '/api/v2/tournaments',
  '/api/v1/tournaments/{tournament_id}': '/api/v2/tournaments/{tournament_id}',
  '/api/v1/tournaments/{tournament_id}/advance':
      '/api/v2/tournaments/{tournament_id}/advance',
  '/api/v1/tournaments/{tournament_id}/join':
      '/api/v2/tournaments/{tournament_id}/join',
  '/api/v1/tournaments/{tournament_id}/matches/{match_id}/result':
      '/api/v2/tournaments/{tournament_id}/matches/{match_id}/result',
  '/api/v1/trader/markets': '/api/v2/trader/markets',
  '/api/v1/trader/orders': '/api/v2/trader/orders',
  '/api/v1/trader/overview': '/api/v2/trader/overview',
  '/api/v1/trader/p2p': '/api/v2/trader/p2p',
  '/api/v1/trader/security/totp/setup': '/api/v2/trader/security/totp/setup',
  '/api/v1/trader/watchlist': '/api/v2/trader/watchlist',
  '/api/v1/transfer-market/clubs/{club_id}/team-dynamics':
      '/api/v2/transfer-market/clubs/{club_id}/team-dynamics',
  '/api/v1/transfer-market/coaches/{club_id}/demands':
      '/api/v2/transfer-market/coaches/{club_id}/demands',
  '/api/v1/transfer-market/coaches/{club_id}/profile':
      '/api/v2/transfer-market/coaches/{club_id}/profile',
  '/api/v1/transfer-market/jobs/run': '/api/v2/transfer-market/jobs/run',
  '/api/v1/transfer-market/listings': '/api/v2/transfer-market/listings',
  '/api/v1/transfer-market/listings/{listing_id}':
      '/api/v2/transfer-market/listings/{listing_id}',
  '/api/v1/transfer-market/listings/{listing_id}/bids':
      '/api/v2/transfer-market/listings/{listing_id}/bids',
  '/api/v1/transfer-market/listings/{listing_id}/close':
      '/api/v2/transfer-market/listings/{listing_id}/close',
  '/api/v1/transfer-market/listings/{listing_id}/contract-offer':
      '/api/v2/transfer-market/listings/{listing_id}/contract-offer',
  '/api/v1/transfer-market/listings/{listing_id}/negotiation':
      '/api/v2/transfer-market/listings/{listing_id}/negotiation',
  '/api/v1/transfer-market/listings/{listing_id}/stream':
      '/api/v2/transfer-market/listings/{listing_id}/stream',
  '/api/v1/transfer-market/players/{player_id}/decision-profile':
      '/api/v2/transfer-market/players/{player_id}/decision-profile',
  '/api/v1/transfer-market/watchlist': '/api/v2/transfer-market/watchlist',
  '/api/v1/transfers/windows': '/api/v2/transfers/windows',
  '/api/v1/transfers/windows/{window_id}':
      '/api/v2/transfers/windows/{window_id}',
  '/api/v1/transfers/windows/{window_id}/bids':
      '/api/v2/transfers/windows/{window_id}/bids',
  '/api/v1/transfers/windows/{window_id}/bids/{bid_id}/accept':
      '/api/v2/transfers/windows/{window_id}/bids/{bid_id}/accept',
  '/api/v1/transfers/windows/{window_id}/bids/{bid_id}/reject':
      '/api/v2/transfers/windows/{window_id}/bids/{bid_id}/reject',
  '/api/v1/transfers/windows/{window_id}/players/{player_id}/regen-bid-evaluations':
      '/api/v2/transfers/windows/{window_id}/players/{player_id}/regen-bid-evaluations',
  '/api/v1/transfers/windows/{window_id}/players/{player_id}/resolve-regen-bid':
      '/api/v2/transfers/windows/{window_id}/players/{player_id}/resolve-regen-bid',
  '/api/v1/trust/me': '/api/v2/trust/me',
  '/api/v1/trust/{user_id}': '/api/v2/trust/{user_id}',
  '/api/v1/ultimate-league/competitors/{competitor_id}':
      '/api/v2/ultimate-league/competitors/{competitor_id}',
  '/api/v1/ultimate-league/matches/result':
      '/api/v2/ultimate-league/matches/result',
  '/api/v1/ultimate-league/matchmaking/batch':
      '/api/v2/ultimate-league/matchmaking/batch',
  '/api/v1/ultimate-league/standings/{tier}':
      '/api/v2/ultimate-league/standings/{tier}',
  '/api/v1/ultimate-league/tactical-presets':
      '/api/v2/ultimate-league/tactical-presets',
  '/api/v1/ultimate-league/tactical-presets/{preset_id}/purchase':
      '/api/v2/ultimate-league/tactical-presets/{preset_id}/purchase',
  '/api/v1/ultimate-league/tiers': '/api/v2/ultimate-league/tiers',
  '/api/v1/ultimate-league/tournaments': '/api/v2/ultimate-league/tournaments',
  '/api/v1/ultimate-league/tournaments/{tournament_id}':
      '/api/v2/ultimate-league/tournaments/{tournament_id}',
  '/api/v1/ultimate-league/tournaments/{tournament_id}/payouts/preview':
      '/api/v2/ultimate-league/tournaments/{tournament_id}/payouts/preview',
  '/api/v1/users/me': '/api/v2/users/me',
  '/api/v1/users/me/profile': '/api/v2/users/me/profile',
  '/api/v1/users/suggestions': '/api/v2/users/suggestions',
  '/api/v1/users/{user_id}/followers': '/api/v2/users/{user_id}/followers',
  '/api/v1/users/{user_id}/following': '/api/v2/users/{user_id}/following',
  '/api/v1/v2/broadcast/pay': '/api/v2/broadcast/pay',
  '/api/v1/v2/broadcast/{match_id}': '/api/v2/broadcast/{match_id}',
  '/api/v1/v2/clubs/list': '/api/v2/clubs/list',
  '/api/v1/v2/clubs/marketplace': '/api/v2/clubs/marketplace',
  '/api/v1/v2/clubs/offer': '/api/v2/clubs/offer',
  '/api/v1/v2/clubs/{club_id}/fans': '/api/v2/clubs/{club_id}/fans',
  '/api/v1/v2/clubs/{club_id}/finances': '/api/v2/clubs/{club_id}/finances',
  '/api/v1/v2/clubs/{club_id}/squad': '/api/v2/clubs/{club_id}/squad',
  '/api/v1/v2/competitions': '/api/v2/competitions',
  '/api/v1/v2/federations': '/api/v2/federations',
  '/api/v1/v2/federations/vote': '/api/v2/federations/vote',
  '/api/v1/v2/federations/{federation_id}/join':
      '/api/v2/federations/{federation_id}/join',
  '/api/v1/v2/feed': '/api/v2/feed',
  '/api/v1/v2/history/records': '/api/v2/history/records',
  '/api/v1/v2/home/dashboard': '/api/v2/home/dashboard',
  '/api/v1/v2/market/bid': '/api/v2/market/bid',
  '/api/v1/v2/market/listings': '/api/v2/market/listings',
  '/api/v1/v2/matches/{match_id}': '/api/v2/matches/{match_id}',
  '/api/v1/v2/players/{player_id}': '/api/v2/players/{player_id}',
  '/api/v1/v2/regens': '/api/v2/regens',
  '/api/v1/v2/stories': '/api/v2/stories',
  '/api/v1/v2/stories/generate': '/api/v2/stories/generate',
  '/api/v1/v2/tasks': '/api/v2/tasks',
  '/api/v1/v2/tasks/{task_id}/claim': '/api/v2/tasks/{task_id}/claim',
  '/api/v1/v2/tournaments/{tournament_id}':
      '/api/v2/tournaments/{tournament_id}',
  '/api/v1/v2/tournaments/{tournament_id}/join':
      '/api/v2/tournaments/{tournament_id}/join',
  '/api/v1/v2/tournaments/{tournament_id}/rent':
      '/api/v2/tournaments/{tournament_id}/rent',
  '/api/v1/v2/tournaments/{tournament_id}/squad':
      '/api/v2/tournaments/{tournament_id}/squad',
  '/api/v1/v2/users/{user_id}': '/api/v2/users/{user_id}',
  '/api/v1/v2/users/{user_id}/follow': '/api/v2/users/{user_id}/follow',
  '/api/v1/v2/ws/market/{listing_id}': '/api/v2/ws/market/{listing_id}',
  '/api/v1/v2/ws/match/{match_id}': '/api/v2/ws/match/{match_id}',
  '/api/v1/v2/ws/notifications': '/api/v2/ws/notifications',
  '/api/v1/value-engine/snapshots/rebuild':
      '/api/v2/value-engine/snapshots/rebuild',
  '/api/v1/value-engine/snapshots/{player_id}/daily-closes':
      '/api/v2/value-engine/snapshots/{player_id}/daily-closes',
  '/api/v1/value-engine/snapshots/{player_id}/history':
      '/api/v2/value-engine/snapshots/{player_id}/history',
  '/api/v1/value-engine/snapshots/{player_id}/latest':
      '/api/v2/value-engine/snapshots/{player_id}/latest',
  '/api/v1/value-engine/snapshots/{player_id}/trend-summary':
      '/api/v2/value-engine/snapshots/{player_id}/trend-summary',
  '/api/v1/version': '/version',
  '/api/v1/viral/accounts': '/api/v2/viral/accounts',
  '/api/v1/viral/cascades': '/api/v2/viral/cascades',
  '/api/v1/viral/clips/trending': '/api/v2/viral/clips/trending',
  '/api/v1/viral/clips/{clip_id}/variants':
      '/api/v2/viral/clips/{clip_id}/variants',
  '/api/v1/viral/clips/{clip_id}/winner':
      '/api/v2/viral/clips/{clip_id}/winner',
  '/api/v1/viral/feed': '/api/v2/viral/feed',
  '/api/v1/viral/feed/for-you': '/api/v2/viral/feed/for-you',
  '/api/v1/viral/matches/{match_key}/clips':
      '/api/v2/viral/matches/{match_key}/clips',
  '/api/v1/viral/sessions/{session_id}': '/api/v2/viral/sessions/{session_id}',
  '/api/v1/wallet': '/api/v2/wallet',
  '/api/v1/wallet/top-up/initiate': '/api/v2/wallet/top-up/initiate',
  '/api/v1/wallet/top-up/verify': '/api/v2/wallet/top-up/verify',
  '/api/v1/wallet/transactions': '/api/v2/wallet/transactions',
  '/api/v1/wallets': '/api/v2/wallets',
  '/api/v1/wallets/accounts': '/api/v2/wallets/accounts',
  '/api/v1/wallets/adaptive-overview': '/api/v2/wallets/adaptive-overview',
  '/api/v1/wallets/conversions': '/api/v2/wallets/conversions',
  '/api/v1/wallets/conversions/quote': '/api/v2/wallets/conversions/quote',
  '/api/v1/wallets/deposits': '/api/v2/wallets/deposits',
  '/api/v1/wallets/deposits/{deposit_id}/submit':
      '/api/v2/wallets/deposits/{deposit_id}/submit',
  '/api/v1/wallets/ledger': '/api/v2/wallets/ledger',
  '/api/v1/wallets/market-topups': '/api/v2/wallets/market-topups',
  '/api/v1/wallets/overview': '/api/v2/wallets/overview',
  '/api/v1/wallets/payment-events': '/api/v2/wallets/payment-events',
  '/api/v1/wallets/providers/{provider_key}/webhook':
      '/api/v2/wallets/providers/{provider_key}/webhook',
  '/api/v1/wallets/purchase-orders': '/api/v2/wallets/purchase-orders',
  '/api/v1/wallets/purchase-orders/quote':
      '/api/v2/wallets/purchase-orders/quote',
  '/api/v1/wallets/purchase-orders/{order_id}':
      '/api/v2/wallets/purchase-orders/{order_id}',
  '/api/v1/wallets/summary': '/api/v2/wallets/summary',
  '/api/v1/wallets/top-up/initiate': '/api/v2/wallets/top-up/initiate',
  '/api/v1/wallets/top-up/verify': '/api/v2/wallets/top-up/verify',
  '/api/v1/wallets/transactions': '/api/v2/wallets/transactions',
  '/api/v1/wallets/withdrawals': '/api/v2/wallets/withdrawals',
  '/api/v1/wallets/withdrawals/eligibility':
      '/api/v2/wallets/withdrawals/eligibility',
  '/api/v1/wallets/withdrawals/quote': '/api/v2/wallets/withdrawals/quote',
  '/api/v1/wallets/withdrawals/{withdrawal_id}/receipt':
      '/api/v2/wallets/withdrawals/{withdrawal_id}/receipt',
  '/api/v1/world-super-cup/countdown': '/api/v2/world-super-cup/countdown',
  '/api/v1/world-super-cup/groups/table':
      '/api/v2/world-super-cup/groups/table',
  '/api/v1/world-super-cup/knockout/bracket':
      '/api/v2/world-super-cup/knockout/bracket',
  '/api/v1/world-super-cup/playoff/draw':
      '/api/v2/world-super-cup/playoff/draw',
  '/api/v1/world-super-cup/qualification/explanation':
      '/api/v2/world-super-cup/qualification/explanation',
  '/api/v1/world/clubs/{club_id}/context':
      '/api/v2/world/clubs/{club_id}/context',
  '/api/v1/world/competitions/{competition_id}/context':
      '/api/v2/world/competitions/{competition_id}/context',
  '/api/v1/world/cultures': '/api/v2/world/cultures',
  '/api/v1/world/narratives': '/api/v2/world/narratives',
  '/api/v1/ws/match/{match_id}': '/api/v2/ws/match/{match_id}',
  '/api/v1/ws/spectate/{match_id}': '/api/v2/ws/spectate/{match_id}',
  '/api/v1/ws/tournament/{tournament_id}':
      '/api/v2/ws/tournament/{tournament_id}',
  '/api/v2/academy': '/api/v2/academy',
  '/api/v2/academy/awards': '/api/v2/academy/awards',
  '/api/v2/academy/fixtures': '/api/v2/academy/fixtures',
  '/api/v2/academy/generate': '/api/v2/academy/generate',
  '/api/v2/academy/promote/{player_id}': '/api/v2/academy/promote/{player_id}',
  '/api/v2/academy/qualification': '/api/v2/academy/qualification',
  '/api/v2/academy/registration': '/api/v2/academy/registration',
  '/api/v2/academy/season-summary': '/api/v2/academy/season-summary',
  '/api/v2/academy/standings': '/api/v2/academy/standings',
  '/api/v2/admin/access': '/api/v2/admin/access',
  '/api/v2/admin/access/permissions': '/api/v2/admin/access/permissions',
  '/api/v2/admin/access/{user_id}/permissions':
      '/api/v2/admin/access/{user_id}/permissions',
  '/api/v2/admin/analytics/agent-learning':
      '/api/v2/admin/analytics/agent-learning',
  '/api/v2/admin/analytics/anomalies': '/api/v2/admin/analytics/anomalies',
  '/api/v2/admin/analytics/funnels': '/api/v2/admin/analytics/funnels',
  '/api/v2/admin/analytics/match-outcomes':
      '/api/v2/admin/analytics/match-outcomes',
  '/api/v2/admin/analytics/player-matching':
      '/api/v2/admin/analytics/player-matching',
  '/api/v2/admin/analytics/player-matching/recompute-weights':
      '/api/v2/admin/analytics/player-matching/recompute-weights',
  '/api/v2/admin/analytics/price-predictions':
      '/api/v2/admin/analytics/price-predictions',
  '/api/v2/admin/analytics/summary': '/api/v2/admin/analytics/summary',
  '/api/v2/admin/analytics/user-segments':
      '/api/v2/admin/analytics/user-segments',
  '/api/v2/admin/calendar-engine/events':
      '/api/v2/admin/calendar-engine/events',
  '/api/v2/admin/calendar-engine/hosted-competitions/{competition_id}/launch':
      '/api/v2/admin/calendar-engine/hosted-competitions/{competition_id}/launch',
  '/api/v2/admin/calendar-engine/national-competitions/{competition_id}/launch':
      '/api/v2/admin/calendar-engine/national-competitions/{competition_id}/launch',
  '/api/v2/admin/calendar-engine/seasons':
      '/api/v2/admin/calendar-engine/seasons',
  '/api/v2/admin/clubs/academy-analytics':
      '/api/v2/admin/clubs/academy-analytics',
  '/api/v2/admin/clubs/analytics': '/api/v2/admin/clubs/analytics',
  '/api/v2/admin/clubs/finance-analytics':
      '/api/v2/admin/clubs/finance-analytics',
  '/api/v2/admin/clubs/ops-summary': '/api/v2/admin/clubs/ops-summary',
  '/api/v2/admin/clubs/scouting-analytics':
      '/api/v2/admin/clubs/scouting-analytics',
  '/api/v2/admin/clubs/sponsorship-analytics':
      '/api/v2/admin/clubs/sponsorship-analytics',
  '/api/v2/admin/clubs/summary': '/api/v2/admin/clubs/summary',
  '/api/v2/admin/clubs/{club_id}': '/api/v2/admin/clubs/{club_id}',
  '/api/v2/admin/clubs/{club_id}/moderate-branding':
      '/api/v2/admin/clubs/{club_id}/moderate-branding',
  '/api/v2/admin/competitions': '/api/v2/admin/competitions',
  '/api/v2/admin/competitions/reminders/dispatch':
      '/api/v2/admin/competitions/reminders/dispatch',
  '/api/v2/admin/competitive-integrity/matches/{match_id}/validation':
      '/api/v2/admin/competitive-integrity/matches/{match_id}/validation',
  '/api/v2/admin/competitive-integrity/workers/run-once':
      '/api/v2/admin/competitive-integrity/workers/run-once',
  '/api/v2/admin/creator/applications': '/api/v2/admin/creator/applications',
  '/api/v2/admin/creator/applications/{application_id}/approve':
      '/api/v2/admin/creator/applications/{application_id}/approve',
  '/api/v2/admin/creator/applications/{application_id}/reject':
      '/api/v2/admin/creator/applications/{application_id}/reject',
  '/api/v2/admin/creator/applications/{application_id}/request-verification':
      '/api/v2/admin/creator/applications/{application_id}/request-verification',
  '/api/v2/admin/creator/cards/assign': '/api/v2/admin/creator/cards/assign',
  '/api/v2/admin/creator/dashboard': '/api/v2/admin/creator/dashboard',
  '/api/v2/admin/creator/fan-share-market/control':
      '/api/v2/admin/creator/fan-share-market/control',
  '/api/v2/admin/discovery/featured-rails':
      '/api/v2/admin/discovery/featured-rails',
  '/api/v2/admin/fan-wars/creator-country-assignments':
      '/api/v2/admin/fan-wars/creator-country-assignments',
  '/api/v2/admin/fan-wars/nations-cup': '/api/v2/admin/fan-wars/nations-cup',
  '/api/v2/admin/fan-wars/nations-cup/{competition_id}/advance':
      '/api/v2/admin/fan-wars/nations-cup/{competition_id}/advance',
  '/api/v2/admin/fan-wars/points': '/api/v2/admin/fan-wars/points',
  '/api/v2/admin/fan-wars/profiles': '/api/v2/admin/fan-wars/profiles',
  '/api/v2/admin/fan-wars/profiles/{profile_id}/rivals/{rival_profile_id}':
      '/api/v2/admin/fan-wars/profiles/{profile_id}/rivals/{rival_profile_id}',
  '/api/v2/admin/federations/run-jobs': '/api/v2/admin/federations/run-jobs',
  '/api/v2/admin/finance/account-controls':
      '/api/v2/admin/finance/account-controls',
  '/api/v2/admin/finance/account-controls/{user_id}':
      '/api/v2/admin/finance/account-controls/{user_id}',
  '/api/v2/admin/finance/control-tower': '/api/v2/admin/finance/control-tower',
  '/api/v2/admin/finance/manual-price-overrides':
      '/api/v2/admin/finance/manual-price-overrides',
  '/api/v2/admin/finance/manual-price-overrides/{asset_type}/{asset_id}':
      '/api/v2/admin/finance/manual-price-overrides/{asset_type}/{asset_id}',
  '/api/v2/admin/finance/match-kill-switches':
      '/api/v2/admin/finance/match-kill-switches',
  '/api/v2/admin/finance/match-kill-switches/{match_id}':
      '/api/v2/admin/finance/match-kill-switches/{match_id}',
  '/api/v2/admin/finance/reconciliation':
      '/api/v2/admin/finance/reconciliation',
  '/api/v2/admin/finance/simulate': '/api/v2/admin/finance/simulate',
  '/api/v2/admin/finance/wallet-protection':
      '/api/v2/admin/finance/wallet-protection',
  '/api/v2/admin/god-mode/audit-events': '/api/v2/admin/god-mode/audit-events',
  '/api/v2/admin/god-mode/bootstrap': '/api/v2/admin/god-mode/bootstrap',
  '/api/v2/admin/god-mode/commissions': '/api/v2/admin/god-mode/commissions',
  '/api/v2/admin/god-mode/competition-controls':
      '/api/v2/admin/god-mode/competition-controls',
  '/api/v2/admin/god-mode/high-risk-actions':
      '/api/v2/admin/god-mode/high-risk-actions',
  '/api/v2/admin/god-mode/liquidity/interventions':
      '/api/v2/admin/god-mode/liquidity/interventions',
  '/api/v2/admin/god-mode/payment-rails':
      '/api/v2/admin/god-mode/payment-rails',
  '/api/v2/admin/god-mode/payment-rails/health':
      '/api/v2/admin/god-mode/payment-rails/health',
  '/api/v2/admin/god-mode/roles': '/api/v2/admin/god-mode/roles',
  '/api/v2/admin/god-mode/treasury': '/api/v2/admin/god-mode/treasury',
  '/api/v2/admin/god-mode/treasury/dashboard':
      '/api/v2/admin/god-mode/treasury/dashboard',
  '/api/v2/admin/god-mode/treasury/withdrawals':
      '/api/v2/admin/god-mode/treasury/withdrawals',
  '/api/v2/admin/god-mode/withdrawal-controls':
      '/api/v2/admin/god-mode/withdrawal-controls',
  '/api/v2/admin/god-mode/withdrawals': '/api/v2/admin/god-mode/withdrawals',
  '/api/v2/admin/god-mode/withdrawals/summary':
      '/api/v2/admin/god-mode/withdrawals/summary',
  '/api/v2/admin/god-mode/withdrawals/{payout_request_id}':
      '/api/v2/admin/god-mode/withdrawals/{payout_request_id}',
  '/api/v2/admin/governance/proposals/{proposal_id}/status':
      '/api/v2/admin/governance/proposals/{proposal_id}/status',
  '/api/v2/admin/hosted-competitions': '/api/v2/admin/hosted-competitions',
  '/api/v2/admin/hosted-competitions/seed':
      '/api/v2/admin/hosted-competitions/seed',
  '/api/v2/admin/hosted-competitions/{competition_id}/finalize':
      '/api/v2/admin/hosted-competitions/{competition_id}/finalize',
  '/api/v2/admin/hosted-competitions/{competition_id}/launch':
      '/api/v2/admin/hosted-competitions/{competition_id}/launch',
  '/api/v2/admin/integrity-engine/incidents/{incident_id}/resolve':
      '/api/v2/admin/integrity-engine/incidents/{incident_id}/resolve',
  '/api/v2/admin/integrity-engine/scan': '/api/v2/admin/integrity-engine/scan',
  '/api/v2/admin/managers/audit-log': '/api/v2/admin/managers/audit-log',
  '/api/v2/admin/managers/catalog/{manager_id}/supply':
      '/api/v2/admin/managers/catalog/{manager_id}/supply',
  '/api/v2/admin/managers/competitions': '/api/v2/admin/managers/competitions',
  '/api/v2/admin/managers/competitions/{code}':
      '/api/v2/admin/managers/competitions/{code}',
  '/api/v2/admin/managers/competitions/{code}/orchestrate':
      '/api/v2/admin/managers/competitions/{code}/orchestrate',
  '/api/v2/admin/moderation/reports': '/api/v2/admin/moderation/reports',
  '/api/v2/admin/moderation/reports/summary':
      '/api/v2/admin/moderation/reports/summary',
  '/api/v2/admin/moderation/reports/{report_id}/assign':
      '/api/v2/admin/moderation/reports/{report_id}/assign',
  '/api/v2/admin/moderation/reports/{report_id}/resolve':
      '/api/v2/admin/moderation/reports/{report_id}/resolve',
  '/api/v2/admin/national-team-engine/competitions':
      '/api/v2/admin/national-team-engine/competitions',
  '/api/v2/admin/national-team-engine/competitions/seed-defaults':
      '/api/v2/admin/national-team-engine/competitions/seed-defaults',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads/rotate':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads/rotate',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads/{ad_id}':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/ads/{ad_id}',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/entries':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/entries',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/entries/lock':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/entries/lock',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/lifecycle/advance':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/lifecycle/advance',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/rentals/cleanup':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/rentals/cleanup',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/story-events/generate':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/story-events/generate',
  '/api/v2/admin/national-team-engine/competitions/{competition_id}/theme':
      '/api/v2/admin/national-team-engine/competitions/{competition_id}/theme',
  '/api/v2/admin/national-team-engine/entries/{entry_id}/squad':
      '/api/v2/admin/national-team-engine/entries/{entry_id}/squad',
  '/api/v2/admin/notifications/announcements':
      '/api/v2/admin/notifications/announcements',
  '/api/v2/admin/referrals/analytics/summary':
      '/api/v2/admin/referrals/analytics/summary',
  '/api/v2/admin/referrals/attributions':
      '/api/v2/admin/referrals/attributions',
  '/api/v2/admin/referrals/creators': '/api/v2/admin/referrals/creators',
  '/api/v2/admin/referrals/creators/{creator_id}':
      '/api/v2/admin/referrals/creators/{creator_id}',
  '/api/v2/admin/referrals/creators/{creator_id}/reward-freeze':
      '/api/v2/admin/referrals/creators/{creator_id}/reward-freeze',
  '/api/v2/admin/referrals/dashboard': '/api/v2/admin/referrals/dashboard',
  '/api/v2/admin/referrals/flags': '/api/v2/admin/referrals/flags',
  '/api/v2/admin/referrals/leaderboard': '/api/v2/admin/referrals/leaderboard',
  '/api/v2/admin/referrals/rewards/pending':
      '/api/v2/admin/referrals/rewards/pending',
  '/api/v2/admin/referrals/rewards/{reward_id}/review':
      '/api/v2/admin/referrals/rewards/{reward_id}/review',
  '/api/v2/admin/referrals/share-codes': '/api/v2/admin/referrals/share-codes',
  '/api/v2/admin/referrals/share-codes/{share_code_id}':
      '/api/v2/admin/referrals/share-codes/{share_code_id}',
  '/api/v2/admin/referrals/share-codes/{share_code_id}/block':
      '/api/v2/admin/referrals/share-codes/{share_code_id}/block',
  '/api/v2/admin/reward-engine/promo-pool/credits':
      '/api/v2/admin/reward-engine/promo-pool/credits',
  '/api/v2/admin/reward-engine/settlements':
      '/api/v2/admin/reward-engine/settlements',
  '/api/v2/admin/sponsorship/analytics': '/api/v2/admin/sponsorship/analytics',
  '/api/v2/admin/sponsorship/categories/{category}':
      '/api/v2/admin/sponsorship/categories/{category}',
  '/api/v2/admin/sponsorship/contracts/{contract_id}/review':
      '/api/v2/admin/sponsorship/contracts/{contract_id}/review',
  '/api/v2/admin/sponsorship/contracts/{contract_id}/settle-next':
      '/api/v2/admin/sponsorship/contracts/{contract_id}/settle-next',
  '/api/v2/admin/sponsorship/offers': '/api/v2/admin/sponsorship/offers',
  '/api/v2/admin/sponsorship/offers/{offer_id}/assign':
      '/api/v2/admin/sponsorship/offers/{offer_id}/assign',
  '/api/v2/admin/sponsorship/offers/{offer_id}/rule':
      '/api/v2/admin/sponsorship/offers/{offer_id}/rule',
  '/api/v2/admin/sponsorship/packages': '/api/v2/admin/sponsorship/packages',
  '/api/v2/admin/story-feed': '/api/v2/admin/story-feed',
  '/api/v2/admin/streamer-tournaments/policy':
      '/api/v2/admin/streamer-tournaments/policy',
  '/api/v2/admin/streamer-tournaments/risk-signals':
      '/api/v2/admin/streamer-tournaments/risk-signals',
  '/api/v2/admin/streamer-tournaments/risk-signals/{signal_id}/review':
      '/api/v2/admin/streamer-tournaments/risk-signals/{signal_id}/review',
  '/api/v2/admin/streamer-tournaments/{tournament_id}/review':
      '/api/v2/admin/streamer-tournaments/{tournament_id}/review',
  '/api/v2/admin/streamer-tournaments/{tournament_id}/settle':
      '/api/v2/admin/streamer-tournaments/{tournament_id}/settle',
  '/api/v2/admin/treasury/bank-accounts':
      '/api/v2/admin/treasury/bank-accounts',
  '/api/v2/admin/treasury/bank-accounts/{account_id}':
      '/api/v2/admin/treasury/bank-accounts/{account_id}',
  '/api/v2/admin/treasury/dashboard': '/api/v2/admin/treasury/dashboard',
  '/api/v2/admin/treasury/deposits': '/api/v2/admin/treasury/deposits',
  '/api/v2/admin/treasury/deposits/{deposit_id}/confirm':
      '/api/v2/admin/treasury/deposits/{deposit_id}/confirm',
  '/api/v2/admin/treasury/deposits/{deposit_id}/reject':
      '/api/v2/admin/treasury/deposits/{deposit_id}/reject',
  '/api/v2/admin/treasury/deposits/{deposit_id}/review':
      '/api/v2/admin/treasury/deposits/{deposit_id}/review',
  '/api/v2/admin/treasury/disputes': '/api/v2/admin/treasury/disputes',
  '/api/v2/admin/treasury/disputes/{dispute_id}':
      '/api/v2/admin/treasury/disputes/{dispute_id}',
  '/api/v2/admin/treasury/disputes/{dispute_id}/messages':
      '/api/v2/admin/treasury/disputes/{dispute_id}/messages',
  '/api/v2/admin/treasury/kyc': '/api/v2/admin/treasury/kyc',
  '/api/v2/admin/treasury/kyc/{profile_id}/review':
      '/api/v2/admin/treasury/kyc/{profile_id}/review',
  '/api/v2/admin/treasury/settings': '/api/v2/admin/treasury/settings',
  '/api/v2/admin/treasury/withdrawal-batches':
      '/api/v2/admin/treasury/withdrawal-batches',
  '/api/v2/admin/treasury/withdrawals': '/api/v2/admin/treasury/withdrawals',
  '/api/v2/admin/treasury/withdrawals/{withdrawal_id}/reviews':
      '/api/v2/admin/treasury/withdrawals/{withdrawal_id}/reviews',
  '/api/v2/admin/treasury/withdrawals/{withdrawal_id}/status':
      '/api/v2/admin/treasury/withdrawals/{withdrawal_id}/status',
  '/api/v2/admin/wallets/market-topups': '/api/v2/admin/wallets/market-topups',
  '/api/v2/admin/wallets/market-topups/quote':
      '/api/v2/admin/wallets/market-topups/quote',
  '/api/v2/admin/wallets/market-topups/{topup_id}/status':
      '/api/v2/admin/wallets/market-topups/{topup_id}/status',
  '/api/v2/admin/wallets/purchase-orders':
      '/api/v2/admin/wallets/purchase-orders',
  '/api/v2/admin/wallets/purchase-orders/{order_id}/status':
      '/api/v2/admin/wallets/purchase-orders/{order_id}/status',
  '/api/v2/admin/world/clubs/{club_id}/context':
      '/api/v2/admin/world/clubs/{club_id}/context',
  '/api/v2/admin/world/cultures/{culture_key}':
      '/api/v2/admin/world/cultures/{culture_key}',
  '/api/v2/admin/world/narratives/{narrative_slug}':
      '/api/v2/admin/world/narratives/{narrative_slug}',
  '/api/v2/agents': '/api/v2/agents',
  '/api/v2/ai-manager/autopilot/live-decision':
      '/api/v2/ai-manager/autopilot/live-decision',
  '/api/v2/ai-manager/autopilot/run': '/api/v2/ai-manager/autopilot/run',
  '/api/v2/ai-manager/economy/reward-preview':
      '/api/v2/ai-manager/economy/reward-preview',
  '/api/v2/ai-manager/profiles/{club_id}':
      '/api/v2/ai-manager/profiles/{club_id}',
  '/api/v2/ai-reporter/feed': '/api/v2/ai-reporter/feed',
  '/api/v2/ai-reporter/run': '/api/v2/ai-reporter/run',
  '/api/v2/analytics/device-fingerprint':
      '/api/v2/analytics/device-fingerprint',
  '/api/v2/analytics/events': '/api/v2/analytics/events',
  '/api/v2/analytics/influencer-leaderboard':
      '/api/v2/analytics/influencer-leaderboard',
  '/api/v2/attachments': '/api/v2/attachments',
  '/api/v2/attachments/{attachment_id}': '/api/v2/attachments/{attachment_id}',
  '/api/v2/auth/change-password': '/api/v2/auth/change-password',
  '/api/v2/auth/logout': '/api/v2/auth/logout',
  '/api/v2/auth/me': '/api/v2/auth/me',
  '/api/v2/auth/refresh': '/api/v2/auth/refresh',
  '/api/v2/awards/categories': '/api/v2/awards/categories',
  '/api/v2/awards/ceremony': '/api/v2/awards/ceremony',
  '/api/v2/awards/nominees': '/api/v2/awards/nominees',
  '/api/v2/awards/winners': '/api/v2/awards/winners',
  '/api/v2/bank-accounts': '/api/v2/bank-accounts',
  '/api/v2/bank-accounts/{bank_account_id}':
      '/api/v2/bank-accounts/{bank_account_id}',
  '/api/v2/broadcast-rights/auctions/{auction_id}/bids':
      '/api/v2/broadcast-rights/auctions/{auction_id}/bids',
  '/api/v2/broadcast-rights/competitions/{competition_id}':
      '/api/v2/broadcast-rights/competitions/{competition_id}',
  '/api/v2/broadcast-rights/competitions/{competition_id}/acquire':
      '/api/v2/broadcast-rights/competitions/{competition_id}/acquire',
  '/api/v2/broadcast-rights/competitions/{competition_id}/auctions':
      '/api/v2/broadcast-rights/competitions/{competition_id}/auctions',
  '/api/v2/broadcast-rights/matches/{match_id}/access':
      '/api/v2/broadcast-rights/matches/{match_id}/access',
  '/api/v2/broadcast-rights/matches/{match_id}/distribute':
      '/api/v2/broadcast-rights/matches/{match_id}/distribute',
  '/api/v2/broadcast-rights/{right_id}/grants':
      '/api/v2/broadcast-rights/{right_id}/grants',
  '/api/v2/broadcast/channels': '/api/v2/broadcast/channels',
  '/api/v2/broadcast/channels/{channel_id}/audio/stems/stream':
      '/api/v2/broadcast/channels/{channel_id}/audio/stems/stream',
  '/api/v2/broadcast/channels/{channel_id}/join':
      '/api/v2/broadcast/channels/{channel_id}/join',
  '/api/v2/broadcast/channels/{channel_id}/stream':
      '/api/v2/broadcast/channels/{channel_id}/stream',
  '/api/v2/broadcast/home': '/api/v2/broadcast/home',
  '/api/v2/broadcast/{match_id}': '/api/v2/broadcast/{match_id}',
  '/api/v2/calendar-engine/dashboard': '/api/v2/calendar-engine/dashboard',
  '/api/v2/calendar-engine/events': '/api/v2/calendar-engine/events',
  '/api/v2/calendar-engine/lifecycle-runs':
      '/api/v2/calendar-engine/lifecycle-runs',
  '/api/v2/calendar-engine/pause-status':
      '/api/v2/calendar-engine/pause-status',
  '/api/v2/calendar-engine/seasons': '/api/v2/calendar-engine/seasons',
  '/api/v2/campaigns': '/api/v2/campaigns',
  '/api/v2/campaigns/create': '/api/v2/campaigns/create',
  '/api/v2/campaigns/{id}/accept': '/api/v2/campaigns/{id}/accept',
  '/api/v2/campaigns/{id}/apply': '/api/v2/campaigns/{id}/apply',
  '/api/v2/campaigns/{id}/performance': '/api/v2/campaigns/{id}/performance',
  '/api/v2/challenges/links/{link_code}':
      '/api/v2/challenges/links/{link_code}',
  '/api/v2/challenges/{challenge_id}': '/api/v2/challenges/{challenge_id}',
  '/api/v2/challenges/{challenge_id}/accept':
      '/api/v2/challenges/{challenge_id}/accept',
  '/api/v2/challenges/{challenge_id}/links':
      '/api/v2/challenges/{challenge_id}/links',
  '/api/v2/challenges/{challenge_id}/publish':
      '/api/v2/challenges/{challenge_id}/publish',
  '/api/v2/challenges/{challenge_id}/share-events':
      '/api/v2/challenges/{challenge_id}/share-events',
  '/api/v2/champions-league/knockout-bracket':
      '/api/v2/champions-league/knockout-bracket',
  '/api/v2/champions-league/league-phase/table':
      '/api/v2/champions-league/league-phase/table',
  '/api/v2/champions-league/playoff-bracket':
      '/api/v2/champions-league/playoff-bracket',
  '/api/v2/champions-league/prize-pool/preview':
      '/api/v2/champions-league/prize-pool/preview',
  '/api/v2/champions-league/qualification-map':
      '/api/v2/champions-league/qualification-map',
  '/api/v2/club/identity': '/api/v2/club/identity',
  '/api/v2/clubs': '/api/v2/clubs',
  '/api/v2/clubs/catalog': '/api/v2/clubs/catalog',
  '/api/v2/clubs/catalog/purchase': '/api/v2/clubs/catalog/purchase',
  '/api/v2/clubs/sale-market/listings': '/api/v2/clubs/sale-market/listings',
  '/api/v2/clubs/{club_id}': '/api/v2/clubs/{club_id}',
  '/api/v2/clubs/{club_id}/academy': '/api/v2/clubs/{club_id}/academy',
  '/api/v2/clubs/{club_id}/academy/players':
      '/api/v2/clubs/{club_id}/academy/players',
  '/api/v2/clubs/{club_id}/academy/players/{player_id}':
      '/api/v2/clubs/{club_id}/academy/players/{player_id}',
  '/api/v2/clubs/{club_id}/academy/programs':
      '/api/v2/clubs/{club_id}/academy/programs',
  '/api/v2/clubs/{club_id}/academy/training-cycles':
      '/api/v2/clubs/{club_id}/academy/training-cycles',
  '/api/v2/clubs/{club_id}/badge': '/api/v2/clubs/{club_id}/badge',
  '/api/v2/clubs/{club_id}/branding': '/api/v2/clubs/{club_id}/branding',
  '/api/v2/clubs/{club_id}/buy-tokens': '/api/v2/clubs/{club_id}/buy-tokens',
  '/api/v2/clubs/{club_id}/challenges': '/api/v2/clubs/{club_id}/challenges',
  '/api/v2/clubs/{club_id}/contracts': '/api/v2/clubs/{club_id}/contracts',
  '/api/v2/clubs/{club_id}/dynasty': '/api/v2/clubs/{club_id}/dynasty',
  '/api/v2/clubs/{club_id}/dynasty/history':
      '/api/v2/clubs/{club_id}/dynasty/history',
  '/api/v2/clubs/{club_id}/eras': '/api/v2/clubs/{club_id}/eras',
  '/api/v2/clubs/{club_id}/finances': '/api/v2/clubs/{club_id}/finances',
  '/api/v2/clubs/{club_id}/finances/budget':
      '/api/v2/clubs/{club_id}/finances/budget',
  '/api/v2/clubs/{club_id}/finances/cashflow':
      '/api/v2/clubs/{club_id}/finances/cashflow',
  '/api/v2/clubs/{club_id}/finances/ledger':
      '/api/v2/clubs/{club_id}/finances/ledger',
  '/api/v2/clubs/{club_id}/honors-timeline':
      '/api/v2/clubs/{club_id}/honors-timeline',
  '/api/v2/clubs/{club_id}/identity': '/api/v2/clubs/{club_id}/identity',
  '/api/v2/clubs/{club_id}/identity/metrics':
      '/api/v2/clubs/{club_id}/identity/metrics',
  '/api/v2/clubs/{club_id}/identity/metrics/refresh':
      '/api/v2/clubs/{club_id}/identity/metrics/refresh',
  '/api/v2/clubs/{club_id}/jerseys': '/api/v2/clubs/{club_id}/jerseys',
  '/api/v2/clubs/{club_id}/jerseys/{jersey_id}':
      '/api/v2/clubs/{club_id}/jerseys/{jersey_id}',
  '/api/v2/clubs/{club_id}/ownership': '/api/v2/clubs/{club_id}/ownership',
  '/api/v2/clubs/{club_id}/prestige': '/api/v2/clubs/{club_id}/prestige',
  '/api/v2/clubs/{club_id}/proposals': '/api/v2/clubs/{club_id}/proposals',
  '/api/v2/clubs/{club_id}/purchases': '/api/v2/clubs/{club_id}/purchases',
  '/api/v2/clubs/{club_id}/reputation': '/api/v2/clubs/{club_id}/reputation',
  '/api/v2/clubs/{club_id}/reputation/history':
      '/api/v2/clubs/{club_id}/reputation/history',
  '/api/v2/clubs/{club_id}/rivalries': '/api/v2/clubs/{club_id}/rivalries',
  '/api/v2/clubs/{club_id}/rivalries/{opponent_club_id}':
      '/api/v2/clubs/{club_id}/rivalries/{opponent_club_id}',
  '/api/v2/clubs/{club_id}/sale-market': '/api/v2/clubs/{club_id}/sale-market',
  '/api/v2/clubs/{club_id}/sale-market/assistant':
      '/api/v2/clubs/{club_id}/sale-market/assistant',
  '/api/v2/clubs/{club_id}/sale-market/history':
      '/api/v2/clubs/{club_id}/sale-market/history',
  '/api/v2/clubs/{club_id}/sale-market/inquiries':
      '/api/v2/clubs/{club_id}/sale-market/inquiries',
  '/api/v2/clubs/{club_id}/sale-market/inquiries/{inquiry_id}/respond':
      '/api/v2/clubs/{club_id}/sale-market/inquiries/{inquiry_id}/respond',
  '/api/v2/clubs/{club_id}/sale-market/listing':
      '/api/v2/clubs/{club_id}/sale-market/listing',
  '/api/v2/clubs/{club_id}/sale-market/listing/cancel':
      '/api/v2/clubs/{club_id}/sale-market/listing/cancel',
  '/api/v2/clubs/{club_id}/sale-market/listing/instant-sell':
      '/api/v2/clubs/{club_id}/sale-market/listing/instant-sell',
  '/api/v2/clubs/{club_id}/sale-market/offers':
      '/api/v2/clubs/{club_id}/sale-market/offers',
  '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/accept':
      '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/accept',
  '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/counter':
      '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/counter',
  '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/reject':
      '/api/v2/clubs/{club_id}/sale-market/offers/{offer_id}/reject',
  '/api/v2/clubs/{club_id}/sale-market/transfer':
      '/api/v2/clubs/{club_id}/sale-market/transfer',
  '/api/v2/clubs/{club_id}/scouting': '/api/v2/clubs/{club_id}/scouting',
  '/api/v2/clubs/{club_id}/scouting-intelligence/academy-supply-signals':
      '/api/v2/clubs/{club_id}/scouting-intelligence/academy-supply-signals',
  '/api/v2/clubs/{club_id}/scouting-intelligence/assignments':
      '/api/v2/clubs/{club_id}/scouting-intelligence/assignments',
  '/api/v2/clubs/{club_id}/scouting-intelligence/badges':
      '/api/v2/clubs/{club_id}/scouting-intelligence/badges',
  '/api/v2/clubs/{club_id}/scouting-intelligence/lifecycle':
      '/api/v2/clubs/{club_id}/scouting-intelligence/lifecycle',
  '/api/v2/clubs/{club_id}/scouting-intelligence/manager-profiles':
      '/api/v2/clubs/{club_id}/scouting-intelligence/manager-profiles',
  '/api/v2/clubs/{club_id}/scouting-intelligence/missions':
      '/api/v2/clubs/{club_id}/scouting-intelligence/missions',
  '/api/v2/clubs/{club_id}/scouting-intelligence/missions/{mission_id}':
      '/api/v2/clubs/{club_id}/scouting-intelligence/missions/{mission_id}',
  '/api/v2/clubs/{club_id}/scouting-intelligence/missions/{mission_id}/complete':
      '/api/v2/clubs/{club_id}/scouting-intelligence/missions/{mission_id}/complete',
  '/api/v2/clubs/{club_id}/scouting-intelligence/networks':
      '/api/v2/clubs/{club_id}/scouting-intelligence/networks',
  '/api/v2/clubs/{club_id}/scouting-intelligence/planning':
      '/api/v2/clubs/{club_id}/scouting-intelligence/planning',
  '/api/v2/clubs/{club_id}/scouting/assignments':
      '/api/v2/clubs/{club_id}/scouting/assignments',
  '/api/v2/clubs/{club_id}/scouting/prospects':
      '/api/v2/clubs/{club_id}/scouting/prospects',
  '/api/v2/clubs/{club_id}/scouting/prospects/{prospect_id}':
      '/api/v2/clubs/{club_id}/scouting/prospects/{prospect_id}',
  '/api/v2/clubs/{club_id}/season-honors':
      '/api/v2/clubs/{club_id}/season-honors',
  '/api/v2/clubs/{club_id}/sell-tokens': '/api/v2/clubs/{club_id}/sell-tokens',
  '/api/v2/clubs/{club_id}/showcase': '/api/v2/clubs/{club_id}/showcase',
  '/api/v2/clubs/{club_id}/sponsorships':
      '/api/v2/clubs/{club_id}/sponsorships',
  '/api/v2/clubs/{club_id}/sponsorships/assets':
      '/api/v2/clubs/{club_id}/sponsorships/assets',
  '/api/v2/clubs/{club_id}/sponsorships/catalog':
      '/api/v2/clubs/{club_id}/sponsorships/catalog',
  '/api/v2/clubs/{club_id}/sponsorships/contracts':
      '/api/v2/clubs/{club_id}/sponsorships/contracts',
  '/api/v2/clubs/{club_id}/sponsorships/contracts/{contract_id}':
      '/api/v2/clubs/{club_id}/sponsorships/contracts/{contract_id}',
  '/api/v2/clubs/{club_id}/treasury': '/api/v2/clubs/{club_id}/treasury',
  '/api/v2/clubs/{club_id}/trophies': '/api/v2/clubs/{club_id}/trophies',
  '/api/v2/clubs/{club_id}/trophy-cabinet':
      '/api/v2/clubs/{club_id}/trophy-cabinet',
  '/api/v2/clubs/{club_id}/valuation': '/api/v2/clubs/{club_id}/valuation',
  '/api/v2/clubs/{club_id}/vote': '/api/v2/clubs/{club_id}/vote',
  '/api/v2/clubs/{club_id}/youth-pipeline':
      '/api/v2/clubs/{club_id}/youth-pipeline',
  '/api/v2/commentary/profiles': '/api/v2/commentary/profiles',
  '/api/v2/commentary/select': '/api/v2/commentary/select',
  '/api/v2/community/creator-clubs/{club_id}/fan-competitions':
      '/api/v2/community/creator-clubs/{club_id}/fan-competitions',
  '/api/v2/community/creator-clubs/{club_id}/fan-groups':
      '/api/v2/community/creator-clubs/{club_id}/fan-groups',
  '/api/v2/community/creator-clubs/{club_id}/fan-state':
      '/api/v2/community/creator-clubs/{club_id}/fan-state',
  '/api/v2/community/creator-clubs/{club_id}/follow':
      '/api/v2/community/creator-clubs/{club_id}/follow',
  '/api/v2/community/creator-matches/{match_id}/chat-room':
      '/api/v2/community/creator-matches/{match_id}/chat-room',
  '/api/v2/community/creator-matches/{match_id}/chat-room/messages':
      '/api/v2/community/creator-matches/{match_id}/chat-room/messages',
  '/api/v2/community/creator-matches/{match_id}/fan-wall':
      '/api/v2/community/creator-matches/{match_id}/fan-wall',
  '/api/v2/community/creator-matches/{match_id}/rivalry-signals':
      '/api/v2/community/creator-matches/{match_id}/rivalry-signals',
  '/api/v2/community/creator-matches/{match_id}/tactical-advice':
      '/api/v2/community/creator-matches/{match_id}/tactical-advice',
  '/api/v2/community/digest': '/api/v2/community/digest',
  '/api/v2/community/fan-competitions/{fan_competition_id}/join':
      '/api/v2/community/fan-competitions/{fan_competition_id}/join',
  '/api/v2/community/fan-groups/{group_id}/join':
      '/api/v2/community/fan-groups/{group_id}/join',
  '/api/v2/community/live-threads': '/api/v2/community/live-threads',
  '/api/v2/community/live-threads/{thread_id}':
      '/api/v2/community/live-threads/{thread_id}',
  '/api/v2/community/live-threads/{thread_id}/messages':
      '/api/v2/community/live-threads/{thread_id}/messages',
  '/api/v2/community/private-messages/threads':
      '/api/v2/community/private-messages/threads',
  '/api/v2/community/private-messages/threads/{thread_id}':
      '/api/v2/community/private-messages/threads/{thread_id}',
  '/api/v2/community/private-messages/threads/{thread_id}/messages':
      '/api/v2/community/private-messages/threads/{thread_id}/messages',
  '/api/v2/community/watchlist': '/api/v2/community/watchlist',
  '/api/v2/community/watchlist/{competition_key}':
      '/api/v2/community/watchlist/{competition_key}',
  '/api/v2/competitions': '/api/v2/competitions',
  '/api/v2/competitions/admin': '/api/v2/competitions/admin',
  '/api/v2/competitions/admin/{code}': '/api/v2/competitions/admin/{code}',
  '/api/v2/competitions/admin/{code}/orchestrate':
      '/api/v2/competitions/admin/{code}/orchestrate',
  '/api/v2/competitions/create': '/api/v2/competitions/create',
  '/api/v2/competitions/join': '/api/v2/competitions/join',
  '/api/v2/competitions/players/{subject_id}/progression':
      '/api/v2/competitions/players/{subject_id}/progression',
  '/api/v2/competitions/records/{competition_id}':
      '/api/v2/competitions/records/{competition_id}',
  '/api/v2/competitions/runtime/{code}': '/api/v2/competitions/runtime/{code}',
  '/api/v2/competitions/{competition_id}':
      '/api/v2/competitions/{competition_id}',
  '/api/v2/competitions/{competition_id}/advance':
      '/api/v2/competitions/{competition_id}/advance',
  '/api/v2/competitions/{competition_id}/finalize':
      '/api/v2/competitions/{competition_id}/finalize',
  '/api/v2/competitions/{competition_id}/financials':
      '/api/v2/competitions/{competition_id}/financials',
  '/api/v2/competitions/{competition_id}/fixtures':
      '/api/v2/competitions/{competition_id}/fixtures',
  '/api/v2/competitions/{competition_id}/invites':
      '/api/v2/competitions/{competition_id}/invites',
  '/api/v2/competitions/{competition_id}/invites/accept':
      '/api/v2/competitions/{competition_id}/invites/accept',
  '/api/v2/competitions/{competition_id}/join':
      '/api/v2/competitions/{competition_id}/join',
  '/api/v2/competitions/{competition_id}/launch':
      '/api/v2/competitions/{competition_id}/launch',
  '/api/v2/competitions/{competition_id}/leave':
      '/api/v2/competitions/{competition_id}/leave',
  '/api/v2/competitions/{competition_id}/matches/{match_id}/events':
      '/api/v2/competitions/{competition_id}/matches/{match_id}/events',
  '/api/v2/competitions/{competition_id}/matches/{match_id}/result':
      '/api/v2/competitions/{competition_id}/matches/{match_id}/result',
  '/api/v2/competitions/{competition_id}/publish':
      '/api/v2/competitions/{competition_id}/publish',
  '/api/v2/competitions/{competition_id}/rewards':
      '/api/v2/competitions/{competition_id}/rewards',
  '/api/v2/competitions/{competition_id}/rounds':
      '/api/v2/competitions/{competition_id}/rounds',
  '/api/v2/competitions/{competition_id}/schedule/jobs':
      '/api/v2/competitions/{competition_id}/schedule/jobs',
  '/api/v2/competitions/{competition_id}/schedule/jobs/{job_id}':
      '/api/v2/competitions/{competition_id}/schedule/jobs/{job_id}',
  '/api/v2/competitions/{competition_id}/schedule/preview':
      '/api/v2/competitions/{competition_id}/schedule/preview',
  '/api/v2/competitions/{competition_id}/seed':
      '/api/v2/competitions/{competition_id}/seed',
  '/api/v2/competitions/{competition_id}/standings':
      '/api/v2/competitions/{competition_id}/standings',
  '/api/v2/competitions/{competition_id}/summary':
      '/api/v2/competitions/{competition_id}/summary',
  '/api/v2/competitive-integrity/fast-game/runs':
      '/api/v2/competitive-integrity/fast-game/runs',
  '/api/v2/competitive-integrity/fast-game/runs/{run_id}':
      '/api/v2/competitive-integrity/fast-game/runs/{run_id}',
  '/api/v2/competitive-integrity/fast-game/runs/{run_id}/play':
      '/api/v2/competitive-integrity/fast-game/runs/{run_id}/play',
  '/api/v2/competitive-integrity/managers':
      '/api/v2/competitive-integrity/managers',
  '/api/v2/competitive-integrity/managers/candidates':
      '/api/v2/competitive-integrity/managers/candidates',
  '/api/v2/competitive-integrity/managers/{manager_id}/instructions':
      '/api/v2/competitive-integrity/managers/{manager_id}/instructions',
  '/api/v2/competitive-integrity/matches':
      '/api/v2/competitive-integrity/matches',
  '/api/v2/competitive-integrity/matches/{match_id}':
      '/api/v2/competitive-integrity/matches/{match_id}',
  '/api/v2/competitive-integrity/matches/{match_id}/execute':
      '/api/v2/competitive-integrity/matches/{match_id}/execute',
  '/api/v2/competitive-integrity/notifications/events':
      '/api/v2/competitive-integrity/notifications/events',
  '/api/v2/conversations': '/api/v2/conversations',
  '/api/v2/conversations/start': '/api/v2/conversations/start',
  '/api/v2/conversations/{conversation_id}/message':
      '/api/v2/conversations/{conversation_id}/message',
  '/api/v2/conversations/{conversation_id}/messages':
      '/api/v2/conversations/{conversation_id}/messages',
  '/api/v2/conversations/{conversation_id}/status':
      '/api/v2/conversations/{conversation_id}/status',
  '/api/v2/creator/application': '/api/v2/creator/application',
  '/api/v2/creator/apply': '/api/v2/creator/apply',
  '/api/v2/creator/cards': '/api/v2/creator/cards',
  '/api/v2/creator/cards/listings': '/api/v2/creator/cards/listings',
  '/api/v2/creator/cards/listings/{listing_id}/buy':
      '/api/v2/creator/cards/listings/{listing_id}/buy',
  '/api/v2/creator/cards/loans/{loan_id}/return':
      '/api/v2/creator/cards/loans/{loan_id}/return',
  '/api/v2/creator/cards/swap': '/api/v2/creator/cards/swap',
  '/api/v2/creator/cards/{creator_card_id}/list':
      '/api/v2/creator/cards/{creator_card_id}/list',
  '/api/v2/creator/cards/{creator_card_id}/loan':
      '/api/v2/creator/cards/{creator_card_id}/loan',
  '/api/v2/creator/clubs/{club_id}/fan-share-market':
      '/api/v2/creator/clubs/{club_id}/fan-share-market',
  '/api/v2/creator/clubs/{club_id}/fan-share-market/distributions':
      '/api/v2/creator/clubs/{club_id}/fan-share-market/distributions',
  '/api/v2/creator/clubs/{club_id}/fan-share-market/holding':
      '/api/v2/creator/clubs/{club_id}/fan-share-market/holding',
  '/api/v2/creator/clubs/{club_id}/fan-share-market/purchase':
      '/api/v2/creator/clubs/{club_id}/fan-share-market/purchase',
  '/api/v2/creator/verify-email': '/api/v2/creator/verify-email',
  '/api/v2/creator/verify-phone': '/api/v2/creator/verify-phone',
  '/api/v2/creators/marketplace': '/api/v2/creators/marketplace',
  '/api/v2/creators/me/competitions': '/api/v2/creators/me/competitions',
  '/api/v2/creators/me/copilot/analyze': '/api/v2/creators/me/copilot/analyze',
  '/api/v2/creators/me/finance': '/api/v2/creators/me/finance',
  '/api/v2/creators/me/insights': '/api/v2/creators/me/insights',
  '/api/v2/creators/me/reputation': '/api/v2/creators/me/reputation',
  '/api/v2/creators/me/summary': '/api/v2/creators/me/summary',
  '/api/v2/creators/profile': '/api/v2/creators/profile',
  '/api/v2/creators/profile/me': '/api/v2/creators/profile/me',
  '/api/v2/creators/{handle}': '/api/v2/creators/{handle}',
  '/api/v2/daily-challenges': '/api/v2/daily-challenges',
  '/api/v2/daily-challenges/me': '/api/v2/daily-challenges/me',
  '/api/v2/daily-challenges/{challenge_key}/claim':
      '/api/v2/daily-challenges/{challenge_key}/claim',
  '/api/v2/discovery/home': '/api/v2/discovery/home',
  '/api/v2/discovery/saved-searches': '/api/v2/discovery/saved-searches',
  '/api/v2/discovery/saved-searches/{search_id}':
      '/api/v2/discovery/saved-searches/{search_id}',
  '/api/v2/discovery/search': '/api/v2/discovery/search',
  '/api/v2/disputes': '/api/v2/disputes',
  '/api/v2/disputes/{dispute_id}': '/api/v2/disputes/{dispute_id}',
  '/api/v2/disputes/{dispute_id}/messages':
      '/api/v2/disputes/{dispute_id}/messages',
  '/api/v2/events/today': '/api/v2/events/today',
  '/api/v2/events/upcoming': '/api/v2/events/upcoming',
  '/api/v2/fan-wars/leaderboards/{board_type}':
      '/api/v2/fan-wars/leaderboards/{board_type}',
  '/api/v2/fan-wars/nations-cup/{competition_id}':
      '/api/v2/fan-wars/nations-cup/{competition_id}',
  '/api/v2/fan-wars/profiles/{profile_id}/dashboard':
      '/api/v2/fan-wars/profiles/{profile_id}/dashboard',
  '/api/v2/fan-wars/rivalries/{board_type}':
      '/api/v2/fan-wars/rivalries/{board_type}',
  '/api/v2/fans/{club_id}': '/api/v2/fans/{club_id}',
  '/api/v2/fast-cups/upcoming': '/api/v2/fast-cups/upcoming',
  '/api/v2/fast-cups/{cup_id}/bracket': '/api/v2/fast-cups/{cup_id}/bracket',
  '/api/v2/fast-cups/{cup_id}/countdown':
      '/api/v2/fast-cups/{cup_id}/countdown',
  '/api/v2/fast-cups/{cup_id}/join': '/api/v2/fast-cups/{cup_id}/join',
  '/api/v2/fast-cups/{cup_id}/result-summary':
      '/api/v2/fast-cups/{cup_id}/result-summary',
  '/api/v2/federations': '/api/v2/federations',
  '/api/v2/federations/proposals/{proposal_id}/votes':
      '/api/v2/federations/proposals/{proposal_id}/votes',
  '/api/v2/federations/rankings': '/api/v2/federations/rankings',
  '/api/v2/federations/regional-tournaments':
      '/api/v2/federations/regional-tournaments',
  '/api/v2/federations/{federation_id}': '/api/v2/federations/{federation_id}',
  '/api/v2/federations/{federation_id}/governance':
      '/api/v2/federations/{federation_id}/governance',
  '/api/v2/federations/{federation_id}/leagues':
      '/api/v2/federations/{federation_id}/leagues',
  '/api/v2/federations/{federation_id}/memberships':
      '/api/v2/federations/{federation_id}/memberships',
  '/api/v2/federations/{federation_id}/narratives':
      '/api/v2/federations/{federation_id}/narratives',
  '/api/v2/federations/{federation_id}/proposals':
      '/api/v2/federations/{federation_id}/proposals',
  '/api/v2/federations/{federation_id}/sanctions':
      '/api/v2/federations/{federation_id}/sanctions',
  '/api/v2/federations/{federation_id}/treasury/distribute':
      '/api/v2/federations/{federation_id}/treasury/distribute',
  '/api/v2/federations/{federation_id}/validate-action':
      '/api/v2/federations/{federation_id}/validate-action',
  '/api/v2/finance': '/api/v2/finance',
  '/api/v2/football-events/players/{player_id}/events':
      '/api/v2/football-events/players/{player_id}/events',
  '/api/v2/football-events/players/{player_id}/impact':
      '/api/v2/football-events/players/{player_id}/impact',
  '/api/v2/gift-engine/me/combos': '/api/v2/gift-engine/me/combos',
  '/api/v2/gift-engine/me/summary': '/api/v2/gift-engine/me/summary',
  '/api/v2/gift-engine/me/transactions': '/api/v2/gift-engine/me/transactions',
  '/api/v2/gift-engine/send': '/api/v2/gift-engine/send',
  '/api/v2/governance/clubs/{club_id}/panel':
      '/api/v2/governance/clubs/{club_id}/panel',
  '/api/v2/governance/me/overview': '/api/v2/governance/me/overview',
  '/api/v2/governance/proposals': '/api/v2/governance/proposals',
  '/api/v2/governance/proposals/{proposal_id}':
      '/api/v2/governance/proposals/{proposal_id}',
  '/api/v2/governance/proposals/{proposal_id}/vote':
      '/api/v2/governance/proposals/{proposal_id}/vote',
  '/api/v2/hosted-competitions': '/api/v2/hosted-competitions',
  '/api/v2/hosted-competitions/mine': '/api/v2/hosted-competitions/mine',
  '/api/v2/hosted-competitions/mine/invites':
      '/api/v2/hosted-competitions/mine/invites',
  '/api/v2/hosted-competitions/templates':
      '/api/v2/hosted-competitions/templates',
  '/api/v2/hosted-competitions/{competition_id}':
      '/api/v2/hosted-competitions/{competition_id}',
  '/api/v2/hosted-competitions/{competition_id}/finance':
      '/api/v2/hosted-competitions/{competition_id}/finance',
  '/api/v2/hosted-competitions/{competition_id}/invites':
      '/api/v2/hosted-competitions/{competition_id}/invites',
  '/api/v2/hosted-competitions/{competition_id}/invites/accept':
      '/api/v2/hosted-competitions/{competition_id}/invites/accept',
  '/api/v2/hosted-competitions/{competition_id}/join':
      '/api/v2/hosted-competitions/{competition_id}/join',
  '/api/v2/hosted-competitions/{competition_id}/launch':
      '/api/v2/hosted-competitions/{competition_id}/launch',
  '/api/v2/hosted-competitions/{competition_id}/standings':
      '/api/v2/hosted-competitions/{competition_id}/standings',
  '/api/v2/infinite-league/economy': '/api/v2/infinite-league/economy',
  '/api/v2/infinite-league/livestream': '/api/v2/infinite-league/livestream',
  '/api/v2/infinite-league/matches': '/api/v2/infinite-league/matches',
  '/api/v2/infinite-league/matches/{match_id}':
      '/api/v2/infinite-league/matches/{match_id}',
  '/api/v2/infinite-league/pundits/{match_id}':
      '/api/v2/infinite-league/pundits/{match_id}',
  '/api/v2/infinite-league/status': '/api/v2/infinite-league/status',
  '/api/v2/infinite-league/tick': '/api/v2/infinite-league/tick',
  '/api/v2/infinite-league/viral-feed': '/api/v2/infinite-league/viral-feed',
  '/api/v2/integrity-engine/me/incidents':
      '/api/v2/integrity-engine/me/incidents',
  '/api/v2/integrity-engine/me/score': '/api/v2/integrity-engine/me/score',
  '/api/v2/kyc': '/api/v2/kyc',
  '/api/v2/leaderboards/dynasties': '/api/v2/leaderboards/dynasties',
  '/api/v2/leaderboards/prestige': '/api/v2/leaderboards/prestige',
  '/api/v2/leaderboards/trophies': '/api/v2/leaderboards/trophies',
  '/api/v2/leagues/register': '/api/v2/leagues/register',
  '/api/v2/leagues/{season_id}/fixtures':
      '/api/v2/leagues/{season_id}/fixtures',
  '/api/v2/leagues/{season_id}/qualification-markers':
      '/api/v2/leagues/{season_id}/qualification-markers',
  '/api/v2/leagues/{season_id}/standings':
      '/api/v2/leagues/{season_id}/standings',
  '/api/v2/leagues/{season_id}/summary': '/api/v2/leagues/{season_id}/summary',
  '/api/v2/live-events': '/api/v2/live-events',
  '/api/v2/manager-duels': '/api/v2/manager-duels',
  '/api/v2/manager-duels/leaderboard': '/api/v2/manager-duels/leaderboard',
  '/api/v2/manager-duels/{duel_id}': '/api/v2/manager-duels/{duel_id}',
  '/api/v2/managers/assign': '/api/v2/managers/assign',
  '/api/v2/managers/catalog': '/api/v2/managers/catalog',
  '/api/v2/managers/compare': '/api/v2/managers/compare',
  '/api/v2/managers/competition-runtime/{code}':
      '/api/v2/managers/competition-runtime/{code}',
  '/api/v2/managers/create': '/api/v2/managers/create',
  '/api/v2/managers/filters': '/api/v2/managers/filters',
  '/api/v2/managers/history': '/api/v2/managers/history',
  '/api/v2/managers/my-trade-listings': '/api/v2/managers/my-trade-listings',
  '/api/v2/managers/recommendation': '/api/v2/managers/recommendation',
  '/api/v2/managers/recruit': '/api/v2/managers/recruit',
  '/api/v2/managers/swap': '/api/v2/managers/swap',
  '/api/v2/managers/team': '/api/v2/managers/team',
  '/api/v2/managers/trade-listings': '/api/v2/managers/trade-listings',
  '/api/v2/managers/trade-listings/{listing_id}/buy':
      '/api/v2/managers/trade-listings/{listing_id}/buy',
  '/api/v2/managers/trade-listings/{listing_id}/cancel':
      '/api/v2/managers/trade-listings/{listing_id}/cancel',
  '/api/v2/managers/{asset_id}/release': '/api/v2/managers/{asset_id}/release',
  '/api/v2/market/buy': '/api/v2/market/buy',
  '/api/v2/market/listings': '/api/v2/market/listings',
  '/api/v2/market/listings/{listing_id}/cancel':
      '/api/v2/market/listings/{listing_id}/cancel',
  '/api/v2/market/listings/{listing_id}/matches':
      '/api/v2/market/listings/{listing_id}/matches',
  '/api/v2/market/listings/{listing_id}/offers':
      '/api/v2/market/listings/{listing_id}/offers',
  '/api/v2/market/movers': '/api/v2/market/movers',
  '/api/v2/market/offers': '/api/v2/market/offers',
  '/api/v2/market/offers/{offer_id}/accept':
      '/api/v2/market/offers/{offer_id}/accept',
  '/api/v2/market/offers/{offer_id}/counter':
      '/api/v2/market/offers/{offer_id}/counter',
  '/api/v2/market/offers/{offer_id}/reject':
      '/api/v2/market/offers/{offer_id}/reject',
  '/api/v2/market/players': '/api/v2/market/players',
  '/api/v2/market/players/{player_id}': '/api/v2/market/players/{player_id}',
  '/api/v2/market/players/{player_id}/candles':
      '/api/v2/market/players/{player_id}/candles',
  '/api/v2/market/players/{player_id}/history':
      '/api/v2/market/players/{player_id}/history',
  '/api/v2/market/sell': '/api/v2/market/sell',
  '/api/v2/market/summary/{asset_id}': '/api/v2/market/summary/{asset_id}',
  '/api/v2/market/ticker/{player_id}': '/api/v2/market/ticker/{player_id}',
  '/api/v2/market/trade-intents': '/api/v2/market/trade-intents',
  '/api/v2/market/trade-intents/{intent_id}/withdraw':
      '/api/v2/market/trade-intents/{intent_id}/withdraw',
  '/api/v2/marketplace/my-players': '/api/v2/marketplace/my-players',
  '/api/v2/marketplace/players': '/api/v2/marketplace/players',
  '/api/v2/marketplace/players/{player_id}':
      '/api/v2/marketplace/players/{player_id}',
  '/api/v2/match-engine/analytics': '/api/v2/match-engine/analytics',
  '/api/v2/match-engine/analytics/{match_key}':
      '/api/v2/match-engine/analytics/{match_key}',
  '/api/v2/match-engine/highlights/{match_key}':
      '/api/v2/match-engine/highlights/{match_key}',
  '/api/v2/match-engine/live-feed/{match_key}':
      '/api/v2/match-engine/live-feed/{match_key}',
  '/api/v2/match-engine/render-sync': '/api/v2/match-engine/render-sync',
  '/api/v2/match-engine/render-sync/{match_key}':
      '/api/v2/match-engine/render-sync/{match_key}',
  '/api/v2/match-engine/replay': '/api/v2/match-engine/replay',
  '/api/v2/match-engine/simulate': '/api/v2/match-engine/simulate',
  '/api/v2/match-engine/summary': '/api/v2/match-engine/summary',
  '/api/v2/match-engine/timeline': '/api/v2/match-engine/timeline',
  '/api/v2/match-share-links/{share_code}':
      '/api/v2/match-share-links/{share_code}',
  '/api/v2/match-share-links/{share_code}/events':
      '/api/v2/match-share-links/{share_code}/events',
  '/api/v2/match-viewer/{match_key}': '/api/v2/match-viewer/{match_key}',
  '/api/v2/match-viewer/{match_key}/illusion':
      '/api/v2/match-viewer/{match_key}/illusion',
  '/api/v2/match-viewer/{match_key}/session':
      '/api/v2/match-viewer/{match_key}/session',
  '/api/v2/matches/complete': '/api/v2/matches/complete',
  '/api/v2/matches/live/active': '/api/v2/matches/live/active',
  '/api/v2/matches/start': '/api/v2/matches/start',
  '/api/v2/matches/{match_id}/analysis': '/api/v2/matches/{match_id}/analysis',
  '/api/v2/matches/{match_id}/audio/stems/stream':
      '/api/v2/matches/{match_id}/audio/stems/stream',
  '/api/v2/matches/{match_id}/chat': '/api/v2/matches/{match_id}/chat',
  '/api/v2/matches/{match_id}/commentary':
      '/api/v2/matches/{match_id}/commentary',
  '/api/v2/matches/{match_id}/commentary/stream':
      '/api/v2/matches/{match_id}/commentary/stream',
  '/api/v2/matches/{match_id}/highlights':
      '/api/v2/matches/{match_id}/highlights',
  '/api/v2/matches/{match_id}/highlights/share-package':
      '/api/v2/matches/{match_id}/highlights/share-package',
  '/api/v2/matches/{match_id}/live': '/api/v2/matches/{match_id}/live',
  '/api/v2/matches/{match_id}/live-reactions':
      '/api/v2/matches/{match_id}/live-reactions',
  '/api/v2/matches/{match_id}/reactions':
      '/api/v2/matches/{match_id}/reactions',
  '/api/v2/matches/{match_id}/replay': '/api/v2/matches/{match_id}/replay',
  '/api/v2/matches/{match_id}/share-links':
      '/api/v2/matches/{match_id}/share-links',
  '/api/v2/matches/{match_id}/spectate': '/api/v2/matches/{match_id}/spectate',
  '/api/v2/matches/{match_id}/stream': '/api/v2/matches/{match_id}/stream',
  '/api/v2/matches/{match_id}/unity-access':
      '/api/v2/matches/{match_id}/unity-access',
  '/api/v2/matches/{match_id}/unity-access/refresh':
      '/api/v2/matches/{match_id}/unity-access/refresh',
  '/api/v2/me/clubs/sale-market/listings':
      '/api/v2/me/clubs/sale-market/listings',
  '/api/v2/me/clubs/sale-market/offers': '/api/v2/me/clubs/sale-market/offers',
  '/api/v2/media': '/api/v2/media',
  '/api/v2/moderation/me/reports': '/api/v2/moderation/me/reports',
  '/api/v2/moderation/reports': '/api/v2/moderation/reports',
  '/api/v2/moments/live': '/api/v2/moments/live',
  '/api/v2/national-team-engine/competitions':
      '/api/v2/national-team-engine/competitions',
  '/api/v2/national-team-engine/competitions/{competition_id}':
      '/api/v2/national-team-engine/competitions/{competition_id}',
  '/api/v2/national-team-engine/competitions/{competition_id}/ads/active':
      '/api/v2/national-team-engine/competitions/{competition_id}/ads/active',
  '/api/v2/national-team-engine/competitions/{competition_id}/auto-build-squad':
      '/api/v2/national-team-engine/competitions/{competition_id}/auto-build-squad',
  '/api/v2/national-team-engine/competitions/{competition_id}/entries':
      '/api/v2/national-team-engine/competitions/{competition_id}/entries',
  '/api/v2/national-team-engine/competitions/{competition_id}/gifts':
      '/api/v2/national-team-engine/competitions/{competition_id}/gifts',
  '/api/v2/national-team-engine/competitions/{competition_id}/lifecycle':
      '/api/v2/national-team-engine/competitions/{competition_id}/lifecycle',
  '/api/v2/national-team-engine/competitions/{competition_id}/presentation':
      '/api/v2/national-team-engine/competitions/{competition_id}/presentation',
  '/api/v2/national-team-engine/competitions/{competition_id}/rental-entry':
      '/api/v2/national-team-engine/competitions/{competition_id}/rental-entry',
  '/api/v2/national-team-engine/competitions/{competition_id}/rental-pool':
      '/api/v2/national-team-engine/competitions/{competition_id}/rental-pool',
  '/api/v2/national-team-engine/competitions/{competition_id}/story-events':
      '/api/v2/national-team-engine/competitions/{competition_id}/story-events',
  '/api/v2/national-team-engine/competitions/{competition_id}/theme':
      '/api/v2/national-team-engine/competitions/{competition_id}/theme',
  '/api/v2/national-team-engine/entries/{entry_id}':
      '/api/v2/national-team-engine/entries/{entry_id}',
  '/api/v2/national-team-engine/entries/{entry_id}/free-players/claim':
      '/api/v2/national-team-engine/entries/{entry_id}/free-players/claim',
  '/api/v2/national-team-engine/entries/{entry_id}/rental-status':
      '/api/v2/national-team-engine/entries/{entry_id}/rental-status',
  '/api/v2/national-team-engine/entries/{entry_id}/rentals':
      '/api/v2/national-team-engine/entries/{entry_id}/rentals',
  '/api/v2/national-team-engine/me/history':
      '/api/v2/national-team-engine/me/history',
  '/api/v2/national-team-engine/me/previous-roster':
      '/api/v2/national-team-engine/me/previous-roster',
  '/api/v2/national-team-engine/rankings':
      '/api/v2/national-team-engine/rankings',
  '/api/v2/news/breaking': '/api/v2/news/breaking',
  '/api/v2/news/daily': '/api/v2/news/daily',
  '/api/v2/news/personalized': '/api/v2/news/personalized',
  '/api/v2/notifications': '/api/v2/notifications',
  '/api/v2/notifications/announcements': '/api/v2/notifications/announcements',
  '/api/v2/notifications/me': '/api/v2/notifications/me',
  '/api/v2/notifications/preferences': '/api/v2/notifications/preferences',
  '/api/v2/notifications/read-all': '/api/v2/notifications/read-all',
  '/api/v2/notifications/subscriptions': '/api/v2/notifications/subscriptions',
  '/api/v2/notifications/subscriptions/{subscription_id}':
      '/api/v2/notifications/subscriptions/{subscription_id}',
  '/api/v2/notifications/{notification_id}/read':
      '/api/v2/notifications/{notification_id}/read',
  '/api/v2/orders': '/api/v2/orders',
  '/api/v2/orders/book/{player_id}': '/api/v2/orders/book/{player_id}',
  '/api/v2/orders/{order_id}': '/api/v2/orders/{order_id}',
  '/api/v2/orders/{order_id}/admin-buyback':
      '/api/v2/orders/{order_id}/admin-buyback',
  '/api/v2/orders/{order_id}/admin-buyback-preview':
      '/api/v2/orders/{order_id}/admin-buyback-preview',
  '/api/v2/orders/{order_id}/cancel': '/api/v2/orders/{order_id}/cancel',
  '/api/v2/organizations': '/api/v2/organizations',
  '/api/v2/organizations/invites/accept':
      '/api/v2/organizations/invites/accept',
  '/api/v2/organizations/me': '/api/v2/organizations/me',
  '/api/v2/organizations/{organization_id}/audit-log':
      '/api/v2/organizations/{organization_id}/audit-log',
  '/api/v2/organizations/{organization_id}/invite':
      '/api/v2/organizations/{organization_id}/invite',
  '/api/v2/ownership-groups': '/api/v2/ownership-groups',
  '/api/v2/ownership-groups/transfers/validate':
      '/api/v2/ownership-groups/transfers/validate',
  '/api/v2/ownership-groups/{group_id}': '/api/v2/ownership-groups/{group_id}',
  '/api/v2/ownership-groups/{group_id}/budget/allocate':
      '/api/v2/ownership-groups/{group_id}/budget/allocate',
  '/api/v2/ownership-groups/{group_id}/budget/transfer':
      '/api/v2/ownership-groups/{group_id}/budget/transfer',
  '/api/v2/ownership-groups/{group_id}/clubs':
      '/api/v2/ownership-groups/{group_id}/clubs',
  '/api/v2/player-cards/admin/preseeded-regens':
      '/api/v2/player-cards/admin/preseeded-regens',
  '/api/v2/player-cards/admin/preseeded-regens/mint':
      '/api/v2/player-cards/admin/preseeded-regens/mint',
  '/api/v2/player-cards/inventory': '/api/v2/player-cards/inventory',
  '/api/v2/player-cards/listings': '/api/v2/player-cards/listings',
  '/api/v2/player-cards/listings/mine': '/api/v2/player-cards/listings/mine',
  '/api/v2/player-cards/listings/{listing_id}/buy':
      '/api/v2/player-cards/listings/{listing_id}/buy',
  '/api/v2/player-cards/listings/{listing_id}/cancel':
      '/api/v2/player-cards/listings/{listing_id}/cancel',
  '/api/v2/player-cards/loans': '/api/v2/player-cards/loans',
  '/api/v2/player-cards/loans/contracts/{loan_contract_id}/return':
      '/api/v2/player-cards/loans/contracts/{loan_contract_id}/return',
  '/api/v2/player-cards/loans/{loan_listing_id}/borrow':
      '/api/v2/player-cards/loans/{loan_listing_id}/borrow',
  '/api/v2/player-cards/marketplace/listings':
      '/api/v2/player-cards/marketplace/listings',
  '/api/v2/player-cards/marketplace/loans':
      '/api/v2/player-cards/marketplace/loans',
  '/api/v2/player-cards/marketplace/loans/contracts':
      '/api/v2/player-cards/marketplace/loans/contracts',
  '/api/v2/player-cards/marketplace/loans/contracts/{contract_id}/return':
      '/api/v2/player-cards/marketplace/loans/contracts/{contract_id}/return',
  '/api/v2/player-cards/marketplace/loans/contracts/{contract_id}/settle':
      '/api/v2/player-cards/marketplace/loans/contracts/{contract_id}/settle',
  '/api/v2/player-cards/marketplace/loans/negotiations/{negotiation_id}/accept':
      '/api/v2/player-cards/marketplace/loans/negotiations/{negotiation_id}/accept',
  '/api/v2/player-cards/marketplace/loans/negotiations/{negotiation_id}/counter':
      '/api/v2/player-cards/marketplace/loans/negotiations/{negotiation_id}/counter',
  '/api/v2/player-cards/marketplace/loans/{listing_id}/cancel':
      '/api/v2/player-cards/marketplace/loans/{listing_id}/cancel',
  '/api/v2/player-cards/marketplace/loans/{listing_id}/negotiations':
      '/api/v2/player-cards/marketplace/loans/{listing_id}/negotiations',
  '/api/v2/player-cards/marketplace/sales':
      '/api/v2/player-cards/marketplace/sales',
  '/api/v2/player-cards/marketplace/sales/{listing_id}/buy':
      '/api/v2/player-cards/marketplace/sales/{listing_id}/buy',
  '/api/v2/player-cards/marketplace/sales/{listing_id}/cancel':
      '/api/v2/player-cards/marketplace/sales/{listing_id}/cancel',
  '/api/v2/player-cards/marketplace/swaps':
      '/api/v2/player-cards/marketplace/swaps',
  '/api/v2/player-cards/marketplace/swaps/{listing_id}/cancel':
      '/api/v2/player-cards/marketplace/swaps/{listing_id}/cancel',
  '/api/v2/player-cards/marketplace/swaps/{listing_id}/execute':
      '/api/v2/player-cards/marketplace/swaps/{listing_id}/execute',
  '/api/v2/player-cards/players': '/api/v2/player-cards/players',
  '/api/v2/player-cards/players/{player_id}':
      '/api/v2/player-cards/players/{player_id}',
  '/api/v2/player-cards/starter-rental': '/api/v2/player-cards/starter-rental',
  '/api/v2/player-cards/watchlist': '/api/v2/player-cards/watchlist',
  '/api/v2/player-cards/watchlist/{watchlist_id}':
      '/api/v2/player-cards/watchlist/{watchlist_id}',
  '/api/v2/players/{player_id}/agency': '/api/v2/players/{player_id}/agency',
  '/api/v2/players/{player_id}/agency/contract-decision':
      '/api/v2/players/{player_id}/agency/contract-decision',
  '/api/v2/players/{player_id}/agency/transfer-decision':
      '/api/v2/players/{player_id}/agency/transfer-decision',
  '/api/v2/players/{player_id}/availability':
      '/api/v2/players/{player_id}/availability',
  '/api/v2/players/{player_id}/career': '/api/v2/players/{player_id}/career',
  '/api/v2/players/{player_id}/career-events':
      '/api/v2/players/{player_id}/career-events',
  '/api/v2/players/{player_id}/career/summary':
      '/api/v2/players/{player_id}/career/summary',
  '/api/v2/players/{player_id}/contracts':
      '/api/v2/players/{player_id}/contracts',
  '/api/v2/players/{player_id}/contracts/summary':
      '/api/v2/players/{player_id}/contracts/summary',
  '/api/v2/players/{player_id}/contracts/{contract_id}/renew':
      '/api/v2/players/{player_id}/contracts/{contract_id}/renew',
  '/api/v2/players/{player_id}/events': '/api/v2/players/{player_id}/events',
  '/api/v2/players/{player_id}/injuries':
      '/api/v2/players/{player_id}/injuries',
  '/api/v2/players/{player_id}/injuries/{injury_id}/recover':
      '/api/v2/players/{player_id}/injuries/{injury_id}/recover',
  '/api/v2/players/{player_id}/lifecycle-snapshot':
      '/api/v2/players/{player_id}/lifecycle-snapshot',
  '/api/v2/players/{player_id}/overview':
      '/api/v2/players/{player_id}/overview',
  '/api/v2/players/{player_id}/regen': '/api/v2/players/{player_id}/regen',
  '/api/v2/players/{player_id}/regen/big-club-approaches':
      '/api/v2/players/{player_id}/regen/big-club-approaches',
  '/api/v2/players/{player_id}/regen/contract-offers/quote':
      '/api/v2/players/{player_id}/regen/contract-offers/quote',
  '/api/v2/players/{player_id}/regen/offer-market':
      '/api/v2/players/{player_id}/regen/offer-market',
  '/api/v2/players/{player_id}/regen/pressure-resolution':
      '/api/v2/players/{player_id}/regen/pressure-resolution',
  '/api/v2/players/{player_id}/regen/special-training':
      '/api/v2/players/{player_id}/regen/special-training',
  '/api/v2/players/{player_id}/regen/transfer-listing':
      '/api/v2/players/{player_id}/regen/transfer-listing',
  '/api/v2/predictions': '/api/v2/predictions',
  '/api/v2/predictions/leaderboard': '/api/v2/predictions/leaderboard',
  '/api/v2/pundits/matches/{match_key}': '/api/v2/pundits/matches/{match_key}',
  '/api/v2/referrals/attribution': '/api/v2/referrals/attribution',
  '/api/v2/referrals/me/invites': '/api/v2/referrals/me/invites',
  '/api/v2/referrals/me/rewards': '/api/v2/referrals/me/rewards',
  '/api/v2/referrals/me/summary': '/api/v2/referrals/me/summary',
  '/api/v2/referrals/share-codes': '/api/v2/referrals/share-codes',
  '/api/v2/referrals/share-codes/me': '/api/v2/referrals/share-codes/me',
  '/api/v2/referrals/share-codes/{code}/redeem':
      '/api/v2/referrals/share-codes/{code}/redeem',
  '/api/v2/referrals/share-codes/{share_code_id}':
      '/api/v2/referrals/share-codes/{share_code_id}',
  '/api/v2/regen-universe/achievements': '/api/v2/regen-universe/achievements',
  '/api/v2/regen-universe/awards': '/api/v2/regen-universe/awards',
  '/api/v2/regen-universe/bloodlines': '/api/v2/regen-universe/bloodlines',
  '/api/v2/regen-universe/hall-of-fame': '/api/v2/regen-universe/hall-of-fame',
  '/api/v2/regen-universe/national-regens':
      '/api/v2/regen-universe/national-regens',
  '/api/v2/regen-universe/player/{player_id}':
      '/api/v2/regen-universe/player/{player_id}',
  '/api/v2/regen-universe/players/{player_id}':
      '/api/v2/regen-universe/players/{player_id}',
  '/api/v2/regen-universe/players/{player_id}/timeline':
      '/api/v2/regen-universe/players/{player_id}/timeline',
  '/api/v2/regen-universe/rankings': '/api/v2/regen-universe/rankings',
  '/api/v2/regen-universe/rising-stars': '/api/v2/regen-universe/rising-stars',
  '/api/v2/regen-universe/scouting-feed':
      '/api/v2/regen-universe/scouting-feed',
  '/api/v2/regen-universe/seasons': '/api/v2/regen-universe/seasons',
  '/api/v2/regen-universe/tracking': '/api/v2/regen-universe/tracking',
  '/api/v2/regen-universe/youth-tournaments':
      '/api/v2/regen-universe/youth-tournaments',
  '/api/v2/regen-universe/youth-tournaments/{tournament_id}':
      '/api/v2/regen-universe/youth-tournaments/{tournament_id}',
  '/api/v2/regens/awards': '/api/v2/regens/awards',
  '/api/v2/regens/awards/{award_id}/vote':
      '/api/v2/regens/awards/{award_id}/vote',
  '/api/v2/regens/creation-orders': '/api/v2/regens/creation-orders',
  '/api/v2/regens/creation-orders/{order_id}':
      '/api/v2/regens/creation-orders/{order_id}',
  '/api/v2/regens/creation-orders/{order_id}/generate-after-payment':
      '/api/v2/regens/creation-orders/{order_id}/generate-after-payment',
  '/api/v2/regens/creation-orders/{order_id}/pay-with-wallet':
      '/api/v2/regens/creation-orders/{order_id}/pay-with-wallet',
  '/api/v2/regens/feed': '/api/v2/regens/feed',
  '/api/v2/regens/jobs/{job_name}': '/api/v2/regens/jobs/{job_name}',
  '/api/v2/regens/request-son': '/api/v2/regens/request-son',
  '/api/v2/regens/request-son/options': '/api/v2/regens/request-son/options',
  '/api/v2/regens/rising': '/api/v2/regens/rising',
  '/api/v2/regens/top': '/api/v2/regens/top',
  '/api/v2/regens/{regen_id}/lineage': '/api/v2/regens/{regen_id}/lineage',
  '/api/v2/replays/countdown/{fixture_id}':
      '/api/v2/replays/countdown/{fixture_id}',
  '/api/v2/replays/me': '/api/v2/replays/me',
  '/api/v2/replays/public/featured': '/api/v2/replays/public/featured',
  '/api/v2/replays/{replay_id}': '/api/v2/replays/{replay_id}',
  '/api/v2/reward-engine/me/settlements':
      '/api/v2/reward-engine/me/settlements',
  '/api/v2/reward-engine/me/summary': '/api/v2/reward-engine/me/summary',
  '/api/v2/rivalries/matches': '/api/v2/rivalries/matches',
  '/api/v2/scout/report/{player_id}': '/api/v2/scout/report/{player_id}',
  '/api/v2/scouts': '/api/v2/scouts',
  '/api/v2/scouts/{scout_id}/discover': '/api/v2/scouts/{scout_id}/discover',
  '/api/v2/season-pass': '/api/v2/season-pass',
  '/api/v2/season-pass/claim': '/api/v2/season-pass/claim',
  '/api/v2/session/bootstrap': '/api/v2/session/bootstrap',
  '/api/v2/simulation-matchmaking/hosted-competitions/preview':
      '/api/v2/simulation-matchmaking/hosted-competitions/preview',
  '/api/v2/simulation-matchmaking/profiles/{user_id}':
      '/api/v2/simulation-matchmaking/profiles/{user_id}',
  '/api/v2/simulation-matchmaking/quick-game':
      '/api/v2/simulation-matchmaking/quick-game',
  '/api/v2/simulation-matchmaking/quick-tournament':
      '/api/v2/simulation-matchmaking/quick-tournament',
  '/api/v2/social/follows': '/api/v2/social/follows',
  '/api/v2/social/follows/me': '/api/v2/social/follows/me',
  '/api/v2/sponsors': '/api/v2/sponsors',
  '/api/v2/sponsorship/clubs/{club_id}/contracts':
      '/api/v2/sponsorship/clubs/{club_id}/contracts',
  '/api/v2/sponsorship/clubs/{club_id}/dashboard':
      '/api/v2/sponsorship/clubs/{club_id}/dashboard',
  '/api/v2/sponsorship/clubs/{club_id}/offers':
      '/api/v2/sponsorship/clubs/{club_id}/offers',
  '/api/v2/sponsorship/clubs/{club_id}/sponsors':
      '/api/v2/sponsorship/clubs/{club_id}/sponsors',
  '/api/v2/sponsorship/contracts/request':
      '/api/v2/sponsorship/contracts/request',
  '/api/v2/sponsorship/me/leads': '/api/v2/sponsorship/me/leads',
  '/api/v2/sponsorship/packages': '/api/v2/sponsorship/packages',
  '/api/v2/sponsorship/placements': '/api/v2/sponsorship/placements',
  '/api/v2/story-feed': '/api/v2/story-feed',
  '/api/v2/story-feed/digest': '/api/v2/story-feed/digest',
  '/api/v2/streamer-tournaments': '/api/v2/streamer-tournaments',
  '/api/v2/streamer-tournaments/mine': '/api/v2/streamer-tournaments/mine',
  '/api/v2/streamer-tournaments/{tournament_id}':
      '/api/v2/streamer-tournaments/{tournament_id}',
  '/api/v2/streamer-tournaments/{tournament_id}/invites':
      '/api/v2/streamer-tournaments/{tournament_id}/invites',
  '/api/v2/streamer-tournaments/{tournament_id}/join':
      '/api/v2/streamer-tournaments/{tournament_id}/join',
  '/api/v2/streamer-tournaments/{tournament_id}/publish':
      '/api/v2/streamer-tournaments/{tournament_id}/publish',
  '/api/v2/streamer-tournaments/{tournament_id}/rewards':
      '/api/v2/streamer-tournaments/{tournament_id}/rewards',
  '/api/v2/tickets/attendance/{match_id}/react':
      '/api/v2/tickets/attendance/{match_id}/react',
  '/api/v2/tickets/buy': '/api/v2/tickets/buy',
  '/api/v2/tickets/event/{match_id}': '/api/v2/tickets/event/{match_id}',
  '/api/v2/tickets/resell': '/api/v2/tickets/resell',
  '/api/v2/tickets/waitlist': '/api/v2/tickets/waitlist',
  '/api/v2/tournaments': '/api/v2/tournaments',
  '/api/v2/tournaments/{tournament_id}': '/api/v2/tournaments/{tournament_id}',
  '/api/v2/tournaments/{tournament_id}/advance':
      '/api/v2/tournaments/{tournament_id}/advance',
  '/api/v2/tournaments/{tournament_id}/join':
      '/api/v2/tournaments/{tournament_id}/join',
  '/api/v2/tournaments/{tournament_id}/matches/{match_id}/result':
      '/api/v2/tournaments/{tournament_id}/matches/{match_id}/result',
  '/api/v2/transfer-market/clubs/{club_id}/team-dynamics':
      '/api/v2/transfer-market/clubs/{club_id}/team-dynamics',
  '/api/v2/transfer-market/coaches/{club_id}/demands':
      '/api/v2/transfer-market/coaches/{club_id}/demands',
  '/api/v2/transfer-market/coaches/{club_id}/profile':
      '/api/v2/transfer-market/coaches/{club_id}/profile',
  '/api/v2/transfer-market/jobs/run': '/api/v2/transfer-market/jobs/run',
  '/api/v2/transfer-market/listings': '/api/v2/transfer-market/listings',
  '/api/v2/transfer-market/listings/{listing_id}':
      '/api/v2/transfer-market/listings/{listing_id}',
  '/api/v2/transfer-market/listings/{listing_id}/bids':
      '/api/v2/transfer-market/listings/{listing_id}/bids',
  '/api/v2/transfer-market/listings/{listing_id}/close':
      '/api/v2/transfer-market/listings/{listing_id}/close',
  '/api/v2/transfer-market/listings/{listing_id}/contract-offer':
      '/api/v2/transfer-market/listings/{listing_id}/contract-offer',
  '/api/v2/transfer-market/listings/{listing_id}/negotiation':
      '/api/v2/transfer-market/listings/{listing_id}/negotiation',
  '/api/v2/transfer-market/listings/{listing_id}/stream':
      '/api/v2/transfer-market/listings/{listing_id}/stream',
  '/api/v2/transfer-market/players/{player_id}/decision-profile':
      '/api/v2/transfer-market/players/{player_id}/decision-profile',
  '/api/v2/transfer-market/watchlist': '/api/v2/transfer-market/watchlist',
  '/api/v2/transfers/windows': '/api/v2/transfers/windows',
  '/api/v2/transfers/windows/{window_id}':
      '/api/v2/transfers/windows/{window_id}',
  '/api/v2/transfers/windows/{window_id}/bids':
      '/api/v2/transfers/windows/{window_id}/bids',
  '/api/v2/transfers/windows/{window_id}/bids/{bid_id}/accept':
      '/api/v2/transfers/windows/{window_id}/bids/{bid_id}/accept',
  '/api/v2/transfers/windows/{window_id}/bids/{bid_id}/reject':
      '/api/v2/transfers/windows/{window_id}/bids/{bid_id}/reject',
  '/api/v2/transfers/windows/{window_id}/players/{player_id}/regen-bid-evaluations':
      '/api/v2/transfers/windows/{window_id}/players/{player_id}/regen-bid-evaluations',
  '/api/v2/transfers/windows/{window_id}/players/{player_id}/resolve-regen-bid':
      '/api/v2/transfers/windows/{window_id}/players/{player_id}/resolve-regen-bid',
  '/api/v2/ultimate-league/competitors/{competitor_id}':
      '/api/v2/ultimate-league/competitors/{competitor_id}',
  '/api/v2/ultimate-league/matches/result':
      '/api/v2/ultimate-league/matches/result',
  '/api/v2/ultimate-league/matchmaking/batch':
      '/api/v2/ultimate-league/matchmaking/batch',
  '/api/v2/ultimate-league/standings/{tier}':
      '/api/v2/ultimate-league/standings/{tier}',
  '/api/v2/ultimate-league/tactical-presets':
      '/api/v2/ultimate-league/tactical-presets',
  '/api/v2/ultimate-league/tactical-presets/{preset_id}/purchase':
      '/api/v2/ultimate-league/tactical-presets/{preset_id}/purchase',
  '/api/v2/ultimate-league/tiers': '/api/v2/ultimate-league/tiers',
  '/api/v2/ultimate-league/tournaments': '/api/v2/ultimate-league/tournaments',
  '/api/v2/ultimate-league/tournaments/{tournament_id}':
      '/api/v2/ultimate-league/tournaments/{tournament_id}',
  '/api/v2/ultimate-league/tournaments/{tournament_id}/payouts/preview':
      '/api/v2/ultimate-league/tournaments/{tournament_id}/payouts/preview',
  '/api/v2/viral/accounts': '/api/v2/viral/accounts',
  '/api/v2/viral/cascades': '/api/v2/viral/cascades',
  '/api/v2/viral/clips/trending': '/api/v2/viral/clips/trending',
  '/api/v2/viral/clips/{clip_id}/variants':
      '/api/v2/viral/clips/{clip_id}/variants',
  '/api/v2/viral/clips/{clip_id}/winner':
      '/api/v2/viral/clips/{clip_id}/winner',
  '/api/v2/viral/feed': '/api/v2/viral/feed',
  '/api/v2/viral/feed/for-you': '/api/v2/viral/feed/for-you',
  '/api/v2/viral/matches/{match_key}/clips':
      '/api/v2/viral/matches/{match_key}/clips',
  '/api/v2/viral/sessions/{session_id}': '/api/v2/viral/sessions/{session_id}',
  '/api/v2/wallet': '/api/v2/wallet',
  '/api/v2/wallet/top-up/initiate': '/api/v2/wallet/top-up/initiate',
  '/api/v2/wallet/top-up/verify': '/api/v2/wallet/top-up/verify',
  '/api/v2/wallet/transactions': '/api/v2/wallet/transactions',
  '/api/v2/wallets': '/api/v2/wallets',
  '/api/v2/wallets/accounts': '/api/v2/wallets/accounts',
  '/api/v2/wallets/adaptive-overview': '/api/v2/wallets/adaptive-overview',
  '/api/v2/wallets/conversions': '/api/v2/wallets/conversions',
  '/api/v2/wallets/conversions/quote': '/api/v2/wallets/conversions/quote',
  '/api/v2/wallets/deposits': '/api/v2/wallets/deposits',
  '/api/v2/wallets/deposits/{deposit_id}/submit':
      '/api/v2/wallets/deposits/{deposit_id}/submit',
  '/api/v2/wallets/ledger': '/api/v2/wallets/ledger',
  '/api/v2/wallets/market-topups': '/api/v2/wallets/market-topups',
  '/api/v2/wallets/overview': '/api/v2/wallets/overview',
  '/api/v2/wallets/payment-events': '/api/v2/wallets/payment-events',
  '/api/v2/wallets/providers/{provider_key}/webhook':
      '/api/v2/wallets/providers/{provider_key}/webhook',
  '/api/v2/wallets/purchase-orders': '/api/v2/wallets/purchase-orders',
  '/api/v2/wallets/purchase-orders/quote':
      '/api/v2/wallets/purchase-orders/quote',
  '/api/v2/wallets/purchase-orders/{order_id}':
      '/api/v2/wallets/purchase-orders/{order_id}',
  '/api/v2/wallets/summary': '/api/v2/wallets/summary',
  '/api/v2/wallets/top-up/initiate': '/api/v2/wallets/top-up/initiate',
  '/api/v2/wallets/top-up/verify': '/api/v2/wallets/top-up/verify',
  '/api/v2/wallets/transactions': '/api/v2/wallets/transactions',
  '/api/v2/wallets/withdrawals': '/api/v2/wallets/withdrawals',
  '/api/v2/wallets/withdrawals/eligibility':
      '/api/v2/wallets/withdrawals/eligibility',
  '/api/v2/wallets/withdrawals/quote': '/api/v2/wallets/withdrawals/quote',
  '/api/v2/wallets/withdrawals/{withdrawal_id}/receipt':
      '/api/v2/wallets/withdrawals/{withdrawal_id}/receipt',
  '/api/v2/world-super-cup/countdown': '/api/v2/world-super-cup/countdown',
  '/api/v2/world-super-cup/groups/table':
      '/api/v2/world-super-cup/groups/table',
  '/api/v2/world-super-cup/knockout/bracket':
      '/api/v2/world-super-cup/knockout/bracket',
  '/api/v2/world-super-cup/playoff/draw':
      '/api/v2/world-super-cup/playoff/draw',
  '/api/v2/world-super-cup/qualification/explanation':
      '/api/v2/world-super-cup/qualification/explanation',
  '/api/v2/world/clubs/{club_id}/context':
      '/api/v2/world/clubs/{club_id}/context',
  '/api/v2/world/competitions/{competition_id}/context':
      '/api/v2/world/competitions/{competition_id}/context',
  '/api/v2/world/cultures': '/api/v2/world/cultures',
  '/api/v2/world/narratives': '/api/v2/world/narratives',
  '/api/value-engine/snapshots/rebuild':
      '/api/v2/value-engine/snapshots/rebuild',
  '/api/value-engine/snapshots/{player_id}/daily-closes':
      '/api/v2/value-engine/snapshots/{player_id}/daily-closes',
  '/api/value-engine/snapshots/{player_id}/history':
      '/api/v2/value-engine/snapshots/{player_id}/history',
  '/api/value-engine/snapshots/{player_id}/latest':
      '/api/v2/value-engine/snapshots/{player_id}/latest',
  '/api/value-engine/snapshots/{player_id}/trend-summary':
      '/api/v2/value-engine/snapshots/{player_id}/trend-summary',
  '/api/version': '/version',
  '/api/viral/accounts': '/api/v2/viral/accounts',
  '/api/viral/cascades': '/api/v2/viral/cascades',
  '/api/viral/clips/trending': '/api/v2/viral/clips/trending',
  '/api/viral/clips/{clip_id}/variants':
      '/api/v2/viral/clips/{clip_id}/variants',
  '/api/viral/clips/{clip_id}/winner': '/api/v2/viral/clips/{clip_id}/winner',
  '/api/viral/feed': '/api/v2/viral/feed',
  '/api/viral/feed/for-you': '/api/v2/viral/feed/for-you',
  '/api/viral/matches/{match_key}/clips':
      '/api/v2/viral/matches/{match_key}/clips',
  '/api/viral/sessions/{session_id}': '/api/v2/viral/sessions/{session_id}',
  '/api/wallet': '/api/v2/wallet',
  '/api/wallet/top-up/initiate': '/api/v2/wallet/top-up/initiate',
  '/api/wallet/top-up/verify': '/api/v2/wallet/top-up/verify',
  '/api/wallet/transactions': '/api/v2/wallet/transactions',
  '/api/wallets': '/api/v2/wallets',
  '/api/wallets/accounts': '/api/v2/wallets/accounts',
  '/api/wallets/adaptive-overview': '/api/v2/wallets/adaptive-overview',
  '/api/wallets/conversions': '/api/v2/wallets/conversions',
  '/api/wallets/conversions/quote': '/api/v2/wallets/conversions/quote',
  '/api/wallets/deposits': '/api/v2/wallets/deposits',
  '/api/wallets/deposits/{deposit_id}/submit':
      '/api/v2/wallets/deposits/{deposit_id}/submit',
  '/api/wallets/ledger': '/api/v2/wallets/ledger',
  '/api/wallets/market-topups': '/api/v2/wallets/market-topups',
  '/api/wallets/overview': '/api/v2/wallets/overview',
  '/api/wallets/payment-events': '/api/v2/wallets/payment-events',
  '/api/wallets/providers/{provider_key}/webhook':
      '/api/v2/wallets/providers/{provider_key}/webhook',
  '/api/wallets/purchase-orders': '/api/v2/wallets/purchase-orders',
  '/api/wallets/purchase-orders/quote': '/api/v2/wallets/purchase-orders/quote',
  '/api/wallets/purchase-orders/{order_id}':
      '/api/v2/wallets/purchase-orders/{order_id}',
  '/api/wallets/summary': '/api/v2/wallets/summary',
  '/api/wallets/top-up/initiate': '/api/v2/wallets/top-up/initiate',
  '/api/wallets/top-up/verify': '/api/v2/wallets/top-up/verify',
  '/api/wallets/transactions': '/api/v2/wallets/transactions',
  '/api/wallets/withdrawals': '/api/v2/wallets/withdrawals',
  '/api/wallets/withdrawals/eligibility':
      '/api/v2/wallets/withdrawals/eligibility',
  '/api/wallets/withdrawals/quote': '/api/v2/wallets/withdrawals/quote',
  '/api/wallets/withdrawals/{withdrawal_id}/receipt':
      '/api/v2/wallets/withdrawals/{withdrawal_id}/receipt',
  '/api/world-super-cup/countdown': '/api/v2/world-super-cup/countdown',
  '/api/world-super-cup/groups/table': '/api/v2/world-super-cup/groups/table',
  '/api/world-super-cup/knockout/bracket':
      '/api/v2/world-super-cup/knockout/bracket',
  '/api/world-super-cup/playoff/draw': '/api/v2/world-super-cup/playoff/draw',
  '/api/world-super-cup/qualification/explanation':
      '/api/v2/world-super-cup/qualification/explanation',
  '/api/world/clubs/{club_id}/context': '/api/v2/world/clubs/{club_id}/context',
  '/api/world/competitions/{competition_id}/context':
      '/api/v2/world/competitions/{competition_id}/context',
  '/api/world/cultures': '/api/v2/world/cultures',
  '/api/world/narratives': '/api/v2/world/narratives',
  '/auth/confirm-email': '/api/v2/auth/confirm-email',
  '/auth/login': '/api/v2/auth/login',
  '/auth/logout': '/api/v2/auth/logout',
  '/auth/recovery/request': '/api/v2/auth/recovery/request',
  '/auth/recovery/reset': '/api/v2/auth/recovery/reset',
  '/auth/refresh': '/api/v2/auth/refresh',
  '/auth/signup/creator': '/api/v2/auth/signup/creator',
  '/auth/signup/trader': '/api/v2/auth/signup/trader',
  '/auth/signup/user': '/api/v2/auth/signup/user',
  '/awards/categories': '/api/v2/awards/categories',
  '/awards/ceremony': '/api/v2/awards/ceremony',
  '/awards/ceremony/tickets': '/api/v2/awards/ceremony/tickets',
  '/awards/ceremony/vote': '/api/v2/awards/ceremony/vote',
  '/awards/nominees': '/api/v2/awards/nominees',
  '/awards/winners': '/api/v2/awards/winners',
  '/bets/history': '/api/v2/bets/history',
  '/bets/odds/{match_id}': '/api/v2/bets/odds/{match_id}',
  '/bets/place': '/api/v2/bets/place',
  '/bets/preferences': '/api/v2/bets/preferences',
  '/broadcast-rights/auctions/{auction_id}/bids':
      '/api/v2/broadcast-rights/auctions/{auction_id}/bids',
  '/broadcast-rights/competitions/{competition_id}':
      '/api/v2/broadcast-rights/competitions/{competition_id}',
  '/broadcast-rights/competitions/{competition_id}/acquire':
      '/api/v2/broadcast-rights/competitions/{competition_id}/acquire',
  '/broadcast-rights/competitions/{competition_id}/auctions':
      '/api/v2/broadcast-rights/competitions/{competition_id}/auctions',
  '/broadcast-rights/matches/{match_id}/access':
      '/api/v2/broadcast-rights/matches/{match_id}/access',
  '/broadcast-rights/matches/{match_id}/distribute':
      '/api/v2/broadcast-rights/matches/{match_id}/distribute',
  '/broadcast-rights/{right_id}/grants':
      '/api/v2/broadcast-rights/{right_id}/grants',
  '/broadcast/channels': '/api/v2/broadcast/channels',
  '/broadcast/{match_id}': '/api/v2/broadcast/{match_id}',
  '/calendar-engine/dashboard': '/api/v2/calendar-engine/dashboard',
  '/calendar-engine/events': '/api/v2/calendar-engine/events',
  '/calendar-engine/lifecycle-runs': '/api/v2/calendar-engine/lifecycle-runs',
  '/calendar-engine/pause-status': '/api/v2/calendar-engine/pause-status',
  '/calendar-engine/seasons': '/api/v2/calendar-engine/seasons',
  '/campaigns': '/api/v2/campaigns',
  '/campaigns/create': '/api/v2/campaigns/create',
  '/campaigns/{id}/accept': '/api/v2/campaigns/{id}/accept',
  '/campaigns/{id}/apply': '/api/v2/campaigns/{id}/apply',
  '/campaigns/{id}/performance': '/api/v2/campaigns/{id}/performance',
  '/career/create': '/api/v2/career/create',
  '/career/retire': '/api/v2/career/retire',
  '/career/train': '/api/v2/career/train',
  '/career/transfer': '/api/v2/career/transfer',
  '/career/{user_id}': '/api/v2/career/{user_id}',
  '/champions-league/knockout-bracket':
      '/api/v2/champions-league/knockout-bracket',
  '/champions-league/league-phase/table':
      '/api/v2/champions-league/league-phase/table',
  '/champions-league/playoff-bracket':
      '/api/v2/champions-league/playoff-bracket',
  '/champions-league/prize-pool/preview':
      '/api/v2/champions-league/prize-pool/preview',
  '/champions-league/qualification-map':
      '/api/v2/champions-league/qualification-map',
  '/club-infra/clubs/{club_id}': '/api/v2/club-infra/clubs/{club_id}',
  '/club-infra/clubs/{club_id}/support':
      '/api/v2/club-infra/clubs/{club_id}/support',
  '/club-infra/my': '/api/v2/club-infra/my',
  '/club-infra/my/facilities/upgrade':
      '/api/v2/club-infra/my/facilities/upgrade',
  '/club-infra/my/stadium/upgrade': '/api/v2/club-infra/my/stadium/upgrade',
  '/club/identity': '/api/v2/club/identity',
  '/clubs/marketplace': '/api/v2/clubs/marketplace',
  '/clubs/{club_id}': '/api/v2/clubs/{club_id}',
  '/clubs/{club_id}/buy-tokens': '/api/v2/clubs/{club_id}/buy-tokens',
  '/clubs/{club_id}/ownership': '/api/v2/clubs/{club_id}/ownership',
  '/clubs/{club_id}/proposals': '/api/v2/clubs/{club_id}/proposals',
  '/clubs/{club_id}/sell-tokens': '/api/v2/clubs/{club_id}/sell-tokens',
  '/clubs/{club_id}/treasury': '/api/v2/clubs/{club_id}/treasury',
  '/clubs/{club_id}/vote': '/api/v2/clubs/{club_id}/vote',
  '/commentary/profiles': '/api/v2/commentary/profiles',
  '/commentary/select': '/api/v2/commentary/select',
  '/community/creator-clubs/{club_id}/fan-competitions':
      '/api/v2/community/creator-clubs/{club_id}/fan-competitions',
  '/community/creator-clubs/{club_id}/fan-groups':
      '/api/v2/community/creator-clubs/{club_id}/fan-groups',
  '/community/creator-clubs/{club_id}/fan-state':
      '/api/v2/community/creator-clubs/{club_id}/fan-state',
  '/community/creator-clubs/{club_id}/follow':
      '/api/v2/community/creator-clubs/{club_id}/follow',
  '/community/creator-matches/{match_id}/chat-room':
      '/api/v2/community/creator-matches/{match_id}/chat-room',
  '/community/creator-matches/{match_id}/chat-room/messages':
      '/api/v2/community/creator-matches/{match_id}/chat-room/messages',
  '/community/creator-matches/{match_id}/fan-wall':
      '/api/v2/community/creator-matches/{match_id}/fan-wall',
  '/community/creator-matches/{match_id}/rivalry-signals':
      '/api/v2/community/creator-matches/{match_id}/rivalry-signals',
  '/community/creator-matches/{match_id}/tactical-advice':
      '/api/v2/community/creator-matches/{match_id}/tactical-advice',
  '/community/digest': '/api/v2/community/digest',
  '/community/fan-competitions/{fan_competition_id}/join':
      '/api/v2/community/fan-competitions/{fan_competition_id}/join',
  '/community/fan-groups/{group_id}/join':
      '/api/v2/community/fan-groups/{group_id}/join',
  '/community/live-threads': '/api/v2/community/live-threads',
  '/community/live-threads/{thread_id}':
      '/api/v2/community/live-threads/{thread_id}',
  '/community/live-threads/{thread_id}/messages':
      '/api/v2/community/live-threads/{thread_id}/messages',
  '/community/private-messages/threads':
      '/api/v2/community/private-messages/threads',
  '/community/private-messages/threads/{thread_id}':
      '/api/v2/community/private-messages/threads/{thread_id}',
  '/community/private-messages/threads/{thread_id}/messages':
      '/api/v2/community/private-messages/threads/{thread_id}/messages',
  '/community/watchlist': '/api/v2/community/watchlist',
  '/community/watchlist/{competition_key}':
      '/api/v2/community/watchlist/{competition_key}',
  '/competitions': '/api/v2/competitions',
  '/competitive-integrity/fast-game/runs':
      '/api/v2/competitive-integrity/fast-game/runs',
  '/competitive-integrity/fast-game/runs/{run_id}':
      '/api/v2/competitive-integrity/fast-game/runs/{run_id}',
  '/competitive-integrity/fast-game/runs/{run_id}/play':
      '/api/v2/competitive-integrity/fast-game/runs/{run_id}/play',
  '/competitive-integrity/managers': '/api/v2/competitive-integrity/managers',
  '/competitive-integrity/managers/candidates':
      '/api/v2/competitive-integrity/managers/candidates',
  '/competitive-integrity/managers/{manager_id}/instructions':
      '/api/v2/competitive-integrity/managers/{manager_id}/instructions',
  '/competitive-integrity/matches': '/api/v2/competitive-integrity/matches',
  '/competitive-integrity/matches/{match_id}':
      '/api/v2/competitive-integrity/matches/{match_id}',
  '/competitive-integrity/matches/{match_id}/execute':
      '/api/v2/competitive-integrity/matches/{match_id}/execute',
  '/competitive-integrity/notifications/events':
      '/api/v2/competitive-integrity/notifications/events',
  '/config/current': '/api/v2/config/current',
  '/config/update': '/api/v2/config/update',
  '/conversations': '/api/v2/conversations',
  '/conversations/start': '/api/v2/conversations/start',
  '/conversations/{conversation_id}/message':
      '/api/v2/conversations/{conversation_id}/message',
  '/conversations/{conversation_id}/messages':
      '/api/v2/conversations/{conversation_id}/messages',
  '/conversations/{conversation_id}/status':
      '/api/v2/conversations/{conversation_id}/status',
  '/creator-campaigns': '/api/v2/creator-campaigns',
  '/creator-campaigns/me': '/api/v2/creator-campaigns/me',
  '/creator-campaigns/{campaign_id}': '/api/v2/creator-campaigns/{campaign_id}',
  '/creator-campaigns/{campaign_id}/metrics':
      '/api/v2/creator-campaigns/{campaign_id}/metrics',
  '/creator-campaigns/{campaign_id}/snapshot':
      '/api/v2/creator-campaigns/{campaign_id}/snapshot',
  '/creator-campaigns/{campaign_id}/snapshots':
      '/api/v2/creator-campaigns/{campaign_id}/snapshots',
  '/creator-league': '/api/v2/creator-league',
  '/creator-league/config': '/api/v2/creator-league/config',
  '/creator-league/financial-report': '/api/v2/creator-league/financial-report',
  '/creator-league/financial-settlements':
      '/api/v2/creator-league/financial-settlements',
  '/creator-league/financial-settlements/{settlement_id}/approve':
      '/api/v2/creator-league/financial-settlements/{settlement_id}/approve',
  '/creator-league/live-priority': '/api/v2/creator-league/live-priority',
  '/creator-league/reset': '/api/v2/creator-league/reset',
  '/creator-league/season-tiers/{season_tier_id}/standings':
      '/api/v2/creator-league/season-tiers/{season_tier_id}/standings',
  '/creator-league/seasons': '/api/v2/creator-league/seasons',
  '/creator-league/seasons/{season_id}':
      '/api/v2/creator-league/seasons/{season_id}',
  '/creator-league/seasons/{season_id}/pause':
      '/api/v2/creator-league/seasons/{season_id}/pause',
  '/creator-league/tiers': '/api/v2/creator-league/tiers',
  '/creator-league/tiers/{tier_id}': '/api/v2/creator-league/tiers/{tier_id}',
  '/creator/application': '/api/v2/creator/application',
  '/creator/apply': '/api/v2/creator/apply',
  '/creator/cards': '/api/v2/creator/cards',
  '/creator/cards/listings': '/api/v2/creator/cards/listings',
  '/creator/cards/listings/{listing_id}/buy':
      '/api/v2/creator/cards/listings/{listing_id}/buy',
  '/creator/cards/loans/{loan_id}/return':
      '/api/v2/creator/cards/loans/{loan_id}/return',
  '/creator/cards/swap': '/api/v2/creator/cards/swap',
  '/creator/cards/{creator_card_id}/list':
      '/api/v2/creator/cards/{creator_card_id}/list',
  '/creator/cards/{creator_card_id}/loan':
      '/api/v2/creator/cards/{creator_card_id}/loan',
  '/creator/clubs/{club_id}/fan-share-market':
      '/api/v2/creator/clubs/{club_id}/fan-share-market',
  '/creator/clubs/{club_id}/fan-share-market/distributions':
      '/api/v2/creator/clubs/{club_id}/fan-share-market/distributions',
  '/creator/clubs/{club_id}/fan-share-market/holding':
      '/api/v2/creator/clubs/{club_id}/fan-share-market/holding',
  '/creator/clubs/{club_id}/fan-share-market/purchase':
      '/api/v2/creator/clubs/{club_id}/fan-share-market/purchase',
  '/creator/verify-email': '/api/v2/creator/verify-email',
  '/creator/verify-phone': '/api/v2/creator/verify-phone',
  '/creators/marketplace': '/api/v2/creators/marketplace',
  '/creators/me/copilot/analyze': '/api/v2/creators/me/copilot/analyze',
  '/creators/me/insights': '/api/v2/creators/me/insights',
  '/creators/me/reputation': '/api/v2/creators/me/reputation',
  '/daily-challenges': '/api/v2/daily-challenges',
  '/daily-challenges/me': '/api/v2/daily-challenges/me',
  '/daily-challenges/{challenge_key}/claim':
      '/api/v2/daily-challenges/{challenge_key}/claim',
  '/diagnostics': '/api/v2/diagnostics',
  '/discovery/home': '/api/v2/discovery/home',
  '/discovery/saved-searches': '/api/v2/discovery/saved-searches',
  '/discovery/saved-searches/{search_id}':
      '/api/v2/discovery/saved-searches/{search_id}',
  '/discovery/search': '/api/v2/discovery/search',
  '/disputes': '/api/v2/disputes',
  '/disputes/me': '/api/v2/disputes/me',
  '/disputes/{dispute_id}': '/api/v2/disputes/{dispute_id}',
  '/disputes/{dispute_id}/messages': '/api/v2/disputes/{dispute_id}/messages',
  '/dynasty': '/api/v2/dynasty',
  '/dynasty/leaderboard': '/api/v2/dynasty/leaderboard',
  '/economy/fx/quote': '/api/v2/economy/fx/quote',
  '/economy/gift-catalog': '/api/v2/economy/gift-catalog',
  '/economy/service-pricing': '/api/v2/economy/service-pricing',
  '/engagement/achievements': '/api/v2/engagement/achievements',
  '/engagement/achievements/me': '/api/v2/engagement/achievements/me',
  '/engagement/milestones/me': '/api/v2/engagement/milestones/me',
  '/engagement/sync': '/api/v2/engagement/sync',
  '/enter': '/api/v2/enter',
  '/events/clip': '/api/v2/events/clip',
  '/events/today': '/api/v2/events/today',
  '/events/upcoming': '/api/v2/events/upcoming',
  '/experience/full-simulation': '/api/v2/experience/full-simulation',
  '/fan-predictions/creator-clubs/{club_id}/leaderboards/weekly':
      '/api/v2/fan-predictions/creator-clubs/{club_id}/leaderboards/weekly',
  '/fan-predictions/leaderboards/weekly':
      '/api/v2/fan-predictions/leaderboards/weekly',
  '/fan-predictions/matches/{match_id}':
      '/api/v2/fan-predictions/matches/{match_id}',
  '/fan-predictions/matches/{match_id}/leaderboard':
      '/api/v2/fan-predictions/matches/{match_id}/leaderboard',
  '/fan-predictions/matches/{match_id}/submissions':
      '/api/v2/fan-predictions/matches/{match_id}/submissions',
  '/fan-predictions/me/submissions': '/api/v2/fan-predictions/me/submissions',
  '/fan-predictions/me/tokens': '/api/v2/fan-predictions/me/tokens',
  '/fan-wars/leaderboards/{board_type}':
      '/api/v2/fan-wars/leaderboards/{board_type}',
  '/fan-wars/nations-cup/{competition_id}':
      '/api/v2/fan-wars/nations-cup/{competition_id}',
  '/fan-wars/profiles/{profile_id}/dashboard':
      '/api/v2/fan-wars/profiles/{profile_id}/dashboard',
  '/fan-wars/rivalries/{board_type}': '/api/v2/fan-wars/rivalries/{board_type}',
  '/fans/profile': '/api/v2/fans/profile',
  '/fans/tribe/join': '/api/v2/fans/tribe/join',
  '/fans/{club_id}': '/api/v2/fans/{club_id}',
  '/fast-cups/upcoming': '/api/v2/fast-cups/upcoming',
  '/fast-cups/{cup_id}/bracket': '/api/v2/fast-cups/{cup_id}/bracket',
  '/fast-cups/{cup_id}/countdown': '/api/v2/fast-cups/{cup_id}/countdown',
  '/fast-cups/{cup_id}/join': '/api/v2/fast-cups/{cup_id}/join',
  '/fast-cups/{cup_id}/result-summary':
      '/api/v2/fast-cups/{cup_id}/result-summary',
  '/federations': '/api/v2/federations',
  '/federations/proposals/{proposal_id}/votes':
      '/api/v2/federations/proposals/{proposal_id}/votes',
  '/federations/rankings': '/api/v2/federations/rankings',
  '/federations/regional-tournaments':
      '/api/v2/federations/regional-tournaments',
  '/federations/{federation_id}': '/api/v2/federations/{federation_id}',
  '/federations/{federation_id}/governance':
      '/api/v2/federations/{federation_id}/governance',
  '/federations/{federation_id}/leagues':
      '/api/v2/federations/{federation_id}/leagues',
  '/federations/{federation_id}/memberships':
      '/api/v2/federations/{federation_id}/memberships',
  '/federations/{federation_id}/narratives':
      '/api/v2/federations/{federation_id}/narratives',
  '/federations/{federation_id}/proposals':
      '/api/v2/federations/{federation_id}/proposals',
  '/federations/{federation_id}/sanctions':
      '/api/v2/federations/{federation_id}/sanctions',
  '/federations/{federation_id}/treasury/distribute':
      '/api/v2/federations/{federation_id}/treasury/distribute',
  '/federations/{federation_id}/validate-action':
      '/api/v2/federations/{federation_id}/validate-action',
  '/feed/following': '/api/v2/feed/following',
  '/feed/for-you': '/api/v2/feed/for-you',
  '/feed/for-you/refresh': '/api/v2/feed/for-you/refresh',
  '/feed/sponsored': '/api/v2/feed/sponsored',
  '/finance': '/api/v2/finance',
  '/follow/{user_id}': '/api/v2/follow/{user_id}',
  '/football-events/players/{player_id}/events':
      '/api/v2/football-events/players/{player_id}/events',
  '/football-events/players/{player_id}/impact':
      '/api/v2/football-events/players/{player_id}/impact',
  '/gift-engine/me/combos': '/api/v2/gift-engine/me/combos',
  '/gift-engine/me/summary': '/api/v2/gift-engine/me/summary',
  '/gift-engine/me/transactions': '/api/v2/gift-engine/me/transactions',
  '/gift-engine/send': '/api/v2/gift-engine/send',
  '/governance/clubs/{club_id}/panel':
      '/api/v2/governance/clubs/{club_id}/panel',
  '/governance/me/overview': '/api/v2/governance/me/overview',
  '/governance/proposals': '/api/v2/governance/proposals',
  '/governance/proposals/{proposal_id}':
      '/api/v2/governance/proposals/{proposal_id}',
  '/governance/proposals/{proposal_id}/vote':
      '/api/v2/governance/proposals/{proposal_id}/vote',
  '/gtex/market/buy': '/api/v2/gtex/market/buy',
  '/gtex/market/sell': '/api/v2/gtex/market/sell',
  '/hall-of-fame': '/api/v2/hall-of-fame',
  '/history/goat-rankings': '/api/v2/history/goat-rankings',
  '/history/leaderboards': '/api/v2/history/leaderboards',
  '/history/records': '/api/v2/history/records',
  '/history/timeline/{subject_type}/{subject_id}':
      '/api/v2/history/timeline/{subject_type}/{subject_id}',
  '/hosted-competitions': '/api/v2/hosted-competitions',
  '/hosted-competitions/mine': '/api/v2/hosted-competitions/mine',
  '/hosted-competitions/mine/invites':
      '/api/v2/hosted-competitions/mine/invites',
  '/hosted-competitions/templates': '/api/v2/hosted-competitions/templates',
  '/hosted-competitions/{competition_id}':
      '/api/v2/hosted-competitions/{competition_id}',
  '/hosted-competitions/{competition_id}/finance':
      '/api/v2/hosted-competitions/{competition_id}/finance',
  '/hosted-competitions/{competition_id}/invites':
      '/api/v2/hosted-competitions/{competition_id}/invites',
  '/hosted-competitions/{competition_id}/invites/accept':
      '/api/v2/hosted-competitions/{competition_id}/invites/accept',
  '/hosted-competitions/{competition_id}/join':
      '/api/v2/hosted-competitions/{competition_id}/join',
  '/hosted-competitions/{competition_id}/launch':
      '/api/v2/hosted-competitions/{competition_id}/launch',
  '/hosted-competitions/{competition_id}/standings':
      '/api/v2/hosted-competitions/{competition_id}/standings',
  '/infinite-league/economy': '/api/v2/infinite-league/economy',
  '/infinite-league/livestream': '/api/v2/infinite-league/livestream',
  '/infinite-league/matches': '/api/v2/infinite-league/matches',
  '/infinite-league/matches/{match_id}':
      '/api/v2/infinite-league/matches/{match_id}',
  '/infinite-league/pundits/{match_id}':
      '/api/v2/infinite-league/pundits/{match_id}',
  '/infinite-league/status': '/api/v2/infinite-league/status',
  '/infinite-league/tick': '/api/v2/infinite-league/tick',
  '/infinite-league/viral-feed': '/api/v2/infinite-league/viral-feed',
  '/integrations/payments/korapay/webhook':
      '/api/v2/integrations/payments/korapay/webhook',
  '/integrations/payments/methods': '/api/v2/integrations/payments/methods',
  '/integrations/payments/orders': '/api/v2/integrations/payments/orders',
  '/integrations/payments/paystack/webhook':
      '/api/v2/integrations/payments/paystack/webhook',
  '/integrations/payments/quote': '/api/v2/integrations/payments/quote',
  '/integrity-engine/me/incidents': '/api/v2/integrity-engine/me/incidents',
  '/integrity-engine/me/score': '/api/v2/integrity-engine/me/score',
  '/internal/ingestion/bootstrap-sync':
      '/api/v2/internal/ingestion/bootstrap-sync',
  '/internal/ingestion/clubs/{club_external_id}/refresh':
      '/api/v2/internal/ingestion/clubs/{club_external_id}/refresh',
  '/internal/ingestion/competitions/{competition_external_id}/refresh':
      '/api/v2/internal/ingestion/competitions/{competition_external_id}/refresh',
  '/internal/ingestion/cursors/{provider_name}':
      '/api/v2/internal/ingestion/cursors/{provider_name}',
  '/internal/ingestion/incremental-sync':
      '/api/v2/internal/ingestion/incremental-sync',
  '/internal/ingestion/players/{player_external_id}/refresh':
      '/api/v2/internal/ingestion/players/{player_external_id}/refresh',
  '/internal/ingestion/providers/{provider_name}/health':
      '/api/v2/internal/ingestion/providers/{provider_name}/health',
  '/internal/ingestion/real-players/batches':
      '/api/v2/internal/ingestion/real-players/batches',
  '/internal/ingestion/real-players/batches/{batch_id}':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}',
  '/internal/ingestion/real-players/batches/{batch_id}/issues':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}/issues',
  '/internal/ingestion/real-players/batches/{batch_id}/resume':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}/resume',
  '/internal/ingestion/real-players/batches/{batch_id}/valuation-status':
      '/api/v2/internal/ingestion/real-players/batches/{batch_id}/valuation-status',
  '/internal/ingestion/real-players/import':
      '/api/v2/internal/ingestion/real-players/import',
  '/internal/ingestion/real-players/publish-jobs':
      '/api/v2/internal/ingestion/real-players/publish-jobs',
  '/internal/ingestion/real-players/publish-jobs/{job_id}':
      '/api/v2/internal/ingestion/real-players/publish-jobs/{job_id}',
  '/internal/ingestion/real-players/status':
      '/api/v2/internal/ingestion/real-players/status',
  '/internal/ingestion/runs': '/api/v2/internal/ingestion/runs',
  '/internal/ingestion/status': '/api/v2/internal/ingestion/status',
  '/jackpot/contribute': '/api/v2/jackpot/contribute',
  '/jackpot/history': '/api/v2/jackpot/history',
  '/jackpot/state': '/api/v2/jackpot/state',
  '/jobs/{job_id}': '/api/v2/jobs/{job_id}',
  '/leaderboard/division/{division}': '/api/v2/leaderboard/division/{division}',
  '/leaderboard/global': '/api/v2/leaderboard/global',
  '/leaderboard/player/{player_id}': '/api/v2/leaderboard/player/{player_id}',
  '/leaderboard/region/{region}': '/api/v2/leaderboard/region/{region}',
  '/leagues/register': '/api/v2/leagues/register',
  '/leagues/{season_id}/fixtures': '/api/v2/leagues/{season_id}/fixtures',
  '/leagues/{season_id}/qualification-markers':
      '/api/v2/leagues/{season_id}/qualification-markers',
  '/leagues/{season_id}/standings': '/api/v2/leagues/{season_id}/standings',
  '/leagues/{season_id}/summary': '/api/v2/leagues/{season_id}/summary',
  '/legacy/board': '/api/v2/legacy/board',
  '/live-events': '/api/v2/live-events',
  '/manager-duels': '/api/v2/manager-duels',
  '/manager-duels/leaderboard': '/api/v2/manager-duels/leaderboard',
  '/manager-duels/{duel_id}': '/api/v2/manager-duels/{duel_id}',
  '/managers': '/api/v2/managers',
  '/managers/leaderboard': '/api/v2/managers/leaderboard',
  '/managers/{manager_id}': '/api/v2/managers/{manager_id}',
  '/managers/{manager_id}/hire': '/api/v2/managers/{manager_id}/hire',
  '/managers/{manager_id}/history': '/api/v2/managers/{manager_id}/history',
  '/managers/{manager_id}/release': '/api/v2/managers/{manager_id}/release',
  '/market/buy': '/api/v2/market/buy',
  '/market/listings': '/api/v2/market/listings',
  '/market/listings/{listing_id}/cancel':
      '/api/v2/market/listings/{listing_id}/cancel',
  '/market/listings/{listing_id}/matches':
      '/api/v2/market/listings/{listing_id}/matches',
  '/market/listings/{listing_id}/offers':
      '/api/v2/market/listings/{listing_id}/offers',
  '/market/movers': '/api/v2/market/movers',
  '/market/offers': '/api/v2/market/offers',
  '/market/offers/{offer_id}/accept': '/api/v2/market/offers/{offer_id}/accept',
  '/market/offers/{offer_id}/counter':
      '/api/v2/market/offers/{offer_id}/counter',
  '/market/offers/{offer_id}/reject': '/api/v2/market/offers/{offer_id}/reject',
  '/market/players': '/api/v2/market/players',
  '/market/players/{player_id}': '/api/v2/market/players/{player_id}',
  '/market/players/{player_id}/candles':
      '/api/v2/market/players/{player_id}/candles',
  '/market/players/{player_id}/history':
      '/api/v2/market/players/{player_id}/history',
  '/market/sell': '/api/v2/market/sell',
  '/market/summary/{asset_id}': '/api/v2/market/summary/{asset_id}',
  '/market/ticker/{player_id}': '/api/v2/market/ticker/{player_id}',
  '/market/trade-intents': '/api/v2/market/trade-intents',
  '/market/trade-intents/{intent_id}/withdraw':
      '/api/v2/market/trade-intents/{intent_id}/withdraw',
  '/market/trending': '/api/v2/market/trending',
  '/marketplace/my-players': '/api/v2/marketplace/my-players',
  '/marketplace/players': '/api/v2/marketplace/players',
  '/marketplace/players/{player_id}': '/api/v2/marketplace/players/{player_id}',
  '/match-engine/analytics': '/api/v2/match-engine/analytics',
  '/match-engine/analytics/{match_key}':
      '/api/v2/match-engine/analytics/{match_key}',
  '/match-engine/highlights/{match_key}':
      '/api/v2/match-engine/highlights/{match_key}',
  '/match-engine/live-feed/{match_key}':
      '/api/v2/match-engine/live-feed/{match_key}',
  '/match-engine/render-sync': '/api/v2/match-engine/render-sync',
  '/match-engine/render-sync/{match_key}':
      '/api/v2/match-engine/render-sync/{match_key}',
  '/match-engine/replay': '/api/v2/match-engine/replay',
  '/match-engine/simulate': '/api/v2/match-engine/simulate',
  '/match-engine/summary': '/api/v2/match-engine/summary',
  '/match-engine/timeline': '/api/v2/match-engine/timeline',
  '/match-viewer/{match_key}': '/api/v2/match-viewer/{match_key}',
  '/match-viewer/{match_key}/illusion':
      '/api/v2/match-viewer/{match_key}/illusion',
  '/match-viewer/{match_key}/session':
      '/api/v2/match-viewer/{match_key}/session',
  '/match/find': '/api/v2/match/find',
  '/match/live/active': '/api/v2/match/live/active',
  '/match/{match_id}/commentary/stream':
      '/api/v2/match/{match_id}/commentary/stream',
  '/match/{match_id}/live': '/api/v2/match/{match_id}/live',
  '/match/{match_id}/unity-access': '/api/v2/match/{match_id}/unity-access',
  '/match/{match_id}/unity-access/refresh':
      '/api/v2/match/{match_id}/unity-access/refresh',
  '/matches/complete': '/api/v2/matches/complete',
  '/matches/live/active': '/api/v2/matches/live/active',
  '/matches/start': '/api/v2/matches/start',
  '/matches/{match_id}/analysis': '/api/v2/matches/{match_id}/analysis',
  '/matches/{match_id}/audio/stems/stream':
      '/api/v2/matches/{match_id}/audio/stems/stream',
  '/matches/{match_id}/chat/messages':
      '/api/v2/matches/{match_id}/chat/messages',
  '/matches/{match_id}/commentary': '/api/v2/matches/{match_id}/commentary',
  '/matches/{match_id}/commentary/stream':
      '/api/v2/matches/{match_id}/commentary/stream',
  '/matches/{match_id}/fan-experience':
      '/api/v2/matches/{match_id}/fan-experience',
  '/matches/{match_id}/highlights': '/api/v2/matches/{match_id}/highlights',
  '/matches/{match_id}/live': '/api/v2/matches/{match_id}/live',
  '/matches/{match_id}/reactions': '/api/v2/matches/{match_id}/reactions',
  '/matches/{match_id}/replay': '/api/v2/matches/{match_id}/replay',
  '/matches/{match_id}/social-warfare':
      '/api/v2/matches/{match_id}/social-warfare',
  '/matches/{match_id}/spectate': '/api/v2/matches/{match_id}/spectate',
  '/matches/{match_id}/spectators': '/api/v2/matches/{match_id}/spectators',
  '/matches/{match_id}/stream': '/api/v2/matches/{match_id}/stream',
  '/matches/{match_id}/tickets': '/api/v2/matches/{match_id}/tickets',
  '/matches/{match_id}/unity-access': '/api/v2/matches/{match_id}/unity-access',
  '/matches/{match_id}/unity-access/refresh':
      '/api/v2/matches/{match_id}/unity-access/refresh',
  '/media': '/api/v2/media',
  '/media-engine/creator-league/broadcast-modes':
      '/api/v2/media-engine/creator-league/broadcast-modes',
  '/media-engine/creator-league/clubs/{club_id}/stadium':
      '/api/v2/media-engine/creator-league/clubs/{club_id}/stadium',
  '/media-engine/creator-league/matches/{match_id}/access':
      '/api/v2/media-engine/creator-league/matches/{match_id}/access',
  '/media-engine/creator-league/matches/{match_id}/analytics':
      '/api/v2/media-engine/creator-league/matches/{match_id}/analytics',
  '/media-engine/creator-league/matches/{match_id}/gifts':
      '/api/v2/media-engine/creator-league/matches/{match_id}/gifts',
  '/media-engine/creator-league/matches/{match_id}/purchase':
      '/api/v2/media-engine/creator-league/matches/{match_id}/purchase',
  '/media-engine/creator-league/matches/{match_id}/stadium':
      '/api/v2/media-engine/creator-league/matches/{match_id}/stadium',
  '/media-engine/creator-league/matches/{match_id}/stadium/placements':
      '/api/v2/media-engine/creator-league/matches/{match_id}/stadium/placements',
  '/media-engine/creator-league/matches/{match_id}/tickets':
      '/api/v2/media-engine/creator-league/matches/{match_id}/tickets',
  '/media-engine/creator-league/season-passes':
      '/api/v2/media-engine/creator-league/season-passes',
  '/media-engine/creator-league/season-passes/me':
      '/api/v2/media-engine/creator-league/season-passes/me',
  '/media-engine/downloads': '/api/v2/media-engine/downloads',
  '/media-engine/downloads/{token}': '/api/v2/media-engine/downloads/{token}',
  '/media-engine/matches/{match_key}/snapshot':
      '/api/v2/media-engine/matches/{match_key}/snapshot',
  '/media-engine/me/clip-earnings': '/api/v2/media-engine/me/clip-earnings',
  '/media-engine/me/purchases': '/api/v2/media-engine/me/purchases',
  '/media-engine/me/share-exports': '/api/v2/media-engine/me/share-exports',
  '/media-engine/purchases': '/api/v2/media-engine/purchases',
  '/media-engine/share-exports': '/api/v2/media-engine/share-exports',
  '/media-engine/share-exports/{export_id}/amplifications':
      '/api/v2/media-engine/share-exports/{export_id}/amplifications',
  '/media-engine/share-templates': '/api/v2/media-engine/share-templates',
  '/media-engine/views': '/api/v2/media-engine/views',
  '/metrics': '/api/v2/metrics',
  '/moderation/me/reports': '/api/v2/moderation/me/reports',
  '/moderation/reports': '/api/v2/moderation/reports',
  '/moments/live': '/api/v2/moments/live',
  '/national-pool': '/api/v2/national-pool',
  '/national-team-engine/competitions':
      '/api/v2/national-team-engine/competitions',
  '/national-team-engine/competitions/{competition_id}':
      '/api/v2/national-team-engine/competitions/{competition_id}',
  '/national-team-engine/competitions/{competition_id}/ads/active':
      '/api/v2/national-team-engine/competitions/{competition_id}/ads/active',
  '/national-team-engine/competitions/{competition_id}/auto-build-squad':
      '/api/v2/national-team-engine/competitions/{competition_id}/auto-build-squad',
  '/national-team-engine/competitions/{competition_id}/entries':
      '/api/v2/national-team-engine/competitions/{competition_id}/entries',
  '/national-team-engine/competitions/{competition_id}/gifts':
      '/api/v2/national-team-engine/competitions/{competition_id}/gifts',
  '/national-team-engine/competitions/{competition_id}/lifecycle':
      '/api/v2/national-team-engine/competitions/{competition_id}/lifecycle',
  '/national-team-engine/competitions/{competition_id}/presentation':
      '/api/v2/national-team-engine/competitions/{competition_id}/presentation',
  '/national-team-engine/competitions/{competition_id}/rental-entry':
      '/api/v2/national-team-engine/competitions/{competition_id}/rental-entry',
  '/national-team-engine/competitions/{competition_id}/rental-pool':
      '/api/v2/national-team-engine/competitions/{competition_id}/rental-pool',
  '/national-team-engine/competitions/{competition_id}/story-events':
      '/api/v2/national-team-engine/competitions/{competition_id}/story-events',
  '/national-team-engine/competitions/{competition_id}/theme':
      '/api/v2/national-team-engine/competitions/{competition_id}/theme',
  '/national-team-engine/entries/{entry_id}':
      '/api/v2/national-team-engine/entries/{entry_id}',
  '/national-team-engine/entries/{entry_id}/free-players/claim':
      '/api/v2/national-team-engine/entries/{entry_id}/free-players/claim',
  '/national-team-engine/entries/{entry_id}/rental-status':
      '/api/v2/national-team-engine/entries/{entry_id}/rental-status',
  '/national-team-engine/entries/{entry_id}/rentals':
      '/api/v2/national-team-engine/entries/{entry_id}/rentals',
  '/national-team-engine/me/history': '/api/v2/national-team-engine/me/history',
  '/national-team-engine/me/previous-roster':
      '/api/v2/national-team-engine/me/previous-roster',
  '/national-team-engine/rankings': '/api/v2/national-team-engine/rankings',
  '/news/breaking': '/api/v2/news/breaking',
  '/news/daily': '/api/v2/news/daily',
  '/news/feed': '/api/v2/news/feed',
  '/news/personalized': '/api/v2/news/personalized',
  '/news/{article_id}': '/api/v2/news/{article_id}',
  '/notifications': '/api/v2/notifications',
  '/notifications/announcements': '/api/v2/notifications/announcements',
  '/notifications/me': '/api/v2/notifications/me',
  '/notifications/preferences': '/api/v2/notifications/preferences',
  '/notifications/read-all': '/api/v2/notifications/read-all',
  '/notifications/subscriptions': '/api/v2/notifications/subscriptions',
  '/notifications/subscriptions/{subscription_id}':
      '/api/v2/notifications/subscriptions/{subscription_id}',
  '/notifications/{notification_id}/read':
      '/api/v2/notifications/{notification_id}/read',
  '/objectives/me': '/api/v2/objectives/me',
  '/observability/config': '/api/v2/observability/config',
  '/orchestrator/config': '/api/v2/orchestrator/config',
  '/orchestrator/metrics': '/api/v2/orchestrator/metrics',
  '/orders': '/api/v2/orders',
  '/orders/book/{player_id}': '/api/v2/orders/book/{player_id}',
  '/orders/{order_id}': '/api/v2/orders/{order_id}',
  '/orders/{order_id}/admin-buyback': '/api/v2/orders/{order_id}/admin-buyback',
  '/orders/{order_id}/admin-buyback-preview':
      '/api/v2/orders/{order_id}/admin-buyback-preview',
  '/orders/{order_id}/cancel': '/api/v2/orders/{order_id}/cancel',
  '/ownership-groups': '/api/v2/ownership-groups',
  '/ownership-groups/transfers/validate':
      '/api/v2/ownership-groups/transfers/validate',
  '/ownership-groups/{group_id}': '/api/v2/ownership-groups/{group_id}',
  '/ownership-groups/{group_id}/budget/allocate':
      '/api/v2/ownership-groups/{group_id}/budget/allocate',
  '/ownership-groups/{group_id}/budget/transfer':
      '/api/v2/ownership-groups/{group_id}/budget/transfer',
  '/ownership-groups/{group_id}/clubs':
      '/api/v2/ownership-groups/{group_id}/clubs',
  '/platform/mode': '/api/v2/platform/mode',
  '/platform/switch': '/api/v2/platform/switch',
  '/player-cards/admin/preseeded-regens':
      '/api/v2/player-cards/admin/preseeded-regens',
  '/player-cards/admin/preseeded-regens/mint':
      '/api/v2/player-cards/admin/preseeded-regens/mint',
  '/player-cards/inventory': '/api/v2/player-cards/inventory',
  '/player-cards/listings': '/api/v2/player-cards/listings',
  '/player-cards/listings/mine': '/api/v2/player-cards/listings/mine',
  '/player-cards/listings/{listing_id}/buy':
      '/api/v2/player-cards/listings/{listing_id}/buy',
  '/player-cards/listings/{listing_id}/cancel':
      '/api/v2/player-cards/listings/{listing_id}/cancel',
  '/player-cards/loans': '/api/v2/player-cards/loans',
  '/player-cards/loans/contracts/{loan_contract_id}/return':
      '/api/v2/player-cards/loans/contracts/{loan_contract_id}/return',
  '/player-cards/loans/{loan_listing_id}/borrow':
      '/api/v2/player-cards/loans/{loan_listing_id}/borrow',
  '/player-cards/marketplace/listings':
      '/api/v2/player-cards/marketplace/listings',
  '/player-cards/marketplace/loans': '/api/v2/player-cards/marketplace/loans',
  '/player-cards/marketplace/loans/contracts':
      '/api/v2/player-cards/marketplace/loans/contracts',
  '/player-cards/marketplace/loans/contracts/{contract_id}/return':
      '/api/v2/player-cards/marketplace/loans/contracts/{contract_id}/return',
  '/player-cards/marketplace/loans/contracts/{contract_id}/settle':
      '/api/v2/player-cards/marketplace/loans/contracts/{contract_id}/settle',
  '/player-cards/marketplace/loans/negotiations/{negotiation_id}/accept':
      '/api/v2/player-cards/marketplace/loans/negotiations/{negotiation_id}/accept',
  '/player-cards/marketplace/loans/negotiations/{negotiation_id}/counter':
      '/api/v2/player-cards/marketplace/loans/negotiations/{negotiation_id}/counter',
  '/player-cards/marketplace/loans/{listing_id}/cancel':
      '/api/v2/player-cards/marketplace/loans/{listing_id}/cancel',
  '/player-cards/marketplace/loans/{listing_id}/negotiations':
      '/api/v2/player-cards/marketplace/loans/{listing_id}/negotiations',
  '/player-cards/marketplace/sales': '/api/v2/player-cards/marketplace/sales',
  '/player-cards/marketplace/sales/{listing_id}/buy':
      '/api/v2/player-cards/marketplace/sales/{listing_id}/buy',
  '/player-cards/marketplace/sales/{listing_id}/cancel':
      '/api/v2/player-cards/marketplace/sales/{listing_id}/cancel',
  '/player-cards/marketplace/swaps': '/api/v2/player-cards/marketplace/swaps',
  '/player-cards/marketplace/swaps/{listing_id}/cancel':
      '/api/v2/player-cards/marketplace/swaps/{listing_id}/cancel',
  '/player-cards/marketplace/swaps/{listing_id}/execute':
      '/api/v2/player-cards/marketplace/swaps/{listing_id}/execute',
  '/player-cards/players': '/api/v2/player-cards/players',
  '/player-cards/players/{player_id}':
      '/api/v2/player-cards/players/{player_id}',
  '/player-cards/starter-rental': '/api/v2/player-cards/starter-rental',
  '/player-cards/watchlist': '/api/v2/player-cards/watchlist',
  '/player-cards/watchlist/{watchlist_id}':
      '/api/v2/player-cards/watchlist/{watchlist_id}',
  '/player-history': '/api/v2/player-history',
  '/player-history/{player_id}': '/api/v2/player-history/{player_id}',
  '/player-import/youth-prospects/me':
      '/api/v2/player-import/youth-prospects/me',
  '/player-import/youth-prospects/{club_id}':
      '/api/v2/player-import/youth-prospects/{club_id}',
  '/players': '/api/v2/players',
  '/players/events': '/api/v2/players/events',
  '/players/markets': '/api/v2/players/markets',
  '/players/match': '/api/v2/players/match',
  '/players/me/match-profile': '/api/v2/players/me/match-profile',
  '/players/me/shares/holdings': '/api/v2/players/me/shares/holdings',
  '/players/real-universe': '/api/v2/players/real-universe',
  '/players/real-universe/search': '/api/v2/players/real-universe/search',
  '/players/real-universe/{player_id}':
      '/api/v2/players/real-universe/{player_id}',
  '/players/summaries/recent': '/api/v2/players/summaries/recent',
  '/players/{player_id}': '/api/v2/players/{player_id}',
  '/players/{player_id}/avatar': '/api/v2/players/{player_id}/avatar',
  '/players/{player_id}/career-events':
      '/api/v2/players/{player_id}/career-events',
  '/players/{player_id}/dna': '/api/v2/players/{player_id}/dna',
  '/players/{player_id}/interviews': '/api/v2/players/{player_id}/interviews',
  '/players/{player_id}/personality': '/api/v2/players/{player_id}/personality',
  '/players/{player_id}/rivalries': '/api/v2/players/{player_id}/rivalries',
  '/players/{player_id}/shares/buy': '/api/v2/players/{player_id}/shares/buy',
  '/players/{player_id}/shares/dividends':
      '/api/v2/players/{player_id}/shares/dividends',
  '/players/{player_id}/shares/events':
      '/api/v2/players/{player_id}/shares/events',
  '/players/{player_id}/shares/issue':
      '/api/v2/players/{player_id}/shares/issue',
  '/players/{player_id}/shares/market':
      '/api/v2/players/{player_id}/shares/market',
  '/players/{player_id}/shares/performance':
      '/api/v2/players/{player_id}/shares/performance',
  '/players/{player_id}/shares/sell': '/api/v2/players/{player_id}/shares/sell',
  '/players/{player_id}/story': '/api/v2/players/{player_id}/story',
  '/players/{player_id}/summary': '/api/v2/players/{player_id}/summary',
  '/policies/acceptances': '/api/v2/policies/acceptances',
  '/policies/country/{country_code}': '/api/v2/policies/country/{country_code}',
  '/policies/documents': '/api/v2/policies/documents',
  '/policies/documents/{document_key}':
      '/api/v2/policies/documents/{document_key}',
  '/policies/me/acceptances': '/api/v2/policies/me/acceptances',
  '/policies/me/compliance': '/api/v2/policies/me/compliance',
  '/policies/me/region': '/api/v2/policies/me/region',
  '/policies/me/requirements': '/api/v2/policies/me/requirements',
  '/portfolio': '/api/v2/portfolio',
  '/portfolio/snapshot': '/api/v2/portfolio/snapshot',
  '/portfolio/summary': '/api/v2/portfolio/summary',
  '/portfolios/me': '/api/v2/portfolios/me',
  '/predictions': '/api/v2/predictions',
  '/predictions/leaderboard': '/api/v2/predictions/leaderboard',
  '/rankings/clubs': '/api/v2/rankings/clubs',
  '/rankings/global': '/api/v2/rankings/global',
  '/rankings/players': '/api/v2/rankings/players',
  '/real-world/events': '/api/v2/real-world/events',
  '/real-world/hybrid-players': '/api/v2/real-world/hybrid-players',
  '/real-world/normalize': '/api/v2/real-world/normalize',
  '/real-world/players': '/api/v2/real-world/players',
  '/real-world/players/{real_player_id}':
      '/api/v2/real-world/players/{real_player_id}',
  '/real-world/providers': '/api/v2/real-world/providers',
  '/real-world/settings/me': '/api/v2/real-world/settings/me',
  '/realtime/matches/{match_id}/gateway':
      '/api/v2/realtime/matches/{match_id}/gateway',
  '/realtime/matches/{match_id}/stream':
      '/api/v2/realtime/matches/{match_id}/stream',
  '/realtime/status': '/api/v2/realtime/status',
  '/realtime/stream': '/api/v2/realtime/stream',
  '/realtime/wallet/gateway': '/api/v2/realtime/wallet/gateway',
  '/realtime/wallet/stream': '/api/v2/realtime/wallet/stream',
  '/regen-hype': '/api/v2/regen-hype',
  '/regen-universe/achievements': '/api/v2/regen-universe/achievements',
  '/regen-universe/awards': '/api/v2/regen-universe/awards',
  '/regen-universe/bloodlines': '/api/v2/regen-universe/bloodlines',
  '/regen-universe/hall-of-fame': '/api/v2/regen-universe/hall-of-fame',
  '/regen-universe/national-regens': '/api/v2/regen-universe/national-regens',
  '/regen-universe/player/{player_id}':
      '/api/v2/regen-universe/player/{player_id}',
  '/regen-universe/players/{player_id}':
      '/api/v2/regen-universe/players/{player_id}',
  '/regen-universe/players/{player_id}/timeline':
      '/api/v2/regen-universe/players/{player_id}/timeline',
  '/regen-universe/rankings': '/api/v2/regen-universe/rankings',
  '/regen-universe/rising-stars': '/api/v2/regen-universe/rising-stars',
  '/regen-universe/scouting-feed': '/api/v2/regen-universe/scouting-feed',
  '/regen-universe/seasons': '/api/v2/regen-universe/seasons',
  '/regen-universe/tracking': '/api/v2/regen-universe/tracking',
  '/regen-universe/youth-tournaments':
      '/api/v2/regen-universe/youth-tournaments',
  '/regen-universe/youth-tournaments/{tournament_id}':
      '/api/v2/regen-universe/youth-tournaments/{tournament_id}',
  '/regens/awards': '/api/v2/regens/awards',
  '/regens/awards/{award_id}/vote': '/api/v2/regens/awards/{award_id}/vote',
  '/regens/creation-orders': '/api/v2/regens/creation-orders',
  '/regens/creation-orders/{order_id}':
      '/api/v2/regens/creation-orders/{order_id}',
  '/regens/creation-orders/{order_id}/generate-after-payment':
      '/api/v2/regens/creation-orders/{order_id}/generate-after-payment',
  '/regens/creation-orders/{order_id}/pay-with-wallet':
      '/api/v2/regens/creation-orders/{order_id}/pay-with-wallet',
  '/regens/feed': '/api/v2/regens/feed',
  '/regens/jobs/{job_name}': '/api/v2/regens/jobs/{job_name}',
  '/regens/request-son': '/api/v2/regens/request-son',
  '/regens/request-son/options': '/api/v2/regens/request-son/options',
  '/regens/rising': '/api/v2/regens/rising',
  '/regens/top': '/api/v2/regens/top',
  '/regens/{regen_id}/lineage': '/api/v2/regens/{regen_id}/lineage',
  '/rent': '/api/v2/rent',
  '/replays/countdown/{fixture_id}': '/api/v2/replays/countdown/{fixture_id}',
  '/replays/me': '/api/v2/replays/me',
  '/replays/public/featured': '/api/v2/replays/public/featured',
  '/replays/{replay_id}': '/api/v2/replays/{replay_id}',
  '/reward-engine/me/settlements': '/api/v2/reward-engine/me/settlements',
  '/reward-engine/me/summary': '/api/v2/reward-engine/me/summary',
  '/risk-ops/me/aml-cases': '/api/v2/risk-ops/me/aml-cases',
  '/risk-ops/me/fraud-cases': '/api/v2/risk-ops/me/fraud-cases',
  '/risk-ops/me/overview': '/api/v2/risk-ops/me/overview',
  '/risk-ops/me/restrictions': '/api/v2/risk-ops/me/restrictions',
  '/risk-ops/me/signals': '/api/v2/risk-ops/me/signals',
  '/scout/report/{player_id}': '/api/v2/scout/report/{player_id}',
  '/scouts': '/api/v2/scouts',
  '/scouts/{scout_id}/discover': '/api/v2/scouts/{scout_id}/discover',
  '/season-pass': '/api/v2/season-pass',
  '/season-pass/claim': '/api/v2/season-pass/claim',
  '/season-pass/me': '/api/v2/season-pass/me',
  '/season-pass/rewards/{reward_id}/claim':
      '/api/v2/season-pass/rewards/{reward_id}/claim',
  '/season/current': '/api/v2/season/current',
  '/season/history': '/api/v2/season/history',
  '/shows/debate': '/api/v2/shows/debate',
  '/shows/post-match/{match_id}': '/api/v2/shows/post-match/{match_id}',
  '/shows/pre-match/{match_id}': '/api/v2/shows/pre-match/{match_id}',
  '/simulation-matchmaking/hosted-competitions/preview':
      '/api/v2/simulation-matchmaking/hosted-competitions/preview',
  '/simulation-matchmaking/profiles/{user_id}':
      '/api/v2/simulation-matchmaking/profiles/{user_id}',
  '/simulation-matchmaking/quick-game':
      '/api/v2/simulation-matchmaking/quick-game',
  '/simulation-matchmaking/quick-tournament':
      '/api/v2/simulation-matchmaking/quick-tournament',
  '/social/clubs/{club_id}/community':
      '/api/v2/social/clubs/{club_id}/community',
  '/social/clubs/{club_id}/community/messages':
      '/api/v2/social/clubs/{club_id}/community/messages',
  '/social/feed': '/api/v2/social/feed',
  '/social/follows': '/api/v2/social/follows',
  '/social/profile/me': '/api/v2/social/profile/me',
  '/social/rivalries/{club_a_id}/{club_b_id}':
      '/api/v2/social/rivalries/{club_a_id}/{club_b_id}',
  '/social/rivalries/{club_a_id}/{club_b_id}/banter':
      '/api/v2/social/rivalries/{club_a_id}/{club_b_id}/banter',
  '/sponsors': '/api/v2/sponsors',
  '/sponsorship/clubs/{club_id}/contracts':
      '/api/v2/sponsorship/clubs/{club_id}/contracts',
  '/sponsorship/clubs/{club_id}/dashboard':
      '/api/v2/sponsorship/clubs/{club_id}/dashboard',
  '/sponsorship/clubs/{club_id}/offers':
      '/api/v2/sponsorship/clubs/{club_id}/offers',
  '/sponsorship/clubs/{club_id}/sponsors':
      '/api/v2/sponsorship/clubs/{club_id}/sponsors',
  '/sponsorship/contracts/request': '/api/v2/sponsorship/contracts/request',
  '/sponsorship/me/leads': '/api/v2/sponsorship/me/leads',
  '/sponsorship/packages': '/api/v2/sponsorship/packages',
  '/sponsorship/placements': '/api/v2/sponsorship/placements',
  '/story-feed': '/api/v2/story-feed',
  '/story-feed/digest': '/api/v2/story-feed/digest',
  '/streamer-tournaments': '/api/v2/streamer-tournaments',
  '/streamer-tournaments/mine': '/api/v2/streamer-tournaments/mine',
  '/streamer-tournaments/{tournament_id}':
      '/api/v2/streamer-tournaments/{tournament_id}',
  '/streamer-tournaments/{tournament_id}/invites':
      '/api/v2/streamer-tournaments/{tournament_id}/invites',
  '/streamer-tournaments/{tournament_id}/join':
      '/api/v2/streamer-tournaments/{tournament_id}/join',
  '/streamer-tournaments/{tournament_id}/publish':
      '/api/v2/streamer-tournaments/{tournament_id}/publish',
  '/streamer-tournaments/{tournament_id}/rewards':
      '/api/v2/streamer-tournaments/{tournament_id}/rewards',
  '/surveillance/circular-trade-alerts':
      '/api/v2/surveillance/circular-trade-alerts',
  '/surveillance/holder-concentration-alerts':
      '/api/v2/surveillance/holder-concentration-alerts',
  '/surveillance/suspicious-clusters':
      '/api/v2/surveillance/suspicious-clusters',
  '/surveillance/suspicious-players': '/api/v2/surveillance/suspicious-players',
  '/surveillance/thin-market-alerts': '/api/v2/surveillance/thin-market-alerts',
  '/sync/update': '/api/v2/sync/update',
  '/tickets/attendance/{match_id}/react':
      '/api/v2/tickets/attendance/{match_id}/react',
  '/tickets/buy': '/api/v2/tickets/buy',
  '/tickets/event/{match_id}': '/api/v2/tickets/event/{match_id}',
  '/tickets/resell': '/api/v2/tickets/resell',
  '/tickets/waitlist': '/api/v2/tickets/waitlist',
  '/trust/me': '/api/v2/trust/me',
  '/trust/{user_id}': '/api/v2/trust/{user_id}',
  '/ultimate-league/competitors/{competitor_id}':
      '/api/v2/ultimate-league/competitors/{competitor_id}',
  '/ultimate-league/matches/result': '/api/v2/ultimate-league/matches/result',
  '/ultimate-league/matchmaking/batch':
      '/api/v2/ultimate-league/matchmaking/batch',
  '/ultimate-league/standings/{tier}':
      '/api/v2/ultimate-league/standings/{tier}',
  '/ultimate-league/tactical-presets':
      '/api/v2/ultimate-league/tactical-presets',
  '/ultimate-league/tactical-presets/{preset_id}/purchase':
      '/api/v2/ultimate-league/tactical-presets/{preset_id}/purchase',
  '/ultimate-league/tiers': '/api/v2/ultimate-league/tiers',
  '/ultimate-league/tournaments': '/api/v2/ultimate-league/tournaments',
  '/ultimate-league/tournaments/{tournament_id}':
      '/api/v2/ultimate-league/tournaments/{tournament_id}',
  '/ultimate-league/tournaments/{tournament_id}/payouts/preview':
      '/api/v2/ultimate-league/tournaments/{tournament_id}/payouts/preview',
  '/users/me': '/api/v2/users/me',
  '/users/me/profile': '/api/v2/users/me/profile',
  '/users/suggestions': '/api/v2/users/suggestions',
  '/users/{user_id}/followers': '/api/v2/users/{user_id}/followers',
  '/users/{user_id}/following': '/api/v2/users/{user_id}/following',
  '/value-engine/snapshots/rebuild': '/api/v2/value-engine/snapshots/rebuild',
  '/value-engine/snapshots/{player_id}/daily-closes':
      '/api/v2/value-engine/snapshots/{player_id}/daily-closes',
  '/value-engine/snapshots/{player_id}/history':
      '/api/v2/value-engine/snapshots/{player_id}/history',
  '/value-engine/snapshots/{player_id}/latest':
      '/api/v2/value-engine/snapshots/{player_id}/latest',
  '/value-engine/snapshots/{player_id}/trend-summary':
      '/api/v2/value-engine/snapshots/{player_id}/trend-summary',
  '/viral/cascades': '/api/v2/viral/cascades',
  '/viral/clips/trending': '/api/v2/viral/clips/trending',
  '/wallet': '/api/v2/wallet',
  '/wallet/top-up/initiate': '/api/v2/wallet/top-up/initiate',
  '/wallet/top-up/verify': '/api/v2/wallet/top-up/verify',
  '/wallet/transactions': '/api/v2/wallet/transactions',
  '/wallets': '/api/v2/wallets',
  '/wallets/accounts': '/api/v2/wallets/accounts',
  '/wallets/adaptive-overview': '/api/v2/wallets/adaptive-overview',
  '/wallets/conversions': '/api/v2/wallets/conversions',
  '/wallets/conversions/quote': '/api/v2/wallets/conversions/quote',
  '/wallets/deposits': '/api/v2/wallets/deposits',
  '/wallets/deposits/{deposit_id}/submit':
      '/api/v2/wallets/deposits/{deposit_id}/submit',
  '/wallets/ledger': '/api/v2/wallets/ledger',
  '/wallets/market-topups': '/api/v2/wallets/market-topups',
  '/wallets/overview': '/api/v2/wallets/overview',
  '/wallets/payment-events': '/api/v2/wallets/payment-events',
  '/wallets/providers/{provider_key}/webhook':
      '/api/v2/wallets/providers/{provider_key}/webhook',
  '/wallets/purchase-orders': '/api/v2/wallets/purchase-orders',
  '/wallets/purchase-orders/quote': '/api/v2/wallets/purchase-orders/quote',
  '/wallets/purchase-orders/{order_id}':
      '/api/v2/wallets/purchase-orders/{order_id}',
  '/wallets/summary': '/api/v2/wallets/summary',
  '/wallets/top-up/initiate': '/api/v2/wallets/top-up/initiate',
  '/wallets/top-up/verify': '/api/v2/wallets/top-up/verify',
  '/wallets/transactions': '/api/v2/wallets/transactions',
  '/wallets/withdrawals': '/api/v2/wallets/withdrawals',
  '/wallets/withdrawals/eligibility': '/api/v2/wallets/withdrawals/eligibility',
  '/wallets/withdrawals/quote': '/api/v2/wallets/withdrawals/quote',
  '/wallets/withdrawals/{withdrawal_id}/receipt':
      '/api/v2/wallets/withdrawals/{withdrawal_id}/receipt',
  '/world-super-cup/countdown': '/api/v2/world-super-cup/countdown',
  '/world-super-cup/groups/table': '/api/v2/world-super-cup/groups/table',
  '/world-super-cup/knockout/bracket':
      '/api/v2/world-super-cup/knockout/bracket',
  '/world-super-cup/playoff/draw': '/api/v2/world-super-cup/playoff/draw',
  '/world-super-cup/qualification/explanation':
      '/api/v2/world-super-cup/qualification/explanation',
  '/ws/match/{match_id}': '/api/v2/ws/match/{match_id}',
  '/ws/spectate/{match_id}': '/api/v2/ws/spectate/{match_id}',
  '/ws/tournament/{tournament_id}': '/api/v2/ws/tournament/{tournament_id}',
};
