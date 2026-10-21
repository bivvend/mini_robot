
from tempfile import TemporaryDirectory
from pathlib import Path

from src.mini_robot.personality.interests import (
    RobotInterest,
    RobotInterestStore,
)


def run_tests():
    with TemporaryDirectory() as directory:
        db_path = Path(directory) / "test.db"

        store = RobotInterestStore(db_path)

        store.seed([
            "Astronomy",
            "Robotics",
            "Puzzles",
        ])

        assert len(store.get_all()) == 3
        assert store.get("Astronomy") is not None

        # Interest evolution
        store.update(
            "Astronomy",
            enthusiasm_change=0.1,
            curiosity_change=0.05,
        )

        astronomy = store.get("Astronomy")
        assert round(astronomy.enthusiasm, 2) == 0.7
        assert round(astronomy.curiosity, 2) == 0.75

        # New interest
        store.add(RobotInterest(
            topic="Coffee",
            enthusiasm=0.4,
            curiosity=0.8,
            description="Curious about coffee brewing chemistry.",
        ))

        assert len(store.get_all()) == 4

        # Simulate a server restart
        store = RobotInterestStore(db_path)
        store.seed(["Astronomy", "Robotics", "Puzzles"])

        assert len(store.get_all()) == 4
        assert round(store.get("Astronomy").enthusiasm, 2) == 0.7
        assert store.get("Coffee").curiosity == 0.8

        # Values remain bounded
        store.update("Astronomy", enthusiasm_change=5.0)
        assert store.get("Astronomy").enthusiasm == 1.0

        print("All robot interest tests passed.")


if __name__ == "__main__":
    run_tests()
