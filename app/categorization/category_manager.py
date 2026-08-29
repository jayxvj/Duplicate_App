"""Category management and rule orchestration."""
from typing import Dict, List, Optional
from app.config import load_default_categories
from app.core.types import Application, CategoryRule
from app.database.repository import Repository
from app.categorization.rule_engine import RuleEngine


class CategoryManager:
    def __init__(self, repository: Optional[Repository] = None):
        self.repo = repository or Repository()
        self._ensure_default_rules()

    def _ensure_default_rules(self) -> None:
        existing = self.repo.get_all_rules()
        if not existing:
            data = load_default_categories()
            categories = data.get("categories", [])
            for cat_data in categories:
                cat_name = cat_data.get("name", "Other")
                priority = cat_data.get("priority", 50)
                for rule_dict in cat_data.get("rules", []):
                    rule = CategoryRule(
                        category=cat_name,
                        field=rule_dict.get("field", "name"),
                        operator=rule_dict.get("operator", "contains"),
                        value=rule_dict.get("value", ""),
                        priority=priority,
                        enabled=True,
                    )
                    self.repo.save_rule(rule)

    def get_rules(self) -> List[CategoryRule]:
        return self.repo.get_all_rules()

    def categorize_applications(self, apps: List[Application]) -> List[Application]:
        rules = self.get_rules()
        for app in apps:
            app.category = RuleEngine.categorize_application(app, rules)
        return apps

    def get_category_counts(self, apps: List[Application]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for app in apps:
            counts[app.category] = counts.get(app.category, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))
