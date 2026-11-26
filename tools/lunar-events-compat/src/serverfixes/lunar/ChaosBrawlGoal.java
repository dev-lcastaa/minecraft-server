package serverfixes.lunar;

import java.util.EnumSet;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.Goal;

/** Simple melee for mobs that have no attack of their own (cows, sheep...), active only during the Chaos Moon. */
final class ChaosBrawlGoal extends Goal {
    static final float UNARMED_DAMAGE = 2.0F;
    private final PathfinderMob mob;
    private int cooldown;
    private int repath;

    ChaosBrawlGoal(PathfinderMob mob) {
        this.mob = mob;
        m_7021_(EnumSet.of(Goal.Flag.MOVE, Goal.Flag.LOOK));
    }

    private boolean active() {
        LivingEntity target = mob.m_5448_();
        return target != null && target.m_6084_() && Rules.isChaos(LunarEvents.moon(mob.m_9236_()));
    }

    @Override public boolean m_8036_() { return active(); }
    @Override public boolean m_8045_() { return active(); }
    @Override public boolean m_183429_() { return true; }

    @Override
    public void m_8056_() {
        repath = 0;
        mob.m_21561_(true);
    }

    @Override
    public void m_8041_() {
        mob.m_21561_(false);
        mob.m_21573_().m_26573_();
    }

    @Override
    public void m_8037_() {
        LivingEntity target = mob.m_5448_();
        if (target == null) return;
        mob.m_21563_().m_24960_(target, 30.0F, 30.0F);
        if (--repath <= 0) {
            repath = 10;
            mob.m_21573_().m_5624_(target, 1.25);
        }
        if (--cooldown <= 0 && mob.m_217066_(target)) {
            cooldown = 20;
            if (mob.m_21204_().m_22171_(Attributes.f_22281_)) mob.m_7327_(target);
            else target.m_6469_(mob.m_269291_().m_269333_(mob), UNARMED_DAMAGE);
        }
    }
}
