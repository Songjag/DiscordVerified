import asyncio
import aiomysql
import logging
import os
import sys
import socket
import subprocess
import importlib
from configparser import ConfigParser
from typing import Optional, Tuple
from contextlib import asynccontextmanager

logger = logging.getLogger("msql_logger")
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    fmt = logging.Formatter("%(asctime)s | PID:%(process)d | %(levelname)s | %(message)s")
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    os.makedirs("logs", exist_ok=True)
    file = logging.FileHandler("logs/msql.log", encoding="utf-8")
    file.setFormatter(fmt)
    logger.addHandler(stream)
    logger.addHandler(file)
REQUIRED_PACKAGES = ["aiohttp", "customtkinter", "aiomysql"]

def install_missing_pack():
    for pkg in REQUIRED_PACKAGES:
        try:
            importlib.import_module(pkg)
        except ImportError:
            logger.warning(f"Missing package: {pkg}. Installing...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg, "-q"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info(f"Installed: {pkg}")

async def save_config(name: str, host: str, port: int, user: str, password: str):
    path = "Config/configdb.cfg"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        config = ConfigParser()
        config.read(path)
        if not config.has_section(name):
            config.add_section(name)
        config[name].update({
            "host": host,
            "port": str(port),
            "user": user,
            "password": password
        })
        with open(path, "w") as f:
            config.write(f)
        logger.info(f"Saved database config: [{name}]")
    except Exception as e:
        logger.exception(f"[SAVE CONFIG ERROR] {e}")

class CAioMysql:
    def __init__(self, pool: Optional[aiomysql.Pool] = None):
        self.pool = pool
        self.host = self.user = self.db = None

    @staticmethod
    async def check_internet(host="8.8.8.8", port=53, timeout=3):
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            logger.warning("No internet connection detected.")
            return False

    @classmethod
    async def connectdb(
        cls,
        host: str, port: int, user: str, password: str, db: str,
        minsize: int = 1, maxsize: int = 10, autocommit: bool = True
    ):
        try:
            pool = await aiomysql.create_pool(
                host=host, port=port, user=user, password=password, db=db,
                minsize=minsize, maxsize=maxsize, autocommit=autocommit
            )
            logger.info(f"Connected to MySQL [{host}:{port}] - DB: {db}")
            instance = cls(pool)
            instance.host, instance.user, instance.db = host, user, db
            return instance
        except Exception as e:
            logger.exception(f"[CONNECT ERROR] {e}")
            raise

    async def connect(self, host, port, user, password, db, **kwargs):
        self.pool = (await self.connectdb(host, port, user, password, db, **kwargs)).pool
        await save_config(db, host, port, user, password)
        logger.info("Connection established and config saved.")
        return self
    async def close(self):
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            logger.info("Connection pool closed.")
    async def is_connected(self) -> bool:
        try:
            async with self.pool.acquire() as con:
                connection:aiomysql.Connection=con
                await connection.ping()
                return True
        except:
            return False

    async def ping(self):
        async with self.pool.acquire() as con:
            connection:aiomysql.Connection =con
            await connection.ping()
            logger.info("Ping successful.")

    async def get_version(self):
        return await self.fetchone("SELECT VERSION()")

    @asynccontextmanager
    async def session(self):
        async with self.pool.acquire() as con:
            connection:aiomysql.Connection=con
            async with connection.cursor() as cur:
                yield cur
    async def execute(self, query: str, params: Tuple = None, *, retry=2, timeout=10):
        if not self.pool:
            raise ConnectionError("Database not connected.")
        for attempt in range(retry + 1):
            try:
                async with asyncio.timeout(timeout):
                    async with self.session() as cursor:
                        cur:aiomysql.Cursor=cursor
                        await cur.execute(query, params)
                        if query.strip().upper().startswith("SELECT"):
                            rows = await cur.fetchall()
                            logger.info(f"[SELECT] {len(rows)} rows returned.")
                            return rows
                        else:
                            await cur.connection.commit()
                            logger.info(f"[EXECUTE] Rows affected: {cur.rowcount}")
                            return cur.rowcount
            except asyncio.TimeoutError:
                logger.warning(f"[TIMEOUT] Retrying query ({attempt+1}/{retry})")
            except Exception as e:
                logger.exception(f"[EXECUTE ERROR] {e}")
                if attempt >= retry:
                    raise
    async def fetchone(self, query: str, params: Tuple = None):
        rows = await self.execute(query, params)
        return rows[0] if rows else None

    async def fetchall(self, query: str, params: Tuple = None):
        return await self.execute(query, params)
    async def connected(self, db: str, path: str = "Config/configdb.cfg"):
        config = ConfigParser()
        config.read(path)
        if not config.has_section("database"):
            raise FileNotFoundError(f"No config section for database in {path}")
        host = config["database"]["host"]
        port = config.getint("database", "port", fallback=3306)
        user = config["database"]["user"]
        password = config["database"]["password"]
        await self.connect(host, port, user, password, db)
        logger.info(f"Loaded connection from config: {path}")
        return self
