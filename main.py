"""Entry point for the prototype."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Kriegsspiel prototype.")
    parser.add_argument(
        "--scenario",
        default="skirmish_small",
        choices=["tutorial", "skirmish_small", "assault_on_hill", "full_battle"],
        help="Built-in scenario to load.",
    )
    parser.add_argument("--seed", type=int, default=1, help="Random seed for combat and AI.")
    args = parser.parse_args()

    try:
        from ui.app import KriegsspielApp
    except ImportError as exc:
        raise SystemExit(
            "Pygame is required for the UI. Install dependencies with "
            "`pip install -r requirements.txt`."
        ) from exc

    KriegsspielApp(scenario_name=args.scenario, seed=args.seed).run()


if __name__ == "__main__":
    main()
