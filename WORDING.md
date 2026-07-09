# K5Bearing — all alert wording

Every phrasing the bot can post. {curly braces} are filled in at post time. One variant is chosen per alert.

**Scope:** Rotterdam, Netherlands. The account posts a twice-daily Rotterdam forecast, **Rotterdam severe-weather alerts** (derived from Open-Meteo — see the section below), and global space weather. The **US (NWS)**, **Europe (MeteoAlarm)**, **Gulf**, **marine**, **earthquake**, **GDACS**, **red tide**, **outdoor**, and **NGA** sections below are the **preserved wording library**: those sources are off, but their phrasing is kept — the Rotterdam alerts reuse the US per-hazard lines, and coverage can be restored later. Nothing here has been deleted from the wording.

**Prefix:** 24-hour local time, the timezone, then a `REGION, place` geo tag — e.g. `11:20 CDT USA, Texas:`, `16:33 CEST EU, France:`, `20:14 GST GCC, United Arab Emirates:`. The place is the US **state** (NWS), the **country** (Europe / Gulf), the **city** (outdoor UV/dust/lightning), or `USA, California` (red tide). Coordinate-less signals — space weather, open-sea marine, NGA navigation warnings — keep the plain `16:33 UTC:` form, as does the scheduled Rotterdam update (deliberately, so it stands out). **No hashtags.**

**Timezones** print their official abbreviation: US/EU native codes (EDT, CEST…), plus GST (UAE/Oman), AST (Saudi/Qatar/Bahrain/Kuwait/Iraq/Yemen), IRST (Iran), AFT (Afghanistan), TRT (Türkiye), GET/AMT/AZT (Caucasus). Open ocean and unmapped zones fall back to `UTC±N`.

**Units:** Rotterdam alerts in **°C** (wind km/h, visibility m). In the preserved library below, US temperatures are documented in **°F**, Europe and the Gulf in **°C**.

**Voice** — most alerts post exactly as written below. Low-stakes ones are softened with a **"Heads up,"** lead: anything ending in "Advisory", the small-craft roundup, extreme-UV, the Gulf dense-fog alert, and the Gulf cold-snap alert. We inform; we don't issue commands.

**Ranking** — purely by severity, highest first. No topic or source gets a boost. (The scheduled Rotterdam update sorts to the top only because its severity is hard-set to 1000.) Per-category **daily caps** keep one region from flooding the feed, but they're **soft**: if nothing else is eligible, a capped category may overflow (still within the daily budget) so the feed never goes silent under-budget. A per-area **cooldown** holds further posts for the same state/country for ~2 h during an outbreak, unless a strictly more severe warning breaks through.

**Freshness** — only alerts current *today* are posted. **No repeats** — the feed won't post the same topic (flood, wind, heat…) twice in a row, even for different places, unless nothing else is available.

---

## Space weather — geomagnetic storm + compass
_Kp 5–6:_
1. A {level} geomagnetic storm is underway at Kp {kp}, and magnetic north is drifting. A compass can read a few degrees off true. Check any bearing against GPS or a known landmark before you rely on it.
2. A {level} geomagnetic storm has set in at Kp {kp}, pulling magnetic north off true. A compass may be a few degrees out. Confirm any bearing with GPS or a fixed landmark before trusting it.

_Kp 7+:_
1. A {level} geomagnetic storm has ramped up to Kp {kp}, throwing magnetic north off by several degrees. Trust GPS or a celestial bearing and treat the compass as a rough guide until it settles.

## Space weather — solar flare
_Lead:_
1. The Sun fired off {article} {class} flare, peaking at {time} UTC.

_Impact:_
- M-class: Flares this strong can cause brief HF (shortwave) radio blackouts on the daylit side of Earth.
- X-class: Flares this strong can trigger widespread shortwave radio blackouts on the daylit side of Earth and impair GPS and HF communications.

## Space weather — solar radiation storm (NOAA S-scale)
1. A solar radiation storm has reached S{level} ({label}). Polar flights can lose HF radio and satellite navigation may degrade.
2. Solar radiation has surged to an S{level} ({label}) storm. Expect HF blackouts over the poles and possible satellite navigation glitches.

## Space weather — radio blackout (NOAA R-scale)
1. A radio blackout has surged to R{level} ({label}), the Sun jamming high-frequency radio across the daylit side of Earth. Mariners and aviators leaning on HF should expect dropouts and dead air until it fades.
2. Solar flaring has driven an R{level} ({label}) radio blackout, smothering high-frequency radio on the sunlit face of the planet. Expect HF comms to wash out and navigation signals to wander until it clears.

## Space weather — solar wind (high-speed stream)
1. The solar wind is screaming past Earth at {speed} km/s, a high-speed stream raking the magnetic field. Expect the compass needle to grow restless and the aurora to push toward lower latitudes.

## Space weather — solar alerts
`Space weather alert: {NOAA headline}`.

---

## Rotterdam severe-weather alerts (derived, Open-Meteo) — ACTIVE

The one alert source now the account is Rotterdam-only. It reads current conditions + today's forecast for Rotterdam and fires when a threshold is crossed, at most once per hazard per day. The opener is the shared `{article} {event} is active/has been issued.` (no `for {area}` — Rotterdam is fixed and rides in the prefix), followed by the reused US per-hazard action line. Prefix: `HH:MM CEST Rotterdam:`.

| Hazard (trigger) | Reused event wording |
| --- | --- |
| Thunderstorm (WMO code 95/96/99) | Severe Thunderstorm Warning |
| Snow (WMO 71/73/75/77/85/86) | Winter Storm Warning |
| Freezing rain/drizzle (WMO 56/57/66/67) | Ice Storm Warning |
| Dense fog (visibility < `fog_visibility_m`, or WMO 45/48) | Dense Fog Warning |
| High wind (gusts ≥ `wind_gust_kmh`) | High Wind Warning |
| Heavy rain (≥ `rain_mm`/h) | Flood Warning |
| Torrential rain (≥ `flash_flood_mm`/h) | Flash Flood Warning |
| Extreme heat (today's high ≥ `heat_c`) | Extreme Heat Warning + `Highs near {t}°C.` |
| Freeze (today's low ≤ `freeze_c`) | Freeze Warning + `Lows near {t}°C.` |
| Extreme cold (today's low ≤ `severe_cold_c`) | Extreme Cold Warning + `Lows near {t}°C.` |

The event wording itself is the per-hazard action line listed under **US weather (NWS)** below (plus the **Dense Fog Warning** line, kept from the European/Gulf fog phrasing). Thresholds live in `config.yaml` under `rotterdam:`.

---

## US weather (NWS) — openers
`{where}` is " for {named areas}". When every area is in one state, that state is in the `USA, <state>` prefix and dropped from the list ("Travis and Williamson"); multi-state alerts keep ", ST".
1. {article} {event} is active{where}.
2. {article} {event} has been issued{where}.

**Heat / cold degree** (US, °F): heat alerts append ` Highs near {N}°F.` and cold/freeze/frost alerts append ` Lows near {N}°F.`, fetched from the forecast at the alert's location.

## US weather (NWS) — per-hazard action lines
**Tornado Warning**
1. Get to a basement or an interior room on the lowest floor and keep clear of windows. Stay there until the warning is lifted.

**Hurricane Warning**
1. Destructive winds and storm surge are expected. Follow any evacuation orders.
2. Life-threatening winds and surge are on the way. Follow any evacuation orders.

**Hurricane Watch**
1. Hurricane conditions are possible within about two days. Keep a close watch on the latest alerts.
2. A hurricane may strike within roughly 48 hours. Keep a close watch on the latest alerts.

**Tropical Storm Warning**
1. Tropical storm-force winds are expected. Head inside before the weather turns rough.
2. Tropical storm-force winds are on the way. Head inside before the weather turns rough.

**Blizzard Warning**
1. Blowing snow will bring ground blizzard whiteouts. Conditions will turn severe in near zero visibility.

**Extreme Wind Warning**
1. Violent winds are imminent. Stay clear of windows until they pass.

**Severe Thunderstorm Warning**
1. A supercell can bring damaging winds and large hail. Head indoors and keep away from windows until the storm moves through.

**Flash Flood Warning**
1. The flash-flood crest can arrive within minutes. Climb to higher ground.

**Flood Warning**
1. Waters are rising. Steer clear of low lying areas.

**Red Flag Warning**
1. Conditions are set for fire to spread fast. Avoid anything that could kick off a blaze.

**Fire Warning**
1. An active fire is threatening the area. Be ready to evacuate immediately.

**Storm Surge Warning**
1. A severe surge of seawater is set to overrun the coast. Heed evacuation orders and get to higher ground.

**Storm Surge Watch**
1. Severe surge flooding may develop along the coast. Keep a close watch on the latest alerts.

**Hurricane Force Wind Warning**
1. Hurricane force winds above 64 knots are expected at sea. Remain in port and keep all vessels well clear of open water.

**Hurricane Force Wind Watch**
1. Hurricane force winds are possible at sea. Monitor alerts closely and prepare to keep vessels in port.

**Gale Warning**
1. Gale force winds and rough seas are expected. Small craft should stay in port and rig larger vessels for heavy weather.

**Gale Watch**
1. Gale force winds are possible at sea. Watch the forecast and ready your vessel for heavy weather.

**Storm Warning**
1. Storm force winds are building offshore. Remain in port and keep well clear of exposed and open water.

**Hazardous Seas Warning**
1. Severe, steep and high seas are expected. Keep vessels in port and off the water until the swell eases.

**Special Marine Warning**
1. Sudden strong winds and severe seas are bearing down on the area. Head for harbour and secure your vessel for heavy weather.

**Heavy Freezing Spray Warning**
1. Rapid ice build-up from freezing spray is expected at sea. Clear decks often and stay in port if you can.

**High Surf Warning**
1. Severe breakers are hitting the shore. Keep well back from seawalls, rocks, and the water's edge.

**Rip Current Statement**
1. Severe rip currents are running along the coast. Swim near a lifeguard and never fight the current if you are caught.

**Beach Hazards Statement**
1. Hazardous conditions such as rip currents or sneaker waves are expected at the beach. Stay alert and heed lifeguard guidance.

**Coastal Flood Warning**
1. Tidal flooding is likely along the coast.

**Lakeshore Flood Warning**
1. Lakeshore flooding is underway. Keep a close watch on the latest alerts.

**Winter Storm Warning**
1. A heavy-hitting winter storm is moving in. Postpone travel and keep supplies within reach.

**Ice Storm Warning**
1. Heavy ice is expected to build up. Stay off the roads and prepare for downed limbs and power cuts.

**Extreme Cold Warning**
1. Bitter wind chill is settling in. Stay inside where you can and guard exposed skin against frostbite.

**Extreme Heat Warning**
1. A severe heat wave is setting in. Drink plenty of water, seek cool spaces, and look out for the vulnerable.

**High Wind Warning**
1. Violent winds are expected. Secure loose objects and watch for downed limbs and power lines.

**Dust Storm Warning**
1. Blinding dust is cutting visibility to nothing. Pull off the road and wait it out.

**Avalanche Warning**
1. Severe avalanche conditions exist in the backcountry. Stay well clear of avalanche terrain and check the local forecast.

**Freeze Warning**
1. A hard sub-freeze is on the way. Cover anything frost-sensitive and guard against burst pipes.

**Air Quality Alert**
1. Air pollution is reaching unhealthy levels. Limit time outdoors, keep windows closed, and take it easy if you have breathing trouble.

**Dense Fog Warning** _(no US NWS "Warning" event; phrasing kept from the European/Gulf fog wording, used by the Rotterdam source)_
1. Dense fog is closing in and visibility is dropping fast. Slow down, switch to low-beam headlights, and watch for sudden slow or stopped traffic.

## US weather (NWS) — Small Craft Advisory roundup
1. Small craft advisories cover {n} stretches of US coastal water. Small craft should remain in harbour until conditions ease.

---

## Europe (MeteoAlarm)
Prefix carries `EU, <country>`. Openers name the affected sub-regions (`{label}` = as many as fit, then "and N other areas"); with no named sub-region, the "for {label}" is dropped (the country is already in the prefix). Awareness codes are normalised, so `extreme_heat`, `High Temperature`, and `high-temperature` all classify the same.
1. {article} {color} {hazard} warning is active for {label}.
2. {article} {color} {hazard} warning has been issued for {label}.

**Heat / cold degree** (°C): heat warnings append ` Highs near {N}°C.` and cold warnings ` Lows near {N}°C.` — the forecast peak over the next 5 days at the country's capital (the feed gives no coordinates, so it's a national proxy).

**Action wording reused from the US lists** — each European hazard maps to a US event:
- thunder → **Severe Thunderstorm Warning**
- wind → **High Wind Warning**
- avalanche → **Avalanche Warning**
- snow → **Winter Storm Warning**
- ice → **Ice Storm Warning**
- flood → **Flood Warning**
- forest / fire → **Red Flag Warning**
- coast → **Coastal Flood Warning**
- high-temp / heat → **Extreme Heat Warning**
- low-temp / cold → **Extreme Cold Warning**

European-only hazards keep their own lines:
**rain**
1. Persistent heavy rain could cause flooding. Steer clear of low ground.

**fog**
1. Dense fog is expected. Visibility will be poor.

**temperature** (generic, when not clearly hot/cold)
1. Temperatures will reach an extreme. Take it easy and look in on the vulnerable.

**(default)**
1. Conditions could get rough. Stay alert and follow local guidance.

---

## GDACS — volcanoes & wildfires (region-filtered)
Prefix carries `REGION, country`; the country is no longer named in the body.
1. {article} {alert} alert is active for {name}{detail}.
2. {article} {alert} alert has been issued for {name}{detail}.

**Volcano**
1. Respect the exclusion zones and heed evacuation guidance from local authorities.

**Wildfire**
1. Stay ready to evacuate at short notice and keep a close watch on local alerts.

---

## Earthquakes (USGS)
Prefix carries `REGION, <state/country>` lifted off the place; the body keeps the precise epicenter.
1. A magnitude {mag} earthquake has hit {place}.

_Tsunami note:_
1. Coastal areas near the epicentre should follow any tsunami warnings issued by local authorities.

_No-tsunami note:_
1. Expect possible aftershocks. Keep away from weakened buildings and be ready for further shaking.

---

## Marine sea-state / high seas (Open-Meteo)
1. Seas are building to {h}m ({low}) in {area}. Secure for heavy weather and keep well clear of exposed waters.

## Marine fog (Open-Meteo visibility)
1. Dense fog has settled over {area}, dropping visibility to around {v} m. Slow down, sound your fog signals, and post a lookout.

## Marine wind — gale / storm / hurricane-force at sea (Open-Meteo)
_{cat} is Gale-force, Storm-force, or Hurricane-force depending on speed._
1. {cat} winds are raking {area} at {w} knots and gusting to {g}. Small craft have no business out there, and larger vessels should batten down and rig for heavy weather.
2. A {cat_low} blow has set in over {area}, winds at {w} knots and gusts to {g}. Hold port if you are small, and lash down everything topside if you are not.

## Marine — long-period swell (Open-Meteo)
1. Powerful long-period groundswell is pushing into {area}, {h} m and spaced {p} seconds apart. That energy stacks up fast in the shallows. Expect sneaker sets and treacherous surf around inlets and bars.

## Marine — harmful algal bloom / red tide (CalHABMAP, US Pacific coast)
Prefix carries `USA, California`.
_Cell-count bloom:_
1. A harmful bloom is taking hold off {name}, Pseudo-nitzschia running to {cells} cells per litre. The water can turn toxic with domoic acid. Avoid discolored patches and do not harvest shellfish until it clears.

_Domoic-acid spike:_
1. Domoic acid is spiking off {name}, the bloom toxin climbing to {da} ng/mL. Do not harvest or eat local shellfish, and keep well clear of any discolored water.

---

## Maritime security / military (NGA)
`{region}` names only the body of water (the bordering country is dropped). No geo-tag prefix.

**Launch hazard**
1. A missile or rocket launch hazard area is active in {region}. Vessels should keep well clear until the operation is complete.

**Mine danger**
1. Drifting mines or unexploded ordnance have been reported in {region}. Vessels should avoid the area and report any sighting. Keep a safe distance.

**Gunfire / live-fire**
1. Naval gunnery or live-fire operations are underway in {region}. Keep well clear of the affected area until it's lifted.

**GPS interference**
1. GPS is being jammed across {region}, positions spoofed or knocked out cold. Don't trust anything the receiver hands you. Fix your position by radar, visual bearings, and dead reckoning.

**Sea ice / iceberg**
1. Ice is drifting into the shipping lanes across {region}. Bergs and growlers adrift in the sea lanes. Slow down, keep radar and a lookout on watch, and steer well clear.

**Cable / pipeline / drifting hazard**
1. A drifting hazard is in force in {region}, adrift objects or subsea cable and pipeline work in the area. Keep clear, slow down, and steer around the marked area.

**Strait / chokepoint**
1. A navigation hazard is in force in {region}, one of the world's busiest chokepoints. Traffic is dense and the margins are thin. Slow down, keep a sharp watch, and follow the routing in force.

---

## Outdoor — extreme UV
Prefix carries `REGION, city`; the city is no longer named in the body. Advisory tier ("Heads up,").
1. The UV index has reached {uv}, an extreme level. Cover up and seek shade through the middle of the day.
2. UV has spiked to {uv}, in the extreme range. Cover exposed skin and stay shaded around midday.

## Outdoor — dust storm
1. Thick dust is filling the air, pushing levels to {dust} µg/m³. Limit time outside, close everything up, and protect your eyes and lungs.

## Outdoor — violent thunderstorm / lightning
_"{hail}" becomes " and hail" or " and large hail" when hail is detected._
1. Violent thunderstorms are rolling through, packing severe lightning{hail}. Seek solid shelter, stay off open ground and water, and wait it out.

---

## Gulf states — extreme heat (Open-Meteo)
1. Severe heat is gripping {name}. Highs near {temp}°C. Stay out of the midday sun, keep drinking water, and watch closely for heat stress.

## Gulf states — cold snap (Open-Meteo)
_Near-freezing tier, advisory ("Heads up,"). Fires when the forecast low is at/below the threshold._
1. A cold snap is gripping {name}. Lows near {low}°C. A hard sub-freeze is on the way. Cover anything frost-sensitive and guard against burst pipes.

## Gulf states — shamal / high winds (Open-Meteo)
_NW winds use the shamal lines; winds from other directions use the generic ones._
_Shamal:_
1. Strong shamal winds are raking {name} at {wind} km/h, gusting to {gust}. Dust will cut visibility and rattle anything loose.

_Other strong winds:_
1. A strong blow has set in over {name}, winds at {wind} km/h and gusts to {gust}. Expect blowing dust and reduced visibility. Secure loose objects and take care outdoors.

## Gulf states — dense fog (Open-Meteo visibility)
_Softened with a "Heads up," lead (advisory tier)._
1. Thick fog is blanketing {name} with visibility near {vis} m. Reduce speed, switch to low-beam headlights, and watch for sudden slow or stopped traffic.

## Gulf states — thunderstorms (Open-Meteo weather codes)
1. Thunderstorms are breaking out over {name}, with lightning, sudden downpours, and gusty winds. Head indoors away from windows and off exposed ground until they pass.

## Gulf states — heavy rain / flash flooding (Open-Meteo precipitation)
1. Heavy rain is hammering {name} at about {rain} mm in the hour, and the hard ground sheds it fast. Avoid wadis and low crossings.

## Gulf states — dust storm (Open-Meteo air-quality)
1. Thick dust is choking the air over {name} at {dust} µg/m³. Visibility and air quality are plummeting. Stay indoors and seal windows.

---

## Almanac — Rotterdam compass / navigation (scheduled, not an alert) — ACTIVE
_Daily "bearing" posts derived from Open-Meteo sun data + solar geometry. Plain two-line format (`HH:MM CEST` + body), no "Heads up," lead. `{az}` is a 3-digit TRUE bearing (051, 309); `{off}` is the live angle to true north (equals the sunrise azimuth, accurate every day — not a fixed 90°). Each fires relative to the actual sun event, so timing stays right year-round._

_Sunrise bearing (within ~3 h after sunrise):_
1. Sunrise bears {az}° today. Line yourself up with it, and true north sits {off}° off your left.

_Sunset bearing (within ~2 h before sunset):_
1. Sun bears {az}° tonight. Line yourself up with it, and true north sits {off}° off your right.

_Solar noon (within ~15 min of solar noon):_
1. Solar noon. The sun is locked due true south right now. Your shadow locks straight true north — the day's cleanest compass check.

_Daylight ledger (with the sunrise post). Seasonal twin — the light is either growing (Dec–Jun) or shrinking (Jun–Dec); {delta} is the day-over-day change ("2 minutes" / "45 seconds"):_
1. _(gaining)_ Daylight today: {len}, and the sun's clawing back about {delta} a day now.
1. _(losing)_ Daylight today: {len}, and the light's clawing off about {delta} a day now.

---

## Tide — Hoek van Holland (scheduled, not an alert) — ACTIVE
_Next predicted high water at Rotterdam's sea gate, from Rijkswaterstaat's open WaterWebservices. Fires once per high-water event, in the ~90 min run-up to it. `{time}` is local (CEST/CET); `{height}` is metres relative to NAP._
1. Next high water at {name}: {time}, {height} m.

---

## City weather update — Rotterdam (scheduled, not an alert)
_Routine twice-daily forecast in local time and °C. Posts once in the morning window and once in the evening window each day. {cond} is a plain-language sky description (clear skies, broken cloud, light rain, fog, thunderstorms, etc.)._

_Morning:_
1. Rotterdam this morning, it's {temp}°C with {cond}. The day reaches {high}°C and eases to {low}°C, with winds {wdesc} near {wind} km/h.

_Evening:_
1. Rotterdam this evening, {temp}°C with {cond}. Overnight settles to {low}°C, and tomorrow climbs to {high}°C with {cond_tmr}.
