"""Command line: ``agenteval <command>``."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys

from agenteval.core.config import get_settings


def _serve(args: argparse.Namespace) -> None:
    import uvicorn

    uvicorn.run(
        "agenteval.main:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        workers=args.workers,
        proxy_headers=True,
        forwarded_allow_ips="*",
        access_log=False,
        log_config=None,
        timeout_graceful_shutdown=30,
    )


def _worker(_: argparse.Namespace) -> None:
    from agenteval.worker import main

    asyncio.run(main())


def _migrate(_: argparse.Namespace) -> None:
    from agenteval.migrations.runner import upgrade

    upgrade(get_settings().database_url)
    print("migrations applied")


def _revision(args: argparse.Namespace) -> None:
    from agenteval.migrations.runner import revision

    revision(get_settings().database_url, args.message)


async def _create_owner(email: str, name: str, password: str) -> None:
    from sqlalchemy import func, select

    from agenteval.core.db import Database
    from agenteval.core.security import hash_password, password_problems
    from agenteval.orgs.models import Membership, Organization
    from agenteval.users.models import User

    if problems := password_problems(password):
        sys.exit("password needs " + ", ".join(problems))
    db = Database(get_settings().database_url, pool_size=1, max_overflow=0)
    try:
        async with db.sessionmaker() as session:
            existing = await session.scalar(
                select(User).where(func.lower(User.email) == email.lower())
            )
            if existing is not None:
                existing.password_hash = hash_password(password)
                existing.disabled = False
                existing.session_version += 1
                user = existing
                print(f"updated {email}")
            else:
                user = User(email=email.lower(), name=name, password_hash=hash_password(password))
                session.add(user)
                await session.flush()
                print(f"created {email}")
            org = await session.scalar(select(Organization).where(Organization.slug == "default"))
            if org is None:
                org = Organization(name="Default organization", slug="default")
                session.add(org)
                await session.flush()
            membership = await session.scalar(
                select(Membership).where(
                    Membership.organization_id == org.id, Membership.user_id == user.id
                )
            )
            if membership is None:
                session.add(Membership(organization_id=org.id, user_id=user.id, role="owner"))
            else:
                membership.role = "owner"
            await session.commit()
    finally:
        await db.dispose()


def _owner(args: argparse.Namespace) -> None:
    password = os.environ.get("AGENTEVAL_OWNER_PASSWORD") or getpass.getpass("Password: ")
    asyncio.run(_create_owner(args.email, args.name, password))


def _openapi(_: argparse.Namespace) -> None:
    from agenteval.openapi import spec, to_yaml

    sys.stdout.write(to_yaml(spec()))


def _seed_demo(_: argparse.Namespace) -> None:
    from agenteval.demo.seed import run

    asyncio.run(run())


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="agenteval", description="Euron Open AgentEval")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("serve", help="run the dashboard and admin API")
    p.add_argument("--host", default="0.0.0.0")  # noqa: S104 the container must listen on all interfaces
    p.add_argument("--port", type=int, default=int(os.environ.get("PORT", "5730")))
    p.add_argument("--workers", type=int, default=int(os.environ.get("WEB_CONCURRENCY", "2")))
    p.set_defaults(fn=_serve)

    sub.add_parser("worker", help="claim and run queued evaluations").set_defaults(fn=_worker)
    sub.add_parser("migrate", help="apply database migrations").set_defaults(fn=_migrate)

    p = sub.add_parser("revision", help="autogenerate a migration from the models")
    p.add_argument("-m", "--message", required=True)
    p.set_defaults(fn=_revision)

    sub.add_parser("openapi", help="print the OpenAPI document as YAML").set_defaults(fn=_openapi)

    p = sub.add_parser("create-owner", help="create or reset an owner account")
    p.add_argument("--email", required=True)
    p.add_argument("--name", default="Owner")
    p.set_defaults(fn=_owner)

    sub.add_parser(
        "seed-demo", help="seed a realistic organization, agent and evaluation history"
    ).set_defaults(fn=_seed_demo)

    args = parser.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
