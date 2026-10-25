"""Retired paid-development entry point; historical source retained in docs/history.

Standing scope permits only explicitly bounded trial-credit use. This command
cannot create an allowance, alter accounting or perform a provider request.
"""
from app.llm.client import LiveBlocked


def main():
    raise LiveBlocked('Historical paid development execution is retired under the standing trial-credit-only project scope')


if __name__ == '__main__':
    main()
