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
        long day = 10 * 24000L;
        check(Rules.seasonalDayTime(day + 18000, 18000) == day + 18000, "Midnight is unchanged");
        check(Rules.seasonalDayTime(day + 13000, 11600) == day + 11600, "Summer: no moon before the late sunset");
        check(Rules.seasonalDayTime(day + 23000, 400) == day + 24400, "Summer: moon gone after the early sunrise");
        check(Rules.seasonalDayTime(day + 11000, 12400) == day + 12400, "Winter: night starts at the early sunset");
        check(Rules.seasonalDayTime(day + 24000 + 1000, 23600) == day + 23600, "Winter: night continues past tick 24000");
        check(Rules.seasonalDayTime(day + 24000 + 2000, 300) == day + 24300, "Winter: next morning after sunrise");
        System.out.println("Lunar rules behave as specified");
    }
}
