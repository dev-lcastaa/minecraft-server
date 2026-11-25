# Inventory and carcass compatibility: implementation and verification

## Deliverables

- Server add-on: `mods/inventory-carcass-compat-1.20.1-1.0.0.jar`
- Client overlay: `client-config/mods/inventory-carcass-compat-1.20.1-1.0.0.jar`
- Server startup script: `server-config/kubejs/startup_scripts/inventory_carcass_stacks.js`
- Identical client startup script: `client-config/kubejs/startup_scripts/inventory_carcass_stacks.js`
- Coremod: `tools/inventory-carcass-compat/coremods/inventory_carcass.js`
- Permission-event helper: `tools/inventory-carcass-compat/src/net/serverfixes/inventory/CarryOnPermissionProbeEvent.java`
- Reproducible builder: `tools/inventory-carcass-compat/build.py`
- Python tests: `tests/test_inventory_carcass_compat.py`
- Actual installed-bytecode harness: `tools/inventory-carcass-compat/BytecodeTest.java`
- This documentation: `tools/inventory-carcass-compat/VERIFICATION.md`

The add-on uses Forge's `lowcodefml` loader, like the existing compatibility
add-ons; there is no missing Java `@Mod` entry point. It packages only its own
event helper, metadata and coremod, never Minecraft/Forge compile stubs.
Server and client add-on jars are byte-identical. No original mod jar is modified.

The targeted versions are Carry On 2.1.2.7, Better Inventory 2.1.0 and Butcher's
Delight's actual metadata version `1.20.12.1.0` (filename version 2.1.0).
Dependencies are pinned to those bytecode versions. The supported platform is
Minecraft 1.20.1, Forge 47 and KubeJS 2001.6.5. A mod upgrade requires reviewing
the targets rather than silently assuming the transforms still apply.

## Root causes and changes

### Carcass pickup duplication

The installed Carry On `CommonEvents.lambda$onBlockClick$0` posts a
`BlockEvent.BreakEvent` to check pickup permissions. Butcher's Delight's
global break listeners interpret that permission probe as a real harvest,
spawning feathers, leather and other products while Carry On still preserves
the original carcass.

The coremod substitutes an otherwise ordinary subclass,
`CarryOnPermissionProbeEvent`, for that one event allocation. The event still
passes through Forge's event bus, and the original cancellation check is
unchanged. All 11 installed Butcher's Delight break callbacks return early
only for the marked permission probe. Ordinary block breaking and harvesting
remain unchanged. No blocks or entities are blacklisted from pickup.

The installed callbacks include the differently capitalized
`HookedgoatblockDestroyedByPlayerProcedure` and
`HookedllamablockDestroyedByPlayerProcedure`; the coverage test scans the
actual jar for every reference to `BlockEvent$BreakEvent`.

### Carcass stack sizes

The mirrored startup script changes the maximum stack size to 16 for all
87 currently installed `butchersdelight:` item IDs beginning with `dead`,
`hooked`, `hoked` or `roasted`: raw item carcasses, placed forms, skins/processing
stages, hanging forms and the roasted carcass forms. Tools, racks, roasters and
unrelated mods are untouched. It changes registry properties, not serialized
inventory contents or existing stack counts.

### Better Inventory ghost pages

The installed `SlotItemHandler` does not override `Slot.setChanged`
(`m_6654_`). Its inherited notification points at an empty container.
Partial shift-click and other in-place stack mutations therefore change the
visible stack without updating the backpack's serialized contents. Reopening
or another handler reading the host can restore the old count.

The added override forwards notification through the existing modifiable
handler's `setStackInSlot(index, getStackInSlot(index))`. In particular, the
installed `BackpackMenu$PageView` maps the visible slot to its current page,
then invokes `ComponentBackedHandler.setStackInSlot`, whose native
`onContentsChanged` writes the host NBT and calls its existing listener.
Read-only handlers are left alone.

Existing mutation paths that already use `setStackInSlot` or `extractItem`
remain unchanged. The missing notification is repaired; there is no
periodic inventory sweep, clearing, guessed deduplication or new client-to-server
inventory packet.

## Mutation and synchronization coverage

The executable harness reads the original installed class bytes and runs the
Nashorn/ASM transformer, not a rewritten Java equivalent of the patched slot.
It checks:

- Original partial-shift-click failure: visible count 25, reopened stored count 40.
- Patched partial shift-click saves 25 through the actual `PageView`.
- Native slot set, partial remove and full remove.
- Direct mutable-stack shrink and grow **followed by the normal `setChanged` notification**.
- Clearing a slot with `ItemStack.EMPTY`, and clearing through the actual
  `TabStorage.clearContent` (`m_6211_`) loop. The loop executes against a fixture
  bridge to the installed component-backed setter; it is not a complete
  vanilla player/container simulation.
- Nonmutating extraction simulation.
- Multiple handlers refreshing from changed authoritative host contents.
- Unrelated page contents, including a count of 1000 at slot 359, surviving
  mutation, clear and NBT save/reload.
- Read-only handler notifications neither failing nor mutating data.
- The actual installed `PlayerLoadout.lambda$pageStore$5` setting `dirty`.
- Structural verification of native `SyncService.syncNow` sending
  `serializeNBT` output and `applyClientSync` using `deserializeNBT`.

The hook cannot intercept arbitrary external code that mutates an `ItemStack`
and never calls a setter or dirty notification. The known native menu paths
perform that notification; unconditional interception would require a broader
ItemStack/inventory design change and is not claimed here.

The harness uses small Minecraft NBT/item and Forge event-bus fixtures. It
executes installed inventory methods and transformed callbacks, but it does
not execute a real Forge event bus, actual network transport, vanilla container
prediction or a complete game server. Native synchronization remains
server-authoritative by design; full multiplayer synchronization is not claimed
as integration-tested.

## Existing serialized inventories

The add-on does not replace or alter Better Inventory's migration algorithms.
The harness round-trips a legacy serialized 180-slot `StoredItems` inventory
with an entry in **every** slot and verifies the installed migration:

```text
newSlot = (oldSlot / 45) * 72 + oldSlot % 45
new size = 360
```

Every item identity and count survives; migration is idempotent and the
installed `ComponentBackedHandler.refresh` persists the migrated host. Another
NBT round-trip retains all 180 entries. Modern inventory contents and other
pages are also checked.

No inventories are cleared and no old saved entries are discarded by this
add-on. Already-stale saved entries cannot safely be identified as phantom
items versus legitimate possessions, so there is deliberately no retrospective
deletion or recovery command. Malformed NBT, duplicate slot entries and
out-of-range records retain the original mod's behavior and are outside the
tested lossless, valid-inventory migration claim.

## Exact commands

Run from the repository root. The bytecode test is skipped without
`INVENTORY_CARCASS_TEST_CLASSPATH`; set it explicitly to avoid that skip.
`JAVA` optionally selects the Java executable; otherwise `java` on PATH is used.
`PYTHONDONTWRITEBYTECODE=1` prevents touching tracked or preexisting Python caches.

```bash
python3 tools/inventory-carcass-compat/build.py

INVENTORY_CARCASS_TEST_CLASSPATH='/path/to/test-deps/*' \
PYTHONDONTWRITEBYTECODE=1 \
python3 -m unittest discover -s tests -p test_inventory_carcass_compat.py -v

PYTHONDONTWRITEBYTECODE=1 \
python3 -m unittest discover -s tests -p test_config_overrides.py -v

sha256sum mods/inventory-carcass-compat-1.20.1-1.0.0.jar \
  client-config/mods/inventory-carcass-compat-1.20.1-1.0.0.jar
```

The classpath requires Nashorn 15.4 and ASM 9.7.1 jars. Replace
`/path/to/test-deps` with the directory containing those jars. The documented
local compatibility run passes all
four tests with **zero skips**; the related configuration suite passes 12 tests.
Build and bytecode-fixture work directories use per-run UUIDs inside
`tools/inventory-carcass-compat/` and are removed in `finally` blocks. They do not
write outside the repository, and concurrent bytecode tests do not share
generated classes.

The builder prefers `--release 17`. The reduced local Java 25 installation
lacks `ct.sym` and rejects that option, so only that specific failure falls
back to `-source 17 -target 17`. The packaged helper is constructor-only,
uses compile-time Minecraft/Forge stubs and has asserted classfile major
version 61 (Java 17). This is not a general guarantee that arbitrary Java 25
source can be compiled safely for Java 17.

## Remaining in-game checks

No deployment was performed. Install the mirrored add-on and startup script
with the existing mods, and restart both server and client; startup item
modification is not a `/reload` change. On a backed-up test world:

1. Pick up, place and repeat for chicken, cow, goat, llama, sheep, pig and hoglin
   carcasses/processing stages. Check no extra feathers/leather/products appear.
   Genuine breaking and butchering should still produce their normal results.
2. Verify locked/permission-denied pickup remains denied and allowed pickup
   retains its normal UX, block-entity NBT and placement.
3. Try stacking raw, skinned, hanging and processed carcasses to 16.
4. Partially shift-click stacks out of hand-held and placed backpacks; shrink,
   grow, clear and remove stacks; switch all pages, close/reopen, relog and
   restart. Check counts against a second client's view and saved NBT.
5. Load a legitimate older backpack and verify every page and item metadata
   after native migration. Do not clear inventories to test or “repair” them.

These are remaining verification steps, not checks already performed.
