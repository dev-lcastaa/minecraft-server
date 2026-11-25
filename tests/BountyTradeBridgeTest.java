import java.util.ArrayList;
import java.util.List;
import serverfixes.bounties.BountyTradeBridge;

class BountyTradeBridgeTest {
    public static final class FakeTrades {
        private final List<Object>[] levels = new List[] {
            new ArrayList<>(), new ArrayList<>(), new ArrayList<>()
        };

        public List<Object> get(int level) {
            return levels[level];
        }
    }

    public static final class FakeEvent {
        private final FakeTrades trades = new FakeTrades();

        public FakeTrades getTrades() {
            return trades;
        }
    }

    public static void main(String[] args) {
        FakeEvent event = new FakeEvent();
        Object existing = new Object();
        Object newListing = new Object();
        event.trades.get(2).add(existing);

        BountyTradeBridge.append(event, newListing, 2);

        if (event.trades.get(2).size() != 2
                || event.trades.get(2).get(0) != existing
                || event.trades.get(2).get(1) != newListing
                || !event.trades.get(1).isEmpty()) {
            throw new AssertionError("Trade was not appended to the requested level");
        }
        System.out.println("Bounty villager trade bridge passed");
    }
}
