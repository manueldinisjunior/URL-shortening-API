from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from typing import Any

from flask import Flask, jsonify, redirect, request

BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def encode_base62(number: int) -> str:
    if number <= 0:
        raise ValueError("number must be positive")
    base = len(BASE62_ALPHABET)
    encoded = []
    while number:
        number, rem = divmod(number, base)
        encoded.append(BASE62_ALPHABET[rem])
    return "".join(reversed(encoded))


@dataclass
class ShortURL:
    id: int
    original_url: str
    code: str


class URLRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._ensure_schema()

    def _get_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_schema(self) -> None:
        with self._get_connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS urls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_url TEXT NOT NULL,
                    code TEXT NOT NULL UNIQUE
                )
                """
            )

    def create(self, original_url: str) -> ShortURL:
        with self._get_connection() as connection:
            cursor = connection.execute(
                "INSERT INTO urls (original_url, code) VALUES (?, ?)",
                (original_url, ""),
            )
            url_id = cursor.lastrowid
            if url_id is None:
                raise RuntimeError("Failed to generate URL id")
            code = encode_base62(url_id)
            connection.execute(
                "UPDATE urls SET code = ? WHERE id = ?",
                (code, url_id),
            )
        return ShortURL(id=url_id, original_url=original_url, code=code)

    def fetch_by_code(self, code: str) -> ShortURL | None:
        with self._get_connection() as connection:
            row = connection.execute(
                "SELECT id, original_url, code FROM urls WHERE code = ?",
                (code,),
            ).fetchone()
        if row is None:
            return None
        return ShortURL(id=row["id"], original_url=row["original_url"], code=row["code"])


@dataclass
class AppConfig:
    base_url: str
    database_url: str

    @classmethod
    def from_env(cls) -> "AppConfig":
        base_url = os.getenv("BASE_URL", "http://localhost:5000")
        database_url = os.getenv("DATABASE_URL", "urls.db")
        return cls(base_url=base_url.rstrip("/"), database_url=database_url)


def create_app() -> Flask:
    config = AppConfig.from_env()
    app = Flask(__name__)
    repository = URLRepository(config.database_url)

    @app.get("/health")
    def health() -> Any:
        return jsonify({"status": "ok"})

    @app.post("/shorten")
    def shorten() -> Any:
        payload = request.get_json(silent=True) or {}
        original_url = payload.get("url")
        if not original_url or not isinstance(original_url, str):
            return jsonify({"error": "url is required"}), 400

        short_url = repository.create(original_url)
        return (
            jsonify(
                {
                    "code": short_url.code,
                    "short_url": f"{config.base_url}/{short_url.code}",
                    "url": short_url.original_url,
                }
            ),
            201,
        )

    @app.get("/<code>")
    def redirect_to_url(code: str) -> Any:
        short_url = repository.fetch_by_code(code)
        if short_url is None:
            return jsonify({"error": "not found"}), 404
        return redirect(short_url.original_url, code=302)

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000)
