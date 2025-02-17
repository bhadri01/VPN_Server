from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name:str
    app_version:str

    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    postgresql_database_url: str

    environment: str

    servername: str
    interface_name : str
    address : str
    # server_ip: str
    # allowed_ips : str
    # server_port : str
    # endpoint : str


    class Config:
        env_file = ".env"

settings = Settings()