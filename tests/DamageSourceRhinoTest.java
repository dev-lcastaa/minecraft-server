import dev.latvian.mods.rhino.Context;
import dev.latvian.mods.rhino.ScriptableObject;
import dev.latvian.mods.rhino.util.RemapForJS;
import dev.latvian.mods.rhino.util.RemapPrefixForJS;
import java.nio.file.Files;
import java.nio.file.Path;

public class DamageSourceRhinoTest {
    public static final class DamageSource {
        private final Object actual;
        private final Object immediate;

        DamageSource(Object actual, Object immediate) {
            this.actual = actual;
            this.immediate = immediate;
        }

        @RemapForJS("getActual")
        public Object m_7639_() {
            return actual;
        }

        @RemapForJS("getImmediate")
        public Object m_7640_() {
            return immediate;
        }
    }

    public static final class Sources {
        public DamageSource create(Object actual, Object immediate) {
            return new DamageSource(actual, immediate);
        }
        public Server server() { return new Server(); }
    }

    // Same shape as KubeJS's MinecraftServerKJS: if vanilla overworld() is left
    // under its SRG name, the kjs$getOverworld bean property claims `overworld`.
    @RemapPrefixForJS("kjs$")
    public interface ServerKJS {
        default Object kjs$getOverworld() { return "overworld-level"; }
    }

    public static final class Server implements ServerKJS {
        public Object m_129783_() { return "overworld-level"; }
    }

    public static void main(String[] args) throws Exception {
        Context context = Context.enter();
        ScriptableObject scope = context.initStandardObjects();
        ScriptableObject.putProperty(scope, "sources",
            Context.javaToJS(context, new Sources(), scope), context);
        context.evaluateString(scope, """
            var global = {};
            function Player() {
              this.mainHandItem = {id: 'sons_of_sins:sickle_of_struggle'};
              this.inventory = {
                bottles: 1,
                find: function() { return this.bottles ? 0 : -1; },
                extractItem: function() { this.bottles--; }
              };
            }
            function ItemEntity(level, x, y, z, item) {
              this.item = item;
              this.getItem = function() { return this.item; };
            }
            var classes = {
              'net.minecraftforge.registries.ForgeRegistries': {
                ENTITY_TYPES: {getKey: function(type) { return type.id; }, getValues: function() {
                  return [{id: 'example:bat', create: function(level) {
                            if (level !== 'overworld-level') throw Error('wrong level');
                            return mob(false);
                          }},
                          {id: 'minecraft:skeleton', create: function() { return mob(true); }},
                          {id: 'example:boat', create: function() { return 'boat'; }}];
                }}
              },
              'net.minecraft.tags.TagKey': {
                create: function(registry, location) { return location.id; }
              },
              'net.minecraft.core.registries.Registries': {ENTITY_TYPE: 'entity'},
              'net.minecraft.resources.ResourceLocation': function(id) { this.id = id; },
              'net.minecraft.world.entity.MobType': {
                UNDEAD: 'undead', WATER: 'water', ARTHROPOD: 'arthropod', ILLAGER: 'illager'
              },
              'net.minecraft.world.entity.player.Player': Player,
              'net.minecraft.world.entity.LivingEntity': Object,
              'net.minecraft.world.entity.item.ItemEntity': ItemEntity,
              'net.mehvahdjukaar.supplementaries.common.items.loot.RandomArrowFunction': {}
            };
            var Java = {loadClass: function(name) {
              if (!classes[name]) throw Error('Unexpected class: ' + name);
              return classes[name];
            }};
            var Ingredient = {of: function(id) { return id; }};
            var Item = {of: function(id, nbt) { return {id: id, nbt: nbt}; }};
            var loadedCallback = null;
            var ServerEvents = {loaded: function(callback) { loadedCallback = callback; }};
            var logged = {info: [], warn: []};
            var console = {warn: function(m) { logged.warn.push(m); }, info: function(m) { logged.info.push(m); }};
            function mob(skeleton) {
              var type = {id: skeleton ? 'minecraft:skeleton' : 'example:bat',
                is: function(tag) { return !skeleton && tag === 'mob_loot_compat:blood_winged'; }};
              var klass = {
                getName: function() {
                  return skeleton ? 'net.minecraft.world.entity.monster.AbstractSkeleton' : 'example.Bat';
                },
                getInterfaces: function() { return []; },
                getSuperclass: function() { return null; }
              };
              return {level: {isClientSide: function() { return false; }}, x: 0, y: 0, z: 0,
                getClass: function() { return klass; }, getType: function() { return type; },
                getMobType: function() { return 'normal'; }};
            }
            function death(victim, source) {
              var items = [];
              var drops = {add: function(item) { items.push(item); },
                iterator: function() { return {hasNext: function() { return false; }}; }};
              global.mobLootCompatDrops({
                getEntity: function() { return victim; },
                getDrops: function() { return drops; },
                isRecentlyHit: function() { return false; },
                getSource: function() { return source; }
              });
              return items;
            }
            """, "rhino-fixture-setup", 1, null);
        context.evaluateString(scope, Files.readString(Path.of(args[0])), args[0], 1, null);
        context.evaluateString(scope, """
            var fire = sources.create(null, null);
            if (typeof fire.getActual !== 'function' || typeof fire.getImmediate !== 'function' ||
                typeof fire.getEntity !== 'undefined' || typeof fire.m_7639_ !== 'undefined') {
              throw Error('Rhino did not expose the expected KubeJS aliases');
            }
            if (death(mob(true), fire).length !== 0 || death(mob(false), fire).length !== 0) {
              throw Error('Environmental death unexpectedly produced blood');
            }
            var player = new Player();
            var drops = death(mob(false), sources.create(player, player));
            if (drops.length !== 1 || drops[0].item.id !== 'sons_of_sins:bottle_of_blood' ||
                drops[0].item.nbt !== '{originEntityCapaity:1.0d}' || player.inventory.bottles !== 0) {
              throw Error('Direct sickle kill did not produce the expected blood');
            }
            player = new Player();
            if (death(mob(false), sources.create(player, {})).length !== 0 ||
                player.inventory.bottles !== 1) {
              throw Error('Indirect kill extracted blood');
            }
            player = new Player();
            player.mainHandItem.id = 'farmersdelight:iron_knife';
            if (death(mob(false), sources.create(player, player)).length !== 0 ||
                player.inventory.bottles !== 1) {
              throw Error('Non-sickle kill extracted blood');
            }
            var server = sources.server();
            if (typeof server.overworld === 'function') throw Error('Fixture did not reproduce overworld shadowing');
            loadedCallback({server: server});
            if (logged.warn.length !== 0 || logged.info.length !== 1 ||
                !/"eligible":1(\\.0)?,"bloodless":1(\\.0)?,"missing":0(\\.0)?,"nonliving":1(\\.0)?,"failed":0(\\.0)?/.test(logged.info[0])) {
              throw Error('Registry audit failed: ' + JSON.stringify(logged));
            }
            """, "rhino-fixture-assertions", 1, null);
        System.out.println("Rhino remapped damage-source gameplay passed");
    }
}
