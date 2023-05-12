#! /bin/bash

doIt()
{
    black --line-length 120 scripts
    black --line-length 120 scripts/entrypoint
    black --line-length 120 scripts/rl-scan

    pylama scripts |
    awk '
    /__init__/ && / W0611/ { next }
    / E501 / { next } # E501 line too long [pycodestyle]
    / E203 / { next } # E203 whitespace before ':' [pycodestyle]
    / C901 / { next } # C901 <something> is too complex (<nr>) [mccabe]
    { print }
    '
}

main()
{
    doIt
    mypy --strict --no-incremental scripts
    mypy --strict --no-incremental scripts/entrypoint
    (
        cd scripts
        mypy --strict --no-incremental rl-scan
    )
}

main
