"""
Rule Engine.

Loads declarative YAML rules from /rules and evaluates them against parsed
cloud-configuration resources.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


class RuleEngine:
    def __init__(self, rules_directory: str = "rules"):
        self.rules_directory = Path(rules_directory)
        self.rules = self.load_rules()

    # ------------------------------------------------ #

    def load_rules(self):
        """Load every YAML rule in /rules (skipping the spec.yaml schema doc)."""
        rules = []

        if not self.rules_directory.exists():
            raise FileNotFoundError(
                f"Rules directory '{self.rules_directory}' not found."
            )

        # Support both .yaml and .yml rule files.
        rule_files = sorted(
            set(self.rules_directory.glob("*.yaml"))
            | set(self.rules_directory.glob("*.yml"))
        )

        for rule_file in rule_files:
            if rule_file.name == "spec.yaml":
                continue

            with open(rule_file, "r", encoding="utf-8") as f:
                rule = yaml.safe_load(f)

            if not rule or "rule_id" not in rule or "condition" not in rule:
                logger.warning("Skipping malformed rule file: %s", rule_file.name)
                continue

            rules.append(rule)
            logger.info("Loaded rule %s", rule["rule_id"])

        return rules

    # ------------------------------------------------ #

    @staticmethod
    def _normalize(parsed):
        """
        Bridge the parser's output to the evaluator's expected input.

        The parser returns whatever shape the uploaded file has (commonly a
        single dict, or a dict wrapping a ``resources`` list). The evaluator
        works on a *list of resource dicts*. This normalization is the missing
        seam between the parser and the engine.
        """
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            if isinstance(parsed.get("resources"), list):
                return parsed["resources"]
            return [parsed]
        return []

    # ------------------------------------------------ #

    def evaluate(self, resources):
        """
        Evaluate every resource against every applicable rule.

        Accepts a list of resource dicts, a single resource dict, or a dict with
        a ``resources`` list. Returns a list of finding dicts.
        """
        resources = self._normalize(resources)
        findings = []

        for resource in resources:
            if not isinstance(resource, dict):
                continue

            resource_type = resource.get("resource_type")

            for rule in self.rules:
                condition = rule.get("condition", {})

                if condition.get("resource_type") != resource_type:
                    continue

                eval_path = condition.get("eval_path")
                if not eval_path:
                    continue

                value = self.get_value(resource, eval_path)

                if self.match(value, condition):
                    findings.append({
                        "resource_id": resource.get("resource_id", "Unknown"),
                        "resource_type": resource_type,
                        "severity": rule["severity"],
                        "rule_id": rule["rule_id"],
                        "message": rule["remediation"],
                    })

        return findings

    # ------------------------------------------------ #

    def get_value(self, data, path):
        """Resolve a dot-notation path (e.g. ``ingress.cidr``, ``tags.owner``)."""
        current = data

        for part in path.split("."):
            if isinstance(current, dict):
                if part not in current:
                    return None
                current = current[part]
            elif isinstance(current, list):
                try:
                    index = int(part)
                    current = current[index]
                except (ValueError, IndexError):
                    return None
            else:
                return None

        return current

    # ------------------------------------------------ #

    def match(self, value, condition):
        """Evaluate the single supported operator present on a condition."""
        if "equals" in condition:
            return value == condition["equals"]

        if "contains" in condition:
            if value is None:
                return False
            return condition["contains"] in str(value)

        if "regex" in condition:
            if value is None:
                return False
            return re.search(condition["regex"], str(value)) is not None

        if "gte" in condition:
            try:
                return float(value) >= float(condition["gte"])
            except Exception:
                return False

        if "lte" in condition:
            try:
                return float(value) <= float(condition["lte"])
            except Exception:
                return False

        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    engine = RuleEngine()

    resources = [
        {"resource_id": "bucket-001", "resource_type": "s3_bucket", "public_read": True},
        {"resource_id": "sg-001", "resource_type": "security_group",
         "ingress": {"cidr": "0.0.0.0/0"}},
        {"resource_id": "policy-001", "resource_type": "iam_policy", "action": "s3:*"},
    ]

    print("\nFindings\n")
    for finding in engine.evaluate(resources):
        print(finding)
