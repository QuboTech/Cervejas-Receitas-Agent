from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import anthropic, os
from supabase import create_client
from datetime import datetime

app = FastAPI(title="Cerveja Artesanal API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class GerarRequest(BaseModel):
    ingredientes: str
    volume: float = 20.0

class SalvarRequest(BaseModel):
    nome: str
    ingredientes: str
    receita: str
    volume: float = 20.0

@app.get("/")
def health():
    return {"status": "ok", "service": "cerveja-artesanal-api"}

@app.post("/gerar")
async def gerar(req: GerarRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(500, "ANTHROPIC_API_KEY não configurada")
    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""Você é um mestre cervejeiro (Brewmaster) com 20 anos de experiência, especialista em todos os estilos BJCP.

O cervejeiro tem estes ingredientes disponíveis: {req.ingredientes}
Volume final a produzir: {req.volume} litros

Crie uma receita completa e técnica seguindo este formato EXATO:

🍺 NOME DA RECEITA
Estilo BJCP: [código e nome do estilo mais adequado]

📊 PARÂMETROS TÉCNICOS ESTIMADOS:
OG: [valor] | FG: [valor] | ABV: [valor]% | IBU: [valor] | SRM: [valor] | EBC: [valor]

📋 INGREDIENTES (para {req.volume}L | eficiência 72%):

MALTES:
[malte] - [quantidade em kg] ([% do grist]) - [função]
[...outros maltes...]

LÚPULOS:
[lúpulo] - [g] - [tempo de fervura]min - [AA%] - [~IBU contrib] - [função: amargor/aroma/dual]
[...outros lúpulos...]

LEVEDURA:
[nome] - Atenuação [%] - Temp: [°C] - [características]

ADJUNTOS/ESPECIAIS (se aplicável):
[item] - [quantidade] - [quando adicionar]

💧 VOLUMES DE ÁGUA:
- Água de mostura: [L] a [temp]°C por [min]min
- Água de lavagem (sparge): [L]
- Volume pré-fervura: [L]
- Perdas estimadas: absorção [L] + evaporação [L] + trub [L]

👨‍🍳 PROCESSO DE BRASSAGEM:
1. [passo detalhado com temperatura e tempo]
2. [...]
[máximo 8 passos claros]

🦠 FERMENTAÇÃO:
- Primária: [dias] a [temp]°C
- Secundária/Guarda: [se aplicável]
- Carbonatação: [método e volumes de CO2]

💡 NOTAS DO MESTRE:
[2-3 dicas específicas para essa receita, incluindo o que esperar no sabor final]

🍻 PERFIL DE SABOR ESPERADO:
[descrição sensorial do resultado final: aroma, cor, sabor, amargor, final de boca]"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    return {"receita": message.content[0].text}

@app.post("/salvar")
async def salvar(req: SalvarRequest):
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise HTTPException(500, "Supabase não configurado")
    sb = create_client(url, key)
    data = {"nome": req.nome, "ingredientes": req.ingredientes,
            "receita": req.receita, "volume": req.volume,
            "criado_em": datetime.utcnow().isoformat()}
    result = sb.table("receitas_cerveja").insert(data).execute()
    return {"ok": True, "id": result.data[0]["id"]}

@app.get("/receitas")
async def listar():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise HTTPException(500, "Supabase não configurado")
    sb = create_client(url, key)
    result = sb.table("receitas_cerveja").select("id,nome,ingredientes,volume,criado_em").order("criado_em", desc=True).limit(50).execute()
    return {"receitas": result.data}

@app.get("/receitas/{id}")
async def detalhe(id: int):
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise HTTPException(500, "Supabase não configurado")
    sb = create_client(url, key)
    result = sb.table("receitas_cerveja").select("*").eq("id", id).single().execute()
    if not result.data:
        raise HTTPException(404, "Receita não encontrada")
    return result.data

@app.delete("/receitas/{id}")
async def deletar(id: int):
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise HTTPException(500, "Supabase não configurado")
    sb = create_client(url, key)
    sb.table("receitas_cerveja").delete().eq("id", id).execute()
    return {"ok": True}
