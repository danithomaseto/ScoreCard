import os

from automation.base import login_with_user_password
from config.operations import OPERATIONS

OPERATION_KEY = "hugo_boss"


def run(headless=True):
    config = OPERATIONS[OPERATION_KEY]
    username = os.environ.get(config["username_env"])
    password = os.environ.get(config["password_env"])

    if not username or not password:
        return {
            "operation": OPERATION_KEY,
            "success": False,
            "message": (
                f"Credenciais nao configuradas. Defina {config['username_env']} e "
                f"{config['password_env']} no arquivo .env."
            ),
        }

    return login_with_user_password(
        login_url=config["login_url"],
        username=username,
        password=password,
        operation_key=OPERATION_KEY,
        headless=headless,
    )
