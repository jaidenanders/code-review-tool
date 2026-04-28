"""TDD tests for LanguageService — extension-to-language detection."""
import pytest
from app.services.language_service import detect_language


class TestDetectLanguage:
    # ── Python ────────────────────────────────────────────
    def test_py_extension(self):
        assert detect_language("foo.py") == "python"

    def test_pyi_extension(self):
        assert detect_language("stubs.pyi") == "python"

    def test_py_case_insensitive(self):
        assert detect_language("FOO.PY") == "python"

    # ── JavaScript ───────────────────────────────────────
    def test_js_extension(self):
        assert detect_language("app.js") == "javascript"

    def test_jsx_extension(self):
        assert detect_language("Component.jsx") == "javascript"

    def test_mjs_extension(self):
        assert detect_language("module.mjs") == "javascript"

    # ── TypeScript ───────────────────────────────────────
    def test_ts_extension(self):
        assert detect_language("service.ts") == "typescript"

    def test_tsx_extension(self):
        assert detect_language("Button.tsx") == "typescript"

    def test_mts_extension(self):
        assert detect_language("mod.mts") == "typescript"

    # ── Other common languages ────────────────────────────
    def test_go_extension(self):
        assert detect_language("main.go") == "go"

    def test_rs_extension(self):
        assert detect_language("lib.rs") == "rust"

    def test_java_extension(self):
        assert detect_language("Main.java") == "java"

    def test_rb_extension(self):
        assert detect_language("app.rb") == "ruby"

    def test_kt_extension(self):
        assert detect_language("Activity.kt") == "kotlin"

    def test_cs_extension(self):
        assert detect_language("Program.cs") == "csharp"

    def test_cpp_extension(self):
        assert detect_language("main.cpp") == "cpp"

    def test_c_extension(self):
        assert detect_language("util.c") == "c"

    def test_swift_extension(self):
        assert detect_language("App.swift") == "swift"

    def test_sh_extension(self):
        assert detect_language("deploy.sh") == "bash"

    def test_php_extension(self):
        assert detect_language("index.php") == "php"

    def test_scala_extension(self):
        assert detect_language("Main.scala") == "scala"

    # ── Config / data formats ─────────────────────────────
    def test_sql_extension(self):
        assert detect_language("schema.sql") == "sql"

    def test_yaml_extension(self):
        assert detect_language("config.yaml") == "yaml"

    def test_yml_extension(self):
        assert detect_language("ci.yml") == "yaml"

    def test_json_extension(self):
        assert detect_language("package.json") == "json"

    def test_toml_extension(self):
        assert detect_language("Cargo.toml") == "toml"

    # ── Unknown / edge cases ──────────────────────────────
    def test_unknown_extension_returns_unknown(self):
        assert detect_language("file.xyz") == "unknown"

    def test_no_extension_returns_unknown(self):
        assert detect_language("Makefile") == "unknown"

    def test_empty_string_returns_unknown(self):
        assert detect_language("") == "unknown"

    def test_path_with_directories(self):
        assert detect_language("src/services/auth.ts") == "typescript"

    def test_dotfile_returns_unknown(self):
        assert detect_language(".gitignore") == "unknown"
