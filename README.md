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

The Docker build copies this directory into `/mods` in the image. On startup,
the base image copies the bundled mods into `/data/mods`. Old mod JARs are removed
before copying so deleted or upgraded mods do not linger in the persistent
volume. Do not manually install additional JARs in `/data/mods`; manage them in
the image instead. World data and mod configuration remain persistent.

Dreamshift `0.2.2-hotfix` and The Bumblezone `7.15.2` are exceptions to Git storage:
their large JARs are downloaded into `/mods` during the Docker build from pinned
Modrinth version URLs in [`Dockerfile`](./Dockerfile). Each download is verified
against its pinned SHA-256; a failed download or checksum mismatch fails the build.
Local copies may remain in `mods/`, but are ignored by Git and excluded from the
Docker build context. A clean checkout therefore contains **253 bundled JARs**;
the built image contains **255** including these downloads. Jenkins uses the same
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
client config ZIP into the instance directory, merging `config/` and `mods/`;
it includes Quark Oddities, not a complete launcher-importable modpack.
Do not delete other configs or mods.
To reproduce the ZIP from the repository:

```sh
(cd client-config && zip -r ../minecraft-client-config.zip README.md config mods -x '*/.DS_Store')
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
| `thirst/item_settings.toml` | 92 explicit drink IDs and 126 food IDs | Add verified drinks, soups, cups, fruit, and moist foods from the installed pack |
| `thirst/common.toml`, `thirst/keyword.toml` | Preserve current balance; keyword matching off | Match client gameplay settings without matching decorative food-display items |
| `mbackrooms/Mbackrooms-Config-Common.toml` | `partialLootKeeping = false` | Backrooms otherwise saves about 30% of inventory even outside its dimensions |
| `chunky/config.json` | `updateInterval = 60` | Pregeneration progress logs once a minute instead of every second |

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

Thirst now has **92 drinks and 126 foods**, with identical server and client
item settings. The November 4 expansion adds 44 drinks and 101 foods without
changing the previous entries. Every configured ID was checked against node004's
live item registry using `clear @a <item> 0`, which does not remove items.

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
