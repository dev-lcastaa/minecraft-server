package serverfixes.lunar;

import dev.corgitaco.enhancedcelestials2core.EnhancedCelestials;
import java.lang.ref.WeakReference;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.WeakHashMap;
import net.minecraft.world.entity.AgeableMob;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.NeutralMob;
import net.minecraft.world.entity.OwnableEntity;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.ai.attributes.Attribute;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.MeleeAttackGoal;
import net.minecraft.world.entity.ai.goal.RangedAttackGoal;
import net.minecraft.world.entity.ai.goal.RangedBowAttackGoal;
import net.minecraft.world.entity.ai.goal.RangedCrossbowAttackGoal;
import net.minecraft.world.entity.ai.goal.WrappedGoal;
import net.minecraft.world.entity.ai.memory.MemoryModuleType;
import net.minecraft.world.entity.ai.memory.MemoryStatus;
import net.minecraft.world.entity.animal.AbstractGolem;
import net.minecraft.world.entity.animal.IronGolem;
import net.minecraft.world.entity.monster.Enemy;
import net.minecraft.world.entity.monster.RangedAttackMob;
import net.minecraft.world.entity.monster.Shulker;
import net.minecraft.world.entity.monster.Zombie;
import net.minecraft.world.entity.npc.Npc;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.EntityJoinLevelEvent;
import net.minecraftforge.event.entity.living.LivingHurtEvent;
import net.minecraftforge.event.entity.living.MobSpawnEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/**
 * Server-side gameplay for lunar_events_compat moons that the Enhanced Celestials 2 datapack format cannot express.
 * Compiled against SRG-named Minecraft so every vanilla call is checked at build time.
 */
@Mod("lunar_events_compat")
public final class LunarEvents {
    static final String SHULKER_TAG = "lunar_events_compat.ender_moon_shulker";
    static final UUID HEALTH_ID = UUID.fromString("5d1c7a52-5f0e-4a8e-9a43-6f2b0c1e7a01");
    static final UUID ARMOR_ID = UUID.fromString("5d1c7a52-5f0e-4a8e-9a43-6f2b0c1e7a02");
    static final UUID TOUGHNESS_ID = UUID.fromString("5d1c7a52-5f0e-4a8e-9a43-6f2b0c1e7a03");
    static final Map<Level, String> MOONS = new WeakHashMap<>();
    static final List<WeakReference<Shulker>> SHULKERS = new ArrayList<>();

    public LunarEvents() {
        MinecraftForge.EVENT_BUS.register(this);
    }

    /** Current lunar event id or null; refreshed once a second per level. */
    public static String moon(Level level) {
        if (level == null || level.m_5776_()) return null;
        String id = MOONS.get(level);
        if (id == null) {
            id = lookup(level);
            MOONS.put(level, id);
        }
        return id.isEmpty() ? null : id;
    }

    static String lookup(Level level) {
        try {
            return EnhancedCelestials.lunarForecastWorldData(level)
                .flatMap(forecast -> forecast.currentLunarEventHolder().m_203543_())
                .map(key -> key.m_135782_().toString())
                .orElse("");
        } catch (RuntimeException e) {
            return "";
        }
    }

    static String typeId(Entity entity) {
        return String.valueOf(EntityType.m_20613_(entity.m_6095_()));
    }

    @SubscribeEvent
    public void onLevelTick(TickEvent.LevelTickEvent event) {
        Level level = event.level;
        if (event.phase != TickEvent.Phase.END || level.m_5776_()) return;
        long time = level.m_46467_();
        if (time % 20 == 0) MOONS.put(level, lookup(level));
        if (time % 80 == 0 && !SHULKERS.isEmpty() && !Rules.ENDER.equals(moon(level))) {
            SHULKERS.removeIf(ref -> {
                Shulker shulker = ref.get();
                if (shulker == null || shulker.m_213877_()) return true;
                if (shulker.m_9236_() != level) return false;
                shulker.m_146870_();
                return true;
            });
        }
    }

    @SubscribeEvent
    public void onFinalizeSpawn(MobSpawnEvent.FinalizeSpawn event) {
        Mob mob = event.getEntity();
        Level level = mob.m_9236_();
        String moon = moon(level);
        if (moon == null) return;
        String spawnType = event.getSpawnType().name();
        if (Rules.blocksPeacefulSpawn(moon, mob instanceof Enemy, spawnType)) {
            event.setSpawnCancelled(true);
            return;
        }
        if (Rules.buffsHorde(moon, mob instanceof Zombie || Rules.HORDE_ZOMBIES.contains(typeId(mob)), spawnType)) {
            buffHordeZombie(mob);
        } else if (Rules.makesBaby(moon, mob instanceof Enemy || mob instanceof AgeableMob, spawnType,
                mob.m_217043_().m_188500_())) {
            mob.m_6863_(true);
        } else if (mob instanceof Shulker shulker && Rules.ENDER.equals(moon) && spawnType.equals("NATURAL")) {
            if (Rules.blocksEnderShulker(moon, spawnType, level.m_46803_(mob.m_20183_()))) {
                event.setSpawnCancelled(true);
            } else {
                shulker.m_20049_(SHULKER_TAG);
                SHULKERS.add(new WeakReference<>(shulker));
            }
        }
    }

    static void buffHordeZombie(Mob mob) {
        addModifier(mob, Attributes.f_22276_, HEALTH_ID, "Horde Moon health", 1.0, AttributeModifier.Operation.MULTIPLY_BASE);
        addModifier(mob, Attributes.f_22284_, ARMOR_ID, "Horde Moon armor", 6.0, AttributeModifier.Operation.ADDITION);
        addModifier(mob, Attributes.f_22285_, TOUGHNESS_ID, "Horde Moon toughness", 2.0, AttributeModifier.Operation.ADDITION);
        mob.m_21153_(mob.m_21233_());
    }

    static void addModifier(Mob mob, Attribute attribute, UUID id, String name, double amount, AttributeModifier.Operation op) {
        AttributeInstance instance = mob.m_21051_(attribute);
        if (instance != null && instance.m_22111_(id) == null)
            instance.m_22125_(new AttributeModifier(id, name, amount, op));
    }

    @SubscribeEvent
    public void onJoin(EntityJoinLevelEvent event) {
        Level level = event.getLevel();
        if (level.m_5776_() || !(event.getEntity() instanceof Mob mob)) return;
        // Shulkers do not despawn, so Ender Moon shulkers leave with the moon even after a chunk reload.
        if (mob instanceof Shulker && mob.m_19880_().contains(SHULKER_TAG) && !Rules.ENDER.equals(moon(level))) {
            event.setCanceled(true);
            return;
        }
        if (!canBrawl(mob)) return;
        mob.f_21346_.m_25352_(0, new ChaosTargetGoal(mob));
        // Mobs with no attack of their own (most animals) get a simple melee so every mob can fight.
        if (mob instanceof PathfinderMob pathfinder && !hasOwnAttack(mob) && !brainDriven(mob))
            mob.f_21345_.m_25352_(0, new ChaosBrawlGoal(pathfinder));
    }

    // Victims hit back at whatever hurt them, even mobs that normally never retaliate.
    @SubscribeEvent
    public void onHurt(LivingHurtEvent event) {
        if (!(event.getEntity() instanceof Mob victim) || !(event.getSource().m_7639_() instanceof LivingEntity attacker)) return;
        if (attacker == victim || victim.m_9236_().m_5776_() || !Rules.isChaos(moon(victim.m_9236_()))) return;
        if (!canBrawl(victim) || !isValidVictim(attacker)) return;
        LivingEntity current = victim.m_5448_();
        if (current == null || !current.m_6084_() || current instanceof Player) setChaosTarget(victim, attacker);
    }

    /** Mobs that may start fights: not pets, villagers, player-built golems or named mobs. */
    static boolean canBrawl(Mob mob) {
        if (!mob.m_6084_() || mob.m_21525_() || mob.m_8077_() || mob instanceof Npc) return false;
        if (mob instanceof OwnableEntity owned && owned.m_21805_() != null) return false;
        return !(mob instanceof AbstractGolem) || (mob instanceof IronGolem golem && !golem.m_28876_());
    }

    static boolean isValidVictim(LivingEntity entity) {
        if (!entity.m_6084_()) return false;
        if (entity instanceof Player player) return !player.m_7500_() && !player.m_5833_();
        return entity instanceof Mob mob && canBrawl(mob);
    }

    static boolean hasOwnAttack(Mob mob) {
        if (mob instanceof RangedAttackMob) return true;
        for (WrappedGoal wrapped : mob.f_21345_.m_148105_()) {
            Object goal = wrapped.m_26015_();
            if (goal instanceof MeleeAttackGoal || goal instanceof RangedAttackGoal || goal instanceof RangedBowAttackGoal
                || goal instanceof RangedCrossbowAttackGoal || goal instanceof ChaosBrawlGoal) return true;
        }
        return false;
    }

    /** Brain-AI mobs (piglins, hoglins, frogs...) move through their brain, not goals. */
    static boolean brainDriven(Mob mob) {
        return mob.m_6274_().m_21876_(MemoryModuleType.f_26370_, MemoryStatus.REGISTERED);
    }

    /** Nearest fight for this mob: usually another mob, sometimes a nearby player. */
    static LivingEntity pickVictim(Mob mob) {
        List<LivingEntity> nearby = mob.m_9236_().m_6443_(LivingEntity.class, mob.m_20191_().m_82400_(Rules.CHAOS_RANGE),
            other -> other != mob && isValidVictim(other) && mob.m_6779_(other));
        LivingEntity nearestPlayer = null, nearestMob = null;
        Comparator<LivingEntity> byDistance = Comparator.comparingDouble(mob::m_20280_);
        for (LivingEntity other : nearby) {
            if (other instanceof Player) {
                if (nearestPlayer == null || byDistance.compare(other, nearestPlayer) < 0) nearestPlayer = other;
            } else if (nearestMob == null || byDistance.compare(other, nearestMob) < 0) {
                nearestMob = other;
            }
        }
        if (nearestPlayer != null && (nearestMob == null || mob.m_217043_().m_188501_() < Rules.CHAOS_PLAYER_CHANCE))
            return nearestPlayer;
        return nearestMob;
    }

    static void setChaosTarget(Mob mob, LivingEntity victim) {
        mob.m_6710_(victim);
        if (mob.m_6274_().m_21876_(MemoryModuleType.f_26372_, MemoryStatus.REGISTERED))
            mob.m_6274_().m_21879_(MemoryModuleType.f_26372_, victim);
        if (mob instanceof NeutralMob neutral) {
            neutral.m_6925_(victim.m_20148_());
            neutral.m_6825_();
        }
    }
}
