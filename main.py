"""Entry point for the prototype."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

SCENARIOS_DIR = Path(__file__).resolve().parent / "data" / "scenarios"


def _discover_scenarios() -> list[str]:
    return sorted(p.stem for p in SCENARIOS_DIR.glob("*.json"))


def _import_pygame_deps():
    """Import UI deps, raising SystemExit with a helpful message on failure."""
    try:
        import pygame
        from ui.app import KriegsspielApp
        from ui.bitmap_font import BitmapFont
        from ui import themes
        return pygame, KriegsspielApp, BitmapFont, themes
    except ImportError as exc:
        raise SystemExit(
            "Pygame is required. Install with `pip install -r requirements.txt`."
        ) from exc


def run_main_menu() -> None:
    pygame, KriegsspielApp, BitmapFont, themes = _import_pygame_deps()
    pygame.init()
    screen = pygame.display.set_mode(themes.WINDOW_SIZE)
    pygame.display.set_caption("Kriegsspiel")
    clock = pygame.time.Clock()

    font = BitmapFont(scale=2)
    small_font = BitmapFont(scale=1)

    from ui.main_menu import MainMenu
    from ui.difficulty_select import DifficultySelect

    menu = MainMenu(font, small_font)
    state = "menu"   # "menu", "difficulty", "scenario_list"
    diff_select = DifficultySelect(font, small_font)
    scenarios = _discover_scenarios()
    scenario_cursor = 0

    def _run_game(scenario_name: str | None, seed: int, difficulty: str, game_state=None) -> None:
        pygame.quit()
        app = KriegsspielApp(
            scenario_name=scenario_name or "skirmish_small",
            seed=seed,
            difficulty=difficulty,
            game_state=game_state,
        )
        app.run()
        # After game ends, re-init pygame and go back to menu
        pygame.init()

    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            if state == "menu":
                action = menu.handle_event(event)
                if action == "quit":
                    running = False
                elif action == "quick_battle":
                    state = "difficulty"
                elif action == "scenario_select":
                    state = "scenario_list"
                    scenario_cursor = 0
                elif action == "tutorial":
                    _run_game("tutorial", seed=1, difficulty="medium")
                    state = "menu"
                elif action == "editor":
                    try:
                        from ui.scenario_editor_ui import ScenarioEditorApp
                        pygame.quit()
                        ScenarioEditorApp().run()
                        pygame.init()
                    except Exception:
                        pass
                    state = "menu"
                elif action == "campaign":
                    # Show "coming soon" for 2s
                    _show_message(screen, font, small_font, "CAMPAIGN MODE COMING SOON", 2.0)
                    state = "menu"

            elif state == "difficulty":
                result = diff_select.handle_event(event)
                if result == "cancel":
                    state = "menu"
                elif result is not None:
                    from core.scenario_generator import generate_skirmish, SkirmishConfig
                    cfg = SkirmishConfig(size="medium", seed=42)
                    gs = generate_skirmish(cfg, rng_seed=42)
                    _run_game(None, seed=42, difficulty=result, game_state=gs)
                    state = "menu"

            elif state == "scenario_list":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        state = "menu"
                    elif event.key == pygame.K_UP:
                        scenario_cursor = max(0, scenario_cursor - 1)
                    elif event.key == pygame.K_DOWN:
                        scenario_cursor = min(len(scenarios) - 1, scenario_cursor + 1)
                    elif event.key == pygame.K_RETURN:
                        _run_game(scenarios[scenario_cursor], seed=1, difficulty="medium")
                        state = "menu"
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # click on scenario items
                    idx = _scenario_click(event.pos, scenarios)
                    if idx is not None:
                        _run_game(scenarios[idx], seed=1, difficulty="medium")
                        state = "menu"

        if not running:
            break

        screen.fill(themes.PANEL_BG)
        if state == "menu":
            menu.update(dt)
            menu.draw(screen)
        elif state == "difficulty":
            diff_select.update(dt)
            diff_select.draw(screen)
        elif state == "scenario_list":
            _draw_scenario_list(screen, font, small_font, scenarios, scenario_cursor)

        pygame.display.flip()

    pygame.quit()


def _show_message(screen, font, small_font, text: str, duration: float) -> None:
    import pygame
    from ui import themes
    end = time.time() + duration
    while time.time() < end:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
        screen.fill(themes.PANEL_BG)
        surf = font.render(text, True, themes.TEXT)
        screen.blit(surf, surf.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2)))
        pygame.display.flip()
        pygame.time.wait(16)


def _draw_scenario_list(screen, font, small_font, scenarios, cursor) -> None:
    import pygame
    from ui import themes
    w, h = screen.get_size()
    screen.fill(themes.PANEL_BG)
    title = font.render("SELECT SCENARIO", True, themes.SELECTION)
    screen.blit(title, title.get_rect(centerx=w // 2, y=60))
    hint = small_font.render("ARROW KEYS TO NAVIGATE, ENTER TO LAUNCH, ESC TO BACK", True, themes.MUTED_TEXT)
    screen.blit(hint, hint.get_rect(centerx=w // 2, y=100))
    item_h = 30
    item_w = 400
    start_y = 140
    for i, name in enumerate(scenarios):
        rect = pygame.Rect(w // 2 - item_w // 2, start_y + i * (item_h + 4), item_w, item_h)
        if i == cursor:
            pygame.draw.rect(screen, (60, 80, 120), rect, border_radius=3)
            pygame.draw.rect(screen, themes.SELECTION, rect, 1, border_radius=3)
            color = themes.SELECTION
        else:
            pygame.draw.rect(screen, (42, 47, 60), rect, border_radius=3)
            color = themes.TEXT
        text = small_font.render(name.replace("_", " ").upper(), True, color)
        screen.blit(text, text.get_rect(center=rect.center))


def _scenario_click(pos, scenarios) -> int | None:
    import pygame
    from ui import themes
    w, h = themes.WINDOW_SIZE
    item_h = 30
    item_w = 400
    start_y = 140
    for i in range(len(scenarios)):
        rect = pygame.Rect(w // 2 - item_w // 2, start_y + i * (item_h + 4), item_w, item_h)
        if rect.collidepoint(pos):
            return i
    return None


def main() -> None:
    scenarios = _discover_scenarios()
    parser = argparse.ArgumentParser(description="Run the Kriegsspiel prototype.")
    parser.add_argument(
        "--scenario",
        default="skirmish_small",
        choices=scenarios,
        help="Scenario to load (any JSON in data/scenarios/).",
    )
    parser.add_argument("--seed", type=int, default=1, help="Random seed.")
    parser.add_argument(
        "--mode",
        choices=["game", "quick_battle", "menu"],
        default="menu",
        help="Launch mode.",
    )
    parser.add_argument(
        "--difficulty",
        choices=["easy", "medium", "hard", "historical"],
        default="medium",
        help="AI difficulty.",
    )
    args = parser.parse_args()

    pygame, KriegsspielApp, BitmapFont, themes = _import_pygame_deps()

    if args.mode == "menu":
        run_main_menu()
    elif args.mode == "game":
        KriegsspielApp(scenario_name=args.scenario, seed=args.seed, difficulty=args.difficulty).run()
    elif args.mode == "quick_battle":
        from core.scenario_generator import generate_skirmish, SkirmishConfig
        cfg = SkirmishConfig(size="medium", seed=args.seed)
        gs = generate_skirmish(cfg, rng_seed=args.seed)
        KriegsspielApp(
            scenario_name="skirmish_small",
            seed=args.seed,
            difficulty=args.difficulty,
            game_state=gs,
        ).run()


if __name__ == "__main__":
    main()
