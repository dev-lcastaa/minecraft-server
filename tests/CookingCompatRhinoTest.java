import dev.latvian.mods.rhino.Context;
import dev.latvian.mods.rhino.ScriptableObject;
import java.nio.file.Files;
import java.nio.file.Path;

public class CookingCompatRhinoTest {
    public static void main(String[] args) throws Exception {
        Context context = Context.enter();
        ScriptableObject scope = context.initStandardObjects();
        context.evaluateString(scope, """
            var callback;
            var unregistered = {
              'culturaldelights:calamari_roll': true,
              'upgrade_aquatic:pickerelweed': true,
              'ecologics:cooked_prickly_pear': true
            };
            var warnings = [];
            var Item = {of: function(id) {
              return {isEmpty: function() { return !!unregistered[id]; }};
            }};
            var console = {warn: function(message) { warnings.push(message); }};
            var ServerEvents = {recipes: function(fn) { callback = fn; }};
            """, "cooking-fixture-setup", 1, null);
        context.evaluateString(scope, Files.readString(Path.of(args[0])), args[0], 1, null);
        context.evaluateString(scope, """
            var originals = {
              'miners_delight:calamari_roll': 'culturaldelights:calamari_roll',
              'abnormals_delight:pickerelweed_juice': 'upgrade_aquatic:pickerelweed',
              'delightful:food/prickly_pear_juice_from_cooked_prickly_pear': 'ecologics:cooked_prickly_pear'
            };
            var removed = {};
            var added = {};
            callback({
              remove: function(filter) { removed[filter.id] = true; },
              custom: function(recipe) {
                return {id: function(id) { added[id] = recipe; }};
              }
            });
            for (var id in originals) {
              if (removed[id] || added[id]) throw Error('Original recipe replaced: ' + id);
              var found = false;
              for (var i = 0; i < warnings.length; i++) {
                if (warnings[i].indexOf(id) !== -1 && warnings[i].indexOf(originals[id]) !== -1) {
                  found = true;
                }
              }
              if (!found) throw Error('Missing warning for ' + id);
            }
            if (!removed['cooking_compat:cutting/cobweb'] ||
                !added['cooking_compat:cutting/cobweb']) {
              throw Error('Valid recipe was not replaced');
            }
            if (cookingMissingIngredient([{item: 'upgrade_aquatic:pickerelweed'},
                                           {item: 'minecraft:stone'}]) !== null ||
                cookingMissingIngredient([{item: 'upgrade_aquatic:pickerelweed'},
                                           {tag: 'forge:crops'}]) !== null) {
              throw Error('A valid alternative was rejected');
            }
            if (cookingMissingIngredient([{item: 'upgrade_aquatic:pickerelweed'},
                                           {item: 'ecologics:cooked_prickly_pear'}]) !==
                'upgrade_aquatic:pickerelweed') {
              throw Error('Missing alternatives were not detected');
            }
            if (cookingMissingRecipeItem({key: {A: {item: 'upgrade_aquatic:pickerelweed'}}}) !==
                'upgrade_aquatic:pickerelweed' ||
                cookingMissingRecipeItem({results: [{item: 'minecraft:stone'},
                                                    {item: 'culturaldelights:calamari_roll'}]}) !==
                'culturaldelights:calamari_roll') {
              throw Error('Missing shaped input or output was not detected');
            }
            """, "cooking-fixture-assertions", 1, null);
        System.out.println("Rhino cooking registry guard passed");
    }
}
