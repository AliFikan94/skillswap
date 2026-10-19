"""Populate a demo database: python -m app.seed   (all demo passwords: demo12345)"""
from .main import SignupIn, conn, create_account

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
        create_account(SignupIn(name=name, email=f"{name.lower()}@demo.test", password="demo12345",
                                bio=bio, offers=offers, wants=wants))
    print(f"seeded {len(DEMO)} users, sign in as ada@demo.test / demo12345")


if __name__ == "__main__":
    run()
