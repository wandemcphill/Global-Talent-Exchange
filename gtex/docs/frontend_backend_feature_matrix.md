# Frontend-Backend Feature Matrix

Owner: Product engineering lead coordinating frontend + backend

## First wave

Chosen modules for the first integration wave:

1. Federations / world functionality
2. National team engine
3. Transfer center

Why these three:

- They deliver the biggest visible product-completeness gain with existing backend depth.
- Two of them had rich backend surfaces but weak or missing routed frontend entry points.
- Transfer center already had live summary data, so a dedicated detail route and action flow closes a high-value gap quickly.

## Matrix

| Module family | Backend route exists | Frontend screen exists | Nav entry exists | Live data wired | Mutation wired | Telemetry present |
| --- | --- | --- | --- | --- | --- | --- |
| Federations / world functionality | Y | Y | Y | Y | Y | Y |
| National team engine | Y | Y | Y | Y | Y | Y |
| Transfer center | Y | Y | Y | Y | Y | Y |
| Fast cups | Y | Y | Y | Partial | N | N |
| Regen universe | Y | Y | Y | Y | N | N |
| Infinite league | Y | N | N | N | N | N |
| Broadcast rights and other backend-only specialist modules | Y | N | N | N | N | N |

## Notes

- `Federations / world functionality` is now exposed through a dedicated federations hub and federation detail route, with live ranking, governance, narrative, and membership-request flows.
- `National team engine` is now exposed through a dedicated hub and competition detail route, with live lifecycle and presentation data plus a live draft-squad action.
- `Transfer center` is now exposed through a dedicated route and listing detail route, with live bidders, negotiation context, bidding, watchlist, and contract-offer flows.
- `Fast cups` are now discoverable in the competitions hub, but the shipped lane is still read-heavy rather than a fully dedicated fast-cup action surface.
- `Regen universe` is already shipped through world and national-team surfaces with live routed data.
- `Infinite league` remains backend-only from the shipped shell, even though it powers supporting generated-match infrastructure behind other surfaces.
- `Broadcast rights and other backend-only specialist modules` remain hidden from the shipped shell until they gain explicit routed owners.
