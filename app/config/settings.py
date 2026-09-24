from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_host: str = "127.0.0.1"; app_port: int = 8000
    dns_host: str = "127.0.0.1"; dns_port: int = 5353
    dns_upstream_servers: str = "8.8.8.8,1.1.1.1"; dns_upstream_port: int = 53
    dns_timeout_seconds: float = 2; dns_retries: int = 1
    cache_max_entries: int = 500; simulation_interval_ms: int = 1000
    database_url: str = "sqlite:///./data/dns_analytics.db"; log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    @property
    def upstreams(self): return [x.strip() for x in self.dns_upstream_servers.split(",") if x.strip()]
    @property
    def cors(self): return [x.strip() for x in self.cors_origins.split(",")]
settings = Settings()
