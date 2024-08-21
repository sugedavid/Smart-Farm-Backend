import firebase_admin
import uvicorn
import os

from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import OAuth2PasswordBearer
from firebase_admin import firestore
from openai import OpenAI

from schemas.analysis_schema import AnalysisRequest, AnalysisResponse

# initialize FastAPI
app = FastAPI()

# initialize firestore db
db = firestore.client()

# initialize OpenAI API
openai_client = OpenAI(api_key=os.getenv("SMART_FARM_OPENAI_API_KEY"))
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# create message api
@app.post("/analysis", response_model=AnalysisResponse)
async def create_analysis(analysis_request: AnalysisRequest, token: str = Security(oauth2_scheme)):
    try:
        thread_id = analysis_request.thread_id
        if not thread_id:
            # create a new thread
            thread = openai_client.beta.threads.create()
            thread_id = thread.id

            # save user data to firestore
            doc_ref = db.collection("users").document(analysis_request.user_id)
            doc_ref.set(
                {
                    "thread_id": thread_id
                }
            )

        instructions = analysis_request.instructions

        # create message
        openai_client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=analysis_request.content
        )

        # run assistant
        openai_client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=analysis_request.assistant_id,
            instructions=instructions,
        )

        # assistant response
        messages = openai_client.beta.threads.messages.list(
            thread_id=thread_id
        )

        message_data = [message.model_dump() for message in messages.data]

        return AnalysisResponse(object=messages.object, data=message_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))