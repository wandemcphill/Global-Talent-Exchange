# GTEX Local Development Runbook

## Canonical boot order
1. Start backend.
2. Verify health/readiness/diagnostics.
3. Start Flutter frontend.
4. Login with a normal user or the seeded super admin account.

## Seeded super admin
- Email: `vidvimedialtd@gmail.com`
- Password: `NewPass1234!`

## Release-focused smoke flow
1. Login as standard user.
2. Open manager market.
3. Recruit a manager.
4. Assign main team and academy slots.
5. Create a trade listing.
6. Cancel the listing.
7. Login as super admin.
8. Open manager admin.
9. Create a scoped admin.
10. Toggle a competition.
11. Increase and decrease manager supply.
12. Review audit log.
