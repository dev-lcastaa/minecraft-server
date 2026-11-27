package serverfixes.lunar;

import com.teamtea.eclipticseasons.common.core.map.MapChecker;
import com.teamtea.eclipticseasons.common.core.solar.SolarAngelHelper;
import com.teamtea.eclipticseasons.config.CommonConfig;
import net.minecraft.world.level.Level;

/** Replaces Level.getDayTime() inside Enhanced Celestials' LunarForecast (coremods/seasonal_moon_night.js). */
public final class LunarClock {
    private LunarClock() { }

    public static long dayTime(Level level) {
        long time = level.m_46468_();
        if (!CommonConfig.Season.daylightChange.get() || !MapChecker.isValidDimension(level)) return time;
        return Rules.seasonalDayTime(time, SolarAngelHelper.getSolarAngelTime(level, time));
    }
}
