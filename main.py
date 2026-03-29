"""Entry point for the prototype."""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("SDL_VIDEO_HIGHDPI_DISABLED", "1")

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
    from core.campaign import CampaignState, STANDARD_CAMPAIGN
    from core.scenario import load_builtin_scenario
    from core.scenario_generator import SkirmishConfig, generate_skirmish
    from ui.campaign_ui import CampaignUI
    from ui.difficulty_select import DifficultySelect
    from ui.main_menu import MainMenu
    from ui.quick_battle import QuickBattle
    from ui.scenario_select import ScenarioSelect

    save_path = Path.home() / ".kriegsspiel" / "campaign.json"

    def _build_ui():
        pygame.init()
        screen = pygame.display.set_mode(themes.WINDOW_SIZE)
        pygame.display.set_caption("Kriegsspiel")
        font = BitmapFont(scale=2)
        small_font = BitmapFont(scale=1)
        return screen, font, small_font

    screen, font, small_font = _build_ui()
    clock = pygame.time.Clock()

    menu = MainMenu(font, small_font)
    diff_select = DifficultySelect(font, small_font)
    quick_battle = QuickBattle(font, small_font)
    scenario_select = ScenarioSelect(font, small_font)
    campaign_ui = CampaignUI(font, small_font)

    state = "menu"
    pending_launch: dict | None = None

    def _refresh_widgets() -> None:
        nonlocal menu, diff_select, quick_battle, scenario_select, campaign_ui
        menu = MainMenu(font, small_font)
        diff_select = DifficultySelect(font, small_font)
        quick_battle = QuickBattle(font, small_font)
        scenario_select = ScenarioSelect(font, small_font)
        campaign_ui = CampaignUI(font, small_font)

    def _run_game(*, scenario_name: str, seed: int, difficulty: str, game_state=None):
        nonlocal screen, font, small_font
        pygame.quit()
        app = KriegsspielApp(
            scenario_name=scenario_name,
            seed=seed,
            difficulty=difficulty,
            game_state=game_state,
        )
        app.run()
        screen, font, small_font = _build_ui()
        _refresh_widgets()
        return app

    def _launch_pending(difficulty: str) -> None:
        nonlocal state, pending_launch, campaign_ui
        if pending_launch is None:
            state = "menu"
            return
        launch = pending_launch
        pending_launch = None
        mode = launch["kind"]
        if mode == "scenario":
            _run_game(
                scenario_name=launch["scenario"],
                seed=launch.get("seed", 1),
                difficulty=difficulty,
            )
            state = "menu"
            return
        if mode == "quick_battle":
            cfg = SkirmishConfig(
                size=launch["size"],
                blue_force=launch["force"],
                red_force=launch["force"],
                seed=launch.get("seed", 42),
            )
            gs = generate_skirmish(cfg, rng_seed=launch.get("seed", 42))
            _run_game(
                scenario_name="skirmish_small",
                seed=launch.get("seed", 42),
                difficulty=difficulty,
                game_state=gs,
            )
            state = "menu"
            return
        if mode == "campaign":
            current = campaign_ui.state.current_scenario
            if current is None:
                state = "campaign"
                return
            scenario = load_builtin_scenario(current.scenario_id)
            from core.game import GameState
            campaign_game = GameState.from_scenario(scenario, rng_seed=launch.get("seed", 1))
            campaign_ui.state.apply_carry_over(campaign_game.units)
            game = _run_game(
                scenario_name=current.scenario_id,
                seed=launch.get("seed", 1),
                difficulty=difficulty,
                game_state=campaign_game,
            )
            winner = game.victory_report.winner if game.victory_report is not None else None
            campaign_ui.state.record_result(
                current.scenario_id,
                winner=winner,
                turns_taken=game.game.current_turn,
                surviving_units=game.game.units.values(),
            )
            save_path.parent.mkdir(parents=True, exist_ok=True)
            campaign_ui.state.save(str(save_path))
            state = "campaign"
            return

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
                    state = "quick_battle"
                elif action == "scenario_select":
                    state = "scenario_select"
                elif action == "tutorial":
                    pending_launch = {"kind": "scenario", "scenario": "tutorial", "seed": 1}
                    state = "difficulty"
                elif action == "editor":
                    try:
                        from ui.scenario_editor_ui import ScenarioEditorApp
                        pygame.quit()
                        ScenarioEditorApp().run()
                        screen, font, small_font = _build_ui()
                        _refresh_widgets()
                    except Exception:
                        pass
                    state = "menu"
                elif action == "campaign":
                    campaign_ui = CampaignUI(font, small_font)
                    state = "campaign"

            elif state == "difficulty":
                result = diff_select.handle_event(event)
                if result == "cancel":
                    state = "menu"
                elif result is not None:
                    _launch_pending(result)

            elif state == "quick_battle":
                result = quick_battle.handle_event(event)
                if result == "back":
                    state = "menu"
                elif isinstance(result, dict):
                    pending_launch = {"kind": "quick_battle", **result, "seed": 42}
                    state = "difficulty"

            elif state == "scenario_select":
                result = scenario_select.handle_event(event)
                if result == "back":
                    state = "menu"
                elif isinstance(result, dict):
                    pending_launch = {
                        "kind": "scenario",
                        "scenario": result["scenario"],
                        "seed": 1,
                    }
                    state = "difficulty"

            elif state == "campaign":
                result = campaign_ui.handle_event(event)
                if result == "back":
                    state = "menu"
                elif result == "start_battle":
                    pending_launch = {"kind": "campaign", "seed": 1}
                    state = "difficulty"

        if not running:
            break

        screen.fill(themes.PANEL_BG)
        if state == "menu":
            menu.update(dt)
            menu.draw(screen)
        elif state == "difficulty":
            diff_select.update(dt)
            diff_select.draw(screen)
        elif state == "quick_battle":
            quick_battle.draw(screen)
        elif state == "scenario_select":
            scenario_select.draw(screen)
        elif state == "campaign":
            campaign_ui.draw(screen)

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
