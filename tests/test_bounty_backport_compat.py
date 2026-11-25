import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/bounty-backport-compat"
PACK = ROOT / "server-config/new-world/datapacks/bounty-backport-compat"
spec = importlib.util.spec_from_file_location("bounty_build", SOURCE / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class BountyBackportCompatTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.models, cls.classes, cls.mods, cls.blocks = build.resources()
        cls.coverage = json.loads((SOURCE / "coverage.json").read_text())

    def test_built_and_client_resources_match_sources_and_datapack(self):
        server = ROOT / "mods" / build.JAR_NAME
        self.assertEqual(server.read_bytes(), (ROOT / "client-config/mods" / build.JAR_NAME).read_bytes())
        with ZipFile(server) as jar:
            expected = {"pack.mcmeta": (SOURCE / "pack.mcmeta").read_bytes()}
            expected.update({p.relative_to(SOURCE).as_posix(): p.read_bytes()
                             for folder in ("META-INF", "coremods")
                             for p in (SOURCE / folder).rglob("*") if p.is_file()})
            expected.update({p.relative_to(SOURCE).as_posix(): p.read_bytes()
                             for p in (SOURCE / "data").rglob("*.json")})
            self.assertEqual(set(jar.namelist()), set(expected))
            for name, content in expected.items():
                self.assertEqual(jar.read(name), content, name)
                if name.startswith("data/") or name == "pack.mcmeta":
                    self.assertEqual((PACK / name).read_bytes(), content, name)
        for folder in ("startup_scripts", "server_scripts"):
            script = Path(f"kubejs/{folder}/bounty_backport_compat.js")
            self.assertEqual((ROOT / "server-config" / script).read_bytes(),
                             (ROOT / "client-config" / script).read_bytes())
        config = Path("config/bountiful/bountiful.json")
        self.assertEqual((ROOT / "server-config" / config).read_bytes(),
                         (ROOT / "client-config" / config).read_bytes())

    def test_every_native_decree_has_additive_obtainable_balanced_pools(self):
        proofs = build.acquisition(self.data, self.models, self.mods, self.classes)
        self.assertEqual(set(self.coverage["decrees"]), set(build.DECREES))
        for decree in build.DECREES:
            native = self.data[f"data/bountiful/bounty_decrees/bountiful/{decree}.json"][1]
            addon = json.loads((SOURCE / f"data/bounty_backport_compat/bounty_decrees/compat/{decree}.json").read_text())
            self.assertFalse(addon["replace"])
            self.assertTrue(native["objectives"])
            self.assertTrue(native["rewards"])
            self.assertIn("compat_supplies_objs", addon["objectives"])
            self.assertIn("compat_supplies_rews", addon["rewards"])
            for suffix in ("objs", "rews"):
                pool = json.loads((SOURCE / f"data/bounty_backport_compat/bounty_pools/compat/compat_{decree}_{suffix}.json").read_text())
                self.assertFalse(pool["replace"])
                self.assertGreater(len(pool["content"]), 0, decree)
                for value in pool["content"].values():
                    identity = value["content"]
                    self.assertTrue(identity in self.models or identity.startswith("minecraft:"), identity)
                    self.assertIn(identity, proofs, identity)
                    self.assertFalse(build.FORBIDDEN.search(identity.split(":")[1]), identity)
                    self.assertLessEqual(value["amount"]["max"], 32 if identity in build.EGGS else 8)
                    self.assertGreater(value["unitWorth"], 0)
                    self.assertLess(value["weightMult"], 1)
        self.assertEqual(set(self.coverage["selected_items"]), set().union(*[
            {v["content"] for v in json.loads(p.read_text())["content"].values()}
            for p in (SOURCE / "data/bounty_backport_compat/bounty_pools/compat").glob("*_rews.json")
        ]))

    def test_acquisition_rejects_disabled_features_and_dormant_dependencies(self):
        self.assertNotIn("incubation", self.mods)
        self.assertFalse(build.conditions_met({"conditions": [
            {"type": "quark:flag", "flag": "leaf_carpet"}
        ]}, self.mods))
        self.assertFalse(build.conditions_met({"conditions": [
            {"type": "forge:mod_loaded", "modid": "this_mod_is_not_installed"}
        ]}, self.mods))
        self.assertFalse(build.conditions_met({"conditions": [
            {"type": "forge:item_exists", "tag": "forge:batter"}
        ]}, self.mods))
        selected = self.coverage["selected_items"]
        self.assertFalse("quark:acacia_leaf_carpet" in selected)
        self.assertFalse("quark:crab_leg" in selected)
        self.assertIn("quark:acacia_leaf_carpet", self.coverage["excluded_recipe_items"])
        self.assertEqual(self.coverage["excluded_recipe_items"]["quark:acacia_leaf_carpet"]["code"], "CONFIG_DISABLED")
        premium = build.entry("ad_astra:netherite_space_boots", "armorer", True)
        self.assertEqual(premium["amount"]["max"], 1)
        self.assertGreaterEqual(premium["unitWorth"], 80000)
        self.assertGreaterEqual(premium["repRequired"], 20)
        self.assertGreaterEqual(build.base_worth("minecraft:netherite_block"), 9 * 64000)

    def test_every_proven_candidate_is_covered_or_defensibly_excluded(self):
        proofs = build.acquisition(self.data, self.models, self.mods, self.classes)
        covered = set(self.coverage["selected_items"])
        excluded = {i for i, reason in self.coverage["excluded_recipe_items"].items() if reason["proven"]}
        self.assertFalse(covered & excluded)
        self.assertEqual(set(proofs), covered | excluded)
        self.assertEqual(self.coverage["audit"]["unaccounted_proven_candidates"], [])
        self.assertGreater(len(covered), 1000)
        self.assertNotIn("DIVERSITY_CAP", self.coverage["audit"]["exclusion_categories"])
        self.assertNotIn("UNCLASSIFIED", self.coverage["audit"]["exclusion_categories"])
        self.assertNotIn("UNVERIFIED_FUNCTIONAL_BLOCK", self.coverage["audit"]["exclusion_categories"])
        self.assertEqual(set(self.coverage["candidate_sources"]),
                         covered | set(self.coverage["excluded_recipe_items"]))
        self.assertTrue(set(self.models) <= set(self.coverage["candidate_sources"]))
        pools = {p.stem: {v["content"] for v in json.loads(p.read_text())["content"].values()}
                 for p in (SOURCE / "data/bounty_backport_compat/bounty_pools/compat").glob("*_objs.json")}
        for identity, decrees in self.coverage["applicable_decrees"].items():
            self.assertTrue(decrees, identity)
            for decree in decrees:
                self.assertTrue(identity in pools[f"compat_{decree}_objs"] or
                                identity in pools["compat_supplies_objs"], identity)
        for identity in ("butchersdelightfoods:beeftenderloin", "butchersdelightfoods:porkribs"):
            self.assertIn(identity, covered)
        self.assertTrue(any(i in self.blocks and i not in {"carpet", "candle"} for i in covered))
        for identity in ("minecraft:spider_eye", "minecraft:ender_eye", "minecraft:brain_coral",
                         "alexsmobs:cockroach_wing_fragment"):
            self.assertIn(identity, covered)
        for identity in build.EGGS:
            self.assertIn("farmer", self.coverage["applicable_decrees"][identity])
            self.assertIn("butcher", self.coverage["applicable_decrees"][identity])

    def test_unknown_conditions_and_nested_quark_flags_are_not_false_proofs(self):
        unknown = {"type": "unsupported:condition"}
        self.assertIsNone(build.conditions_met(unknown, set(), True))
        self.assertIsNone(build.conditions_met({"type": "forge:not", "value": unknown}, set(), True))
        self.assertIsNone(build.conditions_met({"type": "quark:flag", "flag": "unresolved"}, self.mods, True))
        self.assertTrue(build.conditions_met({"type": "quark:flag", "flag": "apple_crate"}, self.mods, True))
        self.assertFalse(build.conditions_met({"type": "quark:flag", "flag": "leaf_carpet"}, self.mods, True))
        self.assertNotIn("minecraft:apple", self.data["__disabled_bounty_items__"][1])
        self.assertNotIn("minecraft:acacia_planks", self.data["__disabled_bounty_items__"][1])
        self.assertEqual(build.input_references({"tag": {"Purity": 100}}), [])

    def test_long_acquisition_chains_require_real_loot_roots_and_positive_outputs(self):
        data = {}
        models = {}
        for i in range(12):
            identity = f"fixture:step_{i}"
            models[identity] = {}
            data[f"data/fixture/recipes/{i:02}.json"] = ("fixture.jar", {
                "type": "minecraft:crafting_shapeless",
                "ingredients": [{"item": "minecraft:cobblestone" if i == 0 else f"fixture:step_{i-1}"}],
                "result": {"item": identity},
            })
        models["fixture:unplaced"] = {}
        table = {"pools": [{"entries": [{"type": "minecraft:item", "name": "fixture:unplaced"}]}]}
        data["data/fixture/loot_tables/blocks/unplaced.json"] = ("fixture.jar", table)
        models["fixture:non_survival_root"] = {}
        data["data/fixture/recipes/unobtainable_input.json"] = ("fixture.jar", {
            "type": "minecraft:crafting_shapeless", "ingredients": [{"item": "minecraft:budding_amethyst"}],
            "result": {"item": "fixture:non_survival_root"},
        })
        proofs = build.acquisition(data, models, set(), {})
        self.assertEqual(proofs["fixture:step_11"]["depth"], 12)
        self.assertNotIn("fixture:unplaced", proofs)
        self.assertNotIn("fixture:non_survival_root", proofs)
        data["__acquisition_world_refs__"] = ("fixture", {"fixture:unplaced": "placed structure fixture"})
        self.assertIn("fixture:unplaced", build.acquisition(data, models, set(), {}))
        table["pools"][0]["functions"] = [{"function": "minecraft:set_count", "count": 0}]
        self.assertNotIn("fixture:unplaced", build.acquisition(data, models, set(), {}))
        self.assertEqual(build.recipe_outputs({"result": {"item": "fixture:empty", "count": 0}}), [])

    def test_supply_values_follow_recipe_multiplicity_without_decorative_name_inflation(self):
        data = {
            "data/fixture/recipes/iron_block.json": ("fixture.jar", {
                "type": "minecraft:crafting_shaped", "pattern": ["###", "###", "###"],
                "key": {"#": {"item": "minecraft:iron_ingot"}}, "result": {"item": "fixture:iron_block"},
            }),
            "data/fixture/recipes/gold_carpet.json": ("fixture.jar", {
                "type": "minecraft:crafting_shapeless", "ingredients": [{"item": "minecraft:wheat"}],
                "result": {"item": "fixture:gold_carpet", "count": 3},
            }),
        }
        proofs = build.acquisition(data, {"fixture:iron_block": {}, "fixture:gold_carpet": {}}, set(), {})
        build.value_proofs(proofs, data)
        self.assertEqual(proofs["fixture:iron_block"]["unitWorth"], 9000)
        self.assertEqual(proofs["fixture:gold_carpet"]["unitWorth"], 20)
        proofs["fixture:gold_carpet"]["block_item"] = True
        value = build.entry("fixture:gold_carpet", "supplies", False, proofs["fixture:gold_carpet"])
        self.assertEqual(value["unitWorth"], 20)
        self.assertEqual(value["amount"]["max"], 32)
        self.assertEqual(build.base_worth(build.EGGS[1]), build.base_worth(build.EGGS[0]))
        self.assertEqual(build.base_worth("forge:gems/diamond"), 10000)
        self.assertEqual(build.base_worth("forge:ingots/iron"), 1000)
        self.assertEqual(build.base_worth("minecraft:planks"), 30)

    def test_actual_bountiful_bytecode_vetoes_stateful_supplies_without_changing_native(self):
        classpath = next((os.environ.get(name) for name in
                          ("BOUNTY_TEST_CLASSPATH", "MOB_LOOT_TEST_CLASSPATH", "CRAVINGS_TEST_CLASSPATH",
                           "LUNCH_BASKET_TEST_CLASSPATH") if os.environ.get(name)), None)
        if not classpath:
            self.skipTest("Set BOUNTY_TEST_CLASSPATH to existing Nashorn/ASM dependencies")
        classpath = os.pathsep.join(str(path) for part in classpath.split(os.pathsep)
                                   for path in (sorted(Path(part[:-1]).glob("*.jar"))
                                                if part.endswith("*") else [part]))
        java = shutil.which("java")
        scratch = SOURCE / f".safety-test-{os.getpid()}"
        scratch.mkdir()
        stubs = {
            "net/minecraftforge/coremod/api/ASMAPI.java": "package net.minecraftforge.coremod.api; public class ASMAPI {public static String mapMethod(String v){return v;}}",
            "net/minecraft/resources/ResourceLocation.java": "package net.minecraft.resources; public class ResourceLocation {String v;public ResourceLocation(String s){v=s;}public String toString(){return v;}}",
            "net/minecraft/server/MinecraftServer.java": "package net.minecraft.server; public class MinecraftServer {}",
            "net/minecraft/world/level/block/Block.java": "package net.minecraft.world.level.block; public class Block {}",
            "net/minecraft/world/level/block/EntityBlock.java": "package net.minecraft.world.level.block; public interface EntityBlock {}",
            "net/minecraft/world/item/Item.java": "package net.minecraft.world.item; public class Item {}",
            "net/minecraft/world/item/BlockItem.java": "package net.minecraft.world.item; public class BlockItem extends Item {net.minecraft.world.level.block.Block b;public BlockItem(net.minecraft.world.level.block.Block v){b=v;}public net.minecraft.world.level.block.Block m_40614_(){return b;}}",
            "net/minecraftforge/registries/IForgeRegistry.java": "package net.minecraftforge.registries; public interface IForgeRegistry<T> {T getValue(net.minecraft.resources.ResourceLocation id);}",
            "net/minecraftforge/registries/ForgeRegistries.java": """package net.minecraftforge.registries;
public class ForgeRegistries {
public static java.util.Map<String,net.minecraft.world.item.Item> VALUES=new java.util.HashMap<>();
public static IForgeRegistry<net.minecraft.world.item.Item> ITEMS=id->VALUES.get(id.toString());
}""",
        }
        fixture = r"""
import java.nio.file.*;
import java.util.zip.*;
import java.util.*;
import javax.script.*;
import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.objectweb.asm.tree.analysis.*;
import org.openjdk.nashorn.api.scripting.NashornScriptEngineFactory;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.item.*;
import net.minecraft.world.level.block.*;
import net.minecraftforge.registries.ForgeRegistries;
public class SafetyTest implements Opcodes {
  static final String OWNER="io/ejekta/bountiful/data/PoolEntry";
  static MethodNode transform(ScriptEngine engine, MethodNode method) throws Exception {
    engine.put("method",method);
    return (MethodNode)engine.eval("initializeCoreMod().supply_state_safety.transformer(method)");
  }
  static class Loader extends ClassLoader {
    Class<?> define(byte[] b){return defineClass(OWNER.replace('/','.'),b,0,b.length);}
  }
  public static class Stateful extends Block implements EntityBlock {}
  public static void main(String[] args) throws Exception {
    ScriptEngine engine=new NashornScriptEngineFactory().getScriptEngine();
    engine.eval(Files.readString(Path.of(args[0])));
    ClassNode actual=new ClassNode();
    try(var jar=new ZipFile(args[1])){new ClassReader(jar.getInputStream(jar.getEntry(OWNER+".class"))).accept(actual,0);}
    MethodNode nativeMethod=actual.methods.stream().filter(m->m.name.equals("isValid")).findFirst().orElseThrow();
    AbstractInsnNode[] old=nativeMethod.instructions.toArray();
    MethodNode transformed=transform(engine,nativeMethod);
    new Analyzer<BasicValue>(new BasicVerifier()).analyze(OWNER,transformed);
    AbstractInsnNode[] after=transformed.instructions.toArray();
    if(after.length<=old.length) throw new AssertionError("No safety guard");
    for(int i=0;i<old.length;i++) if(old[i]!=after[after.length-old.length+i]) throw new AssertionError("Native body changed");
    ClassNode fake=new ClassNode(); fake.version=V17;fake.access=ACC_PUBLIC;fake.name=OWNER;fake.superName="java/lang/Object";
    for(String name:List.of("id","content"))fake.fields.add(new FieldNode(ACC_PUBLIC,name,"Ljava/lang/String;",null,null));
    fake.fields.add(new FieldNode(ACC_PUBLIC,"type","Lnet/minecraft/resources/ResourceLocation;",null,null));
    MethodNode ctor=new MethodNode(ACC_PUBLIC,"<init>","()V",null,null);
    ctor.instructions.add(new VarInsnNode(ALOAD,0));ctor.instructions.add(new MethodInsnNode(INVOKESPECIAL,"java/lang/Object","<init>","()V",false));
    ctor.instructions.add(new InsnNode(RETURN));ctor.maxLocals=1;ctor.maxStack=1;fake.methods.add(ctor);
    MethodNode valid=new MethodNode(ACC_PUBLIC,"isValid","(Lnet/minecraft/server/MinecraftServer;)Z",null,null);
    valid.instructions.add(new InsnNode(ICONST_1));valid.instructions.add(new InsnNode(IRETURN));valid.maxLocals=2;valid.maxStack=1;
    fake.methods.add(transform(engine,valid));
    ClassWriter writer=new ClassWriter(ClassWriter.COMPUTE_MAXS);fake.accept(writer);
    Class<?> c=new Loader().define(writer.toByteArray());Object entry=c.getConstructor().newInstance();
    c.getField("id").set(entry,"compat_supplies_objs.bounty_backport_compat_test");c.getField("type").set(entry,new ResourceLocation("bountiful:item"));
    var method=c.getMethod("isValid",MinecraftServer.class);var server=new MinecraftServer();
    ForgeRegistries.VALUES.put("test:station",new BlockItem(new Stateful()));
    ForgeRegistries.VALUES.put("test:brick",new BlockItem(new Block()));
    ForgeRegistries.VALUES.put("test:food",new Item());
    c.getField("content").set(entry,"test:station");
    if((boolean)method.invoke(entry,server))throw new AssertionError("Stateful station admitted");
    c.getField("id").set(entry,"compat_other_addon_station");
    if(!(boolean)method.invoke(entry,server))throw new AssertionError("Native bounty changed");
    c.getField("id").set(entry,"compat_supplies_objs.bounty_backport_compat_test");
    for(String id:List.of("test:brick","test:food")){
      c.getField("content").set(entry,id);if(!(boolean)method.invoke(entry,server))throw new AssertionError(id);
    }
    c.getField("content").set(entry,"test:station");c.getField("type").set(entry,new ResourceLocation("bountiful:entity"));
    if(!(boolean)method.invoke(entry,server))throw new AssertionError("Entity objective changed");
    System.out.println("Actual method verified; station veto, ordinary supplies and native preservation executed");
  }
}
"""
        try:
            paths = []
            for name, text in {**stubs, "SafetyTest.java": fixture}.items():
                path = scratch / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
                paths.append(str(path))
            compiled = subprocess.run([java, "-m", "jdk.compiler/com.sun.tools.javac.Main",
                                       "-source", "17", "-target", "17", "-cp", classpath,
                                       "-d", str(scratch), *paths], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            result = subprocess.run([java, "-cp", str(scratch) + os.pathsep + classpath,
                                     "SafetyTest", str(SOURCE / "coremods/supply_safety.js"),
                                     str(next((ROOT / "mods").glob("Bountiful-*.jar")))],
                                    cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("station veto", result.stdout)
        finally:
            shutil.rmtree(scratch)

    def test_all_actual_raw_egg_recipes_preserve_outputs_and_use_verified_tag(self):
        count = 0
        for name, jar, original in build.recipes(self.data, self.mods):
            replacement = build.replace_egg(original)
            if replacement == original:
                continue
            generated = json.loads((SOURCE / name).read_text())
            self.assertEqual(generated, replacement, name)
            for key in build.OUTPUT_KEYS:
                if key in original:
                    self.assertEqual(generated[key], original[key], name)
            count += 1
        self.assertEqual(count, len(self.coverage["egg_recipes"]))
        self.assertGreaterEqual(count, 12)
        raw_tag = json.loads((SOURCE / "data/forge/tags/items/eggs.json").read_text())
        self.assertFalse(raw_tag["replace"])
        self.assertEqual(set(raw_tag["values"]), set(build.EGGS))
        for suffix, kind in (("cooking_pot", "farmersdelight:cooking"),
                             ("monster_pot", "dungeonsdelight:monster_cooking")):
            recipe = json.loads((SOURCE / f"data/bounty_backport_compat/recipes/egg_in_{suffix}.json").read_text())
            self.assertEqual(recipe["type"], kind)
            self.assertEqual(recipe["ingredients"], [{"tag": "forge:eggs"}])
            self.assertEqual(recipe["result"]["item"], "farmersdelight:fried_egg")
        for suffix in ("fried_egg", "fried_egg_from_campfire_cooking", "fried_egg_from_smoking"):
            recipe = json.loads((SOURCE / f"data/farmersdelight/recipes/{suffix}.json").read_text())
            self.assertEqual(recipe["ingredient"], {"tag": "forge:eggs"})
        # Copper pots actually read the FD COOKING registry, not an invented recipe type.
        copper = self.classes["com/sammy/minersdelight/content/block/copper_pot/CopperPotBlockEntity.class"][1]
        self.assertIn(b"vectorwing/farmersdelight/common/registry/ModRecipeTypes", copper)
        self.assertIn(b"COOKING", copper)
        self.assertIn(b"CookingPotRecipe", copper)

    def test_real_animal_classes_and_consumed_tags_preserve_vanilla_interactions(self):
        for animal, base in (("chicken", "Chicken"), ("cow", "Cow"), ("pig", "Pig")):
            for temperature in ("Cold", "Warm"):
                name = f"net/akaciobahno/backported_animal_variants/entity/custom/{temperature}{base}.class"
                bytecode = self.classes[name][1]
                self.assertIn(f"net/minecraft/world/entity/animal/{base}".encode(), bytecode)
                self.assertIn(b"m_142606_", bytecode)  # Native variant offspring.
                spawn = self.data[f"data/backported_animal_variants/forge/biome_modifier/spawn_{temperature.lower()}_{animal}.json"][1]
                self.assertEqual(spawn["spawners"][0]["type"],
                                 f"backported_animal_variants:{temperature.lower()}_{animal}")
        butchering = self.classes["net/mcreator/butchersdelight/procedures/CustomDropsProcedure.class"][1]
        for animal in ("Cow", "Pig", "Chicken"):
            self.assertIn(f"net/minecraft/world/entity/animal/{animal}".encode(), butchering)
        for name, (_, tag) in self.data.items():
            if "/tags/items/" not in name:
                continue
            if "minecraft:egg" not in [v if isinstance(v, str) else v.get("id") for v in tag.get("values", [])]:
                continue
            addon = json.loads((SOURCE / name).read_text())
            self.assertTrue(set(build.EGGS[1:]).issubset(addon["values"]), name)
            self.assertFalse(addon["replace"])
        egg_registry = self.classes["net/akaciobahno/backported_animal_variants/item/ModItems.class"][1]
        self.assertIn(b"blue_egg", egg_registry)
        self.assertIn(b"brown_egg", egg_registry)

    def test_kills_have_actual_hostile_registry_classes_and_forge_spawns(self):
        self.assertEqual(set(self.coverage["kill_entities"]),
                         {"fangs_n_claws:goblin", "fangs_n_claws:dart_goblin"})
        for entity in ("goblin", "dart_goblin"):
            spawn = json.loads((SOURCE / f"data/bounty_backport_compat/forge/biome_modifier/{entity}_spawns.json").read_text())
            self.assertEqual(spawn["type"], "forge:add_spawns")
            self.assertEqual(spawn["spawners"]["type"], f"fangs_n_claws:{entity}")
            self.assertLessEqual(spawn["spawners"]["maxCount"], 2)
        placement = self.classes["net/raptorzizi/fangs_n_claws/setup/SpawnSetup.class"][1]
        self.assertIn(b"onSpawnPlacements", placement)
        self.assertIn(b"GOBLIN", placement)
        self.assertIn(b"DART_GOBLIN", placement)

    def test_runtime_scripts_append_trades_and_preserve_recipe_outputs(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js required for KubeJS event fixture")
        fixture = r"""
const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
let tradeHandler, recipes, loaded;
const vanilla = {unchanged: true}, offers = [vanilla];
const listings = [];
function Listing(...args) { listings.push(args); }
class EntityBlock {}
class BlockItem {constructor(block){this.block=block}getBlock(){return this.block}}
const raw = new Set(['minecraft:egg','backported_animal_variants:blue_egg','backported_animal_variants:brown_egg']);
let missingItem = false;
let stationItem = false;
const warnings = [];
const pools = Array.from({length:27},(_,i)=>({
  getId:()=>`compat_${i}`, getItems:()=>({isEmpty:()=>false,forEach:f=>f({
    id:'compat_fixture.bounty_backport_compat_'+i,
    getContent:()=>i===26?'fangs_n_claws:goblin':'farmersdelight:fried_egg',
    getType:()=>i===26?'bountiful:entity':'bountiful:item'
  })})
}));
pools.push({getId:()=> 'compat_other_addon_pool',getItems:()=>({
  forEach:f=>f({id:'compat_other_addon_station',getContent:()=>{throw Error('foreign entry inspected')}})
})});
const context = {
  ForgeEvents: {onEvent: (kind, f) => {assert.equal(kind, 'net.minecraftforge.event.village.VillagerTradesEvent'); tradeHandler=f;}},
  Java: {loadClass: n => {
    if(n.endsWith('ForgeRegistries')) return {VILLAGER_PROFESSIONS:{getKey:value=>value},ENTITY_TYPES:{containsKey:()=>true}};
    if(n.endsWith('BountifulContent')) return {INSTANCE:{getPools:()=>pools}};
    if(n.endsWith('ResourceLocation')) return function(value){this.value=value};
    if(n.endsWith('BlockItem')) return BlockItem;
    if(n.endsWith('EntityBlock')) return EntityBlock;
    assert(n.endsWith('BasicItemListing')); return Listing;
  }},
  Item: {of: value => value.includes('16x ')||value==='minecraft:emerald'?value:{
    isEmpty:()=>missingItem,item:stationItem?new BlockItem(new EntityBlock()):{}
  }},
  ServerEvents: {recipes: f => recipes=f, loaded: f => loaded=f},
  Ingredient: {of: value => {assert.equal(value, '#forge:eggs'); return {itemIds:{contains: value => raw.has(value)}};}},
  console: {info: () => {}, warn:v=>warnings.push(v)}
};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), context);
vm.runInNewContext(fs.readFileSync(process.argv[2], 'utf8'), context);
const event = type => ({getType:()=>type,getTrades:()=>({get:level=>{assert.equal(level,2);return {add:v=>offers.push(v)}}})});
tradeHandler(event('minecraft:butcher')); assert.equal(offers.length,1);
tradeHandler(event('minecraft:farmer')); assert.equal(offers[0],vanilla); assert.equal(offers.length,4);
assert.equal(listings.length,3);
assert.equal(new Set(listings.map(v=>v[0])).size,3);
listings.forEach(args=>{assert(args[0].startsWith('16x '));assert.equal(args[1],'minecraft:emerald');assert.equal(args[2],12)});
recipes({replaceInput:(filter,old,replacement)=>{assert.equal(filter.input,'minecraft:egg');assert.equal(old,'minecraft:egg');assert.equal(replacement,'#forge:eggs')}});
loaded({});
stationItem=true; loaded({}); assert.equal(warnings.length,1); stationItem=false;
missingItem=true; assert.throws(()=>loaded({}),/Unregistered bounty item/); missingItem=false;
raw.delete('backported_animal_variants:blue_egg'); assert.throws(()=>loaded({}),/Missing raw egg/);
"""
        subprocess.run([node, "-e", fixture,
                        str(ROOT / "server-config/kubejs/startup_scripts/bounty_backport_compat.js"),
                        str(ROOT / "server-config/kubejs/server_scripts/bounty_backport_compat.js")],
                       check=True, cwd=ROOT, capture_output=True, text=True)

    def test_actual_bountiful_serializers_accept_pools_decrees_and_merge(self):
        java = shutil.which("java")
        if not java:
            self.skipTest("Java is required for actual Bountiful serializer validation")
        jars = [next((ROOT / "mods").glob(pattern)) for pattern in
                ("Bountiful-*.jar", "kotlinforforge-*.jar")]
        classpath = os.pathsep.join(map(str, jars))
        fixture = r"""
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;
import io.ejekta.bountiful.data.*;
import kotlinx.serialization.*;
import kotlinx.serialization.json.*;
import kotlinx.serialization.modules.*;
import kotlinx.serialization.encoding.*;
import kotlinx.serialization.descriptors.*;
import net.minecraft.resources.ResourceLocation;
public class BountySchemaTest {
  public static void main(String[] args) throws Exception {
    var module = new SerializersModuleBuilder();
    module.contextual(kotlin.jvm.internal.Reflection.getOrCreateKotlinClass(ResourceLocation.class), new KSerializer<ResourceLocation>() {
      public SerialDescriptor getDescriptor() {return kotlinx.serialization.internal.StringSerializer.INSTANCE.getDescriptor();}
      public ResourceLocation deserialize(Decoder d) {return new ResourceLocation(d.decodeString());}
      public void serialize(Encoder e, ResourceLocation r) {e.encodeString(r.toString());}
    });
    Json json = JsonKt.Json(Json.Default, builder -> {
      builder.setSerializersModule(module.build()); return kotlin.Unit.INSTANCE;
    });
    int pools=0, entries=0, decrees=0;
    try (var paths = Files.walk(Path.of(args[0])); var builtin = new ZipFile(args[1])) {
      for (Path p : paths.filter(p -> p.toString().endsWith(".json")).toList()) {
        String text=Files.readString(p);
        if(p.toString().contains("bounty_pools")) {
          Pool pool=json.decodeFromString(Pool.Companion.serializer(),text);
          if(pool.getReplace() || pool.getContent().isEmpty()) throw new AssertionError(p);
          for(var obj:pool.getContent().values()) {
            PoolEntry entry=json.decodeFromString(PoolEntry.Companion.serializer(),obj.toString());
            if(entry.getContent().isBlank() || entry.getAmount().getMin()<1 ||
               entry.getAmount().getMax()<entry.getAmount().getMin() ||
               entry.getUnitWorth()<=0 || entry.getWeightMult()<=0) throw new AssertionError(p);
            entries++;
          }
          pools++;
        } else if(p.toString().contains("bounty_decrees")) {
          Decree addon=json.decodeFromString(Decree.Companion.serializer(),text);
          String name=p.getFileName().toString();
          String original=new String(builtin.getInputStream(builtin.getEntry("data/bountiful/bounty_decrees/bountiful/"+name)).readAllBytes());
          Decree nativeDecree=json.decodeFromString(Decree.Companion.serializer(),original);
          Decree merged=nativeDecree.merged(addon);
          if(!merged.getObjectives().containsAll(nativeDecree.getObjectives()) ||
             !merged.getObjectives().containsAll(addon.getObjectives()) ||
             !merged.getRewards().containsAll(nativeDecree.getRewards()) ||
             !merged.getRewards().containsAll(addon.getRewards())) throw new AssertionError(name);
          decrees++;
        }
      }
    }
    if(decrees!=12 || pools!=27 || entries<1000) throw new AssertionError(decrees+" "+pools+" "+entries);
    System.out.println("Actual Bountiful serializers and additive merge verified: "+decrees+" decrees, "+pools+" pools, "+entries+" entries");
  }
}
"""
        scratch = SOURCE / f".schema-test-{os.getpid()}"
        scratch.mkdir()
        try:
            stubs = {
                "net/minecraft/resources/ResourceLocation.java": """
package net.minecraft.resources;
public class ResourceLocation {
  private String namespace, path;
  public ResourceLocation(String n,String p){namespace=n;path=p;}
  public ResourceLocation(String v){this(v.contains(":")?v.split(":")[0]:"bountiful",v.contains(":")?v.split(":")[1]:v);}
  public String toString(){return namespace+":"+path;}
}
""",
                "net/minecraft/nbt/CompoundTag.java": "package net.minecraft.nbt; public class CompoundTag {}",
                "net/minecraft/ChatFormatting.java": "package net.minecraft; public enum ChatFormatting {WHITE,AQUA,YELLOW,LIGHT_PURPLE,GOLD}",
            }
            stub_paths = []
            for name, content in stubs.items():
                path = scratch / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
                stub_paths.append(str(path))
            compiled = subprocess.run([java, "-m", "jdk.compiler/com.sun.tools.javac.Main",
                                       "-source", "17", "-target", "17", "-d", str(scratch), *stub_paths],
                                      cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            classpath += os.pathsep + str(scratch)
            source = scratch / "BountySchemaTest.java"
            source.write_text(fixture)
            compiled = subprocess.run([java, "-m", "jdk.compiler/com.sun.tools.javac.Main",
                                       "-source", "17", "-target", "17", "-cp", classpath,
                                       "-d", str(scratch), str(source)],
                                      cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            result = subprocess.run([java, "--class-path", classpath, "BountySchemaTest",
                                     str(SOURCE / "data"), str(jars[0])],
                                    cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Actual Bountiful serializers", result.stdout)
        finally:
            shutil.rmtree(scratch)


if __name__ == "__main__":
    unittest.main()
