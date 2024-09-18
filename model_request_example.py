from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from datetime import timezone
import bson
import anthropic
from db_connection import db

import logging

logger = logging.getLogger(__name__)


class TextGenerate(BaseModel):
    id: Optional[str] = None
    userID: str
    prompt: str
    type: str
    pasthistory: Optional[list] = None
    reply: Optional[str] = None
    workspace_id: Optional[str] = None
    group_id: Optional[str] = None
    file_url: Optional[str] = None


class ChatHistory(BaseModel):
    user_id: str
    chat_title: str
    type: str
    pinned: Optional[bool] = False
    history: List[object]
    thumbnail_url: str
    createdAt: datetime = None
    workspace_id: Optional[str] = None
    chat_status: Optional[str] = "Active"
    group_id: Optional[str] = None


class NamedConstants:
    CLAUDE_MODEL = "claude"
    USERS_CHAT_HISTORY_COLLECTION = "users_chat_history"
    USERS_COLLECTION = "users"
    CHAT_HISTORY_COLLECTION = "chat_history"
    USERS_BALANCE_COLLECTION = "users_balance"
    claude_api_key = "your_api_key"


def create_chat_history(request, response_data, created_at):
    user_chat = {"role": "user", "content": request.prompt, "user_id": request.userID}
    assistant_chat = {
        "role": "assistant",
        "content": response_data,
        "type": request.type,
    }
    if request.reply is not None:
        user_chat["reply"] = request.reply
    if request.file_url is not None:
        user_chat["file_url"] = request.file_url
    return ChatHistory(
        user_id=request.userID,
        chat_title=request.prompt,
        type=request.type,
        history=[[user_chat, assistant_chat]],
        workspace_id=request.workspace_id,
        group_id=request.group_id,
        createdAt=datetime.now(timezone.utc),
    )


async def push_chat_history(request, string_data):
    update_data = {
        "$push": {
            "history": [
                {"role": "user", "content": request.prompt, "user_id": request.userID}
            ]
        },
        "$set": {"type": request.type},
    }
    if request.reply is not None:
        update_data["$push"]["history"][0]["reply"] = request.reply
    if request.file_url is not None:
        update_data["$push"]["history"][0]["file_url"] = request.file_url
    update_data["$push"]["history"].append(
        {"role": "assistant", "content": string_data, "type": request.type}
    )
    await db.ChatHistory.find_one_and_update(
        {"_id": bson.ObjectId(request.id)}, update_data, new=True
    )


async def update_user_price(user_id, cost):
    return 100


anthropic_client = anthropic.Anthropic(
    api_key=NamedConstants.claude_api_key,
)


def calculate_text_cost(model_name, prompt_tokens, completion_tokens):
    if model_name == NamedConstants.CLAUDE_MODEL:
        return 100
    return 0


async def execute_claude_call(messages, model_name):
    completion = anthropic_client.messages.create(
        model=model_name, max_tokens=1024, messages=messages
    )
    finish_reason = completion.stop_reason
    response_data = " ".join([item.text for item in completion.content])
    prompt_tokens = completion.usage.input_tokens
    completion_tokens = completion.usage.output_tokens
    cost = calculate_text_cost(model_name, prompt_tokens, completion_tokens)

    if finish_reason != "end_turn":
        messages.append({"role": "assistant", "content": response_data})
        messages.append(
            {"role": "user", "content": "The next part of the conversation..."}
        )
        temp_cost, temp_response = await execute_claude_call(messages, model_name)
        cost += temp_cost
        response_data += " " + temp_response
    return cost, response_data


async def check_user_balance(user_id):
    return False


async def claude_service(request: TextGenerate):
    try:
        response = await check_user_balance(request.userID)
        if response:
            return response
        model_name = NamedConstants.CLAUDE_MODEL
        prompt = request.prompt
        if request.id == "":
            messages = [
                {"role": "user", "content": prompt},
            ]
            cost, response_data = await execute_claude_call(messages, model_name)
            created_at = datetime.now()
            new_chat = create_chat_history(request, response_data, created_at)
            saved_chat = await db.ChatHistory.insert_one(dict(new_chat))
            object_id = saved_chat.inserted_id 
            object_id_string = str(object_id)

            balance = await update_user_price(request.userID, cost)
            content = {
                "data": response_data,
                "id": object_id_string,
                "date": created_at.strftime("%I:%M %p"),
                "thumbnail_url": new_chat.thumbnail_url,
                "balance": balance,
                "user_id": request.userID,
            }
        else:
            users_chat_history_collection = db[
                NamedConstants.USERS_CHAT_HISTORY_COLLECTION
            ]
            messages = await users_chat_history_collection.find_one(
                {"_id": bson.ObjectId(request.id)}, {"history": 1}
            )
            if not messages:
                return {"status_code": 404, "content": {"message": "Chat not found"}}
            messages = [
                message
                for conversation in messages["history"]
                for message in conversation
            ]
            logger.debug("logged previous messages")
            if request.reply and request.reply.strip():
                prompt = request.reply + " " + prompt
            messages.append({"role": "user", "content": prompt})
            cost, response_data = await execute_claude_call(messages, model_name)
            await push_chat_history(request, response_data)
            balance = await update_user_price(request.userID, cost)
            content = {
                "data": response_data,
                "id": request.id,
                "reply": request.reply,
                "balance": balance,
                "user_id": request.userID,
            }
        return {"status_code": 200, "content": content}
    except Exception as e:
        return {"status_code": 500, "content": {"message": str(e)}}


# TODO: Implement new_model_service
async def new_model_service(request: TextGenerate):
    pass