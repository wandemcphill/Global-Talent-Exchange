# Database Blueprint

## Core tables
1. users
2. user_profiles
3. wallets
4. wallet_ledger
5. players
6. player_status
7. player_contracts
8. clubs
9. competitions
10. competition_player_eligibility
11. player_assets
12. user_player_ownership
13. user_teams
14. team_registrations
15. player_match_events
16. value_snapshots
17. market_listings
18. trade_offers
19. swap_listings
20. trades
21. transfer_windows
22. leaderboards
23. leaderboard_entries
24. notifications
25. notification_preferences
26. auction_events
27. auction_bids
28. auction_winners
29. followers
30. discovery_feed_snapshots

## Important rules
- real wallet + demo wallet per user
- one copy per player per user
- exactly 3 teams per user
- player assets must store RMV, BVF, PSP, supply, times traded
