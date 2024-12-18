import asyncio
from model_request_example import TextGenerate, llama_service, NamedConstants
import os
from dotenv import load_dotenv

load_dotenv()

async def test():
    request = TextGenerate(
        userID="test_user_id",
        prompt="I just built a software product. How do i get people to start using it",
        type=NamedConstants.LLAMA_MODEL,
        id="",
        workspace_id="test_workspace",
        group_id=None,
        pasthistory=None,
        reply=None
    )
    
    try:
        response = await llama_service(request)
        
        if response["status_code"] == 200:
            print("\nResponse from Llama:")
            print("-" * 50)
            print(response["content"]["data"])
            print("\nMetadata:")
            print(f"Chat ID: {response['content']['id']}")
            print(f"User ID: {response['content']['user_id']}")
            print(f"Balance: {response['content']['balance']}")
            print(f"Date: {response['content']['date']}")
        else:
            print(f"Error: {response['content']['message']}")
            
    except Exception as e:
        print(f"Error occurred: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test()) 