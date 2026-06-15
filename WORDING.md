# K5Bearing — all alert wording

Every phrasing the bot can post. Text in {curly braces} is filled in automatically at post time (location, magnitude, Kp, time, etc.).
One variant is chosen per alert. Mark up anything you want changed and hand it back to Claude to apply.

**Every post is prefixed with a 24-hour local timestamp**, e.g. `16:33 CEST:` or `09:12 UTC+8:`.

---

## Space weather — geomagnetic storm + compass
_Kp 5–6 (G1–G2):_
1. A {level} geomagnetic storm is underway at Kp {kp}, and magnetic north is drifting. A compass can read a few degrees off true. Check any bearing against GPS or a known landmark before you rely on it.
2. A {level} geomagnetic storm has set in at Kp {kp}, nudging magnetic north off true. A compass may be a few degrees out. Confirm any bearing with GPS or a fixed landmark before trusting it.

_Kp 7+ (G3–G5):_
1. A {level} geomagnetic storm is underway at Kp {kp}, and magnetic north is swinging by several degrees. Treat any compass heading as approximate and hold your course by GPS or a celestial bearing until it eases.
2. A {level} geomagnetic storm has ramped up to Kp {kp}, throwing magnetic north off by several degrees. Trust GPS or a celestial bearing and treat the compass as a rough guide until it settles.

## Space weather — aurora
1. Kp has climbed to {kp}, expanding the auroral oval toward lower latitudes. The aurora may appear over {regions} and at matching southern latitudes. Look poleward, well away from city lights.
2. With Kp up to {kp}, the auroral oval is reaching lower latitudes. The aurora could be visible over {regions} and their southern equivalents. Find a dark spot and scan the poleward sky.

`{regions}` by Kp level:
- Kp 5: Scotland, Scandinavia, and the northern US
- Kp 6: Ireland, Denmark, and the northern US
- Kp 7: the UK, central Europe, and the northern US
- Kp 8: northern France, the Alps, and the central US
- Kp 9: southern Europe and the central US, which is rare

## Space weather — solar flare
_Lead (one picked):_
1. {article} {class} solar flare erupted, peaking at {time} UTC.
2. The Sun fired off {article} {class} flare, peaking at {time} UTC.

_Impact clause (by class):_
- M-class: Flares this strong can cause brief HF (shortwave) radio blackouts on the daylit side of Earth.
- X-class: Flares this strong can trigger widespread shortwave radio blackouts on the daylit side of Earth and degrade GPS and HF communications.

## Space weather — solar alerts
Posts NOAA's own alert headline verbatim, prefixed: `Space weather alert: {NOAA headline}`.

---

## US weather (NWS) — announcement openers
Wraps every US alert ({article}=A/An, {event}=e.g. 'tornado warning', {where}=' for <place>'):
1. {article} {event} is in effect{where}.
2. {article} {event} has been issued{where}.
3. {article} {event} is now active{where}.

## US weather (NWS) — per-hazard action lines
**Tornado Warning**
1. Move to the lowest floor and an interior room away from windows, and stay there until the warning is lifted.
2. Get to a basement or an interior room on the lowest floor now and stay clear of windows, as a tornado can drop fast from the wall cloud.

**Hurricane Warning**
1. Destructive winds and storm surge are expected. Finish your preparations now and follow any evacuation orders without delay.
2. Life-threatening winds and surge are on the way. Complete your storm prep and leave at once if you are told to evacuate.

**Hurricane Watch**
1. Hurricane conditions are possible within about two days. Get your preparations in order and monitor official updates closely.
2. A hurricane may strike within roughly 48 hours. Ready your supplies and keep an eye on the latest forecasts.

**Tropical Storm Warning**
1. Tropical storm force winds are expected. Secure anything loose outside and stay indoors as conditions deteriorate.
2. Strong tropical winds are on the way. Tie down loose items and head inside before the weather turns.

**Tsunami Warning**
1. Move to high ground or inland right away and remain there until officials confirm it is safe to return.
2. Head for high ground or move well inland immediately, and do not return until authorities give the all clear.

**Blizzard Warning**
1. Travel will become dangerous in near zero visibility. Stay off the roads and remain somewhere warm.
2. Blowing snow will bring ground blizzard whiteouts. Avoid all travel and keep warm clothing and supplies within reach.

**Extreme Wind Warning**
1. Extreme winds are about to arrive. Move to the lowest floor and stay clear of windows until they pass.
2. Violent winds are imminent. Shelter on the lowest floor away from windows right now.

**Severe Thunderstorm Warning**
1. Damaging winds and large hail are likely. Head indoors and keep away from windows until the storm moves through.
2. A supercell can bring damaging winds and large hail. Get inside, stay off the road, and wait for it to pass.

**Flash Flood Warning**
1. Water can rise very quickly. Move to higher ground and never try to drive or walk through floodwater.
2. The flash-flood crest can arrive within minutes. Climb to higher ground now and never enter water flowing across a road.

**Flood Warning**
1. Flooding is already underway. Avoid low lying roads and do not drive through water of unknown depth.
2. Waters are rising. Steer clear of low lying areas and turn around rather than crossing a flooded road.

**Red Flag Warning**
1. Conditions are right for fire to spread fast. Avoid anything that could throw a spark and be ready to leave at short notice.
2. Any fire could grow rapidly today. Hold off on open flames and keep an evacuation plan ready.

**Fire Warning**
1. An active fire is threatening the area. Be ready to evacuate immediately and follow the instructions of local officials.
2. A fire is bearing down on the area. Prepare to leave at once and do exactly as local officials direct.

**Storm Surge Warning**
1. Life-threatening flooding from rising ocean water is expected. Follow evacuation orders and move inland to higher ground.
2. A dangerous surge of seawater is set to inundate the coast. Heed evacuation orders and get to higher ground inland.

**Storm Surge Watch**
1. Life-threatening coastal flooding from surge is possible. Review your evacuation plan and monitor official updates.
2. Dangerous surge flooding may develop along the coast. Ready your evacuation plan and track the latest advisories.

**Hurricane Force Wind Warning**
1. Hurricane force winds above 64 knots are expected at sea. Remain in port and keep all vessels well clear of open water.
2. Winds of hurricane force are expected offshore. Stay in harbour and keep every vessel battened down and clear of exposed water.

**Hurricane Force Wind Watch**
1. Hurricane force winds are possible at sea. Monitor advisories closely and prepare to keep vessels in port.
2. Winds of hurricane force may develop offshore. Watch the advisories and be ready to stay in harbour.

**Gale Warning**
1. Gale force winds and rough seas are expected. Small craft should stay in port and larger vessels should secure for heavy weather.
2. Gale conditions are building at sea. Keep small boats ashore and rig larger vessels for heavy weather.

**Gale Watch**
1. Gale force winds are possible at sea. Monitor the forecast and prepare to secure your vessel.
2. Gale conditions may develop offshore. Watch the forecast and ready your vessel for heavy weather.

**Storm Warning**
1. Storm force winds are expected at sea. Remain in port and keep well clear of exposed and open water.
2. Storm force winds are building offshore. Make for port and stay off open water until it blows through.

**Storm Watch**
1. Storm force winds are possible at sea. Track the forecast and prepare to stay in port.
2. Storm force conditions may build offshore. Follow the forecast and be ready to remain in harbour.

**Hazardous Seas Warning**
1. Dangerously steep and high seas are expected. Mariners should remain in port until conditions improve.
2. Hazardous seas are building. Keep vessels in port and off the water until the swell eases.

**Special Marine Warning**
1. Sudden strong winds and dangerous seas are bearing down on the area. Head for harbour and secure your vessel now.
2. A squall of strong winds and rough seas is moving in. Make for the nearest harbour and batten down right away.

**Small Craft Advisory**
1. Winds and seas are rough enough to endanger small boats. Inexperienced mariners and small craft should stay in port.
2. Conditions are hazardous for small vessels. Small craft should remain in harbour until the advisory ends.

**Heavy Freezing Spray Warning**
1. Heavy freezing spray will pile dangerous ice onto vessels. Keep decks clear and consider staying in port.
2. Rapid ice build-up from freezing spray is expected at sea. Clear decks often and stay in port if you can.

**Freezing Spray Advisory**
1. Freezing spray will coat vessels in ice. Clear it regularly and take care moving about the deck.
2. Ice from freezing spray is likely on deck and rigging. Clear it often and watch your footing.

**High Surf Warning**
1. Large and powerful surf is striking the coast. Stay off rocks, jetties, and the beach face.
2. Dangerous breakers are hitting the shore. Keep well back from jetties, rocks, and the water's edge.

**High Surf Advisory**
1. Large breaking waves are expected along the coast. Use caution near the surf and stay off rocks and jetties.
2. Elevated surf is on the way. Keep clear of the waterline, jetties, and exposed rocks.

**Rip Current Statement**
1. Dangerous rip currents are running along the coast. Swim near a lifeguard and never fight the current if you are caught.
2. Strong rip currents are likely at the beach. Stay near a lifeguard and swim parallel to shore to break free of one.

**Beach Hazards Statement**
1. Hazardous conditions such as rip currents or sneaker waves are expected at the beach. Stay alert and heed lifeguard guidance.
2. Dangerous surf and currents are possible at the beach. Keep a close eye on the water and follow lifeguard advice.

**Coastal Flood Warning**
1. Coastal flooding is expected around high tide. Move vehicles to higher ground and stay off flooded roads.
2. Tidal flooding is likely along the coast. Relocate vehicles early and avoid roads near the water.

**Coastal Flood Watch**
1. Coastal flooding is possible around high tide. Monitor advisories and be ready to move vehicles to higher ground.
2. Tidal flooding may develop along the coast. Watch the forecast and prepare to relocate vehicles early.

**Coastal Flood Advisory**
1. Minor coastal flooding is expected around high tide. Avoid flooded roads near the shore.
2. Some tidal flooding is likely near the coast. Steer clear of low roads close to the water.

**Lakeshore Flood Warning**
1. Flooding is expected along the lakeshore. Move vehicles to higher ground and stay off flooded roads.
2. Lakeshore flooding is underway. Relocate vehicles and avoid roads near the water.

**Tsunami Advisory**
1. Strong currents and waves dangerous to anyone in or near the water are expected. Leave the water and stay off the beach.
2. Dangerous currents and surges are expected at the coast. Get out of the water and keep off the beach and harbours.

**Tsunami Watch**
1. A distant earthquake may generate a tsunami. Stay tuned to official updates and be ready to move to high ground.
2. A tsunami is possible after a distant quake. Monitor official advisories and be ready to head for high ground.

**Winter Storm Warning**
1. Heavy snow and ice are expected. Avoid travel and keep warm clothing and supplies within reach.
2. A significant winter storm is moving in. Postpone travel and stock up on warmth and supplies.

**Ice Storm Warning**
1. Significant ice is expected to build up. Stay off the roads and prepare for downed limbs and power cuts.
2. A damaging glaze of ice is on the way. Avoid driving and be ready for outages and falling branches.

**Extreme Cold Warning**
1. A dangerous wind chill is setting in. Limit time outdoors and cover exposed skin to guard against frostbite.
2. Bitter, dangerous cold is settling in. Stay inside where you can and bundle up against frostbite.

**Extreme Heat Warning**
1. Dangerous heat is building. Stay hydrated, find cool air, and check on anyone at risk.
2. A dangerous heat wave is setting in. Drink plenty of water, seek cool spaces, and look out for the vulnerable.

**High Wind Warning**
1. Damaging winds are expected. Secure loose objects and watch for downed limbs and power lines.
2. Strong, damaging gusts are on the way. Tie down loose items and steer clear of fallen lines.

**Dust Storm Warning**
1. A wall of blowing dust is dropping visibility to near zero. Pull off the road, turn your lights off, and wait it out.
2. Blinding dust is cutting visibility to nothing. Leave the roadway, switch off your lights, and stay put.

**Avalanche Warning**
1. Dangerous avalanche conditions exist in the backcountry. Stay well clear of avalanche terrain and check the local forecast.
2. The avalanche danger is high in the backcountry. Avoid steep slopes and consult the local avalanche centre.

## US weather (NWS) — Small Craft Advisory roundup
1. Small craft advisories are in effect across {n} coastal zones. Inexperienced mariners and small craft should stay in port until conditions ease.
2. Small craft advisories cover {n} stretches of coastal water. Small craft should remain in harbour until conditions improve.

---

## Europe (MeteoAlarm) — announcement openers
({article}=A/An, {color}=yellow/orange/red, {hazard}=e.g. wind, {label}=country, {where}=', covering N regions'):
1. {article} {color} {hazard} warning is in effect for {label}{where}.
2. {article} {color} {hazard} warning has been issued for {label}{where}.
3. {article} {color} {hazard} warning is now active for {label}{where}.

## Europe (MeteoAlarm) — per-hazard action lines
**thunder**
1. Severe storms are likely. Stay indoors and away from windows until they pass.
2. Violent thunderstorms are expected. Head inside and keep clear of windows.

**wind**
1. Strong winds are expected. Secure anything loose outside and keep away from exposed areas.
2. Powerful gusts are on the way. Tie down loose items and avoid open, exposed ground.

**rain**
1. Heavy rain may bring flooding. Avoid low lying roads and allow extra time to travel.
2. Persistent heavy rain could cause flooding. Steer clear of low ground and plan for delays.

**flood**
1. Flooding is possible. Avoid low lying roads and do not drive through water of unknown depth.
2. Rising water is likely. Keep away from low lying areas and never cross a flooded road.

**snow**
1. Snow and ice will make travel difficult. Only head out if necessary.
2. Heavy snow is expected. Postpone travel unless it is truly necessary.

**ice**
1. Ice will make roads and paths treacherous. Take extra care and travel only if you need to.
2. Icy surfaces are likely. Tread carefully and avoid driving where you can.

**fog**
1. Visibility will be poor. Slow down and keep your lights on while driving.
2. Dense fog is expected. Reduce speed and use dipped headlights on the road.

**forest**
1. Fire risk is high. Avoid open flames and report any sign of fire immediately.
2. Conditions favour fast moving fire. Hold off on flames and report smoke at once.

**fire**
1. Fire risk is high. Avoid open flames and report any sign of fire immediately.
2. Conditions favour fast moving fire. Hold off on flames and report smoke at once.

**heat**
1. Temperatures will be dangerously high. Stay hydrated and out of the midday sun.
2. A dangerous heat spell is expected. Drink plenty of water and avoid the midday heat.

**temperature**
1. Temperatures will reach an extreme. Limit your exposure and check on those at risk.
2. An extreme in temperature is expected. Take it easy and look in on the vulnerable.

**cold**
1. Temperatures will be dangerously low. Limit time outdoors and dress in warm layers.
2. Bitter cold is expected. Stay in where you can and wrap up in warm layers.

**coast**
1. Coastal conditions will be dangerous. Stay well back from the shoreline and exposed paths.
2. Rough seas are expected along the coast. Keep clear of the shore and exposed walkways.

**avalanche**
1. Avalanche risk is elevated. Stay off backcountry slopes and follow local guidance.
2. The avalanche danger is raised. Avoid steep backcountry terrain and heed local advice.

**(default / other)**
1. Conditions could become dangerous. Stay alert and follow local guidance.
2. The situation may turn hazardous. Stay aware and follow local advice.

---

## Global multi-hazard (GDACS) — announcement openers
({article}=A/An, {alert}=orange/red, {name}=event, {loc}=' near <country>', {detail}=', currently <severity>'):
1. {article} {alert} alert is in effect for {name}{loc}{detail}.
2. {article} {alert} alert has been issued for {name}{loc}{detail}.
3. {article} {alert} alert is now active for {name}{loc}{detail}.

## Global multi-hazard (GDACS) — per-hazard action lines
**Tropical Cyclone**
1. This is a dangerous storm. Follow evacuation orders and stay clear of the coast, where storm surge is deadliest.
2. The system is dangerous. Heed evacuation orders and keep away from the coast, where surge poses the greatest risk.

**Flood**
1. Move to higher ground, keep clear of floodwater, and follow the instructions of local authorities.
2. Get to higher ground, avoid the floodwater, and do as local authorities advise.

**Earthquake**
1. Aftershocks are possible. Stay clear of damaged buildings and be ready for further shaking.
2. Expect possible aftershocks. Keep away from damaged structures and brace for more movement.

**Volcano**
1. Follow any exclusion zones and evacuation guidance issued by local authorities.
2. Respect the exclusion zones and heed evacuation guidance from local authorities.

**Wildfire**
1. Stay ready to evacuate at short notice and keep a close watch on local alerts.
2. Be prepared to leave quickly and monitor local alerts closely.

**Tsunami**
1. Move to high ground or inland immediately and stay there until officials say it is safe.
2. Get to high ground or head inland at once, and remain there until the all clear.

**Drought**
1. Conserve water where you can and follow local guidance.
2. Use water sparingly and follow the advice of local authorities.

---

## Earthquakes (USGS) — lead (one picked)
1. A magnitude {mag} earthquake has struck {place}.
2. A magnitude {mag} earthquake has hit {place}.
3. A magnitude {mag} earthquake was recorded {place}.

_Follow-up — tsunami:_
1. Coastal areas near the epicentre should follow any tsunami warnings issued by local authorities.
2. A tsunami may follow. Coastal areas near the epicentre should heed local warnings.

_Follow-up — no tsunami:_
1. Aftershocks are possible. Stay clear of damaged structures and be ready for further shaking.
2. Expect possible aftershocks. Keep away from weakened buildings and be ready for more shaking.

---

## Marine sea-state / high seas (Open-Meteo)
({cat}=High/Very high/Phenomenal, {h}=wave height in m, {area}=sea area):
1. {cat} seas running to {h}m are reported in {area}. Small craft should stay in port and larger vessels should rig for heavy weather.
2. Seas are building to {h}m ({low}) in {area}. Secure for heavy weather and keep well clear of exposed waters.

---

## Maritime security / military (NGA) — per-category lines
**Missile/rocket launch hazard**
1. A missile or rocket launch hazard area is active in {region}. Vessels should keep well clear until the operation is complete.
2. Launch operations have closed off part of {region}. Steer clear of the hazard area until it reopens.

**Mine danger**
1. Drifting mines or unexploded ordnance have been reported in {region}. Post a lookout, reduce speed, and keep a safe distance from the area.
2. A mine danger exists in {region}. Vessels should avoid the area and report any sighting to the authorities.

**Naval gunfire / live-fire**
1. Naval gunnery or live-fire operations are underway in {region}. Vessels should stand clear of the firing range until it is lifted.
2. Live-fire exercises are taking place in {region}. Keep well clear of the danger zone until the operation ends.

**Military exercise**
1. A naval or military exercise is closing off waters in {region}. Route around the area until it reopens.
2. Military operations are restricting navigation in {region}. Give the area a wide berth until the exercise is complete.

**GPS interference / jamming**
1. GPS interference has been reported in {region}. Verify your position by radar, visual bearings, or dead reckoning.
2. Navigators report GPS jamming or spoofing in {region}. Cross-check your position and do not rely on GPS alone.

---

## Outdoor safety (Open-Meteo) — extreme UV
1. The UV index has reached {uv} in {name}, an extreme level. Cover up, wear sunglasses and sunscreen, and seek shade through the middle of the day.
2. UV has spiked to {uv} in {name}, in the extreme range. Wear sunscreen and shades, cover exposed skin, and stay shaded around midday.

