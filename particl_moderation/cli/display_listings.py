import os

from prompt_toolkit import Application
from prompt_toolkit.key_binding import merge_key_bindings, KeyBindings, ConditionalKeyBindings
from prompt_toolkit.layout.containers import Window, HSplit
from prompt_toolkit.layout.controls import FormattedTextControl, BufferControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.filters import Condition
from prompt_toolkit.layout.processors import BeforeInput
from rich.console import Console
from particl_moderation.utils.config import get_full_path


console = Console()

DEFAULT_MARKET_ADDRESS = "PZijh4WzjCWLbSgBkMUtLHZBaU6dSSmkqN"

class ListingDisplay:
    def __init__(self):
        self.listings = []
        self.filtered_listings = []
        self.page = 0
        self.page_size = 10
        self.selected = 0
        self.search_term = ""
        self.changed_listings = {}
        self.message = ""
        self.search_buffer = Buffer()
        self.is_searching = False

    def search_listings(self, search_term: str):
        self.search_term = search_term.lower()
        if not self.search_term:
            self.filtered_listings = self.listings.copy()
        else:
            self.filtered_listings = [
                listing for listing in self.listings
                if self.search_term in listing["title"].lower() or self.search_term in listing["description"].lower()
            ]
        self.page = 0
        self.selected = 0
        self.message = f"Found {len(self.filtered_listings)} results for '{search_term}'"

    def clear_search(self):
        self.search_term = ""
        self.filtered_listings = self.listings.copy()
        self.page = 0
        self.selected = 0
        self.message = "Search filter cleared"

    def load_listings(self):
        self.listings.clear()
        self.filtered_listings.clear()
        results_file = get_full_path("paths.results_file")
        if not os.path.exists(results_file):
            console.print(f"[yellow]Results file not found. Creating an empty file at {results_file}[/yellow]")
            with open(results_file, 'wb') as f:
                pass
            return

        try:
            with open(results_file, 'rb') as f:
                for line in f:
                    try:
                        line = line.decode('utf-8').strip()
                        parts = line.split('|')
                        if len(parts) >= 4:
                            date_type = parts[0].split(']')
                            date = date_type[0][1:].strip()
                            type = date_type[1].strip()
                            hash = parts[1].strip()
                            title = parts[2].strip()
                            description = parts[3].strip()
                            self.listings.append({
                                "date": date,
                                "type": type,
                                "hash": hash,
                                "title": title,
                                "description": description
                            })
                    except UnicodeDecodeError:
                        console.print(f"[yellow]Skipping a line due to encoding issues.[/yellow]")
        except Exception as e:
            console.print(f"[red]Error reading file: {str(e)}[/red]")
            console.print("[yellow]Try converting the file to UTF-8 encoding first.[/yellow]")
            return

        self.filtered_listings = self.listings.copy()

    def set_moderation_status(self, index: int, new_type: str):
        if index >= len(self.filtered_listings):
            return

        listing = self.filtered_listings[index]
        current_type = listing["type"]

        if current_type != new_type:
            listing["type"] = new_type
            self.changed_listings[listing["hash"]] = new_type
            self.message = f"Listing moderation decision changed to {new_type}"

    def save_changes(self):
        results_file = get_full_path("paths.results_file")
        vote_queue_file = get_full_path("paths.vote_queue_file")

        try:
            with open(results_file, 'rb') as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                try:
                    line_str = line.decode('utf-8')
                    parts = line_str.strip().split('|')
                    if len(parts) >= 2:
                        hash = parts[1].strip()
                        if hash in self.changed_listings:
                            new_type = self.changed_listings[hash]
                            date_end = line_str.index(']') + 1
                            new_line = f"{line_str[:date_end]} {new_type}{line_str[line_str.index('|'):]}"
                            lines[i] = new_line.encode('utf-8')
                except UnicodeDecodeError:
                    console.print(f"[yellow]Skipping a line in results file due to encoding issues.[/yellow]")

            with open(results_file, 'wb') as f:
                f.writelines(lines)

            with open(vote_queue_file, 'rb') as f:
                vote_queue = f.readlines()

            new_vote_queue = []
            for line in vote_queue:
                try:
                    line_str = line.decode('utf-8')
                    hash = line_str.split('|')[0]
                    if hash not in self.changed_listings:
                        new_vote_queue.append(line)
                except UnicodeDecodeError:
                    console.print(f"[yellow]Skipping a line in vote queue file due to encoding issues.[/yellow]")

            for hash, new_type in self.changed_listings.items():
                listing = next(item for item in self.listings if item["hash"] == hash)
                if new_type in ["upvote", "downvote"]:
                    action = "KEEP" if new_type == "upvote" else "REMOVE"
                    new_line = f"{hash}|{listing['title']}|{listing['description']}|{DEFAULT_MARKET_ADDRESS}|{action}\n"
                    new_vote_queue.append(new_line.encode('utf-8'))

            with open(vote_queue_file, 'wb') as f:
                f.writelines(new_vote_queue)

            self.changed_listings.clear()
            self.message = "Changes saved successfully."
            self.load_listings()
        except Exception as e:
            self.message = f"Error saving changes: {str(e)}"

    def search_listings(self, search_term: str):
        self.search_term = search_term
        if not search_term:
            self.filtered_listings = self.listings.copy()
        else:
            self.filtered_listings = [
                listing for listing in self.listings
                if search_term.lower() in listing["title"].lower() or search_term.lower() in listing["description"].lower()
            ]
        self.page = 0
        self.selected = 0

def create_listing_display():
    ld = ListingDisplay()
    ld.load_listings()

    # Create separate key bindings for different modes
    main_kb = KeyBindings()  # For normal navigation mode
    search_kb = KeyBindings() # For search mode
    global_kb = KeyBindings() # For commands that work in both modes

    # Global bindings (always active)
    @global_kb.add('c-c')
    def _(event):
        event.app.exit()

    # Main mode bindings
    @main_kb.add('q')
    def _(event):
        event.app.exit()

    @main_kb.add('s')
    def _(event):
        current_page = ld.page
        ld.save_changes()
        ld.page = min(current_page, (len(ld.filtered_listings) - 1) // ld.page_size)
        ld.selected = 0
        event.app.invalidate()

    @main_kb.add('/')
    def _(event):
        ld.is_searching = True
        ld.search_buffer.reset()
        ld.message = "Enter search term: "
        event.app.invalidate()

    @main_kb.add('c')
    def _(event):
        ld.clear_search()
        event.app.invalidate()

    # Search mode bindings
    @search_kb.add('enter')
    def _(event):
        ld.is_searching = False
        search_term = ld.search_buffer.text
        ld.search_listings(search_term)
        ld.message = f"Search results for '{search_term}'"
        event.app.invalidate()

    @search_kb.add('escape')
    def _(event):
        ld.is_searching = False
        ld.search_buffer.reset()
        ld.message = ""
        event.app.invalidate()

    # Navigation bindings (only active in main mode)
    @main_kb.add('up')
    def _(event):
        ld.selected = max(0, ld.selected - 1)
        event.app.invalidate()

    @main_kb.add('down')
    def _(event):
        ld.selected = min(ld.page_size - 1, ld.selected + 1, len(ld.filtered_listings) - ld.page * ld.page_size - 1)
        event.app.invalidate()

    @main_kb.add('left')
    def _(event):
        ld.page = max(0, ld.page - 1)
        ld.selected = 0
        event.app.invalidate()

    @main_kb.add('right')
    def _(event):
        if (ld.page + 1) * ld.page_size < len(ld.filtered_listings):
            ld.page += 1
            ld.selected = 0
        event.app.invalidate()

    @main_kb.add('u')
    @main_kb.add('U')
    def _(event):
        ld.set_moderation_status(ld.page * ld.page_size + ld.selected, "upvote")
        event.app.invalidate()

    @main_kb.add('d')
    @main_kb.add('D')
    def _(event):
        ld.set_moderation_status(ld.page * ld.page_size + ld.selected, "downvote")
        event.app.invalidate()

    @main_kb.add('i')
    @main_kb.add('I')
    def _(event):
        ld.set_moderation_status(ld.page * ld.page_size + ld.selected, "ignore")
        event.app.invalidate()

    # Create the key bindings registry with proper conditions
    kb = merge_key_bindings([
        global_kb,  # Always active
        ConditionalKeyBindings(search_kb, Condition(lambda: ld.is_searching)),  # Only in search mode
        ConditionalKeyBindings(main_kb, Condition(lambda: not ld.is_searching))  # Only in main mode
    ])

    def get_formatted_text():
        result = [
            ("class:title", "=============== Processed Listings ===============\n"),
            ("", "↑↓ to move cursor. ← → to change pages.\n"),
            ("", "U: Upvote, D: Downvote, I: Ignore\n"),
            ("", "/ to search. C to clear search. S to save. Q to quit.\n"),
            ("class:title", "------------------------------------------------\n"),
        ]

        if ld.search_term:
            result.append(("class:search", f"Search: {ld.search_term}\n"))

        start = ld.page * ld.page_size
        end = min(start + ld.page_size, len(ld.filtered_listings))

        for i in range(start, end):
            listing = ld.filtered_listings[i]
            prefix = "> " if i - start == ld.selected else "  "
            type_color = {
                "downvote": "class:downvote",
                "upvote": "class:upvote",
                "ignore": "class:ignore"
            }.get(listing["type"], "")
            
            asterisk = "*" if listing["hash"] in ld.changed_listings else " "
            
            result.extend([
                ("", prefix),
                ("", asterisk),
                (type_color, f"[{listing['type']}]"),
                ("", f" | {listing['title']} | "),
                ("class:hash", listing["hash"]),
                ("", "\n")
            ])

        for _ in range(ld.page_size - (end - start)):
            result.append(("", "\n"))

        result.extend([
            ("class:title", "------------------------------------------------\n"),
            ("", f"Page: {ld.page + 1}/{(len(ld.filtered_listings) + ld.page_size - 1) // ld.page_size} | "),
            ("", f"Total listings: {len(ld.filtered_listings)}\n"),
            ("class:title", "------------------------------------------------\n"),
            ("class:message", f"{ld.message}\n")
        ])

        return result

    # Create the windows without buffer_name
    main_window = Window(content=FormattedTextControl(get_formatted_text))
    
    search_window = Window(
        height=1,
        content=BufferControl(
            buffer=ld.search_buffer,
            input_processors=[BeforeInput('Search: ')],
        )
    )
    
    message_window = Window(
        height=1,
        content=FormattedTextControl(lambda: ld.message)
    )

    root_container = HSplit([
        main_window,
        search_window,
        message_window
    ])

    layout = Layout(root_container)

    style = Style.from_dict({
        'title': '#ansigreen',
        'downvote': '#ansired',
        'upvote': '#ansigreen',
        'ignore': '#ansiyellow',
        'hash': '#ansicyan',
        'search': '#ansiblue',
        'message': '#ansimagenta',
    })

    app = Application(
        layout=layout,
        key_bindings=kb,
        full_screen=True,
        style=style,
        mouse_support=True,
    )

    return app, ld

def display_processed_listings():
    app, ld = create_listing_display()
    
    if not ld.listings:
        console.print("[yellow]No listings found. The results file may be empty.[/yellow]")
        input("Press Enter to return to the main menu...")
        return

    try:
        app.run()
    except Exception as e:
        console.print(f"[bold red]An error occurred: {str(e)}[/bold red]")
    
    if ld.changed_listings:
        save = console.input("Do you want to save your changes? (y/n): ").lower()
        if save == 'y':
            ld.save_changes()

def run_display_listings():
    display_processed_listings()

if __name__ == "__main__":
    run_display_listings()
