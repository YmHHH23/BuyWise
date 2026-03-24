import os

import boto3
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


def get_bedrock_client():
    return boto3.client(
        "bedrock-runtime",
        region_name=os.getenv("AWS_REGION"),
    )


def invoke_bedrock(prompt: str) -> str:
    client = get_bedrock_client()
    response = client.converse(
        modelId="global.amazon.nova-2-lite-v1:0",
        messages=[
            {
                "role": "user",
                "content": [{"text": prompt}],
            }
        ],
    )
    return response["output"]["message"]["content"][0]["text"]


@app.post("/api/analyze")
def analyze_product(payload: ProductRequest) -> dict[str, str]:
    prompt_string = build_prompt(payload)

    try:
        output_text = invoke_bedrock(prompt_string)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Bedrock request failed: {exc}") from exc

    return {"result": output_text}


@app.post("/chat")
def chat_with_reviews(payload: ChatRequest) -> dict[str, str]:
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    if not payload.context_reviews:
        raise HTTPException(status_code=400, detail="Review context is required.")

    prompt_string = build_chat_prompt(payload)
    try:
        output_text = invoke_bedrock(prompt_string)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Bedrock request failed: {exc}") from exc

    return {"answer": output_text}