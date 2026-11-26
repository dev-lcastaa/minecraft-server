import serverfixes.lunar.Rules;

class BehaviorTest {
    static void check(boolean ok, String message) { if (!ok) throw new AssertionError(message); }

    public static void main(String[] args) {
        check(Rules.blocksPeacefulSpawn(Rules.NS + "peaceful_moon", true, "NATURAL"), "Peaceful blocks natural hostiles");
        check(Rules.blocksPeacefulSpawn("enhancedcelestials2defaultlunarevents:harvest_moon", true, "PATROL"), "Harvest blocks patrols");
        check(!Rules.blocksPeacefulSpawn(Rules.NS + "peaceful_moon", true, "SPAWNER"), "Spawners still work");
        check(!Rules.blocksPeacefulSpawn(Rules.NS + "peaceful_moon", false, "NATURAL"), "Animals still spawn");
        check(!Rules.blocksPeacefulSpawn(null, true, "NATURAL"), "No moon, no blocking");
        check(Rules.buffsHorde(Rules.HORDE, true, "NATURAL") && !Rules.buffsHorde(Rules.HORDE, true, "SPAWN_EGG"), "Horde buffs");
        check(Rules.makesBaby(Rules.BABY_HORDE, true, "NATURAL", 0.5) && !Rules.makesBaby(Rules.BABY_HORDE, true, "NATURAL", 0.9),
            "Baby Horde 85%");
        check(Rules.blocksEnderShulker(Rules.ENDER, "NATURAL", 12) && !Rules.blocksEnderShulker(Rules.ENDER, "NATURAL", 3),
            "Ender shulkers only in the dark");
        check(Rules.isChaos(Rules.CHAOS) && !Rules.isChaos(Rules.HORDE), "Chaos detection");
        check(Rules.CHAOS_PLAYER_CHANCE < 0.5F, "Chaos mobs mostly fight each other");
        System.out.println("Lunar rules behave as specified");
    }
}
