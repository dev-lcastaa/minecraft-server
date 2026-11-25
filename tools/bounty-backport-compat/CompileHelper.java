import java.nio.file.Path;
import javax.tools.ToolProvider;

class CompileHelper {
    public static void main(String[] args) {
        if (args.length != 2) {
            throw new IllegalArgumentException("Expected Java source and output directory");
        }
        var compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) {
            throw new IllegalStateException("A JDK with the Java compiler is required to build bounty compatibility");
        }
        int result = compiler.run(
            null, System.out, System.err, "-source", "17", "-target", "17",
            "-Xlint:-options", "-d",
            Path.of(args[1]).toString(), Path.of(args[0]).toString()
        );
        if (result != 0) {
            throw new IllegalStateException("Could not compile bounty trade bridge (javac exit " + result + ")");
        }
    }
}
