from client_dashboard.auth.service import cleanup
from client_dashboard.database import SessionLocal


def main():
    with SessionLocal() as db:
        cleanup(db)
        db.commit()


if __name__ == "__main__":
    main()
