# Modded Minecraft server

Minecraft **1.20.1**, **Forge**, and **Java 17**, using the
[`itzg/minecraft-server`](https://docker-minecraft-server.readthedocs.io/)
base image.

## Requirements

- Docker Engine and Docker Compose v2 with support for `up --wait`.
- Docker BuildKit with Dockerfile frontend 1.6 support for checksum-verified downloads.
- Enough host RAM for a 19 GiB Minecraft container plus other services and the
  operating system. Java heap is 17 GiB, leaving approximately 2 GiB for JVM
  overhead within the container limit.
- Host swap enabled to use the container's additional allowance of up to 4 GiB.
  Compose sets a 19 GiB RAM limit and a 23 GiB combined RAM-plus-swap limit.
  Swap is a safety net, not a substitute for RAM; heavy swapping can worsen lag
  and host responsiveness. Recreate the container with
  `docker compose up -d --force-recreate minecraft` after changing these limits.
- Outbound internet access to download Forge and Minecraft during first startup.
- Build-time access to Docker Hub for the Dockerfile frontend/base image and
  `cdn.modrinth.com` for the two externally hosted mod JARs.
- TCP port **25565** accessible to your players.
- UDP port **24454** accessible to your players for Simple Voice Chat.

## Add your mods

`mods/` contains the server's mod JARs. Add only **server-compatible Forge 1.20.1**
mods and their dependencies. Do not include client-only mods.

When reviewing additions, keep mods that support both client and dedicated
server, including optional server features and shared libraries. A dependency's
`side="BOTH"` in `mods.toml` describes when that dependency is required; it does
not prove that the declaring mod supports dedicated servers. Check the project's
documentation or distribution metadata when its supported side is unclear.

Keep Connector and Forgified Fabric API: Hardcore Totem Nerf is a Fabric mod
in this pack, and its MidnightLib dependency is bundled inside its JAR. Do not
replace Forgified Fabric API with the regular Fabric API. Cloth Config is also
required on the server by Bosses of Mass Destruction, even though several
client-only mods use it too.

The initial review inspected 172 top-level JARs and 145 nested archives and
removed 27 client-only JARs, leaving 145 top-level JARs for the server.
[`client-only-mods.json`](./client-only-mods.json) records the latest November 4, 2026
cleanup below; earlier counts describe historical reviews. It is a review record, not an
automatic filter for future mod versions. Keep removed mods in your separate
client installation if you want their UI and rendering features.

The October 17, 2026 import reviewed 225 incoming JARs by filename, internal mod
ID, bundled dependencies, and published side/version metadata. It added 87 JARs,
bringing the server to 232 top-level JARs, without replacing or removing any
installed JARs. It skipped 98 duplicates/alternate versions, 39 client-only JARs,
and Canary, which is an alternative Lithium port to the installed Radium.
Even differently named versions and same-named files with different hashes were
left unchanged when their mod was already installed.

Additions include Alex's Caves, Mekanism, Quark/Zeta, Oh The Biomes We've Gone,
Serene Seasons, Weather2, Bountiful, structure/content mods, and their libraries.
Shared libraries and optional server components were retained rather than
discarded merely because client mods also use them. Every added JAR matched a
published Modrinth file hash; client-only exclusions also use project documentation
and the earlier exact-file review where appropriate.

The subsequent dedicated-server launch exposed a runtime defect in
`ToadLib-1.20.1-1.3.5S-3.jar` (internal version `1.3.5S-2`): it loads
`com.mr_toad.lib.api.config.ToadConfig`, which is annotated for the client only.
This unused library was removed, leaving **231 top-level JARs**. No other
installed mod, including nested libraries, declares a ToadLib dependency or
references its classes. This is a broken-build exclusion, not a classification
of all ToadLib versions as client-only. Rebuild and redeploy to remove the old
JAR from the persistent server's mod directory; do not delete the world volume.

Shared mods remain, including AppleSkin, Jade, JEI, ShulkerBoxTooltip, Xaero's
maps, EnhancedVisuals, AtomicStryker's Dynamic Lights, and What Are They Up To.
Their server components provide synchronization or other functionality.
HotVP is Hero of the Village Plus, a client-and-server gameplay mod, not a HUD
mod. Shared libraries (Bookshelf, CreativeCore, Iceberg, Fzzy Config, and YACL)
also remain even when their only current consumer uses them on the client.

The dependency review found no missing declared mandatory server dependencies,
including nested libraries and the Connector/Forgified Fabric API compatibility
layer. This is not a runtime compatibility guarantee: verify startup through the
Compose health check and inspect the server logs after deploying. Current retained
mods require Forge **47.4.0 or newer**; use a compatible version matching the clients.
Forge's recommended 1.20.1 release at the time of this import is **47.4.10**.
The import's static checks found no missing or out-of-range mandatory server
dependencies and no duplicate top-level mod IDs; a dedicated-server startup test
is still required after rebuilding and deploying.

### October 22, 2026 client-only cleanup

The replacement pack contained **243 top-level JARs**. This review removed
**47 confirmed client-only JARs**, leaving **195**. Of the original JARs, 236
matched exact published Modrinth file hashes. Forty-five removals have
`server_side=unsupported` project metadata; the other two, Farsight and the
installed True Darkness fork, were confirmed from embedded descriptions and
client entrypoint/rendering code. The JSON review record lists every removed
filename, SHA-1, and verification source or embedded evidence.

Server-only and shared/optional-server mods remain, including JEI, Jade,
AppleSkin, Enchantment Descriptions, Sound Physics Remastered, Xaero's maps,
Konkrete, and shared libraries. Unknown-side mods were not removed speculatively.
Metadata checks covered 342 top-level/nested mod archives; no retained mandatory
server dependency references a removed mod ID. All 196 retained JARs were
verified unchanged by hash. (An earlier count of 196 was a miscount; 195 were
committed and deployed.)

This cleanup is not a full compatibility or startup test. The replacement pack
also reintroduced the ToadLib version with the previously observed server defect
described above and contained two Alex's Mobs JARs. The shadowed
`alexsmobs-1.22.9.jar` was later removed (Forge only loaded Alex's Mobs
Continued 2.2.3), leaving **194** JARs. Players must remove it from their
client `mods` folder too.

### November 3, 2026 client-only cleanup

The new list contained **313 top-level JARs**. This review removed **57
confirmed client-only JARs**, leaving **256**. Fifty-five exact-file matches
declare a client-only environment in Modrinth metadata. The other two, Farsight
and the installed True Darkness fork, match the exact JARs previously verified
from their embedded descriptions and client-only code. Mods declared shared,
server-only, server-optional, or with unknown side support were retained. This
is a side-support review, not a dedicated-server startup test.

### November 4, 2026 client-only cleanup

The updated pack contained **316 top-level JARs**. This review removed **57
confirmed client-only JARs**, leaving **259**. Of the original JARs, 301 matched
exact published Modrinth hashes; 54 removals have unsupported server-side project
metadata. Farsight and True Darkness match the exact JARs previously verified
from embedded descriptions and code. Punchy Moves explicitly declares
`clientSideOnly=true` in its embedded `META-INF/mods.toml`, despite unknown sides
in the exact-file project's API metadata.

The review inspected **589 top-level/nested archives**. No retained mandatory
Forge server/BOTH dependency or Fabric `depends` entry references an exclusively
removed mod ID, and all 259 retained JARs were verified unchanged by SHA-1.
Simple Voice Chat, shared libraries, and optional-server mods remain, including
JEI, EMI, Jade, AppleSkin, Sound Physics Remastered, and Xaero's maps. Thirteen
retained JARs lack exact Modrinth matches; they were not removed speculatively.
The JSON record lists each removal, its hash, and its classification evidence.
Keep client-only mods in players' separate client installations.

This pass does not establish runtime compatibility. It also found three duplicate
mod IDs: Ecliptic Seasons **0.15.4.1 / 0.15.5**, Alex's Mobs **1.22.9** / Alex's
Mobs Continued **2.2.4**, and EMI Loot **0.7.9 / 0.7.10**.
`nofriendlyfire-1.1-neoforge-1.21.1.jar` targets NeoForge/Minecraft 1.21.1 rather
than this Forge/Minecraft 1.20.1 server. These are not client-only exclusions. The subsequent compatibility cleanup
removed Ecliptic Seasons 0.15.4.1, EMI Loot 0.7.9, Alex's Mobs 1.22.9,
and the incompatible NoFriendlyFire JAR, leaving **255 top-level JARs**.
No duplicate top-level Forge mod IDs remain. A dedicated-server startup test
is still required.

### November 7, 2026 60-minute day/night cycle

[Better Days](https://modrinth.com/mod/betterdays) **1.20.1-3.3.4.5-FORGE**
slows overworld time to one third of vanilla speed, so a full day/night cycle
takes **60 real minutes** instead of 20. Its config,
[`betterdays-common.toml`](./server-config/config/betterdays-common.toml), uses a
uniform `daySpeed = nightSpeed = 0.3333333333` rather than per-phase minutes, so
Ecliptic Seasons' `DynamicDaylightDuration` still decides where sunset falls:
about 30/30 minutes at the equinoxes, up to about 38-minute days in summer and
about 37-minute nights in winter. Ecliptic Seasons has no cycle-length setting of
its own; it only remaps the sun angle and does not advance time, so the two mods
do not conflict. Each solar term stays at 7 in-game days, so seasons last 3x
longer in real time (about 42 hours per season).

Crop growth, furnaces, potions, and hunger keep their vanilla real-time speed
(`randomTickEffect`, `blockEntityEffect`, `potionEffect`, and `hungerEffect` are
`NEVER`), so roughly three times as much happens per in-game day. Better Days'
sleep feature replaces the instant night skip: time accelerates while players
sleep (about vanilla duration when everyone sleeps, partially when only some do),
and morning still fires Forge's sleep-finished event for Bed Benefits and
Ecliptic Seasons' clear-after-sleep. Better Days must be installed on clients
together with the matching `config/betterdays-common.toml` from the client
overlay. Restart the server after changing the config.

### November 7, 2026 Enhanced Celestials compatibility fix

Keep Enhanced Celestials 2 only; the original Enhanced Celestials cannot load
alongside the rewrite. Default Lunar Events **1.0.0.7** references
`dev/corgitaco/enhancedcelestials2core/platform/BuiltAgainstLog`, which is missing
from Core **1.0.3.3**. Core was updated to **1.0.3.4**, whose JAR contains that
class. The installed Corgilib **4.0.3.6** and Data Anchor **1.0.0.24** satisfy
this pair's declared dependencies.

Players must also remove original Enhanced Celestials and replace EC2 Core
1.0.3.3 with 1.0.3.4 in their client installations, keeping Default Lunar Events
1.0.0.7. Rebuild and redeploy the server image to replace the persistent server's
old Core JAR. This fixes the reported missing class; a dedicated-server startup
test is still required.

The Docker build copies this directory into `/mods` in the image. On startup,
the base image copies the bundled mods into `/data/mods`. Old mod JARs are removed
before copying so deleted or upgraded mods do not linger in the persistent
volume. Do not manually install additional JARs in `/data/mods`; manage them in
the image instead. World data and mod configuration remain persistent.

The Cravings food lists are maintained in
[`server-config/new-world/serverconfig/Cravings/cravings-foods.toml`](./server-config/new-world/serverconfig/Cravings/cravings-foods.toml).
They cover all eight craving categories with foods from Delightful, Abnormals
Delight, Alex's Delight, Ender's Delight, Festive Delight, Dungeons Delight,
Mekanism Delight, Miner's Delight, My Nether's Delight, Nether's Delight,
Oceanic Delight, and Butcher's Delight Foods, in addition to vanilla and
Farmer's Delight foods. Butcher's Delight itself registers no foods; its
butchering drops come from the required companion mod Butcher's Delight Foods
`1.0.3` (`butchersdelightfoods`), which clients must also install.
Chef's Delight, Display Delight, Storage Delight, and compatibility-only mods
do not add edible items to these lists.
Rebuild and redeploy after changing these lists; the
image syncs the world server config into the persistent data volume.

Dreamshift `0.2.2-hotfix` and The Bumblezone `7.15.2` are exceptions to Git storage:
their large JARs are downloaded into `/mods` during the Docker build from pinned
Modrinth version URLs in [`Dockerfile`](./Dockerfile). Each download is verified
against its pinned SHA-256; a failed download or checksum mismatch fails the build.
Local copies may remain in `mods/`, but are ignored by Git and excluded from the
Docker build context. A clean checkout therefore contains **255 bundled JARs**;
the built image contains **257** including these downloads. Jenkins uses the same
Docker build and needs no separate download step.

To update either externally hosted mod, change its URL and SHA-256 in
[`Dockerfile`](./Dockerfile) together, verifying the hash against the intended JAR.
If its filename changes, update the matching `.gitignore` and `.dockerignore`
entries too.

Rebuild and redeploy whenever the bundled mods change. Back up the world before
changing mods, especially when removing mods that add blocks or items.

## Server settings

[`server.properties`](./server.properties) is bundled into the image and copied
to `/data/server.properties` on every startup, including when a persistent volume
already exists. The bundled file takes precedence over changes made directly in
the volume. The base image's automatic property generation is disabled so this
file is the source of truth for server settings.
During copying, only `CFG_RCON_` placeholders in properties files are expanded
to inject the RCON password at runtime; files already in `/data` are not interpolated.

Defaults include survival mode, normal difficulty, 4 players, PvP enabled,
online authentication, view distance 8, simulation distance 6, disabled query,
and enabled RCON. Flight is allowed to avoid false flying kicks from movement mods; this
does not grant players creative flight. Spawn protection is 16 blocks, and the
whitelist is disabled.

Edit this file, then rebuild and redeploy to apply settings. Change the MOTD here,
not in `.env`. Keep `server-ip` empty so the server can bind inside the container.
If you change `server-port`, update the Compose port mapping and health-check
configuration to match. The configured world folder is `level-name=new-world`;
changing this setting selects a different world folder rather than deleting the
old one. Keep it unchanged to continue that world. Changing the seed does not
regenerate an existing world.

## Run locally

Copy `.env.example` to `.env`, review the
[Minecraft EULA](https://aka.ms/MinecraftEULA), and set `EULA=TRUE` only if you
accept it. Set `FORGE_VERSION` to the exact Forge version required by your
modpack/clients; `recommended` selects Forge's current recommended release for
Minecraft 1.20.1 and can change over time.
Set `RCON_PASSWORD` to a newly generated password of at least 24 characters using
only letters, digits, underscores, and hyphens to avoid Java properties escaping
issues. Set `RCON_BIND_IP` to the host's LAN/VPN IPv4 address (defaults to
`192.168.1.208`, as shown for node004). It must exist on the Docker host.
Do not commit `.env` or put the password directly in `server.properties`.

```sh
docker compose config --quiet
docker compose build --pull
docker compose up -d --no-build --wait --wait-timeout 900
docker compose logs -f minecraft
```

Connect to `<server-address>:25565`. Clients need matching Minecraft, Forge,
and mods, except mods explicitly documented as server-only.

The first startup downloads and installs the server and may take several minutes.
The health check tests whether Minecraft is responding, and `--wait` reports
startup failures rather than treating a running container as a ready server.

## Jenkins deployment

Configure a Pipeline job using **Pipeline script from SCM** and `Jenkinsfile`.
The **`production`** agent must be a Unix-like agent with a POSIX shell, Docker
Engine access, Git, and Docker Compose v2. Its Docker daemon must be the host
where you want the server to run; a temporary daemon will not preserve the world.
Docker access grants privileged control of that host, so restrict this job to
trusted repository changes and users.

Ensure `mods/` is present after checkout: commit the mods you are permitted to
redistribute (use Git LFS if needed), or add your own provisioning step after
checkout to retrieve them from your private artifact storage. A directory only
on your development machine is not available to Jenkins.

Run the job with:

- `ACCEPT_EULA` enabled after reviewing and accepting the EULA.
- `FORGE_VERSION` matching the clients/modpack.
- `RCON_BIND_IP` set to the production host's LAN/VPN IPv4 address.

Before the first deployment, create a Jenkins **Secret text** credential with ID
**`minecraft-rcon-password`**, containing a newly generated password of at least
24 letters/digits/underscores/hyphens. The pipeline injects it at runtime and
rejects missing/invalid credentials. Rotate any password previously saved in
`server.properties`; it must not be reused. The image contains only a placeholder,
but the runtime properties file and Docker container environment contain the
password, so restrict host, Docker, volume-backup, and Jenkins access.

Both local and Jenkins deployments use a fixed **17 GiB heap**, **19 GiB RAM
limit**, and **23 GiB combined RAM-plus-swap limit**, allowing up to **4 GiB of
host swap**. The host must have swap enabled and Docker swap-limit support.
Exhausting these limits may trigger an out-of-memory kill. Monitor usage with
`docker stats` and host swap usage with `swapon --show`; heavy swapping can worsen
lag, and other services can grow beyond their current usage, so the remaining
host RAM and swap are not guaranteed.

### JVM tuning

Both deployment paths enable the image's
[`USE_AIKAR_FLAGS`](https://docker-minecraft-server.readthedocs.io/en/latest/configuration/jvm-options/#enable-aikars-flags)
G1GC preset on Java 17. The image adjusts its garbage-collection settings for the
17 GiB heap (above the preset's 12 GiB threshold). Heap sizing stays controlled by
`MEMORY`; do not add duplicate `-Xms`/`-Xmx` arguments or combine this preset with
MeowIce's flags or another garbage collector.

The November 3 hardware check of `node004` reported an Intel Core i7-4790
(4 cores/8 threads) and about 23 GiB usable RAM, rather than the expected
OptiPlex 3090 configuration. The 19 GiB container limit leaves roughly
4 GiB for the host, with 2 GiB inside the container for non-heap allocations.
GC thread counts remain JVM-managed rather than hardcoded to a CPU model.
This is a tuning baseline, not a guarantee of improved tick times; monitor
tick times and container memory during exploration and with players online.
If native/non-heap usage approaches the container limit, reduce the heap or
increase the limit while preserving host headroom.

Apply the change with your normal Jenkins deployment or
`docker compose up -d --no-build --wait --wait-timeout 900` for an existing local
image. This recreates the container without deleting the world volume.

The pipeline checks out the repository, validates prerequisites, builds a local
image tagged with the Jenkins build number, and deploys it using
`docker compose up -d`. It waits up to 15 minutes for server health and prints
logs if deployment fails. No registry or registry credentials are needed.
Environment variables from Jenkins override `.env` values.

This Compose project is a single production server. Do not deploy separate
Jenkins jobs or branches to the same Docker host with this project name.
Deployments restart the server when its image changes; schedule them when players
can disconnect. Failed deployments are reported but are not automatically rolled
back. Old images are retained; manage disk usage on the production host.

## Client configuration

[`client-config/config/`](./client-config/config/) mirrors the server's
bundled common configs. Each player
should close Minecraft, back up their instance `config` folder, copy the
contents of `client-config/config/` into it (overwrite), remove
`alexsmobs-1.22.9.jar` and `weather2-1.20.1-2.8.3.jar` from their `mods` folder,
then restart.

See the [client import instructions](./client-config/README.md). Extract the
client config ZIP into the instance directory, merging `config/`, `kubejs/`,
`mods/`, and `resourcepacks/`; it includes Quark Oddities and the Butcher texture
refresh, not a complete launcher-importable modpack.
Do not delete other configs or mods. `kubejs/assets/` contains missing English
tooltip, enchantment-description, and block-name text; KubeJS loads it
automatically, so these text fixes need no resource pack enabled. The separate
Butcher texture refresh must be enabled in **Options > Resource Packs**.
`kubejs/client_scripts/item_stat_tooltips.js` adds generated gray stat lines to
every item, read from the item's own data:
- breakable items (tools, weapons, armor, shields, bows, …): durability (hidden in
  F3+H advanced mode, where vanilla already shows it), armor and toughness,
  mining level and speed, enchantability, and repair material;
- all other items: food hunger/saturation, fuel value (items smelted), block
  hardness, blast resistance, and light level, and stack size, so every item
  shows at least one line. Enchanted books also show Enchantment Descriptions text.

It was checked against all 11,935 registered items on node004: every item
receives at least one line, with no errors.
To reproduce the ZIP from the repository:

```sh
(cd client-config && zip -r ../minecraft-client-config.zip README.md config kubejs mods resourcepacks -x '*/.DS_Store')
```

## Persistent data and operations

The named Docker volume **`minecraft-forge-data`** stores the world, server
properties, Forge installation, and mod configuration independently of the
Jenkins workspace and container image.

```sh
# Gracefully stop the server without deleting its data.
docker compose stop

# Remove the container/network but keep the world.
docker compose down

# Inspect status and recent logs.
docker compose ps
docker compose logs --tail 200 minecraft
```

**Do not run `docker compose down -v` unless you intend to delete the world.**
Back up the named volume while the server is stopped for a consistent backup.
Do not prune volumes that contain server data.

### Bundled loot compatibility datapack

The server-only [`loot-compat` datapack](./server-config/new-world/datapacks/loot-compat/)
fixes Dungeon's Delight 1.3.1 spawner drops with Farmer's Delight 1.3.4.
Both normal and rotten spawner modifiers require `lootTable`, not the older
`table` field. The pack preserves the original conditions and loot table:
8-12 Stained Scrap, with the original Fortune bonus.

The Dockerfile copies the pack to `/config/new-world/datapacks/`, which is synced
to `/data/new-world/datapacks/` at startup. For a live deployment, copy the pack
into that world directory and run `reload` from the server console to discover it.
If it is not enabled automatically, run `datapack enable "file/loot-compat" last`.
No restart is needed. Keep the pack enabled and edit the repository copy rather
than the volume copy. Clients do not need the pack.
Validate with `python3 -m unittest discover -s tests -p 'test_loot_compat.py'`.

### Butcher's Delight texture refresh and recipe compatibility

The client [resource pack](./client-config/resourcepacks/butchers-delight-refresh/)
contains **258 original pixel-art textures** for Butcher's Delight 2.1.0 and
Butcher's Delight Foods 1.0.3: meat cuts, cleaver, hooks, hides, carcasses,
partial carcasses, roasting equipment and drying frames. Icons are 16x16;
model-bound textures retain their original UV dimensions (for example 64x32)
to preserve existing block models. No mod artwork or models are redistributed.
It also corrects Foods' mislabeled llama loin and raw sheep loin/rack names.

Copy the resource-pack folder to the client's `resourcepacks/` directory, or
install the client config overlay above. Enable **Butcher's Delight Refresh**
in **Options > Resource Packs**, above packs that override the same textures.
Use F3+T after updating an enabled pack. This does not change item IDs, food
stats, models, animations, or butchering mechanics. A server datapack cannot
deliver textures; every player needs the resource pack. Automatic server
resource-pack download is not configured: that needs a publicly hosted ZIP URL.

The separate server-only
[`butchers-delight-compat` datapack](./server-config/new-world/datapacks/butchers-delight-compat/)
adds compatibility without replacing existing recipes:

- Foods already supplies all six Forge raw/cooked beef, pork and mutton tags,
  including goat/llama as mutton. Those existing memberships are preserved;
  Delight recipes that accept these tags already accept the matching cuts.
- Bridges `forge:meat_uncooked` into `forge:raw_meat` and adds the cooked species
  and `forge:meat_cooked` to `forge:cooked_meat`. All additions use `replace: false`.
- Adds the Butcher cleaver to the Forge and Farmer's Delight knife tags so it
  can use the cutting board. Other features that consult these tags may also
  recognize it as a knife; knives are **not** made into Butcher cleavers.
- Adds **15 cooked cutting recipes**: cooked beef cuts become beef patties,
  pork cuts become cooked bacon, and sheep/goat/llama cuts become cooked mutton
  chops. Yields equal the original raw cut's meat yield times Farmer's Delight's
  two slices per vanilla meat item, with the same bone count/chance.
  For example, cooked pork loin gives 6 cooked bacon and a 50% chance of a bone.
  Existing raw cutting, smelting, smoking and campfire recipes remain unchanged.
  Raw cuts can already be cut into vanilla meat, then sliced into Delight items.

This supports installed Delight recipes through shared tags and Farmer's
Delight ingredients; recipes with hard-coded special meats (for example hoglin
or End-specific dishes) are intentionally not broadened to unrelated animals.
Requires the installed Butcher's Delight, Foods, and Farmer's Delight mods.
The resource pack and datapack can be used independently.

The existing Dockerfile automatically includes the datapack. For an existing
world, also copy it to that world's `datapacks/butchers-delight-compat/` directory
(the default deployment uses `/data/new-world/datapacks/`), run `reload` and check
`datapack list enabled`. If necessary, run
`datapack enable "file/butchers-delight-compat" last`. Check server reload logs
for recipe/tag errors and JEI for the new cooked cutting recipes.
Clients do not need the datapack; singleplayer users can copy it into
`saves/<world>/datapacks/`.

Rebuild the repository pack files with
`python3 tools/build_butchers_packs.py` (requires Pillow). The builder reads
asset names, dimensions, model UVs and original recipe metadata from the
installed JARs, but draws all artwork from scratch. To write a contact sheet,
add `--preview /path/to/preview.png`.
Validate with `python3 -m unittest discover -s tests -p 'test_butchers_packs.py'`
(also requires Pillow). Static tests cover every texture path, UV dimensions,
raw/cooked and partial-stage differences, additive tag cycles, all 15 exact
recipe yields and installed ingredient/output models. An in-game check is
still needed to judge the rendered appearance and confirm server reload.

### Bundled modpack fixes datapack and KubeJS script

The server-only [`modpack-fixes` datapack](./server-config/new-world/datapacks/modpack-fixes/)
is deployed and enabled the same way as `loot-compat`:

- **Bone meal from bones:** Legionary replaces `minecraft:bone_meal` with a
  forgotten-bone recipe. `serverfixes:bone_meal_from_bone` restores
  1 bone → 3 bone meal; Legionary's recipe still works.
- **Mutant More crash:** Mutant More's wandering-trader mixin searches for
  `#mutantmore:on_suspicious_entrance_maps` and builds a map using a
  client-only decoration type, crashing the server. The tag is replaced with an
  empty list, so the search finds nothing and the map is never created.
- **Sons of Sins organs from blades:** a Farmer's Delight `add_loot_table`
  global loot modifier rolls Sons of Sins' per-mob slicing tables (or a random
  heart, muscle, or ribs) when a **player** kills a non-player mob with an item
  in `#serverfixes:tools/organ_slicers`: Forge/Farmer's Delight knives, Dungeons
  Delight and Butcher's Delight cleavers, Nether's Delight machetes, and the
  Graveyard, Alex's Caves, Fangs & Claws, Unusual End, and SCP daggers/knives.
  Sons of Sins' own slicers, skeletons, flesh creatures, and ether ghosts are
  excluded to avoid double drops. Knives are deliberately not added to
  `sons_of_sins:is_slicer`, which would also remove hit cooldowns and fill
  bottles with blood. This depends on Farmer's Delight's
  `generateFDChestLoot = true`, which enables its loot modifiers.
- **Graveyard corrupted illagers:** the corrupted evoker, vindicator, and pillager
  keep Graveyard's corruption drop and also roll the vanilla illager table
  (Dungeons & Taverns' versions for pillager/vindicator). The evoker also rolls
  Illager Invasion's Sorcerer loot and the vindicator its Basher loot. The
  evoker therefore always drops a Totem of Undying, like a vanilla evoker.
- **Alex's Mobs / vanilla spawn balance:** 91 `forge:add_spawns` biome
  modifiers under `serverfixes:spawn_balance/<namespace>/<biome>` bring the
  passive pools (`creature`, `water_creature`, `water_ambient`, `ambient`) of
  overworld biomes to roughly 50/50 Alex's Mobs vs vanilla spawn weight (every
  adjusted pool lands within 40-60%). Backported Animal Variants counts as
  vanilla; other mods' mobs are not counted. Together with the lowered weights in
  `amc.json` (see config overrides), they work as follows:
  - Where one side dominates, its weight is matched by extra copies of the other
    side's existing mobs.
  - Where a side is missing, mobs are borrowed from a similar biome. For example,
    windswept hills/stony peaks gain bald eagles and gelada monkeys, rivers gain
    plains livestock, and beaches/shores gain cod.
  - End biomes have no vanilla animals, so vanilla placeholders (cow, pig,
    chicken, bat) are added. They cannot spawn on end stone, which roughly halves
    Alex's Mobs End spawns.
  - Hostile pools (Alex's Mobs is about 4%) and the Nether and other dimensions
    are untouched. So are ocean `creature` pools, Devil's Hole pupfish (limited
    to rare chunks), the deep dark, lush-cave pools, and river squid.
  - Each biome is referenced through an optional (`required: false`) biome tag,
    so removing a biome mod does not break the pack.
  - Mob caps are per category, so the total number of mobs is unchanged.
  - Biome modifiers load only at startup, so this part needs a **server
    restart** rather than `reload`; it then applies to existing chunks too.

[`server-config/kubejs/startup_scripts/htn_extra_totems.js`](./server-config/kubejs/startup_scripts/htn_extra_totems.js)
is copied to `/config/kubejs/` and synced into `/data/kubejs/`. It applies
Hardcore Totem Nerf's post-totem penalties to totems that bypass its vanilla
hook: the seven More Totems totems, Fangs & Claws' Totem of Frost, and
Unusual End's (Linked) Void Totem. HTN's pre-use cooldown still blocks More
Totems, but cannot block Totem of Frost or the Void Totem. Startup scripts load
only at boot, so restart the server after changing it. Clients do not need it.

Validate with `python3 -m unittest discover -s tests -p 'test_modpack_fixes.py'`.

### Supplementaries lunch basket food compatibility

The bundled [`lunch-basket-compat` add-on](./tools/lunch-basket-compat/) and
[`food registry script`](./server-config/kubejs/server_scripts/lunch_basket_foods.js)
allow every registered edible item, including hidden items, in lunch baskets.
Foods added by future mods are picked up automatically on tag reload. Whole
cakes, pies, Farmer's Delight feasts and their subclasses, the pack's custom
Oceanic/Ender's/My Nether's Delight cakes and pies, Supplementaries pancakes,
and Display Delight plated foods are also accepted. Optional food/cake/feast/pie
tags cover additional integrations. A new mod's non-edible placeable meal may
need its block class or food tag added to this integration.

This patches Supplementaries' shared insertion predicate, so inventory clicks,
placed baskets and automation agree. Container nesting restrictions remain;
non-food items retain Supplementaries' existing rules. Foods keep their nutrition,
effects, serving sizes and bowl/bottle returns. Whole cakes and feasts are
**storage-compatible**, not directly edible from the basket: take them out and
place/serve them normally.

Install `mods/lunch-basket-compat-1.20.1-1.0.0.jar` on **both server and clients**
(included in the client overlay), then restart both. Tags synchronize from the
server; the client's copy of the registry script also supports singleplayer.
On server startup the script tests every food-tag item against the actual basket
predicate, logs the validated count, and reports an error listing any rejected
items (or an empty food tag). Check this validation message after deployment.
The add-on targets the installed Supplementaries **1.20-3.1.44** and Forge 1.20.1;
review the patch before upgrading Supplementaries. Rebuild both identical JARs
and synchronize the singleplayer script with
`python3 tools/lunch-basket-compat/build.py`. No Java compilation is needed.

Validate with `python3 -m unittest discover -s tests -p 'test_lunch_basket_compat.py'`.
The registry-script fixture requires Node.js. To also execute the installed
Supplementaries predicate before and after the patch, set `JAVA` to a JDK's
`java` executable and `LUNCH_BASKET_TEST_CLASSPATH` to a colon-separated list of
Nashorn Core and ASM (`asm`, `asm-tree`, `asm-commons`, `asm-util`) JARs.

### Bundled mod config overrides

Files in [`server-config/config/`](./server-config/config/) are copied into the
image at `/config/config/` and synced over `/data/config/` on **every start**.
They override edits made directly in the volume; change them in the repo and
redeploy. Other mod configs stay persistent in the volume.

| File | Change | Reason |
| --- | --- | --- |
| `vanillabackport-common.toml` | `has_zombie_horses = false` | Zombie Horse Spawn already adds natural zombie horses |
| `quark-common.toml` | `Expanded Item Interactions = false` | Duplicates Puzzles Lib/Easy Shulker Boxes container item interactions |
| `quark-common.toml` | `Shulker Tooltips = false` | Duplicates Easy Shulker Boxes tooltips |
| `quark-common.toml` | `Horses Swim = false` | Duplicates Horses Can Swim |
| `quark-common.toml` | `Totem Of Holding = true` | Explicitly selected death-recovery totem; Backrooms random retention remains disabled |
| `quark-common.toml` | `Automatic Tool Restock = false`, `Inventory Sorting = false` | Selected inventory profile |
| `quark-common.toml` | `Quick Armor Swapping = true` | Sneak-right-click armor stands to exchange equipped armor |
| `quark-common.toml` | `Villagers Use Simple Harvest = false` | Leave villager farming to Smarter Farmers; player harvesting stays enabled |
| `thirst/item_settings.toml` | 103 explicit drink IDs and 165 food IDs | Add verified drinks, soups, cups, fruit, and moist foods from the installed pack |
| `thirst/common.toml`, `thirst/keyword.toml` | Preserve current balance; keyword matching off | Match client gameplay settings without matching decorative food-display items |
| `mbackrooms/Mbackrooms-Config-Common.toml` | `partialLootKeeping = false` | Backrooms otherwise saves about 30% of inventory even outside its dimensions |
| `chunky/config.json` | `updateInterval = 60` | Pregeneration progress logs once a minute instead of every second |
| `amc.json` | 36 Alex's Mobs spawn weights lowered (e.g. gazelle 40→20, elephant 30→15, tiger 30→21, kangaroo 25→12); all other settings are the live server's values | AM animals outweighed vanilla animals in savanna, jungle, cherry grove, swamp, beach, and ocean pools; works with the `modpack-fixes` spawn-balance modifiers. The full file is synced, so make AM config edits here, not in the volume |

Quark common settings must match on clients; use the client package below.

The November 4 overrides were seeded from the running server's configs, not
regenerated defaults. Existing Quark overlap protections, zombie-horse
exclusion, and sand/snow tuning are preserved.

The subsequent Quark feature review selected **86 enabled / 78 disabled** across
all **164 feature toggles**. Both server and client copies contain the same
profile. Category-wide switches and internal settings are unchanged. Matrix
Enchanting is disabled by choice, not because its separate station conflicts
with Easy Magic. Quick Armor Swapping is enabled: it exchanges armor with an
armor stand and is distinct from Better Inventory's armor-pack swap.

Runtime validation checked all 164 modules. Two selected-true features remain
automatically suppressed by Quark's anti-overlap rules: Automatic Recipe Unlock
with NERB, and Map Washing with Supplementaries. Their `Ignore Anti Overlap`
options stay `false`; the 86/78 totals describe selected toggles, not 86 active
modules. The three Quark block IDs found in the pre-rollout terrain palettes
(`limestone`, `shale`, and `monster_box`) remain registered after the change.

Disabled world features are Chorus Vegetation, Glimmering Weald, New Stone
Types, and Spiral Spires. This changes future generation, not existing terrain.
Many building palettes and a few automation/mob features are also disabled;
consult `quark-common.toml` for the complete selected profile. Disabled content
can lose recipes/behavior even if its registry entries and existing blocks
remain. Back up saves before applying the profile.

Totem of Holding requires the separate **Quark Oddities 1.20.1** marker add-on.
The [Dockerfile](./Dockerfile) downloads its exact published Modrinth artifact
with SHA-256 verification; the client overlay includes the same JAR. All other
Oddities features remain disabled. The add-on itself contains no gameplay code;
it unlocks the implementations already in Quark. Its mandatory Quark dependency
is satisfied by the installed Quark 4.0-462.

Thirst now has **103 drinks and 165 foods**, with identical server and client
item settings. The November 4 expansion adds 44 drinks and 101 foods without
changing the previous entries. The November 7 pass adds 52 more IDs: milk
buckets, Cold Sweat's filled waterskin (`6/8`), Doggy Talents soy milk and sake,
Farmer's Respite strong hot cocoa, the remaining Mekanism Delight shakes, and
additional soups, curries, salads, fruit, and jellies across the Delight mods.
`miners_delight:water_cup` was removed because it is not drinkable. Every
configured ID was checked against node004's live item registry using
`clear @a <item> 0`, which does not remove items.

Cold Sweat's own Thirst integration requires Thirst 3.x, so the waterskin is
configured manually; pouring it over yourself may also hydrate. Mekanism
Delight items registered only by Mekanism Generators, Evolved Mekanism, or
Mekanism Extras (none installed) are excluded.

Coverage includes suspicious stew, Bumblezone bee soup and royal jelly, hot
cocoa, all 23 SCP Ultimate drinks, Miner's Delight soups and cups (including
My Nether's Delight integration cups), My Nether's Delight soups and dried
ghast with milk, Unusual End, Biomes We've Gone fruit/juice/soups, Delightful,
Alex's Delight, Dungeons Delight, Backrooms food/drinks, Ender's Delight,
Alex's Caves, and Abnormals Delight drinks.

New soups use hydration/quenching `4/5`; cups use half their bowl's values,
rounded up. Fruit uses `1/2` or `2/3`, melon slices `4/5`, juices/milkshakes
`8/13`, teas `10/14`, and water/cocoa/potions `6/8`. Water and milk cups use
`3/4`. Existing stronger teas and other previous values remain unchanged.
SCP drink effects, including harmful ones, are not removed by hydration support.
Dry baked goods, decorative food displays, and placeable fluid buckets are not
automatically included; keyword matching stays off.

Unusual End's brewed potions use `minecraft:potion`, already configured at
`6/8`; its separate `unusualend:warped_potion` is now explicit. Splash/lingering
potions are not drinks. Mekanism Delight's `dt_drink` and `fissile_fuel_drink`
are absent from the live registry: their registration requires the uninstalled
`mekanismgenerators` mod. Do not add these invalid IDs unless that dependency is
installed and their registration is verified again. Its available antimatter
and robit stews are included. Ender's Delight's unused `_wood` stew IDs are
also absent and excluded.

Restart the server after changing item settings: Thirst builds its hydration
lookup tables during startup, so a datapack reload is not sufficient. Players
should import the matching client config and restart for consistent tooltips
and singleplayer behavior. These checks verify configuration and registry IDs,
not an automated in-game consumption test.

`keepInventory` must remain `false` in the active world; it is a world gamerule,
not a property set by these files. Totem of Holding is now deliberately enabled
for death-drop recovery, with its existing PvP and collection rules unchanged.
This intentionally replaces the earlier loose-drop-only preference; it does not
keep a random subset of inventory on respawn. Backrooms' loot-retention feature is disabled
entirely, not merely set to a zero random percentage (tagged items could otherwise
still be retained). Test main inventory, armor, offhand, and Better Inventory
storage after respawning; modded storage is not covered by the gamerule alone.

Before a rollout, gracefully stop the server and back up the volume. Rebuild and
redeploy to include these files in the image. For a live config-only rollout,
copy the same overrides into both `/data/config/` and `/config/config/` in the
existing container, then start it again. The latter is the startup sync source;
the former is persistent volume data. A future image must also be rebuilt from
this repository so it carries the same overrides.

Validate TOML syntax, client/server parity, hydration entries, and intended
gameplay/particle limits with Python 3.11 or newer:

```sh
python3 -m unittest discover -s tests -v
```

### Weather2 removal and fresh worlds

Weather2 `2.8.3` was removed on November 4 after a local Spark profile showed
storm biome checks synchronously waiting for chunks, consuming roughly 48-70%
of server-thread wall time during lag windows. The previous workload caps did
not prevent these stalls. Its server and client config overlays were removed too.
Players should remove the Weather2 JAR from their clients. CoroUtil remains
required by What Are They Up To and Zombie Awareness. Storms of the Wild is a
separate mod and remains installed.

When regenerating a world, stop the server cleanly first and back up the entire
directory named by `level-name` in the active `/data/server.properties`, including
player data and all modded dimensions. Do not assume it is named `world`.
Move the old save out of that path before restarting; an empty `level-seed`
generates a random seed. This resets inventories, advancements, and world progress.
Keep the old save outside the active world directory so it can be restored.
Never delete the Docker data volume to reset a world.

After startup, verify the new seed, container health, and tick times. Target
20 TPS with mean tick time below 50 ms; an idle snapshot does not prove performance
under exploration or multiplayer load.

The game port **TCP 25565** and Simple Voice Chat port **UDP 24454** are published
on all host interfaces. RCON **TCP 25575**
is published only on `RCON_BIND_IP`. Online authentication remains enabled.
Allow both player-facing ports through your host firewall and configure router forwarding
if needed. RCON grants administrative control and is unencrypted: restrict it to
trusted LAN/VPN clients using Docker-aware firewall rules and never forward it
publicly through your router. A LAN bind alone is not a firewall rule.

After deployment, check memory limits and test authenticated RCON:

```sh
docker inspect "$(docker compose ps -q minecraft)" \
  --format 'Memory={{.HostConfig.Memory}} MemorySwap={{.HostConfig.MemorySwap}}'
docker compose exec -T minecraft rcon-cli list
docker stats --no-stream
```

Both memory values should be **20401094656** bytes (19 GiB). The RCON command
should return the player list without displaying the password. Also test from
your trusted remote RCON client at `192.168.1.208:25575` (or your configured IP)
to verify host network/firewall access.
