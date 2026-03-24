import os

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="BuyWise Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProductRequest(BaseModel):
    title: str
    price: str
    reviews: str


class ChatRequest(BaseModel):
    question: str
    context_reviews: list[str]


def build_prompt(payload: ProductRequest) -> str:
    return (
        "You are an expert shopping assistant.\n"
        "Analyze the product below and provide a concise response with:\n"
        "- Pros\n"
        "- Cons\n"
        "- Brief verdict\n\n"
        f"Title: {payload.title}\n"
        f"Price: {payload.price}\n"
        f"Reviews: {payload.reviews}\n"
    )


def build_chat_prompt(payload: ChatRequest) -> str:
    reviews_block = "\n".join(
        f"- Review {idx}: {review}"
        for idx, review in enumerate(payload.context_reviews, start=1)
        if review.strip()
    )
    return (
        "You are a professional ecommerce shopping assistant.\n"
        "Use ONLY the review context below to answer the user's question.\n"
        "If the reviews do not contain enough information, clearly say you do not know.\n"
        "Do not invent details.\n\n"
        f"Review Context:\n{reviews_block or '- No review content provided.'}\n\n"
        f"User Question:\n{payload.question}\n"
    )


def invoke_asi1(prompt: str) -> str:
    api_key = os.getenv("ASI1_API_KEY")
    if not api_key:
        raise RuntimeError("Missing ASI1_API_KEY in environment.")

    base_url = os.getenv("ASI1_BASE_URL", "https://api.asi1.ai/v1").rstrip("/")
    model_name = os.getenv("ASI1_MODEL", "asi1")

    response = requests.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        },
        timeout=45,
    )
    response.raise_for_status()
    data = response.json()

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected ASI1 response format: {data}") from exc


@app.post("/api/analyze")
def analyze_product(payload: ProductRequest) -> dict[str, str]:
    prompt_string = build_prompt(payload)

    try:
        output_text = invoke_asi1(prompt_string)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ASI1 request failed: {exc}") from exc

    return {"result": output_text}


@app.post("/chat")
def chat_with_reviews(payload: ChatRequest) -> dict[str, str]:
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    if not payload.context_reviews:
        raise HTTPException(status_code=400, detail="Review context is required.")

    prompt_string = build_chat_prompt(payload)
    try:
        output_text = invoke_asi1(prompt_string)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ASI1 request failed: {exc}") from exc

    return {"answer": output_text}