# wellington-city-hazard-map

Wellington City hazard map with WCC emergency GIS overlays on a static GitHub Pages site.

The map is bounded to the city suburb extent. Pins and searches outside Wellington City are rejected. Hazard overlays stay faintly visible; a pin report ranks the highest-consequence overlays first. Pin URLs are shareable (`?lat=&lng=` or `?q=`).

**Site:** <https://jajera.github.io/wellington-city-hazard-map/>

## Local

```bash
python3 -m http.server 8765
```

Open <http://localhost:8765/>.

Example deep link: <http://localhost:8765/?q=12%20Cuba%20Street,%20Te%20Aro>

## Data

| File | Role |
| --- | --- |
| `wellington-city.geojson` | 57 WCC suburb polygons — city outline and inside-city test |
| `hazards.geojson` | Baked WCC (and city-clipped) hazard overlays |
| `scripts/bake_hazards.py` | Refresh `hazards.geojson` from upstream sources |

## Hazard bake (scheduled)

Weekly (Monday 03:17 UTC) and on `workflow_dispatch`: `.github/workflows/bake-hazards.yml` rebakes `hazards.geojson`, opens PR `chore/bake-hazards`, enables squash auto-merge. Merge to `main` runs Pages deploy.

### Repo setup

| Item | Status |
| --- | --- |
| Allow auto-merge | On |
| Ruleset `main` — require PR, **0** approving reviews | On ([ruleset](https://github.com/jajera/wellington-city-hazard-map/rules/24444604)) |
| Required status checks on `main` | On: `markdown-lint / markdown-lint`, `commitmsg-conform / conform` |
| Secrets `GH_APP_ID` + `GH_APP_PRIVATE_KEY` | On |

### GitHub App

Bake uses a GitHub App so each run gets a short-lived installation token. That token can open the PR in a way that still triggers required checks (the default `GITHUB_TOKEN` cannot). The App private key does not expire.

**Configured for this repo:** App installed on `wellington-city-hazard-map`; secrets `GH_APP_ID` and `GH_APP_PRIVATE_KEY` set.

To recreate elsewhere: [New GitHub App](https://github.com/settings/apps/new) → Contents + Pull requests (Read and write), webhook off → generate private key → install on the repo →

```bash
gh secret set GH_APP_ID --repo OWNER/REPO
gh secret set GH_APP_PRIVATE_KEY --repo OWNER/REPO < /path/to/*.private-key.pem
```

## Checks

Flood, coastal, tsunami, fault, liquefaction, slope (city clip), wind, and earthquake-prone buildings nearby. Colours follow published symbology where known. Layer toggles control both the map overlays and the pin report.

Sources: [wcc-emergency-gis-data](https://github.com/claudecommunity-nz/wcc-emergency-gis-data).

## Disclaimer

Not a LIM. Not live emergency information. In an emergency call 111.
