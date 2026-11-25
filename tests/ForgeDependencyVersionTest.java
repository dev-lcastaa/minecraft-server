import java.io.BufferedReader;
import java.io.InputStreamReader;
import org.apache.maven.artifact.versioning.DefaultArtifactVersion;
import org.apache.maven.artifact.versioning.VersionRange;

class ForgeDependencyVersionTest {
    public static void main(String[] args) throws Exception {
        int checked = 0;
        int failures = 0;
        try (var input = new BufferedReader(new InputStreamReader(System.in))) {
            for (String line; (line = input.readLine()) != null;) {
                String[] fields = line.split("\t", -1);
                if (fields.length != 5 || !(fields[4].equals("true") || fields[4].equals("false"))) {
                    throw new IllegalArgumentException("Invalid dependency test case: " + line);
                }
                boolean accepted = VersionRange.createFromVersionSpec(fields[3])
                    .containsVersion(new DefaultArtifactVersion(fields[2]));
                if (accepted != Boolean.parseBoolean(fields[4])) {
                    System.err.printf("%s requires %s %s; installed version %s was %s%n",
                        fields[0], fields[1], fields[3], fields[2],
                        accepted ? "accepted" : "rejected");
                    failures++;
                }
                checked++;
            }
        }
        if (checked == 0 || failures != 0) {
            throw new AssertionError(failures + " dependency version mismatches in " + checked + " cases");
        }
        System.out.println("Forge Maven version checks passed: " + checked);
    }
}
