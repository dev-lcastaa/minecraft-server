package serverfixes.lunar;

import java.util.Set;

/** Pure moon rules, kept free of Minecraft types so they can be tested directly. */
public final class Rules {
    public static final String NS = "lunar_events_compat:";
    public static final String HORDE = NS + "horde_moon";
    public static final String BABY_HORDE = NS + "baby_horde_moon";
    public static final String ENDER = NS + "ender_moon";
    public static final String CHAOS = NS + "chaos_moon";
    public static final Set<String> PEACEFUL = Set.of(NS + "peaceful_moon",
        "enhancedcelestials2defaultlunarevents:harvest_moon", "enhancedcelestials2defaultlunarevents:super_harvest_moon",
        "enhancedcelestials2defaultlunarevents:blue_moon", "enhancedcelestials2defaultlunarevents:super_blue_moon");
    public static final Set<String> HORDE_ZOMBIES = Set.of("minecraft:zombie", "minecraft:husk", "minecraft:drowned",
        "minecraft:zombie_villager", "dungeonsdelight:rotten_zombie", "rottencreatures:burned",
        "rottencreatures:frostbitten", "rottencreatures:swampy", "rottencreatures:undead_miner",
        "rottencreatures:mummy", "rottencreatures:zap", "graveyard:ghoul");
    public static final double BABY_CHANCE = 0.85;
    public static final int SHULKER_MAX_LIGHT = 7;
    /** Chaos: how far a mob looks for something to fight, and how often it re-picks. */
    public static final double CHAOS_RANGE = 16.0;
    public static final int CHAOS_RETARGET_TICKS = 100;
    /** Hostile mobs go for a nearby player this often; otherwise they fight other mobs. */
    public static final float CHAOS_PLAYER_CHANCE = 0.35F;

    private Rules() { }

    public static boolean blocksPeacefulSpawn(String moon, boolean hostile, String spawnType) {
        return moon != null && PEACEFUL.contains(moon) && hostile
            && (spawnType.equals("NATURAL") || spawnType.equals("PATROL"));
    }

    public static boolean buffsHorde(String moon, boolean zombie, String spawnType) {
        return HORDE.equals(moon) && zombie && !spawnType.equals("COMMAND") && !spawnType.equals("SPAWN_EGG");
    }

    public static boolean makesBaby(String moon, boolean eligible, String spawnType, double roll) {
        return BABY_HORDE.equals(moon) && eligible && roll < BABY_CHANCE
            && (spawnType.equals("NATURAL") || spawnType.equals("REINFORCEMENT") || spawnType.equals("EVENT"));
    }

    public static boolean blocksEnderShulker(String moon, String spawnType, int light) {
        return ENDER.equals(moon) && spawnType.equals("NATURAL") && light > SHULKER_MAX_LIGHT;
    }

    public static boolean isChaos(String moon) {
        return CHAOS.equals(moon);
    }
}
