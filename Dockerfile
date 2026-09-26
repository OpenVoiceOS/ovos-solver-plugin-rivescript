# ovos-solver-plugin-rivescript served via ovos-persona-server.
#
# opm.agents.chat and neon.plugin.solver (legacy) do nothing on their own --
# they are plugin entry points, not a server. This image runs
# ovos-persona-server with a single persona ("rivescript-bot") that is
# configured to use this plugin as its solver, so the image is a ready
# OpenAI-compatible chat endpoint over RiveScript.
FROM python:3.14-slim

RUN useradd -m -u 1000 ovos

WORKDIR /app
COPY . /app

# ovos-persona-server[mcp]>=0.17.0a1: from that release the [mcp] extra alone
# no longer mounts the MCP endpoint, --mcp must be passed explicitly (see
# ENTRYPOINT below). The plugin itself is installed from the local checkout,
# so its version always matches the image.
RUN pip install --no-cache-dir \
        "ovos-persona-server[mcp]>=0.17.0a1" \
    && pip install --no-cache-dir .

USER ovos
ENV HOME=/home/ovos

EXPOSE 8337

# --persona points at the bundled rivescript-bot persona, whose "solvers"
# list names this plugin's entry point ("ovos-solver-rivescript-plugin").
# The same name is registered under both opm.agents.chat and the legacy
# neon.plugin.solver group; ovos-persona-server prefers the ChatEngine.
ENTRYPOINT ["ovos-persona-server", \
            "--persona", "/app/persona/rivescript_bot.json", \
            "--mcp", \
            "--port", "8337", "--host", "0.0.0.0"]
