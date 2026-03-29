# Kriegsspiel

Early implementation of a Python adaptation of the 1824 Prussian Kriegsspiel.

Current slice:
- Hex-grid battlefield model with terrain, line of sight, and A* pathfinding
- Core unit model for infantry, cavalry, artillery, skirmishers, and commanders
- Infantry exchange-piece logic for reduced frontage states
- Delayed order queue with move, attack, formation, rally, hold, and retreat orders
- Fog-of-war engine with explored terrain and last-known enemy positions
- Combat resolution with digital custom-die tables, morale, and fatigue effects
- Scenario loading for `tutorial`, `skirmish_small`, `assault_on_hill`, and `full_battle`
- Rule-based AI opponent and pygame prototype UI
- Headless tests for map, units, orders, combat, morale, AI, scenarios, and turn flow

Run the test suite with:

```bash
python -m unittest discover -s tests -v
```

Run the pygame prototype with:

```bash
pip install -r requirements.txt
python main.py
```

Load a specific built-in scenario with:

```bash
python main.py --scenario tutorial
python main.py --scenario assault_on_hill
python main.py --scenario full_battle
```
