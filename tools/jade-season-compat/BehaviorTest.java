import java.util.List;
import serverfixes.jadeseasons.Compat;

/** Runs the real compiled helper; only methods that need no live world are exercised here. */
class BehaviorTest {
    static void check(boolean ok, String message) { if (!ok) throw new AssertionError(message); }

    public static void main(String[] args) {
        // Ecliptic solar-term chances: spring crops get 0.7-1.25 in spring and 0.0-0.3 out of season.
        check(Compat.inSeason(0.7F, false) && Compat.inSeason(1.25F, false), "Liked solar term must count as in season");
        check(!Compat.inSeason(0.3F, false) && !Compat.inSeason(0.0F, false), "Off-season solar term must not count as in season");
        check(Compat.inSeason(0.0F, true), "A covering season core/greenhouse makes the crop in season");
        check(Compat.inSeason(null, false), "No solar-term rule means no seasonal restriction");

        check(Compat.bonemealGate(null) == 1.0F, "Plants without Ecliptic rules keep vanilla bonemeal");
        check(Compat.bonemealGate(new Compat.SeasonState(true, false, List.of())) == 1.0F, "In season bonemeal must always pass the gate");
        check(Compat.bonemealGate(new Compat.SeasonState(false, false, List.of())) == Compat.OUT_OF_SEASON_BONEMEAL
            && Compat.OUT_OF_SEASON_BONEMEAL == 0.25F, "Out of season bonemeal must pass 25%");
        check(Compat.bonemealGate(new Compat.SeasonState(true, true, List.of())) == 1.0F, "Greenhouse crops behave as in season");

        check(Compat.saplingHints("Block{minecraft:dark_oak_sapling}[stage=0]").get(0).contains("2x2"), "Dark oak hint");
        check(Compat.saplingHints("Block{minecraft:wheat}[age=0]").isEmpty(), "Crops get no sapling hints");
        System.out.println("Season gate and detector helpers behave as specified");
    }
}
