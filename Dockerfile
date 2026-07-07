FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias do SO
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar (inclui o extra MCP: o bridge importa mcp.server.fastmcp)
COPY requirements.txt requirements-mcp.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-mcp.txt

# Copiar os arquivos do projeto
COPY . .

# Expor portas se houver (a ponte MCP usa stdio por padrao, mas pode rodar via rede)
EXPOSE 8000

ENV KABBALAH_LOG_LEVEL=WARNING
ENV PYTHONUNBUFFERED=1

# Entrada padrao para a ponte MCP
CMD ["python", "kabbalah_mcp_bridge.py"]
