import dev.latvian.mods.rhino.Context;
import dev.latvian.mods.rhino.ScriptableObject;
import java.nio.file.Files;
import java.nio.file.Path;

public class LunarEventsCompatRhinoTest {
    public static void main(String[] args) throws Exception {
        Context context = Context.enter();
        ScriptableObject scope = context.initStandardObjects();
        context.evaluateString(scope, """
            var moon = 'lunar_events_compat:peaceful_moon';
            function Mob() {}
            function Enemy() {}
            Enemy.prototype = Object.create(Mob.prototype);
            function Zombie() {}
            Zombie.prototype = Object.create(Enemy.prototype);
            function Shulker() {}
            Shulker.prototype = Object.create(Enemy.prototype);
            function Ageable() {}
            Ageable.prototype = Object.create(Mob.prototype);
            function Golem() {}
            Golem.prototype = Object.create(Mob.prototype);
            function IronGolem() {}
            IronGolem.prototype = Object.create(Golem.prototype);
            function Other() {}
            var classes = {
              'dev.corgitaco.enhancedcelestials2core.EnhancedCelestials': {
                lunarForecastWorldData: function(level) {
                  var key = {location: function() { return moon; }};
                  var holder = {unwrapKey: function() {
                    return {isPresent: function() { return true; }, get: function() { return key; }};
                  }};
                  var forecast = {currentLunarEventHolder: function() { return holder; }};
                  return {isPresent: function() { return true; }, get: function() { return forecast; }};
                }
              },
              'net.minecraft.world.entity.monster.Zombie': Zombie,
              'net.minecraft.world.entity.monster.Enemy': Enemy,
              'net.minecraft.world.entity.Mob': Mob,
              'net.minecraft.world.entity.AgeableMob': Ageable,
              'net.minecraft.world.entity.monster.Shulker': Shulker,
              'net.minecraft.world.entity.OwnableEntity': Other,
              'net.minecraft.world.entity.NeutralMob': Other,
              'net.minecraft.world.entity.animal.AbstractGolem': Golem,
              'net.minecraft.world.entity.animal.IronGolem': IronGolem,
              'net.minecraft.world.entity.monster.RangedAttackMob': Other,
              'net.minecraft.world.entity.monster.Creeper': Other,
              'net.minecraft.world.entity.ai.attributes.Attributes': {
                MAX_HEALTH: 'max_health', ARMOR: 'armor', ARMOR_TOUGHNESS: 'armor_toughness',
                ATTACK_DAMAGE: 'attack_damage'
              },
              'net.minecraft.world.entity.ai.attributes.AttributeModifier': function(id, name, amount, op) {
                this.id = id; this.amount = amount; this.op = op;
              },
              'net.minecraft.world.entity.ai.attributes.AttributeModifier$Operation': {
                ADDITION: 'add', MULTIPLY_BASE: 'multiply_base'
              },
              'java.util.UUID': {fromString: function(id) { return id; }}
            };
            var Java = {loadClass: function(name) {
              if (!classes[name]) throw Error('Unexpected class: ' + name);
              return classes[name];
            }};
            var console = {warn: function(message) { throw Error(message); }};
            var handlers = {check: null, spawned: null, shulker: null, tick: null};
            var EntityEvents = {
              checkSpawn: function(callback) { handlers.check = callback; },
              spawned: function(id, callback) {
                if (callback) handlers.shulker = callback; else handlers.spawned = id;
              }
            };
            var ServerEvents = {tick: function(callback) { handlers.tick = callback; }};
            var nextId = 1;
            var level = {
              getDimension: function() { return 'minecraft:overworld'; },
              getGameTime: function() { return 1000; },
              getMaxLocalRawBrightness: function() { return 3; },
              mobs: [],
              getEntitiesOfClass: function() {
                var list = this.mobs;
                return {size: function() { return list.length; }, get: function(i) { return list[i]; }};
              }
            };
            function entity(kind, typeId) {
              var e = new kind();
              var tags = [];
              var attributes = {};
              e.id = nextId++;
              e.health = 20;
              e.baby = false;
              e.target = null;
              e.getId = function() { return this.id; };
              e.getEncodeId = function() { return typeId; };
              e.getTags = function() { return {contains: function(tag) { return tags.indexOf(tag) >= 0; }}; };
              e.addTag = function(tag) { tags.push(tag); };
              e.getAttribute = function(name) {
                if (!attributes[name]) attributes[name] = {mods: {},
                  getModifier: function(id) { return this.mods[id] || null; },
                  addPermanentModifier: function(m) { this.mods[m.id] = m; }};
                return attributes[name];
              };
              e.getMaxHealth = function() {
                var health = attributes.max_health;
                for (var id in (health ? health.mods : {})) return 40;
                return 20;
              };
              e.setHealth = function(value) { this.health = value; };
              e.setBaby = function(value) { this.baby = value; };
              e.isAlive = function() { return true; };
              e.isNoAi = function() { return false; };
              e.getAttributes = function() { return {hasAttribute: function() { return true; }}; };
              e.getTarget = function() { return this.target; };
              e.setTarget = function(target) { this.target = target; };
              e.canAttack = function() { return true; };
              e.distanceToSqr = function() { return 4; };
              e.blockPosition = function() { return null; };
              e.getLevel = function() { return level; };
              return e;
            }
            function check(e, type) {
              handlers.check({getEntity: function() { return e; }, getLevel: function() { return level; },
                getType: function() { return type; }});
            }
            function spawned(e) {
              var cancelled = false;
              handlers.spawned({getEntity: function() { return e; }, getLevel: function() { return level; },
                cancel: function() { cancelled = true; }});
              return cancelled;
            }
            """, "lunar-fixture-setup", 1, null);
        context.evaluateString(scope, Files.readString(Path.of(args[0])), args[0], 1, null);
        context.evaluateString(scope, """
            var phantom = entity(Enemy, 'minecraft:phantom');
            check(phantom, 'NATURAL');
            if (!spawned(phantom)) throw Error('Peaceful Moon did not block a natural hostile spawn');
            var spawnerZombie = entity(Zombie, 'minecraft:zombie');
            check(spawnerZombie, 'SPAWNER');
            if (spawned(spawnerZombie)) throw Error('Peaceful Moon blocked a spawner spawn');
            moon = 'enhancedcelestials2defaultlunarevents:blue_moon';
            level.getGameTime = function() { return 2000; };
            var pillager = entity(Enemy, 'minecraft:pillager');
            check(pillager, 'PATROL');
            if (!spawned(pillager)) throw Error('Blue Moon did not stay peaceful');

            moon = 'lunar_events_compat:horde_moon';
            level.getGameTime = function() { return 3000; };
            var zombie = entity(Zombie, 'minecraft:zombie');
            check(zombie, 'NATURAL');
            if (zombie.health !== 40 || zombie.getAttribute('armor').mods === null ||
                Object.keys(zombie.getAttribute('armor').mods).length !== 1) {
              throw Error('Horde Moon zombie was not buffed');
            }
            var ghoul = entity(Enemy, 'graveyard:ghoul');
            check(ghoul, 'NATURAL');
            if (ghoul.health !== 40) throw Error('Modded horde zombie was not buffed');

            moon = 'lunar_events_compat:baby_horde_moon';
            level.getGameTime = function() { return 4000; };
            var babies = 0;
            for (var i = 0; i < 40; i++) {
              var small = entity(Zombie, 'minecraft:zombie');
              check(small, 'NATURAL');
              if (small.baby) babies++;
            }
            if (babies < 20) throw Error('Baby Horde Moon produced too few babies: ' + babies);

            moon = 'lunar_events_compat:chaos_moon';
            level.getGameTime = function() { return 5000; };
            var player = entity(Other, 'minecraft:player');
            player.isCreative = function() { return false; };
            player.isSpectator = function() { return false; };
            player.getBoundingBox = function() { return {inflate: function() { return null; }}; };
            player.getUUID = function() { return 'player-uuid'; };
            var skeleton = entity(Enemy, 'minecraft:skeleton');
            var creeper = entity(Enemy, 'minecraft:creeper');
            var villageGolem = entity(IronGolem, 'minecraft:iron_golem');
            villageGolem.isPlayerCreated = function() { return true; };
            level.mobs = [skeleton, creeper, villageGolem];
            handlers.tick({getServer: function() { return {
              getTickCount: function() { return 80; },
              getPlayers: function() { return {size: function() { return 1; }, get: function() { return player; }}; }
            }; }});
            if (skeleton.target === null || creeper.target === null) throw Error('Chaos Moon mobs did not pick fights');
            if (skeleton.target === skeleton) throw Error('Chaos Moon mob targeted itself');
            if (villageGolem.target !== null) throw Error('Chaos Moon turned a player-built golem');
            """, "lunar-fixture-checks", 1, null);
        System.out.println("Rhino lunar events compat passed");
    }
}
