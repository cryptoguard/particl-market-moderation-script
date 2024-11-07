import json
import os

from typing import Dict, List, Any
from rich.console import Console
from rich.prompt import Prompt, Confirm
from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style
from particl_moderation.utils.config import get_full_path

console = Console()

class ModerationRules:
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.predefined_rules: Dict[str, Any] = {}
        self.load_config()
        self.load_predefined_rules()

    def load_config(self):
        config_file = get_full_path("rules.config_file")
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {}

    def load_predefined_rules(self):
        predefined_file = get_full_path("rules.predefined_file")
        if os.path.exists(predefined_file):
            with open(predefined_file, 'r') as f:
                self.predefined_rules = json.load(f)
        else:
            console.print(f"[yellow]Predefined rules file not found: {predefined_file}[/yellow]")
            self.predefined_rules = {}

    def save_config(self):
        config_file = get_full_path("rules.config_file")
        with open(config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
        console.print(f"[green]Configuration saved to {config_file}[/green]")

    def configure_rules(self):
        while True:
            action = self.create_menu("Moderation Rules Configuration", [
                "Apply predefined rule templates",
                "Add custom rules",
                "View current rules",
                "Save and exit"
            ])

            if action == "Apply predefined rule templates":
                console.clear()
                self.apply_predefined_templates()
            elif action == "Add custom rules":
                self.add_custom_rules()
            elif action == "View current rules":
                console.clear()
                self.view_current_rules()
            elif action == "Save and exit":
                self.save_config()
                break

        console.print("[green]Configuration complete. Returning to Moderation Settings.[/green]")

    def apply_predefined_templates(self):
        categories = list(self.predefined_rules.keys())
        selected_categories = self.create_menu("Select categories to apply templates:", categories, multi_select=True)

        for category in selected_categories:
            console.print(f"\nApplying templates for: [yellow]{category}[/yellow]")
            category_changed = False
            
            # Initialize or clear the category if it doesn't exist
            if category not in self.config:
                self.config[category] = {}
                
            for rule_type in ["downvote", "upvote", "ignore"]:
                if rule_type in self.predefined_rules[category]:
                    console.print(f"\n[cyan]{rule_type.capitalize()} rules for {category}:[/cyan]")
                    for rule in self.predefined_rules[category][rule_type]:
                        console.print(f"  - {rule}")
                    
                    use_template = Confirm.ask(f"Apply {rule_type} template for {category}?", default=True)
                    if use_template:
                        # Apply the template
                        self.config.setdefault(category, {})[rule_type] = self.predefined_rules[category][rule_type].copy()
                        category_changed = True
                    else:
                        # Clear the rules if user doesn't want to apply them
                        if category in self.config and rule_type in self.config[category]:
                            self.config[category][rule_type] = []
                            category_changed = True

            if not category_changed:
                # If no templates were applied, ensure the category has empty lists
                self.config[category] = {
                    "downvote": [],
                    "upvote": [],
                    "ignore": []
                }

        # Handle categories that weren't selected - clear their rules
        for category in self.config.keys():
            if category not in selected_categories:
                self.config[category] = {
                    "downvote": [],
                    "upvote": [],
                    "ignore": []
                }

        self.save_config()
        console.print("\n[green]Rule templates have been updated.[/green]")

    def add_custom_rules(self):
        category = Prompt.ask("Enter category name (or choose from existing)", choices=list(self.predefined_rules.keys()) + ["Other"])
        if category == "Other":
            category = Prompt.ask("Enter custom category name")

        rule_type = Prompt.ask("Select rule type", choices=["downvote", "upvote", "ignore"])

        console.print("\nEnter custom rules (one per line, press Enter twice to finish):")
        custom_rules = []
        while True:
            rule = Prompt.ask("Rule")
            if not rule:
                break
            custom_rules.append(rule)

        if custom_rules:
            self.config.setdefault(category, {}).setdefault(rule_type, []).extend(custom_rules)

    def view_current_rules(self):
        console.print("\n[bold]Current Moderation Rules:[/bold]")
        for category, rules in self.config.items():
            console.print(f"\n[yellow]{category}:[/yellow]")
            for rule_type, rule_list in rules.items():
                console.print(f"  [cyan]{rule_type}:[/cyan]")
                for rule in rule_list:
                    console.print(f"    - {rule}")
        
        Prompt.ask("\nPress Enter to continue")

    def create_menu(self, title: str, options: List[str], multi_select: bool = False):
        def get_formatted_text():
            lines = [
                ("class:title", f"{'=' * 40}\n"),
                ("class:title", f"{title.center(40)}\n"),
                ("class:title", f"{'=' * 40}\n\n")
            ]
            for i, option in enumerate(options, 1):
                if multi_select:
                    lines.append(("", f"{i}. [{'x' if option in selected else ' '}] {option}\n"))
                else:
                    lines.append(("", f"{i}. {option}\n"))
            return lines

        kb = KeyBindings()
        selected = set()

        @kb.add('q')
        def _(event):
            event.app.exit()

        for i in range(1, len(options) + 1):
            @kb.add(str(i))
            def _(event, i=i):
                if multi_select:
                    option = options[i-1]
                    if option in selected:
                        selected.remove(option)
                    else:
                        selected.add(option)
                else:
                    event.app.exit(result=options[i-1])

        @kb.add('enter')
        def _(event):
            if multi_select:
                event.app.exit(result=list(selected))
            else:
                event.app.exit()

        layout = Layout(HSplit([
            Window(content=FormattedTextControl(get_formatted_text)),
        ]))

        app = Application(
            layout=layout,
            key_bindings=kb,
            style=Style.from_dict({
                'title': '#ansiyellow',
            }),
            full_screen=True,
        )

        result = app.run()
        return result if result else (list(selected) if multi_select else None)

def initialize_rules():
    rules = ModerationRules()
    rules.configure_rules()

if __name__ == "__main__":
    initialize_rules()