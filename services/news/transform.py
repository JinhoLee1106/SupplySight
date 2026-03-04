from anthropic import AsyncAnthropic
from dotenv import load_dotenv
import asyncio
import os
import json, re


load_dotenv()
claude_api_key = os.getenv("CLAUDE_API_KEY")
client = AsyncAnthropic(api_key = claude_api_key)


async def generate_structured_news(news, client) -> dict:
    message = await client.messages.create(
        model = "claude-haiku-4-5",
        max_tokens = 500,
        messages=[
            {
                "role": "user",
                "content": str(news) + " Is this article related to the supply chain status of tomatoes in the US. If yes assign an relatness score from 0 to 100(0 being not related and 100 being extremely important) and output the response in a json format: {'score': (int), 'affected_products': (list of products)}, if not return an empty json. DO NOT INCLUDE EXTRA EXPLAINATION outside of the json", # prompt needs improvement
            }
        ],
    )
    raw_str = str(message.content)
    json_str = re.findall(r'\{.*?\}', raw_str)
    if json_str:
        return json.loads(json_str[0])
    else:
        return {}

'''test_article = {
    "title": "Mechanistic elucidation of a terpenoid nano-bionematicide for the management of root-knot nematodes, Meloidogyne incognita infecting tomato",
    "content": "Plant-parasitic nematodes, particularly Meloidogyne incognita, represent a major constraint to global vegetable production and cause substantial yield losses. Although azadirachtin exhibits strong nematicidal potential, its practical application is limited by…"
}
print(asyncio.run(generate_structured_news(test_article, client)))'''