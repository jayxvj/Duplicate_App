"""Rule-based application categorization engine."""
import re
from typing import List, Optional

from app.core.types import Application, CategoryRule


class RuleEngine:
    @staticmethod
    def evaluate_rule(rule: CategoryRule, app: Application) -> bool:
        """Evaluates whether an application satisfies a single categorization rule."""
        if not rule.enabled:
            return False

        field_val = RuleEngine._get_field_value(rule.field, app)
        target_val = rule.value

        op = rule.operator.lower()
        if op == "contains":
            return target_val.lower() in str(field_val).lower()
        elif op == "equals":
            return target_val.lower() == str(field_val).lower()
        elif op == "starts_with":
            return str(field_val).lower().startswith(target_val.lower())
        elif op == "ends_with":
            return str(field_val).lower().endswith(target_val.lower())
        elif op == "regex":
            try:
                return bool(re.search(target_val, str(field_val), re.IGNORECASE))
            except re.error:
                return False
        elif op == "gt":
            try:
                return float(field_val) > float(target_val)
            except (ValueError, TypeError):
                return False
        elif op == "lt":
            try:
                return float(field_val) < float(target_val)
            except (ValueError, TypeError):
                return False
        return False

    @staticmethod
    def categorize_application(app: Application, rules: List[CategoryRule]) -> str:
        """
        Evaluates rules in priority order (highest priority first).
        Returns the category of the first matching rule, or 'Other' if none match.
        """
        sorted_rules = sorted(rules, key=lambda r: r.priority, reverse=True)
        for rule in sorted_rules:
            if RuleEngine.evaluate_rule(rule, app):
                return rule.category
        return "Other"

    @staticmethod
    def get_descriptive_category(app: Application) -> str:
        """
        Returns a specific descriptive label ('Script' or 'Application Package')
        when an application is uncategorized or labeled 'Other'.
        """
        script_exts = {".py", ".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd", ".vbs", ".js"}
        package_exts = {".jar", ".war", ".ear", ".apk", ".deb", ".rpm", ".dmg", ".pkg", ".appx", ".msix"}

        exts = {f.file_type.lower() for f in app.files if f.file_type}
        app_type_str = str(app.app_type.value if hasattr(app.app_type, "value") else app.app_type).lower()

        if "python" in app_type_str or exts.intersection(script_exts):
            return "Script"
        
        # Check root path extension
        root_ext = "." + app.root_path.split(".")[-1].lower() if "." in app.root_path else ""
        if root_ext in script_exts:
            return "Script"

        return "Application Package"

    @staticmethod
    def _get_field_value(field: str, app: Application) -> str:
        f = field.lower()
        if f == "name":
            return app.name
        elif f == "path":
            return app.root_path
        elif f == "executable":
            # Check executable files in app
            exe_names = [file.relative_path for file in app.files if file.file_type in [".exe", ".bat", ".cmd", ".jar", ".py", ".sh", ".ps1"]]
            return " ".join(exe_names) if exe_names else app.name
        elif f == "app_type":
            return app.app_type.value if hasattr(app.app_type, "value") else str(app.app_type)
        elif f == "size":
            return str(app.total_size)
        return ""

