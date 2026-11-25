package serverfixes.bounties;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.List;

public final class BountyTradeBridge {
    private BountyTradeBridge() {}

    public static void append(Object event, Object listing, int level) {
        try {
            Object trades = event.getClass().getMethod("getTrades").invoke(event);
            Method getLevel = trades.getClass().getMethod("get", int.class);
            Object offers = getLevel.invoke(trades, level);
            if (!(offers instanceof List<?>)) {
                throw new IllegalStateException("Farmer trade list is not available at level " + level);
            }
            Method add = List.class.getMethod("add", Object.class);
            add.invoke(offers, listing);
        } catch (InvocationTargetException exception) {
            throw new IllegalStateException("Could not append villager trade at level " + level,
                exception.getCause());
        } catch (ReflectiveOperationException exception) {
            throw new IllegalStateException("Could not access villager trade list at level " + level,
                exception);
        }
    }
}
