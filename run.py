import warnings

warnings.filterwarnings(
    "ignore",
    message="urllib3 v2 only supports OpenSSL.*",
)

from skybox.app import run_app


if __name__ == "__main__":
    run_app()
