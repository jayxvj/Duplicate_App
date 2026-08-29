"""Tests for rule engine, priority resolution, and fallback categorization."""
from app.core.types import Application, CategoryRule
from app.categorization.rule_engine import RuleEngine


def test_rule_priority_resolution():
    app = Application(
        name="vscode",
        root_path="C:/Tools/vscode",
        total_size=100000,
        file_count=50,
    )

    rules = [
        CategoryRule(category="Utilities", field="path", operator="contains", value="tools", priority=50),
        CategoryRule(category="Development", field="name", operator="contains", value="code", priority=100),
    ]

    # Should match Development because priority 100 > priority 50
    cat = RuleEngine.categorize_application(app, rules)
    assert cat == "Development"


def test_rule_fallback_to_other():
    app = Application(
        name="UnknownCustomBinary",
        root_path="D:/Random/UnknownCustomBinary",
    )
    rules = [
        CategoryRule(category="Development", field="name", operator="contains", value="python", priority=100)
    ]

    cat = RuleEngine.categorize_application(app, rules)
    assert cat == "Other"


def test_rule_operators_regex_and_equals():
    app = Application(name="Nginx-1.24", root_path="C:/Servers/nginx")

    rule_regex = CategoryRule(category="Web Development", field="name", operator="regex", value=r"nginx-\d+\.\d+", priority=80)
    assert RuleEngine.evaluate_rule(rule_regex, app) is True

    rule_equals = CategoryRule(category="Web Development", field="name", operator="equals", value="nginx-1.24", priority=80)
    assert RuleEngine.evaluate_rule(rule_equals, app) is True


def test_descriptive_category_fallback():
    from app.core.types import FileRecord, AppType
    
    # Script application
    script_app = Application(
        name="backup_script",
        root_path="C:/Scripts/backup.py",
        app_type=AppType.PYTHON_ENV,
        files=[FileRecord(relative_path="backup.py", absolute_path="C:/Scripts/backup.py", file_type=".py", is_readable=True)],
    )
    assert RuleEngine.get_descriptive_category(script_app) == "Script"

    # Application package
    pkg_app = Application(
        name="tool_package",
        root_path="C:/Packages/tool.msi",
        app_type=AppType.STANDALONE_BINARY,
        files=[FileRecord(relative_path="tool.msi", absolute_path="C:/Packages/tool.msi", file_type=".msi", is_readable=True)],
    )
    assert RuleEngine.get_descriptive_category(pkg_app) == "Application Package"

