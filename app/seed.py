"""Populate a demo database: python -m app.seed"""
from .main import conn, create_user, UserIn

DEMO = [
    ("Ada", "Graphic designer", ["logo design", "figma"], ["python", "landing page"]),
    ("Ben", "Backend dev", ["python", "landing page"], ["spanish"]),
    ("Carla", "Spanish tutor", ["spanish"], ["logo design"]),
    ("Dev", "Video editor", ["video editing"], ["figma"]),
    ("Eli", "Marketer", ["social media", "copywriting"], ["video editing"]),
]


def run():
    if conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]:
        print("database not empty, skipping")
        return
    for name, bio, offers, wants in DEMO:
        create_user(UserIn(name=name, bio=bio, offers=offers, wants=wants))
    print(f"seeded {len(DEMO)} users")


if __name__ == "__main__":
    run()
