try:
    import sqlalchemy
    print(f"SQLAlchemy version: {sqlalchemy.__version__}")
except ImportError:
    print("SQLAlchemy not found")
